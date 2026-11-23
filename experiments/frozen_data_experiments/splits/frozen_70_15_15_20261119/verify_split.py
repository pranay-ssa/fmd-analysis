#!/usr/bin/env python3
"""Verify the frozen split against the store. Exit 0 only when every check passes."""
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
STORE = ROOT / "run/frozen_eda_20261117/store"
META = json.loads((HERE / "meta.json").read_text(encoding="utf-8"))

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
EXCLUDED = {"P1_EBC", "P1_LR", "P1_TL", "P2_BSC", "P2_DS", "P1_SG"}

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


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
    drop = set()
    for names in pairs.values():
        names = sorted(names)
        drop.update(set(names) - {max(names, key=lambda n: (box_count[n], -len(n)))})

    pic = defaultdict(lambda: {"lp": set(), "box": set()})
    for t in tags:
        if t["kind"] == "tag":
            pic[t["basename"]]["lp"].add(t["code"])
    for b in boxes:
        pic[b["basename"]]["box"].add(b["code"])
    clear = {m["basename"] for m in man
             if m["is_clear_source"] == "yes" and m["has_marks"] == "no"}
    marked = {m["basename"] for m in man if m["has_marks"] == "yes"}

    expected = {}
    for m in man:
        n = m["basename"]
        if n in drop or n in clear or n not in marked:
            continue
        labels = []
        for col in COLUMNS:
            code = LP_MAP.get(col) or OBJ_MAP[col]
            labels.append(1 if code in (pic[n]["lp"] if col in LP_MAP else pic[n]["box"]) else 0)
        if any(labels):
            expected[(m["picture_key"], n)] = labels

    split_rows = list(csv.DictReader(open(HERE / "split.csv", encoding="utf-8-sig")))
    label_rows = list(csv.DictReader(open(HERE / "labels_17.csv", encoding="utf-8-sig")))

    check("split.csv has 13,631 rows", len(split_rows) == 13631, str(len(split_rows)))
    check("labels_17.csv has 13,631 rows", len(label_rows) == 13631, str(len(label_rows)))
    keys = [(r["md5"], r["image_path"]) for r in label_rows]
    check("no duplicate picture in the table", len(keys) == len(set(keys)),
          f"{len(keys)} rows, {len(set(keys))} unique")
    check("split and label tables name the same pictures",
          {(r["md5"], r["image_path"]) for r in split_rows} == set(keys))
    check("picture set equals the store recomputation", set(keys) == set(expected),
          f"table {len(set(keys))}, store {len(expected)}")

    split = {i: r["split"] for i, r in enumerate(label_rows)}
    check("every split value is train, val or test",
          set(split.values()) <= {"train", "val", "test"}, str(set(split.values())))
    counts = Counter(split.values())
    check("split counts are 9,537 / 2,049 / 2,045",
          counts == {"train": 9537, "val": 2049, "test": 2045}, str(dict(counts)))
    for part, target in (("train", 0.70), ("val", 0.15), ("test", 0.15)):
        share = counts[part] / len(label_rows)
        check(f"{part} share within 1 point of {target:.0%}",
              abs(share - target) <= 0.01, f"{share*100:.2f}%")

    bad = []
    for r in label_rows:
        key = (r["md5"], r["image_path"])
        got = [int(r[c]) for c in COLUMNS]
        if got != expected[key]:
            bad.append(key)
    check("every label row matches the store", not bad, f"{len(bad)} mismatches")
    check("every row has at least one positive",
          all(any(int(r[c]) for c in COLUMNS) for r in label_rows))

    totals = {c: sum(int(r[c]) for r in label_rows) for c in COLUMNS}
    store_totals = {c: sum(v[j] for v in expected.values()) for j, c in enumerate(COLUMNS)}
    check("class totals match the store", totals == store_totals,
          str({c: (totals[c], store_totals[c]) for c in COLUMNS if totals[c] != store_totals[c]}))
    check("class totals match meta.json", totals == META["class_totals"])

    names = {r["image_path"] for r in label_rows}
    check("Clear is absent", not (names & clear), f"{len(names & clear)} present")
    check("the five unmarked pictures are absent",
          not (names & {m["basename"] for m in man
                        if m["has_marks"] == "no" and m["is_clear_source"] != "yes"}))
    check("the four dropped duplicate records are absent", not (names & drop),
          f"{sorted(names & drop)}")
    for names_ in pairs.values():
        names_ = sorted(names_)
        kept = max(names_, key=lambda n: (box_count[n], -len(n)))
        check(f"the kept duplicate record is present: {kept[:40]}", kept in names)

    check("no excluded class is a column", not (set(COLUMNS) & EXCLUDED))
    check("17 columns", len(COLUMNS) == 17, str(len(COLUMNS)))

    # Auxiliary gate table: four size flags, not model columns.
    gate_cols = ["gate_foreign_matter", "gate_fiber",
                 "gate_extraneous_polymer", "gate_hema"]
    gate_rows = list(csv.DictReader(open(HERE / "gates_4.csv", encoding="utf-8-sig")))
    check("gates_4.csv has 13,631 rows", len(gate_rows) == 13631, str(len(gate_rows)))
    check("gate table names the same pictures",
          {(r["md5"], r["image_path"]) for r in gate_rows} == set(keys))
    gate_of = defaultdict(set)
    for t in tags:
        if t["kind"] == "gate":
            gate_of[t["basename"]].add(t["code"])
    gate_totals = {c: sum(int(r[c]) for r in gate_rows) for c in gate_cols}
    store_gate_totals = {
        c: sum(1 for r in gate_rows
               if ("P3_FM_MICRON_THRESHOLD" if c == "gate_foreign_matter" else
                   "P3_FIB_MICRON_THRESHOLD" if c == "gate_fiber" else
                   "P3_EP_MICRON_THRESHOLD" if c == "gate_extraneous_polymer" else
                   "P3_HE_MICRON_THRESHOLD") in gate_of.get(r["image_path"], set()))
        for c in gate_cols}
    check("gate totals match the store", gate_totals == store_gate_totals,
          str({c: (gate_totals[c], store_gate_totals[c]) for c in gate_cols
               if gate_totals[c] != store_gate_totals[c]}))
    check("gate totals match meta", gate_totals == META["gate_totals"])
    pairs_to_class = {
        "gate_foreign_matter": "class_foreign_matter",
        "gate_fiber": "class_fiber",
        "gate_extraneous_polymer": "class_extraneous_polymer",
        "gate_hema": "class_hema",
    }
    label_of = {(r["md5"], r["image_path"]): r for r in label_rows}
    leaked = [r["image_path"] for r in gate_rows
              if any(int(r[g]) and not int(label_of[(r["md5"], r["image_path"])][c])
                     for g, c in pairs_to_class.items())]
    check("a gate only sits on a picture of its class", not leaked, f"{len(leaked)} leaks")
    check("gates_4.csv md5 matches meta",
          md5_of(HERE / "gates_4.csv") == META["files"]["gates_4.csv"])

    check("split.csv md5 matches meta", md5_of(HERE / "split.csv") == META["files"]["split.csv"])
    check("labels_17.csv md5 matches meta",
          md5_of(HERE / "labels_17.csv") == META["files"]["labels_17.csv"])

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print(f"\n{len(checks) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
