"""Add 'the table quoted in the review, line by line' to Objects per class.

In-place edit of the answer workbook; styling matches the rest of the sheet.
"""
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

WB = "D:/fmd-analysis/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx"
ACCENT, BAND, NOTE = "1F3864", "D9E2F2", "595959"

SHEET = "Objects per class"

ROWS = [
    ("Bubble", "862 / 20,831", "862 / 11,045",
     "The picture count agrees. The object count has no source in the archive: every box of every class "
     "in all nine annotation files is 14,996, and the onboarding report also counts 11,045."),
    ("Bubble Cluster", "430 / 1,070", "428 / 1,182",
     "1,070 is the boxes in the seven production files; the other 112 come from the older library, and two "
     "pictures keep an older mark the current files no longer carry."),
    ("Wet Package", "146 / 593", "146 / 662",
     "593 counts only boxes carrying the P2_WP code; the other 69 carry the older plain Wet Package name."),
    ("Foreign Matter", "37 / 179", "331 / 626",
     "Neither figure matches the archive or the onboarding report: the production files alone hold 571 boxes, "
     "so 37 pictures and 179 objects match no counting basis we hold."),
    ("Fiber", "210 / flag 171 / 223", "210 / flag 136 / 277",
     "171 is the Foreign Matter flag count, not the Fiber one. 223 counts only boxes carrying P3_FIB; adding "
     "22 older Fiber boxes and 32 objects the newer annotation calls Extraneous Polymer gives 277."),
    ("Extraneous Polymer", "144 / flag 168 / 149", "112 / flag 33 / 118",
     "144 is the count before 32 objects moved to Fiber; the flag on those 144 pictures is 33. 168 is the "
     "Fiber flag in the training label list, which is why the row reads as more flagged objects than pictures."),
    ("HEMA", "101 / flag 94 / 99", "101 / flag 94 / 103",
     "99 leaves out the 4 boxes from the older library that the onboarding report also counts."),
    ("HEMA Obstruction (legacy)", "89 / 89", "86 pictures / no objects",
     "It is a whole-image tag, so it has no objects. The archive holds it on 86 pictures of record; the "
     "other 88 mentions are superseded."),
]

NOTES = [
    "Read down the two count columns with the note on the right: several figures in the quoted table count a "
    "different unit (boxes carrying one code, boxes in one file group, or a count taken before the 32 objects "
    "moved), which is what makes the five columns look inconsistent.",
    "One internal check closes the question: a size flag sits inside its class, so a class can never show more "
    "flagged objects than pictures. The Extraneous Polymer row shows 168 flagged on 144 pictures, so that row "
    "was assembled from two tables.",
    "The two reports we can test agree line by line in the table above: 14,182 objects on 1,130 pictures, both.",
]

wb = load_workbook(WB)
ws = wb[SHEET]
r = ws.max_row + 2


def put(row, values, bold=False, fill=None, color="000000", size=10, italic=False):
    for j, v in enumerate(values, start=1):
        c = ws.cell(row=row, column=j, value=v)
        c.font = Font(name="Calibri", size=size, bold=bold, italic=italic, color=color)
        if fill:
            c.fill = PatternFill("solid", start_color=fill, end_color=fill)
        c.alignment = Alignment(vertical="center", wrap_text=True)


put(r, ["The table quoted in the review, checked line by line"], bold=True, fill=BAND, color=ACCENT, size=12)
r += 1
put(r, ["Class", "Quoted: pictures / objects (flag)", "Our count: pictures / objects (flag)",
        "What the quoted figure counts"], bold=True, color="FFFFFF", fill=ACCENT)
for j in range(1, 5):
    ws.cell(row=r, column=j).fill = PatternFill("solid", start_color=ACCENT, end_color=ACCENT)
r += 1
for cls, quoted, ours, why in ROWS:
    put(r, [cls, quoted, ours, why])
    r += 1

r += 1
for n in NOTES:
    c = ws.cell(row=r, column=1, value=n)
    c.font = Font(name="Calibri", size=9, italic=True, color=NOTE)
    c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    r += 1

w = {"A": 30, "B": 24, "C": 26, "D": 96}
for col, width in w.items():
    ws.column_dimensions[col].width = width
ws.freeze_panes = "A4"
wb.save(WB)
print("added the quoted-table block to", SHEET, "at row", r - len(ROWS) - len(NOTES) - 3)
