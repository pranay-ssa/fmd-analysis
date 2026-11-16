---
title: Detector dataset for Experiment 2
date: 2026-11-10
type: result
status: active
where: run/detector_20261110/README.md
---

# Detector dataset for Experiment 2

Built on the VM at `/data/FMD_Data_26082026/fmd_detector_20261110` from the frozen split
`run/split_20261103_v8/split_70_15_15.csv` (md5 `1a71d66d2de384cf47a3fcf7d9115baa`) and the
annotation of record `run/eda_full_20261029/resolved_labels.csv`, rows with `shape_kind == box`.

- Seven classes: Bubble, Bubble Cluster, Wet Package, Fiber, Extraneous Polymer, HEMA, Foreign
  Matter. Bubble folds Bubble Irregular and Stretched Bubble; HEMA folds HEMA Obstruction and HEMA
  Fragment. Surface Groove has no pictures.
- 7,470 image symlinks and 7,470 label files, 41 MB. Image names are content md5 values.
- Pictures with boxes: 1,563 train, 341 validation, 343 test. Empty labels: 3,676, 769, 778.
- `data_all.yaml` uses every split picture. `data_objects.yaml` uses only the 1,563 training pictures
  with boxes, for the boxed-only arm.
- `dataset_counts.json` is the builder's record. `dataset_verify.txt` is the independent verifier
  output; it exits 0.

The builder is `vm/ops/build_fmd_detector_dataset.py`; the verifier is
`vm/ops/verify_fmd_detector_dataset.py`. No GPU time was spent.

GPU checked on 10 November at 05:58 UTC: 38,445 MiB in use at 94% by srikantht's YOLO training, and
no pranayp GPU process. The GPU freed at 07:33 UTC. The watcher waited 10 minutes and started the all
arm at 07:43 UTC as pranayp, PID 287348. It finished at 09:51 UTC after 7,760 s (2 h 9 min) and 100
epochs. The boxed-only arm started at 10:10 UTC, PID 301512, and finished at 10:57 UTC after 2,815 s
(46 min 55 s) and 100 epochs; best epoch 82.

## Result: all pictures, primary arm

Test split, `best.pt` (epoch 96), one read. No threshold tuning on test.

| Class | Test pictures | Instances | Precision | Recall | F1 | AP50 | AP50-95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bubble | 325 | 4,249 | 0.557 | 0.757 | 0.642 | 0.697 | 0.388 |
| Bubble Cluster | 170 | 493 | 0.315 | 0.233 | 0.268 | 0.178 | 0.051 |
| Wet Package | 47 | 202 | 0.494 | 0.426 | 0.457 | 0.368 | 0.158 |
| Fiber | 58 | 83 | 0.389 | 0.054 | 0.095 | 0.073 | 0.023 |
| Extraneous Polymer | 17 | 18 | 0.185 | 0.056 | 0.085 | 0.031 | 0.004 |
| HEMA | 27 | 27 | 0.648 | 0.815 | 0.722 | 0.759 | 0.498 |
| Foreign Matter | 112 | 400 | 0.299 | 0.338 | 0.317 | 0.216 | 0.073 |
| All | 1,121 | 5,472 | 0.412 | 0.383 | - | 0.332 | 0.171 |

Bubble carries the detector. HEMA is strong on only 27 test instances. Bubble Cluster, Fiber and
Extraneous Polymer are weak, with 493, 83 and 18 test instances respectively. The validation best was
epoch 96 at 0.1478 mAP50-95; the test figure is 0.1707 on a different population, so the two are not
a like-for-like gain.

`run.json` records `metrics.primary` 0.1707. Its per-class rows were repaired after the driver asked
for summary keys that ultralytics 8.4 does not return; the primary and overall numbers are unchanged.
`test_per_class.csv` holds the table above. Full weights and plots stay on the VM.

## Pass/fail block on the all-pictures arm

The detector's object scores were combined with the Experiment 1 lens columns. Object cuts were
chosen on validation only, by picture-level F1 per class, and applied once to test. Lens cuts are the
Experiment 1 chosen cuts.

| Rule | Cuts | Fail caught | Clear passed | Bubble passed | Overall pass |
|---|---|---:|---:|---:|---:|
| Bubble and Cluster pass | 0.5 | 730 of 768 | 316 of 317 | 21 of 36 | 337 of 353 |
| Bubble and Cluster pass | chosen | 746 of 768 | 316 of 317 | 24 of 36 | 340 of 353 |
| Only Bubble passes | 0.5 | 730 of 768 | 316 of 317 | 16 of 26 | 332 of 343 |
| Only Bubble passes | chosen | 751 of 768 | 316 of 317 | 10 of 26 | 326 of 343 |

