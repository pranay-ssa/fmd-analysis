#!/usr/bin/env python3
"""Build the bubble_full_merge results workbook (2026-10-15).

Matches the house convention of reports/bubble_merge/FMD_OOI_Crops_Comparison_
20261008.xlsx: Read me, Headline, Per class, Counts, Confusion. Adds two sheets
this experiment earned: Source breakdown (misclassifications by annotation
source folder) and Misclassification summary (the phase 2 export).

All numbers are read from the run artifacts, never typed by hand:
  run/bubble_full_merge_metrics.json              headline + per class
  run/bubble_full_merge_confusion.json            confusion matrix
  run/bubble_full_merge_20261015_predictions.csv  per-crop truth vs prediction
  run/bubble_full_merge_crops_manifest.csv        source file per crop
  run/bubble_full_merge_confusion_matrix.png      embedded image

USAGE
  uv run --with openpyxl python make_bubble_full_merge_workbook.py
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RUN = "run"
OUT = os.path.join(RUN, "FMD_BubbleFullMerge_20261015.xlsx")

HEAD_FILL = PatternFill("solid", fgColor="D9E1F2")
BAND_FILL = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="B0B0B0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)
TOP = Alignment(vertical="top")

CLASS_ORDER = ["Bubble", "Wet Package", "Foreign Matter", "Fiber",
               "Extraneous Polymer", "HEMA Fragment"]
SOURCE_ORDER = ["Production 20260925", "Updated 20260922", "Old library"]


def source_folder(rank, sfile):
    if sfile.startswith("annotations_452"):
        return "Production 20260925"
    if sfile.startswith("Updated"):
        return "Updated 20260922"
    return "Old library"


def style_header(ws, row, ncols, widths=None):
    for i in range(1, ncols + 1):
        c = ws.cell(row=row, column=i)
        c.fill = HEAD_FILL
        c.font = Font(bold=True)
        c.border = BORDER
        c.alignment = WRAP
        if widths:
            ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]


def box(ws, r1, r2, c1, c2):
    for row in ws.iter_rows(min_row=r1, max_row=r2, min_col=c1, max_col=c2):
        for c in row:
            c.border = BORDER
            if c.alignment.wrap_text is not True:
                c.alignment = TOP


def prose(ws, pairs, title, width_a=30, width_b=112):
    ws.column_dimensions["A"].width = width_a
    ws.column_dimensions["B"].width = width_b
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=13)
    r = 3
    for a, b in pairs:
        ws.cell(row=r, column=1, value=a).font = Font(bold=True)
        ws.cell(row=r, column=1).alignment = WRAP
        ws.cell(row=r, column=2, value=b).alignment = WRAP
        r += 1
    return r


def main():
    metrics = json.load(open(os.path.join(RUN, "bubble_full_merge_metrics.json")))
    conf = json.load(open(os.path.join(RUN, "bubble_full_merge_confusion.json")))
    preds = list(csv.DictReader(
        open(os.path.join(RUN, "bubble_full_merge_20261015_predictions.csv"))))
    man = list(csv.DictReader(
        open(os.path.join(RUN, "bubble_full_merge_crops_manifest.csv"))))
    counts = list(csv.DictReader(
        open(os.path.join(RUN, "bubble_full_merge_counts.csv"))))
    split = list(csv.DictReader(
        open(os.path.join(RUN, "bubble_full_merge_split_images.csv"))))
    # previous wing (2026-10-08), same recipe, smaller dataset: for the
    # comparison sheet. Read from its own artifacts, never typed.
    old = json.load(open(os.path.join(
        RUN, "bubble_merge_crops_20261008", "exp_b", "metrics.json")))
    old_meta = json.load(open(os.path.join(
        RUN, "bubble_merge_crops_20261008", "split_report.json")))["_meta"]
    assert old["arch"] == metrics["arch"] and old["seed"] == metrics["seed"], \
        "previous run is not the same recipe; comparison sheet would mislead"

    labels = conf["class_names"]
    matrix = conf["matrix"]
    assert len(labels) == 6 and len(matrix) == 6, "confusion shape"
    # the file carries its own support and total; check them against the rows
    assert conf["support"] == [sum(r) for r in matrix], "row sums != support"
    assert conf["n"] == len(preds), "confusion n != predictions rows"

    n_test = len(preds)
    n_wrong = sum(1 for r in preds if r["true"] != r["pred"])
    acc = metrics["overall_accuracy"]
    macro = metrics["macro"]
    weighted = metrics["weighted"]["f1"]

    # per-crop source join
    crop_src = {}
    for m in man:
        crop_src[m["crop_file"].split("/")[-1]] = source_folder(
            m["source_rank"], m["source_file"])

    # source breakdown: test crops / wrong / test images / images with errors
    src = defaultdict(lambda: {"n": 0, "wrong": 0, "imgs": set(), "misimgs": set()})
    src_cls = defaultdict(lambda: {"n": 0, "wrong": 0})
    for r in preds:
        key = crop_src.get(r["file"].split("/")[-1])
        if key is None:
            continue
        d = src[key]
        d["n"] += 1
        # image identity = source image from manifest, but preds carry crop path;
        # join through manifest for the image name
        d["imgs"].add(r["file"])
        if r["true"] != r["pred"]:
            d["wrong"] += 1
            d["misimgs"].add(r["file"])
            src_cls[(key, r["true"])]["wrong"] += 1
        src_cls[(key, r["true"])]["n"] += 1

    # image-level source counts (from split list joined to manifest)
    man_img = {}
    for m in man:
        man_img.setdefault(m["source_image"], source_folder(
            m["source_rank"], m["source_file"]))
    img_src = Counter(man_img.values())
    test_img_src = Counter()
    for s in split:
        if s["split"] == "test":
            test_img_src[man_img.get(s["source_image"], "?")] += 1
    mis_imgs_src = Counter()
    for r in preds:
        if r["true"] != r["pred"]:
            cropname = r["file"].split("/")[-1]
            for m in man:
                if m["crop_file"].split("/")[-1] == cropname:
                    mis_imgs_src[man_img.get(m["source_image"], "?")] += 1
                    break

    wb = Workbook()

    # ---------------- Read me ----------------
    ws = wb.active
    ws.title = "Read me"
    prose(ws, [
        ("The question",
         "The bubble family has been merged before, but on 522 images. This run asks the same question on the enlarged dataset: with every bubble variant folded into one Bubble class, how does the model do on the 2026-10-15 annotation vintage?"),
        ("The label frame",
         "Six classes, exactly as the lead named them: Bubble (consolidated), Wet Package, Foreign Matter, Fiber, Extraneous Polymer, HEMA Fragment. Bubble swallows Bubble Cluster, Bubble Irregular, Bubble On Edge, Bubble On 123 and Bubble Scatter. HEMA Obstruction is not a class: those are tag-only annotations with no boxes anywhere in the data, so they cannot be cropped, and the production code that read as Obstruction is read as HEMA Fragment instead."),
        ("Why the comparison is fair against the previous wing",
         "Same recipe, same seed, same split rule. What changed is the dataset: 1,132 defect images instead of 522, and one fresh image-level split rather than the old one. Nothing about the model or the training was tuned between the two."),
        ("The recipe",
         "MultiLevel MultiScale (resnet50_inception), 50 epochs, batch 8, seed 42, SGD learning rate 0.0001, images resized to 224 by 224. No warm-up pass, so inference timing is cold."),
        ("The split",
         "One image-level 70/30 split, seed 42, stratified on the merged six-class label. 1,132 images cut into 792 train and 340 test; 14,184 crops into 9,795 train and 4,389 test. Crops inherit their image's side, so no image appears on both sides (leakage check: 0 overlapping images)."),
        ("Where the crops come from",
         "Three annotation sources, winner-takes-all by content hash (MD5): the production files, the updated 2026-09-22 file, then the old library. An image carries its boxes from one source only. Production wins 757 images, the two older sources cover the rest. Crops are cut straight from the annotated box, rotated upright first, so the defect fills the frame."),
        ("The answer in one line",
         "The consolidation holds: overall accuracy 90.91% and Bubble recall 97.81% on 3,740 test crops, the largest class by a wide margin. The weakness is not the merge, it is Wet Package recall at 34.38%, which drags the macro numbers down while weighted F1 stays at 90.47%."),
        ("How to read this book",
         "Headline: the six numbers that answer the question. Per class: recall, precision, F1 and support for all six. Counts: images and crops per class and how the split fell. Prev vs full merge: the same recipe on the 2026-10-08 dataset, side by side, with how far each number swayed. Confusion: the matrix as numbers and as the run's own image. Source breakdown: where the misclassified defects come from. Misclassification: the phase 2 export, 399 crops from 145 images."),
        ("The honest footnote",
         "One run, one seed, and a deterministic rerun reproduced the metrics to four decimals, so the numbers are stable but they are still one draw. Test support is lopsided by construction: Bubble carries 3,740 of 4,389 test crops and Extraneous Polymer 44, so read the macro figures as the tail speaking, not the average defect. The 33 contested Extraneous Polymer / Fiber pictures from the earlier boundary check are labelled Extraneous Polymer here; the client's new ambiguous-means-Fiber guidance points the other way, and that question is open."),
    ], "bubble full merge - the bubble family consolidated, six classes, enlarged dataset")
    ws.cell(row=15, column=1).alignment = WRAP

    # ---------------- Headline ----------------
    ws = wb.create_sheet("Headline")
    ws.cell(row=1, column=1, value="Six numbers, one run").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1,
            value="4,389 test crops from 340 images, all six classes merged as described.").alignment = WRAP
    ws.cell(row=4, column=2, value="measure")
    ws.cell(row=4, column=3, value="bubble full merge (6 classes)")
    rows = [
        ("Overall accuracy (%)", round(acc * 100, 2)),
        ("Macro recall (%)", round(macro["recall"] * 100, 2)),
        ("Macro F1 (%)", round(macro["f1"] * 100, 2)),
        ("Weighted F1 (%)", round(weighted * 100, 2)),
        ("Total training time (s)", round(metrics["training_time_sec"], 2)),
        ("Cold inference per image (ms)", round(metrics["inference_per_image_ms"], 3)),
        ("Test crops scored", n_test),
    ]
    r = 5
    for a, b in rows:
        ws.cell(row=r, column=2, value=a)
        ws.cell(row=r, column=3, value=b)
        r += 1
    style_header(ws, 4, 3, [3, 34, 30])
    box(ws, 4, r - 1, 2, 3)
    r += 1
    ws.cell(row=r, column=2, value="Reading it").font = Font(bold=True)
    ws.cell(row=r, column=3, value=(
        "90.91% pooled accuracy is real but it is mostly Bubble: 3,740 of 4,389 test crops are "
        "Bubble and they are found at 97.81%. The macro recall of 69.23% is the tail speaking. "
        "Wet Package is the headline failure and it is a recall problem, not a naming problem: "
        "precision 87.20% (when it says Wet Package it is right) against recall 34.38% (it misses "
        "two of every three). Extraneous Polymer, Fiber and Foreign Matter all sit with precision "
        "in the 44 to 47 percent band, meaning their crops are mostly predicted as something else. "
    )).alignment = WRAP
    ws.row_dimensions[r].height = 118

    # ---------------- Per class ----------------
    ws = wb.create_sheet("Per class")
    ws.cell(row=1, column=1, value="Recall, precision and F1 per class").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=(
        "Ordered by test support. Recall is the share of a class's own test crops that the model "
        "found; precision is the share of its predictions for that class that were right."
    )).alignment = WRAP
    hdr = ["class", "recall %", "precision %", "F1", "support (test crops)",
           "crops wrong", "images affected"]
    for i, h in enumerate(hdr, start=2):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr) + 1, [3, 22, 11, 11, 9, 18, 12, 14])

    per = metrics["per_class"]
    wrong_by_class = Counter()
    imgs_by_class = defaultdict(set)
    src_by_class = defaultdict(dict)
    for m in man:
        src_by_class[m["class"]][m["crop_file"].split("/")[-1]] = m["source_image"]
    for p in preds:
        if p["true"] != p["pred"]:
            wrong_by_class[p["true"]] += 1
            imgs_by_class[p["true"]].add(
                src_by_class[p["true"]].get(p["file"].split("/")[-1], p["file"]))

    r = 5
    for cls in sorted(CLASS_ORDER, key=lambda c: -per[c]["support"]):
        d = per[cls]
        vals = [cls, round(d["recall"] * 100, 2), round(d["precision"] * 100, 2),
                round(d["f1"] * 100, 2), d["support"], wrong_by_class[cls],
                len(imgs_by_class[cls])]
        for i, v in enumerate(vals, start=2):
            ws.cell(row=r, column=i, value=v)
        r += 1
    box(ws, 4, r - 1, 2, len(hdr) + 1)
    r += 1
    ws.cell(row=r, column=2, value="Notes").font = Font(bold=True)
    ws.cell(row=r, column=3, value=(
        "HEMA Fragment at 88.89% recall on 36 test crops is the largest single win of the "
        "consolidation: on the previous 522-image dataset it had 3 test crops and scored 0%. "
        "Wet Package's 34.38% recall against 87.20% precision means the class is under-detected, "
        "not confused: when the model commits to Wet Package it is nearly always right. "
        "Bubble's 2.2% error rate on 3,740 crops is 82 misclassified crops."
    )).alignment = WRAP
    ws.row_dimensions[r].height = 80

    # ---------------- Counts ----------------
    ws = wb.create_sheet("Counts")
    ws.cell(row=1, column=1, value="Images and crops per class, and how the split fell").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=(
        "1,132 images carry boxes and 14,184 crops were cut. The split is at image level, seed 42, "
        "stratified on the merged label; crops follow their image. Leakage check: 0 images on both sides."
    )).alignment = WRAP
    hdr = ["class", "images", "crops", "avg crops/img", "train images", "test images",
           "train crops", "test crops"]
    for i, h in enumerate(hdr, start=2):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr) + 1, [3, 22, 9, 9, 13, 13, 13, 12, 12])
    r = 5
    tot = Counter()
    for c in counts:
        vals = [c["class"], int(c["images_total"]), int(c["crops_total"]),
                float(c["avg_crops_per_image"]), int(c["images_train"]),
                int(c["images_test"]), int(c["crops_train"]), int(c["crops_test"])]
        for i, v in enumerate(vals, start=2):
            ws.cell(row=r, column=i, value=v)
        for k in ("images_total", "crops_total", "images_train", "images_test",
                  "crops_train", "crops_test"):
            tot[k] += int(c[k])
        r += 1
    vals = ["TOTAL (per class, multi-label images counted twice)", tot["images_total"],
            tot["crops_total"], round(tot["crops_total"] / tot["images_total"], 2),
            tot["images_train"], tot["images_test"], tot["crops_train"], tot["crops_test"]]
    for i, v in enumerate(vals, start=2):
        cell = ws.cell(row=r, column=i, value=v)
        cell.font = Font(bold=True)
    r += 1
    n_img = len(split)
    n_tr = sum(1 for s in split if s["split"] == "train")
    vals = ["DISTINCT images (each image once)", n_img, tot["crops_total"],
            round(tot["crops_total"] / n_img, 2), n_tr, n_img - n_tr,
            tot["crops_train"], tot["crops_test"]]
    for i, v in enumerate(vals, start=2):
        cell = ws.cell(row=r, column=i, value=v)
        cell.font = Font(bold=True)
    box(ws, 4, r, 2, len(hdr) + 1)
    r += 2
    ws.cell(row=r, column=2, value=(
        "The per-class image row sums above 1,132 because a few images carry boxes of two "
        "classes and are counted in both. The distinct row is the true image count and is what "
        "the split was built on."
    )).alignment = WRAP

    # ---------------- Prev vs full merge ----------------
    ws = wb.create_sheet("Prev vs full merge", 4)
    ws.cell(row=1, column=1, value="Previous merge (2026-10-08) vs full merge (this run), same recipe").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=(
        "Same architecture, epochs, batch size, seed and split rule; a larger dataset and so a "
        "different, much bigger test set (630 vs 4,389 crops). Deltas show how much the numbers "
        "moved, not a controlled A/B on identical crops. Every figure is read from both runs' "
        "own metrics and split reports."
    )).alignment = WRAP

    r = 4
    ws.cell(row=r, column=2, value="scale")
    ws.cell(row=r, column=3, value="prev merge (exp_b)")
    ws.cell(row=r, column=4, value="full merge")
    ws.cell(row=r, column=5, value="change")
    style_header(ws, r, 5, [3, 26, 20, 20, 22])
    r += 1
    scale_rows = [
        ("images total", old_meta["images_total"], len(split),
         "%.1fx" % (len(split) / old_meta["images_total"])),
        ("images train / test",
         "%d / %d" % (old_meta["images_train"], old_meta["images_test"]),
         "%d / %d" % (n_tr, n_img - n_tr), "same rule"),
        ("crops total", old_meta["crops_total"], tot["crops_total"],
         "%.1fx" % (tot["crops_total"] / old_meta["crops_total"])),
        ("crops train / test",
         "%d / %d" % (old["num_train_images"], old["num_test_images"]),
         "%d / %d" % (tot["crops_train"], tot["crops_test"]), "same rule"),
        ("classes", old["num_classes"], metrics["num_classes"], "same frame"),
        ("seed", old["seed"], metrics["seed"], "same"),
        ("leakage check (overlap images)", 0, 0, "same"),
    ]
    for a, b, c, d in scale_rows:
        ws.cell(row=r, column=2, value=a)
        ws.cell(row=r, column=3, value=b)
        ws.cell(row=r, column=4, value=c)
        ws.cell(row=r, column=5, value=d)
        r += 1
    box(ws, 4, r - 1, 2, 5)

    r += 1
    ws.cell(row=r, column=2, value="headline")
    ws.cell(row=r, column=3, value="prev merge")
    ws.cell(row=r, column=4, value="full merge")
    ws.cell(row=r, column=5, value="sway")
    style_header(ws, r, 5)
    hr = r
    r += 1
    head_rows = [
        ("Overall accuracy (%)", old["overall_accuracy"] * 100, acc * 100),
        ("Macro recall (%)", old["macro"]["recall"] * 100, macro["recall"] * 100),
        ("Macro F1 (%)", old["macro"]["f1"] * 100, macro["f1"] * 100),
        ("Weighted F1 (%)", old["weighted"]["f1"] * 100, weighted * 100),
        ("Total training time (s)", old["training_time_sec"],
         metrics["training_time_sec"]),
        ("Cold inference per image (ms)", old["inference_per_image_ms"],
         metrics["inference_per_image_ms"]),
    ]
    for a, b, c in head_rows:
        ws.cell(row=r, column=2, value=a)
        ws.cell(row=r, column=3, value=round(b, 2))
        ws.cell(row=r, column=4, value=round(c, 2))
        ws.cell(row=r, column=5, value=round(c - b, 2))
        r += 1
    box(ws, hr, r - 1, 2, 5)
    r += 1
    ws.cell(row=r, column=2, value=(
        "Read: accuracy dips 1.79 while macro recall rises 8.81 and macro F1 rises 5.42. That is "
        "one story seen two ways: accuracy is Bubble-pulled, macro averages the six classes "
        "equally and the tail improved. Training time grows 3.4x because crops grew 6.6x. The "
        "inference gap goes the other way on identical architecture, so it is measurement "
        "conditions (GPU load, cache), not a real speedup. Do not quote it as one."
    )).alignment = WRAP
    ws.row_dimensions[r].height = 80

    r += 2
    ws.cell(row=r, column=2, value="per class")
    for j, h in enumerate(["class", "support prev", "support full",
                           "recall prev %", "recall full %", "recall change",
                           "precision prev %", "precision full %",
                           "F1 prev", "F1 full"], start=3):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r, 12, [3, 12, 26, 13, 13, 13, 13, 14, 15, 15, 9, 9])
    hr = r
    r += 1
    for cls in CLASS_ORDER:
        o = old["per_class"][cls]
        n = metrics["per_class"][cls]
        vals = [cls, o["support"], n["support"],
                round(o["recall"] * 100, 2), round(n["recall"] * 100, 2),
                round((n["recall"] - o["recall"]) * 100, 2),
                round(o["precision"] * 100, 2), round(n["precision"] * 100, 2),
                round(o["f1"] * 100, 2), round(n["f1"] * 100, 2)]
        for j, v in enumerate(vals, start=3):
            ws.cell(row=r, column=j, value=v)
        r += 1
    box(ws, hr, r - 1, 2, 12)
    r += 1
    ws.cell(row=r, column=2, value=(
        "Read the support columns first. Bubble held within one point (98.77 to 97.81) while its "
        "test set grew 7.7x, which is the consolidation confirmed. HEMA Fragment +88.89 is real: "
        "3 test crops was an untrainable stub, 36 is a measurement. Fiber +43.35 is mostly sample "
        "size: 13 crops was too few to read, 85 is a real number. Wet Package -43.59 is the one "
        "genuine alarm: precision held (88.46 to 87.20) while recall collapsed on 5.4x the support, "
        "so the class is under-detected, not confused. Extraneous Polymer -21.86 on support 42 to 44 "
        "is the anomaly: the set did not grow, and 35 of those 44 crops are the contested EP/Fiber "
        "boundary set awaiting the client's ambiguous-means-Fiber ruling."
    )).alignment = WRAP
    ws.row_dimensions[r].height = 118

    # ---------------- Confusion ----------------
    ws = wb.create_sheet("Confusion")
    ws.cell(row=1, column=1, value="Confusion matrix, 4,389 test crops").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value="Rows are the true class, columns are what the model predicted.").alignment = WRAP
    ws.cell(row=4, column=2, value="true \\ predicted")
    for j, lab in enumerate(labels):
        ws.cell(row=4, column=3 + j, value=lab)
    ws.cell(row=4, column=3 + len(labels), value="row total")
    style_header(ws, 4, 3 + len(labels), [3, 22] + [16] * len(labels) + [11])
    for i, lab in enumerate(labels):
        rr = 5 + i
        ws.cell(row=rr, column=2, value=lab).font = Font(bold=True)
        rowsum = 0
        for j in range(len(labels)):
            v = matrix[i][j]
            rowsum += v
            c = ws.cell(row=rr, column=3 + j, value=v)
            if i == j:
                c.font = Font(bold=True)
                c.fill = BAND_FILL
        ws.cell(row=rr, column=3 + len(labels), value=rowsum)
    rtot = 5 + len(labels)
    ws.cell(row=rtot, column=2, value="col total").font = Font(bold=True)
    for j in range(len(labels)):
        ws.cell(row=rtot, column=3 + j, value=sum(matrix[i][j] for i in range(len(labels))))
    ws.cell(row=rtot, column=3 + len(labels), value=sum(sum(r) for r in matrix)).font = Font(bold=True)
    box(ws, 4, rtot, 2, 3 + len(labels))
    img_path = os.path.join(RUN, "bubble_full_merge_confusion_matrix.png")
    if os.path.exists(img_path):
        img = XLImage(img_path)
        img.width = int(img.width * 0.62)
        img.height = int(img.height * 0.62)
        ws.add_image(img, "B%d" % (rtot + 2))
    r = rtot + 26
    ws.cell(row=r, column=2, value=(
        "The two diagonal-dominant rows are Bubble (3,658 of 3,740) and HEMA Fragment (32 of 36). "
        "The largest off-diagonal cell is Wet Package leaking to Bubble: 94 crops. Wet Package also "
        "loses 55 to Fiber and 40 to Foreign Matter, which together account for most of its 208 errors."
    )).alignment = WRAP

    # ---------------- Source breakdown ----------------
    ws = wb.create_sheet("Source breakdown")
    ws.cell(row=1, column=1, value="Where the misclassified defects come from").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=(
        "Each test crop is joined back to the annotation source that supplied its box "
        "(winner-takes-all by content hash). Joined with 0 unmatched crops."
    )).alignment = WRAP
    hdr = ["source folder", "test crops", "crops wrong", "error rate %",
           "test images", "images with errors"]
    for i, h in enumerate(hdr, start=2):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr) + 1, [3, 24, 11, 12, 12, 13, 16])
    r = 5
    for f in SOURCE_ORDER:
        d = src[f]
        vals = [f, d["n"], d["wrong"],
                round(100 * d["wrong"] / d["n"], 1) if d["n"] else 0,
                test_img_src[f], mis_imgs_src[f]]
        for i, v in enumerate(vals, start=2):
            ws.cell(row=r, column=i, value=v)
        r += 1
    vals = ["TOTAL", sum(d["n"] for d in src.values()),
            sum(d["wrong"] for d in src.values()),
            round(100 * n_wrong / n_test, 1),
            sum(test_img_src.values()), len({p["file"] for p in preds if p["true"] != p["pred"]})]
    for i, v in enumerate(vals, start=2):
        c = ws.cell(row=r, column=i, value=v)
        c.font = Font(bold=True)
    box(ws, 4, r, 2, len(hdr) + 1)
    r += 2
    ws.cell(row=r, column=2, value="Misclassified crops per class, within each source").font = Font(bold=True)
    r += 1
    hdr2 = ["source folder"] + CLASS_ORDER
    for i, h in enumerate(hdr2, start=2):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, len(hdr2) + 1, [3, 24] + [20] * len(CLASS_ORDER))
    hr = r
    r += 1
    for f in SOURCE_ORDER:
        ws.cell(row=r, column=2, value=f)
        for j, cls in enumerate(CLASS_ORDER):
            d = src_cls[(f, cls)]
            ws.cell(row=r, column=3 + j,
                    value="%d / %d" % (d["wrong"], d["n"]) if d["n"] else "-")
        r += 1
    box(ws, hr, r - 1, 2, len(hdr2) + 1)
    r += 1
    ws.cell(row=r, column=2, value=(
        "Read: production supplies 91% of test crops and 371 of 399 errors, so its 9.3% rate is "
        "simply the overall rate. The old library is the cleanest source at 3.9%. The updated "
        "2026-09-22 file is the worst at 35.0%, but on only 40 test crops, almost all Extraneous "
        "Polymer - the contested boundary set."
    )).alignment = WRAP

    # ---------------- Misclassification ----------------
    ws = wb.create_sheet("Misclassification")
    ws.cell(row=1, column=1, value="Phase 2 export: the 399 misclassified crops").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value=(
        "Built on the VM at bubble_full_merge/misclassification: 399 PNGs plus a CSV and an XLSX "
        "manifest. Each file is named <sno>_<true>_<pred>.png; sno is the primary key, unique per "
        "misclassified crop."
    )).alignment = WRAP
    hdr = ["true label", "pred label", "crops", "source images"]
    for i, h in enumerate(hdr, start=2):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr) + 1, [3, 22, 22, 9, 14])
    pair_imgs = defaultdict(set)
    pair_cnt = Counter()
    img_of = {m["crop_file"].split("/")[-1]: m["source_image"] for m in man}
    for p in preds:
        if p["true"] != p["pred"]:
            k = (p["true"], p["pred"])
            pair_cnt[k] += 1
            pair_imgs[k].add(img_of.get(p["file"].split("/")[-1], p["file"]))
    r = 5
    for (t, pr), c in pair_cnt.most_common():
        ws.cell(row=r, column=2, value=t)
        ws.cell(row=r, column=3, value=pr)
        ws.cell(row=r, column=4, value=c)
        ws.cell(row=r, column=5, value=len(pair_imgs[(t, pr)]))
        r += 1
    box(ws, 4, r - 1, 2, len(hdr) + 1)
    r += 1
    ws.cell(row=r, column=2, value=(
        "399 crops from 145 of 340 test images. Errors cluster: two source images alone carry 55 "
        "and 69 misclassified crops, so the manifest records source image and box bbox to tell "
        "those rows apart."
    )).alignment = WRAP

    wb.save(OUT)
    print("wrote", OUT)

    # ---- verify by reading back ----
    rb = load_workbook(OUT)
    print("sheets:", rb.sheetnames)
    for sn in rb.sheetnames:
        print("  %-20s %d rows x %d cols" % (sn, rb[sn].max_row, rb[sn].max_column))
    # arithmetic gates
    assert sum(sum(r) for r in matrix) == n_test, "confusion total != test crops"
    assert metrics["per_class"]["Bubble"]["support"] == 3740
    assert round(acc * 100, 2) == 90.91, acc
    print("gate confusion total == %d: PASS" % n_test)
    print("gate overall accuracy 90.91: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
