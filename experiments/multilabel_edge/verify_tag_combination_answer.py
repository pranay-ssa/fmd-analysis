"""Verify Tag_Combinations_Answer_20261025.xlsx against the source artifacts.

Recomputes every table from
  run/multilabel_edge_20261023_rev3/label_matrix.csv   (labels per picture, label list,
                                                        one-label, two-label tables)
  run/eda_full_20261015/resolved_labels.csv            (objects per class)
never from the workbook, compares cell by cell, then runs a corrupted-cell proof
on a temporary copy.

Usage:
  python verify_tag_combination_answer.py [workbook.xlsx]
Exit 0 = all checks pass, exit 1 names the bad cells.
"""
import csv, collections, sys, os, shutil, tempfile
from openpyxl import load_workbook

ROOT = "D:/fmd-analysis"
WB = f"{ROOT}/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261025.xlsx"
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"
RES = f"{ROOT}/run/eda_full_20261015/resolved_labels.csv"

meta_cols = {"picture_md5", "winning_path", "folder_group", "line", "mention_status",
             "negatives_reliable", "plain_family_present", "flip_exception",
             "split_eligible", "row_status"}
LEGACY = {"bubble_on_123", "bubble_on_edge", "hema_obstruction"}

rows = list(csv.DictReader(open(MAT, newline="", encoding="utf-8")))
cols = [c for c in rows[0] if c not in meta_cols and c not in LEGACY]
assert len(rows) == 6938 and len(cols) == 20, (len(rows), len(cols))

sets = [frozenset(c for c in cols if r[c] == "1") for r in rows]
card = collections.Counter(len(s) for s in sets)
single = collections.Counter(next(iter(s)) for s in sets if len(s) == 1)
pairs = collections.Counter(s for s in sets if len(s) == 2)
pos = {c: sum(1 for r in rows if r[c] == "1") for c in cols}

# hand-typed expectations, independent of the workbook
EXPECT = {
    "rows": 6938, "one": 5301, "two": 660, "zero": 248,
    "single_sum": 5301, "pair_sum": 660, "pairs_distinct": 21,
    "top_single": 2156, "top_pair": 374,
    "onboard": {1: 3256, 2: 654, 3: 216, 4: 14, 5: 1},
}
assert len(rows) == EXPECT["rows"]
assert card[0] == EXPECT["zero"] and card[1] == EXPECT["one"] and card[2] == EXPECT["two"]
assert sum(single.values()) == EXPECT["single_sum"] and len(single) == 18
assert sum(pairs.values()) == EXPECT["pair_sum"] and len(pairs) == EXPECT["pairs_distinct"]
assert single.most_common(1)[0][1] == EXPECT["top_single"]
assert pairs.most_common(1)[0][1] == EXPECT["top_pair"]

# objects: independent count with the older plain class names folded in
FAMILY = {
    "Bubble": ["P2_BB", "P2_BI", "P2_BST", "Bubble", "Bubble Irregular", "Stretched Bubble"],
    "Bubble Cluster": ["P2_BC", "Bubble Cluster"],
    "Wet Package": ["P2_WP", "Wet Package"],
    "Surface Groove": ["P1_SG"],
    "Fiber": ["P3_FIB", "Fiber"],
    "Extraneous Polymer": ["P3_EP", "Extraneous Polymer"],
    "HEMA": ["P3_HE", "HEMA Fragment"],
    "Foreign Matter": ["P3_FM", "Foreign Matter"],
    "Bubble On 123": ["Bubble On 123"],
    "Bubble On Edge": ["Bubble On Edge"],
}
boxes = [r for r in csv.DictReader(open(RES, newline="", encoding="utf-8"))
         if r["shape_kind"] == "box"]
obj = {}
for name, codes in FAMILY.items():
    sel = [r for r in boxes if r["code"] in codes]
    obj[name] = (len(sel), len({r["picture_md5"] for r in sel}))
OBJ_EXPECT = {"Bubble": (11045, 862), "Bubble Cluster": (1182, 428), "Wet Package": (662, 146),
              "Surface Groove": (0, 0), "Fiber": (245, 178), "Extraneous Polymer": (150, 144),
              "HEMA": (103, 101), "Foreign Matter": (626, 331),
              "Bubble On 123": (79, 13), "Bubble On Edge": (90, 14)}
assert obj == OBJ_EXPECT, {k: (obj[k], OBJ_EXPECT[k]) for k in obj if obj[k] != OBJ_EXPECT[k]}
assert sum(v[0] for v in obj.values()) == len(boxes) == 14182

