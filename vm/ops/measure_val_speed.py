#!/usr/bin/env python3
"""Inference cost on OUR crops at 1280 vs native crop size (1568).

Purpose: the 1280-vs-native comparison we have so far comes from the reference runs on the
full-frame dataset. This measures the same thing on our own images, for speed only.

Caveat stated in the output: the model was trained at 1280, so the mAP at 1568 is degraded
by a train/test size mismatch and is NOT a quality comparison. Only the speed is usable.

Usage: python3 measure_val_speed.py
"""
from pathlib import Path

from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "dataset_multiclass" / "data.yaml"
WEIGHTS = PRJ / "runs" / "yolo26_mc_arch" / "mc_control_stock" / "weights" / "best.pt"
SIZES = [1280, 1568]  # 1568 = native crop width rounded up to a multiple of 32
BATCH = 8


def main():
    print("=" * 88)
    print("INFERENCE COST ON OUR CROPS: 1280 (train size) vs 1568 (native crop size)")
    print("=" * 88)
    print("model: runs/yolo26_mc_arch/mc_control_stock/weights/best.pt (trained at 1280)")
    print("val set: dataset_multiclass/images/val, 88 images, batch 8, A100 80GB")
    print("caveat: mAP at 1568 is degraded by the train/test size mismatch, so read")
    print("        the speed only. This is not a quality comparison.\n")

    for size in SIZES:
        model = YOLO(str(WEIGHTS))
        r = model.val(data=str(DATA), split="val", imgsz=size, batch=BATCH, verbose=False)
        pre = r.speed.get("preprocess", 0.0)
        inf = r.speed.get("inference", 0.0)
        post = r.speed.get("postprocess", 0.0)
        total = pre + inf + post
        print(f"imgsz {size}:")
        print(f"   ms/image   preprocess {pre:.2f}   inference {inf:.2f}   postprocess {post:.2f}"
              f"   TOTAL {total:.2f}")
        print(f"   images/s   {1000 / total:.1f}  (single-stream, batch {BATCH})")
        print(f"   (mAP50 {r.box.map50:.4f} at this size; degraded 1568 by the size mismatch)")


if __name__ == "__main__":
    main()
