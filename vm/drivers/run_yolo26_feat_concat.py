#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Train YOLO26 baseline vs feature-concat fork on crop pipeline.

Compares stock yolo26n (baseline) against yolo26_feat_concat (P3→P4 skip).
Same frozen config as YOLO11 experiments: batch 8, 100 ep, seed 42, imgsz 1280.

Run: cd /home/pranayp/yolo_ooi && python3 -u run_yolo26_feat_concat.py
"""
import json
import time
from pathlib import Path
from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "crop_detect_dataset" / "data.yaml"
RUNS = PRJ / "runs" / "yolo26_arch"

EXPERIMENTS = [
    ("YOLO26n Baseline",  str(PRJ / "yolo26n.pt"),  "yolo26n_baseline"),
    ("YOLO26n FeatConcat", str(PRJ / "yolo26n.pt"),  "yolo26n_feat_concat",
     str(PRJ / "experiments/yolo26_feat_concat.yaml")),
]

COMMON = dict(epochs=100, imgsz=1280, batch=8, device=0, patience=50, seed=42,
              project=str(RUNS), plots=False, single_cls=True, exist_ok=False,
              data=str(DATA))


def run_one(name, weights, run_name, yaml_override=None):
    print("=== START %s %s ===" % (name, time.strftime("%Y-%m-%dT%H:%M:%S")), flush=True)
    t0 = time.time()
    if yaml_override:
        m = YOLO(yaml_override, task="detect")
    else:
        m = YOLO(weights)
    m.train(name=run_name, **COMMON)
    train_s = time.time() - t0

    best = YOLO(str(RUNS / run_name / "weights" / "best.pt"))
    v = best.val(data=str(DATA), split="val", imgsz=1280, single_cls=True,
                 verbose=False, name=run_name + "_val")
    row = {
        "experiment": name,
        "run_dir": str(RUNS / run_name),
        "train_s": round(train_s, 1),
        "epochs_run": int(sum(1 for _ in (RUNS / run_name / "results.csv").open()) - 1),
        "precision": round(float(v.box.mp), 4),
        "recall": round(float(v.box.mr), 4),
        "mAP50": round(float(v.box.map50), 4),
        "mAP50-95": round(float(v.box.map), 4),
        "params": sum(p.numel() for p in m.model.parameters()),
    }
    print("RESULT", json.dumps(row, indent=2), flush=True)
    print("=== DONE %s (%.0fs) %s ===" % (name, train_s, time.strftime("%H:%M:%S")), flush=True)
    return row


def main():
    summary = []
    for name, wts, run_name, *yaml in EXPERIMENTS:
        yaml_path = yaml[0] if yaml else None
        row = run_one(name, wts, run_name, yaml_path)
        summary.append(row)
    out = PRJ / "yolo26_feat_concat_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print("ALL RUNS COMPLETE ->", out)


if __name__ == "__main__":
    main()
