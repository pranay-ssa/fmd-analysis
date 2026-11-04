---
title: "Ticket 028: train_multilabel.py, one trainer for both column groups"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/028-train-multilabel.md
---
Type: build, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Can one trainer serve the object head and the combined head, with the gated target and the
weighting as switches, so every round differs by flags alone and never by a forked script?

## Spec

- File owned by this ticket only: `experiments/multilabel_ooi/train_multilabel.py`.
- Generalise `experiments/multilabel_lp_full/train_lp_v8.py`: reuse its threshold chooser,
  evaluation and prediction dump unchanged in behaviour (grid 0.05 to 0.95 step 0.05 on
  validation, highest F1, ties to the higher cut, guard of 10 validation positives).
- `--columns ooi` trains the seven supported object classes; Surface Groove is never a
  model output. `--columns combined` trains twelve lens plus seven object, twenty minus SG.
- `--gated-target class|gate` picks which column group feeds the four gated classes.
- `--pos-weight on|off`: per-class (N - n) / n computed on the training split only.
- Recipe fixed: resnet50, 224, batch 8, 50 epochs, no early stopping, SGD lr 1e-4
  momentum 0.9, seed 42, BCEWithLogitsLoss.
- Outputs per arm under `run/multilabel_ooi_20261104/<arm>/`: metrics.json (including
  macro AP over the seven supported classes with the prevalence floors beside them, F1 at
  0.5 and at chosen cuts, Bubble/Cluster confusion), thresholds.json, predictions.npz with
  val and test truth and scores, and one run.json written by the runner, never hand-edited,
  with status, config (columns, gated target, weight mode, seed, recipe) and metrics.primary.
- `--labels-only` must print the expected per-split counts; `--smoke` runs a two-batch step
  on the VM (torch lives only there); `--dump-predictions` re-scores from a saved checkpoint.

## Done when

`--labels-only` matches the ticket 027 counts locally and `--smoke` passes on the VM.
