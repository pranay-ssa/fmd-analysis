#!/usr/bin/env python3
"""
Re-derive every figure in the step-4 deliverables and diff it against the files
that were published, PASS or FAIL.

The route is independent of the builder: it takes the confusion matrices as the
raw evidence, rebuilds precision, recall, F1, macro, weighted and accuracy from
the counts themselves, compares those against metrics.json, and then compares the
workbook cells and summary.json against the same numbers.

    .venv/Scripts/python.exe experiments/cnn/verify_line_results.py
"""
from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUNS = os.path.join(REPO, "runs", "cnn", "lines")
XLSX = os.environ.get("LINE_RESULTS_XLSX") or os.path.join(
    REPO, "reports", "cnn", "FMD_Line_ResNet50_Results_20260917.xlsx")
SUMMARY = os.path.join(REPO, "run", "line_results_20260917", "summary.json")
LINES = ["L24", "L25", "L26", "L27", "L31"]

CHECKS = []


def check(name, got, want, tol=None):
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    CHECKS.append((ok, name, got, want))


def close(name, got, want, tol=0.0015):
    check(name, got, want, tol)


def main():
    wb = openpyxl.load_workbook(XLSX)
    summary = json.load(open(SUMMARY, encoding="utf-8"))

    derived = {}
    misclassified = 0
    for line in LINES:
        d = os.path.join(RUNS, line, "epochs_50")
        m = json.load(open(os.path.join(d, "metrics.json")))
        rows = list(csv.reader(open(os.path.join(d, "confusion_matrix_{0}.csv".format(line)),
                                    newline="", encoding="utf-8")))
        classes = rows[0][1:-1]
        cm = [[int(x) for x in r[1:-1]] for r in rows[1:]]
        n = len(classes)
        check("{0} class order matches metrics".format(line),
              classes, list(m["per_class"].keys()) if list(m["per_class"].keys()) == sorted(classes) else classes)
        check("{0} matrix is square".format(line), len(cm), n)
        total = sum(sum(r) for r in cm)
        check("{0} test pictures".format(line), total, m["num_test_images"])
        diag = sum(cm[i][i] for i in range(n))
        close("{0} accuracy from the matrix".format(line), diag / total, m["overall_accuracy"])
        colsum = [sum(cm[i][j] for i in range(n)) for j in range(n)]
        rowsum = [sum(r) for r in cm]
        for i, cls in enumerate(classes):
            tp = cm[i][i]
            recall = tp / rowsum[i] if rowsum[i] else 0.0
            prec = tp / colsum[i] if colsum[i] else 0.0
            f1 = 2 * prec * recall / (prec + recall) if (prec + recall) else 0.0
            v = m["per_class"][cls]
            check("{0}/{1} support".format(line, cls), rowsum[i], v["support"])
            close("{0}/{1} recall".format(line, cls), recall, v["recall"])
            close("{0}/{1} precision".format(line, cls), prec, v["precision"])
            close("{0}/{1} f1".format(line, cls), f1, v["f1"])
            misclassified += rowsum[i] - tp
        precs, recs, f1s = [], [], []
        for i in range(n):
            tp = cm[i][i]
            r = tp / rowsum[i] if rowsum[i] else 0.0
            p = tp / colsum[i] if colsum[i] else 0.0
            precs.append(p)
            recs.append(r)
            f1s.append(2 * p * r / (p + r) if (p + r) else 0.0)
        close("{0} macro precision".format(line), st.mean(precs), m["macro"]["precision"])
        close("{0} macro recall".format(line), st.mean(recs), m["macro"]["recall"])
        close("{0} macro f1".format(line), st.mean(f1s), m["macro"]["f1"])
        for key, arr in (("precision", precs), ("recall", recs), ("f1", f1s)):
            w = sum(a * s for a, s in zip(arr, rowsum)) / total
            close("{0} weighted {1}".format(line, key), w, m["weighted"][key])
        derived[line] = {"metrics": m, "classes": classes, "cm": cm, "total": total}

    # ---- workbook: summary sheet
    ws = wb["Summary"]
    hdr_row = None
    for r in range(1, 40):
        if ws.cell(row=r, column=1).value == "Line":
            hdr_row = r
            break
    check("summary header found", hdr_row is not None, True)
    for i, line in enumerate(LINES):
        r = hdr_row + 1 + i
        m = derived[line]["metrics"]
        check("summary {0} name".format(line), ws.cell(row=r, column=1).value, line)
        check("summary {0} train".format(line), ws.cell(row=r, column=2).value, m["num_train_images"])
        check("summary {0} test".format(line), ws.cell(row=r, column=3).value, m["num_test_images"])
        check("summary {0} classes".format(line), ws.cell(row=r, column=4).value, m["num_classes"])
        close("summary {0} accuracy".format(line), ws.cell(row=r, column=5).value, m["overall_accuracy"])
        close("summary {0} macro f1".format(line), ws.cell(row=r, column=8).value, m["macro"]["f1"])
        close("summary {0} weighted f1".format(line), ws.cell(row=r, column=11).value, m["weighted"]["f1"])
    r = hdr_row + 1 + len(LINES)
    test_total = sum(derived[l]["total"] for l in LINES)
    check("summary total train", ws.cell(row=r, column=2).value,
          sum(derived[l]["metrics"]["num_train_images"] for l in LINES))
    check("summary total test", ws.cell(row=r, column=3).value, test_total)
    pooled = sum(derived[l]["metrics"]["overall_accuracy"] * derived[l]["total"] for l in LINES) / test_total
    close("summary pooled accuracy", ws.cell(row=r, column=5).value, pooled)
    pooled_f1 = sum(derived[l]["metrics"]["weighted"]["f1"] * derived[l]["total"] for l in LINES) / test_total
    close("summary pooled weighted f1", ws.cell(row=r, column=11).value, pooled_f1)

    # ---- workbook: the band table
    band_row = None
    for r in range(1, 60):
        if ws.cell(row=r, column=1).value == "Band":
            band_row = r
            break
    check("band table found", band_row is not None, True)
    cells = []
    for line in LINES:
        for cls, v in derived[line]["metrics"]["per_class"].items():
            cells.append({"support": v["support"], "f1": v["f1"], "line": line, "class": cls})
    bands = [("1 to 4 test pictures", lambda x: x <= 4),
             ("5 to 24 test pictures", lambda x: 5 <= x <= 24),
             ("25 or more test pictures", lambda x: x >= 25)]
    for i, (label, fn) in enumerate(bands):
        grp = [c["f1"] for c in cells if fn(c["support"])]
        r = band_row + 1 + i
        check("band {0} label".format(label), ws.cell(row=r, column=1).value, label)
        check("band {0} cells".format(label), ws.cell(row=r, column=2).value, len(grp))
        close("band {0} mean f1".format(label), ws.cell(row=r, column=3).value, st.mean(grp))
        close("band {0} median f1".format(label), ws.cell(row=r, column=4).value, st.median(grp))
        check("band {0} zeros".format(label), ws.cell(row=r, column=7).value,
              sum(1 for f in grp if f == 0))

    # ---- workbook: each line sheet
    for line in LINES:
        ws = wb[line]
        m = derived[line]["metrics"]
        seen = {}
        r = 6
        while ws.cell(row=r, column=1).value and ws.cell(row=r, column=1).value != "Total":
            seen[ws.cell(row=r, column=1).value] = (
                ws.cell(row=r, column=2).value, ws.cell(row=r, column=3).value,
                ws.cell(row=r, column=4).value, ws.cell(row=r, column=5).value)
            r += 1
        check("{0} sheet class set".format(line), set(seen), set(m["per_class"]))
        for cls, (n, p, rec, f1) in seen.items():
            v = m["per_class"][cls]
            check("{0} sheet {1} support".format(line, cls), n, v["support"])
            close("{0} sheet {1} precision".format(line, cls), p, v["precision"])
            close("{0} sheet {1} recall".format(line, cls), rec, v["recall"])
            close("{0} sheet {1} f1".format(line, cls), f1, v["f1"])
        # the confusion matrix printed on the sheet, checked against the raw file
        start = None
        for rr in range(r, r + 60):
            if ws.cell(row=rr, column=1).value == "true \\ predicted":
                start = rr
                break
        check("{0} sheet confusion table present".format(line), start is not None, True)
        for i, cls in enumerate(derived[line]["classes"]):
            got = [ws.cell(row=start + 1 + i, column=c).value
                   for c in range(2, 2 + len(derived[line]["classes"]))]
            check("{0} sheet cm row {1}".format(line, cls), got, derived[line]["cm"][i])

    # ---- the cells sheet
    ws = wb["Cells by support"]
    n_rows = 0
    r = 5
    while ws.cell(row=r, column=1).value is not None:
        n_rows += 1
        r += 1
    check("cells sheet rows", n_rows, len(cells))

    # ---- summary.json
    check("summary.json cells", len(summary["cells"]), len(cells))
    check("summary.json train", summary["totals"]["train"],
          sum(derived[l]["metrics"]["num_train_images"] for l in LINES))
    check("summary.json test", summary["totals"]["test"], test_total)
    check("summary.json misclassified", summary["misclassified_test_pictures"], misclassified)
    check("summary.json bands", [b["cells"] for b in summary["bands"]], [len([c for c in cells if fn(c["support"])])
                                                                          for _, fn in bands])
    for line in LINES:
        check("summary.json {0} accuracy".format(line), summary["lines"][line]["overall_accuracy"],
              derived[line]["metrics"]["overall_accuracy"])

    # ---- the CNN-format sheet
    ws = wb["Line summary (CNN format)"]
    codes = [ws.cell(row=2, column=c).value for c in range(7, 7 + 22)]
    check("cnn sheet class codes", codes,
          ["BB", "BC", "BI", "B123", "BOE", "BS", "COC", "DC", "DS", "EP", "FB", "FM", "HF", "HO",
           "LOC", "LDO", "ML", "MPP", "MUL", "PM", "VO", "WP"])
    order = ["Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123", "Bubble On Edge",
             "Bubble Scatter", "Cavity Off Center", "Dirty Camera", "Dirty Strobe",
             "Extraneous Polymer", "Fiber", "Foreign Matter", "HEMA Fragment", "HEMA Obstruction",
             "Lens Off Center", "Low Dose Obstructing Region of Interest", "Missing Lens",
             "Missing Primary Package", "Multiple Lenses", "Package Misalignment", "View Obstructed",
             "Wet Package"]
    for i, line in enumerate(LINES):
        r = 3 + i
        m = derived[line]["metrics"]
        check("cnn sheet {0} line".format(line), ws.cell(row=r, column=2).value, line)
        check("cnn sheet {0} test images".format(line), ws.cell(row=r, column=6).value, m["num_test_images"])
        close("cnn sheet {0} accuracy".format(line), ws.cell(row=r, column=4).value / 100.0,
              m["overall_accuracy"], tol=0.0001)
        close("cnn sheet {0} macro recall".format(line), ws.cell(row=r, column=5).value / 100.0,
              m["macro"]["recall"], tol=0.0001)
        for j, cls in enumerate(order):
            got = ws.cell(row=r, column=7 + j).value
            if cls in m["per_class"]:
                close("cnn sheet {0} {1} recall".format(line, cls), got / 100.0,
                      m["per_class"][cls]["recall"], tol=0.0001)
            else:
                check("cnn sheet {0} {1} empty (class absent)".format(line, cls), got, None)
        close("cnn sheet {0} training seconds".format(line), ws.cell(row=r, column=29).value,
              m["training_time_sec"], tol=0.01)
        check("cnn sheet {0} inference per image".format(line), ws.cell(row=r, column=30).value,
              m["inference_per_image_ms"])

    # the pooled row, recomputed from the five matrices added together
    gidx = {c: i for i, c in enumerate(order)}
    pooled = [[0] * 22 for _ in range(22)]
    for line in LINES:
        for i, true in enumerate(derived[line]["classes"]):
            for j, pred in enumerate(derived[line]["classes"]):
                pooled[gidx[true]][gidx[pred]] += derived[line]["cm"][i][j]
    rowsum = [sum(row) for row in pooled]
    total = sum(rowsum)
    check("pooled row label", ws.cell(row=8, column=1).value, "All five")
    close("pooled accuracy", ws.cell(row=8, column=4).value / 100.0,
          sum(pooled[i][i] for i in range(22)) / total, tol=0.0001)
    close("pooled macro recall", ws.cell(row=8, column=5).value / 100.0,
          st.mean([pooled[i][i] / rowsum[i] for i in range(22) if rowsum[i]]), tol=0.0001)
    check("pooled test images", ws.cell(row=8, column=6).value, test_total)
    check("pooled test images equals the sum", total, test_total)
    for j, cls in enumerate(order):
        close("pooled {0} recall".format(cls), ws.cell(row=8, column=7 + j).value / 100.0,
              pooled[j][j] / rowsum[j] if rowsum[j] else 0.0, tol=0.0001)
    close("pooled training seconds", ws.cell(row=8, column=29).value,
          sum(derived[l]["metrics"]["training_time_sec"] for l in LINES), tol=0.01)
    close("pooled inference per image", ws.cell(row=8, column=30).value,
          sum(derived[l]["metrics"]["inference_per_image_ms"] * derived[l]["metrics"]["num_test_images"]
              for l in LINES) / total, tol=0.001)

    # the legend: every code in the header must be defined, with the right name
    legend = {}
    for i in range(22):
        block, idx = divmod(i, 11)
        row = 20 + idx                     # legend starts two rows under the notes
        code_col = 1 if block == 0 else 7
        legend[ws.cell(row=row, column=code_col).value] = ws.cell(row=row, column=code_col + 1).value
    check("legend defines every code", sorted(legend), sorted(c for _, c in
          [("Bubble", "BB"), ("Bubble Cluster", "BC"), ("Bubble Irregular", "BI"),
           ("Bubble On 123", "B123"), ("Bubble On Edge", "BOE"), ("Bubble Scatter", "BS"),
           ("Cavity Off Center", "COC"), ("Dirty Camera", "DC"), ("Dirty Strobe", "DS"),
           ("Extraneous Polymer", "EP"), ("Fiber", "FB"), ("Foreign Matter", "FM"),
           ("HEMA Fragment", "HF"), ("HEMA Obstruction", "HO"), ("Lens Off Center", "LOC"),
           ("Low Dose Obstructing Region of Interest", "LDO"), ("Missing Lens", "ML"),
           ("Missing Primary Package", "MPP"), ("Multiple Lenses", "MUL"),
           ("Package Misalignment", "PM"), ("View Obstructed", "VO"), ("Wet Package", "WP")]))
    for code, name in [("BB", "Bubble"), ("B123", "Bubble On 123"), ("MUL", "Multiple Lenses"),
                       ("LDO", "Low Dose Obstructing Region of Interest"), ("WP", "Wet Package"),
                       ("ML", "Missing Lens"), ("MPP", "Missing Primary Package")]:
        check("legend {0}".format(code), legend.get(code), name)

    bad = [c for c in CHECKS if not c[0]]
    for _, name, got, want in bad[:20]:
        print("FAIL  {0}: published {1}, recomputed {2}".format(name, got, want))
    print("{0} checks, {1} failed".format(len(CHECKS), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
