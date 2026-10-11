#!/usr/bin/env python3
"""Rebuild 'What moved' as a numbers sheet and fix the charts, in place.

The workbook is edited in place so the user's manual changes to the other
sheets survive. openpyxl drops existing charts on load, which is fine: every
chart is re-added here with the right metrics.

What moved (new): one row per class. Correct test answers in the separate
reading, in the merged reading, pictures gained (wrong then, right now),
pictures lost (right then, wrong now), net, and where the gains came from
and the losses went to. The four merged bubble classes form one pooled row;
Bubble Cluster and Bubble Scatter are their own rows. A TOTAL row cross-
checks against the headline accuracy delta.

Charts (new):
    Headline   bubble pictures found, percent: separate vs merged, per arch
    Per class  recall change from merging, points, per class
    What moved correct answers gained or lost, per class
    Image EDA  pictures per class
Data for the first three lives on a small 'Chart data' sheet.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(REPO, "run", "bubble_merge", "20261007", "runs2")
XLSX = os.path.join(REPO, "reports", "bubble_merge",
                    "FMD_BubbleMerge_Comparison_20261007.xlsx")

FAMILY = ["Bubble", "Bubble On 123", "Bubble On Edge", "Bubble Irregular"]
ARCHS = [("ResNet50", "bubble_merge_resnet50_separate",
          "bubble_merge_resnet50_merged"),
         ("MultiLevel MultiScale", "bubble_merge_multiscale_separate",
          "bubble_merge_multiscale_merged")]

HEAD = "2E75B6"
SUBTLE = "F2F7FC"
WHITE = "FFFFFF"
NOTE = "7F7F7F"
N_TEST = 3185


def load_mc(run_id):
    d = os.path.join(RUNS, run_id)
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    with open(os.path.join(d, "confusion.json"), encoding="utf-8") as fh:
        c = json.load(fh)
    return m, c


def load_preds(run_id):
    """basename -> (true, pred)"""
    out = {}
    with open(os.path.join(RUNS, run_id, "predictions.csv"), newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            fn = os.path.basename(r["file"])
            out[fn] = (r["true"], r["pred"])
    return out


def prf(mat, i):
    tp = mat[i][i]
    row = sum(mat[i])
    r = tp / row if row else 0.0
    return r, row


def family_recall(conf, names):
    cls, mat = conf["class_names"], conf["matrix"]
    idx = [i for i, c in enumerate(cls) if c in names]
    tp = sum(mat[i][i] for i in idx)
    support = sum(sum(mat[i]) for i in idx)
    return tp, support, tp / support if support else 0.0


def top_text(counter, n=2, prefix="from"):
    if not counter:
        return ""
    parts = ["%d %s %s" % (v, prefix, k) for k, v in counter.most_common(n)]
    return "; ".join(parts)


def main():
    runs = {}          # rid -> (metrics, confusion)
    preds = {}         # rid -> {fn: (true, pred)}
    for _, sid, mid in ARCHS:
        for rid in (sid, mid):
            runs[rid] = load_mc(rid)
            preds[rid] = load_preds(rid)

    # common classes: everything except the four folded members
    sep_classes = runs[ARCHS[0][1]][1]["class_names"]
    common = sorted(c for c in sep_classes if c not in FAMILY)

    blocks = {}        # arch -> list of row dicts
    totals = {}
    for arch, sid, mid in ARCHS:
        sp, mp = preds[sid], preds[mid]
        rows = []
        # --- the pooled bubble family row -------------------------------
        fam_pics = [fn for fn, (t, _p) in sp.items() if t in FAMILY]
        right_s = sum(1 for fn in fam_pics if sp[fn][1] in FAMILY)
        right_m = sum(1 for fn in fam_pics if mp[fn][1] == "Bubble")
        src = Counter(sp[fn][1] for fn in fam_pics
                      if sp[fn][1] not in FAMILY and mp[fn][1] == "Bubble")
        snk = Counter(mp[fn][1] for fn in fam_pics
                      if sp[fn][1] in FAMILY and mp[fn][1] != "Bubble")
        rows.append({
            "class": "The four bubble classes pooled", "test": len(fam_pics),
            "right_s": right_s, "right_m": right_m,
            "gained": right_m - right_s if right_m >= right_s else 0,
            "lost": right_s - right_m if right_s > right_m else 0,
            "net": right_m - right_s,
            "src": top_text(src, 3, "was called"), "snk": top_text(snk, 3, "now called"),
        })
        # --- the 19 unchanged classes -----------------------------------
        for c in common:
            pics = [fn for fn, (t, _p) in sp.items() if t == c]
            right_s = sum(1 for fn in pics if sp[fn][1] == c)
            right_m = sum(1 for fn in pics if mp[fn][1] == c)
            src = Counter(sp[fn][1] for fn in pics
                          if sp[fn][1] != c and mp[fn][1] == c)
            snk = Counter(mp[fn][1] for fn in pics
                          if sp[fn][1] == c and mp[fn][1] != c)
            rows.append({
                "class": c, "test": len(pics), "right_s": right_s,
                "right_m": right_m, "gained": len(src) and sum(src.values()) or 0,
                "lost": sum(snk.values()), "net": right_m - right_s,
                "src": top_text(src, 2, "was"), "snk": top_text(snk, 2, "now"),
            })
        rows[1:] = sorted(rows[1:], key=lambda r: r["net"])   # losers first
        blocks[arch] = rows
        tot_net = sum(r["net"] for r in rows)
        tot_g = sum(r["gained"] for r in rows)
        tot_l = sum(r["lost"] for r in rows)
        totals[arch] = (tot_g, tot_l, tot_net,
                        100.0 * tot_net / N_TEST,
                        runs[mid][0]["overall_accuracy"]
                        - runs[sid][0]["overall_accuracy"])
        print("%s: gained %d, lost %d, net %d = %.2f points "
              "(headline delta %.2f points)"
              % (arch, tot_g, tot_l, tot_net, 100.0 * tot_net / N_TEST,
                 totals[arch][4] * 100))

    # ---- chart data blocks ----------------------------------------------
    cd_bubble = []     # arch, separate %, merged %
    for arch, sid, mid in ARCHS:
        tp_s, sup, r_s = family_recall(runs[sid][1], FAMILY)
        tp_m, _s, r_m = family_recall(runs[mid][1], ["Bubble"])
        cd_bubble.append([arch, round(100 * r_s, 1), round(100 * r_m, 1)])

    cd_change = []     # class, r50 change pts, ms change pts
    for i, (arch, sid, mid) in enumerate(ARCHS):
        pass
    change_by_class = {}
    for c in ["The four bubble classes pooled"] + common:
        vals = []
        for arch, sid, mid in ARCHS:
            if c == "The four bubble classes pooled":
                _t, _s, r_s = family_recall(runs[sid][1], FAMILY)
                _t2, _s2, r_m = family_recall(runs[mid][1], ["Bubble"])
            else:
                sc, mc = runs[sid][1], runs[mid][1]
                i_s = sc["class_names"].index(c)
                r_s, _n = prf(sc["matrix"], i_s)
                i_m = mc["class_names"].index(c)
                r_m, _n2 = prf(mc["matrix"], i_m)
            vals.append(round(100 * (r_m - r_s), 1))
        change_by_class[c] = vals
    cd_change = [[c, v[0], v[1]] for c, v in change_by_class.items()]

    cd_net = [[r["class"], 0, 0] for r in blocks["ResNet50"]]
    for j, c in enumerate(cd_net):
        c[1] = blocks["ResNet50"][j]["net"]
        c[2] = blocks["MultiLevel MultiScale"][j]["net"]
    # order net/change blocks the same: family row then common sorted by r50 net
    order = [r["class"] for r in blocks["ResNet50"]]
    cd_change.sort(key=lambda r: order.index(r[0]))
    cd_net.sort(key=lambda r: order.index(r[0]))

    # ---- edit the workbook in place -------------------------------------
    wb = load_workbook(XLSX)
    names = wb.sheetnames
    for s in ("What moved", "Chart data"):
        if s in names:
            del wb[s]
    wm = wb.create_sheet("What moved", 2)
    cd = wb.create_sheet("Chart data")

    F = lambda **kw: Font(**kw)
    fill_head = PatternFill("solid", fgColor=HEAD)
    fill_subtle = PatternFill("solid", fgColor=SUBTLE)
    grey = Font(color=NOTE)
    wrap = Alignment(wrap_text=True, vertical="top")

    # -- What moved sheet --
    intro = [
        "Did merging help? One row per class: test pictures the separate "
        "reading got right, test pictures the merged reading got right, and "
        "what moved between them.",
        "Gained = pictures the separate reading got wrong and the merged "
        "reading got right. Lost = the opposite. Net = gained minus lost.",
        "The four merged bubble classes form one pooled row, because in the "
        "merged reading they are one class. Bubble Cluster and Bubble "
        "Scatter stay their own classes in both readings and have their own "
        "rows.",
        "'Gains came from' names the class the separate reading had put "
        "those pictures in. 'Losses went to' names the class the merged "
        "reading put them in. Rows are ordered worst first.",
    ]
    r = 1
    for line in intro:
        wm.cell(row=r, column=1, value=line).font = grey
        wm.cell(row=r, column=1).alignment = wrap
        wm.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
        r += 1
    r += 1
    net_ranges = []
    for arch, sid, mid in ARCHS:
        wm.cell(row=r, column=1, value=arch).font = Font(bold=True, color=HEAD)
        r += 1
        head = ["class", "test pictures", "right: separate", "right: merged",
                "gained", "lost", "net", "gains came from", "losses went to"]
        for j, h in enumerate(head, start=1):
            c = wm.cell(row=r, column=j, value=h)
            c.font = Font(bold=True, color=WHITE)
            c.fill = fill_head
        hr = r
        r += 1
        first_data = r
        for i, row in enumerate(blocks[arch]):
            vals = [row["class"], row["test"], row["right_s"], row["right_m"],
                    row["gained"], row["lost"], row["net"], row["src"],
                    row["snk"]]
            for j, v in enumerate(vals, start=1):
                c = wm.cell(row=r, column=j, value=v)
                if i % 2:
                    c.fill = fill_subtle
                if j in (8, 9):
                    c.alignment = wrap
            r += 1
        net_ranges.append("G%d:G%d" % (first_data, r - 1))
        g, l, net, pts, hd = totals[arch]
        wm.cell(row=r, column=1, value="TOTAL").font = Font(bold=True)
        for j, v in ((5, g), (6, l), (7, net)):
            wm.cell(row=r, column=j, value=v).font = Font(bold=True)
        wm.cell(row=r, column=8, value="net %d pictures = %+.2f points of "
                "accuracy on all 3,185 test pictures" % (net, pts)
                ).font = Font(bold=True)
        r += 2
    for rng in net_ranges:
        wm.conditional_formatting.add(rng, ColorScaleRule(
            start_type="min", start_color="FFF8696B",
            end_type="max", end_color="FF63BE7B"))
    widths = {"A": 34, "B": 12, "C": 14, "D": 13, "E": 9, "F": 9, "G": 8,
              "H": 34, "I": 34}
    for col, w in widths.items():
        wm.column_dimensions[col].width = w
    wm.freeze_panes = "A9"

    # -- Chart data sheet --
    cd.cell(row=1, column=2, value="separate").font = Font(bold=True)
    cd.cell(row=1, column=3, value="merged").font = Font(bold=True)
    for i, (arch, s, m) in enumerate(cd_bubble):
        cd.cell(row=2 + i, column=1, value=arch)
        cd.cell(row=2 + i, column=2, value=s)
        cd.cell(row=2 + i, column=3, value=m)
    r0 = 5
    cd.cell(row=r0, column=1, value="class").font = Font(bold=True)
    cd.cell(row=r0, column=2, value="ResNet50 change (points)").font = Font(bold=True)
    cd.cell(row=r0, column=3, value="MultiScale change (points)").font = Font(bold=True)
    for i, row in enumerate(cd_change):
        for j, v in enumerate(row, start=1):
            cd.cell(row=r0 + 1 + i, column=j, value=v)
    r1 = r0 + len(cd_change) + 2
    cd.cell(row=r1, column=1, value="class").font = Font(bold=True)
    cd.cell(row=r1, column=2, value="ResNet50 net").font = Font(bold=True)
    cd.cell(row=r1, column=3, value="MultiScale net").font = Font(bold=True)
    for i, row in enumerate(cd_net):
        for j, v in enumerate(row, start=1):
            cd.cell(row=r1 + 1 + i, column=j, value=v)

    def bar(title, data_ref, cats_ref, anchor, ws):
        ch = BarChart()
        ch.title = title
        ch.add_data(data_ref, titles_from_data=True)
        ch.set_categories(cats_ref)
        ch.height = 9
        ch.width = 20
        ws.add_chart(ch, anchor)

    # Headline: bubble recall by reading
    bar("Bubble pictures found, percent of 54",
        Reference(cd, min_col=2, max_col=3, min_row=1, max_row=3),
        Reference(cd, min_col=1, min_row=2, max_row=3),
        "G6", wb["Headline"])
    # Per class: recall change per class
    bar("Recall change from merging, points",
        Reference(cd, min_col=2, max_col=3, min_row=r0, max_row=r0 + len(cd_change)),
        Reference(cd, min_col=1, min_row=r0 + 1, max_row=r0 + len(cd_change)),
        "K4", wb["Per class"])
    # What moved: net correct answers per class
    bar("Correct answers gained or lost per class",
        Reference(cd, min_col=2, max_col=3, min_row=r1, max_row=r1 + len(cd_net)),
        Reference(cd, min_col=1, min_row=r1 + 1, max_row=r1 + len(cd_net)),
        "K4", wm)
    # Image EDA: pictures per class (find its header row defensively)
    ieda = wb["Image EDA"]
    hdr = None
    for row in range(1, 10):
        if ieda.cell(row=row, column=1).value == "class":
            hdr = row
            break
    if hdr:
        last = hdr
        while ieda.cell(row=last + 1, column=1).value:
            last += 1
        bar("Pictures per class",
            Reference(ieda, min_col=3, min_row=hdr, max_row=last),
            Reference(ieda, min_col=1, min_row=hdr + 1, max_row=last),
            "H3", ieda)

    wb.save(XLSX)
    print("saved", XLSX)
    print("sheets:", wb.sheetnames)


if __name__ == "__main__":
    main()
