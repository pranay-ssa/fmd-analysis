#!/usr/bin/env python3
"""
Lens Presentation Dataset Split Builder + Packager
====================================================

Builds the stratified train/test split for the Lens Presentation
classification model and packages it into folder-per-class trees that the
notebooks' image_dataset_from_directory consumes.

SPLIT POLICY (locked, reproducible):
  * Split is done at the SOURCE IMAGE level, STRATIFIED on the class label.
    An image goes to train XOR test - never both.
  * TRAIN is served from the MULTI-size crops (the model learns multi-size).
  * TEST is served from the SINGLE-size crops (evaluation on production-style
    single-size). Because split is by source image and each image has exactly
    one crop in each mode, no image's two crops ever span the split.
  * Split is saved to disk (split.csv) and reused by every model run.
  * random_state fixed -> identical split on every invocation.

USAGE
-----
    python3 build_lens_presentation_split.py \
        --multi  /home/pranayp/fmd_crop_output/multi_size_crop \
        --single /home/pranayp/fmd_crop_output/single_size_crop \
        --out    /home/pranayp/lens_presentation_dataset \
        --date   20260902 \
        --test-ratio 0.2 --seed 42

OUTPUT (under --out)
    split.csv        one row per image: source,class,split,multi_crop,single_crop
    train/<Class>/  ...  MULTI crop files (hard links)
    test/<Class>/   ...  SINGLE crop files (hard links)
    split_report.json   per-class train/test counts + totals

Hard links are used so nothing is duplicated on disk and provenance to the
VM crop output is preserved. Falls back to file copy if the filesystem
does not support hard links.
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
        # Deterministic fallback (seeded random) if sklearn is unavailable.
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


def crop_path(manifest_dir: Path, stem: str) -> Path:
    """Path of the _crop.bmp for a source image stem in a mode dir."""
    return manifest_dir / f"{stem}_crop.bmp"


def build(args) -> int:
    multi_root = Path(args.multi)
    single_root = Path(args.single)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # -- 1. Collect per-class source images from the multi manifests. --------
    # The multi and single dirs are 1:1 (verified). We key on the source image
    # stem (derived from the crop filename); a stem maps to both crops.
    files_by_class: dict[str, list[str]] = {}
    skipped: list[str] = []
    for cls in LENS_PRESENTATION_CLASSES:
        multi_dir = multi_root / f"{cls}_{args.date}"
        single_dir = single_root / f"{cls}_{args.date}"
        if not multi_dir.is_dir() or not single_dir.is_dir():
            skipped.append(f"{cls}: one of the mode dirs missing (multi={multi_dir.is_dir()}, single={single_dir.is_dir()})")
            continue
        stems = []
        for f in os.listdir(multi_dir):
            if f.lower().endswith(".bmp") and f.endswith("_crop.bmp"):
                # source image stem = filename minus _crop.bmp
                stems.append(f[: -len("_crop.bmp")])
        # Only keep images that have BOTH a multi and a single crop.
        paired = []
        for st in sorted(stems):
            if single_dir.joinpath(f"{st}_crop.bmp").exists():
                paired.append(st + ".bmp")   # back to source filename for labels
        files_by_class[cls] = paired

    total = sum(len(v) for v in files_by_class.values())
    if total == 0:
        print("ERROR: no paired crops found - check --multi/--single/--date paths")
        return 1
    print(f"Paired source images across {len(files_by_class)} LP classes: {total}")
    for c, v in files_by_class.items():
        print(f"  {c:44s} {len(v):>4}")

    # -- 2. Stratified split by source image. -------------------------------
    split_map = stratified_split(files_by_class, args.test_ratio, args.seed)

    # -- 3. Build train/test folder trees with MULTI(train)/SINGLE(test). ----
    for cls in LENS_PRESENTATION_CLASSES:
        (out / "train" / cls).mkdir(parents=True, exist_ok=True)
        (out / "test" / cls).mkdir(parents=True, exist_ok=True)

    rows = []
    n_hard = n_copy = 0
    for cls in LENS_PRESENTATION_CLASSES:
        multi_dir = multi_root / f"{cls}_{args.date}"
        single_dir = single_root / f"{cls}_{args.date}"
        for src_bmp in files_by_class.get(cls, []):
            stem = src_bmp[: -len(".bmp")]
            where = split_map[src_bmp]
            if where == "train":
                src = crop_path(multi_dir, stem)
                dst = out / "train" / cls / f"{stem}_crop.bmp"
            else:
                src = crop_path(single_dir, stem)
                dst = out / "test" / cls / f"{stem}_crop.bmp"
            if not src.exists():
                rows.append({"source": src_bmp, "class": cls, "split": where,
                             "multi_crop": multi_dir.name + "/" + stem + "_crop.bmp",
                             "single_crop": single_dir.name + "/" + stem + "_crop.bmp",
                             "error": "missing_src"})
                continue
            if dst.exists():
                rows.append({"source": src_bmp, "class": cls, "split": where,
                             "multi_crop": multi_dir.name + "/" + stem + "_crop.bmp",
                             "single_crop": single_dir.name + "/" + stem + "_crop.bmp",
                             "link": "exists"})
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
                         "multi_crop": multi_dir.name + "/" + stem + "_crop.bmp",
                         "single_crop": single_dir.name + "/" + stem + "_crop.bmp",
                         "link": link})

    # -- 4. Write split.csv -------------------------------------------------
    with (out / "split.csv").open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=[
            "source", "class", "split", "multi_crop", "single_crop", "link"])
        wtr.writeheader()
        for r in rows:
            wtr.writerow(r)

    # -- 5. Report ----------------------------------------------------------
    def count_tree(sub):
        d = out / sub
        return sum(1 for c in LENS_PRESENTATION_CLASSES
                   for _ in (d / c).iterdir()) if d.is_dir() else 0

    train_n = count_tree("train")
    test_n = count_tree("test")
    report = {
        "date": args.date, "test_ratio": args.test_ratio, "seed": args.seed,
        "sklearn_used": HAVE_SKLEARN,
        "classes": {c: {"total": len(files_by_class.get(c, []))} for c in LENS_PRESENTATION_CLASSES},
        "counts": {"train": train_n, "test": test_n,
                   "total": train_n + test_n,
                   "source_total": total},
        "link_method": {"hardlink": n_hard, "copy": n_copy},
        "skipped_classes": skipped,
        "train_test_by_class": {},
    }
    for cls in LENS_PRESENTATION_CLASSES:
        td, sed = out / "train" / cls, out / "test" / cls
        trn = sum(1 for _ in td.iterdir()) if td.is_dir() else 0
        ten = sum(1 for _ in sed.iterdir()) if sed.is_dir() else 0
        report["train_test_by_class"][cls] = {"train": trn, "test": ten,
                                              "total": trn + ten}
    with (out / "split_report.json").open("w") as fh:
        json.dump(report, fh, indent=2)

    print("\n===== SPLIT REPORT =====")
    print(f"source images        : {total}")
    print(f"packaged             : train={train_n} test={test_n} total={train_n + test_n}")
    print(f"link method          : hardlink={n_hard} copy={n_copy}")
    print(f"sklearn stratified   : {HAVE_SKLEARN}")
    print("class train/test:")
    for cls, d in report["train_test_by_class"].items():
        print(f"  {cls:44s} train={d['train']:>4} test={d['test']:>3} total={d['total']}")
    if skipped:
        print("SKIPPED classes:", skipped)
    print(f"\nsplit.csv   -> {out / 'split.csv'}")
    print(f"split_report.json -> {out / 'split_report.json'}")
    errs = [r for r in rows if r.get("error")]
    if errs:
        print(f"\nWARNING: {len(errs)} rows had missing source crops:")
        for r in errs[:5]:
            print("  ", r["source"])
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lens Presentation split builder")
    ap.add_argument("--multi", required=True, type=Path,
                    help="multi_size_crop base dir")
    ap.add_argument("--single", required=True, type=Path,
                    help="single_size_crop base dir")
    ap.add_argument("--out", required=True, type=Path,
                    help="output dataset base dir")
    ap.add_argument("--date", default="20260902", help="crop date stamp")
    ap.add_argument("--test-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    return build(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())