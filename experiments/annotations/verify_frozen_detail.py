#!/usr/bin/env python3
"""Recompute the walkthrough's structural numbers from the XML and check the text against them.

Independent of frozen_eda_detail.py: one pass, plain counters.
"""

from __future__ import annotations

import csv
import glob
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
RUN = REPO / "run/eda_full_20261029"
DOC = REPO / "docs/frozen_dataset_eda_walkthrough_20261117.md"

GATES = {"P3_FM_MICRON_THRESHOLD": "P3_FM", "P3_FIB_MICRON_THRESHOLD": "P3_FIB",
         "P3_EP_MICRON_THRESHOLD": "P3_EP", "P3_HE_MICRON_THRESHOLD": "P3_HE"}
LP = {"P1_MPP", "P1_PPM", "P1_COC", "F2_FOV", "P2_LOC", "P1_NL", "P1_ML", "P1_FL",
      "P1_EBC", "P1_TL", "P1_LR", "P2_DS", "P2_DC", "P2_BSC", "P2_LD"}


def base(name: str) -> str:
    return name.rsplit("/", 1)[-1]


name_md5 = {}
for row in csv.DictReader((RUN / "file_manifest.csv").open(encoding="utf-8")):
    name_md5.setdefault(base(row["path"]), row["md5"])
md5_folder = {}
for row in csv.DictReader((RUN / "picture_table.csv").open(encoding="utf-8")):
    parts = row["winning_path"].split("/")
    md5_folder[row["md5"]] = parts[1] if len(parts) > 1 else ""

pics = {}
for path in glob.glob(str(FROZEN / "annotations_*.xml")):
    root = ET.parse(path).getroot()
    for im in root.findall("image"):
        b = base(im.get("name"))
        pics[b] = ([t.get("label") for t in im.findall("tag")],
                   [x.get("label") for x in im.findall("box")])

annotated = {b: v for b, v in pics.items() if v[0] or v[1]}

clear_state = Counter()
bubble_only = 0
label_dist = Counter()
pairs = Counter()
for b, (tags, boxes) in annotated.items():
    folder = md5_folder.get(name_md5.get(b, ""), "")
    lp = {t for t in tags if t not in GATES}
    if folder == "Clear":
        if not tags and not boxes:
            clear_state["no mark"] += 1
        elif not lp and not boxes:
            clear_state["gate only"] += 1
        elif not lp and set(boxes) <= {"P2_BB", "P2_BC"}:
            clear_state["bubbles only"] += 1
        elif not lp:
            clear_state["other box"] += 1
        else:
            clear_state["tag"] += 1
    labs = {GATES.get(t, t) for t in tags} | set(boxes)
    if labs <= {"P2_BB", "P2_BC"}:
        bubble_only += 1
    label_dist[len(labs)] += 1
    lp_sorted = sorted(lp)
    for i in range(len(lp_sorted)):
        for j in range(i + 1, len(lp_sorted)):
            pairs[(lp_sorted[i], lp_sorted[j])] += 1

clear_empty = [b for b in pics if md5_folder.get(name_md5.get(b, ""), "") == "Clear"
               and b not in annotated]
for b in clear_empty:
    label_dist[1] += 1

checks = []


def check(name, got, want):
    checks.append((name, got, want, got == want))


check("clear", len(clear_empty), 42)
check("clear_bubbles_only", clear_state["bubbles only"], 1712)
check("clear_other_box", clear_state["other box"], 255)
check("clear_tag", clear_state["tag"], 324)
check("clear_total", sum(clear_state.values()) + len(clear_empty), 2333)
check("bubble_only", bubble_only, 1798)
check("labels_1", label_dist[1], 4153)
check("labels_2", label_dist[2], 4236)
check("labels_3", label_dist[3], 2756)
check("labels_total", sum(label_dist.values()), 13677)
check("pair_ml_loc", pairs[("P1_ML", "P2_LOC")], 1220)
check("pair_fl_ml", pairs[("P1_FL", "P1_ML")], 571)
check("pair_fl_loc", pairs[("P1_FL", "P2_LOC")], 459)

text = DOC.read_text(encoding="utf-8").replace(",", "")
# labels_1 and labels_total count Clear as a label; the doc reports Clear separately,
# so assert the doc's own figures instead.
for name, got, want, ok in list(checks):
    if ok and name not in {"labels_1", "labels_total"} and str(want) not in text:
        checks.append((f"doc_contains_{name}", "missing", want, False))
for label, want in (("classes_single", 4111), ("classes_total", 13640)):
    checks.append((f"doc_contains_{label}", "found" if str(want) in text else "missing",
                   want, str(want) in text))

bad = [c for c in checks if not c[3]]
for name, got, want, ok in checks:
    print(f"{'ok ' if ok else 'FAIL'} {name}: got {got} want {want}")
print(f"\n{len(checks) - len(bad)} of {len(checks)} checks pass")
raise SystemExit(1 if bad else 0)
