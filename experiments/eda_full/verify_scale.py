#!/usr/bin/env python3
"""Ticket 013a verifier.

Three jobs in one file, so the sampling rule and the aggregation rule are
written down in exactly one place and can be re-run:

  --build-sample   rebuild the sample from the fixed seed and write
                   run/eda_full_20261015/scale_sample.txt
  --aggregate F    join a rim_raw.tsv with the sample and the picture table and
                   write scale_samples.csv and scale_by_stratum.json
  (default)        verify: rebuild the sample and compare, re-derive the
                   per-stratum medians from scale_samples.csv by a second route
                   and diff against scale_by_stratum.json, and re-read a sample
                   of the measured pictures from the shared VM with a separately
                   written rim routine.

Stdlib only. The heavy reading happens on the VM.
"""
import argparse
import base64
import csv
import json
import os
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RUN = os.path.join(REPO, "run", "eda_full_20261015")
PICTURE_TABLE = os.path.join(RUN, "picture_table.csv")
SAMPLE_TXT = os.path.join(RUN, "scale_sample.txt")
SAMPLES_CSV = os.path.join(RUN, "scale_samples.csv")
BY_STRATUM = os.path.join(RUN, "scale_by_stratum.json")

SEED = 20261015
TARGET_N = 200
CAP = 200
LINES = ["L24", "L25", "L26", "L27", "L31"]
GROUPS = ["Updated", "Library"]
VM_ROOT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
NOMINAL_LENS_DIAMETER_UM = 14_200.0  # our own reference, not a client nominal
# Clean rim band in pixels, fixed from the pooled rim histogram before any
# per-stratum number was read. Values below it are mis-located dips.
CLEAN_LO = 640.0
CLEAN_HI = 900.0
STRATUM_KEYS = ["%s|%s" % (g, ln) for g in GROUPS for ln in LINES]
SSH = "C:/Windows/System32/OpenSSH/ssh.exe"
SSH_ARGS = ["-o", "BatchMode=yes", "amd-a100-vm"]


# ---------------------------------------------------------------- sampling
def group_membership(all_folders):
    """Folder groups a picture belongs to, by which folders hold a copy."""
    groups = set()
    for folder in all_folders.split(";"):
        if folder.startswith("Updated "):
            groups.add("Updated")
        elif folder == "ICube Defects Library":
            groups.add("Library")
    return groups


