#!/usr/bin/env python3
"""
Two architectures on the same full split: ResNet50 against ResNet50-Inception MultiLevel MultiScale.

Both runs trained on the identical per-line train halves and were scored on the identical test
halves, so every difference below is the architecture, not the data. Reads

    runs/cnn/lines/<line>/epochs_50/            ResNet50
    runs/cnn/lines_multiscale/<line>/epochs_50/ ResNet50-Inception MultiLevel MultiScale

and writes run/line_results_multiscale_20260917/arch_vs_base.{csv,json}.

Besides the per-line table it decomposes the change in pooled accuracy class by class:

    contribution of a class = (correct multi-scale - correct ResNet50) for that class / all test pictures

The contributions sum to the pooled accuracy gap by construction, which the script asserts, so the
headline number is attributed to named classes instead of being left unexplained.

    python3 compare_architectures.py
"""
from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINES = ["L24", "L25", "L26", "L27", "L31"]
BASE = os.path.join(REPO, "runs", "cnn", "lines")
SCALE = os.path.join(REPO, "runs", "cnn", "lines_multiscale")
OUT = os.path.join(REPO, "run", "line_results_multiscale_20260917")


def read_cm(path):
    rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
    return rows[0][1:-1], [[int(x) for x in r[1:-1]] for r in rows[1:]]


def safe_div(a, b):
    return (a / b) if b else None


