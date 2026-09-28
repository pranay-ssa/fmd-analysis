#!/usr/bin/env python3
"""Evidence for the stratification report: what each split method actually does here.

Three methods are compared on the 3,377 lens-presentation rows, 80/20, 1,000 seeds:

  random      - no stratification at all
  powerset    - stratify on the exact 5-tag combination (the usual fallback)
  iterative   - iterative multi-label stratification (iterstrat), what we use

For each method and seed we record how far each tag's test count lands from its
proportional target. The chosen split (seed 42) is checked against its own file.

Also counted: how many distinct tag combinations exist in this matrix, and in the
full tag matrix, because a combination-based split needs every combination to be
populous enough to divide.

Output: splits/stratification_comparison.json
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_splits as ms                      # noqa: E402
from make_split_variants import load_lp_rows, LP_TAGS  # noqa: E402

SEEDS = 1000
TEST_N = 677          # the test size in the delivered split files
TWO_WAY = HERE / "splits" / "variant_80_20_two_way.csv"
OUT = HERE / "splits" / "stratification_comparison.json"


def load_matrix():
    rows = load_lp_rows(ms.DEFAULT_LABELS)
    order = sorted(rows, key=lambda r: r["image_path"])
    paths = [r["image_path"] for r in order]
    X = np.array([[int(r[t]) for t in LP_TAGS] for r in order], dtype=int)
    return paths, X


def split_random(seed, n):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(paths))
    return set(idx[:n].tolist())


def split_powerset(seed, n, X, patterns):
    from sklearn.model_selection import StratifiedShuffleSplit
    sss = StratifiedShuffleSplit(n_splits=1, test_size=n, random_state=seed)
    tr, te = next(sss.split(np.zeros(len(X)), patterns))
    return set(te.tolist())


def split_iterative(seed, n, X):
    from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit
    mss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=n, random_state=seed)
    tr, te = next(mss.split(np.zeros(len(X)), X))
    return set(te.tolist())


def drift_stats(X, targets, method, splits):
    """worst |drift| per split, plus per-class drift, as fractions."""
    worst = np.zeros(len(splits))
    per_class = np.zeros((len(splits), X.shape[1]))
    for i, te in enumerate(splits):
        te = sorted(te)
        got = X[te].sum(axis=0)
        d = (got - targets) / targets
        per_class[i] = d
        worst[i] = np.abs(d).max()
    return worst, per_class


def pattern_counts(matrix_rows, tags):
    c = Counter(tuple(r) for r in matrix_rows)
    return {
        "rows": len(matrix_rows),
        "distinct_patterns": len(c),
        "patterns_occurring_once": sum(1 for v in c.values() if v == 1),
        "patterns_occurring_twice": sum(1 for v in c.values() if v == 2),
        "smallest_pattern": min(c.values()),
        "largest_pattern": max(c.values()),
    }


def pct(x):
    return round(float(x) * 100, 2)


def main():
    global paths
    paths, X = load_matrix()
    n, k = X.shape
    totals = X.sum(axis=0)
    targets = TEST_N / n * totals
    patterns = [tuple(r) for r in X.tolist()]

    report = {"rows": n, "tags": list(LP_TAGS), "test_size": TEST_N,
              "positives_total": dict(zip(LP_TAGS, totals.tolist())),
              "test_target": dict(zip(LP_TAGS, targets.tolist()))}

    # ---- does the real build path reproduce the delivered file? ------------
    # The build groups rows by content hash and orders them by hash key, then
    # calls assign_iterstrat with ratios 65/15/20 and seed 42. The matrix above
    # is ordered by image_path, which changes index order and therefore which
    # rows a given seed selects, so the check must follow the real path.
    groups, _order = ms.build_groups(load_lp_rows(ms.DEFAULT_LABELS))
    M = np.array([g["labels"] for g in groups], dtype=int)
    paths_by_group = [g["images"][0]["image_path"] for g in groups]
    saved = ms.RATIOS
    ms.RATIOS = {"train": 0.65, "val": 0.15, "test": 0.20}
    try:
        tw = ms.assign_iterstrat(M)
    finally:
        ms.RATIOS = saved
    delivered = set()
    with open(TWO_WAY, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["split"] == "test":
                delivered.add(row["image_path"])
    repro_paths = {paths_by_group[i] for i, s in tw.items() if s == "test"}
    report["reproduces_delivered_test"] = (repro_paths == delivered)
    report["delivered_test_rows"] = len(delivered)
    report["reproduction_path"] = ("content-hash grouping, hash-key order, iterstrat "
                                   "seed 42, ratios 65/15/20")

    # ---- the three methods over SEEDS seeds --------------------------------
    methods = {
        "random":   lambda s: split_random(s, TEST_N),
        "powerset": lambda s: split_powerset(s, TEST_N, X, patterns),
        "iterative": lambda s: split_iterative(s, TEST_N, X),
    }
    summary = {}
    for name, fn in methods.items():
        splits = [fn(s) for s in range(SEEDS)]
        worst, per_class = drift_stats(X, targets, name, splits)
        fl = [sum(X[sorted(t)][LP_TAGS.index("P1_FL")].sum() if False else 0 for t in [0])]  # placeholder
        fl_idx = LP_TAGS.index("P1_FL")
        fl_counts = np.array([X[sorted(t)][:, fl_idx].sum() for t in splits])
        per_class_max = np.abs(per_class).max(axis=0)   # worst drift seen for each tag
        summary[name] = {
            "mean_worst_tag_drift": pct(worst.mean()),
            "median_worst_tag_drift": pct(np.median(worst)),
            "p95_worst_tag_drift": pct(np.percentile(worst, 95)),
            "max_worst_tag_drift": pct(worst.max()),
            "share_over_5pct": pct((worst > 0.05).mean()),
            "share_over_10pct": pct((worst > 0.10).mean()),
            "folded_lens_test_min": int(fl_counts.min()),
            "folded_lens_test_max": int(fl_counts.max()),
            "folded_lens_test_target": round(float(targets[fl_idx]), 1),
            "worst_drift_seen_per_tag": {t: pct(v) for t, v in zip(LP_TAGS, per_class_max)},
        }
    report["methods"] = summary

    # ---- the chosen split, for comparison ----------------------------------
    by_path = {p: i for i, p in enumerate(paths)}
    delivered_idx = {by_path[p] for p in delivered}
    _, chosen = drift_stats(X, targets, "chosen", [delivered_idx])
    report["chosen_split_seed42_worst_drift"] = pct(np.abs(chosen[0]).max())
    report["chosen_split_seed42_per_tag_drift"] = {
        t: pct(v) for t, v in zip(LP_TAGS, chosen[0])}

    # ---- how far a pattern-based split can go ------------------------------
    report["patterns_this_matrix"] = pattern_counts(X.tolist(), LP_TAGS)

    # full tag matrix, all task tags: this is what a pattern split would face
    # if the label space grows (for example when the out-of-inclusion tags join).
    import build_labels as bl
    if hasattr(bl, "load_exports"):
        exports, bad = bl.load_exports(bl.DEFAULT_XML, bl.DEFAULT_BMP_ROOT)
        all_tags, tag_rows, _unres = bl.assign_tags(exports, bl.DEFAULT_OUT)
        all_tags = sorted(all_tags)
        per_image = {r["image_path"]: set() for r in tag_rows}
        for r in tag_rows:
            if r.get("tag_name"):
                per_image.setdefault(r["image_path"], set()).add(r["tag_name"])
        full = [[1 if t in per_image.get(p, set()) else 0 for t in all_tags]
                for p in paths]
        report["patterns_full_matrix"] = pattern_counts(full, all_tags)
        report["full_matrix_tag_count"] = len(all_tags)

    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print("=" * 72)
    print("rows %d | tags %d | test %d | seeds %d"
          % (n, k, TEST_N, SEEDS))
    print("test target per tag: %s"
          % dict(zip(LP_TAGS, [round(float(t), 1) for t in targets])))
    print("\ndelivered test set reproduced by the build path (seed 42, ratios 65/15/20): %s"
          % report["reproduces_delivered_test"])
    print("\nchosen split (seed 42) worst tag drift: %.2f%%"
          % report["chosen_split_seed42_worst_drift"])
    print("  per tag: %s" % report["chosen_split_seed42_per_tag_drift"])

    print("\n%-11s %8s %8s %8s %8s %9s %9s  %s"
          % ("method", "mean", "median", "p95", "max", ">5%", ">10%", "FoldedLens range"))
    for name, s in summary.items():
        print("%-11s %7.2f%% %7.2f%% %7.2f%% %7.2f%% %8.1f%% %8.1f%%  %d..%d (target %.1f)"
              % (name, s["mean_worst_tag_drift"], s["median_worst_tag_drift"],
                 s["p95_worst_tag_drift"], s["max_worst_tag_drift"],
                 s["share_over_5pct"], s["share_over_10pct"],
                 s["folded_lens_test_min"], s["folded_lens_test_max"],
                 s["folded_lens_test_target"]))

    print("\nworst drift ever seen for each tag (over %d seeds):" % SEEDS)
    print("%-11s %s" % ("method", "  ".join("%s" % t[:6] for t in LP_TAGS)))
    for name, s in summary.items():
        print("%-11s %s" % (name, "  ".join("%5.1f%%" % s["worst_drift_seen_per_tag"][t]
                                            for t in LP_TAGS)))

    print("\ntag combinations in this 5-tag matrix: %s"
          % report["patterns_this_matrix"])
    if "patterns_full_matrix" in report:
        print("tag combinations across the full tag set (%d tags): %s"
              % (report["full_matrix_tag_count"], report["patterns_full_matrix"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    global paths
    paths, _X = load_matrix()
    main()
