# YOLO26 Multiclass Baseline & Experiment Hypotheses

**Date:** 2026-09-11
**Dataset:** dataset_multiclass (346 train / 88 val, 10 defect classes, AABB labels from OBB conversion)
**Model:** YOLO26n, 100 epochs, batch 8, imgsz 1280, auto LR, seed 42

## Baseline Results (YOLO26n MC)

| Class | Val Inst | AP50 | P | R | Category |
|---|---|---|---|---|---|
| Bubble Irregular | 9 | 0.940 | 0.898 | 0.983 | Strong |
| Wet Package | 35 | 0.876 | 0.731 | 0.829 | Strong |
| Foreign Matter | 19 | 0.739 | 0.836 | 0.579 | Medium |
| Extraneous Polymer | 3 | 0.665 | 0.649 | 0.667 | Tiny support |
| Bubble | 227 | 0.632 | 0.601 | 0.639 | Medium |
| Fiber | 12 | 0.449 | 0.714 | 0.417 | Weak |
| Bubble Cluster | 26 | 0.356 | 0.562 | 0.308 | Weak |
| Bubble On Edge | 12 | 0.296 | 0.589 | 0.250 | Weak |
| HEMA Fragment | 2 | 0.270 | 1.000 | 0.000 | Tiny support |
| Bubble On 123 | 32 | 0.132 | 1.000 | 0.000 | Broken recall |
| **Overall** | **377** | **0.535** | **0.758** | **0.467** | |

**Overall:** mAP50=0.535, mAP50-95=0.321

## Key Observation

Bubble On 123 has 32 val instances (decent support) but 0% recall. The model cannot find these defects at all. This is the primary target for architecture experiments.

## Where the headroom actually is (2026-09-15)

Two measurements now frame every architecture bet in this file.

**1. Input image size is the biggest lever, and cropping already took most of it.** The same frames trained at 1280 against trained at their native width improve by +0.123 mAP50 (+26%) to +0.194 (+40%), at 3.4x to 3.7x the training time and about 3x the inference. Our crop already hands the model about 11 px of defect at 1280, against about 7 px for a full frame at 1280 and 13 px at native, so cropping banked most of that for a fraction of the cost. Our own jump from 1280 to native crop size (1568) costs about 1.5x training (predicted) and 1.38x inference (measured: 7.65 to 10.57 ms per image), and its quality gain is not yet measured. Details: spec Entry 23.

**2. The box-precision ceiling is data, not model.** Median overlap between a found box and the correct box sits at about 0.80 across every model, learning rate and pipeline tried. Architecture work can move how many defects are found (mAP50, recall), not the quality of the box it draws.

Consequence for the hypotheses: chase recall on the weak classes, expect little on localisation, and measure the noise floor before believing any delta below about 0.05.

## Hypotheses (to be tested)

### H0 (new, prerequisite): the seed-noise floor

- **What:** the stock config trained three times, seeds 42/43/44, nothing changed. Report the spread.
- **Expected output:** a single number, the delta below which a result is not real. Until we have it, every delta in this file is a single-seed observation.
- **Why first:** three of the four expected deltas in the port program are 0.01 to 0.04. Without the floor we cannot call them results, and we have twice caught ourselves reading noise as signal.
- **Cost:** 3 runs, about 30 minutes.
- **Registry row:** to be added when it runs.

### H1: BiFPN bidirectional flow
- **Status 2026-09-11:** ideated as registry row `mc_bifpn`; not built. Must pass `vm/ops/preflight_fork.py` before training.
- **What:** Replace standard FPN with BiFPN in the neck
- **Expected:** +1-2% overall mAP50, notable improvement on Bubble On 123 and Fiber
- **Rationale:** Bidirectional flow lets P3/P4/P5 exchange info more freely; may help the model find defects that the standard top-down pathway misses
- **Confidence:** Medium

### H2: Processed early-layer features
- **Status 2026-09-11:** ideated as registry row `mc_processed_p3`; not built. This is the half of the question that R1 left open, and R1 raised its prior: the raw version of the same idea cost -0.0560 mAP50 (0.6077 vs a 0.6637 control) on the single-class crops, with matched init and a preflight-gated fork.
- **What:** Add P3 features through a processing block (C3k2) before concatenating into P4 head
- **Expected:** +1-3% overall mAP50, small improvement on Fiber and Bubble Cluster
- **Rationale:** Works WITH the FPN, not around it; processed features filter noise while preserving useful detail
- **Confidence:** Medium-high
- **RESULT 2026-09-15: FALSIFIED.** Built as `experiments/yolo26/yolo26_mc_processed_p3.yaml`, gated (preflight PASS: head stock, `reg_max=1`, `one2one` present), matched init, control and fork in one session. The fork scored **0.4363 mAP50 against a 0.5355 control, a cost of 0.0992 (-18.5%)**, with mAP50-95 -0.0891 and recall -0.1059. Processing the features did not rescue the idea, so the failure was not raw noise alone. The control reproduced the recorded baseline exactly for the third time. Details: registry rows `mc_processed_p3_control` and `mc_processed_p3`; spec Entry 22.

