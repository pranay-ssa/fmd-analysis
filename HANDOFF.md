---
title: Handoff (state of the work)
date: 2026-11-03
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** the experiment now runs on the full twenty-four-file annotation of record
(`run/eda_full_20261029/resolved_labels.csv`, 44,791 marks on 5,500 pictures) and split v7
(7,470 rows). Both variants were retrained on 2026-10-29; the current read-out is
`reports/multilabel_production/lp_full_results_20261029.xlsx` and `lp_full_report_20261029.html`.
Variant 1 scores 0.851 macro average precision on the eight judgeable classes (bar 0.85, met),
variant 2 scores 0.817. The OOI flag fires on 99.3 percent of OOI-only pictures and 0.5 percent
of Clear pictures. Folded Lens is the one class under its target at 0.49. What is left is the
reply workbook, which still answers with pre-merge counts, plus the client rulings and the
picture-by-picture legs of ticket 022.

**State**

- The 24-file population joined the experiment on 2026-10-29. It was executed, not argued: the
  label matrix, the split and both trained variants all read the merged record. No decision
  file records it yet, and two entries in `docs/instruction.md` still describe the trained
  models as pre-merge measurements and the VM as read-only for proofs.
- The annotation moved twice in two days. `run/eda_full_20261028/` is the seven-file record
  (20,011 marks); `run/eda_full_20261029/` is the twenty-four-file record (44,791 marks) and is
  byte-identical to `run/eda_full_24files_20261028/` (same md5, f61ea0b9). They are not
  interchangeable: Bubble is 819 pictures on the seven-file record and 2,138 on the merged one.
  The 20261029 folder is the one with the full provenance, 24 files with a sha256 each, and
  3,594 pictures win their annotation at production priority.
- Split v7 is the split of record for the trained models: 7,470 rows, 70/30 is 5,235 / 2,235,
  80/20 is 5,989 / 1,481. 147 pictures are outside it, 62 legacy-only and 85 with an un-gated
  object only. `run/split_20261028_v6/` (6,659 rows) stays on disk for the 2026-10-28 run.
- Variant 1 (twelve LP classes) trained on 5,403 pictures and tested on 1,344; variant 2 (the
  same twelve plus one OOI-present flag) trained on 5,989 and tested on 1,481. Training took
  1,499 s and 1,658 s on the A100; inference 5.6 and 5.65 ms per picture.
- The two commits from the 2026-11-02 documentation pass are unpushed. The tree is otherwise
  clean and every artifact named below is tracked.

**Artifacts of record**

| What | Where | Size |
|---|---|---|
| Annotation of record | `run/eda_full_20261029/resolved_labels.csv` | 24 files, 44,791 marks, 5,500 pictures |
| Picture table, disagreements | `run/eda_full_20261029/picture_table.csv`, `disagreement.csv` | 10,614 pictures, 3,672 unannotated |
| Label matrix | `run/multilabel_edge_20261029_rev4/label_matrix.csv` | rev 4, merged record |
| Split of record | `run/split_20261029_v7/` | 7,470 rows, 70/30 and 80/20 |
| LP label tables | `run/multilabel_lp_full_20261029/labels_a.csv`, `labels_b.csv` | 6,747 and 7,470 rows |
| Run metrics | `run/multilabel_lp_full_20261029/a/`, `b/` | 1,344 and 1,481 test pictures |
| Results read-out | `reports/multilabel_production/lp_full_results_20261029.xlsx` | current in every quote |
| Results report | `reports/multilabel_production/lp_full_report_20261029.html` | current |
| Split by class, 7 vs 24 files | `reports/multilabel_production/FMD_Split_By_Class_20261030.xlsx` | per class, both variants |
| Total EDA | `reports/eda_total_20261028/FMD_EDA_Total_20261028.xlsx` | 10,614 / 5,500 marked / 2,117 Clear / 7,617 analysed |
| 24-file EDA workbooks | `reports/eda_24files_20261028/` | batch and record, verified |
| Client handover package | `handover/model_package/`, `docs/reference/client-handover-lp-multilabel.md` | verified 2026-10-30 |

Superseded and kept as history, never quoted: `run/eda_full_20261028/`, `run/split_20261028_v6/`,
`run/multilabel_lp_full_20261028/`, and everything in `reports/draft2_eda_20261023/`.

