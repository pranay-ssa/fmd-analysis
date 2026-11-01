---
title: LP run on the 24-file annotation, results folder
date: 2026-10-29
type: reference
status: active
where: reports/multilabel_lp_full_20261029/README.md
---

# LP run on the 24-file annotation (2026-10-29)

This folder holds the read-out of the current experiment: both variants rerun on the
24-file annotation of record and split v7. **These results take priority over the
2026-10-28 run in reports/multilabel/ in every quote, message and meeting.**

## Results in one look

| Measure | 2026-10-28 run | This run |
|---|---|---|
| Variant 1 macro average precision, 8 judgeable classes | 0.783 | **0.851** (bar 0.85, met) |
| Variant 2 macro average precision | 0.764 | **0.817** |
| Object flag fires on OOI pictures | 84.5% | **99.3%** (target 90) |
| Object flag fires on Clear pictures | 0.9% | **0.5%** (limit 5) |
| Train / test pictures (variant 2) | 5,327 / 1,332 | 5,989 / 1,481 |
| Train / test pictures (variant 1) | 4,971 / 1,248 | 5,403 / 1,344 |

Underrepresented classes, average precision old to new: Low Dose 0.77 to 0.92,
Dirty Camera 0.58 to 0.72, Folded Lens 0.27 to 0.49, Lens Off Center 0.75 to 0.82.
Folded Lens remains below its 0.70 target; the fold-plus-multiple-lens overlap is a
real limitation, not only a data shortage.

## Where the evidence lives

- Raw run: `run/multilabel_lp_full_20261029/` (metrics for both variants, log,
  model checkpoints on the training machine).
- Split: `run/split_20261029_v7/`, built from `run/eda_full_20261029/resolved_labels.csv`
  through `run/multilabel_edge_20261029_rev4/label_matrix.csv` under the frozen rules.
- Label tables: `run/multilabel_lp_full_20261029/labels_a.csv` (6,747 rows) and
  `labels_b.csv` (7,470 rows).

## Status of this folder

`lp_full_results_20261029.xlsx` and `lp_full_report_20261029.html` are the current read-out,
rebuilt from this run and verified cell by cell against the metrics (25 checks, including a
tamper proof). The two 2026-10-28 files in this folder are the record of what was already
sent, kept as history and not updated. Prose numbers in them are the old run's.
