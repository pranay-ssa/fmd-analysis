# fmd-analysis - Handoff (formerly FMD-Preprocess)

**Date:** 2026-09-15 (YOLO26 H2 executed, then the CNN six-architecture matrix, then the augmentation workstream opened and paused for 2026-09-16; last full verification pass 2026-09-11)
**Project dir:** `D:/02-SSA/fmd-analysis` (local) → Azure VM (see VM details below)
**Status (resume here):** baseline line locked and thrice re-verified (the multiclass control has now reproduced 0.5355 / 0.3211 exactly three times, across two sessions). Re-runs done: **R2** (auto LR beats flat 1e-4 on our crops by 5.8-6.8% mAP50) and **R1** (one raw P3 tap into the mid stage costs -0.0560 mAP50 against a control that reproduced the old baseline exactly). **H2 done 2026-09-15 and FALSIFIED:** the processed version of the low-layer feature idea costs -0.0992 mAP50 on the multiclass arena (0.4363 against a 0.5355 control, recall -0.1059). Two independent tests now say that added low-layer inputs hurt. All work committed 2026-09-15 (four commits). Next, in order: **measure the noise floor** (seed variance, 20 min), **rank raw against processed on the same arena** (`mc_raw_p3_tap`, 20 min), then carry the within-pathway YOLO11 winners onto YOLO26, then `mc_bifpn` with a lowered prior. The lead correction is deliberately deferred (0.4 item 4). **Added 2026-09-15 (later session):** the resolution economics analysis (spec Entry 23: +26% to +40% mAP50 for native frames against 1280, at 3.4x to 3.7x training and about 3x inference, plus our own crop measurement of 1.38x), section 5 of the lead update, and two batches of ideated rows (the seven production-data levers and the six port-program arms). Registry now holds 48 rows, 19 of them ideated. The detailed next-step program with expected outputs per arm is section 0.5 below.

**Second workstream, CNN classifier line (section 10):** the six-architecture matrix on the combined 22-class set is complete. The lead's Architecture 3 and Architecture 4 were trained and evaluated 2026-09-15, the workbook now carries six rows plus a comparison sheet against the teammate's own six-architecture run on a different split, and the reader-facing notebook is built. The headline readings: Architecture 4 has the best macro balance of all six (at 4.3x the training time), Architecture 3 is last of the four Inception-family models on both splits, and the cross-split accuracy gaps are consistent with split luck rather than any model difference. **Added 2026-09-17 (later session):** the five per-line ResNet50 models ran (8,402 pictures, pooled 87.77 per cent), and the two follow-up experiments the lead asked for are prepared and CPU-validated but not started, waiting on the shared GPU: the six highlighted classes with ResNet50 (4,895 pictures, `run/class_subset_6_20260917/`) and the complete per-line split with ResNet50-Inception MultiLevel MultiScale. The seven line-comparison panel pairs and their brightness measurements are built under `reports/lines/line_comparison_20260917/`. Detail in `docs/next_experiments_20260917.md`.

**Third workstream, augmentation (section 11):** opened 2026-09-15 and paused the same day at the user's request, resuming 2026-09-16. The teammate's cut-paste defect augmentation now runs locally against the repo's own defect library, with label export and three verification instruments; three real defects were found and fixed, and one tone step at the paste junction is measured and still open. Nothing is committed yet. Decisions waiting: the target arena (classification crops or detection crops), the Fiber and HEMA Fragment gate, and volume plus split order.

**Audit trail for the corrections:** `reports/yolo26/DOC_CORRECTIONS_20260911.md` (evidence + the C1-C43 change list that produced this refresh).

---

## 0. RESUME HERE (2026-09-11) - YOLO26 architecture experiments

### 0.1 VM verification (2026-09-11): what changed in our understanding

Read-only verification against the VM's own artifacts (`vm/ops/verify_yolo26_claims.py`, `vm/ops/verify_yolo26_lr_trajectory.py`). Checklist IDs below refer to `reports/yolo26/DOC_CORRECTIONS_20260911.md`.

**FeatConcat V1/V2: UNATTRIBUTABLE (four uncontrolled variables).**

1. The VM yamls are byte-identical to the repo copies (md5 match), so these are the files that trained.
2. V1 had **no head edit**: its layer sequence is the stock YOLO26 head. Row 17 `[16, 1, Conv, [256,3,2]]` is the same reference as stock `[-1, ...]` (previous row is 16), and stock already contains the P3-downsample-into-the-P4-stage path (rows 17-18) and the P5→P4 top-down link (row 12). The file's own header comment describes a different (replacement) design that the body does not implement.
3. V2's only real edit is row 18 becoming a 3-way concat that adds row 11, the **raw upsampled P5** tensor, not a P3 skip. Param delta V2−V1 = 32,768 = exactly one extra 256-channel input group.
4. Both forks dropped the stock `end2end: True` and `reg_max: 1` keys, so the head rebuilt as `reg_max=16` with no one2one branch. Verified from the trained checkpoints: baseline `head.reg_max=1`, children `[cv2, cv3, dfl, one2one_cv2, one2one_cv3]`; V1/V2 `head.reg_max=16`, children `[cv2, cv3, dfl]`. Params 2504190 vs 2693491 / 2726259.
5. Both forks use the legacy SPPF row `[1024, 5]`; in ultralytics 8.4.142 that triggers the compat branch (`block.cv1.act = Conv.default_act`) and leaves `self.add = False`, unlike stock `[1024, 5, 3, True]`. Same params, different forward.
6. Both fork drivers build `YOLO(yaml, task="detect")` and never load the `weights` entry in their own `EXPERIMENTS` tuples, so the forks trained **from scratch** while the control used pretrained `yolo26n.pt`.

**LR comparison: was MISLABELLED, now re-run and settled (R2 RESULT below).**

- `run_crop_repro.py` sets `lr0=1e-4, lrf=0.0` but leaves `optimizer` at the default `auto`. In 8.4.142 `optimizer=auto` ignores `lr0`. `crop_repro_fixedlr.log` contains the trainer's own line: `optimizer: 'optimizer=auto' found, ignoring 'lr0=0.0001' ...` followed by `optimizer: AdamW(lr=0.002, momentum=0.9)`.
- Measured `lr/pg0` from `results.csv`: epoch 1 = 0.000636364 and peak = 0.00194 for **both** arms, with matching values at every sampled epoch through 80 (ep40 0.001228 vs 0.001220, ep60 0.000832 vs 0.000820, ep80 0.000436 vs 0.000420). The only realised difference is the final value (2e-5 vs 3.98e-5) plus the YOLO11 auto arm early-stopping at epoch 87 vs 100.
- Conclusion: the arms differ in the decay tail, not in auto-vs-fixed peak LR. The ~1% mAP gap is explained by that, not by the LR regime. Re-run required (R2).
- Loose end, recorded honestly: the tail differs by 2x while the args record `lrf` 0.01 vs 0.0, which does not reconcile cleanly. Do not rebuild the finding on that pair; re-run instead.

**R2 RESULT (2026-09-11, complete). Auto LR beats flat 1e-4 on our crops.**

| Arm (batch 16, 1280, seed 42, single_cls) | mAP50 | mAP50-95 | P | R | epochs |
|---|---|---|---|---|---|
| YOLO11n auto | 0.6007 | 0.3666 | 0.622 | 0.571 | 87 |
| YOLO11n flat 1e-4 (R2) | 0.5678 | 0.3400 | 0.6121 | 0.5525 | 79 |
| YOLO26n auto | 0.6166 | 0.3937 | 0.596 | 0.626 | 100 |
| YOLO26n flat 1e-4 (R2) | 0.5772 | 0.3423 | 0.5278 | 0.6101 | 100 |

- Gate passed on both arms: `args.yaml` carries `optimizer: AdamW, lr0: 0.0001, lrf: 1.0, cos_lr: false, warmup_epochs: 0` and `results.csv` `lr/pg0` reads 0.0001 at epoch 1 and at the final epoch (the invalidated arm read 0.000636364).
- Auto is ahead by **+0.0329 mAP50 (+5.8%)** for YOLO11n and **+0.0394 (+6.8%)** for YOLO26n; on mAP50-95 the gaps are +0.0266 (+7.8%) and +0.0514 (+15.0%).
- Context: the reference script's own 1280 comparison showed +2.1% of its fixed arm, and +15.8% at native 2464. Our crop gap lands between those, so "LR is irrelevant on crops" is dead and the resolution story is not clean either.
- Caveats: one seed per arm; the reference's fixed arm also disables warmup, so the comparison bundles schedule shape with warmup (that is the reference's own design); the YOLO11n fixed arm early-stopped at 79 epochs; matched-IoU for the two new runs is not yet computed.

