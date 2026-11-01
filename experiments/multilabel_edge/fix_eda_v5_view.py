"""Restore view settings that the in-place edit dropped (freeze panes, widths)."""
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

WB = "D:/fmd-analysis/reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx"
WANT_FREEZE = {"Summary": "A4", "LP Summary": "A4", "Tag Combinations": "A4", "OOI Summary": "A4",
               "Standalone Tags": "A4", "Confusion Risks": "A4", "Earlier vs Current": "A4",
               "Training and Test Split": "A4", "Definitions": "A4"}
WANT_WIDTH = {"Summary": [56, 30, 14, 22], "LP Summary": [30, 12, 18, 20, 20, 20, 40],
              "Tag Combinations": [7, 56, 12, 26], "OOI Summary": [26, 10, 22, 24, 14, 16, 16, 62],
              "Standalone Tags": [34, 16, 30, 54], "Confusion Risks": [30, 30, 76, 14, 16],
              "Earlier vs Current": [34, 16, 14, 16, 14],
              "Training and Test Split": [32, 18, 16, 12, 48], "Definitions": [26, 100]}

wb = load_workbook(WB)
for name, cell in WANT_FREEZE.items():
    wb[name].freeze_panes = cell
for name, widths in WANT_WIDTH.items():
    ws = wb[name]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
wb.save(WB)
print("restored freeze panes and column widths on", len(WANT_FREEZE), "sheets")
