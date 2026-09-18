# FMD Training Results — Meeting Talking Points

**Date:** 2026-09-04
**Dataset:** 12 LP classes, 1465 images (802 train / 201 test), fixed-size crops

---

## 1. What we built

- Fixed-size crop pipeline: every image from the same class gets the same crop dimensions, lens centered. Replaces the old variable-size output.
- 22 classes, 1465 images, both modes (single-size with 120px border, multi-size with tighter border). Full run takes ~6.5 minutes on 8 workers.
- Crop is a pure window select. No pixel values change. Calibration preserved.

## 2. Why per-class crop sizes

Lenses are not the same size in the photo, sit at different positions, and some defects live in the surrounding package or camera artifact (not the lens). A single crop size either clips Package Misalignment (largest class, 2020px) or wastes the frame on View Obstructed (smallest, 1496px). Per-class sizes guarantee no clipping with minimal black border.

## 3. Training results

4 architectures tested: ResNet18, ResNet50, ResNet50-Inception (multi-scale feature extraction), ResNet50-SE (channel attention). Each tested at 20, 30, 50 epochs. Batch 8, seed 42.

### Multi-train / single-test (original matrix)

| Architecture | Best Accuracy | Best Epoch |
|---|---|---|
| ResNet18 | 86.07% | 30 |
| ResNet50 | 88.06% | 30 |
| ResNet50-Inception | 89.55% | 50 |
| ResNet50-SE | **91.54%** | **20** |

### Single-train / single-test (epoch 50)

| Architecture | Accuracy |
|---|---|
| ResNet18 | 93.53% |
| ResNet50 | 95.52% |
| ResNet50-Inception | 96.02% |
| ResNet50-SE | **97.51%** |

### Key takeaway

Single-size training is significantly better than multi-train/single-test. The ranking is stable across both: **SE > Inception > ResNet50 > ResNet18**.

## 4. Best model: ResNet50-SE

- 97.51% accuracy on single-size (epoch 50), macroF1 89.10 on multi-train.
- SE (Squeeze-and-Excitation) blocks add channel attention — the model learns which feature channels matter most for each defect class.
- Fastest to converge: peaks at 20 epochs in multi-train mode (other architectures need 30-50).
- Inference time: ~13ms per image (acceptable for production).

## 5. Per-class performance (weak spots)

From the single-size results (epoch 50):

| Class | Full Name | ResNet18 | ResNet50 | Inception | SE |
|---|---|---|---|---|---|
| LOC | Lens Off Center | 33.33% | 66.67% | 83.33% | 66.67% |
| DC | Dirty Camera | 80.00% | 80.00% | 80.00% | 80.00% |
| BS | Bubble Scatter | 100% | 100% | 100% | 100% |

- **LOC (Lens Off Center):** hardest class — only 30 images, lens sits at different positions in every frame. All architectures struggle.
- **DC (Dirty Camera):** capped at 80% across all architectures. Only 25 images, and the defect is camera smudge, not a lens defect — the model may confuse it with normal variation.
- **BS (Bubble Scatter):** only 7 images. ResNet18 and ResNet50 get 0% in multi-train mode (too few examples). Single-size training fixes this.

## 6. What the results mean

- Single-size training is the clear winner. If the lead wants one model to ship, it is ResNet50-SE at 50 epochs on single-size crops.
- The 12-run matrix proved the architectures converge differently — no single best epoch across all four. SE converges fastest (20), Inception needs the most data (50).
- Weak classes (LOC, BS, DC) are data-limited, not architecture-limited. More training data will improve them.

## 7. Deliverable

- Results workbook ready — 4 architectures, both modes, per-class recall for all 12 LP classes, training time, inference time.
- Lead's format reference used as the template.