**H2 RESULT (2026-09-15, complete). The processed low-layer tap also hurts, and by more than the raw one on its own arena.**

| Arm (multiclass arena, 10 classes, batch 8, 1280, seed 42) | mAP50 | mAP50-95 | P | R | params |
|---|---|---|---|---|---|
| H2 control (stock YOLO26n, pretrained) | 0.5355 | 0.3211 | 0.7580 | 0.4670 | 2,572,280 |
| H2 fork (raw P3 tap, downsampled, then C3k2-processed) | 0.4363 | 0.2320 | 0.6811 | 0.3611 | 2,676,344 |
| delta | **-0.0992** | **-0.0891** | -0.0769 | -0.1059 | +104,064 |

- Gates passed before any metric was read: local diff against the pinned stock yaml PASS (9 differing rows, all intended), `vm/ops/preflight_fork.py` PASS (head stock: `reg_max=1`, `one2one_cv2/one2one_cv3`), md5 of yaml and driver identical local vs VM, smoke build OK.
- Matched init: fork = yaml built then `.load("yolo26n.pt")` (363/768 items transferred; the new tap starts from scratch). Both arms logged the same first-epoch lr (0.000232591), so the schedule is controlled.
- Per-class: gains on Bubble (+0.0190, 227 val instances, the only well-supported class) and Foreign Matter (+0.0280, 19); losses on Bubble Cluster -0.1451 (26), Wet Package -0.1143 (35), Bubble On Edge -0.2597 (12), Fiber -0.0323 (12). Bubble On 123, the stated primary target, fell from 0.1317 to 0.0045 with 0% recall. HEMA Fragment and Extraneous Polymer moved by more than 0.2 on 2-3 val images and are not signal.
- **Do not compare -0.0992 with R1's -0.0560 as a ranking.** Different arenas, different baselines (0.5355 ten-class here, 0.6637 single-class there). The comparable fact is the sign, negative in both. `mc_raw_p3_tap` (0.4 item 7) is the same-arena arm that would settle raw versus processed.
- Conclusion: processing the features did not rescue the idea, so the failure is not raw noise alone. Added low-layer inputs have now failed twice, on two arenas, each gated and matched. Arm 2 of the 2026-09-15 update to the lead states this as "early-layer detail helps only after it is cleaned up" being disproved, and the docs record the falsification.
- Artifacts: `reports/yolo26/mc_processed_p3_summary.json` (mirrored), `experiments/yolo26/yolo26_mc_processed_p3.yaml` (md5 01dbbb696d77a22cc3df3de0c16da8fa), `vm/drivers/run_yolo26_mc_processed_p3.py`, registry rows `mc_processed_p3_control` / `mc_processed_p3`, spec Entry 22.

**Verified clean (no change needed):**

- Multiclass baseline: pretrained init, stock head (`reg_max=1`, one2one present), nc=10, params 2507700, mAP50 0.5355. This is the reference for architecture work.
- Single-class crop baselines: stock `yolo26n.pt`, batch 16 = 0.6166, batch 8 = 0.6637.
- Local mirrors in `reports/yolo26/` are byte-faithful to the VM summary JSONs. `crop_repro_summary_all.json` does **not** exist on the VM (each arm was run separately).
- The multiclass per-class table came from `vm/drivers/per_class_simple.py` (`v.summary()`), not from `yolo26_mc_summary.json`, which carries an empty `per_class_ap50` list. Provenance now recorded in the registry row.

### 0.2 What was completed this session (2026-09-10/11)

1. **Auto vs fixed LR comparison on the crop pipeline.** Four runs, values faithful, labels wrong (see 0.1). Data: `reports/yolo26/crop_repro_summary_fixedlr.json`, `crop_repro_iou_fixedlr.json`.
2. **Defect scale analysis (crop vs native).** Measured 2026-09-11: our crops run 1540-1596 px per side (88-image sample, 10 distinct sizes, mode 1560x1532; "~1556x1536" is a mode, not a constant, because crop size is per-class). Ultralytics resizes to 1280 at 0.82x. Native frames are 2448x2048, resized at 0.52x. Our crop GT boxes measure median sqrt(area) 13.03 px at crop resolution, which is 10.69 px effective at 1280, with 48.3% of boxes under 12 px; that confirms the ~10.7 px figure. The teammate's native-side median (~6.2 px) is NOT verified: their dataset files are not readable at the path their `data.yaml` records, so the "distributions are nearly identical" sentence remains unverified.
3. **IoU ceiling.** Median IoU stays at ~0.80 across all conditions (model, LR, pipeline). Data limitation (346 training images, annotation noise at 4-5 px), not model or resolution.
4. **Lead meeting (2026-09-10).** Presented crop pipeline results. Lead confirmed small defects are harder to find and suggested using low/mid layer features more aggressively. Committed to: translate YOLO11 experiments to YOLO26, investigate the feature concatenation idea.
5. **Feature concat experiments V1/V2.** Ran, both scored lower, but not attributable (0.1). The recorded deltas (0.411 and 0.451 vs 0.664) must not be read as the concat result.
6. **R1 (2026-09-11): the attributable version of the same question.** Fork = stock `yolo26.yaml` + one added tap (a stride-2 conv on raw backbone P3, row 4, concatenated into the P4 output stage), matched init, preflight-gated. Result: **control 0.6637 / 0.4111, fork 0.6077 / 0.3598, so the raw P3 tap costs -0.0560 mAP50 (-8.4%) and -0.0513 mAP50-95 (-12.5%), recall -0.0724.** The control reproduced the 2026-09-10 batch-8 baseline exactly, which validates both that baseline and this protocol. The old V1/V2 deltas were 4-5x larger and mostly confounds.
7. **YOLO26n multiclass baseline.** Built `dataset_multiclass` on the VM (OBB→AABB conversion, 10 classes, 346 train / 88 val, 1643 / 377 boxes). Trained and verified.

   Per-class AP50:
   | Class | Val Inst | AP50 | Recall | Category |
   |---|---|---|---|---|
   | Bubble Irregular | 9 | 0.940 | 0.983 | Strong |
   | Wet Package | 35 | 0.876 | 0.829 | Strong |
   | Foreign Matter | 19 | 0.739 | 0.579 | Medium |
   | Extraneous Polymer | 3 | 0.665 | 0.667 | Tiny support |
   | Bubble | 227 | 0.632 | 0.639 | Medium |
   | Fiber | 12 | 0.449 | 0.417 | Weak |
   | Bubble Cluster | 26 | 0.356 | 0.308 | Weak |
   | Bubble On Edge | 12 | 0.296 | 0.250 | Weak |
   | HEMA Fragment | 2 | 0.270 | 0.000 | Tiny support |
   | Bubble On 123 | 32 | 0.132 | 0.000 | Broken recall |
   | **Overall** | **377** | **0.535** | **0.467** | |

   **Bubble On 123 is the most broken class** - 32 instances, 0% recall. The model cannot find these defects at all. This is the primary target.

   Saved: `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`

8. **BiFPN check.** BiFPN is NOT a built-in module in ultralytics 8.4.142. A custom yaml (and a registered custom module) is needed.

### 0.3 Key learnings

