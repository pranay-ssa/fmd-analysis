---
title: "Ticket 004: the four training runs"
date: 2026-10-06
type: experiment
status: active
where: docs/wayfinder/tickets/004-four-training-runs.md
---

# 004: The four training runs

Type: task. Map: [Task 1 bubble merge](../task1_bubble_merge_map.md).
Blocked by: [003 VM readiness and micro-gate](003-vm-readiness-and-micro-gate.md).

## Question

Run the 2 x 2 design on the VM under the frozen recipe and bring the evidence
back locally: architecture in {ResNet50, MultiLevel MultiScale} x reading in
{bubbles separate, bubbles merged}, so the merged class is measured against
the separate classes on identical pictures.

## Runs (registry rows, ideated in `experiments/bubble_merge/registry.json`)

| Row | Arch | Classes | Dump |
|---|---|---|---|
| `bubble_merge_resnet50_separate` | resnet50 | 23 | on |
| `bubble_merge_resnet50_merged` | resnet50 | 20 | on |
| `bubble_merge_multiscale_separate` | resnet50_inception | 23 | on |
| `bubble_merge_multiscale_merged` | resnet50_inception | 20 | on |

Recipe, identical for all four: 50 epochs, batch 8, seed 42, SGD 1e-4
Nesterov, native frame resized to 224x224, `--dump`, one at a time with the
GPU check before each launch.

## Done when

metrics.json, confusion.json, predictions.csv and the confusion PNG exist for
all four runs, mirrored locally with matching md5, the registry rows carry
their results, and the four runs show no crash, no class-count mismatch
between metrics.json and the count tables, and predictions rows equal test
picture counts (3,186 separate, and the merged variant's test count as the
tables say).

## Known limits to quote with the results

Single seed, no measured repeat-run band on this dataset, and no validation
slice (early stopping is not used by this trainer, so no test leakage). Any
delta smaller than the band stays a non-result until a repeat says otherwise.

## Launch record (2026-10-07) and the one deviation

**Update, later the same day: the client confirmed the folder order is
updated-first** (Updated Objects > Updated Categorical > old library; the 33
old-Fiber pictures are Extraneous Polymer). Labels, count tables and split
were rebuilt into `run/bubble_merge/20261007/` (10,614 pictures; split
7,429/3,185; merged Bubble 179 = 130/49; Fiber 329, Extraneous Polymer 267;
verifier 67/67 local and on the VM, rebuild byte-identical). The four runs
below (old order) finished rc=0 and stay on the VM under `runs/` as an
old-order reference; the authoritative rerun lives in `runs2/` from
`runs2/launch_all2.sh`, same recipe, same readout rule, new trees `trees2/`.

All four runs started on the VM under `/home/pranayp/merge_analysis` at
01:56-01:58 UTC: `runs/launch_all.sh` plus `runs/launch_missing.sh`,
everything logged in `runs/launch.log`. The GPU was checked idle before the
first launch (24 CPUs, A100 80 GB, no other compute process).

Deviation from this ticket's "one at a time": the four runs were started
concurrently to fit the user's window, after three simultaneous starts
aborted (rc=134: every TensorFlow process tried to pre-allocate the whole
card, `CUDA_ERROR_OUT_OF_MEMORY`) and were relaunched with
`TF_FORCE_GPU_ALLOW_GROWTH=true`. Seed, epochs, batch size, optimizer and
inputs are exactly the registry rows, so accuracy comparisons stand; the
ms-per-image figures in these four metrics.json are contention numbers and
must not be compared with historical timing rows. If any of the four dies or
miscounts, it is relaunched on its own, one at a time, as the ticket says.

## Result (fill when the four runs finish)