Object cuts chosen on validation: Bubble 0.04, Bubble Cluster 0.03, Wet Package 0.16, Fiber 0.04,
Extraneous Polymer 0.05, HEMA 0.23, Foreign Matter 0.15. They are low because they maximise
per-class presence F1. Under the only-Bubble rule the 0.03 Cluster cut makes almost every bubble
picture fire Cluster, so more bubble-only pictures fail than at 0.5. That is a cut-objective issue,
not a detector AP issue. The Bubble-and-Cluster rule is insensitive to it because Cluster is a pass
class.

Outputs: `passfail_metrics.json`, `thresholds_exp2.json`, `passfail_test.csv`. The test labels were
read once for this endpoint, without choosing any cut on test.

## Result: boxed-only comparison arm

Test split, `best.pt` (epoch 82), one read. The same 1,121 test pictures and 5,472 boxes as the
primary arm; only the training population changed.

| Arm | mAP50-95 | mAP50 | Precision | Recall | Best epoch | Train time |
|---|---:|---:|---:|---:|---:|---:|
| All pictures, primary | 0.1707 | 0.3317 | 0.412 | 0.383 | 96 | 7,760 s |
| Boxed only, comparison | 0.1475 | 0.2624 | 0.290 | 0.424 | 82 | 2,815 s |

Per class AP50-95:

| Class | Test instances | All pictures | Boxed only | Difference |
|---|---:|---:|---:|---:|
| Bubble | 4,249 | 0.388 | 0.187 | -0.200 |
| Bubble Cluster | 493 | 0.051 | 0.026 | -0.025 |
| Wet Package | 202 | 0.158 | 0.137 | -0.021 |
| Fiber | 83 | 0.023 | 0.008 | -0.016 |
| Extraneous Polymer | 18 | 0.004 | 0.022 | +0.018 |
| HEMA | 27 | 0.498 | 0.589 | +0.092 |
| Foreign Matter | 400 | 0.073 | 0.063 | -0.009 |

The boxed-only arm trades precision for recall: precision falls from 0.412 to 0.290, recall rises
from 0.383 to 0.424. Bubble, the dominant class, halves. HEMA and Extraneous Polymer improve, but on
27 and 18 test instances. The overall ranking is lower.

## Pass/fail comparison

The object cuts are chosen on each arm's own validation split, so the chosen rows are not at identical
thresholds. The 0.5 rows are identical for both arms and give the clean comparison.

| Rule and cuts | Arm | Fail caught | Clear passed | Overall pass |
|---|---|---:|---:|---:|
| Bubble and Cluster, 0.5 | All pictures | 730 of 768 | 316 of 317 | 337 of 353 |
| Bubble and Cluster, 0.5 | Boxed only | 738 of 768 | 307 of 317 | 328 of 353 |
| Bubble and Cluster, chosen | All pictures | 746 of 768 | 316 of 317 | 340 of 353 |
| Bubble and Cluster, chosen | Boxed only | 743 of 768 | 270 of 317 | 293 of 353 |
| Only Bubble, chosen | All pictures | 751 of 768 | 316 of 317 | 326 of 343 |
| Only Bubble, chosen | Boxed only | 752 of 768 | 141 of 317 | 153 of 343 |

At the equal 0.5 threshold the boxed arm catches 8 more failing pictures, but wrongly fails 9 more
Clear pictures and passes 9 fewer pictures overall. At its own chosen cuts it catches 3 fewer fails
and wrongly fails 47 Clear pictures, so it passes 47 fewer pictures overall. The only-Bubble rule is
much worse for the boxed arm because its chosen Cluster cut, 0.12, fires on Clear pictures.

**Reading.** The 3,676 background pictures are doing specificity work. Removing them makes the
detector fire on empty frames, and that shows up as Clear false fails. The all-pictures arm stays the
production choice. The boxed-only arm is not a better detector, only a more sensitive one.

One caveat: at a fixed 100 epochs the boxed arm takes 196 batches per epoch against 655, so it also
has about one third of the optimizer steps. The comparison is therefore the practical recipe, not a
pure background ablation. The direction is consistent at both 0.5 and the chosen cuts, and the
all-pictures arm wins on overall AP and on Clear specificity.

Outputs for the boxed arm: `run.json`, `test_per_class.csv`, `results.csv`, `detections_val.csv`,
`detections_test.csv`, `passfail_metrics.json`, `thresholds_exp2.json`, `passfail_test.csv`.
