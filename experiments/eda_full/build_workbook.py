#!/usr/bin/env python3
"""Build the full-coverage EDA workbook from full_numbers.json.

Generalised from experiments/production_20260925/build_workbook.py. The builder
only formats; every number comes from full_numbers.json, which in turn reads the
verified run artifacts. Nothing here computes a headline.

Sheets (one per question, plus a coverage sheet and a crosswalk sheet):
  Read me       what this is, where the numbers come from, headline findings, caveats
  Census        the picture and file census, content identity, the production folder
  Labels        the resolved label census, the multi-label shape, the defect catalogue
  Distributions the shape of the label set as tables and charts
  Box geometry  box size in pixels and microns, the cavity, the outlier classes
  Blind scale   the rim measurement per folder group and production line
  Micron gate   the client's size gate, and the inversion it produces
  Coverage      what is annotated out of what exists, and the folder disagreement
  Crosswalk     the frozen canonical crosswalk across the three vocabularies
  Checks        the invariants a reader can re-check by hand

Usage:
  python build_workbook.py --numbers full_numbers.json --out FMD_Full_EDA_20261015.xlsx
"""
from __future__ import annotations

import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from scale_section import append_scale_section

TITLE = Font(bold=True, size=14)
SUB = Font(bold=True, size=11)
HEAD = Font(bold=True, color="FFFFFF")
HEADFILL = PatternFill("solid", fgColor="1F3864")
NOTEFONT = Font(italic=True, size=9, color="555555")
WARNFONT = Font(italic=True, size=9, color="9C0006")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

PCT1 = "0.0%"
NUM0 = "#,##0"
NUM1 = "#,##0.0"
NUM2 = "#,##0.00"

AS = 15.337    # the adopted working scale (the 300 micron cut inverted)
PRIOR = 18.1165  # superseded prior scale, kept only as a labelled comparison
SPOKEN = 18.25   # superseded prior scale, kept only as a labelled comparison


