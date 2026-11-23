---
title: Handoff (state of the work)
date: 2026-11-23
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** housekeeping. The frozen work is complete and verified but nothing is committed. The
annotation export is now out of git, so the commit can be cut. Five questions are still with the lead;
do not build on their answers until they land.

## Settled on 23 November

- **"FM and Debris" means the four size-tagged classes:** Foreign Matter, Fiber, Extraneous Polymer,
  HEMA.
- **Strict PASS allows an untagged object of another debris class.** A picture passes when none of the
  four carries a size tag, provided it also has no presentation tag, no Bubble Cluster and no Wet
  Package.
- The doubt that this case might not occur in the data is answered: on the frozen split 755 pictures
  carry one of the four classes with no size flag at all, and 244 of them pass, 32 in the test split.
- Recount and decisions: `docs/decisions/2026-11-23-fm-debris-scope.md`.
- **New point for the lead:** 18 of those 244 carry no Bubble box at all and still pass. If a Bubble-free
  object set should not pass, the rule needs one more sentence.

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
- Workbook: `experiments/frozen_data_experiments/multilabel_cnn/results/frozen_multilabel_results.xlsx`,
  verifier 7,385 checks pass. Weights stay on the VM. No re-run is needed to get another metric.
- Lead-facing model review: `reports/frozen_multilabel_cnn_20261119/` (docx and pdf).
- Duplicate pairs, reissued 23 November with oriented boxes, are with the lead:
  `reports/frozen_pairs_20261117/pairs_obb.png` and the four single sheets. Renderer and verifier in
  `experiments/annotations/`. Oriented boxes are now the standing rule:
  `docs/decisions/2026-11-23-oriented-boxes-default.md`.

## Open with the lead

1. Sign-off on the pass/fail counts.
2. The 147 held add-backs wait on client confirmation; 27 legacy pictures are discarded.
3. The four duplicate pairs: the split keeps the highest-box copy; not yet confirmed.
4. **Surface Groove**: 88 pictures carry it, it has no object boxes and is not one of the 17 columns, so
   under the current text it passes unless another fail class is present. Is it a defect?
5. The 18 Bubble-free pictures that pass under strict PASS.

## Next, in order

1. Commit the frozen work. `data/Annotations.zip` and `data/Frozen Annotation Dataset/` are gitignored;
   the derived split, labels and gates stay tracked.
2. Review the workbook with the user.
3. Decide whether the main table stays at 0.5 or moves to the provisional validation cuts.
4. Confirm the AUROC and AUPRC framing with the lead.
5. Finalize the workbook.

## Housekeeping state

- `.gitignore` now excludes the raw annotation export (40 MB, 27 XML files, re-exportable from CVAT).
  `data/Annotations.zip` goes too, because it only repacks XMLs already tracked.
- `notiondocs.md` is deprioritised: the board is rarely used and the knowledge base at `D:/SecondBrain`
  is where information is kept. Backlog if it is ever resumed: 12 entries verified but unpushed,
  5 still draft.
- `docs/INDEX.md` regenerated: 197 files, 0 without a header.
- The wayfinder effort for OOI point 4 is closed; its kanban card is an index card only.

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
