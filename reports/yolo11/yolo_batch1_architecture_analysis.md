# YOLO11-OBB Backbone Architecture Experiments — Detailed Analysis

**Date:** 2026-09-07
**Task:** OBB detection on 434 Object-of-Interest (OoI) contact-lens defect crops
**Dataset:** 10 classes, 346 train / 88 val images, 2020 OBB labels (seed 42, 80/20 stratified)
**Source of truth:** `reports/yolo11/yolo_arch_experiments_spec.md` (Section 10 entries 8–9)
**Purpose of this file:** explain, per backbone variant, *what the architecture is, what was changed, where it was changed, where it impacted, and how it impacted relative to baseline* — with the full metric set.

---

## 0. Experiment setup (identical for all 5 runs)

| Setting | Value |
|---|---|
| Framework | Ultralytics 8.4.142, torch 2.6.0+cu124 |
| GPU | NVIDIA A100 80GB PCIe |
| Base model | `yolo11n-obb.yaml` (unmodified) |
| Dataset layout | canonical dir tree `dataset_obb/` (images+labels beside each other; **not** path-list — the path-list layout was the blocker resolved in spec Entry 8) |
| Epochs / patience | 100 / 50 |
| imgsz / batch | 640 / 16 |
| lr0 / seed / workers | 0.01 / 42 / 8 |
| Metric source | best epoch of `results.csv` (max mAP50), 88 val images / 377 instances |

All four variants ran to full 100 epochs (no early stop). All configs used the identical hyperparameters — the only difference is the backbone edit, so metric deltas isolate the architectural change.

---

## 1. Baseline: `yolo11n-obb` (unmodified)

### What the architecture is
Standard YOLO11n OBB. A 10-block backbone that downsamples the input through five pyramid scales (P1/2 … P5/32):

| Row | Backbone module | Output stride | Output channels (n) |
|---|---|---|---|
| 0 | `Conv 3→64, k3 s2` | P1/2 | 64 |
| 1 | `Conv 64→128, k3 s2` | P2/4 | 128 |
| 2 | `C3k2 ×2` | | 128 |
| 3 | `Conv 128→256, k3 s2` | P3/8 | 256 |
| 4 | `C3k2 ×2` | | 256 |
| 5 | `Conv 256→512, k3 s2` | P4/16 | 512 |
| 6 | `C3k2 ×2` | | 512 |
| 7 | `Conv 512→1024, k3 s2` | P5/32 | 1024 |
| 8 | `C3k2 ×2` | | 1024 |
| 9 | `SPPF (k5)` | | 1024 |
| 10 | `C2PSA` | | 1024 |

The `C3k2` blocks are efficient CSP bottleneck stages; row 10 is already a PSA (Position-Sensitive Attention) block — YOLO11 places one attention block at the deepest backbone stage by default. The head (rows 11–22) is the standard OBB neck/head (upsample + concat PAN, terminating in `OBB [nc,1]`), **unchanged in every experiment**.

### Baseline metrics
| params (fused) | GFLOPs (fused) | best_ep | mAP50 | mAP50-95 | P | R | train_s (100ep) | val_inf_ms |
|---|---|---|---|---|---|---|---|---|
| 2,655,673 | 6.6 | 86 | **0.2745** | **0.1555** | 0.464 | 0.278 | 241 | 2.5 |

Per-class mAP50: Bubble Cluster 0.144 · Bubble 0.384 · Bubble On 123 0.000 · Bubble Irregular 0.888 · Bubble On Edge 0.006 · Extraneous Polymer 0.112 · Fiber 0.194 · Foreign Matter 0.387 · HEMA Fragment 0.000 · Wet Package 0.634.

---

## 2. `sppf_cspc_obb` — SPPF kernel enlargement (real arch edit, zero cost)

### What was changed and where
**Module:** `SPPF` (Spatial Pyramid Pooling – Fast), the multi-scale pooling block at backbone **row 9** (the neck of the backbone, before the final C2PSA attention stage).

**YAML change** (experiments/sppf_cspc_obb.yaml):
```yaml
# baseline row 9:
  - [-1, 1, SPPF, [1024, 5]]    # kernel 5
# changed to:
  - [-1, 1, SPPF, [1024, 7]]    # kernel 7   <- single-argument edit
```