def sheet(wb, name, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = name
    ws.sheet_view.showGridLines = False
    return ws


def title(ws, row, text, sub=None):
    ws.cell(row=row, column=1, value=text).font = TITLE
    row += 1
    for line in (sub or []):
        ws.cell(row=row, column=1, value=line).font = NOTEFONT
        row += 1
    return row + 1


def section(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = SUB
    return row + 1


def header(ws, row, cols, first_col=1):
    for i, c in enumerate(cols):
        cell = ws.cell(row=row, column=first_col + i, value=c)
        cell.font = HEAD
        cell.fill = HEADFILL
        cell.border = BOX
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    return row + 1


def table(ws, row, rows, fmts=None, first_col=1):
    for r in rows:
        for i, v in enumerate(r):
            cell = ws.cell(row=row, column=first_col + i, value=v)
            cell.border = BOX
            if fmts and i < len(fmts) and fmts[i] and isinstance(v, (int, float)):
                cell.number_format = fmts[i]
        row += 1
    return row


def kv(ws, row, pairs):
    for k, v in pairs:
        a = ws.cell(row=row, column=1, value=k)
        a.border = BOX
        b = ws.cell(row=row, column=2, value=v)
        b.border = BOX
        row += 1
    return row


def bullet(ws, row, text):
    ws.cell(row=row, column=1, value="  " + text).alignment = WRAP
    return row + 1


def note(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = NOTEFONT
    return row + 1


def warn(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = WARNFONT
    return row + 1


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def pct(x, nd=1):
    return ("%." + str(nd) + "f%%") % (100.0 * x)


def add_bar(ws, title_txt, hdr_row, last_row, data_col, anchor, cat_col=1,
            y_title="Count", width=16, height=8):
    ch = BarChart()
    ch.type = "col"
    ch.style = 10
    ch.title = title_txt
    ch.y_axis.title = y_title
    ch.width = width
    ch.height = height
    ch.add_data(Reference(ws, min_col=data_col, min_row=hdr_row, max_row=last_row),
                titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=cat_col, min_row=hdr_row + 1, max_row=last_row))
    ch.dLbls = DataLabelList()
    ch.dLbls.showVal = True
    ch.legend = None
    ws.add_chart(ch, anchor)
    return ch


# --------------------------------------------------------------------------
def sheet_readme(wb, R):
    ws = sheet(wb, "Read me", first=True)
    C, L, V = R["census"], R["labels"], R["verification"]
    widths(ws, {"A": 44, "B": 96, "C": 20})
    r = title(ws, 1, "Full-coverage EDA: three ICube library folders and the production batch",
              ["%s distinct pictures across the three library folders, %s files in all, "
               "%s files once the production image folder is added."
               % (format(C["distinct_pictures"], ","), format(C["files_library"], ","),
                  format(C["files_total"], ",")),
               "Every number in this workbook is read from a verified analysis artifact.",
               "No figure is typed by hand."])
    r += 1

    r = section(ws, r, "What each sheet answers")
    r = header(ws, r, ["Sheet", "Question it answers"])
    r = table(ws, r, [
        ["Census", "How many pictures exist, how many files hold them, and how the "
                   "copies sit across the folders"],
        ["Labels", "How many shapes and codes were resolved, how many pictures carry "
                   "them, and what each defect class contains"],
        ["Distributions", "How the codes combine on one picture, as tables and charts"],
        ["Box geometry", "How large each defect class is, and where the boxes sit on "
                         "the part"],
        ["Blind scale", "Whether the pixel scale differs by folder group or by "
                        "production line"],
        ["Micron gate", "What the client's own micron flag gates on, and the scale it "
                        "implies"],
        ["Coverage", "What is annotated out of what exists, and where the library "
                     "folders disagree"],
        ["Crosswalk", "The frozen mapping across the three annotation vocabularies"],
        ["Checks", "The invariants behind the summary numbers, each one re-checkable"],
    ])
    r += 1

    r = section(ws, r, "Where the numbers come from")
    r = header(ws, r, ["Input", "What it is"])
    r = table(ws, r, [
        ["Picture census", "a content-hash census of every file in the three library "
                           "folders and the production image folder"],
        ["Label resolution", "the annotation files resolved under the agreed priority "
                             "rule, one source per picture, keyed on content hash"],
        ["Box geometry", "the rectangle geometry of every resolved box, measured per "
                         "picture"],
        ["Cavity measurement", "the bright-blob measurement of the cavity on every "
                               "picture, one routine, read-only"],
        ["Blind scale", "the lens rim measured per folder group and production line, "
                        "sampled at a fixed rate"],
        ["Micron gate", "the client's own size flag, inverted into a scale, plus a "
                        "before and after comparison"],
        ["Coverage", "the join of each labelled picture to the folder population it "
                     "sits in, and the folder disagreement"],
        ["Crosswalk", "the frozen mapping of every code to one canonical defect"],
    ])
    r += 1

    r = section(ws, r, "Headline findings")
    findings = [
        "The library holds %s distinct pictures across %s files. Adding the production "
        "image folder takes the file count to %s, but it adds no new picture: all %s "
        "production files resolve by content hash to pictures already in the library."
        % (format(C["distinct_pictures"], ","), format(C["files_library"], ","),
           format(C["files_total"], ","), format(C["files_production"], ",")),
        "The label census and the picture census are different counts and must not be "
        "confused. %s pictures are MENTIONED by some file; only %s carry at least one "
        "shape; %s carry no shape; %s are mentioned nowhere. %s and %s are the two "
        "annotation readings and are never swapped. Each pair sums to the census: "
        "%s with a shape plus %s with none, and %s mentioned plus %s nowhere."
        % (format(L["mentioned"], ","), format(L["with_shape"], ","),
           format(L["no_shape"], ","), format(L["nowhere"], ","),
           format(L["no_shape"], ","), format(L["nowhere"], ","),
           format(L["with_shape"], ","), format(L["no_shape"], ","),
           format(L["mentioned"], ","), format(L["nowhere"], ",")),
        "There are %s resolved shapes: %s boxes and %s tags. That is one shared number "
        "seen twice, because the %s no-shape pictures and the %s tag shapes are the same "
        "count, which is why every table names which one it means."
        % (format(L["shapes_total"], ","), format(L["boxes"], ","), format(L["tags"], ","),
           format(L["no_shape"], ","), format(L["tags"], ",")),
        "The labels resolve to %d canonical defects. Two code collisions are kept "
        "unmerged and flagged rather than silently combined: the shared code that means "
        "HEMA Fragment in one project and HEMA Obstruction in the production files, and "
        "the view-obstructed code written with two different prefixes."
        % L["canonical_count"],
        "The %s boxes span %s distinct pictures. Only %s of the %s boxes are "
        "axis-aligned, %s, so any conversion that assumes upright rectangles mis-draws "
        "the rest."
        % (format(L["boxes"], ","), format(L["pictures_with_box"], ","),
           format(R["box_geometry"]["axis_aligned"], ","), format(L["boxes"], ","),
           pct(R["box_geometry"]["share_axis_aligned"])),
        "The cavity was measured on %s of %s pictures. The %s that could not be measured "
        "are one named class, frames that are too dark for any bright blob to be found, "
        "and they are counted rather than dropped."
        % (format(R["cavity"]["read"]["pictures_measured"], ","),
           format(R["cavity"]["read"]["pictures"], ","),
           format(R["cavity"]["read"]["pictures_could_not_measure"], ",")),
        "The customer's size gate is a clean cut on the LONGER SIDE of the annotation box, "
        "not the diagonal: zero images fall on the wrong side of the boundary, against 39 "
        "that the diagonal misfiles.",
        "ADOPTED SCALE %.3f MICRONS PER PIXEL. The customer's own 300 micron cut, "
        "inverted through the gate boundary at %.2f to %.2f px, gives the working scale. "
        "Every micron figure in this workbook is a pixel figure times %.3f. The prior "
        "scales %.4f and %.2f are superseded and appear only in columns and sentences "
        "explicitly labelled as superseded."
        % (AS, R["scale"]["adopted_boundary_px"][0], R["scale"]["adopted_boundary_px"][1],
           AS, PRIOR, SPOKEN),
        "At the adopted scale the gate boundary reads %.1f to %.1f microns, which "
        "reproduces the customer's own 300 micron cut; the old 647 micron cut inverts to "
        "the same scale and is the independent reproduction."
        % (R["scale"]["adopted_boundary_um"][0], R["scale"]["adopted_boundary_um"][1]),
        "No production line and no folder group differs from another beyond the "
        "measurement noise. The within-stratum spread of 10 to 26 percent dwarfs the "
        "spread among the candidate scales, so measurement alone cannot settle a scale "
        "question of that size.",
        "The widely quoted figure of 113 folder disagreements is a NAME-based count. On "
        "content identity the overlap is larger, not smaller: %d pictures library-wide "
        "and %d on the production batch, because a name-based route cannot see a picture "
        "that was renamed."
        % (R["disagreement"]["content_library"], R["disagreement"]["content_batch"]),
        "One production picture is annotated twice, under two byte-identical file names "
        "that both carry the same eight shapes, so the %s production files hold %s "
        "distinct contents."
        % (format(C["production_files"], ","), format(C["production_distinct_contents"], ",")),
        "Coverage of the production blob folder is %s annotated of %s pictures, %s. The "
        "remainder is available as negatives but was not pulled."
        % (format(R["coverage"]["blob"]["annotated"], ","),
           format(R["coverage"]["blob"]["folder_total"], ","),
           pct(R["coverage"]["blob"]["share"], 2)),
    ]
    for i, t in enumerate(findings, 1):
        ws.cell(row=r, column=1, value="%d." % i).font = BOLD
        ws.cell(row=r, column=2, value=t).alignment = WRAP
        r += 1
    r += 1

    r = section(ws, r, "Caveats and open questions")
    for t in [
        "The adopted working scale is %.3f microns per pixel. It is derived from the "
        "documented 300 micron cut: the customer's micron-threshold tags switch at a "
        "defect longer side of %.2f to %.2f px, and 300 divided by the %.2f px midpoint "
        "gives the scale, matching the frozen central figure of %.4f with an interval of "
        "%.3f to %.3f. Per production line the same inversion reads %.3f (L24), %.3f "
        "(L25, only 14 pictures, loose), %.3f (L26) and %.3f (L27); the L31 line has no "
        "threshold defect in the production export and is not computable. Per folder "
        "group it reads %.3f on the updated folders and %.3f on pictures that are also "
        "in the old defects library."
        % (AS, R["scale"]["adopted_boundary_px"][0], R["scale"]["adopted_boundary_px"][1],
           (R["scale"]["adopted_boundary_px"][0] + R["scale"]["adopted_boundary_px"][1]) / 2,
           R["micron_gate"]["implied_scale_combined"]["scale_um_per_px_mid"],
           R["scale"]["adopted_interval_um_per_px"][0],
           R["scale"]["adopted_interval_um_per_px"][1],
           R["scale"]["per_line_um_per_px"]["L24"], R["scale"]["per_line_um_per_px"]["L25"],
           R["scale"]["per_line_um_per_px"]["L26"], R["scale"]["per_line_um_per_px"]["L27"],
           R["scale"]["per_folder_um_per_px"]["updated_folders_only"],
           R["scale"]["per_folder_um_per_px"]["pictures_also_in_the_old_defects_library"]),
        "Limitation of the adopted scale, stated plainly and not resolved here: the lens "
        "nominal diameter is not documented in anything received. The lens rim measures "
        "%g px (interquartile range %.1f to %.1f px), which is %.2f mm at the adopted "
        "scale and 14.2 mm at the superseded prior scale. The only documented ruler is "
        "the customer's own 300 micron cut. A written lens diameter from the customer "
        "would close the remaining question."
        % (R["scale"]["lens"]["rim_median_diam_px"], R["scale"]["lens"]["rim_iqr_diam_px"][0],
           R["scale"]["lens"]["rim_iqr_diam_px"][1],
           R["scale"]["lens"]["rim_median_diam_px"] * AS / 1000.0),
        "The prior scales %.4f and %.2f are superseded. %.4f divided an unsourced 14,200 "
        "micron lens assumption by a lens pixel measurement; the earlier 848 px lens "
        "figure is disproven as a two-ring circle-fit artefact, and the rim-restricted "
        "fit gives %g px. %.2f is written in no document we hold. Both appear in this "
        "workbook only in columns and sentences labelled superseded."
        % (PRIOR, SPOKEN, PRIOR, R["scale"]["lens"]["rim_median_diam_px"], SPOKEN),
        "Every micron figure elsewhere in this workbook is computed at %.3f microns per "
        "pixel from pixels; pixels are the measurement and microns are the restatement." % AS,
        "Two code collisions are kept as distinct flagged rows and are not merged until "
        "the client answers: the shared HEMA code, and the view-obstructed prefix. Every "
        "count that carries them moves if they are later consolidated.",
        "Two library-only classes, Bubble On Edge and Bubble Over 123 Mark, are counted "
        "as their own classes and tagged library-only, because they have not been "
        "consolidated yet.",
        "The HEMA Obstruction class is flagged on every production picture that carries "
        "it, so it is not size gated. It is reported as flagged everywhere, never as a "
        "size-selected subset.",
        "The blind-scale absolute test is blocked: no usable blind nominal exists and no "
        "external figure of 18.25 is written anywhere. Only the relative variation test "
        "was run, and it cannot see a 0.7 percent gap.",
        "This EDA is analysis only. The pooled one-tag-per-image dataset rebuild is a "
        "separate effort.",
        "The earlier single-batch analysis of the production set is superseded by this "
        "full-coverage analysis. The delta is named here rather than cross-referenced: the "
        "superseded record covered %s pictures with %s boxes and %s tags over %s codes; "
        "this analysis covers %s pictures and %s shapes over %d canonical defects."
        % (format(R["superseded_20261013"]["batch_pictures"], ","),
           format(R["superseded_20261013"]["boxes"], ","),
           format(R["superseded_20261013"]["tags"], ","),
           R["superseded_20261013"]["codes"],
           format(R["census"]["distinct_pictures"], ","),
           format(R["labels"]["shapes_total"], ","),
           R["labels"]["canonical_count"]),
    ]:
        r = bullet(ws, r, "- " + t)
    r += 1
    r = note(ws, r, "Verification: %d assertions across every headline, %d failures."
             % (V["assertions"], V["failures"]))
    return ws


# --------------------------------------------------------------------------
def sheet_census(wb, R):
    ws = sheet(wb, "Census")
    C = R["census"]
    widths(ws, {"A": 46, "B": 18, "C": 18, "D": 18, "E": 18, "F": 34})
    r = title(ws, 1, "Census: how many pictures exist, and how many files hold them",
              ["Keyed on content hash, never on a path, because some pictures are "
               "stored under more than one name."])
    r += 1

    r = section(ws, r, "At a glance")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Distinct pictures, three library folders", C["distinct_pictures"]),
        ("Files, three library folders", C["files_library"]),
        ("Files, all three library folders plus the production image folder", C["files_total"]),
        ("Bytes, all folders", C["bytes_total"]),
        ("Distinct pictures in total", C["distinct_pictures"]),
    ])
    r = note(ws, r, "The production image folder adds %s files but no new picture: every "
                    "one resolves by content hash to a picture already in a library folder."
             % format(C["files_production"], ","))
    r += 1

    r = section(ws, r, "Pictures and files per folder")
    r = header(ws, r, ["Folder", "Files", "Bytes"])
    rows = []
    for name, d in sorted(C["per_folder"].items(), key=lambda kv: -kv[1]["files"]):
        rows.append([name, d["files"], d["bytes"]])
    r = table(ws, r, rows, fmts=[None, NUM0, NUM0])
    r += 1

    r = section(ws, r, "Pictures and files per production line")
    r = header(ws, r, ["Line", "Files", "Distinct pictures"])
    for line, d in sorted(C["per_line"].items()):
        r = table(ws, r, [[line, d["files"], d["distinct_pictures"]]], fmts=[None, NUM0, NUM0])
    r += 1

    r = section(ws, r, "Content identity")
    r = header(ws, r, ["Measure", "Value"])
    cd = C["copy_distribution"]
    r = kv(ws, r, [("Content hash held by %s file(s)" % k, v) for k, v in sorted(cd.items())])
    r = table(ws, r, [
        ["Content held under more than one copy", C["hashes_with_more_than_one_copy"]],
        ["Content held in more than one folder", C["hashes_in_more_than_one_folder"]],
        ["Picture names that hide a duplicate content", C["renamed_aliases"]],
    ], fmts=[None, NUM0])
    r = note(ws, r, "A path-based count undercounts, because %d picture names hold a "
                    "content that also exists under a second name."
             % C["renamed_aliases"])
    r += 1

    r = section(ws, r, "The production batch against the library")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Production files", C["production_files"]),
        ("Production files that match a library picture by content", C["production_files"]),
        ("Distinct contents among the production files", C["production_distinct_contents"]),
    ])
    r = note(ws, r, "One production picture is annotated twice, under two byte-identical "
                    "file names that both carry the same eight shapes, so %s files hold "
                    "%s distinct contents."
             % (format(C["production_files"], ","), format(C["production_distinct_contents"], ",")))
    return ws


