#!/usr/bin/env python3
"""
The six highlighted classes: a model trained on just those six against the full model.

Both models scored the same test pictures, because a picture kept its train or test side from the
one split. The subset model only ever answers with six labels. The full model answers with all of
its labels, so its scores on these six classes are read out of its full confusion matrix:

    recall    diagonal of the class divided by that class's row total, the same in both
    precision diagonal of the class divided by that class's column total in the FULL matrix

Reading precision from the full column matters. A foreign matter picture that the full model calls
"Bubble" is a wrong answer in the real world, and using a matrix trimmed to six classes would drop
that error and flatter the full model. Accuracy is counted the same way: correct answered pictures
over all pictures of the six classes, with every wrong answer counted, whatever it was called.

    python3 compare_subset_vs_full.py
"""
from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINES = ["L24", "L25", "L26", "L27", "L31"]
FULL = os.path.join(REPO, "runs", "cnn", "lines")
SUBSET = os.path.join(REPO, "runs", "cnn", "lines_subset6")
OUT = os.path.join(REPO, "run", "line_results_subset6_20260917")
SIX = ["Missing Primary Package", "Multiple Lenses", "Foreign Matter",
       "Lens Off Center", "Missing Lens", "HEMA Obstruction"]


def read_cm(path):
    rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
    classes = rows[0][1:-1]
    matrix = [[int(x) for x in r[1:-1]] for r in rows[1:]]
    return classes, matrix


def main():
    os.makedirs(OUT, exist_ok=True)
    out_rows = []
    print("{0:5s} {1:>8s} {2:>9s} {3:>9s} {4:>8s} {5:>9s} {6:>9s} {7:>8s}".format(
        "line", "test n", "full acc", "six acc", "acc gap", "full macR", "six macR", "R gap"))
    for line in LINES:
        classes, cm = read_cm(os.path.join(FULL, line, "epochs_50",
                                           "confusion_matrix_{0}.csv".format(line)))
        sub = json.load(open(os.path.join(SUBSET, line, "epochs_50", "metrics.json")))
        idx = {c: i for i, c in enumerate(classes)}
        n = sum(sum(cm[idx[c]]) for c in SIX)
        correct = sum(cm[idx[c]][idx[c]] for c in SIX)
        acc_full = correct / n
        rec, prec, f1s = {}, {}, {}
        for c in SIX:
            i = idx[c]
            row = sum(cm[i])
            col = sum(cm[r][i] for r in range(len(classes)))
            rec[c] = cm[i][i] / row if row else None
            prec[c] = cm[i][i] / col if col else None
            f1s[c] = (2 * prec[c] * rec[c] / (prec[c] + rec[c])
                      if prec[c] and rec[c] and (prec[c] + rec[c]) else 0.0)
        macro_r_full = st.mean(v for v in rec.values() if v is not None)
        macro_f1_full = st.mean(f1s.values())
        acc_sub = sub["overall_accuracy"]
        macro_r_sub = sub["macro"]["recall"]
        macro_f1_sub = sub["macro"]["f1"]
        print("{0:5s} {1:8d} {2:9.2f} {3:9.2f} {4:+8.2f} {5:9.2f} {6:9.2f} {7:+8.2f}".format(
            line, n, acc_full * 100, acc_sub * 100, (acc_sub - acc_full) * 100,
            macro_r_full * 100, macro_r_sub * 100, (macro_r_sub - macro_r_full) * 100))
        out_rows.append({"line": line, "test_pictures_of_the_six": n,
                         "full_accuracy": round(acc_full, 4), "six_accuracy": round(acc_sub, 4),
                         "accuracy_gap": round(acc_sub - acc_full, 4),
                         "full_macro_recall": round(macro_r_full, 4),
                         "six_macro_recall": round(macro_r_sub, 4),
                         "macro_recall_gap": round(macro_r_sub - macro_r_full, 4),
                         "full_macro_f1": round(macro_f1_full, 4),
                         "six_macro_f1": round(macro_f1_sub, 4),
                         "macro_f1_gap": round(macro_f1_sub - macro_f1_full, 4),
                         "per_class": {c: {"recall_full": round(rec[c], 4) if rec[c] is not None else None,
                                           "recall_six": sub["per_class"].get(c, {}).get("recall"),
                                           "support": int(sum(cm[idx[c]]))} for c in SIX}})
    tot_n = sum(r["test_pictures_of_the_six"] for r in out_rows)
    pooled_full = sum(r["full_accuracy"] * r["test_pictures_of_the_six"] for r in out_rows) / tot_n
    pooled_six = sum(r["six_accuracy"] * r["test_pictures_of_the_six"] for r in out_rows) / tot_n
    print()
    print("All five, same pictures both times, {0} test pictures of the six classes".format(tot_n))
    print("  pooled accuracy, full model : {0:.2f}%".format(pooled_full * 100))
    print("  pooled accuracy, six model  : {0:.2f}%".format(pooled_six * 100))
    print("  gap                         : {0:+.2f} points".format((pooled_six - pooled_full) * 100))
    print("  mean macro recall full {0:.2f}%, six {1:.2f}%".format(
        st.mean(r["full_macro_recall"] for r in out_rows) * 100,
        st.mean(r["six_macro_recall"] for r in out_rows) * 100))
    with open(os.path.join(OUT, "subset_vs_full.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[k for k in out_rows[0] if k != "per_class"])
        w.writeheader()
        w.writerows([{k: v for k, v in r.items() if k != "per_class"} for r in out_rows])
    with open(os.path.join(OUT, "subset_vs_full.json"), "w", encoding="utf-8") as fh:
        json.dump({"classes": SIX, "lines": out_rows,
                   "pooled": {"test_pictures": tot_n, "full_accuracy": round(pooled_full, 4),
                              "six_accuracy": round(pooled_six, 4)}}, fh, indent=2)
    print("\nwrote {0}".format(os.path.relpath(os.path.join(OUT, "subset_vs_full.csv"), REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
