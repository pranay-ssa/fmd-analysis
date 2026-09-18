# Doc corrections required after VM verification

**Status:** APPLIED 2026-09-11 (C1-C41, C43). C42 (git commit) is deliberately left open pending the user's go-ahead. See Part 5 for what was applied, what stayed open, and what the next actions are.
**Date:** 2026-09-11
**Why:** two headline conclusions in the current docs (FeatConcat V1/V2 hurt; auto vs fixed LR does not matter) are contradicted by the VM artifacts. Everything below is evidence-backed from the VM, not inference.

Checklist IDs (C1, C2, ...) are the tracking unit: tick each one off as the edit lands.

---

## Part 1. Verified facts (raw evidence)

### 1a. The two fork yamls

Identical on VM and local repo (md5 match, no drift):

| File | VM location | md5 | bytes |
|---|---|---|---|
| `yolo26_feat_concat.yaml` | `experiments/` | `72582a867507312edc4063c08dd5e6d9` | 2232 |
| `yolo26_feat_concat_v2.yaml` | **project root** | `4fb871c2de312e2233c853998b6af123` | 1631 |

`experiments/yolo26/` does not exist on the VM. `runs/yolo26_arch/yolo26n_feat_concat/args.yaml` records
`model: /home/pranayp/yolo_ooi/experiments/yolo26_feat_concat.yaml`; the V2 run records
`model: /home/pranayp/yolo_ooi/yolo26_feat_concat_v2.yaml`.

Structural diff against the packaged stock `yolo26.yaml` at ultralytics 8.4.142:

| Row | Stock | V1 | V2 |
|---|---|---|---|
| 9 SPPF | `[1024, 5, 3, True]` | `[1024, 5]` | `[1024, 5]` |
| 17 Conv | `[-1, 1, Conv, [256, 3, 2]]` | `[16, 1, Conv, [256, 3, 2]]` | `[16, 1, Conv, [256, 3, 2]]` |
| 18 Concat | `[[-1, 13], 1, Concat, [1]]` | `[[-1, 13], 1, Concat, [1]]` | `[[-1, 11, 13], 1, Concat, [1]]` |
| `end2end` | `True` | absent | absent |
| `reg_max` | `1` | absent | absent |

Two consequences, both confirmed on the VM:

1. **V1 has no head edit.** Its layer-type sequence is byte-for-byte the stock sequence
   (`Conv,Conv,C3k2,...,Concat,C3k2,Detect`, 24 layers), verified by building both on the VM.
   Row 17's `[16, ...]` is the same reference as stock's `[-1, ...]` (previous row is 16). The
   standard FPN and PAN connections are intact, including the P3-downsample into the P4 stage
   (stock rows 17-18) and the P5 to P4 top-down link (row 12). V2's only real edit is adding row 11
   (raw upsampled P5) as a third input at row 18.
2. **Both forks rebuilt the detection head.** Building the VM yamls on the VM:
   stock `params=2572280 nc=80 reg_max=1 end2end=True`, head children
   `['cv2','cv3','dfl','one2one_cv2','one2one_cv3']`; both fork yamls `params=2727536 / 2760304`,
   `reg_max=None end2end=None`, head children `['cv2','cv3','dfl']`.
   The trained checkpoints match: baseline `head.reg_max=1` with `one2one_cv2/one2one_cv3`;
   V1 and V2 `head.reg_max=16`, no one2one branch. The forks therefore ran 16 DFL bins and no
   NMS-free end-to-end branch, which is a different detector from the baseline.
   Param counts as trained: baseline 2504190, V1 2693491, V2 2726259, mc baseline 2507700.

### 1b. The SPPF row differs in behaviour, not params

In 8.4.142 `parse_model` contains:
`if m is SPPF and len(args) <= 3: block.cv1.act = Conv.default_act` (legacy path), and
`self.add = shortcut and c1 == c2`. The `[1024, 5]` rows therefore get an activated `cv1` and no
residual add, while stock `[1024, 5, 3, True]` keeps the unactivated YOLO26 SPPF with the residual.
Same parameter count, different forward function.

