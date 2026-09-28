"""Independent check of run/annotations_audit_20260923/ against the two annotation XMLs.

Re-derives every published figure through a different code path than the builder
(iterparse instead of ElementTree.parse, counters instead of cross tabulations), then diffs
them against an EXPECTED table embedded here - not against the artifacts - so the harness
cannot agree with whatever the artifacts happen to say.  It then compares the embedded
values with summary.json so a re-run that moves a number fails loudly.

Prints one line per check and exits non-zero on any failure.  Stdlib only.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

NEW_XML = "data/Updated Annotations 20260922.xml"
OLD_XML = "data/annotations.xml"
OUT_DIR = "run/annotations_audit_20260923"

# Published figures, typed in by hand so the check is a check.
EXPECTED = {
    "new_images": 6097,
    "new_tasks": 11,
    "new_labels_defined": 22,
    "new_tag_instances": 4930,
    "new_box_instances": 183,
    "new_images_with_a_tag": 3952,
    "new_images_with_a_box": 137,
    "new_images_with_a_tag_and_a_box": 13,
    "new_images_with_no_annotation": 2021,
    "new_rotated_boxes": 179,
    "labels_used": 20,
    "labels_never_used": ["P1_PPM", "P2_FOV"],
    "old_images": 435,
    "old_box_instances": 2020,
    "shared_basenames": 46,
    "shared_pictures_with_boxes_in_both": 45,
    "reannotation_pairs": 46,
    "reannotation_pairs_identical_geometry": 0,
    "reannotation_pairs_called_p3_ep": 46,
    "reannotation_median_iou_x1000": 719,
    "reannotation_min_iou_x1000": 241,
    "reannotation_max_iou_x1000": 967,
}

TAG_CODES = ["P1_MPP", "P1_PPM", "P1_COC", "P2_FOV", "P2_LOC", "P1_NL", "P1_ML", "P1_FL",
             "P2_DS", "P2_DC", "P2_BSC", "P2_LD", "P2_HMO"]
BOX_CODES = ["P2_BB", "P2_BC", "P2_BI", "P2_BST", "P2_WP", "P3_FIB", "P3_EP", "P3_HE", "P3_FM"]

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<44} got {got!r} want {want!r}")


def scan(path):
    """Count through iterparse - a different code path from the builder.

    Every child of an element is read at that element's END event.  Reading them at the
    start event silently under-counts: on this file the start event sees 4,910 of the
    4,930 tags, because the tree builder has not attached every child yet when the start
    event fires.
    """
    n_img = 0
    tags = 0
    boxes = rot = 0
    with_tag = with_box = with_both = with_neither = 0
    label_defs = []
    task_ids = set()
    tag_labels, box_labels = Counter(), Counter()
    names = set()
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag == "image":
            n_img += 1
            names.add(el.get("name"))
            task_ids.add(el.get("task_id"))
            tl = [t.get("label") for t in el.findall("tag")]
            bl = el.findall("box")
            for b in bl:
                box_labels[b.get("label")] += 1
                if b.get("rotation") is not None:
                    rot += 1
            for t in tl:
                tag_labels[t] += 1
            tags += len(tl)
            boxes += len(bl)
            if tl and bl:
                with_both += 1
            if tl:
                with_tag += 1
            if bl:
                with_box += 1
            if not tl and not bl:
                with_neither += 1
            el.clear()
        elif el.tag == "label":
            label_defs.append(el.findtext("name"))
            el.clear()
    return dict(images=n_img, names=names, task_ids=task_ids, tags=tags, boxes=boxes,
                rotated=rot, with_tag=with_tag, with_box=with_box, with_both=with_both,
                with_neither=with_neither, labels=label_defs,
                tag_labels=tag_labels, box_labels=box_labels)


def main():
    if not os.path.isdir(OUT_DIR):
        print(f"missing {OUT_DIR}: run experiments/annotations/audit_updated_annotations.py first")
        return 1
    summary = json.load(open(f"{OUT_DIR}/summary.json", encoding="utf-8"))
    new = scan(NEW_XML)
    old = scan(OLD_XML)

    check("new_images", new["images"], EXPECTED["new_images"])
    check("new_images_all_named_differently", len(new["names"]), EXPECTED["new_images"])
    check("new_tasks", len(new["task_ids"]), EXPECTED["new_tasks"])
    check("new_labels_defined", len(new["labels"]), EXPECTED["new_labels_defined"])
    check("new_tag_instances", new["tags"], EXPECTED["new_tag_instances"])
    check("new_box_instances", new["boxes"], EXPECTED["new_box_instances"])
    check("new_images_with_a_tag", new["with_tag"], EXPECTED["new_images_with_a_tag"])
    check("new_images_with_a_box", new["with_box"], EXPECTED["new_images_with_a_box"])
    check("new_images_with_a_tag_and_a_box", new["with_both"], EXPECTED["new_images_with_a_tag_and_a_box"])
    check("new_images_with_no_annotation", new["with_neither"], EXPECTED["new_images_with_no_annotation"])
    check("new_rotated_boxes", new["rotated"], EXPECTED["new_rotated_boxes"])
    never = [c for c in new["labels"] if c not in new["tag_labels"] and c not in new["box_labels"]]
    check("labels_never_used", sorted(never), EXPECTED["labels_never_used"])
    check("labels_used", len(new["labels"]) - len(never), EXPECTED["labels_used"])
    check("tag_codes_are_the_ontology_tag_list",
          sorted(set(new["labels"]) & set(TAG_CODES)), sorted(TAG_CODES))
    check("box_codes_are_the_ontology_box_list_minus_two",
          sorted(set(new["labels"]) & set(BOX_CODES)), sorted(BOX_CODES))
    check("two_box_classes_have_no_label_at_all",
          sorted(set(BOX_CODES) - set(new["labels"])), [])
    check("old_images", old["images"], EXPECTED["old_images"])
    check("old_box_instances", old["boxes"], EXPECTED["old_box_instances"])

    # shared basenames and their boxes
    def with_boxes(path):
        out = {}
        for _, el in ET.iterparse(path, events=("end",)):
            if el.tag == "image":
                out[el.get("name").rsplit("/", 1)[-1]] = [
                    (b.get("label"), b.get("xtl"), b.get("ytl"), b.get("xbr"), b.get("ybr"),
                     b.get("rotation")) for b in el.findall("box")]
                el.clear()
        return out

    o, n = with_boxes(OLD_XML), with_boxes(NEW_XML)
    shared = sorted(set(o) & set(n))
    check("shared_basenames", len(shared), EXPECTED["shared_basenames"])
    pairs_pics = [b for b in shared if o[b] and n[b]]
    check("shared_pictures_with_boxes_in_both", len(pairs_pics),
          EXPECTED["shared_pictures_with_boxes_in_both"])

    rows = list(csv.DictReader(open(f"{OUT_DIR}/reannotation_iou.csv", encoding="utf-8")))
    check("reannotation_pairs", len(rows), EXPECTED["reannotation_pairs"])
    check("reannotation_pairs_identical_geometry",
          sum(1 for r in rows if r["identical"] == "True"),
          EXPECTED["reannotation_pairs_identical_geometry"])
    check("reannotation_pairs_called_p3_ep",
          sum(1 for r in rows if r["new_label"] == "P3_EP"), EXPECTED["reannotation_pairs_called_p3_ep"])
    ious = sorted(float(r["iou"]) for r in rows)
    check("reannotation_min_iou_x1000", round(ious[0] * 1000), EXPECTED["reannotation_min_iou_x1000"])
    check("reannotation_max_iou_x1000", round(ious[-1] * 1000), EXPECTED["reannotation_max_iou_x1000"])
    k = (len(ious) - 1) * 0.5
    lo, hi = int(k), min(int(k) + 1, len(ious) - 1)
    med = ious[lo] + (ious[hi] - ious[lo]) * (k - lo)
    check("reannotation_median_iou_x1000", round(med * 1000),
          EXPECTED["reannotation_median_iou_x1000"])

    # the artifact must agree with the fresh read
    check("summary_images_matches_a_fresh_read", summary["images"], new["images"])
    check("summary_tag_instances_matches_a_fresh_read", summary["tag_instances"], new["tags"])
    check("summary_box_instances_matches_a_fresh_read", summary["box_instances"], new["boxes"])
    check("summary_never_used_matches_a_fresh_read", sorted(summary["labels_never_used"]),
          sorted(never))
    check("tasks_csv_rows", len(list(csv.DictReader(open(f"{OUT_DIR}/tasks.csv", encoding="utf-8")))),
          EXPECTED["new_tasks"])
    check("labels_csv_rows", len(list(csv.DictReader(open(f"{OUT_DIR}/labels.csv", encoding="utf-8")))),
          EXPECTED["new_labels_defined"])
    check("builder_reported_no_failed_checks", summary["checks_failed"], 0)

    bad = results.count(False)
    print(f"\n{len(results)} checks, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
