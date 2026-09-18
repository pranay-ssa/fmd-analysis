# Root cause: how four wrong conclusions entered the record

**Date:** 2026-09-11
**Scope:** the YOLO26 experiment line, 2026-09-09 to 2026-09-11.
**Purpose:** name the failure modes that produced conclusions contradicted by their own artifacts, so the same mistakes are not repeated. This is a process document, not a results document. Evidence is inline; the raw traces are in `reports/yolo26/DOC_CORRECTIONS_20260911.md`.

---

## 1. What was claimed, and what the artifacts say

| # | Claim as recorded | Where it was recorded | What the artifacts show |
|---|---|---|---|
| 1 | "V1 replaced the P5→P4 FPN connection; V2 added a P3 skip; both hurt, so raw features to the head hurt" | registry rows, `experiments/README.md` ADR-008, YOLO11 spec Entry 17, HANDOFF | V1 contained no head edit at all (its rows are the stock head). V2's only edit added the raw upsampled P5 tensor. Both also dropped `end2end`/`reg_max`, used the legacy SPPF row, and trained from scratch against a pretrained control |
| 2 | "Auto vs fixed LR barely matters on crops (about 1%)" | HANDOFF, YOLO11 spec Entry 15, and the Teams message to the lead | The "fixed 1e-4" arm never trained at 1e-4: the trainer logged `ignoring 'lr0=0.0001'` and ran AdamW at 0.002. The corrected re-run (R2) shows auto ahead by +0.0329 mAP50 (YOLO11n) and +0.0394 (YOLO26n), i.e. 5.8-6.8% |
| 3 | "The teammate's native-frame dataset showed auto beating fixed by about 30%" | HANDOFF, `experiments/README.md` ADR-009 | Their own summaries: +2.1% of the fixed arm at 1280, +15.8% at native 2464. The 30% figure is the native-vs-1280 resolution gain (+31.7% in mAP50-95), a different comparison |
| 4 | "Batch-1 IoU is not measured" and "armA/armB not trained" | live notes inside registry rows whose own data contradicted them | Every row carries IoU including the batch-16 rows; both arms were trained and scored |
| 5 | "Our crops are ~1556x1536 px" and (inherited) "their native defects are ~6.2 px" | HANDOFF section 0 | Crops measure 1540-1596 px across 10 distinct sizes (the figure is a mode, not a constant). The native-side 6.2 px figure is still unverified: their dataset files are not readable at the path their `data.yaml` gives |

None of these were fabrications. Each came from a mechanism that will produce the same class of error again unless it is blocked.

---

## 2. The failure modes

### M1. Declared config is not executed config
Ultralytics accepts arguments it then discards, and fills missing yaml keys with defaults, without an error:

- `optimizer=auto` discards `lr0` and `momentum` and substitutes its own values. The trainer prints `ignoring 'lr0=0.0001'` and then `AdamW(lr=0.002)`. Our arm records `lr0: 0.0001` in `args.yaml` while the run used 0.002 and a decay schedule. Evidence: `crop_repro_fixedlr.log`, and the measured `lr/pg0` of 0.000636364 at epoch 1 in `runs/crop_repro/*_fixedlr/results.csv`.
- `parse_model` reads `reg_max = d.get("reg_max", 16)` and `end2end = d.get("end2end")`. Dropping those keys from a fork silently rebuilds the head at 16 DFL bins with no end-to-end branch. Evidence: trained fork checkpoints show `head.reg_max=16` and children `[cv2, cv3, dfl]`, against the control's `reg_max=1` with `one2one_cv2/one2one_cv3`.
- A shortened SPPF argument list (`[1024, 5]` instead of `[1024, 5, 3, True]`) converts to the legacy path (`cv1.act = Conv.default_act`, `add = False`): same parameter count, different forward function. Evidence: the 8.4.142 `parse_model` compat branch, plus the fork yamls.

**Rule now in force:** the label of a run is worth nothing until the run's own artifacts are read back. The gate is `args.yaml` for the declared knobs and `results.csv` (`lr/pg0`) for the executed ones, and the built model for the head.

### M2. Template drift in forks
A fork assembled by copying a row list from another generation, or from memory, can look right and build wrong. Both 2026-09-10 forks were YOLO11-shaped: `nc: 80` kept, but `end2end`/`reg_max` gone and the SPPF row shortened. The layer-type sequence printed identical to stock, which is why nobody noticed.

**Rule now in force:** fork from the pinned stock file for that family; diff the top-level keys and the row forms, not just the layer types; run `vm/ops/preflight_fork.py` and require PASS before training. The gate prints the row-level diff so an accidental extra edit is visible, and it notes explicitly when a fork has zero differing rows (i.e. it is the stock architecture).

### M3. Decorative parameters
Both old drivers read `YOLO(yaml_path, task="detect") if yaml_path else YOLO(weights)`. The weights path sat in their own experiment tuples and never reached the model, so the forks trained from scratch while the control trained pretrained. On 346 training images that difference alone can dominate a delta.

**Rule now in force:** matched initialisation (ADR-012). Either both arms come from the same yaml, or the fork loads the checkpoint explicitly (`YOLO(fork).load("yolo26n.pt")`). The run manifest records which, and the driver prints the transfer line at startup. R1 does this.

### M4. Expected direction used instead of a control
A large drop (0.664 to 0.411) looks like a real effect and fits the intuition "raw features should hurt", so it was accepted without asking the cheapest question: does the same fork with the edit removed still reproduce the baseline? Nobody ran the control in the same session, and nobody asked whether the fork was the stock architecture.

**Rule now in force:** run the control and the variant in the same script, same session, same init (R1 pattern), and treat any delta larger than the noise floor as a signal that something other than the intended variable changed until the gates say otherwise. The preflight's row diff plus the head fingerprint is what makes that checkable in seconds.

