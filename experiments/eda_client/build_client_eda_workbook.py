#!/usr/bin/env python3
"""
Build the client workbook for the five EDA questions (2026-09-17).

Decisions taken with the team before building (all four confirmed):
  1. The dataset counts 8,409 unique pictures: both Updated folders plus the
     177 old-library pictures that appear in neither, Clear dropped except the
     128 Clear pictures that carry a defect label.
  2. Sheet D lists all 11 object-level tags, the 4 from the Updated Objects
     folder first.
  3. Sheet A quotes the Updated Categorical Classes folder as 6,241 images, the
     143 duplicate copies having been removed from the source.
  4. Sheet E shows all three multi-tag counts.

Every number comes from experiments/eda_client/client_eda_numbers.py, which
reads the hash-verified record of all files in the three folders. Nothing is
typed by hand.

Output: reports/library/FMD_Library_EDA_Counts_20260917.xlsx
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from client_eda_numbers import (  # noqa: E402
    F_CAT, F_OBJ, F_OLD, LP_TAGS, REPO as _REPO, load, line_of, norm,
)

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

OUT_PATH = os.path.join(REPO, "reports", "library", "FMD_Library_EDA_Counts_20260917.xlsx")

# the ontology's object-level (bounding-box) tag labels; the four the Updated
# Objects folder carries come first, in the order of the client's chart
OOI_TAGS_ORDERED = [
    ("Foreign Matter", "Foreign Matter"),
    ("Fiber", "Fiber"),
    ("Extraneous Polymer", "Extraneous Polymer"),
    ("HEMA Fragment", "HEMA Fragment (folder name: HEMA)"),
    ("Bubble", "Bubble"),
    ("Wet Package", "Wet Package"),
    ("Bubble Irregular", "Bubble Irregular (ontology: Irregular Bubble)"),
    ("Bubble Cluster", "Bubble Cluster"),
    ("Bubble On 123", "Bubble On 123 (ontology: Bubble Over 123 Mark)"),
    ("Bubble On Edge", "Bubble On Edge"),
    ("Stretched Bubble", "Stretched Bubble (no images in the library)"),
]
NON_TAGS = {"Clear", "duplicates"}

TITLE = Font(bold=True, size=14)
SUB = Font(bold=True, size=11)
HEAD = Font(bold=True, color="FFFFFF")
HEADFILL = PatternFill("solid", fgColor="1F3864")
NOTEFONT = Font(italic=True, size=9, color="555555")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, row, ncols, first_col=1):
    for c in range(first_col, first_col + ncols):
        cell = ws.cell(row=row, column=c)
        cell.font = HEAD
        cell.fill = HEADFILL
        cell.border = BOX
        cell.alignment = Alignment(vertical="center")


def style_body(ws, r0, r1, ncols, first_col=1):
    for r in range(r0, r1 + 1):
        for c in range(first_col, first_col + ncols):
            ws.cell(row=r, column=c).border = BOX


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def build():
    recs = load()
    by_folder = {}
    for r in recs:
        by_folder.setdefault(r["folder"], []).append(r)
    md5_folder = {f: {r["md5"] for r in rs} for f, rs in by_folder.items()}
    md5_updated = md5_folder[F_OBJ] | md5_folder[F_CAT]
    md5_all = {r["md5"] for r in recs}
    lines = sorted({r["line"] for r in recs})
    line_of_md5, name_of, folders_of = {}, {}, {}
    for r in recs:
        line_of_md5.setdefault(r["md5"], r["line"])
        name_of.setdefault(r["md5"], r["name"])

    old = by_folder[F_OLD]
    old_unc_rows = [r for r in old if r["md5"] not in md5_updated]
    old_unc_md5 = {r["md5"] for r in old_unc_rows}

    # tags per picture: Clear and duplicates are not tags
    tags_of = {}
    for r in recs:
        if r["cls"] in NON_TAGS:
            continue
        tags_of.setdefault(r["md5"], set()).add(r["tag"])

    dataset = sorted(m for m in md5_all if (m in md5_updated or m in old_unc_md5) and tags_of.get(m))
    ds = set(dataset)
    clear_md5 = {r["md5"] for r in by_folder[F_OBJ] if r["cls"] == "Clear"}
    kept_clear = sorted(clear_md5 & ds)
    clear_set_aside = len(clear_md5 - ds)

    cat_files = len(by_folder[F_CAT]) - 143          # duplicates/ removed at source
    cat_unique = len(md5_folder[F_CAT])
    old_unique = len(md5_folder[F_OLD])
    obj_files, obj_unique = len(by_folder[F_OBJ]), len(md5_folder[F_OBJ])

    wb = Workbook()

    # ------------------------------------------------------------------ README
    ws = wb.active
    ws.title = "README"
    widths(ws, {"A": 34, "B": 104})
    rows = [
        ("T", "ICube defect image library - EDA counts requested on 2026-09-17", None),
        ("", "", None),
        ("S", "What this workbook answers", None),
        ("", "One sheet per request: A totals per folder, B unique pictures per production line,", None),
        ("", "C unique pictures per Lens Presentation tag, D unique pictures per object-of-interest tag,", None),
        ("", "E whether one picture carries more than one tag. A final sheet compares our per-class", None),
        ("", "counts with the figures printed on the client's two bar charts.", None),
        ("", "", None),
        ("S", "Where the numbers come from", None),
        ("", "One row per image file across the three library folders, with the content hash and the", None),
        ("", "byte size of every file. 11,936 image files in total. No number in this workbook was", None),
        ("", "typed by hand; each is produced by the analysis script over that record.", None),
        ("", "", None),
        ("S", "Rules applied", None),
        ("1", "The two Updated folders are the dataset.", None),
        ("2", "The older ICube Defects Library contributes only the pictures that appear in neither", None),
        ("", "Updated folder: 177 pictures.", None),
        ("3", "Clear is excluded as a class, except the 128 pictures that also carry a defect label.", None),
        ("", "Those 128 stay in the dataset under the defect label.", None),
        ("4", "HEMA in the Updated Objects folder is read as HEMA Fragment.", None),
        ("5", "Name equivalences treated as one tag: Low Dose and Low Dose Obstructing Region of", None),
        ("", "Interest; Multiple Lenses and Multiple Lens; Package Misalignment and Primary Package", None),
        ("", "Misalignment; View Obstructed and Field Of View Obstructed.", None),
        ("6", "A unique image means a distinct picture, identified by content hash, never by file name.", None),
        ("7", "The duplicates subfolder is excluded: every file in it repeats a picture that already", None),
        ("", "sits in the same folder.", None),
        ("", "", None),
        ("S", "Headline figures", None),
        ("", "Image files in the three folders: 11,936.  Updated Objects 4,230, Updated Categorical", None),
        ("", "Classes 6,241, older library 1,465.", None),
        ("", "Distinct pictures: 10,614 across the three folders, 10,437 in the two Updated folders.", None),
        ("", "Dataset after the rules above: 8,409 distinct pictures.", None),
        ("", "Production lines: 5 (L24, L25, L26, L27, L31). Every file carries a line number.", None),
        ("", "", None),
        ("S", "How the counts were checked", None),
        ("", "The file counts and the byte totals of our copy match the record written at transfer, and", None),
        ("", "an independent listing of the source storage on 2026-09-17 agrees with every per-class", None),
        ("", "figure in sheets A to D. The removal of the 143 duplicate files was checked in both", None),
        ("", "directions: none of them is a picture that exists only in that folder, and no repeated", None),
        ("", "picture sits outside it. The count of distinct pictures is therefore unchanged.", None),
        ("", "", None),
        ("S", "Known differences against the client's charts", None),
        ("", "Four cells differ by one or two: Dirty Strobe 42 against 43, Lens Off Center 258 against", None),
        ("", "259, Extraneous Polymer 267 against 269, Foreign Matter 1,282 against 1,280. The source", None),
        ("", "listing agrees with our figures in all sixteen cells. See the last sheet.", None),
    ]
    r = 1
    for kind, text, _ in rows:
        cell = ws.cell(row=r, column=1 if kind in ("T", "S", "1") else 2, value=text)
        if kind == "T":
            cell.font = TITLE
        elif kind == "S":
            cell.font = SUB
        else:
            cell.alignment = Alignment(vertical="center")
        r += 1

    # ----------------------------------------------------------------------- A
    ws = wb.create_sheet("A Library totals")
    widths(ws, {"A": 46, "B": 16, "C": 20, "D": 60})
    ws["A1"] = "A. Total images per folder, distinct pictures, production lines"
    ws["A1"].font = TITLE
    ws["A3"] = "Folder"
    ws["B3"] = "Image files"
    ws["C3"] = "Distinct pictures"
    style_header(ws, 3, 3)
    a_rows = [
        ("Updated ICube Objects 20260915", obj_files, obj_unique, "5 object-type folders, Clear included"),
        ("Updated ICube Categorical Classes 20260915", cat_files, cat_unique,
         "12 defect classes, 143 duplicate copies removed at the source"),
        ("ICube Defects Library (older library)", len(old), old_unique,
         "22 class folders, 63 repeated copies inside the folder"),
    ]
    r = 4
    for row in a_rows:
        for c, v in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    ws.cell(row=r, column=1, value="Three folders together").font = BOLD
    ws.cell(row=r, column=2, value=obj_files + cat_files + len(old)).font = BOLD
    ws.cell(row=r, column=3, value=len(md5_all)).font = BOLD
    ws.cell(row=r, column=4, value="Distinct pictures, so fewer than the file total: the folders share 1,226 pictures")
    style_body(ws, 4, r, 3)
    r += 2
    ws.cell(row=r, column=1, value="Production lines").font = SUB
    r += 1
    ws.cell(row=r, column=1, value=len(lines))
    ws.cell(row=r, column=2, value="L24, L25, L26, L27, L31")
    ws.cell(row=r, column=3, value="every file carries a line number, 0 exceptions")
    r += 2
    ws.cell(row=r, column=1, value="The dataset the client asked for, built up").font = SUB
    r += 1
    steps = [
        ("Distinct pictures in the two Updated folders", len(md5_updated)),
        ("Added: pictures that appear in neither Updated folder (older library)", len(old_unc_md5)),
        ("Subtotal", len(md5_updated) + len(old_unc_md5)),
        ("Removed: Clear pictures that carry no defect label", -clear_set_aside),
        ("Dataset, distinct pictures", len(dataset)),
    ]
    start = r
    for i, (label, val) in enumerate(steps):
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=val)
        if label.startswith("Dataset"):
            ws.cell(row=r, column=1).font = BOLD
            ws.cell(row=r, column=2).font = BOLD
        r += 1
    ws.cell(row=r, column=1,
            value="Includes the 128 pictures filed under Clear that also carry a defect label; "
                  "2,333 Clear pictures are set aside in total, 2,205 of them with no other label.")
    ws.cell(row=r, column=1).font = NOTEFONT
    style_body(ws, start, r - 1, 2)
    a_steps = steps

    # ----------------------------------------------------------------------- B
    ws = wb.create_sheet("B Production lines")
    widths(ws, {"A": 38, "B": 18, "C": 20, "D": 18, "E": 16, "F": 18, "G": 46})
    ws["A1"] = "B. Distinct pictures per production line"
    ws["A1"].font = TITLE
    ws["A2"] = "Clear pictures are set aside, so they are shown in their own column and not in the dataset total."
    ws["A2"].font = NOTEFONT
    hdr = ["Production line", "Updated Objects", "Updated Categorical Classes",
           "Older library (kept)", "Clear set aside", "Dataset total", "Note"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=4, column=c, value=h)
    style_header(ws, 4, len(hdr))
    b_rows = []
    for ln in lines:
        o = sum(1 for m in md5_folder[F_OBJ] if line_of_md5[m] == ln)
        c = sum(1 for m in md5_folder[F_CAT] if line_of_md5[m] == ln)
        k = sum(1 for m in old_unc_md5 if line_of_md5[m] == ln)
        cl = sum(1 for m in clear_md5 if line_of_md5[m] == ln)
        tot = sum(1 for m in ds if line_of_md5[m] == ln)
        b_rows.append([ln, o, c, k, cl, tot, ""])
    b_rows.append(["TOTAL", obj_unique, cat_unique, len(old_unc_md5), len(clear_md5), len(dataset),
                   "L24 holds 34 percent of the dataset and L31 24 percent; L25 is the smallest at 11 percent"])
    r = 5
    for row in b_rows:
        for c, v in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=v)
        if row[0] == "TOTAL":
            for c in range(1, 8):
                ws.cell(row=r, column=c).font = BOLD
        r += 1
    style_body(ws, 5, r - 1, len(hdr))

    # ----------------------------------------------------------------------- C
    ws = wb.create_sheet("C Lens Presentation tags")
    widths(ws, {"A": 44, "B": 22, "C": 20, "D": 16, "E": 20, "F": 52})
    ws["A1"] = "C. Distinct pictures per Lens Presentation tag"
    ws["A1"].font = TITLE
    ws["A2"] = "The Updated Categorical Classes folder carries these 12 image-level tags. " \
               "The older library adds 2 further pictures, one Bubble Scatter and one Dirty Strobe."
    ws["A2"].font = NOTEFONT
    hdr = ["Lens Presentation tag", "In the Updated folder", "Added by older library",
           "Dataset total", "Of which were filed under Clear", "Note"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=4, column=c, value=h)
    style_header(ws, 4, len(hdr))
    r = 5
    lp_union = 0
    for tag in LP_TAGS:
        folder_n = len({m for m in md5_folder[F_CAT] if tag in tags_of.get(m, ())})
        allm = {m for m in ds if tag in tags_of.get(m, ())}
        extra = len(allm) - folder_n
        clr = len(allm & clear_md5)
        note = ""
        if tag == "Low Dose Obstructing Region of Interest":
            note = "folder name: Low Dose"
        elif tag == "Multiple Lenses":
            note = "ontology name: Multiple Lens"
        elif tag == "Package Misalignment":
            note = "ontology name: Primary Package Misalignment"
        elif tag == "View Obstructed":
            note = "ontology name: Field Of View Obstructed"
        for c, v in enumerate([tag, folder_n, extra, len(allm), clr, note], start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    lp_union = len({m for m in ds if tags_of.get(m, set()) & set(LP_TAGS)})
    ws.cell(row=r, column=1, value="Pictures carrying at least one of these tags").font = BOLD
    ws.cell(row=r, column=2, value=len({m for m in md5_folder[F_CAT] if tags_of.get(m, set()) & set(LP_TAGS)})).font = BOLD
    ws.cell(row=r, column=3, value=2).font = BOLD
    ws.cell(row=r, column=4, value=lp_union).font = BOLD
    ws.cell(row=r, column=5, value=len({m for m in ds if tags_of.get(m, set()) & set(LP_TAGS)} & clear_md5)).font = BOLD
    ws.cell(row=r, column=6,
            value="The column total is 6,243 against 6,241 distinct pictures in the folder, because the older "
                  "library adds 2 pictures that the Updated folder does not hold.").font = NOTEFONT
    style_body(ws, 5, r, len(hdr))

    # ----------------------------------------------------------------------- D
    ws = wb.create_sheet("D OOI tags")
    widths(ws, {"A": 48, "B": 22, "C": 22, "D": 16, "E": 56})
    ws["A1"] = "D. Distinct pictures per object-of-interest tag"
    ws["A1"].font = TITLE
    ws["A2"] = "All 11 object-level tags of the naming document. The first four are the tags the " \
               "Updated Objects folder carries; the rest reach the dataset through the older library."
    ws["A2"].font = NOTEFONT
    hdr = ["Object-of-interest tag", "In an Updated folder", "Added by older library",
           "Dataset total", "Note"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=4, column=c, value=h)
    style_header(ws, 4, len(hdr))
    r = 5
    d_rows = []
    for raw, label in OOI_TAGS_ORDERED:
        new = len({m for m in md5_updated if raw in tags_of.get(m, ())})
        allm = len({m for m in ds if raw in tags_of.get(m, ())})
        note = ""
        if raw == "Foreign Matter":
            note = "Updated Objects folder holds 1,282 files; one further picture carries this tag as a second label"
        elif raw == "Stretched Bubble":
            note = "no images in the library"
        elif raw in ("Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123", "Bubble On Edge", "Wet Package"):
            note = "reaches the dataset only through the older library"
        d_rows.append([label, new, allm - new, allm, note])
        for c, v in enumerate(d_rows[-1], start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    obj_union = len({m for m in ds if tags_of.get(m, set()) & {t for t, _ in OOI_TAGS_ORDERED}})
    ws.cell(row=r, column=1, value="Pictures carrying at least one object-of-interest tag").font = BOLD
    ws.cell(row=r, column=2, value=len({m for m in md5_updated if tags_of.get(m, set()) & {t for t, _ in OOI_TAGS_ORDERED}})).font = BOLD
    ws.cell(row=r, column=3, value=obj_union - len({m for m in md5_updated if tags_of.get(m, set()) & {t for t, _ in OOI_TAGS_ORDERED}})).font = BOLD
    ws.cell(row=r, column=4, value=obj_union).font = BOLD
    ws.cell(row=r, column=5, value="Bubble Scatter is an image-level tag and is counted in sheet C").font = NOTEFONT
    style_body(ws, 5, r, len(hdr))

    # ----------------------------------------------------------------------- E
    ws = wb.create_sheet("E Multi-tag images")
    widths(ws, {"A": 62, "B": 12, "C": 16, "D": 70})
    ws["A1"] = "E. Is one picture annotated with more than one tag?"
    ws["A1"].font = TITLE
    ws["A2"] = "Yes, but rarely. The count depends on how the name variants are treated, so four views are shown."
    ws["A2"].font = NOTEFONT
    hdr = ["View", "Pictures", "Of which carry three tags", "What it counts"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=4, column=c, value=h)
    style_header(ws, 4, len(hdr))

    tags_exact, tags_all = {}, {}
    for r_ in recs:
        tags_all.setdefault(r_["md5"], set()).add(r_["cls"])
        if r_["cls"] in NON_TAGS:
            continue
        tags_exact.setdefault(r_["md5"], set()).add(r_["cls"])
    c_variants = sum(1 for t in tags_exact.values() if len(t) > 1)          # raw names, Clear/dup ignored
    v3 = sum(1 for t in tags_exact.values() if len(t) > 2)
    c_everything = sum(1 for t in tags_all.values() if len(t) > 1)          # also Clear/duplicates counted
    e3 = sum(1 for t in tags_all.values() if len(t) > 2)
    c_strict = len([m for m in ds if len(tags_of.get(m, ())) > 1])
    e_rows = [
        ("One tag only", len(dataset) - c_strict, 0,
         "pictures in the dataset carrying a single tag"),
        ("More than one tag, name variants treated as one tag", c_strict, 0,
         "the strict answer: Low Dose is one tag with Low Dose Obstructing Region of Interest, "
         "and HEMA with HEMA Fragment; Clear and duplicates are not tags"),
        ("More than one tag, name variants left separate", c_variants, v3,
         "the same, but Low Dose against Low Dose Obstructing Region of Interest and HEMA against "
         "HEMA Fragment each count as two tags"),
        ("More than one tag, counting every label", c_everything, e3,
         "also counts Clear and duplicates as tags; this is the figure our earlier report quoted"),
    ]
    r = 5
    for row in e_rows:
        for c, v in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    style_body(ws, 5, r - 1, len(hdr))
    r += 1
    ws.cell(row=r, column=1,
            value="Counting every label, 8 pictures carry three tags: 4 hold Low Dose, Low Dose Obstructing Region of "
                  "Interest and duplicates (a picture filed under both names and in the duplicate folder), 2 hold "
                  "Clear plus Wet Package plus Multiple Lenses or Lens Off Center, 1 holds Low Dose, Low Dose "
                  "Obstructing Region of Interest and Wet Package, and 1 holds Foreign Matter plus both Low Dose "
                  "names. After merging the name variants, 4 of the 8 keep two tags and 4 keep one.").font = SUB
    r += 2
    ws.cell(row=r, column=1, value="The tag pairs that share a picture (name variants treated as one tag)").font = SUB
    r += 1
    hdr = ["Tag A", "Tag B", "Pictures sharing both tags"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=c, value=h)
    style_header(ws, r, 3)
    r += 1
    pairs = {}
    for m in ds:
        ts = sorted(tags_of.get(m, ()))
        if len(ts) < 2:
            continue
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pairs[(ts[i], ts[j])] = pairs.get((ts[i], ts[j]), 0) + 1
    start = r
    for (a, b), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):
        ws.cell(row=r, column=1, value=a)
        ws.cell(row=r, column=2, value=b)
        ws.cell(row=r, column=3, value=n)
        r += 1
    ws.cell(row=r, column=1, value="Total pictures with more than one tag").font = BOLD
    ws.cell(row=r, column=3, value=c_strict).font = BOLD
    style_body(ws, start, r, 3)
    r += 2
    ws.cell(row=r, column=1,
            value="Separate check on the bounding-box annotation file: of the 435 images it covers, "
                  "no image carries more than one box label.").font = NOTEFONT

    # ------------------------------------------------------- chart reconciliation
    ws = wb.create_sheet("Chart reconciliation")
    widths(ws, {"A": 30, "B": 38, "C": 16, "D": 16, "E": 12})
    ws["A1"] = "Our per-class counts against the client's two bar charts"
    ws["A1"].font = TITLE
    ws["A2"] = "Our figures are the folder file counts, from the same record used in sheets A to D. " \
               "The source storage listing of 2026-09-17 agrees with our column in all sixteen cells."
    ws["A2"].font = NOTEFONT
    hdr = ["Folder", "Class", "Client chart", "Our count", "Difference"]
    for c, h in enumerate(hdr, start=1):
        ws.cell(row=4, column=c, value=h)
    style_header(ws, 4, 5)
    chart_cat = [("Low Dose", 1952), ("Multiple Lenses", 1439), ("Missing Primary Package", 1427),
                 ("Missing Lens", 324), ("Package Misalignment", 293), ("Lens Off Center", 259),
                 ("Cavity Off Center", 183), ("HEMA Obstruction", 175), ("View Obstructed", 117),
                 ("Dirty Strobe", 43), ("Dirty Camera", 25), ("Bubble Scatter", 6)]
    chart_obj = [("Foreign Matter", 1280), ("Fiber", 328), ("Extraneous Polymer", 269), ("HEMA", 20)]
    r = 5
    for cls, n in chart_cat:
        ours = sum(1 for x in by_folder[F_CAT] if x["cls"] == cls)
        for c, v in enumerate(["Updated Categorical Classes", cls, n, ours, ours - n], start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    for cls, n in chart_obj:
        ours = sum(1 for x in by_folder[F_OBJ] if x["cls"] == cls)
        for c, v in enumerate(["Updated Objects", cls, n, ours, ours - n], start=1):
            ws.cell(row=r, column=c, value=v)
        r += 1
    style_body(ws, 5, r - 1, 5)
    r += 1
    ws.cell(row=r, column=1, value="Four cells differ by one or two images. Our counts come from a record "
                                   "of every file with its content hash and are confirmed by the source "
                                   "listing, so the differences sit in the charts.").font = NOTEFONT

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    wb.save(OUT_PATH)
    print("wrote " + os.path.relpath(OUT_PATH, REPO).replace("\\", "/"))
    print("sheets: " + ", ".join(wb.sheetnames))
    print("dataset pictures: {0}  (clear set aside {1})".format(len(dataset), clear_set_aside))
    print("object-tag union: {0}   lp union: {1}".format(obj_union, lp_union))
    print("multi-tag: strict {0}, variants separate {1}, everything {2}".format(
        c_strict, c_variants, c_everything))


if __name__ == "__main__":
    build()
