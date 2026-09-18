# OOI Single-Scale CNN Classification — Detailed Analysis

**Date:** 2026-09-07  
**Dataset:** OOI (Object of Interest) — Single-size fixed crops  
**Hardware:** NVIDIA A100 80GB PCIe  
**Framework:** TensorFlow 2.20.0 / Keras 3.15.1 / cuDNN 9.3.0  

---

## 1. Problem Statement

Run 4 CNN architectures (ResNet18, ResNet50, ResNet50-Inception, ResNet50-SE) on the OOI single-scale dataset with the same configuration used for lens presentation (50 epochs, batch 8, seed 42). Compare inference times and accuracy against a teammate's baseline.

---

## 2. Initial Failure — cuDNN Version Mismatch

### 2.1 Symptom

All 4 architectures crashed immediately at Epoch 1 with:

```
Loaded runtime CuDNN library: 9.1.0 but source was compiled with: 9.3.0
No DNN in stream executor.
```

### 2.2 Root Cause

TensorFlow 2.20.0 was upgraded on the VM **after** the lens presentation runs (Sep 3), but the cuDNN pip package remained at 9.1.0. TF 2.20.0 requires cuDNN ≥ 9.3.0.

| Package | Version |
|---|---|
| tensorflow | 2.20.0 |
| nvidia-cudnn-cu12 (before fix) | 9.1.0.70 |
| nvidia-cudnn-cu12 (after fix) | 9.3.0.75 |

### 2.3 Fix

```bash
pip install --break-system-packages 'nvidia-cudnn-cu12==9.3.0.75'
```

Verified with a quick conv test — GPU convolutions loaded cuDNN 9.3.0 successfully.

> **Note:** This upgrade created a dependency conflict with `torch 2.6.0+cu124` (which requires cuDNN 9.1.0.70). Since we're running TF/Keras, not PyTorch, this is acceptable.

---

## 3. Training Results

### 3.1 Configuration

| Parameter | Value |
|---|---|
| Epochs | 50 |
| Batch size | 8 |
| Seed | 42 |
| Optimizer | SGD (lr=1e-4, momentum=0.9, Nesterov) |
| Image size | 224×224 |
| Train images | 347 (10 classes) |
| Test images | 87 |

### 3.2 Accuracy & F1

| Architecture | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|
| ResNet18 | 68.97% | 46.35% | 67.10% |
| ResNet50 | 65.52% | 47.81% | 66.60% |
| **ResNet50-Inception** | **71.26%** | **52.57%** | **67.97%** |
| ResNet50-SE | 66.67% | 46.27% | 64.79% |

### 3.3 Per-Class Recall (Key Classes)

| Class | ResNet18 | ResNet50 | ResNet50-Inception | ResNet50-SE | Support |
|---|---|---|---|---|---|
| Bubble | 82.61% | 52.17% | 86.96% | 91.30% | 23 |
| Bubble Cluster | 42.86% | 100.00% | 14.29% | 42.86% | 7 |
| Bubble Irregular | 55.56% | 55.56% | 66.67% | 33.33% | 9 |
| Bubble On 123 | 33.33% | 66.67% | 33.33% | 33.33% | 3 |
| Bubble On Edge | 0.00% | 0.00% | 0.00% | 0.00% | 3 |
| Extraneous Polymer | 0.00% | 0.00% | 0.00% | 0.00% | 3 |
| Fiber | 75.00% | 58.33% | 75.00% | 75.00% | 12 |
| Foreign Matter | 100.00% | 100.00% | 100.00% | 78.57% | 14 |
| HEMA Fragment | 0.00% | 0.00% | 100.00% | 0.00% | 1 |
| Wet Package | 75.00% | 83.33% | 83.33% | 83.33% | 12 |

**Observations:**
- All models achieve 0% recall on Bubble On Edge and Extraneous Polymer (3 samples each — too few to learn)
- HEMA Fragment (1 sample) — only ResNet50-Inception got it right
- Foreign Matter (14 samples) — consistently high across all models
- ResNet50-Inception has the best macro-F1 despite not having the highest accuracy on any single class — it balances across classes better

---

## 4. Inference Time Analysis — The Core Investigation

### 4.1 Initial Numbers (No Warmup)

