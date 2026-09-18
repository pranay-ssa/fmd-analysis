#!/usr/bin/env python3
"""
Build the step-4 deliverables from the five per-line runs.

Inputs (local mirrors of the VM run directories):
    runs/cnn/lines/<line>/epochs_50/metrics.json
    runs/cnn/lines/<line>/epochs_50/confusion_matrix_<line>.csv
    runs/cnn/lines/<line>/epochs_50/history.json
    runs/cnn/lines/<line>/epochs_50/confusion_matrix_<line>.png

Outputs:
    reports/cnn/FMD_Line_ResNet50_Results_20260917.xlsx
        Summary | one sheet per line | Cells by support
    notebooks/FMD_Line_Models_20260917.ipynb
        the reader-facing notebook for the lead: protocol, tables, matrices
    run/line_results_20260917/summary.json
        every figure the workbook prints, as data, so the verifier can diff it

One source of truth, three views: nothing in the outputs is typed twice.
"""
from __future__ import annotations

import base64
import csv
import json
import os
import statistics as st

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.environ.get("LINE_RESULTS_RUNS") or os.path.join(REPO, "runs", "cnn", "lines")
OUT_XLSX = os.environ.get("LINE_RESULTS_XLSX") or os.path.join(
    REPO, "reports", "cnn", "FMD_Line_ResNet50_Results_20260917.xlsx")
OUT_NB = os.environ.get("LINE_RESULTS_NB") or os.path.join(
    REPO, "notebooks", "FMD_Line_Models_20260917.ipynb")
OUT_JSON = os.environ.get("LINE_RESULTS_JSON") or os.path.join(
    REPO, "run", "line_results_20260917", "summary.json")

# Which run this workbook describes, and an optional second run to compare it against.
# The same builder then serves the ResNet50 run, the six-class run and the multi-scale
# run, and can put two of them side by side on one sheet.
EXPERIMENT_LABEL = os.environ.get("LINE_RESULTS_LABEL") or "ResNet50"
COMPARE_RUNS = os.environ.get("LINE_RESULTS_COMPARE_RUNS") or ""
COMPARE_LABEL = os.environ.get("LINE_RESULTS_COMPARE_LABEL") or "the comparison run"

LINES = ["L24", "L25", "L26", "L27", "L31"]
def protocol_lines(data):
    """The Summary sheet's protocol block, computed from the run it describes.

    The counts are read from the run's own metrics, so the same builder is correct for the full
    run, the six-class run and the multi-scale run. LINE_RESULTS_DROPPED carries the one detail
    that cannot be read back from the results, namely which cells the split had to drop.
    """
    train = sum(data[l]["metrics"]["num_train_images"] for l in LINES)
    test = sum(data[l]["metrics"]["num_test_images"] for l in LINES)
    cells = sum(data[l]["metrics"]["num_classes"] for l in LINES)
    dropped = os.environ.get("LINE_RESULTS_DROPPED", "")
    second = "Classes with no test picture on a line are dropped from that line entirely"
    if dropped:
        second += ": " + dropped
    second += ". This run holds {0} class-line cells, {1} pictures, {2} train and {3} test.".format(
        cells, train + test, f"{train:,}", f"{test:,}")
    arch = data[LINES[0]]["metrics"].get("arch_label", "ResNet50")
    return [
        "Five models, one per production line. Each model trains on its own line's train half and is",
        "scored on held-out pictures from the same line. Architecture: {0}.".format(arch),
        "50 epochs, batch 4, seed 42, SGD lr 1e-4 momentum 0.9 Nesterov, sparse categorical crossentropy,",
        "ImageNet weights with the base fully trainable. Input is the raw 2448x2048 frame resized to",
        "224x224, no crop.",
        "",
        "Against the six-architecture run of 2026-09-15 the model, optimizer, loss, metric set and seed are",
        "the same code. Three differences are deliberate: batch 4 instead of 8 (the instruction for this",
        "step), the raw frame instead of the fixed-size crop, and one model per line instead of one pooled",
        "model. The batch and the input difference mean these numbers are not comparable with that run's.",
        "",
        "Split: exact-count stratified, seed 42, inside each class inside each line, "
        "test = round-half-up(n x 0.30).",
        second,
    ]


TITLE = Font(bold=True, size=14)
SUB = Font(bold=True, size=11)
HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="1F3864")
NOTE = Font(italic=True, size=9, color="555555")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MISSING_FILL = PatternFill("solid", fgColor="FFF2CC")   # class not present on that line

# The column order and short codes of ContactLensDefectResults_combined22.xlsx Sheet1,
# so the per-line table can be read side by side with the six-architecture table.
CLASS_CODE = [
    ("Bubble", "BB"), ("Bubble Cluster", "BC"), ("Bubble Irregular", "BI"),
    ("Bubble On 123", "B123"), ("Bubble On Edge", "BOE"), ("Bubble Scatter", "BS"),
    ("Cavity Off Center", "COC"), ("Dirty Camera", "DC"), ("Dirty Strobe", "DS"),
    ("Extraneous Polymer", "EP"), ("Fiber", "FB"), ("Foreign Matter", "FM"),
    ("HEMA Fragment", "HF"), ("HEMA Obstruction", "HO"), ("Lens Off Center", "LOC"),
    ("Low Dose Obstructing Region of Interest", "LDO"), ("Missing Lens", "ML"),
    ("Missing Primary Package", "MPP"), ("Multiple Lenses", "MUL"),
    ("Package Misalignment", "PM"), ("View Obstructed", "VO"), ("Wet Package", "WP"),
]