- **A fork yaml must copy the stock head keys verbatim** (`end2end`, `reg_max`, and the module arg forms such as `SPPF [1024, 5, 3, True]`). Omitting them silently builds a different detector. This is what happened to V1/V2 (see ADR-011).
- **Fork arms must share the control's initialisation.** A from-scratch fork against a pretrained control is not a comparison.
- **A raw low-layer tap into the mid stage hurts, with a clean number now.** R1 (one added P3 tap, matched init, preflight gate passed) scored 0.6077 against a 0.6637 control: -0.0560 mAP50 (-8.4%) and -0.0513 mAP50-95 (-12.5%), with recall down 0.0724. The old V1/V2 deltas (-0.253 / -0.213) were 4-5x larger and mostly the head-config and init confounds. Sign confirmed, magnitude corrected.
- **Processing the tap does not rescue it (H2, 2026-09-15).** Adding the same low-layer detail through a C3k2 block cost -0.0992 mAP50 (-18.5%) on the multiclass arena, with recall down 0.1059. Two arenas, two gates, two positive controls: added low-layer inputs hurt whether they are raw or filtered. The direction of the fix is therefore not "add more inputs" but "improve processing inside the existing pathway", which is exactly where the YOLO11 winners came from.
- **Read per-class deltas only where the support is.** Bubble carries 227 of the 377 val instances; HEMA Fragment carries 2 and Extraneous Polymer 3. In H2 those two tiny classes moved by more than 0.2 in opposite directions, which is what noise looks like, while the well-supported classes (Bubble Cluster 26, Wet Package 35) fell by 0.11-0.15.
- **A control that reproduces the baseline is the cheapest confidence check available.** The R1 control landed on exactly the 2026-09-10 numbers (0.6637 / 0.4111 / 0.5993 / 0.6711), which is what makes the fork's delta believable.
- **The 80% IoU ceiling is data-limited, not model-limited.** Architecture changes will not break through it.
- **Crops help find more defects (mAP50) but do not improve box quality (IoU).** The benefit is in recall, not localisation.
- **Auto LR beats flat 1e-4 on our crops, and the earlier reading was wrong.** With the arm finally configured like the reference (`optimizer=AdamW, lr0=1e-4, lrf=1.0, warmup_epochs=0`, verified flat 0.0001 in the `lr` column), auto is ahead by +0.0329 mAP50 for YOLO11n and +0.0394 for YOLO26n (5.8% and 6.8%). The earlier "~1% gap, LR does not matter" came from two arms that both ran the auto schedule. The reference script's own numbers bracket ours: +2.1% at their 1280 and +15.8% at native 2464. The ~30% figure we had carried is not an LR gap at all: +31.7% is the native-vs-1280 resolution gain in mAP50-95.

### 0.4 What to do next (in order)

1. **Measure the noise floor (highest value, cheapest).** Every delta in this line is single-seed on 88 val images: run the same stock config twice with different seeds to learn what delta is meaningful. Without it the R1 (-0.056) and R2 (5.8-6.8%) numbers cannot be separated from seed variance. Two runs, about 20 minutes.
2. ~~**R1: attributable FeatConcat re-run.**~~ **DONE 2026-09-11.** Raw P3 tap into the mid stage hurts: fork 0.6077 vs control 0.6637 (mAP50 -0.0560, mAP50-95 -0.0513). Rows `yolo26n_r1_control` / `yolo26n_r1_p3tap`; the preflight gate is now mandatory for any fork.
3. ~~**R2: real fixed-vs-auto LR arm.**~~ **DONE 2026-09-11.** Auto wins: +0.0329 mAP50 (YOLO11n) and +0.0394 (YOLO26n) over flat 1e-4. Rows `yolo11n_crop_fixedlr_flat` / `yolo26n_crop_fixedlr_flat`.
4. **Correct the record with the lead - DEFERRED 2026-09-15 by decision.** The 2026-09-10 Teams message says "LR doesn't matter on crops". Decision: do not send a standalone correction; fold the corrected direction into the next update and settle the question on production-grade data. Reason: our own number (5.8-6.8%) is single-seed on 88 val images with no noise floor, so a separate correction would swap one uncalibrated claim for another. The evidence stays in 0.1 and spec Entry 20. The 2026-09-15 update to the lead (`reports/yolo26/UPDATE_FOR_LEAD_20260915.md`) frames it as "close on small data, and the gap grows as the defects carry more pixels".
5. ~~**Build processed-P3 variant**~~ **DONE 2026-09-15, FALSIFIED.** Processed low-layer tap costs -0.0992 mAP50 on the multiclass arena (0.4363 vs a 0.5355 control). Rows `mc_processed_p3_control` / `mc_processed_p3`; spec Entry 22.
6. **Build BiFPN for the multiclass arena** (custom module + yaml, not built-in). Registry row `mc_bifpn`. **Prior LOWERED 2026-09-15:** added cross-scale inputs have failed twice, so BiFPN is no longer the highest-expected-value experiment. It is still one run (it restructures fusion inside the pathway rather than bolting on an input), but the within-pathway YOLO11 winners now have the better evidence base. Must pass `vm/ops/preflight_fork.py` first.
7. **Rank raw against processed on the same arena** (`mc_raw_p3_tap`, new 2026-09-15): R1's raw P3 tap on the multiclass arena, so the two negatives can be ranked on identical ground. Control plus fork in one session, about 20 minutes. Without it, the only honest statement is "both hurt".

8. **Carry the YOLO11 winners onto YOLO26** (C2PSA attention at rows 6/8, SPPF k7, P4 Conv block), now gated by preflight rather than review. These are the only changes in this project with positive measured evidence (attention +0.059, P4 Conv +0.037, SPPF k7 +0.018 on the YOLO11 line). Recommended before BiFPN.
9. **Compare against the multiclass baseline** (mAP50=0.535, per-class table above). Focus on Bubble On 123 (0.132, 0% recall), Fiber (0.449), Bubble Cluster (0.356), Bubble On Edge (0.296).
10. **Matched-IoU for the R1, R2 and H2 arms** (mAP only so far). The commit decision is settled: done 2026-09-15, four commits, working tree clean, plus `25d5d33` (resolution economics) and `d4ca183` (update section 5 + the ideated levers).

### 0.5 The port program (2026-09-15): what is left, and what each step should produce

Everything the lead asked for is now answered or deliberately deferred: the spec and registry exist, the baselines are locked and re-verified, the LR question is re-run (R2), the lead's feature idea is tested twice and negative (R1, H2), and the 2026-09-15 update is written with the resolution economics added (spec Entry 23). What remains is the one lead ask not yet done: **carry the YOLO11 winners onto YOLO26 and verify them.**

Every YOLO26 change tested so far was a top-layer or direct-input change (R1, H2, V1, V2) or a straight model comparison (YOLO11 against YOLO26). The untested group is the one that actually moved YOLO11: **changes inside the existing pathway.**

Ordered program. Each arm is control plus fork in one session, `vm/ops/preflight_fork.py` before any training, one variable per fork.

| # | Arm | Change (one variable) | Expected output | Why this order |
|---|---|---|---|---|
| 0 | seed-noise floor (3 seeds) | nothing, stock config, seeds 42/43/44 | The seed spread, that is the delta below which nothing can be claimed | Every other number in this line is single-seed. Without it a +0.02 result cannot be called real. 3 runs, about 30 min. |
| 1 | `mc_attention_port` | backbone rows 6 and 8: C3k2 becomes C2PSA (the module the model already uses at row 10) | +0.02 to +0.06 mAP50; params about 2.57M to 3.0M; recall up more than precision; gains concentrated in the weak classes | Best-evidenced change we have: +0.059 mAP50 on the YOLO11 OBB arena at a third of the s-scale params, and the only variant that detected HEMA Fragment at all. |
| 2 | `mc_sppf_k7` | row 9 SPPF kernel 5 becomes 7, keeping the full arg form `[1024, 7, 3, True]` | 0.00 to +0.02 mAP50, zero params, zero compute | Free if it works, but +0.018 was its YOLO11 value, so it sits at the edge of what our data can resolve. Run it after step 0. |
| 3 | `mc_p4_conv` | 2 x plain Conv [512,3,1] at the P4 stage (after row 6, before row 7) | +0.01 to +0.04 mAP50 | +0.037 on YOLO11, and P4 was the stage that mattered there while extra P5 depth did not. Cheap. |
| 4 | `mc_consolidated` | the winners from steps 1-3 that cleared the noise floor, combined | Roughly the sum of the parts, or less if they overlap | This is the arm that could ship. The YOLO11 line already carries the analogue (`consolidated_obb`). Build it only from changes that individually passed. |
| 5 | `model_scale_s` | YOLO26s, stock architecture, no edits | The capacity reference: on YOLO11 the s scale gave +0.059 mAP50 | Tells us whether our edits beat simply using a bigger model. If they do not, the honest recommendation is the bigger model. |
| 6 | `mc_bifpn` | BiFPN in the neck (custom module and yaml, not built in) | Prior lowered: added cross-scale inputs have failed twice | Still worth one run because it restructures fusion inside the pathway, but it is no longer the leading idea. |

Decision rules for every arm: one variable per fork, control and fork in the same session with matched initialisation, preflight gate before training, matched-IoU computed alongside mAP, and per-class deltas read only where the support is (Bubble carries 227 of 377 val instances; HEMA Fragment and Extraneous Polymer move by more than 0.2 on 2-3 images and are noise).

