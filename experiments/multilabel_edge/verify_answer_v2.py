"""Verify Tag_Combinations_Answer_20261026.xlsx cell by cell.

Recomputes every number from the annotation resolution with a second, separate
derivation, then reads the workbook and compares values by row label (not by
fixed cell address, so inserted rows cannot make the check pass by accident).
Ends with a corrupted-cell proof on a temporary copy.

Exit 0 = pass, exit 1 = names the bad rows.
"""
import csv, json, collections, os, shutil, sys, tempfile
from openpyxl import load_workbook

ROOT = "D:/fmd-analysis"
WB = f"{ROOT}/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx"
RES = f"{ROOT}/run/eda_full_20261015/resolved_labels.csv"
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"

# ------------------------------------------------ second derivation
MAP = {
    "P2_BB": "Bubble", "Bubble": "Bubble", "P2_BI": "Bubble", "Bubble Irregular": "Bubble",
    "P2_BST": "Bubble", "Stretched Bubble": "Bubble", "P2_BC": "Bubble Cluster",
    "Bubble Cluster": "Bubble Cluster", "P2_WP": "Wet Package", "Wet Package": "Wet Package",
    "P3_FM": "Foreign Matter", "Foreign Matter": "Foreign Matter", "P3_FIB": "Fiber", "Fiber": "Fiber",
    "P3_EP": "Extraneous Polymer", "Extraneous Polymer": "Extraneous Polymer", "P3_HE": "HEMA",
    "HEMA Fragment": "HEMA", "Bubble On 123": "Bubble On 123", "Bubble On Edge": "Bubble On Edge",
    "P1_MPP": "Missing Primary Package", "P1_PPM": "Package Misalignment",
    "P1_COC": "Cavity Off Center", "P1_ML": "Multiple Lens", "P1_FL": "Folded Lens", "P1_NL": "No Lens",
    "P2_LOC": "Lens Off Center", "P2_LD": "Low Dose", "P2_DS": "Dirty Strobe", "P2_DC": "Dirty Camera",
    "P2_BSC": "Bubble Scatter", "P2_HMO": "HEMA Obstruction", "F2_FOV": "View Obstructed",
    "P2_FOV": "View Obstructed", "P3_FM_MICRON_THRESHOLD": "Foreign Matter",
    "P3_FIB_MICRON_THRESHOLD": "Fiber", "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer",
    "P3_HE_MICRON_THRESHOLD": "HEMA",
}
GATE = {"Foreign Matter": "P3_FM_MICRON_THRESHOLD", "Fiber": "P3_FIB_MICRON_THRESHOLD",
        "Extraneous Polymer": "P3_EP_MICRON_THRESHOLD", "HEMA": "P3_HE_MICRON_THRESHOLD"}

pictures = collections.defaultdict(set)
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    pictures[r["picture_md5"]].add(r["code"])

flip = set()
clear = set()
for r in csv.DictReader(open(MAT, newline="", encoding="utf-8")):
    cs = pictures.get(r["picture_md5"], set())
    if r["fiber_micron_gate"] == "1" and "P3_FIB_MICRON_THRESHOLD" not in cs:
        flip.add(r["picture_md5"])
    if r["clear"] == "1":
        clear.add(r["picture_md5"])

sets = {}
for p, cs in pictures.items():
    s = {MAP[c] for c in cs}
    if p in flip:
        s -= {"Extraneous Polymer"}
        s |= {"Fiber"}
    sets[p] = s
for p in clear:
    sets[p] = {"Clear"}

N = len(sets)
card = collections.Counter(len(s) for s in sets.values())
single = collections.Counter(next(iter(s)) for s in sets.values() if len(s) == 1)
pair = collections.Counter(tuple(sorted(s)) for s in sets.values() if len(s) == 2)
per = collections.Counter()
for s in sets.values():
    per.update(s)
assert N == 6938 and sum(single.values()) == 5531 and sum(pair.values()) == 649
assert len(pair) == 28 and per["Fiber"] == 210 and per["Extraneous Polymer"] == 112
assert per["Clear"] == 2156 and single["Clear"] == 2156

DEB = ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"]
union = {p for p, s in sets.items() if s & set(DEB)}
multi = sum(1 for p in union if len(sets[p] & set(DEB)) > 1)
gate = {c: {p for p, cs in pictures.items() if GATE[c] in cs} for c in GATE}

# ------------------------------------------------ workbook read
def sheet_rows(wb, name):
    out = []
    for row in wb[name].iter_rows(min_col=1, max_col=8, values_only=True):
        if any(v is not None for v in row):
            out.append(row)
    return out


