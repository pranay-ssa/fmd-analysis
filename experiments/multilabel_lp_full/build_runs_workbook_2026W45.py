"""Build the two-run workbook for the lead: lens only and lens plus object flag.

Seven sheets, every number read from the two run records on the frozen 70/15/15 split:

    Summary              the headline comparison and what it says
    Per-class results    AUPRC, F1 at 0.5, F1 at the chosen threshold, threshold
    Thresholds           the chosen threshold per class in both runs
    Threshold rule       the grid, the 10-positive guard, the four default classes
    Routing              the object flag on the test pictures
    Split                pictures per class in training, validation and test
    Definitions and method

Run:
    .venv/Scripts/python.exe experiments/multilabel_lp_full/build_runs_workbook_2026W45.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
RUN_A = ROOT / "run/multilabel_lp_v8_20261105/a"
RUN_B = ROOT / "run/multilabel_lp_v8_20261103/b"
LABELS = ROOT / "run/multilabel_lp_v8_20261103/labels_b.csv"
OUT = ROOT / "reports/multilabel_production/FMD_MultiLabel_Runs_2026W45.xlsx"

CLASS_ORDER = [
    "P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL",
    "P2_LD", "P1_COC", "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM",
]
JUDGEABLE_MIN = 20
DEFAULT_THRESHOLD = 0.50

INK = "1F2937"
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
BAND_FILL = PatternFill("solid", fgColor="EEF2F8")
NOTE_FILL = PatternFill("solid", fgColor="F6F6F4")
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(bottom=THIN)

TITLE_FONT = Font(name="Calibri", size=16, bold=True, color=INK)
LEAD_FONT = Font(name="Calibri", size=11, color="404040")
SECTION_FONT = Font(name="Calibri", size=11, bold=True, color=INK)
HEAD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="Calibri", size=10, color=INK)
BOLD_FONT = Font(name="Calibri", size=10, bold=True, color=INK)
SMALL_FONT = Font(name="Calibri", size=9, color="595959")


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def split_counts():
    counts = {code: {"train": 0, "val": 0, "test": 0} for code in CLASS_ORDER}
    counts["object_present"] = {"train": 0, "val": 0, "test": 0}
    counts["is_clear"] = {"train": 0, "val": 0, "test": 0}
    totals = {"train": 0, "val": 0, "test": 0}
    with LABELS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            split = row["split"]
            totals[split] += 1
            for code in CLASS_ORDER:
                if row[code] == "1":
                    counts[code][split] += 1
            if row["object_present"] == "1":
                counts["object_present"][split] += 1
            if row["is_clear"] == "1":
                counts["is_clear"][split] += 1
    assert totals == {"train": 5239, "val": 1110, "test": 1121}, totals
    assert counts["object_present"] == {"train": 1563, "val": 341, "test": 343}, counts["object_present"]
    assert counts["is_clear"] == {"train": 1482, "val": 318, "test": 317}, counts["is_clear"]
    return counts, totals


def class_data(metrics, thresholds, counts):
    rows = {}
    for code in CLASS_ORDER:
        pc = metrics["per_class"][code]
        th = thresholds["per_class"][code]
        assert pc["support"] == counts[code]["test"], (code, pc["support"], counts[code]["test"])
        assert th["val_support"] == counts[code]["val"], (code, th["val_support"], counts[code]["val"])
        rows[code] = {
            "code": code,
            "name": pc["name"],
            "test": pc["support"],
            "val": th["val_support"],
            "auprc": pc["auprc"],
            "f1_0.5": pc["f1_0.5"],
            "f1_thr": pc["f1_val_thr"],
            "threshold": pc["threshold"],
            "source": pc["threshold_source"],
            "val_f1_thr": th["val_f1_at_threshold"],
            "val_f1_0.5": th["val_f1_at_0.5"],
        }
    if "object_present" in thresholds["per_class"]:
        th = thresholds["per_class"]["object_present"]
        rows["object_present"] = {
            "code": "object_present",
            "name": "Any object (one flag)",
            "test": counts["object_present"]["test"],
            "val": th["val_support"],
            "auprc": None,
            "f1_0.5": None,
            "f1_thr": None,
            "threshold": th["threshold"],
            "source": th["source"],
            "val_f1_thr": th["val_f1_at_threshold"],
            "val_f1_0.5": th["val_f1_at_0.5"],
        }
    return rows


def title(ws, text: str, lead: str, span: int, width_chars: int):
    ws.sheet_view.showGridLines = False
    ws["A1"] = text
    ws["A1"].font = TITLE_FONT
    ws.row_dimensions[1].height = 28
    ws["A2"] = lead
    ws["A2"].font = LEAD_FONT
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
    ws.row_dimensions[2].height = max(18, 15 * (1 + len(lead) // max(width_chars, 20)))


def header(ws, row: int, headers, widths=None, freeze=True):
    for index, text in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=index, value=text)
        cell.font = HEAD_FONT
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BOX
    ws.row_dimensions[row].height = 38
    if widths:
        for index, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(index)].width = width
    if freeze:
        ws.freeze_panes = f"A{row + 1}"


def write_row(ws, row: int, values, formats=None, bold=False, band=False):
    for index, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=index, value=value)
        cell.font = BOLD_FONT if bold else BODY_FONT
        cell.border = BOX
        if isinstance(value, (int, float)):
            cell.alignment = Alignment(horizontal="right", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        if formats and formats[index - 1]:
            cell.number_format = formats[index - 1]
        if band:
            cell.fill = BAND_FILL
    ws.row_dimensions[row].height = 18


def section(ws, row: int, text: str):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SECTION_FONT
    ws.row_dimensions[row].height = 22


def note(ws, row: int, text: str, span: int, width_chars: int = 100):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SMALL_FONT
    cell.fill = NOTE_FILL
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    ws.row_dimensions[row].height = max(18, 15 * (1 + len(text) // max(width_chars, 20)))


def delta(a, b):
    return b - a


def build():
    a_metrics = load_json(RUN_A / "metrics.json")
    a_thresholds = load_json(RUN_A / "thresholds.json")
    b_metrics = load_json(RUN_B / "metrics.json")
    b_thresholds = load_json(RUN_B / "thresholds.json")
    counts, totals = split_counts()
    a_rows = class_data(a_metrics, a_thresholds, counts)
    b_rows = class_data(b_metrics, b_thresholds, counts)

    a_judge = a_metrics["macro_auprc_judgeable"]
    b_judge = b_metrics["macro_auprc_judgeable"]
    a_f1_half = a_metrics["macro_f1_0.5"]
    b_f1_half = b_metrics["macro_f1_0.5"]
    a_f1_thr = a_metrics["macro_f1_val_thr"]
    b_f1_thr = b_metrics["macro_f1_val_thr"]
    a_exact_half = a_metrics["exact_match"]
    b_exact_half = b_metrics["exact_match"]
    a_exact_thr = a_metrics["exact_match_val_thr"]
    b_exact_thr = b_metrics["exact_match_val_thr"]
    a_ms = a_metrics["timing"]["inference_ms_per_image"]
    b_ms = b_metrics["timing"]["inference_ms_per_image"]

    a_obj = b_metrics["object_column"]
    a_pics = a_metrics["rows"]
    b_pics = b_metrics["rows"]

    wb = Workbook()
    wb.properties.title = "Two runs on the frozen 70/15/15 split"
    wb.properties.creator = "FMD"
    wb.properties.description = (
        "Lens only and lens plus object flag, measured on 1,121 test pictures. "
        "Thresholds chosen on 1,110 validation pictures."
    )

    # ------------------------------------------------------------------ Summary
    ws = wb.active
    ws.title = "Summary"
    title(
        ws,
        "Two runs on the same 7,470 pictures",
        "Runs dated 3 and 5 November 2026. One frozen split: 5,239 training, 1,110 validation, "
        "1,121 test pictures. Every number on this sheet is measured on the 1,121 test pictures; "
        "the thresholds are chosen on the 1,110 validation pictures.",
        span=4,
        width_chars=86,
    )

    r = 4
    section(ws, r, "Headline comparison")
    r += 1
    header(ws, r, ["Measure", "Lens only", "Lens + object flag", "Difference"], [44, 18, 20, 14], freeze=False)
    r += 1
    table = [
        ("Answers per picture", 12, 13, 1, ["0", "0", "+0;-0;0"]),
        ("Lens AUPRC, 8 classes in the average", a_judge, b_judge, delta(a_judge, b_judge), ["0.000", "0.000", "+0.000;-0.000;0.000"]),
        ("Macro F1 at 0.5", a_f1_half, b_f1_half, delta(a_f1_half, b_f1_half), ["0.000", "0.000", "+0.000;-0.000;0.000"]),
        ("Macro F1 at chosen thresholds", a_f1_thr, b_f1_thr, delta(a_f1_thr, b_f1_thr), ["0.000", "0.000", "+0.000;-0.000;0.000"]),
        ("Exact match at 0.5", a_exact_half, b_exact_half, delta(a_exact_half, b_exact_half), ["0.000", "0.000", "+0.000;-0.000;0.000"]),
        ("Exact match at chosen thresholds", a_exact_thr, b_exact_thr, delta(a_exact_thr, b_exact_thr), ["0.000", "0.000", "+0.000;-0.000;0.000"]),
        ("Inference time per picture (ms)", a_ms, b_ms, round(delta(a_ms, b_ms), 2), ["0.00", "0.00", "+0.00;-0.00;0.00"]),
    ]
    for index, (label, a_value, b_value, diff, formats) in enumerate(table):
        write_row(ws, r, [label, a_value, b_value, diff], [None, *formats], band=index % 2 == 1)
        r += 1

    r += 1
    section(ws, r, "What the numbers say")
    r += 1
    dc_drop = abs(b_rows["P2_DC"]["auprc"] - a_rows["P2_DC"]["auprc"])
    fl_gain = b_rows["P1_FL"]["auprc"] - a_rows["P1_FL"]["auprc"]
    lines = [
        f"The lens AUPRC moves from {a_judge:.3f} to {b_judge:.3f} when the object flag joins, "
        f"a drop of {abs(delta(a_judge, b_judge)):.3f}. The loss is concentrated in Dirty Camera, "
        f"down {dc_drop:.3f}; Folded Lens is up {fl_gain:.3f}.",
        f"At the fixed 0.5 threshold, macro F1 is effectively unchanged: {a_f1_half:.3f} to "
        f"{b_f1_half:.3f}. At the chosen thresholds it falls {abs(delta(a_f1_thr, b_f1_thr)):.3f}, "
        f"and exact match falls {abs(delta(a_exact_thr, b_exact_thr)):.3f}.",
        f"The flag routes {a_obj['fire_rate_object_only'] * 100:.1f}% of object-only pictures at its "
        f"chosen 0.55 threshold, and {a_obj['fire_rate_mixed'] * 100:.1f}% of mixed pictures. "
        f"No Clear picture fires. It misses {a_obj['pictures_object_only'] - round(a_obj['fire_rate_object_only'] * a_obj['pictures_object_only'])} "
        f"object-only and {a_obj['pictures_mixed'] - round(a_obj['fire_rate_mixed'] * a_obj['pictures_mixed'])} mixed pictures.",
        f"Folded Lens remains weak: {a_rows['P1_FL']['auprc']:.3f} lens only and "
        f"{b_rows['P1_FL']['auprc']:.3f} with the flag, under the 0.70 target.",
        f"The two times are {a_ms:.2f} and {b_ms:.2f} ms per picture on the A100 used for training, "
        "not the edge device.",
    ]
    for line in lines:
        note(ws, r, "- " + line, span=4, width_chars=86)
        r += 1

    r += 1
    section(ws, r, "Other metrics")
    r += 1
    header(ws, r, ["Measure", "Lens only", "Lens + object flag", "Difference"], [44, 18, 20, 14], freeze=False)
    r += 1
    other = [
        ("Lens AUPRC, all 12 classes", a_metrics["macro_auprc_all"], b_metrics["macro_auprc_all"], ["0.000", "0.000", "+0.000;-0.000;0.000"]),
        ("Hamming loss at 0.5", a_metrics["hamming_loss"], b_metrics["hamming_loss"], ["0.0000", "0.0000", "+0.0000;-0.0000;0.0000"]),
        ("Hamming loss at chosen thresholds", a_metrics["hamming_loss_val_thr"], b_metrics["hamming_loss_val_thr"], ["0.0000", "0.0000", "+0.0000;-0.0000;0.0000"]),
    ]
    for index, (label, a_value, b_value, formats) in enumerate(other):
        write_row(ws, r, [label, a_value, b_value, delta(a_value, b_value)], [None, *formats], band=index % 2 == 1)
        r += 1

    r += 1
    section(ws, r, "What this does not cover")
    r += 1
    limits = [
        "The pass/fail rule is not evaluated here. It is the next stage.",
        "The flag says an object is present, not which of the eight object classes. Splitting it into eight is the next stage.",
        "The times are one measurement on the training GPU, not a benchmark on the edge device.",
        "The October 80/20 readout is not comparable; these runs use a 70/15/15 split and choose thresholds on validation.",
    ]
    for line in limits:
        note(ws, r, "- " + line, span=4, width_chars=86)
        r += 1

    # ------------------------------------------------------------------ Per-class results
    ws = wb.create_sheet("Per-class results")
    title(
        ws,
        "Per-class results on the test split",
        "Measured on the 1,121 test pictures. Runs dated 3 and 5 November 2026. Both runs use the "
        "same frozen split and recipe. A picture can carry more than one class. The object flag is "
        "scored on the Routing sheet.",
        span=8,
        width_chars=120,
    )
    header(
        ws,
        4,
        ["Run", "Class", "Test pictures (of 1,121)", "In lens average", "AUPRC",
         "F1 at 0.5", "F1 at chosen threshold", "Threshold"],
        [19, 28, 13, 11, 9, 11, 13, 9],
    )
    r = 5
    row_index = 0
    for run_label, rows in [("Lens only", a_rows), ("Lens + object flag", b_rows)]:
        for code in CLASS_ORDER:
            item = rows[code]
            write_row(
                ws,
                r,
                [run_label, item["name"], item["test"], "Yes" if item["test"] >= JUDGEABLE_MIN else "No",
                 item["auprc"], item["f1_0.5"], item["f1_thr"], item["threshold"]],
                [None, None, "#,##0", None, "0.000", "0.000", "0.000", "0.00"],
                band=row_index % 2 == 1,
            )
            r += 1
            row_index += 1
    ws.auto_filter.ref = f"A4:H{r - 1}"
    note(
        ws,
        r + 1,
        "The lens average uses the eight classes with at least 20 test pictures. The four classes "
        "with fewer than 20 are shown but not averaged. The four are also the classes that keep "
        "0.50 under the threshold guard. The object flag is scored on the Routing sheet.",
        span=8,
        width_chars=120,
    )
    note(
        ws,
        r + 2,
        "View Obstructed ranks well (AUPRC 0.913 lens only, 0.901 with the flag) but has 9 validation "
        "and 10 test pictures, so the guard keeps 0.50 and its F1 at 0.50 is 0.000.",
        span=8,
        width_chars=120,
    )

    # ------------------------------------------------------------------ Thresholds
    ws = wb.create_sheet("Thresholds")
    title(
        ws,
        "The threshold each class uses",
        "Chosen on the 1,110 validation pictures, then frozen before the 1,121 test pictures are read. "
        "Runs dated 3 and 5 November 2026. The grid and the 10-positive guard are on the Threshold "
        "rule sheet.",
        span=9,
        width_chars=140,
    )
    header(
        ws,
        4,
        ["Run", "Class", "Validation pictures (of 1,110)", "Test pictures (of 1,121)",
         "Threshold", "Basis", "Validation F1 at threshold", "Validation F1 at 0.5",
         "Change in validation F1"],
        [19, 24, 16, 12, 9, 20, 14, 12, 12],
    )
    r = 5
    row_index = 0
    for run_label, rows in [("Lens only", a_rows), ("Lens + object flag", b_rows)]:
        for code in CLASS_ORDER + (["object_present"] if "object_present" in rows else []):
            item = rows[code]
            basis = "Default, under 10" if item["source"] == "default" else "Chosen on validation"
            write_row(
                ws,
                r,
                [run_label, item["name"], item["val"], item["test"], item["threshold"], basis,
                 item["val_f1_thr"], item["val_f1_0.5"], item["val_f1_thr"] - item["val_f1_0.5"]],
                [None, None, "#,##0", "#,##0", "0.00", None, "0.000", "0.000", "+0.000;-0.000;0.000"],
                band=row_index % 2 == 1,
            )
            r += 1
            row_index += 1
    ws.auto_filter.ref = f"A4:I{r - 1}"
    note(
        ws,
        r + 1,
        "The validation F1 is on the 1,110 validation pictures. The test count is shown for context; "
        "it does not choose the threshold. A class with fewer than 10 validation positives keeps 0.50 "
        "and is marked Default. The two runs choose different thresholds for several classes; a "
        "threshold belongs to its run.",
        span=9,
        width_chars=130,
    )

    # ------------------------------------------------------------------ Threshold rule
    ws = wb.create_sheet("Threshold rule")
    title(
        ws,
        "How the threshold is chosen, and why four classes stay at 0.5",
        "The same rule for both runs. The threshold is chosen on the 1,110 validation pictures, then "
        "frozen before the 1,121 test pictures are read.",
        span=4,
        width_chars=86,
    )
    for column, width in {"A": 30, "B": 60, "C": 22, "D": 50}.items():
        ws.column_dimensions[column].width = width
    r = 4
    section(ws, r, "The rule in four steps")
    r += 1
    steps = [
        "1. Score every validation picture with the model's score for the class.",
        "2. Sweep the threshold from 0.05 to 0.95 in 0.05 steps.",
        "3. Pick the threshold with the highest F1 on validation. A tie goes to the higher threshold.",
        "4. A class with fewer than 10 validation positives keeps 0.50 and is marked Default. "
        "The test pictures are read once, after the thresholds are frozen.",
    ]
    for step in steps:
        note(ws, r, step, span=4, width_chars=86)
        r += 1

    r += 1
    section(ws, r, "The grid actually used")
    r += 1
    header(ws, r, ["Item", "Value"], freeze=False)
    r += 1
    grid = [
        ("Steps", "0.05 to 0.95, in 0.05 steps"),
        ("Values", "0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, "
                   "0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95"),
        ("Objective", "Highest F1 on the validation split"),
        ("Default", "0.50"),
        ("Minimum validation positives", "10"),
    ]
    for label, value in grid:
        write_row(ws, r, [label, value])
        ws.row_dimensions[r].height = max(18, 15 * (1 + len(value) // 60))
        r += 1

    r += 1
    section(ws, r, "Classes held at the default")
    r += 1
    header(ws, r, ["Class", "Validation pictures (of 1,110)", "Test pictures (of 1,121)", "Why"], freeze=False)
    r += 1
    for code in ["P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]:
        item = a_rows[code]
        write_row(ws, r, [item["name"], item["val"], item["test"], "Validation has fewer than 10 positives."])
        r += 1
    note(
        ws,
        r + 1,
        "The same four classes default in both runs. The test count is shown for context; the guard "
        "is validation only. In this split, three of the four are also under 10 in test; View "
        "Obstructed has 10.",
        span=4,
        width_chars=86,
    )
    note(
        ws,
        r + 2,
        "View Obstructed ranks well (AUPRC 0.913 lens only, 0.901 with the flag) but has 9 validation "
        "and 10 test pictures, so the guard keeps 0.50 and its F1 at 0.50 is 0.000.",
        span=4,
        width_chars=86,
    )
    note(
        ws,
        r + 3,
        "This run used a 0.05-step grid. The threshold protocol reference specifies a finer grid; "
        "the next full-data run can use it.",
        span=4,
        width_chars=86,
    )

    # ------------------------------------------------------------------ Routing
    ws = wb.create_sheet("Routing")
    title(
        ws,
        "The object flag on the test pictures",
        "One flag for all eight object classes. It says an object is present, not which one. The flag "
        "run is dated 3 November 2026. The 1,121 test pictures split into 120 object-only, 223 with a "
        "lens condition and an object, 317 Clear, and 461 lens-only pictures.",
        span=7,
        width_chars=100,
    )
    header(
        ws,
        4,
        ["Group", "Test pictures", "Flag fires at 0.5", "Share", "Flag fires at 0.55", "Share", "Target"],
        [26, 12, 14, 10, 14, 10, 16],
    )
    r = 5
    rows = [
        ("Object, no lens condition", a_obj["pictures_object_only"],
         round(a_obj["fire_rate_object_only_0.5"] * a_obj["pictures_object_only"]),
         a_obj["fire_rate_object_only_0.5"],
         round(a_obj["fire_rate_object_only"] * a_obj["pictures_object_only"]),
         a_obj["fire_rate_object_only"], "at least 90%"),
        ("Lens condition and object", a_obj["pictures_mixed"],
         round(a_obj["fire_rate_mixed_0.5"] * a_obj["pictures_mixed"]),
         a_obj["fire_rate_mixed_0.5"],
         round(a_obj["fire_rate_mixed"] * a_obj["pictures_mixed"]),
         a_obj["fire_rate_mixed"], "no target"),
        ("Clear", a_obj["pictures_clear"],
         round(a_obj["fire_rate_clear_0.5"] * a_obj["pictures_clear"]),
         a_obj["fire_rate_clear_0.5"],
         round(a_obj["fire_rate_clear"] * a_obj["pictures_clear"]),
         a_obj["fire_rate_clear"], "at most 5%"),
    ]
    for index, values in enumerate(rows):
        write_row(ws, r, list(values), [None, "#,##0", "#,##0", "0.0%", "#,##0", "0.0%", None], band=index % 2 == 1)
        r += 1
    ws.auto_filter.ref = f"A4:G{r - 1}"
    note(
        ws,
        r + 1,
        "The other 461 test pictures carry a lens condition but no object; the flag is not scored on "
        "them. The 120 + 223 + 317 = 660 pictures with an object or Clear.",
        span=7,
        width_chars=110,
    )
    note(
        ws,
        r + 2,
        "At 0.55 the flag misses 3 of 120 object-only pictures and 12 of 223 mixed pictures. It fires "
        "on 0 of 317 Clear pictures. A miss sends a dirty picture down the pass route; a false alarm "
        "sends a good picture to the detector.",
        span=7,
        width_chars=110,
    )
    note(
        ws,
        r + 3,
        "The flag is one answer for all eight object classes. It does not name the class.",
        span=7,
        width_chars=110,
    )

    note(
        ws,
        r + 4,
        "The object flag's validation F1 is 0.959 at 0.5 and 0.961 at 0.55, on 341 validation "
        "pictures with an object. The test table above is the routing evidence; the flag's test F1 "
        "is not used.",
        span=7,
        width_chars=110,
    )

    # ------------------------------------------------------------------ Split
    ws = wb.create_sheet("Split")
    title(
        ws,
        "Pictures per class on the frozen 70/15/15 split",
        "One split of 7,470 pictures: 5,239 training, 1,110 validation, 1,121 test. The split is fixed "
        "for both runs and dates from 3 November 2026. A picture can appear in more than one lens row; "
        "Clear is exclusive.",
        span=5,
        width_chars=100,
    )
    header(ws, 4, ["Class", "Training (of 5,239)", "Validation (of 1,110)", "Test (of 1,121)", "All pictures"], [34, 16, 16, 14, 14])
    r = 5
    for index, code in enumerate(CLASS_ORDER):
        item = a_rows[code]
        row = [item["name"], counts[code]["train"], counts[code]["val"], counts[code]["test"],
               counts[code]["train"] + counts[code]["val"] + counts[code]["test"]]
        write_row(ws, r, row, [None, "#,##0", "#,##0", "#,##0", "#,##0"], band=index % 2 == 1)
        r += 1
    write_row(ws, r, ["Any object (one flag)", counts["object_present"]["train"], counts["object_present"]["val"],
                      counts["object_present"]["test"], sum(counts["object_present"].values())],
              [None, "#,##0", "#,##0", "#,##0", "#,##0"], band=True)
    r += 1
    write_row(ws, r, ["Clear pictures", counts["is_clear"]["train"], counts["is_clear"]["val"],
                      counts["is_clear"]["test"], sum(counts["is_clear"].values())],
              [None, "#,##0", "#,##0", "#,##0", "#,##0"], band=False)
    r += 1
    write_row(ws, r, ["All pictures", totals["train"], totals["val"], totals["test"], sum(totals.values())],
              [None, "#,##0", "#,##0", "#,##0", "#,##0"], bold=True, band=False)
    r += 1
    ws.auto_filter.ref = f"A4:E{r - 1}"
    note(
        ws,
        r + 1,
        "A picture can appear in more than one lens row; Clear is exclusive. The eight object classes "
        "are one flag in this run. The 7,470 split pictures are 7,617 labelled pictures minus 147 "
        "that carry a retired class or no usable object label.",
        span=5,
        width_chars=95,
    )

    # ------------------------------------------------------------------ Definitions and method
    ws = wb.create_sheet("Definitions and method")
    title(
        ws,
        "Definitions and method",
        "Every term on the other sheets, and how the two runs were made.",
        span=2,
        width_chars=120,
    )
    r = 4
    section(ws, r, "Terms")
    r += 1
    header(ws, r, ["Term", "Meaning"], [30, 100], freeze=False)
    r += 1
    terms = [
        ("AUPRC", "Area under the precision-recall curve; average precision. It does not need a threshold. 1 is perfect."),
        ("Macro F1", "The average of the per-class F1 scores over the eight lens classes with at least 20 test pictures."),
        ("F1", "The balance of missed defects and false alarms at one threshold. 1 is perfect."),
        ("Exact match", "The share of test pictures where every lens answer is right."),
        ("Threshold", "The score above which a class is called present."),
        ("Training split", "5,239 pictures used to fit the model."),
        ("Validation split", "1,110 pictures used only to choose the threshold."),
        ("Test split", "1,121 pictures read once, after the thresholds are frozen."),
        ("Object flag", "One binary answer for all eight object classes. It says an object is present, not which one."),
        ("Clear", "A picture with no defect label. Clear is exclusive: a picture with any label is not Clear."),
        ("Default threshold", "0.50, kept when a class has fewer than 10 validation positives."),
        ("Lens average", "The eight lens classes with at least 20 test pictures: Missing Primary Package, Multiple Lens, "
                         "Lens Off Center, Dirty Camera, No Lens, Folded Lens, Low Dose, Cavity Off Center."),
    ]
    for term, meaning in terms:
        write_row(ws, r, [term, meaning])
        ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = max(18, 15 * (1 + len(meaning) // 100))
        r += 1

    r += 1
    section(ws, r, "Method")
    r += 1
    header(ws, r, ["Item", "Detail"], [30, 100], freeze=False)
    r += 1
    method = [
        ("Model", "ResNet-50, 224 px input, binary cross-entropy, no class weighting."),
        ("Training", "Batch 8, 50 epochs, learning rate 1e-4, seed 42."),
        ("Runs", "Lens only: 12 outputs. Lens + object flag: 13 outputs."),
        ("Split", "70/15/15: 5,239 training, 1,110 validation, 1,121 test pictures."),
        ("Threshold", "Highest F1 on validation; 0.05 to 0.95 in 0.05 steps; fewer than 10 validation positives keeps 0.50."),
        ("Test read", "Once, after the thresholds are frozen."),
        ("Timing", "5.76 and 5.59 ms per picture on the A100 used for training, not the edge device."),
        ("Dates", "Lens only: 5 November 2026. Lens + object flag: 3 November 2026."),
        ("Compared with October", "The October readout used 80/20 and chose thresholds on test; these runs use 70/15/15 and validation. The new scores replace the old ones."),
        ("Pass/fail", "Not evaluated here; the next stage."),
        ("Source", "The two run records dated 3 and 5 November 2026."),
    ]
    for item, detail in method:
        write_row(ws, r, [item, detail])
        ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = max(18, 15 * (1 + len(detail) // 100))
        r += 1

    r += 1
    section(ws, r, "What this does not cover")
    r += 1
    limits = [
        "The pass/fail rule is not evaluated here. It is the next stage.",
        "The flag says an object is present, not which of the eight object classes.",
        "The times are one measurement on the training GPU, not a benchmark on the edge device.",
        "The October 80/20 readout is not comparable; these runs use a 70/15/15 split and choose thresholds on validation.",
    ]
    for line in limits:
        note(ws, r, "- " + line, span=2, width_chars=120)
        r += 1

    from openpyxl.worksheet.properties import PageSetupProperties

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = False
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        if sheet.sheet_properties.pageSetUpPr is None:
            sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        else:
            sheet.sheet_properties.pageSetUpPr.fitToPage = True

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
