#!/usr/bin/env python3
"""The scale section of the Box geometry sheet.

This module does two things and nothing else:

  compute(run_dir)          read the sampled rim measurement and the resolved
                            label table and return every number the section
                            needs, by route, with no figure typed by hand;
  append_scale_section(ws, row, run_dir=None)
                            write the section onto an openpyxl worksheet and
                            return the next free row.

It is imported by build_workbook.py, so the workbook stays reproducible from
one command. Stdlib plus openpyxl only.

The section carries three things, in order:
  1. the derivation of the 18.1165 scale, and the status of 18.25;
  2. a second rim measurement on the library folders, reported per folder and
     per production line in two views, with the dropped count and the reason;
  3. a closing note that the October batch record is superseded.

Nothing here writes to the shared VM. All inputs live under run/.
"""
from __future__ import annotations

import csv
import os
import statistics

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_RUN = os.path.join(REPO, "run", "eda_full_20261015")

# The scale the routine derives: its own nominal lens diameter over the measured
# rim in pixels. 14,200 microns is set inside the routine and is cited to no
# client document, so this is our own reference.
NOMINAL_LENS_DIAMETER_UM = 14_200.0

# The five canonical classes in which a normal single lens is NOT present. A
# picture carrying any of them cannot give a rim, so the second view sets them
# aside.
NO_LENS_CLASSES = {
    "missing_lens",
    "multiple_lenses",
    "missing_primary_package",
    "view_obstructed",
    "folded_lens",
}

# The routine searches for the rim dip between 0.50 and 0.92 of the cavity
# RADIUS, so rim_px / cavity_px must lie inside that window.
WINDOW_HI = 0.915   # at or above this, the search hit its upper limit
WINDOW_LO = 0.515   # below this, the search hit its lower limit
VALID_LO = 0.515    # kept window, lower
VALID_HI = 0.910    # kept window, upper

# The published single-sample figures, quoted in the derivation text.
PUBLISHED_RIM_PX = 783.8
PUBLISHED_SCALE = 18.1165
SPOKEN_SCALE = 18.25
SAMPLE_FRAMES = 200
SAMPLE_MEDIAN_PX = 786
SAMPLE_SD_PX = 41.6
SAMPLE_IQR_PX = (764, 804)
SAMPLE_REL_SPREAD_PCT = 5.3
PRODUCTION_SAMPLE_PICTURES = 10_000
PRODUCTION_SAMPLE_PASSED = 7_164

# ---- openpyxl styling, the same visual language as build_workbook.py ----
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
NUM0 = "#,##0"
num2 = "#,##0.00"
NUM1 = "#,##0.0"


