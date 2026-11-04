---
title: "Ticket 027: OOI label table, class and gate columns over the frozen split"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/027-ooi-label-table.md
---
Type: build, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Can an object label table carrying BOTH column groups (class and gate) be built over the
frozen split so that an independent verifier recomputes every column and the subset rule,
with no number taken on trust from the builder?

## Spec

- Files owned by this ticket only: `experiments/multilabel_ooi/build_ooi_matrix.py`,
  `experiments/multilabel_ooi/verify_ooi_matrix.py`, artifacts under `run/ooi_matrix_20261104/`.
- Join `run/eda_full_20261029/resolved_labels.csv` to
  `run/split_20261103_v8/split_70_15_15.csv` on `picture_md5`. Same 7,470 rows, same split
  membership, md5 of the split must be `1a71d66d2de384cf47a3fcf7d9115baa`.
- Class columns (presence of the object, any size): Bubble = bubble + bubble_irregular +
  stretched_bubble; Bubble Cluster = bubble_cluster; Wet Package = wet_package;
  Foreign Matter = foreign_matter + its micron gate; Fiber = fiber + gate;
  Extraneous Polymer = extraneous_polymer + gate; HEMA = hema_fragment + hema_obstruction
  with shape_kind box + hema gate; Surface Groove = all-zero column.
- Exclusions: bubble_on_123 and bubble_on_edge (library-only), the single
  hema_obstruction tag-only picture (legacy tag, not a production box), all gate rows as
  class evidence only for the four gated classes.
- Gate columns for the four gated classes: the micron-gate rows. Gate is a subset of class
  on every row; the verifier asserts this plus the counts: class pictures 2,171 / 1,132 /
  798 / 392 / 314 / 154 / 142 / 0 (Bubble / Cluster / FM / Fiber / Wet / HEMA / EP / SG),
  gate pictures 454 / 362 / 135 / 151, per-split class counts val/test 326-325, 170-170,
  110-112, 60-58, 47-47, 25-27, 19-17.
- Carry the twelve lens columns and `clear` from `run/multilabel_lp_v8_20261103/labels_b.csv`
  verbatim; the verifier asserts row-for-row equality on all 7,470 rows.
- The verifier rebuilds every column from the resolved labels with its own class maps, then
  edits one cell of a copy and must fail naming that cell.

## Done when

`verify_ooi_matrix.py` exits 0 with every count asserted and the tamper proof caught.
