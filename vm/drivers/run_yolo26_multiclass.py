#!/usr/bin/env python3
"""Train YOLO26n multiclass baseline on crop OoI dataset."""
import json, time
from pathlib import Path
from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "dataset_multiclass" / "data.yaml"
RUNS = PRJ / "runs" / "yolo26_multiclass"

EXPERIMENTS = [
    ("YOLO26n MC Baseline", str(PRJ / "yolo26n.pt"), "yolo26n_mc_baseline", None),
]

COMMON = dict(epochs=100, imgsz=1280, batch=8, device=0, patience=50, seed=42,
              project=str(RUNS), plots=True, exist_ok=True, data=str(DATA))

def run_one(name, weights, run_name, yaml_path):
    print(f"=== START {name} {time.strftime('%Y-%m-%dT%H:%M:%S')} ===", flush=True)
    t0 = time.time()
    m = YOLO(yaml_path, task="detect") if yaml_path else YOLO(weights)
    m.train(name=run_name, **COMMON)
    train_s = time.time() - t0
    best = YOLO(str(RUNS / run_name / "weights" / "best.pt"))
    v = best.val(data=str(DATA), split="val", imgsz=1280, verbose=False, name=run_name+"_val")
    # Per-class AP50 + P/R. v.ap50 can come back empty on this build; v.summary() is the working
    # path (see vm/drivers/per_class_simple.py), so use it and keep the v.ap50 fallback.
    per_class = []
    try:
        for row in v.summary():
            per_class.append({
                "class": row["Class"],
                "AP50": round(float(row["AP50"]), 4),
                "AP50_95": round(float(row["AP50-95"]), 4),
                "precision": round(float(row["Precision"]), 4),
                "recall": round(float(row["Recall"]), 4),
            })
            print(f"  {row['Class']:30s}  AP50={row['AP50']:.4f}  P={row['Precision']:.4f}  R={row['Recall']:.4f}")
    except Exception as exc:  # noqa: BLE001
        print(f"  v.summary() unavailable ({exc}); falling back to v.ap50")
    if not per_class and getattr(v, "ap50", None) is not None:
        for cname, cap in zip(v.names, v.ap50):
            per_class.append({"class": cname, "AP50": round(float(cap), 4)})
            print(f"  {cname:30s}  AP50={cap:.4f}")
    row = {
        "experiment": name, "run_dir": str(RUNS / run_name),
        "train_s": round(train_s, 1),
        "epochs_run": int(sum(1 for _ in (RUNS / run_name / "results.csv").open()) - 1),
        "precision": round(float(v.box.mp), 4), "recall": round(float(v.box.mr), 4),
        "mAP50": round(float(v.box.map50), 4), "mAP50-95": round(float(v.box.map), 4),
        "params": sum(p.numel() for p in m.model.parameters()),
        "per_class_ap50": per_class,
    }
    print(f"RESULT {json.dumps(row)}", flush=True)
    print(f"=== DONE {name} ({train_s:.0f}s) ===", flush=True)
    return row

summary = []
for name, wts, run_name, y in EXPERIMENTS:
    summary.append(run_one(name, wts, run_name, y))
out = PRJ / "yolo26_mc_summary.json"
out.write_text(json.dumps(summary, indent=2))
print("ALL DONE ->", out)