NAME = {  # column -> workbook label
    "foreign_matter_micron_gate": "Foreign Matter gate", "fiber_micron_gate": "Fiber gate",
    "extraneous_polymer_micron_gate": "Extraneous Polymer gate", "hema_micron_gate": "HEMA gate",
    "bubble": "Bubble", "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
    "missing_primary_package": "Missing Primary Package", "multiple_lenses": "Multiple Lens",
    "no_lens": "No Lens", "cavity_off_center": "Cavity Off Center", "folded_lens": "Folded Lens",
    "lens_off_center": "Lens Off Center", "dirty_camera": "Dirty Camera", "dirty_strobe": "Dirty Strobe",
    "low_dose": "Low Dose", "view_obstructed": "View Obstructed", "package_misalignment": "Package Misalignment",
    "bubble_scatter": "Bubble Scatter", "clear": "Clear",
}

expected = {}

# Labels per picture
for k in range(0, 9):
    expected[("Labels per picture", f"B{5 + k}")] = card.get(k, 0)
expected[("Labels per picture", "B14")] = 6938
for k in range(1, 6):
    expected[("Labels per picture", f"B{17 + k}")] = EXPECT["onboard"][k]
expected[("Labels per picture", "B23")] = 4141

# Labels considered (row 4 is the first label; order follows the matrix columns)
order = ["foreign_matter_micron_gate", "fiber_micron_gate", "extraneous_polymer_micron_gate",
         "hema_micron_gate", "bubble", "bubble_cluster", "bubble_on_123", "bubble_on_edge",
         "wet_package", "bubble_scatter", "hema_obstruction", "missing_primary_package",
         "multiple_lenses", "no_lens", "cavity_off_center", "folded_lens", "lens_off_center",
         "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed", "package_misalignment", "clear"]
extra = {"bubble_on_123": 13, "bubble_on_edge": 14, "hema_obstruction": 86}
for i, c in enumerate(order, start=4):
    expected[("Labels considered", f"D{i}")] = pos.get(c, extra.get(c))
expected[("Labels considered", "D27")] = 6938

# One-label pictures: 18 rows starting at row 5
for i, (c, n) in enumerate(single.most_common(), start=1):
    expected[("One-label pictures", f"B{3 + i}")] = NAME[c]
    expected[("One-label pictures", f"C{3 + i}")] = n

# Two-label pictures: 21 rows starting at row 5
for i, (s, n) in enumerate(pairs.most_common(), start=1):
    expected[("Two-label pictures", f"B{3 + i}")] = " + ".join(sorted(NAME[c] for c in s))
    expected[("Two-label pictures", f"C{3 + i}")] = n

# Objects per class: 10 class rows starting at row 4
obj_order = ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
             "Extraneous Polymer", "HEMA", "Foreign Matter", "Bubble On 123", "Bubble On Edge"]
row_i = 4
for name in obj_order:
    if name == "Bubble On 123":
        row_i += 1  # section row before the reference classes
    expected[("Objects per class", f"A{row_i}")] = name
    expected[("Objects per class", f"C{row_i}")] = obj[name][0]
    expected[("Objects per class", f"D{row_i}")] = obj[name][1]
    row_i += 1
total_row = row_i
expected[("Objects per class", f"C{total_row}")] = 14182
expected[("Objects per class", f"D{total_row}")] = 1130
expected[("Objects per class", f"E{total_row}")] = 14182


def check(path):
    wb = load_workbook(path, data_only=True)
    bad = []
    for (sheet, cell), want in sorted(expected.items()):
        got = wb[sheet][cell].value
        if got != want:
            bad.append(f"{sheet}!{cell}: workbook {got!r} != recomputed {want!r}")
    # row-count guards, so a silently empty table cannot pass
    guards = [("One-label pictures", 18), ("Two-label pictures", 21), ("Objects per class", 10)]
    for sheet, n in guards:
        labels = [r for r in wb[sheet].iter_rows(min_col=2, max_col=2, values_only=True)
                  if r[0] and str(r[0]).strip()]
        if len(labels) < n:
            bad.append(f"{sheet}: expected at least {n} label rows, found {len(labels)}")
    return bad


wb_path = sys.argv[1] if len(sys.argv) > 1 else WB
bad = check(wb_path)
print(f"checked {len(expected)} cells in {os.path.basename(wb_path)}")
if bad:
    print("FAIL")
    for b in bad:
        print("  ", b)
    sys.exit(1)

# corrupted-cell proof: one wrong number must be caught
with tempfile.TemporaryDirectory() as td:
    copy = os.path.join(td, "tampered.xlsx")
    shutil.copy(wb_path, copy)
    wb = load_workbook(copy)
    cell = wb["One-label pictures"]["C5"]
    cell.value = (cell.value or 0) + 1
    wb.save(copy)
    tampered = check(copy)
    if not tampered:
        print("FAIL: a tampered cell was not caught")
        sys.exit(1)
    print("corrupted-cell proof: caught", len(tampered), "bad cell(s) as expected")

print("PASS: all cells match the recomputed artifacts")
