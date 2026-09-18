"""Build Comparision_CORRECTED_20260908.xlsx containing yesterday's and today's tables.
Avoids the locked Comparision.xlsx (open in Excel) by writing a new workbook."""
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

OUT = "D:/02-SSA/fmd-analysis/Comparision_CORRECTED_20260908.xlsx"
bold = Font(bold=True)
hfill = PatternFill("solid", fgColor="D9E1F2")

wb = openpyxl.Workbook()
wb.remove(wb.active)


def sheet(title, headers, rows):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in ws[1]:
        c.font = bold
        c.fill = hfill
    for r in rows:
        ws.append(r)
    for i in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(i)].width = max(
            12, 8 + max(len(str(h)) for h in headers))
    return ws


# Yesterday: OOI vs Team (from Sheet1)
sheet("Yesterday_OOI_vs_Team",
      ["Architecture", "OOI Train (s)", "OOI Test (s)", "OOI Total (s)", "OOI ms/img (÷87)",
       "Team Train (s)", "Team Test (s)", "Team Total (s)", "Team ms/img (÷93)"],
      [["ResNet18", 46.55, 0.8213, 47.37, 9.44, 48.25, 0.8409, 49.09, 9.042],
       ["ResNet50", 114.99, 2.2934, 117.28, 26.361, 120.97, 2.3325, 123.3, 25.081],
       ["ResNet50-Inception", 138.02, 3.2531, 141.27, 37.392, 145.85, 3.0349, 148.88, 32.633],
       ["ResNet50-SE", 126.92, 2.5845, 129.5, 29.707, 133.96, 2.9012, 136.86, 31.196]])

sheet("Yesterday_Lens",
      ["Architecture", "Lens Train (s)", "Lens Test (s)", "Lens Total (s)", "Lens ms/img (÷201)"],
      [["ResNet18", 96.63, 0.8672, 97.5, 4.314],
       ["ResNet50", 238.51, 2.3992, 240.91, 11.936],
       ["ResNet50-Inception", 289.95, 3.0911, 293.04, 15.379],
       ["ResNet50-SE", 266.29, 2.6676, 268.96, 13.272]])

# Corrected comparison (ms/img only)
sheet("Corrected_20260908",
      ["Architecture", "OOI ms/img CORRECTED (87)", "OOI ms/img yesterday warm",
       "OOI ms/img yesterday no-warm", "Lens ms/img CORRECTED (201)",
       "Lens ms/img yesterday warm", "Lens ms/img yesterday no-warm", "OOI Acc %", "Lens Acc %"],
      [["ResNet18", 0.974, 5.163, 9.441, 0.722, 2.475, 4.314, 68.97, 90.55],
       ["ResNet50", 1.393, 14.116, 26.361, 1.372, 6.367, 11.936, 65.52, 98.01],
       ["ResNet50-Inception", 1.758, 22.888, 37.392, 1.695, 9.947, 15.379, 71.26, 97.51],
       ["ResNet50-SE", 1.744, 16.738, 29.707, 1.667, 7.566, 13.271, 66.67, 96.02]])

# Today's OOI / Lens tables in Sheet1 layout
sheet("Corrected_OOI_20260908",
      ["Architecture", "OOI Train (s)", "OOI Test (s)", "OOI Total (s)", "OOI ms/img (÷87)"],
      [["ResNet18", 46.39, 0.0847, round(46.39 + 0.0847, 4), 0.974],
       ["ResNet50", 115.61, 0.1212, round(115.61 + 0.1212, 4), 1.393],
       ["ResNet50-Inception", 138.85, 0.1530, round(138.85 + 0.1530, 4), 1.758],
       ["ResNet50-SE", 127.88, 0.1517, round(127.88 + 0.1517, 4), 1.744]])

sheet("Corrected_Lens_20260908",
      ["Architecture", "Lens Train (s)", "Lens Test (s)", "Lens Total (s)", "Lens ms/img (÷201)"],
      [["ResNet18", 95.80, 0.1451, round(95.80 + 0.1451, 4), 0.722],
       ["ResNet50", 244.10, 0.2759, round(244.10 + 0.2759, 4), 1.373],
       ["ResNet50-Inception", 290.80, 0.3406, round(290.80 + 0.3406, 4), 1.695],
       ["ResNet50-SE", 267.84, 0.3350, round(267.84 + 0.3350, 4), 1.667]])

wb.save(OUT)
print("saved", OUT)
print("sheets:", wb.sheetnames)