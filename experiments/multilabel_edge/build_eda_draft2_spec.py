"""Generate the spec for EDA_Draft2_20261023.xlsx (9 sheets) from verified artifacts.

Inputs (all read-only, all previously verified):
  run/draft2_eda_20261023/lp_eda.json          LP counts, co-occurrence, cardinality
  run/draft2_eda_20261023/ooi_eda.json         OOI box class stats
  run/multilabel_edge_20261023/standalone_audit.json   ticket 023 result
  run/multilabel_edge_20261023/label_matrix.csv        rev2 matrix (Option A)
  run/split_20261023_v3/meta.json              split v3 recipe + per-class counts
Output: EDA_Draft2_20261023_spec.json (feed to xlsx_create.py)
"""
import json, csv, collections

ROOT = "D:/fmd-analysis"
lp = json.load(open(f"{ROOT}/run/draft2_eda_20261023/lp_eda.json"))
ooi = json.load(open(f"{ROOT}/run/draft2_eda_20261023/ooi_eda.json"))
audit = json.load(open(f"{ROOT}/run/multilabel_edge_20261023/standalone_audit.json"))
meta = json.load(open(f"{ROOT}/run/split_20261023_v3/meta.json"))

# rev2 matrix column counts (verify against build output while assembling)
rows = list(csv.DictReader(open(f"{ROOT}/run/multilabel_edge_20261023/label_matrix.csv", newline="", encoding="utf-8")))
LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "bubble_on_123", "bubble_on_edge",
              "wet_package", "bubble_scatter", "hema_obstruction",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "clear"]
pos = {c: sum(1 for r in rows if r[c] == "1") for c in LABEL_COLS}
assert pos["clear"] == 2156, pos["clear"]
assert len(rows) == 6785, len(rows)

def pct(n, d=6785):
    return {"value": round(n / d, 4), "type": "number", "number_format": "0.0%"}

sheets = []

# ---- 1 Overview ----
sheets.append({
    "name": "Overview",
    "column_widths": {"A": 46, "B": 26},
    "rows": [
        ["EDA Draft 2 - consolidated analysis workbook", None],
        ["Built", "2026-10-23"],
        [None, None],
        ["Populations", None],
        ["Full-coverage EDA census (all sources)", "10,614 distinct picture contents"],
        ["Label matrix (frame rules, rev2)", "6,785 rows"],
        ["Split universe v3 (Draft 2 codes + Clear only)", "6,574 rows"],
        ["Split v3", "4,568 train / 2,006 test (70/30, seed 42)"],
        [None, None],
        ["Headline counts (label matrix rev2)", None],
        ["Clear (exclusive namespace)", "2,156"],
        ["Largest LP class: Multiple Lens P1_ML", "1,433"],
        ["Largest OOI class: Bubble P2_BB", "10,070 box instances / 746 pictures"],
        ["Standalone-tag violations (ticket 023)", "0"],
        [None, None],
        ["Active artifacts", None],
        ["Label matrix", "run/multilabel_edge_20261023/label_matrix.csv"],
        ["Split", "run/split_20261023_v3/split.csv + meta.json"],
        ["EDA numbers", "run/draft2_eda_20261023/*.json"],
        ["Docs", "docs/reference/draft2_eda_lp_20261023.md, draft2_eda_ooi_20261023.md, guide_confusion_table_20261023.md"],
        [None, None],
        ["Superseded (kept on disk)", "matrix 20261021, split v1 + v2, interim 2-sheet workbook"],
    ]})

# ---- 2 LP Tags ----
lp_rows = [["Code", "Name (Draft 2)", "Pictures (matrix)", "Share of 6,785", "In split v3 universe", "Status / note"]]
v3u = {"P1_MPP": 1426, "P1_PPM": 2, "P1_COC": 184, "P2_FOV": 24, "P2_LOC": 922, "P1_NL": 322,
       "P1_ML": 1402, "P1_FL": 226, "P2_DS": 41, "P2_DC": 298, "P2_BSC": 6, "P2_LD": 204}
