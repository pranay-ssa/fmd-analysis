---
title: "Ticket 015: coverage analysis"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/015-coverage.md
---

# 015: Coverage analysis

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 007, 009, 010.

## Resolution (2026-10-15)

Done. Record: `reports/eda_full/coverage_20261015.md`.

- Strata sum to the census on every cut: folders 4,230 plus 6,207 plus 177 equals
  10,614; folder groups 10,437 plus 177; lines 4,348, 972, 1,503, 1,637, 2,154.
  Every row names its population.
- **The 177 library-only pictures are restated with their classes:** Bubble 72, Wet
  Package 27, Bubble Irregular 26, Bubble Cluster 21, Bubble On 123 14, Bubble On
  Edge 14, Dirty Strobe 1, Fiber 1, Bubble Scatter 1. This reproduces the
  2026-09-17 published breakdown exactly.
- **The 113 figure did not reproduce, and the reason matters.** Re-derived three
  ways: content md5 over the whole library gives 279, content md5 over the production
  batch gives 129, basename over the production batch gives 114. The published 113 is
  the name-based batch route, and its breakdown matches with one cell moving (Wet
  Package against Clear is 32 now against 30). On the content-identity rule the
  overlap is LARGER, not smaller, because a name route cannot see renamed duplicates.
  The published figure is kept and labelled as the name-based figure it was, with the
  content figures beside it rather than replacing it.
- Blob coverage quoted once: 1,047 annotated of 10,438 in the production blob folder,
  10.03 percent. Nothing was pulled.
- **This ticket corrected the map.** The map said 5,832 pictures are "mentioned
  nowhere". 5,832 is the no-shape count. The genuine no-mention count is 3,924. Both
  figures are now named separately in the map and in every table.
- Builder 15 checks, verifier 35 checks, 0 failed. Byte-identical rebuild.

## Question

What is annotated out of what exists, by folder group, by production line and by
defect class, and where do the sources disagree about which folder a picture
belongs in?

## Sub-questions

1. Per library folder, how many pictures, and how many carry any label at all
   after resolution.
2. Per canonical defect, how many pictures are labelled and what share of the
   folder it nominally lives in.
3. The production overlap: the 1,047 pictures and the 1,047-collapsed-to-library
   match, stated by content hash.
4. The blob coverage line: 1,047 annotated of 10,438 in the production blob
   folder, 10.0 percent. Stated once, no pull.
5. The folder-label disagreement: the 113 pictures the three library folders
   label differently from each other, re-derived rather than quoted.

## Deliverable

- `run/eda_full_20261015/coverage.csv` plus the two existing workbook sheets it
  needs to match: the folder table and the per-class table.
- A coverage sheet in the final workbook, per ticket 017.

## Acceptance

1. The 113-figure and the 46-name overlap figures are re-derived, and any change
   from the published values is called out rather than quietly updated.
2. Coverage is stated as a ratio against the population it is measured in, and the
   population is named in the same sentence.
3. The library-only classes are included in the coverage tables.
4. Nothing here pulls from blob storage.
