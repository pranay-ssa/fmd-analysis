---
title: "Ticket 002: local dataset and count table for both label variants"
date: 2026-10-06
type: result
status: done
where: docs/wayfinder/tickets/002-local-dataset-and-count-table.md
---

# 002: Local dataset, split and count table

Type: task, AFK. Map: [Task 1 bubble merge](../task1_bubble_merge_map.md).

## Question

Build everything the four runs need on this machine, without touching the VM:
the one-tag-per-image labels for both readings (bubbles separate and bubbles
merged) with Clear added, the shared 70:30 split, the per-class count table
split by LP tag and OOI tag, and the train/test tree builder the CNN trainer
reads. Verify each number against the figures already published to the client.

## Resolution (2026-10-06)

Built and verified:

- `experiments/bubble_merge/build_labels.py` writes
  `run/bubble_merge/20261006/`: labels.csv (10,614 rows, both class columns,
  tag family, split, every source path), count_table_separate.csv,
  count_table_merged.csv, split_70_30_seed42.csv, summary.json.
- `experiments/bubble_merge/verify_labels.py`: **62 checks, 0 failed**, and a
  second build is byte-identical. Independent routes: every class-line cell
  of the 2026-09-17 published split, the 12 LP and 11 OOI tag counts of the
  client EDA, picture-by-picture comparison against the frozen rule builder
  (`src/make_line_splits.py::build_pool`, zero differences), Clear arithmetic
  2,333 = 128 + 2,205, merge arithmetic 113 + 44 + 14 + 14 = 185, split
  rules, and a rebuild-in-memory diff of every row.
- The gap between the tag column and the dataset column sums to **55**, which
  independently reproduces the published count of two-tag pictures.
- `experiments/bubble_merge/build_vm_trees.py` builds the trainer's
  train/test class trees by symlink: full strict build over all 10,614
  pictures passes on synthetic sources locally, and deleting one picture's
  sources makes it fail three separate ways with a non-zero exit.
- Count table record: `reports/bubble_merge/count_table_20261006.md`.
- Registry rows written before running: `experiments/bubble_merge/registry.json`
  (four ideated rows plus the readout rule).

One bug was caught and fixed during the build: the merged tag-presence column
initially also fired on the separate table, showing 185 where 113 belonged;
the verifier now pins both views (checks F8 and F9).

## Consequences for the map

Ticket 003 can start from frozen inputs: the label file, the split, the tree
builder and the trainer flags all exist and are checked locally.
