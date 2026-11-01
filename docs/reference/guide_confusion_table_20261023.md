---
title: "Guide confusion table: what can be mislabeled as what"
date: 2026-10-23
type: result
status: active
where: docs/reference/guide_confusion_table_20261023.md
---

# Guide confusion table

Every confusion, priority and default rule stated in Draft 2 of the FMC
annotation guide (sections 1.3, 3, 4 and 5), one row per rule, with our
current per-class counts from the frozen 6,785-picture label matrix. The
purpose is the class balance and weighting decision before the split
(map ticket 024). The guide is the only source: no model-observed confusion
is in this table.

## Reading the columns

- Direction: one-way means the guide pushes one class toward the other as
  the default; two-way means the guide draws a boundary that cuts both ways.
- Co-occur: pictures carrying BOTH classes in our matrix, out of 6,785.
  Zero is a fact of our labels, not a guarantee for future labels.
- n1 and n2 are the two classes' picture counts in the matrix.

## Confusion and priority rules

| # | Class (n1) | Can be confused with (n2) | Circumstance and reason | Direction | Section | Co-occur |
|---|---|---|---|---|---|---|
| 1 | Cavity Off Center P1_COC (184) | Primary Package Misalignment P1_PPM (2) | Guide: commonly confused. Boundary is root cause: a correctly seated package with a trigger-timing framing shift is COC; a package not seated or positioned is PPM. Both are standalone tags (no co-tags allowed). | two-way | 4.3 | 0 |
| 2 | Lens Off Center P2_LOC (953) | Low Dose P2_LD (215) | Guide: commonly confused. If the lens only looks displaced because solution volume is low, it is LD; a true lens shift in a normally filled bowl is LOC. | two-way | 4.5, 4.15 | 17 |
| 3 | Wet Package P2_WP (146) | Bubble P2_BB (862) | Wet package artifacts resemble bubbles but are liquid, not trapped air: gradual intensity gradient, irregular non-uniform shape, usually near the package perimeter. | one-way (WP looks like Bubble) | 5.2 | 117 |
| 4 | Extraneous Polymer P3_EP | Fiber P3_FIB | One object can carry both traits (a strand plus a clump). Default when uncertain: FIBER. EP is reserved for confident polymer. | one-way default to Fiber | 5.4B | n/a (EP has no matrix column; its pictures sit in the plain-family gate rules) |
| 5 | Surface Groove P1_SG (no data yet) | Torn Lens P1_TL (no data yet) | A groove that opens into a visible tear, flap or opening becomes TL; a shallow surface defect without a tear stays SG. The lens remains intact for SG. | two-way | 5.3, 4.10 | 0 (no data) |
| 6 | Surface Groove P1_SG (no data yet) | Extraneous Polymer P3_EP | Raised or additional translucent material is EP; a groove is missing or displaced material. | one-way (SG looks like EP) | 5.3 | 0 (no data) |
| 7 | Torn Lens P1_TL (no data yet) | Lens Rupture P1_LR (no data yet) | TL keeps one connected structure; separation into pieces, or near-complete division, is LR. | two-way | 4.10, 4.11 | 0 (no data) |
| 8 | Edge Bottle-Capped P1_EBC (no data yet) | Torn Lens, Lens Rupture | EBC is edge deformation with a CONTINUOUS edge; a tear into the body is TL; separated material is LR. EBC may co-occur with other lens damage tags. | one-way (boundary outward) | 4.9 | 0 (no data) |
| 9 | Bubble Scatter P2_BSC (6) | Bubble P2_BB (862) and Bubble Cluster P2_BC (430) | Scatter is a TAG for a diffuse field of many small bubbles across a substantial area; discrete bubbles and touching groups are BOXES. A small number of isolated bubbles is never scatter. | two-way (tag vs box boundary) | 4.14, 5.1B | 0 with Bubble, 0 with Cluster |
| 10 | Dirty Strobe P2_DS (43) | Dirty Camera P2_DC (326) | Same cause, different focal plane: DS marks are diffuse, out of focus, and creep in from the edge; DC marks are sharp, defined, and can sit anywhere. | two-way | 4.12, 4.13 | n/a |
| 11 | No Lens P1_NL (323) | any lens-state class | NL requires a valid, centered, seated package AND confident absence of a lens. An obscured, folded, damaged or displaced lens goes to that class instead; poor image conditions go to an acquisition class. | one-way (NL is the last resort) | 4.6 | 0 with ML, 0 with FL |
| 12 | Multiple Lens P1_ML (1,433) | Folded Lens P1_FL (237) | Not a confusion: the guide says a folded lens in a multi-lens image gets BOTH tags, and large rupture sections force ML as well. | co-occurrence rule | 4.7, 4.8, 4.11 | 236 |
| 13 | Bubble P2_BB | Foreign Matter family | Guide default: anything that cannot be confidently identified as a Bubble is annotated as the most appropriate foreign matter class. | one-way default to FM | 1.3 | n/a |
| 14 | any uncertain defect | most appropriate class | Guide default: annotate uncertain defects with the most appropriate class; prioritize consistency over physical origin. | blanket rule | 1.3 | n/a |

## Non-target look-alikes (systematic false-positive sources)

The guide lists two features that closely resemble target classes but must
NOT be annotated. A trained model will still see them at inference, so they
cap achievable precision on the classes they resemble:

| Non-target feature | Resembles | Section |
|---|---|---|
| Primary Package Marks (fiber-like structures, recurring in the same position across a job) | Fiber, Foreign Matter | 3.1 |
| Crater-Like Bubble Artifacts (rings, depressions, shockwave patterns from bubble collapse) | Wet Package, Fiber, Extraneous Polymer, Foreign Matter | 3.2 |

## What this table says for balance and weighting (facts, not a decision)

- The largest guide-stated confusion pairs sit between classes of very
  different sizes: WP 146 vs Bubble 862 (117 pictures carry both), and
  LOC 953 vs LD 215 (17 carry both).
- PPM (2), Bubble Scatter (6), On 123 (13) and On Edge (14) stay rare. Any
  weighting choice on a confused pair also touches these, because PPM is
  the counterparty of COC and Scatter is the counterparty of Bubble.
- Five Draft 2 classes have no annotated pictures in our data yet: EBC, TL,
  LR, SG, and HEMA read as the single Draft 2 box class P3_HE. A weighting
  scheme that includes them can only be written once their data arrives.
- The four standalone tags carry zero co-tags (ticket 023), so their rows
  are structurally clean; they cannot soak up weight from a confused pair.
