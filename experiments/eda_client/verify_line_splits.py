#!/usr/bin/env python3
"""Re-derive the revised line splits and diff them against the published CSVs and
workbooks, PASS or FAIL. Separate implementation from src/make_line_splits.py: it
rebuilds the pool from the raw record with its own labelling pass, then checks
every cell, every line total and every summary figure.

    .venv/Scripts/python.exe experiments/eda_client/verify_line_splits.py
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
RUN = os.path.join(REPO, "run", "line_eda", "20260917")
XLSX70 = os.path.join(REPO, "reports", "lines", "FMD_class_split_70_30_20260917.xlsx")
XLSX80 = os.path.join(REPO, "reports", "lines", "FMD_class_split_70_30_vs_80_20_20260917.xlsx")
CLIENT_XLSX = os.path.join(REPO, "reports", "library", "FMD_Library_EDA_Counts_20260917.xlsx")

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
F_OLD = "ICube Defects Library"
RANK = {F_OLD: 0, F_OBJ: 1, F_CAT: 2}
NAME_FIX = {"HEMA": "HEMA Fragment", "Low Dose": "Low Dose Obstructing Region of Interest",
            "Multiple Lens": "Multiple Lenses", "Primary Package Misalignment": "Package Misalignment",
            "Field Of View Obstructed": "View Obstructed"}
NOT_CLASS = {"Clear", "duplicates"}

CHECKS = []


def check(name, got, want):
    CHECKS.append((got == want, name, got, want))


def pool_from_record():
    """{md5: (class, line)} built by a second, independent pass."""
    best = {}
    line_of = {}
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        for folder, cls, name, md5, _ in csv.reader(fh):
            if not folder:
                continue
            line_of.setdefault(md5, next((p for p in name.split("_") if p[:1] == "L" and p[1:].isdigit()), "NO-LINE"))
            if cls in NOT_CLASS:
                continue
            cls = NAME_FIX.get(cls, cls)
            if md5 not in best or RANK[folder] < best[md5][0]:
                best[md5] = (RANK[folder], cls)
    return {m: (c, line_of[m]) for m, (_, c) in best.items()}


def main():
    pool = pool_from_record()
    check("pool size", len(pool), 8409)
    check("pictures carrying no line", sum(1 for c, l in pool.values() if l == "NO-LINE"), 0)
    # cross-check against the client workbook's independently built dataset figure
    wb_client = openpyxl.load_workbook(CLIENT_XLSX)
    check("pool equals the client workbook dataset figure",
          len(pool), wb_client["A Library totals"]["B17"].value)

    cells = defaultdict(lambda: defaultdict(int))
    for cls, line in pool.values():
        cells[line][cls] += 1
    check("classes", len({c for c, _ in pool.values()}), 22)

    def half_up(n, r):
        return int(n * r + 0.5)

    # ---- CSV 70:30
    path = os.path.join(RUN, "all_lines_class_split_70_30.csv")
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    per = [r for r in rows if r["class"] != "TOTAL"]
    tot = {r["line"]: r for r in rows if r["class"] == "TOTAL"}
    check("70:30 csv per-class rows", len(per), sum(len(v) for v in cells.values()))
    check("70:30 csv total rows", len(tot), len(cells))
    for r in per:
        n = cells[r["line"]][r["class"]]
        check("70:30 {0}/{1} pictures".format(r["line"], r["class"]), int(r["pictures"]), n)
        check("70:30 {0}/{1} test".format(r["line"], r["class"]), int(r["test_30"]), half_up(n, 0.30))
        check("70:30 {0}/{1} train+test".format(r["line"], r["class"]),
              int(r["train_70"]) + int(r["test_30"]), int(r["pictures"]))
    for ln, r in tot.items():
        check("70:30 total {0} pictures".format(ln), int(r["pictures"]), sum(cells[ln].values()))
        check("70:30 total {0} test".format(ln), int(r["test_30"]),
              sum(half_up(n, 0.30) for n in cells[ln].values()))

    # ---- CSV 70:30 and 80:20
    path2 = os.path.join(RUN, "all_lines_class_split_70_30_and_80_20.csv")
    rows2 = list(csv.DictReader(open(path2, newline="", encoding="utf-8-sig")))
    per2 = [r for r in rows2 if r["class"] != "TOTAL"]
    for r in per2:
        n = cells[r["line"]][r["class"]]
        check("80:20 {0}/{1} test".format(r["line"], r["class"]), int(r["test_20"]), half_up(n, 0.20))
        check("80:20 {0}/{1} train+test".format(r["line"], r["class"]),
              int(r["train_80"]) + int(r["test_20"]), int(r["pictures"]))
        check("80:20 {0}/{1} scorable".format(r["line"], r["class"]),
              r["scorable_70"], "yes" if half_up(n, 0.30) >= 1 else "no")
    # the 70:30 columns must agree between the two CSVs
    a = {(r["line"], r["class"]): r for r in per}
    for r in per2:
        k = (r["line"], r["class"])
        check("csv pair agrees {0}".format(k), (r["pictures"], r["train_70"], r["test_30"]),
              (a[k]["pictures"], a[k]["train_70"], a[k]["test_30"]))

    # ---- workbooks
    wb = openpyxl.load_workbook(XLSX70)
    check("70:30 workbook sheets", wb.sheetnames, ["All lines", "L24", "L25", "L26", "L27", "L31"])
    ws = wb["All lines"]
    summary = {}
    for i in range(5, 11):
        line = ws.cell(row=i, column=1).value
        summary[line] = [ws.cell(row=i, column=c).value for c in range(2, 8)]
    grand = summary.pop("All lines")
    for ln, vals in summary.items():
        present = len(cells[ln])
        scorable = sum(1 for n in cells[ln].values() if half_up(n, 0.30) >= 1)
        thin = sum(1 for n in cells[ln].values() if 1 <= half_up(n, 0.30) <= 4)
        pics = sum(cells[ln].values())
        test = sum(half_up(n, 0.30) for n in cells[ln].values())
        check("workbook {0}".format(ln), vals,
              [present, scorable, pics, pics - test, test, thin])
    check("workbook grand row", grand,
          [sum(len(v) for v in cells.values()),
           sum(1 for v in cells.values() for n in v.values() if half_up(n, 0.30) >= 1),
           len(pool),
           len(pool) - sum(half_up(n, 0.30) for v in cells.values() for n in v.values()),
           sum(half_up(n, 0.30) for v in cells.values() for n in v.values()),
           sum(1 for v in cells.values() for n in v.values() if 1 <= half_up(n, 0.30) <= 4)])
    # per-line sheets carry the same cells as the CSV
    for ln in cells:
        s = wb[ln]
        r = 5
        seen = {}
        while s.cell(row=r, column=1).value not in (None, "Total"):
            seen[s.cell(row=r, column=1).value] = [s.cell(row=r, column=c).value for c in (2, 3, 4)]
            r += 1
        check("workbook sheet {0} class set".format(ln), set(seen), set(cells[ln]))
        for cls, vals in seen.items():
            n = cells[ln][cls]
            check("workbook sheet {0}/{1}".format(ln, cls), vals, [n, n - half_up(n, 0.30), half_up(n, 0.30)])

    wb2 = openpyxl.load_workbook(XLSX80)
    ws2 = wb2["All lines"]
    for i in range(5, 11):
        line = ws2.cell(row=i, column=1).value
        if line == "All lines":
            continue
        t80 = sum(half_up(n, 0.20) for n in cells[line].values())
        check("vs80 workbook {0} test (20%)".format(line), ws2.cell(row=i, column=8).value, t80)
        check("vs80 workbook {0} train (80%)".format(line), ws2.cell(row=i, column=7).value,
              sum(cells[line].values()) - t80)

    bad = [c for c in CHECKS if not c[0]]
    for _, name, got, want in bad[:25]:
        print("FAIL  {0}: published {1}, data says {2}".format(name, got, want))
    print("{0} checks, {1} failed".format(len(CHECKS), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
