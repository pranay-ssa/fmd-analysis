---
title: Experiment 3.1 - size-gate separability pilot on the four gated classes
date: 2026-11-16
type: protocol
status: done
where: docs/wayfinder/exp3_1_size_gate_20261116.md
---

# Experiment 3.1

## Destination

A go / no-go decision on whether a CNN can separate size-flagged from unflagged defects in the
four gated classes well enough to justify the full pass/fail experiment (Experiment 3.2), plus the
split, label table, dataset and scoring harness that 3.2 reuses unchanged.

This is planning only. No ticket is created, no split is built and no run is launched until the
open decisions below are answered.

## What this answers, and what it cannot

It answers: does a picture-level classifier score a defect that is below the micron cut lower than
one above it, by enough to put them on opposite sides of a threshold?

It cannot answer: whether a per-object size head is possible. The gate is one tag per picture, set
by the largest box of that class, so a picture holding one large and several small particles is
flagged once and the tag does not name the box that crossed. The experiment is picture-level by
construction.

It also cannot answer: whether size is learnable at all, if the only arm runs at 224 px. See
decision D1.

## Population facts that shape the design

Measured today from `run/eda_full_20261029/resolved_labels.csv` and the frozen v8 split, with
Bubble Cluster counted as fail per the user's 16 November instruction.

| Class | Pictures with class box | Size-flagged | Unflagged | Unflagged where the size call alone decides | of those outside the split |
|---|---|---|---|---|---|
| Foreign Matter | 834 | 454 | 380 | 51 | 36 |
| Fiber | 405 | 362 | 43 | 14 | 13 |
| Extraneous Polymer | 175 | 135 | 40 | 34 | 33 |
| HEMA | 157 | 151 | 6 | 3 | 3 |

"Size call alone decides" means the picture carries no lens tag, no Wet Package, no Bubble Cluster
and no other gated class. The rest of the unflagged pictures (Foreign Matter 329, Fiber 29,
Extraneous Polymer 6) fail on another label whatever the size call was, so a pass/fail table
cannot score them. Lens tags count as another fail label: a picture with an unflagged Foreign
Matter object and Multiple Lens fails on Multiple Lens regardless of the size call.

Three consequences:

1. **The frozen test split cannot carry this experiment.** It holds 2 decisive Foreign Matter
   pictures and 0 Fiber or Extraneous Polymer. The unflagged population has to be moved into test.
2. **82 decisive pictures are outside the frozen split.** They were dropped by the frozen rule
   "no positive at all". They must come back as test rows.
3. **HEMA has no size contrast.** All 151 production HEMA box pictures carry the gate; the 6
   unflagged ones are September fragments with no gate assessment, where no flag means unassessed,
   not below the cut. HEMA stays a column and is reported as not measurable.

## The split

New artifact, `run/split_exp3_1_20261116/`. Split v8 is not modified.

**Move rule.** A picture leaves train or validation for test when it carries a box of any of the
four classes without that class's gate tag. A picture gated in every gated class it carries keeps
its v8 assignment. Pictures outside v8 that are unflagged for any of the four classes enter as
test rows.

The rule is a union over the four classes, not per class, because one model is scored on one
split. A picture with an unflagged Foreign Matter object and a gated Fiber object is a Foreign
Matter test picture and must not be in training at all, so it moves. It is still a legitimate gated
Fiber test picture, which is why the gated test counts below exceed the v8 test counts.

| | v8 | Exp 3.1 |
|---|---|---|
| rows | 7,470 | 7,555 |
| train | 5,239 | 4,964 |
| validation | 1,110 | 1,058 |
| test | 1,121 | 1,533 |

412 pictures enter test: 327 leave train or validation, 85 come in from outside the split. 41
unflagged pictures were already in the v8 test set and stay.

Per class, by split and gate status:

| Class | train gated | val gated | test gated | test unflagged |
|---|---|---|---|---|
| Foreign Matter | 315 | 60 | 79 | 380 |
| Fiber | 195 | 43 | 124 | 43 |
| Extraneous Polymer | 81 | 14 | 40 | 40 |
| HEMA | 79 | 20 | 52 | 6 |

No unflagged picture of any of the four classes remains in train or validation. That is the
premise of the experiment and the split verifier must assert it.

