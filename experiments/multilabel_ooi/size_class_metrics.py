"""Precision, recall and F1 for the four size classes at their chosen threshold.

The condition table already records these for the fifteen condition classes. This script produces
the matching four rows for the size model, on every test picture that carries the class, flagged
and untagged together.

    python experiments/multilabel_ooi/size_class_metrics.py \
        --predictions run/exp3_1_gate4_224_20261117/predictions.npz \
        --thresholds run/exp3_1_gate4_224_20261117/thresholds.json \
        --labels run/split_exp3_1_20261116/labels.csv \
        --annotation run/eda_full_20261029/resolved_labels.csv \
        --out run/exp3_2_scores_20261116/size_classes_metrics.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

CLASSES = {
    "fm_gated": ("Foreign Matter", {"foreign_matter"}),
    "fiber_gated": ("Fiber", {"fiber"}),
    "ep_gated": ("Extraneous Polymer", {"extraneous_polymer"}),
    "hema_gated": ("HEMA", {"hema", "hema_obstruction", "hema_fragment"}),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--thresholds", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--annotation", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import numpy as np

    with open(args.labels, newline="", encoding="utf-8") as f:
        rows = {r["picture_md5"]: r for r in csv.DictReader(f)}
    test = {m: r for m, r in rows.items() if r["split"] == "test"}

    boxes: dict[str, set[str]] = collections.defaultdict(set)
    with open(args.annotation, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = r["picture_md5"].strip()
            if m in test and (r["shape_kind"] or "").strip() == "box":
                boxes[m].add((r["canonical_id"] or "").strip())

    d = np.load(args.predictions, allow_pickle=True)  # trusted artifact from our trainer
    md5 = [str(x) for x in (d["md5"] if "md5" in d else d["test_md5"])]
    score = d["score"] if "score" in d else d["test_score"]
    columns = [str(x) for x in d["columns"]]
    at = {m: i for i, m in enumerate(md5)}
    cuts = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))["per_class"]

    out_rows = []
    for key, (label, ids) in CLASSES.items():
        pop = [m for m in md5 if boxes[m] & ids]
        j = columns.index(key)
        cut = float(cuts[key]["threshold"])
        pos = [float(score[at[m], j]) for m in pop if test[m][key] == "1"]
        neg = [float(score[at[m], j]) for m in pop if test[m][key] == "0"]
        tp = sum(1 for m in pop if test[m][key] == "1" and float(score[at[m], j]) >= cut)
        fp = sum(1 for m in pop if test[m][key] == "0" and float(score[at[m], j]) >= cut)
        fn = len(pos) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        wins = sum(1 for a in pos for b in neg if a > b) + 0.5 * sum(1 for a in pos for b in neg
                                                                   if a == b)
        auroc = wins / (len(pos) * len(neg)) if (pos and neg) else None
        out_rows.append({"class": label, "read_by": "Size model", "population": len(pop),
                         "flagged": len(pos), "threshold": round(cut, 2),
                         "auroc": round(auroc, 3) if auroc is not None else "",
                         "precision": round(precision, 3), "recall": round(recall, 3),
                         "f1": round(f1, 3)})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    for r in out_rows:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