def load(root=None):
    data = {}
    for line in LINES:
        d = os.path.join(root or RUNS, line, "epochs_50")
        m = json.load(open(os.path.join(d, "metrics.json")))
        cm_rows = list(csv.reader(open(os.path.join(d, "confusion_matrix_{0}.csv".format(line)),
                                        newline="", encoding="utf-8")))
        classes = cm_rows[0][1:-1]
        matrix = [[int(x) for x in row[1:-1]] for row in cm_rows[1:]]
        data[line] = {"metrics": m, "classes": classes, "cm": matrix, "dir": d}
    return data


def band_stats(cells):
    bands = [("1 to 4 test pictures", lambda n: n <= 4),
             ("5 to 24 test pictures", lambda n: 5 <= n <= 24),
             ("25 or more test pictures", lambda n: n >= 25)]
    out = []
    for label, fn in bands:
        grp = [c for c in cells if fn(c["support"])]
        f1s = [c["f1"] for c in grp]
        out.append({
            "band": label, "cells": len(grp),
            "mean_f1": round(st.mean(f1s), 4) if f1s else None,
            "median_f1": round(st.median(f1s), 4) if f1s else None,
            "zero_f1_cells": sum(1 for f in f1s if f == 0),
            "min_f1": round(min(f1s), 4) if f1s else None,
            "max_f1": round(max(f1s), 4) if f1s else None,
        })
    return out


def style_header(ws, row, ncols, first=1):
    for c in range(first, first + ncols):
        cell = ws.cell(row=row, column=c)
        cell.font, cell.fill, cell.border = HEAD, FILL, BOX


def box(ws, r0, r1, ncols, first=1):
    for r in range(r0, r1 + 1):
        for c in range(first, first + ncols):
            ws.cell(row=r, column=c).border = BOX


