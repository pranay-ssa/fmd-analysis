---
title: Multilabel CNN on the frozen data
date: 2026-11-19
type: experiment
status: active
where: experiments/frozen_data_experiments/multilabel_cnn/README.md
---

# Multilabel CNN on the frozen data

The same experiment as Experiment 1, on the frozen dataset.

## Question

Can the multi-label CNN learn the frozen label space, and how well does it separate the 17 defect classes on pictures it has not seen?

## Population

| Item | Pictures |
|---|---:|
| Records in the frozen store | 13,682 |
| Duplicate records dropped | 4 |
| Pictures after the duplicate rule | 13,678 |
| Labelled pictures | 13,673 |
| Clear | 42 |

The 147 held add-backs are not in the frozen store and are not included. The four duplicate pairs keep the record with the most boxes. Pair 1 is the 7/7 tie and keeps the plain name.

## Label space

17 defect columns: 10 lens-presentation classes and 7 object classes. The six classes below 200 pictures are excluded:

| Code | Class | Kind | Pictures |
|---|---|---|---:|
| P1_EBC | Edge Bottle-Capped | LP | 24 |
| P1_LR | Lens Rupture | LP | 35 |
| P1_TL | Torn Lens | LP | 117 |
| P2_BSC | Bubble Scatter | LP | 12 |
| P2_DS | Dirty Strobe | LP | 33 |
| P1_SG | Surface Groove | OOI | 88 |

Clear has 42 pictures. The lead confirmed on 19 November that they are excluded. They are not in the split, and the model has no all-zero row.

## Split

Built at `../splits/frozen_70_15_15_20261119/`. 13,631 pictures: 9,537 train, 2,049 validation, 2,045 test. 17 columns. Split md5 `31a41925e0c349608ff77bf24d801585`, label table md5 `0d76b29097bc3a95e1b4bb14e9c172cb`, gate table md5 `c97cc04314d2e2b925cdd343e0b80058`. The verifier passes 31 of 31 checks.

`gates_4.csv` carries the four size flags as auxiliary columns. They are not model outputs. They travel with the predictions so the flagged and unflagged reads need no second pass over the store.

## Readout, to confirm with the lead

Counts first, not percentages. For each group (flagged FM&D, unflagged FM&D), the workbook reports the actual fail count, the predicted fail count, the actual pass count, the predicted pass count and the total pass count. The four rates come from those counts:

- TAR = TA / (TA + FR)
- TRR = TR / (TR + FA)
- FAR = FA / (TR + FA)
- FRR = FR / (TA + FR)

The group definitions and the TA/TR/FA/FR mapping are still to be confirmed.

## Recipe

Unchanged from Experiment 1: ResNet50, 224 px, BCEWithLogitsLoss, SGD 1e-4 momentum 0.9 Nesterov, batch 8, 50 epochs, seed 42, inverse-frequency weighting. Metric of record: per-class AUPRC.

## Runs

Complete. The run launched automatically at 19:24Z on 19 November, after a 10-minute quiet GPU window, and finished at 19:51Z: 50 epochs, 26.8 minutes, no errors. It used `--columns frozen17` on the frozen split; the VM checks (labels-only read, smoke test) passed before launch. The watcher is finished and no process is running.

The run folder is `runs/20261119_resnet50_224_seed42/`. The copied results are in `runs/20261119_resnet50_224_seed42/results/`. The workbook is `results/frozen_multilabel_results.xlsx`; it has 11 sheets, including Pass fail, Pass images, Per class with pass classes first, and Class split. Its verifier passes 7,385 checks. Weights stay on the VM.

## Results

- Test: 2,045 pictures; 4,908 positive class labels.
- Macro AUPRC 0.8423; macro AUROC 0.9624.
- Macro F1 0.8040 at 0.5; macro precision 0.7500; macro recall 0.8801.
- Macro F1 0.8187 at the validation-chosen cuts (provisional).
- Inference 3.05 ms per picture; 6.2 s for the test set.
- Pass/fail at 0.5: TA 11, FR 137, TR 1,896, FA 1; TAR 7.4%, TRR 99.9%, FAR 0.1%, FRR 92.6%. The high FRR comes from false alarms on good pictures. The model has no size output, so a predicted size class counts as a predicted fail; the size tag changes only the truth.

The per-class table, the counts and the excluded classes are in the workbook. The raw scores and truth are in `predictions.npz`.

## Open

1. Review the workbook with the user.
2. Decide whether the main table stays at 0.5 or moves to the provisional validation cuts.
3. Confirm the AUROC and AUPRC framing with the lead.
4. Review the Pass fail counts with the user. The rule is Bubble only passes, Bubble Cluster fails, any lens tag, Wet Package or size-tagged defect fails, untagged size classes pass, and Clear is outside scope. The model has no size output, so a predicted size class is a predicted fail.

## Code and artifacts

- Repository: `experiments/frozen_data_experiments/multilabel_cnn/`
- VM: `/home/pranayp/frozen_data_experiments/multilabel_cnn/`
- Weights stay on the VM. The repository keeps the run record, the split and the results.
