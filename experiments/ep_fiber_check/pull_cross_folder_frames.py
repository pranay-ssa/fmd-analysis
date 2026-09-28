#!/usr/bin/env python3
"""Write the list of frames to pull for the cross-folder two-class pictures, and the boxes to draw.

Box names in the annotation file sometimes drop the two trailing score fields a folder name carries,
so the lookup tries the name as written and then the stripped form.
"""
import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(r"D:\fmd-analysis")
SPLIT = REPO / "run/multilabel_split_20260921/split.csv"
DETAIL = REPO / "run/multilabel_eda/20260921/3_multi_label_detail.csv"
XML = REPO / "data/annotations.xml"
OUT = Path(r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch")
SCORE_TAIL = re.compile(r"(_\d+\.\d+)+$")

box_of, have = {}, set()
for im in ET.parse(XML).getroot().iter("image"):
    n = im.get("name").split("/")[-1]
    have.add(n)
    box_of[n] = [(b.get("label"), float(b.get("xtl")), float(b.get("ytl")),
                  float(b.get("xbr")), float(b.get("ybr"))) for b in im.findall("box")]


def strip_scores(name):
    """Drop the two trailing score fields a folder name carries, keeping the extension."""
    stem, dot, ext = name.rpartition(".")
    return SCORE_TAIL.sub("", stem) + dot + ext


def find_box(name):
    for cand in (name, strip_scores(name)):
        if cand in have:
            return cand, box_of[cand]
    return None, []


where = {r["file_name"]: r["where"] for r in csv.DictReader(open(DETAIL, encoding="utf-8"))}
rows = [r for r in csv.DictReader(open(SPLIT, encoding="utf-8")) if where.get(r["file_name"], "")]

TWO_CLASS = {"Bubble|Fiber", "Bubble Irregular|Foreign Matter", "Bubble|Extraneous Polymer",
             "Bubble|Foreign Matter", "Extraneous Polymer|Foreign Matter", "Fiber|Foreign Matter",
             "Foreign Matter|Wet Package"}
lines, report = [], []
for r in rows:
    labs = r["folder_labels"].split("|")
    if "|".join(sorted(labs)) not in {"|".join(sorted(p.split("|"))) for p in TWO_CLASS}:
        continue
    name = r["file_name"]
    matched, bs = find_box(name)
    older = where[name].split(";")[0].strip()
    newer = where[name].split(";")[1].strip() if ";" in where[name] else ""
    lines.append("/data/FMD_Data_26082026/fmd_temp_images/%s/%s" % (older, name))
    report.append({"file_name": name, "boxed_label": r["box_label"], "boxes": r["boxes"],
                   "older_library_folder": older, "newer_folder": newer,
                   "annotation_name_matched": matched or "NO MATCH",
                   "box_coords": "; ".join("%s %.0f %.0f %.0f %.0f" % b for b in bs)})

(OUT / "pull_list.txt").write_text("\n".join(lines) + "\n")
with (OUT / "pull_report.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(report[0]))
    w.writeheader()
    w.writerows(report)

print("frames to pull:", len(lines))
for r in report:
    print("  %-46s boxed=%-18s boxes=%-3s older=%s" % (r["file_name"][:44], r["boxed_label"][:16],
                                                       r["boxes"], r["older_library_folder"]))
    if r["annotation_name_matched"] == "NO MATCH":
        print("        warning: no box row found for this name")
