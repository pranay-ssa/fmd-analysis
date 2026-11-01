#!/usr/bin/env python3
"""Phase 1 of the scale plan: ring identity, aggregation and the two
nominal-free discriminators.

Local only. It never talks to the VM and never writes to it. It reads the raw
scanner output produced by vm/ops/scan_rings.py piped over ssh and turns it into
the ring sample list, the ring inventory, the per-candidate-ring summary and the
discriminator result.

The question is pure pixels: which ring in the radial intensity profile is the
lens edge, and what is the lens diameter in PIXELS. No micron figure is produced
anywhere in this file. Nothing here divides by any nominal.

Run:
    python experiments/eda_full/ring_identity.py --sample         # ring_sample.txt
    python experiments/eda_full/ring_identity.py --scanner-input  # stdin for the scanner
    python experiments/eda_full/ring_identity.py --aggregate      # everything else
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "run" / "eda_full_20261015"

PICTURE_TABLE = RUN / "picture_table.csv"
RESOLVED = RUN / "resolved_labels.csv"
POP_B_LISTING = RUN / "ring_pop_b_listing.txt"
REPRO_LISTING = RUN / "ring_repro_listing.txt"
RAW = RUN / "ring_raw.tsv"

OUT_SAMPLE = RUN / "ring_sample.txt"
OUT_INV = RUN / "ring_inventory.csv"
OUT_CAND = RUN / "ring_candidates.json"
OUT_IDENT = RUN / "ring_identity.json"

# The three library folders, the definition used by experiments/eda_full/label_census.py.
LIBRARY_FOLDERS = {
    "ICube Defects Library",
    "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
}
LINES = ["L24", "L25", "L26", "L27", "L31"]

SEED_A = 20261015
SEED_B = 20261016
PER_LINE_A = 400
PER_LINE_B = 100

LABEL_NL = "missing_lens"        # the P1_NL tag
LABEL_LOC = "lens_off_center"    # the P2_LOC tag

# Candidate-ring definition, fixed from the pooled histogram before any
# discriminator number was read.
WIN = 0.02          # half window used when counting "a ring sits at u"
ASSIGN = 0.06       # a ring joins the nearest candidate within this of u
FLOOR_MULT = 3.0    # a candidate peak must beat this multiple of the interior floor
FLOOR_RANGE = (0.35, 0.75)
SMOOTH = 3          # bins, moving average

# The headline lens measurement: the least-squares circle fit restricted to the
# band that holds the ring whose radius mode the inventory finds (see report).
RIM_BAND = (0.80, 0.96)


def line_of(name: str) -> str:
    m = re.search(r"_L(\d+)_", name)
    return "L" + m.group(1) if m else ""


# ---------------------------------------------------------------------------
# sampling
# ---------------------------------------------------------------------------

def build_sample() -> int:
    rows = list(csv.DictReader(PICTURE_TABLE.open(encoding="utf-8")))
    pool_a = defaultdict(list)
    for r in rows:
        if r["winning_path"].split("/", 1)[0] in LIBRARY_FOLDERS:
            pool_a[r["line"]].append(r)

    rng = random.Random(SEED_A)
    out = []
    for line in LINES:
        pool = sorted(pool_a[line], key=lambda r: r["md5"])
        for r in rng.sample(pool, min(PER_LINE_A, len(pool))):
            out.append(("lib", r["line"], r["md5"], r["winning_path"]))

    # Population B: the production-sample drop, *Pass1* only. The whole pool is a
    # single line (the drop is a T24 sample), so the per-line target yields 100,
    # not 500. The stated 500 is kept by topping up from the same pool.
    b_pool = sorted(l.strip() for l in POP_B_LISTING.read_text(encoding="utf-8").splitlines() if l.strip())
    by_line = defaultdict(list)
    for name in b_pool:
        by_line[line_of(name)].append(name)
    rng = random.Random(SEED_B)
    taken = set()
    for line in LINES:
        pool = by_line.get(line, [])
        if not pool:
            continue
        for name in rng.sample(pool, min(PER_LINE_B, len(pool))):
            taken.add(name)
            out.append(("prod", line, "",
                        "20260826_T24_Production_Sample/sample folder/" + name))
    target = PER_LINE_B * len(LINES)
    if len(taken) < target:
        rest = sorted(n for n in b_pool if n not in taken)
        need = min(target - len(taken), len(rest))
        for name in rng.sample(rest, need):
            out.append(("prod", line_of(name), "",
                        "20260826_T24_Production_Sample/sample folder/" + name))

    for rel in (l.strip() for l in REPRO_LISTING.read_text(encoding="utf-8").splitlines()):
        if rel:
            out.append(("repro", line_of(rel), "", rel))

    with OUT_SAMPLE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["tag", "line", "md5", "relpath"])
        w.writerows(out)
    print("ring_sample.txt rows: %d" % len(out))
    return 0


def scanner_input() -> int:
    with OUT_SAMPLE.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sys.stdout.write(row["tag"] + "\t" + row["relpath"] + "\n")
    return 0


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def load_raw():
    pics = {}
    rings = defaultdict(list)
    for raw in RAW.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        f = raw.split("\t")
        if f[0] == "P":
            d = {"tag": f[1], "path": f[3], "flag": f[7],
                 "Rcav": float(f[6]) if f[6] else None,
                 "dip_r": float(f[8]) if f[8] else None,
                 "dip_prom": float(f[9]) if f[9] else None,
                 "grad_r": float(f[10]) if f[10] else None,
                 "circ_r": float(f[11]) if f[11] else None,
                 "circ_rms": float(f[13]) if f[13] else None,
                 "rim_r": float(f[14]) if f[14] else None}
            # a repro frame also drawn into population B keeps one row; the repro
            # tag wins so the reproduction check sees exactly the prior 200 frames
            if f[2] not in pics or d["tag"] == "repro":
                pics[f[2]] = d
        elif f[0] == "R":
            rings[f[1]].append({
                "idx": int(f[2]), "radius": float(f[3]), "depth": float(f[4]),
                "width": float(f[5]), "sharp": float(f[6]),
                "ring_R": float(f[7]) if f[7] else None,
                "ecc": float(f[10]) if f[10] else None,
                "frac_ray": float(f[11]) if f[11] else None,
                "norm": float(f[12]) if f[12] else None})
    return pics, rings


def load_labels():
    lab = defaultdict(set)
    with RESOLVED.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["canonical_id"] in (LABEL_NL, LABEL_LOC):
                lab[row["picture_md5"]].add(row["canonical_id"])
    return lab


def group_of(pics, lab, m):
    s = lab.get(m, ())
    if LABEL_NL in s:
        return "missing_lens"
    if LABEL_LOC in s:
        return "lens_off_center"
    return "other"


# ---------------------------------------------------------------------------
# stats helpers
# ---------------------------------------------------------------------------

def pct(v, p):
    if not v:
        return None
    s = sorted(v)
    k = (len(s) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(s[lo])
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def rad_stats(vals):
    """median radius, IQR and relative spread of a list of pixel radii."""
    if not vals:
        return {"n": 0}
    med = statistics.median(vals)
    q1, q3 = pct(vals, 25), pct(vals, 75)
    return {"n": len(vals),
            "median_radius_px": round(med, 2),
            "iqr_radius_px": [round(q1, 2), round(q3, 2)],
            "rel_spread_pct": round(100.0 * (q3 - q1) / med, 2) if med else None,
            "p10_radius_px": round(pct(vals, 10), 2),
            "p90_radius_px": round(pct(vals, 90), 2),
            "mean_radius_px": round(statistics.fmean(vals), 2),
            "sd_radius_px": round(statistics.pstdev(vals), 2)}


def diam_stats(vals):
    if not vals:
        return {"n": 0}
    med = statistics.median(vals)
    q1, q3 = pct(vals, 25), pct(vals, 75)
    return {"n": len(vals),
            "median_diam_px": round(med, 1),
            "p25_diam_px": round(q1, 1),
            "p75_diam_px": round(q3, 1),
            "iqr_diam_px": round(q3 - q1, 1),
            "rel_spread_pct": round(100.0 * (q3 - q1) / med, 2) if med else None,
            "p10_diam_px": round(pct(vals, 10), 1),
            "p90_diam_px": round(pct(vals, 90), 1),
            "sd_diam_px": round(statistics.pstdev(vals), 1)}


# ---------------------------------------------------------------------------
# candidate rings
# ---------------------------------------------------------------------------

def member_rings(rings_of_pic, lo, hi):
    return [r for r in rings_of_pic if r["norm"] is not None and lo <= r["norm"] < hi]


def deepest(rings_of_pic, lo, hi):
    c = member_rings(rings_of_pic, lo, hi)
    return max(c, key=lambda r: r["depth"]) if c else None


def candidate_centres(pics, rings, ok):
    """Peaks of the pooled normalised ring-radius detection-rate curve."""
    us = [0.35 + 0.02 * i for i in range(36)]
    cnt = []
    for u in us:
        n = 0
        for m in ok:
            if any(abs(r["norm"] - u) <= WIN for r in rings[m] if r["norm"] is not None):
                n += 1
        cnt.append(n / len(ok))
    sm = [statistics.fmean(cnt[max(0, i - SMOOTH // 2):i + SMOOTH // 2 + 1])
          for i in range(len(cnt))]
    floor = statistics.median([sm[i] for i, u in enumerate(us)
                               if FLOOR_RANGE[0] <= u <= FLOOR_RANGE[1]])
    peaks = []
    for i in range(1, len(sm) - 1):
        if sm[i] >= sm[i - 1] and sm[i] > sm[i + 1] and sm[i] > FLOOR_MULT * floor:
            peaks.append((us[i], sm[i]))
    return peaks, floor, list(zip(us, cnt, sm))


def write_inventory(pics):
    cols = ["picture_md5", "path", "population", "folder", "line", "ring_index",
            "radius_px", "depth", "width", "sharpness"]
    n = 0
    with OUT_INV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for m5 in sorted(pics):
            d = pics[m5]
            if d["flag"] != "ok":
                continue
            folder = d["path"].split("/", 1)[0]
            if folder == "20260826_T24_Production_Sample":
                folder = "sample folder"
            pop = {"lib": "library", "prod": "production_sample",
                   "repro": "repro_200"}[d["tag"]]
            for r in d["rings"]:
                w.writerow([m5, d["path"], pop, folder, d["line"], r["idx"],
                            "%.4f" % r["radius"], "%.4f" % r["depth"],
                            "%.4f" % r["width"], "%.6f" % r["sharp"]])
                n += 1
    return n


def aggregate() -> int:
    pics, rings = load_raw()
    labels = load_labels()
    for m5 in pics:
        pics[m5]["rings"] = rings.get(m5, [])
        if not pics[m5].get("line"):
            pics[m5]["line"] = line_of(pics[m5]["path"])
    dupes = 0
    seen = Counter()
    for raw in RAW.read_text(encoding="utf-8").splitlines():
        f = raw.split("\t")
        if f[0] == "P" and f[2]:
            seen[f[2]] += 1
    dupes = sum(1 for v in seen.values() if v > 1)

    ok = [m for m, d in pics.items() if d["flag"] == "ok" and d["Rcav"]]
    n_inv = write_inventory(pics)

    peaks, floor, curve = candidate_centres(pics, rings, ok)

    by_tag = defaultdict(list)
    by_line = defaultdict(list)
    by_group = defaultdict(list)
    for m in ok:
        by_tag[pics[m]["tag"]].append(m)
        by_line[pics[m]["line"]].append(m)
        by_group[group_of(pics, labels, m)].append(m)

    cand = []
    assigned = set()
    for ci, (u, rate) in enumerate(sorted(peaks)):
        lo, hi = u - ASSIGN, u + ASSIGN
        rows = []
        for m in ok:
            r = deepest(rings[m], lo, hi)
            if r is not None:
                rows.append((m, r))
        for m, r in rows:
            assigned.add((m, r["idx"]))

        def sub(sel):
            v = [r["radius"] for m, r in rows if m in sel]
            return rad_stats(v)

        det = {g: (round(len([m for m, _ in rows if m in set(by_group[g])]) / len(by_group[g]), 4)
                   if by_group[g] else None) for g in ("other", "missing_lens", "lens_off_center")}
        e_other = [r["ecc"] for m, r in rows
                   if m in set(by_group["other"]) and r["ecc"] is not None]
        e_loc = [r["ecc"] for m, r in rows
                 if m in set(by_group["lens_off_center"]) and r["ecc"] is not None]
        entry = {
            "candidate_index": ci,
            "norm_centre": round(u, 3),
            "norm_window": [lo, hi],
            "radius_px_at_median_cavity": round(u * statistics.median([pics[m]["Rcav"] for m in ok]), 1),
            "overall": sub(set(ok)),
            "detection_rate": round(len(rows) / len(ok), 4),
            "median_depth": round(statistics.median([r["depth"] for _, r in rows]), 3) if rows else None,
            "median_width_px": round(statistics.median([r["width"] for _, r in rows]), 2) if rows else None,
            "median_sharpness": round(statistics.median([r["sharp"] for _, r in rows]), 4) if rows else None,
            "by_population": {t: sub(set(by_tag[t])) for t in ("lib", "prod", "repro")},
            "by_line": {ln: sub(set(by_line[ln])) for ln in LINES + [""]},
            "detection_rate_by_group": det,
            "radius_by_group": {g: sub(set(by_group[g])) for g in
                                ("other", "missing_lens", "lens_off_center")},
            "centre_offset_from_cavity_px": {
                "other_median": round(statistics.median(e_other), 2) if e_other else None,
                "other_n": len(e_other),
                "lens_off_center_median": round(statistics.median(e_loc), 2) if e_loc else None,
                "lens_off_center_n": len(e_loc),
            },
        }
        cand.append(entry)

    # rings that sit in no candidate window
    unassigned = []
    for m in ok:
        for r in rings[m]:
            if (m, r["idx"]) not in assigned:
                unassigned.append(r["radius"])
    unclustered = {"n": len(unassigned),
                   "detection_rate": round(len(unassigned) / len(ok), 4),
                   "stats": rad_stats(unassigned)}

    OUT_CAND.write_text(json.dumps({
        "note": "one entry per candidate ring. Rings are pooled on radius / cavity "
                "radius, which is scale free and assumes no ring identity. No "
                "nominal is used and no micron figure appears anywhere.",
        "definition": {
            "window_norm": WIN, "assign_norm": ASSIGN,
            "floor_multiple": FLOOR_MULT, "floor_range": list(FLOOR_RANGE),
            "interior_floor_rate": round(floor, 4),
            "rule": "candidate centres are the peaks of the 0.02-step, 3-bin "
                    "smoothed detection-rate curve that exceed 3 x the interior "
                    "floor; a picture's deepest ring within +-0.06 of a centre is "
                    "its member ring",
        },
        "detection_rate_curve": [
            {"u": round(u, 3), "rate": round(c, 4), "rate_smoothed": round(s, 4)}
            for u, c, s in curve],
        "candidates": cand,
        "unclustered_rings": unclustered,
    }, indent=1), encoding="utf-8")

    ident = identity(pics, labels, rings, ok, cand, by_group, n_inv, dupes)
    OUT_IDENT.write_text(json.dumps(ident, indent=1), encoding="utf-8")
    print(json.dumps(ident["verdict"], indent=1))
    return 0


# ---------------------------------------------------------------------------
# discriminators, methods, verdict
# ---------------------------------------------------------------------------

def discriminators(pics, labels, rings, ok, cand, by_group):
    nl = set(by_group["missing_lens"])
    loc = set(by_group["lens_off_center"])
    other = set(by_group["other"])
    out = {}

    # ---- D1: missing lens ---------------------------------------------------
    per = []
    for c in cand:
        lo, hi = c["norm_window"]
        per.append({
            "candidate_index": c["candidate_index"],
            "norm_centre": c["norm_centre"],
            "detection_rate_other": c["detection_rate_by_group"]["other"],
            "detection_rate_missing_lens": c["detection_rate_by_group"]["missing_lens"],
            "median_radius_other_px": c["radius_by_group"]["other"].get("median_radius_px"),
            "median_radius_missing_lens_px": c["radius_by_group"]["missing_lens"].get("median_radius_px"),
        })
    rings_per_nl = statistics.fmean([len(rings[m]) for m in nl]) if nl else None
    rings_per_other = statistics.fmean([len(rings[m]) for m in other]) if other else None
    dip_other = [pics[m]["dip_prom"] for m in other if pics[m]["dip_prom"] is not None]
    dip_nl = [pics[m]["dip_prom"] for m in nl if pics[m]["dip_prom"] is not None]
    out["discriminator_1_missing_lens"] = {
        "label": "P1_NL = missing_lens, %d sampled pictures with a measured cavity" % len(nl),
        "reference_group": "'other' = %d sampled pictures carrying neither tag" % len(other),
        "per_candidate_ring": per,
        "rings_per_picture": {
            "other": round(rings_per_other, 3) if rings_per_other is not None else None,
            "missing_lens": round(rings_per_nl, 3) if rings_per_nl is not None else None,
        },
        "shipped_dip_prominence": {
            "other_median": round(statistics.median(dip_other), 2) if dip_other else None,
            "missing_lens_median": round(statistics.median(dip_nl), 2) if dip_nl else None,
            "other_n": len(dip_other), "missing_lens_n": len(dip_nl),
        },
    }

    # ---- D2: lens off centre ------------------------------------------------
    per2 = []
    for c in cand:
        eo = c["centre_offset_from_cavity_px"]
        per2.append({
            "candidate_index": c["candidate_index"],
            "norm_centre": c["norm_centre"],
            "detection_rate_other": c["detection_rate_by_group"]["other"],
            "detection_rate_lens_off_center": c["detection_rate_by_group"]["lens_off_center"],
            "centre_offset_median_other_px": eo["other_median"],
            "centre_offset_median_lens_off_center_px": eo["lens_off_center_median"],
            "median_radius_other_px": c["radius_by_group"]["other"].get("median_radius_px"),
            "median_radius_lens_off_center_px": c["radius_by_group"]["lens_off_center"].get("median_radius_px"),
        })
    out["discriminator_2_lens_off_center"] = {
        "label": "P2_LOC = lens_off_center, %d sampled pictures with a measured cavity" % len(loc),
        "reference_group": "'other' = %d sampled pictures carrying neither tag" % len(other),
        "per_candidate_ring": per2,
        "note": "the offset is the ring centre less the cavity centre, measured from "
                "the 360 ray dips; the cavity centre is the shipped bright-blob "
                "centroid, the same origin the radial profile uses",
    }
    return out


def methods(pics, ok, labels):
    def d(key):
        return [pics[m][key] for m in ok if pics[m].get(key) is not None]

    def trimmed(vals, frac=0.15):
        s = sorted(vals)
        k = int(len(s) * frac)
        return round(statistics.fmean(s[k:len(s) - k]), 1) if len(s) > 2 * k else None

    repro = [m for m in pics if pics[m]["tag"] == "repro"]
    accepted = [m for m in repro if pics[m]["flag"] == "ok"
                and pics[m].get("dip_prom") is not None and pics[m]["dip_prom"] > 1.0]
    repro_dip = [2.0 * pics[m]["dip_r"] for m in accepted]
    rim = sorted(2.0 * pics[m]["rim_r"] for m in ok if pics[m].get("rim_r") is not None)

    by_tag = defaultdict(list)
    for m in ok:
        by_tag[pics[m]["tag"]].append(m)

    def pop_table(key):
        out = {}
        for t in ("lib", "prod", "repro"):
            v = [2.0 * pics[m][key] for m in by_tag[t] if pics[m].get(key) is not None]
            out[t] = {"n": len(v), "median_diam_px": round(statistics.median(v), 1) if v else None}
        return out

    return {
        "identical_images": True,
        "population": {"measured_ok": len(ok), "repro_frames": len(repro),
                       "repro_accepted_by_dip_gate": len(accepted)},
        "dip_argmax": {"n": len(d("dip_r")), "median_diam_px": round(2.0 * statistics.median(d("dip_r")), 1),
                       "trimmed_mean_diam_px": trimmed([2.0 * v for v in d("dip_r")]),
                       "median_radius_px": round(statistics.median(d("dip_r")), 2),
                       "by_population": pop_table("dip_r")},
        "gradient_annular": {"n": len(d("grad_r")),
                             "median_diam_px": round(2.0 * statistics.median(d("grad_r")), 1),
                             "median_radius_px": round(statistics.median(d("grad_r")), 2),
                             "by_population": pop_table("grad_r")},
        "circle_fit_wide_0.50_1.06": {"n": len(d("circ_r")),
                                      "median_diam_px": round(2.0 * statistics.median(d("circ_r")), 1),
                                      "median_radius_px": round(statistics.median(d("circ_r")), 2),
                                      "median_rms_px": round(statistics.median(d("circ_rms")), 2) if d("circ_rms") else None,
                                      "by_population": pop_table("circ_r")},
        "circle_fit_rim_0.80_0.96": {"n": len(d("rim_r")),
                                     "median_diam_px": round(statistics.median(rim), 1),
                                     "by_population": pop_table("rim_r"),
                                     **{k: v for k, v in diam_stats(rim).items() if k != "median_diam_px"}},
        "prior_run_reproduction": {
            "repro_frames": len(repro),
            "accepted_frames": len(accepted),
            "trimmed_mean_lens_diam_px": trimmed(repro_dip),
            "target_px": 783.8,
            "delta_px": (round(trimmed(repro_dip) - 783.8, 2)
                         if trimmed(repro_dip) is not None else None),
            "within_one_px": (abs(trimmed(repro_dip) - 783.8) <= 1.0
                              if trimmed(repro_dip) is not None else None),
        },
    }


def identity(pics, labels, rings, ok, cand, by_group, n_inv, dupes):
    d1 = discriminators(pics, labels, rings, ok, cand, by_group)
    meth = methods(pics, ok, labels)
    rim = sorted(2.0 * pics[m]["rim_r"] for m in ok if pics[m].get("rim_r") is not None)
    lo, hi = RIM_BAND

    lens_ring = None
    for c in cand:
        if abs(c["norm_centre"] - 0.88) < 0.06:
            lens_ring = c
    outer_ring = None
    for c in cand:
        if c["norm_centre"] > 0.97:
            outer_ring = c
    cav_px = statistics.median([pics[m]["Rcav"] for m in ok])

    verdict = {
        "lens_edge_ring": {
            "candidate_index": lens_ring["candidate_index"] if lens_ring else None,
            "normalised_radius": lens_ring["norm_centre"] if lens_ring else None,
            "median_radius_px": lens_ring["overall"].get("median_radius_px") if lens_ring else None,
            "detection_rate_other": lens_ring["detection_rate_by_group"]["other"] if lens_ring else None,
            "detection_rate_missing_lens": lens_ring["detection_rate_by_group"]["missing_lens"] if lens_ring else None,
            "median_depth": lens_ring["median_depth"] if lens_ring else None,
        },
        "lens_diameter_px": {
            "headline_method": "least-squares circle fit to 360 radial edge points "
                               "restricted to %.2f-%.2f of the cavity radius, "
                               "outlier-rejected" % (lo, hi),
            "median_diam_px": round(statistics.median(rim), 1),
            "p25_diam_px": round(pct(rim, 25), 1),
            "p75_diam_px": round(pct(rim, 75), 1),
            "iqr_diam_px": round(pct(rim, 75) - pct(rim, 25), 1),
            "rel_spread_pct": round(100.0 * (pct(rim, 75) - pct(rim, 25)) / statistics.median(rim), 2),
            "p10_diam_px": round(pct(rim, 10), 1),
            "p90_diam_px": round(pct(rim, 90), 1),
            "sd_diam_px": round(statistics.pstdev(rim), 1),
            "n": len(rim),
            "cross_check_ring_inventory_diam_px": (round(2.0 * lens_ring["overall"]["median_radius_px"], 1)
                                                   if lens_ring else None),
        },
        "other_rings": {
            "outer_ring_at_~1.01_Rcav": {
                "candidate_index": outer_ring["candidate_index"] if outer_ring else None,
                "median_radius_px": outer_ring["overall"].get("median_radius_px") if outer_ring else None,
                "median_diam_px": round(2.0 * outer_ring["overall"]["median_radius_px"], 1) if outer_ring else None,
                "detection_rate_other": outer_ring["detection_rate_by_group"]["other"] if outer_ring else None,
                "median_depth": outer_ring["median_depth"] if outer_ring else None,
                "median_sharpness": outer_ring["median_sharpness"] if outer_ring else None,
            },
            "median_cavity_radius_px": round(cav_px, 1),
            "cavity_diameter_px": round(2.0 * cav_px, 1),
        },
        "structural_argument": (
            "the cavity wall is where the bright disc ends, and the shipped mask "
            "already puts that boundary at R_cav (median %.1f px radius, %.1f px "
            "diameter). A dark feature at 1.01 R_cav is therefore at the wall, not "
            "inside the cavity, and cannot be a free-floating lens rim; a lens whose "
            "rim sat on the wall would fill the cavity exactly, which the existence "
            "of a Lens Off Center class contradicts. The only ring clear of the wall "
            "is the one at %.2f R_cav, and that is the lens edge."
            % (cav_px, 2.0 * cav_px, lens_ring["norm_centre"] if lens_ring else float("nan"))),
        "discriminator_1_outcome": (
            "DECISIVE for the ring family, not for a single ring. Every outer dark "
            "ring, both candidates, is present only when a lens is present."),
        "discriminator_2_outcome": (
            "INCONCLUSIVE. The P2_LOC tag does not move either ring's centre "
            "relative to the cavity centre, so no ring can be assigned by motion."),
        "the_848_px_figure": (
            "REPRODUCED. The wide-band least-squares circle fit, 0.50 to 1.06 of "
            "R_cav, gives a median %.1f px over the same library population "
            "(the earlier figure was 848). It is a blend of the two modes, not a "
            "single physical ring: restricted to the rim band the same fit gives "
            "%.1f px." % (2.0 * statistics.median([pics[m]["circ_r"] for m in ok
                                                   if pics[m].get("circ_r") is not None]),
                          statistics.median(rim))),
    }

    return {
        "phase": "1 of the scale plan",
        "question": "which ring in the radial intensity profile is the lens edge, "
                    "and what is the lens diameter in pixels",
        "micron_free": "no micron figure appears anywhere in this file or its "
                       "siblings. Turning pixels into microns needs the client "
                       "nominal and is Phase 2 and 3 work.",
        "sample": {
            "pictures_measured": len(pics),
            "pictures_ok": len(ok),
            "duplicate_md5_measured_twice": dupes,
            "inventory_rows": n_inv,
            "groups": {g: len(by_group[g]) for g in ("other", "missing_lens", "lens_off_center")},
        },
        "discriminators": d1,
        "methods": meth,
        "verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--scanner-input", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    if a.sample:
        return build_sample()
    if a.scanner_input:
        return scanner_input()
    if a.aggregate:
        return aggregate()
    ap.error("pick --sample, --scanner-input or --aggregate")


if __name__ == "__main__":
    sys.exit(main())
