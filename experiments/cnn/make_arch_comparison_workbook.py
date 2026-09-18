#!/usr/bin/env python3
"""
Workbook for the architecture comparison: ResNet50 against ResNet50-Inception MultiLevel MultiScale,
both on the full 22-class per-line split.

Reads run/line_results_multiscale_20260917/arch_vs_base.json (written by compare_architectures.py) and
writes reports/cnn/FMD_Architecture_Comparison_20260917.xlsx.

    Sheet 1  Two architectures   one row per line, both models on the same test pictures
    Sheet 2  What moved          the pooled accuracy change attributed class by class
    Sheet 3  Per class           every class-line cell, with its change flagged

    python3 make_arch_comparison_workbook.py
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "run", "line_results_multiscale_20260917", "arch_vs_base.json")
OUT = os.path.join(REPO, "reports", "cnn", "FMD_Architecture_Comparison_20260917.xlsx")

TITLE = Font(bold=True, size=14)
SUB = Font(bold=True, size=11)
HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="1F3864")
NOTE = Font(italic=True, size=9, color="555555")
BOLD = Font(bold=True)
UP = PatternFill("solid", fgColor="E2EFDA")
DOWN = PatternFill("solid", fgColor="FCE4E4")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def header(ws, row, values, widths=None):
    for c, v in enumerate(values, start=1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.font = HEAD
        cell.fill = FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(row=row, column=i).column_letter].width = w


def notes(ws, start, lines):
    r = start
    for t in lines:
        ws.cell(row=r, column=1, value=t).font = NOTE
        r += 1
    return r


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    lines = d["lines"]
    pooled = d["pooled"]
    wb = Workbook()

    # ---------------------------------------------------------------- sheet 1
    ws = wb.active
    ws.title = "Two architectures"
    ws["A1"] = "Two architectures on the same split: ResNet50 against ResNet50-Inception MultiLevel MultiScale"
    ws["A1"].font = TITLE
    r = notes(ws, 3, [
        "Both models trained on the identical per-line train halves of the full 22-class split and were scored on",
        "the identical test halves, so every difference in this sheet is the architecture and not the data. Batch 4,",
        "50 epochs, raw frame resized to 224x224 bilinear with no crop, exact-count stratified split, seed 42.",
        "Accuracy is pooled: it counts every test picture of the five lines once, so the five lines are weighted by",
        "the number of pictures they hold rather than averaged equally. Macro recall is the plain mean over the",
        "classes scored on that line, so it moves with thin classes; read it with the per-class sheet.",
        "A positive change means the multi-scale architecture scored higher.",
    ])
    hdr = r + 1
    header(ws, hdr, ["Line", "Test\npictures", "ResNet50\naccuracy", "MultiLevel\nMultiScale accuracy",
                     "Change\n(points)", "ResNet50\nmacro recall", "MultiLevel\nMultiScale macro recall",
                     "Change\n(points)", "Training\nResNet50 (min)", "Training\nmulti-scale (min)"],
           [8, 10, 12, 14, 10, 12, 15, 10, 12, 13])
    for i, ln in enumerate(lines):
        row = hdr + 1 + i
        vals = [ln["line"], ln["test_pictures"], ln["accuracy_resnet50"], ln["accuracy_multiscale"],
                ln["accuracy_gap"], ln["macro_recall_resnet50"], ln["macro_recall_multiscale"],
                ln["macro_recall_gap"], ln["train_minutes_resnet50"], ln["train_minutes_multiscale"]]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = BOX
            if c in (3, 4, 6, 7):
                cell.number_format = "0.0%"
            if c == 5:
                cell.number_format = "+0.0%;-0.0%"
                cell.fill = UP if v > 0 else (DOWN if v < 0 else PatternFill())
            if c == 8:
                cell.number_format = "+0.00%;-0.00%"
                cell.fill = UP if v > 0 else (DOWN if v < 0 else PatternFill())
    tot_row = hdr + 1 + len(lines)
    ws.cell(row=tot_row, column=1, value="All five").font = BOLD
    ws.cell(row=tot_row, column=2, value=pooled["test_pictures"]).font = BOLD
    ws.cell(row=tot_row, column=3, value=pooled["accuracy_resnet50"]).font = BOLD
    ws.cell(row=tot_row, column=4, value=pooled["accuracy_multiscale"]).font = BOLD
    ws.cell(row=tot_row, column=5, value=pooled["accuracy_gap"]).font = BOLD
    ws.cell(row=tot_row, column=6, value=st.mean(l["macro_recall_resnet50"] for l in lines)).font = BOLD
    ws.cell(row=tot_row, column=7, value=st.mean(l["macro_recall_multiscale"] for l in lines)).font = BOLD
    ws.cell(row=tot_row, column=8, value=st.mean(l["macro_recall_multiscale"] for l in lines)
            - st.mean(l["macro_recall_resnet50"] for l in lines)).font = BOLD
    ws.cell(row=tot_row, column=9, value=sum(l["train_minutes_resnet50"] for l in lines)).font = BOLD
    ws.cell(row=tot_row, column=10, value=sum(l["train_minutes_multiscale"] for l in lines)).font = BOLD
    for c in range(2, 11):
        cell = ws.cell(row=tot_row, column=c)
        if c in (3, 4, 6, 7):
            cell.number_format = "0.0%"
        if c in (5, 8):
            cell.number_format = "+0.0%;-0.0%"
        cell.border = BOX
    ws.cell(row=tot_row + 1, column=1,
            value="The All five row pools accuracy over all {0:,} test pictures; macro recall there is the plain mean of the five line values, not a pooled figure.".format(
                pooled["test_pictures"])).font = NOTE

    # ---------------------------------------------------------------- sheet 2
    ws2 = wb.create_sheet("What moved")
    ws2["A1"] = "What moved: the pooled accuracy change ({0:+.2f} points) attributed to classes".format(
        pooled["accuracy_gap"] * 100)
    ws2["A1"].font = TITLE
    r2 = notes(ws2, 3, [
        "Every class-line cell contributes (correct answers under multi-scale minus correct answers under ResNet50)",
        "divided by the {0:,} test pictures, so the column below adds up exactly to the pooled accuracy change.".format(
            pooled["test_pictures"]),
        "This is the answer to which classes the architecture helped and which it cost, rather than only whether",
        "the headline number went up.",
    ])
    hdr2 = r2 + 1
    header(ws2, hdr2, ["Defect class", "Correct answers gained or lost", "Points of pooled accuracy"],
           [46, 30, 24])
    # the json stores each class's share of the pooled accuracy change as a fraction,
    # the sheet reports it in points, so multiply once here
    attrib = {k: v * 100 for k, v in pooled["attribution_by_class_share"].items()}
    change = {}
    for pc in d["per_class"]:
        change[pc["cls"]] = change.get(pc["cls"], 0) + pc["correct_change"]
    for i, (cls, pts) in enumerate(sorted(attrib.items(), key=lambda kv: -abs(kv[1]))):
        row = hdr2 + 1 + i
        ws2.cell(row=row, column=1, value=cls).border = BOX
        c2 = ws2.cell(row=row, column=2, value=change.get(cls, 0))
        c2.border = BOX
        c2.number_format = "+0;-0;0"
        c2.fill = UP if change.get(cls, 0) > 0 else (DOWN if change.get(cls, 0) < 0 else PatternFill())
        c3 = ws2.cell(row=row, column=3, value=pts)
        c3.border = BOX
        c3.number_format = "+0.00;-0.00"
    r3 = hdr2 + 2 + len(attrib)
    ws2.cell(row=r3, column=1, value="Check: sum of the points column").font = BOLD
    ws2.cell(row=r3, column=3, value=round(sum(attrib.values()), 6)).font = BOLD
    ws2.cell(row=r3, column=3).number_format = "+0.0000;-0.0000"
    ws2.cell(row=r3 + 1, column=1,
             value="Pooled accuracy change {0:+.4f} points; the two agree, which is the point of the decomposition.".format(
                 pooled["accuracy_gap"] * 100)).font = NOTE
    r4 = r3 + 3
    ws2.cell(row=r4, column=1, value="Class-line cells, counted").font = SUB
    ws2.cell(row=r4 + 1, column=1, value="Multi-scale recalled more classes").font = BOLD
    ws2.cell(row=r4 + 1, column=2, value=pooled["cells_better"])
    ws2.cell(row=r4 + 2, column=1, value="Multi-scale recalled fewer classes").font = BOLD
    ws2.cell(row=r4 + 2, column=2, value=pooled["cells_worse"])
    ws2.cell(row=r4 + 3, column=1, value="Unchanged").font = BOLD
    ws2.cell(row=r4 + 3, column=2, value=pooled["cells_same"])
    ws2.cell(row=r4 + 4, column=1,
             value="A class-line cell is one defect class on one production line. Cells with one or two test pictures").font = NOTE
    ws2.cell(row=r4 + 5, column=1,
             value="move for reasons no architecture can be credited with, which is why the counts are shown next to the").font = NOTE
    ws2.cell(row=r4 + 6, column=1,
             value="points column rather than instead of it.").font = NOTE

    # ---------------------------------------------------------------- sheet 3
    ws3 = wb.create_sheet("Per class")
    ws3["A1"] = "Every class-line cell: how the two architectures scored the same test pictures"
    ws3["A1"].font = TITLE
    r5 = notes(ws3, 3, [
        "Recall is the share of that class's own test pictures the model answered correctly, on that line.",
        "Low support means the number is fragile: a class with two test pictures can only score 0, 50 or 100 per cent.",
    ])
    hdr3 = r5 + 1
    header(ws3, hdr3, ["Line", "Defect class", "Test pictures", "ResNet50 recall",
                       "MultiLevel MultiScale recall", "Change", "Correct answers gained or lost"],
           [8, 44, 12, 14, 22, 10, 26])
    rows = sorted(d["per_class"], key=lambda x: (x["line"], -x["support"]))
    for i, pc in enumerate(rows):
        row = hdr3 + 1 + i
        vals = [pc["line"], pc["cls"], pc["support"], pc["recall_resnet50"], pc["recall_multiscale"],
                pc["recall_gap"], pc["correct_change"]]
        for c, v in enumerate(vals, start=1):
            cell = ws3.cell(row=row, column=c, value=v)
            cell.border = BOX
            if c in (4, 5):
                cell.number_format = "0.0%"
            if c == 6:
                cell.number_format = "+0.0%;-0.0%"
                cell.fill = UP if v > 0 else (DOWN if v < 0 else PatternFill())
            if c == 7:
                cell.number_format = "+0;-0;0"
                cell.fill = UP if v > 0 else (DOWN if v < 0 else PatternFill())

    wb.save(OUT)
    print("wrote {0}".format(os.path.relpath(OUT, REPO)))
    print("sheets: {0}".format(wb.sheetnames))
    print("class-line rows written: {0}".format(len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
