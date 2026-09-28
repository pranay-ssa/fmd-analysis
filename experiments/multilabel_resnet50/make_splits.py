#!/usr/bin/env python3
"""Group-aware multi-label 70/15/15 splitter, seed 42.

Groups are content md5 values (the 34 pictures stored in two folders and the 27
renamed twins must never straddle two splits). Each group is reduced to the OR
of its members' labels, then assigned to train/val/test as one unit.

Strategies:
  iterstrat : iterative multi-label stratification over groups, used when the
              iterstrat package is installed (auto picks it when available).
  powerset  : documented fallback, stratify on the label-powerset (exact
              combination pattern) with group-aware assignment; patterns are
              processed largest first, groups inside a pattern are shuffled with
              seed 42, and each group goes to the split with the highest
              remaining-capacity / ratio score, so fractions track 70/15/15 by
              image count.

Output: splits/seed42.csv (one row per image) plus splits/seed42.meta.json
recording which strategy ran, so the split is reproducible from disk.

Usage:
    python experiments/multilabel_resnet50/make_splits.py [--strategy auto|iterstrat|powerset]
"""
import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_LABELS = HERE / "labels.csv"
DEFAULT_OUT = HERE / "splits" / "seed42.csv"
LP_TAGS = ["P1_COC", "P1_FL", "P1_ML", "P1_MPP", "P1_NL"]
SEED = 42
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("labels.csv is empty, run build_labels.py first")
    for row in rows:
        for tag in LP_TAGS:
            row[tag] = int(row[tag])
        row["negatives_reliable"] = row["negatives_reliable"] in (True, 1, "1", "True", "true")
    return rows


def build_groups(rows):
    """group_key -> {"images": [...], "labels": OR-vector}"""
    groups = {}
    order = []
    for row in rows:
        md5 = (row.get("md5") or "").strip()
        key = md5 if md5 else "path:" + row["image_path"]
        if key not in groups:
            groups[key] = {"images": [], "labels": [0] * len(LP_TAGS)}
            order.append(key)
        groups[key]["images"].append(row)
        for i, tag in enumerate(LP_TAGS):
            if row[tag]:
                groups[key]["labels"][i] = 1
    # deterministic input order
    order.sort()
    return [groups[k] for k in order], order


def assign_iterstrat(group_matrix):
    """Iterative multi-label stratification over groups (iterstrat package)."""
    from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

    placeholder = np.zeros((group_matrix.shape[0], 1))
    kwargs = {"n_splits": 1, "random_state": SEED}
    first = MultilabelStratifiedShuffleSplit(test_size=RATIOS["test"], **kwargs)
    trainval, test = next(first.split(placeholder, group_matrix))

    val_fraction_of_remainder = RATIOS["val"] / (RATIOS["train"] + RATIOS["val"])
    second = MultilabelStratifiedShuffleSplit(test_size=val_fraction_of_remainder, **kwargs)
    train_rel, val_rel = next(second.split(placeholder[trainval], group_matrix[trainval]))

    assignment = {}
    for global_i in trainval[train_rel]:
        assignment[int(global_i)] = "train"
    for global_i in trainval[val_rel]:
        assignment[int(global_i)] = "val"
    for global_i in test:
        assignment[int(global_i)] = "test"
    return assignment


