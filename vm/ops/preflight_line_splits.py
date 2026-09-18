#!/usr/bin/env python3
"""Preflight: every picture named in a per-line split assignment must exist on
this machine, and the split must carry the class list and counts we expect.

    python3 preflight_line_splits.py --splits /data/.../line_splits_20260917
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", required=True)
    ap.add_argument("--expect-pictures", type=int, default=8402)
    ap.add_argument("--expect-train", type=int, default=5875)
    ap.add_argument("--expect-test", type=int, default=2527)
    args = ap.parse_args()

    lines = sorted(d for d in os.listdir(args.splits) if d.startswith("line_"))
    if len(lines) != 5:
        print("FAIL: expected 5 line folders, found {0}".format(len(lines)))
        return 1
    tot = {"train": 0, "test": 0}
    missing_examples = []
    bad = 0
    for d in lines:
        path = os.path.join(args.splits, d, "split.csv")
        if not os.path.exists(path):
            print("FAIL: {0} has no split.csv".format(d))
            return 1
        counts = defaultdict(lambda: [0, 0])
        dup = set()
        missing = 0
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            key = r["source_md5"]
            if key in dup:
                print("FAIL: {0} lists {1} twice".format(d, key))
                bad += 1
            dup.add(key)
            if r["split"] not in ("train", "test"):
                print("FAIL: {0} bad split value {1}".format(d, r["split"]))
                bad += 1
            counts[r["class"]][0 if r["split"] == "train" else 1] += 1
            if not os.path.exists(r["source_path"]):
                missing += 1
                if len(missing_examples) < 5:
                    missing_examples.append((d, r["source_path"]))
            tot[r["split"]] += 1
        trainn = sum(v[0] for v in counts.values())
        testn = sum(v[1] for v in counts.values())
        print("{0}: {1} rows, {2} classes, train {3}, test {4}, missing files {5}".format(
            d, len(rows), len(counts), trainn, testn, missing))
        if missing:
            bad += 1
    print("total train {0} test {1} pictures {2}".format(tot["train"], tot["test"],
                                                         tot["train"] + tot["test"]))
    if tot["train"] != args.expect_train or tot["test"] != args.expect_test:
        print("FAIL: totals differ from the published 5875 / 2527")
        bad += 1
    for d, p in missing_examples:
        print("missing example [{0}]: {1}".format(d, p))
    print("PREFLIGHT {0}".format("FAILED" if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
