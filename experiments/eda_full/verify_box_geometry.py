#!/usr/bin/env python3
"""Ticket 012 verifier.

Proves the box-geometry deliverables four ways, and prints a check count and a
failure count. Zero failures is required.

  1. Integrity: every box in resolved_labels.csv appears exactly once in
     box_sizes.csv, tags are excluded and counted, and each row's diagonal and
     micron columns recompute from its own coordinates.
  2. Second route: the headline medians (and p25/p75) are re-derived from
     box_sizes.csv with statistics.median and statistics.quantiles(inclusive)
     rather than the interpolating percentile the builder used, and diffed
     against size_by_stratum.json.
  3. Cavity: the per-image cavity containment shares are re-derived from
     box_sizes.csv and cavity_geometry_library.json by a second route.
  4. VM re-read: a fixed sample of pictures is re-measured on the shared VM with
     an independently written cavity routine and compared to the recorded one.

Run:  ./.venv/Scripts/python.exe experiments/eda_full/verify_box_geometry.py
Stdlib only in this file.
"""
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
RESOLVED = os.path.join(RUN, "resolved_labels.csv")
PICTURE_TABLE = os.path.join(RUN, "picture_table.csv")
BOX_SIZES = os.path.join(RUN, "box_sizes.csv")
CAVITY_JSON = os.path.join(RUN, "cavity_geometry_library.json")
BY_STRATUM = os.path.join(RUN, "size_by_stratum.json")

SCALE_OURS = 18.1165
SCALE_LEAD = 18.25
LENS_DIAMETER_PX = 783.8

SSH = "C:/Windows/System32/OpenSSH/ssh.exe"
SSH_ARGS = ["-o", "BatchMode=yes", "amd-a100-vm"]
VM_ROOT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"

# Independently written cavity routine for the VM re-read. Same definition as
# vm/ops/measure_cavity_library.py (bright-blob mask, 0.45 * p99.5, half-max
# width rule, /4.0 radius) but written separately, so an accidental change to
# one does not hide in the other.
REMOTE = r'''
import base64, os, sys
import numpy as np
from PIL import Image
root = sys.argv[sys.argv.index("--root")+1]
def cav(p):
    a = np.asarray(Image.open(p), dtype=np.float64)
    top = float(np.percentile(a, 99.5))
    if top < 20.0:
        return ("low_bright", "", "", "")
    m = a > (0.45 * top)
    idx = np.argwhere(m)
    if idx.shape[0] < 50000:
        return ("no_mask", "", "", "")
    cy = idx[:,0].mean(); cx = idx[:,1].mean()
    widths = m.sum(axis=0); heights = m.sum(axis=1)
    wx = int((widths > 0.5*widths.max()).sum())
    hy = int((heights > 0.5*heights.max()).sum())
    R = (wx + hy) / 4.0
    return ("ok", "%.6f" % cx, "%.6f" % cy, "%.6f" % R)
for line in sys.stdin:
    p = line.strip()
    if not p:
        continue
    full = os.path.join(root, p)
    if not os.path.exists(full):
        flag, cx, cy, rr = "missing", "", "", ""
    else:
        flag, cx, cy, rr = cav(full)
    sys.stdout.write("\t".join([p, cx, cy, rr, flag]) + "\n")
'''

CHECKS = 0
FAILS = 0
DETAIL = []


