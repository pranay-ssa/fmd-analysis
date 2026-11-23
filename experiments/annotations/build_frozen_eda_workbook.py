#!/usr/bin/env python3
"""Build the first draft of the frozen-set EDA workbook.

Reads run/frozen_eda_20261118/label_space.json (produced by frozen_eda_labels.py)
and writes reports/frozen_eda_20261118/FMD_Frozen_EDA_draft_20261118.xlsx.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import Break

REPO = Path(__file__).resolve().parents[2]
DATA = json.loads((REPO / "run/frozen_eda_20261118/label_space.json").read_text(encoding="utf-8"))
SENS = json.loads((REPO / "run/frozen_eda_20261118/duplicate_sensitivity.json").read_text(encoding="utf-8"))
OUT = Path(os.environ.get(
    "EDA_OUT",
    str(REPO / "reports/frozen_eda_20261118/FMD_Frozen_EDA_draft_20261118.xlsx"),
))
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = "1F3864"
LIGHT = "D9E2F3"
GREY = "595959"
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
F_TITLE = Font(name="Calibri", size=16, bold=True, color=NAVY)
F_SUB = Font(name="Calibri", size=10, italic=True, color=GREY)
F_HDR = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
F_SEC = Font(name="Calibri", size=11, bold=True, color=NAVY)
F_BODY = Font(name="Calibri", size=10)
F_BOLD = Font(name="Calibri", size=10, bold=True)

CLASS_NAME = {
    "P1_COC": "Cavity Off Center", "P1_EBC": "Edge Bottle-Capped", "P1_FL": "Folded Lens",
    "P1_LR": "Lens Rupture", "P1_ML": "Multiple Lens", "P1_MPP": "Missing Primary Package",
    "P1_NL": "No Lens", "P1_PPM": "Primary Package Misalignment", "P1_TL": "Torn Lens",
    "P2_BSC": "Bubble Scatter", "P2_DC": "Dirty Camera", "P2_DS": "Dirty Strobe",
    "P2_LD": "Low Dose", "P2_LOC": "Lens Off Center", "F2_FOV": "Field of View Obstructed",
    "P2_BB": "Bubble", "P2_BC": "Bubble Cluster", "P2_WP": "Wet Package",
    "P1_SG": "Surface Groove", "P3_FM": "Foreign Matter", "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer", "P3_HE": "HEMA",
}

def title(ws, text, sub=None, width=8):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    c = ws.cell(row=1, column=1, value=text)
    c.font = F_TITLE
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26
    if sub:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
        c = ws.cell(row=2, column=1, value=sub)
        c.font = F_SUB
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[2].height = 30

def section(ws, row, text, width=8):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    c = ws.cell(row=row, column=1, value=text)
    c.font = F_SEC
    c.fill = PatternFill("solid", fgColor=LIGHT)
    for col in range(1, width + 1):
        ws.cell(row=row, column=col).fill = PatternFill("solid", fgColor=LIGHT)
    return row + 1

def table(ws, row, headers, rows, widths=None, formats=None, bold_last=False):
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.font = F_HDR
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(vertical="center", wrap_text=True)
        c.border = BORDER
    ws.row_dimensions[row].height = 30
    start = row
    for i, r in enumerate(rows, 1):
        for j, v in enumerate(r, 1):
            c = ws.cell(row=row + i, column=j, value=v)
            c.font = F_BOLD if (bold_last and i == len(rows)) else F_BODY
            c.border = BORDER
            c.alignment = Alignment(vertical="center")
            if formats and j <= len(formats) and formats[j - 1]:
                c.number_format = formats[j - 1]
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    return row + len(rows) + 2

def note(ws, row, text, width=8):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name="Calibri", size=9, color=GREY)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    lines = max(1, len(text) // 120 + 1)
    ws.row_dimensions[row].height = 13 * lines + 2
    return row + 1

def label_name(code):
    return CLASS_NAME.get(code, code)

def pshare(num, den):
    """A share is only meaningful when its own denominator is non-zero."""
    return num / den if den else "-"

wb = Workbook()
wb.properties.creator = "Pranay"
wb.properties.lastModifiedBy = "Pranay"

s = DATA["summary"]
lp_rows = DATA["lp"]
ooi_rows = DATA["ooi"]
comp1, top1 = DATA["composition1"], DATA["top1"]
comp2, top2 = DATA["composition2"], DATA["top2"]
comp3, top3 = DATA["composition3"], DATA["top3"]
comp4, top4 = DATA["composition4"], DATA["top4"]
top_inclusive = DATA["top_inclusive"]
passrows = DATA["size_untagged"]

# ---------------- Read me ----------------
ws = wb.active
ws.title = "Read me"
title(ws, "Frozen annotation dataset: label space and size-flag check",
      "First draft. Counts are images unless a column says tags or boxes.", 6)
r = 4
txt = [
    "This workbook counts the frozen annotation: 13,682 records, all retained. Four pictures appear "
    "under two names, so there are 13,678 distinct pictures. The label counts count each picture once; "
    "no record is deleted. The four pairs are unresolved: Duplicate sensitivity shows the counts for all "
    "records, for one copy per pair, and for both copies excluded.",
    "Clear is a label. Every image in the labelled population carries either Clear or at least one "
    "defect class, so there is no zero-label row. The five images with no marks outside the Clear "
    "folder are unannotated and are outside the label counts.",
    "The 147 add-back candidates and the 27 discarded legacy pictures are outside this workbook. "
    "They are a separate decision.",
    "Prepared 18 November 2026. Sheets: Summary, Duplicate sensitivity, LP labels, OOI labels, "
    "Label combinations, Size untagged PASS, Duplicates and Clear, Definitions.",
]
for t in txt:
    r = note(ws, r, t, 6)
    ws.row_dimensions[r - 1].height = 30
ws.column_dimensions["A"].width = 120

# ---------------- Summary ----------------
ws = wb.create_sheet("Summary")
title(ws, "Summary", "The population and the label groups.", 4)
r = 4
r = section(ws, r, "Population", 4)
r = table(ws, r, ["Measure", "Images"], [
    ("Annotation records, all retained", s["annotation_records"]),
    ("Second records of four pairs, retained", s["duplicate_records_removed"]),
    ("Distinct pictures", s["unique_images"]),
    ("Pictures with at least one mark", s["marked"]),
    ("Clear", s["clear"]),
    ("Unannotated, excluded from labels", s["unannotated"]),
    ("Labelled pictures", s["labelled_population"]),
], widths=[42, 14], formats=["#,##0", "#,##0"], bold_last=True)
r = note(ws, r, "Nothing was deleted. Four pictures appear under two names. The tables below use one "
                "copy per pair as a working basis, not a decision; the alternatives and their effect are on "
                "Duplicate sensitivity. Counting both records gives 13,677 labelled records; excluding both "
                "copies gives 13,669.", 4)
r = section(ws, r, "Label groups", 4)
r = table(ws, r, ["Group", "Images"], [
    ("At least one LP tag", s["lp_pictures"]),
    ("At least one OOI box", s["ooi_pictures"]),
    ("LP tag and OOI box", s["lp_and_ooi"]),
    ("Single label, LP", s["single_lp"]),
    ("Single label, OOI", s["single_ooi"]),
    ("Exactly two labels", s["labels"]["2"]),
    ("Exactly three labels", s["labels"]["3"]),
    ("Exactly four labels", s["labels"]["4"]),
    ("Five or more labels", sum(s["labels"][k] for k in ("5", "6", "7", "8", "9"))),
], widths=[42, 14], formats=["#,##0", "#,##0"])
r = note(ws, r, "The LP and OOI groups overlap: 5,648 images carry both. A single-label image carries "
                 "exactly one class, LP or OOI. Clear is a label and is not counted as a class.", 4)

# ---------------- Duplicate sensitivity ----------------
ws = wb.create_sheet("Duplicate sensitivity", 2)
title(ws, "Four duplicate pairs: what each choice does to the counts",
      "No choice has been made. The three bases are shown so the size of the effect is explicit.", 6)
r = 4
r = section(ws, r, "Population and label groups", 6)

def val(base, key):
    return SENS[base][key]

rows1 = [
    ("Annotation records", val("all", "records"), val("one", "records"), val("exclude", "records")),
    ("Labelled pictures", val("all", "labelled"), val("one", "labelled"), val("exclude", "labelled")),
    ("Clear", val("all", "clear"), val("one", "clear"), val("exclude", "clear")),
    ("Unannotated", val("all", "unannotated"), val("one", "unannotated"), val("exclude", "unannotated")),
    ("Pictures with an LP tag", val("all", "lp_pictures"), val("one", "lp_pictures"), val("exclude", "lp_pictures")),
    ("Pictures with an OOI box", val("all", "ooi_pictures"), val("one", "ooi_pictures"), val("exclude", "ooi_pictures")),
    ("Pictures with both", val("all", "both"), val("one", "both"), val("exclude", "both")),
    ("Single label", val("all", "single"), val("one", "single"), val("exclude", "single")),
    ("Two labels", SENS["all"]["buckets"]["2"], SENS["one"]["buckets"]["2"], SENS["exclude"]["buckets"]["2"]),
    ("Three labels", SENS["all"]["buckets"]["3"], SENS["one"]["buckets"]["3"], SENS["exclude"]["buckets"]["3"]),
    ("Four labels", SENS["all"]["buckets"]["4"], SENS["one"]["buckets"]["4"], SENS["exclude"]["buckets"]["4"]),
    ("Five labels", SENS["all"]["buckets"]["5"], SENS["one"]["buckets"]["5"], SENS["exclude"]["buckets"]["5"]),
    ("Six labels", SENS["all"]["buckets"]["6"], SENS["one"]["buckets"]["6"], SENS["exclude"]["buckets"]["6"]),
    ("Seven labels", SENS["all"]["buckets"]["7"], SENS["one"]["buckets"]["7"], SENS["exclude"]["buckets"]["7"]),
    ("Eight labels", SENS["all"]["buckets"]["8"], SENS["one"]["buckets"]["8"], SENS["exclude"]["buckets"]["8"]),
    ("Nine labels", SENS["all"]["buckets"]["9"], SENS["one"]["buckets"]["9"], SENS["exclude"]["buckets"]["9"]),
]
r = table(ws, r, ["Measure", "All records", "One copy per pair", "Both copies excluded"],
          rows1, widths=[34, 16, 18, 18], formats=[None, "#,##0", "#,##0", "#,##0"])
r = note(ws, r, "One copy per pair is the working basis used by the other sheets. It is not a decision. "
                "All records keeps both records of every pair; both copies excluded sets all eight aside.", 4)

r = section(ws, r, "Classes touched by the pairs", 6)
codes = [("P2_BB", "Bubble", "ooi"), ("P2_BC", "Bubble Cluster", "ooi"),
         ("P3_FIB", "Fiber", "ooi"), ("P3_HE", "HEMA", "ooi"),
         ("P3_FM", "Foreign Matter", "ooi"), ("P3_EP", "Extraneous Polymer", "ooi"),
         ("P1_LR", "Lens Rupture", "lp"), ("P2_DC", "Dirty Camera", "lp")]
rows2 = []
for code, name, kind in codes:
    a = SENS["all"][kind + "_classes"].get(code, 0)
    o = SENS["one"][kind + "_classes"].get(code, 0)
    e = SENS["exclude"][kind + "_classes"].get(code, 0)
    rows2.append((code, name, a, o, e, o - a, e - a))
r = table(ws, r, ["Code", "Class", "All records", "One copy", "Both excluded",
                  "Change, one copy", "Change, both"], rows2,
          widths=[10, 26, 13, 12, 14, 14, 13],
          formats=[None, None, "#,##0", "#,##0", "#,##0", "+#,##0;-#,##0;0", "+#,##0;-#,##0;0"])
r = note(ws, r, "Only these eight classes occur on the pair records. Every other class is unchanged.", 6)

r = section(ws, r, "If one copy is kept, which copy changes what", 6)
rows3 = [
    (1, "7 boxes / 7 boxes", "Nothing in the class counts; both records carry the same three classes."),
    (2, "24 boxes / 23 boxes", "Nothing in the class counts; the longer record carries one more Bubble box."),
    (3, "17 boxes / 10 boxes", "Bubble Cluster moves by 1, and the picture moves between five and six labels."),
    (4, "4 boxes / 3 boxes", "Nothing in the class counts; the longer record carries one more Bubble box."),
]
r = table(ws, r, ["Pair", "The two records", "What changes if you keep the other copy"], rows3,
          widths=[8, 22, 80])
r = note(ws, r, "For pairs 1, 2 and 4 the class counts do not depend on which record is kept. Only pair 3 "
                "differs by a class, Bubble Cluster. Box totals can differ even when class counts do not.", 6)

# ---------------- LP labels ----------------
ws = wb.create_sheet("LP labels")
title(ws, "Lens presentation labels",
      "15 classes. Pictures carrying each class; a picture can carry several. The four duplicate records "
      "count once.", 5)
rows = [(x["code"], x["class"], x["pictures"], x["share_of_labelled"]) for x in lp_rows]
rows.append(("Any LP tag", "Distinct pictures with an LP tag", s["lp_pictures"],
             s["lp_pictures"] / s["labelled_population"]))
table(ws, 4, ["Code", "Class", "Pictures", "Share of labelled pictures"],
      rows, widths=[10, 34, 12, 24], formats=[None, None, "#,##0", "0.0%"], bold_last=True)
note(ws, 4 + len(rows) + 2,
     "Rows are not additive: a picture can carry several LP classes, so the class rows overlap and the "
     "shares do not sum to 100%. The table counts pictures, not tag entries: the annotation holds 12,250 "
     "LP tag entries, of which six repeat a class already on the same picture. Clear is not an LP class.", 4)

# ---------------- OOI labels ----------------
ws = wb.create_sheet("OOI labels")
title(ws, "Objects of interest",
      "8 classes. Pictures with a box, boxes drawn, and the size-flag subset. The four duplicate records "
      "count once.", 6)
rows = [(x["code"], x["class"], x["pictures"], x["boxes"], x["size_flagged"], x["share_of_labelled"])
        for x in ooi_rows]
rows.append(("Any OOI box", "Distinct pictures with an OOI box", s["ooi_pictures"],
             sum(x["boxes"] for x in ooi_rows), sum(x["size_flagged"] for x in ooi_rows),
             s["ooi_pictures"] / s["labelled_population"]))
table(ws, 4, ["Code", "Class", "Pictures", "Boxes", "Of which size-flagged", "Share of labelled pictures"],
      rows, widths=[10, 26, 12, 12, 20, 24], formats=[None, None, "#,##0", "#,##0", "#,##0", "0.0%"],
      bold_last=True)
note(ws, 4 + len(rows) + 2,
     "Rows are not additive: a picture can carry several classes and many boxes. Boxes counts every box; "
     "a picture is counted once in Pictures. The size flag is a subset of its class and is never a class of "
     "its own.", 6)

# ---------------- Label combinations ----------------
ws = wb.create_sheet("Label combinations")
title(ws, "Label combinations",
      "How many labels one image carries, then the label sets at one, two, three and four labels. "
      "Composition tables list non-zero splits only; no picture carries three or four LP classes without "
      "an OOI box, so those splits are zero.", 4)
r = 4
r = section(ws, r, "Labels on the image", 4)
count_rows = [(f"{k} label" + ("" if k == 1 else "s"), s["labels"][str(k)]) for k in range(1, 10)]
count_rows.append(("Clear", s["clear"]))
count_rows.append(("Total", s["labelled_population"]))
r = table(ws, r, ["Labels", "Images"], count_rows, widths=[80, 12],
          formats=[None, "#,##0"], bold_last=True)
r = note(ws, r, "Every labelled image carries at least one label. Clear counts as one. There is no "
                "zero-label row; the five unannotated images are outside this table. The four duplicated "
                "pictures are counted once each on the working basis; see Duplicate sensitivity.", 4)

def comp_text(text):
    a, b = text.split(" LP + ")
    a = int(a)
    b = int(b.split()[0])
    if a == 0 and b == 1:
        return "Single OOI"
    if a == 1 and b == 0:
        return "Single LP"
    if b == 0:
        return f"{a} LP only"
    if a == 0:
        return f"{b} OOI only"
    return f"{a} LP + {b} OOI"

def label_block(r, heading, total, comp, top, top_header, top_n, foot=None):
    start = r
    r = section(ws, r, f"{heading}: {total:,} images", 4)
    r = table(ws, r, ["Composition", "Images"],
              [(comp_text(x["composition"]), x["pictures"]) for x in comp],
              widths=[80, 12], formats=[None, "#,##0"])
    r = table(ws, r, [top_header, "Images"],
              [(" + ".join(label_name(c) for c in x["labels"]), x["pictures"]) for x in top[:top_n]],
              widths=[80, 12], formats=[None, "#,##0"])
    if foot:
        r = note(ws, r, foot, 4)
    ws.row_breaks.append(Break(id=max(1, start - 1)))
    return r

# One label: the complete set is one class.
start = r
r = section(ws, r, f"One label: {s['labels']['1']:,} images", 4)
r = table(ws, r, ["Composition", "Images"],
          [(comp_text(x["composition"]), x["pictures"]) for x in comp1],
          widths=[80, 12], formats=[None, "#,##0"])
r = table(ws, r, ["Single label", "Images"],
          [(x["class"], x["pictures"]) for x in DATA["single_labels"]] +
          [("Total", s["labels"]["1"])],
          widths=[80, 12], formats=[None, "#,##0"], bold_last=True)
ws.row_breaks.append(Break(id=max(1, start - 1)))

# Two labels: exact pairs, then inclusive pairs.
start = r
r = section(ws, r, f"Two labels: {s['labels']['2']:,} images", 4)
r = table(ws, r, ["Composition", "Images"],
          [(comp_text(x["composition"]), x["pictures"]) for x in comp2],
          widths=[80, 12], formats=[None, "#,##0"])
r = table(ws, r, ["Exact pair (the complete label set)", "Images"],
          [(" + ".join(label_name(c) for c in x["labels"]), x["pictures"]) for x in top2[:15]],
          widths=[80, 12], formats=[None, "#,##0"])
# The two pair tables do not fit on one page together; start the inclusive table
# on a fresh page rather than splitting it.
ws.row_breaks.append(Break(id=max(1, r - 1)))
r = table(ws, r, ["Inclusive pair (both labels, further labels allowed)", "Images"],
          [(" + ".join(label_name(c) for c in x["labels"]), x["pictures"]) for x in top_inclusive],
          widths=[80, 12], formats=[None, "#,##0"])
r = note(ws, r, "The exact table counts only images whose complete set is that pair. The inclusive table "
                "counts every image that carries both, so a pair can look rare above only because most of "
                "its images carry a third label.", 4)
ws.row_breaks.append(Break(id=max(1, start - 1)))

r = label_block(r, "Three labels", s["labels"]["3"], comp3, top3, "Exact label set", 10)
r = label_block(r, "Four labels", s["labels"]["4"], comp4, top4, "Exact label set", 10)

# ---------------- Size untagged PASS ----------------
ws = wb.create_sheet("Size untagged PASS")
title(ws, "Size-untagged pictures of the four size-flagged classes",
      "A picture that carries a class but not its size flag. Pass means no other defect is present.", 7)
order = ["P3_FM", "P3_FIB", "P3_EP", "P3_HE", "UNION"]
rows = []
for code in order:
    x = passrows[code]
    name = "Any of the four (no size flag at all)" if code == "UNION" else label_name(code)
    rows.append((name, x["pictures"], x["flagged"], x["untagged"], x["pass_strict"],
                 pshare(x["pass_strict"], x["untagged"]),
                 x["pass_extended"], pshare(x["pass_extended"], x["untagged"])))
table(ws, 4, ["Class", "Pictures with the class", "Size-flagged", "No size flag",
              "Pass, bubbles only", "Share", "Pass, bubbles + cluster + wet package", "Share"],
      rows, widths=[30, 16, 12, 12, 15, 9, 24, 9],
      formats=[None, "#,##0", "#,##0", "#,##0", "#,##0", "0.0%", "#,##0", "0.0%"], bold_last=True)
note(ws, 4 + len(rows) + 2,
     "Pass, bubbles only: no presentation tag, no size flag of any class, and every box is Bubble or an "
     "untagged object of the four size-flagged classes. Pass, extended: the same, with Bubble Cluster and "
     "Wet Package also allowed. The Any row counts pictures with no size flag at all, so its flagged and "
     "no-flag columns add to its class total. A picture flagged for one class and untagged for another is "
     "outside the Any row.", 8)
r = 4 + len(rows) + 4
r = section(ws, r, "Why an untagged image can still fail", 8)
reasons = []
for code in order:
    x = passrows[code]
    name = "Any of the four (no size flag at all)" if code == "UNION" else label_name(code)
    reasons.append((name, x["reasons"].get("LP tag present", 0),
                    x["reasons"].get("Another size flag present", 0),
                    x["reasons"].get("Bubble Cluster", 0), x["reasons"].get("Wet Package", 0),
                    x["reasons"].get("Surface Groove", 0)))
table(ws, r, ["Class", "Presentation tag", "Another size flag", "Bubble Cluster", "Wet Package",
              "Surface Groove"], reasons, widths=[30, 16, 17, 15, 13, 14],
      formats=[None, "#,##0", "#,##0", "#,##0", "#,##0", "#,##0"])
note(ws, r + len(reasons) + 2, "One image can fail for more than one reason, so these columns overlap.", 8)

# ---------------- Duplicates and Clear ----------------
ws = wb.create_sheet("Duplicates and Clear")
title(ws, "Four duplicate pairs and the Clear count",
      "The eight records are retained; the label counts count each picture once.", 7)
r = 4
r = section(ws, r, "Four pictures recorded twice", 7)
r = note(ws, r, "Each pair is the same image content under two names, inside one annotation file and one job. "
                "The boxes are near copies, not two independent annotations. Both records remain in the "
                "frozen set; no record was deleted. No choice has been made between keeping one copy and excluding "
                "both; the effect of each is on Duplicate sensitivity.", 7)
r = table(ws, r, ["Pair", "Annotation file", "Boxes A / B", "Matched", "Median IoU",
                  "Median coordinate shift", "Largest shift"], [
    (1, "annotations_4521940.xml", "7 / 7", 7, 0.95, "0.33 px", "4.2 px"),
    (2, "annotations_4521947.xml", "24 / 23", 23, 0.88, "0.35 px", "8.2 px"),
    (3, "annotations_4521947.xml", "10 / 17", 10, 1.00, "0.00 px", "16.0 px"),
    (4, "annotations_4521992.xml", "3 / 4", 3, 0.84, "0.95 px", "1.2 px"),
], widths=[8, 28, 12, 10, 11, 22, 12], formats=[None, None, None, "#,##0", "0.00", None, None])
r = section(ws, r, "Clear", 7)
# The Clear block shares the sheet with a seven-column table, so its label is merged
# across A:C and the count sits in D; resetting widths for a two-column table would
# shrink the annotation-file column above it.
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
for col in range(1, 5):
    ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=NAVY)
    ws.cell(row=r, column=col).border = BORDER
c = ws.cell(row=r, column=1, value="Measure")
c.font = F_HDR
c = ws.cell(row=r, column=4, value="Images")
c.font = F_HDR
ws.row_dimensions[r].height = 20
r += 1
clear_rows = [
    ("Clear-folder images in the frozen set", 2333),
    ("Re-annotated with a class", 2291),
    ("- bubble boxes only", 1712),
    ("- another object box only", 255),
    ("- presentation tag present", 324),
    ("Still Clear", s["clear"]),
]
for i, (label, val) in enumerate(clear_rows, 1):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    c = ws.cell(row=r, column=1, value=label)
    c.font = F_BOLD if i == len(clear_rows) else F_BODY
    c.alignment = Alignment(vertical="center")
    for col in range(1, 5):
        ws.cell(row=r, column=col).border = BORDER
    v = ws.cell(row=r, column=4, value=val)
    v.font = F_BOLD if i == len(clear_rows) else F_BODY
    v.number_format = "#,##0"
    v.border = BORDER
    r += 1
r += 1
r = note(ws, r, "The fall from 2,117 Clear images to 42 is a re-labelling, not a loss of pictures. All 2,333 "
                "Clear-folder images are in the frozen set; 2,291 of them received a defect class.", 7)

# ---------------- Definitions ----------------
ws = wb.create_sheet("Definitions")
title(ws, "Definitions", "Every term used in the sheets above.", 4)
defs = [
    ("Record", "One image element in the frozen annotation, identified by its file name. All records are retained; four pictures have two records."),
    ("Distinct picture", "One distinct image content. Four contents appear twice under two names; both records are retained."),
    ("Labelled pictures", "Distinct pictures that carry Clear or at least one defect class. Five unannotated pictures are outside it."),
    ("LP tag", "A presentation condition marked for the whole image. 15 classes."),
    ("OOI box", "An object of interest marked with a box. 8 classes; one image can carry many boxes."),
    ("Label", "One LP class or one OOI class on an image. Clear is a label of its own."),
    ("Size flag", "A tag saying an object of its class is above the size threshold. A subset of the class."),
    ("Clear", "An image from the Clear folder with no marks. A label, and a negative class."),
    ("Unannotated", "An image with no marks outside the Clear folder. Excluded from label counts."),
    ("Single label", "Exactly one class on the image: one LP class, or one OOI class."),
    ("Matched boxes", "Boxes paired one-to-one between the two records of a duplicate pair."),
    ("Median IoU", "Median overlap of the matched boxes. 1.00 means identical."),
    ("Coordinate shift", "The largest movement of any box edge between the two records; the median is across matched boxes."),
    ("Pass, bubbles only", "No presentation tag, no size flag, and every box is Bubble or an untagged object of the four size-flagged classes."),
    ("Pass, extended", "The same, with Bubble Cluster and Wet Package also allowed."),
]
table(ws, 4, ["Term", "Meaning"], defs, widths=[26, 100])

for sh in wb.worksheets:
    if sh.row_breaks.brk:
        sh.row_breaks.brk.sort(key=lambda b: b.id)
    sh.sheet_view.showGridLines = False
    sh.page_setup.orientation = "landscape"
    sh.page_setup.fitToWidth = 1
    sh.page_setup.fitToHeight = 1 if sh.title in ("Summary", "Read me", "Duplicate sensitivity") else 0
    sh.sheet_properties.pageSetUpPr.fitToPage = True

wb.save(OUT)
print(OUT, OUT.stat().st_size)
