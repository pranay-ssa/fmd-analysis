#!/usr/bin/env python3
"""Build the frozen 70/15/15 split, 17 columns, Clear and six classes excluded.

Population: 13,682 records, four duplicate records dropped by the highest-box
rule (tie keeps the plain name), 42 Clear pictures excluded, five unmarked
pictures excluded. Every remaining picture carries at least one kept label.

Output: split.csv, labels_17.csv, meta.json in this folder.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT / "run/frozen_eda_20261117/store"
OUT = Path(__file__).resolve().parent / "frozen_70_15_15_20261119"
SEED = 42
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}

# Trainer column names, in the trainer's order. The two excluded LP classes
# (Dirty Strobe, Bubble Scatter) are absent, and F2_FOV maps to P2_FOV.
COLUMNS = [
    "P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD", "P1_COC",
    "P2_FOV", "P1_PPM",
    "class_bubble", "class_bubble_cluster", "class_foreign_matter", "class_fiber",
    "class_wet_package", "class_hema", "class_extraneous_polymer",
]
LP_MAP = {
    "P1_MPP": "P1_MPP", "P1_ML": "P1_ML", "P2_LOC": "P2_LOC", "P2_DC": "P2_DC",
    "P1_NL": "P1_NL", "P1_FL": "P1_FL", "P2_LD": "P2_LD", "P1_COC": "P1_COC",
    "P2_FOV": "F2_FOV", "P1_PPM": "P1_PPM",
}
OBJ_MAP = {
    "class_bubble": "P2_BB", "class_bubble_cluster": "P2_BC",
    "class_foreign_matter": "P3_FM", "class_fiber": "P3_FIB",
    "class_wet_package": "P2_WP", "class_hema": "P3_HE",
    "class_extraneous_polymer": "P3_EP",
}
EXCLUDED = {
    "P1_EBC": ("Edge Bottle-Capped", 24),
    "P1_LR": ("Lens Rupture", 35),
    "P1_TL": ("Torn Lens", 117),
    "P2_BSC": ("Bubble Scatter", 12),
    "P2_DS": ("Dirty Strobe", 33),
    "P1_SG": ("Surface Groove", 88),
}


def md5_of(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def main():
    man = list(csv.DictReader(open(STORE / "manifest.csv", encoding="utf-8-sig")))
    boxes = list(csv.DictReader(open(STORE / "labels/boxes.csv", encoding="utf-8-sig")))
    tags = list(csv.DictReader(open(STORE / "labels/tags.csv", encoding="utf-8-sig")))

    box_count = Counter(b["basename"] for b in boxes)
    pairs = defaultdict(list)
    for m in man:
        if m["content_duplicate"] == "yes":
            pairs[m["picture_key"]].append(m["basename"])
    kept_pair_rows = []
    drop = set()
    for key, names in pairs.items():
        names = sorted(names)
        best = max(names, key=lambda n: (box_count[n], -len(n)))
        kept_pair_rows.append({"md5": key, "kept": best,
                               "boxes": {n: box_count[n] for n in names}})
        drop.update(set(names) - {best})

    pic = defaultdict(lambda: {"lp": set(), "box": set()})
    for t in tags:
        if t["kind"] == "tag":
            pic[t["basename"]]["lp"].add(t["code"])
    for b in boxes:
        pic[b["basename"]]["box"].add(b["code"])

    clear = {m["basename"] for m in man
             if m["is_clear_source"] == "yes" and m["has_marks"] == "no"}
    marked = {m["basename"] for m in man if m["has_marks"] == "yes"}

    rows = []
    for m in man:
        n = m["basename"]
        if n in drop or n in clear or n not in marked:
            continue
        labels = [0] * len(COLUMNS)
        for j, col in enumerate(COLUMNS):
            code = LP_MAP.get(col) or OBJ_MAP[col]
            source = pic[n]["lp"] if col in LP_MAP else pic[n]["box"]
            labels[j] = 1 if code in source else 0
        if not any(labels):
            continue
        rows.append({"md5": m["picture_key"], "image_path": n, "labels": labels})

    # deterministic order before the splitter
    rows.sort(key=lambda r: (r["md5"], r["image_path"]))
    X = np.array([r["labels"] for r in rows], dtype=np.int8)
    ph = np.zeros((len(rows), 1))
    kw = dict(n_splits=1, random_state=SEED)
    trainval, test = next(MultilabelStratifiedShuffleSplit(test_size=RATIOS["test"], **kw).split(ph, X))
    val_fraction = RATIOS["val"] / (RATIOS["train"] + RATIOS["val"])
    train_rel, val_rel = next(
        MultilabelStratifiedShuffleSplit(test_size=val_fraction, **kw).split(ph[trainval], X[trainval]))
    split = {}
    for i in trainval[train_rel]:
        split[int(i)] = "train"
    for i in trainval[val_rel]:
        split[int(i)] = "val"
    for i in test:
        split[int(i)] = "test"

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "split.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["md5", "image_path", "split"])
        for i, r in enumerate(rows):
            w.writerow([r["md5"], r["image_path"], split[i]])
    with open(OUT / "labels_17.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["md5", "image_path", "split"] + COLUMNS)
        for i, r in enumerate(rows):
            w.writerow([r["md5"], r["image_path"], split[i]] + r["labels"])

    counts = Counter(split.values())
    class_totals = {c: int(X[:, j].sum()) for j, c in enumerate(COLUMNS)}
    meta = {
        "name": "frozen_70_15_15_20261119",
        "date": str(date(2026, 11, 19)),
        "source_store": str(STORE).replace("\\", "/"),
        "builder": "build_frozen_split.py",
        "seed": SEED,
        "ratios": RATIOS,
        "strategy": "iterative multi-label stratification (iterstrat), 70/15/15",
        "population": {
            "records": len(man),
            "duplicate_records_dropped": len(drop),
            "distinct_pictures": len(man) - len(drop),
            "clear_excluded": len(clear),
            "unmarked_excluded": 5,
            "rows": len(rows),
            "addbacks_included": 0,
        },
        "duplicate_rule": "keep the record with the most boxes; on a tie keep the plain name",
        "duplicate_pairs": sorted(kept_pair_rows, key=lambda r: r["md5"]),
        "excluded_classes": {c: {"name": n, "pictures": p} for c, (n, p) in EXCLUDED.items()},
        "columns": COLUMNS,
        "column_sources": {**LP_MAP, **OBJ_MAP},
        "split_counts": {s: counts[s] for s in ("train", "val", "test")},
        "class_totals": class_totals,
        "files": {
            "split.csv": md5_of(OUT / "split.csv"),
            "labels_17.csv": md5_of(OUT / "labels_17.csv"),
        },
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    print("rows", len(rows))
    print("split", {s: counts[s] for s in ("train", "val", "test")})
    print("shares", {s: round(counts[s] / len(rows) * 100, 2) for s in ("train", "val", "test")})
    for c in COLUMNS:
        print(f"  {c:28s} {class_totals[c]:6d}")
    print("split.csv md5", meta["files"]["split.csv"])
    print("labels_17.csv md5", meta["files"]["labels_17.csv"])


if __name__ == "__main__":
    main()
