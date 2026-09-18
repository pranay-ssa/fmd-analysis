#!/usr/bin/env python3
"""Measure the opacity a pasted defect was laid down at, by defect size.

The paste is `alpha * patch + (1 - alpha) * background`, so a defect's own
contrast is multiplied by alpha at its pixels. alpha is the feathered mask, and
the feather kernel is FIXED (7 px) while the defects are 3 px to 300 px wide.
Where the kernel is wider than the defect, no pixel of that defect is ever fully
opaque: the defect arrives thinner than the library contains it, and the blur
bleeds background into its core.

This is deterministic - no image statistics, no dependency on defect polarity
(some classes here are bright rings, some are dark specks) - so it says exactly
how much of each defect survives the paste.

Reported: mean alpha over each defect's own core pixels, bucketed by defect size,
plus the share of defects that are pasted at essentially full opacity (>= 0.98).

USAGE
    python experiments/augmentation/measure_paste_fidelity.py --out run/augment/preview_v2
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

import cv2
import numpy as np

FEATHER_K = 7
ERODE = 1


def poly_mask(shape, box, grow: float) -> np.ndarray:
    w = (box["xbr"] - box["xtl"]) * (1.0 + grow)
    h = (box["ybr"] - box["ytl"]) * (1.0 + grow)
    cx = (box["xtl"] + box["xbr"]) / 2.0
    cy = (box["ytl"] + box["ybr"]) / 2.0
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillConvexPoly(m, cv2.boxPoints(((cx, cy), (w, h), box["rotation"])).astype(np.int32), 255)
    return m


def bucket(side: float) -> str:
    for lim, name in ((5, "<=5 px"), (10, "6-10 px"), (30, "11-30 px"), (100, "31-100 px")):
        if side <= lim:
            return name
    return ">100 px"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dilate", type=float, default=0.25,
                    help="must match the run that produced the samples")
    args = ap.parse_args()

    rows = []
    for lab in sorted(args.out.glob("*/*/labels.json")):
        d = lab.parent
        meta = json.loads(lab.read_text())
        img = cv2.imread(str(d / "original.png"), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        boxes = meta.get("source_boxes", [])
        if not boxes:
            continue
        k = int(meta.get("feather_k") or FEATHER_K)   # the kernel the run actually used
        # reproduce the pipeline's alpha exactly: feather the union of dilated boxes
        union = np.zeros(img.shape[:2], np.uint8)
        for b in boxes:
            union = cv2.bitwise_or(union, poly_mask(img.shape, b, args.dilate))
        alpha = cv2.GaussianBlur(union.astype(np.float32) / 255.0, (k, k), 0)
        for b in boxes:
            core = poly_mask(img.shape, b, 0.0)
            e = cv2.erode(core, np.ones((3, 3), np.uint8), iterations=ERODE)
            if cv2.countNonZero(e) >= 4:
                core = e
            vals = alpha[core > 0]
            if vals.size == 0:
                continue
            rows.append({"class": d.parent.name, "stem": d.name,
                         "side_px": round(min(b["xbr"] - b["xtl"], b["ybr"] - b["ytl"]), 1),
                         "bucket": bucket(min(b["xbr"] - b["xtl"], b["ybr"] - b["ytl"])),
                         "core_px": int(core.sum() // 255),
                         "alpha_core_mean": round(float(vals.mean()), 4),
                         "alpha_core_min": round(float(vals.min()), 4)})

    if not rows:
        print(f"no labelled samples under {args.out}")
        return 1

    print(f"defects measured            : {len(rows)}  ({len({r['stem'] for r in rows})} images)")
    print(f"defect opacity, all sizes   : median {st.median(r['alpha_core_mean'] for r in rows):.3f}")
    print(f"pasted at full opacity      : "
          f"{sum(1 for r in rows if r['alpha_core_mean'] >= 0.98) / len(rows) * 100:.0f}% of defects")
    print(f"\n{'defect size':<12}{'defects':>8}{'median alpha':>14}{'worst alpha':>13}{'share >=0.98':>14}")
    for b in ("<=5 px", "6-10 px", "11-30 px", "31-100 px", ">100 px"):
        rs = [r for r in rows if r["bucket"] == b]
        if rs:
            full = sum(1 for r in rs if r["alpha_core_mean"] >= 0.98) / len(rs) * 100
            print(f"{b:<12}{len(rs):>8}{st.median(r['alpha_core_mean'] for r in rs):>14.3f}"
                  f"{min(r['alpha_core_mean'] for r in rs):>13.3f}{full:>13.0f}%")
    (args.out / "paste_opacity.json").write_text(json.dumps(rows, indent=2))
    print("\nInterpretation: alpha at the core is the factor by which the pasted defect's own")
    print("contrast is multiplied. Below about 0.9 the defect is visibly thinned by the blend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