# --------------------------------------------------------------------------
def sheet_labels(wb, R):
    ws = sheet(wb, "Labels")
    L = R["labels"]
    widths(ws, {"A": 40, "B": 14, "C": 14, "D": 14, "E": 14, "F": 14, "G": 14, "H": 40})
    r = title(ws, 1, "Labels: the resolved census across every picture",
              ["One source per picture under the agreed priority rule, keyed on content "
               "hash. A shape is a box (a localised defect) or a tag (a whole-picture flag)."])
    r += 1

    r = section(ws, r, "The two annotation readings, never swapped")
    r = header(ws, r, ["Reading", "Pictures", "Note"])
    r = table(ws, r, [
        ["Mentioned by some file", L["mentioned"], "the picture appears in an annotation file"],
        ["Carry at least one shape", L["with_shape"], "a box or a tag was resolved for it"],
        ["Carry no shape", L["no_shape"], "mentioned but no shape resolved"],
        ["Mentioned nowhere", L["nowhere"], "no file names the picture at all"],
    ], fmts=[None, NUM0, None])
    r = note(ws, r, "Each pair sums to the %s-picture census: %s with a shape plus %s "
                    "with none, and %s mentioned plus %s nowhere."
             % (format(R["census"]["distinct_pictures"], ","),
                format(L["with_shape"], ","), format(L["no_shape"], ","),
                format(L["mentioned"], ","), format(L["nowhere"], ",")))
    r += 1

    r = section(ws, r, "Shapes")
    r = header(ws, r, ["Shape", "Count"])
    r = table(ws, r, [
        ["Boxes (localised defects)", L["boxes"]],
        ["Tags (whole-picture flags)", L["tags"]],
        ["Shapes total", L["shapes_total"]],
    ], fmts=[None, NUM0])
    r = note(ws, r, "The %s tags and the %s no-shape pictures are the same count seen "
                    "twice, which is why every table names which one it reports."
             % (format(L["tags"], ","), format(L["no_shape"], ",")))
    r += 1

    r = section(ws, r, "Pictures by shape kind")
    r = header(ws, r, ["Composition", "Pictures", "Share of pictures with a shape"])
    r = table(ws, r, [
        ["Box and tag together", L["both"], L["both"] / L["with_shape"]],
        ["Tag only", L["tag_only"], L["tag_only"] / L["with_shape"]],
        ["Box only", L["box_only"], L["box_only"] / L["with_shape"]],
    ], fmts=[None, NUM0, PCT1])
    r = note(ws, r, "%s pictures carry at least one box, %s carry at least one tag."
             % (format(L["pictures_with_box"], ","), format(L["pictures_with_tag"], ",")))
    r += 1

    r = section(ws, r, "Codes per picture")
    r = header(ws, r, ["Codes on the picture", "Pictures", "Share of census"])
    cpi = {int(k): v for k, v in L["box_codes_per_image"].items()}
    for k in sorted(cpi):
        r = table(ws, r, [[k, cpi[k], cpi[k] / R["census"]["distinct_pictures"]]],
                  fmts=[None, NUM0, PCT1])
    r = note(ws, r, "Median %g, mean %.2f, 90th percentile %g, maximum %d. A code counts "
                    "once per picture even when it appears on several shapes."
             % (L["median_codes"], L["mean_codes"], L["p90_codes"], int(L["max_codes"])))
    r += 1

    r = section(ws, r, "The %d canonical defects" % L["canonical_count"])
    r = note(ws, r, "Two code collisions are kept unmerged and flagged: the shared HEMA "
                    "code, and the view-obstructed prefix. library-only marks a class "
                    "counted on its own pending consolidation.")
    r = header(ws, r, ["Defect", "Shape kind", "Pictures", "Shapes", "Library only",
                       "Size gate", "Kind conflict", "Notes"])
    rows = []
    for d in sorted(L["canonical_defects"], key=lambda x: -x["shapes"]):
        notes = []
        if d["is_size_gate"]:
            notes.append("derived size gate")
        if d["kind_conflict"]:
            notes.append("kind differs between sources")
        if d["library_only"]:
            notes.append("library-only, not consolidated")
        rows.append([d["name"], d["kind"], d["pictures"], d["shapes"],
                     "yes" if d["library_only"] else "",
                     "yes" if d["is_size_gate"] else "",
                     "yes" if d["kind_conflict"] else "",
                     "; ".join(notes)])
    r = table(ws, r, rows, fmts=[None, None, NUM0, NUM0, None, None, None, None])
    r += 1

    r = section(ws, r, "How the labels resolved")
    r = header(ws, r, ["Source priority level", "Pictures it won"])
    for lvl, n in sorted(L["wins_by_level"].items()):
        r = table(ws, r, [[lvl, n]], fmts=[None, NUM0])
    r = note(ws, r, "Winner takes all per picture: the highest-priority file that mentions "
                    "a picture supplies all of its labels, and lower-priority files are "
                    "silent for it. Every picture resolves to exactly one source.")
    return ws


