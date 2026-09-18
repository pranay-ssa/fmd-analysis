#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduce the teammate's stock-detection bbox protocol on OUR cropped OoI set.

YOLO11n and YOLO26n, class-agnostic (single_cls=True), 100 epochs, batch 16, seed 42,
imgsz 1280, patience 30 - on crop_detect_dataset (our 434 single-size crops,
frozen 346/88 split, axis-aligned boxes).

Two LR regimes to match the teammate's reference script (run_bbox_experiments.py):
  - Auto LR  (optimizer=auto, lr0=0.01, default decay)
  - Fixed LR (optimizer=AdamW, lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0)  [their exact knobs]

Usage:
  cd /home/pranayp/yolo_ooi
  python3 -u run_crop_repro.py              # run ALL 4 experiments
  python3 -u run_crop_repro.py auto         # run auto-LR only (2 runs)
  python3 -u run_crop_repro.py fixed        # run fixed-LR only (2 runs)

Writes:
  runs/crop_repro/<run_name>/               # per-run outputs
  crop_repro_summary.json                   # auto-LR results (backward compat)
  crop_repro_summary_fixedlr.json           # fixed-LR results
  crop_repro_summary_all.json               # combined 4-run summary
"""
import json
import sys
import time
from pathlib import Path

from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "crop_detect_dataset" / "data.yaml"
RUNS = PRJ / "runs" / "crop_repro"

# --- Experiment definitions ---------------------------------------------------
# (display_name, weights_path, run_dir_name, lr_overrides)

AUTO_LR = {}  # default Ultralytics LR schedule (optimizer=auto)
# Fixed-LR arm, mirroring the reference script's knobs exactly
#   (teammate: YOLO26_ICube_Defects/run_bbox_experiments.py ->
#    dict(optimizer="AdamW", lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0))
# CRITICAL: optimizer MUST be passed explicitly. With optimizer="auto" the trainer ignores lr0
# entirely ("ignoring 'lr0=...'"), which silently invalidated the 2026-09-10 fixed-LR arm.
FIXED_LR = dict(optimizer="AdamW", lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0)

EXPERIMENTS = [
    ("YOLO11n Auto LR",  str(PRJ / "yolo11n.pt"), "yolo11n_crop_bbox",       AUTO_LR),
    ("YOLO26n Auto LR",  str(PRJ / "yolo26n.pt"), "yolo26n_crop_bbox",       AUTO_LR),
    # R2 arms: corrected flat-1e-4 runs. New run dirs on purpose so the invalidated
    # 2026-09-10 arms stay on disk as the audit trail (DOC_CORRECTIONS_20260911.md cites them).
    ("YOLO11n Fixed LR (flat 1e-4)", str(PRJ / "yolo11n.pt"), "yolo11n_crop_bbox_fixedlr_flat", FIXED_LR),
    ("YOLO26n Fixed LR (flat 1e-4)", str(PRJ / "yolo26n.pt"), "yolo26n_crop_bbox_fixedlr_flat", FIXED_LR),
]

COMMON = dict(epochs=100, imgsz=1280, batch=16, device=0, patience=30, seed=42,
              project=str(RUNS), plots=False, single_cls=True, exist_ok=False)


def run_one(name, wts, run_name, lr_overrides):
    """Train + val one experiment. Returns result dict."""
    print("=== START %s %s ===" % (name, time.strftime("%Y-%m-%dT%H:%M:%S")), flush=True)
    t0 = time.time()
    m = YOLO(wts)
    m.train(name=run_name, data=str(DATA), **COMMON, **lr_overrides)
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
        "lr_mode": "auto" if not lr_overrides else "fixed_1e-4",
    }
    print("RESULT", json.dumps(row, indent=2), flush=True)
    print("=== DONE %s (%.0fs) %s ===" % (name, train_s, time.strftime("%H:%M:%S")), flush=True)
    return row


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "auto":
        subset = [e for e in EXPERIMENTS if "Auto" in e[0]]
    elif mode == "fixed":
        subset = [e for e in EXPERIMENTS if "Fixed" in e[0]]
    else:
        subset = EXPERIMENTS

    summary = []
    for name, wts, run_name, lr_ovr in subset:
        row = run_one(name, wts, run_name, lr_ovr)
        summary.append(row)

    # Write summary file(s) based on what was run. Fixed mode gets a distinct name so the
    # invalidated 2026-09-10 arm (crop_repro_summary_fixedlr.json) is never overwritten.
    if mode == "fixed":
        out = PRJ / "crop_repro_summary_fixedlr_flat.json"
    elif mode == "auto":
        out = PRJ / "crop_repro_summary.json"
    else:
        out = PRJ / "crop_repro_summary_all.json"
        # Also write individual files for backward compat
        auto_rows = [r for r in summary if r["lr_mode"] == "auto"]
        fixed_rows = [r for r in summary if r["lr_mode"] == "fixed_1e-4"]
        if auto_rows:
            (PRJ / "crop_repro_summary.json").write_text(json.dumps(auto_rows, indent=2))
        if fixed_rows:
            (PRJ / "crop_repro_summary_fixedlr.json").write_text(json.dumps(fixed_rows, indent=2))

    out.write_text(json.dumps(summary, indent=2))
    print("ALL RUNS COMPLETE ->", out)


if __name__ == "__main__":
    main()
