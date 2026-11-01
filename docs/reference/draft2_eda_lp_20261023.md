---
title: "Draft-2 EDA part 1: Lens Presentation tags"
date: 2026-10-23
type: result
status: active
where: docs/reference/draft2_eda_lp_20261023.md
---

# Draft-2 EDA, part 1: Lens Presentation tags

## Revised 2026-10-28

Counts now come from the annotation of record, not the 6,785-row matrix. The annotation
re-export of 2026-10-26 did not touch any lens-presentation tag, so these numbers are the same
as the 2026-10-26 rebuild: Multiple Lens 1,439, Missing Primary Package 1,426, Lens Off Center
957, Dirty Camera 329, No Lens 325, Folded Lens 237, Low Dose 215, Cavity Off Center 184,
Dirty Strobe 43, View Obstructed 24, Bubble Scatter 6, Package Misalignment 2. Three cells in
the table below still read the matrix values (Lens Off Center 953, No Lens 323, Multiple Lens
1,433) and are superseded. The workbooks in `reports/draft2_eda_20261023/` are stale and will be
regenerated on the new annotation; the README beside them says which file is which.

Population: the frozen 6,785-picture label matrix (map tickets 019 and 020).
All counts are pictures. Draft 2 names and codes throughout. This is part 1
of 2; part 2 covers the Objects of Interest boxes
(`docs/reference/draft2_eda_ooi_20261023.md`).

## Per-tag picture counts (guide sections 4.1 to 4.15)

| Code | Name | Pictures | Share of 6,785 | Note |
|---|---|---|---|---|
| P1_MPP | Missing Primary Package | 1,426 | 21.0% | standalone, zero co-tags (ticket 023) |
| P1_PPM | Primary Package Misalignment | 2 | 0.03% | standalone; rarest live class |
| P1_COC | Cavity Off Center | 184 | 2.7% | standalone |
| P2_FOV | Field of View Obstructed | 24 | 0.35% | standalone; F2_FOV in production files, code question with the lead |
| P2_LOC | Lens Off Center | 953 | 14.0% | |
| P1_NL | No Lens | 323 | 4.8% | |
| P1_ML | Multiple Lens | 1,433 | 21.1% | largest live class |
| P1_FL | Folded Lens | 237 | 3.5% | co-tag rule with ML |
| P1_EBC | Edge Bottle-Capped | 0 | - | no annotated pictures yet |
| P1_TL | Torn Lens | 0 | - | no annotated pictures yet |
| P1_LR | Lens Rupture | 0 | - | no annotated pictures yet |
| P2_DS | Dirty Strobe | 43 | 0.63% | |
| P2_DC | Dirty Camera | 326 | 4.8% | |
| P2_BSC | Bubble Scatter | 6 | 0.09% | rare |
| P2_LD | Low Dose | 215 | 3.2% | |

## How often LP tags co-occur (pairs with at least one picture)

| Pair | Pictures |
|---|---|
| LOC + ML | 661 |
| ML + FL | 236 (guide co-tag rule) |
| LOC + FL | 148 |
| ML + DC | 104 |
| LOC + DC | 94 |
| DC + LD | 72 |
| LOC + LD | 17 (the guide's confused pair) |
| FL + DC | 21 |
| NL + DC | 4 |
| FL + LD | 4 |
| LOC + DS, ML + DS | 2 each |
| LOC + BSC | 1 |

## Tags per picture

| LP tags on one picture | Pictures |
|---|---|
| 0 | 2,732 (2,156 of these are Clear; 576 carry only OOI boxes or defect columns) |
| 1 | 3,181 |
| 2 | 641 |
| 3 | 216 |
| 4 | 14 |
| 5 | 1 |

4,053 of 6,785 pictures carry at least one LP tag.

## Clear namespace (separate, per the meeting)

2,156 Clear rows (Option A, applied 2026-10-23: Clear carries no other
label). The 10 Clear-folder pictures that carried only a Dirty Camera tag
were made Dirty Camera-only in matrix rev2; under the pre-Option-A matrix
they read Clear 2,166 / DC 326. Clear is a namespace of its own: no Clear
row carries any other label, and no labeled row is Clear.

## Legacy, kept separate under current codes (per the meeting)

- HEMA Obstruction (legacy P2_HMO tag, dropped in Draft 2): 86 pictures,
  own column, never merged into a Draft 2 class.

## Reading for the split decision (facts, not a decision)

- The live LP tag space is 11 classes, not 15: EBC, TL and LR have no data,
  and FOV has 24 pictures under a code the lead has not confirmed.
- Three tags sit under 10 pictures (PPM 2, BSC 6, FOV 24); their test-side
  counts at 70/30 will be 0 or 1 picture each, so their test metrics carry
  one-digit confidence.
- LOC and ML dominate and overlap heavily (661 pictures carry both), so any
  weighting that touches LOC moves a third of ML's positives with it.