### 1c. Fork runs used a different initialisation than the baseline

`run_yolo26_feat_concat.py` and `run_yolo26_v2.py` both do
`m = YOLO(yaml_path, task="detect") if yaml_path else YOLO(weights)`.
The `weights` element sitting in their own `EXPERIMENTS` tuples is unused for the fork branch, so
the baseline trained from pretrained `yolo26n.pt` and both forks trained from scratch.
Confirmed in the run args: baseline `model: /home/pranayp/yolo_ooi/yolo26n.pt`, forks `model: <yaml>`.

### 1d. The "fixed LR 1e-4" runs never ran at 1e-4

`run_crop_repro.py` sets `FIXED_LR = dict(lr0=1e-4, lrf=0.0)` and never sets `optimizer`, which
stays at the default `auto`. `crop_repro_fixedlr.log` contains the trainer's own line:

```
optimizer: 'optimizer=auto' found, ignoring 'lr0=0.0001' and 'momentum=0.937' and determining best 'optimizer', 'lr0' and 'momentum' automatically...
optimizer: AdamW(lr=0.002, momentum=0.9) with parameter groups 81 weight(...), 88 weight(...), 87 bias(...)
```

Actual LR trajectories from `runs/crop_repro/*/results.csv` (lr/pg0):

| Run | epochs | lr ep1 | peak lr | lr ep20 | ep40 | ep60 | ep80 | last |
|---|---|---|---|---|---|---|---|---|
| yolo11n_crop_bbox (auto) | 87 | 0.000636364 | 0.0019406 | 0.001624 | 0.001228 | 0.000832 | 0.000436 | 0.0002972 |
| yolo11n_crop_bbox_fixedlr | 100 | 0.000636364 | 0.00194 | 0.001620 | 0.001220 | 0.000820 | 0.000420 | 0.00002 |
| yolo26n_crop_bbox (auto) | 100 | 0.000636364 | 0.0019406 | 0.001624 | 0.001228 | 0.000832 | 0.000436 | 0.0000398 |
| yolo26n_crop_bbox_fixedlr | 100 | 0.000636364 | 0.00194 | 0.001620 | 0.001220 | 0.000820 | 0.000420 | 0.00002 |

Both arms follow the same auto-AdamW schedule at the same peak. The only realised difference is the
final LR value (2e-5 vs 4e-5), i.e. the decay tail, not the peak. The YOLO11 "auto" run also
early-stopped at epoch 87 while its "fixed" pair ran the full 100.
Open detail: the tail difference is a factor of 2 while the args record `lrf: 0.01` (auto) vs
`lrf: 0.0` (fixed), which does not reconcile cleanly. It does not change the conclusion (0.0001 was
never used), but it means the two arms are not a clean `lrf` A/B either. Cheapest fix is a real
re-run with the optimizer set explicitly, not forensics on this pair.

### 1e. Summary JSON provenance

VM summary files match the local mirrors in `reports/yolo26/` exactly (`crop_repro_summary.json`,
`crop_repro_summary_fixedlr.json`, `yolo26_feat_concat_summary.json`, `yolo26_feat_concat_v2_summary.json`,
`yolo26_mc_summary.json`). `crop_repro_summary_all.json` does **not** exist on the VM (the script
writes it only in `all` mode; the two arms were run separately).
`yolo26_mc_summary.json` carries `"per_class_ap50": []`, so the per-class table in
`reports/yolo26/yolo26_mc_baseline_and_hypotheses.md` did **not** come from that file. It came from
`vm/drivers/per_class_simple.py` (`v.summary()` on the mc best.pt). The mc baseline itself is clean:
pretrained init, stock head (`reg_max=1`, one2one present), 0.5355 mAP50.

---

## Part 2. Required doc changes

### `experiments/registry.json`

