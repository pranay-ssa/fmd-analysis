---
title: Frozen EDA workbook - the 18 November draft
date: 2026-11-18
type: result
status: active
where: docs/frozen_eda_workbook_20261118.md
---

# Frozen EDA workbook: the 18 November draft

This is the current cut of the frozen annotation EDA: one workbook, nine sheets, built from the
verified store and checked by recount before it was written. It replaces the headline counts in
`docs/frozen_dataset_eda_20261117.md` and adds the size-flag PASS analysis and the duplicate-pair
sensitivity that the lead asked for on 18 November.

Workbook: `reports/frozen_eda_20261118/FMD_Frozen_EDA_draft_20261118.xlsx`.
Evidence: `run/frozen_eda_20261118/label_space.json` and `duplicate_sensitivity.json`.
Builders: `experiments/annotations/frozen_eda_labels.py`,
`frozen_eda_duplicate_sensitivity.py`, `build_frozen_eda_workbook.py`.
Verifier: `experiments/annotations/verify_frozen_workbook.py`, 185 checks, 0 failures.

## Population

All 13,682 annotation records are retained. Four pictures appear under two names, so there are
13,678 distinct pictures. The label tables count each picture once. No record was deleted.

| Measure | Pictures |
|---|---:|
| Annotation records, all retained | 13,682 |
| Second records of four pairs, retained | 4 |
| Distinct pictures | 13,678 |
| Pictures with at least one mark | 13,631 |
| Clear | 42 |
| Unannotated, excluded from labels | 5 |
| Labelled pictures | 13,673 |

Counting both records of every pair would give 13,677 labelled records. Excluding both copies of every
pair would give 13,669. The workbook uses the middle basis, one record per picture, as a working basis,
not a decision. The three bases are on the Duplicate sensitivity sheet.

## Label groups

| Group | Pictures |
|---|---:|
| At least one LP tag | 9,251 |
| At least one OOI box | 10,028 |
| LP tag and OOI box | 5,648 |
| Single label, LP | 3,439 |
| Single label, OOI | 672 |
| Exactly two labels | 4,236 |
| Exactly three labels | 2,754 |
| Exactly four labels | 1,262 |
| Five or more labels | 1,268 |

The LP and OOI groups overlap. LP plus OOI minus both equals the 13,631 marked pictures.

## Labels on the picture

| Labels | Pictures |
|---|---:|
| 1 | 4,111 |
| 2 | 4,236 |
| 3 | 2,754 |
| 4 | 1,262 |
| 5 | 715 |
| 6 | 361 |
| 7 | 155 |
| 8 | 33 |
| 9 | 4 |
| Clear | 42 |
| Total | 13,673 |

Clear counts as one label. There is no zero-label row. The five unannotated pictures are outside the
table.

## Three and four labels

Three labels: 1 LP + 2 OOI 1,529; 3 OOI 1,018; 2 LP + 1 OOI 207; 3 LP 0.

Four labels: 1 LP + 3 OOI 627; 2 LP + 2 OOI 438; 4 OOI 112; 3 LP + 1 OOI 85; 4 LP 0.

The composition tables list non-zero splits only. No picture carries three or four LP classes without
an OOI box: all 771 pictures with three or more LP classes also carry at least one OOI. Pictures with
no OOI box carry one LP class (3,439) or two (164).

The exact label-set tables are top 10 or top 15, not exhaustive. An unlisted set is outside the list,
not a zero.

## Size-untagged PASS

For the four size-flagged classes, an untagged picture carries the class but not its size flag. PASS,
bubbles only means no presentation tag, no size flag of any class, and every box is Bubble or an
untagged object of the four classes. PASS, extended also allows Bubble Cluster and Wet Package.

| Class | Pictures with class | Size-flagged | No size flag | Pass, bubbles only | Share | Pass, extended | Share |
|---|---:|---:|---:|---:|---:|---:|---:|
| Foreign Matter | 2,366 | 1,400 | 966 | 237 | 24.5% | 377 | 39.0% |
| Fiber | 1,394 | 1,304 | 90 | 6 | 6.7% | 8 | 8.9% |
| Extraneous Polymer | 1,017 | 1,013 | 4 | 1 | 25.0% | 2 | 50.0% |
| HEMA | 337 | 337 | 0 | - | - | - | - |
| Any of the four, no size flag at all | 4,494 | 3,739 | 755 | 243 | 32.2% | 385 | 51.0% |

The union row is additive: 3,739 flagged plus 755 with no flag equals 4,494. A picture flagged for one
class and untagged for another is outside the union row and fails both definitions.