### H2b: Raw tap on the multiclass arena (new, from the H2 result)
- **What:** The same raw P3 tap as R1, but on the multiclass arena, so raw and processed are ranked on identical ground
- **Why:** H2 cost -0.0992 here and the raw tap cost -0.0560 on the crops arena. Magnitudes across arenas are not comparable, so this arm is the only clean raw-versus-processed comparison
- **Expected:** both negative; the open question is which is less bad
- **Cost:** about 20 minutes of GPU (control plus fork in one session)
- **Confidence in a useful result:** high (it is a measurement, not a bet)

### H3: Different backbone tap points
- **What:** Change which backbone rows feed the head (e.g., row 2 instead of row 4 for P3)
- **Expected:** 0-2% mAP50, variable across classes
- **Rationale:** Current taps are YOLO defaults, not optimized for our defect sizes
- **Confidence:** Medium-low

### H4: FPN channel widths
- **What:** Widen FPN channels (e.g., 768 instead of 512 at P4)
- **Expected:** 0-1% mAP50
- **Rationale:** Current widths are already well-calibrated for n-scale
- **Confidence:** Low

### H5 (new, from the YOLO11 line): port the within-pathway winners into YOLO26

- **What:** three changes that each moved the YOLO11 line, applied one at a time to the YOLO26 multiclass arena: C2PSA attention at backbone rows 6 and 8 (worth +0.059 mAP50 on YOLO11), two extra Conv at the P4 stage (+0.037), and the SPPF kernel enlarged from 5 to 7 (+0.018).
- **Why this group:** added low-layer inputs have now failed twice (R1 raw -0.0560, H2 processed -0.0992), and every YOLO11 gain came from strengthening the processing inside the existing pathway. This is the only group with positive measured evidence behind it.
- **Expected output per arm:** attention +0.02 to +0.06 mAP50 with recall rising more than precision; P4 Conv +0.01 to +0.04; SPPF k7 0.00 to +0.02 (its YOLO11 value sits at the edge of what our val set can resolve). Per-class, read the four weak classes only (Bubble On 123, Fiber, Bubble Cluster, Bubble On Edge) and ignore HEMA Fragment and Extraneous Polymer.
- **Combination arm:** `mc_consolidated`, built only from the changes that individually cleared the noise floor. It is the arm that would actually ship.
- **Costs:** attention adds about 0.4M params (the YOLO11 analogue went 2.66M to 3.13M); SPPF k7 adds zero params and zero compute; P4 Conv adds two 512-channel convolutions. Training time per arm stays near the baseline 566 s at batch 8, 100 epochs.
- **Gate:** preflight against the stock yaml before training, control and fork in the same session, one variable per fork.
- **Confidence:** medium-high for attention (best accuracy per parameter of anything tried on YOLO11, and the only variant that detected HEMA Fragment at all), medium for P4 Conv, low-medium for SPPF k7.

## What We Actually Know From The Single-Class Crops (updated 2026-09-11)

| Change | Result | Verdict |
|---|---|---|
| **Raw P3 tap into the P4 stage (R1, one variable, matched init)** | **0.6077 vs a 0.6637 control** | **HURT by -0.0560 mAP50 (-8.4%)**. Attributable. Use this number. |
| Stock YOLO26n control (R1) | 0.6637 / 0.4111 | Reference. Reproduced the 2026-09-10 batch-8 baseline exactly. |
| Flat 1e-4 LR arm (R2) | 0.5772 vs 0.6166 auto | Auto LR wins by +0.0394. Do not use fixed 1e-4. |
| "V1" (2026-09-10) | 0.411 (-0.253) | **UNATTRIBUTABLE**: the file had no head edit, and the head config, SPPF behaviour and init also changed. |
| "V2" (2026-09-10) | 0.451 (-0.213) | **UNATTRIBUTABLE**: it added raw upsampled P5, not P3, plus the same extra confounds. |

Two consequences for the hypotheses below: H2 ("process the features before adding them") gains real support from R1's attributable loss, and every new fork must pass `vm/ops/preflight_fork.py` before it is allowed to train.

## Per-Class Target for Architecture Experiments

Focus on these classes for per-class improvement:
1. **Bubble On 123** (0.132, 0% recall) - must improve recall
2. **Fiber** (0.449, 0.417 recall) - improve detection
3. **Bubble Cluster** (0.356, 0.308 recall) - improve detection
4. **Bubble On Edge** (0.296, 0.250 recall) - improve detection

Do NOT expect improvement on:
- Bubble Irregular (0.940) - already maxed
- Wet Package (0.876) - already strong
- HEMA Fragment (2 val images) - data-limited
- Extraneous Polymer (3 val images) - data-limited
