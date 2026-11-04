"""Check the v8 threshold logic without torch, on arrays whose answer is known by hand.

What it proves
--------------
1. choose_thresholds returns the threshold with the highest validation F1, on the grid.
2. Ties go to the higher threshold.
3. A class under the val-positive minimum keeps 0.5 and is labelled "default", not tuned.
4. evaluate_test reports precision, recall, F1, exact match and Hamming correctly at both
   cuts, against numbers worked out by hand on a 40-picture synthetic set.

Run:
    python experiments/multilabel_lp_full/verify_thresholds_v8.py
Exit 0 = every hand-typed expectation holds.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_lp_v8 as T  # noqa: E402

problems = []


def check(label, got, want, tol=1e-9):
    if isinstance(want, float):
        ok = abs(float(got) - want) <= tol
    else:
        ok = got == want
    if not ok:
        problems.append(f"{label}: got {got!r}, want {want!r}")


# ---------------------------------------------------------------- 1 and 2: the chooser
# 12 positives, all above 0.6; 12 negatives, all below 0.4. The best F1 is 1.0 and every
# threshold from 0.40 to 0.60 reaches it, so the tie-break must return 0.60, the highest.
pos = np.array([0.95, 0.92, 0.90, 0.88, 0.85, 0.82, 0.80, 0.75, 0.70, 0.68, 0.65, 0.62])
neg = np.array([0.38, 0.35, 0.30, 0.25, 0.20, 0.18, 0.15, 0.10, 0.08, 0.05, 0.02, 0.01])
y_true = np.concatenate([np.ones((12, 1)), np.zeros((12, 1))])
y_score = np.concatenate([pos[:, None], neg[:, None]])

chosen = T.choose_thresholds(y_true, y_score, ["toy"])["toy"]
check("chooser source", chosen["source"], "val")
check("chooser threshold (tie goes high)", chosen["threshold"], 0.60)
check("chooser val support", chosen["val_support"], 12)
check("chooser F1 at chosen", chosen["val_f1_at_threshold"], 1.0)
check("chooser F1 at 0.5", chosen["val_f1_at_0.5"], 1.0)
check("curve length", len(chosen["curve"]), 19)
check("curve is on the grid", [c["threshold"] for c in chosen["curve"]], T.THRESHOLD_GRID)
best_seen = max(chosen["curve"], key=lambda c: (c["f1"], c["threshold"]))
check("chosen equals the best curve point", chosen["threshold"], best_seen["threshold"])

# ---------------------------------------------------------------- 3: the guard
small_true = np.array([[1.0]] * 5 + [[0.0]] * 5)
small_score = np.array([[0.9]] * 5 + [[0.1]] * 5)
guarded = T.choose_thresholds(small_true, small_score, ["rare"], min_positives=10)["rare"]
check("guarded source", guarded["source"], "default")
check("guarded threshold", guarded["threshold"], 0.5)
check("guarded reports the unseen best", guarded["val_best_threshold_seen"], 0.90)

# ---------------------------------------------------------------- 4: the test read
# 40 pictures, two real columns, the other ten all zero.
#   P1_MPP: 20 positives at 0.9, 20 negatives at 0.1.
#   P1_ML : 20 positives (10 at 0.9, 10 at 0.2), 20 negatives at 0.1.
# At 0.5   MPP P/R/F1 = 1 / 1 / 1 ; ML = 1 / 0.5 / 0.667 ; exact 30/40 ; hamming 10/80.
# At 0.2   both perfect ; exact 40/40 ; hamming 0.
n = 40
test_true = np.zeros((n, len(T.LP_COLUMNS)))
test_score = np.zeros((n, len(T.LP_COLUMNS)))
test_true[0:20, 0] = 1.0
test_score[0:20, 0] = 0.9
test_score[20:40, 0] = 0.1
test_true[0:10, 1] = 1.0
test_true[20:30, 1] = 1.0
test_score[0:10, 1] = 0.9
test_score[20:30, 1] = 0.2
test_score[10:20, 1] = 0.1
test_score[30:40, 1] = 0.1

thresholds = {"P1_MPP": {"threshold": 0.50, "source": "val"},
              "P1_ML": {"threshold": 0.20, "source": "val"}}
for code in T.LP_COLUMNS[2:]:
    thresholds[code] = {"threshold": 0.50, "source": "default"}
rows = [{"has_lp": True, "has_object": False, "is_clear": False} for _ in range(n)]

result = T.evaluate_test(test_true, test_score, rows, "a", thresholds)
check("rows", result["rows"], 40)
check("exact match at 0.5", result["exact_match"], 0.75)
check("exact match at cut", result["exact_match_val_thr"], 1.0)
# Hamming is over all twelve LP columns, so the denominator is 40 x 12 = 480 cells.
check("hamming at 0.5", result["hamming_loss"], 10.0 / 480.0)
check("hamming at cut", result["hamming_loss_val_thr"], 0.0)
check("macro F1 at 0.5", result["macro_f1_0.5"], (1.0 + 2.0 / 3.0) / 2.0)
check("macro F1 at cut", result["macro_f1_val_thr"], 1.0)
check("MPP F1 at 0.5", result["per_class"]["P1_MPP"]["f1_0.5"], 1.0)
check("MPP F1 at cut", result["per_class"]["P1_MPP"]["f1_val_thr"], 1.0)
check("ML precision at 0.5", result["per_class"]["P1_ML"]["precision_0.5"], 1.0)
check("ML recall at 0.5", result["per_class"]["P1_ML"]["recall_0.5"], 0.5)
check("ML F1 at 0.5", result["per_class"]["P1_ML"]["f1_0.5"], 2.0 / 3.0)
check("ML F1 at cut", result["per_class"]["P1_ML"]["f1_val_thr"], 1.0)
check("ML threshold carried through", result["per_class"]["P1_ML"]["threshold"], 0.20)
check("judgeable set", result["judgeable_classes"], ["P1_ML", "P1_MPP"])
check("object block absent in variant a", "object_column" in result, False)
check("AUPRC of a perfect column", result["per_class"]["P1_MPP"]["auprc"], 1.0)
check("AUPRC of the second column", result["per_class"]["P1_ML"]["auprc"], 1.0)

if problems:
    print("FAIL")
    for p in problems:
        print("  ", p)
    sys.exit(1)
print("PASS: threshold chooser, guard and test read match the hand-worked values")
