#!/usr/bin/env python3
"""
Build a split assignment restricted to a named subset of classes.

The lead highlighted six classes and asked for ResNet50 trained on those alone
(2026-09-17). A picture's side of the split is copied unchanged from the full
per-line assignment, so the subset run and the full run score the same pictures
on the same side and the two are directly comparable.

Inputs
    run/line_splits_20260917/line_<line>/split.csv     (the full assignment)

Outputs (one folder per line, plus a summary)
    run/class_subset_6_20260917/line_<line>/split.csv
    run/class_subset_6_20260917/summary.csv
    run/class_subset_6_20260917/summary.json
    run/class_subset_6_20260917/README.md

    --classes "A" "B" ...   choose a different subset
    --out DIR               choose a different destination
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(REPO, "run", "line_splits_20260917")
LINES = ["L24", "L25", "L26", "L27", "L31"]

HIGHLIGHTED = [
    "Missing Primary Package",
    "Multiple Lenses",
    "Foreign Matter",
    "Lens Off Center",
    "Missing Lens",
    "HEMA Obstruction",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", nargs="+", default=HIGHLIGHTED)
    ap.add_argument("--from-dir", default=FULL)
    ap.add_argument("--out", default=os.path.join(REPO, "run", "class_subset_6_20260917"))
    args = ap.parse_args()

    wanted = list(args.classes)
    os.makedirs(args.out, exist_ok=True)
    summary = {}
    rows_out = []
    total = {"pictures": 0, "train": 0, "test": 0}
    for line in LINES:
        src = os.path.join(args.from_dir, "line_{0}".format(line), "split.csv")
        if not os.path.exists(src):
            print("FAIL: no full assignment at {0}".format(src))
            return 1
        with open(src, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        present = sorted({r["class"] for r in rows})
        absent = [c for c in wanted if c not in present]
        if absent:
            print("FAIL: {0} does not carry {1}".format(line, absent))
            return 1
        keep = [r for r in rows if r["class"] in wanted]
        dst = os.path.join(args.out, "line_{0}".format(line))
        os.makedirs(dst, exist_ok=True)
        with open(os.path.join(dst, "split.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["source_md5", "source_path", "class", "line", "split"])
            w.writeheader()
            w.writerows(sorted(keep, key=lambda r: (r["class"], r["split"], r["source_md5"])))
        per_class = {}
        for cls in wanted:
            sub = [r for r in keep if r["class"] == cls]
            tr = sum(1 for r in sub if r["split"] == "train")
            per_class[cls] = {"pictures": len(sub), "train": tr, "test": len(sub) - tr}
        t = {"pictures": len(keep), "train": sum(v["train"] for v in per_class.values()),
             "test": sum(v["test"] for v in per_class.values())}
        with open(os.path.join(dst, "split_report.json"), "w", encoding="utf-8") as fh:
            json.dump({"line": line, "classes": per_class, "totals": t}, fh, indent=2)
        summary[line] = {"classes": per_class, "totals": t}
        for k in total:
            total[k] += t[k]
        for cls in wanted:
            v = per_class[cls]
            rows_out.append([line, cls, v["pictures"], v["train"], v["test"]])
        print("{0}: {1} pictures, {2} train, {3} test over {4} classes".format(
            line, t["pictures"], t["train"], t["test"], len(wanted)))

    with open(os.path.join(args.out, "summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["line", "class", "pictures", "train", "test"])
        w.writerows(rows_out)
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"classes": wanted, "lines": summary, "totals": total,
                   "source": os.path.relpath(args.from_dir, REPO).replace("\\", "/")}, fh, indent=2)
    with open(os.path.join(args.out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(
            "# Class subset split: the six classes the lead highlighted\n\n"
            "Built by `src/build_class_subset_splits.py` from the full per-line assignment in\n"
            "`run/line_splits_20260917/`. A picture keeps the train or test side it already had, so this\n"
            "subset run and the full run score the same pictures on the same side.\n\n"
            "Classes: {0}\n\n".format(", ".join(wanted)) +
            "| Line | Pictures | Train | Test |\n|---|---|---|---|\n" +
            "".join("| {0} | {1} | {2} | {3} |\n".format(l, summary[l]["totals"]["pictures"],
                                                       summary[l]["totals"]["train"],
                                                       summary[l]["totals"]["test"]) for l in LINES) +
            "| **All five** | **{0}** | **{1}** | **{2}** |\n\n".format(total["pictures"], total["train"],
                                                                      total["test"]) +
            "All six classes are present on all five lines, so every line trains and scores all six.\n"
        )
    print("TOTAL {0} pictures, {1} train, {2} test".format(total["pictures"], total["train"], total["test"]))
    print("written to {0}".format(os.path.relpath(args.out, REPO).replace("\\", "/")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
