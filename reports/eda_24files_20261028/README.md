---
title: 24-file EDA workbooks, what they are and how they were checked
date: 2026-10-28
type: result
status: active
where: reports/eda_24files_20261028/README.md
---

# 24-file EDA workbooks

Two review workbooks built from the client's re-export of 2026-10-26 (24 files: 7 revised,
17 new). They answer different questions and are read together.

| File | Population | Sheets |
|---|---|---|
| `FMD_EDA_24Files_20261028.xlsx` | the 24 files only: 3,597 entries, 3,594 pictures, 3,592 with marks | Read me, Summary, Lens Presentation 7-17-24, OOI tags 7-17-24 (with the tags-per-picture distribution), Changes in the 7 revised files (133 rows), Changes in the 17 new files (71 rows), Reason summary, Definitions |
| `FMD_EDA_Record_20261028.xlsx` | the merged record: 5,500 marked + 2,117 Clear = 7,617 | Read me, Summary, Before and after, Lens Presentation, OOI tags, Definitions |

## Vocabulary

The two label tiers are named as the review asked, and every row carries the guide code:

- **Lens Presentation**: a whole-picture tag, one per picture. 15 classes in the guide.
- **OOI tags**: objects of interest, marked with a box; one picture can carry many. 8 classes
  in the guide.
- **Legacy**: outside the guide. HEMA Obstruction (P2_HMO, a whole-picture tag), Bubble On 123
  and Bubble On Edge (older library boxes). Shown grey and marked "Legacy" in the record
  workbook; they do not occur in the 24-file export itself.
- Classes with no annotated pictures are listed at 0 so the guide's 15 and 8 hold: Edge
  Bottle-Capped (P1_EBC), Torn Lens (P1_TL), Lens Rupture (P1_LR), Surface Groove (P1_SG).
- Clear is a negative class, not a guide class, and is labelled "Negative".

## What the numbers say

- The 7 revised files changed 133 pictures: 118 folded into Bubble, 11 debris moves, 2 other
  relabels, 2 box moves (box-level diff against the archived copies).
- The 17 new files add 719 pictures to the record and 2,403 class labels, and remove 70 label
  instances: 21 are naming or fold artifacts, 49 real relabels (Multiple Lens 16, Lens Off
  Center to Low Dose 11, Dirty Strobe to Dirty Camera 11, and singles).
- OOI analysis of the 24 files: **2,089 pictures carry at least one OOI tag; 36,098 tags in
  all.** Distribution by tags per picture: 100 pictures with 1, 114 with 2-3, 405 with 4-9,
  812 with 10-19, 658 with 20 or more. Bubble dominates: 2,066 pictures, 27,921 tags, median
  11 per picture, up to 126 on one picture. Foreign Matter next at 797 pictures and 2,553
  tags; Bubble Cluster 1,111 / 3,308; Fiber 391 / 738; Wet Package 289 / 1,271; HEMA 151 /
  157; Extraneous Polymer 137 / 150.
- The merged record moves the big classes: Bubble 862 -> 2,171, Bubble Cluster 427 -> 1,132,
  Foreign Matter 326 -> 834 (flag 166 -> 454), Fiber 179 -> 405 (137 -> 362), HEMA 101 -> 157,
  Low Dose 215 -> 677, Multiple Lens 1,439 -> 1,426. HEMA Obstruction tag 86 -> 36 (production
  files own those pictures and carry HEMA boxes instead).

## Rules applied

- The frozen priority order: the newest production export owns every picture it mentions
  outright; no per-family exceptions. A picture's label set comes from one file only.
- Every annotated picture counts, whether or not it carries a size flag. The flag is a subset
  of its class and is shown as "of which flagged".
- Clear is the Clear-folder pictures with no mark.
- No 0-label drop and no gate-based drop in the EDA.

## Checks

- `experiments/multilabel_edge/ooi_stats.py` computes the OOI tables and the tags-per-picture
  distribution, and checks them against the class table and against itself (the buckets must
  sum to the distinct pictures).
- `experiments/multilabel_edge/build_eda_24files.py` builds both workbooks from the CSVs in
  `run/eda_batch24_20261028/`; nothing is typed in by hand.
- `experiments/multilabel_edge/verify_eda_24files.py` recomputes every table from the
  annotation (XML files and resolved label sets), compares by header name, checks the 15 and 8
  guide rows and the zero rows, and ends with a tampered-cell proof. Last run: workbook 1 OK,
  workbook 2 OK, both tampers CAUGHT.
- The raw-XML cross-check found three pictures listed twice in the export (name with and
  without a score suffix). One pair is identical, two differ by 1 and 7 marks; the record
  counts one annotation per picture. The difference is in the Definitions sheet.

## Rebuild

```
.venv/Scripts/python.exe experiments/multilabel_edge/ooi_stats.py
.venv/Scripts/python.exe experiments/multilabel_edge/build_eda_24files.py
.venv/Scripts/python.exe experiments/multilabel_edge/verify_eda_24files.py
```

The number artifacts (`population.csv`, `class_table.csv`, `lp_table.csv`, `ooi_table.csv`,
`ooi_distribution.csv`, `revised133.csv`, `relabel70.csv`, `record_before_after.csv`,
`cumulative_population.csv`) are in `run/eda_batch24_20261028/`. The merged annotation of
record is `run/eda_full_24files_20261028/resolved_labels.csv`.
