"""Verify EDA_Draft2_20261026.xlsx against the annotation.

Recomputes the numbers from resolved_labels.csv + the Clear/split flags, then
reads the workbook and compares by row label. Ends with a tampered-cell proof.
"""
import csv, collections, os, shutil, sys, tempfile
from openpyxl import load_workbook

ROOT = "D:/fmd-analysis"
WB = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx"
RES = f"{ROOT}/run/eda_full_20261015/resolved_labels.csv"
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"

MAP = {"P2_BB": "Bubble", "Bubble": "Bubble", "P2_BI": "Bubble", "Bubble Irregular": "Bubble",
       "P2_BST": "Bubble", "Stretched Bubble": "Bubble", "P2_BC": "Bubble Cluster",
       "Bubble Cluster": "Bubble Cluster", "P2_WP": "Wet Package", "Wet Package": "Wet Package",
       "P3_FM": "Foreign Matter", "Foreign Matter": "Foreign Matter", "P3_FIB": "Fiber",
       "Fiber": "Fiber", "P3_EP": "Extraneous Polymer", "Extraneous Polymer": "Extraneous Polymer",
       "P3_HE": "HEMA", "HEMA Fragment": "HEMA", "Bubble On 123": "Bubble On 123",
       "Bubble On Edge": "Bubble On Edge", "P1_MPP": "Missing Primary Package",
       "P1_PPM": "Package Misalignment", "P1_COC": "Cavity Off Center", "P1_ML": "Multiple Lens",
       "P1_FL": "Folded Lens", "P1_NL": "No Lens", "P2_LOC": "Lens Off Center", "P2_LD": "Low Dose",
       "P2_DS": "Dirty Strobe", "P2_DC": "Dirty Camera", "P2_BSC": "Bubble Scatter",
       "P2_HMO": "HEMA Obstruction", "F2_FOV": "View Obstructed", "P2_FOV": "View Obstructed",
       "P3_FM_MICRON_THRESHOLD": "Foreign Matter", "P3_FIB_MICRON_THRESHOLD": "Fiber",
       "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer", "P3_HE_MICRON_THRESHOLD": "HEMA"}
GATE = {"Foreign Matter": "P3_FM_MICRON_THRESHOLD", "Fiber": "P3_FIB_MICRON_THRESHOLD",
        "Extraneous Polymer": "P3_EP_MICRON_THRESHOLD", "HEMA": "P3_HE_MICRON_THRESHOLD"}

codes = collections.defaultdict(set)
objects = collections.Counter()
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    codes[r["picture_md5"]].add(r["code"])
    if r["shape_kind"] == "box":
        objects[MAP[r["code"]]] += 1

mat = list(csv.DictReader(open(MAT, newline="", encoding="utf-8")))
FLIP = {r["picture_md5"] for r in mat if r["fiber_micron_gate"] == "1"
        and "P3_FIB_MICRON_THRESHOLD" not in codes[r["picture_md5"]]}
CLEAR = {r["picture_md5"] for r in mat if r["clear"] == "1"}
ELIG = {r["picture_md5"] for r in mat if r["split_eligible"] == "1"}

labels = {}
for p, cs in codes.items():
    s = {MAP[c] for c in cs}
    if p in FLIP:
        s -= {"Extraneous Polymer"}
        s |= {"Fiber"}
    labels[p] = s
for p in CLEAR:
    labels[p] = {"Clear"}
N = len(labels)
per = collections.Counter()
for s in labels.values():
    per.update(s)
card = collections.Counter(len(s) for s in labels.values())
pairs = collections.Counter(tuple(sorted(s)) for s in labels.values() if len(s) == 2)
incl = collections.Counter()
for s in labels.values():
    if len(s) > 1:
        ss = sorted(s)
        for i, a in enumerate(ss):
            for b in ss[i + 1:]:
                incl[(a, b)] += 1
DEB = {"Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"}
deb = {p for p, s in labels.items() if s & DEB}

assert N == 6938 and per["Clear"] == 2156 and per["Bubble Cluster"] == 428
assert dict(card) == {1: 5531, 2: 649, 3: 418, 4: 199, 5: 97, 6: 29, 7: 12, 8: 3}
assert len(deb) == 647 and len(pairs) == 28 and len(incl) == 83
assert objects["Bubble"] == 11045 and objects["HEMA"] == 103


def sheet(wb, name):
    return [r for r in wb[name].iter_rows(min_col=1, max_col=8, values_only=True)
            if any(v is not None for v in r)]


