---
title: Architecture sweep on the multilabel LP task, five runs (one control, four notebook architectures)
date: 2026-09-29
type: result
status: active
where: reports/multilabel/ml_arch_sweep_20260929.md
---

# Architecture sweep, 2026-09-29

The lead asked whether the MultiScale architecture raises Folded Lens recall. That
question, run properly, is a five row test: the four architectures from the architecture
notebook, plus the plain ResNet50 as the control. All five ran in one session, one at a
time on the same A100, on the same 3,377 lens-presentation images and the same frozen
80/20 split (2,700 train, 677 test), with the recipe of the 2026-09-28 base run unchanged
(BCEWithLogitsLoss, SGD lr 1e-4 momentum 0.9 Nesterov, batch 8, 50 epochs, seed 42,
224x224, no augmentation, fixed schedule, no early stopping). The only thing that differs
between any two rows is the architecture. Total wall clock 59 minutes, all five exit 0.

## Headline (test set, 677 images, threshold 0.5)

| Architecture | Params | Macro AUPRC | Macro F1 | Micro P / R | Hamming | Exact match |
|---|---|---|---|---|---|---|
| ResNet50 (control) | 23.5 M | **0.91569** | 0.77118 | 0.99849 / 0.92567 | 0.01595 | 0.92171 |
| MultiLevel MultiScale (notebook arch 1) | 58.4 M | 0.86241 | 0.77434 | 0.99849 / 0.92847 | 0.01536 | 0.92467 |
| MultiLevel Attention SE (notebook arch 2) | 50.4 M | 0.86201 | 0.77153 | 0.99849 / 0.92707 | 0.01566 | 0.92319 |
| Inception + branch attention (notebook arch 3) | 58.6 M | 0.86636 | 0.77434 | 0.99849 / 0.92847 | 0.01536 | 0.92467 |
| Inception + refined decode (notebook arch 4) | 45.9 M | 0.88778 | **0.79051** | 0.99704 / 0.94390 | **0.01241** | **0.94092** |

Macro AUPRC is the metric of record. Four of the five classes are at or near ceiling in
every row, so the whole table turns on Folded Lens and on the calibration of Missing Lens.

## The answer to the lead's question: no, and it is worse than flat

Folded Lens recall at threshold 0.5 is **zero in all five rows**, including the control.
Lowering the Folded Lens threshold does not rescue the architectures either:

| Architecture | FL images | FL AUPRC | Found at 0.5 | 0.4 | 0.3 | 0.2 | 0.1 | 0.05 | 0.02 |
|---|---|---|---|---|---|---|---|---|---|
| ResNet50 (control) | 36 | 0.58229 | 0 | 0 | 1 | 2 | 5 | 5 | 6 |
| MultiLevel MultiScale | 36 | 0.49647 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MultiLevel Attention SE | 36 | 0.49448 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Inception + branch attention | 36 | 0.51463 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Inception + refined decode | 36 | 0.43889 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The mechanism is visible in the scores: on the 36 true Folded Lens test images the four
architectures put **every** score below zero (highest -0.30, -0.74, -0.51, -0.95), so no
threshold can recover them. The control still keeps 8 of the 36 above zero and catches 1
to 6 as the threshold drops. The threshold-free measure agrees: Folded Lens AUPRC falls
from 0.582 in the control to 0.44 to 0.51 in the four architectures. The extra depth,
attention and Inception branches add capacity that the Folded Lens gradient never uses;
they make that output more confidently negative, not less.

This is the co-occurrence structure the design doc predicted, not an architecture fault.
All 178 images in the whole export that carry Folded Lens also carry Multiple Lenses, and
Multiple Lenses is learned almost perfectly (289 of 289 test images found in every row).
The model has no reason to spend a separate output on a tag that is always implied, and
extra architecture capacity makes it more decisive about that, not less.

## The number that changes how the other numbers are read

The control was re-run in this session with the same seed, the same data and the same
recipe. Against the 2026-09-28 base run:

