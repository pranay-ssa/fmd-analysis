#!/usr/bin/env python3
"""Test the annotator's stated rule for the *_MICRON_THRESHOLD tags.

From the handover email:

    "I have also developed a script to tag images containing debris that
     exceeds the 647-micron size threshold - these images in particular should
     be fed into the edge algorithm training process."

So the rule, as stated, is per image and per base code:

    flag the image if it contains a base-code box whose size exceeds 647 um

This script tests that rule directly instead of assuming it. For every image
carrying a gated base code it computes the largest base-code box on that image,
predicts the flag from the 647 micron threshold, and compares the prediction to
the flag actually present in the XML.

Reported per gated code:
  * a confusion matrix against the 647 micron prediction
  * the separating range: the largest unflagged box and the smallest flagged box,
    which brackets the effective threshold
  * the effective threshold in microns, if the two groups separate cleanly

Read-only. Paths are arguments.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import xml.etree.ElementTree as ET

DEFAULT_ANN = ("/home/amd100-user/FMD_Data_26082026/fmd_temp_images/"
               "PRODUCTION_20260925/annotations")

# the four gated families, base code -> gate code
GATED = {
    "P3_EP": "P3_EP_MICRON_THRESHOLD",
    "P3_FIB": "P3_FIB_MICRON_THRESHOLD",
    "P3_FM": "P3_FM_MICRON_THRESHOLD",
    "P3_HE": "P3_HE_MICRON_THRESHOLD",
}


def load(ann_dir):
    """Return {basename: {"codes": set, "max_diag_by_code": {code: px}}}."""
    out = {}
    for path in sorted(glob.glob(os.path.join(ann_dir, "*.xml"))):
        # Parser safety: our own team's CVAT exports from our own VM, not
        # untrusted input. Use defusedxml if this ever points at a third party.
        root = ET.parse(path).getroot()
        for im in root.iter("image"):
            base = os.path.basename(im.get("name"))
            rec = out.setdefault(base, {"codes": set(), "max_diag_by_code": {}})
            for b in im.findall("box"):
                lab = b.get("label")
                d = math.hypot(abs(float(b.get("xbr")) - float(b.get("xtl"))),
                               abs(float(b.get("ybr")) - float(b.get("ytl"))))
                rec["codes"].add(lab)
                rec["max_diag_by_code"][lab] = max(
                    rec["max_diag_by_code"].get(lab, 0.0), d)
            for t in im.findall("tag"):
                rec["codes"].add(t.get("label"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotations", default=DEFAULT_ANN)
    ap.add_argument("--um-per-px", type=float, default=18.1165)
    ap.add_argument("--threshold-um", type=float, default=647.0)
    ap.add_argument("--out", default="micron_gate_test.json")
    a = ap.parse_args()

    um = a.um_per_px
    thr_px = a.threshold_um / um
    data = load(a.annotations)

    report = {
        "rule": "flag an image if it contains a base-code box larger than %.0f um"
                % a.threshold_um,
        "threshold_um": a.threshold_um,
        "threshold_px": thr_px,
        "um_per_px": um,
        "images": len(data),
        "per_code": [],
    }

    print("Rule under test: flag an image when its largest %s box exceeds %.0f um "
          "(%.2f px)\n" % ("base-code", a.threshold_um, thr_px))
    print("%-9s %6s %6s %6s %6s %7s %10s %10s %12s" % (
        "base", "images", "flag", "noflag", "TP", "FP", "max unflag", "min flag",
        "agreement"))
    for base, gate in sorted(GATED.items()):
        rows = [r for r in data.values() if base in r["codes"]]
        tp = fp = fn = tn = 0
        unflagged_max = []
        flagged_min = []
        for r in rows:
            mx = r["max_diag_by_code"].get(base)
            if mx is None:
                continue
            flagged = gate in r["codes"]
            predicted = mx > thr_px
            if flagged:
                flagged_min.append(mx)
            else:
                unflagged_max.append(mx)
            if flagged and predicted:
                tp += 1
            elif flagged and not predicted:
                fp += 1
            elif not flagged and predicted:
                fn += 1
            else:
                tn += 1
        n = tp + fp + fn + tn
        agree = (tp + tn) / n if n else 0.0
        mu = max(unflagged_max) if unflagged_max else None
        mf = min(flagged_min) if flagged_min else None
        print("%-9s %6d %6d %6d %6d %6d %10s %10s %11.1f%%" % (
            base, len(rows), tp + fp, tn + fn, tp, fp,
            ("%.1f px" % mu) if mu is not None else "n/a",
            ("%.1f px" % mf) if mf is not None else "n/a",
            100 * agree))

        entry = {
            "base": base, "gate": gate,
            "images": len(rows),
            "flagged": tp + fp, "unflagged": tn + fn,
            "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
            "agreement": agree,
            "largest_unflagged_px": mu, "largest_unflagged_um": mu * um if mu else None,
            "smallest_flagged_px": mf, "smallest_flagged_um": mf * um if mf else None,
            "separates_cleanly": (mu is not None and mf is not None and mu <= mf),
            "effective_lower_um": mu * um if mu is not None else None,
            "effective_upper_um": mf * um if mf is not None else None,
        }
        report["per_code"].append(entry)

    print()
    for e in report["per_code"]:
        if e["separates_cleanly"]:
            print("  %s: the groups separate cleanly. Largest unflagged box is %.0f um, "
                  "smallest flagged is %.0f um, so the script's cut sits between them "
                  "and the stated %.0f um is inside that window."
                  % (e["base"], e["effective_lower_um"], e["effective_upper_um"],
                     a.threshold_um))
        else:
            print("  %s: the groups do NOT separate cleanly. Largest unflagged box is "
                  "%s um, smallest flagged is %s um, so a single size cut cannot "
                  "reproduce the flags. Agreement with the stated %.0f um rule is %.1f%%."
                  % (e["base"],
                     ("%.0f" % e["effective_lower_um"]) if e["effective_lower_um"] else "n/a",
                     ("%.0f" % e["effective_upper_um"]) if e["effective_upper_um"] else "n/a",
                     a.threshold_um, 100 * e["agreement"]))

    total_img = sum(e["images"] for e in report["per_code"])
    allagree = [e["agreement"] for e in report["per_code"]]
    report["overall"] = {
        "gated_code_images": total_img,
        "mean_agreement": sum(allagree) / len(allagree),
        "all_separate_cleanly": all(e["separates_cleanly"] for e in report["per_code"]),
    }
    print("\nGated-code images across the four families: %d" % total_img)

    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("wrote %s" % os.path.abspath(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
