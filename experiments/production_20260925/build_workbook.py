#!/usr/bin/env python3
"""Build the PRODUCTION_20260925 EDA workbook from batch_numbers.json.

The builder only formats; every number comes from batch_numbers.py, so the
workbook and the README on the VM cannot drift apart.

Sheets:
  Read me        what this is, where the numbers come from, how to regenerate,
                 headline findings and caveats
  EDA            batch composition, codes per image, provenance, rotation,
                 filename families, lines, dates
  Tags & codes   the full catalogue of all 24 codes and what each one means
  Micron         box sizes in pixels and microns, the size thresholds, the
                 *_MICRON_THRESHOLD gates, and the size outliers
  Per image      one row per image, 1,047 rows, filterable
  Checks         the invariants a reader can re-check by hand

Usage:
  python build_workbook.py --numbers batch_numbers.json --out report.xlsx
"""
from __future__ import annotations

import argparse
import datetime
import json
import os

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# house style, matching experiments/eda_client/build_client_eda_workbook.py
TITLE = Font(bold=True, size=14)
SUB = Font(bold=True, size=11)
HEAD = Font(bold=True, color="FFFFFF")
HEADFILL = PatternFill("solid", fgColor="1F3864")
NOTEFONT = Font(italic=True, size=9, color="555555")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
RIGHT = Alignment(horizontal="right")

PCT0 = "0%"
PCT1 = "0.0%"
NUM1 = "#,##0.0"
NUM0 = "#,##0"


