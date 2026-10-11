#!/usr/bin/env python3
"""Emit the JSON spec for the Task 1 workbook (styled, xlsx_create schema).

Writes bubble_merge_wb_spec.json next to this script. Build with:
    python xlsx_create.py bubble_merge_wb_spec.json out.xlsx
All numbers come from run/bubble_merge/20261007/runs2 and the count tables.
"""
from __future__ import annotations

import csv
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(REPO, "run", "bubble_merge", "20261007", "runs2")
DATA = os.path.join(REPO, "run", "bubble_merge", "20261007")
SPEC = os.path.join(REPO, "experiments", "bubble_merge",
                    "bubble_merge_wb_spec.json")

FAMILY = ["Bubble", "Bubble On 123", "Bubble On Edge", "Bubble Irregular"]
ARCHS = [("ResNet50", "bubble_merge_resnet50_separate",
          "bubble_merge_resnet50_merged"),
         ("MultiLevel MultiScale", "bubble_merge_multiscale_separate",
          "bubble_merge_multiscale_merged")]

# palette
TITLE = "1F4E79"        # dark blue
HEAD = "2E75B6"         # header blue
SUBTLE = "F2F7FC"       # banded row tint
WHITE = "FFFFFF"
NOTE = "7F7F7F"
GOOD = "C6EFCE"         # green fill
BAD = "FFC7CE"          # red fill


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


def title_cell(text, span):
    return [{"range": "A1:%s" % span, "type": "merge"}]


def sheet_readme():
    lines = [
        ("Task 1: the four bubble classes merged into one, versus kept "
         "separate", 16, True, TITLE, WHITE),
        ("Does the model get the bubble defects right when Bubble, Bubble "
         "On 123, Bubble On Edge and Bubble Irregular are one class, or "
         "when they stay four classes? This workbook answers that with "
         "four trained models.", 12, False, None, None),
        ("", 12, False, None, None),
        ("The data", 14, True, TITLE, WHITE),
        ("10,614 pictures: 8,409 with a defect tag and 2,205 with no defect "
         "(the Clear class). One tag per picture. When a picture carries "
         "two tags, the newer annotation folders win, as the client "
         "confirmed on 7 October. The 33 pictures called Fiber in the old "
         "library and Extraneous Polymer in the new folders count as "
         "Extraneous Polymer.", 12, False, None, None),
        ("Each class was split 70 percent training, 30 percent testing: "
         "7,429 training pictures and 3,185 test pictures. Both readings "
         "saw exactly these pictures, so every difference between them "
         "comes from the merge alone.", 12, False, None, None),
        ("", 12, False, None, None),
        ("The training setup (identical for all four runs)", 14, True, TITLE, WHITE),
        ("50 epochs, batch size 8, SGD learning rate 0.0001, pictures "
         "resized to 224 by 224 pixels, fixed random seed. Two "
         "architectures: ResNet50 and MultiLevel MultiScale. The separate "
         "reading has 23 classes, the merged reading has 20 (Bubble "
         "Cluster and Bubble Scatter stay separate in both, the client did "
         "not ask to merge them).", 12, False, None, None),
        ("", 12, False, None, None),
        ("How to read this workbook", 14, True, TITLE, WHITE),
        ("Every sheet shows the separate reading and the merged reading "
         "side by side. Change = merged minus separate, in points. "
         "Positive change favours the merged reading. Small classes swing "
         "hard: a class with 4 test pictures moves 25 points when one "
         "picture flips.", 12, False, None, None),
    ]
    rows = []
    for text, size, bold, fill, color in lines:
        cell = {"value": text, "font_size": size}
        if bold:
            cell["bold"] = True
            cell["fill"] = fill
            cell["font_color"] = color
        rows.append([cell])
    guide = [
        ["Headline", "The two readings compared: accuracy on all 3,185 "
         "test pictures and the results on the 54 bubble test pictures."],
        ["What moved", "The classes that took the bubble pictures, and the "
         "pictures the merged Bubble class took in."],
        ["Per class", "Recall for every class in all four runs, with the "
         "change between readings."],
        ["Count table", "The client's count table: pictures with each tag "
         "versus pictures in each class."],
        ["Image EDA", "The pool and the split: pictures per class, "
         "training and test."],
    ]
    hr = len(rows) + 2
    rows.append([{"value": "sheet", "bold": True, "fill": HEAD,
                  "font_color": WHITE},
                 {"value": "what it holds", "bold": True, "fill": HEAD,
                  "font_color": WHITE}])
    for i, g in enumerate(guide):
        tint = SUBTLE if i % 2 else None
        r = [{"value": g[0], "bold": True}]
        c = {"value": g[1]}
        if tint:
            for cc in (r[0], c):
                cc["fill"] = tint
        rows.append([r[0], c])
    return {
        "name": "Read me",
        "rows": rows,
        "merges": [],
        "column_widths": {"A": 16, "B": 100},
        "row_heights": {str(i + 1): 18 for i in range(len(lines))},
        "cells": {},
    }


