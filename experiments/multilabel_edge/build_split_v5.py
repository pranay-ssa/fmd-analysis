"""Build the train/test splits, v5 (frozen considerations, 2026-10-26).

Frozen rules (user, 2026-10-26):
  * universe = the annotation, one annotation of record per picture, newest file wins,
    duplicate copies counted once (6,938 pictures);
  * label space = Draft 2 codes + Clear only; HEMA Obstruction, Bubble On 123 and
    Bubble On Edge are legacy and are not split rows (105 pictures drop);
  * the four gated object classes are positive only on the micron-gate tag
    (Foreign Matter, Fiber, Extraneous Polymer, HEMA); a picture carrying the plain
    object without a gate tag is not a split row (259 pictures drop);
  * Bubble, Bubble Cluster and Wet Package are positives on the class box;
  * Bubble Cluster 428 (the two older-library rescue labels are dropped);
  * 32 objects renamed Fiber / Extraneous Polymer stay under Fiber for the EDA, but only
    the gate tag makes a split positive, so Fiber reads 136.

Recipe unchanged from v4: iterative stratification (Sechidis 2011), two-way,
content md5 groups, no validation split, both 70/30 and 80/20.

Input  (read-only): run/eda_full_20261015/resolved_labels.csv
Output: run/split_20261026_v5/{split_70_30.csv,split_80_20.csv,meta.json}
"""
import csv, json, collections, hashlib, os

ROOT = "D:/fmd-analysis"
# Inputs and output can be pointed at a newer annotation run without editing this file:
#   SPLIT_RESOLVED=run/eda_full_20261028/resolved_labels.csv SPLIT_OUT=run/split_20261028_v6
RES = os.environ.get("SPLIT_RESOLVED", f"{ROOT}/run/eda_full_20261028/resolved_labels.csv")
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"
OUT = os.environ.get("SPLIT_OUT", f"{ROOT}/run/split_20261028_v6")
os.makedirs(OUT, exist_ok=True)

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
# Any object of the four debris families, under either the code or the older plain name.
# A picture carrying one of these without any gate tag is a plain carrier and is not a
# split row (the v4 rule, kept).
PLAIN = {"P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
         "P3_HE", "HEMA Fragment"}

LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "wet_package",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "bubble_scatter", "clear"]
RATIOS = [("70_30", 0.70), ("80_20", 0.80)]


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


codes = collections.defaultdict(set)
path = {}
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    codes[r["picture_md5"]].add(r["code"])
    path[r["picture_md5"]] = r["winning_path"]

lab, plain_only, dropped_legacy, dropped_plain = {}, [], [], []
for m, cs in codes.items():
    row = {c: 0 for c in LABEL_COLS}
    for code in cs:
        if code in GATE:
            row[GATE[code]] = 1
        elif code in CLASS:
            row[CLASS[code]] = 1
    gate_present = any(code in GATE for code in cs)
    plain_present = any(code in PLAIN for code in cs)
    if not any(row[c] for c in LABEL_COLS):
        if cs & PLAIN:
            # carries a debris object but no gate tag and nothing else: no positive
            # to train on, so it is not a split row
            dropped_plain.append(m)
        elif cs:
            dropped_legacy.append(m)  # legacy-only: no Draft 2 code
        else:
            row["clear"] = 1          # nothing marked anywhere
            lab[m] = row
        continue
    lab[m] = row

# Clear pictures carry no annotation entry, so they are not in resolved_labels.csv.
# Their identity comes from the matrix's clear flag, which was checked equal to the
# set of pictures with an empty annotation entry.
clear_md5 = {r["picture_md5"] for r in csv.DictReader(open(MAT, newline="", encoding="utf-8"))
             if r["clear"] == "1"}
assert len(clear_md5) == 2156
for m in clear_md5:
    assert m not in lab
    row = {c: 0 for c in LABEL_COLS}
    row["clear"] = 1
    lab[m] = row

