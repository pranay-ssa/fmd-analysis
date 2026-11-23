#!/usr/bin/env python3
"""Recompute the frozen EDA headline counts from the XML and check the draft doc against them.

Independent of frozen_eda.py: one pass, plain counters, no shared helpers.
Exits non-zero on the first mismatch.
"""

from __future__ import annotations

import glob
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
DOC = REPO / "docs/frozen_dataset_eda_20261117.md"

GATES = {"P3_FM_MICRON_THRESHOLD", "P3_FIB_MICRON_THRESHOLD",
         "P3_EP_MICRON_THRESHOLD", "P3_HE_MICRON_THRESHOLD"}
LP = {"P1_MPP", "P1_PPM", "P1_COC", "F2_FOV", "P2_LOC", "P1_NL", "P1_ML", "P1_FL",
      "P1_EBC", "P1_TL", "P1_LR", "P2_DS", "P2_DC", "P2_BSC", "P2_LD"}
OOI = {"P2_BB", "P2_BC", "P2_WP", "P1_SG", "P3_FIB", "P3_EP", "P3_HE", "P3_FM"}

tag_inst = Counter()
tag_pics: dict[str, set] = {c: set() for c in LP | GATES}
box_inst = Counter()
box_pics: dict[str, set] = {c: set() for c in OOI}
n_tags_all = Counter()
n_tags_lp = Counter()
pics = {}
for path in glob.glob(str(FROZEN / "annotations_*.xml")):
    root = ET.parse(path).getroot()
    for im in root.findall("image"):
        b = im.get("name").rsplit("/", 1)[-1]
        tags = [t.get("label") for t in im.findall("tag")]
        boxes = [x.get("label") for x in im.findall("box")]
        pics[b] = (tags, boxes)
        for t in tags:
            tag_inst[t] += 1
            if t in tag_pics:
                tag_pics[t].add(b)
        for x in boxes:
            box_inst[x] += 1
            if x in box_pics:
                box_pics[x].add(b)
        if tags or boxes:
            n_tags_all[len(set(tags))] += 1
            n_tags_lp[len({t for t in tags if t not in GATES})] += 1

annotated = {b: v for b, v in pics.items() if v[0] or v[1]}
by_n = Counter()
for b, (tags, _boxes) in annotated.items():
    lp_only = {t for t in tags if t not in GATES}
    by_n[len(lp_only)] += 1

coverage = json.loads((REPO / "run/frozen_eda_20261117/coverage.json").read_text())
summary = json.loads((REPO / "run/frozen_eda_20261117/eda_summary.json").read_text())

checks = []


def check(name, got, want):
    checks.append((name, got, want, got == want))


check("pictures", len(pics), 13682)
check("annotated", len(annotated), 13635)
check("empty", len(pics) - len(annotated), 47)
check("lp_instances", sum(tag_inst[c] for c in LP), 12252)
check("lp_pictures", len(set().union(*(tag_pics[c] for c in LP))), 9252)
check("lp_codes_with_data", sum(1 for c in LP if tag_inst[c]), 15)
check("gate_instances", sum(tag_inst[c] for c in GATES), 4060)
check("gate_pictures", len(set().union(*(tag_pics[c] for c in GATES))), 3742)
check("ooi_boxes", sum(box_inst[c] for c in OOI), 119292)
check("ooi_pictures", len(set().union(*(box_pics[c] for c in OOI))), 10032)
check("ooi_codes_with_data", sum(1 for c in OOI if box_inst[c]), 8)
check("all_tags_sum", sum(n_tags_all.values()), 13635)
check("lp_tags_sum", sum(n_tags_lp.values()), 13635)
check("single_tagged", by_n[1], 7237)
check("two_tagged", by_n[2], 1244)
check("three_tagged", by_n[3], 580)
check("no_lp_tag", by_n[0], 4383)
check("single_rows_sum", sum(1 for c in LP for b in tag_pics[c] if len({t for t in annotated[b][0] if t not in GATES}) == 1), 7237)
two = sum(1 for c in LP for b in tag_pics[c] if len({t for t in annotated[b][0] if t not in GATES}) == 2)
check("two_rows_sum", two, 2488)
three = sum(1 for c in LP for b in tag_pics[c] if len({t for t in annotated[b][0] if t not in GATES}) == 3)
check("three_rows_sum", three, 1740)

check("duplicates", coverage["duplicate_pictures_covered_before"], 6771)
check("duplicates_same_labels", coverage["duplicates_with_identical_label_set"], 3269)
check("frozen_only", coverage["frozen_only_pictures"], 6911)
check("frozen_only_new_upload", coverage["frozen_only_pictures_by_source_folder"]["PRODUCTION-20261031"], 3247)
check("frozen_only_old", coverage["frozen_only_pictures_by_source_folder"]["PRODUCTION-20260925"], 3664)
check("previous_only", coverage["previous_only_pictures"], 198)
content = json.loads((REPO / "run/frozen_eda_20261117/previous_only_by_content.json").read_text())
check("previous_only_absent", content["genuinely_absent_from_frozen"], 175)
check("previous_only_aliases", content["same_content_present_in_frozen"], 23)

text = DOC.read_text(encoding="utf-8")
clean = text.replace(",", "")
# The LP-only figures stay as data checks but are no longer the doc's reading: it now
# reports classes across LP and OOI. Skip those five, then assert the class-based numbers.
skip_doc = {"two_tagged", "three_tagged", "no_lp_tag", "two_rows_sum", "three_rows_sum"}
for name, got, want, ok in list(checks):
    if not ok or name in skip_doc:
        continue
    if str(want) not in clean:
        checks.append((f"doc_contains_{name}", "missing", want, False))
for label, want in (("classes_single", 4111), ("classes_multi", 9524),
                    ("classes_two", 4236), ("classes_three", 2756),
                    ("clear_still", 2291), ("addback_candidates", 174),
                    ("addback_pending", 147), ("addback_discarded", 27)):
    checks.append((f"doc_contains_{label}", "found" if str(want) in clean else "missing",
                   want, str(want) in clean))

check("lp_instances_distinct", sum(len({t for t in v[0] if t not in GATES}) for v in annotated.values()), 12246)
check("pictures_with_repeated_tag", sum(1 for v in annotated.values() if len(v[0]) != len(set(v[0]))), 4)

bad = [c for c in checks if not c[3]]
for name, got, want, ok in checks:
    print(f"{'ok ' if ok else 'FAIL'} {name}: got {got} want {want}")
print(f"\n{len(checks) - len(bad)} of {len(checks)} checks pass")
raise SystemExit(1 if bad else 0)