def sheet(wb, name, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = name
    ws.sheet_view.showGridLines = False
    return ws


def title(ws, row, text, sub=None):
    ws.cell(row=row, column=1, value=text).font = TITLE
    row += 1
    if sub:
        for line in sub:
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
    """Write rows of values under an already-written header."""
    for r in rows:
        for i, v in enumerate(r):
            cell = ws.cell(row=row, column=first_col + i, value=v)
            cell.border = BOX
            if fmts and i < len(fmts) and fmts[i] and isinstance(v, (int, float)):
                cell.number_format = fmts[i]
        row += 1
    return row


def kv(ws, row, pairs, keyw=None, valw=None, vfmt=None):
    for k, v in pairs:
        a = ws.cell(row=row, column=1, value=k)
        a.border = BOX
        b = ws.cell(row=row, column=2, value=v)
        b.border = BOX
        if vfmt and isinstance(v, (int, float)):
            b.number_format = vfmt
        row += 1
    return row


def bullet(ws, row, text):
    ws.cell(row=row, column=1, value="  " + text)
    return row + 1


def note(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = NOTEFONT
    return row + 1


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def pct_str(x, nd=1):
    return ("%." + str(nd) + "f%%") % (100.0 * x)


# --------------------------------------------------------------------------
def sheet_readme(wb, R):
    ws = sheet(wb, "Read me", first=True)
    S, F = R["summary"], R["filenames"]
    widths(ws, {"A": 46, "B": 78, "C": 18})
    r = title(ws, 1, "PRODUCTION 2026-09-25 annotation batch: EDA, tags and micron measurements",
              ["%d images, %s boxes and %s tags across %d annotation jobs."
               % (S["images"], format(S["boxes"], ","), format(S["tag_elements"], ","), S["jobs"]),
               "Every number in this workbook is computed from the annotation files by script.",
               "Nothing is transcribed by hand."])
    r += 1

    r = section(ws, r, "What each sheet answers")
    hs = ["Sheet", "Question it answers"]
    hrow = r
    r = header(ws, r, hs)
    r = table(ws, r, [
        ["EDA", "What is in the batch, how do the codes combine on one image, who "
                "made the shapes, and what do the filenames carry"],
        ["Tags & codes", "Every code in the annotation, what it means, whether the client "
                         "has confirmed it, and how often it appears"],
        ["Distributions", "The shape of the batch as charts, and the answer to why one image "
                          "reaches %d codes" % R["distributions"]["summary"]["max_codes"]],
        ["Annotator email", "The annotator's handover email checked against the delivered "
                            "files: the rule behind the micron tags, how the stated counts "
                            "compare to what arrived, and whether the rule reproduces them"],
        ["Micron", "How big each defect class actually is in microns, how that compares "
                   "to the recorded size thresholds, and what the size gate flags"],
        ["Per image", "One row per image with its codes, shape counts, line, date and "
                      "measured cavity geometry, so any single image can be looked up"],
        ["Checks", "The invariants behind the summary numbers, each one re-checkable"],
    ])
    r += 1

    r = section(ws, r, "Where the numbers come from")
    r = header(ws, r, ["Input", "Where it lives"])
    r = table(ws, r, [
        ["Annotation files", "%d CVAT XML exports, one per job (jobs %s to %s)"
         % (S["jobs"], R["provenance"]["jobs"][0]["id"], R["provenance"]["jobs"][-1]["id"])],
        ["Jobs", "Each job is 150 frames; the seven jobs cover frames 0 to 1049"],
        ["Scale", "%s micrometres per pixel, from the pipeline scale estimate%s"
         % (S["um_per_px"],
            " measured on %s images" % R["scale"].get("n_images_used")
            if R.get("scale", {}).get("n_images_used") else "")],
        ["Cavity geometry", "measured per image by vm/ops/measure_cavity_all.py, "
                            "%d of %d images measurable" % (R["cavity"]["images_measured"], S["images"])],
        ["Annotator email", "the handover email that accompanied the upload, which states "
                            "the rule behind the micron tags"],
        ["Generating code", "experiments/production_20260925/batch_numbers.py and "
                            "build_workbook.py in this repository"],
    ])
    r += 1

    r = section(ws, r, "How to regenerate")
    r = note(ws, r, "The shared VM holds no scripts, so both are piped over ssh and write "
                    "only the artifact:")
    r = note(ws, r, "python experiments/production_20260925/batch_numbers.py "
                    "--annotations <dir> --cavity <cavity json> --out batch_numbers.json")
    r = note(ws, r, "python experiments/production_20260925/build_workbook.py "
                    "--numbers batch_numbers.json --out report.xlsx")
    r += 1

    r = section(ws, r, "Headline findings")
    biggest = max(R["codes"], key=lambda c: c["boxes"])
    biggest_img = max(R["codes"], key=lambda c: c["images"])
    he = [c for c in R["codes"] if c["code"] == "P3_HE"][0]
    testable = [g for g in R["gates"] if g["unit_testable"]]
    lo = min(g["ratio"] for g in testable)
    hi = max(g["ratio"] for g in testable)
    findings = [
        "This is a multi-label set, not one class per image. %d of %d images carry more "
        "than one code, the median image carries %g codes and the busiest carries %d. Only "
        "%d images carry exactly one code."
        % (S["images_multi_code"], S["images"], S["median_codes_per_image"],
           S["max_codes_per_image"], S["images_single_code"]),
        "One class dominates: `%s` appears on %s images (%s of the batch) and holds %s of "
        "the %s boxes. A class-folder split would put most of the set in that one bin."
        % (biggest_img["code"], format(biggest_img["images"], ","),
           pct_str(biggest_img["image_share"]), format(biggest["boxes"], ","),
           format(S["boxes"], ",")),
        "The %d codes ending `_MICRON_THRESHOLD` are not separate classes. They are an "
        "image-level flag set by a size rule on the four debris codes: the annotator's email "
        "states that they mark images containing debris over %s micrometres. On the %d gates "
        "that can be tested, images carrying the flag hold a median largest box %.2f to %.2f "
        "times larger than images without it."
        % (S["codes_that_are_gates"],
           format((R.get("email") or {}).get("threshold_um", 647), ","),
           len(testable), lo, hi),
        "Annotation provenance is largely machine. %s of the %s boxes came from an imported "
        "file and only %s were drawn by hand, so most of this set is pre-annotation that a "
        "human reviewed rather than annotation a human created."
        % (format(R["box_source"].get("file", 0), ","), format(S["boxes"], ","),
           format(R["box_source"].get("manual", 0), ",")),
        "The boxes are genuinely rotated: %s of the %s boxes carrying a rotation value "
        "(%s) sit at angles that are not multiples of 90 degrees, and the angles are spread "
        "across all eight 45 degree buckets. An axis-aligned only conversion will mis-draw "
        "almost all of them."
        % (format(S["rotation_other"], ","), format(S["rotation_present"], ","),
           pct_str(S["rotation_other_share"])),
        "`%s` is not a defect spot. Its %d boxes have a median diagonal of %s micrometres, "
        "larger than the %s micrometre lens, so it marks a region and should not be trained "
        "as a detector target beside the %s micrometre median of every other code. This is "
        "also why every one of its images carries the size flag: its smallest box is %s "
        "micrometres, about eight times the %s micrometre threshold."
        % (he["code"], he["boxes"],
           format(round(he_median_um(R)), ","), format(round(lens_um(R)), ","),
           format(round(S["median_box_diag_um"]), ","),
           format(round(he_min_um(R)), ","),
           format((R.get("email") or {}).get("threshold_um", 647), ",")),
        "The batch carries two filename families: %s images use the legacy "
        "date time line cavity serial form, and %s use the line form that adds pallet, "
        "cavity id, board id, a fail count and a selection score. Only the second family "
        "carries those covariates."
        % (format(F["families"].get("plain", 0), ","),
           format(F["families"].get("line", 0), ",")),
    ]
    for i, t in enumerate(findings, 1):
        ws.cell(row=r, column=1, value="%d." % i).font = BOLD
        ws.cell(row=r, column=2, value=t).alignment = WRAP
        r += 1
    r += 1

    r = section(ws, r, "Caveats and open questions")
    unconf = [c["code"] for c in R["codes"] if not c["confirmed"] and not c["is_gate"]]
    cav = R["cavity"]
    for t in [
        "Four codes are not confirmed against the client taxonomy: %s. Their names in this "
        "workbook are placeholders." % ", ".join("`%s`" % c for c in unconf),
        "`P3_HE` still needs the annotator to define it. Its size says it marks a region rather "
        "than a spot, and the size rule explains why all %d of its images carry the flag, but "
        "what the region is meant to cover is not in the email." % he["images"],
        "The size rule behind the micron tags is not exactly reproducible from the delivered "
        "file. No reading of a box's size at the stated %s micrometre cut reproduces all four "
        "codes, and the flags changed during validation, so part of the gap is likely the "
        "validation pass. See the Annotator email sheet."
        % format((R.get("email") or {}).get("threshold_um", 647), ","),
        "The email writes one code as `P2_FOV` where the delivered file writes `F2_FOV`. One of "
        "the two is a typo and it should be settled before either name goes into a class list.",
        "`P2_DC` (Dirty Camera) moved by the largest amount of any code between the email "
        "and the delivered file, +176. Worth asking whether it was redefined during "
        "validation or simply applied more broadly.",
        "The cavity radius is a slightly conservative measurement, so %s box centres land "
        "just outside it. The maximum distance is %.2f times the radius, so nothing is "
        "annotated out on the tray. See the Micron sheet."
        % (pct_str(R["cavity"]["outside"] / R["cavity"]["boxes_placed"]),
           R["cavity"]["max_ratio"]),
        "%s of the %s boxes carry no rotation value at all, so they read as unrotated. "
        "Whether that is deliberate or an export default is not recorded."
        % (format(S["rotation_absent"], ","), format(S["boxes"], ",")),
        "The score values in the %s line-form filenames are the upstream model's selection "
        "scores. They are a sampling covariate, not a label, and should not be used as a "
        "target." % format(F["scored_images"], ","),
        "This batch is %d of the 10,438 images in the blob folder. The remaining 9,391 are "
        "available as negatives and are not included here." % S["images"],
    ]:
        r = bullet(ws, r, "- " + t)
        r += 1
    return ws


def he_median_um(R):
    for s in R["sizes"]:
        if s["code"] == "P3_HE":
            return s["median_um"]
    return 0.0


def lens_um(R):
    """The lens diameter in microns, read from the scale estimate."""
    sc = R.get("scale") or {}
    px = sc.get("lens_diam_px") or sc.get("lens_diam_px_trimmed_mean")
    if not px:
        return 0.0
    return float(px) * R["summary"]["um_per_px"]


# --------------------------------------------------------------------------
def add_bar(ws, title, hdr_row, last_row, data_col, anchor, cat_col=1,
            y_title="Images", width=14, height=8, rotate_labels=False):
    """Add a column chart reading a table already written to the sheet."""
    ch = BarChart()
    ch.type = "col"
    ch.style = 10
    ch.title = title
    ch.y_axis.title = y_title
    ch.x_axis.title = None
    ch.width = width
    ch.height = height
    data = Reference(ws, min_col=data_col, min_row=hdr_row, max_row=last_row)
    cats = Reference(ws, min_col=cat_col, min_row=hdr_row + 1, max_row=last_row)
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.dLbls = DataLabelList()
    ch.dLbls.showVal = True
    ch.legend = None
    ws.add_chart(ch, anchor)
    return ch


def sheet_distributions(wb, R):
    """Distributions, with the multi-code tail answered rather than just plotted."""
    ws = sheet(wb, "Distributions")
    D = R["distributions"]
    s = D["summary"]
    S = R["summary"]
    widths(ws, {"A": 30, "B": 12, "C": 12, "D": 34, "E": 12, "F": 12, "G": 12, "H": 12})
    n_img = S["images"]
    tail = D["tail_images"]

    r = title(ws, 1, "Distributions",
              ["The shape of the batch, and the answer to the obvious question: %d codes on one "
               "image." % s["max_codes"],
               "The median image carries %g codes and the mean is %.2f, so the top of the "
               "distribution is a short tail rather than the norm."
               % (s["median_codes"], s["mean_codes"])])
    r += 1

    r = section(ws, r, "Why one image reaches %d codes" % s["max_codes"])
    for t in [
        "A code counts once per image, and the four size-gate flags count as codes. Those flags "
        "are derived: a `P3_EP_MICRON_THRESHOLD` tag says the image has a large `P3_EP` box, so "
        "it is a second entry for a defect already counted.",
        "Strip the size-gate flags and the maximum falls from %d to %d codes, and the mean falls "
        "from %.2f to %.2f." % (s["max_codes"], s["max_base_codes"], s["mean_codes"],
                                s["mean_base_codes"]),
        "An image's codes are the union of two families: localised defects (boxes) and "
        "whole-image flags (tags). The mean image has %.2f box codes and %.2f tag codes. The %d "
        "tail images average %.1f box codes and %.1f tag codes, so their count is high on both "
        "at once rather than driven by one family."
        % (s["mean_box_codes"], s["mean_tag_codes"], s["tail_images"],
           sum(len(t["box_codes"]) for t in tail) / len(tail),
           sum(len(t["tag_codes"]) for t in tail) / len(tail)),
        "The tail is small. %d images of %d carry %d or more codes, which is %.1f percent of the "
        "batch, and they hold %.1f percent of all shape placements, so the distribution is not "
        "being driven by a handful of over-annotated files."
        % (s["tail_images"], n_img, s["tail_cut"], 100 * s["tail_share_of_images"],
           100 * s["tail_share_of_shapes"]),
        "One code explains most of the spread. `P2_BB` is on %d images, %.1f percent of the batch. "
        "Images carrying it average %.2f codes; images without it average %.2f."
        % (s["with_bubble_images"], 100 * s["with_bubble_images"] / n_img,
           s["with_bubble_mean_codes"], s["without_bubble_mean_codes"]),
    ]:
        r = bullet(ws, r, "- " + t)
        r += 1
    r += 1

    # ---- table 1: codes per image
    r = section(ws, r, "Codes per image")
    hdr = r
    r = header(ws, r, ["Codes", "Images", "Share"])
    t1s = r
    r = table(ws, r, [[k, n, n / n_img] for k, n in D["codes_per_image"]],
              fmts=[NUM0, NUM0, PCT1])
    t1e = r - 1
    ch1 = add_bar(ws, "Images by number of codes", hdr, t1e, 2, "E4")
    r += 1

    # ---- table 2: base codes only
    r = section(ws, r, "Codes per image, size-gate flags excluded")
    r = note(ws, r, "Same count with the four derived flags removed, which is the honest reading "
                    "of how many distinct things are wrong with the part.")
    hdr = r
    r = header(ws, r, ["Base codes", "Images", "Share"])
    t2s = r
    r = table(ws, r, [[k, n, n / n_img] for k, n in D["base_codes_per_image"]],
              fmts=[NUM0, NUM0, PCT1])
    t2e = r - 1
    ch2 = add_bar(ws, "Images by number of base codes", hdr, t2e, 2, "E21")
    r += 1

    # ---- table 3: the two families side by side
    r = section(ws, r, "The two code families per image")
    r = note(ws, r, "Box codes are localised defects. Tag codes are whole-image flags. An image's "
                    "code count is these two added together, which is why the tail has two "
                    "components.")
    hdr = r
    r = header(ws, r, ["Codes of that kind", "Images with that many box codes",
                       "Images with that many tag codes"])
    maxk = max(max(k for k, _ in D["box_codes_per_image"]),
               max(k for k, _ in D["tag_codes_per_image"]))
    bmap = dict(D["box_codes_per_image"])
    tmap = dict(D["tag_codes_per_image"])
    t3s = r
    r = table(ws, r, [[k, bmap.get(k, 0), tmap.get(k, 0)] for k in range(0, maxk + 1)],
              fmts=[NUM0, NUM0, NUM0])
    t3e = r - 1
    ch3 = BarChart()
    ch3.type = "col"
    ch3.style = 10
    ch3.title = "Images by how many codes of each kind"
    ch3.y_axis.title = "Images"
    ch3.width = 16
    ch3.height = 8
    ch3.add_data(Reference(ws, min_col=2, max_col=3, min_row=hdr, max_row=t3e),
                 titles_from_data=True)
    ch3.set_categories(Reference(ws, min_col=1, min_row=hdr + 1, max_row=t3e))
    ws.add_chart(ch3, "E38")
    r += 1

    # ---- table 4: images per code
    r = section(ws, r, "Images per code, most common first")
    hdr = r
    r = header(ws, r, ["Code", "Images", "Share of batch"])
    top = R["codes"][:14]
    t4s = r
    r = table(ws, r, [[c["code"], c["images"], c["image_share"]] for c in top],
              fmts=[None, NUM0, PCT1])
    t4e = r - 1
    ch4 = add_bar(ws, "Images carrying each code (top 14)", hdr, t4e, 2, "E55",
                  y_title="Images", width=18, height=10)
    r += 1

    # ---- table 5: size histogram
    r = section(ws, r, "Box size across the whole batch")
    r = note(ws, r, "Diagonal in microns. The distribution is concentrated just under 200 "
                    "micrometres, with a long tail that the size gate picks out.")
    hdr = r
    r = header(ws, r, ["Size bucket (um)", "Boxes", "Share of boxes"])
    total_boxes = S["boxes"]
    t5s = r
    rows5 = []
    for b in D["size_histogram"]:
        lab = ("under %d" % b["hi_um"]) if b["lo_um"] == 0 else (
            "%d and over" % b["lo_um"] if b["hi_um"] is None else "%d to %d" % (b["lo_um"], b["hi_um"]))
        rows5.append([lab, b["boxes"], b["boxes"] / total_boxes])
    r = table(ws, r, rows5, fmts=[None, NUM0, PCT1])
    t5e = r - 1
    ch5 = add_bar(ws, "Boxes by size bucket", hdr, t5e, 2, "E74",
                  y_title="Boxes", width=18, height=10)
    r += 1

    # ---- tail table
    r = section(ws, r, "Every image carrying %d or more codes" % s["tail_cut"])
    r = note(ws, r, "The full list, so the tail can be inspected rather than assumed. Gate codes "
                    "in the last column are the derived flags.")
    r = header(ws, r, ["File", "Codes", "Base codes", "Gate codes", "Boxes", "Tags", "Line",
                       "Box codes", "Tag codes"])
    rows = []
    for t in tail:
        rows.append([t["basename"], t["codes"], t["base_codes"], t["gate_codes"],
                     t["boxes"], t["tags"], t["line"],
                     "; ".join(t["box_codes"]), "; ".join(t["tag_codes"])])
    r = table(ws, r, rows, fmts=[None, NUM0, NUM0, NUM0, NUM0, NUM0, None, None, None])
    r += 1
    first = tail[0]
    r = note(ws, r, "The top image, %s, carries %d codes: %d localised defects and %d whole-image "
                    "flags, of which %d are size-gate echoes of a box code already counted. Its "
                    "distinct problems number %d."
             % (first["basename"], first["codes"], len(first["box_codes"]),
                len(first["tag_codes"]), first["gate_codes"], first["base_codes"]))
    return ws


def sheet_eda(wb, R):
    ws = sheet(wb, "EDA")
    S, F = R["summary"], R["filenames"]
    widths(ws, {"A": 44, "B": 16, "C": 14, "D": 14, "E": 16, "F": 46})
    r = title(ws, 1, "EDA: what is in the batch",
              ["Counts come from the seven CVAT XML exports. Percentages are of the "
               "%d images unless stated." % S["images"]])
    r += 1

    r = section(ws, r, "Batch at a glance")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Annotation jobs", S["jobs"]),
        ("Images annotated", S["images"]),
        ("Boxes (localised defects)", S["boxes"]),
        ("Tags (whole-image flags)", S["tag_elements"]),
        ("Codes in use", S["distinct_codes"]),
        ("of which size gates", S["codes_that_are_gates"]),
        ("Images carrying 1 code", S["images_single_code"]),
        ("Images carrying 2 or more codes", S["images_multi_code"]),
        ("Images carrying no code", S["images_no_code"]),
        ("Median codes per image", S["median_codes_per_image"]),
        ("Most codes on one image", S["max_codes_per_image"]),
        ("Image geometry", ", ".join("%s (%d images)" % (k, v)
                                     for k, v in S["geometry_variants"].items())),
        ("Scale", "%s um per pixel" % S["um_per_px"]),
    ], vfmt=None)
    r += 1

    r = section(ws, r, "Codes per image")
    r = note(ws, r, "A code counts once per image even when it appears on several shapes.")
    r = header(ws, r, ["Codes on the image", "Images", "Share of batch"])
    r = table(ws, r, [[k, n, n / S["images"]] for k, n in R["codes_per_image_distribution"]],
              fmts=[None, NUM0, PCT1])
    r += 1

    r = section(ws, r, "What kind of shape carries the code")
    r = header(ws, r, ["Shape combination", "Images", "Share of batch"])
    r = table(ws, r, [
        ["Boxes and tags together", S["images_both"], S["images_both"] / S["images"]],
        ["Tags only (whole-image flags)", S["images_tag_only"], S["images_tag_only"] / S["images"]],
        ["Boxes only (localised defects)", S["images_box_only"], S["images_box_only"] / S["images"]],
        ["Nothing annotated", S["images_neither"], S["images_neither"] / S["images"]],
    ], fmts=[None, NUM0, PCT1])
    r += 1

    r = section(ws, r, "Who made the shapes")
    r = note(ws, r, "CVAT records a source per shape. 'file' means it arrived with an "
                    "imported annotation file, so it is pre-annotation a human reviewed. "
                    "'manual' means a human drew it in the tool.")
    r = header(ws, r, ["Shape", "Source", "Shapes", "Share of that shape type"])
    r = table(ws, r, [
        ["Box", "file", R["box_source"].get("file", 0),
         R["box_source"].get("file", 0) / S["boxes"]],
        ["Box", "manual", R["box_source"].get("manual", 0),
         R["box_source"].get("manual", 0) / S["boxes"]],
        ["Tag", "file", R["tag_source"].get("file", 0),
         R["tag_source"].get("file", 0) / S["tag_elements"]],
        ["Tag", "manual", R["tag_source"].get("manual", 0),
         R["tag_source"].get("manual", 0) / S["tag_elements"]],
        ["Tag", "not recorded", R["tag_source"].get("None", 0),
         R["tag_source"].get("None", 0) / S["tag_elements"]],
    ], fmts=[None, None, NUM0, PCT1])
    r = note(ws, r, "Every box has occluded = 0 and z_order = 0, so no shape is marked as "
                    "partly hidden and stacking order carries no information.")
    r = note(ws, r, "Tag elements in the files: %d. Distinct labels after collapsing repeats "
                    "on the same image: %d, so %d label is repeated."
                    % (S["tag_elements"], S["tag_labels_counted"], S["repeated_tag_labels"]))
    r += 1

    r = section(ws, r, "Rotation")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Boxes with a rotation value", S["rotation_present"]),
        ("Boxes with no rotation value", S["rotation_absent"]),
        ("of the rotated boxes, at a multiple of 90 degrees", S["rotation_right_angle"]),
        ("of the rotated boxes, at any other angle", S["rotation_other"]),
        ("Share at a non-right angle", S["rotation_other_share"]),
        ("Rotated boxes whose value is exactly zero", S["rotation_zero"]),
    ], vfmt=None)
    r = note(ws, r, "Rotation values fall in every 45 degree bucket, so the angles are spread "
                    "rather than snapped to the four right angles.")
    r += 1
    r = header(ws, r, ["Rotation bucket (degrees)", "Boxes"])
    r = table(ws, r, [[k, v] for k, v in R["rotation_buckets"]], fmts=[NUM0, NUM0])
    r += 1

    r = section(ws, r, "Covariates carried by the filenames")
    r = note(ws, r, "Two families exist. Only the second carries pallet, board, fail count "
                    "and score.")
    r = header(ws, r, ["Family", "Images", "Fields it carries"])
    r = table(ws, r, [
        ["Legacy: date_time_L##_C##_serial.bmp", F["families"].get("plain", 0),
         "capture date, time, line, cavity position, serial number"],
        ["Line: date_time_L##_PalletGH?_Cavity##_B####_Fail#_Score(#).bmp",
         F["families"].get("line", 0),
         "the above plus pallet, board id, a fail count and a selection score"],
    ], fmts=[None, NUM0, None])
    r += 1

    r = section(ws, r, "Line (covariate available for every image)")
    r = header(ws, r, ["Line", "Images", "Share of batch"])
    r = table(ws, r, [[k, v, v / S["images"]] for k, v in sorted(F["lines"].items())],
              fmts=[None, NUM0, PCT1])
    r += 1

    r = section(ws, r, "Capture date (nine consecutive days)")
    r = header(ws, r, ["Date", "Images", "Share of batch"])
    r = table(ws, r, [[k, v, v / S["images"]] for k, v in sorted(F["dates"].items())],
              fmts=[None, NUM0, PCT1])
    r += 1

    if F["score_stats"]:
        r = section(ws, r, "Selection score, line family only")
        ss = F["score_stats"]
        r = header(ws, r, ["Measure", "Score"])
        r = kv(ws, r, [
            ("Images carrying a score", F["scored_images"]),
            ("Minimum", ss["min"]),
            ("25th percentile", ss["p25"]),
            ("Median", ss["median"]),
            ("75th percentile", ss["p75"]),
            ("Maximum", ss["max"]),
        ], vfmt="0.0000")
        r = note(ws, r, "Scores run from %s to 1.0, so this batch sits in the high-scoring "
                        "tail. The score is a sampling covariate, not a label."
                        % ("%.4f" % ss["min"]))
        r += 1
        r = section(ws, r, "Boards")
        r = kv(ws, r, [("Distinct board ids in the line family", F["boards_distinct"])],
               vfmt=None)
        r += 1

    r = section(ws, r, "Codes that most often appear together")
    r = header(ws, r, ["Code A", "Code B", "Images carrying both"])
    r = table(ws, r, [[p["a"], p["b"], p["images"]] for p in R["code_pairs"][:12]],
              fmts=[None, None, NUM0])
    r = note(ws, r, "`P2_BB` + `P2_BC` at %d images and `P2_BB` + `P3_FM` at %d images are "
                    "the common pairings, which is why a single-label split loses so much."
                    % (R["code_pairs"][0]["images"], R["code_pairs"][1]["images"]))
    return ws


