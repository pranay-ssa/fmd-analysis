---
title: Runs
date: 2026-11-19
type: reference
status: active
where: experiments/frozen_data_experiments/multilabel_cnn/runs/README.md
---

# Runs

One folder per run, named by date, model and arm. Each run folder carries:

- `run.json`: status, parameters, and `metrics.primary`.
- `metrics.json`: per-class numbers.
- `train.log`: the full log.
- `final.pt`: the weights. On the VM only; the repository does not carry them.