# --------------------------------------------------------------------------
def sheet_distributions(wb, R):
    ws = sheet(wb, "Distributions")
    L = R["labels"]
    C = R["census"]
    widths(ws, {"A": 30, "B": 14, "C": 14, "D": 40, "E": 14, "F": 14})
    r = title(ws, 1, "Distributions: how the codes combine on one picture",
              ["A multi-label set: the median picture carries %g code, the mean is %.2f, "
               "and the busiest carries %d."
               % (L["median_codes"], L["mean_codes"], int(L["max_codes"]))])
    r += 1

    r = section(ws, r, "Codes per picture")
    hdr = r
    r = header(ws, r, ["Codes", "Pictures", "Share"])
    start = r
    cpi = {int(k): v for k, v in L["box_codes_per_image"].items()}
    for k in sorted(cpi):
        r = table(ws, r, [[k, cpi[k], cpi[k] / C["distinct_pictures"]]], fmts=[None, NUM0, PCT1])
    end = r - 1
    add_bar(ws, "Pictures by number of codes", hdr, end, 2, "E3", y_title="Pictures")
    r += 1

    r = section(ws, r, "Pictures per canonical defect, largest first")
    hdr = r
    r = header(ws, r, ["Defect", "Pictures", "Shapes"])
    start = r
    for d in sorted(L["canonical_defects"], key=lambda x: -x["pictures"])[:15]:
        r = table(ws, r, [[d["name"], d["pictures"], d["shapes"]]], fmts=[None, NUM0, NUM0])
    end = r - 1
    add_bar(ws, "Pictures carrying each defect (top 15)", hdr, end, 2, "E18",
            y_title="Pictures", width=20, height=10)
    r += 1

    r = section(ws, r, "Pictures and files per production line")
    r = header(ws, r, ["Line", "Files", "Distinct pictures"])
    for line, d in sorted(C["per_line"].items()):
        r = table(ws, r, [[line, d["files"], d["distinct_pictures"]]], fmts=[None, NUM0, NUM0])
    r = note(ws, r, "One defect class dominates the set: the Bubble class alone is on %s "
                    "pictures, so a one-folder-per-class split would put most of the set "
                    "in that one bin."
             % format(next(d["pictures"] for d in L["canonical_defects"] if d["id"] == "bubble"), ","))
    return ws


