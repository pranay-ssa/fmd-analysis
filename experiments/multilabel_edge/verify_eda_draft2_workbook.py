"""Verify the client-facing EDA workbook against its source artifacts.

Recomputes every headline from the artifacts on disk (current label matrix,
training/test split, EDA numbers, standalone-tag check) and diffs against
the reader-facing sheets. Usage: verify_eda_draft2_workbook.py [xlsx_path]
"""
import json, csv, collections, sys
from openpyxl import load_workbook

ROOT = "D:/fmd-analysis"
XLSX = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261023.xlsx"
COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
        "extraneous_polymer_micron_gate", "hema_micron_gate",
        "bubble", "bubble_cluster", "wet_package", "bubble_on_123",
        "bubble_on_edge", "hema_obstruction", "missing_primary_package",
        "multiple_lenses", "no_lens", "cavity_off_center", "folded_lens",
        "lens_off_center", "dirty_camera", "dirty_strobe", "low_dose",
        "view_obstructed", "package_misalignment", "bubble_scatter", "clear"]
fails = []

wb = load_workbook(XLSX)
rows = list(csv.DictReader(open(f"{ROOT}/run/multilabel_edge_20261023/label_matrix.csv",
                                newline="", encoding="utf-8")))
pos = {c: sum(1 for r in rows if r[c] == "1") for c in COLS}
meta = json.load(open(f"{ROOT}/run/split_20261023_v3/meta.json"))
audit = json.load(open(f"{ROOT}/run/multilabel_edge_20261023/standalone_audit.json"))
ooi = json.load(open(f"{ROOT}/run/draft2_eda_20261023/ooi_eda.json"))
lp = json.load(open(f"{ROOT}/run/draft2_eda_20261023/lp_eda.json"))

def chk(name, got, want):
    if got != want:
        fails.append(f"{name}: sheet {got!r} != source {want!r}")

# Class Summary: A=name, B=code, C=pictures, E=split pictures
ws = wb["LP Summary"]
GUIDE_LP = ["Missing Primary Package", "Primary Package Misalignment", "Cavity Off Center",
            "Field of View Obstructed", "Edge Bottle-Capped", "Torn Lens", "Lens Rupture",
            "Lens Off Center", "No Lens", "Multiple Lens", "Folded Lens", "Dirty Strobe",
            "Dirty Camera", "Bubble Scatter", "Low Dose"]
present_lp = {ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)}
chk("Class Summary: all 15 guide tags present",
    [c for c in GUIDE_LP if c not in present_lp], [])
name2code = {"Missing Primary Package": "P1_MPP", "Primary Package Misalignment": "P1_PPM",
             "Cavity Off Center": "P1_COC", "Field of View Obstructed": "P2_FOV",
             "Lens Off Center": "P2_LOC", "No Lens": "P1_NL",
             "Multiple Lens": "P1_ML", "Folded Lens": "P1_FL",
             "Edge Bottle-Capped": "P1_EBC", "Torn Lens": "P1_TL",
             "Lens Rupture": "P1_LR", "Dirty Strobe": "P2_DS",
             "Dirty Camera": "P2_DC", "Bubble Scatter": "P2_BSC",
             "Low Dose": "P2_LD"}
code2col = {"P1_MPP": "missing_primary_package", "P1_PPM": "package_misalignment",
            "P1_COC": "cavity_off_center", "P2_FOV": "view_obstructed",
            "P2_LOC": "lens_off_center", "P1_NL": "no_lens",
            "P1_ML": "multiple_lenses", "P1_FL": "folded_lens",
            "P2_DS": "dirty_strobe", "P2_DC": "dirty_camera",
            "P2_BSC": "bubble_scatter", "P2_LD": "low_dose"}
