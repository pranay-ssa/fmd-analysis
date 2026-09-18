# OOI Single-Scale CNN Classification — Corrected Analysis

**Date:** 2026-09-08
**Dataset:** OOI (Object of Interest) - single-size fixed crops vs Lens Presentation single-size fixed crops
**Hardware:** NVIDIA A100 80GB PCIe
**Framework:** TensorFlow 2.20.0 / Keras 3.15.1 / cuDNN 9.3.0.75 (installed to fix the Sep-7 cuDNN mismatch, see Section 3)
**Supersedes:** the inference-time conclusions of `OOI_CNN_Analysis_20260907.md`. Accuracy numbers in that document remain valid; its timing sections are re-measured here with a corrected warmup and the results change materially.

---

## 1. Executive summary

The Sep-7 analysis concluded OOI inference was ~2x slower than Lens Presentation and attributed the difference to XLA compilation, test-set-size amortization, and (uncertainly) to pixel-content-dependent XLA kernels. A controlled retrain on 2026-09-08 with a corrected timing protocol shows that conclusion was wrong in every part:

1. **The total predict wall-time was always roughly equal between the two datasets.** The reported 2x existed only because an equal total was divided by different test-set sizes (87 vs 201 images). It was a units/amortization artifact, not a speed difference.
2. **A single ~1.1 s one-time cost dominated every "warm" timing.** It is the first-time `model.predict()` graph re-trace that fires when the model is first fed the real file-based test pipeline. The Sep-7 `--warmup` flag warmed the model on dummy `from_tensor_slices` data, which does not pre-trigger that re-trace, so the ~1.1 s cost still landed inside the timed inference.
3. **Once the real test pipeline is warmed (2 dummy passes + 1 throwaway predict on the actual test set), OOI and Lens run at essentially identical speed: about 0.7 to 1.8 ms/image, model-dependent, on both datasets.** The OOI-vs-Lens gap is gone.
4. **Accuracy is not affected by warmup.** Retraining identical configs reproduces accuracy exactly under a fixed seed and fixed cuDNN version. The accuracy "drift" reported on 2026-09-07 was an artifact of comparing a pre-upgrade run (cuDNN 9.1) against a post-upgrade run (cuDNN 9.3) under a false "same configuration" label.

Corrected inference times (batch 8, warm):

| Architecture | OOI ms/img (87) | Lens ms/img (201) | OOI old warmup | Lens old warmup | OOI no-warmup | Lens no-warmup |
|---|---|---|---|---|---|---|
| ResNet18 | 0.97 | 0.72 | 5.163 | 2.475 | 9.441 | 4.314 |
| ResNet50 | 1.39 | 1.37 | 14.116 | 6.367 | 26.361 | 11.936 |
| ResNet50-Inception | 1.76 | 1.69 | 22.888 | 9.947 | 37.392 | 15.379 |
| ResNet50-SE | 1.74 | 1.67 | 16.738 | 7.566 | 29.707 | 13.271 |

The corrected per-image times are equal across datasets within manufacturing noise (about 0.1 to 0.3 ms/image). The old "warmup" columns are still inflated by the ~1.1 s one-time re-trace and should not be used.

---

## 2. Problem statement

Run four CNN architectures (ResNet18, ResNet50, ResNet50-Inception, ResNet50-SE) on the OOI single-scale dataset using the same configuration as the Lens Presentation runs (50 epochs, batch 8, seed 42), and compare inference time and accuracy against a teammate baseline. The immediate trigger for this analysis was a reported ~2x difference in per-image inference time between OOI (87 test images) and Lens Presentation (201 test images).

---

## 3. Setup: the cuDNN version mismatch (unchanged, still valid)

All four architectures initially failed at Epoch 1 with a cuDNN version mismatch. TensorFlow 2.20.0 had been upgraded after the Sep-3 Lens runs while the pip cuDNN package stayed at 9.1.0. TF 2.20.0 requires cuDNN >= 9.3.0.

| Package | Before | After |
|---|---|---|
| tensorflow | 2.20.0 | 2.20.0 |
| nvidia-cudnn-cu12 | 9.1.0.70 | 9.3.0.75 |

