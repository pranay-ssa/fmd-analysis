---
title: Two-phase next round - lens plus object classes, then lens plus detector
date: 2026-11-06
type: protocol
status: active
where: docs/wayfinder/next_phase_two_arms_20261106.md
---

# Two-phase next round

> **Status note, 2026-11-09.** The phase-2 detector arena on the current split is built and verified;
> the spec is `exp2_yolo_detector_20261109.md`. The two questions in this doc are settled: the
> detector carries the seven object classes and the model is YOLO26n. The sections below remain the
> rationale for the block and the YOLO26n choice; where they say the arena is missing, read the
> 9 November spec instead.

## The directive

Two phases, both followed by a conditional pass/fail block:

1. fifteen lens-presentation tags plus eight object-of-interest tags in one multi-label CNN;
2. fifteen lens-presentation tags plus one object-of-interest tag, with the object classes handed to a detector.

The two open questions put back to the lead were whether phase 2 carries the object classes in the
detector or only a coarse tag, and which detector version to use. This doc records what already
exists, what the block is, and the evidence behind the answers.

## What already exists, per phase

| Phase | Exists | Missing |
|---|---|---|
| 1 | Nineteen-column head trained 4 November (twelve lens plus seven object classes, inverse-frequency weighting): object macro AUPRC 0.638, lens macro AUPRC 0.882. Frozen truth and saved scores on the test split. The block is wired to the model and proven end to end on the VM (picture to verdict, sixteen pictures bit-identical, twelve within 0.0005, no verdict mismatch). | No second seed. The live path scores a batch; there is no capture-side runner yet. |
| 2 | Lens plus coarse object flag already run 3 November: lens macro AUPRC 0.818, flag fires on 117 of 120 object-only test pictures at 0.55 and 0 of 317 Clear. A seven-class detector arena exists from September (YOLO26n, 0.535 mAP50 / 0.321 mAP50-95) but on 346 training and 88 validation pictures, older annotation, and with two legacy classes. | The detector on the current frozen split, seven classes. The block's detector adapter is written and self-tested but has no live detector to call. |

## The arithmetic the lead should see before reading any number

The guide defines twenty-three classes: fifteen lens tags and eight object classes. Only twelve and
seven are learnable, and the trained head says so explicitly rather than silently dropping columns:

| Guide | Named | In the data | Why |
|---|---|---|---|
| Lens tags | 15 | 12 | Edge Bottle-Capped, Torn Lens, Lens Rupture have no pictures. |
| Object classes | 8 | 7 | Surface Groove has no pictures. It stays a zero column and is excluded from every average. |

So phase 1 is twelve plus seven trained columns, not fifteen plus eight. The gap is four classes the
annotation never produced, not four classes we skipped.

## The conditional block

`experiments/multilabel_ooi/pass_fail_block.py`. One rule, two interchangeable object sources:

- **Rule (decided 4 November):** a picture passes only when it is Clear or every firing column is
  Bubble or Bubble Cluster. The twelve lens classes and six object classes fail a picture.
- **Phase 1 source:** the CNN's own object columns.
- **Phase 2 source:** the detector's class list, folded in by label, beside the CNN's lens columns.

One implementation rather than one per phase, because a second implementation would let the two
phases differ by the block instead of by the model. The rule is the comparison.

Two properties worth stating because they are what makes it deployable rather than an analysis:

- it returns the verdict with attribution (every column that fired, the driving class, whether the
  picture read as clear, bubble-only, lens or object);
- an unknown detector label raises instead of being dropped, so a renamed class cannot quietly stop
  failing pictures.

Verified against the saved combined scores, five-line rule unchanged from the decision record:

| Operating point | Failing pictures caught | Clear wrongly failed | Bubble-only passed | Passed overall |
|---|---|---|---|---|
| 0.5 | 760 of 768 | 1 of 317 | 8 of 36 | 324 of 353 |
| validation-chosen cuts | 759 of 768 | 1 of 317 | 9 of 36 | 325 of 353 |

Both rows are reproduced from `predictions.npz` by the module itself (`--mode 0.5`, `--mode chosen`),
so the block and the published workbook now share one implementation of the rule.

## The block as a pipeline stage, and the proof it is one

The stages, in order, for one picture:

1. open the picture, convert to RGB, resize to 224 by 224, scale pixels to [0, 1], normalise with the
   ImageNet mean and standard deviation;
