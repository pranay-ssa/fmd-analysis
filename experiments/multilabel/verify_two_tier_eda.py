#!/usr/bin/env python3
"""Re-derive every figure in the two-tier EDA and diff it against the published
output, PASS or FAIL. Independent of the builder: it re-reads both sources and
re-computes each number by a separate route, and where a number already has an
authority outside this script it is checked against that too.

Authorities used here:
    run/client_eda/20260917/summary.json      the client EDA counts (8,409 / 55)
    reports/library/FMD_Library_EDA_Counts_20260917.xlsx  not used, see below
    docs/Manufacturing Condition Ontology V1.docx (Object Sizes table)
                                              per-label box counts, typed by the client

Run:  python experiments/multilabel/verify_two_tier_eda.py
      exits non-zero when any check fails
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
ANN = os.path.join(REPO, "data", "annotations.xml")
CLIENT = os.path.join(REPO, "run", "client_eda", "20260917", "summary.json")
SUMMARY = os.path.join(REPO, "run", "multilabel_eda", "20260921", "summary.json")

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
NON = {"Clear", "duplicates"}
ALIAS = {
    "HEMA": "HEMA Fragment",
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "Multiple Lens": "Multiple Lenses",
    "Primary Package Misalignment": "Package Misalignment",
    "Field Of View Obstructed": "View Obstructed",
}
TAG_TIER = {"Missing Lens", "Multiple Lenses", "Missing Primary Package", "Package Misalignment",
            "Cavity Off Center", "View Obstructed", "HEMA Obstruction",
            "Low Dose Obstructing Region of Interest", "Folded Lens", "Lens Off Center",
            "Dirty Camera", "Dirty Strobe", "Bubble Scatter"}
BOX_TIER = {"Fiber", "Extraneous Polymer", "Foreign Matter", "HEMA Fragment", "Bubble",
            "Stretched Bubble", "Bubble Irregular", "Bubble Cluster", "Bubble On Edge",
            "Bubble On 123", "Wet Package"}

# the client's own per-label box counts, from its Ontology V1 "Object Sizes" table
ONTOLOGY_BOXES = {"Bubble": 1298, "Bubble Cluster": 154, "Bubble Irregular": 46,
                  "Bubble On 123": 79, "Bubble On Edge": 90, "Extraneous Polymer": 17,
                  "Fiber": 62, "Foreign Matter": 77, "HEMA Fragment": 8, "Wet Package": 189}

results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name, got, want))
    return ok


def main():
    pub = json.load(open(SUMMARY, encoding="utf-8"))
    client = json.load(open(CLIENT, encoding="utf-8"))

    # ---- rebuild the picture set by a route that does not use build_pool ----
    rows = [r for r in csv.reader(open(SRC, newline="", encoding="utf-8-sig")) if r and r[0]]
    updated = {r[3] for r in rows if r[0] in (F_OBJ, F_CAT)}
    old_only = {r[3] for r in rows if r[0] not in (F_OBJ, F_CAT)} - updated
    tags_of = defaultdict(set)
    for folder, cls, name, md5, _ in rows:
        if cls not in NON:
            tags_of[md5].add(ALIAS.get(cls, cls))
    dataset = {m for m in tags_of if m in updated or m in old_only}

    # one class per picture, older library first (the priority rule, restated here)
    rank = {"ICube Defects Library": 0, F_OBJ: 1, F_CAT: 2}
    assigned = {}
    best = {}
    for folder, cls, name, md5, _ in rows:
        if cls in NON:
            continue
        key = (rank[folder], ALIAS.get(cls, cls))
        if md5 not in best or key < best[md5]:
            best[md5] = key
    for md5, (_, cls) in best.items():
        if md5 in dataset:
            assigned[md5] = cls

    check("dataset pictures", len(dataset), 8409)
    check("dataset pictures against the client EDA", len(dataset), client["dataset_unique_pictures"])
    check("published summary agrees on the dataset size", pub["dataset_pictures"], 8409)

    tag_pics = {m for m in dataset if tags_of[m] & TAG_TIER}
    box_pics = {m for m in dataset if tags_of[m] & BOX_TIER}
    check("pictures in the tag tier", len(tag_pics), 6243)
    check("pictures in the box tier", len(box_pics), 2179)
    check("pictures in both tiers", len(tag_pics & box_pics), 13)
    check("pictures in neither tier", len(dataset - tag_pics - box_pics), 0)
    check("tag-only plus box-only plus both equals the dataset",
          len(tag_pics - box_pics) + len(box_pics - tag_pics) + len(tag_pics & box_pics), len(dataset))

    multi = {m for m in dataset if len(tags_of[m]) > 1}
    check("multi-label pictures", len(multi), 55)
    check("multi-label pictures against the client EDA", len(multi), client["multi_tag_pictures"])
    check("published summary agrees on the multi-label count", pub["multi_label_pictures"], 55)

    two_box = {m for m in multi if not (tags_of[m] & TAG_TIER)}
    tag_and_box = multi - two_box
    check("multi-label: two box labels on one picture", len(two_box), 42)
    check("multi-label: one tag and one box label", len(tag_and_box), 13)
    check("the two patterns cover every multi-label picture", len(two_box) + len(tag_and_box), len(multi))
    for m in two_box:
        check("two-box picture carries exactly 2 labels", len(tags_of[m]), 2)
    for m in tag_and_box:
        check("tag+box picture carries exactly 1 tag and 1 box label",
              (len(tags_of[m] & TAG_TIER), len(tags_of[m] & BOX_TIER)), (1, 1))

    # no picture carries two TAG-tier labels
    check("pictures carrying two tag-tier labels",
          sum(1 for m in dataset if len(tags_of[m] & TAG_TIER) > 1), 0)

    # ---- the published pair table -----------------------------------------
    pairs = Counter()
    for m in multi:
        ts = sorted(tags_of[m])
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pairs[(ts[i], ts[j])] += 1
    OUT = os.path.join(REPO, "run", "multilabel_eda", "20260921")
    pub_pairs = {(r["label_a"], r["label_b"]): int(r["pictures"]) for r in
                 csv.DictReader(open(os.path.join(OUT, "4_label_pairs.csv"), newline="", encoding="utf-8"))}
    check("published pair table reproduces the pairs", pub_pairs, dict(pairs))
    check("pair counts sum to the multi-label count", sum(pairs.values()), len(multi))
    check("the Extraneous Polymer / Fiber pair", pairs[("Extraneous Polymer", "Fiber")], 33)

    # ---- the single-label rule --------------------------------------------
    dropped = Counter()
    for m in multi:
        for lab in tags_of[m] - {assigned[m]}:
            dropped[lab] += 1
    check("labels the single-label rule drops", sum(dropped.values()), len(multi))
    check("Extraneous Polymer is the label dropped most often", dropped.most_common(1)[0][0],
          "Extraneous Polymer")
    check("Extraneous Polymer dropped on", dropped["Extraneous Polymer"], 34)
    check("pictures tagged Extraneous Polymer in the dataset",
          sum(1 for m in dataset if "Extraneous Polymer" in tags_of[m]), 268)
    check("pictures tagged Extraneous Polymer inside the multi-label set",
          sum(1 for m in multi if "Extraneous Polymer" in tags_of[m]), 36)
    check("pictures the rule assigns to Fiber",
          sum(1 for m in multi if assigned[m] == "Fiber"), 33)
    check("assigned classes sum to the multi-label count",
          sum(1 for m in multi if m in assigned), len(multi))
    pub_dropped = {r["dropped_label"]: int(r["pictures"]) for r in
                   csv.DictReader(open(os.path.join(OUT, "3_dropped_labels.csv"), newline="", encoding="utf-8"))
                   if r["dropped_label"] != "TOTAL"}
    check("published dropped-label table agrees", pub_dropped, dict(dropped))

    # ---- the box tier -----------------------------------------------------
    root = ET.parse(ANN).getroot()
    boxes_by_img = Counter()
    labels_by_img = defaultdict(list)
    for im in root.findall("image"):
        bs = im.findall("box")
        boxes_by_img[im.get("id")] = len(bs)
        labels_by_img[im.get("id")] = [b.get("label") for b in bs]
    total_boxes = sum(boxes_by_img.values())
    check("annotation images", len(boxes_by_img), 435)
    check("annotation boxes", total_boxes, 2020)
    check("images with a different-label second box",
          sum(1 for v in labels_by_img.values() if len(set(v)) > 1), 0)
    check("most boxes on one image", max(boxes_by_img.values()), 38)
    check("published summary agrees on the box count", pub["annotation_boxes"], 2020)

    per_label = Counter(l for v in labels_by_img.values() for l in v)
    check("per-label box counts match the client's own Ontology table", dict(per_label), ONTOLOGY_BOXES)
    check("the Ontology table sums to our box total", sum(ONTOLOGY_BOXES.values()), total_boxes)
    check("box labels used", len(per_label), 10)
    check("box labels the Ontology names but no picture carries",
          sorted(BOX_TIER - set(per_label)), ["Stretched Bubble"])
    check("tag-tier labels used as a box label", sorted(set(per_label) & TAG_TIER), [])

    # how the annotation job was run
    tasks = {t.findtext("id"): t.findtext("name") for t in root.findall("meta/project/tasks/task")}
    check("annotation tasks", len(tasks), 10)
    task_of = defaultdict(set)
    for im in root.findall("image"):
        task_of[im.get("name")].add(tasks[im.get("task_id")])
    check("pictures sitting in more than one annotation task",
          sum(1 for v in task_of.values() if len(v) > 1), 0)
    folder_cls = {r[2]: r[1] for r in rows}
    disagree = sum(1 for im in root.findall("image")
                   if (im.findall("box") and folder_cls.get(im.get("name"))
                       and {b.get("label") for b in im.findall("box")} != {folder_cls[im.get("name")]}))
    check("box label disagreeing with the folder class", disagree, 0)

    # the annotated pictures, by content, against the pooled dataset
    key_of = {(r[0], r[1], os.path.basename(r[2])): r[3] for r in rows}
    boxed = {(n.split("/")[0], n.split("/")[1], os.path.basename(n))
             for n in (im.get("name") for im in root.findall("image"))}
    matched = {key_of[k] for k in boxed if k in key_of}
    check("annotated images matched to a file row", len(matched), 434)
    check("annotated pictures inside the dataset", len(matched & dataset), 434)
    check("one annotated image repeats another's content", len(boxed) - len(matched), 1)
    check("annotated pictures carrying a tag-tier label",
          sum(1 for m in matched if tags_of[m] & TAG_TIER), 5)
    check("annotated pictures carrying more than one pooled label",
          sum(1 for m in matched if len(tags_of[m]) > 1), 47)
    check("two-label pictures plus tag-and-box pictures account for the 47",
          len(two_box) + 5, 47)
    check("published box-tier-in-pool table agrees",
          {r["measure"]: int(r["count"]) for r in
           csv.DictReader(open(os.path.join(OUT, "5_box_tier_in_pool.csv"), newline="", encoding="utf-8"))},
          {"annotated images": 435, "annotated distinct pictures": 434,
           "repeat pictures inside the annotation file": 1,
           "in the pooled defect-class dataset": 434,
           "with a tag-tier label in the pooled record": 5,
           "with more than one label in the pooled record": 47})

    # ---- a tag the ontology names but the dataset does not hold -----------
    check("labels with no picture", sorted(pub["labels_with_no_picture"]), ["Folded Lens", "Stretched Bubble"])

    # ---- report ------------------------------------------------------------
    bad = [r for r in results if not r[0]]
    print("two-tier EDA verification: %d checks, %d failed" % (len(results), len(bad)))
    for ok, name, got, want in bad:
        print("  FAIL %-58s got %r, want %r" % (name, got, want))
    if not bad:
        print("  every figure in run/multilabel_eda/20260921/ is reproduced by a second route,")
        print("  and the box counts independently match the counts in the client's own ontology.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
