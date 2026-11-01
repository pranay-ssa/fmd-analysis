#!/usr/bin/env python3
"""Build the 6-class split dataset for bubble_full_merge (2026-10-15).

DECISIONS (confirmed with the user):
  * ONE fresh image-level 70/30 split, seed 42, stratified on the merged
    6-class label. NOT reused from the 20261008 run: the dataset grew.
  * Crops inherit their image's side: no image in both sides.
  * Single arm, tree at exp/{train,test}/<class>/*.bmp.
  * Stratification rule copied verbatim from the 20261008 build_splits.py
    (round-half-up test share, min 1 test image when the stratum allows,
    single-image strata stay in train) so the only change vs the previous
    wing is the dataset itself.

Reads crops_manifest.csv from --crops. Writes under --out:
  exp/{train,test}/<class>/*.bmp    (copies; --no-copy symlinks on the VM)
  split_images.csv                  image -> split + merged label
  counts.csv, split_report.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
from collections import defaultdict


def stratified_image_split(images, labels, test_ratio, seed):
    """Verbatim from experiments/bubble_merge_crops/build_splits.py."""
    by_label = defaultdict(list)
    for im in images:
        by_label[labels[im]].append(im)
    rng = random.Random(seed)
    assign = {}
    for lab, ims in sorted(by_label.items()):
        ims = list(ims)
        rng.shuffle(ims)
        n_test = int(round(len(ims) * test_ratio))
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

    img_raw = defaultdict(set)
    for r in rows:
        img_raw[r["source_image"]].add(r["class"])

    # stratification label: merged class of the image (first sorted class for
    # the rare multi-class image, same stability rule as the previous wing)
    img_label = {im: sorted(raws)[0] for im, raws in img_raw.items()}
    images = sorted(img_raw)
    assign = stratified_image_split(images, img_label, args.test_ratio, args.seed)

    n_tr = sum(1 for v in assign.values() if v == "train")
    n_te = sum(1 for v in assign.values() if v == "test")
    print("split: %d images -> train %d / test %d (seed %d)"
          % (len(images), n_tr, n_te, args.seed))

    with open(os.path.join(args.out, "split_images.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source_image", "split", "class", "raw_classes"])
        for im in images:
            w.writerow([im, assign[im], img_label[im],
                        ";".join(sorted(img_raw[im]))])

    base = os.path.join(args.out, "exp")
    per = defaultdict(lambda: {"ims": set(), "crops": 0,
                               "ims_tr": set(), "crops_tr": 0,
                               "ims_te": set(), "crops_te": 0})
    counts_rows = [["experiment", "class", "images_train", "images_test",
                    "images_total", "crops_train", "crops_test", "crops_total",
                    "avg_crops_per_image"]]
    for r in rows:
        cls = r["class"]
        split = assign[r["source_image"]]
        d = per[cls]
        d["ims"].add(r["source_image"])
        d["crops"] += 1
        if split == "train":
            d["ims_tr"].add(r["source_image"]); d["crops_tr"] += 1
        else:
            d["ims_te"].add(r["source_image"]); d["crops_te"] += 1
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

    report = {}
    for cls in sorted(per, key=lambda c: -per[c]["crops"]):
        d = per[cls]
        avg = d["crops"] / len(d["ims"]) if d["ims"] else 0
        report[cls] = {
            "images": len(d["ims"]), "crops": d["crops"],
            "images_train": len(d["ims_tr"]), "images_test": len(d["ims_te"]),
            "crops_train": d["crops_tr"], "crops_test": d["crops_te"],
            "avg_crops_per_image": round(avg, 2),
        }
        counts_rows.append(["exp", cls, len(d["ims_tr"]), len(d["ims_te"]),
                            len(d["ims"]), d["crops_tr"], d["crops_te"],
                            d["crops"], round(avg, 2)])

    with open(os.path.join(args.out, "counts.csv"), "w", newline="",
              encoding="utf-8") as fh:
        csv.writer(fh).writerows(counts_rows)

    tr = {im for im, s in assign.items() if s == "train"}
    te = {im for im, s in assign.items() if s == "test"}
    overlap = tr & te
    report_meta = {
        "seed": args.seed, "test_ratio": args.test_ratio,
        "images_total": len(images), "images_train": n_tr, "images_test": n_te,
        "crops_total": len(rows),
        "leakage_overlap_images": len(overlap),
        "stratified_on": "merged 6-class label",
    }
    with open(os.path.join(args.out, "split_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"classes": report, "_meta": report_meta}, fh, indent=2)

    print("\n%-22s %7s %7s %7s %7s" % ("class", "img", "crops", "train", "test"))
    for cls, d in sorted(report.items(), key=lambda kv: -kv[1]["crops"]):
        print("%-22s %7d %7d %7d %7d"
              % (cls, d["images"], d["crops"], d["crops_train"], d["crops_test"]))
    print("\nleakage overlap images:", len(overlap))
    print("wrote:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
