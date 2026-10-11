#!/usr/bin/env python3
"""OOI crops experiment workbook (2026-10-08). Tables + confusion matrix
images, no charts.

Experiment: MultiScale on defect crops (rotate-upright, bbox regions), two
label sets on one shared image-level 70/30 split (seed 42):
  exp_a = 7 classes (Bubble Cluster separate)
  exp_b = 6 classes (cluster merged into Bubble)
Question: does folding Bubble Cluster into Bubble help?

Run: run/bubble_merge_crops_20261008/   Output: reports/bubble_merge/
"""
import json
import os

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

REPO = r"D:\fmd-analysis"
RUN = os.path.join(REPO, "run", "bubble_merge_crops_20261008")
OUT = os.path.join(REPO, "reports", "bubble_merge",
                   "FMD_OOI_Crops_Comparison_20261008.xlsx")

TITLE = "1F4E79"
HEAD = "2E75B6"
SUBTLE = "F2F7FC"
WHITE = "FFFFFF"
GREY = "7F7F7F"
GOOD = "C6EFCE"
BAD = "FFC7CE"
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def load(exp):
    with open(os.path.join(RUN, exp, "metrics.json"), encoding="utf-8") as fh:
        return json.load(fh)


def read_counts():
    rows = []
    with open(os.path.join(RUN, "counts.csv"), newline="", encoding="utf-8") as fh:
        header = fh.readline().strip().split(",")
        for line in fh:
            rows.append(dict(zip(header, line.strip().split(","))))
    return rows


def head(ws, row, texts, start=1):
    for j, t in enumerate(texts, start=start):
        c = ws.cell(row=row, column=j, value=t)
        c.font = Font(bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor=HEAD)
        c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center",
                                vertical="center")


def para(ws, row, text, col=1, grey=False, width=100, bold=False):
    c = ws.cell(row=row, column=col, value=text)
    c.font = Font(size=11, color=GREY if grey else "000000", bold=bold)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    return c


def pct(x):
    return round(100 * x, 2)


