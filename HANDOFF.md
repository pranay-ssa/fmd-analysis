---
title: Handoff (state of the work)
date: 2026-11-05
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** the October story is drafted and the A/B workbook is built for the lead. The draft
is `decks/drafts/FMD_MultiLabel_2026W45_DRAFT.pptx` (12 slides) with a PDF beside it; the workbook is
`reports/multilabel_production/FMD_MultiLabel_Runs_2026W45.xlsx` (7 sheets). Point 4 remains
complete; its workbook and decision are unchanged.

**Numbers to quote (frozen 70/15/15 split, validation-chosen thresholds)**

- Lens only (A, 5 November): lens AUPRC 0.836, macro F1 0.722 at 0.5 and 0.801 at chosen
  thresholds, exact match 0.789 at 0.5 and 0.777 at chosen, 5.76 ms per picture.
- Lens plus object flag (B, 3 November): lens AUPRC 0.818, macro F1 0.724 at 0.5 and 0.781 at
  chosen, exact match 0.764 at 0.5 and 0.762 at chosen, 5.59 ms per picture.
- Object flag on 1,121 test pictures: object-only 117 of 120 (97.5%) at 0.55; mixed 211 of 223
  (94.6%); Clear 0 of 317. The flag's threshold is 0.55.
- Folded Lens: 0.42 alone, 0.49 with the flag, below the 0.70 target.
- The four classes held at 0.50: Dirty Strobe (8 validation / 2 test), View Obstructed (9 / 10),
  Bubble Scatter (1 / 1), Package Misalignment (5 / 5). The guard is validation; test never chooses
  a threshold.

**In flight**

Nothing runs. The draft and workbook are ready for the lead. Pass/fail numbers are deliberately out
of the October story; they are next week's subject.

**Next, in order**

1. Send the draft and the workbook to the lead; invite corrections on the slide face and the
   per-class table.
2. Build the pass/fail readout for the following week from the point-4 scores.
3. Run the full-data retrain under `docs/reference/threshold_protocol.md`; the protocol uses a
   validation precision floor, a 0.05 grid floor, plateau centre, two seeds, and a
   selected-thresholds sheet.
4. Bubble-only false fails, the 0.99 grid boundary, and a second seed remain open.

**State to know**

- The split is `run/split_20261103_v8/` (7,470 rows, md5 `1a71d66d2de384cf47a3fcf7d9115baa`). The
  counts are 5,239 training, 1,110 validation, 1,121 test.
- Run records: `run/multilabel_lp_v8_20261103/b/` (lens plus flag) and
  `run/multilabel_lp_v8_20261105/a/` (lens only). Arm a wrote metrics, thresholds and labels but no
  `run.json`; b did. Fix that on the next run.
- The threshold grid was 0.05 to 0.95 in 0.05 steps; the protocol reference asks for a finer grid on
  the full-data run.
- The deck and workbook use the field's standard terms: train, validation, test, threshold, AUPRC,
  macro F1, exact match, inference time per picture. The decision is
  `docs/decisions/2026-11-05-standard-terms.md`.
- `docs/INDEX.md` is generated; do not hand-edit. `timesheets/*.xlsx` stay local; only the README is
  tracked.

**Open items that need a human**

- P3_HE: HEMA Obstruction in production files, HEMA Fragment in September; until the client rules,
  production boxes count as HEMA.
- Fiber versus Extraneous Polymer naming, provisional.
- Annotation owner: three pictures listed twice, one with no marks.
- Folded Lens below 0.70; the overlap with Multiple Lens is a real limitation.
- The client package still points at the 2026-10-29 checkpoint; the lead has not chosen a variant
  for handover.

**Decisions settled, do not relitigate**

- Object classes, not the micron gate, are the training target. The gate is reported as "of which
  size-flagged".
- Pass/fail: a picture passes only when clear or carrying nothing but Bubble and Bubble Cluster.
- Clear is exclusive. Unannotated pictures are out. Standalone tags carry no co-tags.
- Bubble is one class; Bubble Irregular and Stretched Bubble fold in; Bubble On 123, Bubble On Edge
  and HEMA Obstruction stay out.
- Weighting is inverse frequency on the training split only. Thresholds come from validation only,
  highest F1, ties to the higher threshold.
- The threshold table defaults a class to 0.50 when validation has fewer than 10 positives; test is
  shown but never chooses.
- Reader-facing artifacts carry no internal names, paths, ticket ids or role attribution; every doc
  carries the five-line header.

**Where the history lives**

`docs/sessions/2026-W45.md` covers this week; `2026-W44.md` covers 26 October to 1 November.
Decisions are in `docs/decisions/`, standing instructions in `docs/instruction.md`, and the working
traps in `session_shakehand.md` (dated 2026-10-28, stale on VM staging).