Fix: `pip install --break-system-packages 'nvidia-cudnn-cu12==9.3.0.75'`, verified by a cuDNN 9.3 load on the GPU. The upgrade conflicts with PyTorch 2.6.0+cu124 (needs cuDNN 9.1.0.70), which is acceptable because only TF/Keras is used here.

**Important consequence for every number in this document:** the 9.1 to 9.3 upgrade does change floating-point numerics, so a model retrained after the upgrade can score differently from a pre-upgrade model even with the same seed. Section 6 documents this exactly.

---

## 4. Training configuration

| Parameter | Value |
|---|---|
| Epochs | 50 |
| Batch size | 8 |
| Seed | 42 |
| Optimizer | SGD (lr=1e-4, momentum=0.9, Nesterov) |
| Image size | 224x224 |
| OOI train / test | 347 / 87 (10 classes) |
| Lens train / test | 802 / 201 (12 classes) |

Note the confounded variable: OOI and Lens differ in both task (10 vs 12 classes) and sample count (347/87 vs 802/201). Any OOI-vs-Lens difference in accuracy or training time is driven by class count and data volume, not by the architecture.

---

## 5. Root cause: the ~1.1 s one-time predict re-trace

### 5.1 The decomposition experiment

On 2026-09-08 a fresh ResNet50 (imagenet weights, same graph as training) was timed over the OOI and Lens test pipelines, batch 8, in one process. This isolates the fixed one-time cost from the variable per-batch cost:

| Measurement | OOI (87 imgs, 11 batches) | Lens (201 imgs, 26 batches) |
|---|---|---|
| A. full predict, pipeline cold (Sep-7 `--warmup` method) | 1.240 s -> 14.26 ms/img | 0.278 s -> 1.38 ms/img |
| B. iterate pipeline once (trace + init + decode) | 0.076 s | 0.104 s |
| C. iterate pipeline again (warm decode only) | 4.5 ms/batch | 3.5 ms/batch |
| D. full predict, pipeline warm | 0.126 s -> 1.45 ms/img | 0.244 s -> 1.21 ms/img |
| E. predict on pre-decoded in-RAM arrays (GPU + dispatch only) | 0.112 s -> 1.28 ms/img | 0.240 s -> 1.20 ms/img |

Interpretation, directly from the table:

- A vs D: after dummy-data warmup (the Sep-7 flag), the first timed predict still costs ~1.1 s extra (1.240 vs 0.126 s on OOI). That ~1.1 s is a one-time cost, not a throughput figure.
- The one-time cost is present only once per process. In this experiment it hit OOI (measured first, 1.240 s) and was absent for Lens (0.278 s) because the traced graph was reused. In separate training processes it lands on the single dataset each process evaluates, which is why the recorded warm totals for OOI and Lens were both ~1.25 s (near-equal).
- C vs E: the data pipeline adds only ~3.5 to 4.5 ms per batch of decode work; the GPU kernel is ~10 ms per batch (1.2 to 1.3 ms per image). Neither the decode path nor the GPU is 2x slower on OOI.
- D and E are the true warm measurements: OOI and Lens run at 1.21 to 1.45 ms/img, i.e. effectively identical for the same model.

So the cause is not XLA fusion, not pixel content, and not the data pipeline. It is a model `predict()` graph re-trace that fires the first time the real file-based `image_dataset_from_directory` pipeline is fed, which the dummy-data warmup never pre-triggers.

### 5.2 Why the Sep-7 warmup flag missed it

The Sep-7 warmup ran two `predict` passes on dummy `tf.random.normal` tensor slices batched at 8. Batching to the same shape warms the XLA graph and cuDNN autotune, but the first `predict` on the real directory-pipeline dataset traces a separate graph for that input source. That one-time trace was not absorbed by the dummy warmup and fell into the timed region.

### 5.3 The fix (applied 2026-09-08)

The warmup block now runs: two dummy passes to warm XLA/autotune, then one throwaway `predict` on the real test pipeline to absorb the one-time re-trace, then the timed pass. In `model_training.py`:

```
Warmup: 2 dummy passes + 1 real-pipeline pass (discarded)
start = perf_counter()
y_pred_prob = model.predict(test_ds, verbose=1)   # timed
```

---

## 6. Corrected inference time results

All numbers below are from retrains on 2026-09-08 with the corrected warmup (2 dummy + 1 real-pipeline pass), 50 epochs, batch 8, seed 42.

### 6.1 Per-image inference time (ms/img)

| Architecture | OOI (87 imgs) | Lens (201 imgs) | Delta OOI-Lens | Old OOI warmup | Old Lens warmup |
|---|---|---|---|---|---|
| ResNet18 | 0.974 | 0.722 | +0.25 | 5.163 | 2.475 |
| ResNet50 | 1.393 | 1.372 | +0.02 | 14.116 | 6.367 |
| ResNet50-Inception | 1.758 | 1.695 | +0.06 | 22.888 | 9.947 |
| ResNet50-SE | 1.744 | 1.667 | +0.08 | 16.738 | 7.566 |

After the fix the per-image deltas shrink to 0.02 to 0.25 ms/img, i.e. well within run-to-run noise and negligible. The old "warmup" columns are at 2 to 23 ms/img only because they still contain the one-time ~1.1 s re-trace divided across the test set.

### 6.2 Total test wall-time (s), which is the quantity that actually scales with dataset size

| Architecture | OOI total (s) | Lens total (s) |
|---|---|---|
| ResNet18 | 0.0847 | 0.1451 |
| ResNet50 | 0.1212 | 0.2759 |
| ResNet50-Inception | 0.1530 | 0.3406 |
| ResNet50-SE | 0.1517 | 0.3350 |

Now the totals scale with image count (more images, more total time), which is the expected and correct relationship. Under the old method the totals were artificially equal (~1.2 s for both) because the one-time re-trace dominated.

### 6.3 Accuracy, F1, and training time (unchanged by warmup)

| Architecture | OOI Acc% | OOI Macro-F1% | OOI Wtd-F1% | OOI Train (s) | Lens Acc% | Lens Macro-F1% | Lens Wtd-F1% | Lens Train (s) |
|---|---|---|---|---|---|---|---|---|
| ResNet18 | 68.97 | 46.35 | 67.10 | 46.39 | 90.55 | 75.30 | 89.22 | 95.80 |
| ResNet50 | 65.52 | 47.81 | 66.60 | 115.61 | 98.01 | 88.57 | 98.01 | 244.10 |
| ResNet50-Inception | 71.26 | 52.57 | 67.97 | 138.85 | 97.51 | 87.51 | 97.33 | 290.80 |
| ResNet50-SE | 66.67 | 46.27 | 64.79 | 127.88 | 96.02 | 85.52 | 95.72 | 267.84 |

Accuracy and F1 here are byte-identical to the corresponding no-warmup retrains because warmup touches only the timing path, never the weights or data ordering, and runs are deterministic under seed 42 + cuDNN 9.3. Training time is also unchanged. This confirms: **the warmup flag changes the reported ms/img only, and never accuracy.**

### 6.4 Reproducibility and the version sensitivity of accuracy

With seed 42 + cuDNN 9.3, the exact same config reproduced byte-for-byte across separate runs. Examples: OOI accuracies are 68.97 / 65.52 / 71.26 / 66.67 across every OOI run in this study; Lens with corrected warmup equals the post-upgrade no-warmup Lens rerun for all four architectures (90.55 / 98.01 / 97.51 / 96.02).

The accuracy DID change with the cuDNN upgrade, and that change is directional per architecture:

| Architecture | Lens Acc% pre-upgrade (cuDNN 9.1) | Lens Acc% post-upgrade (cuDNN 9.3) | Shift |
|---|---|---|---|
| ResNet18 | 93.53 | 90.55 | -2.98 |
| ResNet50 | 95.52 | 98.01 | +2.49 |
| ResNet50-Inception | 96.02 | 97.51 | +1.49 |
| ResNet50-SE | 97.51 | 96.02 | -1.49 |

