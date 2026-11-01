---
title: "Draft-2 EDA part 2: Objects of Interest boxes"
date: 2026-10-23
type: result
status: active
where: docs/reference/draft2_eda_ooi_20261023.md
---

# Draft-2 EDA, part 2: Objects of Interest boxes

Source: the resolved shapes line (one winning annotation source per picture,
run/eda_full_20261015/resolved_labels.csv), filtered to box shapes. Draft 2
names and codes throughout. Part 1 of this EDA covers the LP tags
(`docs/reference/draft2_eda_lp_20261023.md`).

## Revised 2026-10-28: annotation re-exported

The production annotation was re-exported by the client on 2026-10-26 and absorbed on
2026-10-28. The seven revised files hold the same 1,047 pictures; 133 were relabelled, mostly
folding Bubble Irregular and Stretched Bubble into Bubble at source. The counts below come from
`run/eda_full_20261028/resolved_labels.csv`. The detailed tables further down describe the
2026-10-15 run and are kept for provenance. The two workbooks in
`reports/draft2_eda_20261023/` are stale for the same reason and will be regenerated, not
patched; see the README beside them.

| Class | Pictures | Objects | Move |
|---|---|---|---|
| Bubble (merged) | 862 | 11,052 | +7 objects |
| Bubble Cluster | 427 | 1,183 | one picture fewer, one object more |
| Wet Package | 146 | 656 | six objects fewer |
| Foreign Matter | 326 | 620 | five pictures and six objects fewer; gate 166 |
| Fiber | 179 | 249 | one picture and four objects more; gate 137 |
| Extraneous Polymer | 144 | 150 | unchanged; gate 34 |
| HEMA (P3_HE boxes plus the four plain-name boxes) | 101 | 103 | unchanged |

Guide object classes total 1,103 pictures and 14,013 objects, unchanged in total: the moves
above cancel out. The three legacy classes stay outside that total: HEMA Obstruction tag 86
pictures, Bubble On 123 13, Bubble On Edge 14.

Populations, stated up front:

- Shape line: every picture in the resolved line with at least one box,
  1,130 pictures. This includes pictures the matrix drops (gate-less plain
  carriers), so detection-relevant boxes are not lost.
- Matrix: the subset of those pictures inside the 6,785-row matrix, 977
  pictures.

Geometry columns are the axis-aligned extents of the oriented boxes (width
and height of the box's own frame), so rotation is preserved in the source
but the medians below read as object size, not orientation.

## Draft 2 box classes (the 8)

CORRECTION 2026-10-25: the first version of this table counted only shapes
whose class string is already a guide code, so the older library's plain class
names (Bubble 799, Bubble Cluster 112, Wet Package 69, Foreign Matter 47,
Fiber 22, Extraneous Polymer 1, Bubble Irregular 41, HEMA Fragment 4) never
reached a class row, while the picture column (taken from the matrix) did
include them. The table below counts every box in the resolved line once, with
those names folded into their guide class, so both columns use one rule. The
geometry columns are still computed on guide-coded boxes only and are marked
as such.

| Code | Class | Pictures carrying (all objects) | Objects marked (all) | Guide-coded objects only | Pictures, coded only | Boxes/picture median (max), coded only | Size median w x h px, coded only |
|---|---|---|---|---|---|---|---|
| P2_BB | Bubble (merged: BB + BI + BST + older names) | 862 | 11,045 | 10,205 | 750 | 11 (67) | 6.6 x 6.4 |
| P2_BC | Bubble Cluster | 428 | 1,182 | 1,070 | 406 | 2 (19) | 11.6 x 10.6 |
| P2_WP | Wet Package | 146 | 662 | 593 | 122 | 3 (91) | 31.8 x 21.9 |
| P1_SG | Surface Groove | 0 | 0 | 0 | 0 | - | no data |
| P3_FIB | Fiber | 178 | 245 | 223 | 156 | 1 (8) | 27.4 x 16.9 |
| P3_EP | Extraneous Polymer | 144 | 150 | 149 | 143 | 1 (2) | 177.1 x 183.4 |
| P3_HE | HEMA | 101 | 103 | 99 | 97 | 1 (2) | 1,050 x 609 |
| P3_FM | Foreign Matter | 331 | 626 | 579 | 287 | 1 (48) | 10.7 x 10.3 |

- 14,013 objects in the eight Draft 2 classes; the two reference classes add
  169 (Bubble On 123 79, Bubble On Edge 90), so all box shapes in the archive
  total 14,182 on 1,130 pictures. 79 percent of the eight-class objects are
  Bubble (11,045 of 14,013).
- The correction adds 1,095 objects on 229 pictures that the first table never
  attributed, plus the objects those pictures carry in plain-name form
  (Bubble 840 including 41 Bubble Irregular, Bubble Cluster 112, Wet Package
  69, Foreign Matter 47, Fiber 22, Extraneous Polymer 1, HEMA Fragment 4).
- Reply convention (2026-10-26): the 32 objects delivered as Extraneous
  Polymer keep the earlier name Fiber in the review reply, so the columns agree
  with the onboarding report (Fiber 277 objects / 210 pictures, Extraneous
  Polymer 118 / 112). The annotation reading stays 245 / 178 and 150 / 144, as
  in the table above; the next annotation uses the newer name.
- HEMA is now 103 objects on 101 pictures: 95 production P3_HE boxes, 4 Sep-22
  P3_HE boxes (both named HEMA Fragment there) and 4 older-library HEMA
  Fragment boxes. The whole-image tag HEMA Obstruction (P2_HMO, 86 pictures)
  remains a separate legacy row and is not an object class.
- Bubble is small (median 6.6 x 6.4 px, p95 under 19 px) and dense: 735 of
  746 P2_BB pictures carry more than one box.
- THE MERGED BUBBLE CLASS, stated exactly (user question 2026-10-23): the
  guide-coded union of BB + BI + BST is 750 pictures and 10,205 box instances
  (10,070 + 128 + 7); folding the older library's plain names (Bubble 799,
  Bubble Irregular 41) gives the all-object row above: 862 pictures and
  11,045 objects. The matrix "bubble" column is also 862 pictures. Use 862
  for the classification matrix and the split.
