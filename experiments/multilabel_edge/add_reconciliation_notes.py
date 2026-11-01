"""Add 'why rows do not add up' reconciliation lines to the reader workbook.

Runs in place on the existing file so hand edits are preserved. Each new row
explains that class rows count class memberships while totals count pictures.
"""
import json, csv, copy
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

XLSX = "D:/fmd-analysis/reports/draft2_eda_20261023/EDA_Draft2_20261023.xlsx"
meta = json.load(open("D:/fmd-analysis/run/split_20261023_v3/meta.json"))
rows = list(csv.DictReader(open("D:/fmd-analysis/run/multilabel_edge_20261023/label_matrix.csv",
                                newline="", encoding="utf-8")))
matrix = {r["picture_md5"]: r for r in rows}
split = list(csv.DictReader(open("D:/fmd-analysis/run/split_20261023_v3/split.csv",
                                 newline="", encoding="utf-8")))
kept = list(meta["per_class"])
extra = {"train": 0, "test": 0}
multi = {"train": 0, "test": 0}
for r in split:
    m = matrix[r["picture_md5"]]
    k = sum(1 for c in kept if m.get(c) == "1")
    extra[r["split"]] += max(0, k - 1)
    multi[r["split"]] += int(k > 1)
train_sum = sum(v["train"] for v in meta["per_class"].values())
test_sum = sum(v["test"] for v in meta["per_class"].values())
assert (train_sum, test_sum) == (6268, 2675)

NOTE_FILL = PatternFill("solid", fgColor="FFF2CC")
SUM_FILL = PatternFill("solid", fgColor="EDEDED")
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = load_workbook(XLSX)

# --- Training and Test Split: sum-of-rows line under the Total ---
ws = wb["Training and Test Split"]
total_row = next(r for r in range(1, ws.max_row + 1)
                 if ws.cell(row=r, column=1).value == "Total")
ws.insert_rows(total_row + 1)
vals = ["Sum of the class rows above", train_sum, test_sum, train_sum + test_sum, None, None,
        f"Larger than the total because {multi['train']} training and {multi['test']} test "
        f"pictures carry more than one class"]
for col, v in enumerate(vals, start=1):
    c = ws.cell(row=total_row + 1, column=col, value=v)
    c.fill = SUM_FILL
    c.border = BORDER
    c.font = Font(italic=True, size=10)
    c.alignment = Alignment(wrap_text=True, vertical="top")

# --- Class Summary: note at the bottom ---
ws = wb["LP Summary"]
r = ws.max_row + 2
c = ws.cell(row=r, column=1,
            value="Class rows are not additive: a picture can carry several tags, so the rows above "
                  "sum to 7,328 against 6,785 distinct pictures. Clear never shares a picture.")
c.font = Font(italic=True, size=10)
c.fill = NOTE_FILL
c.alignment = Alignment(wrap_text=True, vertical="top")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
ws.row_dimensions[r].height = 30

# --- Objects: note under the total ---
ws = wb["Objects"]
r = ws.max_row + 2
c = ws.cell(row=r, column=1,
            value="Pictures with this object are not additive: 2,098 placements across 1,130 distinct "
                  "pictures. Objects marked is additive and equals the total (12,783).")
c.font = Font(italic=True, size=10)
c.fill = NOTE_FILL
c.alignment = Alignment(wrap_text=True, vertical="top")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=12)
ws.row_dimensions[r].height = 30

# --- Summary: note under the main classes ---
ws = wb["Summary"]
r = ws.max_row + 2
c = ws.cell(row=r, column=1,
            value="Rows are not additive: a picture can carry several classes, so the class rows sum "
                  "to more than the picture totals above.")
c.font = Font(italic=True, size=10)
c.fill = NOTE_FILL
c.alignment = Alignment(wrap_text=True, vertical="top")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
ws.row_dimensions[r].height = 28

# --- Definitions: one new term ---
ws = wb["Definitions"]
r = ws.max_row + 1
a = ws.cell(row=r, column=1, value="Why class rows do not add up to the totals")
b = ws.cell(row=r, column=2,
            value="A picture can carry more than one tag, or several marked objects. Class rows therefore "
                  "count class memberships: 4,568 training pictures carry 6,268 class memberships. The "
                  "training and test totals count each picture once, so they are smaller than the column "
                  "sums. The count of marked objects is the exception: each object belongs to one class, "
                  "so that column does add up to its total.")
for c in (a, b):
    c.border = BORDER
    c.alignment = Alignment(wrap_text=True, vertical="top")
a.font = Font(bold=True, size=10)
b.font = Font(size=10)
ws.row_dimensions[r].height = 60
# keep the open-points note last
last_note = ws.cell(row=r + 2, column=1,
                    value="Open points for confirmation: the production code for Field of View Obstructed; "
                          "the code for Stretched Bubble; the size limit for the size flags; and whether the "
                          "Low Dose folder is fully annotated.")
last_note.font = Font(italic=True, size=10)
last_note.alignment = Alignment(wrap_text=True, vertical="top")
ws.merge_cells(start_row=r + 2, start_column=1, end_row=r + 2, end_column=2)
ws.row_dimensions[r + 2].height = 32

wb.save(XLSX)
print("reconciliation rows added:", {
    "train_rows_sum": train_sum, "test_rows_sum": test_sum,
    "extra_memberships": extra, "multi_label_pictures": multi})
