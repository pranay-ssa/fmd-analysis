"""Generate the spec for EDA_Draft2_rev3_<date>.xlsx from the rev3 artifacts.

REV3 (user rulings 2026-10-23):
- Micron gate is split-time only: no pictures dropped for missing gate tags.
  Gated families show "pictures carrying the class" with the gate-tagged subset beside them.
- Tag combinations appear as TWO tables: EXACT-only pairs (the picture's label set
  is precisely that pair) and INCLUSIVE pairs (the picture carries both, other
  labels allowed). Each header names its definition.
- Both splits (70/30 and 80/20) are shown side by side.

Inputs (read-only): run/multilabel_edge_20261023_rev3/{label_matrix.csv,label_matrix_meta.json},
run/split_20261023_v4/meta.json
Output: spec JSON on stdout -> xlsx_create.py
"""
import csv, json, collections

ROOT = "D:/fmd-analysis"
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

rows = [r for r in csv.DictReader(open(MAT, newline="", encoding="utf-8"))]
N = len(rows)
assert N == META["headline"]["eda_rows"], (N, META["headline"]["eda_rows"])
label_sets = {r["picture_md5"]: frozenset(c for c in LABEL_COLS if r[c] == "1") for r in rows}
pos = META["headline"]["per_column_positives"]

def pct(n, d=N):
    return round(n / d, 4)

sheets = []

# ---- Summary ----
sheets.append({
    "name": "Summary",
    "title": "Defect and image-quality analysis - Draft 2 annotation guide, revision 3",
    "rows": [
        ["Pictures in the analysed set", N,
         "Every picture carrying at least one label under the Draft 2 rules, plus Clear-folder pass pictures. No picture is dropped for lacking a micron-gate tag."],
        [],
        ["Labelled pictures", META["headline"]["row_status_counts"]["labeled"], ""],
        ["Clear pass pictures", META["headline"]["clear_rows"], "Clear-folder pictures with nothing to report; Clear never shares a picture with another label"],
        [],
        ["Main classes (pictures carrying the class)"],
    ] + [[NAME[c], pos[c]] for c in
         ["missing_primary_package", "multiple_lenses", "lens_off_center", "clear", "bubble",
          "bubble_cluster", "no_lens", "dirty_camera", "folded_lens", "low_dose"]] + [
        [],
        ["Revision 3 changes against the October 23 draft"],
        ["1", "Pictures whose only defect marks are untagged size-gated families are NO LONGER dropped; they return to the analysed set and to their tag columns."],
        ["2", "The four size-gated families show two numbers: pictures carrying the class, and the micron-gate-tagged subset that the split uses as positives."],
        ["3", "Tag combinations appear as two tables: exact-only pairs and inclusive pairs, each with its definition in the header."],
        ["4", "Both split ratios, 70/30 and 80/20, are provided."],
        [],
        ["Rows are not additive: a picture can carry several classes, so the class rows sum to more than the picture totals above."],
    ],
    "column_widths": {"A": 44, "B": 14},
})

# ---- LP tags ----
lp_codes = [("P1_MPP", "Missing Primary Package", "missing_primary_package"),
            ("P1_COC", "Cavity Off Center", "cavity_off_center"),
            ("F2_FOV/P2_FOV", "Field of View Obstructed", "view_obstructed"),
            ("P2_LOC", "Lens Off Center", "lens_off_center"),
            ("P1_NL", "No Lens", "no_lens"),
            ("P1_ML", "Multiple Lens", "multiple_lenses"),
            ("P1_FL", "Folded Lens", "folded_lens"),
            ("P2_DS", "Dirty Strobe", "dirty_strobe"),
            ("P2_DC", "Dirty Camera", "dirty_camera"),
            ("P2_BSC", "Bubble Scatter", "bubble_scatter"),
            ("P2_LD", "Low Dose", "low_dose")]
sheets.append({
    "name": "LP Tags",
    "title": "Lens-presentation tags: pictures carrying each tag in the analysed set",
    "freeze": "A2",
    "rows": [["Code", "Tag", "Pictures", "Share of analysed pictures"]] +
            [[code, nm, pos[col], pct(pos[col])] for code, nm, col in lp_codes] +
            [[], ["Class rows are not additive: a picture can carry several tags."]],
    "column_widths": {"A": 14, "B": 26, "C": 10, "D": 22},
})

# ---- Object classes with gated families ----
obj = [("P2_BB", "Bubble", "bubble"), ("P2_BC", "Bubble Cluster", "bubble_cluster"),
       ("P2_WP", "Wet Package", "wet_package"), ("P3_FM", "Foreign Matter", "foreign_matter_micron_gate"),
       ("P3_FIB", "Fiber", "fiber_micron_gate"), ("P3_EP", "Extraneous Polymer", "extraneous_polymer_micron_gate"),
       ("P3_HE", "HEMA", "hema_micron_gate")]