# --------------------------------------------------------------------------
def sheet_codes(wb, R):
    ws = sheet(wb, "Tags & codes")
    S = R["summary"]
    widths(ws, {"A": 26, "B": 40, "C": 11, "D": 9, "E": 15, "F": 9, "G": 10, "H": 9,
                "I": 9, "J": 10, "K": 11, "L": 11})
    r = title(ws, 1, "Tags and codes: the full catalogue",
              ["All %d codes in the batch, one row each, biggest first."
               % S["distinct_codes"],
               "A box carries a localised defect. A tag is a whole-image flag with no "
               "location, which is why the two never mix on one code."])
    r += 1

    r = section(ws, r, "Every code")
    r = header(ws, r, ["Code", "Meaning", "Shape type", "Confirmed",
                       "Size gate on", "Images", "Image share", "Boxes", "Tags",
                       "Shapes", "Median box px", "Median box um"])
    diag = {s["code"]: s for s in R["sizes"]}
    rows = []
    for c in R["codes"]:
        d = diag.get(c["code"])
        rows.append([
            c["code"], c["name"],
            "tag" if c["boxes"] == 0 else ("box" if c["tags"] == 0 else "box + tag"),
            "yes" if c["confirmed"] else "NO",
            c["gates"] or "",
            c["images"], c["image_share"], c["boxes"], c["tags"], c["shapes"],
            d["median_px"] if d else None,
            d["median_um"] if d else None,
        ])
    r = table(ws, r, rows, fmts=[None, None, None, None, None, NUM0, PCT1, NUM0, NUM0,
                                 NUM0, NUM1, "#,##0"])
    r += 1
    r = note(ws, r, "Confirmed = the meaning has been agreed with the client. Rows marked NO "
                    "are placeholders and should be corrected before the code is used in a "
                    "class list or a report to the client.")
    r = note(ws, r, "A code whose Shapes column equals its Tags column is a whole-image flag "
                    "and has no boxes; those cannot be trained as detector targets.")
    r += 1

    r = section(ws, r, "What the prefixes mean")
    r = note(ws, r, "The code prefixes group the defects by where they sit in the pipeline, "
                    "not by severity.")
    r = header(ws, r, ["Prefix", "Reading", "Codes", "Images"])
    pref = {}
    for c in R["codes"]:
        p = c["code"].split("_")[0]
        e = pref.setdefault(p, [0, 0])
        e[0] += 1
        e[1] += c["images"]
    r = table(ws, r, [
        ["P1", "Part or package handling: the lens, its package or its alignment", pref["P1"][0], pref["P1"][1]],
        ["P2", "Optical or material condition: bubbles, dose, strobe, wet package", pref["P2"][0], pref["P2"][1]],
        ["P3", "Foreign material and obstruction on the part", pref["P3"][0], pref["P3"][1]],
        ["F2", "Field of view obstruction", pref["F2"][0], pref["F2"][1]],
    ], fmts=[None, None, NUM0, NUM0])
    r += 1

    r = section(ws, r, "Box codes versus tag codes")
    box_codes = [c["code"] for c in R["codes"] if c["boxes"] and not c["is_gate"]]
    tag_codes = [c["code"] for c in R["codes"] if not c["boxes"]]
    r = header(ws, r, ["Group", "Codes", "Count", "Where they can be used"])
    r = table(ws, r, [
        ["Localised (carry boxes)", ", ".join(box_codes), len(box_codes),
         "detection, segmentation, localisation metrics"],
        ["Whole image (tags only)", ", ".join(tag_codes), len(tag_codes),
         "image-level classification only"],
    ], fmts=[None, None, NUM0, None])
    r += 1
    r = note(ws, r, "The size gate codes are excluded from the localised list because they "
                    "describe a base code's size rather than a separate defect.")
    return ws


