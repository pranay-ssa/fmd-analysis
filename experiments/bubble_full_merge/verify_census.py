#!/usr/bin/env python3
"""Dry-run verification of the bubble_full_merge extractor against the XMLs.

No pixels needed: loads boxes from the three annotation sources, applies the
production-first precedence per image MD5, and checks the merged-frame census
against the resolved-labels figures (docs/decisions/2026-10-15-exp-b-label-frame.md).

Exit 0 only when every gate holds.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from extract_crops import load_boxes, load_md5_index, CODE2CLASS, NAME2CLASS  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
os.chdir(ROOT)

base2md5 = load_md5_index("run/line_eda/20260916/image_md5_records.csv")
print("md5 index: %d basenames" % len(base2md5))

prod = sorted(glob.glob("data/annotations_452*.xml"))
files = prod + ["data/Updated Annotations 20260922.xml", "data/annotations.xml"]
maps = [CODE2CLASS] * len(prod) + [CODE2CLASS, NAME2CLASS]

chosen = {}   # md5 -> (boxes, basename)
census = []
for f, m in zip(files, maps):
    b, ni, nb = load_boxes(f, m)
    won = 0
    for nm, bl in b.items():
        md5 = base2md5.get(nm)
        if md5 and md5 not in chosen:
            chosen[md5] = (bl, nm)
            won += 1
    census.append((os.path.basename(f), ni, nb, len(b), won))

print("%-40s %6s %6s %7s %6s" % ("file", "imgs", "boxes", "clsimg", "won"))
for c in census:
    print("%-40s %6d %6d %7d %6d" % c)

per = {}
pics = set()
nboxes = 0
for md5, (bl, nm) in chosen.items():
    for b in bl:
        per.setdefault(b["class"], [set(), 0])
        per[b["class"]][0].add(md5)
        per[b["class"]][1] += 1
        pics.add(md5)
        nboxes += 1

print("\nmerged class census:")
for k in sorted(per, key=lambda x: -per[x][1]):
    print("  %-20s imgs=%5d crops=%6d" % (k, len(per[k][0]), per[k][1]))
print("UNION images (by md5): %d  boxes: %d" % (len(pics), nboxes))

# ---- gates (registry expected_universe) ----
fail = 0
def gate(name, got, want):
    global fail
    ok = got == want
    if not ok:
        fail += 1
    print("%s %s: got %s want %s" % ("PASS" if ok else "FAIL", name, got, want))

gate("union defect images", len(pics), 1132)
gate("HEMA Fragment boxes", per.get("HEMA Fragment", [set(), 0])[1], 103)
gate("Bubble pictures", len(per["Bubble"][0]), 912)
gate("Wet Package pictures", len(per["Wet Package"][0]), 147)
gate("Foreign Matter pictures", len(per["Foreign Matter"][0]), 332)
gate("Fiber pictures", len(per["Fiber"][0]), 178)
gate("Extraneous Polymer pictures", len(per["Extraneous Polymer"][0]), 144)
gate("HEMA Fragment pictures", len(per["HEMA Fragment"][0]), 101)

# production defect pictures among the union: sum of won counts for rank 0..6
prod_won = sum(c[4] for c in census[:len(prod)])
gate("production images won", prod_won, 757)

print("\n%s" % ("ALL GATES PASS" if fail == 0 else "%d GATE(S) FAILED" % fail))
sys.exit(1 if fail else 0)
