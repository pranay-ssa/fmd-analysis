#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Correct IoU for the crop repro, using Ultralytics' OWN save_txt normalized detections.

model.predict(source=<val dir>, save_txt=True) writes, per image, detections in the SAME
normalized "class cx cy w h" frame that the GT labels use (Ultralytics de-letterboxes to the
original frame internally). Comparing those to the GT labels is therefore consistent with the
val-time matching that produced mAP50 ~0.60, unlike reading results.boxes directly.

Usage: cd /home/pranayp/yolo_ooi && python3 -u iou_eval_det2.py
"""
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path("/home/pranayp/yolo_ooi")
VAL_IMGS = ROOT / "crop_detect_dataset" / "images" / "val"
VAL_LABELS = ROOT / "crop_detect_dataset" / "labels" / "val"
IMGSZ = 1280
RUNS = ["yolo11n_crop_bbox", "yolo26n_crop_bbox"]


def iou_full(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    ua = aw * ah + bw * bh - inter
    return inter / ua if ua > 0 else 0.0


def read_boxes(path):
    out = []
    if not path.exists():
        return out
    for ln in path.read_text().splitlines():
        p = ln.split()
        if len(p) >= 5:
            out.append([float(x) for x in p[1:5]])
    return out


def eval_run(name):
    rdir = ROOT / "runs" / "crop_repro" / name
    model = YOLO(str(rdir / "weights" / "best.pt"))
    tmp = Path(tempfile.mkdtemp(prefix="ioupred_"))
    # predict over the whole val dir, writing normalized detections per image
    model.predict(source=str(VAL_IMGS), imgsz=IMGSZ, conf=0.001, device=0,
                  save_txt=True, save_conf=False, project=str(tmp), name="p", exist_ok=True)
    preddir = tmp / "p" / "labels"
    matched_all, n_gt = [], 0
    ceiling = []
    for ip in sorted(VAL_IMGS.glob("*")):
        lab = VAL_LABELS / (ip.stem + ".txt")
        if not lab.exists():
            continue
        gts = read_boxes(lab)
        n_gt += len(gts)
        preds = read_boxes(preddir / (ip.stem + ".txt"))
        # greedy one-to-one matched IoU at conf is handled in predict; here all preds are conf>=0.001
        used = set()
        matches = []
        for p in sorted(preds, key=lambda b: -1):
            best, bi = 0.0, -1
            for gi, g in enumerate(gts):
                if gi in used:
                    continue
                v = iou_full(p, g)
                if v > best:
                    best, bi = v, gi
            if bi >= 0 and best > 0:
                used.add(bi)
                matches.append(best)
        matched_all += matches
        for g in gts:
            ceiling.append(max((iou_full(g, p) for p in preds), default=0.0))
    shutil.rmtree(tmp, ignore_errors=True)
    ma, cb = np.array(matched_all), np.array(ceiling)
    return name, n_gt, ma, cb


def main():
    out = {}
    for name in RUNS:
        name, n_gt, ma, cb = eval_run(name)
        d = {
            "run": name,
            "n_gt": n_gt,
            "note": "detections from Ultralytics save_txt (conf 0.001), same normalized frame as GT and val",
            "matched_ious": {"n": int(len(ma)),
                             "mean": round(float(ma.mean()), 4) if len(ma) else None,
                             "median": round(float(np.median(ma)), 4) if len(ma) else None},
            "match_rate": round(float(len(ma) / n_gt), 4) if n_gt else None,
            "localization_ceiling": {"mean": round(float(cb.mean()), 4),
                                     "median": round(float(np.median(cb)), 4),
                                     "frac>=0.50": round(float((cb >= 0.5).mean()), 4),
                                     "frac>=0.75": round(float((cb >= 0.75).mean()), 4),
                                     "frac==0": round(float((cb == 0).mean()), 4)},
        }
        out[name] = d
        print(json.dumps(d, indent=2), flush=True)
        (ROOT / "runs" / "crop_repro" / name / "iou_det_metrics.json").write_text(json.dumps(d, indent=1))
    (ROOT / "crop_repro_iou.json").write_text(json.dumps(out, indent=1))
    print("wrote", ROOT / "crop_repro_iou.json")


if __name__ == "__main__":
    main()