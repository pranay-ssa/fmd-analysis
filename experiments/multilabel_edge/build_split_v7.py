"""Build the train/test splits, v7, on the annotation after the 24-file export.

Same frozen recipe as v5/v6 (docs/decisions/2026-10-26-split-considerations.md): iterative
stratification (Sechidis 2011), two-way, content-md5 groups, no validation split, both
70/30 and 80/20. Only the inputs moved: the annotation of record is the merged 24-file
record, and Clear is recomputed from the picture table (2,117 pictures).

Input  (read-only): run/eda_full_24files_20261028/{resolved_labels.csv,picture_table.csv}
Output: run/split_20261028_v7/{split_70_30.csv,split_80_20.csv,meta.json}

Checks, printed and enforced: every picture with marks is a split row, a legacy-only drop
or a debris-without-gate drop; Clear is 2,117; no md5 group crosses train/test.
"""
import collections
import csv
import json
import os

ROOT = "D:/fmd-analysis"
RUN = f"{ROOT}/run/eda_full_24files_20261028"
RES = os.environ.get("SPLIT_RESOLVED", f"{RUN}/resolved_labels.csv")
PT = os.environ.get("SPLIT_PICTURES", f"{RUN}/picture_table.csv")
OUT = os.environ.get("SPLIT_OUT", f"{ROOT}/run/split_20261028_v7")
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
RATIOS = [("70_30", 0.70), ("80_20", 0.80)]


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

label_sets = {m: {c for c in LABEL_COLS if lab[m][c]} for m in rows}
pos = {c: sum(1 for m in rows if c in label_sets[m]) for c in LABEL_COLS}
meta = {
    "version": "v7", "date": "2026-10-28",
    "decision": ("frozen considerations of 2026-10-26 applied to the merged 24-file record: label space = "
                 "Draft 2 codes + Clear; legacy classes excluded; gated object classes positive on the "
                 "micron-gate tag only; a picture is dropped only when it has no positive at all"),
    "recipe": "iterative stratification (Sechidis 2011), two-way, content-md5 groups, no validation split",
    "input": {"resolved_labels": RES, "picture_table": PT},
    "population": {"examined": 10614, "marked": len(codes), "clear": len(clear_md5),
                   "analysed": len(codes) + len(clear_md5)},
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
                            "per_class": per_class, "group_crossings": len(crossing)}
    print(f"== {name} ==  rows {n}  counts {dict(counts)}  crossings {len(crossing)}")
    for c in LABEL_COLS:
        p = per_class[c]
        print(f"  {c:34s} train {p['train']:5d} test {p['test']:4d}  (expect {p['expect_train']} / {p['expect_test']})")

v6 = json.load(open(f"{ROOT}/run/split_20261028_v6/meta.json", encoding="utf-8"))
meta["before"] = {"version": "v6", "rows": v6["rows"], "positives": v6["positives"],
                  "splits": {k: {"split_counts": v["split_counts"],
                                 "per_class": {c: {"train": p["train"], "test": p["test"]}
                                               for c, p in v["per_class"].items()}}
                             for k, v in v6["splits"].items()}}
with open(f"{OUT}/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)
print("meta written:", f"{OUT}/meta.json")