def row(rows, key, col=0):
    for r in rows:
        if r[col] is not None and str(r[col]).strip() == key:
            return r
    return None


def check(path):
    wb = load_workbook(path, data_only=True)
    bad = []

    s = sheet(wb, "Summary")
    for key, want in [("Pictures examined", 10614), ("Pictures in an annotation (the analysed set)", 6938),
                      ("of which carry a mark", 4782), ("of which have nothing marked (Clear)", 2156)]:
        r = row(s, key)
        if r is None or r[1] != want:
            bad.append(f"summary {key}: {r and r[1]} != {want}")
    for name, n in per.items():
        r = row(s, name)
        if r is None or r[2] != n:
            bad.append(f"summary {name}: {r and r[2]} != {n}")

    lp = sheet(wb, "LP Summary")
    for name in ["Missing Primary Package", "Multiple Lens", "Lens Off Center", "No Lens", "Folded Lens",
                 "Low Dose", "Cavity Off Center", "Dirty Camera", "Dirty Strobe", "View Obstructed",
                 "Bubble Scatter", "Package Misalignment", "HEMA Obstruction"]:
        r = row(lp, name)
        want = (per[name], sum(1 for p in ELIG if name in labels[p]))
        if r is None or (r[2], r[4]) != want:
            bad.append(f"LP {name}: {r and (r[2], r[4])} != {want}")

    tc = sheet(wb, "Tag Combinations")
    for pr, n in pairs.most_common():
        r = row(tc, " + ".join(pr), col=1)
        if r is None or r[2] != n:
            bad.append(f"exact pair {'+'.join(pr)}: {r and r[2]} != {n}")
    for pr, n in incl.most_common():
        seen = [r[2] for r in tc if r[1] == " + ".join(pr)]
        if n not in seen:
            bad.append(f"inclusive pair {'+'.join(pr)}: {seen} missing {n}")
    for k in range(1, 9):
        got = [r[1] for r in tc if r[0] == k and isinstance(r[1], (int, float))]
        if got != [card.get(k, 0)]:
            bad.append(f"cardinality {k}: {got} != {card.get(k, 0)}")

    oo = sheet(wb, "OOI Summary")
    expect = {"Bubble": (862, 11045), "Bubble Cluster": (428, 1182), "Wet Package": (146, 662),
              "Foreign Matter": (331, 626), "Fiber": (210, 277), "Extraneous Polymer": (112, 118),
              "HEMA": (101, 103)}
    for name, (pics, objs) in expect.items():
        r = row(oo, name)
        if r is None or (r[2], r[4]) != (pics, objs):
            bad.append(f"OOI {name}: {r and (r[2], r[4])} != {(pics, objs)}")
    for cls, gate in GATE.items():
        r = row(oo, cls)
        want = len({p for p, cs in codes.items() if gate in cs})
        if r is None or r[3] != want:
            bad.append(f"OOI gate {cls}: {r and r[3]} != {want}")

    st = sheet(wb, "Standalone Tags")
    for name in ["Missing Primary Package", "Package Misalignment", "Cavity Off Center", "View Obstructed"]:
        r = row(st, name)
        if r is None or r[2] != 0:
            bad.append(f"standalone {name}: extra {r and r[2]} != 0")

    cr = sheet(wb, "Confusion Risks")
    for key, want in [("Wet Package (", 117), ("Multiple Lens (", 236), ("Lens Off Center (", 17)]:
        got = None
        for r in cr:
            if r[0] is not None and str(r[0]).startswith(key):
                got = r[4]
                break
        if got != want:
            bad.append(f"confusion {key}: {got} != {want}")

    ec = sheet(wb, "Earlier vs Current")
    for name, n in per.items():
        r = row(ec, name)
        if r is None or r[3] != n:
            bad.append(f"earlier/current {name}: {r and r[3]} != {n}")
    return bad


bad = check(WB)
print("checked 7 count sheets against the annotation")
if bad:
    print("FAIL")
    for b in bad:
        print("  ", b)
    sys.exit(1)

with tempfile.TemporaryDirectory() as td:
    copy = os.path.join(td, "t.xlsx")
    shutil.copy(WB, copy)
    wb = load_workbook(copy)
    ws = wb["OOI Summary"]
    for r in ws.iter_rows(min_row=1):
        if r[0].value == "HEMA":
            r[4].value = r[4].value + 1
            break
    wb.save(copy)
    if not check(copy):
        print("FAIL: a changed cell was not caught")
        sys.exit(1)
    print("tampered-cell proof: caught as expected")

print("PASS: the workbook matches the annotation")
