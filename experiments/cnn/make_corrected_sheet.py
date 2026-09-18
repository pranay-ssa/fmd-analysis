"""Append a Corrected_20260908 comparison sheet to Comparision.xlsx.

Pairs yesterday's (2026-09-07 reported) numbers against the corrected (2026-09-08)
numbers from ooi_warmup_corrected / lens_warmup_corrected. Existing sheets untouched.
Run:  uv run samples/make_corrected_sheet.py
"""
import shutil
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

SRC = "D:/02-SSA/fmd-analysis/Comparision.xlsx"
BAK = "D:/02-SSA/fmd-analysis/Comparision_backup_before_corrected.xlsx"

rows = [
    # arch, OOI_corr, OOI_yest_warm, OOI_yest_nowarm, Lens_corr, Lens_yest_warm, Lens_yest_nowarm, OOI_acc, Lens_acc
    ("ResNet18",             0.974, 5.163,  9.441,  0.722, 2.475,  4.314,  68.97, 90.55),
    ("ResNet50",             1.393, 14.116, 26.361, 1.372, 6.367,  11.936, 65.52, 98.01),
    ("ResNet50-Inception",   1.758, 22.888, 37.392, 1.695, 9.947,  15.379, 71.26, 97.51),
    ("ResNet50-SE",          1.744, 16.738, 29.707, 1.667, 7.566,  13.271, 66.67, 96.02),
]

test_s = [  # (OOI_corrected_total_s, Lens_corrected_total_s)
    (0.0847, 0.1451),
    (0.1212, 0.2759),
    (0.1530, 0.3406),
    (0.1517, 0.3350),
]

headers = [
    "Architecture",
    "OOI ms/img CORRECTED (87)",
    "OOI ms/img yesterday warm",
    "OOI ms/img yesterday no-warm",
    "Lens ms/img CORRECTED (201)",
    "Lens ms/img yesterday warm",
    "Lens ms/img yesterday no-warm",
    "OOI Acc %",
    "Lens Acc %",
]

shutil.copyfile(SRC, BAK)

wb = openpyxl.load_workbook(SRC)
if "Corrected_20260908" in wb.sheetnames:
    del wb["Corrected_20260908"]
ws = wb.create_sheet("Corrected_20260908")

hfill = PatternFill("solid", fgColor="D9E1F2")
bold = Font(bold=True)
ws.append(headers)
for c in ws[1]:
    c.font = bold
    c.fill = hfill
ws.append([""])
ws.append(["NOTE: CORRECTED = fully warmed on real test pipeline (2 dummy + 1 throwaway predict), 2026-09-08."])
ws.append(["yesterday = figures reported in OOI_CNN_Analysis_20260907.md (no-warm and dummy-only warmup)."])
ws.append(["The 5-37 ms/img 'yesterday' numbers carry a one-time ~1.1s predict re-trace; corrected ~1-1.8 ms/img is the true forward pass."])
ws.append([""])

for (r, ts) in zip(rows, test_s):
    ws.append(list(r) + [ts[0], ts[1]])

# extra header continuation for the appended test-seconds columns
# (placed after the data for readability put them alongside instead)
widths = [20, 22, 22, 23, 22, 22, 23, 12, 12]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

wb.save(SRC)
print("Wrote sheet 'Corrected_20260908' to", SRC)
print("Backup:", BAK)
print("Row count:", ws.max_row)