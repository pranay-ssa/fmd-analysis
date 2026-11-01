"""Local checks that need no torch: label counts and the AUPRC implementation."""
import csv, importlib.util, os
import numpy as np
from sklearn.metrics import average_precision_score

spec = importlib.util.spec_from_file_location(
    "train_lp", r"D:\fmd-analysis\experiments\multilabel_lp_full\train_lp.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

rng = np.random.default_rng(7)
worst = 0.0
for _ in range(300):
    n = int(rng.integers(20, 300))
    y = rng.integers(0, 2, n)
    s = rng.random(n)
    if y.sum() == 0:
        continue
    worst = max(worst, abs(m.average_precision(y, s) - average_precision_score(y, s)))
print("max |ours - sklearn| over 300 random cases:", round(worst, 12))

for y, s in [([1, 0, 1, 0], [0.9, 0.8, 0.7, 0.6]),
             ([0, 1, 1, 0, 0], [0.1, 0.9, 0.8, 0.2, 0.05]),
             ([1, 1, 1], [0.5, 0.5, 0.5])]:
    print(y, "ours", round(m.average_precision(y, s), 6),
          "sklearn", round(average_precision_score(y, s), 6))

BASE = os.environ.get("LP_LABELS_DIR", r"D:\fmd-analysis\run\multilabel_lp_full_20261028")
A = list(csv.DictReader(open(os.path.join(BASE, "labels_a.csv"),
                            newline="", encoding="utf-8")))
B = list(csv.DictReader(open(os.path.join(BASE, "labels_b.csv"),
                            newline="", encoding="utf-8")))
print("A", len(A), "B", len(B), "| A subset of B:", {r["md5"] for r in A} <= {r["md5"] for r in B})
print("split counts A:", {s: sum(1 for r in A if r["split"] == s) for s in ("train", "test")})
print("split counts B:", {s: sum(1 for r in B if r["split"] == s) for s in ("train", "test")})