Parallel track that costs no GPU: `data_iou_ceiling`, the re-annotation overlap measurement, which is the only way to turn "box precision is data-limited" from an inference into a number.

---

## 1. Where the work stands (conclusion first)

Three workstreams:

**Line A: Single-class detection on crops (baselines locked)**
- YOLO26n beats YOLO11n on every metric (mAP50 0.617 vs 0.601 at batch 16; 0.664 at batch 8)
- Feature concat: V1/V2 are **unattributable** (section 0.1), but R1 ran the clean version and it is now a real result: one raw P3 tap into the mid stage costs -0.0560 mAP50 (0.6077 vs a 0.6637 control), with matched init and a preflight-gated fork
- The LR comparison is **settled and corrected** (section 0.1): auto LR beats flat 1e-4 by 5.8-6.8% mAP50 on our crops; the earlier arm was invalid and the earlier "no difference" reading is dead
- IoU ceiling at ~0.80 is data-limited, not model-limited

**Line B: Multiclass detection (baseline verified clean)**
- YOLO26n multiclass: mAP50=0.535, mAP50-95=0.321, params 2507700, stock head
- Per-class AP50 ranges from 0.940 (Bubble Irregular) to 0.132 (Bubble On 123)
- Bubble On 123 has 32 instances but 0% recall - primary target
- The lead's low-layer feature idea is now **closed as tested and negative in both forms**: R1 raw (-0.0560 on the crops arena) and H2 processed (-0.0992 on this arena, 2026-09-15)
- Next: the port program in section 0.5, which starts with the seed-noise floor and then carries the within-pathway YOLO11 winners onto YOLO26. BiFPN keeps its registry row with a lowered prior
- Resolution economics (spec Entry 23): input size is the largest lever measured so far (+26% to +40% mAP50 for native frames against 1280, at 3.4x to 3.7x training and about 3x inference), and cropping already banked most of that detail cheaply

**Line C: CNN classifiers on the combined 22-class set (separate, section 10)**
- Six architectures complete, including the lead's Architecture 3 and 4. Architecture 4 has the best macro balance of the six; Architecture 3 is the weakest of the four Inception-family models on both splits, and attention failed in both positions on this data
- The cross-split accuracy gap is 5 to 12 images out of 293 and consistent with split luck; class imbalance and duplicate leakage were both ruled out
- Deliverables: the six-row workbook with a comparison sheet, and the reader-facing notebook for the lead

---

## 2. Key facts / credentials (redacted)

- **VM:** `pranayp@20.253.232.255` (azure VM `vm-amd-a100-westus2`). SSH key `C:/Users/HP/.ssh/pranayp-vm-amd-a100-keyfile` is **passphrase-protected**; there is **no ssh-agent** on the Windows host.
  - The same host has a second account, `amd100-user`, which owns the source data. Use the alias `amd-a100-vm` (user `amd100-user`, key `C:/Users/HP/.ssh/vm-amd-a100-westus2-srv_amd100-user_key`, also passphrase-protected). The two aliases point at the same VM: same HostName, same port, one HostName in `known_hosts`. Run data work as `amd100-user`.
  - `ControlMaster` multiplexing fails on this Windows/MSYS ssh build ("Failed to connect to new control master"), so plan one passphrase entry per invocation. Chain the remote work into as few invocations as possible.
  - **Armor blob access (added 2026-09-16):** downloader `vm/ops/download_armor_blobs.py`, VM copy `~/download_armor_blobs.py`. Key file `C:/Users/HP/.fmd/armor_blob_conn` locally and `/home/amd100-user/armor_blob_conn` on the VM (mode 600), also readable from `$ARMOR_BLOB_CONNECTION_STRING`. Record: `docs/armor_blob_transfer_20260916.md`.
  - To connect: start an interactive PTY (`terminal(background=true, pty=true)`), then answer the passphrase prompt with `process_manage(action="submit", ...)`. The passphrase must be re-requested from the user each session and must never be written to a file.
  - The `fmd-vm` alias in `~/.ssh/config` resolves correctly (HostName 20.253.232.255, User pranayp, IdentityFile as above, IdentitiesOnly yes).
  - VM keras 3.15.1, keras-hub 0.31.1, sklearn 1.9.0, GPU = A100 80GB.
  - VM ultralytics: `torch==2.6.0+cu124`, `ultralytics==8.4.142`. BiFPN is NOT a built-in module.
- **Shared VM:** other teammate homes exist (`amd100-user` 63G incl. 56G source data on `/data`, `srikantht`, `swetap`). Do not delete other users' files.
- **VM data + run paths (all under `/home/pranayp/yolo_ooi/`):**
  - `dataset_obb/` — canonical OBB dataset (10 classes, 346/88 split, images + labels)
  - `dataset_multiclass/` — AABB conversion of the OBB labels (nc=10)
  - `crop_detect_dataset/` — single-class detection (nc=1, axis-aligned crops)
  - `runs/yolo26_arch/` — YOLO26 architecture experiments (baseline, feat_concat, feat_concat_v2)
  - `runs/yolo26_multiclass/` — YOLO26 multiclass experiments
  - `runs/crop_repro/` — auto vs fixed LR experiments
  - **Fork yaml layout on the VM differs from the repo:** `experiments/yolo26_feat_concat.yaml` (flat) and `yolo26_feat_concat_v2.yaml` (project root). In the local repo both live in `experiments/yolo26/`. The drivers reference the VM paths.
  - Drivers: `run_yolo26_feat_concat.py`, `run_yolo26_v2.py`, `run_yolo26_multiclass.py`, `run_crop_repro.py`, `per_class_simple.py`
  - Logs: `yolo26_feat_concat.log` (V1), `yolo26_v2.log` (V2), `yolo26_mc.log`, `crop_repro.log` (auto arms), `crop_repro_fixedlr.log` (the mislabeled arms)
  - **R1/R2 artifacts (new 2026-09-11):** `experiments/yolo26/` now exists on the VM (mirrors the repo) and holds `yolo26_feat_concat_r1.yaml` plus its `.preflight.json`; `runs/yolo26_arch_r1/` holds `r1_control_stock` and `r1_fork_p3tap`; `r1_feat_concat.log`, `r1_feat_concat_summary.json`, `crop_repro_summary_fixedlr_flat.json`, `verify_scale.out` are all in the project root.
  - **New gate + drivers:** `preflight_fork.py` (mandatory fork gate), `run_yolo26_feat_concat_r1.py` (control + fork in one run, matched init, has `--smoke`), `verify_defect_scale.py`, `verify_yolo26_claims.py`, `verify_yolo26_lr_trajectory.py`. Repo copies live in `vm/ops/` and `vm/drivers/`.
  - **Environment note:** this VM's `python3` has **no pandas**. Drivers must be stdlib-only (use the `csv` module for `results.csv`), or the launch dies before training starts.
  - **Working layout rule:** on the VM, `YOLO` wrapper vs network: the head is `model.model.model[-1]` (the wrapper is `model`, the DetectionModel is `model.model`, the module list is `model.model.model`).
- **Verification scripts:** `vm/ops/verify_yolo26_claims.py`, `vm/ops/verify_yolo26_lr_trajectory.py` (read-only; copies also live on the VM under `/home/pranayp/yolo_ooi/`).
- **Local repo:** `D:/02-SSA/fmd-analysis` (7-zone layout, git tracked)

---

## 3. VM environment setup

```bash
# Connect to VM (interactive passphrase prompt - there is no ssh-agent)
ssh -i C:/Users/HP/.ssh/pranayp-vm-amd-a100-keyfile fmd-vm

# VM env (already installed)
torch==2.6.0+cu124, ultralytics==8.4.142, pillow-heif==1.7.0

# GPU check before any training
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader

# Agent pattern: terminal(background=true, pty=true) + process_manage(action="submit")
# Passphrase: request from the user each session, never store in a file

# MANDATORY gate before any training launch (2026-09-11 onward)
python3 preflight_fork.py experiments/yolo26/<fork>.yaml      # structure + head identity, exits non-zero on fail
python3 -u <driver>.py --smoke                                # build both models, no training
# then launch: python3 -u <driver>.py  (control and variant in the SAME run, matched init)
```

Two gate rules, both learned the hard way on 2026-09-11:

1. A fork is not allowed to train until `preflight_fork.py` says PASS. It asserts the stock keys are present, the SPPF arg form matches, the built head is stock (`reg_max=1` with the `one2one` branch), and it prints the row diff so an accidental extra edit is visible.
2. Every driver has a `--smoke` mode. A build error must cost seconds, not a launch cycle.

