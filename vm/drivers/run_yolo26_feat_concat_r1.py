#!/usr/bin/env python3
"""R1: attributable feature-concat test on the crop pipeline (single-class, batch 8).

Control and fork are trained in the SAME run, with the SAME initialisation (both start from
pretrained yolo26n.pt) and the SAME hyperparameters, so the only difference is the fork's
single added tap. This is the comparison the 2026-09-10 V1/V2 runs failed to provide:

  V1 (2026-09-10)  no head edit at all, built from scratch, stock keys dropped
  V2 (2026-09-10)  added raw upsampled P5 (not P3), built from scratch, stock keys dropped
  R1  (this file)  stock yolo26.yaml + one raw backbone-P3 tap into the P4 stage,
                   pretrained init through .load() for the fork, pretrained control

Gate first (not optional):
  python3 preflight_fork.py experiments/yolo26/yolo26_feat_concat_r1.yaml \\
      && python3 -u run_yolo26_feat_concat_r1.py

Writes runs/yolo26_arch_r1/<name>/ and r1_feat_concat_summary.json (with the effective
first-epoch lr, init source and yaml md5 recorded per run).

Stdlib only: no pandas on this VM (a pandas-based driver copied from another harness dies
immediately; results.csv is read with the csv module instead).
"""
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "crop_detect_dataset" / "data.yaml"
RUNS = PRJ / "runs" / "yolo26_arch_r1"
FORK = PRJ / "experiments" / "yolo26" / "yolo26_feat_concat_r1.yaml"

COMMON = dict(epochs=100, imgsz=1280, batch=8, device=0, patience=50, seed=42,
              project=str(RUNS), plots=False, single_cls=True, exist_ok=False,
              data=str(DATA))

# (label, run name, yaml path or None, load pretrained weights into the built model?)
EXPERIMENTS = [
    ("R1 Control (stock yolo26n, pretrained)", "r1_control_stock", None, False),
    ("R1 Fork (one raw P3 tap, pretrained)", "r1_fork_p3tap", str(FORK), True),
]


def md5(p):
    p = Path(p)
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None


def read_results(run_dir):
    """Return the parsed rows of results.csv as a list of dicts (stdlib csv)."""
    with (run_dir / "results.csv").open(newline="") as fh:
        return list(csv.DictReader(fh))


def first_epoch_lr(rows):
    """The lr the trainer actually used in epoch 1 (not the requested one)."""
    if not rows:
        return None
    key = next((k for k in rows[0] if k.strip() == "lr/pg0"), None)
    return float(rows[0][key].strip()) if key else None


def build(label, yaml_path, load_pretrained):
    """Build the model exactly as the run will, and report its identity.

    YOLO(...) is the trainer wrapper; the network is wrapper.model (DetectionModel) and the
    module list is wrapper.model.model, so the head is wrapper.model.model[-1].
    """
    if yaml_path:
        model = YOLO(yaml_path, task="detect", verbose=False)
        if load_pretrained:
            model.load(str(PRJ / "yolo26n.pt"))  # MATCHED INIT: same starting point as the control
    else:
        model = YOLO(str(PRJ / "yolo26n.pt"))
    net = model.model
    head = net.model[-1]
    facts = {
        "params": sum(p.numel() for p in net.parameters()),
        "reg_max": getattr(head, "reg_max", None),
        "end2end": getattr(head, "end2end", None),
        "head_children": sorted(dict(head.named_children())),
        "n_layers": len(net.model),
    }
    print(f" built [{label}]: params={facts['params']} reg_max={facts['reg_max']} "
          f"end2end={facts['end2end']} head={facts['head_children']} layers={facts['n_layers']}",
          flush=True)
    return model, facts


def run_one(label, run_name, yaml_path, load_pretrained):
    print("\n" + "=" * 72 + f"\n TRAIN  {label}\n" + "=" * 72, flush=True)
    t0 = time.time()
    model, facts = build(label, yaml_path, load_pretrained)
    params = facts["params"]

    model.train(name=run_name, **COMMON)
    train_s = time.time() - t0
    run_dir = RUNS / run_name
    rows = read_results(run_dir)

    best = YOLO(str(run_dir / "weights" / "best.pt"))
    v = best.val(data=str(DATA), split="val", imgsz=1280, single_cls=True,
                 verbose=False, name=run_name + "_val")
    best_head = best.model.model[-1]
    row = {
        "experiment": label,
        "run_dir": str(run_dir),
        "train_s": round(train_s, 1),
        "epochs_run": len(rows),
        "precision": round(float(v.box.mp), 4),
        "recall": round(float(v.box.mr), 4),
        "mAP50": round(float(v.box.map50), 4),
        "mAP50-95": round(float(v.box.map), 4),
        "params_before_train": params,
        "params_best_ckpt": sum(p.numel() for p in best.model.parameters()),
        "head_children_best_ckpt": sorted(dict(best_head.named_children())),
        "head_reg_max_best_ckpt": getattr(best_head, "reg_max", None),
        "lr_first_epoch_actual": first_epoch_lr(rows),
        "init": "pretrained yolo26n.pt" + (" loaded into the fork yaml" if yaml_path else ""),
        "yaml_md5": md5(yaml_path) if yaml_path else None,
    }
    print("RESULT " + json.dumps(row, indent=2), flush=True)
    return row


def main():
    smoke = "--smoke" in sys.argv
    summary = []
    for label, run_name, yaml_path, load_pretrained in EXPERIMENTS:
        if smoke:
            build(label, yaml_path, load_pretrained)
            continue
        summary.append(run_one(label, run_name, yaml_path, load_pretrained))

    if smoke:
        print("\nSMOKE OK: both models build, no training launched.", flush=True)
        return

    out = PRJ / "r1_feat_concat_summary.json"
    out.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 72)
    print(" R1: ATTRIBUTABLE FEATURE-CONCAT TEST (single-class crops, batch 8)")
    print("=" * 72)
    hdr = f"{'experiment':<44}{'mAP50':>8}{'mAP50-95':>10}{'P':>8}{'R':>8}{'params':>10}{'ep':>5}{'lr_ep1':>10}"
    print(hdr)
    for r in summary:
        print(f"{r['experiment']:<44}{r['mAP50']:>8.4f}{r['mAP50-95']:>10.4f}{r['precision']:>8.4f}"
              f"{r['recall']:>8.4f}{r['params_before_train']:>10}{r['epochs_run']:>5}"
              f"{str(r['lr_first_epoch_actual']):>10}")
    if len(summary) == 2:
        print(f"\n fork - control: mAP50 {summary[1]['mAP50'] - summary[0]['mAP50']:+.4f}   "
              f"mAP50-95 {summary[1]['mAP50-95'] - summary[0]['mAP50-95']:+.4f}")
    print(f"\n saved -> {out}")


if __name__ == "__main__":
    main()
