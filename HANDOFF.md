---
title: Handoff (state of the work)
date: 2026-11-16
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** both pieces of 16 November are done and reported. The four-class size pilot
(Experiment 3.1) and the Experiment 1 redo under the new rule order (Experiment 3.2) are built,
scored, verified and written up. The redo workbook is with the lead; the user holds a copy on the
desktop. The one open decision is which rule order is the working rule. The two differ by 18
pictures, all Bubble Cluster.

**Numbers to quote (Experiment 3.1, four gated classes, 1,533-picture test set)**

- Stage 0, the Experiment 1 checkpoint: Foreign Matter AUROC 0.613, false-fire on below-cut pictures
  84.5%, recall 93.7%; Fiber 0.572; Extraneous Polymer 0.922; HEMA 0.779, not judgeable.
- `gate4_224`: Foreign Matter 0.745, false-fire 49.5%, recall 83.5%; Fiber 0.687; EP 0.879; HEMA
  0.974. `gate4_448`: 0.759, 12.4%, 43.0%; Fiber 0.664.
- Size-bin curve: the old model's mean Foreign Matter score falls with box size, 0.792 at 8-12
  native pixels to 0.554 at 36-64; the gate arm rises across the cut at about 19.5 pixels, 0.445 to
  0.556. First evidence the network can read size.
- Pass/fail where size alone decides, 98 pictures: current model fails 13, 224 fails 9, 448 fails 4.
  Quote beside recall.

**Numbers to quote (Experiment 3.2 redo, same 1,121 test pictures as Experiment 1)**

- Primary rule, Bubble Cluster fails: 784 fail, 778 caught (99.2%), 6 missed; 337 pass, 311 passed
  (92.3%), 26 wrongly failed.
- Secondary rule, Cluster passes: 766 fail, 760 caught, 6 missed; 355 pass, 325 passed (91.5%), 30
  wrongly failed.
- Decomposition: the Experiment 1 reading on the same two models gives 768 fail and 353 pass, exactly
  the earlier number. Size correction 2 pictures; new order 18.
- Condition model: macro AP 0.8017 over fifteen columns, per-class AUROC 0.931 to 1.000. Weak by F1:
  Folded Lens 0.578 at precision 0.480, Wet Package 0.517, Bubble Cluster 0.682 at precision 0.533.
- Size model at its cuts on the pictures carrying each class: Foreign Matter precision 0.260, recall
  0.835, F1 0.396; Fiber 0.839 / 0.589 / 0.692; EP 1.000 / 0.375 / 0.545; HEMA 1.000 / 0.846 / 0.917
  on 6 untagged pictures.

**Earlier numbers still standing**

- Experiment 1, frozen split: object macro AUPRC 0.6380, lens macro AUPRC 0.8815, exact match 0.811.
  Rule as run: 760 of 768 failing pictures caught, 324 of 353 pass overall at 0.5. Only Bubble: 776
  of 785, 322 of 336.
- Experiment 2 detector, all pictures: test mAP50-95 0.1707 over 1,121 pictures and 5,472 boxes;
  boxed-only arm 0.1475. All pictures stays primary.

**In flight**

Nothing on the GPU. The VM holds three checkpoints, all git-ignored: `combined/final.pt` 91 MB
`0bce7432`, `exp3_1_gate4_224_20261117/final.pt` 90 MB `36e5d7e0`,
`exp3_1_gate4_448_20261117/final.pt` 90 MB `ff217331`; the condition model's checkpoint is at
`run/exp3_2_cond15_20261116/final.pt`.

**Next, in order**

1. The lead's rule decision. If she takes the primary order, nothing re-runs. If she takes the
   secondary order, the headline becomes 766 / 760 / 355 / 325 without retraining.
2. A second seed for the condition model if the 18-picture gap has to be separated from run noise.
3. A threshold sweep for `gate4_448` if its 43% recall is to be read as tuning rather than a model
   difference.
4. After the rule is settled, the production wiring: one verdict path, the two rule ids in
   `pass_fail_block.py`, and a reader-facing definition of the guard set.

**State to know**

- Frozen split v8: `run/split_20261103_v8/` (7,470 rows, md5 `1a71d66d2de384cf47a3fcf7d9115baa`);
  5,239 / 1,110 / 1,121. Untouched.
- Pilot split: `run/split_exp3_1_20261116/` (7,555 rows, 4,964 / 1,058 / 1,533); labels md5
  `222c873f17a9f101d32b0b36e210e5e3`; 327 pictures left train or validation, 85 added from outside
  v8, 41 already in v8 test.
- Redo condition table: `run/split_exp3_2_20261116/labels_conditions.csv`, md5
  `9f3ef6bc582f3e4586de414510de01e7`, 7,470 rows on the frozen assignment, fifteen columns.
- Annotation of record: `run/eda_full_20261029/resolved_labels.csv` (44,791 rows, md5
  `f61ea0b90df095ebe52d1332f8bfdb8a`); `picture_table.csv` keyed on `md5`, path column
  `winning_path`.
- Images on the VM at `/data/FMD_Data_26082026/fmd_temp_images/{winning_path}`, 2448 by 2048.
- Workbooks: `reports/multilabel_production/size_gate_pilot_20261116.xlsx` (7 sheets) and
  `size_gate_redo_20261116.xlsx` (9 sheets, including the all-class table). Both verified.
- Kanban is not in use. The nine cards from 16 November are archived; work runs through subagents
  and direct SSH on the VM.

**Open items that need a human**

- Which rule order is the working rule: the lead's call. Bubble Cluster is the only difference.
- The size flag reads about 353 microns at our scale, not the client's 300; the scale source is
  unresolved.
- HEMA has 6 untagged test pictures, so its size read says little.
- One run per model. No repeat-seed comparison on this line yet.
- Bubble Scatter has one test picture; its F1 is noise.

**Decisions settled, do not relitigate**

- Two specialists, one verdict. A picture cannot be a training example for its lens tag and an
  unseen example for its size class.
- The rule order is a presentation change, not a recount. Experiment 1 already counted both orders;
  the primary order now leads.
- Size truth for the four gated classes: below the cut passes on that class and only that class. A
  lens condition or Wet Package still fails the picture.
- No pre-registered bars on the size pilot; it is a placeholder judged by the lead.
- `gate4_224` is the reference size arm; `gate4_448` is a trade, not a better model.
- Weighting is inverse frequency on the training split only; thresholds come from validation only,
  highest F1, ties to the higher threshold.
- Object classes, not the micron gate, are the training target for the condition model; the gate is
  the size model's truth.
- Clear is exclusive; unannotated pictures are out; Bubble Irregular and Stretched Bubble fold into
  Bubble.
- Reader-facing artifacts carry no internal names, paths, ticket ids or role attribution; every doc
  carries the five-line header.

**Where the history lives**

`docs/sessions/2026-W47.md` covers 16 November; `2026-W46.md` the week before. The pilot map is
`docs/wayfinder/exp3_1_size_gate_20261116.md`; the redo is
`docs/wayfinder/exp3_2_redo_20261116.md`; the rules are
`docs/decisions/2026-11-16-size-rule-order-and-gate-truth.md`.