---

## 4. Dataset layouts on the VM

| Dataset | Path | nc | Labels | Split |
|---|---|---|---|---|
| OBB (canonical) | `dataset_obb/` | 10 | OBB (8 coords) | 346/88, seed 42 |
| Single-class detect | `crop_detect_dataset/` | 1 | AABB (4 coords, class 0) | 346/88 (symlinked images) |
| Multiclass detect | `dataset_multiclass/` | 10 | AABB (4 coords, class 0-9) | 346/88 (symlinked images) |

**Important:** `dataset_multiclass/` was built by `build_multiclass_dataset.py` — converts OBB corners to AABB via min/max. Images are symlinked from `dataset_obb/`. Labels are new files in `labels/{train,val}/`.

### 4.1 New source image drop, 2026-09-16

Two folders moved from the Armor blob account `stjnjmakearmor`, container `fmd-temp`, into `fmd_temp_images/` on the VM. That path is a symlink to `/data/FMD_Data_26082026/fmd_temp_images`.

| Blob folder | Images | GB |
|---|---|---|
| `Updated ICube Objects 20260915` | 4,230 | 19.8 |
| `Updated ICube Categorical Classes 20260915` | 6,384 | 29.8 |
| **Total** | **10,614** | **49.6** |

Every file is a 2,048 x 2,448 8-bit BMP of 5,014,582 bytes, so the byte total is exact. The transfer
ran on 2026-09-16 with 0 failures, about 8.6 minutes at 102.7 MB/s. Verification: every file was read
from disk again and MD5-checked against the service value, 10,614 of 10,614 OK, and the on-disk byte
total matches the source listing exactly. Two points need a decision before training: 143 images sit in
a `duplicates/` subfolder, and 27 image names appear in both folders. The full record, the script
detail and the re-run commands are in `docs/armor_blob_transfer_20260916.md`.

---

## 5. Experiment results summary

Detection line only. The CNN classifier results (six architectures on the 22-class set) are in section 10.

### Single-class detection (crop pipeline)

| Experiment | mAP50 | mAP50-95 | Mean IoU | Notes |
|---|---|---|---|---|
| YOLO26n auto LR (batch 16) | 0.617 | 0.394 | 0.728 | Stock weights, verified |
| YOLO26n auto LR (batch 8) | 0.664 | 0.411 | 0.729 | Stock weights, verified; arch-experiment baseline |
| YOLO26n "fixed LR" (batch 16) | 0.602 | 0.381 | 0.728 | **MISLABELLED**: trained on the auto schedule, lr0 ignored |
| YOLO11n auto LR (batch 16) | 0.601 | 0.367 | 0.695 | Stock weights, verified |
| YOLO11n "fixed LR" (batch 16) | 0.591 | 0.369 | 0.730 | **MISLABELLED**: same defect, kept as the audit trail |
| YOLO26n flat 1e-4 (R2, batch 16) | **0.577** | **0.342** | n/a | Valid: AdamW lr0 1e-4, lrf 1.0, no warmup, lr column flat 0.0001 |
| YOLO11n flat 1e-4 (R2, batch 16) | **0.568** | **0.340** | n/a | Valid: same knobs, early-stopped at epoch 79 |
| YOLO26n FeatConcat V1 | 0.411 | 0.237 | 0.654 | **UNATTRIBUTABLE**: no head edit in the file; head config + SPPF + init also changed |
| YOLO26n FeatConcat V2 | 0.451 | 0.271 | 0.657 | **UNATTRIBUTABLE**: added raw P5, not P3; same extra confounds |
| YOLO26n R1 control (batch 8) | 0.664 | 0.411 | 0.729 | Reproduces the 2026-09-10 batch-8 baseline exactly |
| YOLO26n R1 fork, raw P3 tap (batch 8) | 0.608 | 0.360 | n/a | **ATTRIBUTABLE**: -0.0560 mAP50 vs its own control; preflight-gated, matched init |

Numbers are faithful to the mirrored JSONs; only the labels/attribution were wrong. Every row's provenance is in `experiments/registry.json`.

### Multiclass detection (10 classes, batch 8, nc=10)

| Experiment | mAP50 | mAP50-95 | P | R | Notes |
|---|---|---|---|---|---|
| YOLO26n MC baseline | 0.535 | 0.321 | 0.758 | 0.467 | Verified clean (stock head, pretrained init) |

---

## 6. Hypotheses for next experiments

Documented in `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`. Registry rows now exist for each (`mc_bifpn`, `mc_processed_p3`, `mc_tap_points`, `mc_fpn_widths`).

| Hypothesis | Registry id | Expected gain | Confidence | Status |
|---|---|---|---|---|
| BiFPN bidirectional flow | `mc_bifpn` | +1-2% mAP50 | Medium | **NEXT TO BUILD** |
| Processed P3 features (C3k2 before concat) | `mc_processed_p3` | +1-3% mAP50 | Medium-high | Queued |
| Different backbone tap points | `mc_tap_points` | 0-2% mAP50 | Medium-low | Queued |
| FPN channel widths | `mc_fpn_widths` | 0-1% mAP50 | Low | Low priority |

**Focus classes:** Bubble On 123 (0.132, 0% recall), Fiber (0.449), Bubble Cluster (0.356), Bubble On Edge (0.296).

**Do NOT expect improvement on:** Bubble Irregular (0.940), Wet Package (0.876), HEMA Fragment (2 val images), Extraneous Polymer (3 val images).

---

## 7. What was sent to the lead

Teams message sent (2026-09-10) with:
- Defect scale comparison (crops vs native)
- Detection quality table (auto vs fixed LR, YOLO11 vs YOLO26)
- Box overlap quality table (IoU comparison)
- Key takeaways: crops help find more defects, LR doesn't matter on crops, YOLO26n is the better model, 80% IoU ceiling is data-limited

**Draft update prepared 2026-09-15:** `reports/yolo26/UPDATE_FOR_LEAD_20260915.md`, six sections and five takeaways: what cropping does, the box-precision data limit, the learning-rate question reframed (close on small data, the gap grows with defect pixel size), the early-layer detail question answered negative, input image size as the biggest measured lever with its cost (section 5, added 2026-09-15), and the preflight guardrail. Written for a non-specialist reader: tables for every number, each claim self-contained, no local file paths, no cross-section references. Delivery to the lead is the user's call; it has not been sent.

