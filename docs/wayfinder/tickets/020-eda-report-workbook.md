---
title: "Ticket 020 - EDA report and workbook, approval gate"
date: 2026-10-21
type: task
status: done
where: docs/wayfinder/tickets/020-eda-report-workbook.md
---

# Ticket 020: EDA report and workbook, approval gate

Deliverables in `reports/multilabel_edge_<date>/`:

1. Workbook with the legend sheet, the change table, per-column prevalence
   (positives, negatives, prevalence baseline), label cardinality and distinct
   label-vector counts, co-occurrence pairs with the subset-column check
   (which column never appears without its superset, plus the reverse count),
   and the multi-label distribution across all usable pictures.
2. Total class count and usable-picture count under the frozen frame, with
   the drop-rule and flip-set deltas stated in the same sentence as each
   headline.
3. Discrepancy notes: Bubble On 123 / Bubble On Edge kept despite Draft 2
   deprecation; HEMA Obstruction kept despite Draft 2 removal; the 75
   strict-drop pictures; the P3_HE production reading.
4. Report prose in simple English, no local paths, no em dashes.

GATE: the user approves the report and workbook before ticket 021 builds any
split. Questions surfaced by the numbers come back to the user, never resolved
by assumption.