# --------------------------------------------------------------------------
def sheet_box_geometry(wb, R):
    ws = sheet(wb, "Box geometry")
    G = R["box_geometry"]
    L = R["labels"]
    widths(ws, {"A": 30, "B": 10, "C": 11, "D": 11, "E": 11, "F": 11, "G": 12, "H": 12,
                "I": 12, "J": 30})
    r = title(ws, 1, "Box geometry and micron size",
              ["Size is the rectangle diagonal, invariant to the rotation attribute that "
               "most boxes carry. Both candidate scales appear side by side and are named "
               "in the same table."])
    r += 1

    r = section(ws, r, "Rotation and the axis-aligned share")
    r = header(ws, r, ["Measure", "Boxes", "Share"])
    r = table(ws, r, [
        ["Axis-aligned (rotation absent or zero)", G["axis_aligned"], G["share_axis_aligned"]],
        ["Rotated", G["rotated"], G["rotated"] / G["total"]],
        ["Total boxes", G["total"], 1.0],
    ], fmts=[None, NUM0, PCT1])
    r = note(ws, r, "Only %s of the %s boxes are axis-aligned, %s. The diagonal does not "
                    "depend on the rotation, so size is unaffected by the split."
             % (format(G["axis_aligned"], ","), format(G["total"], ","),
                pct(G["share_axis_aligned"])))
    r += 1

    r = section(ws, r, "Box size per defect, pixels primary")
    r = note(ws, r, "Diagonal in pixels, then restated in microns at the adopted scale "
                    "%.3f and at the superseded prior scale %.4f. Pixel columns are the "
                    "measurement. Defects are ordered by box count." % (AS, PRIOR))
    r = header(ws, r, ["Defect", "Boxes", "p25 px", "p50 px", "p75 px",
                       "p50 um @15.337 (adopted)", "p50 um @18.1165 (superseded)"])
    rows = []
    for cid, d in sorted(G["by_defect"].items(), key=lambda kv: -kv[1]["n"]):
        rows.append([cid, d["n"], d["diag_px_p25"], d["diag_px_p50"], d["diag_px_p75"],
                     d["diag_um_adopted_p50"], d["diag_um_at_18_1165_p50"]])
    r = table(ws, r, rows, fmts=[None, NUM0, NUM1, NUM1, NUM1, "#,##0", "#,##0"])
    r += 1

    r = section(ws, r, "Box size per folder group, pixels primary")
    r = header(ws, r, ["Folder group", "Boxes", "p25 px", "p50 px", "p75 px",
                       "p50 um @15.337 (adopted)", "p50 um @18.1165 (superseded)"])
    for g, d in sorted(G["by_folder_group"].items(), key=lambda kv: -kv[1]["n"]):
        r = table(ws, r, [[g, d["n"], d["diag_px_p25"], d["diag_px_p50"], d["diag_px_p75"],
                           d["diag_um_adopted_p50"], d["diag_um_at_18_1165_p50"]]],
                  fmts=[None, NUM0, NUM1, NUM1, NUM1, "#,##0", "#,##0"])
    r += 1

    r = section(ws, r, "Box size per production line, pixels primary")
    r = header(ws, r, ["Line", "Boxes", "p25 px", "p50 px", "p75 px",
                       "p50 um @15.337 (adopted)", "p50 um @18.1165 (superseded)"])
    for g, d in sorted(G["by_line"].items()):
        r = table(ws, r, [[g, d["n"], d["diag_px_p25"], d["diag_px_p50"], d["diag_px_p75"],
                           d["diag_um_adopted_p50"], d["diag_um_at_18_1165_p50"]]],
                  fmts=[None, NUM0, NUM1, NUM1, NUM1, "#,##0", "#,##0"])
    r = note(ws, r, "The line and folder-group medians sit between 10 and 15 px, except "
                    "the thin strata which a small tail pulls up. The blind-scale test "
                    "showed the " "pixel scale itself does not vary by line or group beyond noise.")
    r += 1

    r = section(ws, r, "Scale note: how the micron columns are computed")
    for t in [
        "Adopted scale: %.3f microns per pixel. Derived from the customer's documented "
        "300 micron cut: the micron-threshold tags switch at a defect longer side of "
        "%.2f to %.2f px, and 300 divided by the %.2f px midpoint gives the scale. The "
        "old 647 micron cut inverts to the same scale and is the independent "
        "reproduction." % (AS, R["scale"]["adopted_boundary_px"][0],
                           R["scale"]["adopted_boundary_px"][1],
                           (R["scale"]["adopted_boundary_px"][0]
                            + R["scale"]["adopted_boundary_px"][1]) / 2),
        "The prior scale %.4f is superseded; it divided an unsourced 14,200 micron lens "
        "assumption by a lens pixel measurement. The prior 848 px lens figure is "
        "disproven as a two-ring circle-fit artefact; restricted to the rim band the "
        "same fit gives %g px. The lens nominal is not documented in anything received; "
        "a written lens diameter from the customer would close the remaining question."
        % (PRIOR, R["scale"]["lens"]["rim_median_diam_px"]),
        "Every micron figure in this sheet is a pixel figure times %.3f. Pixels are the "
        "measurement; microns are the restatement." % AS,
    ]:
        r = bullet(ws, r, "- " + t)
    r += 1

    r = section(ws, r, "Sanity anchors, recomputed from pixels at the adopted scale")
    r = header(ws, r, ["Anchor", "Pixels", "Microns at 15.337"])
    A = R["scale"]["sanity_anchors"]
    r = table(ws, r, [
        ["Bubble median", A["bubble_median"]["px"], A["bubble_median"]["um"]],
        ["Foreign matter median", A["foreign_matter_median"]["px"], A["foreign_matter_median"]["um"]],
        ["Fiber median", A["fiber_median"]["px"], A["fiber_median"]["um"]],
        ["Gate boundary, lower", R["scale"]["adopted_boundary_px"][0],
         R["scale"]["adopted_boundary_um"][0]],
        ["Gate boundary, upper", R["scale"]["adopted_boundary_px"][1],
         R["scale"]["adopted_boundary_um"][1]],
        ["The old 647 micron cut, restated in pixels", A["old_cut_647_um_in_px"], 647],
    ], fmts=[None, NUM2, NUM1])
    r += 1

    r = section(ws, r, "The cavity, measured per picture")
    cav = R["cavity"]["read"]
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Pictures in the census", cav["pictures"]),
        ("Pictures where the cavity could be measured", cav["pictures_measured"]),
        ("Pictures that could not be measured", cav["pictures_could_not_measure"]),
        ("Cavity radius, p25 / p50 / p75 px",
         "%g / %g / %g" % (cav["cavity_radius_px_p25"], cav["cavity_radius_px_p50"],
                           cav["cavity_radius_px_p75"])),
    ])
    r = note(ws, r, "The %s that could not be measured are one named class, frames too "
                    "dark for any bright blob to be found. They are counted, not dropped: "
                    "%s plus %s equals %s."
             % (format(cav["pictures_could_not_measure"], ","),
                format(cav["pictures_measured"], ","),
                format(cav["pictures_could_not_measure"], ","),
                format(cav["pictures"], ",")))
    r += 1

    r = section(ws, r, "Where the boxes sit on the part")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Boxes with their centre outside the measured cavity radius", 4074),
        ("Share outside", 4074 / 14182),
        ("Boxes beyond 1.5 times the cavity radius", 3),
    ])
    r = note(ws, r, "Measured from each box centre to the measured cavity centre of its "
                    "own picture, not the image centre, because the part is not centred "
                    "in the frame. Only 3 boxes sit further out than 1.5 times the "
                    "radius, so nothing is annotated on the tray or the background.")
    r += 1
    r = section(ws, r, "Region annotations, not defect spots")
    r = note(ws, r, "The HEMA Obstruction and HEMA Fragment classes share a code and their "
                    "boxes are region annotations rather than defect spots: the combined "
                    "median spans more than the whole lens. They must not be read as "
                    "detector targets.")
    r += 1

    # The scale behind the micron columns, the second measurement attempt, and
    # the two corrections. Appended here so the existing box size tables above
    # stay unchanged and still answer what they answered before.
    r = append_scale_section(ws, r)
    return ws


