#!/usr/bin/env python3
"""Effect of the four duplicate pairs on the label counts.

Three bases, no decision:
  all      all 13,682 records
  one      one record per pair (the current working basis; not a decision)
  exclude  both records of every pair removed

Writes run/frozen_eda_20261118/duplicate_sensitivity.json.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STORE = REPO / "run/frozen_eda_20261117/store"
OUT = REPO / "run/frozen_eda_20261118/duplicate_sensitivity.json"

PAIRS = {
    1: ["20241102_004906_L24_C5_9471.bmp", "20241102_004906_L24_C5_9471_0.6629.bmp"],
    2: ["20241109_174228_L24_C4_9649.bmp", "20241109_174228_L24_C4_9649_0.9824.bmp"],
    3: ["20241110_024940_L24_C13_9997.bmp", "20241110_024940_L24_C13_9997_0.6242.bmp"],
    4: ["20260816_093047_L26_PalletGHF0816135159_Cavity12_B01BJQ6_Fail7_Score(0.989757).bmp",
        "20260816_093047_L26_PalletGHF0816135159_Cavity12_B01BJQ6_Fail7_Score(0.989757)_0.9833_0.5392.bmp"],
}
ONE = {  # current working basis: keep the fuller annotation, tie-break base name
    1: "20241102_004906_L24_C5_9471.bmp",
    2: "20241109_174228_L24_C4_9649.bmp",
    3: "20241110_024940_L24_C13_9997_0.6242.bmp",
    4: "20260816_093047_L26_PalletGHF0816135159_Cavity12_B01BJQ6_Fail7_Score(0.989757)_0.9833_0.5392.bmp",
}

manifest = list(csv.DictReader(open(STORE / "manifest.csv", encoding="utf-8-sig")))
keys = {r["basename"] for r in manifest}
pic = defaultdict(lambda: {"lp": set(), "box": set()})
for t in csv.DictReader(open(STORE / "labels/tags.csv", encoding="utf-8-sig")):
    if t["basename"] in keys and t["kind"] != "gate":
        pic[t["basename"]]["lp"].add(t["code"])
for b in csv.DictReader(open(STORE / "labels/boxes.csv", encoding="utf-8-sig")):
    if b["basename"] in keys:
        pic[b["basename"]]["box"].add(b["code"])

marked_all = {n for n, v in pic.items() if v["lp"] or v["box"]}
clear = {r["basename"] for r in manifest
         if str(r.get("is_clear_source")).lower() in ("1", "true", "yes")} - marked_all

def base(drop: set[str]) -> dict:
    present = keys - drop
    marked = {n for n in present if pic[n]["lp"] or pic[n]["box"]}
    labelled = marked | (clear & present)
    classes = {n: pic[n]["lp"] | pic[n]["box"] for n in labelled}
    dist = Counter(len(classes[n]) for n in labelled)
    lp = {n for n in labelled if pic[n]["lp"]}
    ooi = {n for n in labelled if pic[n]["box"]}
    lp_cls = Counter(c for n in labelled for c in pic[n]["lp"])
    ooi_cls = Counter(c for n in labelled for c in pic[n]["box"])
    return {
        "records": len(present),
        "labelled": len(labelled),
        "marked": len(marked),
        "clear": len(clear & present),
        "unannotated": len(present - labelled),
        "lp_pictures": len(lp),
        "ooi_pictures": len(ooi),
        "both": len(lp & ooi),
        "single": sum(1 for n in labelled if len(classes[n]) == 1),
        "buckets": {str(k): dist.get(k, 0) for k in range(1, 10)},
        "lp_classes": dict(sorted(lp_cls.items())),
        "ooi_classes": dict(sorted(ooi_cls.items())),
        "pair_classes": {str(i): sorted(classes.get(n, set())) for i, names in PAIRS.items() for n in [ONE[i]]},
        "pair_second_classes": {str(i): sorted(classes.get([x for x in names if x != ONE[i]][0], set()))
                                for i, names in PAIRS.items()},
    }

data = {
    "all": base(set()),
    "one": base({n for names in PAIRS.values() for n in names} - set(ONE.values())),
    "exclude": base({n for names in PAIRS.values() for n in names}),
}
data["pairs"] = {str(i): names for i, names in PAIRS.items()}
data["kept"] = {str(i): ONE[i] for i in ONE}
OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps({k: {m: v[m] for m in ("records", "labelled", "lp_pictures", "ooi_pictures", "both", "single")}
                  for k, v in data.items() if k in ("all", "one", "exclude")}, indent=2))
print("buckets all", data["all"]["buckets"])
print("buckets one", data["one"]["buckets"])
print("buckets exclude", data["exclude"]["buckets"])
