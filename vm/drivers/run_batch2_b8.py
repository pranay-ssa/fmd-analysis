#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch driver (VM, A100): generic for the yolo_arch runs, batch 8, frozen config.

Usage:  cd /home/pranayp/yolo_ooi && python3 -u run_batch2_b8.py [run1 run2 ...]
With no run names it runs the batch-2 pair (baseline_b8, depth_plus2_deep).
Example for batch 3:  python3 -u run_batch2_b8.py armA_residual_deep armB_conv_p4
Skips any run whose results.csv already exists (safe re-run / resume).
Per run writes results.csv (ultralytics) + metrics.json into runs/yolo_arch/<name>/.
"""
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("/home/pranayp/yolo_ooi")
DATA = ROOT / "dataset_obb.yaml"
PROJ = ROOT / "runs" / "yolo_arch"
N_VAL = 88

RUNS = {
    "baseline_b8": "experiments/baseline_obb.yaml",
    "depth_plus2_deep": "experiments/depth_plus2_deep_obb.yaml",
    "armA_residual_deep": "experiments/armA_residual_deep_obb.yaml",
    "armB_conv_p4": "experiments/armB_conv_p4_obb.yaml",
}

COMMON = dict(epochs=100, patience=50, imgsz=640, batch=8, seed=42,
              lr0=0.01, optimizer="auto", workers=8, device=0,
              project=str(PROJ), val=True, exist_ok=False)


def gpu_util():
    try:
        return subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa
        return "nvidia-smi unavailable"


def model_info(m):
    out = {"params": None, "gflops": None}
    try:
        out["params"] = int(sum(p.numel() for p in m.model.parameters()))
    except Exception as e:  # noqa
        out["info_err"] = str(e)
    try:
        info = m.model.info(verbose=False)
        if isinstance(info, (list, tuple)) and len(info) >= 4:
            out["gflops"] = float(info[3])
    except Exception:  # noqa
        pass
    return out


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["baseline_b8", "depth_plus2_deep"]
    unknown = [t for t in targets if t not in RUNS]
    if unknown:
        print("UNKNOWN RUNS:", unknown, "available:", list(RUNS)); sys.exit(2)
    print("GPU util% before start:", gpu_util(), "targets:", targets, flush=True)
    for run_name in targets:
        rdir = PROJ / run_name
        if (rdir / "results.csv").exists():
            print("SKIP (results.csv exists):", run_name, flush=True)
            continue
        print("=== START %s %s ===" % (run_name, time.strftime("%Y-%m-%dT%H:%M:%S")), flush=True)
        t0 = time.time()
        m = YOLO(str(ROOT / RUNS[run_name]))
        info = model_info(m)
        print("model.info:", info, flush=True)
        m.train(data=str(DATA), name=run_name, **COMMON)
        train_s = time.time() - t0

        best = getattr(m.trainer, "best", None) or str(rdir / "weights" / "best.pt")
        rows = list(csv.DictReader(open(rdir / "results.csv")))
        best_row = max(rows, key=lambda r: float(r["metrics/mAP50(B)"]))
        f = lambda k: float(best_row[k])  # noqa
        t1 = time.time()
        bm = YOLO(str(best))
        bm.val(data=str(DATA), imgsz=640, batch=8, device=0, split="val")
        val_s = time.time() - t1

        metrics = {
            "exp": run_name, "arch": RUNS[run_name], "epochs": COMMON["epochs"],
            "imgsz": COMMON["imgsz"], "batch": COMMON["batch"], "seed": COMMON["seed"],
            "params": info.get("params"), "gflops": info.get("gflops"),
            "val_images": N_VAL, "best_epoch": float(best_row["epoch"]),
            "mAP50": f("metrics/mAP50(B)"), "mAP50_95": f("metrics/mAP50-95(B)"),
            "precision": f("metrics/precision(B)"), "recall": f("metrics/recall(B)"),
            "train_s": round(train_s, 1), "val_inf_ms": round(val_s / N_VAL * 1000.0, 2),
        }
        (rdir / "metrics.json").write_text(json.dumps(metrics, indent=1))
        print("METRICS", json.dumps(metrics, indent=1), flush=True)
        print("=== DONE %s (train %.0fs) %s ===" % (run_name, train_s,
              time.strftime("%Y-%m-%dT%H:%M:%S")), flush=True)
    print("ALL RUNS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
