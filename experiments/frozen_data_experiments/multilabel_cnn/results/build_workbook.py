"""Build the frozen 17-class test-results workbook.

Run from the repository root:

    uv run python experiments/frozen_data_experiments/multilabel_cnn/results/build_workbook.py

The workbook is written beside this script. All numbers come from workbook_data.py,
which reads the copied run artifacts and recomputes AUROC from the saved scores.
"""

from __future__ import annotations

import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

from workbook_data import GROUP_ORDER, load_data

HERE = Path(__file__).resolve().parent
OUT = HERE / "frozen_multilabel_results.xlsx"

NAVY = "1F3864"
BLUE = "2F5597"
LIGHT_BLUE = "D9E2F3"
PALE = "F2F5FA"
WHITE = "FFFFFF"
INK = "262626"
GREY = "595959"
LIGHT_GREY = "D9D9D9"
ORANGE = "C55A11"
LIGHT_ORANGE = "FBE5D6"
GREEN = "548235"
PALE_GREEN = "E2EFDA"

THIN = Side(style="thin", color=LIGHT_GREY)
MEDIUM = Side(style="medium", color=BLUE)
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BORDER_TOP = Border(left=THIN, right=THIN, top=MEDIUM, bottom=THIN)
NO_BORDER = Border()

TITLE_FONT = Font(name="Calibri", size=16, bold=True, color=WHITE)
LINE_FONT = Font(name="Calibri", size=10.5, italic=True, color=GREY)
NOTE_FONT = Font(name="Calibri", size=9, italic=True, color=GREY)
SECTION_FONT = Font(name="Calibri", size=12, bold=True, color=NAVY)
HEADER_FONT = Font(name="Calibri", size=10, bold=True, color=WHITE)
BODY_FONT = Font(name="Calibri", size=10, color=INK)
BODY_BOLD = Font(name="Calibri", size=10, bold=True, color=INK)
GROUP_FONT = Font(name="Calibri", size=10, bold=True, color=NAVY)

TITLE_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FILL = PatternFill("solid", fgColor=BLUE)
SECTION_FILL = PatternFill("solid", fgColor=LIGHT_BLUE)
NOTE_FILL = PatternFill("solid", fgColor=PALE)
SCOPE_FILL = PatternFill("solid", fgColor=LIGHT_ORANGE)
WHITE_FILL = PatternFill("solid", fgColor=WHITE)

GROUP_FILL = {
    "Lens presentation tags": PatternFill("solid", fgColor=WHITE),
    "OOI tags": PatternFill("solid", fgColor="F2F6FC"),
    "OOI tags with Size tag": PatternFill("solid", fgColor="FDF5EE"),
}

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
LEFT_TOP = Alignment(horizontal="left", vertical="top", wrap_text=True)
RIGHT = Alignment(horizontal="right", vertical="center")

COUNT_FMT = "#,##0"
PCT_FMT = "0.0"
SCORE_FMT = "0.000"
CUT_FMT = "0.00"
MS_FMT = "0.00"


def pct(value: float) -> float:
    return round(float(value) * 100.0, 1)


def set_widths(ws, widths: list[float]) -> None:
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width


def setup_print(ws, area: str, paper: str = "9", landscape: bool = True, fit_height: int = 0) -> None:
    ws.print_area = area
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.paperSize = paper
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = fit_height
    ws.page_margins.left = 0.3
    ws.page_margins.right = 0.3
    ws.page_margins.top = 0.4
    ws.page_margins.bottom = 0.4
    ws.page_margins.header = 0.2
    ws.page_margins.footer = 0.2
    ws.oddFooter.center.text = "Page &P of &N"
    ws.oddFooter.center.size = 8
    ws.oddFooter.center.color = "808080"


def title(ws, text: str, last_col: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    cell = ws.cell(row=1, column=1, value=text)
    cell.font = TITLE_FONT
    cell.alignment = LEFT
    for col in range(1, last_col + 1):
        ws.cell(row=1, column=col).fill = TITLE_FILL
    ws.row_dimensions[1].height = 30


def line(ws, row: int, text: str, last_col: int, height: float = 24) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = LINE_FONT
    cell.alignment = LEFT
    ws.row_dimensions[row].height = height


def section(ws, row: int, text: str, last_col: int) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SECTION_FONT
    cell.alignment = LEFT
    for col in range(1, last_col + 1):
        ws.cell(row=row, column=col).fill = SECTION_FILL
    ws.row_dimensions[row].height = 24


def note(ws, row: int, text: str, last_col: int, width_chars: int, height: float | None = None) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = NOTE_FONT
    cell.alignment = LEFT_TOP
    for col in range(1, last_col + 1):
        ws.cell(row=row, column=col).fill = NOTE_FILL
    if height is None:
        chars_per_line = max(40, int(width_chars * 1.05))
        height = 14 * max(1, math.ceil(len(text) / chars_per_line)) + 6
    ws.row_dimensions[row].height = height


def header_row(ws, row: int, headers: list[str]) -> None:
    for index, text in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=index, value=text)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER
        cell.border = BORDER
    ws.row_dimensions[row].height = 34


def body_cell(
    cell,
    value,
    *,
    bold: bool = False,
    align=LEFT,
    fmt: str | None = None,
    fill: PatternFill | None = None,
    border: Border = BORDER,
    font: Font | None = None,
) -> None:
    cell.value = value
    cell.font = font or (BODY_BOLD if bold else BODY_FONT)
    cell.alignment = align
    cell.border = border
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill


def add_page_sheet(wb, name: str, tab_color: str):
    if name in wb.sheetnames:
        ws = wb[name]
    else:
        ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90
    ws.sheet_properties.tabColor = tab_color
    return ws