status = {"P1_MPP": "live, standalone (0 co-tags)", "P1_PPM": "live, standalone; rarest",
          "P1_COC": "live, standalone", "P2_FOV": "live, standalone; F2_FOV code question with lead",
          "P2_LOC": "live", "P1_NL": "live", "P1_ML": "live, largest LP class",
          "P1_FL": "live, co-tag rule with ML", "P1_EBC": "no annotated pictures yet",
          "P1_TL": "no annotated pictures yet", "P1_LR": "no annotated pictures yet",
          "P2_DS": "live", "P2_DC": "live", "P2_BSC": "live, rare", "P2_LD": "live"}
code2col = {"P1_MPP": "missing_primary_package", "P1_PPM": "package_misalignment",
            "P1_COC": "cavity_off_center", "P2_FOV": "view_obstructed",
            "P2_LOC": "lens_off_center", "P1_NL": "no_lens", "P1_ML": "multiple_lenses",
            "P1_FL": "folded_lens", "P2_DS": "dirty_strobe", "P2_DC": "dirty_camera",
            "P2_BSC": "bubble_scatter", "P2_LD": "low_dose"}
lp_data_rows = []
for rec in lp["lp_counts"]:
    code, col, n = rec["code"], rec["column"], rec["pictures"]
    lp_data_rows.append([code, rec["name"], n, pct(n),
                         v3u.get(code, 0) if col != "(none)" else 0, status[code]])
# find pct cell positions later; append legacy + clear
lp_data_rows.append([None, None, None, None, None, None])
lp_data_rows.append(["(legacy)", "HEMA Obstruction P2_HMO", pos["hema_obstruction"], pct(pos["hema_obstruction"]),
                     0, "excluded as a split class (user decision 2026-10-23)"])
lp_data_rows.append(["(clear)", "Clear", pos["clear"], pct(pos["clear"]), 2156,
                     "exclusive namespace (Option A): never carries another label"])
sheets.append({
    "name": "LP Tags",
    "freeze_panes": "A2",
    "column_widths": {"A": 10, "B": 34, "C": 16, "D": 14, "E": 20, "F": 56},
    "rows": lp_rows + lp_data_rows,
    "cells": {f"D{i}": {"value": lp_data_rows[i-1][2], "type": "number"} for i in range(2, len(lp_rows) + len(lp_data_rows) + 1)
              if isinstance(lp_data_rows[i-2][2], int)} if False else {},
})

# fix pct cells for LP sheet (column D shares)
lp_sheet = sheets[-1]
for i, row in enumerate(lp_data_rows, start=2):
    if isinstance(row[3], dict):
        lp_sheet["cells"][f"D{i}"] = row[3]
        row[3] = row[3]["value"]

# ---- 3 LP Co-occurrence ----
co_rows = [["Pair", "Pictures", "Note"]]
notes = {"lens_off_center+multiple_lenses": "largest overlap",
         "multiple_lenses+folded_lens": "guide co-tag rule (apply both)",
         "lens_off_center+low_dose": "the guide's confused pair",
         "dirty_camera+low_dose": ""}
for pair, n in sorted(lp["co"].items(), key=lambda kv: -kv[1]):
    a, b = pair.split("+")
    co_rows.append([f"{a} + {b}", n, notes.get(pair, "")])
co_rows.append([None, None, None])
co_rows.append(["LP tags on one picture", "Pictures", None])
for k, v in lp["card"].items():
    co_rows.append([f"{k} LP tag(s)", v, None])
co_rows.append(["Pictures with >= 1 LP tag", lp["lp_any"], "of 6,785"])
sheets.append({
    "name": "LP Co-occurrence",
    "freeze_panes": "A2",
    "column_widths": {"A": 44, "B": 12, "C": 44},
    "rows": co_rows})

