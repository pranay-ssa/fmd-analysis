#!/usr/bin/env python3
"""
Single-Scale Split Builder + Packager
======================================

Like build_lens_presentation_split.py but serves BOTH train and test from
SINGLE-size crops (single-scale dataset, as the lead requested). Split is
stratified on the source image (seed 42, sklearn) so an image is in train
XOR test — identical membership policy to the multi-train/single-test run.
Only the crop source changes: train is now single-size too, not multi.

USAGE
    python3 build_lens_presentation_split_single.py \
        --single /home/pranayp/fmd_crop_output/single-size_fixed_crop \
        --out    /home/pranayp/lens_presentation_dataset_single_20260903 \
        --date   20260903 --test-ratio 0.2 --seed 42

OUTPUT (under --out)
    split.csv             one row per image: source,class,split,single_crop
    train/<Class>/...     SINGLE crop files (hard links)
    test/<Class>/...      SINGLE crop files (hard links)
    split_report.json     per-class train/test counts + totals
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
import sys
from pathlib import Path

try:
    from sklearn.model_selection import train_test_split
    HAVE_SKLEARN = True
except Exception:
    HAVE_SKLEARN = False

# The 12 Lens Presentation (classification) classes - box-free, image-level.
LENS_PRESENTATION_CLASSES = [
    "Bubble Scatter",
    "Cavity Off Center",
    "Dirty Camera",
    "Dirty Strobe",
    "HEMA Obstruction",
    "Lens Off Center",
    "Low Dose Obstructing Region of Interest",
    "Missing Lens",
    "Missing Primary Package",
    "Multiple Lenses",
    "Package Misalignment",
    "View Obstructed",
]


def stratified_split(files_by_class: dict[str, list[str]],
                     test_ratio: float, seed: int) -> dict[str, str]:
    """Return {source_image: 'train'|'test'} stratified on the class label."""
    images, labels = [], []
    for cls, files in files_by_class.items():
        for f in files:
            images.append(f)
            labels.append(cls)

    if HAVE_SKLEARN:
        tr_idx, te_idx = train_test_split(
            range(len(images)), test_size=test_ratio,
            random_state=seed, stratify=labels)
        tr_set = {images[i] for i in tr_idx}
        te_set = {images[i] for i in te_idx}
    else:
        random.seed(seed)
        by_cls: dict[str, list[str]] = {}
        for img, lbl in zip(images, labels):
            by_cls.setdefault(lbl, []).append(img)
        tr_set, te_set = set(), set()
        for lbl, lst in by_cls.items():
            lst = lst[:]
            random.shuffle(lst)
            n_test = max(1, round(len(lst) * test_ratio))
            te_set.update(lst[:n_test])
            tr_set.update(lst[n_test:])
    return {img: ("train" if img in tr_set else "test") for img in images}


def build(args) -> int:
    single_root = Path(args.single)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # -- 1. Collect per-class source stems from the single crops -----------
    files_by_class: dict[str, list[str]] = {}
    skipped: list[str] = []
    for cls in LENS_PRESENTATION_CLASSES:
        d = single_root / f"{cls}_{args.date}"
        if not d.is_dir():
            skipped.append(f"{cls}: single dir missing ({d})")
            continue
        files_by_class[cls] = sorted(
            f[: -len("_crop.bmp")] + ".bmp"
            for f in os.listdir(d)
            if f.lower().endswith(".bmp") and f.endswith("_crop.bmp"))

    total = sum(len(v) for v in files_by_class.values())
    if total == 0:
        print("ERROR: no single crops found - check --single/--date paths")
        return 1
    print(f"Single source images across {len(files_by_class)} LP classes: {total}")

    # -- 2. Stratified split by source image ------------------------------
    split_map = stratified_split(files_by_class, args.test_ratio, args.seed)

    # -- 3. Build train/test trees, BOTH hard-linked from single crops -----
    for cls in LENS_PRESENTATION_CLASSES:
        (out / "train" / cls).mkdir(parents=True, exist_ok=True)
        (out / "test" / cls).mkdir(parents=True, exist_ok=True)

    rows = []
    n_hard = n_copy = 0
    for cls in LENS_PRESENTATION_CLASSES:
        d = single_root / f"{cls}_{args.date}"
        for src_bmp in files_by_class.get(cls, []):
            stem = src_bmp[: -len(".bmp")]
            where = split_map[src_bmp]
            src = d / f"{stem}_crop.bmp"
            dst = out / where / cls / f"{stem}_crop.bmp"
            if not src.exists():
                rows.append({"source": src_bmp, "class": cls, "split": where,
                             "single_crop": f"{stem}_crop.bmp", "error": "missing_src"})
                continue
            if dst.exists():
                rows.append({"source": src_bmp, "class": cls, "split": where,
                             "single_crop": f"{stem}_crop.bmp", "link": "exists"})
                continue
            try:
                os.link(src, dst)
                n_hard += 1
                link = "hardlink"
            except OSError:
                shutil.copy2(src, dst)
                n_copy += 1
                link = "copy"
            rows.append({"source": src_bmp, "class": cls, "split": where,
                         "single_crop": f"{stem}_crop.bmp", "link": link})

    # -- 4. split.csv -------------------------------------------------------
    with (out / "split.csv").open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=[
            "source", "class", "split", "single_crop", "link"])
        wtr.writeheader()
        for r in rows:
            wtr.writerow(r)

    # -- 5. Report -----------------------------------------------------------
    report = {
        "date": args.date, "test_ratio": args.test_ratio, "seed": args.seed,
        "sklearn_used": HAVE_SKLEARN,
        "mode": "single-only",
        "counts": {"train": sum(1 for r in rows if r["split"] == "train" and r.get("error") is None),
                   "test": sum(1 for r in rows if r["split"] == "test" and r.get("error") is None),
                   "total": total},
        "link_method": {"hardlink": n_hard, "copy": n_copy},
        "skipped_classes": skipped,
        "train_test_by_class": {},
    }
    for cls in LENS_PRESENTATION_CLASSES:
        train_n = sum(1 for r in rows if r["class"] == cls and r["split"] == "train"
                      and r.get("error") is None)
        test_n = sum(1 for r in rows if r["class"] == cls and r["split"] == "test"
                     and r.get("error") is None)
        report["train_test_by_class"][cls] = {"train": train_n, "test": test_n,
                                              "total": train_n + test_n}
    with (out / "split_report.json").open("w") as fh:
        json.dump(report, fh, indent=2)

    print("\n===== SPLIT REPORT (single-scale) =====")
    print(f"source images : {total}")
    print(f"train={report['counts']['train']} test={report['counts']['test']}")
    print(f"link method   : hardlink={n_hard} copy={n_copy}")
    for cls, d in report["train_test_by_class"].items():
        print(f"  {cls:44s} train={d['train']:>4} test={d['test']:>3} total={d['total']}")
    print(f"\nsplit.csv -> {out / 'split.csv'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Single-scale split builder")
    ap.add_argument("--single", required=True, type=Path,
                    help="single-size_fixed_crop base dir")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--date", default="20260903")
    ap.add_argument("--test-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    return build(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
