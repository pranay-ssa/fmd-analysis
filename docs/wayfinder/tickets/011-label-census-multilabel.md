---
title: "Ticket 011: resolved label census and multi-label analysis"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/011-label-census-multilabel.md
---

# 011: Resolved label census and multi-label analysis

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 010.

## Resolution (2026-10-15)

Done. Record: `reports/eda_full/label_census_20261015.md`.

- 20,014 shapes: 14,182 boxes and 5,832 tags. The two tiers are never pooled.
- Picture composition over the 4,782 pictures that carry a shape: box only 453, tag
  only 3,652, both 677.
- Codes per picture: median 1, mean 1.68, 90th percentile 4, maximum 11. 1,411
  pictures carry more than one canonical code, and that falls to a mean of 1.59 and
  a p90 of 3 once the four gate tags are folded into their base codes, which is the
  right way to read them.
- Top pictures by class: Multiple Lenses 1,439, Missing Primary Package 1,426, Lens
  Off Center 957, Bubble 819, Bubble Cluster 428. Top shape counts: Bubble 10,869,
  Missing Primary Package 1,551, Bubble Cluster 1,182.
- Top pairs: Lens Off Center with Multiple Lenses 664; Bubble with Bubble Cluster
  405; Bubble with Foreign Matter 276; Folded Lens with Multiple Lenses 236. Top
  triples: Bubble with Bubble Cluster and Foreign Matter 164.
- Gate subset property re-asserted: Foreign Matter 171 of 171, Fiber 136 of 136,
  Extraneous Polymer 33 of 33, HEMA 94 of 94.
- Library-only classes stay visible: Bubble On 123 at 13 pictures and 79 shapes,
  Bubble On Edge at 14 pictures and 90 shapes.
- 22 of the 28 classes are folder-derived; the six that are not are Folded Lens,
  Stretched Bubble and the four gate tags. That separation is stated rather than
  hidden.
- Builder 10 checks, verifier 48 checks, 0 failed. Every part sums to its whole on
  both picture and shape counts: 56 sums checked, 0 disagreements. Byte-identical
  rebuild.

## Question

Redo the multi-label analysis of the 2026-10-13 batch, at full coverage, on the
resolved labels: how many pictures carry each canonical defect, how many defects
sit on one picture, which pairs and triples recur, and how much of this is one
folder's label versus the annotator's own.

## What the 2026-10-13 run already did, to be reproduced at scale

- codes per image, the histogram and its median, mean and 90th percentile
- box-only, tag-only, both, and neither
- the most common code pairs
- the unlabelled picture, if there still is one

## Deliverable

- `run/eda_full_20261015/label_census.csv`: per canonical defect, its picture
  count and shape count, split by folder group and by production line.
- `run/eda_full_20261015/codes_per_image.csv` and `pairs.csv`.
- `reports/eda_full/label_census_20261015.md`: the written form, with the
  per-line table in it.

## Acceptance

1. Picture counts per defect agree with the per-line and per-folder-group tables
   they are split into.
2. The separation between box defects and tag defects is explicit, because the
   two tiers are annotated to very different depths.
3. The library-only classes are visible under their own names.
4. The four gate tags are reported as strict subsets of their base codes, and the
   subset relationship is asserted, not assumed.
5. The unannotated-or-empty picture count is stated.