# ---- 4 OOI Boxes ----
order = ["Bubble", "Bubble Cluster", "Wet Package", "Fiber",
         "Extraneous Polymer", "HEMA (Draft 2: one class)", "Foreign Matter",
         "Bubble Irregular (folds into Bubble)", "Stretched Bubble (folds into Bubble)",
         "Bubble On 123 (library-only)", "Bubble On Edge (library-only)"]
codes = {"Bubble": "P2_BB", "Bubble Cluster": "P2_BC", "Wet Package": "P2_WP",
         "Surface Groove": "P1_SG", "Fiber": "P3_FIB", "Extraneous Polymer": "P3_EP",
         "HEMA (Draft 2: one class)": "P3_HE", "Foreign Matter": "P3_FM"}
ooi_rows = [["Code", "Class", "Pictures (shape line)", "Pictures (matrix)", "Box instances",
             "Boxes/pic median", "Boxes/pic max", "w median px", "h median px", "w p95 px", "h p95 px", "Note"]]
onotes = {
 "Bubble": "strict P2_BB code. Merged Draft-2 Bubble (with BI+BST) = 750 pictures / 10,205 boxes; matrix column 862 (incl. 112 rescues)",
 "Bubble Irregular (folds into Bubble)": "CONTAINED in the 746: every BI picture also carries P2_BB",
 "Bubble On 123 (library-only)": "excluded as a split class (user decision 2026-10-23)",
 "Bubble On Edge (library-only)": "excluded as a split class",
 "HEMA (Draft 2: one class)": "held as Sep-22 fragment boxes + production boxes; gate column marks the class",
 "Extraneous Polymer": "gate column 33 pictures; most thinned by the matrix drop rule",
}
for name in order:
    d = ooi.get(name)
    if d is None:
        ooi_rows.append([codes.get(name, "(legacy)"), name, 0, 0, 0, None, None,
                         None, None, None, None, "no annotated boxes yet (P1_SG has no data)"])
        continue
    ooi_rows.append([codes.get(name, "(legacy)"), name, d["pictures"], d["pictures_in_matrix"],
                     d["box_instances"], d.get("boxes_per_picture_median"), d.get("boxes_per_picture_max"),
                     d["w_px_median"], d["h_px_median"], d["w_px_p95"], d["h_px_p95"],
                     onotes.get(name, "")])
ooi_rows.append([None, None, None, None, None, None, None, None, None, None, None, None])
ooi_rows.append(["", "TOTAL", 1130, 977, 12783, None, None, None, None, None, None,
                 "12,783 boxes; 79 percent Bubble; 1,130 shape-line pictures carry >= 1 box"])
sheets.append({
    "name": "OOI Boxes",
    "freeze_panes": "C2",
    "column_widths": {"A": 10, "B": 34, "C": 12, "D": 12, "E": 12, "F": 12, "G": 12,
                      "H": 12, "I": 12, "J": 12, "K": 12, "L": 60},
    "rows": ooi_rows})

# ---- 5 Standalone Audit ----
sa_rows = [["Standalone tag", "Pictures tagged", "With extra labels", "With gate tag only", "Verdict"]]
targets = [("P1_MPP", "P1_MPP"), ("P1_PPM", "P1_PPM"), ("P1_COC", "P1_COC"),
           ("P2_FOV", "P2_FOV"), ("F2_FOV", "F2_FOV")]
for code, key in targets:
    a = audit["resolved_derivation"][key]
    b = audit["raw_derivation"][key]
    sa_rows.append([code, a["pictures_tagged"], a["pictures_with_extra_labels"],
                    a["pictures_with_gate_tag_only"],
                    "CLEAN - guide rule holds (both derivations agree)" if a["pictures_with_extra_labels"] == 0 and b["pictures_with_extra_labels"] == 0 else "VIOLATIONS"])
