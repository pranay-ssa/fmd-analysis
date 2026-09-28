#!/usr/bin/env python3
"""Independent re-check of the 2026-09-28 multilabel base run.

Recomputes every headline metric from test_predictions.npz and asserts they
match metrics.json. Also checks the npz rows are exactly the 677 test rows of
the split file. Write-only diagnostics; run from the repo root.
"""
import csv
import json
import sys
import numpy as np

RUN = "run/multilabel_lp_20260928"
SPLIT = "experiments/multilabel_resnet50/splits/variant_80_20_two_way.csv"

d = np.load(RUN + "/test_predictions.npz", allow_pickle=False)
y_true, y_score = d["y_true"].astype(int), d["y_score"]
classes = [c if isinstance(c, str) else c.decode("utf-8") for c in d["classes"]]
yp = (y_score >= 0.5).astype(int)

tp = ((y_true == 1) & (yp == 1)).sum(0)
fp = ((y_true == 0) & (yp == 1)).sum(0)
fn = ((y_true == 1) & (yp == 0)).sum(0)
tn = ((y_true == 0) & (yp == 0)).sum(0)
prec = tp / np.maximum(tp + fp, 1)
rec = tp / np.maximum(tp + fn, 1)
f1 = 2 * prec * rec / np.maximum(prec + rec, 1e-12)


def ap(t, s):
    order = np.argsort(-s, kind="stable")
    hits = t[order]
    tpv = np.cumsum(hits)
    p = tpv / np.arange(1, len(hits) + 1)
    r = tpv / t.sum()
    return float((np.diff(np.concatenate([[0], r])) * p).sum())


aps = [ap(y_true[:, j], y_score[:, j]) for j in range(y_true.shape[1])]

m = json.load(open(RUN + "/metrics.json", encoding="utf-8"))
tm = m["test_metrics"]
checks = {
    "macro_f1": abs(tm["macro_f1"] - f1.mean()) < 1e-4,
    "macro_auprc": abs(tm["macro_auprc"] - float(np.mean(aps))) < 1e-4,
    # metrics.json stores 5-decimal rounded values, so compare at that precision
    "hamming": tm["hamming_loss"] == round(float((y_true != yp).mean()), 5),
    "exact_match": tm["exact_match_ratio"] == round(float((y_true == yp).all(1).mean()), 5),
    "micro_precision": abs(tm["micro_precision"] - float(tp.sum() / (tp + fp).sum())) < 1e-4,
    "micro_recall": abs(tm["micro_recall"] - float(tp.sum() / (tp + fn).sum())) < 1e-4,
}
for j, c in enumerate(classes):
    pc = tm["per_class"][c]
    checks["cm_" + c] = (pc["tp"], pc["fp"], pc["fn"], pc["tn"]) == (
        int(tp[j]), int(fp[j]), int(fn[j]), int(tn[j]))

rows = list(csv.DictReader(open(SPLIT, newline="", encoding="utf-8")))
split_test = sorted(r["image_path"] for r in rows if r["split"] == "test")
npz_paths = [p if isinstance(p, str) else p.decode("utf-8") for p in d["paths"]]
checks["npz_rows_are_test_rows"] = sorted(npz_paths) == split_test

print("recomputed macro F1     : %.5f (run: %.5f)" % (f1.mean(), tm["macro_f1"]))
print("recomputed macro AUPRC  : %.5f (run: %.5f)" % (np.mean(aps), tm["macro_auprc"]))
print("recomputed hamming      : %.5f (run: %.5f)" % ((y_true != yp).mean(), tm["hamming_loss"]))
print("recomputed exact match  : %.5f (run: %.5f)" % ((y_true == yp).all(1).mean(), tm["exact_match_ratio"]))
print("npz rows == split test rows: %s (%d)" % (sorted(npz_paths) == split_test, len(npz_paths)))
bad = [k for k, v in checks.items() if not v]
for k, v in checks.items():
    print("  %-28s %s" % (k, "PASS" if v else "FAIL"))
if bad:
    print("FAILED: %s" % bad)
    sys.exit(1)
print("ALL %d CHECKS PASS: metrics.json is faithful to the raw predictions" % len(checks))
