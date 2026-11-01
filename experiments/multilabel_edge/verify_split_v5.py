"""Verify the v5 splits against the annotation, independently of the builder."""
import csv, json, os, shutil, sys, tempfile, collections

ROOT = "D:/fmd-analysis"
RES = f"{ROOT}/" + os.environ.get("SPLIT_RESOLVED", "run/eda_full_20261028/resolved_labels.csv")
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"
OUT = f"{ROOT}/" + os.environ.get("SPLIT_OUT", "run/split_20261028_v6")

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

codes = collections.defaultdict(set)
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    codes[r["picture_md5"]].add(r["code"])
clear = {r["picture_md5"] for r in csv.DictReader(open(MAT, newline="", encoding="utf-8"))
         if r["clear"] == "1"}

sets, dropped = {}, {"legacy": 0, "plain": 0}
for m, cs in codes.items():
    s = {GATE[c] for c in cs if c in GATE} | {CLASS[c] for c in cs if c in CLASS}
    if not s:
        if cs & DEBRIS:
            dropped["plain"] += 1      # debris object, no gate, nothing else
        else:
            dropped["legacy"] += 1
        continue
    sets[m] = s
for m in clear:
    sets[m] = {"clear"}

EXPECT = {"foreign_matter_micron_gate": 166, "fiber_micron_gate": 137,
          "extraneous_polymer_micron_gate": 34, "hema_micron_gate": 94, "bubble": 862,
          "bubble_cluster": 427, "wet_package": 146, "missing_primary_package": 1426,
          "multiple_lenses": 1439, "no_lens": 325, "cavity_off_center": 184, "folded_lens": 237,
          "lens_off_center": 957, "dirty_camera": 329, "dirty_strobe": 43, "low_dose": 215,
          "view_obstructed": 24, "package_misalignment": 2, "bubble_scatter": 6, "clear": 2156}
TOTALS = {"70_30": (4653, 2006), "80_20": (5327, 1332)}

meta = json.load(open(f"{OUT}/meta.json", encoding="utf-8"))
bad = []

if len(sets) != 6659:
    bad.append(f"rows {len(sets)} != 6659")
if dropped != {"legacy": 105, "plain": 174}:
    bad.append(f"dropped {dropped}")
pos = {c: sum(1 for s in sets.values() if c in s) for c in LAB}
for c, n in EXPECT.items():
    if pos[c] != n:
        bad.append(f"positives {c}: {pos[c]} != {n}")
if meta["rows"] != len(sets):
    bad.append(f"meta rows {meta['rows']} != {len(sets)}")


def check(name, path):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    got = {r["picture_md5"]: r["split"] for r in rows}
    if set(got) != set(sets):
        bad.append(f"{name}: key set differs ({len(got)} rows)")
        return
    counts = collections.Counter(got.values())
    if (counts["train"], counts["test"]) != TOTALS[name]:
        bad.append(f"{name}: totals {counts['train']}/{counts['test']} != {TOTALS[name]}")
    for c in LAB:
        tr = sum(1 for m, s in sets.items() if c in s and got[m] == "train")
        te = sum(1 for m, s in sets.items() if c in s and got[m] == "test")
        pc = meta["splits"][name]["per_class"][c]
        if (pc["train"], pc["test"]) != (tr, te):
            bad.append(f"{name} {c}: meta {pc['train']}/{pc['test']} != file {tr}/{te}")
        if tr + te != pos[c]:
            bad.append(f"{name} {c}: positives {tr + te} != {pos[c]}")


check("70_30", f"{OUT}/split_70_30.csv")
check("80_20", f"{OUT}/split_80_20.csv")

print(f"rows {len(sets)}  dropped {dropped}")
if bad:
    print("FAIL")
    for b in bad:
        print("  ", b)
    sys.exit(1)

# tamper proof: move one picture to the other side in a copy
with tempfile.TemporaryDirectory() as td:
    src = f"{OUT}/split_70_30.csv"
    dst = os.path.join(td, "split_70_30.csv")
    shutil.copy(src, dst)
    rows = list(csv.DictReader(open(dst, newline="", encoding="utf-8")))
    rows[0]["split"] = "test" if rows[0]["split"] == "train" else "train"
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["picture_md5", "group_id", "split"])
        w.writeheader()
        w.writerows(rows)
    got = {r["picture_md5"]: r["split"] for r in rows}
    counts = collections.Counter(got.values())
    if (counts["train"], counts["test"]) == TOTALS["70_30"]:
        print("FAIL: tampered row was not caught")
        sys.exit(1)
    print("tampered-row proof: caught as expected")

print("PASS: both splits match the annotation under the frozen rules")
