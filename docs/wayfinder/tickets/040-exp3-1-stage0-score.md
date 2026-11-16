---
title: "Ticket 040: score the Experiment 1 checkpoint on the Experiment 3.1 test population"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/040-exp3-1-stage0-score.md
---
Type: run, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

How does the Experiment 1 nineteen-column checkpoint score the four gated classes on the new
1,533-picture test population? This is the baseline, before any training.

## Spec

- Checkpoint `run/multilabel_ooi_20261104/combined/final.pt`, ResNet50, 19 output columns,
  imgsz 224. Record the checkpoint md5 in the run record.
- Script `vm/ops/score_exp3_1_stage0.py`. Reuse the trainer's own preprocessing. Do not write a
  second resize or normalisation: import from `experiments/multilabel_ooi/train_multilabel.py`
  if the functions are importable without torch side effects, otherwise replicate the validation
  transform and prove it by scoring 20 pictures twice and getting a maximum absolute difference
  below 1e-3.
- Score the 1,533 test rows of `run/split_exp3_1_20261116/labels.csv`, in table order, and save
  the four object columns only: `class_foreign_matter`, `class_fiber`,
  `class_extraneous_polymer`, `class_hema`. Keep all 19 scores in the npz if it costs one line;
  the four are what the scorer reads.
- Write `run/exp3_1_stage0_20261117/predictions.npz` (md5 list, scores, column names),
  `thresholds.json` copied from `run/multilabel_ooi_20261104/combined/thresholds.json`, and
  `run.json` with `family: score`, `status: ok`, `metrics.primary` = the Foreign Matter AUROC
  against unflagged test pictures, and a `notes` field carrying this caveat verbatim: 327 of the
  1,533 test pictures were in this checkpoint's training set, so their scores are contaminated;
  the 85 out-of-split and 41 already-in-test pictures are clean.
- Inference only. No training, no threshold choice, no pass/fail verdict.

## Done when

1,533 predictions written, the double-score check passes, `run.json` status ok, and the AUROC is
reported with its support (79 gated against 380 unflagged for Foreign Matter). Report the number
in the card; the scorer recomputes it independently in ticket 043.
