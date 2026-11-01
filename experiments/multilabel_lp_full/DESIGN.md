---
title: Experiment design: multi-label CNN on all LP tags plus Clear
date: 2026-10-27
type: decision
status: planned
where: experiments/multilabel_lp_full/DESIGN.md
---

# Experiment design: multi-label CNN on all LP tags plus Clear

Date ideated: 2026-10-27
Status: spec frozen, no code written, no training launched
Owner: Pranay
Registry: `experiments/multilabel_lp_full/registry.json`

## 1. Question

Does the multi-label CNN that worked on five lens-presentation (LP) tags still work when
it is extended to every LP tag that has pictures, with Clear pictures included as the
all-zero row?

This run does not decide pass or fail and does not implement the edge rules. It answers one
thing: can the network see the LP conditions, and does it stop seeing them when an object is
present instead.

## 2. What this run does and does not answer

| In scope | Out of scope |
|---|---|
| Per-class LP learnability on the current annotation | Pass/fail policy, thresholds for a verdict |
| Clear as an all-zero row, so the model has seen a pass image | Gate semantics (cannot inspect) |
| One coarse "object present" output, to test the routing conditional | Object type, object location, any detection metric |
| Whether LP scores hold on pictures that also carry an object | The YOLO head itself |

## 3. Variants

| | A: pure LP | B: LP plus object |
|---|---|---|
| Purpose | LP learnability with no object interference | Same, plus the routing conditional |
| Rows | 6,219 | 6,659 |
| Columns | 12 LP | 12 LP + 1 object present |
| Clear | 2,156 all-zero rows | 2,156 all-zero rows |
| Object-only pictures | excluded | 440 rows, all-zero on LP |
| 80/20 train / test | 4,971 / 1,248 | 5,327 / 1,332 |

A is the clean measurement. B is the same measurement plus one extra output, and its LP
columns are read on their own, never averaged with the object column.

## 4. Label space

Twelve LP tags have pictures. Three have none and are not columns: Edge Bottle-Capped,
Torn Lens, Lens Rupture.

| Column | Total | Train | Test | Judge? |
|---|---|---|---|---|
| Multiple Lens | 1,439 | 1,151 | 288 | yes |
| Missing Primary Package | 1,426 | 1,141 | 285 | yes |
| Lens Off Center | 957 | 766 | 191 | yes |
| Dirty Camera | 329 | 262 | 67 | yes |
| No Lens | 325 | 260 | 65 | yes |
| Folded Lens | 237 | 200 | 37 | yes |
| Low Dose | 215 | 172 | 43 | yes, with the negative caveat |
| Cavity Off Center | 184 | 147 | 37 | yes |
| Dirty Strobe | 43 | 34 | 9 | report only |
| View Obstructed | 24 | 19 | 5 | report only |
| Bubble Scatter | 6 | 5 | 1 | report only |
| Package Misalignment | 2 | 2 | 0 | cannot be judged, no test picture |
| Object present (B only) | 929 | 746 | 183 | fire rate only, no AUPRC |

Object present is one column covering Bubble, Bubble Cluster, Wet Package, Foreign Matter,
Fiber, Extraneous Polymer and HEMA. 1,103 pictures carry one of them; 929 are inside the
split rows, of which 614 have no LP tag and 489 carry both.

## 5. Population and exclusions

| Item | Pictures |
|---|---|
| All annotated | 6,938 |
| LP-tagged | 4,063 (3,186 one tag, 646 two, 216 three, 14 four, 1 five) |
| Clear | 2,156 |
| Object present | 1,103 |
| Legacy-only, excluded | 105 (HEMA Obstruction, Bubble On 123, Bubble On Edge) |
| Object-only without a gate tag, outside the split rows | 174 |

Labels are built from the annotation of record (`run/eda_full_20261015/resolved_labels.csv`),
not from the September export. Clear comes from the matrix's clear flag, which was verified
equal to the set of pictures with an empty annotation entry.

A legacy mention does not disqualify a picture that carries a Draft 2 code. Eight pictures carry
the HEMA Obstruction tag and also a condition (Lens Off Center 2, Multiple Lens 2, Low Dose 4),
so they are rows and contribute only that condition. The tag is not a column, nothing about it
is trained or scored, and the object flag reads 0 for them because obstruction is not one of the
seven object classes. The 78 pictures whose only mark is obstruction stay out.

## 6. Split

The current assignment (`run/split_20261028_v6/`) is used as is: content md5 groups, no picture in
both sides, no group crossing. Variant A is the LP and Clear subset of those rows, so both
variants share the same assignment for the same picture.

80/20 is the run of record, because it matches the five-tag runs. The 70/30 assignment exists
and can be run later without a rebuild.

## 7. Recipe

Frozen, identical to the 2026-10-05 multi-label run except where stated:

| Item | Value |
|---|---|
| Framework | PyTorch and torchvision, the client's stack |
| Architecture | ResNet50, ImageNet weights |
| Head | one linear score per column, sigmoid at inference |
| Loss | BCEWithLogitsLoss, pos_weight off on the first run, global pos_weight on the second |
| Input | 224 x 224, no augmentation |
| Optimizer | SGD, lr 1e-4, momentum 0.9, Nesterov |
| Batch / epochs | 8 / 50, fixed schedule, no early stopping |
| Seed | 42 |
| Precision | AMP on CUDA |
| Device | the shared A100 |