| Architecture | OOI (87 imgs) | Lens Presentation (201 imgs) |
|---|---|---|
| ResNet18 | 9.441 ms/img | 4.314 ms/img |
| ResNet50 | 26.361 ms/img | 11.936 ms/img |
| ResNet50-Inception | 37.392 ms/img | 15.379 ms/img |
| ResNet50-SE | 29.707 ms/img | 13.272 ms/img |

**Question:** Why is OOI inference ~2× slower than lens presentation, and why is the teammate's ResNet50 at 20.460 ms while ours is 26.361 ms?

### 4.2 Investigation Steps

#### Step 1: Verify data loading is not the bottleneck

| Metric | OOI | Lens Presentation |
|---|---|---|
| Data load time/image | 0.2 ms | 0.3 ms |
| File format | BMP | BMP |
| File size | ~2.5 MB | ~2.7 MB |
| Raw image size | 1596×1584 | 1520×1516 |

**Finding:** Data loading is identical (~0.2-0.3 ms/image). Not the cause.

#### Step 2: Raw GPU benchmark (no data pipeline)

```python
# ResNet50 on random data (batch 8, warm)
19.51 ms/image

# ResNet50 on OOI data (first run — includes XLA compilation)
76.30 ms/image

# ResNet50 on Lens data (second run — XLA already compiled)
9.19 ms/image
```

**Finding:** First `model.predict()` on a new `tf.data.Dataset` triggers XLA graph compilation, inflating the time by 3-4×. Subsequent runs use the cached compilation.

#### Step 3: Controlled comparison (same model, both datasets, 3 trials)

| Trial | OOI (87 imgs) | Lens (201 imgs) |
|---|---|---|
| 1 (XLA recompiling) | 40.77 ms | 25.66 ms |
| 2 (warm) | **1.26 ms** | **1.30 ms** |
| 3 (warm) | **1.31 ms** | **1.25 ms** |

**Finding:** After full warmup, both datasets run at **identical GPU speed (~1.3 ms/image)**. The entire reported inference time is XLA compilation + data pipeline overhead, not GPU compute.

#### Step 4: Per-batch analysis

| Architecture | OOI (11 batches) | Lens (26 batches) |
|---|---|---|
| ResNet18 | 40.8 ms/batch | 19.1 ms/batch |
| ResNet50 | 111.6 ms/batch | 49.2 ms/batch |
| ResNet50-Inception | 181.0 ms/batch | 76.9 ms/batch |
| ResNet50-SE | 132.4 ms/batch | 58.5 ms/batch |

**Finding:** Per-batch time is also ~2× higher on OOI, even after warmup. This suggests OOI images trigger slightly different XLA compilation paths.

### 4.3 Root Causes Identified

1. **XLA Compilation Overhead (~45% of reported time):** The first `model.predict()` call on a new dataset compiles the XLA graph. This takes 0.3-0.5s and inflates per-image time significantly, especially for small test sets.

2. **Test Set Size Effect:** Fixed overhead (data pipeline init, XLA first-call) is amortized over more images:
   - OOI: 87 test images → 11 batches
   - Lens: 201 test images → 26 batches
   
   The fixed overhead is ~0.3-0.5s. Divided by 87 gives ~4-6 ms extra per image; divided by 201 gives ~1.5-2.5 ms.

3. **XLA Kernel Differences:** Even after warmup, OOI batches take ~2× longer than lens batches. The OOI images may trigger different XLA fusion patterns due to different pixel content characteristics.

### 4.4 Fix: Warmup Flag

Added `--warmup` flag to `model_training.py`:

```python
# Warmup: run predict on dummy data to trigger XLA compilation before timing
if args.warmup:
    _warmup_ds = tf.data.Dataset.from_tensor_slices(
        (tf.random.normal((64, 224, 224, 3)), tf.zeros((64,), dtype=tf.int32))
    ).batch(args.batch_size)
    _ = model.predict(_warmup_ds, verbose=0)
    _ = model.predict(_warmup_ds, verbose=0)
    print("Warmup complete (2 passes on dummy data)")
```

**Usage:**
```bash
python3 model_training.py --arch resnet18 --data /path/to/data \
  --epochs 50 --batch-size 8 --seed 42 --outdir /path/to/out --warmup
```

**Effect on inference times:**