- [x] **C1** line 3: `"updated": "2026-09-08"` -> `2026-09-11`. It is stale by three days of new rows.
- [x] **C2** line 6: `source_of_truth[0]` -> `reports/yolo11/yolo_arch_experiments_spec.md` (file moved).
- [x] **C3** lines 20-28 `protocol.frozen_config`: describes only the OBB 640 arena (`imgsz: 640`, batch 16/8, epochs 100). Add the second protocol block used by the detect rows now in the file (`imgsz: 1280`, `single_cls true` for the crop rows, `nc=10` for the multiclass row, patience 30 for crop repro vs 50 for the arch runs).
- [x] **C4** line 44 `comparability_note`: says two arenas. Three are now in use. Add `multiclass_detect_1280_10cls` (nc=10, AABB from OBB, batch 8) and state that the mc baseline is not comparable to the single-class crop rows.
- [x] **C5** line 1040: V1 `file` -> `experiments/yolo26/yolo26_feat_concat.yaml` (local) and note the VM path `experiments/yolo26_feat_concat.yaml` (flat).
- [x] **C6** line 1063: V2 `file` -> `experiments/yolo26/yolo26_feat_concat_v2.yaml` (local) and note the VM path is the **project root** `yolo26_feat_concat_v2.yaml`. This is the one place HANDOFF was right and the registry was wrong.
- [x] **C7** rows `yolo26n_feat_concat_v1` (lines 1037-1058) and `yolo26n_feat_concat_v2` (lines 1059-1081): `summary` and `note` are factually wrong about what was tested. V1 tested no head change at all; V2 tested adding raw upsampled P5 at the P4 stage. Both also differed from the baseline in head config (`reg_max` 1->16, end2end branch dropped), SPPF behaviour, and initialisation (scratch vs pretrained). Add `verdict: "UNATTRIBUTABLE"` and a line pointing at the re-run requirement (R1).
- [x] **C8** New rows needed for the two fixed-LR runs (results already mirrored: YOLO11n 0.5907/0.3687, YOLO26n 0.6016/0.3807) with a note that the label "fixed LR 1e-4" is wrong and the arm is pending re-run (R2).
- [x] **C9** New rows for the current hypotheses in the multiclass arena: BiFPN (H1) and processed-P3 (H2) at minimum, plus H3 tap points and H4 channel widths. README section 3.1 requires ideating in the registry before a row earns a file, and the only BiFPN row today is the parked YOLO11 one at lines 912-924.
- [x] **C10** line 129 `baseline_obb` note: remove "IoU not measured (pre-IoU protocol)"; the row carries `iou_mean_matched: 0.5969` and a full `iou_per_class` block.
- [x] **C11** line 731 `armA_residual_deep` note and line 819 `armB_conv_p4` note: both still say "Not trained. Run with: python3 -u run_batch2_b8.py ..." while `status: done` with full results. Replace with the outcome (armA null, armB win).
- [x] **C12** line 1114 `yolo26n_mc_baseline.results_source`: name the actual per-class source (`vm/drivers/per_class_simple.py` output / `reports/yolo26/yolo26_mc_baseline_and_hypotheses.md`), since `yolo26_mc_summary.json` holds an empty `per_class_ap50`.

### `experiments/README.md`

- [x] **C13** line 5: companion doc path -> `reports/yolo11/yolo_arch_experiments_spec.md`.
- [x] **C14** line 80 (technical debt): "IoU exists only for batch-8 runs" is false; every registry row carries IoU, including the batch-16 batch-1 rows.
- [x] **C15** line 102 (ADR-007): "Two distinct arenas exist" -> three, adding `multiclass_detect_1280_10cls`.
- [x] **C16** line 103 (ADR-008): rewrite. Keep the principle stated by the lead's feature idea and by the V1/V2 *intent*, but record that the V1/V2 runs cannot support the claim (C7 evidence), so "raw features to the head hurt" is currently unproven.
- [x] **C17** line 104 (ADR-009): rewrite. The arm labelled "fixed LR 1e-4" trained on the auto-AdamW schedule at peak 0.00194 (evidence 1d). Keep the observation that the two arms scored within ~1%, and record the reason it does not mean what it says: the arms differed only in the decay tail.
- [x] **C18** lines 114-118 (YOLO26 crop detection status): V1 line "mAP50 0.411 (-0.253), hurt badly, removing P5 context from P4 head" and V2 line "0.451 (-0.213), raw P3 features add noise" must be corrected to the actual architectures (1a) and marked unattributable.
- [x] **C19** line 26: same correction for the single-class summary line; "Feature concat experiments (V1, V2) both hurt. Standard FPN is already optimal" is not supported yet.
- [x] **C20** lines 33, 60, 64: the "don't add raw backbone features (V1 and V2 proved this hurts)" instruction should be downgraded to "unproven: the V1/V2 runs changed four variables at once (see ADR-008)"; the instruction itself (process features before adding) can stay as a design preference.
- [x] **C21** lines 120-123 (multiclass status): add that the mc baseline is clean and is the reference, and list the pending hypotheses with registry rows (C9).