sa_rows.append([None, None, None, None, None])
sa_rows.append(["Guide rule", "Draft 2 sections 4.1-4.4: these four tags are standalone; no additional tags or labels.", None, None, None])
sa_rows.append [""] if False else None
sa_rows = [r for r in sa_rows if r is not None]
sa_rows.append(["Derivations", "resolved line (winning source) + raw parse of all 8 newer files; 0 unmapped label-bearing names", None, None, None])
sa_rows.append(["Artifacts", "run/multilabel_edge_20261023/standalone_audit.json + empty violation lists", None, None, None])
sheets.append({
    "name": "Standalone Audit",
    "freeze_panes": "A2",
    "column_widths": {"A": 34, "B": 16, "C": 16, "D": 18, "E": 52},
    "rows": sa_rows})

# ---- 6 Guide Confusion Rules ----
cr_rows = [["#", "Class (n1)", "Confused with (n2)", "Circumstance and reason", "Direction", "Guide section", "Co-occur"],
 [1, "Cavity Off Center P1_COC (184)", "Package Misalignment P1_PPM (2)", "Root cause boundary: trigger-timing framing shift vs package not seated. Both standalone.", "two-way", "4.3", 0],
 [2, "Lens Off Center P2_LOC (953)", "Low Dose P2_LD (215)", "Apparent displacement from low solution = LD; true lens shift in a filled bowl = LOC.", "two-way", "4.5, 4.15", 17],
 [3, "Wet Package P2_WP (146)", "Bubble P2_BB (862)", "Liquid, not trapped air: gradual intensity gradient, irregular shape, near package perimeter.", "one-way (WP looks like Bubble)", "5.2", 117],
 [4, "Extraneous Polymer P3_EP", "Fiber P3_FIB", "Mixed strand-plus-clump objects default to FIBER; EP only when confident.", "one-way default to Fiber", "5.4B", "n/a"],
 [5, "Surface Groove P1_SG (0)", "Torn Lens P1_TL (0)", "Groove opening into a tear/flap becomes TL; shallow surface defect stays SG.", "two-way", "5.3, 4.10", "no data"],
 [6, "Surface Groove P1_SG (0)", "Extraneous Polymer P3_EP", "Raised/additional translucent material is EP; a groove is missing material.", "one-way (SG looks like EP)", "5.3", "no data"],
 [7, "Torn Lens P1_TL (0)", "Lens Rupture P1_LR (0)", "TL keeps one connected structure; separation or near-complete division is LR.", "two-way", "4.10, 4.11", "no data"],
 [8, "Edge Bottle-Capped P1_EBC (0)", "Torn Lens, Lens Rupture", "EBC keeps a continuous edge; tear into body is TL; separated material is LR.", "one-way (boundary outward)", "4.9", "no data"],
 [9, "Bubble Scatter P2_BSC (6)", "Bubble (862) / Cluster (430)", "Tag for a diffuse field vs boxes for discrete bubbles; isolated bubbles never scatter.", "two-way (tag vs box)", "4.14, 5.1B", "0"],
 [10, "Dirty Strobe P2_DS (43)", "Dirty Camera P2_DC (326)", "Same cause, different focal plane: diffuse edge-creeping vs sharp defined marks.", "two-way", "4.12, 4.13", "n/a"],
 [11, "No Lens P1_NL (323)", "any lens-state class", "NL requires valid package AND confident lens absence; otherwise the specific class.", "one-way (last resort)", "4.6", "0"],
 [12, "Multiple Lens P1_ML (1,433)", "Folded Lens P1_FL (237)", "Co-tag rule, not a confusion: folded lens in multi-lens image gets BOTH; rupture sections force ML.", "co-occurrence rule", "4.7, 4.8, 4.11", 236],
 [13, "Bubble P2_BB", "Foreign Matter family", "Default: anything not confidently a Bubble is annotated as the most appropriate FM class.", "one-way default to FM", "1.3", "n/a"],
 [14, "any uncertain defect", "most appropriate class", "Annotate uncertain defects with the most appropriate class; consistency over physical origin.", "blanket rule", "1.3", "n/a"],
 [None, None, None, None, None, None, None],
 ["Non-target look-alikes (do not annotate; false-positive sources)", None, None, None, None, None, None],
 ["Primary Package Marks (fiber-like, recur in same position per job)", "resembles Fiber, Foreign Matter", None, None, None, "3.1", None],
 ["Crater-Like Bubble Artifacts (rings, depressions, shockwave patterns)", "resembles Wet Package, Fiber, EP, FM", None, None, None, "3.2", None]]
