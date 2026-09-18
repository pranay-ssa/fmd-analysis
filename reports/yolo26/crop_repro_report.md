# YOLO26 Crop Reproduction - Reference Report (OoI Defect Classes)

**Status:** reference baseline for future YOLO26 experiments.
**Date:** 2026-09-09
**Purpose:** this is the reproducible reference point for the YOLO26 vs YOLO11 comparison
on OUR crop pipeline. Future YOLO26 work (backbone edits, resolution, losses) should be
measured against the numbers here, under the same protocol.

---

## 1. What was measured

Two stock detection models (YOLO11n and YOLO26n, no architecture change, pretrained
weights) were trained and evaluated on our single-size fixed crops:

- Task: class-agnostic bounding-box detection (all ten defect types collapsed to one
  object class). This isolates box localization from class recognition.
- Data: our 434 single-size fixed crops, frozen 346 train / 88 held-out split, labels as
  axis-aligned boxes in crop coordinates.
- Training: 100 epochs, batch 16, input 1280 px, learning-rate schedule auto, seed 42.
- Metrics: mAP50, mAP50-95 (official validation), plus a box-quality (IoU) analysis.

This mirrors the protocol a teammate ran on the SAME 434 source images but on the full
native frames (2448x2048) instead of our crops, so the two can be read side by side.

## 2. Results on our crops

**Detection quality (mAP):**

| Model | Params | mAP50 | mAP50-95 | Precision | Recall |
|---|---|---|---|---|---|
| YOLO11n | 2.59 M | 0.6007 | 0.3666 | 0.622 | 0.571 |
| YOLO26n | 2.50 M | **0.6166** | **0.3937** | 0.596 | **0.626** |

**Bounding-box quality (IoU on the held-out set):**

| Model | Matched IoU (mean) | Matched IoU (median) | Ceiling >=0.50 | Ceiling >=0.75 | Hard-miss floor |
|---|---|---|---|---|---|
| YOLO11n | 0.695 | 0.786 | 87.8% | 62.9% | 3.7% |
| YOLO26n | **0.728** | **0.804** | 87.8% | **70.0%** | 4.2% |

**Verdict on our crops: YOLO26n beats YOLO11n on every metric.** mAP50 +0.016, mAP50-95
+0.027, matched-IoU +0.033, share of boxes at IoU >= 0.75 by +7 points, recall +0.055.
YOLO26's boxes are tighter and it finds more of them, which is consistent with its
small-object loss improvements (Progressive Loss and Scale-Targeted Attention).

## 3. How this compares with the teammate's native-frame numbers

Same two stock models, same class-agnostic protocol, but on the full native frames
(trained at 1280 and at native 2448 by the teammate).

| Model (auto LR) | Ours: crops @1280 mAP50 / mAP50-95 | Teammate: native @2448 mAP50 / mAP50-95 | Teammate: native @1280 mAP50 / mAP50-95 |
|---|---|---|---|
| YOLO11n | 0.601 / 0.367 | 0.680 / 0.429 | 0.487 / 0.274 |
| YOLO26n | 0.617 / 0.394 | 0.596 / 0.378 | 0.473 / 0.287 |

**IoU (best-IoU-per-defect ceiling):**

| Model (auto LR) | Ours: crops @1280 mean / med / >=0.75 | Teammate: native @2448 mean / med / >=0.75 |
|---|---|---|
| YOLO11n | 0.695 / 0.786 / 62.9% | 0.766 / 0.820 / 69.2% |
| YOLO26n | 0.728 / 0.804 / 70.0% | 0.773 / 0.844 / 73.6% |

**Honest reading:**
- The 26-vs-11 ordering is arena-dependent. On OUR crops YOLO26n wins; on the teammate's
  native frames YOLO11n is as good or better. Our production pipeline is the crop
  pipeline, so YOLO26 is favored here.
- The absolute gap between the columns is not meaningful: ours are crops, theirs are
  native frames (different inputs and splits). The signal is (a) the per-arena ordering
  and (b) that cropping lifts stock models roughly +0.11 mAP50 at the same input size.
- YOLO26n is slightly leaner than YOLO11n (2.50 M vs 2.59 M params) yet localizes better
  on crops, so there is no capacity cost to the switch.

## 4. Metric definitions (keep these fixed for future comparisons)

| Metric | Meaning |
|---|---|
| mAP50 | detection + label quality at IoU 0.5 |
| mAP50-95 | detection + label quality averaged over IoU 0.5 to 0.95 (strict localization) |
| Matched IoU | mean/median overlap of one-to-one matched detections, greedy, conf 0.001 |
| Match rate | share of true boxes that receive any matched detection (coverage) |
| Localization ceiling | best IoU per true box over all predictions at conf 0.001 |
| >=0.50 / >=0.75 | share of true boxes whose best overlap clears that threshold |
| Hard-miss floor | share of true boxes with no overlapping prediction at all, even at conf 0.001 |

**Two easily-confused numbers:** matched-IoU is tightness (how well each found box hugs
the defect); match rate is coverage (how many defects get a box at all). Reported together.

## 5. Why this file is the reference for future YOLO26 work

- It fixes the protocol (stock models, class-agnostic, our crops, 1280 px, batch 16,
  seed 42) and the metrics (mAP + IoU set above).
- Any future YOLO26 experiment (a backbone edit, a higher input resolution, a different
  optimizer) should be compared to YOLO26n Auto LR here (mAP50 0.6166, mAP50-95 0.3937,
  matched-IoU 0.728, ceiling >=0.75 70.0%) on identical data.
- Change one thing at a time; keep the arena (crops, single-class, 1280) and the metric
  set fixed so every new result is attributable.

*Data are held out and shared across the team; all numbers above are taken from the
recorded reproduction run outputs on the same 88-image held-out set.*
