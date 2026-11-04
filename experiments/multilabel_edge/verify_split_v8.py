"""Verify the v8 split against the annotation, independently of the builder.

The point of this file is to disagree with the builder. It rebuilds the label sets from
the annotation and the picture table with its own code, recomputes every count, and
compares them with the split file and with meta.json. It also tampers with a copy of the
split to prove it would notice.

Run:
    python experiments/multilabel_edge/verify_split_v8.py
Exit 0 = the split matches the annotation under the frozen rules.
"""
import collections
import csv
import json
import os
import shutil
import sys
import tempfile

ROOT = "D:/fmd-analysis"
RUN = f"{ROOT}/run/eda_full_20261029"
RES = os.environ.get("SPLIT_RESOLVED", f"{RUN}/resolved_labels.csv")
PT = os.environ.get("SPLIT_PICTURES", f"{RUN}/picture_table.csv")
OUT = os.environ.get("SPLIT_OUT", f"{ROOT}/run/split_20261103_v8")
NAME = "70_15_15"

GATE = {"P3_FM_MICRON_THRESHOLD": "foreign_matter_micron_gate",
        "P3_FIB_MICRON_THRESHOLD": "fiber_micron_gate",
        "P3_EP_MICRON_THRESHOLD": "extraneous_polymer_micron_gate",
        "P3_HE_MICRON_THRESHOLD": "hema_micron_gate"}
CLASS = {"P2_BB": "bubble", "Bubble": "bubble", "P2_BI": "bubble", "Bubble Irregular": "bubble",
         "P2_BST": "bubble", "Stretched Bubble": "bubble",
         "P2_BC": "bubble_cluster", "Bubble Cluster": "bubble_cluster",
         "P2_WP": "wet_package", "Wet Package": "wet_package",
         "P1_MPP": "missing_primary_package", "P1_PPM": "package_misalignment",
         "P1_COC": "cavity_off_center", "P2_FOV": "view_obstructed", "F2_FOV": "view_obstructed",
         "P1_NL": "no_lens", "P1_ML": "multiple_lenses", "P1_FL": "folded_lens",
         "P2_LOC": "lens_off_center", "P2_LD": "low_dose", "P2_DS": "dirty_strobe",
         "P2_DC": "dirty_camera", "P2_BSC": "bubble_scatter"}
DEBRIS = {"P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
          "P3_HE", "HEMA Fragment"}
LAB = ["foreign_matter_micron_gate", "fiber_micron_gate", "extraneous_polymer_micron_gate",
       "hema_micron_gate", "bubble", "bubble_cluster", "wet_package", "missing_primary_package",
       "multiple_lenses", "no_lens", "cavity_off_center", "folded_lens", "lens_off_center",
       "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed", "package_misalignment",
       "bubble_scatter", "clear"]

# Hand-typed from the 2026-11-03 readout, not copied from meta.json.
TOTALS = (5239, 1110, 1121)          # train / val / test
SPOT = {"folded_lens": (249, 33, 51),
        "clear": (1482, 318, 317),
        "dirty_strobe": (23, 8, 2),
        "bubble_scatter": (3, 1, 1)}
EXPECT_POS = {"foreign_matter_micron_gate": 454, "fiber_micron_gate": 362,
              "extraneous_polymer_micron_gate": 135, "hema_micron_gate": 151, "bubble": 2171,
              "bubble_cluster": 1132, "wet_package": 314, "missing_primary_package": 1428,
              "multiple_lenses": 1426, "no_lens": 326, "cavity_off_center": 185,
              "folded_lens": 333, "lens_off_center": 1201, "dirty_camera": 573,
              "dirty_strobe": 33, "low_dose": 677, "view_obstructed": 63,
              "package_misalignment": 33, "bubble_scatter": 5, "clear": 2117}

codes = collections.defaultdict(set)
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    codes[r["picture_md5"]].add(r["code"])

clear = {p["md5"] for p in csv.DictReader(open(PT, newline="", encoding="utf-8"))
         if p["winning_path"].split("/")[1:2] == ["Clear"] and p["md5"] not in codes}