Among the 755 union pictures, 370 carry a presentation tag, 339 Bubble Cluster, 76 Wet Package and 14
Surface Groove. The class rows overlap, so they do not add to the union.

Three definitions were open on 18 November. Two are settled: on 23 November the lead confirmed that
"FM and Debris" means all four size-flagged classes, and that a below-cut object of another debris
class is allowed in the strict PASS. Both are recorded with a recount in
`decisions/2026-11-23-fm-debris-scope.md`; on the frozen split 755 pictures carry one of the four
classes with no size flag at all, and 244 of them pass. Whether Surface Groove is a defect is still
open.

## Duplicate sensitivity

| Measure | All records | One copy per pair | Both copies excluded |
|---|---:|---:|---:|
| Annotation records | 13,682 | 13,678 | 13,674 |
| Labelled pictures | 13,677 | 13,673 | 13,669 |
| Pictures with an LP tag | 9,252 | 9,251 | 9,250 |
| Pictures with an OOI box | 10,032 | 10,028 | 10,024 |
| Pictures with both | 5,649 | 5,648 | 5,647 |
| Single label | 4,111 | 4,111 | 4,111 |
| Three labels | 2,756 | 2,754 | 2,752 |
| Four labels | 1,263 | 1,262 | 1,261 |
| Five labels | 716 | 715 | 715 |
| Six labels | 361 | 361 | 360 |

Only eight classes occur on the pair records: Bubble, Bubble Cluster, Fiber, HEMA, Foreign Matter,
Extraneous Polymer, Lens Rupture and Dirty Camera. Every other class is unchanged. The per-class deltas
are on the Duplicate sensitivity sheet.

Which copy matters for one pair only. Pairs 1, 2 and 4 carry the same classes in both records; box
counts differ (7/7, 24/23, 3/4). Pair 3 differs by Bubble Cluster: the longer record has it and six
labels, the shorter has five. Keeping the other copy moves Bubble Cluster by one and moves that picture
between the five and six label rows.

No duplicate decision has been made. The sensitivity sheet is the record of the alternatives.

## The four pairs and Clear

| Pair | Annotation file | Boxes A / B | Matched | Median IoU | Median shift | Largest shift |
|---|---|---|---:|---:|---:|---:|
| 1 | annotations_4521940.xml | 7 / 7 | 7 | 0.95 | 0.33 px | 4.2 px |
| 2 | annotations_4521947.xml | 24 / 23 | 23 | 0.88 | 0.35 px | 8.2 px |
| 3 | annotations_4521947.xml | 10 / 17 | 10 | 1.00 | 0.00 px | 16.0 px |
| 4 | annotations_4521992.xml | 3 / 4 | 3 | 0.84 | 0.95 px | 1.2 px |

Both records of every pair remain in the frozen set. Clear: 2,333 Clear-folder pictures, of which 2,291
were re-annotated (1,712 bubble boxes only, 255 another object, 324 a presentation tag) and 42 remain
Clear. The fall from 2,117 is a re-labelling, not a loss of pictures.

## Verification

`verify_frozen_workbook.py` recounts the label tables from the store on a separate code path and
compares them with the workbook. It checks every share against its own numerator and denominator, every
total against its parts, the three duplicate bases, the eight affected classes, the Clear block, and
that no share falls outside 0 to 1. A zero denominator must show "-", not 0%. 185 checks pass.

Two errors were caught and fixed while building this:

1. The union PASS row divided 243 passes by 1,037 pictures that were untagged for at least one class.
   That denominator included 282 pictures with a size flag on another class, which can never pass. The
   correct population is 755 pictures with no size flag at all; the share is 32.2%, not 23.4%.
2. HEMA has zero untagged pictures, and its pass share showed 0%. It now shows "-".

## Open

1. The four-pair decision: one copy per pair (and which copy), or exclude both copies. The workbook uses
   one copy as a working basis and shows all three bases.
2. Confirm that "FM and Debris" means Foreign Matter, Fiber, Extraneous Polymer and HEMA.
3. Confirm the strict PASS allows below-cut objects of the other debris classes and treats Surface
   Groove as a defect.
4. The 147 add-backs wait on client confirmation; 27 legacy pictures are discarded.
5. Job 4522010 is in the client table but not in the export. `F2_FOV` against the guide code `P2_FOV` is
   still a naming decision.
6. The crosswalk has no rows for EBC, TL, LR and Surface Groove.
7. The library tree and the two November uploads remain separate decisions.

No git commit has been made for any of this work.
