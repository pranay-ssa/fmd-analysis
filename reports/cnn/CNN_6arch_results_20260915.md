# CNN classifier line: six architectures on the combined 22-class set

**Date:** 2026-09-15
**Scope:** the six-architecture matrix (ResNet18, ResNet50, MultiLevel MultiScale, MultiLevel Attention,
Inception plus branch attention, Inception plus refined decode) on the combined 22-class dataset, plus the
cross-split comparison against the teammate's run of the same six architectures.
**Companion files:** `experiments/cnn/README.md` (protocol and open items), the workbook
`reports/cnn/ContactLensDefectResults_combined22.xlsx`, and the reader-facing notebook
`notebooks/FMD_CNN_6Architectures.ipynb`.

This document exists so the workbook does not have to carry the argument. The workbook holds the numbers,
this holds what they mean.

---

## 1. Protocol

| Item | Value |
|---|---|
| Architectures | 6: `resnet18`, `resnet50`, `resnet50_inception`, `resnet50_se`, `resnet50_inception_attention`, `resnet50_inception_refine` |
| Epochs / batch / seed | 50 / 8 / 42 |
| Optimizer | SGD, lr 1e-4, momentum 0.9, Nesterov |
| Input | 224x224 |
| Our split | 1172 train / 293 test, 22 classes, one crop per source image |
| Timing | warm protocol: 2 dummy passes plus 1 discarded real-pipeline pass before the timed predict |
| New on 2026-09-15 | the lead's Architecture 3 and Architecture 4 (registry keys `resnet50_inception_attention` and `resnet50_inception_refine`); the other four rows already existed |

The four architectures the lead supplied are unchanged in our code. Verified structurally, not by eye:
`experiments/cnn/compare_lead_vs_ours.py` compares her cells against ours as ordered sequences of
(layer type, positional args, keyword args), normalising whitespace, comments, variable names, layer `name=`
strings and the one forced API rename (`LeakyReLU(alpha=...)` became `negative_slope=...` in Keras 3).
Helper blocks, assemblies and the l3/l4/l5 filter configurations are identical for all four.

---

## 2. Results on our split

| Architecture | Acc % | Macro P | Macro R | Macro F1 | Train s | Inference ms (warm) | Params |
|---|---|---|---|---|---|---|---|
| ResNet18 | 82.94 | 66.38 | 64.56 | 64.37 | 136.8 | 0.67 | not measured |
| ResNet50 | 88.40 | 69.64 | 71.66 | 70.14 | 345.4 | 1.28 | 25,716,630 |
| ResNet50 MultiLevel MultiScale | 88.05 | 72.23 | 72.36 | 70.49 | 495.0 | 1.75 | 58,547,094 |
| ResNet50 MultiLevel Attention (SE) | 87.37 | 73.29 | 70.24 | 70.98 | 380.9 | 1.51 | 50,544,246 |
| Inception + branch attention (Arch 3) | 86.01 | 71.11 | 67.68 | 67.92 | 449.7 | 1.76 | 58,744,051 |
| Inception + refined decode (Arch 4) | 88.05 | 74.52 | 74.21 | 73.64 | 2132.2 | 2.12 | 45,988,758 |

Per-class recall for all 22 classes, plus training time, is in the workbook. Confusion matrices were saved
for both new runs.

---

## 3. Cross-split comparison (teammate's split, no warmup)

| Architecture | Theirs | Ours | Delta (ours - theirs) |
|---|---|---|---|
| ResNet18 | 87.03 | 82.94 | -4.09 |
| ResNet50 | 86.69 | 88.40 | +1.71 |
| MultiLevel MultiScale | 90.44 | 88.05 | -2.39 |
| MultiLevel Attention (SE) | 89.42 | 87.37 | -2.05 |
| Inception + branch attention (Arch 3) | 88.74 | 86.01 | -2.73 |
| Inception + refined decode (Arch 4) | 91.81 | 88.05 | -3.76 |

Ranking, side by side:

| # | Theirs | Ours |
|---|---|---|
| 1 | Arch 4 (91.81) | ResNet50 (88.40) |
| 2 | MultiLevel MultiScale (90.44) | MultiLevel MultiScale (88.05) |
| 3 | MultiLevel Attention (89.42) | Arch 4 (88.05) |
| 4 | Arch 3 (88.74) | MultiLevel Attention (87.37) |
| 5 | ResNet18 (87.03) | Arch 3 (86.01) |
| 6 | ResNet50 (86.69) | ResNet18 (82.94) |

---

## 4. What the comparison shows

**4.1 Class imbalance is ruled out.** Their recall decimals give away their per-class test supports; inferred
from their own six rows they match ours exactly on 15 of 22 classes including every large one (Bubble 23,
Bubble Cluster 7, HEMA Obstruction 21, Wet Package 17, Foreign Matter 14, Fiber 12, Low Dose Obstructing 19).
The remaining differences are one image (Multiple Lenses 42 against our 41, Bubble Irregular 8 against 9,
View Obstructed 5 against 4) or unreadable because every model scored 0 or 100 there. Independently:
weighting their per-class deltas by our class sizes reproduces their overall accuracies to within 0.2 pp for
all six architectures, which cannot happen if their class mix differed.

**4.2 Duplicate leakage is ruled out on our side.** `experiments/cnn/check_split_integrity.py` on `split.csv`:
1465 crops from 1463 distinct source images, train 1172 / test 293, **0 sources present on both sides**,
0 leaked crops, crops per source 1.00 on both sides, 0 identical crop filenames across sides. One crop per
source means a source cannot straddle the split, so our numbers carry no duplicate inflation.

**4.3 The gap is 5 to 12 images out of 293.** At 293 test images, 1 pp is 2.93 images, so the gaps above are
5 to 12 images against a sampling standard error of about 1.9 pp per estimate, and at least that for the
difference between two overlapping 20 percent draws. Gaps of 2.0 to 4.1 pp sit at roughly 1 to 2 standard
errors: this is what a different random 20 percent draw produces by itself.

**4.4 It is not run noise.** With the split held fixed, runs reproduce exactly (in the detection line the same
control landed on identical numbers three times). So the cross-split variation is the split, and only the split.

**4.5 Where the luck sits, and why it is not a model property.**

| Class | n | Architectures where ours is worse | Mean gap |
|---|---|---|---|
| Wet Package | 17 | 6 of 6 | -21.6 pp |
| Bubble Irregular | 8-9 | 5 of 6 | -25.2 pp |
| Fiber | 12 | 5 of 6 | -19.4 pp |
| Multiple Lenses | 41 | 5 of 6 | -2.1 pp |
| HEMA Obstruction | 21 | 0 of 6 | +4.0 pp (ours better) |
| Foreign Matter | 14 | 0 of 6 | +6.0 pp (ours better) |
| Low Dose Obstructing | 19 | 1 of 6 | +4.4 pp (ours better) |

A gap that repeats across six independently trained models cannot be a property of the model. The pattern is
also anti-correlated (they win where we lose and the reverse on HEMA Obstruction, Foreign Matter and Low Dose
Obstructing), which is what two overlapping draws from the same image pool look like. For scale, one image in a
17-image class is 5.9 pp, so a 20-point swing there is 3 to 4 pictures.

**4.6 What survives the split change.** The four Inception-family architectures keep the same internal order on
both splits: MultiLevel MultiScale and Arch 4 at the top, MultiLevel Attention in the middle, Arch 3 last. The
two plain baselines do not hold at all (ResNet50 first for us and last for them, ResNet18 fifth for them and
last for us). Only within-split comparisons should be read as architecture results.

---

## 5. Architecture conclusions

**Arch 4, Inception plus refined decode: the best-balanced model of the six.** Joint top accuracy on our split
(88.05, level with MultiLevel MultiScale and behind only plain ResNet50 at 88.40), best of all six on every
macro measure (recall 74.21, precision 74.52, F1 73.64 against 72.36 / 72.23 / 70.49 for MultiLevel
MultiScale), and top of the table on the teammate's split. It reaches that with 12.6M fewer parameters
(45.99M against 58.55M) because the depthwise plus 1x1 decode replaces the 2048-channel transposed
convolution, the largest layer in the parent design. The price is speed: 4.3x the training time
(2132 s against 495 s per 50 epochs) and the slowest inference of the six (2.12 ms against 1.75 warm).
Fewer parameters but more wall-clock, because the depthwise step over a 14x14x2048 tensor is
bandwidth-bound while the transposed convolution is dense and cuDNN-tuned. Per-class against MultiLevel
MultiScale it gains on the small-support classes (Bubble Cluster 42.9 to 85.7 on 7 images, Bubble Irregular
22.2 to 55.6 on 9) and gives back Fiber (91.7 to 58.3 on 12) and part of Low Dose Obstructing (100 to 89.5
on 19).

