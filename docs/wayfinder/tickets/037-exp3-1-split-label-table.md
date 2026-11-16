---
title: "Ticket 037: Experiment 3.1 split and 4-column label table"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/037-exp3-1-split-label-table.md
---
Type: build, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

Build the derived split and the 4-column gate label table that Experiment 3.1 uses, without
touching split v8 or any file Experiment 1 and 2 read.

## Inputs, with the md5 to check first

| File | md5 |
|---|---|
| `run/eda_full_20261029/resolved_labels.csv` (44,791 rows) | `f61ea0b90df095ebe52d1332f8bfdb8a` |
| `run/eda_full_20261029/picture_table.csv` (10,614 pictures) | `a03ddeead53bae370c17bd8ea15c0df0` |
| `run/split_20261103_v8/split_70_15_15.csv` (7,470 rows) | `1a71d66d2de384cf47a3fcf7d9115baa` |

Stop and report if any md5 differs.

## Counting rules, apply exactly

- Identity is `picture_md5`. One annotation per picture, newest file wins. Dedupe on md5.
- A picture carries a class when it has a `shape_kind == box` row with that class's canonical id:
  `foreign_matter`, `fiber`, `extraneous_polymer`, and for HEMA any of `hema`, `hema_obstruction`,
  `hema_fragment`.
- A picture is size-flagged for a class when it carries that class's gate code as a tag row:
  `P3_FM_MICRON_THRESHOLD`, `P3_FIB_MICRON_THRESHOLD`, `P3_EP_MICRON_THRESHOLD`,
  `P3_HE_MICRON_THRESHOLD`.
- Unflagged means class box present and that class's gate code absent.
- The gate is a subset of its class, never a label of its own.

## Split rule

Start from the v8 assignment. A picture leaves train or validation for test when it carries a box
of any of the four classes without that class's gate tag. A picture gated in every gated class it
carries keeps its v8 assignment. A picture outside v8 that is unflagged for any of the four
classes is added as a test row. The rule is a union over the four classes because one model is
scored on one split.

## Expected counts, assert every row

| | v8 | Exp 3.1 |
|---|---|---|
| rows | 7,470 | 7,555 |
| train | 5,239 | 4,964 |
| validation | 1,110 | 1,058 |
| test | 1,121 | 1,533 |

412 pictures enter test: 327 leave train or validation, 85 come from outside the split. 41
unflagged pictures were already in the v8 test set.

| Class | train gated | val gated | test gated | test unflagged | decisive total | decisive outside v8 |
|---|---|---|---|---|---|---|
| Foreign Matter | 315 | 60 | 79 | 380 | 51 | 36 |
| Fiber | 195 | 43 | 124 | 43 | 14 | 13 |
| Extraneous Polymer | 81 | 14 | 40 | 40 | 34 | 33 |
| HEMA | 79 | 20 | 52 | 6 | 3 | 3 |

Assert: zero unflagged pictures of any of the four classes remain in train or validation. This is
the premise of the experiment.

Decisive, for a class, means the picture carries that class unflagged AND carries no lens tag (the
12 canonical lens ids: missing_primary_package, multiple_lenses, lens_off_center, dirty_camera,
no_lens, folded_lens, low_dose, cavity_off_center, dirty_strobe, view_obstructed, bubble_scatter,
package_misalignment), no `wet_package`, no `bubble_cluster`, no `surface_groove`, and no other
class in this set that is gated.

## Outputs

Under `run/split_exp3_1_20261116/`:

- `split.csv`: `picture_md5, group_id, split`. Same schema as v8. 7,555 rows.
- `labels.csv`: `picture_md5, image_path, split, fm_gated, fiber_gated, ep_gated, hema_gated`.
  `image_path` copied from `picture_table.winning_path` for every row, including the 85 outside v8.
  `image_path` must match `winning_path` exactly.
- `picture_detail.csv`: `picture_md5, split, image_path, fm_present, fm_gated, fiber_present,
  fiber_gated, ep_present, ep_gated, hema_present, hema_gated, decisive_fm, decisive_fiber,
  decisive_ep, decisive_hema, largest_fm_px, largest_fiber_px, largest_ep_px, largest_hema_px,
  other_fail_labels`. `largest_*_px` is the longer side of the largest box of that class, in
  native pixels, from the annotation coordinates. `other_fail_labels` is a semicolon list.
- `meta.json`: version, date, the rule text above, the input md5s, the counts, and the move list
  size. Version `exp3_1_v1`.

Builder and verifier under `experiments/multilabel_ooi/`:
`build_split_exp3_1.py`, `verify_split_exp3_1.py`. The verifier must not import the builder. It
recomputes every count from the annotation and proves it catches one moved row and one flipped
gate cell.

Do not run `tools/index_docs.py`; the orchestrator owns `docs/INDEX.md`. Do not modify split v8,
the v8 meta, or any Experiment 1 or 2 artifact.

## Done when

The verifier exits 0, every count above matches, the tamper proofs are recorded, and `meta.json`
carries the input md5s. Report the counts and the file md5s in the card summary.
