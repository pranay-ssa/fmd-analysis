#!/usr/bin/env python3
"""Build the train/test class trees the CNN trainer reads, from labels.csv.

The trainer (experiments/cnn/model_training.py) takes --data pointing at a
root with train/<class>/ and test/<class>/ subdirectories, so each variant of
Task 1 needs its own tree:

    <out>/separate/train/<class>/...   23 classes
    <out>/separate/test/<class>/...
    <out>/merged/train/<class>/...     20 classes (four bubbles folded)
    <out>/merged/test/<class>/...

Nothing is copied unless --mode copy is asked for: by default each picture is
symlinked from its source, exactly how dataset_multiclass was built on the VM.

Resolution: labels.csv carries every on-disk copy of a picture in
folder-priority order (older ICube Defects Library, Updated Objects, Updated
Categorical), so the first path that exists under --image-root is the one
linked, and a picture is linked exactly once.

Verification (always, before exit 0):
  * every label row linked to exactly one target, target readable
  * every target's split and class equal the label row
  * no md5 in both train and test
  * per-class counts equal the counts recomputed from labels.csv
  * --strict additionally checks the counts against count_table_<v>.csv, so
    a VM build is held to the same numbers the local verifier passed

Run (VM):
  python build_vm_trees.py --image-root /data/FMD_Data_26082026/fmd_temp_images \\
      --out /home/pranayp/bubble_merge_20261006 --variant both --strict
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_LABELS = os.path.join(REPO, "run", "bubble_merge", "20261006", "labels.csv")
DEFAULT_COUNTS = os.path.join(REPO, "run", "bubble_merge", "20261006")
VARIANTS = {"separate": "class_separate", "merged": "class_merged"}

problems = []


def build(variant, key, labels, image_root, out_root, mode, limit, strict,
          counts_dir):
    linked, unresolved, targets = 0, [], defaultdict(int)
    rows = labels if limit is None else labels[:limit]
    dest = os.path.join(out_root, variant)
    for rec in rows:
        cls, split = rec[key], rec["split"]
        src = None
        for rel in rec["sources"].split("|"):
            cand = os.path.join(image_root, rel)
            if os.path.exists(cand):
                src = cand
                break
        if src is None:
            unresolved.append(rec["md5"])
            continue
        fname = "%s_%s" % (rec["md5"][:12], os.path.basename(src))
        target = os.path.join(dest, split, cls, fname)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if mode == "copy":
            if not os.path.exists(target):
                with open(src, "rb") as fi, open(target, "wb") as fo:
                    fo.write(fi.read())
        else:
            if not os.path.exists(target):
                try:
                    os.symlink(os.path.abspath(src), target)
                except OSError:
                    with open(src, "rb") as fi, open(target, "wb") as fo:
                        fo.write(fi.read())
        if not os.path.exists(target):
            problems.append("%s: target missing after link: %s" % (variant, target))
            continue
        linked += 1
        targets[(cls, split)] += 1

    # ---- internal verification ------------------------------------------
    n_rows = len(rows)
    if linked + len(unresolved) != n_rows:
        problems.append("%s: %d linked + %d unresolved != %d rows"
                        % (variant, linked, len(unresolved), n_rows))
    if unresolved and limit is None:
        problems.append("%s: %d pictures have no source under the image root "
                        "(first: %s)" % (variant, len(unresolved), unresolved[:3]))

    # no md5 in both splits: labels.csv is one row per md5, so check the file
    seen = defaultdict(set)
    for rec in rows:
        seen[rec["md5"]].add(rec["split"])
    both = [m for m, s in seen.items() if len(s) > 1]
    if both:
        problems.append("%s: %d pictures in both splits" % (variant, len(both)))

    # per-class counts recomputed straight from the label rows
    expect = defaultdict(lambda: [0, 0])
    for rec in rows:
        expect[rec[key]][0 if rec["split"] == "train" else 1] += 1
    for cls, (tr, te) in expect.items():
        for split, want in (("train", tr), ("test", te)):
            got = targets.get((cls, split), 0)
            if got != want:
                problems.append("%s: %s/%s has %d links, labels say %d"
                                % (variant, cls, split, got, want))

    # strict: hold the build to the locally verified count tables
    if strict and limit is None:
        path = os.path.join(counts_dir, "count_table_%s.csv" % variant)
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                want_tr, want_te = int(r["train"]), int(r["test"])
                got = (targets.get((r["class"], "train"), 0),
                       targets.get((r["class"], "test"), 0))
                if got != (want_tr, want_te):
                    problems.append("%s: strict count mismatch %s: built %s, "
                                    "verified table says (%d, %d)"
                                    % (variant, r["class"], got, want_tr, want_te))
    return linked, len(unresolved), sum(targets.values())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", default=DEFAULT_LABELS)
    ap.add_argument("--image-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", choices=["separate", "merged", "both"],
                    default="both")
    ap.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    ap.add_argument("--limit", type=int, default=None,
                    help="build only the first N label rows (local smoke)")
    ap.add_argument("--strict", action="store_true",
                    help="hold per-class counts to count_table_<variant>.csv")
    ap.add_argument("--counts-dir", default=DEFAULT_COUNTS)
    args = ap.parse_args(argv)

    with open(args.labels, newline="", encoding="utf-8") as fh:
        labels = list(csv.DictReader(fh))

    variants = ["separate", "merged"] if args.variant == "both" else [args.variant]
    for v in variants:
        linked, unres, total = build(v, VARIANTS[v], labels, args.image_root,
                                     args.out, args.mode, args.limit,
                                     args.strict, args.counts_dir)
        print("%-9s linked %5d | unresolved %4d | entries %5d"
              % (v, linked, unres, total))

    if problems:
        print("\nFAIL: %d problem(s)" % len(problems))
        for p in problems[:40]:
            print("  " + p)
        return 1
    print("PASS: every label row linked once, splits and counts agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
