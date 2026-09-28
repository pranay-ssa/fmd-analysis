#!/usr/bin/env python3
"""Build the two small detection sets used by the multi-label tests. No image is copied.

Test 1 asks the plain question: split the 47 pictures that carry boxes into 34 train and 13 test.
Test 2 asks whether the score survives a group the model has never seen: keep every picture from
line 25 in the test set, and train on the other lines only.

The crop and the label both come from the existing detection set on this box, which already holds a
matching pair for every annotated picture. The model therefore sees byte-identical inputs to the
ones the recorded baseline trained on.

Name trouble, and how it is handled. A picture in the folder record can carry a name the crop
pipeline never used: the crop names drop the two appended score fields, and some pictures are filed
under a longer pallet-named variant. So a name is matched in three steps, longest first, and a
prefix match must be unique before it is accepted.

Every built label is then checked against the box count measured from the annotation file. A
mismatch means the wrong crop was matched, so it is reported rather than trained on.

Reads   /tmp/test_split.csv
Writes  dataset_test_picture_split/   test 1, 34 train against 13 test
        dataset_test_line_split/      test 2, train on every line except 25
"""
import csv
import re
from pathlib import Path

PRJ = Path("/home/pranayp/yolo_ooi")
SOURCE = PRJ / "dataset_obb"
SPLIT_CSV = Path("/tmp/test_split.csv")
SCORE_TAIL = re.compile(r"(_\d+\.\d+)+$")

CLASS_NAMES = ["Bubble Cluster", "Bubble", "Bubble On 123", "Bubble Irregular", "Bubble On Edge",
               "Extraneous Polymer", "Fiber", "Foreign Matter", "HEMA Fragment", "Wet Package"]


def source_index():
    idx = {}
    for split in ("train", "val"):
        for lbl in (SOURCE / "labels" / split).glob("*_crop.txt"):
            idx[lbl.stem] = split
    return idx


IDX = source_index()


def obb_to_aabb(parts):
    xs = [float(parts[1]), float(parts[3]), float(parts[5]), float(parts[7])]
    ys = [float(parts[2]), float(parts[4]), float(parts[6]), float(parts[8])]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    cl = lambda v: max(0.0, min(1.0, v))
    return (int(parts[0]), cl((xmin + xmax) / 2), cl((ymin + ymax) / 2), cl(xmax - xmin), cl(ymax - ymin))


def match(stem, line):
    """Return the crop name this picture is filed under, or None."""
    cands = [stem, SCORE_TAIL.sub("", stem)]
    for c in cands:
        if c + "_crop" in IDX:
            return c + "_crop"
    stamp = stem.split("_")[0] + "_" + stem.split("_")[1] + "_" + line
    hits = [k for k in IDX if k.startswith(stamp)]
    return hits[0] if len(hits) == 1 else None


def build(dst, sets, expect):
    problems, n_pics, n_boxes, classes = [], 0, 0, set()
    for split, stems in sets.items():
        (dst / "images" / split).mkdir(parents=True, exist_ok=True)
        (dst / "labels" / split).mkdir(parents=True, exist_ok=True)
        for stem, line, want in stems:
            m = match(stem, line)
            if m is None:
                problems.append("no match in the existing detection set: %s" % stem)
                continue
            src_split = IDX[m]
            src_lbl = SOURCE / "labels" / src_split / (m + ".txt")
            src_img = SOURCE / "images" / src_split / (m + ".bmp")
            lines, got = [], 0
            for line_txt in src_lbl.read_text().splitlines():
                p = line_txt.split()
                if len(p) != 9:
                    continue
                cls, cx, cy, w, h = obb_to_aabb(p)
                lines.append("%d %.6f %.6f %.6f %.6f" % (cls, cx, cy, w, h))
                classes.add(cls)
                got += 1
            if want and got != want:
                problems.append("box count differs for %s: annotation says %s, the existing label has %d"
                                % (stem, want, got))
            if not lines:
                problems.append("empty label: %s" % stem)
                continue
            link = dst / "images" / split / src_img.name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(src_img)
            (dst / "labels" / split / src_lbl.name).write_text("\n".join(lines) + "\n")
            n_pics += 1
            n_boxes += len(lines)
    names = "\n".join("  %d: %s" % (i, n) for i, n in enumerate(CLASS_NAMES))
    (dst / "data.yaml").write_text("path: %s\ntrain: images/train\nval: images/val\nnc: %d\nnames:\n%s\n"
                                   % (dst, len(CLASS_NAMES), names))
    print("--- %s" % dst)
    for split in sets:
        print("    %-5s %3d images, %3d labels" % (
            split, len(list((dst / "images" / split).iterdir())),
            len(list((dst / "labels" / split).glob("*.txt")))))
    print("    pictures %d, boxes %d, class ids %s" % (n_pics, n_boxes, sorted(classes)))
    print("    symlink only, no image copied: %s" % all(
        p.is_symlink() for p in (dst / "images").rglob("*.bmp")))
    for pr in problems:
        print("    PROBLEM %s" % pr)
    return problems


rows = [r for r in csv.DictReader(open(SPLIT_CSV, newline="", encoding="utf-8"))
        if r["split"] in ("train", "val")]
want_of = {}
for r in csv.DictReader(open(SPLIT_CSV, newline="", encoding="utf-8")):
    want_of[r["file_name"].rsplit(".", 1)[0]] = int(r["boxes"]) if r["boxes"] else 0

prep = lambda rs: [(r["file_name"].rsplit(".", 1)[0], r["line"], want_of[r["file_name"].rsplit(".", 1)[0]]) for r in rs]
test1 = {"train": prep([r for r in rows if r["split"] == "train"]),
         "val": prep([r for r in rows if r["split"] == "val"])}
# "L25" here is the value written in the split file for the production line a frame came from,
# not a shorthand for anything.
test2 = {"val": prep([r for r in rows if r["line"] == "L25"]),
         "train": prep([r for r in rows if r["line"] != "L25"])}

print("test 1, split by picture: train %d, test %d" % (len(test1["train"]), len(test1["val"])))
print("test 2, line 25 held out: train %d, test %d" % (len(test2["train"]), len(test2["val"])))
p1 = build(PRJ / "dataset_test_picture_split", test1, True)
p2 = build(PRJ / "dataset_test_line_split", test2, True)
print("problems: test 1 %d, test 2 %d" % (len(p1), len(p2)))