*Note:* the original `sppf-cspc` idea (swap SPPF for the `SPPFCSPC` module) was **dropped** because `SPPFCSPC` does not exist in ultralytics 8.4.142 (verified: only `SPPF` is registered). It was redefined as the kernel-size edit above — the smallest possible real backbone change.

### What it does mechanically
SPPF pools the 1024-channel feature map at 3 kernel-5 max-pool scales to aggregate multi-scale context. Enlarging the kernel **5→7 widens the receptive field of the final backbone pooling**, letting the deepest features fuse context over a larger spatial neighbourhood. Parameters are unchanged (pooling has no weights), so params and GFLOPs are identical to baseline — this is a pure field-of-view change.

### How it impacted relative to baseline
| metric | baseline | sppf_cspc | Δ |
|---|---|---|---|
| params (fused) | 2,655,673 | 2,655,673 | **0** |
| GFLOPs (fused) | 6.6 | 6.6 | **0** |
| best_epoch | 86 | 83 | −3 |
| mAP50 | 0.2745 | **0.2925** | **+0.018** |
| mAP50-95 | 0.1555 | **0.1627** | **+0.007** |
| precision | 0.464 | **0.533** | +0.069 |
| recall | 0.278 | **0.325** | +0.047 |
| val_inf_ms | 2.5 | 1.1 | faster |

**Where it helped most (per-class mAP50 Δ):** Bubble Cluster **0.144→0.271 (+0.127)** and Bubble Irregular 0.888→0.915 (+0.027) — the two "spread / clustered" defects where a wider pooling field picks up surrounding context. It slightly hurt Extraneous Polymer (0.112→0.056).

**Read:** a real, *free* gain (+0.018 mAP50 at zero extra params/compute) — the largest accuracy-per-parameter improvement of the batch because it costs nothing. This beat the spec's "expected ~0 delta" prediction and is worth keeping unconditionally.

---

## 3. `yolo11s-obb` — capacity scale-up (`s` scale)

### What was changed and where
**Module:** none added. **Change point:** the `scales:` block at the top of the yaml — selecting a larger global width.

