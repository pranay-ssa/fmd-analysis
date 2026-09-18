#!/usr/bin/env python3
"""
Build the per-line train/test assignments for the five per-line ResNet50 models.

WHAT THIS ADDS
    The 2026-09-17 split table holds counts per class per line. This script turns
    those counts into an actual assignment: one row per picture, saying which
    side of the split it sits on. Nothing else in the repository did that.

RULES (agreed with the team, 2026-09-17)
    * The pool is the 22-class pooled dataset of src/make_line_splits.py, 8,409
      pictures under the clarified rules (HEMA reads as HEMA Fragment, Clear and
      duplicates are not classes).
    * Classes with no test picture on a line are dropped from that line entirely,
      both halves. At 70:30 that is 7 cells, each a single picture, which leaves
      8,402 pictures for the run: 5,875 train and 2,527 test.
    * The split is exact-count stratified: inside each class inside each line the
      pictures are shuffled with seed 42 and exactly round-half-up(n x 0.30) of
      them become the test half. This reproduces the published table cell for
      cell, so the table the lead and the client already have stays true.

OUTPUT (one folder per line)
    run/line_splits_20260917/line_L24/split.csv
        source_md5, source_path, class, line, split
    run/line_splits_20260917/line_L24/split_report.json
        per-class train/test counts, totals, the class list, the seed and the rule
    run/line_splits_20260917/README.md
        what the folders hold and how the assignment was made

    --check  diff the assignment against the published table and print PASS/FAIL
             per cell, then the per-line totals.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from make_line_splits import build_pool, half_up, split_cell  # noqa: E402

SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
TABLE = os.path.join(REPO, "run", "line_eda", "20260917", "all_lines_class_split_70_30_and_80_20.csv")
OUT = os.path.join(REPO, "run", "line_splits_20260917")

VM_ROOT = "/data/FMD_Data_26082026/fmd_temp_images"
# The image library stays on the library account's volume; every experiment reads it
# by path. /home/amd100-user/FMD_Data_26082026 is a symlink to the same place and also
# works, but /data is the stable spelling and is world-readable.
# canonical source folder for a picture: the older library first, then the updated folders
FOLDER_RANK = {
    "ICube Defects Library": 0,
    "Updated ICube Objects 20260915": 1,
    "Updated ICube Categorical Classes 20260915": 2,
}
SEED = 42


def canonical_paths():
    """{md5: (folder, class, basename)} the deterministic source of each picture."""
    best = {}
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        for folder, cls, name, md5, _ in csv.reader(fh):
            if not folder:
                continue
            key = (FOLDER_RANK[folder], cls, name)
            if md5 not in best or key < best[md5]:
                best[md5] = key
    out = {}
    for md5, (rank, cls, name) in best.items():
        folder = [f for f, r in FOLDER_RANK.items() if r == rank][0]
        out[md5] = (folder, cls, name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    pool = build_pool()                       # {md5: (class, line, name)}
    paths = canonical_paths()

    # the class list per line, dropping every cell with no test picture
    cells = defaultdict(lambda: defaultdict(list))
    for md5, (cls, line, _) in pool.items():
        cells[line][cls].append(md5)

    dropped = []
    for line in sorted(cells):
        for cls in list(cells[line]):
            n = len(cells[line][cls])
            if half_up(n, 0.30) == 0:
                dropped.append((line, cls, n))
                del cells[line][cls]

    os.makedirs(OUT, exist_ok=True)
    published = {}
    with open(TABLE, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["class"] != "TOTAL":
                published[(r["line"], r["class"])] = (int(r["pictures"]), int(r["train_70"]), int(r["test_30"]))

    grand = {"train": 0, "test": 0, "pictures": 0}
    report_rows = []
    for line in sorted(cells):
        rng = random.Random(SEED)
        rows, per_class = [], {}
        for cls in sorted(cells[line]):
            md5s = sorted(cells[line][cls])          # sorted first, so the shuffle is reproducible
            rng.shuffle(md5s)
            n_test = half_up(len(md5s), 0.30)
            test = set(md5s[-n_test:]) if n_test else set()
            for md5 in md5s:
                folder, src_cls, name = paths[md5]
                rows.append({
                    "source_md5": md5,
                    "source_path": "{0}/{1}/{2}/{3}".format(VM_ROOT, folder, src_cls, name),
                    "class": cls,
                    "line": line,
                    "split": "test" if md5 in test else "train",
                })
            per_class[cls] = {"pictures": len(md5s), "train": len(md5s) - n_test, "test": n_test}
        line_dir = os.path.join(OUT, "line_{0}".format(line))
        os.makedirs(line_dir, exist_ok=True)
        with open(os.path.join(line_dir, "split.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["source_md5", "source_path", "class", "line", "split"])
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: (r["class"], r["split"], r["source_md5"])))
        tot_train = sum(v["train"] for v in per_class.values())
        tot_test = sum(v["test"] for v in per_class.values())
        with open(os.path.join(line_dir, "split_report.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "line": line,
                "rule": "exact-count stratified: seed 42, test = round-half-up(pictures x 0.30), train = rest",
                "seed": SEED,
                "classes": per_class,
                "totals": {"classes": len(per_class), "pictures": tot_train + tot_test,
                           "train": tot_train, "test": tot_test},
            }, fh, indent=2)
        grand["train"] += tot_train
        grand["test"] += tot_test
        grand["pictures"] += tot_train + tot_test
        report_rows.append([line, len(per_class), tot_train + tot_test, tot_train, tot_test])
        if args.check:
            for cls, v in sorted(per_class.items()):
                want = published.get((line, cls))
                ok = want == (v["pictures"], v["train"], v["test"])
                if not ok:
                    print("FAIL {0} {1}: assignment {2}, table {3}".format(
                        line, cls, (v["pictures"], v["train"], v["test"]), want))
                if (line, cls) not in published:
                    print("FAIL {0} {1}: cell not in the published table".format(line, cls))
    grand["classes"] = sum(r[1] for r in report_rows)

    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(
            "# Per-line split assignments, 2026-09-17\n\n"
            "One folder per production line. `split.csv` is the assignment: one row per picture with its\n"
            "content hash, its source file on the VM, its class, its line and whether it sits in the train\n"
            "or the test half. `split_report.json` holds the per-class counts, the class list and the rule.\n\n"
            "The rule is exact-count stratified: inside each class inside each line the pictures are shuffled\n"
            "with seed 42 and exactly round-half-up(pictures x 0.30) become the test half. It reproduces the\n"
            "published table in `run/line_eda/20260917/all_lines_class_split_70_30_and_80_20.csv` cell for cell.\n\n"
            "Classes with no test picture on a line are dropped from that line entirely, both halves: {0}\n"
            "cells at 70:30. The run therefore covers {1} pictures, {2} train and {3} test.\n".format(
                len(dropped), grand["pictures"], grand["train"], grand["test"])
        )
        for d in dropped:
            fh.write("- dropped: {0} {1} ({2} picture)\n".format(*d))

    print("line   classes  pictures  train  test")
    for r in report_rows:
        print("{0:6s} {1:8d} {2:9d} {3:6d} {4:5d}".format(r[0], r[1], r[2], r[3], r[4]))
    print("TOTAL  {0:8d} {1:9d} {2:6d} {3:5d}".format(grand["classes"], grand["pictures"],
                                                       grand["train"], grand["test"]))
    print("\ndropped cells with no test picture: {0}".format(len(dropped)))
    for d in dropped:
        print("  {0} | {1} | {2} picture".format(*d))
    print("\nwritten to run/line_splits_20260917/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