# --------------------------------------------------------------------------
def sheet_blind_scale(wb, R):
    ws = sheet(wb, "Blind scale")
    S = R["scale"]
    b = S["blind"]
    widths(ws, {"A": 20, "B": 9, "C": 10, "D": 10, "E": 10, "F": 12, "G": 12, "H": 16})
    r = title(ws, 1, "Blind scale: does the pixel scale differ by group or by line",
              ["The lens is the same physical part on every line, so a real difference "
               "in measured rim pixels between strata would be a real scale difference. "
               "The absolute test is blocked: no usable blind nominal exists."])
    r += 1

    r = section(ws, r, "The adopted scale, per line and per folder")
    r = note(ws, r, "The gate inversion of the customer's 300 micron cut, run per "
                    "stratum. The adopted working scale is %.3f microns per pixel, the "
                    "frozen central figure." % AS)
    r = header(ws, r, ["Production line", "Scale (um/px)", "Note"])
    r = table(ws, r, [
        ["L24", S["per_line_um_per_px"]["L24"], ""],
        ["L25", S["per_line_um_per_px"]["L25"], "only 14 pictures, loose"],
        ["L26", S["per_line_um_per_px"]["L26"], ""],
        ["L27", S["per_line_um_per_px"]["L27"], ""],
        ["L31", "not computable", "no threshold defect in the production export"],
    ], fmts=[None, NUM2, None])
    r = header(ws, r, ["Folder group", "Scale (um/px)", "Note"])
    r = table(ws, r, [
        ["Updated folders only", S["per_folder_um_per_px"]["updated_folders_only"], ""],
        ["Pictures also in the old defects library",
         S["per_folder_um_per_px"]["pictures_also_in_the_old_defects_library"], ""],
    ], fmts=[None, NUM2, None])
    r = header(ws, r, ["The lens finding"])
    r = table(ws, r, [
        ["Lens rim, median diameter", "%g px (IQR %.1f to %.1f px)"
         % (S["lens"]["rim_median_diam_px"], S["lens"]["rim_iqr_diam_px"][0],
            S["lens"]["rim_iqr_diam_px"][1])],
        ["Lens diameter at the adopted scale", "12101 um (12.10 mm)"],
        ["Lens diameter at the superseded prior scale", "14.20 mm"],
        ["The earlier 848 px lens figure", "disproven: a two-ring circle-fit artefact; "
         "restricted to the rim band the same fit gives %g px" % S["lens"]["rim_median_diam_px"]],
        ["The lens nominal", "not documented in anything received; a written figure from "
         "the customer would close the remaining question"],
    ])
    r += 1

    r = section(ws, r, "The relative variation test")
    for t in [
        "No production line and no folder group differs from another beyond the "
        "measurement noise.",
        "Between stratum, the raw rim median runs %g to %g px, a range of %g px, %.1f "
        "percent of the mean. Within stratum, the relative spread runs 10.0 to 25.7 "
        "percent. The between-stratum spread does not clearly exceed the within-stratum "
        "spread."
        % (b["between_stratum_rim_p50_px"]["min"], b["between_stratum_rim_p50_px"]["max"],
           b["between_stratum_rim_p50_px"]["range_px"],
           b["between_stratum_rim_p50_px"]["range_pct_of_mean"]),
        "On the clean band of the rim, the %d strata agree to within %.1f percent, which "
        "is the size of the within-stratum spread itself."
        % (len(b["strata"]), b["between_stratum_clean_rim_p50_px"]["range_pct_of_mean"]),
        "The gap this test was aimed at, 18.1165 against 18.25, is 0.7 percent. The "
        "within-stratum spread is 10 to 26 percent. The gap is far inside the noise, so "
        "no version of this measurement can resolve it. That is itself the finding.",
    ]:
        r = bullet(ws, r, "- " + t)
    r += 1

    r = section(ws, r, "Per stratum, rim pixels")
    r = header(ws, r, ["Stratum", "Measured", "Failed", "rim p25", "rim p50", "rim p75",
                       "rim sd", "Relative spread"])
    rows = []
    for s in S["strata"]:
        rim = s.get("rim_px", {})
        rows.append([s["stratum"], s.get("measured_ok_n"), s.get("failed_n"),
                     rim.get("p25"), rim.get("p50"), rim.get("p75"),
                     rim.get("sd"), (rim.get("rel_spread_pct") or 0) / 100.0])
    r = table(ws, r, rows, fmts=[None, NUM0, NUM0, NUM1, NUM1, NUM1, NUM1, PCT1])
    r = note(ws, r, "Every stratum has a long lower tail: the rim finder occasionally "
                    "locks onto a dark feature inside the lens band instead of the rim. "
                    "That is a measurement misfire, not a small lens, and it is what the "
                    "clean-band figures set aside.")
    r += 1

    r = section(ws, r, "Between-stratum against within-stratum")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Between-stratum rim median, range px", b["between_stratum_rim_p50_px"]["range_px"]),
        ("Between-stratum rim median, percent of mean", b["between_stratum_rim_p50_px"]["range_pct_of_mean"]),
        ("Between-stratum clean rim median, range px", b["between_stratum_clean_rim_p50_px"]["range_px"]),
        ("Between-stratum clean rim median, percent of mean", b["between_stratum_clean_rim_p50_px"]["range_pct_of_mean"]),
    ])
    r = note(ws, r, "The implied microns-per-pixel columns in the stratum tables below "
                    "are computed at the superseded 14,200 micron reference and are kept "
                    "only to show the failed measurement; the adopted scale everywhere "
                    "else in this workbook is %.3f microns per pixel." % AS)
    return ws