def main():
    os.makedirs(OUT, exist_ok=True)
    lines_out, per_class = [], []
    diag_b_sum = diag_s_sum = 0
    print("{0:5s} {1:>7s} {2:>8s} {3:>8s} {4:>8s} {5:>8s} {6:>8s} {7:>8s} {8:>7s}".format(
        "line", "test n", "R50 acc", "MS acc", "acc gap", "R50 macR", "MS macR", "R gap", "mins"))
    for line in LINES:
        cb, cmb = read_cm(os.path.join(BASE, line, "epochs_50",
                                       "confusion_matrix_{0}.csv".format(line)))
        cs, cms = read_cm(os.path.join(SCALE, line, "epochs_50",
                                       "confusion_matrix_{0}.csv".format(line)))
        if cb != cs:
            print("class order differs on {0}, cannot compare".format(line))
            return 2
        mb = json.load(open(os.path.join(BASE, line, "epochs_50", "metrics.json")))
        ms = json.load(open(os.path.join(SCALE, line, "epochs_50", "metrics.json")))
        n = sum(sum(r) for r in cmb)
        if n != sum(sum(r) for r in cms):
            print("test picture count differs on {0}".format(line))
            return 2

        rec = {}
        for i, c in enumerate(cb):
            sup = sum(cmb[i])
            if not sup:
                continue
            rb, rs = safe_div(cmb[i][i], sup), safe_div(cms[i][i], sup)
            rec[c] = (rb, rs, sup, cms[i][i] - cmb[i][i])
            per_class.append({"line": line, "cls": c, "support": sup,
                              "recall_resnet50": round(rb, 4), "recall_multiscale": round(rs, 4),
                              "recall_gap": round(rs - rb, 4),
                              "correct_resnet50": cmb[i][i], "correct_multiscale": cms[i][i],
                              "correct_change": cms[i][i] - cmb[i][i]})
        macb = st.mean(v[0] for v in rec.values())
        macs = st.mean(v[1] for v in rec.values())
        # pooled from the confusion matrices, not from the stored accuracies: metrics.json
        # keeps those rounded to 4 places, which leaves a ~2e-5 residue against the exact
        # decomposition below and would make a correct attribution look wrong
        diag_b_sum += sum(cmb[i][i] for i in range(len(cb)))
        diag_s_sum += sum(cms[i][i] for i in range(len(cs)))
        lines_out.append({
            "line": line, "test_pictures": n,
            "accuracy_resnet50": round(mb["overall_accuracy"], 4),
            "accuracy_multiscale": round(ms["overall_accuracy"], 4),
            "accuracy_gap": round(ms["overall_accuracy"] - mb["overall_accuracy"], 4),
            "macro_recall_resnet50": round(macb, 4), "macro_recall_multiscale": round(macs, 4),
            "macro_recall_gap": round(macs - macb, 4),
            "macro_f1_resnet50": round(mb["macro"]["f1"], 4),
            "macro_f1_multiscale": round(ms["macro"]["f1"], 4),
            "macro_f1_gap": round(ms["macro"]["f1"] - mb["macro"]["f1"], 4),
            "train_minutes_resnet50": round(mb["training_time_sec"] / 60, 1),
            "train_minutes_multiscale": round(ms["training_time_sec"] / 60, 1),
            "classes_scored": len(rec),
            "per_class": {c: {"support": v[2], "resnet50": round(v[0], 4),
                              "multiscale": round(v[1], 4), "gap": round(v[1] - v[0], 4),
                              "correct_change": v[3]} for c, v in rec.items()},
        })
        print("{0:5s} {1:7d} {2:8.2f} {3:8.2f} {4:+8.2f} {5:8.2f} {6:8.2f} {7:+8.2f} {8:7.1f}".format(
            line, n, mb["overall_accuracy"] * 100, ms["overall_accuracy"] * 100,
            (ms["overall_accuracy"] - mb["overall_accuracy"]) * 100,
            macb * 100, macs * 100, (macs - macb) * 100, ms["training_time_sec"] / 60))

    tot = sum(r["test_pictures"] for r in lines_out)
    pool_b = diag_b_sum / tot
    pool_s = diag_s_sum / tot
    print()
    print("All five, {0} test pictures, identical pictures both times".format(tot))
    print("  pooled accuracy  ResNet50 {0:.2f}%   MultiLevelMultiScale {1:.2f}%   gap {2:+.2f}".format(
        pool_b * 100, pool_s * 100, (pool_s - pool_b) * 100))
    print("  mean macro recall ResNet50 {0:.2f}%   MultiLevelMultiScale {1:.2f}%   gap {2:+.2f}".format(
        st.mean(r["macro_recall_resnet50"] for r in lines_out) * 100,
        st.mean(r["macro_recall_multiscale"] for r in lines_out) * 100,
        (st.mean(r["macro_recall_multiscale"] for r in lines_out)
         - st.mean(r["macro_recall_resnet50"] for r in lines_out)) * 100))

    # attribution: which classes moved the pooled accuracy, in percentage points of the whole test set
    contrib = {}
    for r in per_class:
        contrib[r["cls"]] = contrib.get(r["cls"], 0) + r["correct_change"]
    total_change = sum(contrib.values())
    implied = total_change / tot
    print()
    print("Attribution of the pooled accuracy gap ({0:+.2f} points), by class".format(implied * 100))
    assert abs(implied - (pool_s - pool_b)) < 1e-9, "attribution does not sum to the pooled gap"
    print("  decomposition adds up to the pooled gap exactly (checked)")
    rank = sorted(contrib.items(), key=lambda kv: -abs(kv[1]))
    for cls, ch in rank[:8]:
        print("    {0:24s} {1:+5d} correct answers  {2:+6.2f} points".format(
            cls, ch, ch / tot * 100))

    better = sum(1 for r in per_class if r["recall_gap"] > 0)
    worse = sum(1 for r in per_class if r["recall_gap"] < 0)
    same = sum(1 for r in per_class if r["recall_gap"] == 0)
    print()
    print("  class-line cells where multi-scale recalled more: {0}".format(better))
    print("  class-line cells where it recalled less            : {0}".format(worse))
    print("  class-line cells unchanged                         : {0}".format(same))
    big = [r for r in per_class if r["support"] >= 20]
    print("  cells with at least 20 test pictures: {0}, of which better {1}, worse {2}".format(
        len(big), sum(1 for r in big if r["recall_gap"] > 0), sum(1 for r in big if r["recall_gap"] < 0)))

    with open(os.path.join(OUT, "arch_vs_base.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[k for k in lines_out[0] if k != "per_class"])
        w.writeheader()
        w.writerows([{k: v for k, v in r.items() if k != "per_class"} for r in lines_out])
    with open(os.path.join(OUT, "arch_vs_base.json"), "w", encoding="utf-8") as fh:
        json.dump({"architectures": ["ResNet50", "ResNet50-Inception MultiLevel MultiScale"],
                   "lines": lines_out, "per_class": per_class,
                   "pooled": {"test_pictures": tot,
                              "accuracy_resnet50": round(pool_b, 6),
                              "accuracy_multiscale": round(pool_s, 6),
                              "accuracy_gap": pool_s - pool_b,  # unrounded: the attribution below sums to it exactly
                              "attribution_by_class_share": {k: v / tot
                                                             for k, v in contrib.items()},
                              "cells_better": better, "cells_worse": worse, "cells_same": same}},
                  fh, indent=2)
    print("\nwrote {0}".format(os.path.relpath(os.path.join(OUT, "arch_vs_base.csv"), REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