### `reports/yolo11/yolo_arch_experiments_spec.md`

- [x] **C22** line 4 header: `Last updated` says 2026-09-08T16:08:42 (Entry 13) while entries 15-18 exist. Update to the last entry.
- [x] **C23** Entry 15 (lines 487-493): rewrite the LR finding per 1d.
- [x] **C24** Entry 17 (lines 505-510): rewrite per 1a/1c. The claim "Replaced P5->P4 FPN connection with P3->P4 skip" and "Removing P5 semantic context from P4 head destroyed the model's ability" are not what the yaml does.
- [x] **C25** Decide where the YOLO26 entries live. Section 1 of this spec says the file is the YOLO11 OBB single source of truth and that runs must not be mixed, yet entries 15-18 (15, 17, 18 are YOLO26 detect) are now appended here. Option A: create the planned `reports/yolo26/yolo26_arch_experiments_spec.md` and move entries 15, 17, 18 into it, leaving a pointer. Option B: amend Section 1 to declare this file cross-family and keep them. Pick one and record it.

### `HANDOFF.md`

- [x] **C26** line 5 status line and lines 86-90: "Feature concat experiments complete (both hurt)" -> pending re-run (R1).
- [x] **C27** lines 13-25 (section 0.1 table): the LR table must carry the corrected label. Keep the numbers (they are faithful) but rename the arm and add one line stating the arm did not train at 1e-4.
- [x] **C28** lines 35-38 (section 0.5 V1/V2) and lines 66-70 (key learnings, two bullets): rewrite per 1a/1c.
- [x] **C29** lines 74-78 (what to do next): item 4 ("Run YOLO11 experiments on YOLO26") is still unbuilt; items 1-2 are still the right next steps. Add the two re-runs (R1, R2) above them so the order is honest.
- [x] **C30** lines 114-115 (VM yaml paths): correct as C5/C6 (V2 is in the project root on the VM; both forks are under `experiments/yolo26/` locally).
- [x] **C31** line 125: the ssh line (`ssh -i ... fmd-vm`) contradicts the PTY plus passphrase note two lines below; either delete it or add the PTY requirement. The alias `fmd-vm` does exist in `~/.ssh/config` and works, so the fix is only about the interactive passphrase.
- [x] **C32** lines 157-162 (experiment summary table): add a footnote that the two FeatConcat rows are unattributable and add the fixed-LR rows with the corrected label.
- [x] **C33** lines 197-203 (section 8) and 217-218 (references): both spec/report paths moved to `reports/yolo11/`; section 8 cites "section 10 entries 8-14" while the log now runs to entry 18.
- [x] **C34** line 221: "`yolo26_v2.log` - V1+V2 training log" is wrong. V1 is `yolo26_feat_concat.log`, V2 is `yolo26_v2.log`; both exist on the VM.
- [x] **C35** line 176 (biases table): "BiFPN bidirectional flow, NEXT TO BUILD" is right as intent, but the registry row it needs (C9) is missing.

### `reports/yolo26/PLAN_yolo26_experiments.md`