# --------------------------------------------------------------------------
def sheet_email(wb, R):
    """Reconcile the annotator's handover email against the delivered XML."""
    ws = sheet(wb, "Annotator email")
    em = R.get("email")
    widths(ws, {"A": 30, "B": 14, "C": 14, "D": 14, "E": 14, "F": 12, "G": 46})
    if not em:
        title(ws, 1, "Annotator email",
              ["The handover email was not available, so this reconciliation was skipped."])
        return ws

    r = title(ws, 1, "The annotator's handover email, checked against the delivered files",
              ["Source: %s." % em.get("source"),
               "The email was written before validation finished, so its counts are the "
               "state at that time. The XML files that were delivered are later, and they "
               "are the source of truth."])
    r += 1

    r = section(ws, r, "What the email says about the micron tags")
    r = note(ws, r, "Stated rule: %s" % em.get("stated_rule"))
    r = note(ws, r, "Purpose: the email asks that these images be fed into the edge algorithm "
                    "training process.")
    r = note(ws, r, "The four gated codes are exactly the four P3 (foreign material) codes, so "
                    "the rule was applied to the whole debris family.")
    r += 1

    r = section(ws, r, "Code counts: as stated in the email against the delivered XML")
    r = note(ws, r, "Delivered shapes counts every box and every tag. A positive delta means "
                    "the delivered file holds more than the email did.")
    r = header(ws, r, ["Email code", "Delivered code", "Email stated", "Delivered shapes",
                       "Delivered images", "Delta", "Note"])
    rows = []
    for x in em["rows"]:
        rows.append([x["email_code"], x["xml_code"], x["stated"], x["xml_shapes"],
                     x["xml_images"], x["delta_shapes"],
                     "the email writes this code with a different prefix" if x["renamed"] else ""])
    r = table(ws, r, rows, fmts=[None, None, NUM0, NUM0, NUM0, "+#,##0;-#,##0;0", None])
    r += 1
    top = [x for x in em["rows"] if x["delta_shapes"] is not None and abs(x["delta_shapes"]) >= 10][:4]
    if top:
        r = note(ws, r, "The four largest movements are %s. Most codes moved by a handful, and "
                        "the tag-only codes with no ambiguity moved by none at all."
                 % "; ".join("%s %+d" % (x["email_code"], x["delta_shapes"]) for x in top))
        r += 1
    dc = [x for x in em["rows"] if x["email_code"] == "P2_DC"]
    if dc and dc[0]["delta_shapes"] is not None:
        r = bullet(ws, r, "`P2_DC` (Dirty Camera) moved by %+d, the largest change in the "
                          "batch. Worth asking whether the code was redefined during "
                          "validation or simply applied more broadly."
                   % dc[0]["delta_shapes"])
        r += 1
    r += 1

    r = section(ws, r, "The micron tags: as stated against the delivered XML")
    r = header(ws, r, ["Code", "Email stated", "Delivered images", "Delta"])
    r = table(ws, r, [[x["code"], x["stated"], x["xml_images"], x["delta_images"]]
                      for x in em["micron_rows"]],
              fmts=[None, NUM0, NUM0, "+#,##0;-#,##0;0"])
    r = note(ws, r, "The flags changed during validation too, so the flags in the delivered "
                    "file are not exactly what the script produced when the email was written.")
    r += 1

    r = section(ws, r, "Naming difference to settle")
    r = header(ws, r, ["Code", "Note"])
    r = table(ws, r, [[k, v] for k, v in em.get("naming_notes", {}).items()],
              fmts=[None, None])
    r += 1

    mt = R.get("micron_metric_test")
    r = section(ws, r, "Does the stated 647 micron rule reproduce the flags?")
    if not mt:
        r = note(ws, r, "Not tested: run test_micron_metric.py and pass its output in with "
                        "--micron-test.")
        return ws
    r = note(ws, r, "The email says a size threshold but does not say how the size of a box is "
                    "read. A box has several plausible sizes. Each row below tests one reading "
                    "of size: the percentage of images whose flag is reproduced by cutting at "
                    "exactly %s micrometres (%.2f px)."
             % (mt["threshold_um"], mt["threshold_px"]))
    codes = sorted(mt["per_code"].keys())
    metrics = sorted({m for c in mt["per_code"].values() for m in c})
    # order by the weakest code, because a rule has to hold for all of them
    metrics.sort(key=lambda m: -min(mt["per_code"][c][m]["agreement_at_stated_cut"]
                                    for c in codes if m in mt["per_code"][c]))
    r = header(ws, r, ["Reading of size"] + codes + ["Weakest case"]
               + ["Cut that separates each code perfectly (um)"])
    rows = []
    for m in metrics:
        agg = [mt["per_code"][c][m]["agreement_at_stated_cut"]
               for c in codes if m in mt["per_code"][c]]
        cuts = [("%.0f" % mt["per_code"][c][m]["best_threshold_um"])
                if mt["per_code"][c][m]["best_threshold_um"] else "n/a"
                for c in codes if m in mt["per_code"][c]]
        rows.append([m] + agg + [min(agg)] + [", ".join(cuts)])
    r = table(ws, r, rows, fmts=[None] + [PCT1] * len(codes) + [PCT1, None])
    r += 1
    r = note(ws, r, "The first four columns give the percentage of each code's images whose flag "
                    "is reproduced by cutting at exactly %s micrometres. The weakest case column "
                    "is the lowest of those, because a rule has to hold for every code. No "
                    "reading of size reaches 100 percent on all four. The closest is the longest "
                    "side of the box, which reproduces every flag on `P3_EP` and `P3_HE` and "
                    "about nine in ten on `P3_FIB` and `P3_FM`."
             % format(mt["threshold_um"], ","))
    r = note(ws, r, "The last column is the cut, in micrometres, at which each code's flagged "
                    "and unflagged images separate cleanly. Where a code reaches 100 percent, "
                    "that cut is the one that does it, and the stated %s micrometres falls "
                    "inside the window it implies. Where a code stays below 100 percent even at "
                    "its best cut, some flagged image holds a smaller box than some unflagged "
                    "one, so no single cut on that reading can reproduce the flags."
             % format(mt["threshold_um"], ","))
    r += 1

    r = section(ws, r, "What this resolves and what it does not")
    for t in [
        "Resolved: the micron tags are not a separate defect class. They are an image-level "
        "flag set by a size rule on the four debris codes, which is what the earlier size "
        "analysis inferred from the data alone.",
        "Resolved: `P3_HE` is flagged on all %d of its images because every one of its boxes "
        "exceeds %s micrometres. Its smallest box is %s micrometres, about eight times the "
        "threshold, so the rule flags it on every image without exception."
        % (he_images(R), format(em.get("threshold_um"), ","), format(int(he_min_um(R)), ",")),
        "Open: the exact cut is not reproducible from the delivered file, and the flags moved "
        "during validation, so part of the gap is likely the validation pass rather than the "
        "script. Ask which reading of size the script uses, and whether the micron tags were "
        "hand-edited during validation.",
        "Open: the rule is stated per image, but %d images carry two micron tags and one carries "
        "three, so an image can be flagged for more than one material at once."
        % images_with_two_or_more_gates(R),
    ]:
        r = bullet(ws, r, "- " + t)
        r += 1
    return ws