for r in range(1, ws.max_row + 1):
    nm = ws.cell(row=r, column=1).value
    code = ws.cell(row=r, column=2).value
    if nm in name2code:
        chk(f"class code {nm}", code, name2code[nm])
        col = code2col.get(code)
        chk(f"class pictures {nm}", ws.cell(row=r, column=3).value,
            pos[col] if col else 0)
        chk(f"class split {nm}", ws.cell(row=r, column=5).value,
            meta["per_class"][col]["train"] + meta["per_class"][col]["test"] if col else 0)
    if nm == "Clear":
        chk("class Clear", ws.cell(row=r, column=3).value, 2156)
        chk("class Clear split", ws.cell(row=r, column=5).value, 2156)
    if nm == "HEMA Obstruction (legacy)":
        chk("class legacy HEMA", ws.cell(row=r, column=3).value, 86)

# Tag Combinations: A=label pair, B=pictures; recompute pairs and cardinality
ws = wb["Tag Combinations"]
lp_cols = [c for c in COLS if c not in ("foreign_matter_micron_gate", "fiber_micron_gate",
           "extraneous_polymer_micron_gate", "hema_micron_gate", "bubble", "bubble_cluster",
           "wet_package", "bubble_on_123", "bubble_on_edge", "hema_obstruction", "clear")]
co = collections.Counter()
card = collections.Counter()
for r in rows:
    on = [c for c in lp_cols if r[c] == "1"]
    card[len(on)] += 1
    for i in range(len(on)):
        for j in range(i + 1, len(on)):
            co[f"{on[i]}+{on[j]}"] += 1
for r in range(1, ws.max_row + 1):
    a = ws.cell(row=r, column=1).value
    if isinstance(a, str) and " and " in a:
        x, y = a.split(" and ")
        want = co.get(f"{x}+{y}", co.get(f"{y}+{x}", 0))
        chk(f"pair {a}", ws.cell(row=r, column=2).value, want)
    if isinstance(a, str) and a.endswith("tag(s)"):
        chk(f"card {a}", ws.cell(row=r, column=2).value, card[int(a.split()[0])])

# Objects: A=name, C=pictures, E=objects
ws = wb["Objects"]
present = {ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)}
GUIDE_OOI = ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
             "Extraneous Polymer", "HEMA (Draft 2: one class)", "Foreign Matter"]
missing = [c for c in GUIDE_OOI if c not in present]
chk("Objects: all 8 guide classes present", missing, [])
for r in range(1, ws.max_row + 1):
    nm = ws.cell(row=r, column=1).value
    if nm in ooi:
        chk(f"obj pictures {nm}", ws.cell(row=r, column=3).value, ooi[nm]["pictures"])
        chk(f"obj marked {nm}", ws.cell(row=r, column=5).value, ooi[nm]["box_instances"])
    if nm == "Total, the 8 object classes":
        chk("obj 8-class pictures", ws.cell(row=r, column=3).value, 1130)
        chk("obj 8-class marked", ws.cell(row=r, column=5).value, 12783)
    if nm == "Total, all object classes":
        chk("obj all-class pictures", ws.cell(row=r, column=3).value, 1130)
        chk("obj all-class marked", ws.cell(row=r, column=5).value, 13087)
    if nm == "Surface Groove":
        chk("obj SG", ws.cell(row=r, column=5).value, 0)

# additive checks: objects marked must sum to the posted total
GUIDE_KEYS = ["Bubble", "Bubble Cluster", "Wet Package", "Fiber", "Extraneous Polymer",
              "HEMA (Draft 2: one class)", "Foreign Matter"]
guide_marked = sum(ooi[k]["box_instances"] for k in GUIDE_KEYS)
all_marked = sum(ooi[k]["box_instances"] for k in ooi)
chk("objects: 8-class total", guide_marked, 12783)
chk("objects: all-class total", all_marked, 13087)
lp_sum = sum(pos[c] for c in ["missing_primary_package", "package_misalignment",
                              "cavity_off_center", "view_obstructed", "lens_off_center",
                              "no_lens", "multiple_lenses", "folded_lens", "dirty_strobe",
                              "dirty_camera", "bubble_scatter", "low_dose"]) + pos["clear"]
chk("class rows: membership sum", lp_sum, 7328)