2. resnet50 forward pass, nineteen logits, sigmoid, so nineteen scores in [0, 1];
3. compare each score to its cut (0.5, or the cut chosen on validation);
4. fail if any of the eighteen fail columns is at or above its cut; pass otherwise;
5. emit the verdict with the fired columns and the driving class.

Steps 1 and 2 are the trained head; steps 3 to 5 are `pass_fail_block.py`. The seam was checked on the
VM against the saved scores rather than asserted: sixteen test pictures scored from disk came back
bit-identical (difference 0.0) and the other twelve within 0.0005, with no verdict disagreement. The
residual on the second set is batch-boundary alignment under fp16, not a different rule or
preprocessing. So the numbers in the table above are produced by the same path that would run on a
line picture, not by a spreadsheet that re-approximates it.

## Per-class tally

Every column's contribution on the test split at 0.5 (`--per-class`). Two readings: what happens to
pictures that truly carry the class, and how many good pictures the class wrongly fails.

| Column | Role | Truth | Failed | Escaped | Fires | False fails |
|---|---|---|---|---|---|---|
| Foreign Matter | fail | 112 | 110 | 2 | 236 | 23 |
| Fiber | fail | 58 | 57 | 1 | 144 | 11 |
| Low Dose | fail | 102 | 102 | 0 | 125 | 6 |
| Dirty Camera | fail | 86 | 86 | 0 | 160 | 6 |
| Wet Package | fail | 47 | 47 | 0 | 107 | 5 |
| Lens Off Center | fail | 180 | 178 | 2 | 249 | 3 |
| Multiple Lenses | fail | 214 | 214 | 0 | 227 | 2 |
| Bubble Scatter | fail | 1 | 0 | 1 | 5 | 2 |
| Missing Primary Package | fail | 214 | 214 | 0 | 212 | 0 |
| HEMA | fail | 27 | 27 | 0 | 42 | 0 |
| Bubble | pass | 325 | 315 | 10 | 360 | 0 |
| Bubble Cluster | pass | 170 | 165 | 5 | 285 | 0 |

Read it as three claims:

- **The escapes are few**: eight truly failing pictures pass, which are per class 2 Foreign Matter,
  2 Lens Off Center, 2 Cavity Off Center, 1 Fiber, 1 Extraneous Polymer and 1 Bubble Scatter (one
  picture carries two of these, hence nine mentions for eight pictures).
- **The false fails are almost entirely two classes**: 29 good pictures fail (1 Clear, 28 bubble-only),
  and Foreign Matter appears on 23 of them and Fiber on 11. That is the specificity problem already on
  record, not a new one, and it is where the hard-negative arm is aimed.
- **A pass class still fails often, for other reasons**: 315 of 325 Bubble pictures fail, but because
  they also carry a lens condition or a failing object, not because of Bubble. A pass column can fire
  freely; it just cannot be the reason.

How many fail columns fire per picture the block fails, at 0.5: one column 379, two 134, three 131,
four 71, five 26, six 22, seven 17, eight 9. That is 379 of the 789 pictures the block fails with a
single cause, which is what makes the "driver" attribution useful in a review.

## The real-time path, measured

One picture in, one verdict out, is one call:

```python
reader = Reader(checkpoint, cuts, device="cuda")   # once, at start-up
result = reader.verdict("/path/to/picture.bmp")    # per picture, returns pass or fail
```

`predict_picture.py`, measured on the VM at single-picture batches, which is the line's case:

| Device | Decode | Forward | Rule | Total p50 | Total p95 | Worst |
|---|---|---|---|---|---|---|
| GPU (fp16) | 21.7 ms | 7.5 ms | 0.03 ms | **29.2 ms** | 29.4 ms | 29.9 ms |
| CPU | 25.0 ms | 28.9 ms | 0.03 ms | **53.9 ms** | 54.7 ms | 67.5 ms |

Against a 200 ms budget that is 3.7 times the headroom on CPU and 6.8 on GPU, with no batching and
no optimisation applied. Two consequences:

- **The decode is the cost, not the model.** On GPU it is three quarters of the budget. If throughput
  ever needs to rise, decode on a second thread and feed the model from a queue; a faster model buys
  little.
- **The process must stay resident.** Start-up, meaning import torch and load the 94 MB checkpoint,
  measured 3.56 s. Paying that per picture would miss the budget by eighteen times over, so the line
  imports this and calls it per frame, or talks to it as a service. One shot per picture is for replay
  and testing only.