- [x] **C36** Phase 1 (lines 43-48): the three artifacts it lists do not exist and were replaced by the shared `experiments/README.md` plus `experiments/registry.json`. Record the decision and tick the box.
- [x] **C37** Phase 2 (lines 50-66): the three YOLO11-winner forks (`yolo26_attention.yaml`, `yolo26_sppf_k7.yaml`, `yolo26_armB_p4.yaml`) are still unbuilt. Note that SPPF k7 and the P4 block interact with the `reg_max`/`end2end` bug (C7): any new fork must copy the stock `end2end` and `reg_max` keys or it will silently build a different head.
- [x] **C38** lines 88-96 frozen config: it says `nc=1` crop task, while the live work is the nc=10 multiclass arena. Add the mc config block.
- [x] **C39** Phase 3 (lines 68-79): mark done with the correct outcome (two runs, both confounded), and Phase 4 dates need re-baselining against the Sep 15 deadline.

### Repo hygiene

- [x] **C40** `.continue-here.md` is a 2026-09-03 artifact for the finished crop workstream (`task: algo-finalized`). Archive or delete; it contradicts the current handoff.
- [x] **C41** root `README.md` line 102 points at `reports/fixed_size_crop_spec.md`; the file is at `reports/preprocessing/fixed_size_crop_spec.md`.
- [ ] **C42** `experiments/` and `reports/` are still untracked in git (`??`). Commit the governance files so the corrections are recoverable.
- [x] **C43** `vm/drivers/run_yolo26_multiclass.py` writes `per_class_ap50` but the VM json came out empty, and the report numbers came from a second script. Fold `per_class_simple.py`'s `v.summary()` path into the run script so one artifact carries the table.

---

## Part 3. Required re-runs

- **R1 FeatConcat, attributable version.** One variable. Copy stock `yolo26.yaml` verbatim, change only the intended edit, and keep `end2end: True`, `reg_max: 1`, `SPPF [1024, 5, 3, True]`, `nc: 80`. Initialise both arms the same way: either train the control from the yaml too, or load `yolo26n.pt` into the fork with `YOLO(fork.yaml).load("yolo26n.pt")`. Validate on the VM before spending GPU: `sum(p.numel())` must match the control, and the built head must show `reg_max=1` plus `one2one_cv2/one2one_cv3`.
- **R2 LR, attributable version.** Set the optimizer explicitly in the script (`optimizer="AdamW"` or `"SGD"`), keep `lr0` and `lrf` as the only differences (`lrf: 1.0` for a genuinely flat LR), and confirm from `results.csv` that the `lr` column sits at the intended value before reading any metric. Until then, do not restate the crop LR finding to the lead in its current form.
- **R3 Optional.** Re-run the same two arms with `lrf` held equal (0.01 both) to isolate whether the observed ~1% gap was init, early stopping, or the decay tail.

---

## Part 4. Not in scope of this correction

- The multiclass baseline numbers (0.5355 / 0.3211, per-class table) stand. Pretrained init, stock head, single change-free control.
- The single-class crop baselines (batch 16: 0.6166; batch 8: 0.6637) stand; both are stock `yolo26n.pt` runs.
- The IoU ceiling and defect-scale findings are unaffected (they come from the crop repro runs, which changed nothing but the LR args, so 1d applies only to the LR interpretation).
- The claim "auto LR barely matters" is likely still true in practice; what is broken is the label and the mechanism, not necessarily the outcome.

---

## Part 5. Close-out (2026-09-11)

### Applied