| Metric | 2026-09-28 | 2026-09-29 control | Delta |
|---|---|---|---|
| Macro AUPRC | 0.90454 | 0.91569 | +0.01115 |
| Macro F1 | 0.80826 | 0.77118 | -0.03708 |
| Exact match | 0.93944 | 0.92171 | -0.01773 |
| Folded Lens recall | 0.05556 | 0.00000 | -0.05556 |
| Folded Lens F1 | 0.10256 | 0.00000 | -0.10256 |
| Missing Lens recall | 0.93846 | 0.80000 | -0.13846 |

That is the run-to-run band, and it is larger than every architecture delta in the
headline table. Nothing there should be called an architecture effect. Two things in the
sweep are still categorical rather than marginal, because they are not deltas at all:
Folded Lens recall is zero in all five rows, and the four architectures move the Folded
Lens scores further from the boundary rather than closer to it. Everything else, including
the macro F1 movement, sits inside the band the control itself produced.

## Timing, no warmup anywhere

| Architecture | Cold ms/image (in process, first pass) | Cold ms/image (fresh process, first pass) | First batch, fresh process | Repeat ms/image | Train total | Train s/epoch |
|---|---|---|---|---|---|---|
| ResNet50 (control) | 3.285 | 3.461 | 355 ms | 3.230 | 500.6 s | 10.0 |
| MultiLevel MultiScale | 3.401 | 3.705 | 487 ms | 3.289 | 653.0 s | 13.1 |
| MultiLevel Attention SE | 3.297 | 3.541 | 399 ms | 3.239 | 579.4 s | 11.6 |
| Inception + branch attention | 3.408 | 3.817 | 514 ms | 3.301 | 790.0 s | 15.8 |
| Inception + refined decode | 3.471 | 3.762 | 493 ms | 3.333 | 947.9 s | 19.0 |

The no-warmup convention for this project: the timed pass is the first pass over the test
set as it comes, and the metrics come from that same pass, so there is no extra pass and no
optimizer warmup at all. Two layers are reported. In process, the pass is timed from the
first batch inside the training run. In a fresh process, the number also contains process
start, CUDA init and the checkpoint load, which is the strictest reading of no warmup; that
number was produced per run by a separate script that rebuilds the model from the
checkpoint's own recorded settings and refuses to continue if the state dict does not load
cleanly. Timings are comparable because the five runs were sequential: one model on the
device at a time. Inference per image is nearly flat across all five architectures, 3.29 to
3.47 ms, because the loader and image decode dominate; training time is not flat, 1.2x to
1.9x the control, because that is where the extra depth and branches cost.

## Per class (threshold 0.5)

