# YOLO26 Experiment Plan (2026-09-10 to 2026-09-15)

**Updated 2026-09-11:** after VM verification, two earlier conclusions in this plan were corrected (see `reports/yolo26/DOC_CORRECTIONS_20260911.md`). Phase 1 is closed with a recorded decision; Phase 3 ran but is unattributable; Phase 2 is still open. Re-runs R1/R2 in `experiments/registry.json` take priority over new forks.

## Context

Lead meeting 2026-09-10: presented crop pipeline results. Lead confirmed small defects are harder to find and suggested using low/mid layer features more aggressively for small-defect detection. User committed to:
1. Translate YOLO11 architecture experiments to YOLO26
2. Investigate lead's feature concatenation idea
3. Prepare YOLO26 spec, registry, README

## Terminology Reference

### Layer numbering (YOLO26n, bottom-to-top in yaml)

| Row | Module | Scale | Role | What it sees |
|---|---|---|---|---|
| 0 | Conv | P1/2 | Input stem | Raw image, 1/2 resolution |
| 1 | Conv | P2/4 | Early backbone | Edges, textures |
| 2 | C3k2 | P2/4 | Early backbone | Feature refinement |
| 3 | Conv | P3/8 | Early backbone | Small patterns |
| 4 | C3k2 | P3/8 | Early backbone | **Feeds head P3 (row 15 concat)** |
| 5 | Conv | P4/16 | Mid backbone | Object parts |
| 6 | C3k2 | P4/16 | Mid backbone | **Feeds head P4 (row 12 concat)** |
| 7 | Conv | P5/32 | Deep backbone | Full objects |
| 8 | C3k2 | P5/32 | Deep backbone | Feature refinement |
| 9 | SPPF | P5/32 | Deep backbone | Multi-scale context |
| 10 | C2PSA | P5/32 | Deep backbone | Attention |
| 11-22 | Head (FPN+PAN) | P3-P5 | Detection head | Multi-scale fusion |
| 23 | Detect | P3+P4+P5 | Output | Final predictions |

### What "low" and "mid" layers mean

- **Low/early layers** = rows 0-4 (P1-P3). High resolution, detect tiny features.
- **Mid layers** = rows 5-6 (P4). Medium resolution, detect object parts.
- **Deep layers** = rows 7-10 (P5). Low resolution, detect whole objects.
- Standard FPN already connects P3 (row 4) and P4 (row 6) to the head.

### YOLO11 vs YOLO26 architecture

Both have identical backbone structure (Conv, C3k2, SPPF, C2PSA).
Key difference: YOLO11 uses OBB head (rotated boxes), YOLO26 uses Detect head (axis-aligned boxes).
The backbone and neck are structurally the same.

## Phase 1: YOLO26 Spec + Registry (by Wed Sep 11) - CLOSED, decision recorded 2026-09-11

- [x] **Decision: fold YOLO26 into the shared governance + registry files instead of forking them.** The protocol, split, seed and comparison rules are shared with the YOLO11 line, so `experiments/README.md` carries a YOLO26 section (2a) plus ADR-011/012/013, and `experiments/registry.json` holds one registry for both families with `model_family` + `data_arena` on every row. A separate `experiments/yolo26/README.md` and `registry.json` were deliberately NOT created; only the fork yamls live under `experiments/yolo26/`.
- [x] `reports/yolo26/yolo26_arch_experiments_spec.md` created: the YOLO26 detect log (single-class + multiclass).
- [x] YOLO26 baselines documented and VM-verified (HANDOFF section 5; registry rows `yolo26n_crop_repro`, `yolo26n_crop_b8_auto`, `yolo26n_mc_baseline`).
- [x] The "fixed LR" arm is documented as mislabeled, not as a baseline (see re-run R2).

## Phase 2: Translate YOLO11 Experiments to YOLO26 (by Thu Sep 12)

Winning YOLO11 experiments to carry over:

| YOLO11 Experiment | What Changed | mAP50 Delta | YOLO26 Fork |
|---|---|---|---|
| attention_backbone | C3k2→C2PSA at rows 6/8 | +0.059 | yolo26_attention.yaml |
| sppf_cspc | SPPF kernel 5→7 | +0.018 | yolo26_sppf_k7.yaml |
| armB_conv_p4 | +2 Conv at P4 stage | +0.037 | yolo26_armB_p4.yaml |

Note: YOLO26 backbone already has C2PSA at row 10. Need to check if adding C2PSA at rows 6/8 (like YOLO11 attention_backbone) is compatible or if YOLO26 already has attention there.

- [ ] Build yolo26_attention.yaml (C2PSA at rows 6/8)
- [ ] Build yolo26_sppf_k7.yaml (SPPF kernel 7)
- [ ] Build yolo26_armB_p4.yaml (+2 Conv at P4 stage)
- [ ] Validate all forks (structural validator + param count on VM)
- [ ] Train baseline + 3 variants (batch 8, 100 ep, seed 42, imgsz 1280, auto LR)

**Status 2026-09-15: this is the live phase.** R1 and H2 are done and negative (no added low-layer inputs, raw or processed), so Phase 2 is now the port of the within-pathway winners, which is where the YOLO11 gains actually came from. Same three forks as before, plus the capacity reference, each as its own gated arm:

| YOLO11 experiment | Change | YOLO11 delta | YOLO26 arm | Expected on our multiclass arena |
|---|---|---|---|---|
| `attention_backbone_obb` | C3k2 becomes C2PSA at rows 6 and 8 | +0.059 mAP50, +0.014 mAP50-95, params 2.66M to 3.13M (+18%) | `mc_attention_port` | +0.02 to +0.06 mAP50; recall up more than precision; weak classes are where any gain shows |
| `armB_conv_p4` | 2 x plain Conv [512,3,1] at the P4 stage | +0.037 mAP50 | `mc_p4_conv` | +0.01 to +0.04 mAP50 |
| `sppf_cspc_obb` | SPPF kernel 5 becomes 7 | +0.018 mAP50, +0.007 mAP50-95, zero params | `mc_sppf_k7` | 0.00 to +0.02 mAP50 (at the edge of resolvable on 88 val images) |
| (`yolo11s_obb`, for reference) | s scale, stock | +0.059 mAP50 at 3.65x cost | `model_scale_s` | The capacity reference, so we learn whether edits beat a bigger model |
| (`consolidated_obb`, ideated on the YOLO11 line) | attention plus k7 combined | not run | `mc_consolidated` | Roughly the sum of the parts, or less if they overlap |

**Prerequisite, do this first:** the seed-noise floor (3 runs, seeds 42/43/44, about 30 min). Three of the four expected deltas above are 0.01 to 0.04, and on 88 val images with a single seed that is not separable from run-to-run variation. The floor decides which of them we are allowed to call a result.

Pitfalls that have burned this line before and apply to all four forks:
- Copy the stock head keys verbatim (`end2end: True`, `reg_max: 1`) and keep the SPPF arg form `[1024, 5, 3, True]`. Copying a YOLO11-style row list drops them and silently rebuilds a different detector without an error (that is what invalidated V1/V2).
- The SPPF edit must keep all four arguments: `[1024, 7, 3, True]`, never `[1024, 7]`.
- The C2PSA swap changes params by about +0.4M, so there is no param-matched control. Report the delta as the effect of the change as a whole.
- Every fork passes `vm/ops/preflight_fork.py` (param count and head children against the control) before training starts, and control plus fork run in the same session with matched initialisation.

## Phase 3: Lead's Feature Concatenation Idea (by Fri Sep 13)

The lead suggested concatenating low and mid layer features more aggressively for small defects.

Possible implementations:
1. **Direct P3→P5 skip**: Concat row 4 (P3 features) directly into the P5 stage, bypassing the sequential FPN
2. **Multi-scale concat head**: Feed row 4 + row 6 + row 10 features simultaneously into a new detection head
3. **Feature Pyramid enhancement**: Add extra connections between backbone stages (e.g., row 2→row 6, row 4→row 8)

- [ ] Design 2-3 candidate architectures
- [ ] Validate structurally
- [ ] Train and compare against YOLO26 baseline

**Status 2026-09-11: ran twice (V1, V2), both UNATTRIBUTABLE.** V1 contained no head edit at all (its head rows are the stock YOLO26 head), V2's only real edit added raw upsampled P5 rather than a P3 skip, and both additionally changed the head config (`end2end`/`reg_max` dropped: 16 DFL bins, no one2one branch), the SPPF behaviour (legacy activated row, no residual) and the initialisation (from scratch vs a pretrained control). Moved to the YOLO26 spec log as a corrected entry. The clean test is re-run R1; the processed-P3 variant (`mc_processed_p3`) is the second candidate.

**R1 has since run (2026-09-11):** one raw P3 tap into the P4 stage, matched init, preflight PASS. Result: fork 0.6077 against its own control 0.6637, that is **-0.0560 mAP50 (-8.4%)**. The idea hurts in its raw form, at about a quarter of the old confounded deltas. The `mc_processed_p3` variant is now the open question.

## Phase 4: Results + Report (by Mon Sep 15)

**Status 2026-09-11 (session close):** registry updated with every result including R1 and R2 (34 rows, provenance per row). Still open: the noise floor (seed variance), matched-IoU for the R1/R2 arms, the corrected LR statement to the lead, the BiFPN and processed-P3 builds, and the git commit of the governance files.

- [x] Collect all metrics (mAP50, mAP50-95, IoU, matched rate) - done for every run except the R1/R2 IoU
- [x] Update registry with all results
- [ ] Write comparison report
- [ ] Present to lead

## Frozen Config (same as YOLO11 experiments)

### Single-class crop arena (crop_detect_dataset, nc=1)

- Split: 346 train / 88 val, seed 42, stratified
- Epochs: 100, patience: 50
- Batch: 8 (for fair comparison with batch-2/3 YOLO11 runs)
- imgsz: 1280
- optimizer: auto, lr0: 0.01
- Task: single-class detection (nc=1, class-agnostic)
- Data: crop_detect_dataset (our 434 single-size crops, axis-aligned labels)

**Pitfall for any LR experiment in this arena:** `optimizer: auto` discards `lr0` (8.4.142 logs `ignoring 'lr0=...'`). A "fixed LR" arm must set the optimizer explicitly, and the `lr` column in `results.csv` must be checked before the numbers are read. This is exactly the defect that invalidated the 2026-09-10 LR comparison.

### Multiclass arena (dataset_multiclass, nc=10) - the live line

- Split: 346 train / 88 val, seed 42 (same images, AABB labels from the OBB conversion)
- Epochs: 100, patience: 50
- Batch: 8
- imgsz: 1280
- optimizer: auto, lr0: 0.01 (auto resolves to AdamW lr 0.000714 at nc=10)
- Task: multiclass detection (nc=10, no single_cls)
- Baseline to beat: mAP50 0.5355, mAP50-95 0.3211 (VM-verified clean)
- Every fork must pass the P-9 gate (param count + head children match the control) before training.

## GPU Rules

- Shared A100 80GB with teammate srikantht
- Only one training job at a time
- Check `nvidia-smi --query-compute-apps` before launching
- One run at a time, sequential
