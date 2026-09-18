"""Step 1: Filter Object-of-Interest images from CVAT annotations into a CSV.

An OoI image = an <image> that has at least one <box> annotation.  Presentation
tags (no bbox) are held out.  The CSV uses RELATIVE paths (relative to the crop
base), so it is portable between the local dev machine and the VM.

Usage:
    python src/yolo_ooi/01_filter_ooi.py --annot data/annotations.xml \
        --crop-base run/single-size_fixed_crop --out runs/yolo11/ooi_images.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import parse_annotations, write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annot", required=True, help="CVAT annotations.xml (read-only)")
    ap.add_argument("--crop-base", required=True, help="dir containing <Class>_<date>/crop_manifest.csv + *_crop.bmp")
    ap.add_argument("--out", required=True, help="output ooi_images.csv")
    args = ap.parse_args()

    crop_base = Path(args.crop_base)
    images = parse_annotations(Path(args.annot))

    rows = []
    n_total = 0
    n_ooi = 0
    n_boxes = 0
    classes_seen = {}
    missing_crop = []  # OoI images with no matching crop window on disk

    for img in images:
        n_total += 1
        if not img["boxes"]:
            continue  # presentation tag, hold out
        n_ooi += 1
        n_boxes += len(img["boxes"])
        classes_seen[img["class"]] = classes_seen.get(img["class"], 0) + 1

        # verify the crop manifest exists for this class (the fixed-crop run)
        candidates = sorted(crop_base.glob(f"{img['class']}_*/crop_manifest.csv"))
        has_crop_dir = any(candidates)
        if candidates:
            # relative path to the crop bmp (structure: <Class>_<date>/<stem>_crop.bmp)
            crop_dir = candidates[0].parent.name
            rel_crop = f"{crop_dir}/{img['stem']}_crop.bmp"
        else:
            rel_crop = ""
            missing_crop.append(img["stem"])

        rows.append({
            "image_id": img["name"],
            "class": img["class"],
            "stem": img["stem"],
            "n_boxes": len(img["boxes"]),
            "src_w": img["width"],
            "src_h": img["height"],
            "crop_relpath": rel_crop,
            "has_crop_dir": "yes" if candidates else "no",
        })

    write_csv(Path(args.out), rows, list(rows[0].keys()) if rows else [])

    print(f"XML images total      : {n_total}")
    print(f"OoI images (>=1 box)  : {n_ooi}")
    print(f"total bboxes          : {n_boxes}")
    print(f"avg bboxes/image      : {n_boxes / max(n_ooi,1):.2f}")
    print(f"OoI classes           : {len(classes_seen)}")
    print(f"crop base             : {crop_base}")
    print(f"OoI images with NO crop dir on disk: {len(missing_crop)}")
    if missing_crop:
        print("  e.g.", missing_crop[:5])
    print(f"Wrote                 : {Path(args.out)}")


if __name__ == "__main__":
    main()