#!/usr/bin/env python3
"""Read-only: index every .bmp under the image root -> basename, path.

Writes image_path_manifest.csv (basename,path). Run on the VM.
No files are modified; this only walks the tree and writes one CSV.
"""
import csv
import os
import sys

ROOT = "/data/FMD_Data_26082026/fmd_temp_images"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/amd100-user/image_path_manifest.csv"

# folders we trust as sources of record (updated first, then old library)
PREFERRED = [
    "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
    "ICube Defects Library",
]

rows = {}   # basename -> path (first hit wins, preferred folders scanned first)

def scan(base, tag):
    if not os.path.isdir(base):
        return 0
    n = 0
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if not f.lower().endswith(".bmp"):
                continue
            # skip YOLO dataset copies unless nothing else found later
            if f not in rows:
                rows[f] = os.path.join(dirpath, f)
                n += 1
    return n

total = 0
for sub in PREFERRED:
    n = scan(os.path.join(ROOT, sub), sub)
    total += n
    print("scanned %-45s +%d" % (sub, n))

# anything else under root (other folders) as fallback
n = scan(ROOT, "rest")
total += n
print("scanned (all remaining) +%d" % n)

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["basename", "path"])
    for k in sorted(rows):
        w.writerow([k, rows[k]])
print("WROTE %s  (%d rows)" % (OUT, len(rows)))
