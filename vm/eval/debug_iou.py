#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug the crop-repro IoU: inspect GT vs prediction coordinate spaces for a few val images."""
import os
from pathlib import Path
import numpy as np
from PIL import Image
from ultralytics import YOLO

ROOT = Path("/home/pranayp/yolo_ooi")
VI = ROOT / "crop_detect_dataset" / "images" / "val"
VL = ROOT / "crop_detect_dataset" / "labels" / "val"
model = YOLO(str(ROOT / "runs" / "crop_repro" / "yolo26n_crop_bbox" / "weights" / "best.pt"))

imgs = sorted(os.listdir(VI))[:3]
for name in imgs:
    ip = VI / name
    lab = VL / (name[:-4] + ".txt")
    with Image.open(ip) as im:
        w, h = im.size
    gts = []
    for ln in lab.read_text().splitlines():
        p = ln.split()
        if len(p) != 5:
            continue
        cx, cy, bw, bh = map(float, p[1:])
        gts.append([cx * w, cy * h, bw * w, bh * h])
    r = model.predict(str(ip), conf=0.25, imgsz=1280, device=0, verbose=False)[0]
    xy = r.boxes.xyxy.cpu().numpy()
    print("img", name, "size", (w, h), "n_gt", len(gts), "n_pred", len(xy))
    print("  pred xyxy min/max:", round(float(xy.min()), 2), round(float(xy.max()), 2))
    print("  first 3 preds:", [ [round(float(v),1) for v in b] for b in xy[:3].tolist() ])
    print("  first 3 gt  :", [ [round(float(v),1) for v in g] for g in gts[:3] ])
    # best-IoU per gt (preds as pixels)
    def iou(a, b):
        ix = max(0, min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0]))
        iy = max(0, min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]))
        inter = ix*iy
        ua = a[2]*a[3]+b[2]*b[3]-inter
        return inter/ua if ua>0 else 0
    for g in gts[:5]:
        pb = [ [float(x1),float(y1),float(x2-x1),float(y2-y1)] for (x1,y1,x2,y2) in xy ]
        best = max((iou(g, p) for p in pb), default=0.0)
        print("    gt", [round(v,1) for v in g], "-> best_iou(as pixels) %.3f" % best)