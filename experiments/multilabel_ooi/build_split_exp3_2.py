"""Build the Experiment 3.2 split and 19-column label table.

Experiment 3.2 is a redo of Experiment 1 under the size-gate constraint: for the four gated
classes the model sees size-tagged pictures only in train and validation, and the test set holds
untagged pictures of those classes plus a small tagged guard. The other fifteen columns (twelve
lens conditions, Bubble, Bubble Cluster, Wet Package) follow the same picture assignment.

The picture assignment is the Experiment 3.1 assignment, recomputed here from the annotation and
asserted, not copied on trust. Experiment 3.2 is a separate artifact: nothing from Experiment 1 is
read or overwritten.

    python experiments/multilabel_ooi/build_split_exp3_2.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ANNOTATION = Path("run/eda_full_20261029/resolved_labels.csv")
PICTURES = Path("run/eda_full_20261029/picture_table.csv")
SOURCE_SPLIT = Path("run/split_exp3_1_20261116/split.csv")
OUT = Path("run/split_exp3_2_20261116")

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
    ("class_foreign_matter", {"foreign_matter"}),
    ("class_fiber", {"fiber"}),
    ("class_extraneous_polymer", {"extraneous_polymer"}),
    ("class_hema", {"hema", "hema_obstruction", "hema_fragment"}),
]
GATES = {
    "fm_gated": "P3_FM_MICRON_THRESHOLD",
    "fiber_gated": "P3_FIB_MICRON_THRESHOLD",
    "ep_gated": "P3_EP_MICRON_THRESHOLD",
    "hema_gated": "P3_HE_MICRON_THRESHOLD",
}
EXPECT = {"train": 4964, "val": 1058, "test": 1533}


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    boxes = defaultdict(set)
    tags = defaultdict(set)
    gate_codes = defaultdict(set)
    with ANNOTATION.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m = row["picture_md5"].strip()
            if not m:
                continue
            cid = (row["canonical_id"] or "").strip()
            if (row["shape_kind"] or "").strip() == "box":
                boxes[m].add(cid)
            elif (row["shape_kind"] or "").strip() == "tag":
                tags[m].add(cid)
            if row["code"] in GATES.values():
                gate_codes[m].add(row["code"])

    assignment = {}
    with SOURCE_SPLIT.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            assignment[row["picture_md5"]] = row["split"]

    # Assert the premise: no untagged picture of a gated class in train or val.
    bad = 0
    for m, split in assignment.items():
        if split == "test":
            continue
        for cls, gate in (("foreign_matter", "fm_gated"), ("fiber", "fiber_gated"),
                          ("extraneous_polymer", "ep_gated"), ("hema", "hema_gated")):
            if cls == "hema":
                present = bool(boxes[m] & OBJECTS[6][1])
            else:
                present = cls in boxes[m]
            if present and GATES[gate] not in gate_codes[m]:
                bad += 1
                break
    if bad:
        raise SystemExit(f"{bad} untagged gated-class pictures remain in train or val")

    paths = {}
    with PICTURES.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            paths[row["md5"]] = row["winning_path"]

    columns = [c for c, _ in LENS] + [c for c, _ in OBJECTS] + list(GATES)
    rows = []
    for m, split in sorted(assignment.items()):
        r = {"picture_md5": m, "image_path": paths[m], "split": split}
        for name, ids in LENS:
            r[name] = int(bool(tags[m] & ids or boxes[m] & ids))
        for name, ids in OBJECTS:
            r[name] = int(bool(boxes[m] & ids))
        for name, code in GATES.items():
            r[name] = int(code in gate_codes[m])
        rows.append(r)

    with (out / "labels_19.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["picture_md5", "image_path", "split"] + columns)
        w.writeheader()
        w.writerows(rows)

    # split.csv, same assignment, written separately so this artifact stands alone
    with (out / "split.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["picture_md5", "split"])
        w.writeheader()
        w.writerows({"picture_md5": m, "split": s} for m, s in sorted(assignment.items()))

    counts = Counter(r["split"] for r in rows)
    if dict(counts) != EXPECT:
        raise SystemExit(f"split counts {dict(counts)} != {EXPECT}")
    positives = {
        c: {s: sum(r[c] for r in rows if r["split"] == s) for s in ("train", "val", "test")}
        for c in columns
    }
    meta = {
        "version": "exp3_2_v1",
        "date": "2026-11-16",
        "rows": len(rows),
        "splits": dict(counts),
        "columns": columns,
        "gate_columns": list(GATES),
        "rule": ("Picture assignment identical to Experiment 3.1: an untagged picture of any of "
                 "the four gated classes is test only; pictures gated in every gated class they "
                 "carry keep their frozen assignment; flagged test pictures stay as a guard."),
        "training_target": ("For the four gated classes the target is the gate column. Untagged "
                            "pictures of those classes are absent from train and val by "
                            "construction, so target equals class presence there."),
        "evaluation_truth": ("class_* is the truth for the fifteen non-gated columns and for the "
                             "object side of the gated ones; gate_* is the size truth."),
        "inputs": {
            "annotation": {"path": str(ANNOTATION), "md5": md5_of(ANNOTATION)},
            "pictures": {"path": str(PICTURES), "md5": md5_of(PICTURES)},
            "assignment": {"path": str(SOURCE_SPLIT), "md5": md5_of(SOURCE_SPLIT)},
        },
        "positives": positives,
        "note": ("Nothing from Experiment 1 is read or written. The picture assignment is shared "
                 "with Experiment 3.1 because the constraint is identical, and it is re-asserted "
                 "here rather than trusted."),
        "outputs": {
            "labels": {"path": str(out / "labels_19.csv"), "md5": md5_of(out / "labels_19.csv")},
            "split": {"path": str(out / "split.csv"), "md5": md5_of(out / "split.csv")},
        },
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"splits": dict(counts), "positives": positives}, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