sets, dropped = {}, {"legacy": 0, "plain": 0}
for m, cs in codes.items():
    s = {GATE[c] for c in cs if c in GATE} | {CLASS[c] for c in cs if c in CLASS}
    if not s:
        if cs & DEBRIS:
            dropped["plain"] += 1
        else:
            dropped["legacy"] += 1
        continue
    sets[m] = s
for m in clear:
    sets[m] = {"clear"}

bad = []
if len(sets) != 7470:
    bad.append(f"rows {len(sets)} != 7470")
pos = {c: sum(1 for s in sets.values() if c in s) for c in LAB}
for c, n in EXPECT_POS.items():
    if pos[c] != n:
        bad.append(f"positives {c}: {pos[c]} != {n}")
if dropped != {"legacy": 62, "plain": 85}:
    bad.append(f"dropped buckets {dropped} != legacy 62 / plain 85")

meta = json.load(open(f"{OUT}/meta.json", encoding="utf-8"))
if meta["rows"] != len(sets):
    bad.append(f"meta rows {meta['rows']} != {len(sets)}")
if meta["dropped"] != {"legacy_only": 62, "debris_without_gate_and_nothing_else": 85}:
    bad.append(f"meta dropped {meta['dropped']}")

split_path = f"{OUT}/split_{NAME}.csv"
rows = list(csv.DictReader(open(split_path, newline="", encoding="utf-8")))
got = {r["picture_md5"]: r["split"] for r in rows}

if set(got) != set(sets):
    bad.append(f"split key set differs: {len(got)} rows vs {len(sets)} in the annotation")
else:
    counts = collections.Counter(got.values())
    actual = (counts["train"], counts["val"], counts["test"])
    if actual != TOTALS:
        bad.append(f"totals {actual} != hand-typed {TOTALS}")
    if counts["train"] + counts["val"] + counts["test"] != len(rows):
        bad.append("a row carries a split name outside train/val/test")
    for c in LAB:
        tr = sum(1 for m, s in sets.items() if c in s and got[m] == "train")
        va = sum(1 for m, s in sets.items() if c in s and got[m] == "val")
        te = sum(1 for m, s in sets.items() if c in s and got[m] == "test")
        pc = meta["splits"][NAME]["per_class"][c]
        if (pc["train"], pc["val"], pc["test"]) != (tr, va, te):
            bad.append(f"{c}: meta {pc['train']}/{pc['val']}/{pc['test']} != file {tr}/{va}/{te}")
        if tr + va + te != pos[c]:
            bad.append(f"{c}: split positives {tr + va + te} != annotation {pos[c]}")
        if c in SPOT and (tr, va, te) != SPOT[c]:
            bad.append(f"{c}: spot check {tr}/{va}/{te} != hand-typed {SPOT[c]}")

# A group is one md5, so a picture may not appear twice and may not straddle splits.
per_group = collections.defaultdict(set)
for r in rows:
    per_group[r["group_id"]].add(r["split"])
straddle = [g for g, s in per_group.items() if len(s) > 1]
if straddle:
    bad.append(f"{len(straddle)} groups straddle splits")
if len(per_group) != len(rows):
    bad.append(f"{len(rows) - len(per_group)} duplicate group ids")

print(f"rows {len(sets)}  dropped {dropped}")
print(f"split counts {TOTALS[0]} / {TOTALS[1]} / {TOTALS[2]}")
if bad:
    print("FAIL")
    for b in bad:
        print("  ", b)
    sys.exit(1)

# Tamper proof: move one val picture to test in a copy. The count check must fail.
with tempfile.TemporaryDirectory() as td:
    dst = os.path.join(td, "split.csv")
    shutil.copy(split_path, dst)
    tampered = list(csv.DictReader(open(dst, newline="", encoding="utf-8")))
    for row in tampered:
        if row["split"] == "val":
            row["split"] = "test"
            break
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["picture_md5", "group_id", "split"])
        w.writeheader()
        w.writerows(tampered)
    c = collections.Counter(r["split"] for r in tampered)
    if (c["train"], c["val"], c["test"]) == TOTALS:
        print("FAIL: the tampered row was not caught")
        sys.exit(1)
    print("tampered-row proof: caught as expected")

print("PASS: the v8 split matches the annotation under the frozen rules")
