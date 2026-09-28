#!/usr/bin/env python3
"""Two-way 80/20 split over the 3,377 LP rows: train and test only, no validation set.

This is stage 1 of the 3-way splitter run on its own: same seed 42, same
test_size=0.20, same group matrix, same iterstrat algorithm. Because the first
stage is bit-for-bit the same operation, the test set must come out identical to
splits/variant_80_20.csv, and the train set must equal that file's
split_named=train. This script asserts both, so the two options differ in
exactly one way: whether 507 of the 2,700 non-test images are withheld as a
validation set.

Output: splits/variant_80_20_two_way.csv + .meta.json
"""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_splits as ms                      # noqa: E402
from make_split_variants import load_lp_rows, LP_TAGS, HEADER  # noqa: E402

SEED = 42
TEST_FRAC = 0.20
OUT = HERE / "splits" / "variant_80_20_two_way.csv"
REF = HERE / "splits" / "variant_80_20.csv"


def build():
    rows = load_lp_rows(ms.DEFAULT_LABELS)
    groups, order = ms.build_groups(rows)

    from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit
    matrix = np.array([g["labels"] for g in groups], dtype=int)
    placeholder = np.zeros((matrix.shape[0], 1))
    mss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=TEST_FRAC,
                                           random_state=SEED)
    train_idx, test_idx = next(mss.split(placeholder, matrix))
    assign = {}
    for i in train_idx:
        assign[int(i)] = "train"
    for i in test_idx:
        assign[int(i)] = "test"

    out = []
    for i, _key in enumerate(order):
        split = assign[i]
        for row in groups[i]["images"]:
            out.append([
                row["image_path"], row.get("md5", ""), row.get("task_name", ""),
                *[row[t] for t in LP_TAGS],
                int(row["negatives_reliable"]), split, split,   # split == split_named here
            ])
    out.sort(key=lambda r: r[0])
    return rows, groups, out


def main():
    rows, groups, out = build()
    n = len(out)
    count = Counter(r[-2] for r in out)
    problems = []

    if n != 3377:
        problems.append("row count %d" % n)
    if len({r[0] for r in out}) != n:
        problems.append("duplicate image_path")

    # groups must not straddle
    per_group = defaultdict(set)
    for r in out:
        per_group[r[1] or ("path:" + r[0])].add(r[-2])
    leaks = sum(1 for v in per_group.values() if len(v) > 1)
    if leaks:
        problems.append("%d groups cross splits" % leaks)

    # per-class drift against the proportional target
    total = {t: sum(int(r[3 + i]) for r in out) for i, t in enumerate(LP_TAGS)}
    worst = 0.0
    drift = {}
    for s, frac in (("train", 1 - TEST_FRAC), ("test", TEST_FRAC)):
        d = {}
        for i, t in enumerate(LP_TAGS):
            got = sum(int(r[3 + i]) for r in out if r[-2] == s)
            want = frac * total[t]
            d[t] = (got, want, (got - want) / want if want else 0.0)
            worst = max(worst, abs(d[t][2]))
        drift[s] = d
    if worst > 0.05:
        problems.append("drift %.1f%%" % (100 * worst))

    # ---- the identity checks against the 3-way file -----------------------
    identity = {}
    if REF.exists():
        ref = list(csv.DictReader(open(REF, newline="", encoding="utf-8")))
        ref_test = {r["image_path"] for r in ref if r["split"] == "test"}
        ref_named_train = {r["image_path"] for r in ref if r["split_named"] == "train"}
        mine_test = {r[0] for r in out if r[-2] == "test"}
        mine_train = {r[0] for r in out if r[-2] == "train"}
        identity = {
            "test identical to 3-way test": ref_test == mine_test,
            "train identical to 3-way split_named=train": ref_named_train == mine_train,
            "test rows": len(mine_test),
            "train rows": len(mine_train),
        }
        if ref_test != mine_test:
            problems.append("test set differs from the 3-way file")
        if ref_named_train != mine_train:
            problems.append("train set differs from split_named=train")

    # ---- determinism -------------------------------------------------------
    _, _, again = build()
    deterministic = [r for r in out] == [r for r in again]
    if not deterministic:
        problems.append("not deterministic")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(out)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()[:16]

    meta = {
        "seed": SEED,
        "strategy": "iterstrat (stage 1 only: single 20% test carve)",
        "test_fraction": TEST_FRAC,
        "ratios": {"train": 0.80, "test": 0.20},
        "validation_set": None,
        "rows": n,
        "images_per_split": dict(count),
        "fractions": {k: round(v / n, 4) for k, v in count.items()},
        "label_positives_total": total,
        "positives_per_split": {s: {t: drift[s][t][0] for t in LP_TAGS} for s in drift},
        "worst_per_class_drift": round(worst, 4),
        "group_split_leaks": leaks,
        "groups_total": len(groups),
        "identical_to_variant_80_20": identity,
        "deterministic_rerun": deterministic,
        "sha256_16": digest,
        "verified": not problems,
    }
    OUT.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    print("wrote %s (%d rows) sha256:%s" % (OUT.name, n, digest))
    print("counts     : %s" % dict(count))
    print("fractions  : %s" % {k: "%.2f%%" % (100 * v / n) for k, v in count.items()})
    print("group leaks: %d | deterministic: %s" % (leaks, deterministic))
    print("worst drift: %.2f%%" % (100 * worst))
    print("\nper-class positives (train / test):")
    for t in LP_TAGS:
        tr, tw, _ = drift["train"][t]
        te, tee, _ = drift["test"][t]
        print("  %-8s %5d / target %6.1f   |  %4d / target %5.1f"
              % (t, tr, tw, te, tee))
    if identity:
        print("\nidentity against splits/variant_80_20.csv:")
        for k, v in identity.items():
            print("  %-42s %s" % (k, v))
    if problems:
        print("\nPROBLEMS: %s" % problems)
        return 1
    print("\nVERIFIED: 2-way and 3-way options share the same test set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