| Architecture | Class | Support | Precision | Recall | F1 | AUPRC |
|---|---|---|---|---|---|---|
| ResNet50 (control) | Cavity Off Center | 37 | 1.00000 | 0.94595 | 0.97222 | 1.00000 |
| ResNet50 (control) | Folded Lens | 36 | 0.00000 | 0.00000 | 0.00000 | 0.58229 |
| ResNet50 (control) | Multiple Lenses | 289 | 0.99654 | 0.99654 | 0.99654 | 0.99999 |
| ResNet50 (control) | Missing Primary Package | 286 | 1.00000 | 0.99650 | 0.99825 | 1.00000 |
| ResNet50 (control) | Missing Lens | 65 | 1.00000 | 0.80000 | 0.88889 | 0.99617 |
| MultiLevel MultiScale | Cavity Off Center | 37 | 1.00000 | 0.97297 | 0.98630 | 1.00000 |
| MultiLevel MultiScale | Folded Lens | 36 | 0.00000 | 0.00000 | 0.00000 | 0.49647 |
| MultiLevel MultiScale | Multiple Lenses | 289 | 0.99655 | 1.00000 | 0.99827 | 0.99999 |
| MultiLevel MultiScale | Missing Primary Package | 286 | 1.00000 | 0.99650 | 0.99825 | 0.99801 |
| MultiLevel MultiScale | Missing Lens | 65 | 1.00000 | 0.80000 | 0.88889 | 0.81758 |
| MultiLevel Attention SE | Cavity Off Center | 37 | 1.00000 | 0.94595 | 0.97222 | 1.00000 |
| MultiLevel Attention SE | Folded Lens | 36 | 0.00000 | 0.00000 | 0.00000 | 0.49448 |
| MultiLevel Attention SE | Multiple Lenses | 289 | 0.99655 | 1.00000 | 0.99827 | 1.00000 |
| MultiLevel Attention SE | Missing Primary Package | 286 | 1.00000 | 0.99650 | 0.99825 | 0.99801 |
| MultiLevel Attention SE | Missing Lens | 65 | 1.00000 | 0.80000 | 0.88889 | 0.81758 |
| Inception + branch attention | Cavity Off Center | 37 | 1.00000 | 0.97297 | 0.98630 | 1.00000 |
| Inception + branch attention | Folded Lens | 36 | 0.00000 | 0.00000 | 0.00000 | 0.51463 |
| Inception + branch attention | Multiple Lenses | 289 | 0.99655 | 1.00000 | 0.99827 | 1.00000 |
| Inception + branch attention | Missing Primary Package | 286 | 1.00000 | 0.99650 | 0.99825 | 0.99959 |
| Inception + branch attention | Missing Lens | 65 | 1.00000 | 0.80000 | 0.88889 | 0.81758 |
| Inception + refined decode | Cavity Off Center | 37 | 1.00000 | 0.91892 | 0.95775 | 1.00000 |
| Inception + refined decode | Folded Lens | 36 | 0.00000 | 0.00000 | 0.00000 | 0.43889 |
| Inception + refined decode | Multiple Lenses | 289 | 0.99313 | 1.00000 | 0.99655 | 0.99999 |
| Inception + refined decode | Missing Primary Package | 286 | 1.00000 | 0.99650 | 0.99825 | 1.00000 |
| Inception + refined decode | Missing Lens | 65 | 1.00000 | 1.00000 | 1.00000 | 1.00000 |

Confusion counts at threshold 0.5, as TP/FP/FN/TN: control 35/0/2/640, 0/0/36/641,
288/1/1/387, 285/0/1/391, 52/0/13/612; MultiScale 36/0/1/640, 0/0/36/641, 289/1/0/387,
285/0/1/391, 52/0/13/612; MultiLevel Attention SE 35/0/2/640, 0/0/36/641, 289/1/0/387,
285/0/1/391, 52/0/13/612; Inception + branch attention 36/0/1/640, 0/0/36/641, 289/1/0/387,
285/0/1/391, 52/0/13/612; Inception + refined decode 34/0/3/640, 0/0/36/641, 289/2/0/386,
285/0/1/391, 65/0/0/612.

## Why three rows show the same Missing Lens AUPRC

The Missing Lens AUPRC is 0.81758 in three architecture rows, to five decimals, which looks
like a copy error and is not one. The scores differ between those runs by up to 15 logits.
What is identical is the shape of the ranking: all three put the same 52 Missing Lens
positives above every one of the 613 negatives, and the remaining 13 in the last 13 ranks.
When the positives are separated that cleanly, the average precision is a constant of that
structure rather than a property of the model, and it lands on the same value in all three.
The condition is harmless here because Missing Lens is not the question, but it is the
reason to read AUPRC next to the per-image score spread rather than alone. It also separates
two different failures: the refined decode row ranks Missing Lens perfectly (AUPRC 1.0) yet
finds only 52 of 65 at threshold 0.5, so its 13 misses are a threshold placement, not a
ranking failure.

## Verification chain

1. The port was proven before any training. The four architectures are written for another
   framework and were rebuilt for the training framework actually used, keeping every filter
   count, branch tap, fusion width and head layer; the final layer is 5 independent scores
   instead of a single-answer softmax because one image can carry several tags. A dedicated
   checker recomputed every module's parameter count from the notebook's own filter
   dictionary and compared the totals with the notebook's models as built earlier in the
   other framework: 38 checks, 0 failed. The only gap between the two frameworks is
   BatchNorm accounting (one counts the moving statistics as weights, the other keeps them as
   buffers), proved by hand to be exactly the difference on every row, and the shared
   backbone cancels out of every pairwise comparison.