def build_readme(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Read me", NAVY)
    set_widths(ws, [22, 82])
    title(ws, "Defect model results", 2)
    line(ws, 2, "Read this first.", 2, 22)

    rows = [
        ("What it shows", "The test results of one multi-label model on 2,045 held-out pictures, for 17 defect classes."),
        ("Population", "13,631 analysed pictures: 9,537 training, 2,049 validation, 2,045 test."),
        (
            "Main table",
            "The per-class table uses a 0.5 threshold and lists the pass classes first. The validation-chosen cuts are on a separate sheet and are provisional.",
        ),
        (
            "Pass/fail",
            "One verdict per picture under the agreed rule; the counts and the four rates are on the Pass fail sheet.",
        ),
        (
            "Pass images",
            "The 148 truth-pass pictures by class and by exact class set, with predicted pass and fail counts.",
        ),
        (
            "Class split",
            "Pictures carrying each class in train, validation and test, including tagged and untagged counts for the four size classes.",
        ),
        (
            "Excluded",
            "Clear (42 pictures) and six classes with fewer than 200 pictures. The six classes are excluded as model outputs only; their 281 pictures remain in the analysed set.",
        ),
        ("Counts", "Counts are pictures unless the header says labels. A picture can carry more than one class."),
        ("Prepared", "20 November 2026."),
    ]
    row = 4
    for label, text in rows:
        cell = ws.cell(row=row, column=1, value=label)
        cell.font = BODY_BOLD
        cell.alignment = LEFT_TOP
        text_cell = ws.cell(row=row, column=2, value=text)
        text_cell.font = BODY_FONT
        text_cell.alignment = LEFT_TOP
        ws.row_dimensions[row].height = 30 if len(text) < 95 else 45
        row += 2

    setup_print(ws, "A1:B22", paper="9", landscape=False)


def build_summary(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Summary", BLUE)
    set_widths(ws, [30, 16, 62, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3])
    title(ws, "Defect model results", 6)
    line(ws, 2, "Test results at a 0.5 threshold on 2,045 held-out pictures, for 17 defect classes.", 6, 24)

    excluded_text = "; ".join(
        f"{item['code']} {item['name']} ({item['pictures']})" for item in data["excluded"]
    )
    scope = (
        "Scope: 17 defect classes. Clear (42 pictures) is excluded. Six classes with fewer than 200 "
        f"pictures are excluded as model outputs only: {excluded_text}. Their {data['excluded_union']} "
        "distinct pictures remain; no picture carries only an excluded class."
    )
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    sc = ws.cell(row=3, column=1, value=scope)
    sc.font = Font(name="Calibri", size=9, italic=True, color=ORANGE)
    sc.alignment = LEFT_TOP
    for col in range(1, 7):
        ws.cell(row=3, column=col).fill = SCOPE_FILL
    ws.row_dimensions[3].height = 64

    header_row(ws, 5, ["Measure", "Value", "Note"])
    kpis = [
        ("Macro F1 (%)", pct(data["macro"]["f1_05"]), "Unweighted mean over 17 classes", PCT_FMT),
        ("Macro precision (%)", pct(data["macro"]["precision_05"]), "", PCT_FMT),
        ("Macro recall (%)", pct(data["macro"]["recall_05"]), "", PCT_FMT),
        ("Macro AUROC", round(data["macro"]["auroc"], 3), "Threshold-independent", SCORE_FMT),
        ("Macro AUPRC", round(data["macro"]["auprc"], 3), "Area under the precision-recall curve", SCORE_FMT),
        (
            "Inference per picture (ms)",
            round(data["timing"]["inference_ms_per_image"], 2),
            f"{data['timing']['seconds_inference']:.1f} s for {data['timing']['inference_images']:,} pictures",
            MS_FMT,
        ),
    ]
    row = 6
    for label, value, note_text, fmt in kpis:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label, bold=True, fill=WHITE_FILL)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, value, align=RIGHT, fmt=fmt, fill=WHITE_FILL)
        c2.font = Font(name="Calibri", size=14, bold=True, color=NAVY)
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, note_text, font=NOTE_FONT, fill=WHITE_FILL)
        c3.alignment = LEFT
        ws.row_dimensions[row].height = 24
        row += 1

    note(
        ws,
        12,
        "AUROC is threshold-independent. AUPRC uses the precision-recall curve; its baseline is the class prevalence.",
        6,
        120,
        30,
    )

    chosen = (
        "At the validation-chosen cuts (provisional): "
        f"macro F1 {pct(data['macro']['f1_chosen']):.1f}%, "
        f"precision {pct(data['macro']['precision_chosen']):.1f}%, "
        f"recall {pct(data['macro']['recall_chosen']):.1f}%."
    )
    note(ws, 13, chosen, 6, 120, 18)

    counts = (
        f"{data['test_pictures']:,} test pictures; {data['positive_labels']:,} positive class labels. "
        "A picture can carry more than one class."
    )
    note(ws, 14, counts, 6, 120, 18)

    ws.merge_cells(start_row=16, start_column=1, end_row=16, end_column=6)
    chart_title = ws.cell(row=16, column=1, value="F1 at 0.5 by class")
    chart_title.font = Font(name="Calibri", size=11, bold=True, color=NAVY)
    chart_title.alignment = LEFT
    ws.row_dimensions[16].height = 20

    per = wb["Per class"]
    values = Reference(per, min_col=11, min_row=4, max_row=20)
    cats = Reference(per, min_col=2, min_row=4, max_row=20)
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.grouping = "clustered"
    chart.title = None
    chart.x_axis.title = "Class"
    chart.y_axis.title = "F1 (%)"
    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 100
    chart.y_axis.majorUnit = 20
    chart.y_axis.delete = False
    chart.x_axis.delete = False
    chart.legend = None
    chart.height = 10.5
    chart.width = 22
    chart.add_data(values, titles_from_data=False)
    chart.set_categories(cats)
    chart.series[0].graphicalProperties.solidFill = BLUE
    chart.series[0].graphicalProperties.line.solidFill = NAVY
    ws.add_chart(chart, "A17")

    flag_note = (
        "The four OOI tags with a size tag are scored as class presence. The size tag is a "
        "separate reporting subset, not a model output."
    )
    note(ws, 39, flag_note, 6, 120, 30)

    setup_print(ws, "A1:N40", paper="9", landscape=True, fit_height=1)