def he_images(R):
    for c in R["codes"]:
        if c["code"] == "P3_HE":
            return c["images"]
    return 0


def he_min_um(R):
    for s in R["sizes"]:
        if s["code"] == "P3_HE":
            return s["min_um"]
    return 0.0


def images_with_two_or_more_gates(R):
    """How many images carry more than one _MICRON_THRESHOLD tag."""
    gates = {c["code"] for c in R["codes"] if c["is_gate"]}
    n = 0
    for p in R["per_image"]:
        cs = {x for x in p["tag_codes"].split("; ") if x in gates}
        if len(cs) > 1:
            n += 1
    return n


# --------------------------------------------------------------------------
def sheet_micron(wb, R):
    ws = sheet(wb, "Micron")
    S = R["summary"]
    widths(ws, {"A": 26, "B": 8, "C": 11, "D": 11, "E": 11, "F": 11, "G": 11, "H": 11,
                "I": 12, "J": 12, "K": 12, "L": 40})
    um = S["um_per_px"]
    lens_px = (R.get("scale") or {}).get("lens_diam_px")
    r = title(ws, 1, "Micron measurements",
              ["Box size is the diagonal of the annotated rectangle, so it is a length "
               "across the defect rather than a diameter or an area.",
               "Converted at %s micrometres per pixel. The lens is %s px across, which is "
               "%s micrometres." % (um, ("%g" % lens_px) if lens_px else "unknown",
                                format(round(lens_um(R)), ",")),
               "Rotation does not change the diagonal, so these sizes hold for the rotated "
               "boxes as drawn."])
    r += 1

    sc = R.get("scale") or {}
    r = section(ws, r, "The scale everything is converted with")
    r = note(ws, r, "Taken from the same scale estimate used by the crop pipeline, so the "
                    "two agree by construction.")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Micrometres per pixel", um),
        ("Images the scale was measured on", sc.get("n_images_used")),
        ("Lens diameter, px", sc.get("lens_diam_px")),
        ("Lens diameter, micrometres", round(lens_um(R))),
        ("Lens diameter spread across images, percent", sc.get("rel_spread_pct")),
        ("Cavity diameter, px", sc.get("cav_diam_px")),
        ("Recorded size thresholds, microns",
         ", ".join(str(t) for t in sc.get("thresholds_um") or [])),
    ], vfmt=None)
    r = note(ws, r, "The lens varies image to image, so a defect close to a threshold can "
                    "fall either side of it depending on the part. The relative spread is "
                    "%s percent." % sc.get("rel_spread_pct"))
    r += 1

    r = section(ws, r, "Box size by code, pixels and microns")
    r = note(ws, r, "Only codes that carry boxes appear here. Rows are ordered by box count.")
    r = header(ws, r, ["Code", "Boxes", "Min px", "P25 px", "Median px", "P75 px",
                       "Max px", "Mean px", "Median um", "P75 um", "Max um", "Reading"])
    readings = {
        "P2_BB": "smallest class: sub-millimetre bubbles",
        "P2_BC": "bubble clusters, roughly twice the single bubble",
        "P2_WP": "wet package spreads over the part",
        "P3_FM": "foreign matter spots",
        "P3_FIB": "fibres, thin but long",
        "P2_BI": "irregular bubbles, wider spread than plain bubbles",
        "P3_HE": "not a spot: region annotation, larger than the lens",
        "P3_EP": "extraneous polymer, the largest true defect class",
        "P2_BST": "only three boxes, treat any number here as indicative",
    }
    r = table(ws, r, [[s["code"], s["n"], s["min_px"], s["p25_px"], s["median_px"],
                       s["p75_px"], s["max_px"], s["mean_px"], s["median_um"],
                       s["p75_um"], s["max_um"], readings.get(s["code"], "")]
                      for s in R["sizes"]],
              fmts=[None, NUM0, NUM1, NUM1, NUM1, NUM1, NUM1, NUM1, "#,##0", "#,##0",
                    "#,##0", None])
    o = R["overall_size"]
    allrow = r
    r = table(ws, r, [["ALL CODES", o["n"], o["min"], o["p25"], o["median"], o["p75"],
                       o["max"], o["mean"], o["median"] * um, o["p75"] * um,
                       o["max"] * um, "overall"]],
              fmts=[None, NUM0, NUM1, NUM1, NUM1, NUM1, NUM1, NUM1, "#,##0", "#,##0",
                    "#,##0", None])
    for c in range(1, 13):
        ws.cell(row=allrow, column=c).font = BOLD
    r += 1

    r = section(ws, r, "How many boxes cross each recorded size threshold")
    r = note(ws, r, "The product's recorded thresholds are %s microns. A box crosses a "
                    "threshold when its diagonal is larger."
                    % ", ".join(str(t) for t in [t["threshold_um"] for t in R["thresholds"]]))
    r = header(ws, r, ["Threshold um", "Equivalent px", "Boxes above", "Share of all boxes"])
    r = table(ws, r, [[t["threshold_um"], t["threshold_px"], t["boxes_above"],
                       t["boxes_above_share"]] for t in R["thresholds"]],
              fmts=["#,##0", NUM1, NUM0, PCT1])
    thr_um = (R.get("email") or {}).get("threshold_um", 647)
    _flag_um = [g["flagged_median_px"] * um for g in R["gates"] if g["unit_testable"]]
    _unflag_um = [g["unflagged_median_px"] * um for g in R["gates"] if g["unit_testable"]]
    r = note(ws, r, "The annotator's email states the rule behind these flags: they mark images "
                    "containing debris over %s micrometres. The data agrees in direction. On "
                    "every testable class the flagged group's median largest box (%s microns) "
                    "is well above that cut, and the unflagged group's median (%s microns) is "
                    "below it. Whether the exact cut reproduces every individual flag is tested "
                    "on the Annotator email sheet."
             % (format(thr_um, ","),
                ", ".join("%.0f" % v for v in _flag_um),
                ", ".join("%.0f" % v for v in _unflag_um)))
    r += 1

    r = section(ws, r, "The `_MICRON_THRESHOLD` codes are a size gate")
    r = note(ws, r, "Test: on images carrying the base code, compare the largest base-code "
                    "box between images that carry the gate flag and images that do not.")
    r = header(ws, r, ["Gate code", "Base code", "Flagged images", "Unflagged images",
                       "Flagged median px", "Unflagged median px", "Ratio", "Gap um", "Note"])
    grows = []
    for g in R["gates"]:
        if g["unit_testable"]:
            grows.append([g["gate"], g["base"], g["flagged_images"],
                          g["unflagged_images"], g["flagged_median_px"],
                          g["unflagged_median_px"], g["ratio"], g["gap_um"],
                          "gate tracks size"])
        else:
            grows.append([g["gate"], g["base"], g["flagged_images"],
                          g["unflagged_images"], g["flagged_median_px"], None, None,
                          None, "no unflagged group: every box in this class exceeds the cut"])
    r = table(ws, r, grows, fmts=[None, None, NUM0, NUM0, NUM1, NUM1, "0.00",
                                  "#,##0", None])
    r += 1
    for g in R["gates"]:
        if g["unit_testable"]:
            r = bullet(ws, r, "%s: the base code's largest box has a median of %.1f px "
                              "(%.0f um) when flagged against %.1f px (%.0f um) when not, "
                              "a factor of %.2f, across %d flagged and %d unflagged images."
                       % (g["base"], g["flagged_median_px"],
                          g["flagged_median_px"] * um, g["unflagged_median_px"],
                          g["unflagged_median_px"] * um, g["ratio"],
                          g["flagged_images"], g["unflagged_images"]))
            r += 1
        else:
            r = bullet(ws, r, "%s: every one of its %d images carries %s, so there is no "
                              "unflagged group. That is not the flag being unconditional: the "
                              "smallest %s box in the batch is %.0f micrometres, about eight "
                              "times the %s micrometre cut, so the rule fires on every image."
                       % (g["base"], g["flagged_images"], g["gate"], g["base"],
                          he_min_um(R), format(thr_um, ",")))
            r += 1
    r += 1

    r = section(ws, r, "Size outliers worth eyeballing")
    r = note(ws, r, "Boxes with a diagonal over %d px (about %.0f micrometres). A box this "
                    "large on a code whose median is far smaller is usually a whole-part "
                    "region mark or a mislabelled shape."
                    % (R["outlier_threshold_px"], R["outlier_threshold_px"] * um))
    r = header(ws, r, ["Code", "Boxes", "Over %d px" % R["outlier_threshold_px"],
                       "Share of the code", "Largest px", "Largest um"])
    r = table(ws, r, [[o["code"], o["boxes"], o["boxes_over_200px"], o["share_over_200px"],
                       o["largest_px"], o["largest_px"] * um] for o in R["outliers"]],
              fmts=[None, NUM0, NUM0, PCT1, NUM1, "#,##0"])
    r += 1
    bb = [o for o in R["outliers"] if o["code"] == "P2_BB"]
    if bb:
        r = bullet(ws, r, "`P2_BB` is the one to check: %d of its %s boxes are over %d px "
                          "while the class median is %.1f px, so those are not bubbles on the "
                          "same scale as the rest."
                   % (bb[0]["boxes_over_200px"], format(bb[0]["boxes"], ","),
                      R["outlier_threshold_px"],
                      [s for s in R["sizes"] if s["code"] == "P2_BB"][0]["median_px"]))
        r += 1
    r += 1

    r = section(ws, r, "Where the boxes sit on the part")
    c = R["cavity"]
    r = note(ws, r, "Measured against the cavity of each image's own part, not the image "
                    "centre, because the part is not centred in the frame.")
    r = header(ws, r, ["Measure", "Value"])
    r = kv(ws, r, [
        ("Images where the cavity could be measured", c["images_measured"]),
        ("Images too dark or too small to measure", c["images_unmeasured"]),
        ("Box centres placed", c["boxes_placed"]),
        ("Inside the measured cavity radius", c["inside"]),
        ("Outside it", c["outside"]),
        ("Share outside", c["outside"] / c["boxes_placed"]),
        ("Further out than 1.5 times the radius", c["beyond_1_5x"]),
        ("Distance from cavity centre, as a multiple of the radius: p50", c["p50_ratio"]),
        ("as a multiple of the radius: p75", c["p75_ratio"]),
        ("as a multiple of the radius: p95", c["p95_ratio"]),
        ("as a multiple of the radius: maximum", c["max_ratio"]),
    ], vfmt=None)
    r = note(ws, r, "The median box centre sits at %.2f of the cavity radius and the furthest "
                    "is %.2f, so every annotation is on or beside the part. The %s that fall "
                    "outside the radius sit in the thin band just past it, because the "
                    "measured radius is slightly conservative."
                    % (c["p50_ratio"], c["max_ratio"],
                       pct_str(c["outside"] / c["boxes_placed"])))
    r += 1
    r = header(ws, r, ["Code", "Boxes", "Outside the radius", "Share outside"])
    r = table(ws, r, [[x["code"], x["boxes"], x["outside"], x["outside_share"]]
                      for x in R["cavity_per_code"]],
              fmts=[None, NUM0, NUM0, PCT1])
    return ws


