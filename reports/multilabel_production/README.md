---
title: Multilabel production reports
date: 2026-11-05
type: reference
status: active
where: reports/multilabel_production/README.md
---

# Multilabel production reports

This folder holds the client-safe workbooks and reports for the lens-presentation and object models.

## Current read-out (2026-11-05)

`FMD_MultiLabel_Runs_2026W45.xlsx` is the A/B comparison for the October story. Seven sheets:
Summary, Per-class results, Thresholds, Threshold rule, Routing, Split, Definitions and method. It
reads the frozen 70/15/15 split: 5,239 training, 1,110 validation, 1,121 test pictures.

| Measure | Lens only | Lens + object flag |
|---|---:|---:|
| Lens AUPRC, 8 classes | 0.836 | 0.818 |
| Macro F1 at 0.5 | 0.722 | 0.724 |
| Macro F1 at chosen thresholds | 0.801 | 0.781 |
| Exact match at 0.5 | 0.789 | 0.764 |
| Exact match at chosen thresholds | 0.777 | 0.762 |
| Inference time per picture | 5.76 ms | 5.59 ms |

The workbook carries per-class thresholds, validation and test counts, the four 0.50 defaults, the
object-flag routing table and the split. It is verified against the two run records (429 checks, plus
a tamper proof). Pass/fail numbers are not in it; they are next week's subject.

Sources: `run/multilabel_lp_v8_20261105/a/` (lens only) and
`run/multilabel_lp_v8_20261103/b/` (lens plus flag).

## History

- `ooi_point4_workbook_20261104.xlsx` - point 4 pass/fail workbook; the numbers are in the week-45
  session doc.
- `lp_thresholds_20261103.xlsx` - per-class thresholds from the 3 November lens-plus-flag run.
- `FMD_Split_By_Class_20261030.xlsx` - split counts by class, 30 October.
- `lp_full_results_20261029.xlsx` and `lp_full_report_20261029.html` - 2026-10-29 read-out on the
  24-file annotation and split v7. They are history; do not quote them against the new split.
- The 2026-10-28 files are the record of what was sent; do not update them.

## Rule

Every workbook in this folder is generated from a saved run record and re-checked after it is
written. A number that cannot be traced to a run record does not go in.
