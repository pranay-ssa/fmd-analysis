#!/usr/bin/env python3
"""Ticket 014 the 300 micron gate: verifier.

Re-derives the headline numbers by a SECOND route, independent of the builder.
The builder reads the box geometry from run/eda_full_20261015/box_sizes.csv and
the gate tags from the production XML. This verifier ignores box_sizes.csv and
reads the box geometry straight from the production XML files itself, so a bug
in box_sizes.csv cannot hide the result. It also re-reads the 2026-10-13 files
from the local read-only copy for the delta.

Every check prints ok or FAIL. Exit is non-zero on any failure. Zero failures
required.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/verify_micron_gate.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
RUN = os.path.join(REPO, "run", "eda_full_20261015")

GATE_ANALYSIS = os.path.join(RUN, "gate_analysis.csv")
GATE_DELTA = os.path.join(RUN, "gate_delta.csv")
SCALE_JSON = os.path.join(RUN, "gate_scale_estimate.json")

OLD_PROD_DIR = os.path.join(
    os.environ.get("OLD_PROD_DIR",
                   "C:/Users/Abcom/AppData/Local/hermes/cache/scratch/old_prod"))

SCALE_OURS = 18.1165
SCALE_LEAD = 18.25
PRODUCTION_FILES = [f"annotations_45219{n}.xml" for n in range(40, 47)]

CHECK_COUNT = 0
FAIL_COUNT = 0


def check(name, ok, note=""):
    global CHECK_COUNT, FAIL_COUNT
    CHECK_COUNT += 1
    if not ok:
        FAIL_COUNT += 1
    print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")


def basename(name):
    return name.rsplit("/", 1)[-1]


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def q123(vals):
    """p25/p50/p75 via statistics.quantiles inclusive, a different route."""
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None, None, None
    if n == 1:
        return float(s[0]), float(s[0]), float(s[0])
    q = statistics.quantiles(s, n=4, method="inclusive")
    return q[0], q[1], q[2]


def main():
    with open(SCALE_JSON, encoding="utf-8") as fh:
        scale = json.load(fh)

    # basename -> md5, from the manifest (same key the builder uses).
    by = {}
    with open(os.path.join(RUN, "file_manifest.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            by[basename(r["path"])] = r["md5"]

    # ---- independent box geometry straight from the XML ---------------------
    # current (2026-10-15) production boxes and tags, keyed by md5.
    cur_tags = defaultdict(Counter)
    cur_side = defaultdict(float)   # (md5, code) -> largest max(w,h)
    cur_diag = defaultdict(float)   # (md5, code) -> largest diagonal
    for fn in PRODUCTION_FILES:
        root = ET.parse(os.path.join(DATA, fn)).getroot()  # trusted export
        for img in root.findall("image"):
            m = by.get(basename(img.get("name")))
            if not m:
                continue
            for t in img.findall("tag"):
                cur_tags[m][t.get("label")] += 1
            for b in img.findall("box"):
                code = b.get("label")
                w = abs(float(b.get("xbr")) - float(b.get("xtl")))
                h = abs(float(b.get("ybr")) - float(b.get("ytl")))
                key = (m, code)
                if max(w, h) > cur_side[key]:
                    cur_side[key] = max(w, h)
                if math.sqrt(w * w + h * h) > cur_diag[key]:
                    cur_diag[key] = math.sqrt(w * w + h * h)

    GATE = {"P3_FM": "P3_FM_MICRON_THRESHOLD", "P3_FIB": "P3_FIB_MICRON_THRESHOLD",
            "P3_EP": "P3_EP_MICRON_THRESHOLD", "P3_HE": "P3_HE_MICRON_THRESHOLD"}

    # recomputed boundaries and distributions, production scope, side + diag
    recomp = {}
    for base, gate in GATE.items():
        flagged_side, unflagged_side = [], []
        flagged_diag, unflagged_diag = [], []
        for (m, code), v in cur_side.items():
            if code != base:
                continue
            g = gate in cur_tags.get(m, Counter())
            (flagged_side if g else unflagged_side).append(v)
            (flagged_diag if g else unflagged_diag).append(cur_diag[(m, code)])
        recomp[base] = {
            "side": (unflagged_side, flagged_side),
            "diag": (unflagged_diag, flagged_diag),
        }

    # ---- check 1: the two proxies, side separates, diag does not -----------
    print("proxy comparison (production scope, new 300 cut):")
    for base in GATE:
        fu, fl = recomp[base]["side"]
        misclass_side = (sum(1 for x in fl if fu and x < max(fu))
                         + sum(1 for x in fu if fl and x >= min(fl))) if (fu and fl) else None
        du, dl = recomp[base]["diag"]
        misclass_diag = (sum(1 for x in dl if du and x < max(du))
                         + sum(1 for x in du if dl and x >= min(dl))) if (du and dl) else None
        if fu and fl:
            print(f"  {base}: side misclass={misclass_side} (unflag_max={max(fu):.3f}, "
                  f"flag_min={min(fl):.3f}); diag misclass={misclass_diag}")
    fm_u, fm_f = recomp["P3_FM"]["side"]
    fm_du, fm_df = recomp["P3_FM"]["diag"]
    check("side_proxy_zero_misclassification_fm",
          sum(1 for x in fm_f if x < max(fm_u)) == 0
          and sum(1 for x in fm_u if x >= min(fm_f)) == 0,
          f"max(unflag)={max(fm_u):.3f} < min(flag)={min(fm_f):.3f}")
    check("diag_proxy_has_misclassification_fm",
          sum(1 for x in fm_df if x < max(fm_du)) > 0,
          f"{sum(1 for x in fm_df if x < max(fm_du))} flagged below max(unflagged diag)")

    # ---- check 2: the boundaries match the JSON -----------------------------
    for base in ("P3_FM", "P3_FIB"):
        fu, fl = recomp[base]["side"]
        jb = scale["scale_estimate"]["new_boundaries_px"][base]
        check(f"boundary_matches_json__{base}",
              abs(max(fu) - jb["lower_px"]) < 1e-6 and abs(min(fl) - jb["upper_px"]) < 1e-6,
              f"({max(fu):.3f}, {min(fl):.3f}] vs json ({jb['lower_px']}, {jb['upper_px']}]")

    # ---- check 3: distributions in the CSV match a second route -------------
    rows = list(csv.DictReader(open(GATE_ANALYSIS, encoding="utf-8")))
    by_key = {(r["base_code"], r["size_proxy"], r["scope"], r["gate_state"]): r
              for r in rows}
    worst = 0.0
    for base in GATE:
        for proxy, idx in (("side", 0), ("diag", 1)):
            fu, fl = recomp[base][proxy]
            for state, arr in (("unflagged", fu), ("flagged", fl)):
                row = by_key[(base, proxy, "production", state)]
                check_n = int(row["n_images"]) == len(arr)
                if arr:
                    a, b, c = q123(arr)
                    dv = max(abs(a - float(row["p25_px"])), abs(b - float(row["p50_px"])),
                             abs(c - float(row["p75_px"])))
                    worst = max(worst, dv)
                else:
                    dv = 0.0
                check(f"dist_matches__{base}__{proxy}__{state}", check_n and dv < 1e-6,
                      f"n={len(arr)} max percentile delta={dv:.2e}")
    check("distribution_second_route_bounded", worst < 1e-6, f"worst delta {worst:.2e}")

    # ---- check 4: both scales present in every micron column ----------------
    hdr = rows[0].keys()
    has_both = ("p50_um_18_1165" in hdr and "p50_um_18_25" in hdr
                and "boundary_mid_um_18_1165" in hdr and "boundary_mid_um_18_25" in hdr)
    check("both_scales_in_every_micron_table", has_both, ",".join(hdr))
    # spot: p50_um_18_25 / p50_um_18_1165 == 18.25/18.1165
    spot = by_key[("P3_FM", "side", "production", "flagged")]
    ratio = float(spot["p50_um_18_25"]) / float(spot["p50_um_18_1165"])
    check("micron_columns_use_the_right_scales",
          abs(ratio - SCALE_LEAD / SCALE_OURS) < 1e-6, f"ratio {ratio:.9f}")

    # ---- check 5: HEMA unconditional ----------------------------------------
    hema_un = by_key[("P3_HE", "side", "production", "unflagged")]
    check("hema_unflagged_group_empty",
          int(hema_un["n_images"]) == 0 and "no unflagged group" in hema_un["note"],
          f"n={hema_un['n_images']} note set")
    hema_fu, hema_fl = recomp["P3_HE"]["side"]
    check("hema_every_picture_flagged", len(hema_fu) == 0 and len(hema_fl) == 94,
          f"unflagged {len(hema_fu)}, flagged {len(hema_fl)}")

    # ---- check 6: the delta, straight from the XML --------------------------
    old_cnt = defaultdict(Counter)
    new_cnt = defaultdict(Counter)
    old_geom = defaultdict(list)
    new_geom = defaultdict(list)
    delta_ok = os.path.isdir(OLD_PROD_DIR)
    if delta_ok:
        for fn in PRODUCTION_FILES:
            old = ET.parse(os.path.join(OLD_PROD_DIR, fn)).getroot()
            new = ET.parse(os.path.join(DATA, fn)).getroot()
            for root, cnt, geom in ((old, old_cnt, old_geom), (new, new_cnt, new_geom)):
                for img in root.findall("image"):
                    m = by.get(basename(img.get("name")))
                    if not m:
                        continue
                    for t in img.findall("tag"):
                        cnt[m][t.get("label")] += 1
                    for b in img.findall("box"):
                        geom[m].append((b.get("label"), b.get("xtl"), b.get("ytl"),
                                        b.get("xbr"), b.get("ybr"), b.get("rotation")))
        changed = [m for m in set(old_cnt) | set(new_cnt) if old_cnt[m] != new_cnt[m]]
        adds = Counter(); dels = Counter()
        for m in changed:
            for k, v in (new_cnt[m] - old_cnt[m]).items():
                adds[k] += v
            for k, v in (old_cnt[m] - new_cnt[m]).items():
                dels[k] += v
        geom_changed = sum(1 for m in set(old_geom) | set(new_geom)
                           if sorted(old_geom[m]) != sorted(new_geom[m]))
        check("delta_changed_pictures", len(changed) == 170, f"{len(changed)}")
        check("delta_added_tags",
              dict(adds) == {"P3_FM_MICRON_THRESHOLD": 118,
                             "P3_FIB_MICRON_THRESHOLD": 51,
                             "P3_EP_MICRON_THRESHOLD": 1}, f"{dict(adds)}")
        check("delta_removed_tags", dict(dels) == {"P1_ML": 1}, f"{dict(dels)}")
        check("delta_geometry_untouched", geom_changed == 0, f"{geom_changed}")
        # CSV row count
        drows = list(csv.DictReader(open(GATE_DELTA, encoding="utf-8")))
        check("delta_csv_rows", len(drows) == 170, f"{len(drows)} rows")
        # added gate bases reconcile to the flagged/unflagged shift
        shift_fm = len(recomp["P3_FM"]["side"][1]) - 53
        check("fm_newly_flagged_matches_delta", shift_fm == 118,
              f"new flagged {len(recomp['P3_FM']['side'][1])} minus old 53 = {shift_fm}")
    else:
        check("delta_available", False, f"OLD_PROD_DIR missing: {OLD_PROD_DIR}")

    # ---- check 7: the inverted scale ----------------------------------------
    nb = scale["scale_estimate"]["new_boundaries_px"]
    lo = max(nb["P3_FM"]["lower_px"], nb["P3_FIB"]["lower_px"])
    hi = min(nb["P3_FM"]["upper_px"], nb["P3_FIB"]["upper_px"])
    slo = 300.0 / hi; shi = 300.0 / lo
    comb = scale["scale_estimate"]["implied_scale_combined"]
    inew = scale["scale_estimate"]["implied_scale_new"]
    check("implied_scale_new_range",
          abs(slo - inew["scale_um_per_px_low"]) < 1e-3
          and abs(shi - inew["scale_um_per_px_high"]) < 1e-3,
          f"recomputed [{slo:.4f}, {shi:.4f}] vs json new [{inew['scale_um_per_px_low']}, {inew['scale_um_per_px_high']}]")
    check("implied_scale_combined_is_intersection",
          comb["scale_um_per_px_low"] >= inew["scale_um_per_px_low"] - 1e-9
          and comb["scale_um_per_px_high"] <= inew["scale_um_per_px_high"] + 1e-9,
          f"combined [{comb['scale_um_per_px_low']}, {comb['scale_um_per_px_high']}] within new")
    check("implied_scale_rules_out_both_candidates",
          comb["agreement"] == "neither" and not comb["agrees_with_18_1165"]
          and not comb["agrees_with_18_25"],
          f"agreement={comb['agreement']}, mid={comb['scale_um_per_px_mid']}")
    check("implied_scale_below_both",
          comb["scale_um_per_px_high"] < SCALE_OURS,
          f"high {comb['scale_um_per_px_high']} < {SCALE_OURS}")
    # ratio test: old boundary vs new boundary == 647/300
    ob = scale["scale_estimate"]["old_boundaries_px"]
    old_lo = ob["P3_FM"]["lower_px"]; old_hi = ob["P3_FIB"]["upper_px"]
    ratio_lo = old_lo / hi; ratio_hi = old_hi / lo
    check("boundary_ratio_brackets_647_over_300",
          ratio_lo <= 647.0 / 300.0 <= ratio_hi,
          f"({ratio_lo:.3f}, {ratio_hi:.3f}] brackets {647.0/300.0:.3f}")
    # implied cut at our scales
    cut = scale["scale_estimate"]["implies_at_our_scales"]
    check("implied_cut_at_our_scales_above_300",
          cut["cut_um_at_18_1165_low"] > 300.0 and cut["cut_um_at_18_25_low"] > 300.0,
          f"{cut['cut_um_at_18_1165_low']}..{cut['cut_um_at_18_1165_high']} @18.1165")

    # ---- check 8: recorded output md5s match the files -----------------------
    for fname, key in (("gate_analysis.csv", "gate_analysis.csv"),
                       ("gate_delta.csv", "gate_delta.csv")):
        rec = scale["outputs"][fname]["md5"]
        live = md5_file(os.path.join(RUN, fname))
        check(f"recorded_md5_matches__{fname}", rec == live, f"{rec} vs {live}")

    print(f"verifier checks: {CHECK_COUNT}, failed: {FAIL_COUNT}")
    return 1 if FAIL_COUNT else 0


if __name__ == "__main__":
    sys.exit(main())