| Where | Items |
|---|---|
| `experiments/registry.json` | C1-C12. `updated` bumped; `source_of_truth` re-pointed; per-arena protocol blocks added (`protocols_by_arena`); `comparability_note` covers three arenas; V1/V2 rows corrected and marked `UNATTRIBUTABLE`; the two fixed-LR rows added; four hypothesis rows added (`mc_bifpn`, `mc_processed_p3`, `mc_tap_points`, `mc_fpn_widths`); stale notes on `baseline_obb`, `armA_residual_deep`, `armB_conv_p4` fixed; multiclass provenance recorded; `pending_reruns` R1-R3 added. Now 30 rows, valid JSON. |
| `experiments/README.md` | C13-C21. Companion-doc paths; section 2a rewritten; don'ts corrected; tech-debt IoU line fixed; ADR-007 rewritten for three arenas; ADR-008 and ADR-009 rewritten as open/void; ADR-011, ADR-012, ADR-013 added; new pitfalls P-9 to P-12; section 10 status rewritten for both YOLO26 arenas. |
| `reports/yolo11/yolo_arch_experiments_spec.md` | C22-C25. Header date updated; Section 1 scope note added; entries 15-18 replaced by Entry 19, which records the move and both corrections. |
| `reports/yolo26/yolo26_arch_experiments_spec.md` | New file (C25, option A). The YOLO26 detect log: arenas, frozen configs, verified baselines, the mandatory pre-training gate, re-run list, and entries 15-19 with the corrections in place. |
| `HANDOFF.md` | C26-C35. Section 0 rebuilt around the verification result, section 1, 5, 6, 7, 8 corrected, VM yaml layout recorded (V2 is in the project root on the VM), lab log names fixed, references re-pointed. |
| `reports/yolo26/PLAN_yolo26_experiments.md` | C36-C39. Phase 1 closed with the fold-into-shared-files decision; Phase 2 status plus the head-config warning; Phase 3 recorded as run-but-unattributable; frozen config split into the crop arena and the multiclass arena. |
| `README.md` (root) | C41. Spec path corrected to `reports/preprocessing/`. |
| `vm/drivers/run_yolo26_multiclass.py` | C43. Per-class AP50 and P/R now collected via `v.summary()` (with the `v.ap50` fallback) so a run's own JSON carries the table. |
| `.continue-here.md` | C40. Moved to `docs/archive/continue-here_20260903_fixed_size_crop.md`. |
| `reports/yolo11/yolo_batch1_architecture_analysis.md` | C45 (found during the post-edit sweep). Two live pointers to `reports/yolo_arch_experiments_spec.md` corrected to `reports/yolo11/`. |

Post-edit verification: `registry.json` parses and reports 30 rows with `pending_reruns` R1-R3; the three edited or added Python files compile; a repo-wide grep for the old paths, the old `.continue-here.md`, and `reports/fixed_size_crop_spec.md` returns no live hits (only historical entries inside the append-only spec log, which are intentionally left as written).

### Left open

- [x] **C42 - commit the governance files.** Done 2026-09-15: three commits (`215844c` reorganization + `runs/` ignored, `b67eec6` docs/governance/registry/specs, `17f78bf` VM scripts and the preflight gate). Working tree clean. While staging, a stored SSH passphrase was found in three ops scripts and scrubbed before they were committed (never in git history), and one line of the VM's bash history was cleaned.
- [ ] **C44 - `yolo11n_crop_repro.params` (2590035) has no recorded source.** The crop-repro summary JSONs carry no `params` field. The YOLO26 equivalent (2504190) was confirmed from the VM checkpoint; the YOLO11 one was not. Either confirm it on the VM or mark it unverified.
- [ ] **C46 - `experiments/validate_backbone_edit.py` predates the head-config trap.** It still only checks routing and channels, not head identity. Extend it (or `vm/drivers/validate_yaml.py`) to assert `reg_max` / `end2end` / head children match the control, so the P-9 gate is automated rather than manual.

### Next actions (in order)