def load_picture_table():
    with open(PICTURE_TABLE, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_sample():
    """Deterministic sample. Returns (stratum -> paths, stratum -> universe size)."""
    import random

    rows = load_picture_table()
    universe = {(g, ln): [] for g in GROUPS for ln in LINES}
    for row in rows:
        for g in group_membership(row["all_folders"]):
            if row["line"] in LINES:
                universe[(g, row["line"])].append(row["winning_path"])

    sampled = {}
    for g in GROUPS:
        for ln in LINES:
            pool = sorted(universe[(g, ln)])          # sorted, so the draw is stable
            rng = random.Random("013a|%d|%s|%s" % (SEED, g, ln))
            n = min(CAP, len(pool))
            sampled[(g, ln)] = sorted(rng.sample(pool, n))
    sizes = {k: len(v) for k, v in universe.items()}
    return sampled, sizes


def write_sample_txt(sampled):
    paths = sorted({p for v in sampled.values() for p in v})
    with open(SAMPLE_TXT, "w", encoding="utf-8", newline="\n") as fh:
        for p in paths:
            fh.write(p + "\n")
    return paths


# ---------------------------------------------------------------- aggregation
def load_raw(path):
    raw = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            p, rim, cav, flag = parts[0], parts[1], parts[2], parts[3]
            raw[p] = (rim, cav, flag)
    return raw


def pct(sorted_vals, q):
    """Same linear interpolation as numpy default, so it matches the JSON."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def trimmed_mean(vals, frac=0.15):
    v = sorted(vals)
    k = int(len(v) * frac)
    if len(v) - 2 * k <= 0:
        return float(sum(v)) / len(v)
    return float(sum(v[k:len(v) - k])) / (len(v) - 2 * k)


def aggregate(raw):
    sampled, sizes = build_sample()
    rows = []
    for g in GROUPS:
        for ln in LINES:
            for p in sampled[(g, ln)]:
                rim, cav, flag = raw.get(p, ("", "", "not_measured"))
                rows.append({
                    "folder_group": g, "line": ln, "stratum": "%s|%s" % (g, ln),
                    "path": p, "rim_px": rim, "cavity_px": cav, "method_flags": flag,
                })

    with open(SAMPLES_CSV, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=["stratum", "folder_group", "line",
                                           "path", "rim_px", "cavity_px",
                                           "method_flags"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    out = {}
    for g in GROUPS:
        for ln in LINES:
            key = "%s|%s" % (g, ln)
            mine = [r for r in rows if r["stratum"] == key]
            ok = [r for r in mine if r["method_flags"] == "ok"]
            flags = {}
            for r in mine:
                flags[r["method_flags"]] = flags.get(r["method_flags"], 0) + 1
            rim = sorted(float(r["rim_px"]) for r in ok)
            cav = sorted(float(r["cavity_px"]) for r in ok)
            n = len(rim)
            rec = {
                "folder_group": g,
                "line": ln,
                "universe_n": sizes[(g, ln)],
                "target_n": TARGET_N,
                "sampled_n": len(mine),
                "capped": sizes[(g, ln)] < TARGET_N,
                "measured_ok_n": n,
                "failed_n": len(mine) - n,
                "flag_counts": dict(sorted(flags.items())),
            }
            if n:
                mean = float(sum(rim)) / n
                sd = statistics.pstdev(rim) if n > 1 else 0.0
                p25, p50, p75 = pct(rim, 0.25), pct(rim, 0.50), pct(rim, 0.75)
                rec["rim_px"] = {
                    "p25": round(p25, 1), "p50": round(p50, 1), "p75": round(p75, 1),
                    "mean": round(mean, 1), "sd": round(sd, 1),
                    "trimmed_mean_15pct": round(trimmed_mean(rim), 1),
                    "rel_spread_pct": round(100.0 * sd / mean, 1),
                    "min": round(rim[0], 1), "max": round(rim[-1], 1),
                }
                rec["cavity_px"] = {
                    "p25": round(pct(cav, 0.25), 1),
                    "p50": round(pct(cav, 0.50), 1),
                    "p75": round(pct(cav, 0.75), 1),
                    "mean": round(sum(cav) / len(cav), 1),
                }
                rec["implied_um_per_px_at_our_14200um_reference"] = {
                    "from_p50": round(NOMINAL_LENS_DIAMETER_UM / p50, 4),
                    "from_mean": round(NOMINAL_LENS_DIAMETER_UM / mean, 4),
                    "note": "our own 14,200 micron reference, not an independent check",
                }
                # Clean band, fixed from the pooled rim histogram before reading
                # any per-stratum number: 640 to 900 px. Values below it are the
                # mis-located dips (the method locking onto an interior feature),
                # values above it are its mirror. This is a measurement-quality
                # filter, written down here so a second reader can repeat it.
                clean = [x for x in rim if CLEAN_LO <= x <= CLEAN_HI]
                rec["contamination_pct"] = round(100.0 * (n - len(clean)) / n, 1)
                if clean:
                    cmean = sum(clean) / len(clean)
                    csd = statistics.pstdev(clean) if len(clean) > 1 else 0.0
                    rec["clean_rim_px"] = {
                        "band_px": [CLEAN_LO, CLEAN_HI],
                        "n": len(clean),
                        "p25": round(pct(clean, 0.25), 1),
                        "p50": round(pct(clean, 0.50), 1),
                        "p75": round(pct(clean, 0.75), 1),
                        "mean": round(cmean, 1),
                        "sd": round(csd, 1),
                        "rel_spread_pct": round(100.0 * csd / cmean, 1),
                    }
            out[key] = rec

    keys = ["%s|%s" % (g, ln) for g in GROUPS for ln in LINES]
    raw_p50 = [out[k]["rim_px"]["p50"] for k in keys if "rim_px" in out[k]]
    raw_sd = [out[k]["rim_px"]["sd"] for k in keys if "rim_px" in out[k]]
    cl = [out[k]["clean_rim_px"] for k in keys if out[k].get("clean_rim_px")]
    cl_p50 = [c["p50"] for c in cl]
    cl_sd = [c["sd"] for c in cl]
    out["_comparison"] = {
        "strata": keys,
        "between_stratum_rim_p50_px": {
            "min": min(raw_p50), "max": max(raw_p50),
            "range_px": round(max(raw_p50) - min(raw_p50), 1),
            "range_pct_of_mean": round(100.0 * (max(raw_p50) - min(raw_p50))
                                       / (sum(raw_p50) / len(raw_p50)), 1),
        },
        "within_stratum_rim_sd_px": {"min": min(raw_sd), "max": max(raw_sd)},
        "between_stratum_clean_rim_p50_px": {
            "min": min(cl_p50), "max": max(cl_p50),
            "range_px": round(max(cl_p50) - min(cl_p50), 1),
            "range_pct_of_mean": round(100.0 * (max(cl_p50) - min(cl_p50))
                                       / (sum(cl_p50) / len(cl_p50)), 1),
        },
        "within_stratum_clean_rim_sd_px": {"min": min(cl_sd), "max": max(cl_sd)},
        "note": ("between-stratum spread is compared with the within-stratum "
                 "spread above; the clean band is %d to %d px"
                 % (CLEAN_LO, CLEAN_HI)),
    }

    with open(BY_STRATUM, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return out


# ---------------------------------------------------------------- verification
REMEASURE = r'''
import os, sys
import numpy as np
from PIL import Image

ROOT = sys.argv[sys.argv.index("--root") + 1]

def rim(path):
    """Independently written re-implementation of the same rim definition,
    re-read from the picture file. Same maths, different code path."""
    im = np.asarray(Image.open(path)).astype(np.float32)
    hi = np.percentile(im, 99.5)
    if hi < 20:
        raise ValueError("dark")
    mask = im > 0.45 * hi
    ys, xs = np.nonzero(mask)
    if xs.size < 50000:
        raise ValueError("small")
    cx, cy = float(xs.mean()), float(ys.mean())
    col = mask.sum(axis=0)
    rwp = mask.sum(axis=1)
    R = (int((col > 0.5 * col.max()).sum())
         + int((rwp > 0.5 * rwp.max()).sum())) / 4.0
    H, W = im.shape
    yy, xx = np.mgrid[0:H, 0:W]
    rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.int64).ravel()
    rmax = int(R * 1.05)
    keep = rad < rmax
    counts = np.bincount(rad[keep], minlength=rmax)
    sums = np.bincount(rad[keep], weights=im.ravel()[keep], minlength=rmax)
    prof = sums / np.maximum(counts, 1)
    sm = np.convolve(prof, np.ones(7) / 7.0, mode="same")
    lo, hc = int(0.50 * R), int(0.92 * R)
    seg = sm[lo:hc]
    w = 25
    pad = np.pad(seg, (w, w), mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(pad, 2 * w + 1)
    base = win.max(axis=1)                      # rolling max, vectorised
    r_edge = lo + int(np.argmax(base - seg))
    return 2.0 * r_edge, 2.0 * R

for line in sys.stdin:
    p = line.rstrip("\n")
    if not p:
        continue
    try:
        rd, cd = rim(os.path.join(ROOT, p))
        sys.stdout.write("%s\t%.1f\t%.1f\n" % (p, rd, cd))
    except Exception as exc:
        sys.stdout.write("%s\tERR\t%s\n" % (p, type(exc).__name__))
'''


def ssh_remeasure(paths):
    blob = base64.b64encode(REMEASURE.encode()).decode()
    remote = ("python3 -c \"import base64;exec(base64.b64decode('%s'))\" "
              "--root '%s'" % (blob, VM_ROOT))
    proc = subprocess.run([SSH] + SSH_ARGS + [remote],
                          input="".join(x + "\n" for x in paths).encode(),
                          capture_output=True)
    if proc.returncode != 0:
        print(proc.stderr.decode(errors="replace"))
        raise SystemExit("ssh re-measure failed")
    out = {}
    for line in proc.stdout.decode().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            out[parts[0]] = (parts[1], parts[2])
    return out


def verify():
    failures = []

    # 1. sample reproducible from the seed
    sampled, _ = build_sample()
    regen = sorted({p for v in sampled.values() for p in v})
    on_disk = [l.rstrip("\n") for l in open(SAMPLE_TXT, encoding="utf-8") if l.strip()]
    check1 = (regen == on_disk)
    print("check 1 sample reproducible from seed:", "PASS" if check1 else "FAIL",
          "(%d paths)" % len(regen))
    if not check1:
        failures.append("sample list does not reproduce from seed")

    # 2. medians re-derived by a second route from the CSV
    rows = list(csv.DictReader(open(SAMPLES_CSV, newline="", encoding="utf-8")))
    by = json.load(open(BY_STRATUM, encoding="utf-8"))
    diffs = 0
    for key in STRATUM_KEYS:
        rec = by[key]
        vals = sorted(float(r["rim_px"]) for r in rows
                      if r["stratum"] == key and r["method_flags"] == "ok")
        if not vals:
            continue
        med = statistics.median(vals)          # second route: no numpy
        mean = statistics.fmean(vals)
        # the JSON stores these rounded to 0.1 px, so allow half a step
        if abs(med - rec["rim_px"]["p50"]) > 0.06:
            diffs += 1
        if abs(mean - rec["rim_px"]["mean"]) > 0.06:
            diffs += 1
    print("check 2 medians/means re-derived, mismatches:", diffs,
          "PASS" if diffs == 0 else "FAIL")
    if diffs:
        failures.append("median/mean mismatch between CSV and JSON")

    # 3. independently re-read a sample of the pictures from the VM
    picks = []
    for key in STRATUM_KEYS:
        ok = [r["path"] for r in rows
              if r["stratum"] == key and r["method_flags"] == "ok"]
        if not ok:
            continue
        for i in sorted({0, len(ok) // 2, len(ok) - 1}):
            picks.append((key, ok[i]))
    got = ssh_remeasure([p for _, p in picks])
    bad = 0
    worst_rim = worst_cav = 0.0
    for key, p in picks:
        if p not in got or got[p][0] == "ERR":
            bad += 1
            continue
        rd, cd = float(got[p][0]), float(got[p][1])
        rec = by[key]
        # recorded rim is the per-image dip value; the CSV carries it per row
        row = next(r for r in rows if r["path"] == p and r["stratum"] == key)
        rim_csv = float(row["rim_px"])
        cav_csv = float(row["cavity_px"])
        dr = abs(rd - rim_csv)
        dc = abs(cd - cav_csv)
        worst_rim = max(worst_rim, dr)
        worst_cav = max(worst_cav, dc)
        if dr > 8.0 or dc > 4.0:
            bad += 1
    print("check 3 independent re-read: %d pictures, disagreements: %d, "
          "worst rim delta %.1f px, worst cavity delta %.1f px, %s"
          % (len(picks), bad, worst_rim, worst_cav, "PASS" if bad == 0 else "FAIL"))
    if bad:
        failures.append("%d re-read disagreements" % bad)

    if failures:
        print("VERIFY FAILED:", "; ".join(failures))
        return 1
    print("VERIFY PASSED")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-sample", action="store_true")
    ap.add_argument("--aggregate", metavar="RIM_RAW_TSV")
    args = ap.parse_args()
    if args.build_sample:
        sampled, sizes = build_sample()
        paths = write_sample_txt(sampled)
        print("sample written: %d unique paths" % len(paths))
        for g in GROUPS:
            for ln in LINES:
                print("  %-8s %-5s universe %5d sampled %3d capped %s"
                      % (g, ln, sizes[(g, ln)], len(sampled[(g, ln)]),
                         sizes[(g, ln)] < TARGET_N))
        return 0
    if args.aggregate:
        out = aggregate(load_raw(args.aggregate))
        print("aggregated %d strata" % len(out))
        return 0
    return verify()


if __name__ == "__main__":
    sys.exit(main())
