"""Verification gate for the 70/30 split (ticket 022, split portion).

Three legs, per the repo's triple-check rule:
  1. Hand-typed expected values (typed from the 2026-10-23 build readout,
     NOT computed here): headline row counts and per-class split counts.
  2. Independent second derivation: per-class train/test counts recomputed
     from label_matrix.csv + split.csv with set logic written separately
     from the builder, then diffed against meta.json.
  3. Coverage: every split-eligible row exactly once, no ineligible row,
     no group crossing (trivial by singleton groups, still asserted),
     train+test sums per class equal the eligible positives.
"""
import csv, json, collections, sys

ROOT = "D:/fmd-analysis"
MAT = f"{ROOT}/run/multilabel_edge_20261021/label_matrix.csv"
SPL = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/run/split_20261023/split.csv"
META = sys.argv[2] if len(sys.argv) > 2 else f"{ROOT}/run/split_20261023/meta.json"
LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "bubble_on_123", "bubble_on_edge",
              "wet_package", "bubble_scatter", "hema_obstruction",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "clear"]

fails = []

# ---- leg 1: hand-typed expected values (from the 2026-10-23 readout) ----
EXPECTED_TOTALS = {"rows": 6679, "train": 4645, "test": 2034,
                   "group_crossings": 0}
EXPECTED_CLASS = {  # class: (train, test)
    "foreign_matter_micron_gate": (123, 48),
    "fiber_micron_gate": (89, 48),
    "extraneous_polymer_micron_gate": (25, 8),
    "hema_micron_gate": (66, 28),
    "bubble": (552, 237),
    "bubble_cluster": (266, 114),
    "bubble_on_123": (9, 4),
    "bubble_on_edge": (10, 4),
    "wet_package": (88, 38),
    "bubble_scatter": (4, 2),
    "hema_obstruction": (60, 26),
    "missing_primary_package": (998, 428),
    "multiple_lenses": (981, 421),
    "no_lens": (225, 97),
    "cavity_off_center": (129, 55),
    "folded_lens": (167, 59),
    "lens_off_center": (645, 277),
    "dirty_camera": (213, 85),
    "dirty_strobe": (29, 12),
    "low_dose": (143, 61),
    "view_obstructed": (17, 7),
    "package_misalignment": (1, 1),
    "clear": (1516, 650),
}
meta = json.load(open(META, encoding="utf-8"))
if meta["rows"] != EXPECTED_TOTALS["rows"]:
    fails.append(f"rows {meta['rows']} != {EXPECTED_TOTALS['rows']}")
if meta["split_counts"].get("train") != EXPECTED_TOTALS["train"]:
    fails.append(f"train {meta['split_counts'].get('train')} != {EXPECTED_TOTALS['train']}")
if meta["split_counts"].get("test") != EXPECTED_TOTALS["test"]:
    fails.append(f"test {meta['split_counts'].get('test')} != {EXPECTED_TOTALS['test']}")
if meta["group_crossings"] != EXPECTED_TOTALS["group_crossings"]:
    fails.append("group_crossings nonzero")
for c, (tr, te) in EXPECTED_CLASS.items():
    got = meta["per_class"][c]
    if (got["train"], got["test"]) != (tr, te):
        fails.append(f"{c} meta ({got['train']},{got['test']}) != hand-typed ({tr},{te})")

# ---- leg 2: independent second derivation (set logic, separate code path) ----
matrix = {r["picture_md5"]: r
          for r in csv.DictReader(open(MAT, newline="", encoding="utf-8"))
          if r["split_eligible"] == "1"}
split = {}
for r in csv.DictReader(open(SPL, newline="", encoding="utf-8")):
    split[r["picture_md5"]] = r["split"]
if set(split) != set(matrix):
    fails.append("split.csv key set != eligible matrix key set")
train_ids = {m for m, s in split.items() if s == "train"}
test_ids = {m for m, s in split.items() if s == "test"}
if train_ids & test_ids:
    fails.append("train/test overlap")
for c in LABEL_COLS:
    tr = sum(1 for m in train_ids if matrix[m][c] == "1")
    te = sum(1 for m in test_ids if matrix[m][c] == "1")
    if (tr, te) != EXPECTED_CLASS[c]:
        fails.append(f"{c} derived ({tr},{te}) != hand-typed {EXPECTED_CLASS[c]}")
    if tr + te != sum(1 for m in matrix if matrix[m][c] == "1"):
        fails.append(f"{c} split positives != eligible positives")

# ---- leg 3: coverage ----
if len(split) != len(matrix):
    fails.append("split row count != eligible rows")
dup = [m for m, n in collections.Counter(
    r["picture_md5"] for r in csv.DictReader(open(SPL, newline="", encoding="utf-8"))).items() if n > 1]
if dup:
    fails.append(f"duplicate rows in split.csv: {len(dup)}")
ineligible = set(split) - set(matrix)
if ineligible:
    fails.append(f"{len(ineligible)} ineligible rows in split")

print("FAILURES:" if fails else "ALL CHECKS PASS", len(fails))
for f_ in fails[:20]:
    print(" -", f_)
sys.exit(1 if fails else 0)
