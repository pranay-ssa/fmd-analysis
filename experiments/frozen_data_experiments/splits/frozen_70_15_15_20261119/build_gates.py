#!/usr/bin/env python3
"""Add the four size-flag columns to the frozen split as an auxiliary table.

The model has 17 outputs. The four gate flags are not model columns; they ride
along so the run can save them in predictions.npz and the results can separate
flagged from unflagged pictures without another pass over the store.

Reads labels_17.csv and the store tags, writes gates_4.csv, updates meta.json.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
STORE = ROOT / "run/frozen_eda_20261117/store"
GATES = {
    "gate_foreign_matter": "P3_FM_MICRON_THRESHOLD",
    "gate_fiber": "P3_FIB_MICRON_THRESHOLD",
    "gate_extraneous_polymer": "P3_EP_MICRON_THRESHOLD",
    "gate_hema": "P3_HE_MICRON_THRESHOLD",
}


def md5_of(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def main():
    tags = list(csv.DictReader(open(STORE / "labels/tags.csv", encoding="utf-8-sig")))
    gate_of = defaultdict(set)
    for t in tags:
        if t["kind"] == "gate":
            gate_of[t["basename"]].add(t["code"])

    rows = list(csv.DictReader(open(HERE / "labels_17.csv", encoding="utf-8-sig")))
    totals = Counter()
    out = []
    for r in rows:
        values = [1 if code in gate_of.get(r["image_path"], set()) else 0
                  for code in GATES.values()]
        for name, v in zip(GATES, values):
            totals[name] += v
        out.append([r["md5"], r["image_path"]] + values)

    with open(HERE / "gates_4.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["md5", "image_path"] + list(GATES))
        w.writerows(out)

    meta = json.loads((HERE / "meta.json").read_text(encoding="utf-8"))
    meta["aux_columns"] = list(GATES)
    meta["gate_sources"] = {k: v for k, v in GATES.items()}
    meta["gate_totals"] = {k: totals[k] for k in GATES}
    meta.setdefault("files", {})["gates_4.csv"] = md5_of(HERE / "gates_4.csv")
    (HERE / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    print("rows", len(out))
    for k in GATES:
        print(f"  {k:28s} {totals[k]}")
    print("gates_4.csv md5", meta["files"]["gates_4.csv"])


if __name__ == "__main__":
    main()