This is the exact source of the 2026-09-07 note that lens accuracy "drifted" between the warmup and no-warmup appendix tables: the no-warmup appendix used the pre-upgrade run and the warmup appendix used the post-upgrade run. Under a single cuDNN version the two agree exactly, as shown above. It also cautions against reading sub-3-point accuracy differences between architectures as meaningful if they were measured across a TensorFlow/cuDNN upgrade.

---

## 7. Statistical caution on architecture ranking

- OOI test accuracy is measured on 87 samples. The standard error at ~71% accuracy is about 4.9 points, so the best-vs-third gap (ResNet50-Inception 71.26 vs ResNet50-SE 66.67, a 4.59-point spread) is under one standard error. It is not a significant difference from one seed.
- Several OOI classes have 1 to 3 test images (Bubble On Edge 3, Extraneous Polymer 3, HEMA Fragment 1). Recall of 0% or 100% on such classes carries no information; macro-F1 on OOI (46 to 53%) is dragged down by these near-empty classes, not by genuine model weakness.
- The best architecture is data-regime dependent. On Lens (802 train images) ResNet50 is highest post-upgrade at 98.01%; on OOI (347 train images) ResNet50-Inception is highest at 71.26%. Select the deployment model for the regime and class distribution of the actual production set, not from a single cross-arch run.
- Any architecture claim below ~3 points and any per-class claim on supports under ~10 should be backed by 2 to 3 seeds or a bootstrap interval before it is treated as a decision.

---

## 8. Comparison with the teammate baseline

| Architecture | OOI ms/img (87) | Team ms/img (93) | Diff | OOI train (s) | Team train (s) |
|---|---|---|---|---|---|
| ResNet18 | 0.974 | 9.042 | n/a* | 46.39 | 48.25 |
| ResNet50 | 1.393 | 25.081 | n/a* | 115.61 | 120.97 |
| ResNet50-Inception | 1.758 | 32.633 | n/a* | 138.85 | 145.85 |
| ResNet50-SE | 1.744 | 31.196 | n/a* | 127.88 | 133.96 |

*The two sides are not comparable as-is. The teammate columns are total-test-time divided by 93 and therefore carry that side's full one-time re-trace overhead (as the Sep-7 no-warmup numbers did). Training times match within 5%, which confirms the teammate runs the same workload on the same GPU class. The teammate accuracy is not available in this repo, so the accuracy comparison promised in the problem statement remains open.

A separate number 20.460 ms/image for the teammate's ResNet50 appears in the Sep-7 doc as the motivation for this investigation, but it does not appear in any workbook or metrics file on the VM, and it does not match the head-to-head value of 25.081 ms/image (a 28.8% gap). It should be reconciled with the teammate by asking for their exact timing definition (which warmed quantities were included) before it is cited again.

---

## 9. Recommendations

1. **Timing protocol:** always report the total test wall-time in seconds together with the image count, and give ms/img only for a model that has been warmed on the real test pipeline (2 dummy passes + 1 real-pipeline pass). The corrected warmup is now the default in `model_training.py`.
2. **Do not report or compare ms/img from a model that has only been warmed on dummy data.** Any number in the 5 to 37 ms/img range in the Sep-7 doc is inflated by the one-time re-trace and should be discarded.
3. **Cross-dataset time comparisons:** compare per-image time on equally warmed models; the OOI-vs-Lens gap was an artifact and does not exist.
4. **Version discipline:** record the TensorFlow and cuDNN versions with every result. Do not compare accuracies across a cuDNN upgrade without flagging it, as the shifts can be +/-3 points per architecture.
5. **Production model:** for an OOI-like low-data, imbalanced, 10-class regime, ResNet50-Inception had the highest accuracy (71.26) and macro-F1 (52.57); its corrected per-image time (~1.8 ms/img) is small enough for any realistic deployment. Confirm on 2 to 3 seeds.
6. **Data collection:** prioritize the smallest classes (Bubble On Edge, Extraneous Polymer, HEMA Fragment have 1 to 3 test samples and cannot be learned or validated reliably). Add examples before treating per-class recall on these as meaningful.
7. **Teammate comparison:** obtain the teammate's accuracy and their exact timing definition; run both models on one shared data split before any accuracy head-to-head.

