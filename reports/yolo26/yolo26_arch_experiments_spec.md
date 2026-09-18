# YOLO26 Detect Experiments on OoI Tags - Spec

**Created:** 2026-09-11
**Owner:** Pranay
**Repo root:** `D:/02-SSA/fmd-analysis`
**Status:** v1 - baselines established and VM-verified; the two 2026-09-10/11 architecture runs are recorded as UNATTRIBUTABLE and need re-runs R1/R2 before any conclusion is drawn.

---

## 1. Why this document exists (single source of truth for this line)

This is the single source of truth for the **YOLO26 detect experiments on Object-of-Interest (OoI) tags**. Section 10 at the bottom is the append-only, timestamped log where every finding, decision and result goes. If something is rejected or changes direction, the entry stays with its timestamp and outcome; that is the audit trail.

**Scope:** the YOLO26 detect line only, in two arenas: single-class detection on our crops at 1280, and 10-class detection on the AABB-converted labels at 1280. The YOLO11 OBB line keeps its own spec at `reports/yolo11/yolo_arch_experiments_spec.md`. Rule for both: one spec per experiment line; do not start further spec files or spreadsheets. The YOLO26 entries that had been appended to the YOLO11 spec were moved here on 2026-09-11 (keeping their original entry numbers).

**Companion docs:** `experiments/registry.json` (every experiment and result, machine-readable, with `pending_reruns`), `experiments/README.md` (governance: dos and don'ts, ADRs, pitfalls), `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md` (multiclass baseline and hypothesis list), `reports/yolo26/DOC_CORRECTIONS_20260911.md` (the 2026-09-11 correction audit trail and evidence).

---

## 2. What we are testing (the question)

Given the stock `yolo26n` architecture and the frozen 346/88 split:

1. **Multiclass (primary):** which structural changes raise 10-class detection above the stock baseline (mAP50 0.5355, mAP50-95 0.3211), with attention on the weak classes: Bubble On 123 (0.132 AP50, 0% recall), Fiber (0.449), Bubble Cluster (0.356), Bubble On Edge (0.296)?
2. **Single-class (secondary):** does anything beat the stock crop baseline (mAP50 0.6637 at batch 8, 0.6166 at batch 16), given the data-limited ~0.80 median-IoU ceiling?

We want a grounded answer, not a leaderboard. A well-characterised null is an acceptable and useful outcome, provided it is attributable to one variable.

---

## 3. Arenas and frozen configs

| Arena | Data | Task | nc | imgsz | batch | epochs | patience | seed | optimizer |
|---|---|---|---|---|---|---|---|---|---|
| `multiclass_detect_1280_10cls` | `dataset_multiclass` (AABB from OBB) | detect | 10 | 1280 | 8 | 100 | 50 | 42 | auto (resolves to AdamW lr 0.000714) |
| `crop_detect_1280_singlecls` | `crop_detect_dataset` (single-class crops) | detect, `single_cls=true` | 1 | 1280 | 8 (arch), 16 (reference runs) | 100 | 50 (arch), 30 (reference runs) | 42 | auto (resolves to AdamW lr 0.002) |

The registry rows carry `model_family` + `data_arena`; deltas are only valid inside one arena. The multiclass numbers are not comparable to the single-class crop numbers (different label space and head).

---

## 4. What we measure (per run)

- Metrics of record: **mAP50, mAP50-95**. For the crop arena also **matched-IoU** (mean/median, from the `vm/eval/iou_eval_det2.py` path; `iou_eval_det.py` is broken).
- Diagnostics: precision, recall, and per-class AP50 (plus per-class P/R via `v.summary()`, the working path on this build).
- Params as built, plus the head identity check (see section 6). GFLOPs are not currently available in this build and must not be quoted as measured.
- Provenance: every number in `registry.json` must come from `results.csv` / `metrics.json` / a summary JSON, never hand-typed. If a number has no recorded source, mark it unverified.

---

## 5. Baselines (verified on the VM 2026-09-11)

| Run | Arena | mAP50 | mAP50-95 | P | R | params | init |
|---|---|---|---|---|---|---|---|
| YOLO26n MC baseline | multiclass 10cls | 0.5355 | 0.3211 | 0.758 | 0.467 | 2507700 | pretrained `yolo26n.pt` |
| YOLO26n crop (batch 8) | single-class crops | 0.6637 | 0.4111 | 0.5993 | 0.6711 | 2504190 | pretrained `yolo26n.pt` |
| YOLO26n crop (batch 16) | single-class crops | 0.6166 | 0.3937 | 0.5959 | 0.6259 | 2504190 | pretrained `yolo26n.pt` |
| YOLO11n crop (batch 16) | single-class crops | 0.6007 | 0.3666 | 0.6218 | 0.5713 | 2590035 | pretrained `yolo11n.pt` |

The multiclass baseline is the reference for all architecture work. It is clean: single change-free control, stock YOLO26 head (`reg_max=1`, no `one2one` removal), nc=10.

Per-class AP50 for the multiclass baseline: Bubble Irregular 0.940, Wet Package 0.876, Foreign Matter 0.739, Extraneous Polymer 0.665, Bubble 0.632, Fiber 0.449, Bubble Cluster 0.356, Bubble On Edge 0.296, HEMA Fragment 0.270, Bubble On 123 0.132. Full table with P/R: `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`.

---

## 6. Pre-training gate (mandatory since 2026-09-11)

The 2026-09-11 post-mortem found that a fork yaml can silently rebuild a different detector. Before any fork spends GPU time:

1. Build it on the VM (`YOLO(fork, task="detect")`) and print `sum(p.numel() for p in model.model.parameters())`.
2. Print `model.model[-1].reg_max` and `sorted(dict(model.model[-1].named_children()))`.
3. Compare against the control: the param count must match except for the intended edit, and the head must show `reg_max=1` with `one2one_cv2`/`one2one_cv3` present.
4. Confirm the initialisation is matched between control and fork (both from the yaml, or both from the same pretrained weights). `YOLO(yaml, task="detect")` builds from scratch and ignores any separately passed weights path.

Rationale and evidence: ADR-011, ADR-012, pitfalls P-9 to P-12 in `experiments/README.md`.

---

## 7. Re-runs required

| Id | Title | Why | Gate |
|---|---|---|---|
| R1 | Attributable feature-concat re-run | V1 tested no head change; V2 tested the wrong addition; both moved four variables | Param count matches control; head shows `reg_max=1` + `one2one` |
| R2 | Real fixed-vs-auto LR arm | The "fixed 1e-4" arms never used 1e-4 (`optimizer=auto` discarded `lr0`) | Set `optimizer` explicitly; check the `lr` column in `results.csv` |
| R3 | Optional LR control | The two LR arms also differed in early stopping and the decay tail | Hold `lrf` equal across both arms |

Canonical list: `pending_reruns` in `experiments/registry.json`.

---

## 8. In scope / out of scope

**In scope:** backbone and neck structural edits (module swaps, feature fusion, tap points, channel widths), plus the training-regime questions that the protocol requires answering first (R2).

**Out of scope for now:** changes that break comparability (different splits, seeds, imgsz or label space), anything requiring a custom Python module that is not first registered and gated (BiFPN falls here), and deployment-side questions such as latency or quantisation.

---

## 9. Where results live

- `experiments/registry.json` - one row per experiment, with the arena, axis, hypothesis, results and provenance. Ideate new work here first; a row earns a yaml only after its idea is written down.
- `reports/yolo26/` - human-readable reports: crop repro, multiclass baseline and hypotheses, this spec, the corrections audit trail.
- VM `/home/pranayp/yolo_ooi/runs/` - run outputs, `results.csv` per-epoch truth, weights.

---

## 10. Incoming changes (timestamped, append-only)

**Entry 15 - 2026-09-10 (corrected 2026-09-11) - Crop LR comparison: VOID AS RUN.**

- Ran YOLO11n and YOLO26n on the crop pipeline (single-class, 1280 px, batch 16, 100 epochs) with what was intended as an auto-LR arm and a fixed-1e-4 arm.
- **Correction (2026-09-11):** both arms were trained by `optimizer=auto`, which in ultralytics 8.4.142 discards `lr0`. The trainer log states `ignoring 'lr0=0.0001'` followed by `AdamW(lr=0.002)`. Measured `lr/pg0` from `results.csv`: both arms sat at 0.000636364 at epoch 1 and peaked at 0.00194, matching at every sampled epoch through 80. The only realised difference was the final value (2e-5 vs 3.98e-5) and the YOLO11 auto arm early-stopping at epoch 87 while its pair ran 100. The reported ~1% gap is therefore a decay-tail plus early-stopping difference, not auto-versus-fixed at 1e-4.
- **Unaffected findings from this work:** the defect-scale analysis (crops resized 0.82x to 1280, defects ~10.7 px median at inference vs ~6.2 px for native frames) and the IoU ceiling (median IoU ~0.80 across all conditions, taken as a data limitation at 346 training images and 4-5 px annotation noise). Both rest on the crop runs, which changed nothing but LR arguments.
- Data: `reports/yolo26/crop_repro_summary.json`, `crop_repro_iou.json`, `crop_repro_summary_fixedlr.json`, `crop_repro_iou_fixedlr.json` (verified byte-faithful to the VM mirror). Note `crop_repro_summary_all.json` does not exist: each arm was run separately.
- **Reference script (verified 2026-09-11):** `/home/amd100-user/FMD_Data_26082026/fmd_temp_images/YOLO26_ICube_Defects/run_bbox_experiments.py` is the source our crop runner's protocol was derived from. Three arms: YOLO26n auto, YOLO26n fixed, YOLO11n auto; epochs 100, imgsz 1280, batch 16, patience 30, seed 42, single_cls=True, val on best.pt with single_cls=True. Its fixed arm is `optimizer="AdamW", lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0`, and its `results.csv` `lr/pg0` reads 0.0001 at epoch 1 and 0.0001 at epoch 100, i.e. genuinely flat with no warmup.
- **Derived, not copied:** our runner keeps that protocol but runs on OUR crop dataset, adds a fourth arm (YOLO11n fixed) that the reference does not have, and adds the matched-IoU harness that the reference bbox script does not carry (their IoU work lives in a separate sweep script). Those adaptations are intentional; the data difference is the point of the comparison, not a deviation.
- **Their measured auto-vs-fixed gaps:** +0.0097 mAP50 at 1280 (+2.1% of the fixed arm) and +0.0815 at native 2464 (+15.8% mAP50, +12.5% mAP50-95). The ~30% we had carried is their native-vs-1280 resolution gain (+31.7% in mAP50-95 for the auto arm), not an LR effect.
- **R2 outcome (2026-09-11): auto LR wins on our crops.** Auto vs flat 1e-4: YOLO11n 0.6007 vs 0.5678 mAP50 (+0.0329, +5.8%) and 0.3666 vs 0.3400 mAP50-95 (+0.0266, +7.8%); YOLO26n 0.6166 vs 0.5772 (+0.0394, +6.8%) and 0.3937 vs 0.3423 (+0.0514, +15.0%). Both R2 arms passed the gate (`optimizer: AdamW, lr0: 0.0001, lrf: 1.0, cos_lr: false, warmup_epochs: 0`, `lr/pg0` = 0.0001 at epoch 1 and at the final epoch). Caveats: one seed per arm; the reference's fixed arm disables warmup too, so schedule shape and warmup are bundled; the YOLO11n fixed arm early-stopped at epoch 79.

---

**Entry 16 - 2026-09-10 - Lead meeting: low/mid-layer feature concatenation for small defects.**

- Lead confirmed small defects are harder to find and suggested using low/mid-layer features more aggressively.
- Lead's framing: "when we work with small defect data, we take the features from the low layer and mid layer, we concat all the features and we pass it so the model can learn and pass the information."
- User committed to: translate the YOLO11 experiments to YOLO26, and investigate the feature concatenation idea.
- Open: `mc_processed_p3` (P3 through a C3k2 processing block before it enters the P4 stage, standard FPN intact) is the testable form of this idea. Registry row is `ideated`.

---

**Entry 17 - 2026-09-11 (corrected 2026-09-11) - Feature-concat forks V1 and V2: UNATTRIBUTABLE.**

- Two fork yamls were written and trained on the crop arena against the batch-8 baseline.
- **Correction (2026-09-11), verified against the VM:** V1 contained **no head edit at all**. Its head rows are the stock YOLO26 head (row 17 `[16, 1, Conv, [256, 3, 2]]` is the same reference as stock `[-1, 1, Conv, [256, 3, 2]]`, and stock already contains the P3-downsample-into-the-P4-stage path at rows 17-18 and the P5-to-P4 top-down link at row 12). The header comment in the file describes a different (replacement) design that the body does not implement. V2's only real edit is row 18 becoming a 3-way concat that adds row 11, the **raw upsampled P5** tensor, not a P3 skip; the V2 minus V1 parameter delta of 32,768 matches exactly one extra 256-channel input group.
- Both forks additionally: dropped `end2end: True` and `reg_max: 1` (so the head rebuilt as `reg_max=16` with no `one2one` branch; trained params 2693491 and 2726259 against the control's 2504190), used the legacy SPPF row `[1024, 5]` which the 8.4.142 parser activates and strips the residual from, and trained **from scratch** while the control used pretrained `yolo26n.pt`.
- **Verdict: UNATTRIBUTABLE.** Four uncontrolled variables, one of them in the opposite direction to the label. No conclusion about raw-versus-processed features can be drawn. The numbers (mAP50 0.4112 and 0.4510) are retained in the registry for the audit trail.
- Next: R1, a minimal one-variable re-run that passes the section 6 gate. **R1 has run (2026-09-11): see Entry 21.** The attributable effect of a raw P3 tap into the mid stage is -0.0560 mAP50.

---

**Entry 18 - 2026-09-11 - Multiclass baseline established (10 classes) and verified clean.**

- Built `dataset_multiclass` on the VM: OBB to AABB conversion, 10 classes, 346 train / 88 val, 1643 / 377 boxes, images symlinked from `dataset_obb`.
- YOLO26n multiclass baseline: mAP50 0.5355, mAP50-95 0.3211, P 0.758, R 0.467, params 2507700, 100 epochs, batch 8, imgsz 1280, pretrained init, stock head (`reg_max=1`, `one2one` present).
- Per-class AP50: Bubble Irregular 0.940, Wet Package 0.876, Foreign Matter 0.739, Extraneous Polymer 0.665, Bubble 0.632, Fiber 0.449, Bubble Cluster 0.356, Bubble On Edge 0.296, HEMA Fragment 0.270, Bubble On 123 0.132.
- **Bubble On 123 is the primary target:** 32 val instances, 0% recall. The model cannot find these defects at all.
- Per-class provenance note: `yolo26_mc_summary.json` carries an empty `per_class_ap50` list, so the table came from `vm/drivers/per_class_simple.py` (`v.summary()`). The run driver was patched on 2026-09-11 to collect per-class AP50 and P/R in one pass so future runs carry the table in their own JSON.
- Hypotheses documented: `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`; registry rows `mc_bifpn`, `mc_processed_p3`, `mc_tap_points`, `mc_fpn_widths`.

---

**Entry 19 - 2026-09-11 - VM verification pass: what is clean, what is not.**

- Read-only verification against the VM's own artifacts (`vm/ops/verify_yolo26_claims.py`, `vm/ops/verify_yolo26_lr_trajectory.py`) settled four open questions:
  1. The VM fork yamls are byte-identical to the repo copies (md5 match), so the trained models are the files on disk.
  2. The head-config trap is confirmed in the trained artifacts (V1/V2 `reg_max=16`, no `one2one`; baselines `reg_max=1` with `one2one`).
  3. The "fixed LR" arms ran the auto schedule (trainer log + `lr` column evidence).
  4. The multiclass baseline and both single-class crop baselines are clean (pretrained init, stock head).
- Doc corrections applied the same day: 43 tracked items across `experiments/registry.json`, `experiments/README.md`, `reports/yolo11/yolo_arch_experiments_spec.md`, `HANDOFF.md`, `reports/yolo26/PLAN_yolo26_experiments.md`, plus the addition of ADR-011/012/013 and pitfalls P-9 to P-12. Full list: `reports/yolo26/DOC_CORRECTIONS_20260911.md`.
- Remaining before the Sep 15 review: R1, the corrected LR statement to the lead (see Entry 20), and the BiFPN build.

---

**Entry 20 - 2026-09-11 - R2 executed: auto LR beats flat 1e-4 on our crops (the earlier "no difference" reading is dead).**

- Re-ran the fixed-LR arm with the reference script's exact knobs on our crop pipeline, batch 16, imgsz 1280, seed 42, single_cls, 100 epochs: `optimizer=AdamW, lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0`. Run dirs: `runs/crop_repro/yolo11n_crop_bbox_fixedlr_flat`, `runs/crop_repro/yolo26n_crop_bbox_fixedlr_flat`. Summary: `reports/yolo26/crop_repro_summary_fixedlr_flat.json`.
- **Gate passed before any metric was read:** `args.yaml` carries those five knobs, and `results.csv` `lr/pg0` reads 0.0001 at epoch 1 and at the final epoch for both arms. The invalidated 2026-09-10 arm read 0.000636364 at epoch 1.
- Head to head (auto arm from the same batch-16 protocol):

| Model | auto mAP50 / mAP50-95 | flat 1e-4 mAP50 / mAP50-95 | delta mAP50 | relative |
|---|---|---|---|---|
| YOLO11n | 0.6007 / 0.3666 | 0.5678 / 0.3400 | +0.0329 | +5.8% |
| YOLO26n | 0.6166 / 0.3937 | 0.5772 / 0.3423 | +0.0394 | +6.8% |

- mAP50-95 gaps: +0.0266 (+7.8%) for YOLO11n, +0.0514 (+15.0%) for YOLO26n. Auto is also the better schedule on both models, so the crop pipeline does not behave like "LR is irrelevant".
- Placement against the reference script's own numbers: their 1280 comparison showed +2.1% of its fixed arm (auto ahead), and their native 2464 comparison +15.8%. Our crop gap sits between the two.
- Caveats recorded with the result: one seed per arm; the reference's fixed arm also disables warmup, so this comparison bundles schedule shape (flat vs one-cycle) with warmup, which is the reference's own design; the YOLO11n flat arm early-stopped at epoch 79 while its auto counterpart ran 87. Matched-IoU for both new runs is not yet computed (the LR conclusion rests on mAP, which is the metric the reference reports).
- Registry: rows `yolo11n_crop_fixedlr_flat` and `yolo26n_crop_fixedlr_flat` (`verdict: VALID`); the invalidated rows stay in place marked `UNATTRIBUTABLE`.

---

**Entry 21 - 2026-09-11 - R1 executed: the raw low-layer tap is now a real, attributable result (-0.0560 mAP50).**

- **Design:** fork = pinned stock `yolo26.yaml` with ONE added tap: a stride-2 conv on raw backbone P3 (row 4) concatenated into the P4 output stage. Everything else stock, including `end2end: True`, `reg_max: 1`, the SPPF arg form `[1024, 5, 3, True]`, `nc: 80`. Fork file `experiments/yolo26/yolo26_feat_concat_r1.yaml` (md5 20e9c33e2afabc11e9f52cdfd4f76d5f).
- **Gate (vm/ops/preflight_fork.py, PASS):** stock top-level keys present and equal; SPPF arg form identical; built head `reg_max=1` with `one2one_cv2/one2one_cv3` present; 24 rows to 25 and +82,048 params, all accounted for by the intended edit; row diff printed and contains nothing else.
- **Matched init:** control from pretrained `yolo26n.pt`; fork built from the yaml and then `.load("yolo26n.pt")` (the script prints `14 items from pretrained weights`). Both arms logged the same first-epoch lr, 0.000651515.
- **Results** (batch 8, 100 epochs, 1280 px, seed 42, single_cls, val on best.pt):

| Arm | mAP50 | mAP50-95 | P | R | params |
|---|---|---|---|---|---|
| R1 control (stock) | 0.6637 | 0.4111 | 0.5993 | 0.6711 | 2,572,280 |
| R1 fork (raw P3 tap) | 0.6077 | 0.3598 | 0.5807 | 0.5987 | 2,654,328 |
| delta | **-0.0560** | **-0.0513** | -0.0186 | -0.0724 | +82,048 |

- **Two conclusions.** (1) Adding raw backbone-P3 features into the mid stage degrades detection, and the sign of the old V1/V2 verdict survives. (2) The magnitude does not: -0.056 against the old -0.253 / -0.213, so roughly three quarters of the old effect was the head-config, SPPF and initialisation confounds. Do not quote the old deltas again.
- **Control validation:** the control reproduced the 2026-09-10 batch-8 baseline exactly (0.6637 / 0.4111 / 0.5993 / 0.6711), so the earlier baseline and this protocol both stand.
- **Caveats:** single seed; the edit inherently adds params (the widened concat), so there is no param-matched control; matched-IoU for both arms is not yet computed. The noise floor is not yet measured, so -0.056 should be read as a real but uncalibrated effect size.
- **Rows:** `yolo26n_r1_control`, `yolo26n_r1_p3tap` (`verdict: VALID`); `pending_reruns.R1.status = done`. The processed-feature counterpart is the separate `mc_processed_p3` row, kept deliberately distinct so the raw-versus-processed questions do not mix.

---

**Entry 22 - 2026-09-15 - H2 executed: processing the low-layer tap does not rescue it (-0.0992 mAP50 on the multiclass arena).**

- **Design:** fork = pinned stock `yolo26.yaml` with raw backbone P3 (row 4) downsampled to P4 resolution, passed through a `C3k2` processing block, then concatenated into the P4 stage as a third input. Everything else stock (`end2end: True`, `reg_max: 1`, SPPF `[1024, 5, 3, True]`, `nc: 80`). Fork file `experiments/yolo26/yolo26_mc_processed_p3.yaml` (md5 01dbbb696d77a22cc3df3de0c16da8fa). Driver `vm/drivers/run_yolo26_mc_processed_p3.py` (control and fork in one session, matched init, `--smoke` build mode).
- **Gates, all passed before any metric was read:** local diff against the pinned stock yaml PASS (9 differing rows, all intended); `vm/ops/preflight_fork.py` PASS (no failures, head stock: `reg_max=1`, `one2one_cv2/one2one_cv3`); md5 of the yaml and the driver identical on the workstation and the VM; smoke build OK (control 2,572,280 params, fork 2,676,344, delta +104,064).
- **Matched init:** control = pretrained `yolo26n.pt`; fork = built from the yaml then `.load("yolo26n.pt")` (363/768 items transferred, the new tap starts from scratch). Both arms logged the same first-epoch lr (0.000232591), so the schedule is controlled.
- **Results** (multiclass arena, batch 8, 100 epochs, 1280 px, seed 42, val on best.pt):

| Arm | mAP50 | mAP50-95 | P | R | params |
|---|---|---|---|---|---|
| H2 control (stock) | 0.5355 | 0.3211 | 0.7580 | 0.4670 | 2,572,280 |
| H2 fork (processed P3 tap) | 0.4363 | 0.2320 | 0.6811 | 0.3611 | 2,676,344 |
| delta | **-0.0992** | **-0.0891** | -0.0769 | -0.1059 | +104,064 |

- **Conclusion: H2 is falsified.** A processed low-layer tap costs 0.0992 mAP50 (-18.5%) and 0.0891 mAP50-95 (-27.8%), with recall falling more than precision, so the model finds fewer defects. Processing the features did not rescue the idea, which means the failure was not raw noise alone.
- **Do not compare magnitudes across arenas.** The raw tap cost -0.0560 against a 0.6637 control on single-class crops; this cost -0.0992 against a 0.5355 ten-class baseline. The comparable fact is the sign, negative in both. Ranking raw against processed cleanly needs a same-arena raw-tap arm, which has not been run.
- **Per-class:** only Bubble (+0.0190, 227 val instances) and Foreign Matter (+0.0280, 19) gained; Bubble Cluster -0.1451 (26), Wet Package -0.1143 (35), Bubble On Edge -0.2597 (12), Fiber -0.0323 (12). Bubble On 123, the stated primary target, fell from 0.1317 to 0.0045 with 0% recall. Classes with 2-3 val images (HEMA Fragment, Extraneous Polymer) moved by more than 0.2 and are not signal.
- **Control validation:** the control reproduced the multiclass baseline exactly (0.5355 / 0.3211 / 0.758 / 0.467), the third exact reproduction of that number across two sessions.
- **Caveats:** single seed; the noise floor is still unmeasured, so treat ~0.1 as a real but uncalibrated effect size; the edit adds params, so there is no param-matched control; matched-IoU for these arms is not yet computed.
- **Rows:** `mc_processed_p3_control` and `mc_processed_p3` (`verdict: VALID`). The `mc_bifpn` row keeps its ideated status with a lowered prior, and now points at the within-pathway YOLO11 winners (attention, P4 Conv, SPPF k7) as the better-evidenced next step.

---

**Entry 23 - 2026-09-15 - What the 1280-vs-native comparison costs, beyond defect size (reference artifacts, read-only) plus one measurement of our own.**

- **Source:** the reference runs (teammate's artifacts), read only: `runs/yolo26n_icube_bbox{,_fixedlr1e-4}`, `..._native`, `runs/yolo11n_icube_bbox{, _native}`, `bbox_experiments_native_summary.json`, and their logs. Protocol: 100 epochs, batch 16, patience 30, workers 8, seed 42, single_cls. Their dataset is 368 train / 66 val images (their own log line: `Using 368 train, 66 val images ... at imgsz=2464`), so it is comparable in size to ours (346 / 88). The native arms record `imgsz: 2448` and ultralytics rounds the input up to 2464 (their log carries the warning `imgsz=[2448] must be multiple of max stride 32, updating to [2464]`).
- **Training wall clock on the same A100.** In `results.csv` the `time` column is cumulative seconds, so the total is the last row (verified monotonic):

| Arm (100 epochs, batch 16) | Input | Total train time | s/epoch |
|---|---|---|---|
| YOLO26n auto | 1280 | 373.7 s (6.2 min) | 3.74 |
| YOLO26n auto | 2464 (native) | 1396.2 s (23.3 min) | 13.96 |
| YOLO26n fixed 1e-4 | 1280 | 385.0 s (6.4 min) | 3.85 |
| YOLO26n fixed 1e-4 | 2464 (native) | 1410.2 s (23.5 min) | 14.10 |
| YOLO11n auto | 1280 | 297.4 s (5.0 min) | 2.97 |
| YOLO11n auto | 2464 (native) | 1019.7 s (17.0 min) | 10.20 |

- **Cost ratio: 3.74x, 3.66x and 3.43x for native over 1280.** That tracks the input-area ratio (2464² / 1280² = 3.70), so resolution cost here is essentially pixels, not architecture.
- **Inference per image, from their validation logs:** 1.7-2.6 ms at 1280 against 5.8-9.6 ms at native (about 3x). One first pass logged 4.5-5.3 ms at 1280, consistent with a cold-start measurement. Preprocess time also grows (0.2-4.1 ms at 1280 against 0.7-14.3 ms at native).
- **Quality, from their own cross-resolution summary:**

| Model | native mAP50 / mAP50-95 | 1280 mAP50 / mAP50-95 | delta mAP50 | delta mAP50-95 |
|---|---|---|---|---|
| YOLO26n auto | 0.5962 / 0.3782 | 0.4728 / 0.2871 | +0.1234 (+26.1%) | +0.0911 (+31.7%) |
| YOLO26n fixed 1e-4 | 0.5147 / 0.3363 | 0.4631 / 0.2552 | +0.0516 (+11.1%) | +0.0811 (+31.8%) |
| YOLO11n auto | 0.6801 / 0.4290 | 0.4866 / 0.2738 | +0.1935 (+39.8%) | +0.1552 (+56.7%) |

- **Our own inference measurement** (`vm/ops/measure_val_speed.py`, multiclass control `best.pt`, our 88-image val split, batch 8, A100): at 1280 the total is 7.65 ms per image (2.48 preprocess, 3.88 inference, 1.29 postprocess), 130.7 images/s; at 1568 (native crop width rounded to a multiple of 32) the total is 10.57 ms (3.98 / 5.33 / 1.27), 94.6 images/s. Ratio 1.38x, against a 1.50x input-area ratio. Sanity check passed: the 1280 pass reproduced mAP50 0.5355 exactly, the recorded baseline.
- **Side finding worth keeping:** the same model evaluated at a size it was not trained at scores 0.4849 mAP50 (0.5355 at its training size), so the inference size must match the training size or quality is lost for free.
- **How to read the resolution effect against everything else we have measured:** full resolution is worth +0.12 to +0.19 mAP50, which is larger than the learning-rate question (+0.01 to +0.08) and larger than any architecture change measured so far (best +0.059 on the YOLO11 line). It costs 3.4-3.7x training time and about 3x inference on full frames. On our crops the same jump is smaller (crops are ~1560 px wide against 2448), so the predicted training cost is about 1.5x our 1280 cost (566 s to roughly 850 s per 100-epoch arm).
- **Not yet done:** a native-size arm on our crop pipeline, which is the only way to state the resolution effect on our own data rather than the reference's.
- **Scripts added:** `vm/ops/ref_native_analysis.py` (read-only reference analysis) and `vm/ops/measure_val_speed.py` (our speed measurement).

---

**Entry 24 - 2026-09-15 - PLANNED, NOT RUN: the port of the within-pathway YOLO11 winners onto the YOLO26 multiclass arena (H0, H5).**

- **Context.** The outstanding lead ask is "translate the YOLO11 experiments to YOLO26". Every YOLO26 change tested so far is a top-layer or direct-input change (V1, V2, R1, H2) or a model comparison. The group that actually moved the YOLO11 line is different: changes that strengthen processing inside the existing pathway. That group has never been tested on YOLO26.
- **Why it is the right next step.** Added low-layer inputs have now failed twice on two arenas with matched initialisation and passing gates (R1 -0.0560, H2 -0.0992). The YOLO11 positives all came from inside the pathway. Evidence points one way.
- **Arms and expected outputs.** Baseline to beat: the multiclass control, 0.5355 mAP50 and 0.3211 mAP50-95, reproduced three times.

| Arm | Change (one variable) | Expected output | YOLO11 evidence |
|---|---|---|---|
| `mc_noise_floor` (H0) | none, stock config, seeds 42/43/44 | the seed spread: the delta below which nothing is real | none needed; it is a measurement |
| `mc_attention_port` (H5a) | backbone rows 6 and 8: C3k2 becomes C2PSA | +0.02 to +0.06 mAP50, recall up more than precision, gains in the weak classes | +0.059 mAP50, +0.014 mAP50-95, best accuracy per parameter, only variant that found HEMA Fragment |
| `mc_sppf_k7` (H5b) | row 9 SPPF kernel 5 becomes 7, keeping `[1024, 7, 3, True]` | 0.00 to +0.02 mAP50, zero params, zero compute | +0.018 mAP50, +0.007 mAP50-95 at zero parameter cost |
| `mc_p4_conv` (H5c) | two extra plain Conv [512,3,1] at the P4 stage | +0.01 to +0.04 mAP50 | +0.037 mAP50, and P4 depth helped where P5 depth did not |
| `mc_consolidated` (H5d) | the H5 changes that individually cleared the noise floor | roughly the sum of the parts, less if they overlap | the YOLO11 line carries the analogue as ideated `consolidated_obb` |
| `model_scale_s` (reference) | YOLO26s, stock, no edits | whether edits beat simply using a bigger model | the YOLO11 s scale gave +0.059 mAP50 at 3.65x params |
| `mc_raw_p3_tap` (H2b) | the raw P3 tap on this arena | both negatives; which is less bad | not applicable, it is the control for H2 |

- **Order:** noise floor first, because three of the four expected deltas (0.01 to 0.04) sit in the range a seed change alone can produce.
- **Gate per arm:** local yaml diff against the pinned stock yaml, then `vm/ops/preflight_fork.py` (head children and param count against the control), matched initialisation for control and fork in one session, one variable per fork. The C2PSA swap adds about 0.4M params, so no param-matched control exists for H5a; report the change as a whole.
- **Pitfalls to carry:** keep the stock head keys (`end2end: True`, `reg_max: 1`) and the complete SPPF arg form; copying a YOLO11-style row list drops both and silently rebuilds a different detector.
- **Status:** registry rows are ideated (`mc_noise_floor`, `mc_attention_port`, `mc_sppf_k7`, `mc_p4_conv`, `mc_consolidated`, `mc_raw_p3_tap`). No fork yaml is written yet.