**Cost of the union rule.** 56 gated Fiber training pictures and 20 gated HEMA training pictures
leave training because they also carry an unflagged class. Fiber gated positives fall from 251 to
195 (-22%), HEMA from 99 to 79 (-20%). This is a real loss of positive support and is reported in
the result, not hidden.

## Label space

Four columns, one per gated class, positive on the gate tag:

- `fm_gated`, `fiber_gated`, `ep_gated`, `hema_gated`

Unflagged pictures are negative on their class column by truth, never masked. That is what makes
the test a false-fire measurement. Bubble, Bubble Cluster and the lens tags are not columns in this
pilot; they exist only in the pass/fail layer.

Rejected: one column per class holding both gated and unflagged pictures. It cannot express the
question, because the model would learn one class and the gate would be invisible in the target.

## Stage 0: score the existing checkpoint first

Before any training, score the Experiment 1 combined checkpoint (`final.pt` in
`run/multilabel_ooi_20261104/combined/`) on the new 1,533-picture test population, reading only
its four object columns. Inference only, no training, minutes on the A100.

This gives the "how is the model seeing the defects" baseline the user asked for, and it needs no
GPU time beyond a forward pass. Caveat to state wherever it appears: 327 of the 1,533 test pictures
were in that checkpoint's training set, so its scores on them are contaminated. The 85 out-of-split
and 41 already-in-test pictures are clean. Stage 0 is a baseline for shape and magnitude, not a
fair comparison; Stage 1 is the fair number.

Baseline on the old 72 / 40 population, computed today from `predictions.npz`:

| Arm | Foreign Matter AUROC | Fiber AUROC |
|---|---|---|
| gate-trained | 0.547 | 0.223 |
| class-trained, weighted | 0.673 | 0.304 |
| combined 19-column | 0.700 | 0.527 |

The gate-trained arm sits at chance on Foreign Matter. That is the result this pilot has to beat.

## Stage 1: the runs

Two arms, one variable apart. Everything except the input size is identical, so a difference is
attributable to resolution and nothing else.

- Model: ResNet50, batch 8, 50 epochs, SGD 1e-4 momentum 0.9 nesterov, weight decay 1e-4,
  seed 42, BCEWithLogitsLoss, no early stopping. Same recipe as Experiment 1.
- Arm A `gate4_224`: 224 px, exactly the Experiment 1 recipe. This is the comparable arm.
- Arm B `gate4_448`: 448 px, the same recipe. At 448 the gate boundary is about 4.3 px instead of
  2.1, which is the smallest change that gives size a chance to be representable. Expect roughly
  four times the epoch time of arm A; about 25 minutes each on a quiet A100.
- If arm A and arm B disagree, arm B is the informative one about size and arm A is the statement
  about the Experiment 1 recipe. Report both, never merge them.
- Weighting: inverse frequency on the training split only, per column. Expected weights
  (N - n) / n with N = 4,964: Foreign Matter 14.8, Fiber 24.5, Extraneous Polymer 60.3,
  HEMA 61.8.
- Thresholds: per column, validation only, grid 0.05 to 0.95, highest F1, ties to the higher cut,
  extended to 0.99 if the maximum lands at 0.95.
- One seed. A second seed is a follow-up, not part of the pilot.
- Trainer change: a new `--columns gate4` mode reading a new label table. The existing `ooi`,
  `combined` and `gate` modes are untouched, so Experiment 1 and 2 records stay reproducible.

## Scoring

Primary, per class, on the new test population:

| Measure | Population | Why |
|---|---|---|
| AUROC, gated against unflagged | all test pictures carrying the class | threshold-free; the cleanest single number for "does it see size" |
| False-fire rate at the chosen cut | all unflagged test pictures of the class | the production consequence |
| False-fire rate at the chosen cut | decisive unflagged test pictures only | the verdict consequence |
| Recall at the chosen cut | gated test pictures | the trade-off; a model that never fires would otherwise look perfect |

Secondary, per class: score against the largest box's longer side, native pixels and microns, with
the gate boundary marked. This is the figure that shows how the model sees the defect. It also
exposes the mixed-size problem in the flagged group: a flagged picture may hold one large and
several small particles.

