---
title: "Ticket 026 - Clear as a third namespace"
date: 2026-10-22
type: task
status: done
where: docs/wayfinder/tickets/026-clear-namespace.md
---

# Ticket 026: Clear as a third namespace

Meeting 2026-10-22 confirmed: a picture in a Clear folder with no tags gets
Clear as its tag. The model then works with three label namespaces:

1. Lens Presentation: tags.
2. Objects of Interest: bounding boxes.
3. Clear: the picture's own tag.

## Question

Does the frozen 2026-10-21 frame match this exactly, and does the label
matrix builder implement it as stated?

## Method

Compare the meeting statement with the frame decision (Clear = winning path
in a Clear folder of the two Updated libraries, 2,166 pictures). Check the
matrix builder: no Clear picture carries another label, and no tagged
picture sits in the Clear namespace. Count any picture that breaks either
rule.

## Output

A short confirmation note: the rule as implemented, the count of Clear
pictures, the count of any conflicts, and the three namespaces written into
the matrix spec. If the frame differs from the meeting statement in any way,
write the difference down and ask before changing anything.

## Feeds

Ticket 021: Clear is a column of the split like any other.

## Resolution (2026-10-23)

The frame and the matrix builder match the meeting statement on all but one
edge, measured on the 6,785-row matrix:

- Clear rows: 2,166. Every one sits in a Clear folder of the two Updated
  libraries, matching the frame decision (Clear = winning path in a Clear
  folder).
- Clear-folder pictures in the matrix: 2,333. The other 167 carry defect or
  LP labels (rescued by older files, or LP-tagged), so they are not Clear.
  Composition of the 167: bubble-only or bubble-with-cluster/WP/camera-tag
  combinations dominate; full list in the run artifacts.
- THE ONE DIFFERENCE: 10 pictures carry Clear AND Dirty Camera. The builder
  checks only defect and plain columns before granting Clear, not the LP
  columns, so a Clear-folder picture tagged only Dirty Camera gets both.
- RESOLVED (user, Option A, 2026-10-23): Clear must be clear and carry no
  other label. The matrix was rebuilt (rev2, run/multilabel_edge_20261023/,
  builder build_label_matrix_rev2.py): the 10 rows are now Dirty Camera-only,
  Clear 2,166 -> 2,156, every other column unchanged (6,785 rows, eligible
  6,679). The split was rebuilt on the rev2 matrix (v3,
  run/split_20261023_v3/, 4,568 train / 2,006 test) and re-verified with
  hand-typed values, independent derivation, byte-identical rerun and the
  corrupted-input proof. All previous artifacts stay on disk.
- The three namespaces hold: LP tags (11 columns with data, 4 Draft 2 tags
  with none), OOI boxes, Clear (2,166).