def check(name, ok, detail=""):
    global CHECKS, FAILS
    CHECKS += 1
    if not ok:
        FAILS += 1
        DETAIL.append("%s: %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))
    return ok


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


def quart(vals):
    """p25,p50,p75 by a second route; a single value is its own percentile."""
    if len(vals) == 1:
        return float(vals[0]), float(vals[0]), float(vals[0])
    return statistics.quantiles(vals, n=4, method="inclusive")


def main():
    # ---------------------------------------------------- load everything
    with open(BOX_SIZES, newline="") as fh:
        box_rows = list(csv.DictReader(fh))
    with open(RESOLVED, newline="") as fh:
        src = list(csv.DictReader(fh))
    with open(CAVITY_JSON) as fh:
        cavity = json.load(fh)
    with open(BY_STRATUM) as fh:
        strat = json.load(fh)

    src_boxes = [r for r in src if r["shape_kind"] == "box"]
    src_tags = [r for r in src if r["shape_kind"] != "box"]

    # 1 -------------------------------------------------------- integrity
    check("box_row_count", len(box_rows) == len(src_boxes),
          "%d vs %d" % (len(box_rows), len(src_boxes)))
    check("box_count_is_14182", len(box_rows) == 14182, str(len(box_rows)))
    check("tags_excluded_is_5832", len(src_tags) == 5832, str(len(src_tags)))
    check("tags_excluded_json", strat["counts"]["tags_excluded"] == len(src_tags),
          "%s vs %d" % (strat["counts"]["tags_excluded"], len(src_tags)))

    # every box appears exactly once: compare sorted (md5, canonical, source,
    # rounded diag) multisets
    src_key = sorted((r["picture_md5"], r["canonical_id"], r["source_file"],
                      "%.4f" % float(((float(r["xbr"]) - float(r["xtl"])) ** 2
                                      + (float(r["ybr"]) - float(r["ytl"])) ** 2) ** 0.5))
                     for r in src_boxes)
    out_key = sorted((r["picture_md5"], r["canonical_id"], r["source_file"],
                      "%.4f" % float(r["diag_px"])) for r in box_rows)
    check("every_box_exactly_once", src_key == out_key,
          "%d mismatched" % sum(1 for a, b in zip(src_key, out_key) if a != b))
    dup = len(src_boxes) - len(set((r["picture_md5"], r["canonical_id"], r["source_file"],
                                    r["xtl"], r["ytl"], r["xbr"], r["ybr"], r["rotation"])
                                   for r in src_boxes))
    check("no_duplicate_source_boxes", dup == 0, "%d duplicates" % dup)

    # each row's own coordinates recompute its diag and micron columns
    diag_bad = um1_bad = um2_bad = axis_bad = 0
    for r in box_rows:
        d = ((float(r["w_px"]) ** 2 + float(r["h_px"]) ** 2) ** 0.5)
        if not approx(d, float(r["diag_px"]), 1e-3):
            diag_bad += 1
        if not approx(float(r["diag_um_at_18_1165"]), float(r["diag_px"]) * SCALE_OURS, 1e-3):
            um1_bad += 1
        if not approx(float(r["diag_um_at_18_25"]), float(r["diag_px"]) * SCALE_LEAD, 1e-3):
            um2_bad += 1
        rot = r["rotation"].strip()
        want = 1 if (rot == "" or float(rot) == 0.0) else 0
        if int(r["is_axis_aligned"]) != want:
            axis_bad += 1
    check("diag_recomputes", diag_bad == 0, str(diag_bad))
    check("um_18_1165_recomputes", um1_bad == 0, str(um1_bad))
    check("um_18_25_recomputes", um2_bad == 0, str(um2_bad))
    check("axis_flag_recomputes", axis_bad == 0, str(axis_bad))

    # 2 --------------------------------------- second route on the medians
    # by defect
    by_def = {}
    for r in box_rows:
        by_def.setdefault(r["canonical_id"], []).append(float(r["diag_px"]))
    med_fail = 0
    for cid, vals in by_def.items():
        blk = strat["by_defect"][cid]
        p25, p50, p75 = quart(vals)
        if not (approx(p50, blk["diag_px_p50"], 1e-3)
                and approx(p25, blk["diag_px_p25"], 1e-3)
                and approx(p75, blk["diag_px_p75"], 1e-3)
                and approx(statistics.median(vals), blk["diag_px_p50"], 1e-3)):
            med_fail += 1
    check("defect_medians_second_route", med_fail == 0, str(med_fail))
    check("defect_count", len(by_def) == len(strat["by_defect"]),
          "%d vs %d" % (len(by_def), len(strat["by_defect"])))

    # by folder group
    by_grp = {}
    for r in box_rows:
        by_grp.setdefault(r["folder_group"], []).append(float(r["diag_px"]))
    grp_fail = 0
    for g, vals in by_grp.items():
        blk = strat["by_folder_group"][g]
        p25, p50, p75 = quart(vals)
        if not (approx(p50, blk["diag_px_p50"], 1e-3) and approx(p25, blk["diag_px_p25"], 1e-3)
                and approx(p75, blk["diag_px_p75"], 1e-3)):
            grp_fail += 1
    check("group_medians_second_route", grp_fail == 0, str(grp_fail))

    # by line
    by_line = {}
    for r in box_rows:
        by_line.setdefault(r["line"], []).append(float(r["diag_px"]))
    line_fail = 0
    for ln, vals in by_line.items():
        blk = strat["by_line"][ln]
        p25, p50, p75 = quart(vals)
        if not (approx(p50, blk["diag_px_p50"], 1e-3) and approx(p25, blk["diag_px_p25"], 1e-3)
                and approx(p75, blk["diag_px_p75"], 1e-3)):
            line_fail += 1
    check("line_medians_second_route", line_fail == 0, str(line_fail))

    # triples
    by_tri = {}
    for r in box_rows:
        by_tri.setdefault((r["canonical_id"], r["folder_group"], r["line"]), []).append(
            float(r["diag_px"]))
    tri_fail = 0
    tri_doc = {(t["canonical_id"], t["folder_group"], t["line"]): t
               for t in strat["by_defect_folder_group_line"]}
    check("triple_count", len(by_tri) == len(tri_doc),
          "%d vs %d" % (len(by_tri), len(tri_doc)))
    for k, vals in by_tri.items():
        blk = tri_doc.get(k)
        if blk is None or blk["n"] != len(vals):
            tri_fail += 1
            continue
        p25, p50, p75 = quart(vals)
        if not (approx(p50, blk["diag_px_p50"], 1e-3) and approx(p25, blk["diag_px_p25"], 1e-3)
                and approx(p75, blk["diag_px_p75"], 1e-3)):
            tri_fail += 1
    check("triple_medians_second_route", tri_fail == 0, str(tri_fail))

    # micron columns of the per-stratum doc follow the px column at each scale
    um_fail = 0
    for cid, blk in strat["by_defect"].items():
        for name in ("p25", "p50", "p75"):
            if not approx(blk["diag_um_at_18_1165_" + name], blk["diag_px_" + name] * SCALE_OURS, 1e-2):
                um_fail += 1
            if not approx(blk["diag_um_at_18_25_" + name], blk["diag_px_" + name] * SCALE_LEAD, 1e-2):
                um_fail += 1
    check("stratum_um_columns", um_fail == 0, str(um_fail))

    # 3 ---------------------------------------------------------- axis share
    n_axis = sum(int(r["is_axis_aligned"]) for r in box_rows)
    check("axis_share_matches_json",
          n_axis == strat["axis_aligned"]["n_axis_aligned"],
          "%d vs %d" % (n_axis, strat["axis_aligned"]["n_axis_aligned"]))
    check("axis_share_value",
          approx(strat["axis_aligned"]["share_axis_aligned"], n_axis / len(box_rows), 1e-6))
    check("axis_no_explicit_zero",
          all(r["rotation"].strip() == "" for r in box_rows if int(r["is_axis_aligned"]) == 1))

    # 4 ------------------------------------------------ cavity second route
    per_pic = cavity["per_picture"]
    check("cavity_pictures_is_census", cavity["summary"]["pictures"] == len(per_pic),
          "%d vs %d" % (cavity["summary"]["pictures"], len(per_pic)))
    n_meas = sum(1 for c in per_pic.values() if c["measured"])
    check("cavity_measured_count", n_meas == cavity["summary"]["pictures_measured"])
    fails = {}
    for c in per_pic.values():
        if not c["measured"]:
            fails[c["flag"]] = fails.get(c["flag"], 0) + 1
    check("cavity_failure_classes_sum",
          sum(fails.values()) == cavity["summary"]["pictures_could_not_measure"])
    check("cavity_no_silent_drop",
          sum(fails.values()) + n_meas == cavity["summary"]["pictures"],
          "%d + %d != %d" % (sum(fails.values()), n_meas, cavity["summary"]["pictures"]))

    # re-derive containment shares. box_sizes.csv carries only w/h, so the
    # box centre is recomputed from the source coordinates (resolved_labels.csv)
    # and joined on (md5, canonical, source, rounded w, rounded h).
    n_o = n_f = n_m = n_u = 0
    src_index = {}
    for r in src_boxes:
        w = abs(float(r["xbr"]) - float(r["xtl"]))
        h = abs(float(r["ybr"]) - float(r["ytl"]))
        src_index.setdefault((r["picture_md5"], r["canonical_id"], r["source_file"],
                              "%.4f" % w, "%.4f" % h), []).append(r)
    n_o = n_f = n_m = n_u = 0
    unmatched = 0
    for r in box_rows:
        key = (r["picture_md5"], r["canonical_id"], r["source_file"],
               "%.4f" % float(r["w_px"]), "%.4f" % float(r["h_px"]))
        cands = src_index.get(key)
        if not cands:
            unmatched += 1
            continue
        s = cands.pop()
        c = per_pic[r["picture_md5"]]
        if not c["measured"]:
            n_u += 1
            continue
        n_m += 1
        cx = (float(s["xtl"]) + float(s["xbr"])) / 2.0
        cy = (float(s["ytl"]) + float(s["ybr"])) / 2.0
        d = ((cx - c["cx"]) ** 2 + (cy - c["cy"]) ** 2) ** 0.5
        if d > c["R_px"]:
            n_o += 1
        if d > c["R_px"] * 1.5:
            n_f += 1
    check("cavity_rows_matched", unmatched == 0, str(unmatched))
    ov = strat["cavity_containment"]["overall"]
    check("cavity_outside_second_route", n_o == ov["n_outside_cavity"],
          "%d vs %d" % (n_o, ov["n_outside_cavity"]))
    check("cavity_beyond_1_5x_second_route", n_f == ov["n_beyond_1_5x_cavity"],
          "%d vs %d" % (n_f, ov["n_beyond_1_5x_cavity"]))
    check("cavity_measured_boxes", n_m == ov["n_boxes_measured"],
          "%d vs %d" % (n_m, ov["n_boxes_measured"]))

    # 5 ------------------------------------------------------ P3_HE caveat
    p3 = strat["p3_he_region_annotation"]
    he = [float(r["diag_px"]) for r in box_rows if r["canonical_id"] in ("hema_obstruction", "hema_fragment")]
    check("p3he_combined_p50_second_route",
          approx(statistics.median(he), p3["combined_diag_px_p50"], 1e-3))
    check("p3he_combined_over_lens",
          p3["combined_diag_px_p50"] > LENS_DIAMETER_PX,
          "%s vs %s" % (p3["combined_diag_px_p50"], LENS_DIAMETER_PX))

    # 6 --------------------------------------------------- VM re-read sample
    vm_checks = vm_fail = 0
    try:
        sample = sample_pictures(per_pic, box_rows, n=12)
        rec = ssh_remeasure(sample)
        for path, (flag, cx, cy, rr) in rec.items():
            md5 = path_to_md5.get(path)
            if md5 is None:
                continue
            c = per_pic[md5]
            vm_checks += 1
            if c["flag"] != flag:
                vm_fail += 1
                continue
            if flag == "ok":
                if not (approx(float(cx), c["cx"], 1e-6)
                        and approx(float(cy), c["cy"], 1e-6)
                        and approx(float(rr), c["R_px"], 1e-6)):
                    vm_fail += 1
        check("vm_reread_agrees", vm_fail == 0 and vm_checks > 0,
              "%d checks, %d fails" % (vm_checks, vm_fail))
    except Exception as exc:
        check("vm_reread_agrees", False, "could not run: %r" % exc)

    # ---------------------------------------------------------------- report
    print("")
    print("checks: %d   failures: %d   vm_reread_checks: %d" % (CHECKS, FAILS, vm_checks))
    if DETAIL:
        print("failures:")
        for d in DETAIL:
            print("  " + d)
    return 1 if FAILS else 0


def sample_pictures(per_pic, box_rows, n=12):
    # deterministic spread across the three folder groups
    with open(PICTURE_TABLE, newline="") as fh:
        table = list(csv.DictReader(fh))
    by_md5 = {r["md5"]: r for r in table}
    pics = sorted({r["picture_md5"] for r in box_rows})
    # balanced across folder groups
    buckets = {}
    for m in pics:
        buckets.setdefault(by_md5[m]["winning_path"].split("/")[0], []).append(m)
    out = []
    keys = sorted(buckets)
    i = 0
    while len(out) < n and any(buckets[k] for k in keys):
        k = keys[i % len(keys)]
        if buckets[k]:
            m = buckets[k].pop(0)
            out.append(by_md5[m]["winning_path"])
        i += 1
    return out


path_to_md5 = {}


def ssh_remeasure(paths):
    blob = base64.b64encode(REMOTE.encode()).decode()
    remote = ("python3 -c \"import base64;exec(base64.b64decode('%s'))\" --root '%s'"
              % (blob, VM_ROOT))
    proc = subprocess.run([SSH] + SSH_ARGS + [remote],
                          input="".join(p + "\n" for p in paths).encode(),
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace"))
    out = {}
    for line in proc.stdout.decode().splitlines():
        parts = line.split("\t")
        if len(parts) == 5:
            out[parts[0]] = (parts[4], parts[1], parts[2], parts[3])
    return out


def _load_path_to_md5():
    global path_to_md5
    with open(PICTURE_TABLE, newline="") as fh:
        for r in csv.DictReader(fh):
            path_to_md5[r["winning_path"]] = r["md5"]


if __name__ == "__main__":
    _load_path_to_md5()
    sys.exit(main())
