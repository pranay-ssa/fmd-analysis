#!/usr/bin/env python3
"""List the Clear images that also carry a defect label, one row per picture.

The lead asked for the list behind the published 128 Clear images that also carry a defect class.
Source of truth is the delivered-file table built at download time, one row per delivered file:
folder, class, file name, content hash, bytes.

A picture is counted once, by content hash, because the same picture can be filed in more than one
folder under more than one class. That is the case this list is about, so the list carries how many
copies of the picture stand behind the defect label, and where they sit.

Numbers this script checks itself against, all published on 2026-09-16:
  2,333 Clear pictures in total, 128 of them also carrying a defect class, 2,205 carrying no other label
  37 Bubble, 34 Wet Package, 16 Dirty Strobe, 16 Bubble Irregular, 15 Bubble Cluster, 10 Dirty Camera
  123 of the 128 carry the same file name in both folders, 5 differ by two appended score fields
  two pictures sit in three folders under three labels

Writes:
  run/clear_tag/20260922/clear_with_defect_128.csv     the list
  run/clear_tag/20260922/clear_with_defect_128.xlsx    the same list, plus a summary sheet

Run with the project virtual environment, which holds openpyxl:
  .venv/Scripts/python.exe experiments/clear_tag/list_clear_with_defect.py
"""
from __future__ import annotations

import csv
import os
import re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
OUT = os.path.join(REPO, "run", "clear_tag", "20260922")
os.makedirs(OUT, exist_ok=True)

NOT_A_DEFECT = {"Clear", "duplicates"}


def stem(name: str) -> str:
    return name.rsplit(".", 1)[0]


def strip_scores(name: str) -> str:
    """Drop the appended floating point fields the pipeline adds to a file name."""
    parts = stem(name).split("_")
    while len(parts) > 1 and re.fullmatch(r"[0-9.]+", parts[-1]):
        parts.pop()
    return "_".join(parts)


by_hash = defaultdict(list)
for folder, cls, name, md5, size in csv.reader(open(SRC, encoding="utf-8-sig")):
    by_hash[md5].append({"folder": folder, "cls": cls, "name": name, "bytes": int(size)})

clear_hashes, targets = [], []
for md5, files in by_hash.items():
    classes = {f["cls"] for f in files}
    if "Clear" not in classes:
        continue
    clear_hashes.append(md5)
    if any(f["cls"] not in NOT_A_DEFECT for f in files):
        targets.append(md5)

clear_only = len(clear_hashes) - len(targets)

canon, relation, where, notes = Counter(), Counter(), Counter(), Counter()
records = []
for md5 in targets:
    files = by_hash[md5]
    clear_files = [f for f in files if f["cls"] == "Clear"]
    defects = [f for f in files if f["cls"] not in NOT_A_DEFECT]
    clear_name = clear_files[0]["name"]

    library = [f for f in defects if f["folder"] == "ICube Defects Library"]
    primary = (library or defects)[0]
    canon[primary["cls"]] += 1
    other_names = sorted({f["cls"] for f in defects} - {primary["cls"]})

    folders = {f["folder"] for f in defects}
    classes = {f["cls"] for f in defects}
    names = {f["name"] for f in defects}
    where[len(folders)] += 1

    # how many copies of the picture stand behind the defect label, and where they sit
    if len(defects) == 1:
        note = "one copy"
    elif len(folders) == 1 and len(classes) == 1 and len(names) > 1:
        note = "a second copy in the same class folder, under a camera style name"
    elif len(folders) == 1 and len(classes) == 1:
        note = "the same row repeated in the same class folder"
    elif len(folders) > 1 and len(classes) == 1:
        note = "copies in more than one folder, same class name"
    else:
        note = "copies under more than one class name"
    notes[note] += 1

    if any(f["name"] == clear_name for f in defects):
        rel, defect_name = "same file name in both folders", clear_name
    elif any(strip_scores(f["name"]) == strip_scores(clear_name) for f in defects):
        rel = "differs by two appended score fields"
        defect_name = next(f["name"] for f in defects if strip_scores(f["name"]) == strip_scores(clear_name))
    else:
        rel, defect_name = "differs in name style", defects[0]["name"]
    relation[rel] += 1

    records.append({
        "n": 0,
        "file_in_clear_folder": clear_name,
        "file_under_defect_class": defect_name,
        "file_name_relation": rel,
        "defect_class": primary["cls"],
        "also_labelled": "; ".join(other_names),
        "copies_under_the_defect_label": len(defects),
        "defect_folders_holding_a_copy": len(folders),
        "all_folders_holding_it": len({f["folder"] for f in files}),
        "what_the_copies_are": note,
        "content_hash": md5,
        "bytes": clear_files[0]["bytes"],
    })