def sheet_headline(runs):
    intro = [
        "The two readings side by side. Change = merged minus separate, "
        "in points. Positive favours the merged reading.",
        "'Bubble pictures found' counts the 54 test pictures from the four "
        "bubble classes. In the separate reading a picture counts only "
        "when the model names its exact class; in the merged reading every "
        "correct bubble picture counts.",
        "The last row of each block is the cost side: of all pictures the "
        "model called Bubble, the share that really were bubbles. A drop "
        "means the merged class pulls in pictures that are not bubbles.",
        "Macro F1 rises partly by arithmetic: merging removes two classes "
        "that scored near zero, so the average climbs without any picture "
        "changing. The bubble rows are the real effect.",
    ]
    rows = []
    for line in intro:
        rows.append([{"value": line, "font_color": NOTE}])
    rows.append([])
    hr = len(rows) + 1
    head = ["architecture", "measure", "separate reading", "merged reading",
            "change (points)"]
    rows.append([{"value": h, "bold": True, "fill": HEAD, "font_color": WHITE}
                 for h in head])
    r0 = hr + 1
    for arch, sid, mid in ARCHS:
        s, m = runs[sid][0], runs[mid][0]
        tp_s, sup, exr_s, famr_s, prec_s = family(runs[sid][1], FAMILY)
        tp_m, _s, exr_m, famr_m, prec_m = family(runs[mid][1], ["Bubble"])
        block = [
            [arch, "Accuracy on all 3,185 test pictures",
             round(100 * s["overall_accuracy"], 1),
             round(100 * m["overall_accuracy"], 1),
             round(100 * (m["overall_accuracy"] - s["overall_accuracy"]), 1)],
            [arch, "Macro F1 score (average over classes)",
             round(100 * s["macro"]["f1"], 1),
             round(100 * m["macro"]["f1"], 1),
             round(100 * (m["macro"]["f1"] - s["macro"]["f1"]), 1)],
            [arch, "Bubble pictures found (of 54)", tp_s, tp_m, tp_m - tp_s],
            [arch, "Bubble pictures found, percent",
             round(100 * exr_s, 1), round(100 * exr_m, 1),
             round(100 * (exr_m - exr_s), 1)],
            [arch, "Bubble pictures found as any bubble class, percent",
             round(100 * famr_s, 1), round(100 * famr_m, 1),
             round(100 * (famr_m - famr_s), 1)],
            [arch, "Pictures called Bubble that were right, percent",
             round(100 * prec_s, 1), round(100 * prec_m, 1),
             round(100 * (prec_m - prec_s), 1)],
        ]
        for row in block:
            rows.append(row)
        rows.append([])
    last = hr + 2 * len(block) + 2 + 2      # data rows + blanks
    dr = "E%d:E%d" % (r0, last)
    return {
        "name": "Headline",
        "rows": rows,
        "column_widths": {"A": 22, "B": 46, "C": 17, "D": 16, "E": 16},
        "freeze_panes": "A%d" % (hr + 1),
        "conditional_formats": [
            {"range": dr, "type": "color_scale",
             "start_color": "FFF8696B", "end_color": "FF63BE7B"},
        ],
        "charts": [
            {"type": "bar", "title": "Bubble pictures found, percent",
             "anchor": "G%d" % r0,
             "data": "C%d:D%d" % (hr + 4, hr + 4),
             "titles_from_data": True,
             "categories": "B%d" % (hr + 4)},
        ],
        "cells": {},
    }, r0