rows = sorted(lab)
n = len(rows)
assert n == 6659, n
assert len(dropped_legacy) == 105 and len(dropped_plain) == 174, (len(dropped_legacy), len(dropped_plain))
assert len(codes) == 4782 and len(codes) + len(clear_md5) == 6938

label_sets = {m: {c for c in LABEL_COLS if lab[m][c]} for m in rows}


def iterative_stratification(samples, label_sets, ratios):
    c = {j: {l: ratios[j][1] * sum(1 for s in samples if l in label_sets[s])
             for l in LABEL_COLS} for j in range(len(ratios))}
    cap = {j: ratios[j][1] * len(samples) for j in range(len(ratios))}
    unassigned = set(samples)
    assignment = {}
    while unassigned:
        remaining = {l: sum(1 for s in unassigned if l in label_sets[s]) for l in LABEL_COLS}
        label = max(sorted(remaining), key=lambda l: remaining[l])
        if remaining[label] == 0:
            break
        for s in sorted(s for s in unassigned if label in label_sets[s]):
            best = max(range(len(ratios)), key=lambda j: (c[j][label], -cap[j]))
            assignment[s] = ratios[best][0]
            for l in label_sets[s]:
                c[best][l] -= 1
            cap[best] -= 1
            unassigned.discard(s)
    for s in sorted(unassigned):
        best = max(range(len(ratios)), key=lambda j: cap[j])
        assignment[s] = ratios[best][0]
        cap[best] -= 1
    return assignment


pos = {c: sum(1 for m in rows if c in label_sets[m]) for c in LABEL_COLS}
meta = {
    "version": "v5", "date": "2026-10-26",
    "decision": ("user 2026-10-26: maintain the approved EDA distribution; label space = Draft 2 codes + "
                 "Clear; legacy classes excluded; gated object classes positive on the micron-gate tag only; "
                 "the gate rule applies to the four gated classes only, so a picture is dropped "
                 "only when it has no positive at all; Bubble Cluster 428"),
    "recipe": "iterative stratification (Sechidis 2011), two-way, content-md5 groups, no validation split",
    "input": {"resolved_labels": RES, "resolved_labels_md5": md5_of(RES)},
    "rows": n,
    "dropped": {"legacy_only": len(dropped_legacy), "debris_without_gate_and_nothing_else": len(dropped_plain)},
    "positives": pos,
    "splits": {},
}
for name, r_train in RATIOS:
    assignment = iterative_stratification(rows, label_sets, [("train", r_train), ("test", 1 - r_train)])
    groups = collections.defaultdict(set)
    for m in rows:
        groups[m].add(assignment[m])
    crossing = [g for g, s in groups.items() if len(s) > 1]
    assert not crossing
    out_path = f"{OUT}/split_{name}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["picture_md5", "group_id", "split"])
        for m in rows:
            w.writerow([m, m, assignment[m]])
    per_class = {}
    for c in LABEL_COLS:
        tr = sum(1 for m in rows if c in label_sets[m] and assignment[m] == "train")
        te = sum(1 for m in rows if c in label_sets[m] and assignment[m] == "test")
        per_class[c] = {"train": tr, "test": te,
                        "expect_train": round(r_train * (tr + te), 1),
                        "expect_test": round((1 - r_train) * (tr + te), 1)}
    counts = collections.Counter(assignment.values())
    meta["splits"][name] = {"r_train": r_train, "split_counts": dict(counts),
                            "per_class": per_class, "group_crossings": len(crossing),
                            "split_csv_md5": md5_of(out_path)}
    print(f"== {name} ==  rows {n}  counts {dict(counts)}  crossings {len(crossing)}")
    for c in LABEL_COLS:
        p = per_class[c]
        print(f"  {c:34s} train {p['train']:5d} test {p['test']:4d}  (expect {p['expect_train']} / {p['expect_test']})")

with open(f"{OUT}/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)
print("meta written:", f"{OUT}/meta.json")
print("positives:", pos)
