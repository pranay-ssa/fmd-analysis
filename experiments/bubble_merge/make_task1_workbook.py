#!/usr/bin/env python3
"""Task 1 workbook (v2, plain English): merged versus separate bubbles.

reports/bubble_merge/FMD_BubbleMerge_Comparison_20261007.xlsx

Sheets
    Read me      the question, the data, the training setup, how to read
    Headline     both readings side by side, changes in percentage points
    What moved   where the bubble pictures went, what the merged class took in
    Per class    recall for every class, four readings, changes included
    Count table  the client's count table: tag columns versus dataset counts
    Image EDA    the pool and the split, per class, train and test

Inputs (verified): run/bubble_merge/20261007/runs2/<id>/{metrics,confusion}
.json and the run/bubble_merge/20261007 count tables + summary. Repo venv.
"""
from __future__ import annotations

import csv
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(REPO, "run", "bubble_merge", "20261007", "runs2")
DATA = os.path.join(REPO, "run", "bubble_merge", "20261007")
OUT = os.path.join(REPO, "reports", "bubble_merge",
                   "FMD_BubbleMerge_Comparison_20261007.xlsx")

FAMILY = ["Bubble", "Bubble On 123", "Bubble On Edge", "Bubble Irregular"]
ARCHS = [("ResNet50", "bubble_merge_resnet50_separate",
          "bubble_merge_resnet50_merged"),
         ("MultiLevel MultiScale", "bubble_merge_multiscale_separate",
          "bubble_merge_multiscale_merged")]

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BOLD = Font(bold=True)
GREY = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def pct(x, dp=1):
    return round(100.0 * x, dp) if x is not None else None


def load(run_id):
    d = os.path.join(RUNS, run_id)
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    with open(os.path.join(d, "confusion.json"), encoding="utf-8") as fh:
        c = json.load(fh)
    return m, c


def prf(mat, i):
    tp = mat[i][i]
    col = sum(mat[r][i] for r in range(len(mat)))
    row = sum(mat[i])
    p = tp / col if col else 0.0
    r = tp / row if row else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f, row


def family(conf, names):
    cls, mat = conf["class_names"], conf["matrix"]
    idx = [i for i, c in enumerate(cls) if c in names]
    tp = sum(mat[i][i] for i in idx)
    support = sum(sum(mat[i]) for i in idx)
    cross = sum(mat[r][c] for r in idx for c in idx if r != c)
    pred_as = sum(mat[r][i] for r in range(len(cls)) for i in idx)
    return (tp, support, tp / support if support else 0.0,
            (tp + cross) / support if support else 0.0,
            tp / pred_as if pred_as else 0.0)


def cells(conf, cls_name, side, limit=8):
    cls, mat = conf["class_names"], conf["matrix"]
    if cls_name not in cls:
        return []
    i = cls.index(cls_name)
    if side == "row":
        out = [(mat[i][j], cls[j]) for j in range(len(cls))
               if j != i and mat[i][j] > 0]
    else:
        out = [(mat[r][i], cls[r]) for r in range(len(cls))
               if r != i and mat[r][i] > 0]
    out.sort(reverse=True)
    return out[:limit]


