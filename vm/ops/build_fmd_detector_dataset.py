#!/usr/bin/env python3
"""Build the Experiment 2 YOLO26 detector dataset on the frozen split.

Reads the split and the annotation of record, writes one image symlink and one
YOLO label file per split picture, and records the counts. The image name is the
content md5, so duplicate file names cannot collide.

Run on the VM, from the repository root or through ssh stdin:

    python3 - --picture-table /tmp/fmd_picture_table.csv --force
"""
import argparse
import csv
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

REPO = Path("/home/pranayp/fmd-analysis")
SPLIT = REPO / "run/split_20261103_v8/split_70_15_15.csv"
LABELS = REPO / "run/eda_full_20261029/resolved_labels.csv"
IMAGES = Path("/data/FMD_Data_26082026/fmd_temp_images")
OUT = Path("/data/FMD_Data_26082026/fmd_detector_20261110")

CLASSES = [
    "Bubble",
    "Bubble Cluster",
    "Wet Package",
    "Fiber",
    "Extraneous Polymer",
    "HEMA",
    "Foreign Matter",
]
CODE_TO_CLASS = {
    "bubble": 0,
    "bubble_irregular": 0,
    "stretched_bubble": 0,
    "bubble_cluster": 1,
    "wet_package": 2,
    "fiber": 3,
    "extraneous_polymer": 4,
    "hema_obstruction": 5,
    "hema_fragment": 5,
    "foreign_matter": 6,
}
EXCLUDED = {"bubble_on_edge", "bubble_on_123"}
SPLITS = ("train", "val", "test")


def read_split():
    split = {}
    with SPLIT.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            md5 = row["picture_md5"].strip()
            part = row["split"].strip()
            if part not in SPLITS:
                raise SystemExit(f"unknown split {part!r} for {md5}")
            if md5 in split and split[md5] != part:
                raise SystemExit(f"{md5} appears in two splits")
            split[md5] = part
    return split


def read_paths(picture_table):
    paths = {}
    with Path(picture_table).open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            paths[row["md5"].strip()] = row["winning_path"].strip()
    return paths


def read_boxes(split):
    boxes = defaultdict(list)
    skipped = Counter()
    outside = 0
    with LABELS.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["shape_kind"].strip() != "box":
                continue
            md5 = row["picture_md5"].strip()
            if md5 not in split:
                outside += 1
                continue
            code = row["canonical_id"].strip()
            if code in EXCLUDED:
                skipped[code] += 1
                continue
            cls = CODE_TO_CLASS.get(code)
            if cls is None:
                skipped[code] += 1
                continue
            try:
                x1 = float(row["xtl"])
                y1 = float(row["ytl"])
                x2 = float(row["xbr"])
                y2 = float(row["ybr"])
            except (TypeError, ValueError):
                skipped["bad_coords"] += 1
                continue
            if x2 <= x1 or y2 <= y1:
                skipped["zero_area"] += 1
                continue
            boxes[md5].append((cls, x1, y1, x2, y2))
    return boxes, skipped, outside


