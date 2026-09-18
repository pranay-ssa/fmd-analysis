#!/usr/bin/env python3
"""
Class-wise train/test splits per production line, under the client rules agreed
2026-09-17.

WHY THIS EXISTS
    The 2026-09-16 splits were built from a 22-class pool of 8,401 pictures that
    excluded the 8 pictures the Updated Objects folder files under "HEMA" and that
    carry no other label. The client has since said HEMA reads as HEMA Fragment,
    and Clear is out of scope except for the pictures that carry a defect label.
    The pool is therefore 8,409 pictures. This script rebuilds the splits from
    the current rules and reports every cell that moves.

THE POOL (rules fixed with the team, 2026-09-17)
    R1  Clear and duplicates are not classes. A picture that carries a defect
        label elsewhere takes that label and stays.
    R2  HEMA in the Updated Objects folder reads as HEMA Fragment.
    R3  Name equivalences: Low Dose = Low Dose Obstructing Region of Interest,
        Multiple Lenses = Multiple Lens, Package Misalignment = Primary Package
        Misalignment, View Obstructed = Field Of View Obstructed.
    R4  A picture is counted once, by content hash, never by file name.
    R5  One class per picture. Where a picture carries two labels the older
        ICube Defects Library decides; failing that the Updated Categorical
        Classes folder decides; failing that the Updated Objects folder decides.
        (Unchanged from the 2026-09-16 rule, so the two pools can be compared.)
    R6  The duplicates subfolder is excluded; every file in it repeats a picture
        already in the same folder.

THE SPLIT (unchanged from 2026-09-16, so no cell moves for a method reason)
    Inside each class inside each line: test = round-half-up(pictures * ratio),
    train = pictures - test. A cell is scorable when it leaves at least one test
    picture. A thin cell is one with 1 to 4 test pictures. Nothing is discarded:
    every picture that is not a test picture trains.

OUTPUT
    run/line_eda/20260917/all_lines_class_split_70_30.csv
    run/line_eda/20260917/all_lines_class_split_70_30_and_80_20.csv
    reports/lines/ALL_LINES_class_split_70_30_20260917.md
    reports/lines/FMD_class_split_70_30_20260917.xlsx
    reports/lines/FMD_class_split_70_30_vs_80_20_20260917.xlsx

    --diff  compare against the 2026-09-16 split and list every cell that moved.
"""
from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
OLD_SPLIT = os.path.join(REPO, "run", "line_eda", "20260916", "all_lines_class_split_70_30_and_80_20.csv")
OUT_RUN = os.path.join(REPO, "run", "line_eda", "20260917")
OUT_REP = os.path.join(REPO, "reports", "lines")

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
F_OLD = "ICube Defects Library"

# R5 priority: the older library decides; where the library is silent the Updated
# Objects folder decides, then the categorical folder. The objects-over-categorical
# order is the one the 2026-09-16 pool used, kept so the two pools differ only by
# the new HEMA rule. It changes exactly one picture (L26: Extraneous Polymer
# against Multiple Lenses); flipping it is a one-line edit.
PRIORITY = {F_OLD: 0, F_OBJ: 1, F_CAT: 2}
ALIAS = {
    "HEMA": "HEMA Fragment",
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "Multiple Lens": "Multiple Lenses",
    "Primary Package Misalignment": "Package Misalignment",
    "Field Of View Obstructed": "View Obstructed",
}
NON_CLASS = {"Clear", "duplicates"}


def norm(cls: str) -> str:
    return ALIAS.get(cls, cls)


def line_of(name: str) -> str:
    for part in name.split("_"):
        if len(part) >= 3 and part[0] == "L" and part[1:].isdigit():
            return part
    return "NO-LINE"


def build_pool():
    """Return {md5: (class, line, name)} for the pooled defect-class dataset."""
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    cand = defaultdict(list)          # md5 -> [(priority, class)]
    line_of_md5, name_of = {}, {}
    for folder, cls, name, md5, _ in rows:
        line_of_md5.setdefault(md5, line_of(name))
        name_of.setdefault(md5, name)
        if cls in NON_CLASS:
            continue
        cand[md5].append((PRIORITY[folder], norm(cls)))
    pool = {}
    for md5, opts in cand.items():
        cls = sorted(opts, key=lambda o: o[0])[0][1]
        pool[md5] = (cls, line_of_md5[md5], name_of[md5])
    return pool


def half_up(n: int, ratio: float) -> int:
    return int(n * ratio + 0.5)


