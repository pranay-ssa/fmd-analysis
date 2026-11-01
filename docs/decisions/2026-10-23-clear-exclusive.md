---
title: "Decision: Clear is exclusive (Option A)"
date: 2026-10-23
type: decision
status: active
where: docs/decisions/2026-10-23-clear-exclusive.md
---

# Decision: Clear is exclusive (Option A)

Decided by the user on 2026-10-23, after reviewing the ticket 026 finding.

## The problem

Ten pictures sit in a Clear folder and carry only a Dirty Camera tag. The
matrix builder granted Clear without checking the LP tag columns, so those
ten rows carried Clear AND Dirty Camera. A picture cannot meaningfully be
both clear and camera-dirty.

## The decision

A picture is Clear only when it carries NO other label of any kind (defect,
gate, or LP tag). A tagged picture is never Clear. The ten affected rows
become Dirty Camera-only.

This amends frame decision 14 of 2026-10-21 (Clear = winning path in a Clear
folder): the folder still decides candidacy, but Clear no longer survives a
second label.

## Effect

- Label matrix rev2: Clear 2,166 to 2,156. Every other column unchanged;
  6,785 rows; 6,679 split-eligible.
- Split v3 rebuilt on rev2: 4,568 train / 2,006 test; Dirty Camera 209/89,
  Clear 1,509/647; zero group crossings; all verification legs pass.
- Artifacts: run/multilabel_edge_20261023/label_matrix.csv,
  run/split_20261023_v3/split.csv + meta.json. Builders
  build_label_matrix_rev2.py and build_split_v3.py; verifier
  verify_split_v3.py.
- Superseded but kept on disk: matrix 20261021, split v1 and v2.
