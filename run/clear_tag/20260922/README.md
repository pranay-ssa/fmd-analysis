---
title: run/clear_tag/20260922 - the list of Clear images that also carry a defect class
date: 2026-09-22
type: result
status: active
where: run/clear_tag/20260922/README.md
---

# The 128 Clear images that also carry a defect class

The lead asked for the list behind the published 128. The list is one row per picture, 128 rows. A
picture is one physical inspection frame, identified by its content hash, so it appears once here even
when several copies of it sit on disk: the 128 pictures stand behind 172 files. Each row carries the
file name in the Clear folder, the file name under the defect class, the class, and how many copies
stand behind that label.

Source of truth: `run/line_eda/20260916/image_md5_records.csv`, one row per delivered file, built at
download time. A picture is counted once by content hash, because the same picture is filed in more
than one folder under more than one class, which is the case this list is about.

## The numbers, and which ones are a re-check

Every figure published on 2026-09-16 reproduces exactly from the list:

| | This list | Published 2026-09-16 |
|---|---|---|
| Clear pictures in total | 2,333 | 2,333 |
| Clear pictures that also carry a defect class | 128 | 128 |
| Clear pictures with no other label | 2,205 | 2,205 |
| Bubble | 37 | 37 |
| Wet Package | 34 | 34 |
| Dirty Strobe | 16 | 16 |
| Bubble Irregular | 16 | 16 |
| Bubble Cluster | 15 | 15 |
| Dirty Camera | 10 | 10 |
| Same file name in both folders | 123 | 123 |
| Differ by two appended score fields | 5 | 5 |
| Three folders under three different labels | 2 | 2 |

## Three things the list adds

- **172 defect folder rows stand behind the 128 pictures.** 44 of the pictures are filed under the
  defect label more than once, so a naive count of files rather than pictures inflates this set.
- **16 of the 128 have a second copy inside the same class folder**, under a camera style name rather
  than the short name, for example `20241101_235953_L24_C2_9893.bmp` beside
  `20241101_235953_L24_PalletGHT1102042028_Cavity2_B0177C5_Fail7_Score(0.98931).bmp`. Both are the
  same picture by content hash. These 16 are why a name comparison alone finds 123 of 128 and not
  fewer: at least one copy of each does carry the identical name.
- **28 pictures sit in three folders once the Clear copy is counted**, but only **2** of them sit in
  three folders under three different labels. The other 26 are filed as Clear, then under the same
  defect class in both the categorical folder and the older library. Both figures are on the summary
  sheet, labelled, so the list cannot be read as contradicting the published note.

## What stands behind the label, in full

| What the copies are | Pictures |
|---|---|
| One copy | 84 |
| Copies in more than one folder, same class name | 26 |
| A second copy in the same class folder, under a camera style name | 16 |
| Copies under more than one class name | 2 |
| **Total** | **128** |



## What the list does not settle

Whether Clear becomes a class of its own. That is a client decision, and the argument for and against
is in `docs/clear_tag_analysis_20260916.md`. This list only answers which pictures are involved and
where each of them sits.

## Files

| File | What it holds |
|---|---|
| `clear_with_defect_128.csv` | the list, 128 rows, for forwarding |
| `clear_with_defect_128.xlsx` | the same list plus a summary sheet, for a reader who prefers a workbook |
| `experiments/clear_tag/list_clear_with_defect.py` | the derivation, with the published numbers printed beside the result as the check |
| `notebooks/Clear_128_List_20260922.ipynb` | the list in a notebook, for reading and for exporting |

## Rebuilding

```bash
.venv/Scripts/python.exe experiments/clear_tag/list_clear_with_defect.py
```

It prints every published figure beside the value it derives, so a difference shows up in the output
rather than in a later comparison.