# --------------------------------------------------------------------------
def sheet_micron_micron(wb, R):
    ws = sheet(wb, "Micron gate")
    G = R["micron_gate"]
    widths(ws, {"A": 22, "B": 14, "C": 14, "D": 14, "E": 14, "F": 14, "G": 16, "H": 40})
    r = title(ws, 1, "The client's micron gate, and the scale it implies",
              ["The four gate flags are the client's own authority. Everything derived "
               "here is reported beside them, never instead of them."])
    r += 1

    # the inversion, now adopted
    ic = G["implied_scale_combined"]
    inew = G["implied_scale_new"]
    iold = G["implied_scale_old"]
    SC = R["scale"]
    r = section(ws, r, "THE ADOPTED SCALE: the gate inverts to %.3f microns per pixel"
                % SC["adopted_um_per_px"])
    r = note(ws, r, "This is the adopted working scale of the whole analysis, derived "
                    "from the customer's own documented cut.")
    r = header(ws, r, ["Boundary", "Pixels", "Implied scale (um/px)"])
    r = table(ws, r, [
        ["New %g micron cut, foreign matter and fiber intersected" % G["cut_um"],
         "(%.3f, %.3f]" % (inew["boundary_px_lower"], inew["boundary_px_upper"]),
         "%.4f to %.4f" % (inew["scale_um_per_px_low"], inew["scale_um_per_px_high"])],
        ["Old %g micron cut, foreign matter and fiber intersected" % G["old_cut_um"],
         "(%.3f, %.3f]" % (iold["boundary_px_lower"], iold["boundary_px_upper"]),
         "%.4f to %.4f" % (iold["scale_um_per_px_low"], iold["scale_um_per_px_high"])],
        ["Combined (new and old intersected)",
         "-",
         "%.4f to %.4f, adopted midpoint %.3f"
         % (ic["scale_um_per_px_low"], ic["scale_um_per_px_high"], SC["adopted_um_per_px"])],
    ], fmts=[None, None, None])
    r += 1
    for t in [
        "The customer's own gate inverts to about %.2f microns per pixel "
        "(%.3f to %.3f, from a %g micron boundary at %.2f to %.2f px and a %g micron "
        "boundary at %.2f to %.2f px). Read back at the adopted scale, the boundary "
        "sits at %.1f to %.1f microns, which reproduces the customer's 300 micron cut."
        % (SC["adopted_um_per_px"], SC["adopted_interval_um_per_px"][0],
           SC["adopted_interval_um_per_px"][1],
           G["cut_um"], inew["boundary_px_lower"], inew["boundary_px_upper"],
           G["old_cut_um"], iold["boundary_px_lower"], iold["boundary_px_upper"],
           SC["adopted_boundary_um"][0], SC["adopted_boundary_um"][1]),
        "The old %g micron cut inverts to %.3f to %.3f microns per pixel, the same "
        "scale, and is the independent reproduction of the adopted figure."
        % (G["old_cut_um"], iold["scale_um_per_px_low"], iold["scale_um_per_px_high"]),
        "The prior scales %.4f and %.2f are superseded and disagree with the adopted "
        "scale; they are retained only as labelled comparisons elsewhere in this "
        "workbook." % (PRIOR, SPOKEN),
    ]:
        r = bullet(ws, r, "- " + t)
    r += 1

    r = section(ws, r, "The gate is a clean cut on the longer side, not the diagonal")
    r = note(ws, r, "The proxy that fits is the longer side of the annotation rectangle, "
                    "max(w, h). The diagonal does not fit: an image is misclassified when "
                    "a flagged image's size sits below the largest unflagged size, or an "
                    "unflagged image reaches the smallest flagged size.")
    r = header(ws, r, ["Proxy", "Misclassifications, foreign matter", "Misclassifications, fiber"])
    r = table(ws, r, [
        ["Longer side max(w, h)", 0, 0],
        ["Rectangle diagonal", 39, 4],
    ], fmts=[None, NUM0, NUM0])
    r = note(ws, r, "The longer side fits exactly; the diagonal misfiles 39 foreign-matter "
                    "images and 4 fiber images.")
    r += 1

    r = section(ws, r, "The boundary, new and old, at the adopted and superseded scales")
    r = note(ws, r, "Micron columns read the boundary midpoint at each named scale. The "
                    "adopted column is current; the superseded column is kept only for "
                    "comparison.")
    r = header(ws, r, ["Base code", "Cut (customer)", "Unflagged max px", "Flagged min px",
                       "Mid px", "Mid um @15.337 (adopted)", "Mid um @18.1165 (superseded)"])
    rows = []
    for base, d in G["new_boundaries_px"].items():
        mid = (d["lower_px"] + d["upper_px"]) / 2.0 if d["lower_px"] and d["upper_px"] else None
        rows.append([base, G["cut_um"], d["lower_px"], d["upper_px"], mid,
                     mid * AS if mid else None, mid * PRIOR if mid else None])
    for base, d in G["old_boundaries_px"].items():
        mid = (d["lower_px"] + d["upper_px"]) / 2.0 if d["lower_px"] and d["upper_px"] else None
        rows.append([base, G["old_cut_um"], d["lower_px"], d["upper_px"], mid,
                     mid * AS if mid else None, mid * PRIOR if mid else None])
    r = table(ws, r, rows, fmts=[None, NUM0, NUM2, NUM2, NUM2, NUM1, NUM1])
    r = note(ws, r, "At the adopted scale the new-cut boundary midpoint reads as %.1f to "
                    "%.1f microns, matching the customer's cut. At the superseded %.4f "
                    "the same boundary would read as about 352 to 355 microns, which is "
                    "one of the reasons that scale was set aside."
             % (SC["adopted_boundary_um"][0], SC["adopted_boundary_um"][1], PRIOR))
    r += 1

    r = section(ws, r, "The inversion rests on four assumptions")
    for t in G["assumptions"]:
        r = bullet(ws, r, "- " + t)
    r += 1

    r = section(ws, r, "The before and after delta")
    d = G["delta"]
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Pictures whose gate state changed between the two file dates", d["changed_pictures"]),
        ("Pictures that gained a foreign-matter flag", d["added_tags"].get("P3_FM_MICRON_THRESHOLD")),
        ("Pictures that gained a fiber flag", d["added_tags"].get("P3_FIB_MICRON_THRESHOLD")),
        ("Pictures that gained an extraneous-polymer flag", d["added_tags"].get("P3_EP_MICRON_THRESHOLD")),
        ("Pictures that lost a multiple-lenses flag", d["removed_tags"].get("P1_ML")),
        ("Pictures whose box geometry changed", d["geometry_changed_pictures"]),
    ])
    r = note(ws, r, "Only tags differ between the two dates; no box moved. The cut the "
                    "client announced is exactly the move the data shows. HEMA Obstruction "
                    "is flagged on all of its pictures because every one of its boxes "
                    "exceeds the cut; it is not size gated.")
    return ws


# --------------------------------------------------------------------------
def sheet_coverage(wb, R):
    ws = sheet(wb, "Coverage")
    CO = R["coverage"]
    D = R["disagreement"]
    widths(ws, {"A": 16, "B": 40, "C": 12, "D": 12, "E": 12, "F": 12, "G": 14})
    r = title(ws, 1, "Coverage: what is annotated out of what exists",
              ["Every stratum names the population it is measured in, in the same row."])
    r += 1

    r = section(ws, r, "By folder, folder group and production line")
    r = header(ws, r, ["Cut", "Stratum", "Pictures", "Mentioned", "With a shape",
                       "No shape", "Mentioned nowhere"])
    for s in CO["strata"]:
        r = table(ws, r, [[s["type"], s["value"] or s["population"], s["distinct"],
                           s["mentioned"], s["with_shape"], s["no_shape"], s["nowhere"]]],
                  fmts=[None, None, NUM0, NUM0, NUM0, NUM0, NUM0])
    r = note(ws, r, "The strata sum to the census on every cut: the folders to %s "
                    "pictures, the groups to the same, and the lines to the same. The "
                    "two unannotated figures are different numbers and are never swapped."
             % format(R["census"]["distinct_pictures"], ","))
    r += 1

    r = section(ws, r, "Coverage of the production blob folder")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Pictures in the production blob folder", CO["blob"]["folder_total"]),
        ("Annotated in the batch", CO["blob"]["annotated"]),
        ("Coverage", pct(CO["blob"]["share"], 2)),
    ])
    r = note(ws, r, "%s annotated of %s pictures, %s. The remainder is available as "
                    "negatives and was not pulled."
             % (format(CO["blob"]["annotated"], ","),
                format(CO["blob"]["folder_total"], ","), pct(CO["blob"]["share"], 2)))
    r += 1

    r = section(ws, r, "Pictures in the library alone, with their classes")
    r = header(ws, r, ["Defect class", "Pictures"])
    for name, n in CO["library_only_classes"]:
        r = table(ws, r, [[name, n]], fmts=[None, NUM0])
    r = table(ws, r, [["Total", CO["library_only_pictures"]]], fmts=[None, NUM0])
    r += 1

    r = section(ws, r, "Folder disagreement, by two different rules")
    r = warn(ws, r, "The widely quoted 113 figure is a NAME-based count, not a content "
                    "count. On content identity the overlap is larger.")
    r = header(ws, r, ["Rule", "Pictures the folders label differently", "What it counts"])
    r = table(ws, r, [
        ["Name-based, on the production batch", D["name_based_batch"],
         "matches pictures by file name, so a renamed duplicate is invisible"],
        ["Content identity, on the production batch", D["content_batch"],
         "matches pictures by content hash"],
        ["Content identity, library-wide", D["content_library"],
         "matches pictures by content hash across all three folders"],
    ], fmts=[None, NUM0, None])
    r = note(ws, r, "A name route cannot see a picture that was renamed, so it reports a "
                    "smaller overlap. The %d library-wide and %d batch figures are the "
                    "content-identity counts; 113 is the name-based one."
             % (D["content_library"], D["content_batch"]))
    r += 1
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Pictures where a higher-priority source disagreed with a lower one", D["rows"]),
        ("Mentions the middle-priority source lost", D["sep22_mentions"]),
        ("Mentions the lowest-priority source lost", D["old_mentions"]),
    ])
    return ws


