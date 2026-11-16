#!/usr/bin/env python3
"""Verify the Experiment 2 detector dataset against the frozen split and annotation.

Independent of the builder: it re-reads the source CSVs, recomputes the expected
picture and box counts, then walks the built dataset and checks every label.
Exits 0 only when every check passes.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/pranayp/fmd-analysis")
SPLIT = REPO / "run/split_20261103_v8/split_70_15_15.csv"
LABELS = REPO / "run/eda_full_20261029/resolved_labels.csv"
PICTURES = Path("/tmp/fmd_picture_table.csv")
IMAGES = Path("/data/FMD_Data_26082026/fmd_temp_images")
OUT = Path("/data/FMD_Data_26082026/fmd_detector_20261110")
SPLITS = ("train", "val", "test")

CLASSES = ["Bubble", "Bubble Cluster", "Wet Package", "Fiber",
           "Extraneous Polymer", "HEMA", "Foreign Matter"]
CODE_TO_CLASS = {
    "bubble": 0, "bubble_irregular": 0, "stretched_bubble": 0,
    "bubble_cluster": 1, "wet_package": 2, "fiber": 3,
    "extraneous_polymer": 4, "hema_obstruction": 5, "hema_fragment": 5,
    "foreign_matter": 6,
}
EXCLUDED = {"bubble_on_edge", "bubble_on_123"}
EXPECTED = {
    "Bubble": {"train": (1520, 20154), "val": (326, 4338), "test": (325, 4249)},
    "Bubble Cluster": {"train": (792, 2397), "val": (170, 529), "test": (170, 493)},
    "Foreign Matter": {"train": (576, 1905), "val": (110, 249), "test": (112, 400)},
    "Fiber": {"train": (274, 567), "val": (60, 90), "test": (58, 83)},
    "Wet Package": {"train": (220, 987), "val": (47, 153), "test": (47, 202)},
    "HEMA": {"train": (102, 107), "val": (25, 27), "test": (27, 27)},
    "Extraneous Polymer": {"train": (106, 116), "val": (19, 21), "test": (17, 18)},
}
EXPECTED_SPLIT = {"train": 5239, "val": 1110, "test": 1121}
EXPECTED_WITH_BOXES = {"train": 1563, "val": 341, "test": 343}
EXPECTED_EMPTY = {"train": 3676, "val": 769, "test": 778}

errors = []


def fail(msg):
    errors.append(msg)


def read_split():
    split = {}
    with SPLIT.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            md5 = row["picture_md5"].strip()
            part = row["split"].strip()
            if md5 in split:
                fail(f"split: {md5} appears twice")
            split[md5] = part
    return split


def read_paths():
    paths = {}
    with PICTURES.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            paths[row["md5"].strip()] = row["winning_path"].strip()
    return paths


def expected_counts(split):
    pics = defaultdict(set)
    boxes = Counter()
    skipped = Counter()
    with LABELS.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["shape_kind"].strip() != "box":
                continue
            md5 = row["picture_md5"].strip()
            if md5 not in split:
                continue
            code = row["canonical_id"].strip()
            if code in EXCLUDED:
                skipped[code] += 1
                continue
            cls = CODE_TO_CLASS.get(code)
            if cls is None:
                skipped[code] += 1
                continue
            part = split[md5]
            pics[(part, CLASSES[cls])].add(md5)
            boxes[(part, CLASSES[cls])] += 1
    return pics, boxes, skipped


def check_yaml(path, key):
    text = Path(path).read_text(encoding="utf-8")
    if "nc: 7" not in text:
        fail(f"{path.name}: nc is not 7")
    for i, name in enumerate(CLASSES):
        if f"{i}: {name}" not in text:
            fail(f"{path.name}: missing class {i} {name}")
    if f"path: {OUT}" not in text:
        fail(f"{path.name}: path is not {OUT}")
    if key not in text:
        fail(f"{path.name}: missing {key}")


def main():
    split = read_split()
    paths = read_paths()
    pics, boxes, skipped = expected_counts(split)

    if len(split) != 7470:
        fail(f"split rows {len(split)} != 7470")
    for part, n in EXPECTED_SPLIT.items():
        got = sum(1 for v in split.values() if v == part)
        if got != n:
            fail(f"split {part}: {got} != {n}")

    if not OUT.is_dir():
        fail(f"{OUT} does not exist")
        print("\n".join(errors))
        return 1

    counts_path = OUT / "counts.json"
    if not counts_path.is_file():
        fail("counts.json missing")
        counts = {}
    else:
        counts = json.loads(counts_path.read_text(encoding="utf-8"))

    for name in CLASSES:
        for part in SPLITS:
            want_pics, want_boxes = EXPECTED[name][part]
            got_pics = len(pics[(part, name)])
            got_boxes = boxes[(part, name)]
            if (got_pics, got_boxes) != (want_pics, want_boxes):
                fail(f"source {name} {part}: {got_pics}/{got_boxes} != {want_pics}/{want_boxes}")
            recorded = counts.get("per_class", {}).get(name, {}).get(part, {})
            if recorded.get("pictures") != got_pics or recorded.get("boxes") != got_boxes:
                fail(f"counts.json {name} {part}: {recorded} != {got_pics}/{got_boxes}")

    if counts.get("skipped_codes") != dict(sorted(skipped.items())):
        fail(f"counts.json skipped_codes {counts.get('skipped_codes')} != source {dict(skipped)}")

    seen = set()
    with_boxes = Counter()
    empty = Counter()
    for part in SPLITS:
        img_dir = OUT / "images" / part
        lbl_dir = OUT / "labels" / part
        images = sorted(p for p in img_dir.iterdir() if p.is_symlink())
        labels = sorted(lbl_dir.glob("*.txt"))
        if len(images) != EXPECTED_SPLIT[part]:
            fail(f"{part}: {len(images)} images != {EXPECTED_SPLIT[part]}")
        if len(labels) != EXPECTED_SPLIT[part]:
            fail(f"{part}: {len(labels)} labels != {EXPECTED_SPLIT[part]}")
        img_stems = {p.stem for p in images}
        lbl_stems = {p.stem for p in labels}
        if img_stems != lbl_stems:
            fail(f"{part}: image and label stems differ by {len(img_stems ^ lbl_stems)}")
        for img in images:
            md5 = img.stem
            if md5 in seen:
                fail(f"{md5} appears in more than one split")
            seen.add(md5)
            if split.get(md5) != part:
                fail(f"{md5} is in {part}, split says {split.get(md5)}")
            try:
                target = img.resolve(strict=True)
            except FileNotFoundError:
                fail(f"{part}/{md5}: symlink target missing")
                continue
            if IMAGES not in target.parents:
                fail(f"{part}/{md5}: target outside {IMAGES}: {target}")
            label = lbl_dir / f"{md5}.txt"
            text = label.read_text(encoding="utf-8").strip()
            if text:
                with_boxes[part] += 1
            else:
                empty[part] += 1
            for lineno, line in enumerate(text.splitlines(), 1):
                fields = line.split()
                if len(fields) != 5:
                    fail(f"{part}/{md5}.txt:{lineno}: {len(fields)} fields")
                    continue
                try:
                    cls = int(fields[0])
                    cx, cy, w, h = (float(v) for v in fields[1:])
                except ValueError:
                    fail(f"{part}/{md5}.txt:{lineno}: non-numeric")
                    continue
                if not 0 <= cls < len(CLASSES):
                    fail(f"{part}/{md5}.txt:{lineno}: class {cls}")
                if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    fail(f"{part}/{md5}.txt:{lineno}: box outside 0..1")
                if cx - w / 2 < -1e-6 or cx + w / 2 > 1 + 1e-6:
                    fail(f"{part}/{md5}.txt:{lineno}: x edge outside frame")
                if cy - h / 2 < -1e-6 or cy + h / 2 > 1 + 1e-6:
                    fail(f"{part}/{md5}.txt:{lineno}: y edge outside frame")

    for part in SPLITS:
        if with_boxes[part] != EXPECTED_WITH_BOXES[part]:
            fail(f"{part}: {with_boxes[part]} pictures with boxes != {EXPECTED_WITH_BOXES[part]}")
        if empty[part] != EXPECTED_EMPTY[part]:
            fail(f"{part}: {empty[part]} empty labels != {EXPECTED_EMPTY[part]}")

    if len(seen) != 7470:
        fail(f"{len(seen)} unique pictures != 7470")

    check_yaml(OUT / "data_all.yaml", "train: images/train")
    check_yaml(OUT / "data_objects.yaml", "train: train_objects.txt")
    train_objects = (OUT / "train_objects.txt").read_text(encoding="utf-8").strip().splitlines()
    if len(train_objects) != EXPECTED_WITH_BOXES["train"]:
        fail(f"train_objects.txt {len(train_objects)} != {EXPECTED_WITH_BOXES['train']}")
    for line in train_objects[:5]:
        if not Path(line).is_file():
            fail(f"train_objects.txt missing {line}")

    print(json.dumps({
        "split": {p: sum(1 for v in split.values() if v == p) for p in SPLITS},
        "pictures_with_boxes": dict(with_boxes),
        "empty_labels": dict(empty),
        "per_class": counts.get("per_class"),
        "skipped_codes": dict(skipped),
        "facts": "7 class detector dataset on the frozen split",
    }, indent=2))
    if errors:
        print(f"\nFAILED with {len(errors)} error(s):")
        for msg in errors[:50]:
            print(" -", msg)
        return 1
    print("\nOK: dataset matches the frozen split and the annotation of record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
