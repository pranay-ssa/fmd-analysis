#!/usr/bin/env python3
"""Read-only: what the reference runs show at 1280 vs native, beyond defect size.

Reads the teammate's own run artifacts (args.yaml + results.csv + logs) and prints
training time, effective input size, and metrics at both input sizes. Nothing is written.

  - results.csv `time` is CUMULATIVE seconds, so the total is the LAST value (verified:
    sum over 100 rows ~= 100/2 * last, i.e. the column increases monotonically).
  - imgsz 2448 is not a multiple of 32, so ultralytics rounds the input to 2464.

Usage: python3 ref_native_analysis.py
"""
import csv
import json
import re
from pathlib import Path

import yaml

REF = Path("/home/amd100-user/FMD_Data_26082026/fmd_temp_images/YOLO26_ICube_Defects")
RUNS = [
    ("YOLO26n auto @1280", "yolo26n_icube_bbox"),
    ("YOLO26n auto @native", "yolo26n_icube_bbox_native"),
    ("YOLO26n fixed @1280", "yolo26n_icube_bbox_fixedlr1e-4"),
    ("YOLO26n fixed @native", "yolo26n_icube_bbox_fixedlr1e-4_native"),
    ("YOLO11n auto @1280", "yolo11n_icube_bbox"),
    ("YOLO11n auto @native", "yolo11n_icube_bbox_native"),
]
ARGS_KEYS = ["imgsz", "batch", "epochs", "patience", "optimizer", "lr0", "lrf",
             "cos_lr", "warmup_epochs", "seed", "single_cls", "workers"]


def col(rows, name):
    for k in rows[0]:
        if k.strip() == name:
            return k
    return None


def run_facts(name, run):
    d = REF / "runs" / run
    out = {"arm": name, "exists": d.exists()}
    if not d.exists():
        return out
    a = yaml.safe_load((d / "args.yaml").read_text())
    out["args"] = {k: a.get(k) for k in ARGS_KEYS}
    with (d / "results.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    out["epochs_logged"] = len(rows)
    tk = col(rows, "time")
    if tk:
        t = [float(r[tk]) for r in rows if r.get(tk)]
        out["total_train_s"] = round(t[-1], 1)          # cumulative -> last value is the total
        out["s_per_epoch"] = round(t[-1] / len(t), 2)
        out["monotonic_cumulative"] = all(b >= a_ for a_, b in zip(t, t[1:]))
        out["time_first"] = round(t[0], 2)
    for key, label in (("metrics/mAP50(B)", "mAP50"), ("metrics/mAP50-95(B)", "mAP50-95"),
                       ("metrics/precision(B)", "P"), ("metrics/recall(B)", "R")):
        k = col(rows, key)
        if k:
            vals = [float(r[k]) for r in rows if r.get(k)]
            if vals:
                out["best_" + label] = round(max(vals), 4)
                out["best_epoch_" + label] = vals.index(max(vals)) + 1
    return out


def speed_lines(log):
    p = REF / log
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(errors="replace").splitlines() if "Speed:" in ln]


def main():
    print("=" * 100)
    print("REFERENCE RUNS: 1280 vs native (read-only, teammate's artifacts)")
    print("=" * 100)

    facts = {}
    print("\n[1] what actually ran")
    head = f"{'arm':<22}{'imgsz':>7}{'batch':>7}{'epochs':>8}{'patience':>9}{'optimizer':>10}{'lr0':>9}{'workers':>8}"
    print(head)
    print("-" * len(head))
    for name, run in RUNS:
        f = run_facts(name, run)
        facts[name] = f
        a = f.get("args", {})
        print(f"{name:<22}{str(a.get('imgsz')):>7}{str(a.get('batch')):>7}{str(a.get('epochs')):>8}"
              f"{str(a.get('patience')):>9}{str(a.get('optimizer')):>10}{str(a.get('lr0')):>9}"
              f"{str(a.get('workers')):>8}")

    print("\n[2] training wall clock (same GPU, 100 epochs, batch 16)")
    head = f"{'arm':<22}{'total s':>10}{'total min':>11}{'s/epoch':>9}{'cumulative?':>12}"
    print(head)
    print("-" * len(head))
    for name, _ in RUNS:
        f = facts[name]
        tot = f.get("total_train_s")
        print(f"{name:<22}{str(tot):>10}{('%.1f' % (tot / 60)) if tot else '-':>11}"
              f"{str(f.get('s_per_epoch')):>9}{str(f.get('monotonic_cumulative')):>12}")

    print("\n[3] cost of native, relative to the same arm at 1280")
    for model in ("YOLO26n auto", "YOLO26n fixed", "YOLO11n auto"):
        a1280 = facts[f"{model} @1280"].get("total_train_s")
        anat = facts[f"{model} @native"].get("total_train_s")
        if a1280 and anat:
            print(f"  {model:<14} 1280 {a1280:>7.1f} s   native {anat:>7.1f} s   ratio {anat / a1280:.2f}x")

    print("\n[4] metrics from their per-epoch results.csv (best over 100 epochs)")
    head = f"{'arm':<22}{'best mAP50':>12}{'best mAP50-95':>15}{'best P':>9}{'best R':>9}{'ep':>5}"
    print(head)
    print("-" * len(head))
    for name, _ in RUNS:
        f = facts[name]
        print(f"{name:<22}{str(f.get('best_mAP50')):>12}{str(f.get('best_mAP50-95')):>15}"
              f"{str(f.get('best_P')):>9}{str(f.get('best_R')):>9}{str(f.get('best_epoch_mAP50')):>5}")

    print("\n[5] their own cross-resolution summary (val protocol of the script)")
    p = REF / "bbox_experiments_native_summary.json"
    if p.exists():
        for e in json.loads(p.read_text()):
            print(f"  {e['experiment']:<22} native {e['mAP50']:.4f} / {e['mAP50-95']:.4f}   "
                  f"1280 {e['mAP50_1280']:.4f} / {e['mAP50-95_1280']:.4f}   "
                  f"d mAP50 {e['d_mAP50']:+.4f} ({100 * e['d_mAP50'] / e['mAP50_1280']:+.1f}%)   "
                  f"d mAP50-95 {e['d_mAP50-95']:+.4f} ({100 * e['d_mAP50-95'] / e['mAP50-95_1280']:+.1f}%)")

    print("\n[6] inference speed from their logs (ms per image)")
    for log in ("bbox_experiments.log", "bbox_experiments_native.log"):
        hits = speed_lines(log)
        print(f"  {log} ({len(hits)} lines):")
        for ln in hits:
            print("    " + ln[:130])

    print("\n[7] dataset size and effective input, from their logs")
    lp = REF / "bbox_experiments_native.log"
    if lp.exists():
        txt = lp.read_text(errors="replace")
        for pat in (r"WARNING .*must be multiple of max stride[^\n]*", r"Using \d+ train, \d+ val images[^\n]*"):
            for m in re.findall(pat, txt)[:2]:
                print("   " + m.strip())


if __name__ == "__main__":
    main()
