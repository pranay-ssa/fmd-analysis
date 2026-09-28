#!/usr/bin/env python3
"""Resolve the real file names of the nine frames on the box, then list them for copying.

The folder record carries two appended score fields that the file on disk does not have, and one
frame is filed under a longer pallet-named variant, so each name is tried as written, then without
the score fields, then by its date, time and line prefix with a uniqueness check.
"""
import csv
import re
from pathlib import Path

ROOT = Path("/data/FMD_Data_26082026/fmd_temp_images")
SCORE_TAIL = re.compile(r"(_\d+\.\d+)+$")
ROWS = Path("/tmp/pull_report.csv")


def strip_scores(name):
    stem, dot, ext = name[:-4], ".", name[-4:] if name.lower().endswith(".bmp") else ""
    if not ext:
        stem, dot, ext = name, "", ""
    return SCORE_TAIL.sub("", stem) + dot + ext


resolved, missing = [], []
for r in csv.DictReader(open(ROWS, encoding="utf-8")):
    name = r["file_name"]
    folder = ROOT / r["older_library_folder"]
    found = None
    for cand in (name, strip_scores(name)):
        p = folder / cand
        if p.exists():
            found = p
            break
    if found is None:
        prefix = name[:19]
        hits = sorted(folder.glob(prefix + "*"))
        if len(hits) == 1:
            found = hits[0]
        elif hits:
            missing.append("%s: %d candidates %s" % (name, len(hits), [h.name for h in hits]))
            continue
    if found is None:
        missing.append("%s: nothing in %s" % (name, folder))
        continue
    resolved.append((name, r["older_library_folder"], str(found), found.stat().st_size))

Path("/tmp/resolved.txt").write_text("\n".join(p for _, _, p, _ in resolved) + "\n")
print("resolved %d of %d" % (len(resolved), len(resolved) + len(missing)))
for rec, folder, path, size in resolved:
    print("   %-6.1f MB  %s" % (size / 1e6, path.replace(str(ROOT) + "/", "")))
for m in missing:
    print("   PROBLEM:", m)
