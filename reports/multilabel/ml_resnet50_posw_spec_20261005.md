---
title: Spec: ml_resnet50_posw, the pos-weight imbalance lever on the LP multilabel line
date: 2026-10-05
type: experiment
status: done
where: reports/multilabel/ml_resnet50_posw_spec_20261005.md
---

# Spec: ml_resnet50_posw (pos-weight imbalance lever)

## 1. Question

Does a per-class positive weight in the BCE loss raise Folded Lens (P1_FL) recall,
which is 0 at threshold 0.5 in the base run (F1 0.103, AUPRC 0.523), without paying
for it elsewhere on the 5-tag LP multilabel task?

This is the model-side lever named after the 2026-09-29 architecture sweep closed the
data-side question: all four notebook architectures plus the control leave FL recall at
0, because every FL image in the export also carries Multiple Lenses (178 of 178), so
the tag is always implied and plain BCE never fires it at threshold 0.5. The pos-weight
run tests the one lever that changes the loss instead of the architecture.

## 2. Provenance: the 2026-10-05 client ruling changes no label here

The client ruled that the 33 pictures named Fiber in the older library and Extraneous
Polymer in the newer folder are Extraneous Polymer going forward, with a new
two-dimensional-structure definition added to the annotation guide. This affects the
decision-stage defect classes only (Foreign Matter, Extraneous Polymer, HEMA Fragment,
Fiber in the second-stage model). Verified 2026-09-24 (`experiments/multilabel_resnet50/relabel_impact_20260924.txt`):
0 of the 31 contested pictures sit in the 3,377 LP rows; the one contested picture in
the LP set carries only Multiple Lenses. So `labels.csv`, the split and every LP number
are untouched by this ruling. What it does change: the pending rerun R4 (the class
mapping for Fiber / Extraneous Polymer) is settled in favour of Extraneous Polymer and
the per-class detection and defect-classifier figures that carried the provisional flag
can now be re-run and de-provisioned. That re-run belongs to the detection/classifier
line, not this experiment.

## 3. Run definition (one switch against the base)

| Field | Value | Same as base? |
|---|---|---|
| Script | `experiments/multilabel_resnet50/train.py` (unmodified) | yes |
| Driver | `experiments/multilabel_resnet50/run_ml_posw.py` (new, standalone) | new |
| arch | resnet50 | yes |
| labels | labels.csv, md5-logged in the run manifest | yes |
| split | splits/variant_80_20_two_way.csv, split_named, 2700/677 | yes |
| loss | BCEWithLogitsLoss + --pos-weight | **the one change** |
| pos_weight vector | P1_COC 17.4932, P1_FL 18.0141, P1_ML 1.3417, P1_MPP 1.3663, P1_NL 9.3846 | computed from the train split (n=2700), asserted by the driver before launch |
| optimizer | SGD lr 1e-4, momentum 0.9, Nesterov, wd 1e-4 | yes |
| epochs / batch / imgsz / seed | 50 / 8 / 224 / 42, workers 8 | yes |
| early stop | patience 5 on macro AUPRC (val loader empty in the two-way split, so it runs the full 50) | yes |
| reliable_only | false (all 3,377 rows) | yes |
| machine | pranayp VM (A100), `/home/pranayp/yolo_ooi/multilabel_lp_posw_20261005/` | yes |
| image root | `/home/amd100-user/FMD_Data_26082026/fmd_temp_images` | yes |

Expected cost: 50 epochs at about 10 s/epoch, about 9 to 12 minutes total.

## 4. Gates (all before training starts)

1. Split gate: split file still holds exactly 2700 train / 677 test under split_named.
2. pos-weight gate: the driver recomputes (n - pos) / pos from the train split and
   refuses to launch if any class drifts more than 0.01 from the spec vector above.
3. Smoke gate: `run_ml_posw.py --smoke` (2 optimizer steps on 8 real train images)
   must pass before the full run; the driver prints the pos_weight tensor train.py
   computes so the asserted and the applied vectors are checked against each other
   in the same log.
4. md5 gate: labels.csv and the split file hash into the run manifest before and
   after; the driver source is copied into the run dir.

## 5. Readout (what gets reported)

Primary: P1_FL precision / recall / F1 at 0.5 and AUPRC on the 677-image test set
(36 FL positives), against base (P 0.667 / R 0.056 / F1 0.103 / AUPRC 0.523).
Secondary: the other four tags' deltas, macro AUPRC (base 0.90454), macro F1
(base 0.80826), exact match (base 0.93944), and the full timing block.
Reading rules:

- The run-to-run band measured on this line (macro F1 +/-0.037, exact match +/-0.018)
  is the yardstick; deltas inside it are not claimed as effects.
- The expected trade is FL recall up against FL precision down and some exact-match
  loss (a raised FL score can flip rows that only carry ML). If FL recall moves and
  the other four tags hold, the lever works and the threshold question (raise the FL
  threshold to buy precision back) becomes the next, GPU-free step.
- If FL recall stays 0 even with weight 18, the co-occurrence explanation is
  strengthened to the point that only data (more FL examples that are not also ML)
  or the reliable-negatives row can move this class, and this line's model-side
  work closes.

## 6. Registry

Row `ml_resnet50_posw` in `experiments/multilabel_resnet50/registry.json` is `planned`
and flips to `done` when `runs/ml_resnet50_posw_20261005/metrics.json` exists and the
12-check prediction recompute passes, mirroring `run/multilabel_lp_posw_20261005/`.

## 7. Result (2026-10-05)

The run completed. Exit 0 on the pranayp VM (A100 80GB PCIe), 50 of 50 epochs at a
mean 9.99 s/epoch (499.7 s total, amp on). Best = final epoch, as expected under the
fixed schedule with no val set. Same model as base (23,518,277 params), same
labels.csv, same split_named 2700/677 carve, seed 42. Artifacts mirrored to
`run/multilabel_lp_posw_20261005/`; md5 identical to the VM for metrics.json,
history.csv and test_predictions.npz. A 24-check metric recompute from
test_predictions.npz matches metrics.json with max abs diff 4.62e-06.

### P1_FL: base vs pos-weight (test, threshold 0.5, support 36)

| Metric | base (09-28) | posw (10-05) |
|---|---|---|
| precision | 0.66667 | 0.54839 |
| recall | 0.05556 | 0.47222 |
| F1 | 0.10256 | 0.50746 |
| AUPRC | 0.52271 | 0.62153 |

FL recall moves from near zero to 0.472. The spec's expected trade is real: precision
drops from 0.667 to 0.548 (17 tp, 14 fp, 19 fn at 0.5).

### The other four tags

| Tag | Support | base P/R/F1 | posw P/R/F1 | AUPRC |
|---|---|---|---|---|
| P1_COC | 37 | 1.0 / 0.946 / 0.972 | 0.925 / 1.0 / 0.961 | 1.0 |
| P1_ML | 289 | 0.997 / 1.0 / 0.998 | 1.0 / 1.0 / 1.0 | 1.0 |
| P1_MPP | 286 | 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 | 1.0 |
| P1_NL | 65 | 1.0 / 0.938 / 0.968 | 1.0 / 0.985 / 0.992 | 1.0 |

No class pays for the FL gain. COC trades a little precision for full recall; NL and
ML improve slightly.

### Headlines against the noise band

| Metric | base | posw | delta | band |
|---|---|---|---|---|
| macro AUPRC | 0.90454 | 0.92431 | +0.020 | n/a |
| macro F1 | 0.80826 | 0.89215 | +0.084 | 0.037 |
| exact match | 0.93944 | 0.94535 | +0.006 | 0.018 |
| hamming | 0.01241 | 0.01093 | -0.001 | n/a |
| micro P / R | - | - | 0.976 / 0.972 | n/a |

The band is the run-to-run spread measured on 2026-09-29 (control re-run, same config,
new session): macro F1 moves 0.037, exact match 0.018. The macro F1 gain of +0.084 is
more than double that band, so the pos-weight effect is claimed as real. Macro AUPRC
(+0.020) and exact match (+0.006) sit inside or near the band and are not claimed as
effects on their own.

### Interpretation

The lever works and is reported, but it is a band-aid. All 178 FL images in the export
also carry Multiple Lenses, so under plain BCE the loss economics never fire FL at
threshold 0.5 (the 2026-09-29 sweep proved this: all four notebook architectures plus
the control leave FL recall at 0). Raising the FL positive weight to 18 buys recall by
overriding that economics; it does not create information. The real fix is data: more
Folded Lens examples that are not also Multiple Lenses, so the class becomes learnable
as an appearance instead of being recoverable only through the loss. Until such data
exists, this line's model-side work on FL is closed.

### Threshold caveat

There is no validation set (the frozen two-way 80/20 decision). Tuning the FL
threshold on the test set would leak, so no tuned threshold is reported. Any tuned
threshold needs a third split first.
