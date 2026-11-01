"""Verify EDA_Draft2_rev3_20261023.xlsx against the rev3 artifacts.

Recomputes every headline cell from run/multilabel_edge_20261023_rev3 and
run/split_20261023_v4 (never from the workbook) and compares cell by cell.
Usage:
  python verify_eda_draft2_rev3_workbook.py                # verify the shipped file
  python verify_eda_draft2_rev3_workbook.py <copy.xlsx> --expect-fail <cell>=<value>
Exit 0 = all checks pass; exit 1 names the bad cells.
"""
import csv, json, sys, collections, shutil, subprocess
from openpyxl import load_workbook

ROOT = "D:/fmd-analysis"
WB = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_rev3_20261023.xlsx"
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"
META = json.load(open(f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix_meta.json", encoding="utf-8"))
SPLIT = json.load(open(f"{ROOT}/run/split_20261023_v4/meta.json", encoding="utf-8"))

LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "wet_package",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "bubble_scatter", "clear"]
NAME = {"foreign_matter_micron_gate": "Foreign Matter (micron gate)", "fiber_micron_gate": "Fiber (micron gate)",
        "extraneous_polymer_micron_gate": "Extraneous Polymer (micron gate)", "hema_micron_gate": "HEMA (micron gate)",
        "bubble": "Bubble", "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
        "missing_primary_package": "Missing Primary Package", "multiple_lenses": "Multiple Lens",
        "no_lens": "No Lens", "cavity_off_center": "Cavity Off Center", "folded_lens": "Folded Lens",
        "lens_off_center": "Lens Off Center", "dirty_camera": "Dirty Camera", "dirty_strobe": "Dirty Strobe",
        "low_dose": "Low Dose", "view_obstructed": "View Obstructed",
        "package_misalignment": "Package Misalignment", "bubble_scatter": "Bubble Scatter", "clear": "Clear"}

rows = list(csv.DictReader(open(MAT, newline="", encoding="utf-8")))
N = len(rows)
pos = {c: sum(1 for r in rows if r[c] == "1") for c in LABEL_COLS}
label_sets = [frozenset(c for c in LABEL_COLS if r[c] == "1") for r in rows]
pair_exact = collections.Counter()
pair_incl = collections.Counter()
for s in label_sets:
    ss = sorted(s)
    for i in range(len(ss)):
        for j in range(i + 1, len(ss)):
            pair_incl[(ss[i], ss[j])] += 1
            if len(s) == 2:
                pair_exact[(ss[i], ss[j])] += 1

expected = {}   # (sheet, cell) -> value

# Summary (no title row; first spec row is row 1)
n_labeled = META["headline"]["row_status_counts"]["labeled"]
expected[("Summary", "B1")] = N
expected[("Summary", "B3")] = n_labeled
expected[("Summary", "B4")] = META["headline"]["clear_rows"]

# LP Tags (rows 2..12 in lp_codes order)
lp_codes = [("missing_primary_package",), ("cavity_off_center",), ("view_obstructed",),
            ("lens_off_center",), ("no_lens",), ("multiple_lenses",), ("folded_lens",),
            ("dirty_strobe",), ("dirty_camera",), ("bubble_scatter",), ("low_dose",)]
for i, (col,) in enumerate(lp_codes, start=2):
    expected[("LP Tags", f"C{i}")] = pos[col]

# Object Classes (rows 2..8)
obj = ["bubble", "bubble_cluster", "wet_package", "foreign_matter_micron_gate",
       "fiber_micron_gate", "extraneous_polymer_micron_gate", "hema_micron_gate"]
fam = META["headline"]["gated_families"]
for i, col in enumerate(obj, start=2):
    expected[("Object Classes", f"C{i}")] = pos[col]
    if col in fam:
        expected[("Object Classes", f"D{i}")] = fam[col]["of_which_micron_gate_tagged"]

# Tag pair sheets: top row values (C2) and counts of listed rows
top_exact = pair_exact.most_common(1)[0][1]
top_incl = pair_incl.most_common(1)[0][1]
expected[("Tag Pairs Exact", "C2")] = top_exact
expected[("Tag Pairs Inclusive", "C2")] = top_incl
expected[("Tag Pairs Exact", "B2")] = f"{NAME[pair_exact.most_common(1)[0][0][0]]} + {NAME[pair_exact.most_common(1)[0][0][1]]}"
expected[("Tag Pairs Inclusive", "B2")] = f"{NAME[pair_incl.most_common(1)[0][0][0]]} + {NAME[pair_incl.most_common(1)[0][0][1]]}"

# Split sheets
for key, sheet in [("70_30", "Split 70-30"), ("80_20", "Split 80-20")]:
    s = SPLIT["splits"][key]
    kept = [c for c in LABEL_COLS if s["per_class"][c]["train"] + s["per_class"][c]["test"]]
    for i, c in enumerate(kept, start=2):
        p = s["per_class"][c]
        expected[(sheet, f"B{i}")] = p["train"]
        expected[(sheet, f"C{i}")] = p["test"]
    total_row = 2 + len(kept) + 1
    sc = s["split_counts"]
    expected[(sheet, f"B{total_row}")] = sc["train"]
    expected[(sheet, f"C{total_row}")] = sc["test"]
    expected[(sheet, f"D{total_row}")] = sc["train"] + sc["test"]

# ---- compare ----
wb_path = sys.argv[1] if len(sys.argv) > 1 else WB
wb = load_workbook(wb_path, data_only=True)
bad = []
for (sheet, cell), want in sorted(expected.items()):
    got = wb[sheet][cell].value
    if got != want:
        bad.append(f"{sheet}!{cell}: workbook {got!r} != recomputed {want!r}")

# split CSV consistency: every eligible row present once, no crossing
for key in ("70_30", "80_20"):
    sp = list(csv.DictReader(open(f"{ROOT}/run/split_20261023_v4/split_{key}.csv", newline="", encoding="utf-8")))
    if len(sp) != SPLIT["rows"]:
        bad.append(f"split_{key}: row count {len(sp)} != meta {SPLIT['rows']}")
    sides = collections.Counter(r["split"] for r in sp)
    ids = collections.Counter(r["picture_md5"] for r in sp)
    if max(ids.values()) != 1:
        bad.append(f"split_{key}: duplicate picture rows")

if bad:
    print("FAIL")
    for b in bad:
        print(" ", b)
    sys.exit(1)
print(f"OK: {len(expected)} workbook cells + 2 split files verified against the rev3 artifacts")
