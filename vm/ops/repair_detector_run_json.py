#!/usr/bin/env python3
"""Repair a detector run.json whose per-class rows used the wrong summary keys.

The first Experiment 2 run wrote metrics.per_class as an error because the driver
asked for AP50/Precision/Recall while ultralytics 8.4 returns Box-P, Box-R,
Box-F1, mAP50 and mAP50-95. This re-evaluates the test split with the run's best
weights, replaces the per-class rows, and writes test_per_class.csv beside them.
It does not retrain and does not change the test split.
"""
import argparse
import csv
import json
import time
from pathlib import Path

from ultralytics import YOLO


def rows_from(val):
    rows = []
    for row in val.summary():
        rows.append({
            "class": row["Class"],
            "images": int(row["Images"]),
            "instances": int(row["Instances"]),
            "precision": round(float(row["Box-P"]), 4),
            "recall": round(float(row["Box-R"]), 4),
            "f1": round(float(row["Box-F1"]), 4),
            "AP50": round(float(row["mAP50"]), 4),
            "AP50-95": round(float(row["mAP50-95"]), 4),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    config = record["config"]
    best = run_dir / "weights" / "best.pt"

    model = YOLO(str(best))
    val = model.val(
        data=args.data,
        split="test",
        imgsz=config["imgsz"],
        batch=config["batch"],
        device=config["device"],
        verbose=False,
        plots=False,
        project=str(run_dir.parent),
        name=run_dir.name + "_recheck",
        exist_ok=True,
    )
    rows = rows_from(val)

    record["metrics"].update({
        "primary": round(float(val.box.map), 4),
        "primary_name": "mAP50-95",
        "mAP50": round(float(val.box.map50), 4),
        "mAP50-95": round(float(val.box.map), 4),
        "precision": round(float(val.box.mp), 4),
        "recall": round(float(val.box.mr), 4),
        "per_class": rows,
        "per_class_source": "test split, best.pt, ultralytics summary()",
    })
    record["metrics_repaired_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    tmp = run_dir / "run.json.tmp"
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    tmp.replace(run_dir / "run.json")

    csv_path = run_dir / "test_per_class.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "class", "images", "instances", "precision", "recall", "f1",
            "AP50", "AP50-95",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print("REPAIRED", run_dir / "run.json")
    print("CSV", csv_path)
    print(json.dumps(record["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
