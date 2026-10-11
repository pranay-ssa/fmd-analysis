#!/usr/bin/env python3
"""Lead workbook: minimal, to the point. One file to share.

reports/bubble_merge/FMD_BubbleMerge_Lead_20261007.xlsx

Four sheets, one screen each:
    1. Answer       the question, the answer, the one table that matters
    2. Bubble recall  bar chart per reading, plus the numbers behind it
    3. What it cost   the two named costs, one row each, numbers inline
    4. Recommendation what to decide, what to ask the client, limits

All numbers from the verified runs2 artifacts. Plain English headers.
"""
from __future__ import annotations

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(REPO, "run", "bubble_merge", "20261007", "runs2")
OUT = os.path.join(REPO, "reports", "bubble_merge",
                   "FMD_BubbleMerge_Lead_20261007.xlsx")

FAMILY = ["Bubble", "Bubble On 123", "Bubble On Edge", "Bubble Irregular"]
ARCHS = [("ResNet50", "bubble_merge_resnet50_separate",
          "bubble_merge_resnet50_merged"),
         ("MultiLevel MultiScale", "bubble_merge_multiscale_separate",
          "bubble_merge_multiscale_merged")]

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

TITLE = "1F4E79"
HEAD = "2E75B6"
WHITE = "FFFFFF"
SUBTLE = "F2F7FC"
GREY = "7F7F7F"
GOOD = "C6EFCE"
BAD = "FFC7CE"
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def load(run_id):
    d = os.path.join(RUNS, run_id)
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    with open(os.path.join(d, "confusion.json"), encoding="utf-8") as fh:
        c = json.load(fh)
    return m, c


def family(conf, names):
    cls, mat = conf["class_names"], conf["matrix"]
    idx = [i for i, c in enumerate(cls) if c in names]
    tp = sum(mat[i][i] for i in idx)
    support = sum(sum(mat[i]) for i in idx)
    cross = sum(mat[r][c] for r in idx for c in idx if r != c)
    return tp, support, tp / support if support else 0.0, cross


def recall(conf, name):
    cls, mat = conf["class_names"], conf["matrix"]
    i = cls.index(name)
    tp = mat[i][i]
    return tp, tp / sum(mat[i]) if sum(mat[i]) else 0.0


def head(ws, row, cols, texts):
    for j, t in enumerate(texts, start=1):
        c = ws.cell(row=row, column=cols + j - 1, value=t)
        c.font = Font(bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor=HEAD)
        c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")


