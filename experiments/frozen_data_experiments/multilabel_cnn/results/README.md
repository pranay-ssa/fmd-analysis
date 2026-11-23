---
title: Results
date: 2026-11-20
type: reference
status: active
where: experiments/frozen_data_experiments/multilabel_cnn/results/README.md
---

# Results

Pulled from the VM after the frozen 17-class run. No weights.

The copied run files are in `../runs/20261119_resnet50_224_seed42/results/`:

- `metrics.json`
- `predictions.npz`
- `thresholds.json`
- `run.log`
- `watcher.log`
- `watcher_status.json`

The review workbook is `frozen_multilabel_results.xlsx`. It has 11 sheets: Read me, Summary, Pass fail, Pass images, Per class, Class split, Selected thresholds, Threshold rule, Scope and exclusions, Method, Definitions. It is built by `build_workbook.py` and checked by `verify_workbook.py` (7,385 checks). `workbook_data.py` is the shared data layer; it recomputes AUROC, the pass/fail counts, the pass-image tables and the per-class split counts from the saved test scores, labels and size tags.

The workbook's main table uses a 0.5 threshold. The validation-chosen cuts are on a separate sheet and are provisional.
