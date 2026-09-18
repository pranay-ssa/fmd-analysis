#!/usr/bin/env python3
from ultralytics import YOLO
m = YOLO("runs/yolo26_multiclass/yolo26n_mc_baseline/weights/best.pt")
v = m.val(data="dataset_multiclass/data.yaml", split="val", imgsz=1280, verbose=False)
# Use summary() for per-class data
s = v.summary()
for row in s:
    print(f"  {row['Class']:30s}  AP50={row['AP50']:.4f}  AP50-95={row['AP50-95']:.4f}  P={row['Precision']:.4f}  R={row['Recall']:.4f}")
print(f"\n  {'all':30s}  AP50={v.box.map50:.4f}  AP50-95={v.box.map:.4f}  P={v.box.mp:.4f}  R={v.box.mr:.4f}")