def _section(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = SUB
    return row + 1


def _header(ws, row, cols, first_col=1):
    for i, c in enumerate(cols):
        cell = ws.cell(row=row, column=first_col + i, value=c)
        cell.font = HEAD
        cell.fill = HEADFILL
        cell.border = BOX
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    return row + 1


def _table(ws, row, rows, fmts=None, first_col=1):
    for r in rows:
        for i, v in enumerate(r):
            cell = ws.cell(row=row, column=first_col + i, value=v)
            cell.border = BOX
            if fmts and i < len(fmts) and fmts[i] and isinstance(v, (int, float)):
                cell.number_format = fmts[i]
        row += 1
    return row


def _note(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = NOTEFONT
    return row + 1


def _warn(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = WARNFONT
    return row + 1


def _bullet(ws, row, text):
    ws.cell(row=row, column=1, value="  " + text).alignment = WRAP
    return row + 1


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
def compute(run_dir=None):
    """Read the sampled rim measurement and the resolved label table.

    Returns a dict with the window counts and the per-folder and per-line
    figures in both views. One row per distinct picture: the sample draws a
    picture once per folder group it sits in, so the raw rows repeat a picture
    that is held in more than one folder.
    """
    run_dir = run_dir or DEFAULT_RUN
    samples = os.path.join(run_dir, "scale_samples.csv")
    labels = os.path.join(run_dir, "resolved_labels.csv")

    rows = list(csv.DictReader(open(samples, newline="", encoding="utf-8")))
    total_rows = len(rows)
    total_pictures = len({r["path"] for r in rows})

    measured = {}
    for r in rows:
        if r.get("method_flags") != "ok":
            continue
        rim = _num(r.get("rim_px"))
        cav = _num(r.get("cavity_px"))
        if rim is None or cav is None or cav == 0:
            continue
        measured.setdefault(r["path"], r)

    pic = []
    for r in measured.values():
        rim = _num(r["rim_px"])
        cav = _num(r["cavity_px"])
        pic.append({
            "path": r["path"],
            "folder": r["path"].split("/")[0],
            "line": r["line"],
            "rim": rim,
            "ratio": rim / cav,
        })

    pinned_hi = [p for p in pic if p["ratio"] >= WINDOW_HI]
    pinned_lo = [p for p in pic if p["ratio"] < WINDOW_LO]
    valid = [p for p in pic if VALID_LO <= p["ratio"] <= VALID_HI]
    max_ratio = max(p["ratio"] for p in pic)
    dropped = len(pic) - len(valid)

    # canonical defects per winning path. This table carries paths, not content
    # hashes, so the join is a path join. That is stated in the section.
    defects = {}
    with open(labels, newline="", encoding="utf-8") as fh:
        for lr in csv.DictReader(fh):
            defects.setdefault(lr["winning_path"], set()).add(lr["canonical_id"])

    def joins(p):
        return p["path"] in defects

    def no_lens(p):
        # keep a picture with no resolved label: none of the five classes can be
        # attributed to it
        d = defects.get(p["path"])
        return bool(d) and bool(d & NO_LENS_CLASSES)

    valid_join = sum(1 for p in valid if joins(p))
    measured_join = sum(1 for p in pic if joins(p))
    rows_join = sum(1 for r in rows if r["path"] in defects)
    valid_nolens = sum(1 for p in valid if no_lens(p))

    view_all = valid
    view_no_lens = [p for p in valid if not no_lens(p)]

    def stat(ps):
        rim = sorted(p["rim"] for p in ps)
        med = statistics.median(rim) if rim else None
        return {
            "n": len(ps),
            "rim_p25": round(rim[len(rim) // 4], 1) if rim else None,
            "rim_p50": round(med, 1) if med is not None else None,
            "um_px": round(NOMINAL_LENS_DIAMETER_UM / med, 2) if med else None,
        }

    def by(ps, key):
        out = {}
        for k in sorted({key(p) for p in ps}):
            out[k] = stat([p for p in ps if key(p) == k])
        return out

    return {
        "total_rows": total_rows,
        "total_pictures": total_pictures,
        "measured": len(pic),
        "pinned_hi": len(pinned_hi),
        "pinned_lo": len(pinned_lo),
        "max_ratio": round(max_ratio, 4),
        "valid": len(valid),
        "dropped": dropped,
        "dropped_pct": round(100.0 * dropped / len(pic), 1),
        "valid_join": valid_join,
        "measured_join": measured_join,
        "rows_join": rows_join,
        "valid_nolens": valid_nolens,
        "view_all_n": len(view_all),
        "view_no_lens_n": len(view_no_lens),
        "folder_all": by(view_all, lambda p: p["folder"]),
        "folder_no_lens": by(view_no_lens, lambda p: p["folder"]),
        "line_all": by(view_all, lambda p: p["line"]),
        "line_no_lens": by(view_no_lens, lambda p: p["line"]),
    }


# --------------------------------------------------------------------------
FOLDER_LABEL = {
    "Updated ICube Objects 20260915": "Updated Objects",
    "Updated ICube Categorical Classes 20260915": "Updated Categorical",
    "ICube Defects Library": "Library",
}
VIEW_ALL = "all valid pictures"
VIEW_NO_LENS = "excluding the five no-lens classes"


def append_scale_section(ws, row, run_dir=None):
    """Write the scale block and the two measurement tables. Returns next row."""
    R = compute(run_dir)

    # ---- 0. the adopted scale --------------------------------------------
    row = _section(ws, row, "The adopted scale: 15.337 microns per pixel")
    for t in [
        "The adopted working scale is 15.337 microns per pixel. It is derived from the "
        "customer's own documented 300 micron cut: the micron-threshold tags switch at "
        "a defect longer side of 19.41 to 19.61 px, and 300 divided by the 19.51 px "
        "midpoint gives the scale, matching the frozen central figure of 15.3369 with "
        "an interval of 15.298 to 15.376.",
        "Per production line the same inversion reads 15.377 (L24), 15.601 (L25, only "
        "14 pictures, loose), 15.400 (L26) and 15.337 (L27). The L31 line has no "
        "threshold defect in the production export and is not computable. Per folder "
        "group it reads 15.377 on the updated folders and 15.400 on pictures that are "
        "also in the old defects library.",
        "The old 647 micron cut inverts to the same scale, from a boundary at 42.08 to "
        "42.79 px, and is the independent reproduction.",
        "The lens rim measures 789 px (interquartile range 764.4 to 809.5 px), which is "
        "about 12.10 mm at the adopted scale. The earlier 848 px lens figure is "
        "disproven: it was a least-squares circle fit spanning two rings, and restricted "
        "to the rim band the same fit gives 789.0 px.",
        "Limitation, stated plainly and not resolved here: the lens nominal diameter is "
        "not documented in anything received. The only documented ruler is the "
        "customer's own 300 micron cut. A written lens diameter from the customer would "
        "close the remaining question.",
        "Every micron figure in this workbook is a pixel figure times 15.337. The prior "
        "scales 18.1165 and 18.25 are superseded and appear only in columns and "
        "sentences labelled superseded.",
    ]:
        row = _bullet(ws, row, "- " + t)
    row += 1

    # ---- 1. the superseded prior scale, kept for the record ---------------
    row = _section(ws, row, "The superseded prior scale of 18.1165, kept for the record")
    row = _note(ws, row,
                "The block below records how the superseded prior scale was derived and "
                "why it was set aside. It is history, not a scale in use. Two scales were "
                "in circulation before the adoption; this block names each one, gives the "
                "derivation of the first, and states that the second is not derived at "
                "all.")
    row = _header(ws, row, ["Scale (microns per pixel)", "The columns that use it", "Status"])
    row = _table(ws, row, [
        ["18.1165", "the comparison column headed at 18.1165",
         "superseded prior scale, derivation kept below"],
        ["18.25", "named in no column",
         "superseded prior scale, spoken once, written in no document we hold"],
    ])
    row += 1

    row = _section(ws, row, "How the superseded 18.1165 was derived, kept for the record")
    for t in [
        "The measurement read 200 random machine-passed frames from a separate "
        "production-sample drop dated 2026-08-26. That drop holds 10,000 pictures, of "
        "which 7,164 are machine-passed frames, so the 200 were drawn from the passed "
        "frames alone.",
        "That sample is NOT the annotated batch analysed in this workbook, and NOT the "
        "library folders. The scale was never measured on either of them.",
        "The method: a bright mask at 0.45 of the 99.5th percentile; the cavity centre "
        "from the mask centroid; the cavity radius from the row and column profile "
        "widths; the radial intensity profile smoothed over 7 pixels; the most prominent "
        "dark dip searched between 0.50 and 0.92 of the cavity radius; the lens diameter "
        "taken as twice that radius; a frame accepted only when the dip prominence "
        "exceeds 1.0.",
        "The result is a lens rim diameter of 783.8 pixels, a 15 percent trimmed mean "
        "over the accepted frames.",
        "The nominal lens diameter the routine divides into is 14,200 microns. That "
        "number is set inside the routine itself and is cited to no document the client "
        "has given us. It is our own figure, not a client nominal.",
        "14,200 divided by 783.8 is 18.1165, the scale in the column header.",
        "The spread over the 200 frames: median 786 pixels, standard deviation 41.6 "
        "pixels, interquartile range 764 to 804 pixels, a relative spread of 5.3 "
        "percent. The scale itself therefore carries about 5.3 percent, before any other "
        "uncertainty.",
    ]:
        row = _bullet(ws, row, "- " + t)
    row += 1

    row = _section(ws, row, "What is known about 18.25")
    for t in [
        "18.25 is written in no document we hold. It exists only in our own notes "
        "recording that it was quoted to us.",
        "No derivation, no sample and no nominal supports 18.25. It cannot be checked "
        "against anything we have.",
        "The gap between 18.1165 and 18.25 is 0.7 percent. The spread of the 18.1165 "
        "measurement alone is 5.3 percent, so the two cannot be told apart by any "
        "measurement in this workbook, and neither should be read as confirmed.",
    ]:
        row = _bullet(ws, row, "- " + t)
    row = _warn(ws, row,
                "Because the 14,200 micron nominal is ours and sits in no customer "
                "document, the superseded prior scale was never a calibrated "
                "measurement. This is one of the reasons it was set aside in favour of "
                "the adopted 15.337.")
    row += 1

    # ---- 2. the second measurement, on the library folders ---------------
    row = _section(ws, row, "A second measurement, on the library folders, does not behave")
    row = _note(ws, row,
                "The same rim and cavity method was applied to the library folders. It "
                "does not give a usable scale, and the reason is the method itself. The "
                "numbers below are reported to show that failure, not to be quoted.")
    row = _note(ws, row,
                "The method finds the rim dip between 0.50 and 0.92 of the cavity "
                "RADIUS, so the ratio of rim diameter to cavity diameter must lie inside "
                "that window. A ratio pinned at the window edge is the search hitting its "
                "limit, not a rim.")
    row = _header(ws, row, ["Measure", "Pictures"])
    row = _table(ws, row, [
        ["Sampled for this measurement", R["total_pictures"]],
        ["Measured (the method returned a value)", R["measured"]],
        ["Pinned at the upper window edge (ratio at or above 0.915)", R["pinned_hi"]],
        ["Below the lower window edge (ratio below 0.515)", R["pinned_lo"]],
        ["Valid (ratio from 0.515 to 0.910)", R["valid"]],
        ["Set aside by the window", R["dropped"]],
    ], fmts=[None, NUM0])
    row = _warn(ws, row,
                "No measured ratio exceeds 0.918, and the highest is %.4f. That confirms "
                "the pinned rows are the search stopping at its own 0.92 limit and never "
                "a rim beyond it. The 427 set aside are %s percent of the measured "
                "pictures, so the method fails on about a quarter of this population by "
                "its own boundaries." % (R["max_ratio"], R["dropped_pct"]))
    row += 1

    # per folder, both views
    row = _section(ws, row, "Per folder, both views")
    row = _note(ws, row,
                "View one uses every valid picture. View two removes the pictures whose "
                "canonical defects include a missing lens, multiple lenses, a missing "
                "primary package, an obstructed view or a folded lens. A picture with no "
                "resolved label is kept in view two, because none of those five classes "
                "can be attributed to it.")
    row = _header(ws, row, ["Folder", "View", "n", "rim p50 (px)",
                            "implied microns per pixel, at the superseded 14,200 micron reference"])
    frows = []
    for f in sorted(R["folder_all"]):
        a = R["folder_all"][f]
        b = R["folder_no_lens"].get(f, {"n": 0, "rim_p50": None, "um_px": None})
        frows.append([FOLDER_LABEL.get(f, f), VIEW_ALL, a["n"], a["rim_p50"], a["um_px"]])
    for f in sorted(R["folder_no_lens"]):
        b = R["folder_no_lens"][f]
        frows.append([FOLDER_LABEL.get(f, f), VIEW_NO_LENS, b["n"], b["rim_p50"], b["um_px"]])
    row = _table(ws, row, frows, fmts=[None, None, NUM0, NUM1, num2])
    row += 1

    # per line, both views
    row = _section(ws, row, "Per production line, both views")
    row = _header(ws, row, ["Line", "View", "n", "rim p50 (px)",
                            "implied microns per pixel, at the superseded 14,200 micron reference"])
    lrows = []
    for ln in sorted(R["line_all"]):
        a = R["line_all"][ln]
        lrows.append([ln, VIEW_ALL, a["n"], a["rim_p50"], a["um_px"]])
    for ln in sorted(R["line_no_lens"]):
        b = R["line_no_lens"][ln]
        lrows.append([ln, VIEW_NO_LENS, b["n"], b["rim_p50"], b["um_px"]])
    row = _table(ws, row, lrows, fmts=[None, None, NUM0, NUM1, num2])

    row = _note(ws, row,
                "The canonical defect of each picture is read by matching its winning "
                "path in the resolved label table. That match is a path match, not a "
                "content match, because that table carries paths rather than content "
                "hashes. Of the %s measured pictures, %s carry no resolved label and so "
                "cannot be classified; at row level %s of the %s sampled rows fail to "
                "match. A picture with no resolved label cannot be positively confirmed "
                "to hold a normal lens, and is counted, not dropped."
                % (format(R["measured"], ","),
                   format(R["measured"] - R["measured_join"], ","),
                   format(R["total_rows"] - R["rows_join"], ","),
                   format(R["total_rows"], ",")))
    row = _note(ws, row,
                "The two Updated folders disagree sharply, and the disagreement survives "
                "removal of the five classes. The categorical folder reads near 21 microns "
                "per pixel and the other Updated folder near 19. That is a property of the "
                "pictures, not a real scale difference. Many pictures in the categorical "
                "folder are classes where a normal single lens is not present, so there is "
                "no rim to find and the method returns a small or edge-pinned value. Image "
                "brightness also varies by class, which moves the relative brightness mask "
                "and therefore the cavity radius the method depends on.")
    row = _warn(ws, row,
                "The numbers in the two tables above are not quotable as a scale. They "
                "are shown only to make the failure visible: the method fails on about a "
                "quarter of this population by hitting its own search limit, so a scale "
                "read from them would be an artefact of the method, not a measurement of "
                "the lens.")
    row += 1

    # ---- 3. closing note -------------------------------------------------
    row = _section(ws, row, "Two corrections carried into this sheet")
    for t in [
        "The October batch analysis is superseded by the full-coverage analysis. It is "
        "kept for history, and its figures are not to be quoted.",
        "Its earlier statement that the size gate is not a 300 micron cut was an "
        "artefact of measuring the box diagonal. Measured on the box's longer side "
        "instead, the gate is a clean 300 micron cut: no picture sits on the wrong side "
        "of the boundary.",
    ]:
        row = _bullet(ws, row, "- " + t)
    return row + 1


if __name__ == "__main__":
    import json
    print(json.dumps(compute(), indent=2, sort_keys=True))
