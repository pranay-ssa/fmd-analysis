#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detection-model IoU eval for the crop reproduction (YOLO11n/YOLO26n single-cls).

Both GT and predictions are compared in NORMALIZED coordinates (0-1) so no resolution or
letterbox scaling can break the IoU. GT labels are "class cx cy w h" normalized; predictions
come from Results.boxes.xyxyn (also normalized to the original frame).

Metrics (same spirit as the teammate's):
  - matched IoU: greedy one-to-one, per-GT overlap of the closest same-frame detection at conf 0.25
  - match rate: share of GT boxes with any same-frame detection (lenient, IoU > 0)
  - localization ceiling: best IoU per GT over ALL predictions at conf 0.001
    + frac>=0.50 / >=0.75, and the zero-overlap (hard-miss) floor.
Usage: cd /home/pranayp/yolo_ooi && python3 -u iou_eval_det.py
"""
import json
from pathlib import Path

import numpy as np
from ultralytics import YOLO

ROOT = Path("/home/pranayp/yolo_ooi")
VAL_IMGS = ROOT / "crop_detect_dataset" / "images" / "val"
VAL_LABELS = ROOT / "crop_detect_dataset" / "labels" / "val"
IMGSZ = 1280
MATCH_CONF = 0.25
CEIL_CONF = 0.001
RUNS = ["yolo11n_crop_bbox", "yolo26n_crop_bbox"]


def parse_gt(p):
    """class cx cy w h (normalized)."""
    return [[float(t) for t in ln.split()[1:5]] for ln in p.read_text().splitlines()
            if len(ln.split()) == 5]


def iou_full(ax, ay, aw, ah, bx, by, bw, bh):
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    ua = aw * ah + bw * bh - inter
    return inter / ua if ua > 0 else 0.0


def greedy(preds, gts):
    used = set()
    matches = []
    for p in sorted(preds, key=lambda z: -z[0]):
        best, bi = 0.0, -1
        for gi, g in enumerate(gts):
            if gi in used:
                continue
            v = iou_full(p[1], p[2], p[3], p[4], g[0], g[1], g[2], g[3])
            if v > best:
                best, bi = v, gi
        if bi >= 0 and best > 0:
            used.add(bi)
            matches.append(best)
    return matches


def cxcywh_of(res):
    if res.boxes is None or len(res.boxes) == 0:
        return []
    xy = res.boxes.xyxyn.cpu().numpy()  # normalized [x1,y1,x2,y2] to the original frame
    conf = res.boxes.conf.cpu().numpy()
    return [(float(c), float((a + c) / 2), float((b + dd) / 2), float(c - a), float(dd - b))
            for (a, b, c, dd), c in zip(xy, conf)]


def eval_run(name):
    rdir = ROOT / "runs" / "crop_repro" / name
    model = YOLO(str(rdir / "weights" / "best.pt"))
    matched_all, n_gt = [], 0
    ceiling = []
    for ip in sorted(VAL_IMGS.glob("*")):
        lab = VAL_LABELS / (ip.stem + ".txt")
        if not lab.exists():
            continue
        gts = parse_gt(lab)
        n_gt += len(gts)
        r25 = model.predict(str(ip), conf=MATCH_CONF, imgsz=IMGSZ, device=0, verbose=False)[0]
        matched_all += greedy(cxcywh_of(r25), gts)
        r01 = model.predict(str(ip), conf=CEIL_CONF, imgsz=IMGSZ, device=0, verbose=False)[0]
        cp = cxcywh_of(r01)
        for g in gts:
            best = max((iou_full(g[0], g[1], g[2], g[3], p[1], p[2], p[3], p[4]) for p in cp), default=0.0)
            ceiling.append(best)
    return name, n_gt, matched_all, ceiling


def main():
    out = {}
    for name in RUNS:
        name, n_gt, matched_all, ceiling = eval_run(name)
        rdir = ROOT / "runs" / "crop_repro" / name
        ma = np.array(matched_all)
        cb = np.array(ceiling)
        d = {
            "run": name,
            "n_gt": n_gt,
            "matched_conf": MATCH_CONF,
            "matched_ious": {"n": int(len(ma)),
                             "mean": round(float(ma.mean()), 4) if len(ma) else None,
                             "median": round(float(np.median(ma)), 4) if len(ma) else None},
            "match_rate": round(float(len(ma) / n_gt), 4) if n_gt else None,
            "localization_ceiling_conf": CEIL_CONF,
            "localization_ceiling": {"mean": round(float(cb.mean()), 4),
                                     "median": round(float(np.median(cb)), 4),
                                     "frac>=0.50": round(float((cb >= 0.5).mean()), 4),
                                     "frac>=0.75": round(float((cb >= 0.75).mean()), 4),
                                     "frac==0": round(float((cb == 0).mean()), 4)},
        }
        out[name] = d
        print(json.dumps(d, indent=2), flush=True)
        (rdir).mkdir(exist_ok=True)
        (rdir / "iou_det_metrics.json").write_text(json.dumps(d, indent=1))
    (ROOT / "crop_repro_iou.json").write_text(json.dumps(out, indent=1))
    print("wrote", ROOT / "crop_repro_iou.json")


if __name__ == "__main__":
    main()