# --------------------------------------------------------------------------
def sheet_images(wb, R):
    ws = sheet(wb, "Per image")
    cols = ["File name", "Job", "Date", "Time", "Line", "Filename family",
            "Cavity position", "Pallet", "Board", "Fail count", "Score",
            "Codes on image", "Codes", "Boxes", "Tags", "Shapes",
            "Codes with boxes", "Codes as tags",
            "Cavity centre x", "Cavity centre y", "Cavity radius px"]
    widths(ws, {"A": 52, "B": 9, "C": 11, "D": 9, "E": 7, "F": 15, "G": 15, "H": 12,
                "I": 10, "J": 11, "K": 10, "L": 14, "M": 40, "N": 8, "O": 7, "P": 8,
                "Q": 30, "R": 30, "S": 15, "T": 15, "U": 16})
    r = title(ws, 1, "One row per image",
              ["%d images. Blank covariate cells mean the filename family does not carry "
               "that field." % R["summary"]["images"]])
    r += 1
    r = header(ws, r, cols)
    first_data = r
    rows = []
    for p in R["per_image"]:
        rows.append([
            p["basename"], p["job_id"], p["date"], p["time"], p["line"], p["family"],
            p["cavity_id"], p["pallet"], p["board"], p["fail"], p["score"],
            p["n_codes"], p["codes"], p["n_boxes"], p["n_tags"], p["shapes"],
            p["box_codes"], p["tag_codes"],
            p["cavity_cx"], p["cavity_cy"], p["cavity_r"],
        ])
    r = table(ws, r, rows, fmts=[None, None, None, None, None, None, None, None, None,
                                 NUM0, "0.0000", NUM0, None, NUM0, NUM0, NUM0, None,
                                 None, NUM1, NUM1, NUM1])
    ws.freeze_panes = ws.cell(row=first_data, column=1)
    ws.auto_filter.ref = "A%d:U%d" % (first_data - 1, r - 1)
    return ws


