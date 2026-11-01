"""Corrected object (box) counts for the Draft-2 OOI table.

The first OOI EDA counted only shapes whose class string is already a guide
code, so the old library's plain class names (Bubble 799, Bubble Cluster 112,
Wet Package 69, Foreign Matter 47, Fiber 22, Extraneous Polymer 1,
Bubble Irregular 41, HEMA Fragment 4) never reached the class rows. The
picture column came from the label matrix, which does fold those names in, so
the two columns of that table used different rules.

This script counts every box in the resolved line once, with the plain names
folded into their guide class, and writes the numbers the OOI table should
carry.

Input:  run/eda_full_20261015/resolved_labels.csv
Output: run/draft2_eda_20261023/ooi_objects_all.json
"""
import csv, collections, json

ROOT = "D:/fmd-analysis"
RES = f"{ROOT}/run/eda_full_20261015/resolved_labels.csv"
OUT = f"{ROOT}/run/draft2_eda_20261023/ooi_objects_all.json"

# guide class -> every class string that belongs to it
FAMILY = collections.OrderedDict([
    ("Bubble", ["P2_BB", "P2_BI", "P2_BST", "Bubble", "Bubble Irregular", "Stretched Bubble"]),
    ("Bubble Cluster", ["P2_BC", "Bubble Cluster"]),
    ("Wet Package", ["P2_WP", "Wet Package"]),
    ("Surface Groove", ["P1_SG"]),
    ("Fiber", ["P3_FIB", "Fiber"]),
    ("Extraneous Polymer", ["P3_EP", "Extraneous Polymer"]),
    ("HEMA", ["P3_HE", "HEMA Fragment"]),
    ("Foreign Matter", ["P3_FM", "Foreign Matter"]),
])
REFERENCE = collections.OrderedDict([
    ("Bubble On 123", ["Bubble On 123"]),
    ("Bubble On Edge", ["Bubble On Edge"]),
])

rows = [r for r in csv.DictReader(open(RES, newline="", encoding="utf-8"))
        if r["shape_kind"] == "box"]

by_code = collections.Counter(r["code"] for r in rows)
all_codes = set(by_code)
claimed = set()
out = {"population": {}, "classes": {}, "reference": {}, "composition": {}}

for name, codes in FAMILY.items():
    claimed |= set(codes)
    sel = [r for r in rows if r["code"] in codes]
    out["classes"][name] = {
        "objects": len(sel),
        "pictures": len({r["picture_md5"] for r in sel}),
        "codes": [c for c in codes if by_code.get(c)],
        "by_code": {c: by_code.get(c, 0) for c in codes if by_code.get(c)},
    }
for name, codes in REFERENCE.items():
    claimed |= set(codes)
    sel = [r for r in rows if r["code"] in codes]
    out["reference"][name] = {"objects": len(sel),
                              "pictures": len({r["picture_md5"] for r in sel})}

unclaimed = {c: by_code[c] for c in all_codes - claimed}
out["population"] = {
    "boxes_total": len(rows),
    "pictures_with_a_box": len({r["picture_md5"] for r in rows}),
    "unclaimed_codes": unclaimed,
}
out["composition"]["Bubble"] = {c: by_code.get(c, 0) for c in FAMILY["Bubble"] if by_code.get(c)}
out["totals"] = {
    "classes": sum(v["objects"] for v in out["classes"].values()),
    "reference": sum(v["objects"] for v in out["reference"].values()),
    "all": len(rows),
}
assert not unclaimed, unclaimed
assert out["totals"]["classes"] + out["totals"]["reference"] == out["totals"]["all"]

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)

print("written:", OUT)
for name, v in out["classes"].items():
    print(f'{name:<20} {v["objects"]:6} objects  {v["pictures"]:5} pictures')
for name, v in out["reference"].items():
    print(f'{name:<20} {v["objects"]:6} objects  {v["pictures"]:5} pictures')
print("total", out["totals"], "| pictures with a box", out["population"]["pictures_with_a_box"])