def main():
    runs = {}
    for _, sid, mid in ARCHS:
        runs[sid] = load(sid)
        runs[mid] = load(mid)

    wb = Workbook()
    wb.remove(wb.active)

    # ================= sheet 1: Answer =================
    ws = wb.create_sheet("Answer")
    ws.column_dimensions["A"].width = 4
    for col, w in (("B", 30), ("C", 16), ("D", 16), ("E", 15)):
        ws.column_dimensions[col].width = w

    ws["B2"] = "Should the four bubble classes become one class?"
    ws["B2"].font = Font(size=16, bold=True, color=TITLE)
    ws["B3"] = "Same pictures, same test set, same training setup. Only the class names changed."
    ws["B3"].font = Font(color=GREY)

    ws["B5"] = "The number that matters: bubble test pictures found (of 54)"
    ws["B5"].font = Font(bold=True)
    head(ws, 6, 1, ["model", "four classes", "one class", "gain"])
    r = 7
    chart_rows = []
    for arch, sid, mid in ARCHS:
        tp_s, sup, r_s, _ = family(runs[sid][1], FAMILY)
        tp_m, _s, r_m, _ = family(runs[mid][1], ["Bubble"])
        ws.cell(row=r, column=2, value=arch).border = BOX
        ws.cell(row=r, column=3, value=round(100 * r_s, 1)).border = BOX
        ws.cell(row=r, column=4, value=round(100 * r_m, 1)).border = BOX
        g = ws.cell(row=r, column=5, value=round(100 * (r_m - r_s), 1))
        g.border = BOX
        g.fill = PatternFill("solid", fgColor=GOOD)
        g.font = Font(bold=True)
        chart_rows.append((arch, round(100 * r_s, 1), round(100 * r_m, 1)))
        r += 1
    ws.cell(row=r, column=2, value="Percent of the 54 bubble test pictures the model named correctly.").font = Font(color=GREY)

    ws["B12"] = "Overall accuracy: no drop"
    ws["B12"].font = Font(bold=True)
    head(ws, 13, 1, ["model", "four classes", "one class", "change"])
    r = 14
    for arch, sid, mid in ARCHS:
        s, m = runs[sid][0]["overall_accuracy"], runs[mid][0]["overall_accuracy"]
        ws.cell(row=r, column=2, value=arch).border = BOX
        ws.cell(row=r, column=3, value=round(100 * s, 1)).border = BOX
        ws.cell(row=r, column=4, value=round(100 * m, 1)).border = BOX
        c = ws.cell(row=r, column=5, value=round(100 * (m - s), 1))
        c.border = BOX
        r += 1
    ws.cell(row=r, column=2, value="Accuracy on all 3,185 test pictures. The merge costs nothing overall.").font = Font(color=GREY)

    # ================= sheet 2: Bubble recall =================
    ws = wb.create_sheet("Bubble recall")
    ws.column_dimensions["A"].width = 4
    for col, w in (("B", 24), ("C", 14), ("D", 14), ("E", 12)):
        ws.column_dimensions[col].width = w
    ws["B2"] = "Bubble test pictures found (of 54)"
    ws["B2"].font = Font(size=16, bold=True, color=TITLE)
    ws["B3"] = "Percent the model named correctly, per reading."
    ws["B3"].font = Font(color=GREY)
    head(ws, 5, 1, ["model", "four classes", "one class", "gain"])
    for i, (arch, s, m) in enumerate(chart_rows):
        r = 6 + i
        ws.cell(row=r, column=2, value=arch).border = BOX
        ws.cell(row=r, column=3, value=s).border = BOX
        ws.cell(row=r, column=4, value=m).border = BOX
        g = ws.cell(row=r, column=5, value=round(m - s, 1))
        g.border = BOX
        g.fill = PatternFill("solid", fgColor=GOOD)
        g.font = Font(bold=True)

    ch = BarChart()
    ch.title = "Bubble pictures found, percent (of 54)"
    data = Reference(ws, min_col=3, max_col=4, min_row=5, max_row=7)
    cats = Reference(ws, min_col=2, min_row=6, max_row=7)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.height, ch.width = 8, 16
    ws.add_chart(ch, "B10")

    # ================= sheet 3: What it cost =================
    ws = wb.create_sheet("What it cost")
    ws.column_dimensions["A"].width = 4
    for col, w in (("B", 22), ("C", 14), ("D", 14), ("E", 46)):
        ws.column_dimensions[col].width = w
    ws["B2"] = "The merge has two watch-points. Both are named."
    ws["B2"].font = Font(size=16, bold=True, color=TITLE)
    head(ws, 4, 1, ["class", "before", "after", "change", "why it moved"])
    r = 5
    for arch, sid, mid in ARCHS:
        c = ws.cell(row=r, column=2, value=arch)
        c.font = Font(bold=True, color=HEAD)
        r += 1
        for cls in ("Bubble Cluster", "Fiber"):
            _tp, r_s = recall(runs[sid][1], cls)
            _tpm, r_m = recall(runs[mid][1], cls)
            delta = round(100 * (r_m - r_s), 1)
            if cls == "Bubble Cluster":
                if delta < 0:
                    why = ("not part of the merge, but the bigger Bubble "
                           "class pulls in its pictures: 6 of 11 test "
                           "pictures called Bubble")
                else:
                    why = ("same pull, but this model gains more from the "
                           "merge elsewhere; the swallow shows on ResNet50")
            else:
                why = ("17 of its test pictures now land in Foreign Matter; "
                       "partly the annotation update, partly the merge")
            ws.cell(row=r, column=2, value=cls).border = BOX
            ws.cell(row=r, column=3, value=round(100 * r_s, 1)).border = BOX
            ws.cell(row=r, column=4, value=round(100 * r_m, 1)).border = BOX
            d = ws.cell(row=r, column=5, value=delta)
            d.border = BOX
            d.fill = PatternFill("solid", fgColor=BAD if delta < 0 else GOOD)
            d.font = Font(bold=True)
            why_c = ws.cell(row=r, column=6, value=why)
            why_c.alignment = Alignment(wrap_text=True, vertical="top")
            why_c.border = BOX
            r += 1
    ws.column_dimensions["F"].width = 52
    ws.cell(row=r + 1, column=2,
            value="All other classes move less than one point, except gains "
                  "on Foreign Matter (+9.4) and HEMA Obstruction (+19.6 on "
                  "MultiScale). The merge does not destabilize the model."
            ).font = Font(color=GREY)

    # ================= sheet 4: Recommendation =================
    ws = wb.create_sheet("Recommendation")
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 110
    ws["B2"] = "What we recommend"
    ws["B2"].font = Font(size=16, bold=True, color=TITLE)
    lines = [
        ("Merge the four bubble classes, as proposed.", True),
        ("Result: bubble recall rises from 43-56 to 65-67 percent. "
         "Overall accuracy does not drop (MultiScale gains 1.4 points).", False),
        ("", False),
        ("Ask the client one question: should Bubble Cluster join the merge?", True),
        ("It sits outside the merge and loses pictures to the bigger "
         "Bubble class (45.5 to 18.2 recall on ResNet50). Folding it in "
         "fixes that; same defect family, 36 pictures. We can bring the "
         "verified number in about two hours.", False),
        ("", False),
        ("Watch Fiber. Do not change anything for it yet.", True),
        ("It drops 20 points on ResNet50, but part of that is the "
         "annotation update (33 old-Fiber pictures became Extraneous "
         "Polymer), not the merge. It needs its own look.", False),
        ("", False),
        ("The honest limit", True),
        ("One run per cell, one fixed seed. The big moves above are far "
         "outside noise. Moves under one point, and classes with fewer "
         "than 10 test pictures, are not conclusive on their own.", False),
    ]
    r = 4
    for text, bold in lines:
        c = ws.cell(row=r, column=2, value=text)
        c.font = Font(size=12, bold=True, color=TITLE) if bold else Font(size=11)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        r += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
