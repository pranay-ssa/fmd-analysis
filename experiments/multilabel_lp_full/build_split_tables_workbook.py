"""Per-class train/test split tables for the lead.

One workbook, four tables: run 1 and run 2 of the 2026-10-28 experiment and run 1 and
run 2 of the 2026-10-29 experiment. Counts are read from the split label tables of each
run and cross-checked against the run metrics before the workbook is written.

Run as:  uv run python experiments/multilabel_lp_full/build_split_tables_workbook.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
RUNS = {
    "20261028": ROOT / "run/multilabel_lp_full_20261028",
    "20261029": ROOT / "run/multilabel_lp_full_20261029",
}
OUT = ROOT / "reports/multilabel_production/FMD_Split_By_Class_20261030.xlsx"

# What each experiment was, and when the lead saw it.
EXPERIMENTS = [
    ("20261028", "Experiment results of 2026-10-28, shared with you on 2026-10-29",
     "Seven revised annotation files, 1,047 pictures."),
    ("20261029", "Experiment results of 2026-10-29, shared with you today, 2026-10-30",
     "All twenty-four annotation files, 3,597 pictures, the full annotation of record."),
]

CLS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL",
       "P2_LD", "P1_COC", "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]
NAMES = {"P1_MPP": "Missing Primary Package", "P1_ML": "Multiple Lens",
         "P2_LOC": "Lens Off Center", "P2_DC": "Dirty Camera", "P1_NL": "No Lens",
         "P1_FL": "Folded Lens", "P2_LD": "Low Dose", "P1_COC": "Cavity Off Center",
         "P2_DS": "Dirty Strobe", "P2_FOV": "View Obstructed",
         "P2_BSC": "Bubble Scatter", "P1_PPM": "Package Misalignment"}


def split_counts(run_dir: Path, labels_file: str) -> tuple[dict, dict]:
    counts = {c: {"train": 0, "test": 0} for c in CLS}
    totals = {"train": 0, "test": 0}
    with open(run_dir / labels_file, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            totals[row["split"]] += 1
            for c in CLS:
                if row[c] == "1":
                    counts[c][row["split"]] += 1
    return counts, totals


def check_against_metrics(run_dir: Path, variant: str, counts: dict, totals: dict) -> None:
    m = json.loads((run_dir / variant / "metrics.json").read_text(encoding="utf-8"))
    assert totals["test"] == m["rows"], (variant, totals, m["rows"])
    for code, v in m["per_class"].items():
        assert counts[code]["test"] == v["support"], (variant, code, counts[code], v["support"])


DATA = {}
for date, run_dir in RUNS.items():
    for variant, labels_file in (("a", "labels_a.csv"), ("b", "labels_b.csv")):
        counts, totals = split_counts(run_dir, labels_file)
        check_against_metrics(run_dir, variant, counts, totals)
        DATA[(date, variant)] = (counts, totals)

# ---------------------------------------------------------------- workbook styling
HDR_FILL = PatternFill("solid", fgColor="1F3B57")
HDR_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14)
TABLE_FONT = Font(bold=True, size=12)
NOTE_FONT = Font(italic=True, size=9, color="555555")
BOX_FILL = PatternFill("solid", fgColor="F2F5F9")
THIN = Side(style="thin", color="CCCCCC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

RUN_LABELS = {
    "a": "Run 1: twelve lens-presentation classes",
    "b": "Run 2: the same twelve classes plus the object flag",
}


def class_table(ws, start_row, title, counts, totals):
    ws.cell(row=start_row, column=1, value=title).font = TABLE_FONT
    header = ["LP class", "Pictures for training", "Pictures held back for testing",
              "All pictures with the class"]
    r0 = start_row + 1
    for j, h in enumerate(header, start=1):
        c = ws.cell(row=r0, column=j, value=h)
        c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
    r = r0 + 1
    for code in CLS:
        t, s = counts[code]["train"], counts[code]["test"]
        for j, v in enumerate((NAMES[code], t, s, t + s), start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BORDER
            if j > 1:
                c.number_format = "#,##0"
            c.alignment = Alignment(vertical="top")
        r += 1
    for j, v in enumerate(("All classes", totals["train"], totals["test"],
                           totals["train"] + totals["test"]), start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.font = Font(bold=True)
        c.fill, c.border = BOX_FILL, BORDER
        if j > 1:
            c.number_format = "#,##0"
    for j, w in enumerate((30, 22, 26, 24), start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    return r + 2


wb = Workbook()
wb.remove(wb.active)

for date, heading, population in EXPERIMENTS:
    ws = wb.create_sheet(f"Results {date}")
    ws["A1"] = heading
    ws["A1"].font = TITLE_FONT
    ws["A2"] = (f"Where the pictures with each lens-presentation class went in each run: "
                f"{population} Both runs split the same pictures 80 / 20: four pictures in "
                "five teach the model, one in five is held back and used only to measure.")
    ws["A2"].font = NOTE_FONT
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")

    ca, ta = DATA[(date, "a")]
    cb, tb = DATA[(date, "b")]
    nxt = class_table(ws, 4, RUN_LABELS["a"], ca, ta)
    nxt = class_table(ws, nxt, RUN_LABELS["b"], cb, tb)
    ws.cell(row=nxt, column=1,
            value="A picture can carry more than one class, so the class rows do not add up "
                  "to the total row. The total row counts pictures, the class rows count "
                  "pictures carrying that class.").font = NOTE_FONT
    ws.freeze_panes = "A4"

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print(f"written {OUT}")
