---
title: "Ticket 005: merged versus separate readout, with the class responsible"
date: 2026-10-06
type: experiment
status: active
where: docs/wayfinder/tickets/005-merged-vs-separate-readout.md
---

# 005: Merged versus separate readout

Type: task (HITL for the judgement call). Map:
[Task 1 bubble merge](../task1_bubble_merge_map.md).
Blocked by: [004 The four training runs](004-four-training-runs.md).

## Question

Answer the question the client actually asked: does the merged Bubble class
perform better, the same or worse than the four separate classes, and when it
reads worse, which class is responsible?

## Method (fixed before the numbers exist, in `registry.json`)

1. Per architecture, put the merged and separate readings side by side on the
   identical test pictures: overall accuracy, macro F1, and per-class
   precision, recall, F1 and support.
2. Compare the merged Bubble (185 pictures, 55 in test) against the sum of
   the four separate classes (same 185 pictures, same 55 in test), not
   against any other row.
3. Name the class responsible from the confusion cells of both readings:
   which class the merged Bubble pictures are predicted as, and which class's
   pictures are being predicted as Bubble. The dump makes this a table, not
   an impression.
4. Quote every delta beside the single-run band, and say plainly when a delta
   is inside it.
5. Report both architectures even if one is unflattering.

## Done when

A table exists with both readings for both architectures, the Bubble line has
an attribution naming a specific class (or states that no class movement
explains the delta), and every number traces to a mirrored metrics.json or
confusion.json.