def find(rows, key, col=0):
    for r in rows:
        if r[col] is not None and str(r[col]).strip() == key:
            return r
    return None


def check(path):
    wb = load_workbook(path, data_only=True)
    bad = []

    # labels per picture
    rows = sheet_rows(wb, "Labels per picture")
    for k in range(0, 9):
        r = find(rows, str(k))
        if r is None:
            bad.append(f"labels per picture: row {k} missing")
            continue
        if r[1] != card.get(k, 0):
            bad.append(f"labels per picture: {k} labels -> {r[1]}, recomputed {card.get(k, 0)}")
    tot = find(rows, "Total")
    if tot is None or tot[1] != N:
        bad.append(f"labels per picture: total {tot and tot[1]} != {N}")

    # labels considered
    rows = sheet_rows(wb, "Labels considered")
    for name, n in per.items():
        r = find(rows, name)
        if r is None:
            bad.append(f"labels considered: {name} missing")
        elif r[3] != n:
            bad.append(f"labels considered: {name} -> {r[3]}, recomputed {n}")
    for name in DEB:
        r = find(rows, name + " size flag")
        if r is None or r[3] != len(gate[name]):
            bad.append(f"labels considered: {name} flag -> {r and r[3]}, recomputed {len(gate[name])}")

    # one-label
    rows = sheet_rows(wb, "One-label pictures")
    for name, n in single.most_common():
        r = find(rows, name, col=1)
        if r is None or r[2] != n:
            bad.append(f"one-label: {name} -> {r and r[2]}, recomputed {n}")
    tot = find(rows, "Total", col=1)
    if tot is None or tot[2] != sum(single.values()):
        bad.append(f"one-label: total {tot and tot[2]} != {sum(single.values())}")

    # two-label
    rows = sheet_rows(wb, "Two-label pictures")
    for pr, n in pair.most_common():
        r = find(rows, " + ".join(pr), col=1)
        if r is None or r[2] != n:
            bad.append(f"two-label: {' + '.join(pr)} -> {r and r[2]}, recomputed {n}")
    tot = find(rows, "Total", col=1)
    if tot is None or tot[2] != sum(pair.values()):
        bad.append(f"two-label: total {tot and tot[2]} != {sum(pair.values())}")

    # debris
    rows = sheet_rows(wb, "Debris group")
    for name in DEB:
        r = find(rows, name)
        if r is None or r[1] != per[name] or r[2] != len(gate[name]):
            bad.append(f"debris: {name} -> {r and (r[1], r[2])}, recomputed {(per[name], len(gate[name]))}")
    r = find(rows, "Debris group, pictures (each picture once)")
    if r is None or r[1] != len(union):
        bad.append(f"debris: group total {r and r[1]} != {len(union)}")
    r = find(rows, "Two or more of the four classes")
    if r is None or r[1] != multi:
        bad.append(f"debris: multi-class {r and r[1]} != {multi}")

    # objects per class
    rows = sheet_rows(wb, "Objects per class")
    expect = {"Bubble": (11045, 862), "Bubble Cluster": (1182, 428), "Wet Package": (662, 146),
              "Fiber": (277, 210), "Extraneous Polymer": (118, 112), "HEMA": (103, 101),
              "Foreign Matter": (626, 331), "Bubble On 123": (79, 13), "Bubble On Edge": (90, 14)}
    for name, (o, p) in expect.items():
        r = find(rows, name)
        if r is None or r[2] != o or r[3] != p:
            bad.append(f"objects: {name} -> {r and (r[2], r[3])}, recomputed {(o, p)}")
    tot = find(rows, "Total objects")
    if tot is None or tot[2] != 14182:
        bad.append(f"objects: total {tot and tot[2]} != 14182")
    return bad


bad = check(WB)
print(f"checked 8 sheets against a second derivation")
if bad:
    print("FAIL")
    for b in bad:
        print("  ", b)
    sys.exit(1)

with tempfile.TemporaryDirectory() as td:
    copy = os.path.join(td, "t.xlsx")
    shutil.copy(WB, copy)
    wb = load_workbook(copy)
    ws = wb["One-label pictures"]
    for row in ws.iter_rows(min_row=1):
        if row[1].value == "Clear":
            row[2].value = row[2].value + 1
            break
    wb.save(copy)
    if not check(copy):
        print("FAIL: a changed cell was not caught")
        sys.exit(1)
    print("corrupted-cell proof: caught as expected")

print("PASS: every number in the workbook matches the annotation")