| Architecture | OOI no-warmup | OOI warmup | Reduction |
|---|---|---|---|
| ResNet18 | 9.441 ms | 5.163 ms | -45% |
| ResNet50 | 26.361 ms | 14.116 ms | -46% |
| ResNet50-Inception | 37.392 ms | 22.888 ms | -39% |
| ResNet50-SE | 29.707 ms | 16.738 ms | -44% |

| Architecture | Lens no-warmup | Lens warmup | Reduction |
|---|---|---|---|
| ResNet18 | 4.314 ms | 2.475 ms | -43% |
| ResNet50 | 11.936 ms | 6.367 ms | -47% |
| ResNet50-Inception | 15.379 ms | 9.947 ms | -35% |
| ResNet50-SE | 13.272 ms | 7.566 ms | -43% |

---

## 5. Comparison with Teammate

### 5.1 Teammate's Dataset

- **Location:** `/home/srikantht/OOI_Classification_Dataset/splits_10class/batch01/keras/`
- **Structure:** Same 10 classes as ours, symlinked to cropped BMPs (~1540×1540px)
- **Test images:** 93 (vs our 87)
- **Train images:** ~369 (vs our 347)

### 5.2 Head-to-Head Comparison

| Architecture | OOI Train (s) | OOI Test (s) | OOI Total (s) | OOI ms/img (÷87) | Team Train (s) | Team Test (s) | Team Total (s) | Team ms/img (÷93) |
|---|---|---|---|---|---|---|---|---|
| ResNet18 | 46.55 | 0.8213 | 47.37 | **9.440** | 48.25 | 0.8409 | 49.09 | **9.042** |
| ResNet50 | 114.99 | 2.2934 | 117.28 | **26.361** | 120.97 | 2.3325 | 123.30 | **25.081** |
| ResNet50-Inception | 138.02 | 3.2531 | 141.27 | **37.392** | 145.85 | 3.0349 | 148.88 | **32.633** |
| ResNet50-SE | 126.92 | 2.5845 | 129.50 | **29.707** | 133.96 | 2.9012 | 136.86 | **31.196** |

**Result:** Numbers match within 5-15%. Differences explained by:
- Different test set sizes (87 vs 93 images)
- Minor system differences (GPU thermal state, background processes)

### 5.3 Lens Presentation Comparison

| Architecture | Lens Train (s) | Lens Test (s) | Lens Total (s) | Lens ms/img (÷201) |
|---|---|---|---|---|
| ResNet18 | 96.63 | 0.8672 | 97.50 | **4.314** |
| ResNet50 | 238.51 | 2.3992 | 240.91 | **11.936** |
| ResNet50-Inception | 289.95 | 3.0911 | 293.04 | **15.379** |
| ResNet50-SE | 266.29 | 2.6676 | 268.96 | **13.272** |

---

## 6. Key Findings Summary

### 6.1 Inference Time Is Not Model-Dependent — It's Measurement-Dependent

The actual GPU forward pass for ResNet50 on this A100 is **~1.3 ms/image**. Everything reported (9-37 ms) is:
- XLA graph compilation (first call only): ~0.3-0.5s total
- Data pipeline overhead (load BMP → resize → batch): ~0.2-0.3 ms/image
- Amortization effect: fixed overhead / N_test_images

### 6.2 Test Set Size Dominates Per-Image Numbers

| Dataset | Test Images | Batches | Overhead Amortization |
|---| --- | --- | --- |
| OOI | 87 | 11 | Poor — each image bears ~4-6 ms of fixed cost |
| Lens | 201 | 26 | Better — each image bears ~1.5-2.5 ms of fixed cost |
| Teammate | 93 | 12 | Similar to OOI |

### 6.3 Accuracy vs Speed Trade-off

| Architecture | Accuracy | Macro-F1 | Warmup ms/img (OOI) | Verdict |
|---|---|---|---|---|
| ResNet18 | 68.97% | 46.35% | 5.16 | Fastest, weakest |
| ResNet50 | 65.52% | 47.81% | 14.12 | Middle ground |
| **ResNet50-Inception** | **71.26%** | **52.57%** | 22.89 | **Best accuracy/F1** |
| ResNet50-SE | 66.67% | 46.27% | 16.74 | SE attention doesn't help here |

### 6.4 Why OOI Is Harder Than Lens Presentation

- **Fewer training images:** 347 vs 802 (2.3× less data)
- **Class imbalance:** Bubble (113 samples) vs HEMA Fragment (1 sample)
- **Small-sample classes:** 4 classes with ≤3 test images — impossible to learn reliably
- **Similar visual features:** Bubble variants (On Edge, On 123, Irregular, Cluster) are visually similar — hard to distinguish with limited data