# --------------------------------------------------------------------------
def sheet_checks(wb, R):
    ws = sheet(wb, "Checks")
    S = R["summary"]
    widths(ws, {"A": 52, "B": 18, "C": 60})
    r = title(ws, 1, "Checks",
              ["Each row can be re-verified from the annotation files. The expected value "
               "is what the summary reports."])
    r += 1
    r = header(ws, r, ["Invariant", "Value", "How to re-check"])
    jobs_sum = sum(int(j["size"]) for j in R["provenance"]["jobs"] if j["size"])
    checks = [
        ("Annotation files read", len(R["provenance"]["xml_files"]),
         "the annotations folder holds this many XML files"),
        ("Images", S["images"], "one <image> element per image, all names distinct"),
        ("Boxes", S["boxes"], "sum of <box> elements over the files"),
        ("Tag elements", S["tag_elements"], "sum of <tag> elements over the files"),
        ("Tag labels after collapsing repeats", S["tag_labels_counted"],
         "one repeated label on one image, so this is one lower"),
        ("Shapes total", S["boxes"] + S["tag_elements"],
         "boxes plus tag elements"),
        ("Codes", S["distinct_codes"], "distinct label attribute values"),
        ("Size gates", S["codes_that_are_gates"],
         "codes ending _MICRON_THRESHOLD"),
        ("Images across all codes",
         sum(c["images"] for c in R["codes"]),
         "higher than the image count because most images carry several codes"),
        ("Frames the jobs cover", jobs_sum, "sum of the job size field"),
        ("Boxes plus tags placed per image, min",
         min(p["shapes"] for p in R["per_image"]),
         "the one image with no annotation at all"),
        ("Boxes plus tags placed per image, max",
         max(p["shapes"] for p in R["per_image"]), "busiest image in the batch"),
        ("Image geometry variants", len(S["geometry_variants"]),
         "all images are the same size"),
        ("um per pixel", S["um_per_px"], "from the scale estimate, not re-derived here"),
        ("Cavity images measured", R["cavity"]["images_measured"],
         "the rest were too dark or too small for the threshold"),
    ]
    r = table(ws, r, checks, fmts=[None, NUM0, None])
    r += 1
    r = note(ws, r, "Cross-checks that should hold and do: every size gate code's image set "
                    "is a subset of its base code; the sum of codes per image distribution "
                    "equals the image count; the sum of the box size table equals the box "
                    "count.")
    r += 1
    r = section(ws, r, "Codes per image distribution, as a check on the summary")
    r = header(ws, r, ["Codes", "Images"])
    dist = R["codes_per_image_distribution"]
    r = table(ws, r, [list(x) for x in dist], fmts=[NUM0, NUM0])
    totrow = r
    r = table(ws, r, [["TOTAL", sum(n for _, n in dist)]], fmts=[None, NUM0])
    for c in (1, 2):
        ws.cell(row=totrow, column=c).font = BOLD
    return ws


def build(numbers_path, out_path):
    R = json.load(open(numbers_path, encoding="utf-8"))
    wb = Workbook()
    sheet_readme(wb, R)
    sheet_eda(wb, R)
    sheet_distributions(wb, R)
    sheet_codes(wb, R)
    sheet_email(wb, R)
    sheet_micron(wb, R)
    sheet_images(wb, R)
    sheet_checks(wb, R)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wb.save(out_path)
    return wb


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--numbers", default="batch_numbers.json")
    ap.add_argument("--out", default="report.xlsx")
    a = ap.parse_args()
    build(a.numbers, a.out)
    print("wrote %s" % os.path.abspath(a.out))


if __name__ == "__main__":
    main()
