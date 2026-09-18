#!/usr/bin/env python3
"""H2 / mc_processed_p3: processed early-layer features into the mid stage (multiclass arena).

Control and fork run in the SAME session with the SAME initialisation, so the only
difference is the fork's single edit group (one added tap, processed by a C3k2 block
before it joins the P4 stage). This is the clean form of the lead's feature idea, and the
half of the question that R1 (raw tap, single-class crops, -0.0560 mAP50) left open.

Arena: dataset_multiclass, 10 classes, batch 8, 100 epochs, imgsz 1280, seed 42.
Baseline to beat: mAP50 0.5355 / mAP50-95 0.3211 (stock yolo26n, verified clean).

Gate first (not optional):
  python3 preflight_fork.py experiments/yolo26/yolo26_mc_processed_p3.yaml \\
      && python3 -u run_yolo26_mc_processed_p3.py --smoke \\
      && python3 -u run_yolo26_mc_processed_p3.py

Stdlib only (no pandas on this VM). Writes runs/yolo26_mc_arch/<name>/ and
mc_processed_p3_summary.json, including per-class AP50 and P/R.
"""
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

from ultralytics import YOLO

PRJ = Path("/home/pranayp/yolo_ooi")
DATA = PRJ / "dataset_multiclass" / "data.yaml"
RUNS = PRJ / "runs" / "yolo26_mc_arch"
FORK = PRJ / "experiments" / "yolo26" / "yolo26_mc_processed_p3.yaml"

COMMON = dict(epochs=100, imgsz=1280, batch=8, device=0, patience=50, seed=42,
              project=str(RUNS), plots=False, exist_ok=False, data=str(DATA))

# (label, run name, yaml path or None, load pretrained weights into the built model?)
EXPERIMENTS = [
    ("MC Control (stock yolo26n, pretrained)", "mc_control_stock", None, False),
    ("MC Fork (processed P3 tap, pretrained)", "mc_fork_p3proc", str(FORK), True),
]


def md5(p):
    p = Path(p)
    return hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None


def read_results(run_dir):
    with (run_dir / "results.csv").open(newline="") as fh:
        return list(csv.DictReader(fh))


def first_epoch_lr(rows):
    if not rows:
        return None
    key = next((k for k in rows[0] if k.strip() == "lr/pg0"), None)
    return float(rows[0][key].strip()) if key else None


def build(label, yaml_path, load_pretrained):
    """Build exactly as the run will. The head is wrapper.model.model[-1]."""
    if yaml_path:
        model = YOLO(yaml_path, task="detect", verbose=False)
        if load_pretrained:
            model.load(str(PRJ / "yolo26n.pt"))  # MATCHED INIT
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


def per_class(v):
    """Per-class AP50 and P/R via v.summary(); fall back to v.ap50 when keys differ."""
    rows = []
    try:
        for r in v.summary():
            keys = r.keys()
            name = r.get("Class")
            ap50 = r.get("AP50", r.get("mAP50"))
            rows.append({
                "class": name,
                "AP50": round(float(ap50), 4) if ap50 is not None else None,
                "AP50_95": round(float(r.get("AP50-95", r.get("mAP50-95", 0.0))), 4),
                "precision": round(float(r.get("Precision", r.get("Box-P", 0.0))), 4),
                "recall": round(float(r.get("Recall", r.get("Box-R", 0.0))), 4),
            })
            print(f"   {name:>20}  AP50={rows[-1]['AP50']}  P={rows[-1]['precision']}  R={rows[-1]['recall']}",
                  flush=True)
        return rows
    except Exception as exc:  # noqa: BLE001
        print(f"   v.summary() unavailable ({exc}); falling back to v.ap50", flush=True)
        if getattr(v, "ap50", None) is not None:
            for name, ap in zip(v.names, v.ap50):
                rows.append({"class": name, "AP50": round(float(ap), 4)})
        return rows


def run_one(label, run_name, yaml_path, load_pretrained):
    print("\n" + "=" * 72 + f"\n TRAIN  {label}\n" + "=" * 72, flush=True)
    t0 = time.time()
    model, facts = build(label, yaml_path, load_pretrained)
    model.train(name=run_name, **COMMON)
    train_s = time.time() - t0
    run_dir = RUNS / run_name
    rows = read_results(run_dir)

    print(f"\n VAL    {label}", flush=True)
    best = YOLO(str(run_dir / "weights" / "best.pt"))
    v = best.val(data=str(DATA), split="val", imgsz=1280, verbose=False,
                 name=run_name + "_val")
    classes = per_class(v)
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
        "params_before_train": facts["params"],
        "head_children_best_ckpt": sorted(dict(best_head.named_children())),
        "head_reg_max_best_ckpt": getattr(best_head, "reg_max", None),
        "lr_first_epoch_actual": first_epoch_lr(rows),
        "init": "pretrained yolo26n.pt" + (" loaded into the fork yaml" if yaml_path else ""),
        "yaml_md5": md5(yaml_path) if yaml_path else None,
        "per_class": classes,
    }
    print("RESULT " + json.dumps(row, indent=2), flush=True)
    return row


def main():
    if "--smoke" in sys.argv:
        for label, _run, yaml_path, load_pretrained in EXPERIMENTS:
            build(label, yaml_path, load_pretrained)
        print("\nSMOKE OK: both models build, no training launched.", flush=True)
        return

    summary = []
    for label, run_name, yaml_path, load_pretrained in EXPERIMENTS:
        summary.append(run_one(label, run_name, yaml_path, load_pretrained))

    out = PRJ / "mc_processed_p3_summary.json"
    out.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 72)
    print(" H2: PROCESSED EARLY-LAYER FEATURES, MULTICLASS ARENA")
    print("=" * 72)
    for r in summary:
        print(f" {r['experiment']:<44} mAP50={r['mAP50']:.4f} mAP50-95={r['mAP50-95']:.4f} "
              f"P={r['precision']:.4f} R={r['recall']:.4f} params={r['params_before_train']}")
    if len(summary) == 2:
        print(f"\n fork - control: mAP50 {summary[1]['mAP50'] - summary[0]['mAP50']:+.4f}   "
              f"mAP50-95 {summary[1]['mAP50-95'] - summary[0]['mAP50-95']:+.4f}")
        ctrl = {c["class"]: c["AP50"] for c in summary[0]["per_class"]}
        fork = {c["class"]: c["AP50"] for c in summary[1]["per_class"]}
        print("\n per-class AP50 (control -> fork, delta):")
        for k in ctrl:
            if k in fork and ctrl[k] is not None and fork[k] is not None:
                print(f"   {k:>20}  {ctrl[k]:.4f} -> {fork[k]:.4f}  ({fork[k] - ctrl[k]:+.4f})")
    print(f"\n saved -> {out}")


if __name__ == "__main__":
    main()
