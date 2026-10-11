---
title: "Ticket 006: result record and workbook for the lead"
date: 2026-10-06
type: experiment
status: active
where: docs/wayfinder/tickets/006-result-record-and-workbook.md
---

# 006: Result record and workbook

Type: task. Map: [Task 1 bubble merge](../task1_bubble_merge_map.md).
Blocked by: [005 Merged versus separate readout](005-merged-vs-separate-readout.md).

## Question

Turn the four runs into the two artifacts this task owes: a repo record that
future sessions can trust, and a workbook/message the lead can read without
opening the repo.

## Checklist

1. Result record in `reports/bubble_merge/`: what ran, the recipe, the four
   headline rows, the Bubble attribution, the noise-band caveat, and the
   verification that each number came from a mirrored artifact.
2. Workbook with one sheet per reading (separate, merged) plus a comparison
   sheet, built from the mirrored metrics, never typed by hand; the count
   table from ticket 002 rides as its own sheet so the email's table and the
   result table cannot drift apart.
3. A short message for the lead carrying the numbers: merged versus separate
   for both architectures, the class responsible if any, and the one-tag rule
   as verified (with the correction that no earlier run deducted the 178).
   Numbers are presented the moment they are read; verification happens in
   parallel and a correction follows if it contradicts.
4. Registry rows moved to done with results and verification notes;
   `HANDOFF.md` rewritten as state only; `tools/index_docs.py` re-run.
5. Self-contained prose: no cross-section references, no em dashes, no local
   file paths in anything meant to leave the team.

## Done when

The record and workbook exist, every figure reconciles with a mirrored
artifact, the registry and index are updated, and the lead has the numbers.
