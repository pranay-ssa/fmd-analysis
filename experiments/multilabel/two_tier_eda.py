#!/usr/bin/env python3
"""Two-tier label structure of the FMD dataset, measured.

WHY THIS EXISTS
    The 2026-09-21 meeting left one question open with the lead: what to do with
    pictures that carry more than one tag, and whether YOLO can train on such
    pictures at all. Every answer to that depends on how much multi-tag data we
    actually hold, and the repository had never counted it in the two tiers the
    client's own ontology defines.

THE TWO TIERS (docs/Manufacturing Condition Ontology V1.docx)
    Image Level Labels (TAG)   - 13 tags, no location, applied to the whole frame
    Object-Level Labels (BOX)  - 11 labels, always carrying a bounding box
    A picture can carry tags, boxes, or both. The ontology never says a picture
    may hold only one of either.

WHAT THIS MEASURES
    1  the label space, both tiers, with the pictures the dataset holds for each
    2  the dataset split by tier: tags only, boxes only, both, neither
    3  the multi-tag pictures, their tier pattern and their class under the
       current single-label rule
    4  the tag pairs that share a picture
    5  the box tier: the annotation file, its boxes per image and per label
    6  the pictures the single-label rule drops a label from

RULES
    The same rules the client EDA and the line splits use: the two Updated
    folders are the dataset, the older library adds only pictures they do not
    hold, Clear and duplicates are not tags, HEMA reads as HEMA Fragment, name
    variants collapse, a picture is one content hash, and one class per picture
    decided by the older library first.

OUTPUT
    run/multilabel_eda/20260921/*.csv and summary.json
    printed report on stdout

Run:  python experiments/multilabel/two_tier_eda.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "src"))

from make_line_splits import build_pool  # noqa: E402

SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
ANN = os.path.join(REPO, "data", "annotations.xml")
OUT = os.path.join(REPO, "run", "multilabel_eda", "20260921")

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
F_OLD = "ICube Defects Library"
UPDATED = (F_OBJ, F_CAT)

ALIAS = {
    "HEMA": "HEMA Fragment",
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "Multiple Lens": "Multiple Lenses",
    "Primary Package Misalignment": "Package Misalignment",
    "Field Of View Obstructed": "View Obstructed",
}
NON_TAGS = {"Clear", "duplicates"}

# the ontology's two tiers, in the dataset's own spelling of each name
TAG_TIER = [
    "Missing Lens", "Multiple Lenses", "Missing Primary Package", "Package Misalignment",
    "Cavity Off Center", "View Obstructed", "HEMA Obstruction",
    "Low Dose Obstructing Region of Interest", "Folded Lens", "Lens Off Center",
    "Dirty Camera", "Dirty Strobe", "Bubble Scatter",
]
BOX_TIER = [
    "Fiber", "Extraneous Polymer", "Foreign Matter", "HEMA Fragment", "Bubble",
    "Stretched Bubble", "Bubble Irregular", "Bubble Cluster", "Bubble On Edge",
    "Bubble On 123", "Wet Package",
]


def norm(cls: str) -> str:
    return ALIAS.get(cls, cls)


def load_records():
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    return [{"folder": r[0], "cls": r[1], "name": r[2], "md5": r[3]} for r in rows]


def write_csv(name, headers, rows):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)
    return path


def table(rows, headers):
    rows = [[str(c) for c in r] for r in rows]
    rows = [[str(c) for c in headers]] + rows
    if not rows:
        return ""
    w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for i, r in enumerate(rows):
        out.append("  ".join(c.ljust(w[j]) for j, c in enumerate(r)).rstrip())
        if i == 0:
            out.append("  ".join("-" * x for x in w))
    return "\n".join("  " + x for x in out)


def read_annotations():
    """(image_name, [labels]) for every image in the CVAT export."""
    root = ET.parse(ANN).getroot()
    out = []
    for im in root.findall("image"):
        out.append((im.get("name"), [b.get("label") for b in im.findall("box")]))
    return out


def main():
    recs = load_records()
    pool = build_pool()                      # {md5: (class, line, name)}, the 8,409
    written = []

    # ---- tag set per picture, from every source ---------------------------
    tags_of = defaultdict(set)
    for r in recs:
        if r["cls"] not in NON_TAGS:
            tags_of[r["md5"]].add(norm(r["cls"]))
    dataset = sorted(pool)
    unknown = {t for m in dataset for t in tags_of[m]} - set(TAG_TIER) - set(BOX_TIER)
    if unknown:
        raise SystemExit("tag outside the ontology's two tiers: %s" % sorted(unknown))

    tag_of_pic = {m: tags_of[m] & set(TAG_TIER) for m in dataset}
    box_of_pic = {m: tags_of[m] & set(BOX_TIER) for m in dataset}

    # ---- 1. the label space ------------------------------------------------
    print("=" * 78)
    print("1  THE LABEL SPACE, BOTH TIERS")
    print("=" * 78)
    space = []
    for tag in TAG_TIER + BOX_TIER:
        tier = "tag" if tag in TAG_TIER else "box"
        n = sum(1 for m in dataset if tag in tags_of[m])
        space.append([tag, tier, n])
    print(table(space, ["label", "tier", "pictures in the dataset"]))
    written.append(write_csv("1_label_space.csv", ["label", "tier", "pictures"], space))
    zero = [s[0] for s in space if s[2] == 0]
    print("\n  labels with no picture in the dataset: %s" % (", ".join(zero) or "none"))

    # ---- 2. the dataset by tier -------------------------------------------
    only_tag = [m for m in dataset if tag_of_pic[m] and not box_of_pic[m]]
    only_box = [m for m in dataset if box_of_pic[m] and not tag_of_pic[m]]
    both = [m for m in dataset if box_of_pic[m] and tag_of_pic[m]]
    multi = [m for m in dataset if len(tags_of[m]) > 1]
    print()
    print("=" * 78)
    print("2  THE DATASET BY TIER")
    print("=" * 78)
    rows = [
        ["dataset, distinct pictures", len(dataset)],
        ["  with at least one tag", sum(1 for m in dataset if tag_of_pic[m])],
        ["  with at least one box label", sum(1 for m in dataset if box_of_pic[m])],
        ["  with both tiers", len(both)],
        ["  tag only", len(only_tag)],
        ["  box only", len(only_box)],
        ["  neither (would be a bug)", sum(1 for m in dataset if not tag_of_pic[m] and not box_of_pic[m])],
        ["carrying more than one label, any tier", len(multi)],
        ["  ... as a share of the dataset", "%.2f percent" % (100.0 * len(multi) / len(dataset))],
    ]
    print(table(rows, ["measure", "pictures"]))
    written.append(write_csv("2_dataset_by_tier.csv", ["measure", "pictures"], rows))

    print("\n  labels per picture, per tier:")
    print("    tag tier: %s" % dict(sorted(Counter(len(tag_of_pic[m]) for m in dataset).items())))
    print("    box tier: %s" % dict(sorted(Counter(len(box_of_pic[m]) for m in dataset).items())))

    # ---- 3. the multi-label pictures, by tier pattern ----------------------
    print()
    print("=" * 78)
    print("3  THE MULTI-LABEL PICTURES, BY TIER PATTERN")
    print("=" * 78)
    pattern = Counter((len(tag_of_pic[m]), len(box_of_pic[m])) for m in multi)
    prows = []
    for (n_tag, n_box), n in sorted(pattern.items()):
        kind = ("two box labels on one picture" if n_tag == 0 else
                "one tag and one box label on one picture")
        prows.append(["tag=%d box=%d" % (n_tag, n_box), kind, n])
    print(table(prows, ["tier pattern", "reading", "pictures"]))
    written.append(write_csv("3_multi_label_patterns.csv",
                             ["tier_pattern", "reading", "pictures"], prows))

    detail = []
    for m in sorted(multi, key=lambda x: (len(tags_of[x]), sorted(tags_of[x]))):
        cls, line, name = pool[m]
        dropped = sorted(tags_of[m] - {cls})
        where = "; ".join(sorted("%s/%s" % (r["folder"].replace(" 20260915", ""), r["cls"])
                                 for r in recs if r["md5"] == m))
        detail.append(["|".join(sorted(tags_of[m])), len(tags_of[m]), line, cls,
                       "|".join(dropped), where, name])
    written.append(write_csv("3_multi_label_detail.csv",
                             ["labels", "label_count", "line", "assigned_class",
                              "labels_dropped", "where", "file_name"], detail))

    # every label dropped by the single-label rule, over the whole dataset
    assigned = {m: pool[m][0] for m in dataset}
    dropped_by_class = Counter()
    drop_total = 0
    for m in multi:
        for lab in tags_of[m] - {assigned[m]}:
            dropped_by_class[lab] += 1
            drop_total += 1
    print("\n  what the current one-class-per-picture rule drops (the older library decides):")
    print(table([[k, v] for k, v in dropped_by_class.most_common()] + [["TOTAL dropped labels", drop_total]],
                ["dropped label", "pictures"]))
    written.append(write_csv("3_dropped_labels.csv", ["dropped_label", "pictures"],
                             [[k, v] for k, v in dropped_by_class.most_common()] +
                             [["TOTAL", drop_total]]))
    print("\n  assigned class of the %d multi-label pictures:" % len(multi))
    for k, v in Counter(assigned[m] for m in multi).most_common():
        print("    %-44s %d" % (k, v))

    # ---- 4. tag pairs ------------------------------------------------------
    print()
    print("=" * 78)
    print("4  LABEL PAIRS THAT SHARE A PICTURE")
    print("=" * 78)
    pairs = Counter()
    for m in multi:
        ts = sorted(tags_of[m])
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pairs[(ts[i], ts[j])] += 1

    def tiers(a, b):
        ta = "tag" if a in TAG_TIER else "box"
        tb = "tag" if b in TAG_TIER else "box"
        return ("both " + ta) if ta == tb else ("%s + %s" % (ta, tb))

    prows = [[a, b, tiers(a, b), n] for (a, b), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))]
    print(table(prows, ["label A", "label B", "tiers", "pictures"]))
    written.append(write_csv("4_label_pairs.csv", ["label_a", "label_b", "tiers", "pictures"], prows))
    tc = Counter(r[2] for r in prows for _ in range(r[3]))
    print("\n  pair readings, by picture:")
    for k, v in tc.most_common():
        print("    %-20s %d" % (k, v))

    # ---- 5. the box tier ---------------------------------------------------
    print()
    print("=" * 78)
    print("5  THE BOX TIER (data/annotations.xml)")
    print("=" * 78)
    ann = read_annotations()
    per_img = {name: labs for name, labs in ann}
    nbox = [len(v) for v in per_img.values()]
    rows = [
        ["images in the annotation file", len(ann)],
        ["boxes", sum(nbox)],
        ["images with no box", sum(1 for n in nbox if n == 0)],
        ["images with one box", sum(1 for n in nbox if n == 1)],
        ["images with two or more boxes", sum(1 for n in nbox if n >= 2)],
        ["most boxes on one image", max(nbox)],
        ["images carrying two or more DIFFERENT box labels",
         sum(1 for v in per_img.values() if len(set(v)) > 1)],
        ["distinct box labels present", len({l for v in per_img.values() for l in v})],
    ]
    print(table(rows, ["measure", "count"]))
    written.append(write_csv("5_box_tier_summary.csv", ["measure", "count"], rows))
    hist = [[k, v] for k, v in sorted(Counter(nbox).items())]
    written.append(write_csv("5_boxes_per_image.csv", ["boxes_on_the_image", "images"], hist))
    per_label = []
    for lab, n in Counter(l for v in per_img.values() for l in v).most_common():
        per_label.append([lab, n, sum(1 for v in per_img.values() if lab in v)])
    print()
    print(table(per_label, ["box label", "boxes", "images"]))
    written.append(write_csv("5_box_tier_by_label.csv", ["label", "boxes", "images"], per_label))

    # how the annotation job was run: one CVAT task per box label
    root = ET.parse(ANN).getroot()
    tasks = {t.findtext("id"): t.findtext("name") for t in root.findall("meta/project/tasks/task")}
    tag_as_box = sorted({l for v in per_img.values() for l in v} & set(TAG_TIER))
    task_of = defaultdict(set)
    for im in root.findall("image"):
        task_of[im.get("name")].add(tasks[im.get("task_id")])
    folder_cls = {r["name"]: r["cls"] for r in recs}
    disagree = sum(1 for name, labs in per_img.items()
                   if labs and folder_cls.get(name) and set(labs) != {folder_cls[name]})
    rows = [
        ["annotation tasks, one per box label", len(tasks)],
        ["task names", "; ".join(sorted(tasks.values()))],
        ["pictures sitting in more than one task", sum(1 for v in task_of.values() if len(v) > 1)],
        ["tag-tier labels used as a box label", len(tag_as_box)],
        ["box label that disagrees with the folder class", disagree],
    ]
    print()
    print(table(rows, ["measure", "count"]))
    written.append(write_csv("5_annotation_tasks.csv", ["measure", "count"], rows))

    # the boxed pictures inside the pooled dataset
    rec_keys = {(r["folder"], r["cls"], os.path.basename(r["name"])): r["md5"] for r in recs}
    boxed_keys = {(name.split("/")[0], name.split("/")[1], os.path.basename(name)) for name in per_img}
    matched = {rec_keys[k] for k in boxed_keys if k in rec_keys}
    in_pool_22 = matched & set(dataset)
    dup = len(boxed_keys) - len(matched)
    boxed_tag = sum(1 for m in matched if tags_of[m] & set(TAG_TIER))
    boxed_multi = sum(1 for m in matched if len(tags_of[m]) > 1)
    print("\n  the annotated pictures: %d images, %d distinct pictures (%d repeat a picture "
          "already in the file); %d of them are in the 22-class pool"
          % (len(boxed_keys), len(matched), dup, len(in_pool_22)))
    print("  of those pictures, %d carry a tag-tier label and %d carry more than one label "
          "in the pooled record, although the annotation file gives each of them exactly one box label"
          % (boxed_tag, boxed_multi))
    written.append(write_csv("5_box_tier_in_pool.csv",
                             ["measure", "count"],
                             [["annotated images", len(boxed_keys)],
                              ["annotated distinct pictures", len(matched)],
                              ["repeat pictures inside the annotation file", dup],
                              ["in the pooled defect-class dataset", len(in_pool_22)],
                              ["with a tag-tier label in the pooled record", boxed_tag],
                              ["with more than one label in the pooled record", boxed_multi]]))

    # ---- summary -----------------------------------------------------------
    summary = {
        "source_record": "run/line_eda/20260916/image_md5_records.csv",
        "source_annotations": "data/annotations.xml",
        "ontology": "docs/Manufacturing Condition Ontology V1.docx",
        "dataset_pictures": len(dataset),
        "labels_with_no_picture": zero,
        "pictures_tag_tier": sum(1 for m in dataset if tag_of_pic[m]),
        "pictures_box_tier": sum(1 for m in dataset if box_of_pic[m]),
        "pictures_both_tiers": len(both),
        "pictures_tag_only": len(only_tag),
        "pictures_box_only": len(only_box),
        "multi_label_pictures": len(multi),
        "multi_label_share_percent": round(100.0 * len(multi) / len(dataset), 2),
        "patterns": {"tag=%d box=%d" % k: v for k, v in sorted(pattern.items())},
        "labels_dropped_by_single_label_rule": drop_total,
        "dropped_labels_by_name": dict(dropped_by_class.most_common()),
        "annotation_images": len(ann),
        "annotation_boxes": sum(nbox),
        "annotation_images_with_two_different_labels":
            sum(1 for v in per_img.values() if len(set(v)) > 1),
        "annotation_boxes_per_image_max": max(nbox),
        "annotation_tasks": len(tasks),
        "annotation_pictures_in_two_tasks": sum(1 for v in task_of.values() if len(v) > 1),
        "tag_labels_used_as_a_box_label": len(tag_as_box),
        "box_label_against_folder_class_disagreements": disagree,
        "annotation_pictures_in_pool": len(in_pool_22),
        "annotation_pictures_with_a_tag_label": boxed_tag,
        "annotation_pictures_with_more_than_one_pooled_label": boxed_multi,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print()
    print("written to run/multilabel_eda/20260921/:")
    for p in written + [os.path.join(OUT, "summary.json")]:
        print("  " + os.path.basename(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
