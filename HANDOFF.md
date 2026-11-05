---
title: Handoff (state of the work)
date: 2026-11-04
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** point 4 is complete. The object-of-interest flag is now seven trainable object
classes plus a size-gate subset, trained in one nineteen-column head with inverse-frequency weights,
and the pass/fail rule is read from that head. The delivered artifact is
`reports/multilabel_production/ooi_point4_workbook_20261104.xlsx`; the decision record is
`docs/decisions/2026-11-04-ooi-class-vs-gate.md`; the round-by-round record is
`docs/sessions/2026-W45.md`.

**Numbers to quote**

- Class labels beat gate labels on identical truth: macro AP 0.4955 against 0.4391.
- The weight beats no weight: 0.6330 against 0.4955, with HEMA 0.963 and Extraneous Polymer 0.428.
- One head holds both jobs: object 0.6380, lens judgeable 0.8815 against November's 0.8182.
- Pass/fail at 0.5: 760 of 768 fail pictures caught, 1 clear picture wrongly failed, 8 of 36
  bubble-only pictures passed, 324 of 353 passed overall. Under the same rule November catches
  710 of 768 and wrongly fails 3 clear pictures.

**In flight**

Nothing runs. The four arms of `run/multilabel_ooi_20261104/` are complete with `status: ok` in
each `run.json`; the checkpoints (`final.pt`, 91 MB each) live on the VM only and are gitignored
locally. The A100 is idle.

**Parked for review:** the atomised plan for the next round is
`docs/wayfinder/next_chain_lanes_20261105.md`. Nothing is created and nothing is dispatched. Read the
plain-English walkthrough and the point-4 workbook first; approval of the plan creates the cards, and a
second go releases the first dispatch.

**Ready for the full-data rerun:** `docs/reference/threshold_protocol.md`. It fixes the rule we will use
when the model is retrained on the complete data: validation precision floor instead of a picture-count
guard, grid floor at 0.05, plateau centre instead of a single peak, two seeds, and a selected-thresholds
sheet in the workbook. No approval needed, it is a method doc.

**Next, in order**

1. Bubble-only false fails: 28 of 36, with Foreign Matter firing on 23 and Fiber on 11. Hard
   negatives from bubble-only pictures, or a specificity term on those two classes.
2. Extend the threshold grid to 0.99 and rescore; HEMA and No Lens chose 0.95, the grid boundary.
3. A second seed of the weighted and combined arms, to put an error bar on every delta.
4. The gate-plus-weight arm, testing "the gate is worse" against the best gate, not an unweighted one.
5. Client rulings, then the annotation owner's items, then ticket 022.

**State to know**

- The split is `run/split_20261103_v8/` (7,470 rows, md5 `1a71d66d2de384cf47a3fcf7d9115baa`) and is
  unchanged since 2026-11-03. Every number above reads it.
- The label table is `run/ooi_matrix_20261104/ooi_labels.csv` (7,470 x 27, md5 `7fd1106e`), carrying
  both `class_*` and `gate_*` columns. The gate column is a subset, never a second class.
- Surface Groove has zero pictures. Nineteen columns are trained, not twenty; the map and ticket 033
  were corrected.
- `train_multilabel.py` carries a fix for a lens-branch `KeyError` that only fired at the end of a
  combined run. Its smoke still does not cover the evaluation branch; that is a known gap.
- One seed only. Treat any delta below about 0.03 AP as unproven.

**Open items that need a human**

- P3_HE: HEMA Obstruction in the production files, HEMA Fragment in the September project. Until
  the client rules, production boxes count as HEMA and the whole-image tag stays a reference row.
- Fiber versus Extraneous Polymer naming, provisional until the next annotation.
- Annotation owner: three pictures are listed twice in the export, and one is listed with no marks.
- Ticket 022 picture-by-picture legs (Fiber gate 137-vs-136, Folded Lens 237-vs-178, the 84-picture
  rescue set) were parked on the seven-file record and need re-reading against the current one.
- Folded Lens stays below its 0.70 target; the overlap with Multiple Lens is a real limitation.
- Whether `handover/model_package/config.json` should be corrected now, and whether the methodology
  doc covers both the old and the new measurement.

**Decisions settled, do not relitigate**

- Object classes, not the micron gate, are the training target. The gate is reported as "of which
  size-flagged" and never fed to the same model as a second class.
- Pass/fail: a picture passes only when clear or carrying nothing but Bubble and Bubble Cluster.
- Clear is exclusive. Unannotated pictures are out. Standalone tags carry no co-tags.
- Bubble is one class: Bubble Irregular and Stretched Bubble fold in; Bubble On 123, Bubble On Edge
  and HEMA Obstruction stay out of the split label space.
- Weighting is inverse frequency on the training split only. Thresholds come from validation only,
  grid 0.05 to 0.95, highest F1, ties to the higher cut.
- Reader-facing artifacts carry no internal names, paths, ticket ids or role attribution, and every
  doc carries the five-line header. `docs/INDEX.md` is generated, never hand-edited.

**Where the history lives**

`docs/sessions/2026-W45.md` covers this work; `2026-W44.md` covers 26 October to 1 November.
Decisions are in `docs/decisions/`, standing instructions in `docs/instruction.md`, and the
working traps in `session_shakehand.md`, dated 2026-10-28 and stale on VM staging.
