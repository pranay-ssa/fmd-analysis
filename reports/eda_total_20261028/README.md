---
title: Total EDA after the 24-file export, and the split before and after
date: 2026-10-28
type: result
status: active
where: reports/eda_total_20261028/README.md
---

# Total EDA after the 24-file export

One workbook for the whole record after the client's 24-file export, in the shape of the
earlier Draft-2 workbook, plus the training and test split measured before and after the
24 files.

`FMD_EDA_Total_20261028.xlsx` - sheets: Read me, Summary, LP Summary, Tag Combinations,
OOI Summary, Training and Test Split, Reconciliation, Definitions.

## The numbers

- Population: 10,614 pictures examined, 5,500 with at least one mark, 2,117 Clear,
  **7,617 in the analysed set**. 2,332 pictures carry at least one OOI tag, 4,630 at least
  one lens presentation tag.
- OOI: 37,199 tags across the 8 guide classes on 2,332 pictures. Bubble 2,171 pictures /
  28,741 tags (median 11 labels per picture, up to 126); Bubble Cluster 1,132 / 3,419;
  Wet Package 314 / 1,342; Foreign Matter 834 / 2,592 (454 size-flagged); Fiber 405 / 753
  (362); HEMA 157 / 164 (151); Extraneous Polymer 175 / 188 (135); Surface Groove 0.
- Lens presentation: 15 guide classes, 3 with no pictures. Missing Primary Package 1,428,
  Multiple Lens 1,426, Lens Off Center 1,201, Low Dose 677, Dirty Camera 573, Folded Lens
  333, No Lens 326, Cavity Off Center 185, View Obstructed 63, Package Misalignment 33,
  Dirty Strobe 33, Bubble Scatter 5.
- Legacy (outside the guide): HEMA Obstruction (P2_HMO) 36 pictures; Bubble On 123 13;
  Bubble On Edge 14.
- Tag combinations over the 19 guide classes (the size flag is not a label): the exact and
  inclusive pair tables, plus the label-count distribution. The largest exact pair is Lens
  Off Center + Multiple Lens (371); the largest inclusive pair is Bubble + Bubble Cluster
  (1,110). 62 pictures carry 0 class labels - all legacy-only, not Clear.
- Split: 6,659 rows before (70/30 4,653 / 2,006; 80/20 5,327 / 1,332) against **7,470 rows
  after** (70/30 5,235 / 2,235; 80/20 5,989 / 1,481). 279 pictures were outside the split
  before, 147 after. Every class row is in the workbook, both ratios, before and after.

## What the split change means

The 24 files add 719 pictures to the record, but the split grows by 811 rows: the analysed
set grew by 679 pictures and 132 fewer pictures fall outside a split (147 against 279).
Pictures fall outside only when their only marks are legacy classes or an un-gated object,
so the decrease comes from the newer annotation carrying a usable label on more pictures.

The two readings are deliberate and must stay apart: **the EDA counts every picture of a
class**, with the size flag as the "of which size-flagged" subset; **the split keeps the
frozen gate-only positives** for Foreign Matter, Fiber, Extraneous Polymer and HEMA. So the
85 pictures whose only mark is an un-gated object appear in their class in the EDA and are
outside the split; the 62 legacy-only pictures have no guide class at all. 147 pictures are
outside the split, and 62 of them have no class label.

The "after" split is built under the frozen rules of 26 October 2026, not copied from the
earlier split: Draft 2 codes plus Clear, legacy excluded, the four gated classes positive on
the size flag only, iterative stratification, content-md5 groups, no validation split.

## Checks

- `experiments/multilabel_edge/total_eda_stats.py` computes the population, LP, OOI, pair,
  label-count and split tables, and checks every class count against the record workbook.
- `experiments/multilabel_edge/build_split_v7.py` builds the after split (rows, drops,
  crossings, per-class counts) and writes `run/split_20261028_v7/meta.json`.
- `experiments/multilabel_edge/build_eda_total.py` builds the workbook from the CSVs.
- `experiments/multilabel_edge/verify_eda_total.py` recomputes every table from the
  annotation and both split metas, compares cell by cell, and proves a tampered cell is
  caught. Last run: workbook OK, tamper CAUGHT.
- The Reconciliation sheet repeats the record workbook's figures; every row reads Yes.

## Rebuild

```
.venv/Scripts/python.exe experiments/multilabel_edge/build_split_v7.py
.venv/Scripts/python.exe experiments/multilabel_edge/total_eda_stats.py
.venv/Scripts/python.exe experiments/multilabel_edge/build_eda_total.py
.venv/Scripts/python.exe experiments/multilabel_edge/verify_eda_total.py
```

Artifacts: `run/eda_total_20261028/` (population, lp, ooi, combos, label counts, splits,
reconciliation) and `run/split_20261028_v7/` (both split CSVs and meta).