**Arch 3, attention inside every Inception branch: last of the four on both splits.** 86.01 against 88.05 on
our split (-2.04) and 88.74 against 90.44 on the teammate's (-1.70). It is not a weight problem: +0.197M
parameters against the plain design, the same training time, the same inference. And the ordering is
monotone on both splits: plain MultiLevel MultiScale beats SE on the taps, which beats SE inside the
branches. On two independent splits, the further attention is woven into the fusion, the worse the model
does. The plausible reading is that the three taps are already selected pretrained features, so re-weighting
channels inside every branch adds parameters and nonlinearity without adding information, with 1172 training
images to learn the gates from.

**The two plain baselines: no conclusion survives the split change.** Their ranking reverses between splits, so
ResNet18 and ResNet50 should be quoted only as within-split reference points.

---

## 6. Warmup and the inference column

- Warmup changes the **per-image timing only**. Accuracy, per-class recall and the confusion matrix are
  warmup-independent: the warmup predictions are discarded and inference does not update weights. This is
  documented in `reports/cnn/OOI_CNN_Analysis_CORRECTED_20260908.md` section 6.3.
- The workbook's cold-start column is an **estimate** (marked with a tilde): warm time plus that architecture's
  one-time cost from our 2026-09-08 decomposition divided by the 293 test images. Measuring it on this split is
  open, and it is blocked on saving trained weights.
- The teammate's per-image numbers are **excluded** from the comparison for this reason: their run had no
  warmup, so their ms/img carries a one-time process cost. Their internal architecture-to-architecture ratios
  also look inconsistent (their ResNet18 took 228 s against their ResNet50 352 s, where ours are 137 s and
  345 s), which points at different machine conditions, so their timing columns are not a cross-machine
  baseline either.

---

## 7. Artifacts

| Artifact | Where |
|---|---|
| Workbook, six rows plus the comparison sheet | `reports/cnn/ContactLensDefectResults_combined22.xlsx` (previous four-row version archived under `reports/cnn/archive/`) |
| Teammate's numbers as data | `experiments/cnn/teammate_split_20260915.json` |
| Reader-facing notebook | `notebooks/FMD_CNN_6Architectures.ipynb`, generated by `experiments/cnn/make_notebook.py` |
| Workbook builders | `build_combined22_landing_pad.py` (Sheet1), `build_teammate_comparison.py` (Sheet2) |
| Verification | `compare_lead_vs_ours.py` (structure diff), `check_split_integrity.py` (leakage check) |
| Runner for the two new architectures | `run_combined22_two_new.sh` |
| Confusion matrices and metrics | one per run, on the VM under `combined_22_runs/<arch>/epochs_50/`; local mirrors under `runs/cnn/combined22/` (gitignored) |

---

## 8. Open items

1. Save the trained weights. `model_training.py` writes metrics and a confusion matrix but no checkpoint, so no
   finished run can be reused or re-measured without retraining. This blocks items 2 and 3.
2. Measure the real cold-start inference on our split and replace the estimated column.
3. Cross-evaluate: our models on their test images and theirs on ours. This is the decisive test of test-set
   difficulty against train composition, and it needs item 1.
4. A second split of our own, to give the split-variance band. Until then, single-split deltas under about
   2 points (7 images) should not be treated as resolvable.
5. Run the two new architectures on the 12-class Lens Presentation set if that workbook is to list six rows.
6. Tiny-support classes (Bubble On Edge 3 images, Bubble Scatter 1, Extraneous Polymer 3 in our split) are
   noise in both splits and should not be quoted in either direction.
