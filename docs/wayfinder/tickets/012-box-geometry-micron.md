---
title: "Ticket 012: box geometry and micron distributions"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/012-box-geometry-micron.md
---

# 012: Box geometry and micron distributions

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 010, 013.

## Resolution (2026-10-15)

Done. Record: `reports/eda_full/box_geometry_20261015.md`.

- 14,182 boxes over 1,130 distinct pictures; 5,832 tags excluded. Every box appears
  exactly once.
- Axis-aligned share: 660 of 14,182 = 4.65 percent. All 660 carry an absent rotation
  attribute, none an explicit zero. 13,522 are rotated, so a conversion that assumes
  axis-aligned rectangles mis-draws 95 percent of the set.
- **The cavity was measured on the whole census, not just the production batch**:
  10,470 of 10,614 pictures measured, 144 unmeasurable in one named class,
  `low_bright` (dark or obstructed frames). The 2026-10-13 cavity file covered only
  1,016 of the 1,047 production pictures and none of the library.
- Size medians in pixels: Bubble 9.30, Foreign Matter 19.03, Fiber 46.03. Updated
  group 10.26 against Library 12.20. Lines L24 to L31 span 10.12 to 15.16 px.
- The `P3_HE` caveat is carried into the record: its combined median is 1,208.29 px,
  which is 1.54 times the 783.8 px lens diameter, so those boxes are region
  annotations and not defect spots.
- Every micron figure appears at both candidate scales side by side, with the pixel
  columns primary, per ticket 013a's finding that the two scales are not separable.
- Verifier 31 checks, 0 failures, plus 12 read-back checks on the VM through an
  independently written cavity routine with 0 disagreements. Byte-identical rebuild.

## Question

What are the box size distributions, in pixels and in microns, per canonical
defect, per folder group and per production line, and how many boxes sit outside
the cavity?

## Carried forward from the 2026-10-13 run

- the rectangle diagonal `sqrt(w^2 + h^2)` as the size measure, because it is
  invariant to the rotation attribute that 95 percent of boxes carry
- the cavity measured per image rather than assumed, since the cavity centre sits
  a median 96 px off the image centre
- the per-code share of boxes whose centre falls outside the cavity
- the note that `P3_HE` boxes are region annotations, not defect spots, and must
  not be read as detector targets

## Deliverable

- `run/eda_full_20261015/box_sizes.csv` and `cavity_geometry.json`.
- `reports/eda_full/box_geometry_20261015.md`, with the micron columns stated
  against both candidate scales and the scale named in every table.

## Acceptance

1. Every micron number names the scale it was computed at, and the two candidate
   scales are carried side by side rather than one being chosen silently.
2. Rotation is handled explicitly, and the number of boxes that are axis-aligned
   is reported.
3. The cavity measurement covers every image the method can measure, and the
   images it cannot are counted and named as a class, not dropped.
4. The `P3_HE` region-annotation caveat is carried into the report, not left in a
   ticket.
5. Distributions are reported at p25, p50 and p75 at minimum, never as a single
   mean.