sheets.append({
    "name": "Guide Confusion Rules",
    "freeze_panes": "A2",
    "column_widths": {"A": 5, "B": 30, "C": 28, "D": 66, "E": 24, "F": 12, "G": 10},
    "rows": cr_rows})

# ---- 7 Full EDA vs Draft 2 ----
cmp_rows = [["Tag", "Full EDA: images", "Draft-2 matrix (6,785)", "Split v3 universe (6,574)", "Why the columns differ"],
 ["Missing Primary Package", 1426, 1426, 1426, "identical at every stage"],
 ["Multiple Lenses", 1439, 1433, 1402, "-6 only-plain drops; -31 ineligible"],
 ["Lens Off Center", 957, 953, 922, "-4 only-plain; -31 ineligible"],
 ["Dirty Camera", 329, 326, 298, "-3 only-plain; -28 ineligible"],
 ["Missing Lens P1_NL", 325, 323, 322, "-2 only-plain; -1 ineligible"],
 ["Folded Lens", 237, 237, 226, "-11 ineligible"],
 ["Low Dose", 215, 215, 204, "-11 ineligible"],
 ["Cavity Off Center", 184, 184, 184, "identical"],
 ["Foreign Matter gate", 171, 171, 171, "identical"],
 ["Fiber gate", 136, 168, 137, "matrix 168 = 137 true gate-tag pictures + 31 Fiber/EP flip rows; the 136-vs-137 gap is the parked item"],
 ["HEMA gate", 94, 94, 94, "identical"],
 ["Dirty Strobe", 43, 43, 41, "-2 ineligible"],
 ["Extraneous Polymer gate", 33, 33, 33, "identical"],
 ["View Obstructed", 24, 24, 24, "identical"],
 ["Bubble Scatter", 6, 6, 6, "identical"],
 ["Package Misalignment", 2, 2, 2, "identical"],
 ["HEMA Obstruction", 86, 86, 0, "excluded as a class (user decision 2026-10-23)"],
 ["Bubble On 123", "(box tier)", 13, 0, "excluded as a class"],
 ["Bubble On Edge", "(box tier)", 14, 0, "excluded as a class"],
 ["Clear", "(new)", 2156, 2156, "exclusive namespace (Option A)"],
 [None, None, None, None, None],
 ["The three delta mechanisms", None, None, None, None],
 ["1. Full EDA vs matrix", "the frame's gate rule drops gate-less plain carriers even when they carry an LP tag: 10 pictures (ML 6, LOC 4, DC 3, NL 2)", None, None, None],
 ["2. Fiber gate", "matrix column 168 = 137 true gate-tag pictures + 31 rows of the verified Fiber/EP flip (decision 12). The census 136 vs 137 eligible gap is the parked 137-vs-136 item (1 picture, unresolved)", None, None, None],
 ["3. Matrix vs split universe (-211)", "106 labeled-but-ineligible gate-less plain carriers + 105 rows carrying only excluded-class labels", None, None, None]]
sheets.append({
    "name": "Full EDA vs Draft 2",
    "freeze_panes": "A2",
    "column_widths": {"A": 26, "B": 16, "C": 20, "D": 22, "E": 72},
    "rows": cmp_rows})

