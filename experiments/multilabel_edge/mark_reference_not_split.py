"""Mark the three reference labels as not-split-positives, and say so on the split sheet.

In-place edits, no rebuild, so formatting edits by hand survive.
"""
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

EDA = "D:/fmd-analysis/reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx"
ANS = "D:/fmd-analysis/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx"
REF = {"HEMA Obstruction", "Bubble On 123", "Bubble On Edge"}

# answer workbook: Labels considered, column E ("Counted as a label")
wb = load_workbook(ANS)
ws = wb["Labels considered"]
changed = 0
for row in ws.iter_rows(min_row=1):
    if row[0].value in REF and row[4].value == "Yes":
        row[4].value = "Reference only, not in the split"
        changed += 1
wb.save(ANS)
print("answer workbook: marked", changed, "reference labels")

# EDA workbook: note at the foot of the split sheet
wb = load_workbook(EDA)
ws = wb["Training and Test Split"]
r = ws.max_row + 2
c = ws.cell(row=r, column=1, value=(
    "Only the Draft 2 codes and Clear are positives. 105 pictures whose only marks are HEMA Obstruction, "
    "Bubble On 123 or Bubble On Edge are left out, so the split covers 6,574 pictures out of the 6,679 that "
    "can otherwise enter."))
c.font = Font(name="Calibri", size=9, italic=True, color="595959")
c.alignment = Alignment(vertical="center", wrap_text=True)
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
wb.save(EDA)
print("EDA workbook: note added to Training and Test Split at row", r)