def make_sheet(wb, title, intro, header, rows, widths, bold_delta_col=None):
    ws = wb.create_sheet(title)
    r = 1
    for line in intro:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        ws.merge_cells(start_row=r, start_column=1, end_row=r,
                       end_column=max(len(header), 4))
        ws.row_dimensions[r].height = 15 * (1 + len(line) // 110)
        r += 1
    r += 1
    hr = r
    for j, h in enumerate(header, start=1):
        c = ws.cell(row=hr, column=j, value=h)
        c.font = BOLD
        c.fill = GREY
        c.border = BOX
        c.alignment = Alignment(wrap_text=True, vertical="center",
                                horizontal="center")
    ws.row_dimensions[hr].height = 30
    for row in rows:
        r += 1
        for j, v in enumerate(row, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            if j in (1, 2) and isinstance(v, str):
                c.alignment = WRAP
            if bold_delta_col and j == bold_delta_col and isinstance(v, (int, float)):
                c.font = BOLD
    ws.freeze_panes = ws.cell(row=hr + 1, column=1)
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    return ws


def main():
    runs = {}
    for _, sid, mid in ARCHS:
        runs[sid] = load(sid)
        runs[mid] = load(mid)

    wb = Workbook()
    wb.remove(wb.active)

    # ---- Read me --------------------------------------------------------
    make_sheet(
        wb, "Read me",
        ["This workbook answers one question: does the model get the bubble "
         "defects right when the four bubble classes are merged into one "
         "class, or when they stay separate?",
         "The four bubble classes are Bubble, Bubble On 123, Bubble On Edge "
         "and Bubble Irregular. In the merged reading they are one class "
         "called Bubble. Bubble Cluster and Bubble Scatter are bubble "
         "classes too, but the client did not ask to merge them, so they "
         "stay separate in both readings. The separate reading has 23 "
         "classes, the merged reading has 20.",
         "Both readings were trained on the same pictures: 10,614 pictures "
         "in total (8,409 with a defect tag, 2,205 with no defect, called "
         "Clear). Each class was split 70 percent for training and 30 "
         "percent for testing: 7,429 training pictures and 3,185 test "
         "pictures. Every number in this workbook comes from those 3,185 "
         "test pictures.",
         "Training setup, identical for all four runs: 50 epochs, batch "
         "size 8, SGD learning rate 0.0001, pictures squeezed to 224 by 224 "
         "pixels, fixed random seed. Two architectures were trained: "
         "ResNet50 and MultiLevel MultiScale.",
         "One tag per picture. When a picture carries two tags, the tag "
         "from the newer annotation folders wins, as the client confirmed "
         "on 7 October. The 33 pictures called Fiber in the old library and "
         "Extraneous Polymer in the new folders count as Extraneous "
         "Polymer.",
         "How to read the sheets: every sheet shows the separate reading "
         "and the merged reading side by side. A positive change favours "
         "the merged reading. Small classes swing hard: a class with 4 test "
         "pictures moves 25 points when one picture changes, so read its "
         "numbers with care."],
        ["sheet", "what it holds"],
        [["Headline", "The two readings compared: accuracy on all 3,185 "
                      "test pictures, and the results on the 54 bubble test "
                      "pictures."],
         ["What moved", "The classes that took the bubble pictures, and "
                        "the pictures the merged Bubble class took in."],
         ["Per class", "Recall for every class in all four runs, with the "
                       "change between readings."],
         ["Count table", "The client's count table: how many pictures "
                         "carry each tag, versus how many pictures each "
                         "class holds in the dataset."],
         ["Image EDA", "The pool and the split: how many pictures each "
                       "class holds, and how many went to training and "
                       "testing."]],
        [16, 96])

    # ---- Headline -------------------------------------------------------
    rows = []
    for arch, sid, mid in ARCHS:
        s, m = runs[sid][0], runs[mid][0]
        tp_s, sup, exr_s, famr_s, prec_s = family(runs[sid][1], FAMILY)
        tp_m, _sup, exr_m, famr_m, prec_m = family(runs[mid][1], ["Bubble"])
        rows += [
            [arch, "Accuracy on all 3,185 test pictures",
             pct(s["overall_accuracy"]), pct(m["overall_accuracy"]),
             pct(m["overall_accuracy"] - s["overall_accuracy"])],
            [arch, "Macro F1 score (average over classes)",
             pct(s["macro"]["f1"]), pct(m["macro"]["f1"]),
             pct(m["macro"]["f1"] - s["macro"]["f1"])],
            [arch, "Bubble pictures found (of 54)", tp_s, tp_m, tp_m - tp_s],
            [arch, "Bubble pictures found, percent", pct(exr_s), pct(exr_m),
             pct(exr_m - exr_s)],
            [arch, "Bubble pictures found as any bubble class, percent",
             pct(famr_s), pct(famr_m), pct(famr_m - famr_s)],
            [arch, "Pictures called Bubble that were right, percent",
             pct(prec_s), pct(prec_m), pct(prec_m - prec_s)],
            [],
        ]
    make_sheet(
        wb, "Headline",
        ["The two readings side by side. Change = merged reading minus "
         "separate reading, in percentage points. Positive change favours "
         "the merged reading.",
         "'Bubble pictures found' counts the 54 test pictures from the four "
         "bubble classes. In the separate reading a picture only counts as "
         "found when the model names its exact class. In the merged reading "
         "there is one class, so every correct bubble picture counts.",
         "The last row of each block is the cost side: of all the pictures "
         "the model called Bubble, the share that really were bubbles. When "
         "this drops, the merged class is pulling in pictures that are not "
         "bubbles.",
         "Macro F1 rises partly by arithmetic: merging removes two classes "
         "that scored near zero, so the average goes up without any picture "
         "changing. The bubble rows are the real effect."],
        ["architecture", "measure", "separate reading", "merged reading",
         "change (points)"],
        rows, [22, 44, 17, 16, 16], bold_delta_col=5)

    # ---- What moved -----------------------------------------------------
    rows = []
    for arch, sid, mid in ARCHS:
        mc = runs[mid][1]
        sc = runs[sid][1]
        rows.append([arch, "merged", "The merged Bubble class lost its "
                     "test pictures to these classes", "", "", ""])
        for n, c in cells(mc, "Bubble", "row"):
            rows.append(["", "merged", "lost to", c, n,
                         "%d of the 54 bubble test pictures" % n])
        rows.append(["", "merged", "The merged Bubble class took in test "
                     "pictures from these classes", "", "", ""])
        for n, c in cells(mc, "Bubble", "col"):
            rows.append(["", "merged", "took in from", c, n,
                         "not a bubble picture, but called Bubble"])
        rows.append(["", "separate", "The separate bubble classes lost "
                     "their test pictures to these classes", "", "", ""])
        for b in FAMILY:
            for n, c in cells(sc, b, "row", limit=4):
                rows.append(["", "separate", "%s lost to" % b, c, n, ""])
        rows.append([])
    make_sheet(
        wb, "What moved",
        ["Where the bubble test pictures went, and what the merged Bubble "
         "class took in. All counts are test pictures from the 3,185.",
         "'Lost to': a bubble picture the model placed in another class. "
         "'Took in from': a picture from another class the model called "
         "Bubble. The take-in list explains the drop in the merged class's "
         "share of correct Bubble calls on the Headline sheet."],
        ["architecture", "reading", "direction", "class", "test pictures",
         "note"],
        rows, [20, 11, 44, 34, 13, 34])

    # ---- Per class ------------------------------------------------------
    percls = {}
    for _, sid, mid in ARCHS:
        for rid in (sid, mid):
            conf = runs[rid][1]
            for i, c in enumerate(conf["class_names"]):
                percls[(rid, c)] = prf(conf["matrix"], i)
    r50s, r50m = ARCHS[0][1], ARCHS[0][2]
    mss, msm = ARCHS[1][1], ARCHS[1][2]
    allc = sorted({c for (_r, c) in percls})
    rows = []
    for c in allc:
        def g(rid):
            v = percls.get((rid, c))
            return (v[1], v[3]) if v else (None, None)
        r50s_r, sup = g(r50s)
        r50m_r, _ = g(r50m)
        mss_r, _ = g(mss)
        msm_r, _ = g(msm)
        d50 = pct(r50m_r - r50s_r) if (r50m_r is not None
                                       and r50s_r is not None) else None
        dms = pct(msm_r - mss_r) if (msm_r is not None
                                     and mss_r is not None) else None
        note = ""
        if c == "Bubble":
            # the honest comparison for the merged Bubble row: the merged
            # class against the four separate bubble classes pooled
            s50 = family(runs[r50s][1], FAMILY)
            m50 = family(runs[r50m][1], ["Bubble"])
            sms = family(runs[mss][1], FAMILY)
            mmsf = family(runs[msm][1], ["Bubble"])
            r50s_r, r50m_r = pct(s50[2]), pct(m50[2])
            mss_r, msm_r = pct(sms[2]), pct(mmsf[2])
            d50 = pct(m50[2] - s50[2])
            dms = pct(mmsf[2] - sms[2])
            sup = s50[1]
            note = ("separate column = the four bubble classes pooled; "
                    "merged = the one Bubble class, same 54 test pictures")
        elif c in FAMILY[1:]:
            note = "folded into Bubble in the merged reading"
        rows.append([c, sup if sup is not None else "",
                     r50s_r if c == "Bubble" else pct(r50s_r),
                     r50m_r if c == "Bubble" else pct(r50m_r), d50,
                     mss_r if c == "Bubble" else pct(mss_r),
                     msm_r if c == "Bubble" else pct(msm_r), dms, note])
    make_sheet(
        wb, "Per class",
        ["Recall for every class: of that class's test pictures, the share "
         "the model named correctly. Four columns: each architecture in "
         "each reading. Change = merged minus separate, in points.",
         "Test pictures = the class's share of the 3,185 test pictures. "
         "Classes with fewer than 10 test pictures move many points per "
         "picture: Bubble On Edge has 4 test pictures, so one picture "
         "moves it 25 points.",
         "Clear is the class of pictures with no defect tag. Bubble "
         "Cluster and Bubble Scatter stay separate in both readings."],
        ["class", "test pictures", "ResNet50 separate", "ResNet50 merged",
         "change (points)", "MultiScale separate", "MultiScale merged",
         "change (points)", "note"],
        rows, [34, 12, 15, 14, 14, 15, 14, 14, 40])

    # ---- Count table ----------------------------------------------------
    ct = []
    for name, reading in (("count_table_separate.csv", "separate"),
                          ("count_table_merged.csv", "merged")):
        with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ct.append([reading, r["class"], r["tag_family"],
                           int(r["tag_presence_pictures"]),
                           int(r["dataset_pictures"]),
                           int(r["train"]), int(r["test"])])
    make_sheet(
        wb, "Count table",
        ["The client's count table, both readings. Two counts per class, "
         "and they answer different questions.",
         "Tag column: how many pictures carry that tag anywhere, counting "
         "every tag a picture has. 55 pictures carry two tags, so the tag "
         "columns sum to more than 10,614.",
         "Dataset column: how many pictures the class holds in the dataset, "
         "where each picture sits in exactly one class. The dataset column "
         "sums to 8,409 defect pictures plus 2,205 Clear pictures, exactly "
         "10,614.",
         "LP tags and OOI tags are the client's two annotation tracks. "
         "Train and test split every class 70 to 30."],
        ["reading", "class", "tag family", "pictures with the tag",
         "pictures in the class (dataset)", "training pictures (70%)",
         "test pictures (30%)"],
        ct, [11, 36, 10, 19, 24, 19, 18])

    # ---- Image EDA ------------------------------------------------------
    eda = []
    with open(os.path.join(DATA, "count_table_separate.csv"), newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            eda.append([r["class"], r["tag_family"],
                        int(r["dataset_pictures"]), int(r["train"]),
                        int(r["test"]), int(r["tag_presence_pictures"])])
    eda.sort(key=lambda x: (x[1], -x[2]))
    make_sheet(
        wb, "Image EDA",
        ["The pool and the split, one row per class. Pictures in the class "
         "= training + test. The split keeps identical pictures (same file "
         "content) on one side, so no picture is both trained on and "
         "tested on.",
         "Totals: 10,614 pictures = 8,409 defect pictures + 2,205 Clear "
         "pictures; 7,429 training and 3,185 test.",
         "The merged reading changes only the four bubble rows: their 179 "
         "dataset pictures become one Bubble class (125 training, 54 "
         "test). Every other row is the same in both readings."],
        ["class", "tag family", "pictures in the class",
         "training (70%)", "test (30%)", "pictures with the tag"],
        eda, [34, 10, 17, 13, 12, 19])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
