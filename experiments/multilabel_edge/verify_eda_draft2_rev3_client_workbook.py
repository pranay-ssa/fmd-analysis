"""Verify EDA_Draft2_20261023.xlsx (rev3 client layout) against the artifacts.

Two layers:
1. Artifact assertions: recompute the headline counts, pair tables and split
   totals directly from run/multilabel_edge_20261023_rev3 and
   run/split_20261023_v4.
2. Cell comparison: regenerate the spec (same builder the workbook was made
   from) and compare EVERY cell of the workbook against it.

Usage: python verify_eda_draft2_rev3_client_workbook.py [workbook.xlsx]
Exit 0 = all checks pass; exit 1 lists the bad cells.
"""
import csv, json, sys, collections
from openpyxl import load_workbook

ROOT = "D:/fmd-analysis"
REV3 = f"{ROOT}/run/multilabel_edge_20261023_rev3"
WB = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261023.xlsx"
bad = []

# ---- layer 1: artifact assertions ----
META = json.load(open(f"{REV3}/label_matrix_meta.json", encoding="utf-8"))
SPLIT = json.load(open(f"{ROOT}/run/split_20261023_v4/meta.json", encoding="utf-8"))
rows = list(csv.DictReader(open(f"{REV3}/label_matrix.csv", newline="", encoding="utf-8")))
pos = collections.Counter()
for r in rows:
    for c, v in r.items():
        if v == "1":
            pos[c] += 1
checks = [
    (len(rows), META["headline"]["eda_rows"], "matrix rows vs meta"),
    (pos["multiple_lenses"], 1439, "ML"), (pos["lens_off_center"], 957, "LOC"),
    (pos["no_lens"], 325, "NL"), (pos["dirty_camera"], 329, "DC"),
    (pos["clear"], 2156, "Clear"), (pos["hema_obstruction"], 86, "HMO"),
    (pos["bubble"], 862, "Bubble"), (pos["missing_primary_package"], 1426, "MPP"),
    (META["headline"]["gated_families"]["foreign_matter_micron_gate"]["pictures_carrying_class"], 331, "FM carrying"),
    (META["headline"]["gated_families"]["fiber_micron_gate"]["pictures_carrying_class"], 210, "Fiber carrying"),
    (SPLIT["splits"]["70_30"]["split_counts"]["train"], 4568, "70/30 train"),
    (SPLIT["splits"]["80_20"]["split_counts"]["train"], 5269, "80/20 train"),
]
for got, want, what in checks:
    if got != want:
        bad.append(f"artifact {what}: recomputed {got!r} != expected {want!r}")

# ---- layer 2: every workbook cell vs the regenerated spec ----
import subprocess
spec_path = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261023_rev3_spec.json"
subprocess.run([sys.executable, f"{ROOT}/experiments/multilabel_edge/build_eda_draft2_rev3_client_spec.py"],
               check=True, capture_output=True)
spec = json.load(open(spec_path, encoding="utf-8"))
expected = {}
for sh in spec["sheets"]:
    grid = []
    for r in sh["rows"]:
        grid.append([("" if v is None else v) for v in r] if isinstance(r, list) else [])
    for addr, val in sh.get("cells", {}).items():
        ri = int(addr[1:]) - 1; ci = ord(addr[0]) - 65
        while len(grid) <= ri:
            grid.append([])
        while len(grid[ri]) <= ci:
            grid[ri].append("")
        grid[ri][ci] = val.get("value", val) if isinstance(val, dict) else val
    for ri, row in enumerate(grid, start=1):
        for ci, val in enumerate(row, start=1):
            if isinstance(val, dict):
                val = val.get("value", "")
            if val != "":
                expected[(sh["name"], f"{chr(64 + ci)}{ri}")] = val

wb_path = sys.argv[1] if len(sys.argv) > 1 else WB
wb = load_workbook(wb_path, data_only=True)
if set(wb.sheetnames) != {s["name"] for s in spec["sheets"]}:
    bad.append(f"sheet names differ: {wb.sheetnames}")
for (sheet, cell), want in sorted(expected.items()):
    if sheet not in wb.sheetnames:
        continue
    got = wb[sheet][cell].value
    if isinstance(want, float) and got is not None:
        if abs(float(got) - want) > 1e-9:
            bad.append(f"{sheet}!{cell}: workbook {got!r} != spec {want!r}")
    elif got != want:
        bad.append(f"{sheet}!{cell}: workbook {got!r} != spec {want!r}")

if bad:
    print("FAIL")
    for b in bad[:40]:
        print(" ", b)
    sys.exit(1)
print(f"OK: {len(checks)} artifact assertions + {len(expected)} workbook cells verified")