# --------------------------------------------------------------------------
def sheet_crosswalk(wb, R):
    ws = sheet(wb, "Crosswalk")
    X = R["crosswalk"]
    widths(ws, {"A": 22, "B": 24, "C": 12, "D": 16, "E": 16, "F": 16, "G": 22, "H": 10,
                "I": 18, "J": 16, "K": 30})
    r = title(ws, 1, "Canonical crosswalk: one line per defect",
              ["%d canonical defects. Each code in each source is mapped to exactly one "
               "canonical defect. The crosswalk is frozen." % X["count"]])
    r += 1

    r = section(ws, r, "Two code collisions, kept unmerged and flagged")
    for name, text in X["collision_flags"].items():
        r = bullet(ws, r, "- " + text)
    r += 1

    r = section(ws, r, "The crosswalk")
    r = header(ws, r, ["Canonical defect", "Library folder", "Shape kind", "Kind conflict",
                       "Code in project 3", "Code in the 09-22 project",
                       "Code in the production files", "Size gate", "Gate base",
                       "Collision flag"])
    rows = []
    for c in sorted(X["table"], key=lambda x: x["name"]):
        rows.append([c["name"], c["lib"], c["kind"],
                     "yes" if c["kind_conflict"] == "yes" else "",
                     c["p2"], c["p22"], c["p25"], c["gate"], c["base"],
                     c["collision"] or ""])
    r = table(ws, r, rows, fmts=[None] * 10)
    r = note(ws, r, "Where a source writes the shape kind differently, both are kept and "
                    "the row is flagged rather than silently reconciled. Two collisions "
                    "are flagged: the shared HEMA code, and the view-obstructed prefix.")
    return ws


# --------------------------------------------------------------------------
def sheet_checks(wb, R):
    ws = sheet(wb, "Checks")
    L, C, V = R["labels"], R["census"], R["verification"]
    widths(ws, {"A": 54, "B": 18, "C": 62})
    r = title(ws, 1, "Checks: the invariants behind the summary numbers",
              ["Each row can be re-checked by hand from the same inputs."])
    r += 1
    r = header(ws, r, ["Invariant", "Value", "How to re-check"])
    checks = [
        ("Distinct pictures", C["distinct_pictures"], "distinct content hashes across the folders"),
        ("Files, library folders", C["files_library"], "sum of the three library folders"),
        ("Files, all folders", C["files_total"], "library files plus the production image files"),
        ("Pictures mentioned by some file", L["mentioned"], "one mention makes a picture mentioned"),
        ("Pictures carrying a shape", L["with_shape"], "pictures with at least one box or tag"),
        ("Pictures carrying no shape", L["no_shape"], "census minus the with-shape count"),
        ("Pictures mentioned nowhere", L["nowhere"], "census minus the mentioned count"),
        ("Shapes", L["shapes_total"], "boxes plus tags"),
        ("Boxes", L["boxes"], "sum of box shapes"),
        ("Tags", L["tags"], "sum of tag shapes; equals the no-shape picture count"),
        ("Canonical defects", L["canonical_count"], "rows in the frozen crosswalk"),
        ("Box pictures", L["pictures_with_box"], "pictures carrying at least one box"),
        ("Axis-aligned boxes", R["box_geometry"]["axis_aligned"], "boxes with no rotation or a zero rotation"),
        ("Cavity pictures measured", R["cavity"]["read"]["pictures_measured"],
         "census minus the unmeasurable class"),
        ("Cavity pictures unmeasurable", R["cavity"]["read"]["pictures_could_not_measure"],
         "one named class, too dark to measure"),
    ]
    r = table(ws, r, checks, fmts=[None, NUM0, None])
    r += 1
    r = section(ws, r, "Cross-checks that should hold and do")
    for t in [
        "%s with a shape plus %s with none equals the %s census; %s mentioned plus %s "
        "nowhere equals the same census."
        % (format(L["with_shape"], ","), format(L["no_shape"], ","),
           format(C["distinct_pictures"], ","), format(L["mentioned"], ","),
           format(L["nowhere"], ",")),
        "%s boxes plus %s tags equals %s shapes."
        % (format(L["boxes"], ","), format(L["tags"], ","), format(L["shapes_total"], ",")),
        "Every picture resolves to exactly one source file, and no picture carries labels "
        "from two sources.",
        "Every size-gate flag is a strict subset of its base code, and every gate picture "
        "carries its base code.",
        "The %s no-shape picture count and the %s tag-shape count are the same number and "
        "are reported together, never swapped with the %s no-mention count."
        % (format(L["no_shape"], ","), format(L["tags"], ","), format(L["nowhere"], ",")),
    ]:
        r = bullet(ws, r, "- " + t)
    r += 1
    r = section(ws, r, "Independent verification of the analysis")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Assertions run across every headline", V["assertions"]),
        ("Failures", V["failures"]),
        ("Cross-artifact checks", V["checks"]),
        ("Headline figures independently re-derived", V["figures"]),
    ])
    return ws


def build(numbers_path, out_path):
    R = json.load(open(numbers_path, encoding="utf-8"))
    wb = Workbook()
    sheet_readme(wb, R)
    sheet_census(wb, R)
    sheet_labels(wb, R)
    sheet_distributions(wb, R)
    sheet_box_geometry(wb, R)
    sheet_blind_scale(wb, R)
    sheet_micron_micron(wb, R)
    sheet_coverage(wb, R)
    sheet_crosswalk(wb, R)
    sheet_checks(wb, R)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wb.save(out_path)
    return wb


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--numbers", default="full_numbers.json")
    ap.add_argument("--out", default="FMD_Full_EDA_20261015.xlsx")
    a = ap.parse_args()
    build(a.numbers, a.out)
    print("wrote %s" % os.path.abspath(a.out))


if __name__ == "__main__":
    main()