def main():
    a = load("exp_a")
    b = load("exp_b")
    counts = read_counts()

    wb = Workbook()
    wb.remove(wb.active)

    # ---------------- Read me ----------------
    ws = wb.create_sheet("Read me")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 104
    ws["A1"] = ("Feeding the model the defect only: OOI crops, "
                "cluster separate vs merged")
    ws["A1"].font = Font(size=16, bold=True, color=TITLE)

    r = 3
    for label, text in [
        ("The question",
         "The first bubble merge test showed the answer but was not "
         "conclusive, so this run changes what the model sees. Instead of "
         "whole 2448x2048 images, the model is shown only the defect: each "
         "crop is cut straight from the annotated bounding box, rotated "
         "upright first, so the defect fills the frame. Only object-of-Interest "
         "classes are used. No lens-package classes are in the mix."),
        ("The two experiments",
         "exp_a: 7 classes - Bubble (the four bubble classes merged), Bubble "
         "Cluster kept separate, Extraneous Polymer, Fiber, Foreign Matter, "
         "HEMA Fragment, Wet Package.  exp_b: 6 classes - the same, except "
         "Bubble Cluster folds into Bubble (five bubble classes merged). "
         "Stretched Bubble (4 boxes) is not in either list and was excluded."),
        ("Why the comparison is fair",
         "Both experiments use one shared split: 522 images cut 70/30 into "
         "366 train and 156 test, seed 42, stratified on the 7-class labels. "
         "Crops inherit their image's split, so no image appears on both "
         "sides (leakage check: 0 overlapping images). Both runs score the "
         "same 630 test crops - only the label set differs."),
        ("The recipe (identical in both runs)",
         "MultiLevel MultiScale (resnet50_inception), 50 epochs, batch 8, "
         "seed 42, SGD learning rate 0.0001, images resized to 224 by 224. "
         "No warm-up pass, so inference timing is cold."),
        ("Where the crops come from",
         "Both annotation files, updated-first: where the updated file has "
         "boxes for an image they replace the old-library boxes (45 images). "
         "Each crop keeps its own box label, so the 8 images holding boxes of "
         "two classes contribute to both. 526 images, 2,157 boxes read, 4 "
         "Stretched Bubble boxes excluded, 2,153 crops written, 0 crop "
         "errors. Crops range from 6x5 to 1040x268 pixels and are resized to "
         "224x224 by the training pipeline."),
        ("The answer in one line",
         "Merging Bubble Cluster helps: overall accuracy 91.27% (cluster "
         "separate) to 92.70% (cluster merged), +1.43 points on identical "
         "test crops, and the bubble family is found more completely. The "
         "shared non-bubble classes move only slightly and in both "
         "directions, on small test counts."),
        ("How to read this book",
         "Headline: the four numbers that answer the question. Per class: "
         "recall, precision and F1 for every class in both experiments. "
         "Counts: pictures and crops per class and how the split fell. "
         "Confusion exp_a / exp_b: the confusion matrices as images."),
        ("The honest footnote",
         "One run, one seed. Test counts are small for the tail classes - "
         "HEMA Fragment has 3 test crops (it scores 0% in both experiments, "
         "which is a sample-size limit, not a merge effect), Fiber has 13. "
         "Read moves on those rows with that in mind. Crops beat whole "
         "images: 91-93% accuracy here versus 86-87.5% on full images in the "
         "earlier test, because the model is shown the defect instead of "
         "hunting for it."),
    ]:
        c = ws.cell(row=r, column=1, value=label)
        c.font = Font(size=12, bold=True, color=TITLE)
        c.alignment = Alignment(vertical="top")
        para(ws, r, text, col=2)
        ws.row_dimensions[r].height = 78
        r += 2

    # ---------------- Headline ----------------
    ws = wb.create_sheet("Headline")
    for col, w in (("A", 4), ("B", 34), ("C", 18), ("D", 18), ("E", 14)):
        ws.column_dimensions[col].width = w
    ws["B1"] = "Does merging Bubble Cluster help?"
    ws["B1"].font = Font(size=16, bold=True, color=TITLE)
    para(ws, 2, "Same 630 test crops in both runs. Change = exp_b minus "
                "exp_a; green favours the merge.", col=2, grey=True)

    head(ws, 4, ["measure", "exp_a: cluster separate",
                 "exp_b: cluster merged", "change"], start=2)
    rows = [
        ("Overall accuracy (%)", pct(a["overall_accuracy"]),
         pct(b["overall_accuracy"]), True),
        ("Macro recall (%)", pct(a["macro"]["recall"]),
         pct(b["macro"]["recall"]), False),
        ("Macro F1 (%)", pct(a["macro"]["f1"]), pct(b["macro"]["f1"]), False),
        ("Weighted F1 (%)", pct(a["weighted"]["f1"]),
         pct(b["weighted"]["f1"]), True),
        ("Total training time (s)", a["training_time_sec"],
         b["training_time_sec"], False),
        ("Cold inference per image (ms)", a["inference_per_image_ms"],
         b["inference_per_image_ms"], False),
        ("Test crops scored", a["num_test_images"], b["num_test_images"], None),
    ]
    r = 5
    for name, va, vb, higher_better in rows:
        ws.cell(row=r, column=2, value=name).border = BOX
        ws.cell(row=r, column=3, value=va).border = BOX
        ws.cell(row=r, column=4, value=vb).border = BOX
        d = round(vb - va, 3)
        dc = ws.cell(row=r, column=5, value=d)
        dc.border = BOX
        dc.font = Font(bold=True)
        if higher_better is not None and d != 0:
            good = (d > 0) if higher_better else (d < 0)
            dc.fill = PatternFill("solid", fgColor=GOOD if good else BAD)
        r += 1

    r += 1
    para(ws, r, "Reading it: the merge lifts overall accuracy by 1.43 points "
                "on the very same test crops, and weighted F1 by 1.52. Macro "
                "recall and macro F1 read lower in exp_b, but that is "
                "arithmetic, not damage: exp_a carries a seventh row (Bubble "
                "Cluster, F1 86) that lifts its average, and exp_a's own "
                "Bubble row is the easier 405-crop set while exp_b's Bubble "
                "must cover all 486. On the classes both runs share, moves "
                "are small and mixed (Extraneous Polymer +2.4 recall, Fiber "
                "-7.7, Wet Package -5.1, Foreign Matter -3.7), each on test "
                "counts of 13 to 59 crops.", col=2, grey=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    ws.row_dimensions[r].height = 90
    r += 2
    para(ws, r, "Bubble family found (pooled, of 486 crops): exp_a scores "
                "467/486 = 96.09% (Bubble 402 + Cluster 65); exp_b scores "
                "480/486 = 98.77%. The cluster's 81 crops are found at "
                "80.25% on their own and 98.77% inside Bubble.", col=2,
         bold=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    ws.row_dimensions[r].height = 46

    # ---------------- Per class ----------------
    ws = wb.create_sheet("Per class")
    widths = {"A": 4, "B": 24, "C": 11, "D": 11, "E": 8, "F": 6, "G": 11,
              "H": 11, "I": 8, "J": 6, "K": 11}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws["B1"] = "Recall, precision and F1 for every class"
    ws["B1"].font = Font(size=16, bold=True, color=TITLE)
    para(ws, 2, "exp_a keeps Bubble Cluster as its own class; exp_b folds it "
                "into Bubble, so its row disappears and Bubble grows from 405 "
                "to 486 test crops. Deltas compare shared classes only.",
         col=2, grey=True)

    ws.cell(row=4, column=3, value="exp_a: cluster separate").font = Font(
        bold=True, color=HEAD)
    ws.cell(row=4, column=7, value="exp_b: cluster merged").font = Font(
        bold=True, color=HEAD)
    ws.merge_cells(start_row=4, start_column=3, end_row=4, end_column=6)
    ws.merge_cells(start_row=4, start_column=7, end_row=4, end_column=10)
    head(ws, 5, ["class", "recall %", "precision %", "F1", "support",
                 "recall %", "precision %", "F1", "support",
                 "recall change"], start=2)

    order = ["Bubble", "Bubble Cluster", "Wet Package", "Extraneous Polymer",
             "Foreign Matter", "Fiber", "HEMA Fragment"]
    r = 6
    for i, cls in enumerate(order):
        pa = a["per_class"].get(cls)
        pb = b["per_class"].get(cls)
        fill = PatternFill("solid", fgColor=SUBTLE) if i % 2 else None
        c = ws.cell(row=r, column=2, value=cls)
        c.border = BOX
        c.font = Font(bold=(cls == "Bubble Cluster"))
        if fill:
            c.fill = fill
        for col, d, key in ((3, pa, "recall"), (4, pa, "precision"),
                            (5, pa, "f1"), (6, pa, "support"),
                            (7, pb, "recall"), (8, pb, "precision"),
                            (9, pb, "f1"), (10, pb, "support")):
            if d is None:
                cc = ws.cell(row=r, column=7, value="folded into Bubble")
                cc.border = BOX
                cc.font = Font(italic=True, color=GREY)
                cc.alignment = Alignment(horizontal="center")
                if fill:
                    cc.fill = fill
                ws.merge_cells(start_row=r, start_column=7, end_row=r,
                               end_column=10)
                break
            v = d[key]
            if key != "support":
                v = pct(v)
            cc = ws.cell(row=r, column=col, value=v)
            cc.border = BOX
            if fill:
                cc.fill = fill
        if pa and pb:
            delta = pct(pb["recall"]) - pct(pa["recall"])
            dc = ws.cell(row=r, column=11, value=round(delta, 2))
            dc.border = BOX
            dc.font = Font(bold=True)
            if delta:
                dc.fill = PatternFill(
                    "solid", fgColor=GOOD if delta > 0 else BAD)
        r += 1

    r += 1
    para(ws, r, "HEMA Fragment scores 0% in both runs on 3 test crops, and "
                "Fiber sits at 31-38% on 13: both are sample-size limits, "
                "not consequences of the merge. Bubble Cluster is the row the "
                "experiment is about - 80.25% alone versus 98.77% inside "
                "Bubble.", col=2, grey=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=12)
    ws.row_dimensions[r].height = 46

    # ---------------- Counts ----------------
    ws = wb.create_sheet("Counts")
    for col, w in (("A", 4), ("B", 7), ("C", 24), ("D", 12), ("E", 11),
                   ("F", 12), ("G", 12), ("H", 11), ("I", 12), ("J", 13)):
        ws.column_dimensions[col].width = w
    ws["B1"] = "Pictures and crops per class, and how the split fell"
    ws["B1"].font = Font(size=16, bold=True, color=TITLE)
    para(ws, 2, "526 images carry boxes, 2,153 crops were written (4 Stretched "
                "Bubble boxes excluded, 0 crop errors). One shared split: 522 "
                "images into 366 train / 156 test, seed 42, stratified on the "
                "7-class labels; 0 images in both sides.", col=2, grey=True)

    r = 4
    for exp, title in (("exp_a", "exp_a: 7 classes (cluster separate)"),
                       ("exp_b", "exp_b: 6 classes (cluster merged)")):
        c = ws.cell(row=r, column=2, value=title)
        c.font = Font(bold=True, color=HEAD)
        r += 1
        head(ws, r, ["#", "class", "images", "crops", "avg crops/img",
                     "train images", "test images", "train crops",
                     "test crops"], start=2)
        r += 1
        rows = [x for x in counts if x["experiment"] == exp]
        for i, x in enumerate(rows, start=1):
            vals = [i, x["class"], int(x["images_total"]), int(x["crops_total"]),
                    float(x["avg_crops_per_image"]), int(x["images_train"]),
                    int(x["images_test"]), int(x["crops_train"]),
                    int(x["crops_test"])]
            for j, v in enumerate(vals, start=2):
                cc = ws.cell(row=r, column=j, value=v)
                cc.border = BOX
                if i % 2 == 0:
                    cc.fill = PatternFill("solid", fgColor=SUBTLE)
            r += 1
        # totals
        ti = sum(int(x["images_total"]) for x in rows)
        tc = sum(int(x["crops_total"]) for x in rows)
        ttr = sum(int(x["crops_train"]) for x in rows)
        tte = sum(int(x["crops_test"]) for x in rows)
        for j, v in ((2, ""), (3, "TOTAL"), (4, ti), (5, tc),
                     (6, round(tc / ti, 2)), (7, ""), (8, ""), (9, ttr),
                     (10, tte)):
            cc = ws.cell(row=r, column=j, value=v)
            cc.font = Font(bold=True)
            cc.border = BOX
            cc.fill = PatternFill("solid", fgColor="DDEBF7")
        r += 3

    para(ws, r, "Note: Bubble Cluster shows 76 train and 81 test crops because "
                "its 12 test images happen to carry more boxes than its 25 "
                "train images. The image split itself is 70/30 (25 train / 12 "
                "test) as intended; crops per image vary from 1 to 11. "
                "Bubble averages 8.2 crops per image in exp_a - the model "
                "sees the same picture's defects many times, which is why "
                "bubble rows dominate the crop pool (71% of all crops).",
         col=2, grey=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=10)
    ws.row_dimensions[r].height = 60

    # ---------------- Confusion matrices ----------------
    for exp, sheet, blurb in (
        ("exp_a", "Confusion exp_a",
         "exp_a, 7 classes, cluster separate. Rows are the true class, "
         "columns what the model predicted. 630 test crops."),
        ("exp_b", "Confusion exp_b",
         "exp_b, 6 classes, cluster merged. Rows are the true class, "
         "columns what the model predicted. The same 630 test crops."),
    ):
        ws = wb.create_sheet(sheet)
        ws.column_dimensions["A"].width = 4
        ws["B1"] = "Confusion matrix: %s" % exp
        ws["B1"].font = Font(size=16, bold=True, color=TITLE)
        para(ws, 2, blurb, col=2, grey=True)
        p = os.path.join(RUN, exp, "confusion_matrix_resnet50_inception.png")
        img = XLImage(p)
        # source renders around 6.5x5.5 in; keep readable size
        img.width = int(img.width * 0.85)
        img.height = int(img.height * 0.85)
        ws.add_image(img, "B4")

    wb.save(OUT)
    print("wrote", OUT)
    print("sheets:", wb.sheetnames)


if __name__ == "__main__":
    main()
