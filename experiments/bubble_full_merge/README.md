---
title: bubble full merge - experiment record
date: 2026-10-15
type: experiment
status: active
where: experiments/bubble_full_merge/README.md
---

# bubble_full_merge ("bubble full merge")

Experiment B re-run on OOI crops with the enlarged 2026-10-15 dataset.
Registry with the frozen decisions: `registry.json` (written before running).
Label-frame decision: `docs/decisions/2026-10-15-exp-b-label-frame.md`.

## What changed vs the 20261008 crops wing

- Three annotation sources with production-first precedence (was two).
- 6 classes: the whole bubble family consolidates (Cluster, Scatter included).
- P2_BST is Bubble now, not "Stretched Bubble" excluded.
- Production `P3_HE` boxes are HEMA Fragment (collision resolved).
- Fresh 70:30 stratified split, seed 42 (old split not reused).
- `--dump` and `--save-model` are mandatory on the run: the prediction dump
  feeds phase 2, the misclassification export.

## Pipeline

1. `extract_crops.py` (on the VM, images live there) -> `crops/`,
   `crops_manifest.csv`, `excluded.csv`, `source_census.json`.
   Verification gate: image counts per source must match the resolved census
   (758 production defect pictures, 1,132 union).
2. `build_splits.py` -> `exp/{train,test}/<class>`, `split_images.csv`,
   `counts.csv`, `split_report.json`. Leakage check must read 0.
3. `/home/pranayp/model_training.py --arch resnet50_inception --data exp
   --epochs 50 --batch-size 8 --seed 42 --dump --save-model`.
4. Phase 2 (local, after numbers are read): misclassification folder +
   manifest Excel, spec in the registry readout section.

## Phase 2 spec (frozen with the user)

- Every misclassified test crop -> `experiments/misclassification/`,
  converted BMP -> PNG or JPEG.
- Filename `<sno>_<true>_<pred>` (e.g. `1_hema_fragment_extraneous_polymer.png`),
  sno a globally unique integer, primary key of the manifest.
- Manifest Excel: sno, original crop file, source image, crop bbox
  (the safeguard for the multi-crop-per-image case), true label, predicted label.

## Comparability

Numbers are NOT comparable to `run/bubble_merge_crops_20261008/exp_b`
(dataset and split both changed). The old run is context only.
