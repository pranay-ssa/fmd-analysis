# experiments/ - YOLO Architecture Experiments

**Owner:** Pranay
**Scope:** structural experiments on YOLO11-OBB and YOLO26 backbones for Object-of-Interest (OoI) contact-lens defect detection.
**Companion docs:** `registry.json` (every experiment + result in one place, machine-readable, plus `pending_reruns`), `reports/yolo11/yolo_arch_experiments_spec.md` (YOLO11 OBB timestamped Section 10 audit log), `reports/yolo26/yolo26_arch_experiments_spec.md` (YOLO26 detect log), and `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md` (YOLO26 multiclass baseline + hypotheses). This README is the governance layer: the ideology, the dos and don'ts, the pitfalls, the technical debt, and the ADRs.

---

## 1. Why we experiment here (the ideology)

We are not building a leaderboard. We are learning *how YOLO actually works* and *why* a structural change moves (or does not move) the model. Every experiment, including the ones that "fail", must end with a stated reason, because a well-characterized null result is as informative as a win.

Two hard principles:
1. **Change exactly one thing per run.** The batch-2 `depth_plus2_deep` test changed four variables at once (the fact of adding layers, the layer TYPE, the LOCATION, and a small DOSE because the n-scale width shrinks channel args). Its flat result told us nothing specific. We re-frame it as a question, not a verdict, and answer it by ablation.
2. **Grounded, not asserted.** Every number in `registry.json` is regenerated from `results.csv` / `metrics.json`, never hand-typed. Relative deltas are the signal; absolute mAP on 88 val images is expected-low and not worth chasing.

## 2. What we are experimenting for

