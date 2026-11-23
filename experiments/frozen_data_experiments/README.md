---
title: Frozen data experiments
date: 2026-11-19
type: experiment
status: active
where: experiments/frozen_data_experiments/README.md
---

# Frozen data experiments

One folder per experiment on the frozen dataset. The same tree exists on the VM and in this repository.

| Experiment | State | Split | Run | Headline |
|---|---|---|---|---|
| multilabel_cnn | done | frozen_70_15_15_20261119 | 20261119_resnet50_224_seed42 | Macro AUROC 0.9624; macro F1 80.4% at 0.5 |

## Rules

1. One experiment, one folder, named by what it is. No "experiment 1" and no version numbers.
2. One run, one folder, with its own record, log and weights.
3. The split is built once at the root and linked into each experiment. A different split gets its own folder.
4. The VM holds the weights. The repository holds the records, the split and the results, never the weights.

## Paths

- VM: `/home/pranayp/frozen_data_experiments/`
- Repository: `experiments/frozen_data_experiments/`

## State

The label space is 17 defect columns. The lead confirmed on 19 November that the 42 Clear pictures are excluded. The split population is 13,631 pictures. The class cut removes no pictures.
