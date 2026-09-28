---
title: First multilabel LP run (ml_resnet50_base), results and verification
date: 2026-09-28
type: result
status: active
where: reports/multilabel/ml_resnet50_base_run_20260928.md
---

# First multilabel LP run, 2026-09-28

One round of execution of the multi-label ResNet50 on the 5 lens-presentation tags,
as asked by the lead ("please go for one round of execution"). The architecture
works. Config matches the notebook the lead holds: ResNet50 ImageNet weights,
BCEWithLogitsLoss, SGD lr 1e-4, momentum 0.9, Nesterov, no warmup, batch 8,
50 epochs, seed 42, fixed schedule with no early stopping (two-way 80/20, no
validation set), 224x224, no augmentation, all 3,377 LP-tagged images.

## Headline (test set, 677 images, threshold 0.5)

| Metric | Value |
|---|---|
| Macro AUPRC (metric of record) | **0.90454** |
| Macro F1 | 0.80826 |
| Micro precision / recall | 0.99704 / 0.94390 |
| Hamming loss | 0.01241 (12.4 errors per 1,000 label cells) |
| Exact match ratio | 0.93944 (636 of 677 images fully correct) |

Training: 50 epochs at 9.8 s/epoch on the A100 (about 8 minutes), final train
loss 0.037. GPU was free at launch (0 MiB used) and released after.

## Per-class results

| Class | Test support | Precision | Recall | F1 | AUPRC |
|---|---|---|---|---|---|
| Cavity Off Center (P1_COC) | 37 | 1.000 | 0.946 | 0.972 | 1.000 |
| Folded Lens (P1_FL) | 36 | 0.667 | **0.056** | 0.103 | 0.523 |
| Multiple Lenses (P1_ML) | 289 | 0.997 | 1.000 | 0.998 | 1.000 |
| Missing Primary Package (P1_MPP) | 286 | 1.000 | 1.000 | 1.000 | 1.000 |
| Missing Lens (P1_NL) | 65 | 1.000 | 0.938 | 0.968 | 1.000 |

Confusion counts per class (TP/FP/FN/TN, threshold 0.5):
P1_COC 35/0/2/640, P1_FL 2/1/34/640, P1_ML 289/1/0/387, P1_MPP 286/0/0/391,
P1_NL 61/0/4/612.

## The one weak class, read before anyone asks

Folded Lens is the failure, and it is the failure the design doc predicted.
Design risk (section 8): "Folded Lens never appears without Multiple Lenses in
this export (178 of 178), so a model may learn the co-occurrence instead of the
folded-lens appearance." That is what happened: the model predicts Multiple
Lenses almost perfectly (289/289 recall), then defaults to not firing the
separate Folded Lens output. Of the 36 true Folded Lens test images, the FL
score is negative at 0.5 in almost all cases (median -0.44); only 2 clear the
0.5 threshold. Lowering the FL threshold to 0.1 lifts recall to 0.31, so the
signal exists in the scores but is weak. The raw scores are saved
(test_predictions.npz), so any threshold can be read without a re-run.

Not a data bug: the split is verified leak-free (below), and the class is simply
2 per cent of labels. The levers if asked: pos_weight on FL, reliable-only
training, or more FL examples (annotation-side, since only 178 exist in the
whole export).

## Verification chain (what makes these numbers trustworthy)

1. Split verified independently, twice, by a dedicated 15-check script
   (verify_split_80_20.py, written for this run): row counts 2700/677 (79.95 /
   20.05 per cent), all five per-class totals match the annotation audit
   (183/178/1442/1427/325), positives per split match the frozen split meta,
   no duplicate paths, no path in both splits, **zero md5 group leaks** (the 34
   two-folder pictures and 27 renamed twins cannot straddle the split), the
   delivered dataframe agrees with the split file row for row, the test set is
   identical to the approved 3-way variant's test set, every label matches the
   master labels.csv, and the Folded Lens within Multiple Lenses co-occurrence
   holds at 178/178. Ran clean on the local repo and again on the VM copy of
   the files after transfer. One finding during verification: the dataframe's
   internal split column also carves a 507-image validation set inside the 80
   per cent; the run correctly ignores it (split_named column, two-way design,
   no val set, fixed 50 epochs), and no val image reaches test.
2. Pre-flight on the VM, in order: GPU free (A100 80GB, 0 MiB, no compute
   apps), torch 2.6.0+cu124 and CUDA available as pranayp, files staged and
   md5-checked byte-identical local to VM, split re-verified on the VM copy,
   then a 2-step smoke on 8 real training images (caught and fixed one
   smoke-only bug: the smoke path skipped moving the batch to the GPU; fixed,
   re-smoked, PASS).
3. After the run: every headline metric recomputed from the raw prediction
   dump by a second script (verify_run_20260928.py, 12 checks) and matched the
   run's metrics.json exactly; the npz rows proven identical to the 677 test
   rows of the split file; all four artifacts pulled back to the repo mirror
   md5-identical to the VM originals.

## Artifacts

- Workbook for the lead: `reports/multilabel/FMD_MultiLabel_Run_20260928.xlsx`
  (run summary, per-class metrics, confusion counts, epoch history with the
  loss curve, and a metric guide).
- VM: /home/pranayp/yolo_ooi/multilabel_lp_20260928/runs/ml_resnet50_base_20260928/
  (best.pt weights, history.csv, metrics.json, test_predictions.npz) and the
  training log train_ml_base.log.
- Repo mirror: run/multilabel_lp_20260928/ (metrics.json, history.csv,
  test_predictions.npz, train log; md5-checked against the VM).
- Code: experiments/multilabel_resnet50/train.py (updated this run: SGD option
  matching the lead's notebook, two-way no-val mode, full metric suite, raw
  prediction dump), verify_split_80_20.py, verify_run_20260928.py.
- Registry: experiments/multilabel_resnet50/registry.json, row ml_resnet50_base
  moved planned to done with these numbers.

## What this run does and does not claim

- It proves the multi-label architecture trains and scores end to end on real
  data. That was the ask.
- The numbers are a baseline of record, single seed (42), no val set, fixed 50
  epochs. Not comparable to any detection arena (different task, label space,
  registry comparability note).
- Four of five classes are at or near ceiling. The macro numbers are dragged by
  Folded Lens alone; macro F1 without FL would be 0.985.
- Next levers if she asks for more: ml_resnet50_reliable and ml_resnet50_posw
  (registry rows already exist, planned), a threshold sweep for FL from the
  saved scores, or the same run with early stopping on the internal 507-image
  val carve-out. None launched: one round of execution was the ask.
