"""Step 7: Build a canonical Ultralytics directory-layout dataset.

RESOLVES the baseline-training blocker (HANDOFF 7.2, spec Entry 8): the
path-list layout (train.txt/val.txt) fails to resolve labels for dirs whose
name contains a space (e.g. `Bubble Cluster_20260903`), because Ultralytics'
path-list label resolver cannot pair entries with labels in a separate
`labels/` dir and the dir-scan fallback chokes on the space.

This builds the canonical tree Ultralytics documents for OBB:
    <out>/
      images/train/  <stem>_crop.bmp   (symlinks -> crop_base)
      images/val/    <stem>_crop.bmp
      labels/train/  <stem>_crop.txt   (symlinks -> labels_dir/<stem>.txt)
      labels/val/    <stem>_crop.txt
and writes <out>.yaml pointing `train:`/`val:` at the two image dirs.  A single
recursive scan then pairs each image with its label by sibling filename.  No
image copies (symlinks only); no path-list; space-in-dirname is irrelevant
because the scan never walks the class dirs.

Usage:
    python src/yolo_ooi/07_build_dir_layout.py \
        --labels-dir runs/yolo11/labels \
        --crop-base run/single-size_fixed_crop \
        --train-txt runs/yolo11/train.txt --val-txt runs/yolo11/val.txt \
        --classes-file runs/yolo11/classes.txt \
        --out-dir runs/yolo11/dataset_obb
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels-dir", required=True, help="dir of <stem>.txt YOLO-OBB labels")
    ap.add_argument("--crop-base", required=True,
                    help="dir containing <Class>_<date>/<stem>_crop.bmp")
    ap.add_argument("--train-txt", required=True)
    ap.add_argument("--val-txt", required=True)
    ap.add_argument("--classes-file", required=True, help="one class per line")
    ap.add_argument("--out-dir", required=True,
                    help="destination root (images/ + labels/ created inside)")
    args = ap.parse_args()

    labels_dir = Path(args.labels_dir)
    crop_base = Path(args.crop_base)
    root = Path(args.out_dir)

    total_links = 0
    for split in ("train", "val"):
        imgdir = root / "images" / split
        lbdir = root / "labels" / split
        imgdir.mkdir(parents=True, exist_ok=True)
        lbdir.mkdir(parents=True, exist_ok=True)
        miss_img = miss_lbl = links = 0
        for line in Path(getattr(args, f"{split}_txt")).read_text(
                encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            bmp = crop_base / line
            fname = Path(line).name            # <stem>_crop.bmp
            stem = Path(line).stem             # <stem>_crop
            real = stem[:-5] if stem.endswith("_crop") else stem
            if not bmp.exists():
                miss_img += 1
                continue
            ti = imgdir / fname
            if not ti.exists():
                ti.symlink_to(bmp)
                links += 1
            lf = labels_dir / f"{real}.txt"
            if not lf.exists():
                miss_lbl += 1
                continue
            tl = lbdir / f"{stem}.txt"
            if not tl.exists():
                tl.symlink_to(lf)
                links += 1
        total_links += links
        print(f"{split:5s} img_missing={miss_img:3d} lbl_missing={miss_lbl:3d} "
              f"links={links}")

    # write sibling dataset yaml (absolute path: this tree is machine-specific)
    classes = [ln.strip() for ln in
               Path(args.classes_file).read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    lines = [
        "# YOLO-OBB dataset (canonical dir layout) — built by "
        "src/yolo_ooi/07_build_dir_layout.py",
        f"path: {root.resolve()}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(classes)}",
        "names:",
    ]
    lines += [f"  {i}: {c}" for i, c in enumerate(classes)]
    yaml_path = root.with_suffix(".yaml")
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"total links  : {total_links}")
    print(f"dataset tree : {root.resolve()}")
    print(f"dataset yaml : {yaml_path.resolve()}")


if __name__ == "__main__":
    main()