**Owed correction (updated after R2, 2026-09-11):** the "LR doesn't matter on crops" takeaway is now doubly wrong: the arm never ran at 1e-4 (both arms ran the auto schedule, so the original comparison tested two decay tails), and the corrected re-run shows auto ahead by +0.0329 mAP50 (YOLO11n) and +0.0394 (YOLO26n), i.e. 5.8-6.8%. The correction message must be self-contained, state its evidence inline (the trainer's `ignoring 'lr0=0.0001'` line, the measured `lr` column of 0.0001 constant in the corrected run, and both mAP pairs), and place our gap against the teammate's own numbers (+2.1% at their 1280, +15.8% at native 2464). No local file paths in the message.

---

## 8. Session close (2026-09-11)

**State:** the GPU is free, no training job is running, and no run was left mid-flight. All shells/sessions from this session were closed.

**Done this session:** the VM verification pass (two headline claims retired), the 43-item doc correction, the corrected R2 LR arms, the corrected R1 feature-concat pair, the new `preflight_fork.py` gate, the `--smoke` pattern, and the root-cause document. Registry holds 34 rows with `pending_reruns.R1.status = done` and `R2.status = done`.

**Not done, and deliberately so:**

- **Committed 2026-09-15** in three commits: `215844c` (the 7-zone reorganization recorded, `runs/` ignored), `b67eec6` (governance, registry, specs, corrections, root cause), `17f78bf` (VM drivers, eval, ops, preflight gate). The working tree is clean.
- **Security fix applied 2026-09-15:** the SSH passphrase was hard-coded in three ops scripts (`poll_gpu.sh`, `wait_b2.sh`, `wait_crop_repro.sh`). They now read `VM_SSH_PASSPHRASE` or prompt once, and write a private temp askpass helper. It was also present in one line of the VM's `~/.bash_history`, which was scrubbed (the file is now mode 600). It was never committed to git (checked across all history). **The key passphrase should still be rotated**, because it sat in plaintext files and shell history: `ssh-keygen -p -f ~/.ssh/pranayp-vm-amd-a100-keyfile`. The VM home directory is mode 755, so other users on the shared VM can read world-readable files there; `chmod 750 /home/pranayp` narrows that.
- The corrected LR statement has not been sent to the lead (draft in section 7).
- No matched-IoU for the R1 or R2 arms (mAP only).
- The noise floor is not measured, so every delta in this file is single-seed.
- `mc_bifpn` and `mc_processed_p3` are ideated in the registry but not built. (Since that date: `mc_processed_p3` ran and was falsified on 2026-09-15, the governance files are committed, and `mc_bifpn` carries a lowered prior.)

**First three actions as of 2026-09-11:** (1) commit the governance files (done 2026-09-15, four commits), (2) run the seed-variance pair for the noise floor (still open; it is step 0 of the port program in section 0.5), (3) send the corrected LR statement to the lead (deferred by decision; folded into the 2026-09-15 update). The current ordered plan is section 0.4 plus section 0.5, and the CNN classifier line is section 10.

---

## 9. YOLO11 OBB experiments (completed, for reference)

Batches 1-3 complete. Key findings:
- **LOCATION matters, not TYPE.** Adding layers helps only at P4 (mid-resolution), not P5 (deep).
- Winning ideas: attention C2PSA at rows 6/8 (+0.059 mAP50), SPPF k7 (+0.018), P4 Conv block (+0.037).
- Detailed analysis: `reports/yolo11/yolo_batch1_architecture_analysis.md`
- Spec: `reports/yolo11/yolo_arch_experiments_spec.md` (Section 10 log, entries 8-18)
- YOLO26 detect work now has its own log: `reports/yolo26/yolo26_arch_experiments_spec.md`

---

## 10. CNN classifier line (2026-09-15)

Separate workstream from the YOLO detection line above: whole-image ResNet-family classifiers on the combined 22-class set (22 classes, 1172 train / 293 test on our split, 224x224). Full numbers and reasoning: `reports/cnn/CNN_6arch_results_20260915.md`. Protocol and open items: `experiments/cnn/README.md`.

**State:** complete for the six architectures. The lead's Architecture 3 and Architecture 4 were added to `model_training.py`, smoke-built (58,744,051 and 45,988,758 params), trained and evaluated 2026-09-15 (arch 3 05:05 to 05:13 UTC, arch 4 05:13 to 05:49 UTC, both exit 0). The workbook carries six rows plus a comparison sheet against the teammate's own six-architecture run on a different split, and the reader-facing notebook is built for the lead.

| Architecture | Acc % | Macro F1 | Train s | Inference ms (warm) | Params |
|---|---|---|---|---|---|
| ResNet18 | 82.94 | 64.37 | 136.8 | 0.67 | not measured |
| ResNet50 | 88.40 | 70.14 | 345.4 | 1.28 | 25,716,630 |
| MultiLevel MultiScale | 88.05 | 70.49 | 495.0 | 1.75 | 58,547,094 |
| MultiLevel Attention (SE) | 87.37 | 70.98 | 380.9 | 1.51 | 50,544,246 |
| Arch 3, Inception + branch attention | 86.01 | 67.92 | 449.7 | 1.76 | 58,744,051 |
| Arch 4, Inception + refined decode | 88.05 | 73.64 | 2132.2 | 2.12 | 45,988,758 |

**Conclusions:**

- **Arch 4 is the best-balanced model of the six.** Joint top accuracy on our split, best macro precision/recall/F1 of all six (74.52 / 74.21 / 73.64), and top of the teammate's table. It reaches that with 12.6M fewer parameters than the plain Inception, because the depthwise plus 1x1 decode replaces the 2048-channel transposed convolution. The price is 4.3x the training time and the slowest inference of the six.
- **Arch 3 is the weakest of the four Inception-family models, on both splits** (86.01 against 88.05 ours, 88.74 against 90.44 theirs), with no size penalty (+0.197M params). Attention fails in both positions and in the same order on both splits: plain beats SE on the taps, which beats SE inside the branches. On this data, attention did not pay.
- **The two plain baselines do not hold their ranking across splits** (ResNet50 first for us and last for them, ResNet18 fifth for them and last for us), so only within-split comparisons count as architecture evidence.

**Cross-split comparison (their split, no warmup):** five of six architectures score higher on their split, by 2.05 to 3.76 pp, with ResNet50 the exception at -1.71. Class imbalance is ruled out (their inferred per-class supports match ours on 15 of 22 classes including every large one, and weighting their per-class deltas by our class sizes reproduces their overall accuracies to within 0.2 pp). Duplicate leakage is ruled out on our side (0 sources present on both sides, one crop per source, 0 shared filenames). The gaps are 5 to 12 images out of 293 against a sampling standard error of about 1.9 pp, so split luck is a sufficient explanation; the systematic part sits in Wet Package (ours worse in 6 of 6 models) and the bubble-family classes, which is a property of the test half rather than of any model.

**Warmup:** accuracy, per-class numbers and the confusion matrices are warmup-independent (warmup predictions are discarded, inference does not update weights; also recorded in `reports/cnn/OOI_CNN_Analysis_CORRECTED_20260908.md` section 6.3). The workbook's cold-start inference column is an ESTIMATE marked with a tilde. The teammate's ms/img is deliberately excluded from the comparison because their run had no warmup, and their internal architecture-to-architecture training-time ratios also look inconsistent with ours, which points at different machine conditions.

**Verification done this session:** the lead's four architecture cells are structurally identical to ours (`experiments/cnn/compare_lead_vs_ours.py`: helper blocks, assemblies and filter configurations all equal; the only code-level differences are the Keras 3 rename `alpha` to `negative_slope`, the layer name strings in Arch 3, and the packaging as callable functions). Our split integrity is clean (`check_split_integrity.py`). The notebook was verified to compile and to match the trainer function for function.

**Next steps for this line** (detail in the results doc section 8 and `experiments/cnn/README.md`): save the trained weights, measure the real cold-start inference, cross-evaluate on the other split, take a second split of our own, and optionally run the two new architectures on the 12-class Lens Presentation set.

**Artifacts:** `reports/cnn/CNN_6arch_results_20260915.md` (results + reasoning), the workbook (Sheet1 six rows + estimated cold column, Sheet2 comparison), `notebooks/FMD_CNN_6Architectures.ipynb` and its generator, `experiments/cnn/teammate_split_20260915.json` (their numbers as data), the two workbook builders, the two verification scripts, and one confusion matrix per new run (on the VM under `combined_22_runs/<arch>/epochs_50/`).

---

## 11. Augmentation workstream (local cut-paste), paused 2026-09-15, resumes 2026-09-16

**Status: the pipeline runs locally and is instrumented; nothing is committed yet.**
Started from the teammate's VM preview script `augment_pipeline.py` (kept for reference as
`vm/teammates/augment_srikanth.py`, md5 `dd15126ea22db9f9129f70eebae08242`, identical to the VM
copy). His idea is the 5 steps: select image, mark defect region, remove it, inpaint the hole,
reinsert the defect. Decision taken with the user: **build and test locally first, move to the VM
only once the script is solid.**

**Local assets confirmed sufficient:** `data/incoming/` holds all 1465 BMPs, every one 2448x2048
mode L, in 22 class folders whose counts match the VM library exactly, and `data/annotations.xml`
matches the VM exactly (435 images, 434 with boxes, 2020 boxes, 2015 rotated, 10 of 12 OOI classes
annotated; `Bubble Scatter` and `HEMA Obstruction` have no boxes at all). `opencv-python-headless`
(OpenCV 5.0.0) was added to `.venv`, the same cv2 major version as the VM.

**Built:** `experiments/augmentation/` with `cutpaste_augment.py` (5 steps, label export in
`labels.json` + YOLO OBB and AABB txt, manifest, summary, per-class QA sheets), `check_labels.py`
(label-vs-pixel check, patch-border step, paste junction step, optional 3x zoom crops),
`measure_paste_fidelity.py` (paste opacity per defect size), and `README.md` with the full protocol.
`run/augment/` added to `.gitignore`. The current output is `run/augment/preview_v3`.

**Verified (measured, 2026-09-15):**

| Check | Result |
|---|---|
| CVAT corner math vs `cv2.boxPoints`, all 2020 boxes | worst mask IoU **1.000000** |
| Preview run, 6 classes x 3 images | 18 sampled, 13 processed, 5 gate-skipped, 88 files, 11.6 s |
| Labels vs pixels | recall median 0.761, fill 0.865 |
| Patch border step | **0** at every border |
| Defect opacity at the core, defects <= 5 px | median **1.000**, 83% fully opaque (was 0.924 / 0%) |