def split_cell(n: int) -> dict:
    t30, t20 = half_up(n, 0.30), half_up(n, 0.20)
    return {
        "pictures": n, "train_70": n - t30, "test_30": t30,
        "train_80": n - t20, "test_20": t20,
        "scorable_70": "yes" if t30 >= 1 else "no",
        "scorable_80": "yes" if t20 >= 1 else "no",
    }


def note_for(c: dict) -> str:
    bits = []
    if c["test_20"] == 0:
        bits.append("no test picture at 80:20")
    if 1 <= c["test_30"] <= 4:
        bits.append("thin test set at 70:30")
    elif c["test_30"] == 0:
        bits.append("no test picture at 70:30")
    return "; ".join(bits)


def md_note(n: int, c: dict) -> str:
    if c["test_30"] == 0:
        return "one picture only"
    if 1 <= c["test_30"] <= 4:
        return "thin test set"
    return ""


def compute():
    pool = build_pool()
    cells = defaultdict(lambda: defaultdict(int))
    for cls, line, _ in pool.values():
        cells[line][cls] += 1
    return pool, cells


def rows_for(cells):
    out = []
    for line in sorted(cells):
        for cls, n in sorted(cells[line].items(), key=lambda kv: (-kv[1], kv[0])):
            c = split_cell(n)
            out.append({"line": line, "class": cls, **c, "note": note_for(c)})
        tot = {"pictures": 0, "train_70": 0, "test_30": 0, "train_80": 0, "test_20": 0}
        for cls, n in cells[line].items():
            c = split_cell(n)
            for k in tot:
                tot[k] += c[k]
        tot["scorable_70"] = sum(1 for n in cells[line].values() if half_up(n, 0.30) >= 1)
        tot["scorable_80"] = sum(1 for n in cells[line].values() if half_up(n, 0.20) >= 1)
        out.append({"line": line, "class": "TOTAL", **tot,
                    "note": "{0} classes".format(len(cells[line]))})
    return out


def write_csvs(rows, pool, cells):
    os.makedirs(OUT_RUN, exist_ok=True)
    p1 = os.path.join(OUT_RUN, "all_lines_class_split_70_30.csv")
    with open(p1, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["line", "class", "pictures", "train_70", "test_30", "note"])
        for r in rows:
            if r["class"] == "TOTAL":
                w.writerow([r["line"], "TOTAL", r["pictures"], r["train_70"], r["test_30"], r["note"]])
            else:
                w.writerow([r["line"], r["class"], r["pictures"], r["train_70"], r["test_30"],
                            md_note(r["pictures"], r)])
    p2 = os.path.join(OUT_RUN, "all_lines_class_split_70_30_and_80_20.csv")
    with open(p2, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["line", "class", "pictures", "train_70", "test_30", "train_80", "test_20",
                    "scorable_70", "scorable_80", "note"])
        for r in rows:
            w.writerow([r["line"], r["class"], r["pictures"], r["train_70"], r["test_30"],
                        r["train_80"], r["test_20"], r["scorable_70"], r["scorable_80"], r["note"]])
    return p1, p2