**Next, in order**

1. Rebuild the reply workbook on the merged record. The client has the pre-merge counts:
   `reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx` is stale by its own
   README. The builder and verifier exist (`build_answer_v2.py`, `verify_answer_v2.py`) but
   still read `run/eda_full_20261015/` and the rev-3 matrix, so they need repointing to the
   24-file record and rev 4 before they run.
2. Record the join as a decision, one short file, so it is not reopened: population is the
   twenty-four-file annotation, split v7, and the 2026-10-28 models are superseded
   measurements. Then add superseding entries to `docs/instruction.md` for the two 2026-10-28
   entries this contradicts (trained models are pre-merge; compute is local and the VM is
   read-only for proofs).
3. `docs/reference/draft2_eda_ooi_20261023.md` still cites the seven-file record as current.
   Its class and object counts are seven-file counts. It needs the 24-file figures or an
   explicit stale note.
4. Push the two 2026-11-02 commits.
5. Client rulings, then the annotation owner's items, then ticket 022.

**Open items that need a human**

- P3_HE: HEMA Obstruction in the production files, HEMA Fragment in the September project.
  Until the client rules, production boxes count as HEMA and the whole-image tag stays a
  reference row.
- Fiber versus Extraneous Polymer naming: provisional until the next annotation. The reply
  convention keeps the earlier Fiber name so the columns agree with the onboarding report, and
  states the annotation reading in a note.
- Annotation owner: three pictures are listed twice in the export (one identical pair, two
  differing by 1 and 7 marks), and one picture is listed with no marks and loses its only label
  under precedence.
- Ticket 022, picture-by-picture legs: Fiber gate 137-vs-136, Folded Lens 237-vs-178, the
  84-picture rescue set. These were parked on the seven-file record; the class counts have
  moved since (Folded Lens is 333 pictures on the merged record), so re-read the discrepancy
  against the current record before closing it.
- Folded Lens stays below its 0.70 target. The fold-plus-multiple-lens overlap is a real
  limitation, not only a data shortage.

**Decisions settled and must not be relitigated**

- Gate IS the class for Foreign Matter, Fiber, Extraneous Polymer and HEMA in the split; the
  EDA counts every picture that shows the class and reports the gate as "of which
  size-flagged". Never present one as the other.
- Clear = the winning path sits in a Clear folder of the two Updated libraries, and Clear is
  exclusive: a picture with any other label is not Clear.
- Standalone tags carry no co-tags (measured, ticket 023).
- Unannotated pictures are out: zero tags means no tags.
- Bubble is one class; Bubble Irregular, Stretched Bubble and the older plain names fold in.
  Bubble On 123, Bubble On Edge and HEMA Obstruction stay out of the split label space.
- 70/30 two-way split, seed 42, content-md5 groups, no validation split. The trainer uses a
  fixed schedule and never selects on the test set.
- Draft 2 codes and the legend in every artifact.

**Rules in force**

Numbers go to the user the moment they are read, before verification or documentation.
Verification runs in parallel and a correction follows if it contradicts the first reading.
Every generated artifact has a verifier that recomputes from the annotation and proves a
tampered cell is caught. A triple check is three legs: hand-typed expected values, a
byte-identical rerun, and an independent second derivation.

Training runs on the shared A100, because the pixels live there; the staged tree is
`/home/pranayp/fmd-analysis` and scripts are piped over ssh, so nothing loose is left on the
box. Credentials are never printed. Everything else computes local.

Reader-facing artifacts carry no internal names: no paths, script names, run folders, ticket
ids or version tags, and no role attribution. Result first, method in one plain sentence,
definitions where a term first appears. Every doc carries the five-line header and
`docs/INDEX.md` is generated, never hand-edited. Pitfalls go to `docs/pitfalls.md`.

**Where the history lives**

`docs/sessions/2026-W44.md` covers 26 October to 1 November, including the re-export, the
merged record, the 2026-10-29 retrain and the 2026-10-30 read-out. `2026-W43.md` covers the
Draft-2 EDA and split v3. Decisions are in `docs/decisions/`; standing instructions are in
`docs/instruction.md`; the working context and the traps are in `session_shakehand.md`, which
is dated 2026-10-28 and is stale on the VM staging and on the split in use.
