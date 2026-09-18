"""Aggregate batch-1 YOLO-OBB results into one comparison.

Reads each run dir's results.csv, finds the best epoch (max mAP50), and
emits a summary table plus JSON.  Mirrors the per-run metrics.json that
run_batch1.py does not write (only Ultralytics' results.csv is produced).

Usage:
    python src/yolo_ooi/collect_batch_results.py \
        --runs-dir runs/yolo11/yolo_arch \
        --out runs/yolo11/batch1_summary.json
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

# param/GFLOPs known from CPU YOLO().info() validation (spec Entry 6).
KNOWN = {
    "baseline_obb":         {"params": 2655673, "gflops": 6.6, "arch": "yolo11n-obb (unmodified)"},
    "yolo11s-obb":          {"params": 9744931, "gflops": 22.8, "arch": "yolo11s scale"},
    "scale_wider_only_obb": {"params": 21327571, "gflops": 48.7, "arch": "n-topology, depth .50 width .75"},
    "attention_backbone_obb": {"params": 3174851, "gflops": 8.7, "arch": "C3k2->C2PSA rows 6,8"},
    "sppf_cspc_obb":        {"params": 2655673, "gflops": 6.6, "arch": "SPPF kernel 5->7"},
}


def summarize(run_dir: Path):
    """Return dict of best-epoch + final metrics from results.csv."""
    csvp = run_dir / "results.csv"
    rows = list(csv.DictReader(csvp.open()))
    if not rows:
        return None
    best = max(rows, key=lambda r: float(r["metrics/mAP50(B)"]))
    last = rows[-1]
    n = len(rows)
    # total train time = last epoch cumulative time (seconds)
    return {
        "best_epoch": int(best["epoch"]),
        "mAP50": float(best["metrics/mAP50(B)"]),
        "mAP50_95": float(best["metrics/mAP50-95(B)"]),
        "precision": float(best["metrics/precision(B)"]),
        "recall": float(best["metrics/recall(B)"]),
        "n_epochs": n,
        "final_mAP50": float(last["metrics/mAP50(B)"]),
        "final_time_s": float(last["time"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs_dir = Path(args.runs_dir)
    out = []
    for sub in sorted(runs_dir.iterdir()):
        if not sub.is_dir():
            continue
        if not (sub / "results.csv").exists():
            continue
        name = sub.name
        s = summarize(sub)
        if s is None:
            print(f"{name}: no results.csv rows")
            continue
        info = KNOWN.get(name, {})
        row = {"exp": name, **info, **s}
        out.append(row)
        print(f"{name:26s} best_ep={row['best_epoch']:3d} "
              f"mAP50={row['mAP50']:.4f} mAP50-95={row['mAP50_95']:.4f} "
              f"P={row['precision']:.3f} R={row['recall']:.3f} "
              f"params={row['params']:,} GFLOPs={row['gflops']}")

    # sort baseline first then by mAP50 desc
    out.sort(key=lambda r: (r["exp"] != "baseline_obb", -r["mAP50"]))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {Path(args.out)} ({len(out)} runs)")


if __name__ == "__main__":
    main()