def sheet_moved(runs):
    intro = [
        "Where the bubble test pictures went, and what the merged Bubble "
        "class took in. All counts are test pictures from the 3,185.",
        "'Lost to': a bubble picture the model placed in another class. "
        "'Took in from': a picture from another class the model called "
        "Bubble. The take-in list explains the drop in the share of "
        "correct Bubble calls on the Headline sheet.",
    ]
    rows = [[{"value": t, "font_color": NOTE} for t in intro]
            if False else [{"value": t, "font_color": NOTE}] for t in intro]
    rows.append([])
    hr = len(rows) + 1
    head = ["architecture", "reading", "direction", "class",
            "test pictures", "note"]
    rows.append([{"value": h, "bold": True, "fill": HEAD, "font_color": WHITE}
                 for h in head])
    for arch, sid, mid in ARCHS:
        mc, sc = runs[mid][1], runs[sid][1]
        rows.append([{"value": arch, "bold": True},
                     {"value": "merged"},
                     {"value": "The merged Bubble class lost its test "
                               "pictures to these classes", "bold": True},
                     "", "", ""])
        for n, c in cells(mc, "Bubble", "row"):
            rows.append(["", "merged", "lost to", c, n,
                         "%d of the 54 bubble test pictures" % n])
        rows.append(["", "merged",
                     {"value": "The merged Bubble class took in test "
                               "pictures from these classes", "bold": True},
                     "", "", ""])
        for n, c in cells(mc, "Bubble", "col"):
            rows.append(["", "merged", "took in from", c, n,
                         "not a bubble picture, but called Bubble"])
        rows.append(["", "separate",
                     {"value": "The separate bubble classes lost their test "
                               "pictures to these classes", "bold": True},
                     "", "", ""])
        for b in FAMILY:
            for n, c in cells(sc, b, "row", limit=4):
                rows.append(["", "separate", "%s lost to" % b, c, n, ""])
        rows.append([])
    return {
        "name": "What moved",
        "rows": rows,
        "column_widths": {"A": 20, "B": 11, "C": 44, "D": 34, "E": 13, "F": 34},
        "freeze_panes": "A%d" % (hr + 1),
        "cells": {},
    }


def sheet_perclass(runs):
    intro = [
        "Recall for every class: of that class's test pictures, the share "
        "the model named correctly. Four columns: each architecture in "
        "each reading. Change = merged minus separate, in points.",
        "Test pictures = the class's share of the 3,185 test pictures. "
        "Classes with fewer than 10 test pictures move many points per "
        "picture: Bubble On Edge has 4 test pictures, so one picture moves "
        "it 25 points.",
        "The Bubble row is the fair comparison: the separate column pools "
        "the four bubble classes, the merged column is the one Bubble "
        "class, both on the same 54 test pictures.",
        "Clear is the class of pictures with no defect tag. Bubble Cluster "
        "and Bubble Scatter stay separate in both readings.",
    ]
    rows = [[{"value": t, "font_color": NOTE} for t in intro]]
    rows.append([])
    hr = len(rows) + 1
    head = ["class", "test pictures", "ResNet50 separate", "ResNet50 merged",
            "change (points)", "MultiScale separate", "MultiScale merged",
            "change (points)", "note"]
    rows.append([{"value": h, "bold": True, "fill": HEAD, "font_color": WHITE}
                 for h in head])
    percls = {}
    for _, sid, mid in ARCHS:
        for rid in (sid, mid):
            conf = runs[rid][1]
            for i, c in enumerate(conf["class_names"]):
                percls[(rid, c)] = prf(conf["matrix"], i)
    r50s, r50m = ARCHS[0][1], ARCHS[0][2]
    mss, msm = ARCHS[1][1], ARCHS[1][2]
    allc = sorted({c for (_r, c) in percls})
    r0 = hr + 1
    for c in allc:
        def g(rid):
            v = percls.get((rid, c))
            return v if v else None
        v50s, v50m, vms_s, vms_m = g(r50s), g(r50m), g(mss), g(msm)
        note = ""
        if c == "Bubble":
            s50 = family(runs[r50s][1], FAMILY)
            m50 = family(runs[r50m][1], ["Bubble"])
            sms = family(runs[mss][1], FAMILY)
            mmsf = family(runs[msm][1], ["Bubble"])
            row = [c, s50[1],
                   round(100 * s50[2], 1), round(100 * m50[2], 1),
                   round(100 * (m50[2] - s50[2]), 1),
                   round(100 * sms[2], 1), round(100 * mmsf[2], 1),
                   round(100 * (mmsf[2] - sms[2]), 1),
                   "separate column pools the four bubble classes"]
        else:
            note = ("folded into Bubble in the merged reading"
                    if c in FAMILY[1:] else "")
            row = [c, v50s[3] if v50s else "",
                   round(100 * v50s[1], 1) if v50s else "",
                   round(100 * v50m[1], 1) if v50m else "",
                   round(100 * (v50m[1] - v50s[1]), 1)
                   if v50s and v50m else "",
                   round(100 * vms_s[1], 1) if vms_s else "",
                   round(100 * vms_m[1], 1) if vms_m else "",
                   round(100 * (vms_m[1] - vms_s[1]), 1)
                   if vms_s and vms_m else "", note]
        rows.append(row)
    last = r0 + len(allc) - 1
    return {
        "name": "Per class",
        "rows": rows,
        "column_widths": {"A": 34, "B": 12, "C": 15, "D": 14, "E": 14, "F": 15, "G": 14, "H": 14, "I": 40},
        "freeze_panes": "A%d" % (hr + 1),
        "conditional_formats": [
            {"range": "E%d:E%d" % (r0, last), "type": "color_scale",
             "start_color": "FFF8696B", "end_color": "FF63BE7B"},
            {"range": "H%d:H%d" % (r0, last), "type": "color_scale",
             "start_color": "FFF8696B", "end_color": "FF63BE7B"},
        ],
        "cells": {},
    }


