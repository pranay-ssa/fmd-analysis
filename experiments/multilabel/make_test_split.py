#!/usr/bin/env python3
"""Train/val split for the multi-label pictures that have boxes.

Why 70/30 and not 80/20, and why the unit is 47 pictures rather than 55:

* Detection needs boxes. 47 of the 55 carry at least one box; 8 carry none (4 HEMA pairs where the
  obstruction is a frame-level tag, and 4 others). The 8 are excluded and listed, not silently
  dropped.
* At 47 pictures the training signal is flat: both 33 and 38 training pictures are far below the
  346 the existing detection set uses, so the model lands near its floor either way and six fewer
  pictures change
  little. The measurement is what is fragile here, not the learning. 9 validation pictures (80/20)
  would be almost all Fiber, so five of the six classes would score by absence, and the aggregate
  would carry an interval wide enough to swallow any real difference. 14 validation pictures (70/30)
  buys class coverage on the side where the variance lives, at a cost the training side does not
  notice.
* Stratified by the class in the box file, seeded 42 to match the repo's other splits.
* Whole line clusters are kept on one side where possible, because frames from one capture session
  on one line are near duplicates and a split through them flatters the score.
* A class with fewer than three pictures goes to train whole. A class that appears only in
  validation teaches nothing and cannot be scored meaningfully.
"""
import csv
import os
import random
from collections import Counter, defaultdict

REPO = r"D:\fmd-analysis"
SRC = os.path.join(REPO, "run", "ep_fiber_check", "20260921", "55_boxes_available.csv")
OUT = os.path.join(REPO, "run", "multilabel_split_20260921")
SEED = 42
VAL_SHARE = 0.30

rows = [r for r in csv.DictReader(open(SRC, newline="", encoding="utf-8"))]
boxed = [r for r in rows if int(r["boxes"]) > 0]
unboxed = [r for r in rows if int(r["boxes"]) == 0]
print("pictures: %d total, %d with boxes, %d without" % (len(rows), len(boxed), len(unboxed)))
print("excluded (no box anywhere):")
for r in unboxed:
    print("   %-58s %s" % (r["file_name"], r["folder_labels"]))

rng = random.Random(SEED)
by_class = defaultdict(list)
for r in boxed:
    by_class[r["box_labels"]].append(r)

val, train, plan = [], [], []
for cls in sorted(by_class, key=lambda c: -len(by_class[c])):
    group = by_class[cls]
    n = len(group)
    if n < 3:
        n_val = 0
    else:
        n_val = max(1, round(VAL_SHARE * n))
    # keep whole line clusters together: take from the largest line groups first
    lines = defaultdict(list)
    for r in group:
        lines[r["line"]].append(r)
    order = sorted(lines, key=lambda L: -len(lines[L]))
    chosen = []
    for L in order:
        if len(chosen) >= n_val:
            break
        pool = sorted(lines[L], key=lambda r: r["file_name"])
        rng.shuffle(pool)
        take = min(len(pool), n_val - len(chosen))
        chosen += pool[:take]
    chosen_names = {r["file_name"] for r in chosen}
    val += chosen
    train += [r for r in group if r["file_name"] not in chosen_names]
    plan.append((cls, n, len(chosen), sorted({r["line"] for r in chosen})))

print()
print("%-20s %6s %8s  %s" % ("class in box file", "total", "to val", "lines in val"))
for cls, n, nv, ls in plan:
    print("%-20s %6d %8d  %s" % (cls, n, nv, ",".join(ls)))
print()
print("train %d  val %d  (%.0f per cent validation)" % (len(train), len(val),
                                                        100.0 * len(val) / len(boxed)))
print("boxes: train %d, val %d" % (sum(int(r["boxes"]) for r in train),
                                   sum(int(r["boxes"]) for r in val)))
print("val class mix:", dict(Counter(r["box_labels"] for r in val)))
print("train line mix:", dict(sorted(Counter(r["line"] for r in train).items())))
print("val line mix:", dict(sorted(Counter(r["line"] for r in val).items())))

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "split.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["file_name", "split", "box_label", "line", "boxes", "folder_labels", "note"])
    for r in sorted(train + val, key=lambda r: (r["line"], r["file_name"])):
        split = "val" if r in val else "train"
        w.writerow([r["file_name"], split, r["box_labels"], r["line"], r["boxes"],
                    r["folder_labels"], "excluded: no box" if False else ""])
    for r in unboxed:
        w.writerow([r["file_name"], "excluded", "", r["line"], 0, r["folder_labels"],
                    "no box anywhere"])
for name, subset in (("train.txt", train), ("val.txt", val)):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        for r in sorted(subset, key=lambda r: r["file_name"]):
            fh.write(r["file_name"].rsplit(".", 1)[0] + "_crop.bmp\n")
print()
print("written:", OUT, "-> split.csv, train.txt, val.txt")
