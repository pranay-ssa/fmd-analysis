---
title: "Map: multi-label Edge experiment - EDA, then train/test split"
date: 2026-10-21
type: protocol
status: active
where: docs/wayfinder/multilabel_edge_map.md
---

# Map: Multi-label Edge experiment - EDA, then train/test split

## Destination

One label matrix and one triple-checked EDA over the 10,614-picture universe
under the 2026-10-21 label frame (`docs/decisions/2026-10-21-multilabel-edge-frame.md`):
23 columns (5 defect boxes, Bubble Scatter, HEMA Obstruction legacy, 4 gate
classes, 11 presentation tags, Clear), the previous-name to new-tag change
table, the usable-picture count with the drop rule applied, the multi-label
distribution, and then a 70/30 train/test split built from that matrix with
its verifier. All local; the VM is read-only if needed (md5 proofs).

## Notes

- Base data: `run/eda_full_20261015/resolved_labels.csv` (winner-takes-all),
  `picture_table.csv` for the universe, `data/crosswalk.csv` for codes and
  the legend. Nothing here re-parses the raw XMLs unless a check fails.
- Draft 2 of the FMC Annotation Guide (`D:/FMD-KB/Annotation Guides/`) is
  authoritative for names and codes; its changelog is the source for the
  change table.
- Every doc carries the five-line header; `tools/index_docs.py` runs after
  doc changes. Pitfalls log: `docs/pitfalls.md`.
- Triple check = verifier with hand-typed expected values, byte-identical
  rerun, independent second derivation of every headline.
- Numbers go to the user the moment they are read; verification in parallel.
- Gates before the grill: the two fact finders still running (bubble census,
  Fiber/EP flip list) feed tickets 019 and 020 and must be reconciled against
  the frame before any table is published.

## Decisions so far

- 2026-10-21 grill, rounds 1 to 3: the full frame is frozen in
  `docs/decisions/2026-10-21-multilabel-edge-frame.md`. Highlights: gate IS
  the class for the four gated families; plain-family pictures without a gate
  drop out (345 measured); BI and BST fold into Bubble; Bubble On 123, Bubble
  On Edge and HEMA Obstruction stay as classes despite Draft 2 (discrepancy
  noted in the workbook); 70/30 two-way split, seed 42, md5 groups.
- 2026-10-22 meeting clarifications: the Draft 2 guide counts are 15 LP tags
  and 8 OOI box classes. P1_MPP, P1_PPM, P1_COC and P2_FOV are standalone
  tags (guide sections 4.1 to 4.4: no additional tags); the annotations must
  be audited against that rule (ticket 023). A picture in a Clear folder with
  no tags carries Clear as its tag; the model works with three namespaces:
  LP tags, OOI boxes, Clear (ticket 026). Dropped and library-only classes
  stay in the EDA but separate, under their current codes (ticket 025).
- [023 Standalone-tag audit](tickets/023-standalone-tag-audit.md): the rule
  holds. Two derivations (resolved line, raw parse of all eight newer files)
  agree: 1,426 MPP + 2 PPM + 184 COC + 24 F2_FOV pictures, zero pictures with
  any extra label, zero gate co-occurrence. No co-tag policy needed. The
  F2_FOV vs P2_FOV naming stays an open question (ticket 018, with the lead
  since 2026-10-23); working assumption until they answer: P2_FOV is the
  guide code and F2_FOV is the same class in the production files.
- [024 Guide confusion table](tickets/024-guide-confusion-table.md): 14
  rules extracted from Draft 2 into
  `docs/reference/guide_confusion_table_20261023.md`, each with our matrix
  counts and pair co-occurrence. Biggest pairs: WP-Bubble 117 co-occur,
  LOC-LD 17; ML-FL 236 is a co-tag rule. The weighting decision stays open
  for the user, fed to ticket 021.
- [026 Clear namespace](tickets/026-clear-namespace.md): frame matches the
  meeting rule on 2,156 of 2,166 Clear rows. ONE DIFFERENCE: 10 Clear-folder
  pictures carry only a Dirty Camera tag and are labeled Clear AND Dirty
  Camera (the builder never checks LP columns before granting Clear). Asked
  the user 2026-10-23; both readings shown in the EDA; 10 rows = 0.15
  percent, split not blocked.
- 2026-10-23 user decision, split label space narrowed: Draft 2 codes plus
  Clear only. On 123, On Edge and HEMA Obstruction excluded as classes;
  gate tags mark the four gated families. Universe 6,679 to 6,574 (105
  rows carried only excluded labels). Split v2: 4,572 / 2,002, fully
  verified. Record: docs/decisions/2026-10-23-split-label-space.md.
- 2026-10-23 user decision, Option A: Clear must be clear and carry no
  other label. Matrix rev2 (Clear 2,156; the 10 Clear+Dirty Camera rows are
  Dirty Camera-only), split v3 on it: 4,568 / 2,006, fully verified.
  Active artifacts: run/multilabel_edge_20261023/ + run/split_20261023_v3/.

## Ticket index

| Ticket | Type | Status | Blocked by |
|---|---|---|---|
| [019 Label matrix and change table](tickets/019-label-matrix-change-table.md) | task | done | - |
| [020 EDA report and workbook](tickets/020-eda-report-workbook.md) | task | done, user-accepted 2026-10-21 | - |
| [023 Standalone-tag audit](tickets/023-standalone-tag-audit.md) | task | done 2026-10-23 | - |
| [024 Guide confusion table](tickets/024-guide-confusion-table.md) | task | done 2026-10-23 | - |
| [025 Draft-2 EDA, two parts](tickets/025-draft2-eda.md) | task | done 2026-10-23 | 023 |
| [026 Clear as a third namespace](tickets/026-clear-namespace.md) | task | done 2026-10-23, one user question out | - |
| [021 Train/test split](tickets/021-train-test-split.md) | task | done 2026-10-23 (v2 supersedes v1 same day) | 023, 024, 025, 026 |
| [022 Verification gate](tickets/022-verification-gate.md) | task | open, split legs done; parked-item checks remain | 021 |

## Out of scope

- Training, architecture or any model run: this map ends at a verified split.
- Changing any source annotation, or re-annotating.
- The 2026-10-15 full-coverage EDA: its outputs are read-only inputs.
- Resolving the On 123 / On Edge and HEMA Obstruction discrepancies with the
  client: noted in the workbook, decided later.