def build_pass_fail(wb, data: dict) -> None:
    pf = data["pass_fail"]
    ws = add_page_sheet(wb, "Pass fail", BLUE)
    widths = [34, 14, 62]
    set_widths(ws, widths)
    title(ws, "Pass and fail counts", 3)
    line(
        ws,
        2,
        f"One verdict per test picture under the agreed rule; {data['test_pictures']:,} test pictures at a {pf['cut']:.1f} threshold.",
        3,
        24,
    )
    note(ws, 3, "Clear is outside this experiment. Bubble alone passes; Bubble Cluster fails.", 3, 110, 18)

    row = 5
    section(ws, row, "Counts", 3)
    row += 1
    header_row(ws, row, ["Result", "Count", "Meaning"])
    row += 1
    for label, count, meaning in [
        ("True Accept (TA)", pf["TA"], "Good picture accepted"),
        ("False Reject (FR)", pf["FR"], "Good picture rejected"),
        ("True Reject (TR)", pf["TR"], "Defective picture rejected"),
        ("False Accept (FA)", pf["FA"], "Defective picture accepted"),
    ]:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label, bold=True)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, count, align=RIGHT, fmt=COUNT_FMT)
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, meaning, font=NOTE_FONT)
        c3.alignment = LEFT
        ws.row_dimensions[row].height = 20
        row += 1
    c1 = ws.cell(row=row, column=1)
    body_cell(c1, "Total", bold=True)
    c2 = ws.cell(row=row, column=2)
    body_cell(c2, data["test_pictures"], align=RIGHT, fmt=COUNT_FMT, bold=True)
    c3 = ws.cell(row=row, column=3)
    body_cell(c3, "All test pictures", font=NOTE_FONT)
    c3.alignment = LEFT
    ws.row_dimensions[row].height = 20
    row += 2

    section(ws, row, "Rates", 3)
    row += 1
    header_row(ws, row, ["Rate", "Formula", "Value (%)"])
    row += 1
    for label, formula, value in [
        ("TAR", "TA / (TA + FR)", pf["tar"]),
        ("TRR", "TR / (TR + FA)", pf["trr"]),
        ("FAR", "FA / (TR + FA)", pf["far"]),
        ("FRR", "FR / (TA + FR)", pf["frr"]),
    ]:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label, bold=True)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, formula, font=NOTE_FONT)
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, pct(value), align=RIGHT, fmt=PCT_FMT)
        ws.row_dimensions[row].height = 20
        row += 1
    note(ws, row, "TAR + FRR = 100 percent; TRR + FAR = 100 percent.", 3, 110, 18)
    row += 2

    section(ws, row, "What fails a picture", 3)
    row += 1
    header_row(ws, row, ["Condition", "Actual fail pictures", "Predicted fail pictures"])
    row += 1
    for cause in pf["causes"]:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, cause["label"])
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, cause["actual"], align=RIGHT, fmt=COUNT_FMT)
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, cause["predicted"], align=RIGHT, fmt=COUNT_FMT)
        ws.row_dimensions[row].height = 20
        row += 1
    note(
        ws,
        row,
        "A picture can have more than one cause; the cause counts overlap and do not add to the fail total.",
        3,
        110,
        30,
    )
    row += 2

    section(ws, row, "Rule", 3)
    row += 1
    header_row(ws, row, ["Picture", "Verdict", ""])
    row += 1
    for picture, verdict in [
        ("Clear", "Outside this experiment (excluded)"),
        ("Bubble only", "Pass"),
        ("Bubble Cluster", "Fail"),
        ("Any lens presentation tag", "Fail"),
        ("Wet Package", "Fail"),
        ("Size-tagged class below the cut (untagged)", "Pass"),
        ("Size-tagged class above the cut (tagged)", "Fail"),
    ]:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, picture)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, verdict)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
        ws.row_dimensions[row].height = 20
        row += 1
    note(
        ws,
        row,
        "This is the agreed rule. No second rule is applied. The model predicts class presence, not size, so a predicted size-tagged class counts as a predicted fail; the size tag changes only the truth. This block is an object-presence proxy for the size rule.",
        3,
        110,
        45,
    )
    setup_print(ws, f"A1:C{row}", paper="9", landscape=True, fit_height=1)