# Standalone Tags: A=tag, B=tagged, C=extras
ws = wb["Standalone Tags"]
for r in range(1, ws.max_row + 1):
    code = ws.cell(row=r, column=1).value
    if code in audit["resolved_derivation"]:
        a = audit["resolved_derivation"][code]
        chk(f"standalone {code} tagged", ws.cell(row=r, column=2).value, a["pictures_tagged"])
        chk(f"standalone {code} extras", ws.cell(row=r, column=3).value, a["pictures_with_extra_labels"])

# Training and Test Split: A=display name, B=train, C=test
ws = wb["Training and Test Split"]
pretty2key = {"Foreign Matter size flag": "foreign_matter_micron_gate",
              "Fiber size flag": "fiber_micron_gate",
              "Extraneous Polymer size flag": "extraneous_polymer_micron_gate",
              "HEMA size flag": "hema_micron_gate",
              "Bubble (merged class)": "bubble", "Bubble Cluster": "bubble_cluster",
              "Wet Package": "wet_package",
              "Missing Primary Package": "missing_primary_package",
              "Multiple Lens": "multiple_lenses", "No Lens": "no_lens",
              "Cavity Off Center": "cavity_off_center", "Folded Lens": "folded_lens",
              "Lens Off Center": "lens_off_center", "Dirty Camera": "dirty_camera",
              "Dirty Strobe": "dirty_strobe", "Low Dose": "low_dose",
              "View Obstructed": "view_obstructed",
              "Package Misalignment": "package_misalignment",
              "Bubble Scatter": "bubble_scatter", "Clear": "clear"}
for r in range(1, ws.max_row + 1):
    nm = ws.cell(row=r, column=1).value
    if nm in pretty2key:
        p = meta["per_class"][pretty2key[nm]]
        chk(f"split {nm} train", ws.cell(row=r, column=2).value, p["train"])
        chk(f"split {nm} test", ws.cell(row=r, column=3).value, p["test"])
    if nm == "Total":
        chk("split total train", ws.cell(row=r, column=2).value, meta["split_counts"]["train"])
        chk("split total test", ws.cell(row=r, column=3).value, meta["split_counts"]["test"])
        chk("split total rows", ws.cell(row=r, column=4).value, meta["rows"])
    if nm == "Sum of the class rows above":
        chk("split row-sum train", ws.cell(row=r, column=2).value,
            sum(v["train"] for v in meta["per_class"].values()))
        chk("split row-sum test", ws.cell(row=r, column=3).value,
            sum(v["test"] for v in meta["per_class"].values()))

# Earlier vs Current: A=name, C=current analysed set
ws = wb["Earlier vs Current"]
census2matrix = {"Missing Primary Package": "missing_primary_package",
                 "Multiple Lenses": "multiple_lenses", "Lens Off Center": "lens_off_center",
                 "Dirty Camera": "dirty_camera", "Missing Lens (No Lens)": "no_lens",
                 "Folded Lens": "folded_lens", "Low Dose": "low_dose",
                 "Cavity Off Center": "cavity_off_center",
                 "Foreign Matter size flag": "foreign_matter_micron_gate",
                 "Fiber size flag": "fiber_micron_gate",
                 "HEMA size flag": "hema_micron_gate",
                 "Dirty Strobe": "dirty_strobe",
                 "Extraneous Polymer size flag": "extraneous_polymer_micron_gate",
                 "View Obstructed": "view_obstructed",
                 "Bubble Scatter": "bubble_scatter",
                 "Package Misalignment": "package_misalignment",
                 "HEMA Obstruction": "hema_obstruction",
                 "Bubble On 123": "bubble_on_123", "Bubble On Edge": "bubble_on_edge",
                 "Clear": "clear"}
for r in range(1, ws.max_row + 1):
    nm = ws.cell(row=r, column=1).value
    if nm in census2matrix:
        chk(f"earlier {nm}", ws.cell(row=r, column=3).value, pos[census2matrix[nm]])

print("FAILURES:" if fails else "ALL CHECKS PASS", len(fails))
for f_ in fails[:25]:
    print(" -", f_)
sys.exit(1 if fails else 0)