## 8. Metrics

- Per-class AUPRC is the metric of record.
- Macro AUPRC over the eight judgeable classes, unweighted.
- Precision, recall and F1 at 0.5, plus F1 at the best threshold per class, reported so a
  threshold effect is visible.
- Exact match ratio and Hamming loss over the LP columns only.
- Object column: fire rate on object-only rows, fire rate on Clear rows (the false-fire
  number that matters), and fire rate on the 489 mixed rows. No AUPRC is quoted for it.
- LP AUPRC recomputed on three subsets: LP-only, mixed, and Clear, so a shortcut shows up
  as a drop on the mixed subset.

## 9. Success criteria

Variant A, on the eight judgeable classes:

- Macro AUPRC at least 0.85.
- Folded Lens at least 0.70, against 0.62 to 0.68 in the earlier runs.
- Lens Off Center at least 0.90, Dirty Camera at least 0.85, Low Dose at least 0.70.
- No judgeable class below 0.60.

Variant B, in addition:

- Every LP class within 0.03 of its variant A value.
- Object fires on at least 90% of object-only rows.
- Object fires on at most 5% of Clear rows.
- LP AUPRC on the mixed subset within 0.05 of the LP-only subset.

If A passes and B's object column fires as above, the conditional block is worth building.
If B's mixed-subset LP score collapses, the shortcut is real and the routing design changes.

## 9a. Low Dose: the unfinished task, checked

The September export lists 1,951 Low Dose image entries and only 76 of them carry a tag. The
seven production files add 115 tagged Low Dose pictures. So 179 Low Dose folder pictures are
labelled in total, and 1,772 entries are empty placeholders from a task that was never
finished. They are unannotated, not clean.

This does not reach the experiment. Labels come from the annotation of record, and a picture
becomes a row only when it carries a label or is Clear. An empty entry in an unfinished task
is neither, so it is not a row and never becomes a negative. Low Dose therefore trains on 215
positives and confirmed negatives only, and no reliable-only variant is needed.

The same check for Package Misalignment: 293 folder pictures, 2 tagged, the rest empty. The
class stays in the label set but cannot be judged, as section 4 says.

## 10. Risks and mitigations

| Risk | Why it is real | Mitigation |
|---|---|---|
| Object column becomes a shortcut | only 489 of 4,063 LP pictures also carry an object, so "object means no LP tag" is easy to learn | report LP AUPRC on mixed versus LP-only; if it drops, retrain without the object column in the loss and keep it as an output only |
| Folded Lens never separates from Multiple Lens | 236 of 237 FL pictures carry ML | pos_weight on FL; report FL at the best threshold; accept a lower number rather than a fake one |
| Low Dose task is unfinished | 1,951 entries, 76 tagged in the September export | empty entries are excluded by construction; only labelled pictures and Clear become rows |
| Rare classes are noise | Dirty Strobe 9 test, View Obstructed 5, Bubble Scatter 1, Package Misalignment 0 | report only, keep them out of the macro average |
| No augmentation | the earlier runs used none, so the comparison stays clean | keep none for the first run; add later as a separate experiment |

## 11. Artifacts and run order

One file, `train_lp.py`, handles both variants. The labels are built inside it, so there is
no second copy of the label logic to drift.

1. `train_lp.py --variant a --labels-only` writes `run/multilabel_lp_full_20261027/labels_a.csv`
   (6,219 rows). Same for `--variant b` (6,659 rows). No torch needed; runs on any machine.
2. `train_lp.py --variant a --smoke` runs two steps on random tensors to prove shapes, loss
   and AMP. No images needed, torch required.
3. `train_lp.py --variant a --image-root <dir> --out <dir>` trains 50 epochs and writes
   `metrics.json`, `final.pt` and the per-class numbers inside the metrics file. The root is
   the folder that holds all three top folders the picture paths begin with; the script checks
   40 sampled paths against it and stops before building the model if any is missing.
4. `verify_labels.py` re-checks the label counts and proves the AUPRC function matches
   sklearn exactly (300 random cases, zero difference).
5. `reports/multilabel/lp_full_run_<date>.md` holds the reading once the runs exist.
6. `make_notebook.py` writes the reader-facing notebook `notebooks/FMD_MultiLabel_LP_AllTags.ipynb`:
   seventeen sections, design before code, no internal paths or names, and the real label counts
   embedded so it reads without being executed.

Framework: PyTorch and torchvision, which is what the client uses. The older single-label
arena was TensorFlow; this line has always been PyTorch, so there is nothing to port.

## 12. Decisions taken before coding

1. pos_weight is off on the first run, matching the October run's first execution. A second
   run adds global pos_weight, again matching the order used then. No per-class weights.
2. Low Dose needs no special handling: the 1,772 empty entries in the unfinished task are not
   rows. See section 9a.
3. 80/20 is the run of record. 70/30 is available and runs later if asked.
