#!/usr/bin/env python3
"""Train YOLO26n on the Experiment 2 seven-class detector dataset.

One arm per invocation. Run on the VM as pranayp:

    sudo -u pranayp -H /usr/bin/python3.12 vm/drivers/run_yolo26_fmd_detector.py \
        --data /data/.../data_all.yaml --name yolo26n_fmd_7cls_all

Writes run.json beside that arm's artifacts. A crash still writes run.json with
status crashed and the traceback path.
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from ultralytics import YOLO

RUN_ROOT = Path("/home/pranayp/fmd-analysis/run/detector_20261110")
WEIGHTS = Path("/home/pranayp/yolo_ooi/yolo26n.pt")
DEFAULT_DATA = "/data/FMD_Data_26082026/fmd_detector_20261110/data_all.yaml"
DEFAULT_NAME = "yolo26n_fmd_7cls_all"

BASE_CONFIG = {
    "epochs": 100,
    "imgsz": 1280,
    "batch": 8,
    "device": 0,
    "patience": 50,
    "seed": 42,
    "optimizer": "auto",
    "workers": 8,
    "project": str(RUN_ROOT),
    "exist_ok": True,
    "plots": True,
}


def per_class_rows(val):
    rows = []
    try:
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
    except Exception as exc:  # noqa: BLE001
        rows.append({"error": f"summary unavailable: {exc}"})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DEFAULT_DATA)
    parser.add_argument("--name", default=DEFAULT_NAME)
    args = parser.parse_args()

    data = Path(args.data)
    name = args.name
    arm = RUN_ROOT / name
    arm.mkdir(parents=True, exist_ok=True)

    config = dict(BASE_CONFIG, data=str(data), name=name)
    record = {
        "run": name,
        "data": str(data),
        "weights": str(WEIGHTS),
        "config": {k: v for k, v in config.items() if k not in ("project", "name")},
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    started = time.time()
    try:
        model = YOLO(str(WEIGHTS) if WEIGHTS.is_file() else "yolo26n.pt")
        model.train(**config)
        best_path = arm / "weights" / "best.pt"
        best = YOLO(str(best_path))
        val = best.val(
            data=str(data),
            split="test",
            imgsz=config["imgsz"],
            batch=config["batch"],
            device=config["device"],
            verbose=False,
            project=str(RUN_ROOT),
            name=name + "_test",
            exist_ok=True,
        )
        record.update({
            "status": "ok",
            "metrics": {
                "primary": round(float(val.box.map), 4),
                "primary_name": "mAP50-95",
                "mAP50": round(float(val.box.map50), 4),
                "mAP50-95": round(float(val.box.map), 4),
                "precision": round(float(val.box.mp), 4),
                "recall": round(float(val.box.mr), 4),
                "per_class": per_class_rows(val),
            },
            "train_s": round(time.time() - started, 1),
            "best_weights": str(best_path),
            "test_dir": str(RUN_ROOT / (name + "_test")),
        })
    except Exception:  # noqa: BLE001
        tb_path = arm / "traceback.txt"
        tb_path.write_text(traceback.format_exc(), encoding="utf-8")
        record.update({
            "status": "crashed",
            "train_s": round(time.time() - started, 1),
            "notes": f"traceback written to {tb_path}",
        })
        (arm / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print("RESULT " + json.dumps(record), flush=True)
        return 1

    (arm / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("RESULT " + json.dumps(record), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