- HEMA boxes are the outliers in size: median width 1,050 px on a 2,448 px
  frame, consistent with the ring-shaped demold residue the guide describes.
- Draft 2 HEMA is one class; our data holds it as three strands: 95
  production P3_HE boxes, 4 Sep-22 P3_HE boxes (named HEMA Fragment there)
  and 4 older-library HEMA Fragment boxes. All 103 are in the P3_HE row
  above; the older-library name is folded in by the 2026-10-25 correction.
  HEMA Obstruction P2_HMO stays a separate legacy TAG (86 pictures) and is
  never counted as an object.

## Legacy box classes, kept separate under current codes (per the meeting)

| Class | Pictures | Box instances | Boxes/picture median (max) | Size median w x h px | Note |
|---|---|---|---|---|---|
| Bubble Irregular P2_BI | 108 | 128 | 1 (3) | 25.9 x 23.9 | folds into Bubble; CONTAINED in the 746: every BI picture also carries P2_BB. The older library adds 41 boxes on 39 pictures under the same name, also folded into Bubble |
| Stretched Bubble P2_BST | 6 | 7 | 1 (2) | 100.9 x 22.2 | folds into Bubble; code question open with the client |
| Bubble On 123 | 13 | 79 | 4 (13) | 5.2 x 5.5 | library-only, no Draft 2 code |
| Bubble On Edge | 14 | 90 | 5 (17) | 8.7 x 10.4 | library-only, no Draft 2 code |

## Reading for the split decision (facts, not a decision)

- The classification matrix holds Bubble, Cluster and Wet Package as
  picture columns (862, 430 and 146 pictures there; higher than the shape
  line because older-file labels rescue Clear-folder pictures into the
  matrix). Fiber, EP, FM and HEMA live in the plain family: they enter the
  matrix only through their micron-gate columns (168, 33, 171 and 94).
- Object totals, corrected: 14,013 objects in the eight Draft 2 classes and
  169 in the two reference classes, 14,182 in all. The superseded figures were
  12,783 (guide-coded, eight classes) and 13,087 (adding the legacy rows); both
  omitted the older library's plain-name objects. Never quote 12,783 or 13,087
  as "all boxes".
- For detection-style use, the shape line is the honest population: 1,130
  pictures with boxes, Bubble-dominated, with EP (67 of 143 in matrix) the
  class most thinned by the matrix drop rule.
- The reference classes total 141 pictures and 304 guide-coded boxes (Bubble
  Irregular 128 + Stretched Bubble 7 + On 123 79 + On Edge 90); they stay out
  of the Draft 2 class counts but remain listed here under their own codes. In
  the all-object reading, Bubble Irregular and Stretched Bubble are already
  inside the merged Bubble row and only On 123 / On Edge sit outside the eight
  classes.
