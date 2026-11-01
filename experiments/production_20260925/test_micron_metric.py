#!/usr/bin/env python3
"""Work out which size metric and cut reproduces the *_MICRON_THRESHOLD flags.

From the handover email:

    "I have also developed a script to tag images containing debris that
     exceeds the 647-micron size threshold - these images in particular should
     be fed into the edge algorithm training process."

The rule is stated as a 647 micron size cut, applied per image, on the
P3 (foreign material) family. "Size" is not defined in the email, and a box has
several plausible sizes: its diagonal, its longest side, its shorter side, or
the diameter of a circle with the same area. Which one was used changes which
boxes fall over the cut.

So rather than assume, this tests each candidate metric:

  1. does the stated 647 micron cut, under this metric, reproduce the flags
     already in the XML;
  2. if not, what cut would, and how far is it from 647 microns;
  3. which metric separates the flagged from the unflagged images cleanly at all.

Reported per base code per metric. Read-only, paths are arguments.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import xml.etree.ElementTree as ET

DEFAULT_ANN = ("/home/amd100-user/FMD_Data_26082026/fmd_temp_images/"
               "PRODUCTION_20260925/annotations")

GATED = {
    "P3_EP": "P3_EP_MICRON_THRESHOLD",
    "P3_FIB": "P3_FIB_MICRON_THRESHOLD",
    "P3_FM": "P3_FM_MICRON_THRESHOLD",
    "P3_HE": "P3_HE_MICRON_THRESHOLD",
}

# candidate readings of "size" for a box of width w and height h, in pixels
METRICS = {
    "diagonal": lambda w, h: math.hypot(w, h),
    "longest side": lambda w, h: max(w, h),
    "shorter side": lambda w, h: min(w, h),
    "same-area circle diameter": lambda w, h: math.sqrt(4.0 * w * h / math.pi),
    "geometric mean of the sides": lambda w, h: math.sqrt(w * h),
}


def load(ann_dir):
    out = {}
    for path in sorted(glob.glob(os.path.join(ann_dir, "*.xml"))):
        # Parser safety: our own team's CVAT exports from our own VM, not
        # untrusted input. Use defusedxml if this ever points at a third party.
        root = ET.parse(path).getroot()
        for im in root.iter("image"):
            base = os.path.basename(im.get("name"))
            rec = out.setdefault(base, {"codes": set(), "boxes": []})
            for b in im.findall("box"):
                w = abs(float(b.get("xbr")) - float(b.get("xtl")))
                h = abs(float(b.get("ybr")) - float(b.get("ytl")))
                rec["boxes"].append((b.get("label"), w, h))
            for t in im.findall("tag"):
                rec["codes"].add(t.get("label"))
    return out


def sweep(pairs):
    """pairs: list of (value, flagged). Return (threshold, agreement)."""
    n = len(pairs)
    if not n:
        return None, 0.0
    vals = sorted({v for v, _ in pairs})
    cands = [(vals[i] + vals[i + 1]) / 2.0 for i in range(len(vals) - 1)]
    cands.append(vals[-1] * 1.0000001 + 1e-9)
    best_t, best_a = None, -1.0
    for t in cands:
        a = sum(1 for v, f in pairs if (v > t) == bool(f)) / n
        if a > best_a:
            best_t, best_a = t, a
    return best_t, best_a


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotations", default=DEFAULT_ANN)
    ap.add_argument("--um-per-px", type=float, default=18.1165)
    ap.add_argument("--threshold-um", type=float, default=647.0)
    ap.add_argument("--out", default="micron_metric_test.json")
    a = ap.parse_args()

    um = a.um_per_px
    stated_px = a.threshold_um / um
    data = load(a.annotations)

    print("Stated rule: flag an image when its debris box exceeds %.0f um, which is "
          "%.2f px at %s um/px.\n" % (a.threshold_um, stated_px, um))
    print("For each reading of 'size': how well does the stated cut reproduce the flags,")
    print("and what cut would do better.\n")
    print("%-9s %-28s %10s %10s %12s %12s" % (
        "base", "metric", "at 647um", "best cut", "best cut um", "best agree"))

    report = {"um_per_px": um, "threshold_um": a.threshold_um,
              "threshold_px": stated_px, "per_code": {}}

    for base, gate in sorted(GATED.items()):
        report["per_code"][base] = {}
        rows = [r for r in data.values() if any(l == base for l, _, _ in r["boxes"])]
        for mname, fn in METRICS.items():
            pairs = []
            for r in rows:
                vals = [fn(w, h) for l, w, h in r["boxes"] if l == base]
                if not vals:
                    continue
                pairs.append((max(vals), gate in r["codes"]))
            if not pairs:
                continue
            n = len(pairs)
            at_stated = sum(1 for v, f in pairs if (v > stated_px) == bool(f)) / n
            bt, ba = sweep(pairs)
            report["per_code"][base][mname] = {
                "images": n,
                "agreement_at_stated_cut": at_stated,
                "best_threshold_px": bt,
                "best_threshold_um": bt * um if bt else None,
                "best_agreement": ba,
            }
            print("%-9s %-28s %9.1f%% %10s %12s %11.1f%%" % (
                base, mname, 100 * at_stated,
                ("%.1f px" % bt) if bt is not None else "n/a",
                ("%.0f" % (bt * um)) if bt else "n/a",
                100 * ba))

    # which metric, if any, reproduces all four codes at the stated cut
    print("\nMetrics that reproduce every flag at the stated %.0f um cut:" % a.threshold_um)
    perfect = []
    for mname in METRICS:
        vals = [report["per_code"][b].get(mname, {}).get("agreement_at_stated_cut", 0)
                for b in GATED]
        if vals and all(v is not None and v >= 0.9999 for v in vals):
            perfect.append(mname)
    if perfect:
        for m in perfect:
            print("  %s" % m)
    else:
        print("  none of them. No single size reading at %.0f um reproduces all four "
              "codes exactly." % a.threshold_um)
    report["metrics_reproducing_all_at_stated_cut"] = perfect

    print("\nMetrics that separate flagged from unflagged cleanly on every code:")
    clean = []
    for mname in METRICS:
        vals = [report["per_code"][b].get(mname, {}).get("best_agreement", 0) for b in GATED]
        if vals and all(v >= 0.9999 for v in vals):
            clean.append(mname)
    if clean:
        for m in clean:
            bt = [report["per_code"][b][m]["best_threshold_um"] for b in GATED]
            print("  %-28s best cut ranges %.0f to %.0f um across the four codes"
                  % (m, min(bt), max(bt)))
    else:
        print("  none. Every metric leaves some flagged image smaller than some "
              "unflagged one.")
    report["metrics_separating_cleanly"] = clean

    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("\nwrote %s" % os.path.abspath(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