Pass/fail layer, as asked for: on the 99 decisive pictures (Foreign Matter 51, Fiber 14,
Extraneous Polymer 34; HEMA 3 not counted), where no other fail label exists, the object-side
verdict is exact. On the full 1,533, a verdict is object-side only and is labelled that way,
because the pilot has no lens columns. The full 19-column rule is Experiment 3.2, not this pilot.

Two table sets go in the workbook, kept apart:

1. **The usual pass/fail read:** pictures caught, Clear pictures passed, Bubble-only pictures
   passed, overall, with the column that drove each fail.
2. **The size read, one row per gated class:** size-flagged counted as fail, unflagged counted as
   pass, Bubble and Clear as pass, every other class as fail. Each row carries the gated support,
   unflagged support, recall, false-fire rate, decisive-subset false-fire rate and AUROC.

A per-picture sheet carries truth, verdict, every column that fired, the decisive flag, the gate
status and the largest box size, so a reviewer can check the model is doing what the rule expects
rather than only reading aggregates.

## No pre-registered bars

The user's 16 November decision is that the pilot is a placeholder experiment: the tables are
judged after they are shared with the lead, and no pass mark is fixed in advance. Do not invent
one, and do not describe any result as a pass or a fail of the pilot.

What the tables must therefore carry, so the judgement is informed:

- The Stage 0 baseline and both Stage 1 arms side by side on the same population, never pooled.
- The per-class AUROC with its support on both sides, since AUROC on 79 against 380 is not the
  same statement as on 17 against 40.
- The false-fire rate on all unflagged pictures and on the decisive subset, kept apart.
- The score-against-box-size curve with the gate boundary marked.
- HEMA reported as not measurable, with the reason in the same row.
- A one-line note wherever a number is not comparable to Experiment 1, because the test population
  changed.

## Verification gates

1. **Split:** builder writes `split.csv` and `meta.json`; the verifier recomputes every count from
   the annotation, asserts no unflagged gated-class picture in train or validation, and proves it
   catches one moved row. Counts must equal the tables above.
2. **Dataset:** every row has an image on the VM root, the builder reads each image's size rather
   than assuming, and the verifier exits 0. md5 of the split, the label table and the trainer
   recorded on both ends.
3. **Labels only:** the trainer's `--labels-only` on the VM matches the local per-split counts.
4. **Stage 0:** every quoted number reproduced locally from the saved scores, never from a log.
5. **Run:** `run.json` with `status: ok` and `metrics.primary`, one record per run.
6. **Report:** the workbook verifier recomputes each cell from the annotation and the scores;
   tampering with one cell is caught.

## Risks

- **224 px may make size invisible.** A 2448 x 2048 frame resized to 224 is downsampled 10.9x, so
  the gate boundary of 19.4 to 19.6 native pixels becomes about 2.1 px, and the unflagged range
  becomes sub-pixel to 2 px. A null result at 224 says the recipe cannot see size, not that size is
  unlearnable. Decision D1.
- **One tag per picture, set by the largest box.** The flagged group is mixed-size, which can only
  push recall down. State it beside every recall number.
- **The 300 micron label does not match our scale.** The cut reads about 353 microns at 18.1165 to
  18.25 microns per pixel. Quote the pixel boundary and both scales.
- **Seed noise.** One seed. A gap under 0.03 AUROC between arms is not a finding.
- **Cross-class training loss** from the union move rule, quantified above.
- **Stage 0 contamination** on 327 pictures, labelled wherever it appears.

## Decisions settled on 16 November

**D1. Resolution.** Two arms: 224, the Experiment 1 recipe, and 448, the same recipe. One variable
changed, both reported.

**D2. Move rule.** The union rule stands; one 4-column head. The loss of 56 gated Fiber and 20
gated HEMA training pictures is accepted and quantified in the result. Four single-class models
were rejected because the pilot must match the form of the experiment it precedes.

**D3. Pass/fail scope.** Object-side verdicts on the 99 decisive pictures, plus an object-side-only
verdict on the full test set, labelled as such in the header of that table.

**D4. Success criterion.** None. The pilot is a placeholder; the tables are judged after the lead
sees them. Nothing in the workbook may call the result a pass or a fail.

**D5. Gating.** Nothing gates Experiment 3.2 mechanically. The next step is decided after the
results are shared with the lead.

## Ticket chain