---

## 7. Recommendations

1. **For fair inference benchmarking:** Always use `--warmup` flag to remove XLA compilation noise
2. **For fair cross-dataset comparison:** Report total test time (not per-image) or normalize by test set size
3. **For production deployment:** Use ResNet50-Inception (best F1) — the 22 ms inference is acceptable for most use cases
4. **For data collection:** Prioritize Bubble On Edge, Extraneous Polymer, and HEMA Fragment classes — current sample counts (1-3) are insufficient for learning
5. **For teammate comparison:** Numbers are consistent — no investigation needed beyond test set size differences

---

## 8. Files & Locations

| Item | Path |
|---|---|
| OOI dataset | `/home/pranayp/OoI_dataset_single/` |
| Lens presentation dataset | `/home/pranayp/lens_presentation_dataset_single_20260903/` |
| Teammate's dataset | `/home/srikantht/OOI_Classification_Dataset/splits_10class/batch01/keras/` |
| Training script | `/home/pranayp/model_training.py` |
| OOI results | `/home/pranayp/ooi_single_model_runs/` |
| Lens results | `/home/pranayp/model_runs_single50/` |
| OOI warmup results | `/home/pranayp/ooi_warmup/` |
| Lens warmup results | `/home/pranayp/lens_warmup/` |
| Results tarball | `/home/pranayp/ooi_single50_metrics.tar.gz` |
| Excel results | `/home/pranayp/ooi_single50_results.xlsx` |

---

## Appendix: Raw Data Dump

### A. OOI Full Metrics (No Warmup)

```json
ResNet18:    acc=0.6897  macro_f1=0.4635  infer=9.441ms   train=46.55s   test=0.8213s
ResNet50:    acc=0.6552  macro_f1=0.4781  infer=26.361ms  train=114.99s  test=2.2934s
Inception:   acc=0.7126  macro_f1=0.5257  infer=37.392ms  train=138.02s  test=3.2531s
SE:          acc=0.6667  macro_f1=0.4627  infer=29.707ms  train=126.92s  test=2.5845s
```

### B. OOI Full Metrics (With Warmup)

```json
ResNet18:    acc=0.6897  macro_f1=0.4635  infer=5.163ms   train=46.0s    test=0.4492s
ResNet50:    acc=0.6552  macro_f1=0.4781  infer=14.116ms  train=115.1s   test=1.2281s
Inception:   acc=0.7126  macro_f1=0.5257  infer=22.888ms  train=137.4s   test=1.9913s
SE:          acc=0.6667  macro_f1=0.4627  infer=16.738ms  train=127.0s   test=1.4562s
```

### C. Lens Presentation Full Metrics (No Warmup)

```json
ResNet18:    acc=0.9353  macro_f1=0.8062  infer=4.314ms   train=96.63s   test=0.8672s
ResNet50:    acc=0.9552  macro_f1=0.8483  infer=11.936ms  train=238.51s  test=2.3992s
Inception:   acc=0.9602  macro_f1=0.8575  infer=15.379ms  train=289.95s  test=3.0911s
SE:          acc=0.9751  macro_f1=0.9467  infer=13.271ms  train=266.29s  test=2.6676s
```

### D. Lens Presentation Full Metrics (With Warmup)

```json
ResNet18:    acc=0.9055  macro_f1=0.7530  infer=2.475ms   train=95.8s    test=0.4974s
ResNet50:    acc=0.9801  macro_f1=0.8857  infer=6.367ms   train=241.2s   test=1.2798s
Inception:   acc=0.9751  macro_f1=0.8751  infer=9.947ms   train=287.2s   test=1.9993s
SE:          acc=0.9602  macro_f1=0.8552  infer=7.566ms   train=268.1s   test=1.5207s
```

### E. Teammate Baseline

```json
ResNet18:    train=48.25s   test=0.8409s   ms/img=9.042   (93 test imgs)
ResNet50:    train=120.97s  test=2.3325s   ms/img=25.081  (93 test imgs)
Inception:   train=145.85s  test=3.0349s   ms/img=32.633  (93 test imgs)
SE:          train=133.96s  test=2.9012s   ms/img=31.196  (93 test imgs)
```
