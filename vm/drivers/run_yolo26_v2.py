#!/usr/bin/env python3
# YOLO26 baseline vs feat_concat_v2 (additive P3 skip)
import json, time
from pathlib import Path
from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "crop_detect_dataset" / "data.yaml"
RUNS = PRJ / "runs" / "yolo26_arch"

EXPERIMENTS = [
    ("YOLO26n Baseline", str(PRJ / "yolo26n.pt"), "yolo26n_baseline", None),
    ("YOLO26n FeatConcatV2", str(PRJ / "yolo26n.pt"), "yolo26n_feat_concat_v2",
     str(PRJ / "experiments/yolo26_feat_concat_v2.yaml")),
]

COMMON = dict(epochs=100, imgsz=1280, batch=8, device=0, patience=50, seed=42,
              project=str(RUNS), plots=False, single_cls=True, exist_ok=True,
              data=str(DATA))

def run_one(name, weights, run_name, yaml_path):
    print(f"=== START {name} {time.strftime('%Y-%m-%dT%H:%M:%S')} ===", flush=True)
    t0 = time.time()
    m = YOLO(yaml_path, task="detect") if yaml_path else YOLO(weights)
    m.train(name=run_name, **COMMON)
    train_s = time.time() - t0
    best = YOLO(str(RUNS / run_name / "weights" / "best.pt"))
    v = best.val(data=str(DATA), split="val", imgsz=1280, single_cls=True,
                 verbose=False, name=run_name + "_val")
    row = {
        "experiment": name, "run_dir": str(RUNS / run_name),
        "train_s": round(train_s, 1),
        "epochs_run": int(sum(1 for _ in (RUNS / run_name / "results.csv").open()) - 1),
        "precision": round(float(v.box.mp), 4), "recall": round(float(v.box.mr), 4),
        "mAP50": round(float(v.box.map50), 4), "mAP50-95": round(float(v.box.map), 4),
        "params": sum(p.numel() for p in m.model.parameters()),
    }
    print(f"RESULT {json.dumps(row)}", flush=True)
    print(f"=== DONE {name} ({train_s:.0f}s) ===", flush=True)
    return row

summary = []
for name, wts, run_name, y in EXPERIMENTS:
    summary.append(run_one(name, wts, run_name, y))
out = PRJ / "yolo26_feat_concat_v2_summary.json"
out.write_text(json.dumps(summary, indent=2))
print("ALL DONE ->", out)
