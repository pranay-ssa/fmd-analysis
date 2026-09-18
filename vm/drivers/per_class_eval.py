#!/usr/bin/env python3
"""Per-class AP50 for YOLO26n baseline on crop dataset."""
from ultralytics import YOLO
import json

m = YOLO("runs/yolo26_arch/yolo26n_baseline/weights/best.pt")

# Multi-class eval (single_cls=False) to get per-class AP
v = m.val(data="crop_detect_dataset/data.yaml", split="val", imgsz=1280,
          single_cls=False, verbose=False)

names = v.names
ap50 = v.ap50
results = []
print("Per-class AP50 (multi-class eval):")
for i, (name, ap) in enumerate(zip(names, ap50)):
    results.append({"class": name, "AP50": round(float(ap), 4)})
    print(f"  {name:30s}  AP50={ap:.4f}")

print(f"\nOverall mAP50: {v.box.map50:.4f}")

with open("per_class_ap50_baseline.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved to per_class_ap50_baseline.json")