# ---- 8 Split v3 ----
sp_rows = [["Class", "Train", "Test", "Total", "Expect train (70%)", "Expect test (30%)", "Note"]]
rare = {"package_misalignment", "bubble_scatter", "view_obstructed", "extraneous_polymer_micron_gate"}
for c in meta and ["foreign_matter_micron_gate", "fiber_micron_gate", "extraneous_polymer_micron_gate",
                   "hema_micron_gate", "bubble", "bubble_cluster", "wet_package",
                   "missing_primary_package", "multiple_lenses", "no_lens", "cavity_off_center",
                   "folded_lens", "lens_off_center", "dirty_camera", "dirty_strobe", "low_dose",
                   "view_obstructed", "package_misalignment", "bubble_scatter", "clear"]:
    p = meta["per_class"][c]
    note = "RARE: one-digit test confidence" if c in rare else ""
    sp_rows.append([c, p["train"], p["test"], p["train"] + p["test"],
                    p["expect_train"], p["expect_test"], note])
sp_rows.append([None, None, None, None, None, None, None])
sp_rows.append(["TOTAL", meta["split_counts"]["train"], meta["split_counts"]["test"],
                meta["rows"], round(0.7 * meta["rows"], 1), round(0.3 * meta["rows"], 1),
                "zero group crossings"])
sp_rows.append([None, None, None, None, None, None, None])
sp_rows.append(["Recipe", "iterative stratification (Sechidis 2011), two-way 70/30, seed 42, content-md5 groups, no validation split", None, None, None, None, None])
sp_rows.append(["Label space", "Draft 2 guide codes + Clear only (user decision 2026-10-23). On 123, On Edge, HEMA Obstruction excluded; gate tags mark the gated classes", None, None, None, None, None])
sp_rows.append(["Verification", "hand-typed expected values, independent second derivation, byte-identical rerun, corrupted-input proof - all pass (verify_split_v3.py)", None, None, None, None, None])
sp_rows.append(["Artifacts", "run/split_20261023_v3/split.csv + meta.json", None, None, None, None, None])
sheets.append({
    "name": "Split v3",
    "freeze_panes": "A2",
    "column_widths": {"A": 34, "B": 10, "C": 10, "D": 10, "E": 18, "F": 18, "G": 44},
    "rows": sp_rows})

# ---- 9 Decisions ----
dc_rows = [["Date", "Decision", "Effect"],
 ["2026-10-21", "Frame frozen (15 items): gate IS the class; folder-rule Clear; 3,676 unannotated dropped; BI and BST fold into Bubble; 70/30 split, seed 42, md5 groups", "the label matrix"],
 ["2026-10-22", "Meeting: Draft 2 = 15 LP tags + 8 OOI classes; MPP/PPM/COC/FOV standalone; Clear as third namespace; dropped classes stay in EDA but separate", "tickets 023-026"],
 ["2026-10-23", "Standalone audit: zero violations, rule holds", "no co-tag policy needed"],
 ["2026-10-23", "Split label space = Draft 2 codes + Clear ONLY; On 123, On Edge, HEMA Obstruction excluded; gate tags mark gated classes", "universe 6,679 -> 6,574; split v2"],
 ["2026-10-23", "Option A: Clear must be clear, carries no other label", "matrix rev2, Clear 2,166 -> 2,156; split v3"],
 ["2026-10-23", "Merged Bubble measured: all 108 BI pictures carry P2_BB (containment); merged = 750 shape line / 862 matrix", "Bubble row stated exactly"],
 ["open", "P2_FOV vs F2_FOV code, P2_BST code, 300 micron gate cut, Low Dose task completeness", "with the lead"]]
sheets.append({
    "name": "Decisions",
    "freeze_panes": "A2",
    "column_widths": {"A": 12, "B": 90, "C": 46},
    "rows": dc_rows})

spec = {"workbook": {"default_header_style": True}, "sheets": sheets}
out = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261023_spec.json"
json.dump(spec, open(out, "w", encoding="utf-8"), indent=1)
print("spec written:", out)
