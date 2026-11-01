"""Build the 70/30 train/test split (ticket 021).

Frame: docs/decisions/2026-10-21-multilabel-edge-frame.md, ticket 021.
Recipe (frozen, must not be relitigated): iterative stratification
(Sechidis et al. 2011) over the 23-column multi-hot matrix, two-way 70/30,
seed 42, group-aware assignment keyed on content md5 (each matrix row is
one distinct content, so groups are singletons by construction; the group
logic is kept so a multi-file content can never cross splits).

Inputs (read-only): run/multilabel_edge_20261021/label_matrix.csv
Outputs: run/split_20261023/split.csv + meta.json
Rows used: split_eligible == 1 only.
Checks at build time: zero groups crossing splits; per-class counts printed
with their 70/30 expectation; rare classes reported with exact test counts.
Determinism: sorted row order, deterministic tie-breaks, seed only for the
label-less fallback shuffle; a rerun must produce a byte-identical file.
"""
import csv, json, collections, hashlib, os

ROOT = "D:/fmd-analysis"
MAT = f"{ROOT}/run/multilabel_edge_20261021/label_matrix.csv"
OUT = f"{ROOT}/run/split_20261023"
os.makedirs(OUT, exist_ok=True)
LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "bubble_on_123", "bubble_on_edge",
              "wet_package", "bubble_scatter", "hema_obstruction",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "clear"]
R_TRAIN = 0.70
SEED = 42

rows = [r for r in csv.DictReader(open(MAT, newline="", encoding="utf-8"))
        if r["split_eligible"] == "1"]
rows.sort(key=lambda r: r["picture_md5"])
n = len(rows)

def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def iterative_stratification(samples, label_sets, ratios):
    """Sechidis et al. 2011. samples: list of ids; label_sets: id -> set(labels);
    ratios: [(name, r), ...]. Returns id -> subset name."""
    c = {j: {l: ratios[j][1] * sum(1 for s in samples if l in label_sets[s])
             for l in LABEL_COLS} for j in range(len(ratios))}
    cap = {j: ratios[j][1] * len(samples) for j in range(len(ratios))}
    unassigned = set(samples)
    assignment = {}
    while unassigned:
        # label with the most unassigned samples; tie -> alphabetical (deterministic)
        remaining = {l: sum(1 for s in unassigned if l in label_sets[s])
                     for l in LABEL_COLS}
        label = max(sorted(remaining), key=lambda l: remaining[l])
        if remaining[label] == 0:
            break
        holders = sorted(s for s in unassigned if label in label_sets[s])
        for s in holders:
            best = max(range(len(ratios)),
                       key=lambda j: (c[j][label], -cap[j]))
            assignment[s] = ratios[best][0]
            for l in label_sets[s]:
                c[best][l] -= 1
            cap[best] -= 1
            unassigned.discard(s)
    # label-less samples: deterministic round-robin on largest remaining capacity
    for s in sorted(unassigned):
        best = max(range(len(ratios)), key=lambda j: cap[j])
        assignment[s] = ratios[best][0]
        cap[best] -= 1
    return assignment

label_sets = {r["picture_md5"]: {c for c in LABEL_COLS if r[c] == "1"}
              for r in rows}
assignment = iterative_stratification([r["picture_md5"] for r in rows],
                                      label_sets,
                                      [("train", R_TRAIN), ("test", 1 - R_TRAIN)])

# group crossing check (groups are singletons here, but keep the guard)
groups = collections.defaultdict(set)
for r in rows:
    groups[r["picture_md5"]].add(assignment[r["picture_md5"]])
crossing = [g for g, s in groups.items() if len(s) > 1]
assert not crossing, crossing

out_path = f"{OUT}/split.csv"
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["picture_md5", "group_id", "split"])
    for r in rows:
        m = r["picture_md5"]
        w.writerow([m, m, assignment[m]])

per_class = {}
for c in LABEL_COLS:
    tr = sum(1 for r in rows if r[c] == "1" and assignment[r["picture_md5"]] == "train")
    te = sum(1 for r in rows if r[c] == "1" and assignment[r["picture_md5"]] == "test")
    per_class[c] = {"train": tr, "test": te,
                    "expect_train": round(R_TRAIN * (tr + te), 1),
                    "expect_test": round((1 - R_TRAIN) * (tr + te), 1)}
counts = collections.Counter(assignment.values())
meta = {
    "ticket": "021", "date": "2026-10-23",
    "recipe": "iterative stratification (Sechidis 2011), 70/30 two-way, seed 42, content-md5 groups, no validation split",
    "seed": SEED, "train_ratio": R_TRAIN,
    "input": {"label_matrix": MAT, "label_matrix_md5": md5_of(MAT)},
    "rows": n, "split_counts": dict(counts),
    "per_class": per_class,
    "rare_columns": {c: per_class[c] for c in
                     ("package_misalignment", "bubble_scatter", "bubble_on_123",
                      "bubble_on_edge", "view_obstructed")},
    "group_crossings": len(crossing),
    "split_csv_md5": md5_of(out_path),
}
with open(f"{OUT}/meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)
print(json.dumps({"rows": n, "split_counts": dict(counts),
                  "group_crossings": len(crossing),
                  "split_csv_md5": meta["split_csv_md5"]}, indent=2))
for c in LABEL_COLS:
    p = per_class[c]
    if p["train"] + p["test"]:
        print(f"{c:34s} train {p['train']:5d} test {p['test']:4d}  (expect {p['expect_train']} / {p['expect_test']})")
