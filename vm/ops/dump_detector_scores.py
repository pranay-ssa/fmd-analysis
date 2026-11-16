#!/usr/bin/env python3
"""Dump per-picture detector scores for one split.

Writes one row per picture: the highest confidence per class at a low confidence
floor, and the box count per class. The pass/fail block only needs the highest
score per class, so this keeps the file small enough to review; boxes stay on the
VM in the run's own artifacts.

Run as pranayp from the repo root:

    /usr/bin/python3.12 vm/ops/dump_detector_scores.py \
        --weights run/detector_20261110/yolo26n_fmd_7cls_all/weights/best.pt \
        --images /data/FMD_Data_26082026/fmd_detector_20261110/images/val \
        --split val --out run/detector_20261110/yolo26n_fmd_7cls_all/detections_val.csv
"""
import argparse
import csv
from pathlib import Path

from ultralytics import YOLO

CLASSES = ["Bubble", "Bubble Cluster", "Wet Package", "Fiber",
           "Extraneous Polymer", "HEMA", "Foreign Matter"]
FIELDS = ["md5", "split", "boxes"]
for name in CLASSES:
    FIELDS += [f"{name}_max", f"{name}_count"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--split", required=True, choices=["val", "test"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="0")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    model = YOLO(args.weights)
    names = {int(k): v for k, v in model.names.items()}
    missing = [c for c in CLASSES if c not in names.values()]
    if missing:
        raise SystemExit(f"model names missing classes: {missing}; has {sorted(names.values())}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        results = model.predict(
            source=args.images, stream=True, conf=args.conf, iou=0.7,
            imgsz=args.imgsz, batch=args.batch, device=args.device,
            max_det=300, verbose=False, save=False,
        )
        for result in results:
            row = {field: 0.0 for field in FIELDS}
            row["md5"] = Path(result.path).stem
            row["split"] = args.split
            boxes = result.boxes
            if boxes is not None and len(boxes):
                classes = boxes.cls.tolist()
                confs = boxes.conf.tolist()
                row["boxes"] = len(classes)
                for cls, conf in zip(classes, confs):
                    name = names[int(cls)]
                    if name not in CLASSES:
                        continue
                    row[f"{name}_max"] = max(row[f"{name}_max"], float(conf))
                    row[f"{name}_count"] += 1
            writer.writerow(row)
            written += 1
            if written % 200 == 0:
                print(f"{args.split}: {written} pictures", flush=True)
            if args.limit and written >= args.limit:
                break

    print(f"{args.split}: wrote {written} rows to {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