Three real defects were found and fixed, each by an instrument rather than by eye: labels that sat
at the source position while the pixels moved (recall 0.000 on all 13 samples), a patch padded 2 px
against a 7 px Gaussian feather (border step up to 21 grey levels, now 0), and a fixed feather on
3-5 px defects that pasted them at 92% opacity median (now size-aware, 100%). One contrast meter was
discarded rather than patched (it returned retention ratios of -73 on this library: ring-shaped
bright defects, near-zero source contrast, and neighbours inside a defect's annulus), and one
apparent "hard rectangular seam" seen in a zoom turned out to be the removed defect's inpainted
footprint, not the paste.

**Open, measured, not fixed:** the paste junction carries a tone step of median **13.59** grey
levels (worst 42.69), which is median **1.48x** and worst **8.15x** the local surface noise. Cause:
the patch carries a rim of source background (box dilated 25%) laid onto a different part of the
lens. First candidate is matching the patch's low-frequency level to the destination before
blending; second is `cv2.seamlessClone` above some defect size (the teammate abandoned it because it
fails on tiny masks). `check_labels.py` already reports the junction, so either fix is accepted or
rejected on a number.

**Decisions waiting on the user before any generation at scale:**

1. Target arena: the 22-class classifier crops at 224, or the detection crops at 1280 where
   `Bubble On 123` is at AP50 0.132 with 0% recall (this is the recommendation, and the label export
   already supports it).
2. Fiber and HEMA Fragment: the 2% gate is really a 1.28% box-area gate once the 25% dilation is
   applied, and it excludes 45 of 62 Fiber boxes and 25% of HEMA Fragment. Learned inpainer (LaMa),
   or ship mark-only for those two classes?
3. Volume per class, and whether generation happens before or after the train/test split
   (an augmented copy must stay in its source's split; `manifest.csv` carries `source_image`).

The related ideated registry row is `aug_small_object` (data augmentation for small objects, status
ideated); the local work is its implementation path, and a note linking the two is worth adding when
this moves to the VM.

**Uncommitted work to commit at the start of the next session:** `experiments/augmentation/` (three
scripts + README), `vm/teammates/` (the teammate's file), `.gitignore` (the one added line), and the
2026-09-16 blob drop (`vm/ops/download_armor_blobs.py`, `docs/armor_blob_transfer_20260916.md`, plus
the HANDOFF entry).

---

## 12. Production line analysis and the five-model plan (2026-09-16)

The client question is whether one model can handle all production lines. The plan is **five
ResNet-50 models, one per line**, each trained on its own line only and scored on that line's
held-out images, then compared on the classes that three or more lines share. If the line-specific
models agree on the shared classes, the line carries no information and one model is justified.
The premise is that the capture method is identical, so an image carries no trace of its line.

The three folders label the same defect classes, so the analysis **pools them by class, not by
folder**, and every table counts one unique picture once. The pool is built by three rules, and every
number below depends on them:

1. `Low Dose` and `Low Dose Obstructing Region of Interest` are one class (86 pictures carry both names).
2. `Clear`, `HEMA` and `duplicates` are **not** defect classes, so 2,213 pictures whose only label is
   Clear or HEMA fall outside the 22-class set. The `duplicates/` folder adds no picture that is not
   already in a class folder.
3. A picture carrying two defect classes takes the class the **older library** assigns, which is the
   canonical taxonomy. That settles 51 pictures (33 of them Extraneous Polymer against Fiber).

Pool verified: 1,226 pictures sit in more than one folder and **none of them disagree on the line**.

Counts, each confirmed by two independent counts (identical SHA-256 over all 12,079 rows, plus a
third count of the old library):

- 12,079 images across the three folders; 10,614 unique pictures after content-fingerprint dedupe; **5 lines** (L24, L25, L26, L27, L31); **0 images without a line tag**.
- **Pooled defect-class dataset: 8,409 unique pictures across the 22 classes** (revised 2026-09-17; the 2026-09-16 revision said 8,401 and the difference is the 8 pictures the Updated Objects folder files under HEMA, which now read as HEMA Fragment). Per line: L24 2,853, L25 952, L26 1,220, L27 1,365, L31 2,019.
- **Comparison set: 13 classes are scorable on all five lines, 2 on four, 2 on three, so 17 of the 22.** 3 classes are scorable on two lines (one line pair each) and 2 on one line only (Dirty Camera, Bubble On 123), which give no comparison at all.
- **Splits, pooled, at 70:30:** 87 scorable class-line cells, 2,527 test and 5,882 train images (revised 2026-09-17; 2,525 and 5,876 before). At 80:20: 78 cells, 1,677 test and 6,732 train. Nothing is discarded either way, because every non-test image trains. Per line at 70:30: L24 858/1,995, L25 287/665, L26 365/855, L27 409/956, L31 608/1,411. The revision is recorded in `docs/line_split_revision_20260917.md`.
- **Thin cells:** 35 class-line cells hold fewer than five test images (L24 4, L25 7, L26 8, L27 7, L31 9). Seven classes have a single test image on at least one line (eight before the 2026-09-17 revision, when HEMA Fragment's weakest cell held one).
- **Data traps:** 1,465 repeated files (1,287 of the library's 1,465 images are byte-identical to images in the new drop; 1,249 of those also share the file name, so a name comparison misses 38 of them, and no file name appears in two folders over different content); of the 418 pictures with two labels, 271 involve Clear or duplicates and 10 pair HEMA with a defect class, so only 51 are real defect-against-defect conflicts.
- **The Updated Objects folder is a source, not a dataset:** it groups by object type (Clear 2,333, Foreign Matter 1,282, Fiber 328, Extraneous Polymer 267, HEMA 20), and Clear and HEMA are not classes. Its value is that it carries Fiber, Foreign Matter and Extraneous Polymer, which the new Categorical folder lacks; pooling lifts Fiber from 61 pictures to 359, Foreign Matter from 71 to 1,278, Extraneous Polymer from 17 to 234.
- **Three conditions for a conclusive comparison:** match the five training sets (pooled, L24 would train on 1,995 pictures and L25 on 665), compare per-class recall on shared classes rather than overall accuracy (the models carry different class lists), and set a tolerance in advance (35 thin cells; L27 has 7 classes and L31 has 9 with fewer than five test images).

**Independent verification on the VM (2026-09-16):** `vm/ops/verify_clear_on_vm.py` re-read and re-hashed all 12,079 files in the three folders on the VM (`/home/amd100-user/FMD_Data_26082026/fmd_temp_images`), matched them against `manifest.csv` (0 mismatches), rebuilt the pool from the files and diffed 48 numbers against the published ones. Result: every figure reproduced except `pictures_in_two_folders`, where our prose said 1,278 and the data says **1,226** (1,278 is the Foreign Matter class total, transposed by hand); the prose in HANDOFF, the markdown record and the lead message was corrected. The name-versus-content check was added in the same pass: no file name appears in two folders over different content (0 false merges), 1,287 of the library's 1,465 files overlap the new drop by content against 1,249 by name, 122 pictures are filed under more than one name across folders, and of the 128 Clear pictures carrying a defect class 123 share the file name and 5 differ by appended score fields. **The Clear question is recorded in `docs/clear_tag_analysis_20260916.md`, including a superseded-numbers table; treat that doc as the authority for the 2,333 / 128 / 2,205 figures and for the 1,226 correction.**

Artifacts: `reports/lines/line_report_20260916.html` (reader page: sections 2 and 3 are folder-agnostic and class-centric, generated by `src/make_line_report.py` from `run/line_eda/20260916/*.csv`), `reports/lines/LINE_TAG_ANALYSIS_20260916.md` (full record, sections 6 and 7 hold the pooled matrix), `reports/lines/teams_message_clear_20260916.md` (message for the lead), `reports/lines/all_lines_class_split_70_30.md`, `reports/lines/FMD_class_split_70_30.xlsx` and `reports/lines/FMD_class_split_70_30_vs_80_20.xlsx` (class-wise splits, one sheet per line plus a summary, built from `run/line_eda/20260916/all_lines_class_split_70_30.csv` and `..._70_30_and_80_20.csv`), the 2026-09-17 revision of the splits (`src/make_line_splits.py`, `run/line_eda/20260917/*.csv`, `reports/lines/ALL_LINES_class_split_70_30_20260917.md`, `reports/lines/FMD_class_split_70_30_20260917.xlsx`, `reports/lines/FMD_class_split_70_30_vs_80_20_20260917.xlsx`, `experiments/eda_client/verify_line_splits.py`, recorded in `docs/line_split_revision_20260917.md`), the client EDA workbook (`reports/library/FMD_Library_EDA_Counts_20260917.xlsx`, `experiments/eda_client/`, recorded in `docs/client_eda_numbers_20260917.md`), `reports/lines/teams_message_clear_verified_20260916.md` (the Clear answer for the client), `reports/lines/line_heatmap_22x5.png|.pdf|.jpg` (the section 3 heatmap at 400 dpi), and `docs/clear_tag_analysis_20260916.md` (the Clear question: numbers, method, superseded numbers, open decision).

**Per-line models run (2026-09-17, step 4):** five ResNet50 models, one per production line, trained and evaluated. The split assignments were built by `src/build_line_split_assignments.py` from the revised 70:30 table: 8,402 pictures, 5,875 train and 2,527 test over 87 class-line cells, with the 7 single-picture cells that have no test picture dropped from their line. Input is the raw 2448x2048 frame resized to 224x224 (no crop), batch 4, 50 epochs, seed 42, 54.4 minutes on the A100 for all five. Accuracy: L24 87.30, L25 91.29, L26 84.38, L27 84.60, L31 90.95; pooled 87.77 percent, pooled weighted F1 87.33. Two readings that matter before any per-class number is quoted: **the score tracks the test-cell size, not the line** (35 cells hold 1 to 4 test pictures and have a median F1 of zero, while no cell with 25 or more scores zero), and 142 of the 309 misclassified test pictures sit inside the Foreign Matter / Fiber / Extraneous Polymer family, whose labels overlap in the dataset itself. Full record `docs/line_models_20260917.md`, workbook `reports/cnn/FMD_Line_ResNet50_Results_20260917.xlsx`, notebook `notebooks/FMD_Line_Models_20260917.ipynb`, verifier `experiments/cnn/verify_line_results.py` (910 checks, 0 failed), local mirror `runs/cnn/lines/<line>/epochs_50/`. The trained weights stay on the VM at `~/line_experiment_20260917/runs/<line>/epochs_50/`; nothing was copied from the image library, which the runs read by absolute path.

**Six-class and multi-scale runs (2026-09-17, step 4 continued):** the two experiments the lead added both ran, A from 09:54Z for 32 minutes and B from 10:46Z for 63 minutes, five lines each, all exit 0, GPU released.

*A, the six highlighted classes on ResNet50* (a smaller set: 4,895 pictures against the full split's 8,402, of which 3,424 train and 1,471 test, built from the existing split so every picture kept its side). Pooled accuracy 96.26 percent against 90.34 percent for the full ResNet50 model restricted to the same six classes on the same pictures, so **+5.92 points from narrowing the classes**, and macro recall +6.84. Best where data is thinnest: L31 +17.43 points on 132 test pictures, L27 +12.84 on 218; L26 level (its macro-recall drop is two classes with 1 or 2 test pictures, not a regression). Workbooks `reports/cnn/FMD_Line_SixClasses_ResNet50_20260917.xlsx` and `reports/cnn/FMD_SixClasses_vs_FullModel_20260917.xlsx`, record `docs/next_experiments_20260917.md` section F.

*B, the complete split on ResNet50-Inception MultiLevel MultiScale.* Pooled accuracy 89.47 against ResNet50's 87.77 on the identical 2,527 test pictures, so **+1.70 points**, while **mean macro recall falls 2.67 points** (59.26 to 56.60). The gain is concentrated and the loss is spread: Foreign Matter +24 correct answers (+0.95 points), View Obstructed +13, Extraneous Polymer +12, Multiple Lenses +8, against Bubble -5 and Lens Off Center -4; 20 class-line cells recalled more, 26 fewer, 41 unchanged. The per-class decomposition adds up to the pooled change exactly and the comparison script asserts it. Artifacts: `reports/cnn/FMD_Line_MultiScale_ResNet50_20260917.xlsx` (31 checks against the run's own metrics, 0 failed), `reports/cnn/FMD_Architecture_Comparison_20260917.xlsx`, `notebooks/FMD_Line_MultiScale_20260917.ipynb` and `notebooks/FMD_Architecture_Comparison_20260917.ipynb` (the lead reads notebooks), `run/line_results_multiscale_20260917/arch_vs_base.json`, `experiments/cnn/compare_architectures.py`, `experiments/cnn/make_arch_comparison_workbook.py`, `experiments/cnn/verify_multiscale_workbook.py`. Local mirror of the metrics `runs/cnn/lines_multiscale/<line>/epochs_50/`; weights stayed on the VM.

Both numbers are single-seed and the seed spread has still not been measured on this data, so the 1.70-point gain should not be treated as settled. The honest summary of both runs together: narrowing the decision (A) helps every line, while widening the model (B) helps the common classes and costs the rare ones, which is a product decision rather than a measurement one.

Disk, same session: the teammate confirmed his 57 GB copy could go and it was removed after a file-by-file match against the /data copy (12,081 files by name and size, 51 checksums, none differing). Free space 3.1 GB to 60 GB, root filesystem 98 percent to about 50 percent used. Record with the safeguard used: `reports/ops/disk_breakdown_20260917.md`.

Open before any further training: matched or full per-line sets, the similarity tolerance, whether to run the line-predictability check, the 7 classes only the library carries, and whether Clear returns as a 23rd class. The five per-line models have run, and so have both follow-ups (above). Still open: whether the multi-scale architecture goes forward given it wins on pooled accuracy and loses on macro recall, the seed-spread measurement that would say whether the 1.70-point gain is above run-to-run variation, one pooled model on the same split, and the batch-4 against batch-8 cost question.

## Suggested skills (invoke as relevant)
- `yolo-obb-pipeline` — YOLO/OBB detection pipeline setup and pitfalls
- `remote-ssh-access` — the PTY + submit pattern for this VM's passphrase-protected key
- `verification-before-completion` — evidence-first before claiming results
- `systematic-debugging` — if training fails or metrics look wrong

## References (do not duplicate content from these)
- `reports/yolo26/DOC_CORRECTIONS_20260911.md` — the corrections audit trail (evidence + C1-C43, plus Parts 5-7 covering R2 and R1)
- `reports/yolo26/ROOT_CAUSE_20260911.md` — how the wrong conclusions entered the record, the seven failure modes, and the standing rules that block each one
- `reports/yolo26/r1_feat_concat_summary.json` — R1 control + fork (the first attributable architecture result)
- `reports/yolo26/crop_repro_summary_fixedlr_flat.json` — R2 corrected flat-1e-4 arms
- `experiments/yolo26/yolo26_feat_concat_r1.yaml` — the R1 fork (preflight PASS, kept as the template for future forks)
- `vm/ops/preflight_fork.py` — the mandatory fork gate
- `vm/ops/verify_defect_scale.py` — the crop-vs-native defect scale measurement
- `reports/yolo26/yolo26_arch_experiments_spec.md` — YOLO26 detect log (single source of truth for this line)
- `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md` — multiclass baseline + hypotheses
- `reports/yolo26/crop_repro_report.md` — single-class crop repro results
- `reports/yolo26/crop_repro_summary.json`, `crop_repro_iou.json` — auto-LR results (verified faithful to the VM)
- `reports/yolo26/crop_repro_summary_fixedlr.json`, `crop_repro_iou_fixedlr.json` — mislabeled LR arm, kept for the audit trail
- `reports/yolo11/yolo_arch_experiments_spec.md` — YOLO11 OBB spec (single source of truth for that line)
- `reports/yolo11/yolo_batch1_architecture_analysis.md` — YOLO11 batch 1 analysis
- `experiments/README.md` — governance: dos/don'ts, pitfalls, ADRs, blast radius
- `experiments/registry.json` — every experiment + result, plus `pending_reruns` (R1-R3)
- `experiments/yolo26/yolo26_feat_concat.yaml`, `yolo26_feat_concat_v2.yaml` — the two invalid fork yamls (kept as negative examples)
- VM: `/home/pranayp/yolo_ooi/yolo26_feat_concat.log` (V1), `yolo26_v2.log` (V2), `yolo26_mc.log` (multiclass), `crop_repro.log` + `crop_repro_fixedlr.log` (LR arms)
