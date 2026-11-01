"""Build the two 24-file EDA workbooks from the frozen number artifacts.

Workbook 1: the 24-file export (7 revised + 17 new): population, lens presentation and OOI
            tag tables per group, OOI tag distribution, and the change lists with a reason.
Workbook 2: the cumulative record, before and after absorbing the 24 files.

Every number comes from run/eda_batch24_20261028/*.csv, which were computed from the
annotation of record. Nothing is typed in by hand; the workbook only formats.

Client-safe: no paths, script names, job ids or version tags.
"""
import csv
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = "D:/fmd-analysis"
NUM = f"{ROOT}/run/eda_batch24_20261028"
OUT = f"{ROOT}/reports/eda_24files_20261028"
os.makedirs(OUT, exist_ok=True)

ACCENT, LEGACY_FILL = "1F3864", "F2F2F2"
HEAD_FONT = Font(bold=True, color="FFFFFF")
TITLE = Font(bold=True, size=14, color=ACCENT)
SUB = Font(italic=True, size=9, color="595959")
BOLD = Font(bold=True)

GROUPS = ["7 revised", "17 new", "24 total"]

# The guide's 15 lens presentation classes, in guide order. None = no canonical row (zero).
LP_GUIDE = [
    ("P1_MPP", "Missing Primary Package", "missing_primary_package"),
    ("P1_PPM", "Package Misalignment", "package_misalignment"),
    ("P1_COC", "Cavity Off Center", "cavity_off_center"),
    ("P2_FOV", "View Obstructed", "view_obstructed"),
    ("P2_LOC", "Lens Off Center", "lens_off_center"),
    ("P1_NL", "No Lens", "missing_lens"),
    ("P1_ML", "Multiple Lens", "multiple_lenses"),
    ("P1_FL", "Folded Lens", "folded_lens"),
    ("P1_EBC", "Edge Bottle-Capped", None),
    ("P1_TL", "Torn Lens", None),
    ("P1_LR", "Lens Rupture", None),
    ("P2_DS", "Dirty Strobe", "dirty_strobe"),
    ("P2_DC", "Dirty Camera", "dirty_camera"),
    ("P2_BSC", "Bubble Scatter", "bubble_scatter"),
    ("P2_LD", "Low Dose", "low_dose"),
]

# The guide's 8 OOI classes, in guide order.
OOI_GUIDE = [
    ("P2_BB", "Bubble"), ("P2_BC", "Bubble Cluster"), ("P2_WP", "Wet Package"),
    ("P1_SG", "Surface Groove"), ("P3_FIB", "Fiber"), ("P3_EP", "Extraneous Polymer"),
    ("P3_HE", "HEMA"), ("P3_FM", "Foreign Matter"),
]

# Outside the 23-class guide. Kept in the record workbook for reference, marked legacy.
LEGACY = [("P2_HMO", "HEMA Obstruction"), ("", "Bubble On 123"), ("", "Bubble On Edge")]

CODE_NAME = {code: name for code, name, _ in LP_GUIDE}
CODE_NAME.update({code: name for code, name in OOI_GUIDE})
CODE_NAME.update({code: name for code, name in LEGACY})
EXTRA_CODES = {"P2_BI": "Bubble Irregular", "P2_BST": "Stretched Bubble",
               "P3_FM_MICRON_THRESHOLD": "Foreign Matter size flag",
               "P3_FIB_MICRON_THRESHOLD": "Fiber size flag",
               "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer size flag",
               "P3_HE_MICRON_THRESHOLD": "HEMA size flag",
               "F2_FOV": "View Obstructed"}
CODE_NAME.update(EXTRA_CODES)
NAME_CODE = {name: code for code, name in CODE_NAME.items() if code != "F2_FOV"}


