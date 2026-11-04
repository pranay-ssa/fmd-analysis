"""Build the train/val/test split, v8: three-way 70/15/15 on the 24-file record.

What changed from v7 (2026-10-28)
---------------------------------
v7 is two-way (70/30 and 80/20), no validation split. v8 is ONE three-way split:

    train 70%   the model trains here
    val   15%   used for one thing only: choosing a decision threshold per class
    test  15%   read once, at the end, and never used to choose anything

The val share exists because the current runs report a threshold picked on the test
set. That number is optimistic by construction, and the handover package carries
those test-set values as if they were held out. With a val split the threshold has
its own data and the test read stays honest.

Frozen rules kept from v5/v7 (docs/decisions/2026-10-26-split-considerations.md):
  * universe = the annotation, one annotation of record per picture, newest file wins,
    duplicate copies counted once;
  * label space = Draft 2 codes + Clear only; legacy names are not split rows;
  * the four gated object classes are positive only on the micron-gate tag;
  * Bubble, Bubble Cluster and Wet Package are positives on the class box;
  * Clear is a picture with no other label, taken from the picture table.

Recipe unchanged: iterative stratification (Sechidis 2011), content-md5 groups,
seed-free deterministic assignment (the stratifier has no randomness; the file is
reproducible byte for byte).

Input  (read-only): run/eda_full_20261029/{resolved_labels.csv,picture_table.csv}
Output: run/split_20261103_v8/{split_70_15_15.csv,meta.json}
"""
import collections
import csv
import json
import os

ROOT = "D:/fmd-analysis"
RUN = f"{ROOT}/run/eda_full_20261029"
RES = os.environ.get("SPLIT_RESOLVED", f"{RUN}/resolved_labels.csv")
PT = os.environ.get("SPLIT_PICTURES", f"{RUN}/picture_table.csv")
OUT = os.environ.get("SPLIT_OUT", f"{ROOT}/run/split_20261103_v8")
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
PLAIN = {"P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
         "P3_HE", "HEMA Fragment"}
LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "wet_package",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "bubble_scatter", "clear"]

# The one split this version builds. Order matters: it is the tie-break order in the
# stratifier, so changing it changes the file.
RATIOS = [("train", 0.70), ("val", 0.15), ("test", 0.15)]
NAME = "70_15_15"
TOLERANCE = 0.01          # a split count may sit this far from its target share


def iterative_stratification(samples, label_sets, ratios):
    """Sechidis 2011, N-way. Each label keeps a running need per split; a sample goes
    to the split that still needs most of its rarest label."""
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


codes = collections.defaultdict(set)
for r in csv.DictReader(open(RES, newline="", encoding="utf-8")):
    codes[r["picture_md5"]].add(r["code"])

lab, dropped_legacy, dropped_plain = {}, [], []
for m, cs in codes.items():
    row = {c: 0 for c in LABEL_COLS}
    for code in cs:
        if code in GATE:
            row[GATE[code]] = 1
        elif code in CLASS:
            row[CLASS[code]] = 1
    if not any(row[c] for c in LABEL_COLS):
        if cs & PLAIN:
            dropped_plain.append(m)
        else:
            dropped_legacy.append(m)
        continue
    lab[m] = row

clear_md5 = {p["md5"] for p in csv.DictReader(open(PT, newline="", encoding="utf-8"))
             if p["winning_path"].split("/")[1:2] == ["Clear"] and p["md5"] not in codes}
for m in clear_md5:
    row = {c: 0 for c in LABEL_COLS}
    row["clear"] = 1
    lab[m] = row

rows = sorted(lab)
n = len(rows)
print(f"marked pictures {len(codes)}, clear {len(clear_md5)}, split rows {n}")
print(f"dropped: legacy-only {len(dropped_legacy)}, debris without gate and nothing else {len(dropped_plain)}")
assert len(codes) == 5500, len(codes)
assert len(clear_md5) == 2117, len(clear_md5)
assert len(codes) + len(clear_md5) - len(dropped_legacy) - len(dropped_plain) == n
assert n == 7470, n

label_sets = {m: {c for c in LABEL_COLS if lab[m][c]} for m in rows}
pos = {c: sum(1 for m in rows if c in label_sets[m]) for c in LABEL_COLS}

assignment = iterative_stratification(rows, label_sets, RATIOS)

groups = collections.defaultdict(set)
for m in rows:
    groups[m].add(assignment[m])
crossing = [g for g, s in groups.items() if len(s) > 1]
assert not crossing

counts = collections.Counter(assignment.values())
for name, share in RATIOS:
    want = share * n
    got = counts[name]
    assert abs(got - want) <= TOLERANCE * n, (name, got, want)

out_path = f"{OUT}/split_{NAME}.csv"
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["picture_md5", "group_id", "split"])
    for m in rows:
        w.writerow([m, m, assignment[m]])

per_class = {}
for c in LABEL_COLS:
    tr = sum(1 for m in rows if c in label_sets[m] and assignment[m] == "train")
    va = sum(1 for m in rows if c in label_sets[m] and assignment[m] == "val")
    te = sum(1 for m in rows if c in label_sets[m] and assignment[m] == "test")
    per_class[c] = {"train": tr, "val": va, "test": te,
                    "expect_train": round(0.70 * (tr + va + te), 1),
                    "expect_val": round(0.15 * (tr + va + te), 1),
                    "expect_test": round(0.15 * (tr + va + te), 1),
                    "val_share": round(va / (tr + va + te), 4) if (tr + va + te) else None}

meta = {
    "version": "v8",
    "date": "2026-11-03",
    "decision": ("user 2026-11-03: move to 70/15/15 so the per-class decision threshold can be "
                 "chosen on a validation split instead of on the test set. All frozen counting "
                 "rules of 2026-10-26 are unchanged; only the split shape and the role of the "
                 "middle share are new."),
    "recipe": ("iterative stratification (Sechidis 2011), three-way, content-md5 groups, "
               "deterministic (no random seed)"),
    "roles": {"train": "training only", "val": "decision threshold per class, nothing else",
              "test": "read once at the end, never used to choose anything"},
    "input": {"resolved_labels": RES, "picture_table": PT},
    "population": {"examined": 10614, "marked": len(codes), "clear": len(clear_md5),
                   "analysed": len(codes) + len(clear_md5)},
    "rows": n,
    "dropped": {"legacy_only": len(dropped_legacy),
                "debris_without_gate_and_nothing_else": len(dropped_plain)},
    "positives": pos,
    "splits": {
        NAME: {
            "ratios": {k: v for k, v in RATIOS},
            "split_counts": dict(counts),
            "per_class": per_class,
            "group_crossings": len(crossing),
            "split_csv": out_path,
        }
    },
}
with open(f"{OUT}/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print(f"\n== {NAME} == rows {n} counts {dict(counts)} crossings {len(crossing)}")
print(f"{'class':34s} {'train':>6s} {'val':>5s} {'test':>5s}   val share")
for c in LABEL_COLS:
    p = per_class[c]
    print(f"  {c:32s} {p['train']:6d} {p['val']:5d} {p['test']:5d}   {p['val_share']}")
print("meta written:", f"{OUT}/meta.json")
print("positives:", pos)