records.sort(key=lambda r: r["file_in_clear_folder"])
for i, r in enumerate(records, start=1):
    r["n"] = i

print("Clear pictures:", len(clear_hashes), "| also carrying a defect class:", len(targets),
      "| Clear only:", clear_only)
print("published:      2,333                | 128" + " " * 22 + "| 2,205")
print()
print("class the Clear picture is also labelled with:")
for cls, n in canon.most_common():
    print("   %-24s %3d" % (cls, n))
print("   %-24s %3d" % ("total", sum(canon.values())))
print("published: 37 Bubble, 34 Wet Package, 16 Dirty Strobe, 16 Bubble Irregular, 15 Bubble Cluster, 10 Dirty Camera")
print()
print("file name, Clear copy against defect copy:")
for rel, n in relation.most_common():
    print("   %-40s %3d" % (rel, n))
print("published: 123 same file name, 5 differing by two appended score fields")
print()
print("what stands behind the defect label:")
for note, n in notes.most_common():
    print("   %-62s %3d" % (note, n))
print("   defect folder rows behind the 128 pictures:",
      sum(len([f for f in by_hash[m] if f["cls"] not in NOT_A_DEFECT]) for m in targets))

FIELDS = list(records[0].keys())
csv_path = os.path.join(OUT, "clear_with_defect_128.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(records)
print()
print("wrote", os.path.relpath(csv_path, REPO), len(records), "rows")

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "The 128"
    ws.append([f.replace("_", " ") for f in FIELDS])
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(vertical="top", wrap_text=True)
    for r in records:
        ws.append([r[f] for f in FIELDS])
    widths = {"n": 5, "file_in_clear_folder": 48, "file_under_defect_class": 48,
              "file_name_relation": 30, "defect_class": 18, "also_labelled": 18,
              "copies_under_the_defect_label": 10, "defect_folders_holding_a_copy": 10, "all_folders_holding_it": 10,
              "what_the_copies_are": 60, "content_hash": 34, "bytes": 10}
    for i, f in enumerate(FIELDS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(f, 14)
    ws.freeze_panes = "A2"

    s = wb.create_sheet("Summary")
    s.append(["Clear images that also carry a defect class", len(records)])
    s.append(["Clear images in total", len(clear_hashes)])
    s.append(["Clear images with no other label", clear_only])
    s.append([])
    s.append(["Defect class the Clear image also carries", "Pictures"])
    for cls, n in canon.most_common():
        s.append([cls, n])
    s.append(["Total", sum(canon.values())])
    s.append([])
    s.append(["File name, Clear copy against defect copy", "Pictures"])
    for rel, n in relation.most_common():
        s.append([rel, n])
    s.append([])
    s.append(["What stands behind the defect label", "Pictures"])
    for note, n in notes.most_common():
        s.append([note, n])
    s.append([])
    s.append(["Pictures whose copies sit in one defect folder", where.get(1, 0)])
    s.append(["Pictures whose copies sit in two defect folders", where.get(2, 0)])
    s.append(["Pictures sitting in three folders in total, counting the Clear copy",
              sum(1 for r in records if r["all_folders_holding_it"] == 3)])
    s.append(["Pictures sitting in three folders under three different labels",
              sum(1 for r in records if r["also_labelled"])])
    s.append([])
    s.append(["Source", "delivered-file table, one row per delivered file, counted by content hash"])
    s.append(["Derived by", "experiments/clear_tag/list_clear_with_defect.py"])
    for row in s["A"]:
        if row.value:
            row.font = Font(bold=True)
    s.column_dimensions["A"].width = 62
    s.column_dimensions["B"].width = 66
    xlsx_path = os.path.join(OUT, "clear_with_defect_128.xlsx")
    wb.save(xlsx_path)
    print("wrote", os.path.relpath(xlsx_path, REPO))
except ImportError:
    print("openpyxl not available in this interpreter, csv written only")
