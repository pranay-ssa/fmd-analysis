#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IoU eval (VM): matched-box IoU on the frozen val split for a trained OBB run.

Lead's metric of record (2026-09-08): mean IoU of matched detections vs GT at
conf >= 0.25 (greedy one-to-one, class-aware). Geometry lives in iou_geometry.py
(torch-free, locally sanity-tested).

Usage: python3 iou_eval.py <run_dir_name>   e.g. iou_eval.py depth_plus2_deep
Writes <run_dir>/iou_metrics.json and prints a per-class table.
"""
import json
import sys
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from iou_geometry import parse_gt, greedy_match

ROOT = Path("/home/pranayp/yolo_ooi")
VAL_IMGS = ROOT / "dataset_obb" / "images" / "val"
VAL_LABELS = ROOT / "dataset_obb" / "labels" / "val"
CONF = 0.25
CLASSES = ["Bubble Cluster", "Bubble", "Bubble On 123", "Bubble Irregular",
           "Bubble On Edge", "Extraneous Polymer", "Fiber", "Foreign Matter",
           "HEMA Fragment", "Wet Package"]


def main():
    if len(sys.argv) != 2:
        print("usage: iou_eval.py <run_dir_name>")
        sys.exit(2)
    run_name = sys.argv[1]
    rdir = ROOT / "runs" / "yolo_arch" / run_name
    best = rdir / "weights" / "best.pt"
    if not best.exists():
        print("no best.pt at", best)
        sys.exit(1)
    model = YOLO(str(best))

    per_cls_iou = {c: [] for c in CLASSES}
    per_cls = {c: {"matched": 0, "gt": 0} for c in CLASSES}
    n_gt = n_matched = 0

    img_paths = sorted(VAL_IMGS.glob("*"))
    for ip in img_paths:
        lab = VAL_LABELS / (ip.stem + ".txt")
        if not lab.exists():
            continue
        # native size for denormalizing GT + predicting in source space
        from PIL import Image
        with Image.open(ip) as im:
            w, h = im.size
        gts = parse_gt(lab, w, h)
        if not gts:
            continue
        for gc, _ in gts:
            per_cls[CLASSES[gc]]["gt"] += 1
            n_gt += 1
        res = model.predict(str(ip), conf=CONF, imgsz=640, device=0, verbose=False)[0]
        obb = res.obb
        preds = []
        if obb is not None and obb.xyxyxyxy is not None and len(obb.xyxyxyxy) > 0:
            xy = obb.xyxyxyxy.cpu().numpy()  # (N, 4, 2) corners
            cls = obb.cls.cpu().numpy().astype(int)
            conf = obb.conf.cpu().numpy()
            # guard: normalized coords would all be <= ~1.5
            if xy.max() <= 1.5:
                xy = xy * np.array([w, h])
            for c, pts, cf in zip(cls, xy, conf):
                preds.append((c, np.asarray(pts, dtype=float), float(cf)))
        matches = greedy_match(preds, gts)
        for iou, c in matches:
            per_cls[CLASSES[c]]["matched"] += 1
            per_cls_iou[CLASSES[c]].append(iou)
            n_matched += 1

    out = {"run": run_name, "conf": CONF, "n_val_images": len(img_paths),
           "n_gt_boxes": n_gt, "n_matched": n_matched,
           "match_rate": round(n_matched / n_gt, 4) if n_gt else None,
           "per_class": {}}
    ious = []
    print("%-22s %8s %8s %10s %10s" % ("class", "gt", "matched", "mean_iou", "match%"))
    for c in CLASSES:
        vals = per_cls_iou[c]
        mi = float(np.mean(vals)) if vals else None
        mr = per_cls[c]["matched"] / per_cls[c]["gt"] if per_cls[c]["gt"] else None
        out["per_class"][c] = {"gt": per_cls[c]["gt"], "matched": per_cls[c]["matched"],
                               "mean_iou": None if mi is None else round(mi, 4),
                               "match_rate": None if mr is None else round(mr, 4)}
        ious += vals
        print("%-22s %8d %8d %10s %10s" % (c, per_cls[c]["gt"], per_cls[c]["matched"],
                                           "-" if mi is None else "%.4f" % mi,
                                           "-" if mr is None else "%.0f%%" % (100 * mr)))
    out["iou_mean_overall"] = round(float(np.mean(ious)), 4) if ious else None
    out["iou_median_overall"] = round(float(np.median(ious)), 4) if ious else None
    print("overall mean IoU:", out["iou_mean_overall"], " median:", out["iou_median_overall"],
          " match rate:", out["match_rate"])
    with open(rdir / "iou_metrics.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", rdir / "iou_metrics.json")


if __name__ == "__main__":
    main()