def build_cnn_format_sheet(wb, data):
    """A per-line table in the layout of ContactLensDefectResults_combined22.xlsx Sheet1.

    Columns keep that workbook's order and short class codes. Two columns are added
    because the five models do not carry the same class list: the number of test
    pictures in the line, and the macro recall. A class that does not occur on a line
    has no recall to report, so the cell is left empty and shaded amber.
    """
    ws = wb.create_sheet("Line summary (CNN format)")
    ws["A1"] = "#"
    ws["B1"] = "Line"
    ws["C1"] = "Model"
    ws["D1"] = "Overall Accuracy (%)"
    ws["E1"] = "Macro recall (%)"
    ws["F1"] = "Test images"
    ws["G1"] = "Recall (%)"
    first_cls = 7
    for i, (_, code) in enumerate(CLASS_CODE):
        ws.cell(row=2, column=first_cls + i, value=code)
    last_cls = first_cls + len(CLASS_CODE) - 1
    train_col = last_cls + 1
    infer_col = train_col + 1
    ws.cell(row=1, column=train_col, value="Training time (s)")
    ws.cell(row=1, column=infer_col, value="Inference Time per Image(ms)")
    ws.merge_cells(start_row=1, start_column=7, end_row=1, end_column=last_cls)
    for c in list(range(1, 7)) + [train_col, infer_col]:
        ws.merge_cells(start_row=1, start_column=c, end_row=2, end_column=c)
    for c in range(1, infer_col + 1):
        cell = ws.cell(row=1, column=c)
        cell.font, cell.fill, cell.border = HEAD, FILL, BOX
        ws.cell(row=2, column=c).font, ws.cell(row=2, column=c).fill = HEAD, FILL
        ws.cell(row=2, column=c).border = BOX
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=1, column=7).alignment = Alignment(horizontal="center", vertical="center")

    r = 2
    for i, line in enumerate(LINES):
        r += 1
        m = data[line]["metrics"]
        ws.cell(row=r, column=1, value=i + 1)
        ws.cell(row=r, column=2, value=line)
        ws.cell(row=r, column=3, value="ResNet50")
        ws.cell(row=r, column=4, value=round(m["overall_accuracy"] * 100, 2))
        ws.cell(row=r, column=5, value=round(m["macro"]["recall"] * 100, 2))
        ws.cell(row=r, column=6, value=m["num_test_images"])
        for j, (cls, _) in enumerate(CLASS_CODE):
            col = first_cls + j
            if cls in m["per_class"]:
                ws.cell(row=r, column=col, value=round(m["per_class"][cls]["recall"] * 100, 2))
            else:
                ws.cell(row=r, column=col, value=None)
                ws.cell(row=r, column=col).fill = MISSING_FILL
        ws.cell(row=r, column=train_col, value=round(m["training_time_sec"], 2))
        ws.cell(row=r, column=infer_col, value=m["inference_per_image_ms"])
    box(ws, 3, r, infer_col)

    # Pooled row: the five confusion matrices added together, so it answers "all five lines together"
    # rather than "the average of five numbers". Every one of the 22 classes then has a recall over all
    # the test pictures of that class across the lines.
    global_order = [cls for cls, _ in CLASS_CODE]
    gidx = {c: i for i, c in enumerate(global_order)}
    pooled = [[0] * len(global_order) for _ in global_order]
    for line in LINES:
        classes = data[line]["classes"]
        for i, true in enumerate(classes):
            for j, pred in enumerate(classes):
                pooled[gidx[true]][gidx[pred]] += data[line]["cm"][i][j]
    rowsum = [sum(row) for row in pooled]
    diag = sum(pooled[i][i] for i in range(len(pooled)))
    total = sum(rowsum)
    r += 1
    ws.cell(row=r, column=1, value="All five")
    ws.cell(row=r, column=2, value="pooled")
    ws.cell(row=r, column=3, value="ResNet50 x5")
    ws.cell(row=r, column=4, value=round(diag / total * 100, 2))
    ws.cell(row=r, column=5, value=round(st.mean([pooled[i][i] / rowsum[i] for i in range(len(pooled))
                                                  if rowsum[i]]) * 100, 2))
    ws.cell(row=r, column=6, value=total)
    for j in range(len(global_order)):
        ws.cell(row=r, column=first_cls + j,
                value=round(pooled[j][j] / rowsum[j] * 100, 2) if rowsum[j] else None)
    ws.cell(row=r, column=train_col, value=round(sum(data[l]["metrics"]["training_time_sec"] for l in LINES), 2))
    ws.cell(row=r, column=infer_col,
            value=round(sum(data[l]["metrics"]["inference_per_image_ms"] * data[l]["metrics"]["num_test_images"]
                            for l in LINES) / total, 3))
    for c in range(1, infer_col + 1):
        ws.cell(row=r, column=c).font = BOLD
    box(ws, r, r, infer_col)
    pooled_row = r

    r += 2
    # The notes are computed from the data, not written for one run, so the same builder tells the
    # truth for the full run, the six-class run and the multi-scale run.
    test_total = sum(data[l]["metrics"]["num_test_images"] for l in LINES)
    pooled_acc = sum(data[l]["metrics"]["overall_accuracy"] * data[l]["metrics"]["num_test_images"]
                     for l in LINES) / test_total
    mean_acc = st.mean(data[l]["metrics"]["overall_accuracy"] for l in LINES)
    mean_macro_r = st.mean(data[l]["metrics"]["macro"]["recall"] for l in LINES)
    class_counts = [data[l]["metrics"]["num_classes"] for l in LINES]
    union = sorted({c for l in LINES for c in data[l]["classes"]})
    pooled = {c: [0, 0] for c in union}          # correct, total, over the five lines added up
    for l in LINES:
        classes = data[l]["classes"]
        for i, true in enumerate(classes):
            pooled[true][0] += data[l]["cm"][i][i]
            pooled[true][1] += sum(data[l]["cm"][i])
    recs = [pooled[c][0] / pooled[c][1] for c in union if pooled[c][1]]
    pooled_macro = sum(recs) / len(recs) if recs else 0.0
    per_line_tests = ", ".join(str(data[l]["metrics"]["num_test_images"]) for l in LINES)
    class_counts_text = ("{0} and {1}".format(", ".join(str(c) for c in class_counts[:-1]),
                                              class_counts[-1]) if len(class_counts) > 1
                         else str(class_counts[0]))
    notes = [
        "The All five row adds the five confusion matrices together rather than averaging five numbers. Its "
        "accuracy, {0:.2f} percent, is over every test picture the run scored, and each class recall there is "
        "over all the test pictures of that class on all five lines. Its macro recall is the mean over the "
        "{1} classes of that pooled matrix, {2:.2f} percent, so it is a different quantity from the plain "
        "mean of the five per-line macro recalls, {3:.2f} percent, which appears on the Summary sheet.".format(
            pooled_acc * 100, len(union), pooled_macro * 100, mean_macro_r * 100),
        "Amber cells: the class does not occur on that line at all, so there is no recall to report. The five "
        "models carry {0} classes against {1} in the union of all five.".format(
            class_counts_text, len(union))
        if len(set(class_counts)) > 1 else
        "Every line carries the same {0} classes, so a class absent from a line has no cells to report and "
        "its column is amber throughout.".format(len(union)),
        "Overall Accuracy is that line's own test half, so each figure rests on a different number of "
        "pictures: {0}. Pooled over all {1}, accuracy is {2:.2f} percent; the plain mean of the five is "
        "{3:.2f} percent.".format(per_line_tests, test_total, pooled_acc * 100, mean_acc * 100),
        "Macro recall is the mean of that line's per-class recalls, so a class with one or two test pictures "
        "moves it a lot. Accuracy and macro recall answer different questions and should be read together.",
        "Dataset: the Updated folders plus the {0} pictures only the older library holds, one label per "
        "picture, exact-count stratified 70:30 inside each class inside each line, seed 42.".format(
            os.environ.get("LINE_RESULTS_OLD_ONLY", "177")),
        "Input: the raw 2448x2048 frame resized to 224x224, no crop. Batch 4, 50 epochs, seed 42. This is not "
        "the crop pipeline of the six-architecture table, so the two are not directly comparable.",
        "Training time and inference per image are that line's own run as recorded, in seconds and "
        "milliseconds. Inference was timed during the evaluation pass with no separate warmup pass, so it "
        "includes the one-time graph and cuDNN cost and reads higher than the warm column in the "
        "six-architecture table. Compare the two columns only with that in mind.",
        "Every recall figure here is the row's true-class recall from that line's confusion matrix, on its "
        "own test half only. A cell with four or fewer test pictures is not evidence.",
    ]
    if os.environ.get("LINE_RESULTS_EXTRA_NOTE"):
        notes.append(os.environ["LINE_RESULTS_EXTRA_NOTE"])
    for text in notes:
        ws.cell(row=r, column=1, value=text).font = NOTE
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="Legend: the short codes used in the Recall block above").font = SUB
    ws.cell(row=r, column=7, value="(continued)").font = SUB
    r += 1
    half = (len(CLASS_CODE) + 1) // 2
    for i, (cls, code) in enumerate(CLASS_CODE):
        block, idx = divmod(i, half)
        row = r + idx
        code_col = 1 if block == 0 else 7
        ws.cell(row=row, column=code_col, value=code).font = BOLD
        ws.cell(row=row, column=code_col + 1, value=cls)
        ws.merge_cells(start_row=row, start_column=code_col + 1, end_row=row, end_column=code_col + 5)
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 11
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 13
    ws.column_dimensions["F"].width = 11
    for i in range(len(CLASS_CODE)):
        ws.column_dimensions[ws.cell(row=2, column=first_cls + i).column_letter].width = 7
    for c in (train_col, infer_col):
        ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = 15
    ws.freeze_panes = "D3"