| # | Ticket | Card | Owner | Depends on |
|---|---|---|---|---|
| 037 | Build the split and the 4-column label table, with verifier | `t_d968fd78` | default | - |
| 038 | Stage the split and label table on the VM, verify every image resolves | `t_c0604159` | ml-runner | 037 |
| 039 | Add `--columns gate4` and a smoke test, labels-only match | `t_11234b0c` | default | 037 |
| 040 | Stage 0: score the Experiment 1 checkpoint on the new test population | `t_c4a87d42` | ml-runner | 038 |
| 041 | Stage 1a: train `gate4_224`, wait-mode launcher, run record | `t_79fc08df` | ml-runner | 038, 039 |
| 042 | Stage 1b: train `gate4_448`, wait-mode launcher, run record | `t_eb3ab4ab` | ml-runner | 038, 039 |
| 043 | Score both arms: AUROC, false-fire, recall, size curve | `t_f58e747d` | default | 040, 041, 042 |
| 044 | Workbook with the two table sets and the per-picture sheet, verifier | `t_4e13d669` | default | 043 |
| 045 | Decision file, session doc, handoff | `t_48d862ba` | default | 044 |

Routing notes: `default` owns the split, the label table, the trainer change, the scoring and the
workbook, one executor per file. `ml-runner` owns the VM dataset build, Stage 0 inference and both
training runs, and writes one `run.json` per run. The orchestrator pushes the modules and the
dataset with the `tee` idiom and records md5s both ends; a dispatched worker cannot use that route
and will be blocked on sudo.

## Out of scope

- Any change to split v8, the Experiment 1 workbook, the Experiment 2 dataset or either detector arm.
- A per-object size head; the tag cannot train one.
- Bubble Cluster pass status; this pilot assumes fail and does not test the alternative.
- Crops, tiling or any resolution beyond what D1 selects.
- Lead-facing artifacts. The pilot is internal; a lead-facing workbook only follows a go decision
  on Experiment 3.2.


## Result (16 November)

The pilot ran end to end. Stage 0 scored the Experiment 1 checkpoint on the new test population
before any training, to fix the starting point.

| Arm | Foreign Matter AUROC | Recall at cut | False-fire, all untagged | False-fire, size decides |
|---|---|---|---|---|
| Stage 0, Experiment 1 checkpoint | 0.613 | 93.7% | 84.5% | 23.5% (12/51) |
| `gate4_224` | 0.745 | 83.5% | 49.5% | 9.8% (5/51) |
| `gate4_448` | 0.759 | 43.0% | 12.4% | 2.0% (1/51) |

Fiber: 0.572 at Stage 0, 0.687 at 224, 0.664 at 448. Extraneous Polymer 0.922, 0.879, 0.870. HEMA
0.779, 0.974, 0.958, not judgeable because every production HEMA picture carries the flag.

The size-bin curve is the finding that matters. Mean Foreign Matter score by largest box in native
pixels, bins 0-8 / 8-12 / 12-18 / 18-24 / 24-36 / 36-64 / 64+:

- Experiment 1 checkpoint: 0.764 / 0.792 / 0.776 / 0.703 / 0.646 / 0.554 / 0.691, falling with size.
- `gate4_224`: 0.418 / 0.445 / 0.480 / 0.522 / 0.556 / 0.463 / 0.702, rising across the boundary at
  about 19.5 native pixels.

That is the first evidence in this line that the network can learn size rather than texture.

Pass/fail on the pictures where size alone decides: 98 distinct pictures. The class counts are
Foreign Matter 51, Fiber 14, Extraneous Polymer 34 and HEMA 3, which is 102 class-decisions over 101
pictures: one picture is decisive for both Foreign Matter and Fiber, and the three HEMA pictures are
left out because HEMA cannot be judged. The table therefore rests on 98. The current model fails 13
of them, `gate4_224` 9, `gate4_448` 4. Read beside recall: 448 looks best only because it passes
almost everything.

Decision as taken: no pre-registered bars. The pilot is a placeholder judged after the lead sees the
tables. `gate4_224` stays the reference arm; `gate4_448` buys fewer false fails with less than half
the recall and is not a better model. Its lower recall is a threshold choice, not worse learning:
the ranking barely moved, 0.745 to 0.759, and no threshold sweep was run.

The four-class results feed Experiment 3.2, which uses `gate4_224` as its size specialist.
