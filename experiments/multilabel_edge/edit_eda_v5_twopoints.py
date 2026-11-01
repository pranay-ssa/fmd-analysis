"""Two in-place edits on EDA_Draft2_20261026.xlsx, keeping the user's formatting.

1. Summary: drop the Debris group row (the four classes stay, per class).
2. Confusion Risks: fill the two n/a co-occurrence counts and add a note that
   explains the numbers in brackets.

Nothing else is touched; the workbook is saved in place.
"""
import csv, collections
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

WB = "D:/fmd-analysis/reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx"
RES = "D:/fmd-analysis/run/eda_full_20261015/resolved_labels.csv"
MAT = "D:/fmd-analysis/run/multilabel_edge_20261023_rev3/label_matrix.csv"

# co-occurrence counts for the two rows that carried "n/a"
codes = collections.defaultdict(set)
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    codes[r["picture_md5"]].add(r["code"])
flip = {r["picture_md5"] for r in csv.DictReader(open(MAT, newline="", encoding="utf-8"))
        if r["fiber_micron_gate"] == "1" and "P3_FIB_MICRON_THRESHOLD" not in codes[r["picture_md5"]]}


def has(p, names):
    s = {n for n in codes[p]}
    if p in flip:
        if "P3_EP" in s:
            s.discard("P3_EP"); s.add("P3_FIB")
    return bool(s & names)


ep_fiber = sum(1 for p in codes if has(p, {"P3_EP", "Extraneous Polymer"}) and has(p, {"P3_FIB", "Fiber"}))
ds_dc = sum(1 for p in codes if has(p, {"P2_DS"}) and has(p, {"P2_DC"}))
print("EP & Fiber together:", ep_fiber, "| Dirty Strobe & Dirty Camera together:", ds_dc)

wb = load_workbook(WB)

# 1. Summary: drop the Debris group row
ws = wb["Summary"]
drop = None
for i, row in enumerate(ws.iter_rows(min_col=1, max_col=1), start=1):
    if row[0].value and str(row[0].value).startswith("Debris group"):
        drop = i
        break
if drop:
    ws.delete_rows(drop, 1)
    print("Summary: removed the Debris group row at", drop)
else:
    print("Summary: no Debris group row found")

# 2. Confusion Risks: fill the n/a cells, add the note
ws = wb["Confusion Risks"]
for row in ws.iter_rows(min_row=1):
    a = row[0].value
    if a == "Extraneous Polymer" and row[1].value == "Fiber":
        row[4].value = ep_fiber
    elif a and str(a).startswith("Dirty Strobe (") and row[1].value and str(row[1].value).startswith("Dirty Camera"):
        row[4].value = ds_dc
last = ws.max_row
note = ("The number in brackets after a class is how many pictures carry that class, from the Summary "
        "sheet. The last column counts the pictures carrying both classes; a zero means the two never "
        "appear on the same picture.")
c = ws.cell(row=last + 1, column=1, value=note)
c.font = Font(name="Calibri", size=9, italic=True, color="595959")
c.alignment = Alignment(vertical="center", wrap_text=True)
ws.merge_cells(start_row=last + 1, start_column=1, end_row=last + 1, end_column=5)
print("Confusion Risks: n/a replaced, note added at row", last + 1)

wb.save(WB)
print("saved", WB)