- Find backbone/neck edits that improve OoI detection, measured on **mAP50, mAP50-95 and matched-IoU** (the lead's metrics of record). Precision/recall stay logged but are diagnostics only.
- Characterize the *axis* of each change: module (attention, pooling), capacity (width, depth), scale/pyramid, head/neck, feature-fusion. Registry rows carry an `axis` label so we can tell which lever is worth pulling.
- Understand the trade-off surface (params vs GFLOPs vs IoU vs mAP50-95) so decisions are defensible to the lead and the team.

## 2a. YOLO26 experiments (current focus)

YOLO26 experiments use the same frozen split (346/88, seed 42) as YOLO11. Three arenas are live (see ADR-007 for the full rule), plus one planned:
- **Single-class detection** (crop_detect_dataset, nc=1, single_cls=true, imgsz 1280): baselines 0.617 (batch 16) and 0.664 (batch 8), IoU 0.728-0.729. Both from stock `yolo26n.pt`, verified on the VM 2026-09-11.
- **Multiclass detection** (dataset_multiclass, nc=10, imgsz 1280): baseline mAP50=0.535, mAP50-95=0.321, verified clean (pretrained init, stock head with `reg_max=1` and the one2one branch). Per-class AP50 from 0.940 (Bubble Irregular) down to 0.132 (Bubble On 123, 0% recall). Primary target for architecture experiments.
- **YOLO11 OBB on crops at 640** (the older arena, batch 1-3): reference only, not comparable to either detect arena.
- **Resolution and data levers** (`production_size_and_data_levers`, planned, no runs): input size on our crops, tighter crop margin, two-stage cascade, annotation-ceiling measurement, small-object augmentation, capacity step, seed ensemble. Ideated only and deliberately held for the production-grade set, because on 346 training images the effects in that range cannot be separated from run-to-run variation (registry rows prefixed `res_`, `data_`, `aug_`).

**The feature-concat runs (V1, V2) are NOT evidence of anything yet.** They are recorded as `UNATTRIBUTABLE` in `registry.json`: V1 contained no head edit at all, V2 added raw upsampled P5 (not P3), and both also changed the head config (dropped `end2end`/`reg_max`, so they trained 16 DFL bins with no one2one branch), changed SPPF behaviour, and trained from scratch against a pretrained control. See ADR-008 and ADR-011, and `pending_reruns` R1 in the registry.

**YOLO26 vs YOLO11:** Same backbone structure (Conv, C3k2, SPPF, C2PSA). Key difference: YOLO11 OBB head (rotated boxes) vs YOLO26 Detect head (axis-aligned, end-to-end). The backbone and neck are structurally similar, but the YOLO26 head is NOT interchangeable with a YOLO11-style head and needs its yaml keys preserved (ADR-011).

**Hypotheses under test (registry ideated rows, 2026-09-15):** the port program leads, because it is the only group with positive measured evidence behind it, and all of that evidence sits inside the existing pathway: `mc_noise_floor` (the prerequisite measurement), `mc_attention_port` (C2PSA at rows 6/8, +0.02 to +0.06 expected), `mc_p4_conv`, `mc_sppf_k7`, `mc_consolidated`, plus `mc_raw_p3_tap` as the arena control for H2. `mc_bifpn` keeps its row with a lowered prior. Full hypothesis doc: `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`.

**What NOT to do:** Don't add raw backbone features straight to the head without them being processed first, and don't cite the V1/V2 numbers as the reason (they changed four variables at once). The design preference stands on the FPN's role, not on those runs.

## 3. How to add an experiment (the loop)

1. **Ideate** the change and record it in `registry.json` with an `axis`, a `hypothesis`, and a `theoretical_possible` flag (true / partial / custom-needed). A row only earns a file once its idea is written down.
2. **Design the yaml fork**, changing exactly one thing. Start from the packaged stock yaml for that family and keep every key you are not intentionally editing, especially the head keys (`end2end`, `reg_max`) and full module arg lists (ADR-011). For any row insertion, recompute the head routing refs and retap (see Pitfalls P-3). For YOLO26, use `task="detect"` (not OBB).
3. **Validate locally first**: run the structural validator (`vm/drivers/validate_yaml.py` for YOLO26, `experiments/validate_backbone_edit.py` for YOLO11). This catches routing bugs, channel mismatches, and future-row references before they burn GPU.
4. **Validate on the VM**: `YOLO(fork, task="detect")` builds and prints a param count. Confirm the numbers match expectation. Check `layers[i].f` (from attribute) matches your intended routing.
5. **Train** one run at a time on the shared A100 (never over a teammate's job; check `nvidia-smi --query-compute-apps` first). Batch 8, seed 42, 100 epochs, frozen split.
6. **Measure** mAP50 / mAP50-95 / precision / recall from `results.csv` best epoch, and IoU from `vm/iou_eval_det2.py` (the correct one; `iou_eval_det.py` is BROKEN). For multiclass, also pull per-class AP50 via `v.summary()`. Write the results into `registry.json` and append a spec Entry with outcome AND reason.

## 4. Dos

- Do change exactly one variable per run; pairs that keep a variable fixed (Arm A type, Arm B location) are how we isolate a null.
- Do keep the frozen split (346/88, seed 42) and protocol untouched. Deltas are only attributable if the environment is identical.
- Do validate structurally (step 3) before any GPU time, and verify the exact param count on the VM.
- Do record every outcome and reason, including failures, in the spec log + registry.
- Do check the GPU is free (one-at-a-time on the shared A100) before launching.
- Do use batch size consistently within a comparison set (batch 8 for batch-2+; batch-1 at 16 is reference only).
- Do treat precision/recall as diagnostics and mAP + IoU as the decision metrics.

## 5. Don'ts

- Don't change multiple variables at once (the depth-plus2 mistake); it makes the result uninterpretable.
- Don't compare across batch sizes as if exact (8 vs 16 moves ~nothing here, but treat cross-batch deltas as indicative).
- Don't use a path-list `dataset.yaml` (`train: train.txt`); use the canonical dir tree `dataset_obb/` (path-list breaks label pairing and chokes on spaces in dir names).
- Don't append backbone rows without retapping the head: rows added after row 10 with the P5 tap left at 10 are dead compute with no loss path.
- Don't swap in a module that does not exist in ultralytics 8.4.142 (e.g. `SPPFCSPC`, `BiFPN`) without registering it as a custom module - it will fail or silently no-op.
- Don't rely on the yaml filename for scale unless intended: ultralytics picks the scale from the filename (rename `?...s` forks so the `s` row is actually selected).
- Don't hand-type any number into `registry.json`; read it from `results.csv` / `metrics.json` / `iou_metrics.json`. If a number has no recorded source, mark it as unverified rather than guessing.
- Don't leave credentials in any file here or under `vm/`; use the ephemeral askpass helper only.
- Don't omit the head-level yaml keys when forking (`end2end`, `reg_max`) or shorten a module's arg list (`SPPF [1024, 5]` instead of `[1024, 5, 3, True]`). `parse_model` fills the gaps with different defaults and the fork silently becomes a different detector; see ADR-011 and pitfall P-9.
- Don't add raw backbone features directly to the head unprocessed. The FPN's sequential fusion is the design that works; if you want to add features, process them first (C3k2, channel reduction) and keep the standard FPN path intact. Note the supporting *evidence* for this is pending (V1/V2 were unattributable, R1 pending).
- Don't compare a fork trained from scratch against a control trained from pretrained weights. Match the initialisation (ADR-012).

## 6. Pitfalls (specific to this experiment line)

- **P-1 width scale shrinks channel args.** The n-scale width factor (0.25) multiplies yaml channel args. `Conv [1024]` is ~256 effective channels, +0.59M params per added conv. This is why `depth_plus2_deep` is 3.88M params, not the ~21M a naive read would guess. Always confirm on the VM, never trust the yaml arg as the real width.
- **P-2 baseline row 4 is `C3k2 [512]`, not `[256]`.** A fork that copies `[256]` there silently diverges from the validated control. The structural validator catches this.
- **P-3 head retap is mandatory on any insertion.** Adding N rows shifts all downstream indices by N. P5 concat, head P4 ref, and the OBB input list `[a,b,c]` must all be updated; the P3/P4 backbone taps before the insertion stay.
- **P-4 `model.info()` returns None in this ultralytics build.** Use the parameter count `sum(p.numel() for p in model.model.parameters())` for cost; GFLOPs are currently unavailable and should not be quoted as measured.
- **P-5 the final head rows (e.g. P5 stem when you insert into the P4 stage) keep their real channel:** inserting `Conv [512]` at P4 then resuming must use the baseline `Conv [1024, 3, 2]` as the next row, not `[512]`. The validator caught exactly this bug in `armB` before training.
- **P-6 `val_inf_ms` in `metrics.json` is inflated**, not the warm-benchmark number (it includes dataset setup + the tree). Do not quote ms/img from it; follow the latency guidance in the fmd-preprocess skill for honest timing.
- **P-7 matched-IoU is computed over only the boxes matched at conf >= 0.25** (greedy, class-aware). Mean IoU ~0.56 with match rate ~37-38% means recall (fraction of GT boxes detected) is the binding constraint, not box accuracy. Read IoU together with match rate.
- **P-8 consecutive-weight misses:** most run `weights/` (best.pt/last.pt) stay on the VM; only selected ones mirror locally. Weights on the VM are the canonical model artifacts.
- **P-9 the head-config trap (bit us on the YOLO26 forks).** `parse_model` reads `reg_max = d.get("reg_max", 16)` and `end2end = d.get("end2end")`, and for base modules it rebuilds args as `[c1, c2, *args[1:]]`. A fork yaml that omits `end2end`/`reg_max` or shortens the SPPF row therefore builds a *different* detector while the topology looks identical: V1/V2 trained `reg_max=16` with no one2one branch (params 2693491 vs the control's 2504190) and an activated, residual-less SPPF. Gate before training: build the fork and print `sum(p.numel())`, `model.model[-1].reg_max` and `sorted(dict(model.model[-1].named_children()))`; they must match the control except for the intended edit.
- **P-10 layer-type sequences are not enough to prove identity.** V1's layer-type list was byte-identical to stock while the built model differed in head config and SPPF behaviour. Compare param counts and head children, not just the type list.
- **P-11 "optimizer=auto" silently discards lr0.** In 8.4.142, `build_optimizer` logs `ignoring 'lr0=...'` and substitutes its own value (`lr_fit = 0.002*5/(4+nc)` for AdamW when iterations <= 10000, else MuSGD at 0.01). Any "fixed LR" arm must set `optimizer` explicitly, and the `lr` column in `results.csv` must be checked before the run is believed.
- **P-12 initialisation must be recorded per run.** `YOLO(yaml, task="detect")` ignores any separately passed weights path and builds from scratch; `YOLO(yolo26n.pt).load(fork.yaml)` or training the control from the same yaml is how a control/fork pair stays comparable.

## 7. Technical debt

- **GFLOPs readout broken** (P-4): we track params only; a GFLOPs path (thop-style count or a patched `model.info`) is owed.
- **IoU coverage.** Every registry row in the three YOLO11/YOLO26 crop arenas carries `iou_mean_matched`, including the batch-16 batch-1 rows (an earlier note here claimed batch-1 IoU was null; it is not). Still missing: a matched-IoU number for the multiclass detect arena (`multiclass_detect_1280_10cls`), where only mAP and per-class AP50 have been computed.
- **Two summary sources.** `registry.json` is the registry summary; `results.csv` is per-epoch truth. No automated sync yet - keep them consistent by regeneration, and treat registry as derived.
- **Fused vs unfused params discrepancy** (baseline 2,655,673 fused vs 2,695,747 build). registry rows record what each run logged; the difference is ultralytics fusing. Do not mix the two as if equal.
- **No automated `registry.json` updater.** A small script that reads a run's metrics.json + iou_metrics.json and upserts the row would remove human-typing risk.
- **Uncommitted / untracked state.** Many run outputs and this experiments folder are not committed to git. Decide and commit the governance files (registry.json, README.md, spec) so the state is recoverable.

## 8. Blast radius

- **Shared A100 (80GB)**: the highest risk. Launching over a teammate's job steals their GPU and can corrupt concurrent training. Always confirm zero `--query-compute-apps` before a run. A crashed/duplicate remote job can also corrupt a run folder; verify exactly one process after launch (DataLoader workers share the command line, so count >1 is normal - check the log stream, not just the count).
- **A broken yaml can silently no-op or OOM.** The cost of a wrong yaml is hours of GPU and a misleading result. Validation (steps 3-4) is the gate.
- **The frozen split is shared and sacred.** Moving it invalidates every comparison. Do not touch the split, the seed, or `dataset_obb/`.
- **Real data set is small (434 images / 377 val instances).** Tiny-support classes (Bubble On 123, Bubble On Edge, Extraneous, HEMA, ~2-3 val images each) produce noisy per-class AP50. Never read a per-class delta on fewer than ~15 train images as architecture signal.
- **Credential exposure.** The VM key passphrase must live only in the ephemeral askpass helper, never in repo files including this folder.

## 9. ADRs (Architectural Decision Records)

- **ADR-001: batch = 8 for batch-2+ experiments.** Batch-1 ran at 16; the user chose a fresh control + variant pair at 8 for the initial test. Consequences: within-batch comparability; cross-batch deltas indicative. Validated: baseline_b8 (0.2729/0.1556) vs baseline_obb b16 (0.2745/0.1555), nearly identical.
- **ADR-002: metrics of record = mAP50, mAP50-95, and matched-mean-IoU.** Per the lead (2026-09-08): precision is "garbage" for YOLO in her view; good IoU means bbox extraction is efficient and certain. mAP50-95 is already IoU-swept (0.5-0.95); the direct IoU gives a single interpretable localization number. Precision/recall demoted to diagnostics.
- **ADR-003: treat `depth_plus2_deep` as an attribution question, not a verdict.** It conflated fact/type/location/dose and returned null. Decision: keep the row, run a one-variable-at-a-time ablation (Arm A residual type, Arm B P4 location) before concluding anything about depth.
- **ADR-004 (revised after batch 3): consolidated direction = attention (C2PSA rows 6/8) + SPPF k7 + a P4-stage feature block (armB-style), optional width.** Combines the batch-1 module-level wins with the batch-3 finding that an addition at the P4 stage is the value point (armB: mAP50 0.3096 +0.037 over baseline, IoU 0.583). Depth/feature addition is kept ONLY at a resolution the small defects route through (P4); never at the deepest P5 scale.
- **ADR-005: canonical dir dataset layout, never path-list.** Ultralytics pair labels beside images reliably; path-list breaks and fails on spaces in class dir names.
- **ADR-006: frozen split + seed + env = the isolation mechanism.** No experiment may alter the split, seed, ot the training hyperparameters; the architecture edit is the only difference.
- **ADR-007: numbers are only comparable within one (model_family, data_arena, imgsz, task) cell.** Three arenas exist: (1) YOLO11 OBB on crops at 640 (multiclass, batches 1-3); (2) YOLO11/YOLO26 class-agnostic detection on crops at 1280 (`crop_detect_1280_singlecls`, single_cls=true); (3) YOLO26 10-class detection on the AABB-converted labels at 1280 (`multiclass_detect_1280_10cls`, nc=10). Never compare across arenas or across model families: the multiclass baseline is not comparable to the single-class crop rows (different label space and head). Every registry row carries model_family + data_arena (registry schema v2), and `protocols_by_arena` records the frozen config per arena. YOLO26 forks live in `experiments/yolo26/` locally; on the VM the two 2026-09-11 forks sit at `experiments/yolo26_feat_concat.yaml` and `yolo26_feat_concat_v2.yaml` (project root).
- **ADR-008: raw low-layer features into the mid stage hurt (measured by R1); the processed counterpart is still open.** The 2026-09-11 runs labelled FeatConcat V1 and V2 remain `UNATTRIBUTABLE` and are not evidence: V1 contained no head edit at all (its rows are the stock head), V2's only real edit added raw upsampled P5 rather than P3, both dropped the head keys `end2end`/`reg_max` (training 16 DFL bins with no one2one branch, params 2693491/2726259 vs the control's 2504190), both used the legacy activated SPPF row, and both trained from scratch against a pretrained control. Four uncontrolled variables (see ADR-011, ADR-012, P-9). The design preference (process features before feeding the head, keep the FPN path) stands on the FPN's role from the YOLO11 batch work, where in-pathway changes such as C2PSA attention and the P4 Conv block did win. **R1 (2026-09-11) then answered the raw half cleanly:** one added tap on raw backbone P3 into the P4 stage scored 0.6077 against its own 0.6637 control, that is -0.0560 mAP50 (-8.4%) and -0.0513 mAP50-95, with matched initialisation, a preflight-gated fork (stock keys, stock head, one intended edit) and identical first-epoch lr on both arms. Raw low-layer features into the mid stage genuinely hurt, at about a quarter of the old confounded deltas. The processed counterpart (`mc_processed_p3`) is the open half of the question.
- **ADR-009: the crop LR comparison is void as run; the underlying question is still open.** The arms labelled "auto" and "fixed 1e-4" were both trained by `optimizer=auto`, which in 8.4.142 discards `lr0` (the log states `ignoring 'lr0=0.0001'`, then `AdamW(lr=0.002)`). Measured from `results.csv`, both arms sat at lr 0.000636364 at epoch 1 and peaked at 0.00194, matching at every sampled epoch through 80; the only realised difference is the final value (2e-5 vs 3.98e-5), plus the YOLO11 auto arm early-stopping at epoch 87 while its pair ran 100. So the ~1% gap is a decay-tail and early-stopping difference, not auto-versus-fixed at 1e-4. The reference script's own numbers (verified 2026-09-11) put the auto-vs-fixed gap at +0.0097 mAP50 at 1280 (+2.1% of the fixed arm) and +0.0815 at native 2464 (+15.8% mAP50, +12.5% mAP50-95), so the LR effect grows with resolution, not with dataset identity. The ~30% figure we carried was a misread: +31.7% is the native-vs-1280 resolution gain in mAP50-95 for the auto arm, not an LR gap. Re-run required (R2) with the reference script's exact knobs (`optimizer=AdamW, lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0`); verify the `lr` column before reading metrics. **R2 ran 2026-09-11 and reverses the reading:** auto beats flat 1e-4 by +0.0329 mAP50 (+5.8% of the fixed arm) for YOLO11n and +0.0394 (+6.8%) for YOLO26n, with both runs gated on a constant `lr/pg0` of 0.0001. "LR does not matter on crops" is dead; the surviving statement is that auto is the better schedule on this pipeline, by roughly 6%.
- **ADR-010: the 80% IoU ceiling is data-limited.** Median IoU stays at ~0.80 across ALL conditions (model, LR, pipeline). Architecture changes cannot break through this ceiling. The bottleneck is 346 training images and annotation noise at 4-5px defect sizes.
- **ADR-011: a fork yaml must copy the stock head keys and full module arg lists verbatim.** `parse_model` reads `reg_max = d.get("reg_max", 16)` and `end2end = d.get("end2end")`, and rebuilds base-module args as `[c1, c2, *args[1:]]`. Dropping `end2end`/`reg_max` therefore changes the detector (16 DFL bins, no one2one branch) with no error, and a shortened SPPF row (`[1024, 5]` instead of `[1024, 5, 3, True]`) silently switches to the legacy path, which activates `cv1` and removes the residual. Consequence: any fork must pass a pre-training gate that compares param count and head children against the control.
- **ADR-012: a control/fork pair must share its initialisation.** `YOLO(yaml, task="detect")` ignores a separately supplied weights path and builds from scratch. Either train the control from the same yaml, or load pretrained weights explicitly into the fork (`YOLO(fork.yaml).load("yolo26n.pt")`). Record which one each run used in `args.yaml`-derived metadata.
- **ADR-013: verdict labels are part of the record.** A result whose run changed more than one variable, or whose arm did not do what its name says, is recorded as `verdict: "UNATTRIBUTABLE"` with the numbers kept for the audit trail. Do not delete or quietly overwrite such rows: they are the evidence that produced the corrected protocol.

## 10. Current status (see registry.json for full data)

### YOLO11 OBB (completed)
- **Batch 1 (batch 16):** baseline + 4 variants, all beat baseline on mAP50. Efficiency winner: attention_backbone (+0.059, 3.2M). Raw winner: scale_wider_only (0.3610 / 0.2113, ~7x compute). Free win: sppf_cspc (+0.018, zero params).
- **Batch 2 (batch 8):** baseline_b8 + depth_plus2_deep. Null result on plain deep convs (mAP50 +0.004, mAP50-95 -0.012, IoU -0.012).
- **Batch 3 (done):** armA_residual_deep (TYPE, null) and armB_conv_p4 (LOCATION, win). Attribution: LOCATION, not TYPE.

### YOLO26 crop detection (single-class, `crop_detect_1280_singlecls`)
- **Baselines (verified clean):** stock `yolo26n.pt`, mAP50 0.617 at batch 16 and 0.664 at batch 8; stock `yolo11n.pt`, 0.601.
- **LR arms (R2 done 2026-09-11):** the original pair both trained on the auto schedule (`lr0` ignored), so that comparison was void. Re-run with the reference knobs, auto beats flat 1e-4 by +0.0329 mAP50 (YOLO11n) and +0.0394 (YOLO26n), i.e. 5.8-6.8%. Rows `yolo11n_crop_fixedlr_flat`, `yolo26n_crop_fixedlr_flat` (`VALID`); the old pair stays marked `UNATTRIBUTABLE`.
- **FeatConcat V1:** mAP50 0.411, but the file contained no head edit (stock topology) and the head rebuilt at reg_max=16 with no one2one branch. `UNATTRIBUTABLE`.
- **FeatConcat V2:** mAP50 0.451; the only real edit added raw upsampled P5 at the P4 stage, plus the same head-config, SPPF and init confounds. `UNATTRIBUTABLE`.
- **R1 (done 2026-09-11):** the clean version of the same read. One added tap on raw backbone P3 into the P4 stage scored **0.6077 against its own 0.6637 control: -0.0560 mAP50 (-8.4%), -0.0513 mAP50-95**, with matched init and a preflight-gated fork. The control reproduced the 2026-09-10 batch-8 baseline exactly.
- **Verdict:** the old V1/V2 numbers must not be quoted. The attributable statement is that raw low-layer features into the mid stage cost about 0.056 mAP50.
- **H2 (done 2026-09-15): the processed counterpart loses too.** On the multiclass arena the processed tap scored 0.4363 against a 0.5355 control, that is -0.0992 mAP50 (-18.5%) with recall -0.1059, gated and matched. Both forms of added low-layer input are now negative. `mc_raw_p3_tap` is the arm that would rank raw against processed on identical ground.

### YOLO26 multiclass detection (10 classes, `multiclass_detect_1280_10cls`)
- **Baseline (verified clean):** mAP50=0.535, mAP50-95=0.321, params 2507700, pretrained init, stock head (`reg_max=1`, one2one present). Per-class AP50 from 0.940 to 0.132.
- **Primary target:** Bubble On 123 (0.132, 0% recall, 32 val instances).
- **Next experiments (2026-09-15):** the port program from the YOLO11 line, in order: `mc_noise_floor` (the prerequisite), `mc_attention_port`, `mc_sppf_k7`, `mc_p4_conv`, then `mc_consolidated` and the `model_scale_s` capacity reference. `mc_processed_p3` is resolved (falsified 2026-09-15) and `mc_bifpn` carries a lowered prior, because added cross-scale inputs have now failed twice. Expected outputs per arm: spec Entry 24 and `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md` H5.
- **Resolution economics (2026-09-15):** input image size is the largest measured lever in the project (+26% to +40% mAP50 for native frames against 1280, at 3.4x to 3.7x training time and about 3x inference), and cropping already banked most of it. Our own 1280-to-native step on crops measures 7.65 to 10.57 ms per image (1.38x). Full detail: spec Entry 23.
- **Hypotheses documented:** `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`; per-class AP50/P/R provenance is `vm/drivers/per_class_simple.py` (`v.summary()`), not the run script's JSON.