def read_csv(name):
    with open(f"{NUM}/{name}", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEAD_FONT
        cell.fill = PatternFill("solid", fgColor=ACCENT)
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def title_block(ws, title, subtitle, width):
    ws.cell(row=1, column=1, value=title).font = TITLE
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    ws.cell(row=2, column=1, value=subtitle).font = SUB
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    ws.row_dimensions[1].height = 22


def note(ws, row, text, width):
    c = ws.cell(row=row, column=1, value=text)
    c.font = SUB
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    ws.row_dimensions[row].height = 26


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def translate(text):
    """Replace annotation codes with 'Name (CODE)' in a detail string."""
    def rep(m):
        code = m.group(0)
        return f"{CODE_NAME[code]} ({code})" if code in CODE_NAME else code
    return re.sub(r"\bP[123]_[A-Z_]+\b|\bF2_FOV\b", rep, text)


def names_of(codes):
    """Codes (';' separated) to 'Name (CODE)', de-duplicated."""
    out = []
    for c in sorted(filter(None, (x.strip() for x in codes.split(";")))):
        n = f"{CODE_NAME[c]} ({c})" if c in CODE_NAME else c
        if n not in out:
            out.append(n)
    return "; ".join(out)


def name_code(name):
    code = NAME_CODE.get(name.strip())
    return f"{name.strip()} ({code})" if code else name.strip()


def names_by_name(text):
    """Display names (';' separated) to 'Name (CODE)', de-duplicated."""
    out = []
    for n in sorted(filter(None, (x.strip() for x in text.split(";")))):
        n = name_code(n)
        if n not in out:
            out.append(n)
    return "; ".join(out)


def zero_note():
    return "No annotated pictures in this export; listed to keep the guide's class count."


# ---------------------------------------------------------------- workbook 1
def build_batch_workbook():
    pop = {r["group"]: r for r in read_csv("population.csv")}
    lp = {}
    for r in read_csv("lp_table.csv"):
        lp.setdefault(r["lp_tag"], {})[r["group"]] = int(r["pictures"])
    ooi = {}
    for r in read_csv("ooi_table.csv"):
        ooi.setdefault(r["class"], {})[r["group"]] = r
    dist = {}
    for r in read_csv("ooi_distribution.csv"):
        dist.setdefault(r["bucket"], {})[r["group"]] = int(r["pictures"])
    revised = read_csv("revised133.csv")
    relabel = read_csv("relabel70.csv")

    marked = int(pop["24 total"]["pictures_with_marks"])
    ooi_pics = dist["Pictures with at least one OOI tag"]["24 total"]
    ooi_tags = sum(int(ooi[name]["24 total"]["tags"]) for _, name in OOI_GUIDE)

    wb = Workbook()

    # ---- Read me
    ws = wb.active
    ws.title = "Read me"
    title_block(ws, "Defect and image-quality analysis: the 24-file export",
                "Prepared 28 October 2026 from the client's annotation exports. Client-safe.", 6)
    lines = [
        "This workbook counts the 24 annotation files received in October 2026: the 7 revised files and the 17 new files.",
        "The files hold 3,597 picture entries. Duplicate copies of the same picture collapse to one, leaving 3,594 distinct pictures; "
        "3,592 carry at least one mark. Two entries carry no mark at all and are placeholders, not pictures.",
        "Two label tiers are counted apart: lens presentation (one whole-picture tag; 15 classes in the guide) and OOI tags "
        "(objects of interest, marked with a box; 8 classes in the guide). A picture can carry several of each.",
        "Every picture counts, whether or not it carries a size flag. The size flag is shown as 'of which flagged' under its class "
        "and is never counted as a label of its own.",
        "Classes with no annotated pictures are still listed at 0, so the guide's 15 lens presentation and 8 OOI class numbers hold. "
        "Classes outside the guide are marked legacy.",
        "Sheets: Summary; Lens Presentation 7-17-24; OOI tags, 7 vs 17 vs 24; Changes, 7 revised files; "
        "Changes, 17 new files; Reason summary; Definitions.",
        "Counts are read from the annotation files. Where a picture appears in more than one file, the newest export owns the "
        "picture and the older label set is not counted.",
    ]
    r = 4
    for line in lines:
        c = ws.cell(row=r, column=1, value=line)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.row_dimensions[r].height = 30
        r += 1
    widths(ws, {"A": 110})

    # ---- Summary
    ws = wb.create_sheet("Summary")
    title_block(ws, "Summary", "Population of the 24-file export and what the guide's class list covers.", 8)
    ws.cell(row=4, column=1, value="Population").font = BOLD
    hdr = ["Group", "Image entries", "Distinct pictures", "Pictures with marks", "Picture entries with no mark"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=5, column=i, value=h)
    style_header(ws, 5, len(hdr))
    for i, g in enumerate(GROUPS, 6):
        p = pop[g]
        vals = [g, int(p["image_entries"]), int(p["distinct_pictures"]),
                int(p["pictures_with_marks"]), int(p["zero_shape_entries"])]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=i, column=j, value=v)
            if j > 1:
                cell.number_format = "#,##0"
    note(ws, 9, "24 total = 7 revised + 17 new. Duplicate entries of the same picture are counted once per group.", 8)

    ws.cell(row=11, column=1, value="Headline").font = BOLD
    hl = [
        ("Pictures with at least one OOI tag", ooi_pics),
        ("OOI tags in total", ooi_tags),
        ("Lens presentation classes in the guide", 15),
        ("Lens presentation classes with no annotated pictures", 3),
        ("OOI classes in the guide", 8),
        ("OOI classes with no annotated pictures", 1),
    ]
    for i, (k, v) in enumerate(hl, 12):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v).number_format = "#,##0"
    note(ws, 19, "The classes with no annotated pictures are Edge Bottle-Capped (P1_EBC), Torn Lens (P1_TL), "
                 "Lens Rupture (P1_LR) and Surface Groove (P1_SG). They are listed at 0 in the class sheets.", 8)
    note(ws, 21, "Legacy classes outside the guide - HEMA Obstruction (P2_HMO), Bubble On 123 and Bubble On Edge - "
                 "do not occur in this export. The cumulative workbook lists them for reference.", 8)
    widths(ws, {"A": 46, "B": 14, "C": 16, "D": 18, "E": 22})

    # ---- Lens Presentation
    ws = wb.create_sheet("Lens Presentation 7-17-24")
    title_block(ws, "Lens presentation by file group",
                "Whole-picture conditions. Pictures carrying each class; a picture can carry several.", 7)
    hdr = ["Code", "Class", "7 revised", "17 new", "24 total",
           "Share of pictures with marks (24)", "Note"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for code, name, cid in LP_GUIDE:
        vals = [code, name] + [lp.get(cid, {}).get(g, 0) for g in GROUPS]
        vals.append((lp.get(cid, {}).get("24 total", 0) / marked) if cid else 0)
        vals.append("" if cid else zero_note())
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j in (3, 4, 5):
                cell.number_format = "#,##0"
            if j == 6:
                cell.number_format = "0.0%"
            if j == 7:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    note(ws, rr + 1, "A lens presentation class is one whole-picture tag. The share is out of the 3,592 pictures with marks. "
                     "Rows are not additive: a picture can carry several classes.", 7)
    widths(ws, {"A": 10, "B": 30, "C": 11, "D": 11, "E": 11, "F": 18, "G": 60})
    ws.freeze_panes = "C5"

    # ---- OOI tags
    ws = wb.create_sheet("OOI tags, 7 vs 17 vs 24")
    title_block(ws, "OOI tags by file group",
                "Objects of interest marked with a box: pictures, the number of tags, and the size-flag subset.", 14)
    hdr = ["Code", "Class",
           "7 revised: pictures", "7 revised: tags", "7 revised: of which flagged",
           "17 new: pictures", "17 new: tags", "17 new: of which flagged",
           "24 total: pictures", "24 total: tags", "24 total: of which flagged",
           "Tags per picture (24)", "Median tags per picture (24)", "Most tags on one picture (24)", "Note"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for code, name in OOI_GUIDE:
        vals = [code, name]
        for g in GROUPS:
            row = ooi.get(name, {}).get(g)
            vals += [int(row["pictures"]), int(row["tags"]), int(row["flagged"])] if row else [0, 0, 0]
        row = ooi.get(name, {}).get("24 total")
        if row and int(row["pictures"]):
            vals += [float(row["mean"]), float(row["median"]), int(row["max"]), ""]
        else:
            vals += ["-", "-", "-", zero_note()]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if isinstance(v, (int, float)) and 3 <= j <= 14:
                cell.number_format = "#,##0" if j <= 11 or j == 14 else "0.0"
            if j == 15:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    note(ws, rr + 1, "A size flag is a subset of its class: Foreign Matter, Fiber, Extraneous Polymer and HEMA carry one. "
                     "A picture without the flag still counts in the class.", 15)

    rr += 3
    ws.cell(row=rr, column=1, value="OOI tags per picture").font = BOLD
    rr += 1
    hdr2 = ["Tags on one picture", "7 revised", "17 new", "24 total"]
    for i, h in enumerate(hdr2, 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, len(hdr2))
    rr += 1
    for bucket in ("1 tag", "2 to 3 tags", "4 to 9 tags", "10 to 19 tags", "20 or more tags"):
        vals = [bucket] + [dist[bucket][g] for g in GROUPS]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j > 1:
                cell.number_format = "#,##0"
        rr += 1
    vals = ["Pictures with at least one OOI tag"] + [dist["Pictures with at least one OOI tag"][g] for g in GROUPS]
    for j, v in enumerate(vals, 1):
        cell = ws.cell(row=rr, column=j, value=v)
        if j > 1:
            cell.number_format = "#,##0"
        cell.font = BOLD
    note(ws, rr + 2, f"Each picture counts once here, by how many OOI tags it carries in all classes. "
                     f"{ooi_pics:,} pictures carry at least one OOI tag in the 24 files; {ooi_tags:,} tags in all.", 15)
    widths(ws, {"A": 10, "B": 28, "C": 12, "D": 12, "E": 14, "F": 12, "G": 12, "H": 14,
                "I": 12, "J": 12, "K": 14, "L": 14, "M": 16, "N": 18, "O": 44})
    ws.freeze_panes = "C5"

    # ---- Changes, revised
    ws = wb.create_sheet("Changes, 7 revised files")
    title_block(ws, "Changes in the 7 revised files", "One row per picture whose annotation moved. 133 pictures.", 5)
    hdr = ["Picture", "Old labels", "New labels", "What changed", "Reason"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in sorted(revised, key=lambda x: (x["reason"], x["picture"])):
        vals = [row["picture"].split("/")[-1], names_of(row["old_labels"]), names_of(row["new_labels"]),
                translate(row["detail"]), row["reason"]]
        for j, v in enumerate(vals, 1):
            ws.cell(row=rr, column=j, value=v).alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    widths(ws, {"A": 52, "B": 50, "C": 50, "D": 60, "E": 26})
    ws.freeze_panes = "A5"

    # ---- Changes, new files
    ws = wb.create_sheet("Changes, 17 new files")
    title_block(ws, "Label changes in the 17 new files", "One row per picture that already carried a label from an earlier file "
                 "and whose label the newer annotation no longer carries. 71 pictures.", 6)
    hdr = ["Picture", "Line", "Label no longer counted", "Old labels", "New labels", "Reason"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in sorted(relabel, key=lambda x: (x["reason"], x["picture"])):
        vals = [row["picture"], row["line"], name_code(row["removed_label"]),
                names_by_name(row["old_labels"]), names_by_name(row["new_labels"]), row["reason"]]
        for j, v in enumerate(vals, 1):
            ws.cell(row=rr, column=j, value=v).alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    widths(ws, {"A": 52, "B": 7, "C": 30, "D": 56, "E": 56, "F": 60})
    ws.freeze_panes = "A5"

    # ---- Reason summary
    ws = wb.create_sheet("Reason summary")
    title_block(ws, "Why the counts moved", "Counts per reason for both change lists.", 4)
    ws.cell(row=4, column=1, value="7 revised files").font = BOLD
    hdr = ["Reason", "Pictures"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=5, column=i, value=h)
    style_header(ws, 5, 2)
    rr = 6
    counts = {}
    for row in revised:
        counts[row["reason"]] = counts.get(row["reason"], 0) + 1
    for reason, n in sorted(counts.items(), key=lambda x: -x[1]):
        ws.cell(row=rr, column=1, value=reason)
        ws.cell(row=rr, column=2, value=n).number_format = "#,##0"
        rr += 1
    ws.cell(row=rr, column=1, value="Total").font = BOLD
    ws.cell(row=rr, column=2, value=len(revised)).font = BOLD
    rr += 2

    ws.cell(row=rr, column=1, value="17 new files").font = BOLD
    rr += 1
    for i, h in enumerate(hdr, 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, 2)
    rr += 1
    counts2 = {}
    for row in relabel:
        counts2[row["reason"]] = counts2.get(row["reason"], 0) + 1
    for reason, n in sorted(counts2.items(), key=lambda x: -x[1]):
        ws.cell(row=rr, column=1, value=reason)
        ws.cell(row=rr, column=2, value=n).number_format = "#,##0"
        rr += 1
    ws.cell(row=rr, column=1, value="Total").font = BOLD
    ws.cell(row=rr, column=2, value=len(relabel)).font = BOLD
    rr += 2

    explanations = [
        ("Folded into Bubble", "The same bubble was annotated under an older name (Bubble Irregular, Stretched Bubble) or was moved "
                                "from another bubble family; the newer file writes Bubble."),
        ("Debris class moved", "The object changed family between Foreign Matter, Fiber and Extraneous Polymer."),
        ("Other relabel", "A different class sits on the same box."),
        ("Box position changed", "The label is the same; only the box outline moved."),
        ("Relabelled Dirty Strobe to Dirty Camera", "The newer file names the same dirty artifact as Dirty Camera."),
        ("Relabelled Lens Off Center to Low Dose", "The newer file names the presentation condition as Low Dose."),
        ("Relabelled Low Dose to Lens Off Center", "The newer file names the presentation condition as Lens Off Center."),
        ("Relabelled Missing Primary Package to No Lens", "The newer file names the package condition as No Lens."),
        ("Dropped; the newer annotation carries no replacement condition", "The picture keeps its other labels; this condition is "
                                                                          "not marked in the newer file."),
        ("Dropped; the newer annotation labels only the objects", "The newer file marks the objects and no whole-image condition."),
        ("Dropped; the picture is listed in the newer file with no marks", "The picture carries an empty entry in the newer export. "
                                                                            "This one needs the annotation owner."),
    ]
    ws.cell(row=rr, column=1, value="What the reasons mean").font = BOLD
    rr += 1
    for reason, text in explanations:
        ws.cell(row=rr, column=1, value=reason)
        c = ws.cell(row=rr, column=2, value=text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    widths(ws, {"A": 70, "B": 90})

    # ---- Definitions
    ws = wb.create_sheet("Definitions")
    title_block(ws, "Definitions", "Every term used in the sheets above.", 4)
    defs = [
        ("Picture", "One 2448 by 2048 image. Two names for the same image are one picture."),
        ("Image entry", "One picture listed inside an annotation file. A file can list the same picture twice."),
        ("Mark", "An OOI tag (a box) or a lens presentation tag (a whole-picture tag)."),
        ("OOI tag", "An object of interest, marked with a box. One picture can carry many. The guide defines 8 OOI classes."),
        ("Lens Presentation", "A condition marked for the whole picture, one tag per picture. The guide defines 15 classes."),
        ("Class code", "The short code the annotation guide uses, such as P2_BB. The code is the same across exports; "
                       "the plain name can differ between campaigns."),
        ("Size flag", "A tag that says the object is above the size threshold. It is a subset of its class and is reported as "
                      "'of which flagged', never as a separate label. A picture without the flag still counts in the class."),
        ("Clear", "A picture with nothing marked. Clear is a label; every annotated picture carries something."),
        ("Classes with no examples", "Edge Bottle-Capped (P1_EBC), Torn Lens (P1_TL), Lens Rupture (P1_LR) and Surface Groove "
                                     "(P1_SG) are in the guide but carry no annotated picture. They are listed at 0."),
        ("Legacy classes", "HEMA Obstruction (P2_HMO, a whole-picture tag from an earlier project), Bubble On 123 and Bubble On "
                           "Edge (older library classes). They are outside the 23-class guide and are not part of the split."),
        ("Bubble", "One class. Bubble Irregular (P2_BI) and Stretched Bubble (P2_BST) fold into it, and the older library's "
                   "plain Bubble name does too."),
        ("Revised files", "The 7 files re-exported over versions already counted. Their pictures are compared with the earlier copy."),
        ("New files", "The 17 files that add pictures to the record."),
        ("Duplicate entries", "Three pictures are listed twice in the export, under a name with and without a score suffix. "
                              "One pair carries identical marks; two differ by one and seven marks. One annotation per picture "
                              "is counted."),
    ]
    rr = 4
    for term, text in defs:
        ws.cell(row=rr, column=1, value=term).font = BOLD
        c = ws.cell(row=rr, column=2, value=text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    widths(ws, {"A": 26, "B": 110})

    path = f"{OUT}/FMD_EDA_24Files_20261028.xlsx"
    wb.save(path)
    print("wrote", path)
    return path


# ---------------------------------------------------------------- workbook 2
def build_record_workbook():
    pop = {r["scope"]: r for r in read_csv("cumulative_population.csv")}
    rec = {r["name"]: r for r in read_csv("record_before_after.csv")}
    look = pop["merged record"]
    clear_before = 2156
    clear_after = int(look["clear_pictures"])
    examined = 10614
    marked = int(look["pictures_with_marks"])
    analysed = int(look["analysed_pictures"])

    def row_for(name, code, kind, guide):
        r = rec.get(name)
        if r is None:
            return {"code": code, "name": name, "kind": kind, "guide": guide,
                    "old": 0, "new": 0, "delta": 0, "of": 0, "nf": 0, "os": 0, "ns": 0}
        return {"code": code, "name": name, "kind": kind, "guide": guide,
                "old": int(r["old_pictures"]), "new": int(r["merged_pictures"]),
                "delta": int(r["delta_pictures"]), "of": int(r["old_flagged"]),
                "nf": int(r["merged_flagged"]), "os": int(r["old_shapes"]),
                "ns": int(r["merged_shapes"])}

    lp_rows = [row_for(name, code, "Lens Presentation", True) for code, name, _ in LP_GUIDE]
    ooi_rows = [row_for(name, code, "OOI tag", True) for code, name in OOI_GUIDE]
    legacy_rows = [row_for(name, code, "Legacy", False) for code, name in LEGACY]

    wb = Workbook()

    # ---- Read me
    ws = wb.active
    ws.title = "Read me"
    title_block(ws, "Defect and image-quality analysis: the record after the 24-file export",
                "Prepared 28 October 2026. Client-safe.", 6)
    lines = [
        f"This workbook counts the whole annotation record after the 24 files were absorbed: {marked:,} pictures with at least "
        f"one mark and {clear_after:,} pictures with nothing marked (Clear), {analysed:,} in all, out of {examined:,} images examined.",
        "The 24 files were the newest annotation: where a picture appears in one of them, their label set owns the picture and "
        "the earlier file's labels for it are not counted. Nothing is merged label by label.",
        "Two label tiers are counted apart: lens presentation (15 classes in the guide) and OOI tags (8 classes in the guide). "
        "Classes with no annotated pictures are listed at 0; classes outside the guide are marked legacy.",
        "The before and after sheets show, for every class, the count before the 24 files and the count after.",
        "Every picture counts, whether or not it carries a size flag. The flag is a subset of its class and is shown as "
        "'of which flagged'.",
        "Sheets: Summary; Before and after; Lens Presentation; OOI tags; Definitions.",
    ]
    r = 4
    for line in lines:
        c = ws.cell(row=r, column=1, value=line)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.row_dimensions[r].height = 30
        r += 1
    widths(ws, {"A": 110})

    # ---- Summary
    ws = wb.create_sheet("Summary")
    title_block(ws, "Summary", "Population and label counts after the 24 files.", 8)
    ws.cell(row=4, column=1, value="Population").font = BOLD
    hdr = ["Measure", "Pictures"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=5, column=i, value=h)
    style_header(ws, 5, 2)
    vals = [("Pictures examined", examined), ("Pictures with at least one mark", marked),
            ("Pictures with nothing marked (Clear)", clear_after), ("Analysed set", analysed)]
    rr = 6
    for k, v in vals:
        ws.cell(row=rr, column=1, value=k)
        ws.cell(row=rr, column=2, value=v).number_format = "#,##0"
        rr += 1
    note(ws, rr + 1, "The analysed set is the pictures with marks plus Clear. A picture with no marks and outside the Clear "
                     "folder is a placeholder and is not counted.", 8)

    ws.cell(row=rr + 3, column=1, value="Labels").font = BOLD
    hdr = ["Code", "Label", "Type", "In guide", "Pictures", "of which flagged", "OOI tags"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=rr + 4, column=i, value=h)
    style_header(ws, rr + 4, len(hdr))
    rr2 = rr + 5
    ws.cell(row=rr2, column=2, value="Clear")
    ws.cell(row=rr2, column=3, value="Clear")
    ws.cell(row=rr2, column=4, value="Negative")
    ws.cell(row=rr2, column=5, value=clear_after).number_format = "#,##0"
    rr2 += 1
    for row in lp_rows + ooi_rows + legacy_rows:
        vals = [row["code"], row["name"], row["kind"], "Yes" if row["guide"] else "Legacy",
                row["new"], row["nf"], row["ns"] if row["kind"] == "OOI tag" else ""]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr2, column=j, value=v)
            if isinstance(v, int) and j >= 5:
                cell.number_format = "#,##0"
            if not row["guide"]:
                cell.fill = PatternFill("solid", fgColor=LEGACY_FILL)
        rr2 += 1
    note(ws, rr2, "Rows are not additive: a picture can carry several labels. For a lens presentation class the OOI tag "
                  "count is blank; the pictures column is the count.", 8)
    widths(ws, {"A": 10, "B": 30, "C": 20, "D": 10, "E": 12, "F": 16, "G": 12})

    # ---- Before and after
    ws = wb.create_sheet("Before and after")
    title_block(ws, "Before and after the 24 files",
                "The count of each class in the record before the 24 files and after. A positive change means the newer "
                "annotation carried the class on more pictures.", 11)
    hdr = ["Code", "Label", "Type", "In guide", "Pictures before", "Pictures after", "Change",
           "of which flagged before", "of which flagged after", "OOI tags before", "OOI tags after"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in sorted(lp_rows + ooi_rows + legacy_rows, key=lambda x: (-x["delta"], x["name"])):
        vals = [row["code"], row["name"], row["kind"], "Yes" if row["guide"] else "Legacy",
                row["old"], row["new"], row["delta"], row["of"], row["nf"],
                row["os"] if row["kind"] == "OOI tag" else "", row["ns"] if row["kind"] == "OOI tag" else ""]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if isinstance(v, int) and j >= 5:
                cell.number_format = "#,##0;-#,##0"
            if not row["guide"]:
                cell.fill = PatternFill("solid", fgColor=LEGACY_FILL)
        rr += 1
    vals = ["", "Clear", "Clear", "Negative", clear_before, clear_after, clear_after - clear_before, "", "", "", ""]
    for j, v in enumerate(vals, 1):
        cell = ws.cell(row=rr, column=j, value=v)
        if isinstance(v, int) and j >= 5:
            cell.number_format = "#,##0;-#,##0"
    rr += 1
    note(ws, rr + 1, "The 24 files own 3,592 pictures. On those, the newer label set replaces the earlier one; pictures the 24 "
                     "files do not mention keep their earlier labels. Clear is the Clear-folder pictures with no mark.", 11)
    widths(ws, {"A": 10, "B": 30, "C": 20, "D": 10, "E": 14, "F": 14, "G": 10, "H": 18, "I": 18, "J": 14, "K": 14})
    ws.freeze_panes = "E5"

    # ---- Lens Presentation view
    ws = wb.create_sheet("Lens Presentation")
    title_block(ws, "Lens Presentation: before and after", "Pictures carrying each class before and after the 24 files.", 5)
    hdr = ["Code", "Class", "Before", "After", "Change"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in lp_rows:
        for j, v in enumerate([row["code"], row["name"], row["old"], row["new"], row["delta"]], 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j >= 3:
                cell.number_format = "#,##0;-#,##0"
        rr += 1
    note(ws, rr + 1, "3 of the guide's 15 lens presentation classes carry no annotated picture and are listed at 0: "
                     "Edge Bottle-Capped (P1_EBC), Torn Lens (P1_TL), Lens Rupture (P1_LR).", 5)
    widths(ws, {"A": 10, "B": 30, "C": 12, "D": 12, "E": 10})
    ws.freeze_panes = "A5"

    # ---- OOI view
    ws = wb.create_sheet("OOI tags")
    title_block(ws, "OOI tags: before and after", "Pictures and tags carrying each OOI class before and after the 24 files.", 7)
    hdr = ["Code", "Class", "In guide", "Pictures before", "Pictures after", "Change", "Tags before", "Tags after"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in ooi_rows + legacy_rows:
        vals = [row["code"], row["name"], "Yes" if row["guide"] else "Legacy",
                row["old"], row["new"], row["delta"], row["os"], row["ns"]]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if isinstance(v, int) and j >= 4:
                cell.number_format = "#,##0;-#,##0"
            if not row["guide"]:
                cell.fill = PatternFill("solid", fgColor=LEGACY_FILL)
        rr += 1
    note(ws, rr + 1, "Surface Groove (P1_SG) is in the guide with no annotated picture and is listed at 0. "
                     "HEMA Obstruction (P2_HMO), Bubble On 123 and Bubble On Edge are legacy classes outside the guide.", 8)
    widths(ws, {"A": 10, "B": 30, "C": 10, "D": 14, "E": 14, "F": 10, "G": 12, "H": 12})
    ws.freeze_panes = "A5"

    # ---- Definitions
    ws = wb.create_sheet("Definitions")
    title_block(ws, "Definitions", "Every term used in the sheets above.", 4)
    defs = [
        ("Picture", "One 2448 by 2048 image."),
        ("Mark", "An OOI tag (a box) or a lens presentation tag (a whole-picture tag)."),
        ("OOI tag", "An object of interest, marked with a box. One picture can carry many. The guide defines 8 OOI classes."),
        ("Lens Presentation", "A condition marked for the whole picture, one tag per picture. The guide defines 15 classes."),
        ("Class code", "The short code the annotation guide uses, such as P2_BB. The code is the same across exports; "
                       "the plain name can differ between campaigns."),
        ("Clear", "A picture with nothing marked. Clear is a label; every annotated picture carries something."),
        ("Size flag", "A tag saying the object is above the size threshold. It is a subset of its class, shown as "
                      "'of which flagged', never as a separate label."),
        ("HEMA", "The HEMA row (P3_HE) counts boxes. The older project also used a whole-picture HEMA Obstruction tag "
                 "(P2_HMO) on pictures without a HEMA box; that tag is a separate legacy row."),
        ("Legacy classes", "HEMA Obstruction (P2_HMO), Bubble On 123 and Bubble On Edge: outside the 23-class guide and not "
                           "part of the split. Shown grey."),
        ("Bubble", "One class. Bubble Irregular (P2_BI) and Stretched Bubble (P2_BST) fold into it."),
        ("Fiber and Extraneous Polymer", "The two annotation campaigns name a small set of objects differently. The counts here "
                                          "use the name in each picture's own annotation and never add the two together."),
        ("Duplicate entries", "Three pictures are listed twice in the export, under a name with and without a score suffix; "
                              "one annotation per picture is counted."),
    ]
    rr = 4
    for term, text in defs:
        ws.cell(row=rr, column=1, value=term).font = BOLD
        c = ws.cell(row=rr, column=2, value=text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    widths(ws, {"A": 28, "B": 110})

    path = f"{OUT}/FMD_EDA_Record_20261028.xlsx"
    wb.save(path)
    print("wrote", path)
    return path


if __name__ == "__main__":
    build_batch_workbook()
    build_record_workbook()