def sheet_counts():
    intro = [
        "The client's count table, both readings. Two counts per class, "
        "and they answer different questions.",
        "Tag column: how many pictures carry that tag anywhere, counting "
        "every tag a picture has. 55 pictures carry two tags, so the tag "
        "columns sum to more than 10,614.",
        "Dataset column: how many pictures the class holds in the dataset, "
        "where each picture sits in exactly one class. The dataset column "
        "sums to 8,409 defect pictures plus 2,205 Clear pictures, exactly "
        "10,614.",
        "LP tags and OOI tags are the client's two annotation tracks. "
        "Train and test split every class 70 to 30.",
    ]
    rows = [[{"value": t, "font_color": NOTE} for t in intro]]
    rows.append([])
    hr = len(rows) + 1
    head = ["reading", "class", "tag family", "pictures with the tag",
            "pictures in the class (dataset)", "training pictures (70%)",
            "test pictures (30%)"]
    rows.append([{"value": h, "bold": True, "fill": HEAD, "font_color": WHITE}
                 for h in head])
    for name, reading in (("count_table_separate.csv", "separate"),
                          ("count_table_merged.csv", "merged")):
        with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rows.append([reading, r["class"], r["tag_family"],
                             int(r["tag_presence_pictures"]),
                             int(r["dataset_pictures"]),
                             int(r["train"]), int(r["test"])])
    return {
        "name": "Count table",
        "rows": rows,
        "column_widths": {"A": 11, "B": 36, "C": 10, "D": 19, "E": 24, "F": 19, "G": 18},
        "freeze_panes": "A%d" % (hr + 1),
        "autofilter": "A%d:G%d" % (hr, hr + 46),
        "cells": {},
    }


def sheet_eda():
    intro = [
        "The pool and the split, one row per class. Pictures in the class "
        "= training + test. The split keeps identical pictures (same file "
        "content) on one side, so no picture is both trained on and tested "
        "on.",
        "Totals: 10,614 pictures = 8,409 defect pictures + 2,205 Clear "
        "pictures; 7,429 training and 3,185 test.",
        "The merged reading changes only the four bubble rows: their 179 "
        "dataset pictures become one Bubble class (125 training, 54 test). "
        "Every other row is the same in both readings.",
    ]
    rows = [[{"value": t, "font_color": NOTE} for t in intro]]
    rows.append([])
    hr = len(rows) + 1
    head = ["class", "tag family", "pictures in the class",
            "training (70%)", "test (30%)", "pictures with the tag"]
    rows.append([{"value": h, "bold": True, "fill": HEAD, "font_color": WHITE}
                 for h in head])
    eda = []
    with open(os.path.join(DATA, "count_table_separate.csv"), newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            eda.append([r["class"], r["tag_family"],
                        int(r["dataset_pictures"]), int(r["train"]),
                        int(r["test"]), int(r["tag_presence_pictures"])])
    eda.sort(key=lambda x: (x[1], -x[2]))
    for row in eda:
        rows.append(row)
    r0 = hr + 1
    return {
        "name": "Image EDA",
        "rows": rows,
        "column_widths": {"A": 34, "B": 10, "C": 17, "D": 13, "E": 12, "F": 19},
        "freeze_panes": "A%d" % (hr + 1),
        "tables": [{"name": "PoolAndSplit",
                    "range": "A%d:F%d" % (hr, r0 + len(eda) - 1),
                    "style": "TableStyleMedium9"}],
        "charts": [
            {"type": "bar", "title": "Pictures per class",
             "anchor": "H%d" % r0,
             "data": "C%d" % hr,
             "titles_from_data": True,
             "categories": "A%d:A%d" % (r0, r0 + len(eda) - 1)},
        ],
        "cells": {},
    }


def main():
    runs = {}
    for _, sid, mid in ARCHS:
        runs[sid] = load(sid)
        runs[mid] = load(mid)

    headline, r0 = sheet_headline(runs)
    spec = {
        "sheets": [
            sheet_readme(),
            headline,
            sheet_moved(runs),
            sheet_perclass(runs),
            sheet_counts(),
            sheet_eda(),
        ],
    }
    with open(SPEC, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1)
    print("wrote", SPEC)
    print("sheets:", [s["name"] for s in spec["sheets"]])


if __name__ == "__main__":
    main()
