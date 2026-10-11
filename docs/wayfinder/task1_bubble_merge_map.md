---
title: Wayfinder map - Task 1, bubble merge end to end
date: 2026-10-06
type: protocol
status: active
where: docs/wayfinder/task1_bubble_merge_map.md
---

# Map: Task 1, merged Bubble class to a report the lead can read

## Destination

The four bubble classes folded into one Bubble class (and the same data read
with them separate), Clear added as a class, one tag per image, ResNet50 and
MultiScale trained on both readings, and a written result that answers the
client's actual question: is the merged Bubble class doing better, the same,
or worse, and if worse, which class is eating it. The count table and the
two-tag story are part of the destination because the email asked for them.

## Notes

- Domain: FMD lens inspection, two tag families (LP and OOI), pooled folder
  dataset of 10,614 distinct pictures on the pranayp VM.
- Skills every session should consult: `multi-label-image-classification`
  (label matrix, split and readout discipline even though this task is
  single-label), `fmd-cnn-classification` for the CNN trainer conventions,
  `grilling` when a decision is the blocker.
- Standing preferences: one tag per image decided by the frozen folder rule;
  nothing runs on the VM without md5 pairs on both machines; numbers are
  presented to the lead the moment they are read, verification runs in
  parallel; experiments are ideated in `registry.json` before they run; every
  doc carries the five-line header and `docs/INDEX.md` is regenerated after.
- Tracker: local markdown. Tickets live in `docs/wayfinder/tickets/`,
  blocking is written in the ticket body, and the frontier is the tickets
  marked open with no unfinished blocker.

## Decisions so far

- [Two-tag rule verification: no earlier run counted the 178 Folded Lens pictures against Multiple Lenses](tickets/001-two-tag-rule-verification.md): Folded Lens is not a class in any single-label set here, Multiple Lenses never lost a picture, and the 178 sits in both columns of the multi-label line.
- [Local dataset and count table built and verified](tickets/002-local-dataset-and-count-table.md): 10,614 pictures, 8,409 tagged plus 2,205 Clear, 23 classes become 20, one shared 70:30 split, 62 checks pass and a rerun is byte-identical.

## Not yet specified

- What the merged Bubble result has to beat: no repeat-run band exists on
  this dataset, so how small a delta we are willing to call real is not yet
  pinned (it belongs to the readout ticket once the numbers exist).
- Whether Bubble Cluster eventually folds in too: open only if the client
  asks.
- Whether the pooled model should later be split per production line, which
  is Task 3 territory and not this map.

## Out of scope

- Task 2 (HEMA Fragment on clear images), Task 3 (defect size across five
  production lines at 18.25 um/pixel), Task 4 (pass/fail framing, including
  whether Edge passes) belong to their own efforts; nothing on this map
  produces their results.
- Re-annotating or changing any label in the source data: this map only
  re-reads existing labels.
- The multi-label LP line and its thresholds: unchanged by this task, its
  results stand as published.

## Ticket index

| Ticket | Type | Status | Blocked by |
|---|---|---|---|
| [001 Two-tag rule verification](tickets/001-two-tag-rule-verification.md) | research | done | - |
| [002 Local dataset and count table](tickets/002-local-dataset-and-count-table.md) | task | done | - |
| [003 VM readiness and micro-gate](tickets/003-vm-readiness-and-micro-gate.md) | task | open | the user's go (work starts tomorrow) |
| [004 The four training runs](tickets/004-four-training-runs.md) | task | open | 003 |
| [005 Merged versus separate readout](tickets/005-merged-vs-separate-readout.md) | task | open | 004 |
| [006 Result record and workbook](tickets/006-result-record-and-workbook.md) | task | open | 005 |
