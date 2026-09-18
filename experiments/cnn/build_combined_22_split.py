#!/usr/bin/env python3
"""Combine ALL 22 defect classes into one train/test set for a single 22-class
classifier, 80-20 stratified by source image (seed 42, sklearn), single-size crops.

Mirrors build_lens_presentation_split_single.py but over the full 22-class set
the lead requested (merge OOI + Lens Presentation into one classification task).

USAGE
    python3 build_combined_22_split.py \
        --single /home/pranayp/fmd_crop_output/single-size_fixed_crop \
        --out    /home/pranayp/combined_dataset_single_20260908 \
        --date   20260903 --test-ratio 0.2 --seed 42

OUTPUT (under --out)
    split.csv             one row per image: source,class,split,single_crop
    train/<Class>/...     single crops (hard links)
    test/<Class>/...      single crops (hard links)
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

# All 22 ICube defect classes (10 OOI detection + 12 Lens Presentation).
ALL_22_CLASSES = [
    # OOI (presented with bounding boxes)
    "Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123",
    "Bubble On Edge", "Extraneous Polymer", "Fiber", "Foreign Matter",
    "HEMA Fragment", "Wet Package",
    # Lens Presentation (image-level)
    "Bubble Scatter", "Cavity Off Center", "Dirty Camera", "Dirty Strobe",
    "HEMA Obstruction", "Lens Off Center", "Low Dose Obstructing Region of Interest",
    "Missing Lens", "Missing Primary Package", "Multiple Lenses",
    "Package Misalignment", "View Obstructed",
]


def stratified_split(files_by_class: dict[str, list[str]],
                     test_ratio: float, seed: int,
                     min_train_per_class: int = 2) -> dict[str, str]:
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
            # keep at least min_train_per_class in train for the tiny classes
            n_test = min(n_test, len(lst) - min_train_per_class)
            te_set.update(lst[:n_test])
            tr_set.update(lst[n_test:])
    return {img: ("train" if img in tr_set else "test") for img in images}


def build(args) -> int:
    single_root = Path(args.single)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # -- 1. Collect per-class source stems from single crops ----------------
    files_by_class: dict[str, list[str]] = {}
    skipped: list[str] = []
    discovered = sorted(
        d.name for d in single_root.iterdir()
        if d.is_dir() and d.name.endswith(f"_{args.date}"))
    for cls in ALL_22_CLASSES:
        d = single_root / f"{cls}_{args.date}"
        if not d.is_dir():
            skipped.append(f"{cls}: single dir missing ({d})")
            continue
        files_by_class[cls] = sorted(
            f[: -len("_crop.bmp")] + ".bmp"
            for f in os.listdir(d)
            if f.lower().endswith("_crop.bmp"))

    # sanity: discovered dirs should equal our 22 expected classes
    expected = {f"{c}_{args.date}" for c in ALL_22_CLASSES}
    unexpected = [name for name in discovered if name not in expected]
    if unexpected:
        print("WARNING: unexpected class dirs:", unexpected)

    total = sum(len(v) for v in files_by_class.values())
    if total == 0:
        print("ERROR: no single crops found - check --single/--date paths")
        return 1
    print(f"Single source images across {len(files_by_class)} of 22 classes: {total}")

    # -- 2. Stratified split by source image --------------------------------
    split_map = stratified_split(files_by_class, args.test_ratio, args.seed)

    # -- 3. Build train/test trees, hard-linked from single crops -----------
    for cls in files_by_class:
        (out / "train" / cls).mkdir(parents=True, exist_ok=True)
        (out / "test" / cls).mkdir(parents=True, exist_ok=True)

    rows = []
    n_hard = n_copy = 0
    for cls, files in files_by_class.items():
        d = single_root / f"{cls}_{args.date}"
        for src_bmp in files:
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

    # -- 4. split.csv --------------------------------------------------------
    with (out / "split.csv").open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=[
            "source", "class", "split", "single_crop", "link"])
        wtr.writeheader()
        for r in rows:
            wtr.writerow(r)

    # -- 5. Report ------------------------------------------------------------
    ok_rows = [r for r in rows if r.get("error") is None]
    train_imgs = {r["source"] for r in ok_rows if r["split"] == "train"}
    test_imgs = {r["source"] for r in ok_rows if r["split"] == "test"}
    report = {
        "date": args.date, "test_ratio": args.test_ratio, "seed": args.seed,
        "sklearn_used": HAVE_SKLEARN, "n_classes": len(files_by_class),
        "mode": "combined-22-single",
        "counts": {"train": len(train_imgs), "test": len(test_imgs),
                   "total": total, "total_placed": len(ok_rows)},
        "disjoint_train_test": len(train_imgs & test_imgs) == 0,
        "link_method": {"hardlink": n_hard, "copy": n_copy},
        "skipped_classes": skipped,
        "train_test_by_class": {},
    }
    for cls in files_by_class:
        train_n = sum(1 for r in ok_rows if r["class"] == cls and r["split"] == "train")
        test_n = sum(1 for r in ok_rows if r["class"] == cls and r["split"] == "test")
        report["train_test_by_class"][cls] = {"train": train_n, "test": test_n,
                                              "total": train_n + test_n}
    with (out / "split_report.json").open("w") as fh:
        json.dump(report, fh, indent=2)

    print("\n===== SPLIT REPORT (combined 22-class, single-scale) =====")
    print(f"source images : {total}  placed: {len(ok_rows)}")
    print(f"train={len(train_imgs)} test={len(test_imgs)} "
          f"disjoint={report['disjoint_train_test']}")
    print(f"link method   : hardlink={n_hard} copy={n_copy} sklearn={HAVE_SKLEARN}")
    for cls, d in report["train_test_by_class"].items():
        print(f"  {cls:44s} train={d['train']:>4} test={d['test']:>3} total={d['total']}")
    print(f"\nsplit.csv -> {out / 'split.csv'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Combined 22-class split builder")
    ap.add_argument("--single", required=True, type=Path,
                    help="single-size_fixed_crop base dir")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--date", default="20260903")
    ap.add_argument("--test-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    return build(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())