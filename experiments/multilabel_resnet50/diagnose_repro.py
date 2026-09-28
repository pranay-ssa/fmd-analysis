#!/usr/bin/env python3
"""Why did simulate_stratification.py report reproduce=False?

The two-way builder reproduced the delivered test set, so the split is
deterministic. This isolates which input difference broke the match: row order
(groups are ordered by md5 key, the simulation sorted by image_path) and
test_size as a float versus an integer.
"""
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_splits as ms                      # noqa: E402
from make_split_variants import load_lp_rows, LP_TAGS  # noqa: E402

TWO_WAY = HERE / "splits" / "variant_80_20_two_way.csv"


def delivered_test():
    out = set()
    with open(TWO_WAY, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["split"] == "test":
                out.add(row["image_path"])
    return out


def stage1(matrix, test_size, seed=42):
    from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit
    ph = np.zeros((matrix.shape[0], 1))
    mss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=test_size,
                                           random_state=seed)
    _tr, te = next(mss.split(ph, matrix))
    return te


def main():
    rows = load_lp_rows(ms.DEFAULT_LABELS)
    ref = delivered_test()
    print("delivered test rows: %d" % len(ref))

    # variant 1: canonical group order (md5 key order), float test_size
    groups, order = ms.build_groups(rows)
    paths_by_group = [g["images"][0]["image_path"] for g in groups]
    M = np.array([g["labels"] for g in groups], dtype=int)
    print("\nrows %d | groups %d | first 3 group keys: %s"
          % (len(rows), len(groups), [k[:8] for k in order[:3]]))

    for label, mat, pl in (
        ("canonical group order (md5 key)", M, paths_by_group),
        ("sorted by image_path",
         M[[paths_by_group.index(p) for p in sorted(paths_by_group)]],
         sorted(paths_by_group)),
    ):
        for ts in (0.20, 677, 676):
            te = stage1(mat, ts)
            picked = {pl[i] for i in te}
            print("  order=%-32s test_size=%-6s n_test=%4d  matches delivered: %s"
                  % (label, ts, len(te), picked == ref))

    # what the full three-way assignment gives
    saved = ms.RATIOS
    ms.RATIOS = {"train": 0.65, "val": 0.15, "test": 0.20}
    try:
        tw = ms.assign_iterstrat(M)
    finally:
        ms.RATIOS = saved
    from collections import Counter
    print("\nfull assign_iterstrat(RATIOS=65/15/20) -> %s" % dict(Counter(tw.values())))
    te = {paths_by_group[i] for i, s in tw.items() if s == "test"}
    print("test rows %d | matches delivered test: %s" % (len(te), te == ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
