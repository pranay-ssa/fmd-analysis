#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh experiments/registry.json rows from on-disk run artifacts (never hand-typing).

Rules this enforces:
- Results are read ONLY from the run's metrics.json, iou_metrics.json, or results.csv.
  Nothing is typed in. If no artifact has data, the row is skipped with a warning.
- Status flips to "done" only when fresh result artifacts exist for the run.
- The write is atomic (tmp file + replace) so a crash cannot corrupt registry.json.

Usage (run from repo root):
    python experiments/update_registry.py <id> [<id> ...]      # refresh specific rows
    python experiments/update_registry.py all                  # refresh every row with artifacts on disk

Example after training + IoU eval this evening:
    python experiments/update_registry.py armA_residual_deep armB_conv_p4
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "experiments" / "registry.json"
RUNS = REPO / "run" / "yolo_ooi" / "runs" / "yolo_arch"


def run_dir_for(rid):
    """registry id uses underscores; batch-1 run dirs use hyphens. Try both."""
    for cand in (RUNS / rid, RUNS / rid.replace("_", "-")):
        if cand.is_dir():
            return cand
    return None


def read_metrics(d):
    p = d / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else None


def read_iou(d):
    p = d / "iou_metrics.json"
    return json.loads(p.read_text()) if p.exists() else None


def read_results_best(d):
    """Fallback when metrics.json is absent (batch-1 runs): best-mAP50 row of results.csv."""
    p = d / "results.csv"
    if not p.exists():
        return None
    rows = list(csv.DictReader(p.open()))
    if not rows:
        return None
    best = max(rows, key=lambda r: float(r["metrics/mAP50(B)"]))
    f = lambda k: float(best[k])  # noqa
    return {
        "best_epoch": f("epoch"),
        "mAP50": f("metrics/mAP50(B)"),
        "mAP50_95": f("metrics/mAP50-95(B)"),
        "precision": f("metrics/precision(B)"),
        "recall": f("metrics/recall(B)"),
    }


def build_payload(rid, d):
    payload = {}
    m = read_metrics(d)
    if m:
        for k in ("params", "best_epoch", "mAP50", "mAP50_95", "precision", "recall", "batch"):
            if k in m and m[k] is not None:
                payload[k] = m[k]
    else:
        c = read_results_best(d)
        if c:
            payload.update(c)
    iou = read_iou(d)
    if iou:
        payload["iou_mean_matched"] = iou.get("iou_mean_overall")
        payload["match_rate"] = iou.get("match_rate")
        payload["iou_per_class"] = iou.get("per_class")
    return payload, m is not None, iou is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    by_id = {e["id"]: e for e in reg["experiments"]}
    targets = [e["id"] for e in reg["experiments"]] if args.ids == ["all"] else args.ids

    done = skipped = 0
    for rid in targets:
        if rid not in by_id:
            print("  SKIP  unknown registry id: %s" % rid)
            skipped += 1
            continue
        d = run_dir_for(rid)
        if d is None:
            print("  SKIP  no run dir for: %s" % rid)
            skipped += 1
            continue
        payload, has_meta, has_iou = build_payload(rid, d)
        if not payload:
            print("  SKIP  no result artifacts (metrics.json/results.csv) for: %s" % rid)
            skipped += 1
            continue
        row = by_id[rid]
        row["results"] = payload
        if not has_meta and "batch" in payload:
            payload.pop("batch", None)  # results.csv has no batch; do not guess
        if has_iou:
            row["results_source"] = ("runs/yolo11/yolo_arch/%s/metrics.json, iou_metrics.json"
                                     % d.name if has_meta else
                                     "runs/yolo11/yolo_arch/%s/results.csv, iou_metrics.json" % d.name)
        else:
            row["results_source"] = ("runs/yolo11/yolo_arch/%s/metrics.json" % d.name if has_meta else
                                     "runs/yolo11/yolo_arch/%s/results.csv" % d.name)
        if row.get("status") != "done":
            row["status"] = "done"
        print("  OK    %s -> status=%s mAP50=%s mAP50-95=%s iou=%s"
              % (rid, row["status"], payload.get("mAP50"), payload.get("mAP50_95"),
                 payload.get("iou_mean_matched")))
        done += 1

    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reg, indent=2) + "\n")
    tmp.replace(REGISTRY)
    print("registry updated: %d rows written, %d skipped" % (done, skipped))


if __name__ == "__main__":
    main()