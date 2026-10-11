#!/usr/bin/env python3
"""Build the two OOI-crop split datasets for the bubble merge crops wing.

DECISIONS (confirmed with the user):
  * One SHARED image-level 70/30 split, seed 42, stratified on the finer
    7-class labels (cluster SEPARATE). Both experiments reuse this exact
    split, so (a) and (b) are scored on identical test images.
  * Crops inherit their image's split: no image appears in both sides.
  * Two outputs:
      exp_a/  7 classes (Bubble merged from 4, Bubble Cluster its own class)
      exp_b/  6 classes (Bubble merged from 5, cluster folded in)
  * Stretched Bubble never reaches here (dropped by extract_crops).

Reads crops_manifest.csv from --crops. Writes under --out:
  exp_a/{train,test}/<class>/*.bmp     folder-per-class trees (copies)
  exp_b/{train,test}/<class>/*.bmp
  split_images.csv                     image -> split (the shared split)
  counts.csv                           images/crops/avg per class, per exp
  split_report.json                    machine-readable summary

USAGE
  python build_splits.py --crops run/bubble_merge_crops_20261008 \
      --out run/bubble_merge_crops_20261008 --seed 42 --test-ratio 0.30
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
from collections import defaultdict

FOUR = {"Bubble", "Bubble Irregular", "Bubble On 123", "Bubble On Edge"}
CLUSTER = "Bubble Cluster"

# experiment label maps from raw class
def label_a(raw):        # 7 classes, cluster separate
    return "Bubble" if raw in FOUR else raw

def label_b(raw):        # 6 classes, cluster merged
    if raw in FOUR or raw == CLUSTER:
        return "Bubble"
    return raw


def stratified_image_split(images, labels, test_ratio, seed):
    """images: list of str; labels: dict image->str. Returns dict image->split.
    Stratified by label; falls back to putting tiny strata whole in train
    only when a stratum has <2 images (cannot split)."""
    by_label = defaultdict(list)
    for im in images:
        by_label[labels[im]].append(im)
    rng = random.Random(seed)
    assign = {}
    for lab, ims in sorted(by_label.items()):
        ims = list(ims)
        rng.shuffle(ims)
        n_test = int(round(len(ims) * test_ratio))
        # ensure at least 1 test image if stratum allows, and keep >=1 train
        if len(ims) >= 2:
            n_test = max(1, min(n_test, len(ims) - 1))
        else:
            n_test = 0        # single-image stratum: keep in train
        for im in ims[:n_test]:
            assign[im] = "test"
        for im in ims[n_test:]:
            assign[im] = "train"
    return assign


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops", required=True, help="dir holding crops_manifest.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--test-ratio", type=float, default=0.30)
    ap.add_argument("--no-copy", action="store_true",
                    help="symlink instead of copy (VM, same filesystem)")
    args = ap.parse_args()

    man = os.path.join(args.crops, "crops_manifest.csv")
    rows = list(csv.DictReader(open(man, newline="", encoding="utf-8")))
    print("crops in manifest:", len(rows))

    # image -> raw classes present (for stratification use label_a = 7-class)
    img_raw = defaultdict(set)
    for r in rows:
        img_raw[r["source_image"]].add(r["raw_class"])

    # stratification label: the 7-class label of the image. An image can hold
    # several raw classes (8 such images) -> use the FIRST raw class sorted
    # for a stable single stratification key.
    img_label = {im: label_a(sorted(raws)[0]) for im, raws in img_raw.items()}
    images = sorted(img_raw)
    assign = stratified_image_split(images, img_label, args.test_ratio, args.seed)

    n_tr = sum(1 for v in assign.values() if v == "train")
    n_te = sum(1 for v in assign.values() if v == "test")
    print("shared split: %d images -> train %d / test %d (seed %d)"
          % (len(images), n_tr, n_te, args.seed))

    # write shared split
    with open(os.path.join(args.out, "split_images.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source_image", "split", "label_a", "label_b", "raw_classes"])
        for im in images:
            w.writerow([im, assign[im], img_label[im],
                        label_b(sorted(img_raw[im])[0]),
                        ";".join(sorted(img_raw[im]))])

    # build both trees
    report = {}
    counts_rows = [["experiment", "class", "images_train", "images_test",
                    "images_total", "crops_train", "crops_test", "crops_total",
                    "avg_crops_per_image"]]
    for exp_name, labeller in (("exp_a", label_a), ("exp_b", label_b)):
        base = os.path.join(args.out, exp_name)
        per = defaultdict(lambda: {"ims": set(), "crops": 0,
                                   "ims_tr": set(), "crops_tr": 0,
                                   "ims_te": set(), "crops_te": 0})
        for r in rows:
            cls = labeller(r["raw_class"])
            split = assign[r["source_image"]]
            d = per[cls]
            d["ims"].add(r["source_image"])
            d["crops"] += 1
            if split == "train":
                d["ims_tr"].add(r["source_image"]); d["crops_tr"] += 1
            else:
                d["ims_te"].add(r["source_image"]); d["crops_te"] += 1
            # place the file
            dst_dir = os.path.join(base, split, cls)
            os.makedirs(dst_dir, exist_ok=True)
            src = os.path.join(args.crops, "crops", r["crop_file"])
            dst = os.path.join(dst_dir, os.path.basename(r["crop_file"]))
            if os.path.exists(dst):
                os.remove(dst)
            if args.no_copy:
                os.symlink(os.path.abspath(src), dst)
            else:
                shutil.copy2(src, dst)
        report[exp_name] = {}
        for cls in sorted(per, key=lambda c: -per[c]["crops"]):
            d = per[cls]
            avg = d["crops"] / len(d["ims"]) if d["ims"] else 0
            report[exp_name][cls] = {
                "images": len(d["ims"]), "crops": d["crops"],
                "images_train": len(d["ims_tr"]), "images_test": len(d["ims_te"]),
                "crops_train": d["crops_tr"], "crops_test": d["crops_te"],
                "avg_crops_per_image": round(avg, 2),
            }
            counts_rows.append([exp_name, cls, len(d["ims_tr"]), len(d["ims_te"]),
                                len(d["ims"]), d["crops_tr"], d["crops_te"],
                                d["crops"], round(avg, 2)])

    with open(os.path.join(args.out, "counts.csv"), "w", newline="",
              encoding="utf-8") as fh:
        csv.writer(fh).writerows(counts_rows)

    # leakage check: no image in both splits
    tr = {im for im, s in assign.items() if s == "train"}
    te = {im for im, s in assign.items() if s == "test"}
    overlap = tr & te
    report["_meta"] = {
        "seed": args.seed, "test_ratio": args.test_ratio,
        "images_total": len(images), "images_train": n_tr, "images_test": n_te,
        "crops_total": len(rows),
        "leakage_overlap_images": len(overlap),
        "stratified_on": "label_a (7 classes, cluster separate)",
        "shared_split": True,
    }
    with open(os.path.join(args.out, "split_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    # console table
    print("\n%-7s %-22s %7s %7s %7s %7s" % ("exp", "class", "img", "crops",
                                             "train", "test"))
    for exp_name in ("exp_a", "exp_b"):
        for cls, d in sorted(report[exp_name].items(),
                             key=lambda kv: -kv[1]["crops"]):
            print("%-7s %-22s %7d %7d %7d %7d"
                  % (exp_name, cls, d["images"], d["crops"],
                     d["crops_train"], d["crops_test"]))
    print("\nleakage overlap images:", len(overlap))
    print("wrote:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
