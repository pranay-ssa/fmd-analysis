#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a class-agnostic DETECTION dataset from our existing cropped OoI set.

Source: /home/pranayp/yolo_ooi/dataset_obb (canonical OBB layout, frozen 346/88 split).
Output: /home/pranayp/yolo_ooi/crop_detect_dataset
  - images/{train,val}  -> dir-symlinks to dataset_obb/images/{train,val} (reuse crop symlinks, no dup)
  - labels/{train,val}  -> new axis-aligned "0 cx cy w h" (AABB of the 8 OBB corners), normalized, nc=1
  - data.yaml           -> project-origin canonical layout
Mirrors the teammate's stock-detection protocol but on OUR single-size fixed crops.
"""
from pathlib import Path

SRC = Path("/home/pranayp/yolo_ooi/dataset_obb")
DST = Path("/home/pranayp/yolo_ooi/crop_detect_dataset")


def link_images():
    (DST / "images").mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        dest = DST / "images" / split
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(SRC / "images" / split, target_is_directory=True)


def clamp01(v):
    return max(0.0, min(1.0, v))


def convert_labels():
    for split in ("train", "val"):
        outdir = DST / "labels" / split
        outdir.mkdir(parents=True, exist_ok=True)
        srcdir = SRC / "labels" / split
        n_files = n_boxes = 0
        for lbl in sorted(srcdir.glob("*.txt")):
            lines = []
            for line in lbl.read_text().splitlines():
                parts = line.split()
                if len(parts) != 9:
                    continue
                _, x1, y1, x2, y2, x3, y3, x4, y4 = [float(t) for t in parts]
                xs = [x1, x2, x3, x4]
                ys = [y1, y2, y3, y4]
                xmin, xmax = clamp01(min(xs)), clamp01(max(xs))
                ymin, ymax = clamp01(min(ys)), clamp01(max(ys))
                cx = (xmin + xmax) / 2.0
                cy = (ymin + ymax) / 2.0
                w = xmax - xmin
                h = ymax - ymin
                lines.append("0 %.6f %.6f %.6f %.6f" % (cx, cy, w, h))
            if lines:
                (outdir / lbl.name).write_text("\n".join(lines) + "\n")
                n_files += 1
                n_boxes += len(lines)
        print("%s: %d label files, %d axis-aligned boxes" % (split, n_files, n_boxes))


def write_yaml():
    (DST / "data.yaml").write_text(
        "path: /home/pranayp/yolo_ooi/crop_detect_dataset\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names:\n"
        "  0: defect\n")


link_images()
convert_labels()
write_yaml()
print("crop_detect_dataset built at", DST)