fam = META["headline"]["gated_families"]
sheets.append({
    "name": "Object Classes",
    "title": "Object classes: pictures carrying the class; gated families also show the micron-gate-tagged subset",
    "freeze": "A2",
    "rows": [["Code", "Class", "Pictures carrying the class", "Of which micron-gate tagged", "Note"]] +
            [[code, nm, pos[col],
              (fam[col]["of_which_micron_gate_tagged"] if col in fam else ""),
              ("Split positives = the gate-tagged subset (they exceed the size threshold and must be failed)" if col in fam else "")]
             for code, nm, col in obj] +
            [[], ["Bubble merges irregular and stretched bubbles per Draft 2. Bubble On 123 (13), Bubble On Edge (14) and HEMA Obstruction (86) stay separate legacy rows."]],
    "column_widths": {"A": 10, "B": 24, "C": 24, "D": 24, "E": 52},
})

# ---- Tag combinations: EXACT ----
pair_exact = collections.Counter()
pair_incl = collections.Counter()
for s in label_sets.values():
    ss = sorted(s)
    for i in range(len(ss)):
        for j in range(i + 1, len(ss)):
            a, b = ss[i], ss[j]
            pair_incl[(a, b)] += 1
            if len(s) == 2:
                pair_exact[(a, b)] += 1

def pair_sheet(kind, counter):
    body = [["Rank", "Tag pair", "Pictures"]] if kind == "exact" else \
           [["Rank", "Tag pair (both present, other labels allowed)", "Pictures"]]
    for k, ((a, b), v) in enumerate(counter.most_common(15), 1):
        body.append([k, f"{NAME[a]} + {NAME[b]}", v])
    return body

sheets.append({
    "name": "Tag Pairs Exact",
    "title": "Tag combinations - EXACT pairs only: the picture's label set is precisely that pair, nothing else",
    "freeze": "A2",
    "rows": pair_sheet("exact", pair_exact),
    "column_widths": {"A": 6, "B": 52, "C": 10},
})
sheets.append({
    "name": "Tag Pairs Inclusive",
    "title": "Tag combinations - INCLUSIVE pairs: the picture carries both tags; other labels in addition are allowed",
    "freeze": "A2",
    "rows": pair_sheet("incl", pair_incl) + [[],
        ["Read the two tables together: a pair can be rare exactly because most of its pictures carry a third label. Example: Multiple Lens + Lens Off Center."]],
    "column_widths": {"A": 6, "B": 52, "C": 10},
})

# ---- Splits ----
for key, label in [("70_30", "Split 70-30"), ("80_20", "Split 80-20")]:
    s = SPLIT["splits"][key]
    body = [["Class", "Training", "Test", "Total", "Expected train", "Expected test"]]
    for c in LABEL_COLS:
        p = s["per_class"][c]
        if p["train"] + p["test"]:
            body.append([NAME[c], p["train"], p["test"], p["train"] + p["test"], p["expect_train"], p["expect_test"]])
    sc = s["split_counts"]
    body += [[], ["Total", sc["train"], sc["test"], sc["train"] + sc["test"]],
             ["Split positives for the four gated families are the micron-gate-tagged pictures; every picture appears in exactly one side; no separate validation set."]]
    sheets.append({
        "name": label,
        "title": f"Train/test split {key.replace('_', '/')} - iterative stratification, seed 42, content groups",
        "freeze": "A2",
        "rows": body,
        "column_widths": {"A": 30, "B": 10, "C": 10, "D": 10, "E": 14, "F": 14},
    })

# ---- Definitions ----
sheets.append({
    "name": "Definitions",
    "title": "Definitions",
    "rows": [
        ["Term", "Meaning"],
        ["Analysed set", f"All {N} pictures carrying at least one label under the Draft 2 rules, plus Clear-folder pass pictures. No picture is excluded for lacking a micron-gate tag."],
        ["Micron gate", "A size flag: the defect exceeds the agreed size limit. An EDA concept: the gate-tagged subset is shown beside the class total. A split concept: gate-tagged pictures are the positives the model must fail."],
        ["Clear", "A picture with nothing to report; never shares a picture with another label."],
        ["Exact pair", "A picture whose complete label set is exactly that pair of labels, nothing else."],
        ["Inclusive pair", "A picture that carries both labels of the pair, regardless of what else it carries."],
        ["Legacy rows", "Bubble On 123, Bubble On Edge and HEMA Obstruction are kept for reference; they are not Draft 2 classes and do not stratify the split."],
    ],
    "column_widths": {"A": 18, "B": 110},
})

spec = {"workbook": {"default_header_style": True, "full_calc_on_load": True}, "sheets": sheets}
print(json.dumps(spec, indent=1))
