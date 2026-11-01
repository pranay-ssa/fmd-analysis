---
title: "Ticket 025 - Draft-2 EDA, two parts: LP tags and OOI boxes"
date: 2026-10-22
type: task
status: done 2026-10-23
where: docs/wayfinder/tickets/025-draft2-eda.md
---

# Ticket 025: Draft-2 EDA, two parts

Meeting 2026-10-22 asked for a fresh EDA under the Draft 2 guide and its
naming: 15 Lens Presentation tags and 8 Objects of Interest. Two separate
deliverables, one for LP, one for OOI.

## Question

What does the data at hand look like under the Draft 2 frame? Distributions,
counts, multi-label structure, and where the legacy classes sit.

## Scope rules

- Universe: the verified local label universe (the 10,614-contents picture
  set and the 6,785 usable pictures from the 2026-10-21 frame). No re-parse
  of raw XMLs unless a check fails.
- Draft 2 names and codes everywhere (P1_, P2_, P3_).
- Dropped and library-only classes stay IN the EDA but separate, under their
  current codes: Bubble On 123, Bubble On Edge, HEMA Obstruction (legacy
  tag), plus the frame's fold decisions (Bubble Irregular and Stretched
  Bubble into Bubble). Each carries its own column or section marked legacy,
  never merged into a Draft 2 class count.
- Part 1 (LP): per-tag picture counts, tag co-occurrence, standalone-tag
  overlap from ticket 023, Clear bucket reported as its own namespace.
- Part 2 (OOI): per-class box counts, boxes per picture, box count and
  geometry per class, legacy box classes listed separately.

## Output

Two docs plus two workbooks (or one workbook, two sheets), each
self-contained, numbers first. Report the numbers to the user as soon as
they are read; verification runs in parallel.

## Feeds

Ticket 021: the split is decided on this EDA.

## Resolution (2026-10-23)

Two docs + one workbook (two sheets), all verified against the computed
JSONs in run/draft2_eda_20261023/:

- Part 1 LP: docs/reference/draft2_eda_lp_20261023.md. 15 Draft 2 tags, 11
  with data (ML 1,433 and MPP 1,426 lead; PPM 2, BSC 6, FOV 24 trail),
  3 with no data (EBC, TL, LR). LP co-occurrence: LOC+ML 661, ML+FL 236.
  Tags per picture: 3,181 one, 872 two or more. Clear 2,166 separate,
  10 dual-tagged rows flagged. Legacy HEMA Obstruction 86 kept separate.
- Part 2 OOI: docs/reference/draft2_eda_ooi_20261023.md. Shape line 1,130
  pictures, 12,783 boxes, 79 percent Bubble (10,070 boxes, median 11 per
  picture, 6.6 x 6.4 px). Matrix subset 977 pictures. Legacy classes
  separate: BI 128, BST 7, On 123 79, On Edge 90 boxes. HEMA box median
  1,050 px wide (ring shape).
- Workbook: reports/draft2_eda_20261023/draft2_eda_20261023.xlsx, sheets
  "LP tags" and "OOI boxes". Verifier:
  experiments/multilabel_edge/verify_draft2_eda_workbook.py (0 mismatches
  against run/draft2_eda_20261023/*.json).
- CORRECTION (user question, 2026-10-23): the OOI table's Bubble row is the
  strict P2_BB count. Merged Draft-2 Bubble = union(BB, BI, BST) = 750
  pictures / 10,205 boxes on the shape line; every BI picture also carries
  P2_BB (containment, not addition). Matrix bubble column 862 = 750 + 112
  rescues. Doc, workbook notes and BI row updated; re-verified.
- CONSOLIDATED WORKBOOK (user-approved 9-sheet layout, 2026-10-23):
  reports/draft2_eda_20261023/EDA_Draft2_20261023.xlsx. Sheets: Summary,
  Class Summary, Tag Combinations, Objects, Standalone Tags, Confusion
  Risks, Earlier vs Current, Training and Test Split, Definitions. Spec
  builder build_eda_draft2_client_spec.py; verifier
  verify_eda_draft2_workbook.py recomputes every headline from the
  artifacts (0 failures; corrupted-cell proof caught a tampered cell).
- WORKBOOK IS READER-FACING (user direction 2026-10-23, rule now in
  AGENTS.md): no internal paths, script names, ticket ids or version tags;
  plain column headers that name their population; a definitions sheet; a
  "what this shows" line on each sheet; styled headers, frozen panes,
  autofilters and a summary chart. Internal builder and revision names live
  in this ticket instead.
- VERIFIER FINDING during that build: the "Full EDA vs Draft 2" Fiber-gate
  cell was first written as 137, which is the eligible count, not the matrix
  column. The matrix column is 168 = 137 true gate-tag pictures + 31 Fiber/
  EP flip rows (decision 12). The census 136 vs 137 eligible gap is the
  parked 137-vs-136 item and stays open.