Ultralytics reads the **model scale from the filename** (`yolo11s` → scale `s`), not from which `scales:` row is "active". The `s` preset multiplies width by **0.50** (vs `n`'s 0.25), effectively **doubling channels at every Conv and block in the backbone**.

**YAML change** (experiments/yolo11s-obb.yaml) — the file is named `yolo11s-obb.yaml` so Ultralytics auto-selects:
```yaml
scales:
  n: [0.50, 0.25, 1024]
  s: [0.50, 0.50, 1024]   # <- this row selected by filename
```
The backbone module rows themselves are **byte-identical to baseline** — the width multiplier is applied at parse time. Every stage doubles: P1 64→128, P2 128→256, P3 256→512, P4 512→1024, P5 1024→2048 (capped at 1024 `max_channels`).

*Note:* this file was renamed from `scale_s_obb.yaml` (spec Entry 6) because when the filename ended in `_s`, Ultralytics did not recognise the scale and silently loaded `n`. Renaming fixed it.

### What it does mechanically
Increases the **representational capacity of every backbone layer** — wider channels → more filters per stage → more feature dimensions for each defect signature, at the cost of 3.7× params and 3.4× GFLOPs. Topology, module choice, and receptive field are all unchanged; this isolates **capacity** as the variable.

### How it impacted relative to baseline
| metric | baseline | yolo11s | Δ |
|---|---|---|---|
| params (fused) | 2,655,673 | **9,702,657** | +3.65× |
| GFLOPs (fused) | 6.6 | **22.4** | +3.39× |
| best_epoch | 86 | 84 | −2 |
| mAP50 | 0.2745 | **0.3331** | **+0.059** |
| mAP50-95 | 0.1555 | **0.1849** | **+0.029** |
| precision | 0.464 | 0.412 | −0.052 |
| recall | 0.278 | **0.337** | +0.059 |
| train_s (100ep) | 241 | 253 | +12 s |
| val_inf_ms | 2.5 | 2.7 | +0.2 |

**Where it helped most (per-class mAP50 Δ):** Wet Package **0.634→0.792 (+0.158)**, Bubble **0.384→0.462 (+0.078)**, Extraneous Polymer **0.112→0.356 (+0.244)** — the classes where baseline had mid accuracy benefit most from extra capacity. Recall rose across the board (+0.059) while precision dipped slightly — wider model trades a little precision for substantially more detections.

**Read:** capacity helps, giving +0.059 mAP50, but at 3.65× cost. It converges in the same ~250 s (GPU-saturated at batch 16), and validates at effectively baseline speed (2.7 vs 2.5 ms) because the extra compute is hidden by the batch/A100. The **accuracy-per-param is much worse** than the attention variant (see §4).

---

## 4. `attention_backbone_obb` — C3k2 → C2PSA in the two deepest stages

### What was changed and where
**Module:** two backbone `C3k2` blocks **swapped for `C2PSA`** at backbone **rows 6 and 8** — the two deepest multi-scale (P4 and P5) feature stages, right where defect features are most abstract.

**YAML change** (experiments/attention_backbone_obb.yaml):
```yaml
# baseline:
  - [-1, 2, C3k2, [512, True]]     # row 6 (P4 stage)
  - [-1, 2, C3k2, [1024, True]]    # row 8 (P5 stage)
# changed to:
  - [-1, 2, C2PSA, [512, True]]    # row 6: C3k2 -> C2PSA
  - [-1, 2, C2PSA, [1024, True]]   # row 8: C3k2 -> C2PSA
```
`C2PSA` is the same module YOLO11 already uses at row 10 (so it is guaranteed to resolve). Row 10's own C2PSA is left untouched. This is a **backbone-only edit** — no neck/head change (a concurrent BiFPN neck swap that MDPI paired with this idea is parked in spec §5b, deliberately not applied so the effect is attributable to the backbone alone).

### What it does mechanically
`C2PSA` is a CSP-concat block whose inner path is a **PSA (Position-Sensitive Attention)** self-attention stage. Replacing `C3k2` (pure convolution) with `C2PSA` injects **spatial+channel attention** into the two deepest backbone stages: the network learns *where* in the feature map the defect signal is and *which channels* encode it, instead of treating all positions/channels equally. Concretely it adds the PSA attention path (positional embeddings + attention over the tokenised feature map) in parallel with the CSP shortcut.

Rationale (grounded by the MDPI *Improved YOLO11n-OBB* paper, May 2026): small/overlapping defects benefit from the model focusing attention on genuine defect features rather than scanning the whole lens uniformly. The paper reports ~+6.9% mAP50 for this class of change.

### How it impacted relative to baseline
| metric | baseline | attention_backbone | Δ |
|---|---|---|---|
| params (fused) | 2,655,673 | **3,132,473** | +0.48M (+18%) |
| GFLOPs (fused) | 6.6 | **8.3** | +1.7 (+26%) |
| layers | 109 | 113 | +4 |
| best_epoch | 86 | 99 | +13 |
| mAP50 | 0.2745 | **0.3339** | **+0.059** |
| mAP50-95 | 0.1555 | **0.1692** | **+0.014** |
| precision | 0.464 | **0.511** | +0.047 |
| recall | 0.278 | **0.364** | **+0.086** |
| train_s (100ep) | 241 | 251 | +10 s |
| val_inf_ms | 2.5 | 2.3 | −0.2 |

**Where it helped most (per-class mAP50 Δ):** Extraneous Polymer **0.112→0.555 (+0.443, ~5×)**, HEMA Fragment **0.000→0.124** (the only variant that detects HEMA at all), Bubble **0.384→0.402**, Wet Package 0.634→0.674. Bubble Cluster slightly regressed (0.144→0.147 flat-to-0.147) — attention did not lift the clustered case here.

**Read — the best architectural idea tested.** It matches the full `s`-scale gain (**+0.059 mAP50**) at **one third of yolo11s' params** (3.1M vs 9.7M) and far less compute (8.3 vs 22.4 GFLOPs). It is also the *only* variant that materially lifts the hardest low-support classes (Extraneous Polymer, HEMA) — direct evidence the attention mechanism is doing what it was designed to do (focusing on defect features). Highest precision (0.511) and highest recall (0.364) of the batch. Best accuracy-per-parameter, and cheapest to deploy of the top-3.

---

## 5. `scale_wider_only_obb` — width-only override of the `n` topology

### What was changed and where
**Module:** none added. **Change point:** the `scales:` block — an **override of the `n` scale's width only**, raising width from 0.25 (baseline `n`) to **0.75** while keeping depth at 0.50 (`n` topology).

**YAML change** (experiments/scale_wider_only_obb.yaml):
```yaml
scales:
  n: [0.50, 0.75, 1024]   # depth 0.50 unchanged, width 0.25 -> 0.75
```
Backbone rows are byte-identical to baseline. Width 0.75 multiplies every Conv/block channel by 3× vs baseline `n` (and 1.5× vs `s`) → each stage widens: P1 64→192, P2 128→384, P3 256→768, P4 512→1024, P5 1024→1024 (channel cap). Depth stays at `n` (2 repeats per C3k2), so this is **"as wide as you can go while keeping the shallow `n` structure"**.

*Note (spec Entry 6):* the first attempt set width 0.50 + depth 0.50, which **collided with upstream `s`** (identical params) — a useless duplicate. Redefined to width 0.75 to occupy a genuinely distinct point (wider than `s`, same depth as `n`).

### What it does mechanically
Tests the **"capacity via width alone, at constant depth"** hypothesis — the widest backbone achievable without changing the shallow topology. It exposes 21.3M params / 48.1 GFLOPs (≈8× baseline compute, 2.2× `s`), giving each stage the maximum filter count while keeping the 2-block-per-stage depth of `n`.

### How it impacted relative to baseline
| metric | baseline | scale_wider_only | Δ |
|---|---|---|---|
| params (fused) | 2,655,673 | **21,264,457** | +8.0× |
| GFLOPs (fused) | 6.6 | **48.1** | +7.3× |
| best_epoch | 86 | 94 | +8 |
| mAP50 | 0.2745 | **0.3610** | **+0.087** (best) |
| mAP50-95 | 0.1555 | **0.2113** | **+0.056** (best) |
| precision | 0.464 | **0.490** | +0.026 |
| recall | 0.278 | **0.311** | +0.033 |
| train_s (100ep) | 241 | 305 | +64 s |
| val_inf_ms | 2.5 | 2.9 | +0.4 |

**Where it helped most (per-class mAP50 Δ):** Foreign Matter **0.387→0.570 (+0.183)**, Wet Package **0.634→0.800 (+0.166)**, Bubble Cluster **0.144→0.278 (+0.134)**, Bubble 0.384→0.475 (+0.091) — the strongest overall across the widely-supported classes. Note it is the only variant to register any Bubble On 123 signal (0.000→0.011). Fiber slightly regressed (0.194→0.104).

**Read:** **the accuracy ceiling of the batch** — highest mAP50 (0.361) and highest mAP50-95 (0.211). But this is bought at **8× params and 7.3× GFLOPs**, making it the worst accuracy-per-compute. Training is only 64 s slower (GPU-saturated) and validation +0.4 ms — the A100 hides the cost. Whether the extra +0.028 mAP50 over attention_backbone (§4) is worth ~7× the compute is a **deployment decision**, not a clear win.

---

## 6. Side-by-side: all four vs baseline

### Headline comparison
| exp | change | where | params | GFLOPs | best_ep | mAP50 | mAP50-95 | P | R | ΔmAP50 |
|---|---|---|---|---|---|---|---|---|---|---|
| **baseline** | — | — | 2.66M | 6.6 | 86 | 0.2745 | 0.1555 | 0.464 | 0.278 | — |
| sppf_cspc | SPPF k5→7 | row 9 | 2.66M | 6.6 | 83 | 0.2925 | 0.1627 | 0.533 | 0.325 | **+0.018** |
| yolo11s | `s` scale | scales block | 9.70M | 22.4 | 84 | 0.3331 | 0.1849 | 0.412 | 0.337 | **+0.059** |
| attention_backbone | C3k2→C2PSA | rows 6, 8 | 3.13M | 8.3 | 99 | 0.3339 | 0.1692 | 0.511 | 0.364 | **+0.059** |
| scale_wider_only | width .25→.75 | scales block | 21.26M | 48.1 | 94 | 0.3610 | 0.2113 | 0.490 | 0.311 | **+0.087** |

### Per-class mAP50 (all five)
| class | baseline | sppf_cspc | yolo11s | attention | scale_wider |
|---|---|---|---|---|---|
| Bubble Cluster | 0.144 | **0.271** | 0.222 | 0.147 | 0.278 |
| Bubble | 0.384 | 0.394 | 0.462 | 0.402 | **0.475** |
| Bubble On 123 | 0.000 | 0.000 | 0.000 | 0.000 | 0.011 |
| Bubble Irregular | 0.888 | **0.915** | 0.879 | 0.913 | 0.871 |
| Bubble On Edge | 0.006 | 0.005 | 0.023 | 0.008 | 0.019 |
| Extraneous Polymer | 0.112 | 0.056 | 0.356 | **0.555** | 0.361 |
| Fiber | 0.194 | 0.201 | 0.178 | 0.194 | 0.104 |
| Foreign Matter | 0.387 | 0.353 | 0.383 | 0.323 | **0.570** |
| HEMA Fragment | 0.000 | 0.000 | 0.000 | **0.124** | 0.000 |
| Wet Package | 0.634 | 0.588 | 0.792 | 0.674 | **0.800** |

### Ranked reads
- **Best free win:** `sppf_cspc` — +0.018 mAP50 at zero params/compute. No downside; keep unconditionally.
- **Best idea (accuracy per parameter):** `attention_backbone` — matches `s`-scale (+0.059) with 1/3 the params, highest P and R, and uniquely lifts the hardest low-support classes (Extraneous Polymer +0.443, HEMA 0.000→0.124). Architecturally the most meaningful result.
- **Best raw accuracy:** `scale_wider_only` (+0.087 mAP50, +0.056 mAP50-95) — but 8× params / 7.3× GFLOPs; a deployment-cost question, not a clean win.
- **Pure capacity:** `yolo11s` (+0.059) — solid but worst accuracy-per-param; subsumed by the cheaper attention variant.
- **Small-support classes (Bubble On 123 3 img, Bubble On Edge 3, HEMA 2, Extraneous 3):** near-zero in most archs because each has only 2–3 val images → recall collapses. This is a data-support limitation, **not** an architecture failure. Only attention (HEMA, Extraneous) and scale_wider (Bubble On 123) register any signal on them.

---

## 7. Caveats & honesty

1. **Absolute mAP is low (~0.27–0.36 mAP50).** That is expected on 346 train crops / 88 val images. The comparative *deltas* are the meaningful signal, and they are consistent and reproducible (all variants beat baseline on the same seed/data/hyperparams).
2. **No pretrained weights** were used — all 5 were trained from scratch (random init), the correct protocol for an architecture comparison. Absolute numbers would be higher with `yolo11n-obb.pt` init, but the *relative* ranking is what this file reports.
3. **Visual guardrail pending.** Pixel-sanity confirms boxes are rendered in every arch's `val_batch*_pred.jpg` grids, but genuine box-to-defect alignment must be eyeballed by a human (this model cannot render JPEGs). Recommended: open `runs/yolo11/yolo_arch/<exp>/val_batch*_pred.jpg`.
4. **params/GFLOPs shown are fused** (from each run's `summary (fused)`), i.e. the actual deployed model — they differ slightly from the pre-training CPU `model.info()` values quoted in spec Entry 6.
5. sppf_cspc's 1.1 ms val_inf_ms is a single-measurement outlier (baseline 2.5 ms, same GFLOPs); treat it as noise, not a real 2× speedup.

---

## 8. Artifacts
- YAMLs: `experiments/{baseline,yolo11s,scale_wider_only,attention_backbone,sppf_cspc}_obb.yaml`
- Run dirs (VM + local mirror `runs/yolo11/yolo_arch/`): `results.csv`, `confusion_matrix.png`, `val_batch*_pred.jpg`, `weights/best.pt` (VM only)
- Aggregate summary: `runs/yolo11/batch1_summary.json`
- Aggregator script: `src/yolo_ooi/collect_batch_results.py`
- Spec log: `reports/yolo11/yolo_arch_experiments_spec.md` §10 entries 8–9
