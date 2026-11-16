"""The condition specialist's 15-column label table (Experiment 3.2, Option B).

Twelve lens columns plus Bubble, Bubble Cluster and Wet Package. The four gated classes are the
other specialist and do not appear here, so no size flag is needed and no picture is moved out of
training. The picture assignment is the frozen one, so the lens results are measured on the same
pictures as Experiment 1.

    python experiments/multilabel_ooi/build_labels_conditions.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ANNOTATION = Path("run/eda_full_20261029/resolved_labels.csv")
PICTURES = Path("run/eda_full_20261029/picture_table.csv")
SPLIT = Path("run/split_20261103_v8/split_70_15_15.csv")
OUT = Path("run/split_exp3_2_20261116/labels_conditions.csv")

LENS = [
    ("P1_MPP", {"missing_primary_package"}),
    ("P1_ML", {"multiple_lenses"}),
    ("P2_LOC", {"lens_off_center"}),
    ("P2_DC", {"dirty_camera"}),
    ("P1_NL", {"missing_lens"}),
    ("P1_FL", {"folded_lens"}),
    ("P2_LD", {"low_dose"}),
    ("P1_COC", {"cavity_off_center"}),
    ("P2_DS", {"dirty_strobe"}),
    ("P2_FOV", {"view_obstructed"}),
    ("P2_BSC", {"bubble_scatter"}),
    ("P1_PPM", {"package_misalignment"}),
]
OBJECTS = [
    ("class_bubble", {"bubble"}),
    ("class_bubble_cluster", {"bubble_cluster"}),
    ("class_wet_package", {"wet_package"}),
]
EXPECT = {"train": 5239, "val": 1110, "test": 1121}


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    boxes = defaultdict(set)
    tags = defaultdict(set)
    with ANNOTATION.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m = row["picture_md5"].strip()
            if not m:
                continue
            cid = (row["canonical_id"] or "").strip()
            kind = (row["shape_kind"] or "").strip()
            if kind == "box":
                boxes[m].add(cid)
            elif kind == "tag":
                tags[m].add(cid)

    split = {}
    with SPLIT.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            split[row["picture_md5"]] = row["split"]

    paths = {}
    with PICTURES.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            paths[row["md5"]] = row["winning_path"]

    columns = [c for c, _ in LENS] + [c for c, _ in OBJECTS]
    rows = []
    for m, side in sorted(split.items()):
        r = {"picture_md5": m, "image_path": paths[m], "split": side}
        for name, ids in LENS:
            r[name] = int(bool(tags[m] & ids or boxes[m] & ids))
        for name, ids in OBJECTS:
            r[name] = int(bool(boxes[m] & ids))
        rows.append(r)

    counts = Counter(r["split"] for r in rows)
    if dict(counts) != EXPECT:
        raise SystemExit(f"split counts {dict(counts)} != {EXPECT}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["picture_md5", "image_path", "split"] + columns)
        w.writeheader()
        w.writerows(rows)

    positives = {c: {s: sum(r[c] for r in rows if r["split"] == s)
                     for s in ("train", "val", "test")} for c in columns}
    meta = {
        "version": "exp3_2_cond15_v1",
        "date": "2026-11-16",
        "rows": len(rows),
        "splits": dict(counts),
        "columns": columns,
        "rule": "Twelve lens columns plus the three non-gated object classes.",
        "assignment": "Frozen 70/15/15 picture assignment, so lens results compare with Experiment 1.",
        "inputs": {"annotation": md5_of(ANNOTATION), "pictures": md5_of(PICTURES),
                   "split": md5_of(SPLIT)},
        "positives": positives,
        "output": {"path": str(OUT), "md5": md5_of(OUT)},
    }
    (OUT.parent / "meta_conditions.json").write_text(json.dumps(meta, indent=2) + "\n",
                                                     encoding="utf-8")
    print(json.dumps({"splits": dict(counts), "positives": positives}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
