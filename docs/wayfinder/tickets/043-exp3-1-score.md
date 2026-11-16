---
title: "Ticket 043: score both arms and the baseline on the same population"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/043-exp3-1-score.md
---
Type: analysis, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

What do the three score sets (Stage 0 baseline, gate4_224, gate4_448) say about size separation,
and how many unflagged pictures would each arm wrongly fail?

## Spec

Read only saved scores. No torch, no images.

- AUROC per class, gated against unflagged test pictures, with ties counted 0.5. Report both
  supports in every row. Populations from `picture_detail.csv`.
- Recall at the arm's own chosen cut, gated test pictures.
- False-fire rate at the same cut on all unflagged test pictures, and separately on the decisive
  unflagged pictures only. Keep the two columns apart.
- Pass/fail verdict at the chosen cut on the 99 decisive pictures (Foreign Matter 51, Fiber 14,
  Extraneous Polymer 34), where the object-side verdict is exact because no other fail label is
  present. Lens tags count as another fail label. On the full 1,533 the verdict is object-side only; label the table header that way.
- Size curve: score against `largest_*_px` for the class, with the gate boundary at 19.4 to 19.6 px
  marked, and a micron column at both 18.1165 and 18.25 microns per pixel.
- Outputs under `run/exp3_1_scores_20261117/`: `per_class.csv`, `per_picture.csv`,
  `size_curve.csv`, `summary.json`. One row per arm per class; never pool the arms.
- Deterministic: re-running must produce identical files. Record the input md5s.

## Done when

Every number is reproduced from the npz in this ticket rather than copied from a log or a card,
the three score sets are visibly separate, and HEMA is present as `not measurable` with the reason
in the row. Report the per-class table in the card summary.