The npz plays no part in this path. It is the audit record that lets a reviewer recompute every
reported number without a GPU; nothing on a line picture touches it. Likewise the build-time scripts
(train, evaluate, record) are not runtime dependencies: the deployed pair is `predict_picture.py` for
the forward pass and `pass_fail_block.py` for the rule, and the second one is plain Python so it can
be reviewed and re-derived without torch.

## One pipeline, three modules

| Module | Runs where | Job |
|---|---|---|
| `train_multilabel.py` | VM, torch | pictures to scores, and cuts chosen on validation |
| `pass_fail_block.py` | anywhere, no torch | scores plus cuts to a verdict with attribution |
| `run_arm.py` | anywhere, no torch | the stages in order, and the record they write |

One command per arm: `run_arm.py --arm-dir <arm> --mode both --write`. It writes `decision.json`
beside the arm's artifacts and merges a `decision` section into that arm's `run.json`, leaving
metrics and the rest of the record untouched, then reads the file back and prints what it found. An
arm is now finished when one record holds both halves: what the model scored, and what the rule did
with it.

Two properties are enforced rather than documented:

- the merge refuses to continue if re-reading `run.json` shows a lost key, so a malformed rewrite
  fails the stage instead of quietly erasing the training record;
- deciding an arm that has no object columns is refused outright. A lens-only head would read every
  object-only picture as clear, which on this test split would pass 120 pictures that carry an
  object. The refusal is checked against a stand-in lens-only arm.

The three stay separate files on purpose. The rule must run where torch is not installed (the line
runner, the workbook verifier, a laptop re-checking a sent workbook). Phase 2 feeds the same rule from
a detector, which must not import the trainer. And the layers change on different clocks: the rule
when a decision changes, the cuts when the data changes, the model when the recipe changes. Welded
into a training script, a threshold change means editing the trainer, and this project has already
paid once for that kind of divergence, with per-arm result files that no registry could rebuild from.

## Why phase 2 carries classes in the detector, not a bare tag

The pass rule is not "is something present". It passes a picture that carries only bubbles and fails
a picture that carries contamination. A coarse object tag cannot make that distinction: at 0.5 it
would fail all 36 bubble-only test pictures, because the flag fires on them too. The class has to be
predicted wherever the object side is predicted, so in phase 2 that means the detector predicts the
seven classes. It also keeps the location, which a tag throws away.

Two caveats to carry into the phase-2 result:

- Surface Groove is the eighth class and has no pictures, so the detector trains seven.
- Bubble Cluster is close to nested inside Bubble in this record (22 Cluster-only pictures across the
  split, 10 on the test split), so the two are reported with their confusion, not as independently
  separable.

## Why YOLO26n

YOLO26 is the current Ultralytics family and is what the September arena used. On our own crops,
same recipe, single seed, the measured order is YOLO26n ahead of YOLO11n: 0.617 against 0.601 mAP50
(+0.016, +2.6%) and 0.394 against 0.367 mAP50-95 (+0.027, +7.4%). The gap is small on 88 validation
pictures and is a single-seed observation, so the reason to pick YOLO26n is comparability with the
existing arena plus the n-series' small-object handling, not the 0.016.

The September multiclass baseline is evidence that the classes are learnable per class (Wet Package
0.876 AP50, Foreign Matter 0.739, Bubble 0.632, Fiber 0.449, HEMA 0.270 on two validation
instances), not a phase-2 number. It is trained on 346/88 pictures from the older annotation with two
legacy classes included. Phase 2 needs the current frozen split and seven classes before any figure
from it is quoted.

## Order of work

1. Build the phase-2 arena: boxes from the annotation of record, seven classes, the frozen 70/15/15
   assignment reused (never a new split), labels in the detector's format. Check that every one of
   the 7,470 split rows resolves to a picture and that the class counts match the nineteen-column
   table for the seven object classes.
2. Train YOLO26n on it, one seed, and close the arm with `run_arm.py` so the detector's record carries
   the block's verdicts beside its own detection metrics, exactly as the phase-1 arm now does.
3. Score both phases on the same held-out pictures and report the block's four numbers side by side.
   The lens side should be unchanged; the object side is the comparison.
4. Second seed for the phase-1 head, then the hard-negative arm for bubble-only specificity.

## Open questions

- Does the pass rule keep Bubble Scatter as a failing lens class? It is currently failing, and it is
  the class that most looks like a bubble defect. The rule is decided; this is the one part a lead
  could reasonably want to revisit.
- Does phase 2 need the object's size (the micron gate) reported beside the class, or is the class
  alone enough for the fail decision? The block currently ignores size.
