#!/usr/bin/env python3
"""Single, two and three class pictures under the all-class definition.

A class is one distinct LP presentation code or one OOI object class on a picture. The four size
flags do not add a class: a gate only ever appears where its class box already is (checked: zero
gates without their class). Five Bubble boxes are one class, not five.

Emits, under run/frozen_eda_20261117/detail/:
    composition_summary.json
    single_by_class.csv
    two_compositions.csv, two_pairs.csv
    three_compositions.csv, three_triples.csv
    pairs_all.csv
"""

from __future__ import annotations

import csv
import glob
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
RUN = REPO / "run/eda_full_20261029"
OUT = REPO / "run/frozen_eda_20261117/detail"

GATES = {"P3_FM_MICRON_THRESHOLD", "P3_FIB_MICRON_THRESHOLD",
         "P3_EP_MICRON_THRESHOLD", "P3_HE_MICRON_THRESHOLD"}
LP = {"P1_MPP", "P1_PPM", "P1_COC", "F2_FOV", "P2_LOC", "P1_NL", "P1_ML", "P1_FL",
      "P1_EBC", "P1_TL", "P1_LR", "P2_DS", "P2_DC", "P2_BSC", "P2_LD"}
OOI = {"P2_BB", "P2_BC", "P2_WP", "P1_SG", "P3_FIB", "P3_EP", "P3_HE", "P3_FM"}
NAMES = {
    "P1_MPP": "Missing Primary Package", "P1_PPM": "Package Misalignment",
    "P1_COC": "Cavity Off Center", "F2_FOV": "View Obstructed",
    "P2_LOC": "Lens Off Center", "P1_NL": "No Lens",
    "P1_ML": "Multiple Lens", "P1_FL": "Folded Lens",
    "P1_EBC": "Edge Bottle-Capped", "P1_TL": "Torn Lens",
    "P1_LR": "Lens Rupture", "P2_DS": "Dirty Strobe",
    "P2_DC": "Dirty Camera", "P2_BSC": "Bubble Scatter", "P2_LD": "Low Dose",
    "P2_BB": "Bubble", "P2_BC": "Bubble Cluster", "P2_WP": "Wet Package",
    "P1_SG": "Surface Groove", "P3_FIB": "Fiber", "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA", "P3_FM": "Foreign Matter",
}


def base(n: str) -> str:
    return n.rsplit("/", 1)[-1]


def write(name: str, rows: list[dict]) -> None:
    if not rows:
        (OUT / name).write_text("", encoding="utf-8")
        return
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    md5_of = {}
    for row in csv.DictReader((RUN / "file_manifest.csv").open(encoding="utf-8")):
        md5_of.setdefault(base(row["path"]), row["md5"])
    folder_of = {}
    for row in csv.DictReader((RUN / "picture_table.csv").open(encoding="utf-8")):
        parts = row["winning_path"].split("/")
        folder_of[row["md5"]] = parts[1] if len(parts) > 1 else ""

    classes = {}
    for path in glob.glob(str(FROZEN / "annotations_*.xml")):
        for im in ET.parse(path).getroot().findall("image"):
            b = base(im.get("name"))
            tags = [t.get("label") for t in im.findall("tag")]
            boxes = [x.get("label") for x in im.findall("box")]
            classes[b] = set(t for t in tags if t not in GATES) | set(boxes)

    clear_pics = [b for b in classes if not classes[b] and folder_of.get(md5_of.get(b, ""), "") == "Clear"]
    for b in clear_pics:
        classes[b] = {"Clear"}

    n_dist = Counter(len(v) for v in classes.values())
    single = Counter()
    single_by_class = Counter()
    two_comp = Counter()
    two_pairs = Counter()
    three_comp = Counter()
    three_triples = Counter()
    pairs_all = Counter()

    for b, cs in classes.items():
        n = len(cs)
        if n == 1:
            (code,) = tuple(cs)
            if code == "Clear":
                single["clear, no mark"] += 1
            elif code in LP:
                single["one LP tag"] += 1
                single_by_class[code] += 1
            else:
                single["one OOI box class"] += 1
                single_by_class[code] += 1
        elif n == 2:
            lp = sum(1 for c in cs if c in LP)
            ooi = sum(1 for c in cs if c in OOI)
            kind = {(2, 0): "LP + LP", (1, 1): "LP + OOI", (0, 2): "OOI + OOI"}[(lp, ooi)]
            two_comp[kind] += 1
            a, b2 = sorted(cs)
            two_pairs[(a, b2)] += 1
        elif n == 3:
            lp = sum(1 for c in cs if c in LP)
            ooi = sum(1 for c in cs if c in OOI)
            kind = {(3, 0): "3 LP", (2, 1): "2 LP + 1 OOI",
                    (1, 2): "1 LP + 2 OOI", (0, 3): "3 OOI"}[(lp, ooi)]
            three_comp[kind] += 1
            three_triples[tuple(sorted(cs))] += 1
        if n >= 2:
            ordered = sorted(cs)
            for i in range(len(ordered)):
                for j in range(i + 1, len(ordered)):
                    pairs_all[(ordered[i], ordered[j])] += 1

    def kind(c: str) -> str:
        return "LP" if c in LP else ("OOI" if c in OOI else "Clear")

    write("single_by_class.csv",
          [{"class": c, "name": NAMES.get(c, c), "kind": kind(c), "pictures": v}
           for c, v in sorted(single_by_class.items(), key=lambda kv: -kv[1])])
    write("two_compositions.csv", [{"composition": k, "pictures": v}
                                   for k, v in two_comp.most_common()])
    write("two_pairs.csv",
          [{"class_a": a, "name_a": NAMES.get(a, a), "class_b": b,
            "name_b": NAMES.get(b, b), "composition": "%s + %s" % (kind(a), kind(b)),
            "pictures": v} for (a, b), v in two_pairs.most_common()])
    write("three_compositions.csv", [{"composition": k, "pictures": v}
                                     for k, v in three_comp.most_common()])
    write("three_triples.csv",
          [{"triple": ";".join(t), "names": ";".join(NAMES.get(c, c) for c in t), "pictures": v}
           for t, v in three_triples.most_common(40)])
    write("pairs_all.csv",
          [{"class_a": a, "name_a": NAMES.get(a, a), "class_b": b, "name_b": NAMES.get(b, b),
            "composition": "%s + %s" % (kind(a), kind(b)), "pictures": v}
           for (a, b), v in pairs_all.most_common()])

    summary = {
        "pictures": len(classes),
        "classes_per_picture": dict(sorted(n_dist.items())),
        "single": dict(single),
        "single_total": sum(single.values()),
        "single_by_class_total": sum(single_by_class.values()),
        "two": dict(two_comp),
        "two_total": sum(two_comp.values()),
        "three": dict(three_comp),
        "three_total": sum(three_comp.values()),
        "multi_total": sum(two_comp.values()) + sum(three_comp.values())
        + sum(v for k, v in n_dist.items() if k >= 4),
        "pairs_distinct": len(pairs_all),
        "top_pair": pairs_all.most_common(1)[0],
    }
    (OUT / "composition_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
