#!/usr/bin/env python3
"""
OoI Dataset Single Builder
==========================

Like `vm/build_lens_presentation_split_single.py` but for Object-of-Interest
(OoI) tags.  Same line-for-line structure as the LP single builder:

  1. Scan <crop_base>/<Class>_<date>/ for *_crop.bmp (same as LP single).
  2. Build files_by_class: dict[str, list[str]] (same shape).
  3. Stratified split, sklearn train_test_split(stratify=labels) (same RNG,
     same seed, same test ratio).
  4. Build folder-per-class trees via hardlinks (same hardlink->copy fallback).
  5. Write split.csv + split_report.json (same schema).

The ONLY structural addition is `--ooi-csv`: the OoI subset is images with
bounding boxes.  Each class dir on disk has some presentation-tag-only samples
(Bubble has 114 bmp, only 113 have boxes; the 1-image delta is presentation).
We intersect the on-disk files with the OoI CSV so the split is over OoI images
only.

USAGE
    python3 build_ooi_dataset_single.py \
        --crop-base run/single-size_fixed_crop \
        --ooi-csv   runs/yolo11/ooi_images.csv \
        --out       run/ooi_dataset_single_20260907 \
        --date      20260903 --test-ratio 0.2 --seed 42

OUTPUT (under --out)
    split.csv             source, class, split, single_crop, link
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


# The 10 Object-of-Interest (OoI) classes -- only images with bounding boxes.
# Verified 2026-09-07 against runs/yolo11/classes.txt + runs/yolo11/dataset.yaml
# + data/annotations.xml (unique <box label> values in OoI subset).
OOI_CLASSES = [
    "Bubble",
    "Bubble Cluster",
    "Bubble Irregular",
    "Bubble On 123",
    "Bubble On Edge",
    "Extraneous Polymer",
    "Fiber",
    "Foreign Matter",
    "HEMA Fragment",
    "Wet Package",
]


def stratified_split(files_by_class: dict[str, list[str]],
                     test_ratio: float, seed: int) -> dict[str, str]:
    """Return {source_image: 'train'|'test'} stratified on the class label.

    Bit-identical to vm/build_lens_presentation_split_single.py:stratified_split.
    """
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
            n_test = round(len(lst) * test_ratio)
            te_set.update(lst[:n_test])
            tr_set.update(lst[n_test:])
    return {img: ("train" if img in tr_set else "test") for img in images}


def build(args) -> int:
    crop_base = Path(args.crop_base)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # -- 1. OoI filter: read ooi_images.csv and build {class: set(stem)} ----
    ooi_csv = Path(args.ooi_csv)
    if not ooi_csv.is_file():
        print(f"ERROR: --ooi-csv not found: {ooi_csv}")
        return 1
    with ooi_csv.open(newline="", encoding="utf-8") as fh:
        ooi_rows = list(csv.DictReader(fh))
    ooi_by_class: dict[str, set[str]] = {}
    for r in ooi_rows:
        if not r.get("class") or not r.get("stem"):
            continue
        ooi_by_class.setdefault(r["class"], set()).add(r["stem"])

    # -- 2. Collect per-class source stems from the single crops -----------
    files_by_class: dict[str, list[str]] = {}
    skipped: list[str] = []
    for cls in OOI_CLASSES:
        d = crop_base / f"{cls}_{args.date}"
        if not d.is_dir():
            skipped.append(f"{cls}: crop dir missing ({d})")
            continue
        ooi_stems = ooi_by_class.get(cls, set())
        if not ooi_stems:
            skipped.append(f"{cls}: no OoI stems in {ooi_csv}")
            continue
        files_by_class[cls] = sorted(
            f[: -len("_crop.bmp")] + ".bmp"
            for f in os.listdir(d)
            if f.lower().endswith(".bmp") and f.endswith("_crop.bmp")
            and f[: -len("_crop.bmp")] in ooi_stems)

    total = sum(len(v) for v in files_by_class.values())
    if total == 0:
        print("ERROR: no OoI crops found - check --crop-base / --ooi-csv / --date paths")
        return 1
    print(f"OoI source images across {len(files_by_class)} classes: {total}")

    # -- 3. Stratified split by source image ------------------------------
    split_map = stratified_split(files_by_class, args.test_ratio, args.seed)

    # -- 4. Build train/test trees, hard-linked from single crops ----------
    for cls in OOI_CLASSES:
        (out / "train" / cls).mkdir(parents=True, exist_ok=True)
        (out / "test"  / cls).mkdir(parents=True, exist_ok=True)

    rows = []
    n_hard = n_copy = 0
    for cls in OOI_CLASSES:
        d = crop_base / f"{cls}_{args.date}"
        for src_bmp in files_by_class.get(cls, []):
            stem = src_bmp[: -len(".bmp")]
            where = split_map[src_bmp]
            src = d / f"{stem}_crop.bmp"
            dst = out / where / cls / f"{stem}_crop.bmp"
            if not src.exists():
                rows.append({"source": src_bmp, "class": cls, "split": where,
                             "single_crop": f"{stem}_crop.bmp", "error": "missing_src"})
                continue
            if dst.exists() or dst.is_symlink():
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

    # -- 5. split.csv (same schema as LP single) ---------------------------
    with (out / "split.csv").open("w", newline="", encoding="utf-8") as fh:
        wtr = csv.DictWriter(fh, fieldnames=[
            "source", "class", "split", "single_crop", "link"])
        wtr.writeheader()
        for r in rows:
            wtr.writerow(r)

    # -- 6. split_report.json ---------------------------------------------
    report = {
        "crop_base": str(crop_base),
        "ooi_csv":   str(ooi_csv),
        "date": args.date,
        "test_ratio": args.test_ratio,
        "seed": args.seed,
        "sklearn_used": HAVE_SKLEARN,
        "mode": "single-only",
        "counts": {
            "train": sum(1 for r in rows if r["split"] == "train" and r.get("error") is None),
            "test":  sum(1 for r in rows if r["split"] == "test"  and r.get("error") is None),
            "total": total,
        },
        "link_method": {"hardlink": n_hard, "copy": n_copy},
        "skipped_classes": skipped,
        "train_test_by_class": {},
    }
    for cls in OOI_CLASSES:
        train_n = sum(1 for r in rows if r["class"] == cls and r["split"] == "train"
                      and r.get("error") is None)
        test_n = sum(1 for r in rows if r["class"] == cls and r["split"] == "test"
                     and r.get("error") is None)
        report["train_test_by_class"][cls] = {"train": train_n, "test": test_n,
                                              "total": train_n + test_n}
    with (out / "split_report.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print("\n===== OoI SPLIT REPORT (single-scale, sklearn stratified) =====")
    print(f"crop base         : {crop_base}")
    print(f"ooi csv           : {ooi_csv}")
    print(f"out dir           : {out}")
    print(f"sklearn_used      : {HAVE_SKLEARN}")
    print(f"source images     : {total}")
    print(f"train={report['counts']['train']} test={report['counts']['test']}")
    print(f"link method       : hardlink={n_hard} copy={n_copy}")
    if skipped:
        print(f"skipped classes   : {len(skipped)}")
    for cls, d in report["train_test_by_class"].items():
        print(f"  {cls:30s} train={d['train']:>4} test={d['test']:>3} total={d['total']:>4}")
    print(f"\nsplit.csv         -> {out / 'split.csv'}")
    print(f"split_report.json -> {out / 'split_report.json'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="OoI single-scale split builder (sklearn stratified)")
    ap.add_argument("--crop-base", required=True, type=Path,
                    help="single-size_fixed_crop base dir (contains <Class>_<date>/)")
    ap.add_argument("--ooi-csv", required=True, type=Path,
                    help="ooi_images.csv (intersect with on-disk crops to get OoI subset)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--date", default="20260903")
    ap.add_argument("--test-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    return build(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
