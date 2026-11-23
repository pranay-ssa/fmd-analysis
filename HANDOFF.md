---
title: Handoff (state of the work)
date: 2026-11-23
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** the frozen work is committed at `3214483` (173 files); nothing is pushed yet. Five
questions are still with the lead; do not build on their answers until they land.

## Settled on 23 November

- **"FM and Debris" means the four size-tagged classes:** Foreign Matter, Fiber, Extraneous Polymer,
  HEMA.
- **Strict PASS allows an untagged object of another debris class.** A picture passes when none of the
  four carries a size tag, provided it also has no presentation tag, no Bubble Cluster and no Wet
  Package.
- The doubt that this case might not occur in the data is answered: on the frozen split 755 pictures
  carry one of the four classes with no size flag at all, and 244 of them pass, 32 in the test split.
- Recount and decisions: `docs/decisions/2026-11-23-fm-debris-scope.md`.
- **Surface Groove is not a fail class today.** It sits below the 200-picture cut, so it is neither a
  column nor a fail condition. When augmentation brings the class to about 200 pictures it becomes a fail
  class and takes a column, on the same trigger, with no new decision needed. 88 pictures carry it and 87
  already fail for another reason, so today it changes one train verdict and no test number.
- **Precedence, restated by the lead:** fail dominates. A picture fails if any fail condition is on it,
  and passes only when none is. Pass conditions are a Bubble box or an untagged size-gated class. That
  settles the 18 Bubble-free passes: they pass on their untagged class, not on an empty mark set. No
  picture in the split has an empty mark set.
- Decision file: `docs/decisions/2026-11-23-surface-groove-threshold.md`.

## Frozen split and run

| Item | Value |
|---|---:|
| Pictures | 13,631 |
| Train / Validation / Test | 9,537 / 2,049 / 2,045 |
| Columns | 17 (10 lens, 7 object) |

- md5: `split.csv` `31a41925e0c349608ff77bf24d801585`, `labels_17.csv`
  `0d76b29097bc3a95e1b4bb14e9c172cb`, `gates_4.csv` `c97cc04314d2e2b925cdd343e0b80058`. Verifier: 31 of
  31 checks pass.
- Run: 50 epochs, ResNet-50 at 224, seed 42, 26.8 minutes, no errors. Macro AUPRC 0.8423, macro AUROC
  0.9624, macro F1 0.8040 at 0.5 and 0.8187 at the validation-chosen cuts. Inference 3.05 ms per
  picture.
- Pass/fail at 0.5: TA 11, FR 137, TR 1,896, FA 1. TAR 7.4 percent, TRR 99.9 percent, FAR 0.1 percent,
  FRR 92.6 percent. Object-presence proxy; the run has no size output.
- Workbook: `experiments/frozen_data_experiments/multilabel_cnn/results/frozen_multilabel_results.xlsx`. A
  fresh build from the builder passes all 7,385 verifier checks. The file in the repository is not that
  build: it was re-saved in Excel on 20 November, which inserted a row in Summary, typed an AUROC caveat
  sentence into Per class and dropped the freeze panes on two sheets. It does not pass its own verifier.
  Decide whether to fold that sentence into the builder and rebuild, or to keep the hand-edited file as
  the delivered one and quote no verifier count for it. Weights stay on the VM. No re-run is needed to
  get another metric.
- Lead-facing model review: `reports/frozen_multilabel_cnn_20261119/` (docx and pdf).
- Duplicate pairs, reissued 23 November with oriented boxes, are with the lead:
  `reports/frozen_pairs_20261117/pairs_obb.png` and the four single sheets. Renderer and verifier in
  `experiments/annotations/`. Oriented boxes are now the standing rule:
  `docs/decisions/2026-11-23-oriented-boxes-default.md`.
- Pair 4 framing, from the lead's feedback: only the black border is removed. The window is the
  specimen extent from lit runs (>= 24 px) padded 5 percent, plus 5 percent at the top and right,
  which the user marked as too tight. 823 lit pixels of 1.36 million fall outside it, all 4 to 15
  grey levels in 267 isolated clusters (sensor speckle). Panel scale 0.483, lens about 660 px in a
  760 px panel, visible margins 73/68/68/76. Pairs 1 to 3 keep the annotated region.
  `--frame trim|whole|crop` switches the modes.
- The pair-4 framing is not a new method: it is the content-anchored border crop specified on
  2026-09-03 in `reports/preprocessing/fixed_size_crop_spec.md`. The run-length detection there
  answers that spec's own guard-cause note about a far streak inflating the content box. Noted in
  that doc and in the figure reference; present it as the original border crop.

## Open with the lead

1. Sign-off on the pass/fail counts.
2. The 147 held add-backs wait on client confirmation; 27 legacy pictures are discarded.
3. The four duplicate pairs: the split keeps the highest-box copy; not yet confirmed.

## Next, in order

1. Push `3214483` when an off-machine copy is wanted.
2. Review the workbook with the user.
3. Decide whether the main table stays at 0.5 or moves to the provisional validation cuts.
4. Confirm the AUROC and AUPRC framing with the lead.
5. Finalize the workbook.
6. When the Surface Groove augmentation lands and the class clears 200 pictures: add it as an 18th column,
   retrain, and say in the report that the result is not comparable with the 17-column run.

## Housekeeping state

- `.gitignore` now excludes the raw annotation export (40 MB, 27 XML files, re-exportable from CVAT).
  `data/Annotations.zip` goes too, because it only repacks XMLs already tracked.
- `notiondocs.md` is deprioritised: the board is rarely used and the knowledge base at `D:/SecondBrain`
  is where information is kept. Backlog if it is ever resumed: 12 entries verified but unpushed,
  5 still draft.
- `docs/INDEX.md` regenerated: 199 files, 0 without a header.
- The wayfinder effort for OOI point 4 is closed; its kanban card is an index card only.
- Stale Word lock file removed from `reports/frozen_multilabel_cnn_20261119/`. The `.bak` files stay: the
  ignore rules keep them on disk on purpose.
- Split verifier re-run today: 31 of 31 checks pass, md5s unchanged.

## Decisions settled, do not relitigate

- Clear is excluded: 42 pictures.
- The six classes under 200 pictures are removed as columns only; no picture drops.
- One copy per duplicate pair, highest box count; the 7/7 tie keeps the plain name.
- Split 70/15/15, seed 42, rows sorted by md5 before assignment.
- Counts first, not percentages.
- The workbook main table uses 0.5; the validation-chosen cuts are a separate provisional sheet.
- Pass/fail rule as written in `docs/decisions/2026-11-20-pass-fail-rule.md`, with the scope confirmed in
  `docs/decisions/2026-11-23-fm-debris-scope.md`.
- Oriented boxes everywhere; upright only on request and labelled as upright.
- The watcher uses a 10-minute quiet window below 10,000 MiB and 20 percent; a new compute process resets
  it.

## Where the history lives

`docs/sessions/2026-W47.md` covers 16 to 19 November. Decisions are one file each under
`docs/decisions/`. Split and run records are under `experiments/frozen_data_experiments/`. The EDA
workbook and its verifier are in `reports/frozen_eda_20261118/`, with state in
`docs/frozen_eda_workbook_20261118.md`.