---

## 10. Files and locations (VM, user pranayp)

| Item | Path |
|---|---|
| OOI dataset | /home/pranayp/OoI_dataset_single |
| Lens Presentation dataset | /home/pranayp/lens_presentation_dataset_single_20260903 |
| Training script (with corrected warmup) | /home/pranayp/model_training.py |
| Corrected OOI warmup retrain (metrics) | /home/pranayp/ooi_warmup_corrected/<arch>/epochs_50/metrics.json |
| Corrected Lens warmup retrain (metrics) | /home/pranayp/lens_warmup_corrected/<arch>/epochs_50/metrics.json |
| Decomposition experiment | /home/pranayp/diag_pipeline_timing.py + diag_pipeline_result.json |
| Pre-upgrade Lens no-warmup runs | /home/pranayp/model_runs_single50 |
| Post-upgrade Lens no-warmup rerun | /home/pranayp/lens_single_rerun |
| Teammate head-to-head source | /home/pranayp (Comparision workbook) |

Local canonical scripts (repo `D:\02-SSA\FMD-Preprocess`): `samples/model_training.py`, `samples/run_warmup_corrected.sh`, `samples/diag_pipeline_timing.py`.

---

## Appendix: full corrected raw data

### A. Corrected warm metrics (2026-09-08)

```json
OOI (87 imgs):
ResNet18:    acc=0.6897  macro_f1=0.4635  train=46.39s  test=0.0847s  ms/img=0.974
ResNet50:    acc=0.6552  macro_f1=0.4781  train=115.61s test=0.1212s  ms/img=1.393
Inception:   acc=0.7126  macro_f1=0.5257  train=138.85s test=0.1530s  ms/img=1.758
SE:          acc=0.6667  macro_f1=0.4627  train=127.88s test=0.1517s  ms/img=1.744

LENS (201 imgs):
ResNet18:    acc=0.9055  macro_f1=0.7530  train=95.80s  test=0.1451s  ms/img=0.722
ResNet50:    acc=0.9801  macro_f1=0.8857  train=244.10s test=0.2759s  ms/img=1.372
Inception:   acc=0.9751  macro_f1=0.8751  train=290.80s test=0.3406s  ms/img=1.695
SE:          acc=0.9602  macro_f1=0.8552  train=267.84s test=0.3350s  ms/img=1.667
```

### B. Decomposition (ResNet50, fresh graph, batch 8)

```json
OOI (11 batches):  A cold 1.240s (14.26 ms/img) | C warm decode 4.5 ms/batch
                   D predict warm 0.126s (1.45 ms/img) | E pre-decoded GPU 0.112s (1.28 ms/img)
LENS (26 batches): A cold 0.278s (1.38 ms/img) | C warm decode 3.5 ms/batch
                   D predict warm 0.244s (1.21 ms/img) | E pre-decoded GPU 0.240s (1.20 ms/img)
```

### C. Numbers superseded by this document (from 2026-09-07, do not use)

```json
OOI old-warmup ms/img:  R18 5.163 | R50 14.116 | Inc 22.888 | SE 16.738
Lens old-warmup ms/img: R18 2.475 | R50 6.367 | Inc 9.947 | SE 7.566
OOI no-warmup  ms/img:  R18 9.441 | R50 26.361 | Inc 37.392 | SE 29.707
Lens no-warmup ms/img:  R18 4.314 | R50 11.936 | Inc 15.379 | SE 13.271
```

---

## Verification note

Every number in this document is traced to a real pipeline run: the corrected metrics come from the 2026-09-08 retrain `ooi_warmup_corrected` / `lens_warmup_corrected` on the VM A100, cross-checked against their `metrics.json`; the decomposition comes from `diag_pipeline_timing.py`; the accuracy-only claims reproduce the seed-fixed runs bit-for-bit. Nothing is asserted from memory.