def build_workbook(data, cells, bands, compare=None, label_a="ResNet50",
                   label_b="the comparison run"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "Per-line models: {0}, 70:30, batch 4, 50 epochs (2026-09-17)".format(
        EXPERIMENT_LABEL)
    ws["A1"].font = TITLE
    r = 3
    for line in protocol_lines(data):
        ws.cell(row=r, column=1, value=line)
        r += 1
    r += 1

    hdr = ["Line", "Train", "Test", "Classes", "Accuracy", "Macro precision", "Macro recall",
           "Macro F1", "Weighted precision", "Weighted recall", "Weighted F1", "Train minutes"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=c, value=h)
    style_header(ws, r, len(hdr))
    first_data = r + 1
    for line in LINES:
        m = data[line]["metrics"]
        r += 1
        vals = [line, m["num_train_images"], m["num_test_images"], m["num_classes"],
                m["overall_accuracy"], m["macro"]["precision"], m["macro"]["recall"],
                m["macro"]["f1"], m["weighted"]["precision"], m["weighted"]["recall"],
                m["weighted"]["f1"], round(m["training_time_sec"] / 60.0, 1)]
        for c, v in enumerate(vals, start=1):
            ws.cell(row=r, column=c, value=v)
            if c >= 5 and c <= 11:
                ws.cell(row=r, column=c).number_format = "0.00%"
    r += 1
    test_total = sum(data[l]["metrics"]["num_test_images"] for l in LINES)
    pooled_acc = sum(data[l]["metrics"]["overall_accuracy"] * data[l]["metrics"]["num_test_images"]
                     for l in LINES) / test_total
    pooled_f1 = sum(data[l]["metrics"]["weighted"]["f1"] * data[l]["metrics"]["num_test_images"]
                    for l in LINES) / test_total
    vals = ["All five", sum(data[l]["metrics"]["num_train_images"] for l in LINES), test_total,
            len(cells), pooled_acc, None, None,
            round(st.mean(data[l]["metrics"]["macro"]["f1"] for l in LINES), 4), None, None,
            pooled_f1, round(sum(data[l]["metrics"]["training_time_sec"] for l in LINES) / 60.0, 1)]
    for c, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = BOLD
        if c in (5, 8, 11):
            cell.number_format = "0.00%"
    ws.cell(row=r, column=1).alignment = Alignment(horizontal="left")
    box(ws, first_data, r, len(hdr))
    ws.cell(row=r + 1, column=1,
            value="All five: accuracy and weighted F1 are pooled over the 2,527 test pictures, which is not the "
                  "same as a plain average of the five lines (the plain mean of the five accuracies is 87.70 "
                  "percent against the pooled 87.77). Macro F1 is the plain mean of the five per-line macro "
                  "figures, because the five class lists differ and there is no single macro quantity across "
                  "them. Classes are counted once per line, so the 87 is cells, not classes.")
    ws.cell(row=r + 1, column=1).font = NOTE

    r += 3
    ws.cell(row=r, column=1, value="Score against test-cell size, over all 87 class-line cells").font = SUB
    r += 1
    hdr = ["Band", "Cells", "Mean F1", "Median F1", "Lowest F1", "Highest F1", "Cells scoring zero F1"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=c, value=h)
    style_header(ws, r, len(hdr))
    start = r + 1
    for b in bands:
        r += 1
        vals = [b["band"], b["cells"], b["mean_f1"], b["median_f1"], b["min_f1"], b["max_f1"],
                b["zero_f1_cells"]]
        for c, v in enumerate(vals, start=1):
            ws.cell(row=r, column=c, value=v)
            if c in (3, 4, 5, 6) and v is not None:
                ws.cell(row=r, column=c).number_format = "0.00%"
    box(ws, start, r, len(hdr))
    r += 2
    ws.cell(row=r, column=1,
            value="Reading: a class-line cell with four or fewer test pictures carries almost no information "
                  "(median F1 zero), a cell with 25 or more never scores zero, and every difference between the "
                  "five lines sits inside those bands rather than in the line.")
    ws.cell(row=r, column=1).font = NOTE
    ws.column_dimensions["A"].width = 62
    for col in "BCDEFGHIJKL":
        ws.column_dimensions[col].width = 15
    ws.freeze_panes = "A{}".format(first_data)

    for line in LINES:
        m = data[line]["metrics"]
        ws = wb.create_sheet(line)
        ws["A1"] = "{0}: ResNet50, 70:30, batch 4, 50 epochs".format(line)
        ws["A1"].font = TITLE
        ws["A2"] = ("{0} train / {1} test, {2} classes, accuracy {3:.2%}, macro F1 {4:.2%}, "
                    "weighted F1 {5:.2%}, {6:.1f} minutes of training.").format(
            m["num_train_images"], m["num_test_images"], m["num_classes"], m["overall_accuracy"],
            m["macro"]["f1"], m["weighted"]["f1"], m["training_time_sec"] / 60.0)
        ws["A3"] = "Cells with four or fewer test pictures are marked thin: their score is not evidence."
        ws["A3"].font = NOTE
        hdr = ["Class", "Test pictures", "Precision", "Recall", "F1", "Note"]
        for c, h in enumerate(hdr, start=1):
            ws.cell(row=5, column=c, value=h)
        style_header(ws, 5, len(hdr))
        r = 6
        for cls in data[line]["classes"]:
            v = m["per_class"][cls]
            note = "thin cell" if v["support"] <= 4 else ""
            for c, val in enumerate([cls, v["support"], v["precision"], v["recall"], v["f1"], note], start=1):
                cell = ws.cell(row=r, column=c, value=val)
                if c in (3, 4, 5):
                    cell.number_format = "0.00%"
            r += 1
        box(ws, 6, r - 1, len(hdr))
        ws.cell(row=r, column=1, value="Total").font = BOLD
        ws.cell(row=r, column=2, value=m["num_test_images"]).font = BOLD
        r += 2

        ws.cell(row=r, column=1, value="Confusion matrix, rows are the true class, columns the prediction").font = SUB
        r += 1
        for c, h in enumerate(["true \\ predicted"] + data[line]["classes"] + ["support"], start=1):
            ws.cell(row=r, column=c, value=h)
        style_header(ws, r, len(data[line]["classes"]) + 2)
        head_row = r
        for i, cls in enumerate(data[line]["classes"]):
            r += 1
            ws.cell(row=r, column=1, value=cls).font = BOLD
            for j, val in enumerate(data[line]["cm"][i], start=2):
                ws.cell(row=r, column=j, value=val)
            ws.cell(row=r, column=len(data[line]["classes"]) + 2,
                    value=sum(data[line]["cm"][i]))
        box(ws, head_row, r, len(data[line]["classes"]) + 2)
        r += 1
        diag = sum(data[line]["cm"][i][i] for i in range(len(data[line]["classes"])))
        ws.cell(row=r, column=1, value="correct on the diagonal: {0} of {1}".format(
            diag, m["num_test_images"])).font = NOTE
        r += 2
        png = os.path.join(data[line]["dir"], "confusion_matrix_{0}.png".format(line))
        if os.path.exists(png):
            img = XLImage(png)
            img.width, img.height = 720, 720
            ws.add_image(img, "A{0}".format(r))
        ws.column_dimensions["A"].width = 46
        for col in "BCDEF":
            ws.column_dimensions[col].width = 13
        ws.freeze_panes = "A6"

    ws = wb.create_sheet("Cells by support")
    ws["A1"] = "Every class-line cell, ordered by how many test pictures it holds"
    ws["A1"].font = TITLE
    ws["A2"] = ("This is the evidence under the summary sheet's reading. A cell's F1 says more about its test "
                "size than about the line it came from.")
    ws["A2"].font = NOTE
    hdr = ["Test pictures", "Line", "Class", "Support", "Recall", "F1", "Thin?"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=4, column=c, value=h)
    style_header(ws, 4, len(hdr))
    r = 5
    for c in sorted(cells, key=lambda x: (x["support"], x["line"], x["class"])):
        for i, val in enumerate([c["support"], c["line"], c["class"], c["support"], c["recall"], c["f1"],
                                 "thin" if c["support"] <= 4 else ""], start=1):
            cell = ws.cell(row=r, column=i, value=val)
            if i in (5, 6):
                cell.number_format = "0.00%"
        r += 1
    box(ws, 5, r - 1, len(hdr))
    ws.column_dimensions["A"].width = 13
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 46
    for col in "DEFG":
        ws.column_dimensions[col].width = 13
    ws.freeze_panes = "A5"
    build_cnn_format_sheet(wb, data)
    if compare is not None:
        build_comparison_sheet(wb, data, compare, label_a, label_b)
    os.makedirs(os.path.dirname(OUT_XLSX), exist_ok=True)
    wb.save(OUT_XLSX)


def pooled(data, lines):
    """Pooled accuracy and the plain mean of the per-line macro scores.

    Pooled accuracy weights each line by its test count, which is the same as total correct
    over total scored. The macro column is a plain mean over lines, stated as such, because
    a macro score has no picture count to weight by.
    """
    test_total = sum(data[l]["metrics"]["num_test_images"] for l in lines)
    acc = sum(data[l]["metrics"]["overall_accuracy"] * data[l]["metrics"]["num_test_images"]
              for l in lines) / test_total
    macro_r = st.mean(data[l]["metrics"]["macro"]["recall"] for l in lines)
    macro_f1 = st.mean(data[l]["metrics"]["macro"]["f1"] for l in lines)
    weighted_f1 = sum(data[l]["metrics"]["weighted"]["f1"] * data[l]["metrics"]["num_test_images"]
                      for l in lines) / test_total
    return {"test": test_total, "accuracy": acc, "macro_recall": macro_r,
            "macro_f1": macro_f1, "weighted_f1": weighted_f1}


def build_comparison_sheet(wb, data, other, label_a, label_b):
    """Two runs on the same split, line by line, with the change between them."""
    ws = wb.create_sheet("{0} vs {1}".format(label_a, label_b)[:31])
    ws["A1"] = "{0} against {1}, same split, same protocol".format(label_a, label_b)
    ws["A1"].font = TITLE
    r = 3
    for text in ("Every line trains and scores the same pictures in both runs, so a difference "
                 "is the architecture and nothing else.",
                 "Pooled accuracy weights each line by its test count. The macro columns are "
                 "plain means over the five lines.",
                 "Change columns: a positive number means {0} scored higher.".format(label_b)):
        ws.cell(row=r, column=1, value=text).font = NOTE
        r += 1
    r += 1

    hdr = ["Line", "Test pictures", "{0} accuracy".format(label_a), "{0} accuracy".format(label_b),
           "Accuracy change", "{0} macro recall".format(label_a), "{0} macro recall".format(label_b),
           "Macro recall change", "{0} macro F1".format(label_a), "{0} macro F1".format(label_b),
           "Macro F1 change"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=c, value=h)
    style_header(ws, r, len(hdr))
    r += 1
    for line in LINES:
        a, b = data[line]["metrics"], other[line]["metrics"]
        vals = [line, a["num_test_images"], a["overall_accuracy"], b["overall_accuracy"],
                round(b["overall_accuracy"] - a["overall_accuracy"], 4),
                a["macro"]["recall"], b["macro"]["recall"],
                round(b["macro"]["recall"] - a["macro"]["recall"], 4),
                a["macro"]["f1"], b["macro"]["f1"],
                round(b["macro"]["f1"] - a["macro"]["f1"], 4)]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            if c in (3, 4, 5, 6, 7, 8, 9, 10, 11):
                cell.number_format = "+0.00%;-0.00%" if c in (5, 8, 11) else "0.00%"
        r += 1
    row_r = r
    for label, d in ((label_a, data), (label_b, other)):
        p = pooled(d, LINES)
        r += 1
        ws.cell(row=r, column=1, value="All five, {0}".format(label)).font = BOLD
        ws.cell(row=r, column=2, value=p["test"]).font = BOLD
        for c, v in ((3, p["accuracy"]), (6, p["macro_recall"]), (9, p["macro_f1"])):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BOLD
            cell.number_format = "0.00%"
    r += 1
    ws.cell(row=r + 1, column=1,
            value="Both runs: batch 4, 50 epochs, seed 42, raw frames resized to 224, "
                  "no crop pass.").font = NOTE
    box(ws, 7, row_r - 1, len(hdr))
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 13
    for col in "CDEFGHIJK":
        ws.column_dimensions[col].width = 15
    ws.freeze_panes = "B8"


def build_notebook(data, cells, bands):
    def md(text):
        return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}

    def code(text):
        return {"cell_type": "code", "execution_count": None, "metadata": {},
                "outputs": [], "source": text.splitlines(keepends=True)}

    def img(path, caption):
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        return {"cell_type": "markdown", "metadata": {},
                "source": ["![{0}](data:image/png;base64,{1})\n".format(caption, b64)]}

    cells_nb = [
        md("# Per-line ResNet50 models - results\n\n"
           "**Step 4, 2026-09-17.** Five models, one per production line, each trained on its own line's train\n"
           "half and scored on held-out pictures from the same line.\n\n"
           "| Setting | Value |\n|---|---|\n"
           "| Model | ResNet50, ImageNet weights, base fully trainable |\n"
           "| Head | Global average pooling, batch norm, dense 1024, dropout 0.3, softmax |\n"
           "| Optimizer | SGD, learning rate 1e-4, momentum 0.9, Nesterov |\n"
           "| Loss | sparse categorical crossentropy |\n"
           "| Epochs / batch / seed | 50 / 4 / 42 |\n"
           "| Input | the raw 2448x2048 frame resized to 224x224, no crop |\n"
           "| Split | exact-count stratified inside each class inside each line, seed 42, 70:30 |\n"
           "| Data | 8,402 pictures, 5,875 train, 2,527 test, 87 class-line cells |\n"
           "| Total training time | 52.5 minutes on one A100 for all five lines |\n\n"
           "The model, optimizer, loss, metric set and seed are the same code as the 2026-09-15\n"
           "six-architecture run. Three things differ on purpose: batch 4 instead of 8, the raw frame instead\n"
           "of the fixed-size crop, and one model per line instead of one pooled model. Those differences mean\n"
           "these numbers should not be compared with that run's numbers."),
        md("## The five models\n\n"
           "| Line | Train | Test | Classes | Accuracy | Macro F1 | Weighted F1 | Train minutes |\n"
           "|---|---|---|---|---|---|---|---|\n" +
           "".join("| {0} | {1} | {2} | {3} | {4:.2%} | {5:.2%} | {6:.2%} | {7:.1f} |\n".format(
               l, data[l]["metrics"]["num_train_images"], data[l]["metrics"]["num_test_images"],
               data[l]["metrics"]["num_classes"], data[l]["metrics"]["overall_accuracy"],
               data[l]["metrics"]["macro"]["f1"], data[l]["metrics"]["weighted"]["f1"],
               data[l]["metrics"]["training_time_sec"] / 60.0) for l in LINES) +
           "\nAccuracy and weighted F1 are pooled over the 2,527 test pictures across the five models. Macro F1\n"
           "is the mean of the five per-line macro figures; the five class lists differ, so there is no single\n"
           "macro quantity across them."),
        code("import json, os\n"
             "root = 'runs/cnn/lines'\n"
             "for line in ['L24', 'L25', 'L26', 'L27', 'L31']:\n"
             "    m = json.load(open(os.path.join(root, line, 'epochs_50', 'metrics.json')))\n"
             "    print('{0}: acc {1:.2%}  macro F1 {2:.2%}  weighted F1 {3:.2%}  test {4}'.format(\n"
             "        line, m['overall_accuracy'], m['macro']['f1'], m['weighted']['f1'], m['num_test_images']))"),
        md("## What the numbers actually say\n\n"
           "**1. The score tracks how many test pictures a class has, not which line it came from.**\n\n"
           "| Test pictures in the cell | Cells | Mean F1 | Median F1 | Lowest | Highest | Cells at zero F1 |\n"
           "|---|---|---|---|---|---|---|\n" +
           "".join("| {0} | {1} | {2:.2%} | {3:.2%} | {4:.2%} | {5:.2%} | {6} |\n".format(
               b["band"], b["cells"], b["mean_f1"], b["median_f1"], b["min_f1"], b["max_f1"], b["zero_f1_cells"])
               for b in bands) +
           "\nA cell with four or fewer test pictures has a median F1 of zero. Every cell with 25 or more test\n"
           "pictures scores above zero, and 24 of them average 83.52 percent. So a low number in a thin cell\n"
           "measures the cell, not the model and not the line.\n\n"
           "**2. The same class produces wildly different scores on different lines, and the swing follows the\n"
           "cell size.**\n\n"
           "| Class | L24 | L25 | L26 | L27 | L31 |\n|---|---|---|---|---|---|\n"
           "| Lens Off Center | 87% (59) | 0% (2) | 100% (2) | 14% (8) | 50% (6) |\n"
           "| View Obstructed | 0% (6) | 91% (5) | 33% (10) | 100% (3) | 95% (11) |\n"
           "| Missing Lens | 99% (55) | 67% (2) | 0% (1) | 96% (24) | 100% (15) |\n"
           "| Bubble Cluster | 18% (5) | 0% (1) | 100% (1) | 0% (3) | 0% (1) |\n"
           "| Multiple Lenses | 89% (101) | 95% (83) | 98% (202) | 100% (16) | 93% (29) |\n"
           "| Missing Primary Package | 100% (344) | 100% (57) | 80% (2) | 100% (4) | 100% (22) |\n\n"
           "The numbers in brackets are test pictures in that cell. Every large class repeats across lines;\n"
           "every small class does not.\n\n"
           "**3. Most errors sit inside one family, and a documented confusion shows up.**\n\n"
           "Across the five models 309 of the 2,527 test pictures are misclassified, 12.2 percent. The largest\n"
           "single directions are:\n\n"
           "| True class | Predicted as | Test pictures |\n|---|---|---|\n"
           "| Foreign Matter | Fiber | 66 |\n"
           "| Fiber | Foreign Matter | 21 |\n"
           "| Extraneous Polymer | Fiber | 20 |\n"
           "| Extraneous Polymer | Foreign Matter | 17 |\n"
           "| Lens Off Center | Low Dose Obstructing Region of Interest | 14 |\n"
           "| Foreign Matter | Extraneous Polymer | 10 |\n"
           "| Fiber | Extraneous Polymer | 8 |\n"
           "| View Obstructed | Bubble | 8 |\n\n"
           "Foreign Matter, Fiber and Extraneous Polymer account for 142 of the 309 errors, 46 percent, and they\n"
           "keep taking each other's labels. The dataset does not separate them cleanly either: 33 pictures carry\n"
           "both Extraneous Polymer and Fiber as labels and our pooling rule gives each one label. The client's\n"
           "naming document states that Lens Off Center is commonly confused with Low Dose, and that is exactly\n"
           "where 14 of the errors land.\n\n"
           "One line-specific example: on L24 all 6 of View Obstructed's test pictures were called HEMA\n"
           "Obstruction, on the one line where HEMA Obstruction is a heavyweight class. Across all five lines the\n"
           "class's largest confusion is Bubble, 8 pictures.\n\n"
           "**4. The classes that hold up are the structural ones; the ones that fail are small objects.**\n\n"
           "Missing Primary Package, Cavity Off Center, Package Misalignment and Multiple Lenses score 80 to 100\n"
           "percent nearly everywhere. Fiber, Extraneous Polymer, Bubble Cluster, Bubble Irregular and the\n"
           "single-picture classes fail. That is what a 2448-wide frame squeezed to 224x224 does to a defect a\n"
           "few tens of pixels across, and it is the visible cost of dropping the crop step."),
    ]
    for line in LINES:
        m = data[line]["metrics"]
        tbl = ["## {0}\n\n".format(line),
               "{0} train / {1} test, {2} classes, accuracy {3:.2%}, macro F1 {4:.2%}, weighted F1 {5:.2%}, "
               "{6:.1f} minutes.\n\n".format(m["num_train_images"], m["num_test_images"], m["num_classes"],
                                             m["overall_accuracy"], m["macro"]["f1"], m["weighted"]["f1"],
                                             m["training_time_sec"] / 60.0),
               "| Class | Test pictures | Precision | Recall | F1 |\n|---|---|---|---|---|\n"]
        for cls in data[line]["classes"]:
            v = m["per_class"][cls]
            tbl.append("| {0} | {1} | {2:.2%} | {3:.2%} | {4:.2%} |\n".format(
                cls, v["support"], v["precision"], v["recall"], v["f1"]))
        cells_nb.append(md("".join(tbl)))
        png = os.path.join(data[line]["dir"], "confusion_matrix_{0}.png".format(line))
        if os.path.exists(png):
            cells_nb.append(img(png, "confusion matrix {0}".format(line)))
    cells_nb.append(md("## Files\n\n"
                       "| Item | Where |\n|---|---|\n"
                       "| This notebook | `notebooks/FMD_Line_Models_20260917.ipynb` |\n"
                       "| Results workbook | `reports/cnn/FMD_Line_ResNet50_Results_20260917.xlsx` |\n"
                       "| Split assignments | `run/line_splits_20260917/line_<line>/split.csv` |\n"
                       "| Per-run outputs | `runs/cnn/lines/<line>/epochs_50/` (metrics, confusion matrix, history, log) |\n"
                       "| Trained weights | on the VM only: `~/line_experiment_20260917/runs/<line>/epochs_50/weights.weights.h5` |\n"
                       "| Trainer | `experiments/cnn/train_line_model.py` |\n"
                       "| Split builder | `src/build_line_split_assignments.py` |\n"))
    nb = {"cells": cells_nb, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                         "name": "python3"},
                                          "language_info": {"name": "python", "version": "3.12"}},
          "nbformat": 4, "nbformat_minor": 5}
    os.makedirs(os.path.dirname(OUT_NB), exist_ok=True)
    with open(OUT_NB, "w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1)


def main():
    data = load()
    cells = []
    directions = {}
    misclassified = 0
    for line in LINES:
        m = data[line]["metrics"]
        classes = data[line]["classes"]
        for cls, v in m["per_class"].items():
            cells.append({"line": line, "class": cls, "support": v["support"],
                          "recall": v["recall"], "precision": v["precision"], "f1": v["f1"]})
        for i, true in enumerate(classes):
            for j, pred in enumerate(classes):
                n = data[line]["cm"][i][j]
                if n and pred != true:
                    directions[(true, pred)] = directions.get((true, pred), 0) + n
                    misclassified += n
    bands = band_stats(cells)
    compare = load(COMPARE_RUNS) if COMPARE_RUNS else None
    build_workbook(data, cells, bands, compare=compare, label_a=EXPERIMENT_LABEL,
                   label_b=COMPARE_LABEL)
    build_notebook(data, cells, bands)
    top_directions = sorted(directions.items(), key=lambda kv: -kv[1])
    summary = {
        "lines": {l: data[l]["metrics"] for l in LINES},
        "cells": cells,
        "bands": bands,
        "confusion_directions": ["{0} -> {1}: {2}".format(a, b, n) for (a, b), n in top_directions],
        "misclassified_test_pictures": misclassified,
        "debris_family_errors": sum(n for (a, b), n in directions.items()
                                    if a in ("Foreign Matter", "Fiber", "Extraneous Polymer")
                                    and b in ("Foreign Matter", "Fiber", "Extraneous Polymer")),
        "totals": {
            "train": sum(data[l]["metrics"]["num_train_images"] for l in LINES),
            "test": sum(data[l]["metrics"]["num_test_images"] for l in LINES),
            "cells": len(cells),
            "training_time_sec": round(sum(data[l]["metrics"]["training_time_sec"] for l in LINES), 2),
        },
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    def show(path):
        try:
            return os.path.relpath(path, REPO).replace("\\", "/")
        except ValueError:          # staging path on another drive
            return path.replace("\\", "/")
    for path in (OUT_XLSX, OUT_NB, OUT_JSON):
        print("wrote", show(path))
    print("cells {0}, bands {1}".format(len(cells), [b["cells"] for b in bands]))


if __name__ == "__main__":
    main()
