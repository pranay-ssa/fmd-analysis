#!/usr/bin/env python3
"""Train YOLO26n on the multi-label pictures, at the usual settings, and report.

Usual settings are taken from vm/drivers/run_yolo26_multiclass.py: 100 epochs, imgsz 1280, batch 8,
patience 50, seed 42. Two tests, one variable between them: the split.

  test 1  the 47 pictures split by picture, 34 train against 13 test  (the asked-for run)
  test 2  every picture from line 25 held out, train on the other lines (does the score survive
          a group the model has never seen)

Each test is also scored on the existing 88-picture test set, for a common yardstick, with the
caveat that most of that set belongs to classes this training never saw.

Writes  runs/multilabel_test/         one folder per test, plus the training log
        multilabel_test_summary.json  every number, straight from the run
"""
import json
import time
from pathlib import Path

from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
WEIGHTS = str(PRJ / "yolo26n.pt")
FULL_SET_TEST = str(PRJ / "dataset_multiclass" / "data.yaml")
RUNS = PRJ / "runs" / "multilabel_test"
COMMON = dict(epochs=100, imgsz=1280, batch=8, device=0, patience=50, seed=42,
              project=str(RUNS), plots=True, exist_ok=True)

TESTS = [("test 1 split by picture", PRJ / "dataset_test_picture_split" / "data.yaml",
          "test1_split_by_picture"),
         ("test 2 line 25 held out", PRJ / "dataset_test_line_split" / "data.yaml",
          "test2_line_25_held_out")]


def pick(row, *keys):
    """Read a field under whichever name this ultralytics build uses."""
    for k in keys:
        if k in row:
            return row[k]
    return None


def summarise(v):
    per_class = []
    try:
        for row in v.summary():
            per_class.append({"class": row["Class"],
                              "pictures": int(pick(row, "Images") or 0),
                              "defects": int(pick(row, "Instances") or 0),
                              "precision": round(float(pick(row, "Box-P", "Precision")), 4),
                              "recall": round(float(pick(row, "Box-R", "Recall")), 4),
                              "mAP50": round(float(pick(row, "mAP50", "AP50")), 4),
                              "mAP50-95": round(float(pick(row, "mAP50-95", "AP50-95")), 4)})
    except Exception as exc:  # noqa: BLE001
        print("   per-class table unavailable:", exc)
    return per_class


summary = []
for name, yaml_path, run_name in TESTS:
    print("=== START %s %s ===" % (name, time.strftime("%H:%M:%S")), flush=True)
    t0 = time.time()
    model = YOLO(WEIGHTS)
    model.train(data=str(yaml_path), name=run_name, **COMMON)
    train_s = time.time() - t0
    best = YOLO(str(RUNS / run_name / "weights" / "best.pt"))
    own = best.val(data=str(yaml_path), split="val", imgsz=1280, verbose=False,
                   name=run_name + "_own_test_set")
    whole = best.val(data=FULL_SET_TEST, split="val", imgsz=1280, verbose=False,
                     name=run_name + "_full_test_set")
    row = {
        "test": name, "run_dir": str(RUNS / run_name), "train_s": round(train_s, 1),
        "epochs_run": int(sum(1 for _ in (RUNS / run_name / "results.csv").open()) - 1),
        "own_test_set": {
            "pictures": len(list((Path(str(yaml_path)).parent / "labels" / "val").glob("*.txt"))),
            "precision": round(float(own.box.mp), 4), "recall": round(float(own.box.mr), 4),
            "mAP50": round(float(own.box.map50), 4), "mAP50-95": round(float(own.box.map), 4),
            "per_class": summarise(own)},
        "full_test_set": {
            "pictures": 88,
            "precision": round(float(whole.box.mp), 4), "recall": round(float(whole.box.mr), 4),
            "mAP50": round(float(whole.box.map50), 4), "mAP50-95": round(float(whole.box.map), 4),
            "per_class": summarise(whole)},
        "params": sum(p.numel() for p in model.model.parameters()),
    }
    print("RESULT " + json.dumps({k: v for k, v in row.items() if k not in ("own_test_set", "full_test_set")}), flush=True)
    print("   own test set : %s" % json.dumps({k: v for k, v in row["own_test_set"].items()
                                               if k != "per_class"}))
    for pc in row["own_test_set"]["per_class"]:
        print("      %-20s pictures=%-4s defects=%-4s mAP50=%-7s P=%-7s R=%s"
              % (pc["class"], pc["pictures"], pc["defects"], pc["mAP50"], pc["precision"], pc["recall"]))
    print("   full 88 set  : %s" % json.dumps({k: v for k, v in row["full_test_set"].items()
                                               if k != "per_class"}))
    summary.append(row)

out = PRJ / "multilabel_test_summary.json"
out.write_text(json.dumps(summary, indent=2))
print("ALL DONE ->", out, flush=True)