def build_pass_images(wb, data: dict) -> None:
    images = data["pass_images"]
    ws = add_page_sheet(wb, "Pass images", BLUE)
    widths = [38, 20, 18, 18, 18]
    set_widths(ws, widths)
    title(ws, "Pass images by class", 5)
    line(
        ws,
        2,
        f"{images['total']} truth-pass test pictures at a 0.5 threshold. Predicted pass means no fail score is at or above the cut.",
        5,
        30,
    )

    section(ws, 4, "By class", 5)
    header_row(ws, 5, ["Class", "Pass class", "Pass pictures", "Predicted pass", "Predicted fail"])
    row = 6
    for item in images["by_class"]:
        if item["pass_class"] == "Fail":
            continue
        values = [
            (item["name"], LEFT, None, False, BODY_FONT),
            (item["pass_class"], LEFT, None, False, BODY_FONT),
            (item["pictures"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["predicted_pass"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["predicted_fail"], RIGHT, COUNT_FMT, False, BODY_FONT),
        ]
        for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
            body_cell(ws.cell(row=row, column=col), value, align=align, fmt=fmt, font=font, bold=bold)
        ws.row_dimensions[row].height = 20
        row += 1
    values = [
        ("All truth-pass pictures", LEFT, None, True, BODY_BOLD),
        ("", LEFT, None, True, BODY_BOLD),
        (images["total"], RIGHT, COUNT_FMT, True, BODY_BOLD),
        (images["predicted_pass"], RIGHT, COUNT_FMT, True, BODY_BOLD),
        (images["predicted_fail"], RIGHT, COUNT_FMT, True, BODY_BOLD),
    ]
    for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
        body_cell(ws.cell(row=row, column=col), value, align=align, fmt=fmt, font=font, bold=bold)
    ws.row_dimensions[row].height = 20
    row += 2

    note(
        ws,
        row,
        "The class rows overlap: a picture can carry Bubble and Foreign Matter. The total is distinct pictures, not the sum of the rows.",
        5,
        sum(widths),
        30,
    )
    row += 2

    section(ws, row, "Exact class set of each truth-pass picture", 5)
    row += 1
    header_row(ws, row, ["Class set of the picture", "Pass pictures", "Predicted pass", "Predicted fail"])
    row += 1
    for item in images["by_set"]:
        values = [
            (item["label"], LEFT, None, False, BODY_FONT),
            (item["pictures"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["predicted_pass"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["predicted_fail"], RIGHT, COUNT_FMT, False, BODY_FONT),
        ]
        for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
            body_cell(ws.cell(row=row, column=col), value, align=align, fmt=fmt, font=font, bold=bold)
        ws.row_dimensions[row].height = 20
        row += 1
    values = [
        ("All truth-pass pictures", LEFT, None, True, BODY_BOLD),
        (images["total"], RIGHT, COUNT_FMT, True, BODY_BOLD),
        (images["predicted_pass"], RIGHT, COUNT_FMT, True, BODY_BOLD),
        (images["predicted_fail"], RIGHT, COUNT_FMT, True, BODY_BOLD),
    ]
    for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
        body_cell(ws.cell(row=row, column=col), value, align=align, fmt=fmt, font=font, bold=bold)
    row += 2

    note(
        ws,
        row,
        "The exact sets add to 148. No truth-pass picture carries HEMA or Extraneous Polymer. HEMA has no untagged test picture; Extraneous Polymer has one untagged test picture that also carries another fail label.",
        5,
        sum(widths),
        45,
    )
    row += 1
    note(
        ws,
        row,
        "A truth-pass picture carries only Bubble and untagged Foreign Matter or Fiber. Bubble alone passes; a size-tagged Foreign Matter or Fiber picture fails.",
        5,
        sum(widths),
        30,
    )
    setup_print(ws, f"A1:E{row}", paper="9", landscape=True, fit_height=1)


def build_class_split(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Class split", BLUE)
    widths = [24, 28, 10, 12, 10, 10, 12, 10, 10, 10]
    set_widths(ws, widths)
    title(ws, "Pictures by class and split", 10)
    line(
        ws,
        2,
        "Pictures carrying each class in the 70/15/15 split. A picture can carry more than one class.",
        10,
        24,
    )

    section(ws, 4, "All classes", 6)
    header_row(ws, 5, ["Group", "Class", "Train", "Validation", "Test", "Total"])
    row = 6
    group_start = 6
    previous_group = None
    for item in data["class_split"]:
        new_group = item["group"] != previous_group
        border = BORDER_TOP if new_group else BORDER
        if new_group and previous_group is not None:
            ws.merge_cells(start_row=group_start, start_column=1, end_row=row - 1, end_column=1)
            group_start = row
        previous_group = item["group"]
        fill = GROUP_FILL[item["group"]]
        values = [
            (item["group"], LEFT, None, True, GROUP_FONT),
            (item["name"], LEFT, None, False, BODY_FONT),
            (item["train"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["val"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["test"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["total"], RIGHT, COUNT_FMT, False, BODY_FONT),
        ]
        for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
            body_cell(ws.cell(row=row, column=col), value, align=align, fmt=fmt, fill=fill, border=border, font=font, bold=bold)
        ws.row_dimensions[row].height = 20
        row += 1
    ws.merge_cells(start_row=group_start, start_column=1, end_row=row - 1, end_column=1)

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    body_cell(ws.cell(row=row, column=1), "All analysed pictures", bold=True)
    for col, value in enumerate(
        [data["splits"]["train"], data["splits"]["val"], data["splits"]["test"], data["analysed"]],
        start=3,
    ):
        body_cell(ws.cell(row=row, column=col), value, align=RIGHT, fmt=COUNT_FMT, bold=True)
    ws.row_dimensions[row].height = 20
    row += 2
    note(
        ws,
        row,
        "Class rows overlap; the total is the number of analysed pictures, not the sum of the class rows.",
        10,
        sum(widths),
        30,
    )
    row += 2

    section(ws, row, "Size-tagged classes, tagged and untagged", 10)
    row += 1
    header_row(
        ws,
        row,
        [
            "Class",
            "Train total",
            "Train tagged",
            "Train untagged",
            "Validation total",
            "Validation tagged",
            "Validation untagged",
            "Test total",
            "Test tagged",
            "Test untagged",
        ],
    )
    row += 1
    for item in data["size_split"]:
        values = [
            (item["name"], LEFT, None, False, BODY_FONT),
            (item["train_total"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["train_tagged"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["train_untagged"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["val_total"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["val_tagged"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["val_untagged"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["test_total"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["test_tagged"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["test_untagged"], RIGHT, COUNT_FMT, False, BODY_FONT),
        ]
        for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
            body_cell(ws.cell(row=row, column=col), value, align=align, fmt=fmt, font=font, bold=bold)
        ws.row_dimensions[row].height = 20
        row += 1
    row += 1

    note(
        ws,
        row,
        "Tagged means the size tag is set. Tagged pictures fail under the agreed rule; untagged ones pass when no other fail condition is present.",
        10,
        sum(widths),
        30,
    )
    row += 1
    note(
        ws,
        row,
        "HEMA has no untagged picture in any split. Extraneous Polymer has 2 untagged pictures in train, 1 in validation and 1 in test; the test picture also carries another fail label, so it is not a truth-pass picture.",
        10,
        sum(widths),
        45,
    )
    row += 1
    note(
        ws,
        row,
        "The split is 70/15/15, seed 42, iterative multi-label stratification. It is not a size-gate split; tagged and untagged pictures are mixed.",
        10,
        sum(widths),
        30,
    )
    setup_print(ws, f"A1:J{row}", paper="8", landscape=True, fit_height=1)


def build_per_class(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Per class", BLUE)
    widths = [22, 26, 16, 11, 8, 8, 8, 8, 11, 11, 11, 9, 9]
    set_widths(ws, widths)
    title(ws, "Test results by class", 13)
    line(
        ws,
        2,
        "17 classes at a 0.5 threshold; 2,045 test pictures. Pass classes are first. Counts are class presence; picture-level pass/fail is on Pass images.",
        13,
        30,
    )
    headers = [
        "Group",
        "Class",
        "Pass class",
        "Test pictures",
        "TA",
        "FR",
        "TR",
        "FA",
        "Precision (%)",
        "Recall (%)",
        "F1 (%)",
        "AUROC",
        "AUPRC",
    ]
    header_row(ws, 3, headers)

    row = 4
    group_start = 4
    previous_group = None
    for item in data["reader_rows"]:
        new_group = item["group"] != previous_group
        border = BORDER_TOP if new_group else BORDER
        if new_group and previous_group is not None and row - 1 > group_start:
            ws.merge_cells(start_row=group_start, start_column=1, end_row=row - 1, end_column=1)
            group_start = row
        elif new_group and previous_group is not None:
            group_start = row
        previous_group = item["group"]
        fill = GROUP_FILL[item["group"]]
        values = [
            (item["group"], LEFT, None, True, GROUP_FONT),
            (item["name"], LEFT, None, False, BODY_FONT),
            (item["pass_class"], LEFT, None, False, BODY_FONT),
            (item["support"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["ta_05"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["fr_05"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["tr_05"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["fa_05"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (pct(item["precision_05"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["recall_05"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["f1_05"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (round(item["auroc"], 3), RIGHT, SCORE_FMT, False, BODY_FONT),
            (round(item["auprc"], 3), RIGHT, SCORE_FMT, False, BODY_FONT),
        ]
        for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col)
            body_cell(cell, value, align=align, fmt=fmt, fill=fill, border=border, font=font, bold=bold)
        ws.row_dimensions[row].height = 20
        row += 1
    if row - 1 > group_start:
        ws.merge_cells(start_row=group_start, start_column=1, end_row=row - 1, end_column=1)

    note_row = row + 1
    note(
        ws,
        note_row,
        "Counts are per class at a 0.5 threshold. For one class: TA = class absent and predicted absent; FR = class absent and predicted present; TR = class present and predicted present; FA = class present and predicted absent. Each row uses all 2,045 test pictures.",
        13,
        sum(widths),
        45,
    )
    note(
        ws,
        note_row + 1,
        "Pass class: Bubble passes alone. Foreign Matter, Fiber, HEMA and Extraneous Polymer pass only when untagged. The other 12 classes fail when present. The model has no size output.",
        13,
        sum(widths),
        30,
    )
    note(
        ws,
        note_row + 2,
        "These rows are one-versus-rest and are not additive across classes. The picture-level pass/fail table is on Pass images.",
        13,
        sum(widths),
        30,
    )
    note(
        ws,
        note_row + 3,
        "Macro values are unweighted means over the 17 classes; each class counts equally.",
        13,
        sum(widths),
        18,
    )
    note(
        ws,
        note_row + 4,
        "The test picture count is the class support. Prevalence is that count divided by 2,045; it is the baseline for AUPRC, so AUPRC is not comparable across classes with different prevalence.",
        13,
        sum(widths),
        30,
    )
    note(
        ws,
        note_row + 5,
        "Read the test picture count beside each rate. A class with 33 test pictures moves about 3 percentage points per picture.",
        13,
        sum(widths),
        18,
    )
    note(
        ws,
        note_row + 6,
        "AUROC is computed from the saved test scores; it does not depend on a threshold.",
        13,
        sum(widths),
        18,
    )

    ws.freeze_panes = "A4"
    ws.print_title_rows = "3:3"
    setup_print(ws, f"A1:M{note_row + 6}", paper="8", landscape=True)


def build_selected_thresholds(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Selected thresholds", ORANGE)
    widths = [22, 26, 7, 11, 11, 11, 11, 11, 11, 11, 8, 8, 8, 8, 11]
    set_widths(ws, widths)
    title(ws, "Validation-chosen cuts", 15)
    line(
        ws,
        2,
        "Provisional cuts chosen on the validation split, scored once on the 2,045 test pictures.",
        15,
        24,
    )
    rule = data["threshold_rule"]
    grid = rule["grid"]
    grid_text = (
        f"{grid[0]:.2f} to {grid[-1]:.2f}, step {grid[1] - grid[0]:.2f} ({len(grid)} cuts)"
        if grid
        else ""
    )
    rule_note = (
        "Rule: highest F1 on validation, "
        f"{grid_text}, at least {rule['min_val_positives']} validation pictures, one seed. "
        f"Classes left at the default {rule['default_threshold']:.2f}: {rule['n_default']}. "
        "These cuts are provisional. The agreed protocol uses a 0.01-step grid, a validation precision "
        "floor of 0.5, the plateau centre and two seeds."
    )
    note(ws, 3, rule_note, 15, sum(widths), 45)

    headers = [
        "Group",
        "Class",
        "Cut",
        "Validation pictures",
        "Validation precision (%)",
        "Validation recall (%)",
        "Validation F1 (%)",
        "Test precision (%)",
        "Test recall (%)",
        "Test F1 (%)",
        "Test TA",
        "Test FR",
        "Test TR",
        "Test FA",
        "Test pictures",
    ]
    header_row(ws, 5, headers)

    row = 6
    group_start = 6
    previous_group = None
    for item in data["rows"]:
        new_group = item["group"] != previous_group
        border = BORDER_TOP if new_group else BORDER
        if new_group and previous_group is not None:
            ws.merge_cells(start_row=group_start, start_column=1, end_row=row - 1, end_column=1)
            group_start = row
        previous_group = item["group"]
        fill = GROUP_FILL[item["group"]]
        values = [
            (item["group"], LEFT, None, True, GROUP_FONT),
            (item["name"], LEFT, None, False, BODY_FONT),
            (item["cut"], RIGHT, CUT_FMT, False, BODY_FONT),
            (item["val_support"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (pct(item["val_precision_at_cut"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["val_recall_at_cut"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["val_f1_at_cut"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["precision_chosen"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["recall_chosen"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (pct(item["f1_chosen"]), RIGHT, PCT_FMT, False, BODY_FONT),
            (item["ta_chosen"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["fr_chosen"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["tr_chosen"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["fa_chosen"], RIGHT, COUNT_FMT, False, BODY_FONT),
            (item["support"], RIGHT, COUNT_FMT, False, BODY_FONT),
        ]
        for col, (value, align, fmt, bold, font) in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col)
            body_cell(cell, value, align=align, fmt=fmt, fill=fill, border=border, font=font, bold=bold)
        ws.row_dimensions[row].height = 20
        row += 1
    ws.merge_cells(start_row=group_start, start_column=1, end_row=row - 1, end_column=1)

    note(
        ws,
        row + 1,
        "Validation pictures are the pictures carrying the class in the validation split. Test counts are on the 2,045 test pictures. The cut is applied once to the test set.",
        15,
        sum(widths),
        30,
    )
    note(
        ws,
        row + 2,
        "The validation columns show why the cut was chosen; the test columns show what it did.",
        15,
        sum(widths),
        18,
    )

    ws.freeze_panes = "A6"
    ws.print_title_rows = "5:5"
    setup_print(ws, f"A1:O{row + 2}", paper="8", landscape=True)


def build_threshold_rule(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Threshold rule", ORANGE)
    set_widths(ws, [30, 90])
    title(ws, "Threshold rule", 2)
    line(ws, 2, "How the provisional cuts were chosen.", 2, 22)
    rule = data["threshold_rule"]
    grid = rule["grid"]
    grid_text = (
        f"{grid[0]:.2f} to {grid[-1]:.2f}, step {grid[1] - grid[0]:.2f} ({len(grid)} cuts)"
        if grid
        else ""
    )
    rows = [
        ("Selection split", "Validation"),
        ("Objective", "Maximum F1 per class"),
        ("Grid", grid_text),
        ("Minimum validation pictures", str(rule["min_val_positives"])),
        ("Default if below minimum", f"{rule['default_threshold']:.2f}"),
        ("Seeds", str(rule["seeds"])),
        ("Classes left at 0.5", "None" if rule["n_default"] == 0 else str(rule["n_default"])),
        ("Test use", "Scored once"),
    ]
    header_row(ws, 4, ["Item", "Value"])
    row = 5
    for label, value in rows:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label, bold=True)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, value)
        ws.row_dimensions[row].height = 20
        row += 1

    note(
        ws,
        row + 1,
        "These cuts are provisional. The agreed protocol uses a 0.01-step grid, a validation precision floor "
        "of 0.5, the plateau centre and two seeds. Re-derive the cuts under that protocol before production.",
        2,
        100,
        45,
    )
    setup_print(ws, f"A1:B{row + 1}", paper="9", landscape=False)


def build_scope(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Scope and exclusions", GREY)
    widths = [42, 14, 52, 34]
    set_widths(ws, widths)
    title(ws, "Scope and exclusions", 4)
    line(ws, 2, "What is in the analysed set, and what was excluded.", 4, 22)

    section(ws, 4, "Population", 4)
    header_row(ws, 5, ["Step", "Pictures", "Note", ""])
    ws.merge_cells(start_row=5, start_column=3, end_row=5, end_column=4)
    population = [
        ("Records in the frozen store", data["records"], "All annotated records before de-duplication"),
        (
            "Duplicate records removed",
            -data["duplicates"],
            "One copy kept per pair; most boxes wins, a 7/7 tie keeps the plain name",
        ),
        ("Distinct pictures", data["distinct"], ""),
        ("Pictures with no label removed", -data["unmarked"], "No class mark"),
        ("Labelled pictures", data["labelled"], ""),
        (
            "Clear pictures excluded",
            -data["clear"],
            "Excluded from the analysed set by the agreed scope; the model has no Clear output",
        ),
        ("Analysed pictures", data["analysed"], ""),
    ]
    row = 6
    for label, count, note_text in population:
        bold = label == "Analysed pictures"
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label, bold=bold)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, count, align=RIGHT, fmt=COUNT_FMT, bold=bold)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, note_text, font=NOTE_FONT)
        c3.alignment = LEFT
        ws.row_dimensions[row].height = 24 if len(note_text) < 70 else 32
        row += 1

    section(ws, 14, "Split", 4)
    header_row(ws, 15, ["Split", "Pictures", "Note", ""])
    ws.merge_cells(start_row=15, start_column=3, end_row=15, end_column=4)
    splits = [
        ("Train", data["splits"]["train"], "70%"),
        ("Validation", data["splits"]["val"], "15%"),
        ("Test", data["splits"]["test"], "15%; all per-class counts use these pictures"),
    ]
    row = 16
    for label, count, note_text in splits:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, count, align=RIGHT, fmt=COUNT_FMT)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, note_text, font=NOTE_FONT)
        c3.alignment = LEFT
        ws.row_dimensions[row].height = 20
        row += 1
    note(ws, row, "70/15/15 split, seed 42.", 4, sum(widths), 18)

    section(ws, 21, "Classes excluded as model outputs", 4)
    note(
        ws,
        22,
        "Six classes have fewer than 200 pictures. They are not model outputs; their pictures remain in the analysed set.",
        4,
        sum(widths),
        30,
    )
    header_row(ws, 23, ["Code", "Class", "Pictures carrying it", "Treatment"])
    row = 24
    for item in data["excluded"]:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, item["code"], bold=True)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, item["name"])
        c3 = ws.cell(row=row, column=3)
        body_cell(c3, item["pictures"], align=RIGHT, fmt=COUNT_FMT)
        c4 = ws.cell(row=row, column=4)
        body_cell(c4, "Column excluded; pictures kept", font=NOTE_FONT)
        ws.row_dimensions[row].height = 20
        row += 1

    union_row = row
    c1 = ws.cell(row=union_row, column=1)
    body_cell(c1, "Distinct pictures carrying at least one excluded class", bold=True)
    c2 = ws.cell(row=union_row, column=2)
    body_cell(c2, data["excluded_union"], align=RIGHT, fmt=COUNT_FMT, bold=True)
    ws.merge_cells(start_row=union_row, start_column=3, end_row=union_row, end_column=4)
    c3 = ws.cell(row=union_row, column=3)
    body_cell(c3, "The six class rows overlap; they do not add to this union.", font=NOTE_FONT)
    ws.row_dimensions[union_row].height = 32

    only_row = union_row + 1
    c1 = ws.cell(row=only_row, column=1)
    body_cell(c1, "Pictures carrying only excluded classes", bold=True)
    c2 = ws.cell(row=only_row, column=2)
    body_cell(c2, data["excluded_only"], align=RIGHT, fmt=COUNT_FMT, bold=True)
    ws.merge_cells(start_row=only_row, start_column=3, end_row=only_row, end_column=4)
    c3 = ws.cell(row=only_row, column=3)
    body_cell(c3, "No picture was dropped for these six classes.", font=NOTE_FONT)
    ws.row_dimensions[only_row].height = 20

    annotation = (
        f"Counts are pictures, not annotations. One Lens Rupture picture carries two annotations "
        f"({next(x['pictures'] for x in data['excluded'] if x['code'] == 'P1_LR')} pictures, "
        f"{data['p1_lr_annotations']} annotations)."
    )
    note(ws, only_row + 1, annotation, 4, sum(widths), 30)
    note(
        ws,
        only_row + 2,
        "Every one of the 281 pictures also carries at least one of the 17 modelled classes.",
        4,
        sum(widths),
        18,
    )

    section(ws, only_row + 4, "Modelled classes", 4)
    note(
        ws,
        only_row + 5,
        "17 classes: 10 lens presentation tags, 7 OOI tags. Four OOI tags carry an auxiliary size tag; "
        "the tag is not a model output.",
        4,
        sum(widths),
        30,
    )
    note(
        ws,
        only_row + 6,
        "The test set has 2,045 pictures. Every per-class count in this workbook uses those pictures.",
        4,
        sum(widths),
        18,
    )

    setup_print(ws, f"A1:D{only_row + 6}", paper="8", landscape=True, fit_height=1)


def build_method(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Method", GREY)
    set_widths(ws, [30, 92])
    title(ws, "Method", 2)
    line(ws, 2, "How the model was trained and scored.", 2, 22)
    model = data["model"]
    rows = [
        ("Model", model["arch"]),
        ("Input", f"{model['imgsz']} x {model['imgsz']} pixels"),
        ("Training pictures", f"{data['splits']['train']:,}"),
        ("Validation pictures", f"{data['splits']['val']:,}"),
        ("Test pictures", f"{data['splits']['test']:,}"),
        ("Epochs", str(model["epochs"])),
        ("Batch size", str(model["batch"])),
        ("Learning rate", f"{model['lr']:.4f}, SGD with momentum 0.9 (Nesterov)"),
        ("Loss", "BCEWithLogitsLoss with inverse-frequency class weights"),
        ("Seed", str(model["seed"])),
        ("Training time", f"{data['timing']['seconds_training'] / 60:.1f} minutes ({data['timing']['seconds_per_epoch']:.1f} s per epoch)"),
        ("Total run time", f"{data['timing']['seconds_total'] / 60:.1f} minutes"),
        ("Test inference", f"{data['timing']['seconds_inference']:.1f} s for {data['timing']['inference_images']:,} pictures ({data['timing']['inference_ms_per_image']:.2f} ms per picture)"),
        ("Main threshold", f"{data['threshold_rule']['default_threshold']:.2f}"),
        ("Test use", "Scored once"),
    ]
    header_row(ws, 4, ["Item", "Value"])
    row = 5
    for label, value in rows:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, label, bold=True)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, value)
        ws.row_dimensions[row].height = 22
        row += 1

    note(
        ws,
        row + 1,
        "The model outputs 17 independent class scores. A picture can carry more than one class. "
        "The four size tags are not model outputs; they are a separate reporting subset.",
        2,
        110,
        30,
    )
    note(
        ws,
        row + 2,
        "Inference was measured on the test set with batch size 8 on an A100 GPU.",
        2,
        110,
        18,
    )
    setup_print(ws, f"A1:B{row + 2}", paper="9", landscape=False)


def build_definitions(wb, data: dict) -> None:
    ws = add_page_sheet(wb, "Definitions", GREY)
    set_widths(ws, [30, 100])
    title(ws, "Definitions", 2)
    line(ws, 2, "Terms used in the tables.", 2, 22)
    definitions = [
        ("Test picture", "A picture held out from training and validation. All 2,045 are scored once."),
        (
            "Support",
            "The number of test pictures carrying the class. A picture can carry more than one class, so supports add to more than 2,045.",
        ),
        ("Prevalence", "Support divided by 2,045, shown as a percentage."),
        (
            "TA, FR, TR, FA",
            "Per class at the stated threshold, where the class is the defect. TA: class absent and predicted absent; FR: class absent and predicted present; TR: class present and predicted present; FA: class present and predicted absent. TA is large when a class is rare; it is not a quality score on its own.",
        ),
        (
            "TAR, TRR, FAR, FRR",
            "Picture-level rates from the pass/fail block. TAR = TA / (TA + FR); TRR = TR / (TR + FA); FAR = FA / (TR + FA); FRR = FR / (TA + FR). TAR + FRR = 100 percent; TRR + FAR = 100 percent.",
        ),
        ("Precision", "TR divided by TR plus FR. The share of predicted defects that are correct."),
        ("Recall", "TR divided by TR plus FA. The share of actual defects that are found."),
        ("F1", "The harmonic mean of precision and recall."),
        (
            "Macro",
            "The unweighted mean of the 17 per-class values. Each class counts equally, regardless of how many pictures carry it.",
        ),
        (
            "AUROC",
            "The chance that a random positive picture scores above a random negative picture. 0.5 is chance; 1.0 is perfect.",
        ),
        (
            "AUPRC",
            "The area under the precision-recall curve. The prevalence is the AUPRC of always answering present, so AUPRC is not comparable across classes with different prevalence.",
        ),
        ("Threshold", "The score cut for a positive decision. The main table uses 0.5."),
        (
            "Size tag",
            "An auxiliary tag on four OOI tags that records whether the object is above the size threshold. It is not a model output.",
        ),
        (
            "Pass class",
            "A class that can appear in a passing picture. Bubble passes alone. Foreign Matter, Fiber, HEMA and Extraneous Polymer pass only when untagged. The other 12 classes fail when present.",
        ),
        (
            "Truth pass, truth fail",
            "The picture-level verdict under the agreed rule. A picture is truth pass when it carries no fail condition, and truth fail otherwise.",
        ),
        (
            "Predicted pass, predicted fail",
            "The model's picture-level verdict from its 17 class scores at 0.5. Predicted pass means no fail score is at or above the cut.",
        ),
        ("Clear", "A picture marked clear (no defect). Clear pictures are excluded from the analysed set."),
        (
            "Excluded class",
            "A class with fewer than 200 pictures. It is not a model output; its pictures remain in the analysed set.",
        ),
        ("Positive class label", "One picture and one class that is present. The test set has 4,908."),
    ]
    header_row(ws, 4, ["Term", "Meaning"])
    row = 5
    for term, meaning in definitions:
        c1 = ws.cell(row=row, column=1)
        body_cell(c1, term, bold=True)
        c2 = ws.cell(row=row, column=2)
        body_cell(c2, meaning)
        ws.row_dimensions[row].height = 32 if len(meaning) < 140 else 46
        row += 1

    setup_print(ws, f"A1:B{row - 1}", paper="9", landscape=False)


def main() -> None:
    data = load_data()
    wb = Workbook()
    wb.remove(wb.active)

    for name, color in [
        ("Read me", NAVY),
        ("Summary", BLUE),
        ("Pass fail", BLUE),
        ("Pass images", BLUE),
        ("Per class", BLUE),
        ("Class split", BLUE),
        ("Selected thresholds", ORANGE),
        ("Threshold rule", ORANGE),
        ("Scope and exclusions", GREY),
        ("Method", GREY),
        ("Definitions", GREY),
    ]:
        add_page_sheet(wb, name, color)

    build_readme(wb, data)
    build_summary(wb, data)
    build_pass_fail(wb, data)
    build_pass_images(wb, data)
    build_per_class(wb, data)
    build_class_split(wb, data)
    build_selected_thresholds(wb, data)
    build_threshold_rule(wb, data)
    build_scope(wb, data)
    build_method(wb, data)
    build_definitions(wb, data)

    wb.properties.creator = "Pranay"
    wb.properties.lastModifiedBy = "Pranay"
    wb.properties.title = "Defect model results"
    wb.properties.subject = "Frozen test set, 17 defect classes"
    wb.properties.description = "Test results of one multi-label model on 2,045 held-out pictures."
    wb.properties.keywords = "defect, multi-label, test results"

    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