1. **R2 - real fixed-vs-auto LR arm** (cheapest, and the claim already went to the lead).
2. **Correction message to the lead** for the 2026-09-10 Teams message (self-contained, one claim per sentence with its evidence inline).
3. **R1 - attributable feature-concat re-run** (copy stock `yolo26.yaml`, one edit, matched init, pass the section 6 gate).
4. **Build `mc_bifpn`** (custom module + yaml; highest-priority architecture experiment for the multiclass arena).
5. **Build `mc_processed_p3`** (the testable form of the lead's feature idea).
6. **Commit the governance files** (C42) once the docs are accepted.
7. **Check the shared A100 is free** before any training launch.

---

## Part 6. R2 executed (2026-09-11)

**R2 is done and it overturns the LR conclusion rather than just relabelling it.**

- Arm run with the reference script's exact knobs (`optimizer=AdamW, lr0=1e-4, lrf=1.0, cos_lr=False, warmup_epochs=0`), on our crop pipeline, batch 16, imgsz 1280, seed 42, single_cls.
- Gate checked before reading any metric: `results.csv` `lr/pg0` = 0.0001 at epoch 1 and at the final epoch, both arms (the invalid arm read 0.000636364).
- Result: auto beats flat 1e-4 by **+0.0329 mAP50 (+5.8%)** for YOLO11n (0.6007 vs 0.5678) and **+0.0394 (+6.8%)** for YOLO26n (0.6166 vs 0.5772). On mAP50-95: +0.0266 (+7.8%) and +0.0514 (+15.0%).
- So the item that was going to be a relabel ("the arm did not do what its name says") turned into a reversed finding ("the schedule matters, and auto is better"). Both statements now sit in the docs.
- Caveats: one seed per arm; warmup is bundled with schedule shape in the reference's own fixed arm; YOLO11n flat arm early-stopped at 79 epochs; matched-IoU for the two new runs pending.

**Where the R2 results now live:** `reports/yolo26/crop_repro_summary_fixedlr_flat.json` (mirrored from the VM), registry rows `yolo11n_crop_fixedlr_flat` / `yolo26n_crop_fixedlr_flat` (`verdict: VALID`), `pending_reruns.R2.status = done` with the full delta table, HANDOFF section 0, the YOLO26 spec Entry 20, and ADR-009 in `experiments/README.md`.

**Still open on the LR thread:** matched-IoU for the two new runs (the LR conclusion rests on mAP, which is what the reference reports); R3 (holding `lrf` equal) is now optional, since R2 answered the question the LR pair was meant to answer.

---

## Part 7. R1 executed (2026-09-11)

**The raw-feature question now has a clean, attributable answer: -0.0560 mAP50.**

- Fork: pinned stock `yolo26.yaml` plus ONE added tap, a stride-2 conv on raw backbone P3 (row 4) concatenated into the P4 output stage. `experiments/yolo26/yolo26_feat_concat_r1.yaml`, md5 `20e9c33e2afabc11e9f52cdfd4f76d5f`.
- Gate: `vm/ops/preflight_fork.py` PASS, and for the first time this gate is a real artifact rather than a review step. It asserts stock top-level keys, the SPPF arg form, the built head's `reg_max` and the presence of the one2one branch, prints the row-level diff, and exits non-zero on any failure so a launcher can block on it. It also prints the initialisation contract (a yaml-built model starts from scratch), which is what makes M3 checkable.
- Init: both arms pretrained. The fork loads the checkpoint explicitly (`14 items from pretrained weights`). Both arms recorded the same first-epoch lr, 0.000651515.
- Results: control 0.6637 / 0.4111 / P 0.5993 / R 0.6711; fork 0.6077 / 0.3598 / P 0.5807 / R 0.5987. Delta: **-0.0560 mAP50 (-8.4%), -0.0513 mAP50-95 (-12.5%), recall -0.0724**.
- Control validation: the control reproduced the 2026-09-10 batch-8 baseline exactly, so the earlier baseline and this protocol both stand. This is the cheapest confidence check in the toolkit and it should be standard practice.
- Two conclusions: the sign of the old V1/V2 verdict survives (raw features into the mid stage hurt), the magnitude does not (roughly three quarters of the old -0.253/-0.213 was confound). The old deltas must not be quoted again.
- Caveats: single seed; the edit inherently adds params (widened concat), so no param-matched control; matched-IoU not computed; the noise floor is unmeasured, so -0.056 is a real but uncalibrated effect size.

**Where the R1 results live:** `reports/yolo26/r1_feat_concat_summary.json` (mirrored from the VM), registry rows `yolo26n_r1_control` / `yolo26n_r1_p3tap` (`verdict: VALID`), `pending_reruns.R1.status = done`, HANDOFF sections 0.2/0.3/0.4/1/5, the YOLO26 spec Entry 21, and ADR-008.

**Next on this thread:** the noise floor (two runs with different seeds) before any further effect size is reported, then `mc_processed_p3` as the "process before adding" half of the same question.
