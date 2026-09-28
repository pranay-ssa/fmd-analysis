#!/usr/bin/env python3
"""Build the notebook that shows the 128 Clear images that also carry a defect class.

The lead reads in notebooks, so the list ships as one as well as a csv and a workbook. Cells use the
standard library only, so the notebook runs wherever she opens it.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "notebooks", "Clear_128_List_20260922.ipynb")

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip().splitlines(keepends=True)}
code = lambda s: {"cell_type": "code", "execution_count": None, "metadata": {},
                  "outputs": [], "source": s.strip().splitlines(keepends=True)}

cells = [
    md("""
# The 128 Clear images that also carry a defect class

**2026-09-22.** The list behind the number. One row per **picture**, and a picture means one physical
inspection frame, identified by its content hash. The same frame is filed in more than one folder, so a
picture appears once here even when several copies of it sit on disk: the 128 pictures stand behind 172
files.

| | Pictures |
|---|---|
| Clear images in total | 2,333 |
| Clear images that also carry a defect class | **128** |
| Clear images with no other label | 2,205 |

| Defect class the Clear image also carries | Pictures |
|---|---|
| Bubble | 37 |
| Wet Package | 34 |
| Dirty Strobe | 16 |
| Bubble Irregular | 16 |
| Bubble Cluster | 15 |
| Dirty Camera | 10 |



The list itself is in `run/clear_tag/20260922/clear_with_defect_128.csv`, and as a workbook beside it.
The cell below reads the csv and prints the whole list.
"""),
    code("""
import csv, os

PATH = 'run/clear_tag/20260922/clear_with_defect_128.csv'
rows = list(csv.DictReader(open(PATH, encoding='utf-8-sig')))
print(len(rows), 'pictures\\n')

print('{0:>3}  {1:<18} {2:<48} {3}'.format('no', 'defect class', 'file in the Clear folder', 'file name'))
for r in rows:
    print('{0:>3}  {1:<18} {2:<48} {3}'.format(
        r['n'], r['defect_class'], r['file_in_clear_folder'], r['file_name_relation']))
"""),
    md("""
## Three things the list adds to the published number

**1. 172 defect folder rows stand behind the 128 pictures.** 44 of the pictures are filed under the
defect label more than once, so counting files instead of pictures inflates this set.

**2. 16 of the 128 have a second copy inside the same class folder**, under a camera style name
instead of the short name. Same picture, same class folder, two file names.

**3. 28 pictures sit in three folders once the Clear copy is counted**, but only **2** of those sit in
three folders under three different labels. The other 26 are filed as Clear and then under the same
defect class in both the categorical folder and the older library.
"""),
    code("""
from collections import Counter

print('what stands behind the defect label:\\n')
for what, count in Counter(r['what_the_copies_are'] for r in rows).most_common():
    print('  {0:<64} {1:>3}'.format(what, count))

print('\\nthe pictures carrying more than one copy:\\n')
for r in rows:
    if r['copies_under_the_defect_label'] != '1':
        print('  {0:>3}  {1:<6} {2:<18} {3}'.format(
            r['n'], r['line'], r['defect_class'], r['file_in_clear_folder']))
        if r['file_under_defect_class'] != r['file_in_clear_folder']:
            print('        other copy: {0}'.format(r['file_under_defect_class']))
"""),
    md("""
## What the list does not settle

Whether Clear becomes a class of its own. That is a client decision, and the case for and against sits
in `docs/clear_tag_analysis_20260916.md`. This notebook answers which pictures are involved and where
each of them sits.

Every figure published on 2026-09-16 reproduces from the list: 2,333 Clear pictures, 128 of them also
carrying a defect class, 2,205 with no other label, the six class counts, 123 with the same file name
in both folders and 5 differing by two appended score fields, and 2 pictures sitting in three folders
under three different labels.
"""),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(nb, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print("wrote", os.path.relpath(OUT, REPO), "cells:", len(cells))
