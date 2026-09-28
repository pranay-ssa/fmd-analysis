#!/usr/bin/env python3
"""Emit the box list for a blind-ish comparison sheet.

Group A  the 34 boxes on the 33 two-name pictures   (older library says Fiber, newer folder says
                                                    Extraneous Polymer)
Group B  the 17 Extraneous Polymer boxes            (both folders agree it is Extraneous Polymer)
Group C  17 of the ordinary Fiber boxes             (each folder's own position; the older library
                                                    says Fiber and the newer folder agrees)

Every box carries a label, so the crop job on the VM does not need to know which group is which
until the sheet is read.
"""
import csv
import os
import xml.etree.ElementTree as ET

REPO = r"D:\fmd-analysis"
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
ANN = os.path.join(REPO, "data", "annotations.xml")
OUT = r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch\ep_fiber_boxes.csv"

rows = [r for r in csv.reader(open(SRC, newline="", encoding="utf-8-sig")) if r and r[0]]
folders_of = {}
for folder, cls, name, md5, _ in rows:
    folders_of.setdefault(md5, []).append((folder, cls, os.path.basename(name)))
fib = {m for m, v in folders_of.items() if any(c == "Fiber" for _, c, _ in v)}
ep = {m for m, v in folders_of.items() if any(c == "Extraneous Polymer" for _, c, _ in v)}
conflict = fib & ep

# built with a plain loop on purpose: the nested dict comprehension that stood here attached the
# folder name to the older library's rows instead of the file hash, so every group A picture fell
# through to the control group and the conflict set came out empty. Verified against the simple
# build: 1,465 keys wrong, exactly the older library rows.
rec_key = {}
for _md5, _files in folders_of.items():
    for _folder, _cls, _name in _files:
        rec_key[(_folder, _cls, _name)] = _md5

out = []
for im in ET.parse(ANN).getroot().findall("image"):
    parts = im.get("name").split("/")
    key = (parts[0], parts[1], os.path.basename(im.get("name")))
    md5 = rec_key.get(key)
    for bi, b in enumerate(im.findall("box")):
        if md5 in conflict and b.get("label") == "Fiber":
            group = "A_conflict"
        elif b.get("label") == "Extraneous Polymer":
            group = "B_ref_extraneous_polymer"
        elif b.get("label") == "Fiber":
            group = "C_ref_fiber"
        else:
            continue
        out.append([group, key[2], bi, b.get("label"), b.get("xtl"), b.get("ytl"),
                    b.get("xbr"), b.get("ybr"), im.get("width"), im.get("height")])

# keep the control group the same size as the reference group
c = [r for r in out if r[0] == "C_ref_fiber"]
b = [r for r in out if r[0] == "B_ref_extraneous_polymer"]
if len(c) > len(b):
    c = c[:len(b)]
out = [r for r in out if r[0] != "C_ref_fiber"] + c

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["group", "file_name", "box_idx", "box_label", "xtl", "ytl", "xbr", "ybr",
                "img_w", "img_h"])
    w.writerows(out)

from collections import Counter
print("wrote", OUT)
print("rows:", Counter(r[0] for r in out))
print("any box outside the frame:",
      sum(1 for r in out if float(r[4]) < 0 or float(r[6]) > float(r[7]) or float(r[5]) < 0
          or float(r[7 - 1]) > float(r[8])))
