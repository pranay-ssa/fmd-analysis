"""Ticket 019/020: change table, legend, and workbook spec for the
multi-label Edge EDA. Reads the built label matrix and the frozen crosswalk,
never hand-types a figure. Emits spec.json (for xlsx_create.py) and stats.json
(for the report)."""
import csv, json, collections

ROOT = "D:/fmd-analysis"
EDA = f"{ROOT}/run/eda_full_20261015"
OUT = f"{ROOT}/run/multilabel_edge_20261021"

LABELS = [("foreign_matter_micron_gate", "P3_FM_MICRON_THRESHOLD", "gate"),
          ("fiber_micron_gate", "P3_FIB_MICRON_THRESHOLD", "gate"),
          ("extraneous_polymer_micron_gate", "P3_EP_MICRON_THRESHOLD", "gate"),
          ("hema_micron_gate", "P3_HE_MICRON_THRESHOLD", "gate"),
          ("bubble", "P2_BB (absorbs P2_BI, P2_BST)", "box"),
          ("bubble_cluster", "P2_BC", "box"),
          ("bubble_on_123", "(library name; no newer code)", "box"),
          ("bubble_on_edge", "(library name; no newer code)", "box"),
          ("wet_package", "P2_WP", "box"),
          ("bubble_scatter", "P2_BSC", "tag"),
          ("hema_obstruction", "P2_HMO (retired in Draft 2)", "tag"),
          ("missing_primary_package", "P1_MPP", "tag"),
          ("multiple_lenses", "P1_ML", "tag"),
          ("no_lens", "P1_NL", "tag"),
          ("cavity_off_center", "P1_COC", "tag"),
          ("folded_lens", "P1_FL", "tag"),
          ("lens_off_center", "P2_LOC (production alias F2_FOV is view_obstructed)", "tag"),
          ("dirty_camera", "P2_DC", "tag"),
          ("dirty_strobe", "P2_DS", "tag"),
          ("low_dose", "P2_LD", "tag"),
          ("view_obstructed", "P2_FOV / F2_FOV", "tag"),
          ("package_misalignment", "P1_PPM", "tag"),
          ("clear", "(computed, not annotated)", "computed")]

CHANGE_TABLE = [
    ["Missing Primary Package", "P1_MPP", "Missing Primary Package", "Code added in Draft 2", "In scope"],
    ["Multiple Lenses", "P1_ML", "Multiple Lens", "Renamed singular; fragment-size rule added", "In scope"],
    ["Missing Lens", "P1_NL", "No Lens", "Renamed; validity preconditions added", "In scope"],
    ["Cavity Off Center", "P1_COC", "Cavity Off Center", "Code added; cause test made explicit", "In scope"],
    ["Folded Lens", "P1_FL", "Folded Lens", "Code added; severity and Multiple-Lens co-occurrence rules", "In scope"],
    ["Lens Off Center", "P2_LOC", "Lens Off Center", "Code added; LOC-vs-Low-Dose rule now bidirectional", "In scope"],
    ["Dirty Camera", "P2_DC", "Dirty Camera", "Code added; one-tag-per-image rule; focal-plane distinction", "In scope"],
    ["Dirty Strobe", "P2_DS", "Dirty Strobe", "Code added; focal-plane cause stated", "In scope"],
    ["Low Dose", "P2_LD", "Low Dose Obstructing Region of Interest", "Code added; LOC-vs-LD rule bidirectional", "In scope; negatives flagged unreliable"],
    ["View Obstructed", "P2_FOV", "Field of View Obstructed", "Code added; quality exclusions; production files use anomalous F2_FOV (collision kept)", "In scope"],
    ["Package Misalignment", "P1_PPM", "Primary Package Misalignment", "Renamed; absorbs Multiple Primary Package and Package Off Center", "In scope (2 images)"],
    ["Bubble", "P2_BB", "Bubble", "Code added", "In scope"],
    ["Bubble Irregular", "P2_BB", "Bubble", "Merged into Bubble (Draft 2 consolidation)", "In scope, inside Bubble"],
    ["Stretched Bubble", "P2_BB", "Bubble", "Merged into Bubble (Draft 2 consolidation)", "In scope, inside Bubble"],
    ["Bubble Cluster", "P2_BC", "Bubble Cluster", "Stays a box class; grouping criteria expanded (4-5 px separations, favor smaller clusters)", "In scope"],
    ["Bubble on Edge", "(none)", "deprecated", "Draft 2 deprecates as a distinct label; location attributes dropped", "KEPT as own column; discrepancy noted in workbook"],
    ["Bubble on \"123\" Mark", "(none)", "deprecated", "Draft 2 deprecates as a distinct label; location attributes dropped", "KEPT as own column; discrepancy noted in workbook"],
    ["Bubble Scatter", "P2_BSC", "Bubble Scatter", "Explicitly a presentation tag, not an object; application thresholds added", "In scope (6 images)"],
    ["Wet Package", "P2_WP", "Wet Package", "Code added", "In scope"],
    ["HEMA Fragment", "P3_HE", "HEMA", "Renamed (Fragment dropped); ring fragments now included", "In scope via the HEMA gate class"],
    ["HEMA Obstruction", "(removed)", "no successor", "Draft 2 retires the tag; the intact-obstruction case is unassigned", "KEPT as legacy column (86 pictures); discrepancy noted"],
    ["Foreign Matter", "P3_FM", "Foreign Matter", "Reworded from catch-all-first to explicit default-last", "In scope via the FM gate class"],
    ["Fiber", "P3_FIB", "Fiber", "New tiebreak: uncertain cases default to Fiber", "In scope via the Fiber gate class and the 33-picture flip"],
    ["Extraneous Polymer", "P3_EP", "Extraneous Polymer", "Tiebreak and fragment rule added", "In scope via the EP gate class"],
    ["(new) micron gates", "P3_FM/FIB/EP/HE_MICRON_THRESHOLD", "four * micron gate tags", "Production-only size-gate tags; in this experiment the gate IS the class", "4 gate columns"],
    ["Clear", "(none)", "(none)", "Not an annotation; computed as no defect-class label", "Computed column"],
    ["Edge Bottle-Capped", "P1_EBC", "Edge Bottle-Capped", "Draft 2 new class; zero shapes in any annotation file", "SKIPPED (no data)"],
    ["Torn Lens", "P1_TL", "Torn Lens", "Draft 2 new class; zero shapes in any annotation file", "SKIPPED (no data)"],
    ["Lens Rupture", "P1_LR", "Lens Rupture", "Draft 2 new class; zero shapes in any annotation file", "SKIPPED (no data)"],
    ["Surface Groove", "P1_SG", "Surface Groove", "Draft 2 new class; zero shapes in any annotation file", "SKIPPED (no data)"],
]

