#!/usr/bin/env python3
"""Build three candidate split files over the 3,377 LP-tagged rows.

She has been asked whether the split should be 70/15/15 (with a val set) or the
older two-way style 70/30 / 80/20. This pre-builds all three so whichever she
picks is already on disk.

Row set: labels.csv filtered to images carrying at least one LP tag (3,377).

Every scheme is stratified THREE ways internally (train/val/test), seed 42,
group-aware on content md5, using make_splits.assign_iterstrat unchanged. The
val share is held at 15% in all three schemes, so the only thing that varies
between them is the train/test tradeoff she is actually deciding.

  variant_70_15_15.csv   train 70 / val 15 / test 15
  variant_70_30.csv      train 55 / val 15 / test 30
  variant_80_20.csv      train 65 / val 15 / test 20

Two columns carry the assignment:
  split        the three-way assignment, what train.py reads
  split_named  her framing. For the two-way schemes the 15% val is reported as
               part of "train", because from her side it is data that is not
               held out for final testing. So split_named reads 70/30 and 80/20.

The val share exists because early stopping needs one: without it, model
selection would run against the test set and the test number would be optimistic.

Outputs land in splits/, each with a .meta.json recording ratios and counts.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_splits as ms  # noqa: E402

LP_TAGS = ms.LP_TAGS
SEED = ms.SEED
OUT_DIR = HERE / "splits"

# name -> (three-way ratios, merge train+val for split_named?)
SCHEMES = [
    ("variant_70_15_15", {"train": 0.70, "val": 0.15, "test": 0.15}, False),
    ("variant_70_30", {"train": 0.55, "val": 0.15, "test": 0.30}, True),
    ("variant_80_20", {"train": 0.65, "val": 0.15, "test": 0.20}, True),
]


def load_lp_rows(labels_path):
    rows = ms.load_rows(Path(labels_path))
    return [r for r in rows if any(r[t] for t in LP_TAGS)]


def scheme_split(ratios, groups):
    """Run the existing iterative stratifier under a temporary ratio set."""
    saved = ms.RATIOS
    ms.RATIOS = ratios  # assign_iterstrat reads this at call time
    try:
        matrix = np.array([g["labels"] for g in groups], dtype=int)
        return ms.assign_iterstrat(matrix)
    finally:
        ms.RATIOS = saved


def expand(rows, groups, order, three_way, named):
    out = []
    for i, _key in enumerate(order):
        split = three_way[i]
        name = named[i]
        for row in groups[i]["images"]:
            out.append([
                row["image_path"], row.get("md5", ""), row.get("task_name", ""),
                *[row[t] for t in LP_TAGS],
                int(row["negatives_reliable"]), split, name,
            ])
    out.sort(key=lambda r: r[0])
    return out


HEADER = ["image_path", "md5", "task_name"] + LP_TAGS + [
    "negatives_reliable", "split", "split_named"]


def write_csv(path, out_rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(out_rows)


def verify(out_rows, ratios, groups, order, merge, total_rows, total_pos):
    """Return (ok, list of problem strings, stats dict)."""
    problems = []

    n = len(out_rows)
    if n != total_rows:
        problems.append("row count %d != %d" % (n, total_rows))

    paths = [r[0] for r in out_rows]
    if len(set(paths)) != n:
        problems.append("%d duplicate image_path rows" % (n - len(set(paths))))

    split_col, named_col = HEADER.index("split"), HEADER.index("split_named")

    # no group may straddle splits
    per_group = defaultdict(set)
    for r in out_rows:
        per_group[r[1] or ("path:" + r[0])].add(r[split_col])
    leaks = sum(1 for v in per_group.values() if len(v) > 1)
    if leaks:
        problems.append("%d groups cross splits" % leaks)

    counts = Counter(r[split_col] for r in out_rows)
    named_counts = Counter(r[named_col] for r in out_rows)
    for s, target in ratios.items():
        want = target * n
        got = counts.get(s, 0)
        if abs(got - want) > max(3.0, 0.01 * n):
            problems.append("%s %d vs target %.0f (off by %.0f)" % (s, got, want, got - want))

    # split_named must be consistent with split
    for r in out_rows:
        if merge:
            ok = ((r[named_col] == "train" and r[split_col] in ("train", "val"))
                  or (r[named_col] == "test" and r[split_col] == "test"))
        else:
            ok = r[named_col] == r[split_col]
        if not ok:
            problems.append("split_named inconsistent with split")
            break

    # per-column positives per split, against the proportional target
    per_split_pos = {s: [0] * len(LP_TAGS) for s in ratios}
    for r in out_rows:
        for j in range(len(LP_TAGS)):
            per_split_pos[r[split_col]][j] += r[3 + j]
    drift = {}
    for s, target in ratios.items():
        worst = 0.0
        for j, tag in enumerate(LP_TAGS):
            want = target * total_pos[tag]
            got = per_split_pos[s][j]
            if want > 0:
                worst = max(worst, abs(got - want) / want)
        drift[s] = worst
        if worst > 0.10:
            problems.append("%s worst per-class drift %.1f%% over target" % (s, worst * 100))

    stats = {
        "rows": n,
        "images_per_split": dict(counts),
        "images_per_split_named": dict(named_counts),
        "fractions": {s: round(counts.get(s, 0) / n, 4) for s in ratios},
        "positives_per_split": {s: dict(zip(LP_TAGS, per_split_pos[s])) for s in ratios},
        "worst_per_class_drift_vs_target": {s: round(drift[s], 4) for s in ratios},
        "group_split_leaks": leaks,
        "groups_total": len(groups),
        "groups_singleton": sum(1 for g in groups if len(g["images"]) == 1),
    }
    return (not problems), problems, stats


def main():
    rows = load_lp_rows(ms.DEFAULT_LABELS)
    groups, order = ms.build_groups(rows)
    total_pos = {t: sum(r[t] for r in rows) for t in LP_TAGS}
    print("row set: %d LP-tagged images | %d md5 groups (%d singleton) | seed %d"
          % (len(rows), len(groups), sum(1 for g in groups if len(g["images"]) == 1), SEED))
    print("positives: %s\n" % total_pos)

    all_ok = True
    summary = {}
    for name, ratios, merge in SCHEMES:
        tw = scheme_split(ratios, groups)
        # split_named derives from that same assignment, never a second shuffle
        named_map = {i: ("train" if merge and tw[i] in ("train", "val") else tw[i])
                     for i in range(len(groups))}
        out_rows = expand(rows, groups, order, tw, named_map)

        ok, problems, stats = verify(out_rows, ratios, groups, order, merge,
                                     len(rows), total_pos)
        path = OUT_DIR / ("%s.csv" % name)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        write_csv(path, out_rows)

        meta = {
            "seed": SEED,
            "strategy": "iterstrat",
            "ratios_three_way": ratios,
            "split_named_merges_train_and_val": merge,
            "row_set": "labels.csv filtered to images with >=1 LP tag",
            "source_labels": ms.DEFAULT_LABELS.name,
            "label_positives_total": total_pos,
            **stats,
            "verified": ok,
        }
        (path.with_suffix(".meta.json")).write_text(json.dumps(meta, indent=1),
                                                    encoding="utf-8")
        summary[name] = (ok, stats, problems, path)
        all_ok = all_ok and ok

        print("%s  %s" % (name, "OK" if ok else "FAILED"))
        print("   split       : %s" % stats["images_per_split"])
        print("   split_named : %s" % stats["images_per_split_named"])
        print("   drift vs proportional target: %s"
              % {k: "%.1f%%" % (v * 100) for k, v in stats["worst_per_class_drift_vs_target"].items()})
        print("   group leaks : %d" % stats["group_split_leaks"])
        for p in problems:
            print("   PROBLEM: %s" % p)
        print()

    # rare-class test counts, the number that decides how much a metric can be trusted
    print("Folded_Lens (178 total) positives held out for testing:")
    for name, _r, _m in SCHEMES:
        s = summary[name][1]
        test_counts = s["positives_per_split"].get("test", {})
        print("   %-18s test=%3d  val=%3d  train=%3d"
              % (name, test_counts.get("P1_FL", 0),
                 s["positives_per_split"].get("val", {}).get("P1_FL", 0),
                 s["positives_per_split"].get("train", {}).get("P1_FL", 0)))

    print("\nall schemes verified: %s" % all_ok)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