def build(picture_table, force):
    split = read_split()
    paths = read_paths(picture_table)
    boxes, skipped, outside = read_boxes(split)

    missing_paths = [md5 for md5 in split if md5 not in paths]
    if missing_paths:
        raise SystemExit(f"{len(missing_paths)} split pictures have no path in the picture table")

    if OUT.exists():
        if not force:
            raise SystemExit(f"{OUT} exists; pass --force to rebuild")
        shutil.rmtree(OUT)
    for part in SPLITS:
        (OUT / "images" / part).mkdir(parents=True, exist_ok=True)
        (OUT / "labels" / part).mkdir(parents=True, exist_ok=True)

    pics = defaultdict(set)
    box_count = Counter()
    has_boxes = Counter()
    empty_labels = Counter()
    missing_images = []
    bad_size = []

    manifest = (OUT / "manifest.csv").open("w", newline="", encoding="utf-8")
    writer = csv.writer(manifest)
    writer.writerow(["md5", "split", "n_boxes", "classes", "source_path"])

    for i, (md5, part) in enumerate(sorted(split.items()), 1):
        rel = paths[md5]
        src = IMAGES / rel
        if not src.is_file():
            missing_images.append(str(src))
            continue
        try:
            with Image.open(src) as im:
                width, height = im.size
        except Exception as exc:  # noqa: BLE001
            bad_size.append(f"{src}: {exc}")
            continue

        dst_img = OUT / "images" / part / f"{md5}.bmp"
        if dst_img.is_symlink() or dst_img.exists():
            dst_img.unlink()
        dst_img.symlink_to(src)

        lines = []
        present = set()
        for cls, x1, y1, x2, y2 in boxes.get(md5, []):
            x1 = max(0.0, min(float(width), x1))
            x2 = max(0.0, min(float(width), x2))
            y1 = max(0.0, min(float(height), y1))
            y2 = max(0.0, min(float(height), y2))
            if x2 <= x1 or y2 <= y1:
                skipped["clipped_zero"] += 1
                continue
            cx = (x1 + x2) / 2.0 / width
            cy = (y1 + y2) / 2.0 / height
            w = (x2 - x1) / width
            h = (y2 - y1) / height
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            present.add(CLASSES[cls])
            box_count[(part, CLASSES[cls])] += 1

        label_path = OUT / "labels" / part / f"{md5}.txt"
        label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        if lines:
            has_boxes[part] += 1
            for name in present:
                pics[(part, name)].add(md5)
        else:
            empty_labels[part] += 1

        writer.writerow([md5, part, len(lines), "|".join(sorted(present)), rel])
        if i % 1000 == 0:
            print(f"  {i}/{len(split)}", flush=True)

    manifest.close()

    counts = {
        "built": "2026-11-09",
        "split_csv": str(SPLIT),
        "annotation": str(LABELS),
        "image_root": str(IMAGES),
        "output": str(OUT),
        "classes": CLASSES,
        "split_rows": {p: sum(1 for v in split.values() if v == p) for p in SPLITS},
        "pictures_with_boxes": {p: has_boxes[p] for p in SPLITS},
        "pictures_with_empty_labels": {p: empty_labels[p] for p in SPLITS},
        "per_class": {
            name: {
                p: {"pictures": len(pics[(p, name)]), "boxes": box_count[(p, name)]}
                for p in SPLITS
            }
            for name in CLASSES
        },
        "skipped_codes": dict(sorted(skipped.items())),
        "boxes_outside_split": outside,
        "missing_images": missing_images,
        "bad_images": bad_size,
    }
    (OUT / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")

    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASSES))
    (OUT / "data_all.yaml").write_text(
        f"path: {OUT}\ntrain: images/train\nval: images/val\ntest: images/test\n"
        f"nc: {len(CLASSES)}\nnames:\n{names}\n",
        encoding="utf-8",
    )
    train_objects = [
        str((OUT / "images" / "train" / f"{md5}.bmp"))
        for md5, part in sorted(split.items())
        if part == "train" and (OUT / "labels" / "train" / f"{md5}.txt").is_file()
        and (OUT / "labels" / "train" / f"{md5}.txt").stat().st_size > 0
    ]
    (OUT / "train_objects.txt").write_text("\n".join(train_objects) + "\n", encoding="utf-8")
    (OUT / "data_objects.yaml").write_text(
        f"path: {OUT}\ntrain: train_objects.txt\nval: images/val\ntest: images/test\n"
        f"nc: {len(CLASSES)}\nnames:\n{names}\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "output": str(OUT),
        "split_rows": counts["split_rows"],
        "pictures_with_boxes": counts["pictures_with_boxes"],
        "pictures_with_empty_labels": counts["pictures_with_empty_labels"],
        "skipped_codes": counts["skipped_codes"],
        "missing_images": len(missing_images),
        "bad_images": len(bad_size),
        "train_objects": len(train_objects),
    }, indent=2))
    if missing_images or bad_size:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--picture-table", default="/tmp/fmd_picture_table.csv")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build(args.picture_table, args.force)


if __name__ == "__main__":
    sys.exit(main())
