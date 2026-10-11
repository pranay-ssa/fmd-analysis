#!/usr/bin/env python3
"""Standalone launcher for the ml_resnet50_posw run (pos-weight imbalance lever).

Runs the SAME recipe as ml_resnet50_base (2026-09-28) with ONE switch turned on:
--pos-weight, i.e. per-class BCE pos_weight computed from the train split inside
train.py. Nothing else changes: same arch (plain ResNet50), same labels.csv,
same two-way 80/20 split (split_named), same seed, optimizer, epochs, batch.

The original train.py is not modified: this driver calls it as a module and adds
only (a) a fixed expected pos_weight vector asserted before training and
(b) a run manifest written next to the outputs. It also copies its own source
into the run dir so the exact driver that ran is preserved.

Data provenance note (2026-10-05 client ruling): the 33 Fiber/Extraneous-Polymer
pictures are decision-stage defect classes, not lens-presentation tags. Verified
2026-09-24 (relabel_impact_20260924.txt): 0 of the contested pictures sit in the
3,377 LP rows, so this ruling changes no label this run trains on.

Usage (VM, /home/pranayp/yolo_ooi/multilabel_lp_posw_20261005):
    python3 -u run_ml_posw.py --smoke       # 2 steps on real images first
    python3 -u run_ml_posw.py               # full run
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAGS = ["P1_COC", "P1_FL", "P1_ML", "P1_MPP", "P1_NL"]
# Computed from train split (n=2700): pos_weight = (n - pos) / pos.
# P1_COC pos=146, P1_FL pos=142, P1_ML pos=1153, P1_MPP pos=1141, P1_NL pos=260.
EXPECTED_POS_WEIGHT = [17.4932, 18.0141, 1.3417, 1.3663, 9.3846]
LABELS = HERE / "labels.csv"
SPLIT = HERE / "splits" / "variant_80_20_two_way.csv"


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify_split_unchanged():
    """The split file must be byte-identical to the one the base run used."""
    import json as _json
    meta = _json.loads((SPLIT.parent / "variant_80_20_two_way.meta.json").read_text())
    print("split meta:", {k: meta[k] for k in list(meta)[:6]})
    # exact row counts as a hard gate
    with open(SPLIT, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    counts = {}
    for r in rows:
        counts[r["split_named"]] = counts.get(r["split_named"], 0) + 1
    if counts.get("train") != 2700 or counts.get("test") != 677:
        raise SystemExit("GATE FAIL: split counts changed: %s" % counts)
    print("split gate OK: train=2700 test=677")
    return counts


def verify_train_labels():
    """Recompute the pos_weight vector from the train split locally before launch."""
    labels = {}
    with open(LABELS, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            labels[r["image_path"]] = r
    try:
        import numpy as np
    except ImportError:
        # stdlib fallback, same arithmetic
        y = []
        with open(SPLIT, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["split_named"] == "train":
                    y.append([int(labels[r["image_path"]][t]) for t in TAGS])
        n = len(y)
        pos = [sum(row[j] for row in y) for j in range(len(TAGS))]
        pw = [(n - p) / max(p, 1) for p in pos]
    else:
        y = []
        with open(SPLIT, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["split_named"] == "train":
                    y.append([int(labels[r["image_path"]][t]) for t in TAGS])
        arr = np.array(y, dtype=np.int64)
        n = len(arr)
        pos = arr.sum(axis=0)
        pw = ((n - pos) / np.maximum(pos, 1)).round(4).tolist()
    diffs = [(t, a, b) for t, a, b in zip(TAGS, pw, EXPECTED_POS_WEIGHT) if abs(a - b) > 0.01]
    if diffs:
        raise SystemExit("GATE FAIL: pos_weight drifted from spec: %s" % diffs)
    print("pos_weight gate OK: n=%d pos=%s pw=%s" % (n, pos, [round(v, 4) for v in pw]))
    return {"n_train": int(n), "pos": [int(v) for v in pos],
            "pos_weight": [round(float(v), 4) for v in pw]}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image-root", default="/home/amd100-user/FMD_Data_26082026/fmd_temp_images")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--smoke", action="store_true",
                    help="pass through to train.py --smoke (2 steps, real images)")
    ap.add_argument("--train-module", default=str(HERE / "train.py"),
                    help="path to the untouched train.py this driver calls")
    args = ap.parse_args()

    out_dir = HERE / "runs" / "ml_resnet50_posw_20261005"
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = verify_split_unchanged()
    pw_check = verify_train_labels()

    cmd = [
        sys.executable, "-u", args.train_module,
        "--labels", str(LABELS),
        "--split", str(SPLIT),
        "--split-column", "split_named",
        "--image-root", args.image_root,
        "--out", str(out_dir),
        "--arch", "resnet50",
        "--epochs", str(args.epochs),
        "--batch", str(args.batch),
        "--workers", str(args.workers),
        "--optimizer", "sgd", "--lr", "1e-4", "--momentum", "0.9", "--weight-decay", "1e-4",
        "--seed", str(args.seed),
        "--pos-weight",
    ]
    if args.smoke:
        cmd.append("--smoke")

    manifest = {
        "run_id": "ml_resnet50_posw",
        "run_date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "driver": Path(__file__).name,
        "driver_md5": md5(__file__),
        "train_py_md5": md5(args.train_module),
        "labels_md5": md5(LABELS),
        "split_md5": md5(SPLIT),
        "split_counts": counts,
        "pos_weight_check": pw_check,
        "expected_pos_weight": EXPECTED_POS_WEIGHT,
        "config_overrides_vs_base": {"pos_weight": True},
        "command": cmd,
        "smoke": args.smoke,
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    # preserve the exact driver source next to the outputs
    shutil.copy2(__file__, out_dir / Path(__file__).name)

    print("command:", " ".join(cmd))
    t0 = time.time()
    rc = subprocess.call(cmd)
    manifest["exit_code"] = rc
    manifest["wall_seconds"] = round(time.time() - t0, 1)
    manifest["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("exit_code=%d wall=%.1fs" % (rc, manifest["wall_seconds"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