# ---- stats from the matrix ----
with open(f"{OUT}/label_matrix.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
cols = [c for c, _, _ in LABELS]
pos = {c: sum(int(r[c]) for r in rows) for c in cols}
N = len(rows)
card = collections.Counter(sum(int(r[c]) for c in cols) for r in rows)
DEF = cols[:11]
LP = cols[11:22]
import itertools
co = collections.Counter()
for r in rows:
    on = [c for c in cols if int(r[c])]
    for a, b in itertools.combinations(on, 2):
        co[tuple(sorted((a, b)))] += 1
subsets = []
for a, b in itertools.permutations(cols, 2):
    if pos[a] and not any(int(r[a]) and not int(r[b]) for r in rows):
        rev = sum(1 for r in rows if int(r[b]) and not int(r[a]))
        subsets.append([a, b, pos[a], pos[b], rev])
rs = collections.Counter(r["row_status"] for r in rows)
stats_str = "labeled " + str(rs.get("labeled", 0)) + " / clear_folder " + str(rs.get("clear_folder", 0)) + " / unlabeled " + str(rs.get("unlabeled", 0))

stats = {
    "universe": 10614, "eda_rows": N,
    "split_eligible": sum(1 for r in rows if int(r["split_eligible"])),
    "flip_rows": sum(1 for r in rows if int(r["flip_exception"])),
    "clear": pos["clear"],
    "clear_unreliable": sum(1 for r in rows if r["clear"] == "1" and r["negatives_reliable"] == "0"),
    "clear_folder": sum(1 for r in rows if r["row_status"] == "clear_folder"),
    "row_status_str": stats_str,
    "per_column": pos,
    "cardinality": dict(sorted(card.items())),
    "distinct_vectors": len({tuple(r[c] for c in cols) for r in rows}),
    "defect_rows": sum(1 for r in rows if any(int(r[c]) for c in DEF)),
    "multi_defect_rows": sum(1 for r in rows if sum(int(r[c]) for c in DEF) >= 2),
    "lp_rows": sum(1 for r in rows if any(int(r[c]) for c in LP)),
    "top_pairs": [[a, b, n] for (a, b), n in co.most_common(20)],
    "subsets": subsets,
}
with open(f"{OUT}/eda_stats.json", "w", encoding="utf-8") as f:
    json.dump(stats, f, indent=2)

# ---- workbook spec ----
legend_rows = [["Column in matrix", "Draft 2 code", "Shape kind", "Positives"]] + [
    [c, code, kind, pos[c]] for c, code, kind in LABELS]
prev_rows = [["Column", "Positives", "Negatives", "Prevalence"]] + [
    [c, pos[c], N - pos[c], round(pos[c] / N, 4)] for c in cols]
card_rows = [["Labels per image", "Images"]] + [[k, v] for k, v in sorted(card.items())]
pair_rows = [["Class A", "Class B", "Images with both"]] + stats["top_pairs"]
sub_rows = [["Column A (never appears without B)", "Column B", "A positives", "B positives", "B without A (reverse count)"]] + subsets
read_rows = [["Reading", "Pictures"],
             ["Universe (distinct pictures, three libraries)", 10614],
             ["Dropped: only-plain FM/Fiber/EP/HEMA, flip not saving them", -153],
             ["EDA matrix rows", N],
             ["Split-ineligible: gate-less plain carriers still in matrix (75 mixed + 31 flipped)", -106],
             ["Split universe", stats["split_eligible"]],
             ["Clear folder rule: pictures in the Clear folders", stats["clear_folder"]],
             ["Defect-labeled folder pictures (winning file 167, rescued from older files 84, overlap most)", "-"],
             ["Clear class after the folder rule (all reliable by folder membership)", stats["clear"]],
             ["Dropped: unannotated (1,907 name-listed empty + 1,769 never listed)", -3676],
             ["Row status: labeled / clear_folder", stats["row_status_str"]],
             ["Flip pictures kept as Fiber in EDA (31) / with gate (2)", 31]]
disc_rows = [["#", "Discrepancy", "Handling"],
    [1, "Draft 2 deprecates Bubble On 123 and Bubble On Edge; this experiment keeps them as own classes (13 + 14 pictures, library-only)", "Kept; flagged; fold-in would move 27 pictures into Bubble"],
    [2, "Draft 2 retires HEMA Obstruction with no successor tag", "Kept as legacy column (86 legacy tags only; production P3_HE boxes belong to the HEMA gate column)"],
    [3, "The client's 33-image EP/Fiber ruling equals the Fiber-to-EP flip set exactly; the EP gate set is also 33 but overlaps it by only 2 pictures", "Flip applied from the verified md5 list; coincidence documented, never used"],
    [4, "31 of the 33 flipped pictures carry no gate, so the split reading excludes them; the EDA reading keeps them as Fiber", "Two readings, one artifact; split_eligible column"],
    [5, "Clear is a folder-derived class (winning path in a Clear folder), not a computed absence; older-file defect labels rescue folder pictures into defect classes", "Adopted 2026-10-21; Clear = 2,166, all reliable by folder membership"],
    [6, "P3_HE means HEMA Fragment in Sep-22 and boxes in production (collision); F2_FOV production alias for P2_FOV", "Collisions kept unmerged per the frozen crosswalk; client questions remain out"],
    [7, "Low Dose task is only partially annotated, so no-tag is not no-defect there", "negatives_reliable flag per picture; trainer switch"],
    [8, "3,676 pictures carry no label at all: 1,907 name-listed empty by the Sep-22 export, 1,769 never listed in any annotation file", "RESOLVED 2026-10-21: 0 tags = no tags, dropped from the experiment; VM hash sweep verified the 12,079 library bitmaps byte-identical (10,614 distinct)"]]
spec = {"full_calc_on_load": False, "sheets": [
    {"name": "Legend", "rows": legend_rows, "column_widths": {"A": 34, "B": 46, "C": 14, "D": 12}, "freeze_panes": "A2"},
    {"name": "Change table", "rows": [["Previous name", "Draft 2 code", "Draft 2 name", "What changed", "Status in this experiment"]] + CHANGE_TABLE,
     "column_widths": {"A": 24, "B": 30, "C": 34, "D": 62, "E": 42}, "freeze_panes": "A2"},
    {"name": "Column prevalence", "rows": prev_rows, "column_widths": {"A": 34, "B": 12, "C": 12, "D": 12}, "freeze_panes": "A2"},
    {"name": "Distribution", "rows": card_rows, "column_widths": {"A": 18, "B": 12}},
    {"name": "Co-occurrence", "rows": pair_rows, "column_widths": {"A": 32, "B": 32, "C": 16}, "freeze_panes": "A2"},
    {"name": "Subset checks", "rows": sub_rows, "column_widths": {"A": 34, "B": 34, "C": 12, "D": 12, "E": 26}, "freeze_panes": "A2"},
    {"name": "Readings", "rows": read_rows, "column_widths": {"A": 72, "B": 12}},
    {"name": "Discrepancy notes", "rows": disc_rows, "column_widths": {"A": 5, "B": 72, "C": 62}},
]}
with open(f"{OUT}/workbook_spec.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)
print("wrote spec + stats;", N, "rows,", len(cols), "columns,", len(subsets), "subset pairs")