def write_md(rows, pool, cells):
    lines = sorted(cells)
    total_pic = sum(len([1 for c, l, _ in pool.values() if l == ln]) for ln in lines)
    scorable70 = sum(1 for r in rows if r["class"] != "TOTAL" and r["scorable_70"] == "yes")
    test70 = sum(r["test_30"] for r in rows if r["class"] == "TOTAL")
    train70 = sum(r["train_70"] for r in rows if r["class"] == "TOTAL")

    out = []
    out.append("# Class-wise 70:30 split for all five lines, revised 2026-09-17\n")
    out.append("Pooled defect-class dataset from the three folders, one row per unique picture, under the")
    out.append("rules agreed with the client on 2026-09-17: Clear and duplicates are not classes (a picture")
    out.append("that carries a defect label elsewhere keeps that label), HEMA in the Updated Objects folder")
    out.append("reads as HEMA Fragment, and a picture carrying two labels takes the class the older ICube")
    out.append("Defects Library assigns. The pool is {0} pictures, against 8,401 in the 2026-09-16".format(total_pic))
    out.append("revision; the 8 added pictures are the ones the Updated Objects folder files under HEMA and")
    out.append("that carry no other label, which now read as HEMA Fragment.")
    out.append("")
    out.append("The split rule is unchanged from the 2026-09-16 revision: inside each class inside each line,")
    out.append("test = round-half-up(pictures x ratio) and train = pictures - test. A class with a single")
    out.append("picture produces no test picture, so it trains and is never scored.")
    out.append("")
    out.append("## Summary\n")
    out.append("| Line | Classes present | Classes scorable | Pictures | Train (70%) | Test (30%) | Thin cells |")
    out.append("|---|---|---|---|---|---|---|")
    for ln in lines:
        rr = [r for r in rows if r["line"] == ln]
        tot = [r for r in rr if r["class"] == "TOTAL"][0]
        present = len([r for r in rr if r["class"] != "TOTAL"])
        thing = len([r for r in rr if r["class"] != "TOTAL" and 1 <= r["test_30"] <= 4])
        out.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            ln, present, tot["scorable_70"], tot["pictures"], tot["train_70"], tot["test_30"], thing))
    out.append("| **All lines** | **{0}** | **{1}** | **{2}** | **{3}** | **{4}** | **{5}** |".format(
        sum(1 for r in rows if r["class"] != "TOTAL"), scorable70, total_pic, train70, test70,
        sum(1 for r in rows if r["class"] != "TOTAL" and 1 <= r["test_30"] <= 4)))
    out.append("")
    for ln in lines:
        rr = [r for r in rows if r["line"] == ln and r["class"] != "TOTAL"]
        tot = [r for r in rows if r["line"] == ln and r["class"] == "TOTAL"][0]
        out.append("## {0}\n".format(ln))
        out.append("{0} classes, {1} pictures, {2} train and {3} test. {4} classes can be scored.\n".format(
            len(rr), tot["pictures"], tot["train_70"], tot["test_30"], tot["scorable_70"]))
        out.append("| Class | Pictures | Train (70%) | Test (30%) | Note |")
        out.append("|---|---|---|---|---|")
        for r in rr:
            out.append("| {0} | {1} | {2} | {3} | {4} |".format(
                r["class"], r["pictures"], r["train_70"], r["test_30"], md_note(r["pictures"], r)))
        out.append("| **Total** | **{0}** | **{1}** | **{2}** | **{3} classes** |".format(
            tot["pictures"], tot["train_70"], tot["test_30"], len(rr)))
        out.append("")
    path = os.path.join(OUT_REP, "ALL_LINES_class_split_70_30_20260917.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return path


def write_xlsx(rows, cells, vs80: bool):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1F3864")
    title = Font(bold=True, size=13)
    thin = Side(style="thin", color="BFBFBF")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)

    wb = Workbook()
    ws = wb.active
    ws.title = "All lines"
    ws["A1"] = "Class-wise {0} split, all production lines (revised 2026-09-17)".format(
        "70:30 and 80:20" if vs80 else "70:30")
    ws["A1"].font = title
    ws["A2"] = ("Pooled defect-class dataset: the three source folders, counted once per unique picture. "
                "Every picture carries its line number. A class with a single picture produces no test "
                "picture, so it trains and is never scored.")
    if vs80:
        hdr = ["Line", "Classes present", "Classes scorable at 70:30", "Pictures", "Train (70%)",
               "Test (30%)", "Train (80%)", "Test (20%)", "Thin test sets at 70:30 (1 to 4 test pictures)"]
    else:
        hdr = ["Line", "Classes present", "Classes scorable", "Pictures", "Train (70%)", "Test (30%)",
               "Thin test sets (1 to 4 test pictures)"]
    for c, h in enumerate(hdr, start=1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.font, cell.fill, cell.border = head, fill, box
    r = 5
    tot = {"pictures": 0, "train_70": 0, "test_30": 0, "train_80": 0, "test_20": 0}
    present = scorable = thin = 0
    for ln in sorted(cells):
        rr = [x for x in rows if x["line"] == ln]
        t = [x for x in rr if x["class"] == "TOTAL"][0]
        p = len([x for x in rr if x["class"] != "TOTAL"])
        th = len([x for x in rr if x["class"] != "TOTAL" and 1 <= x["test_30"] <= 4])
        vals = [ln, p, t["scorable_70"], t["pictures"], t["train_70"], t["test_30"]]
        if vs80:
            vals += [t["train_80"], t["test_20"]]
        vals += [th]
        for c, v in enumerate(vals, start=1):
            ws.cell(row=r, column=c, value=v)
        present += p
        scorable += t["scorable_70"]
        thin += th
        for k in tot:
            tot[k] += t[k]
        r += 1
    vals = ["All lines", present, scorable, tot["pictures"], tot["train_70"], tot["test_30"]]
    if vs80:
        vals += [tot["train_80"], tot["test_20"]]
    vals += [thin]
    for c, v in enumerate(vals, start=1):
        ws.cell(row=r, column=c, value=v).font = Font(bold=True)
    ws.column_dimensions["A"].width = 12
    for col in "BCDEFGHI":
        ws.column_dimensions[col].width = 16
    ws.freeze_panes = "A5"

    for ln in sorted(cells):
        rr = [x for x in rows if x["line"] == ln and x["class"] != "TOTAL"]
        t = [x for x in rows if x["line"] == ln and x["class"] == "TOTAL"][0]
        s = wb.create_sheet(ln)
        s["A1"] = "{0} class-wise {1} split".format(ln, "70:30 and 80:20" if vs80 else "70:30")
        s["A1"].font = title
        s["A2"] = ("Pooled defect-class dataset, one row per unique picture: {0} classes, {1} pictures, "
                   "{2} train and {3} test at 70:30. {4} classes can be scored; a class with a single "
                   "picture produces no test picture, so it trains and is never scored.").format(
            len(rr), t["pictures"], t["train_70"], t["test_30"], t["scorable_70"])
        hdr = ["Class", "Pictures", "Train (70%)", "Test (30%)"]
        if vs80:
            hdr += ["Train (80%)", "Test (20%)"]
        hdr += ["Note"]
        for c, h in enumerate(hdr, start=1):
            cell = s.cell(row=4, column=c, value=h)
            cell.font, cell.fill, cell.border = head, fill, box
        r = 5
        for x in rr:
            vals = [x["class"], x["pictures"], x["train_70"], x["test_30"]]
            if vs80:
                vals += [x["train_80"], x["test_20"]]
            vals += [md_note(x["pictures"], x)]
            for c, v in enumerate(vals, start=1):
                s.cell(row=r, column=c, value=v)
            r += 1
        vals = ["Total", t["pictures"], t["train_70"], t["test_30"]]
        if vs80:
            vals += [t["train_80"], t["test_20"]]
        vals += ["{0} classes".format(len(rr))]
        for c, v in enumerate(vals, start=1):
            s.cell(row=r, column=c, value=v).font = Font(bold=True)
        s.column_dimensions["A"].width = 46
        for col in ("B", "C", "D", "E", "F"):
            s.column_dimensions[col].width = 12
        s.column_dimensions["G"].width = 34
        s.freeze_panes = "A5"

    name = "FMD_class_split_70_30_vs_80_20_20260917.xlsx" if vs80 else "FMD_class_split_70_30_20260917.xlsx"
    path = os.path.join(OUT_REP, name)
    wb.save(path)
    return path


def diff_against_yesterday(rows):
    old = {}
    with open(OLD_SPLIT, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["class"] == "TOTAL":
                continue
            old[(r["line"], r["class"])] = (int(r["pictures"]), int(r["train_70"]), int(r["test_30"]))
    new = {(r["line"], r["class"]): (r["pictures"], r["train_70"], r["test_30"])
           for r in rows if r["class"] != "TOTAL"}
    moved = []
    for k in sorted(set(old) | set(new)):
        if old.get(k) != new.get(k):
            moved.append((k, old.get(k), new.get(k)))
    print("\nDiff against the 2026-09-16 split ({0} cells compared, {1} moved)".format(
        len(set(old) | set(new)), len(moved)))
    for (line, cls), o, n in moved:
        print("  {0:4s} {1:50s} was {2}  now {3}".format(line, cls, o, n))
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", action="store_true", help="also diff against the 2026-09-16 split")
    args = ap.parse_args()

    pool, cells = compute()
    rows = rows_for(cells)
    total = len(pool)
    print("pool: {0} pictures, {1} lines, {2} classes".format(
        total, len(cells), len({c for c, _, _ in pool.values()})))
    for ln in sorted(cells):
        t = [r for r in rows if r["line"] == ln and r["class"] == "TOTAL"][0]
        print("  {0}: {1} pictures, {2} train, {3} test, {4} classes, {5} scorable".format(
            ln, t["pictures"], t["train_70"], t["test_30"],
            len([r for r in rows if r["line"] == ln and r["class"] != "TOTAL"]), t["scorable_70"]))
    if args.diff:
        diff_against_yesterday(rows)
    p1, p2 = write_csvs(rows, pool, cells)
    pmd = write_md(rows, pool, cells)
    px1 = write_xlsx(rows, cells, vs80=False)
    px2 = write_xlsx(rows, cells, vs80=True)
    for p in (p1, p2, pmd, px1, px2):
        print("wrote " + os.path.relpath(p, REPO).replace("\\", "/"))


if __name__ == "__main__":
    main()
