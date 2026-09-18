#!/usr/bin/env python3
"""Re-derive every published figure in the client workbook and diff it against
the workbook cells, PASS or FAIL. Independent of the builder: it re-reads the
source record and re-computes each number by a separate route.

    .venv/Scripts/python.exe experiments/eda_client/verify_client_eda.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
XLSX = os.path.join(REPO, "reports", "library", "FMD_Library_EDA_Counts_20260917.xlsx")

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
F_OLD = "ICube Defects Library"
UPDATED = (F_OBJ, F_CAT)
NON = {"Clear", "duplicates"}
ALIAS = {
    "HEMA": "HEMA Fragment",
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "Multiple Lens": "Multiple Lenses",
    "Primary Package Misalignment": "Package Misalignment",
    "Field Of View Obstructed": "View Obstructed",
}
LP = ["Bubble Scatter", "Cavity Off Center", "Dirty Camera", "Dirty Strobe", "HEMA Obstruction",
      "Lens Off Center", "Low Dose Obstructing Region of Interest", "Missing Lens",
      "Missing Primary Package", "Multiple Lenses", "Package Misalignment", "View Obstructed"]
OOI = ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA Fragment", "Bubble", "Wet Package",
       "Bubble Irregular", "Bubble Cluster", "Bubble On 123", "Bubble On Edge", "Stretched Bubble"]

results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name, got, want))
    return ok


def main():
    rows = [r for r in csv.reader(open(SRC, newline="", encoding="utf-8-sig")) if r and r[0]]
    rows = [r for r in rows if not (r[0] == F_CAT and r[1] == "duplicates")]   # removed at source
    files = defaultdict(int)
    by_class = defaultdict(int)
    pics = defaultdict(set)
    pics_of = defaultdict(set)
    line_of = {}
    line_re = re.compile(r"_L(\d+)_")
    no_line = 0
    for folder, cls, name, md5, _ in rows:
        files[folder] += 1
        by_class[(folder, cls)] += 1
        pics[folder].add(md5)
        pics_of[md5].add(folder)
        m = line_re.search(name)
        if m:
            line_of.setdefault(md5, "L" + m.group(1))
        else:
            no_line += 1
            line_of.setdefault(md5, "NO-LINE")
    md5_updated = pics[F_OBJ] | pics[F_CAT]
    md5_all = set(pics_of)
    tags = defaultdict(set)
    for folder, cls, name, md5, _ in rows:
        if cls not in NON:
            tags[md5].add(ALIAS.get(cls, cls))
    old_only = {m for m in pics[F_OLD] if m not in md5_updated}
    dataset = {m for m in md5_all if (m in md5_updated or m in old_only) and tags.get(m)}
    clear = {r[3] for r in rows if r[0] == F_OBJ and r[1] == "Clear"}

    wb = openpyxl.load_workbook(XLSX)
    cell = lambda sheet, ref: wb[sheet][ref].value
    col = lambda sheet, c, r0, r1: [wb[sheet].cell(row=r, column=c).value for r in range(r0, r1 + 1)]

    # ---- sheet A
    check("A: Objects image files", files[F_OBJ], cell("A Library totals", "B4"))
    check("A: Objects distinct pictures", len(pics[F_OBJ]), cell("A Library totals", "C4"))
    check("A: Categorical image files", files[F_CAT], cell("A Library totals", "B5"))
    check("A: Categorical distinct pictures", len(pics[F_CAT]), cell("A Library totals", "C5"))
    check("A: older library image files", files[F_OLD], cell("A Library totals", "B6"))
    check("A: older library distinct pictures", len(pics[F_OLD]), cell("A Library totals", "C6"))
    check("A: three folders, files", sum(files.values()), cell("A Library totals", "B7"))
    check("A: three folders, distinct pictures", len(md5_all), cell("A Library totals", "C7"))
    check("A: production lines", len({line_of[m] for m in md5_all}), cell("A Library totals", "A10"))
    check("A: files with no line marker", no_line, 0)
    check("A: updated folders distinct", len(md5_updated), cell("A Library totals", "B13"))
    check("A: older library adds", len(old_only), cell("A Library totals", "B14"))
    check("A: subtotal", len(md5_updated) + len(old_only), cell("A Library totals", "B15"))
    check("A: Clear with no defect label removed", -(len(clear) - len(clear & dataset)), cell("A Library totals", "B16"))
    check("A: dataset distinct pictures", len(dataset), cell("A Library totals", "B17"))

    # ---- sheet B
    lines = sorted({line_of[m] for m in md5_all})
    for i, ln in enumerate(lines):
        r = 5 + i
        want = len([m for m in dataset if line_of[m] == ln])
        check("B: dataset {0}".format(ln), want, cell("B Production lines", "F{0}".format(r)))
        check("B: objects {0}".format(ln), len([m for m in pics[F_OBJ] if line_of[m] == ln]),
              cell("B Production lines", "B{0}".format(r)))
        check("B: categorical {0}".format(ln), len([m for m in pics[F_CAT] if line_of[m] == ln]),
              cell("B Production lines", "C{0}".format(r)))
        check("B: older kept {0}".format(ln), len([m for m in old_only if line_of[m] == ln]),
              cell("B Production lines", "D{0}".format(r)))
        check("B: clear set aside {0}".format(ln), len([m for m in clear if line_of[m] == ln]),
              cell("B Production lines", "E{0}".format(r)))
    check("B: dataset total", len(dataset), cell("B Production lines", "F10"))
    check("B: clear total", len(clear), cell("B Production lines", "E10"))

    # ---- sheet C
    for i, tag in enumerate(LP):
        r = 5 + i
        inupd = len([m for m in md5_updated if tag in tags.get(m, ())])
        total = len([m for m in dataset if tag in tags.get(m, ())])
        clr = len([m for m in dataset if tag in tags.get(m, ()) and m in clear])
        check("C: {0} in folder".format(tag), inupd, cell("C Lens Presentation tags", "B{0}".format(r)))
        check("C: {0} total".format(tag), total, cell("C Lens Presentation tags", "D{0}".format(r)))
        check("C: {0} via Clear".format(tag), clr, cell("C Lens Presentation tags", "E{0}".format(r)))
    check("C: union", len([m for m in dataset if tags.get(m, set()) & set(LP)]),
          cell("C Lens Presentation tags", "D17"))

    # ---- sheet D
    for i, tag in enumerate(OOI):
        r = 5 + i
        total = len([m for m in dataset if tag in tags.get(m, ())])
        check("D: {0} total".format(tag), total, cell("D OOI tags", "D{0}".format(r)))
        check("D: {0} in an updated folder".format(tag),
              len([m for m in md5_updated if tag in tags.get(m, ())]),
              cell("D OOI tags", "B{0}".format(r)))
    check("D: union", len([m for m in dataset if tags.get(m, set()) & set(OOI)]),
          cell("D OOI tags", "D16"))

    # ---- sheet E
    raw = defaultdict(set)
    for folder, cls, name, md5, _ in rows:
        if cls not in NON:
            raw[md5].add(cls)
    allb = defaultdict(set)
    rows_all = [r for r in csv.reader(open(SRC, newline="", encoding="utf-8-sig")) if r and r[0]]
    for folder, cls, name, md5, _ in rows_all:
        allb[md5].add(cls)
    strict = len([m for m in dataset if len(tags.get(m, ())) > 1])
    variants = len([m for m in raw.values() if len(m) > 1])
    everything = len([m for m in allb.values() if len(m) > 1])
    check("E: strict multi-tag", strict, cell("E Multi-tag images", "B6"))
    check("E: variants separate", variants, cell("E Multi-tag images", "B7"))
    check("E: every label", everything, cell("E Multi-tag images", "B8"))
    check("E: one tag only", len(dataset) - strict, cell("E Multi-tag images", "B5"))
    pairs = defaultdict(int)
    for m in dataset:
        ts = sorted(tags.get(m, ()))
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pairs[(ts[i], ts[j])] += 1
    check("E: pair entries sum to the strict count", sum(pairs.values()), strict)

    # ---- reconciliation sheet
    wsc = wb["Chart reconciliation"]
    for r in range(5, 21):
        folder = wsc.cell(row=r, column=1).value
        cls = wsc.cell(row=r, column=2).value
        chart_n = wsc.cell(row=r, column=3).value
        ours = wsc.cell(row=r, column=4).value
        real = by_class[(F_CAT if folder.startswith("Updated Categorical") else F_OBJ, cls)]
        check("reconcile: {0}/{1}".format(folder, cls), real, ours)
        check("reconcile chart column: {0}/{1}".format(folder, cls),
              wsc.cell(row=r, column=5).value, ours - chart_n)

    bad = [r for r in results if not r[0]]
    for ok, name, got, want in results:
        if not ok:
            print("FAIL  {0}: workbook says {1}, data says {2}".format(name, want, got))
    print("{0} checks, {1} failed".format(len(results), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