2. A two-step smoke on real images with the exact run arguments passed for all five
   architectures, with the taps checked after a real forward pass rather than before it, and
   with a warning in the training path if a non-baseline architecture's taps do not resolve.
   The taps are the notebook's pre-activation residual adds, not the post-activation stage
   outputs.
3. After the sweep, all 75 checks of an independent recompute passed locally: every headline
   metric and all 20 confusion counts per architecture recomputed from the raw prediction
   dump, the dump proven to hold exactly the 677 test rows of the frozen split in order, the
   parameter count and the recorded architecture checked per row, the timing block checked
   for no warmup and for the image count, and the training seconds checked against the summed
   epoch history. All 25 mirrored files are md5 identical to the VM originals.

## Artifacts

- Workbook for the lead: `reports/multilabel/FMD_MultiLabel_ArchSweep_20260929.xlsx`
  (sweep summary, Folded Lens with the threshold read-out, per class, timing, epoch history,
  method). Reader-facing names only, no local paths.
- Focused workbook for the lead's own question, baseline against MultiScale only:
  `reports/multilabel/FMD_MultiLabel_Baseline_vs_MultiScale_20260929.xlsx` (seven sheets:
  summary with a delta column, every class, the Folded Lens detail including the
  co-occurrence profile read from the annotation export, timing, two figures, the figure
  source numbers, and the method and evidence list).
- Repo mirror: `run/multilabel_lp_archs_20260929/` (per-architecture metrics.json,
  history.csv, test_predictions.npz, inference_cold.json, the five training logs, the sweep
  log, and the staged copies of train.py and verify_archs.py that ran; md5-checked).
- VM: `/home/pranayp/yolo_ooi/multilabel_lp_archs_20260929/` holds the same files plus the
  `best.pt` weights for all five runs, which stay there as in the 2026-09-28 run.
- Code: `experiments/multilabel_resnet50/train.py` (architecture set, `--arch` flag, faithful
  ports, no-warmup inference pass, result and timing blocks), `verify_archs.py` (38-check
  port proof), `measure_inference_cold.py` (fresh-process no-warmup timing and checkpoint
  check), `verify_archs_run_20260929.py` (75-check result recompute),
  `make_arch_sweep_workbook.py`, `make_baseline_vs_multiscale_workbook.py` (the focused
  workbook above), `vm/drivers/run_ml_archs_20260929.sh`.
- Registry: five rows added to `experiments/multilabel_resnet50/registry.json`
  (ml_arch_resnet50_control_20260929, ml_arch_multiscale, ml_arch_multilvl_attention,
  ml_arch_inception_attention, ml_arch_inception_refine), each carrying the metrics, the
  Folded Lens threshold read-out and the timing block. The planned lever rows are unchanged.

## What this does and does not claim

- It answers the lead's question. MultiScale does not raise Folded Lens recall; it is zero,
  and the architecture pushes the Folded Lens scores further negative than the plain
  ResNet50 does. The same holds for the other three architectures.
- It does not say architecture choice is irrelevant. Macro F1 moves up to +0.019 and the
  refined decode row is the best row on macro F1, hamming loss and exact match, and the only
  row with a perfect Missing Lens ranking. All of that is inside the run-to-run band the
  control measured, so it is a candidate, not a finding.
- One seed per row, no validation set, fixed 50 epochs, test evaluated once. Nothing here
  separates a real architecture effect from seed and framework variation except where the
  result is categorical, which is the Folded Lens outcome.
- The Folded Lens problem is not reachable by architecture. All 178 Folded Lens images in
  the export also carry Multiple Lenses, so the tag is always implied. The levers that
  address it are data-side (more Folded Lens examples, or Folded Lens images that are not
  also Multiple Lenses), loss-side (a positive weight on Folded Lens, registry row
  ml_resnet50_posw, planned), or the reliable-negatives row (ml_resnet50_reliable, planned).
  None of the three was run in this sweep and none should be read into these numbers.