def assign_powerset(groups):
    """Fallback: label-powerset pattern stratification, group aware."""
    rng = random.Random(SEED)
    total_images = sum(len(g["images"]) for g in groups)
    left = {s: RATIOS[s] * total_images for s in RATIOS}
    preference = {"train": 2, "val": 1, "test": 0}  # deterministic tie break

    patterns = defaultdict(list)
    for i, g in enumerate(groups):
        patterns[tuple(g["labels"])].append(i)

    assignment = {}
    # largest patterns first, ties broken by the pattern itself for determinism
    for pattern in sorted(patterns, key=lambda p: (-len(patterns[p]), p)):
        members = patterns[pattern][:]
        rng.shuffle(members)
        for i in members:
            # send the group to the split that is furthest behind its image target
            best = max(RATIOS, key=lambda s: (left[s] / RATIOS[s], preference[s]))
            assignment[i] = best
            left[best] -= len(groups[i]["images"])
    return assignment


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=str(DEFAULT_LABELS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--strategy", choices=["auto", "iterstrat", "powerset"], default="auto")
    args = ap.parse_args()

    rows = load_rows(Path(args.labels))
    groups, order = build_groups(rows)

    try:
        import iterstrat  # noqa: F401
        iterstrat_available = True
    except ImportError:
        iterstrat_available = False

    strategy = args.strategy
    if strategy == "auto":
        strategy = "iterstrat" if iterstrat_available else "powerset"
    if strategy == "iterstrat" and not iterstrat_available:
        print("iterstrat is not installed, falling back to the powerset strategy")
        strategy = "powerset"

    matrix = np.array([g["labels"] for g in groups], dtype=int)
    if strategy == "iterstrat":
        assignment = assign_iterstrat(matrix)
    else:
        assignment = assign_powerset(groups)

    # expand groups to images
    out_rows = []
    for i, key in enumerate(order):
        split = assignment[i]
        for row in groups[i]["images"]:
            out_rows.append([
                row["image_path"], row.get("md5", ""), key, row.get("task_name", ""),
                *[row[t] for t in LP_TAGS],
                int(row["negatives_reliable"]), split,
            ])
    out_rows.sort(key=lambda r: r[0])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["image_path", "md5", "group_key", "task_name"] + LP_TAGS + [
        "negatives_reliable", "split"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(out_rows)

    # ---- report -----------------------------------------------------------------
    split_images = Counter(r[-1] for r in out_rows)
    split_groups = Counter(assignment[i] for i in range(len(groups)))
    split_reliable = Counter(r[-1] for r in out_rows if r[-2] == 1)
    split_labels = {s: [0] * len(LP_TAGS) for s in RATIOS}
    for r in out_rows:
        for j in range(len(LP_TAGS)):
            split_labels[r[-1]][j] += r[4 + j]

    n_images = len(out_rows)
    print("strategy: %s (iterstrat installed: %s) | seed %d" % (strategy, iterstrat_available, SEED))
    print("wrote %s (%d image rows, %d groups)" % (out_path, n_images, len(groups)))
    for s in ("train", "val", "test"):
        frac = split_images[s] / n_images if n_images else 0.0
        labels_txt = ", ".join("%s=%d" % (t, split_labels[s][j]) for j, t in enumerate(LP_TAGS))
        print("  %-5s images=%5d (%.2f%%, target %.0f%%) groups=%5d reliable_neg_ok=%5d | %s"
              % (s, split_images[s], frac * 100, RATIOS[s] * 100, split_groups[s],
                 split_reliable.get(s, 0), labels_txt))

    leaks = 0
    per_group_splits = defaultdict(set)
    for r in out_rows:
        per_group_splits[r[2]].add(r[-1])
    leaks = sum(1 for v in per_group_splits.values() if len(v) > 1)
    print("leakage check: %d groups appear in more than one split (must be 0)" % leaks)

    meta = {
        "seed": SEED,
        "strategy": strategy,
        "iterstrat_available": iterstrat_available,
        "ratios": RATIOS,
        "groups_total": len(groups),
        "images_total": n_images,
        "images_per_split": dict(split_images),
        "groups_per_split": dict(split_groups),
        "label_positives_per_split": {s: dict(zip(LP_TAGS, split_labels[s])) for s in RATIOS},
        "group_split_leaks": leaks,
        "source_labels": str(Path(args.labels).name),
    }
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote %s" % meta_path)

    if leaks:
        return 1
    if split_images["train"] == 0 or split_images["val"] == 0 or split_images["test"] == 0:
        print("MISMATCH: an empty split")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