### M5. Narrative inheritance (claim drift through retelling)
Numbers and mechanisms were carried between documents and into a stakeholder message without being re-derived. The "~30%" is the clearest case: it is a real number (+31.7% is the auto arm's mAP50-95 gain from 1280 to native), but it migrated into the LR comparison and then acquired a mechanism ("the crop pipeline eliminates the scale-dependent failure mode") that the evidence never supported. Note the tables were not wrong: `reports/yolo26/crop_repro_report.md` transcribes their six numbers correctly. The drift happened in the prose summaries around the tables.

**Rule now in force:** every stakeholder-facing claim states its source in the same sentence. Corrections are tracked per item (C1-C43 plus Parts 5-6 of the corrections file) and old rows stay in place as the audit trail, so a retelling can always be traced back to the run.

### M6. Derived docs not regenerated
The registry is declared "never hand-typed, regenerated from results", yet it carried a stale `updated` field, notes contradicting their own rows (`status: done` beside "Not trained"), an arena list that stopped at two while three were in use, and file paths that did not exist. The specs had a "Last updated" header four entries behind.

**Rule now in force:** a note is part of the row's data, not commentary. Notes must agree with status and results. Doc-consistency checks run before anything is shared, and the registry is schema-validated on every edit (the 2026-09-11 pass did this by hand; automation is still owed, see section 5).

### M7. Harness dependencies copied across environments
The R1 driver was adapted from the teammate's script and inherited `import pandas`, which this VM's python does not have. The first launch died in under a second. Same class as M2, one layer down: code copied across harnesses drags environment assumptions with it.

**Rule now in force:** drivers are stdlib-only, and every training script has a `--smoke` mode that builds the models and exits without training, so a build error costs seconds instead of a launch cycle. R1 runs `--smoke` as part of its gate.

---

## 3. What was NOT affected (do not over-correct)

- **Baselines.** Multiclass 0.5355 and the single-class crop baselines (0.6166 batch 16, 0.6637 batch 8) are stock-weight runs with the stock head, verified on the VM. They stand.
- **The IoU ceiling.** Median matched IoU around 0.80 across every condition rests on the crop repro runs, which changed nothing but LR arguments. Independently, the teammate's augmentation sweep also shows a flat matched-IoU band (0.8323 baseline, best arm 0.8407).
- **The defect-scale finding for our crops.** Verified by measurement: crops 1540-1596 px, scale 0.8205 to 1280, GT median sqrt(area) 13.03 px, 10.69 px effective, 48.3% of boxes under 12 px.
- **The YOLO11 architecture results (batches 1-3).** Those runs passed their structural validation and their numbers reproduce from `results.csv`; the batch-3 attribution (LOCATION, not TYPE) is unaffected.
- **The direction of R2.** Auto is the better schedule; what was wrong was the label, the mechanism, and the magnitude (1% claimed against 5.8-6.8% measured).

---

## 4. Standing rules (all now written into the docs)

1. No fork trains without the preflight gate: stock keys present, SPPF arg form identical, built head identity equal to the control, row diff printed.
2. No comparison without matched initialisation, stated in the run manifest.
3. No run label is believed until `args.yaml` and `results.csv` are read back (particularly the executed learning rate).
4. No delta above the noise floor is called attributable unless a control reproduced the baseline in the same session.
5. No claim leaves the repository without its source in the same sentence.
6. A corrected conclusion keeps the old row (marked `UNATTRIBUTABLE`) and gets a numbered entry, so the history of the error is preserved.
7. Fork from the pinned stock file; diff keys and arg forms, not layer-type lists.

---

## 5. What is still missing (the honest gap list)

- **A noise floor.** Every LR and architecture delta in this line is single-seed on 88 val images. Until the same config is run with different seeds, "5.8% vs 2.1%" cannot be separated from seed variance. This is the highest-value missing measurement for honest reporting, and it is cheap (two control runs).
- **Automated registry regeneration.** A script that upserts a row from a run's artifacts and flags notes that contradict status would remove the M6 class entirely.
- **The preflight gate is proven once.** Extend it to assert the initialisation contract from the driver source (does the driver actually call `.load()`?), so M3 is machine-checked rather than reviewed.
- **Matched-IoU for the new runs.** The R1 arms and the two R2 arms have mAP but no IoU yet.
- **The teammate's native-side defect scale (about 6.2 px) is unverified.** Their dataset files are not readable at the path their `data.yaml` declares, so that one inherited number stays flagged until either access changes or they supply the labels.
- **Docs-only claims in this line are now committed** (2026-09-15, three commits), so the corrected history is recoverable from git. One security item from the same pass remains open: the key passphrase must be rotated (`ssh-keygen -p`) because it had been stored in plaintext in three ops scripts and in one line of the VM's bash history.

---

## 6. Postscript (2026-09-11, after R1 finished)

This document was written while R1 was still training. R1 has since completed and it holds up the rules above:

- Fork = pinned stock `yolo26.yaml` plus one added raw-P3 tap into the P4 stage. `preflight_fork.py` PASS. Matched init via `.load()`, same first-epoch lr on both arms.
- Control 0.6637 / 0.4111, fork 0.6077 / 0.3598. Delta **-0.0560 mAP50**. The control reproduced the 2026-09-10 baseline exactly.
- So M4's remedy (a control in the same session using the same init) produced the first attributable number in this line, and the old -0.253 / -0.213 are retired.
- The rules in section 4 are now backed by a run, not only by argument. The gap list in section 5 is unchanged, and the noise floor remains the top item: -0.056 is real but not yet calibrated against seed variance.
