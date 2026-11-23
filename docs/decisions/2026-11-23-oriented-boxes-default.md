---
title: Oriented boxes are the default for every box artefact
date: 2026-11-23
type: decision
status: active
where: docs/decisions/2026-11-23-oriented-boxes-default.md
---

# Oriented boxes are the default

## Decision

Every artefact that draws, measures or converts a box uses the oriented box: figures, IoU, object
size, label conversion, workbook columns. An upright footprint is a different measurement. It is
produced only on request and is labelled upright wherever it appears.

The lead asks for oriented boxes only.

## Why

CVAT keeps the base rectangle in `xtl, ytl, xbr, ybr` and the angle in `rotation`, applied about the
rectangle centre. About 95 percent of the boxes in this corpus carry an angle, so the upright
footprint is not the shape the annotator drew. For thin classes the upright footprint can be several
times the annotated area, which is what the lead saw as "boxes that look odd" on the duplicate-pair
sheets.

## Where it applies

- Figures of boxes on pictures: `experiments/annotations/draw_frozen_pairs_obb.py`, with the spin
  from `src/yolo_ooi/common.py`. Do not re-derive the sign by eye.
- IoU and match figures are polygon IoU on the oriented boxes. An upright-box IoU is not the same
  number on the same pair and is never presented as one.
- Object size and any micron figure use a rotation-invariant measure.
- Label conversion already writes OBB corners; keep it that way.

## Consequence for already published numbers

The duplicate-pair sheets were reissued on 2026-11-23. Their measured lines moved because polygon
IoU on oriented boxes is stricter than upright-box IoU on the same pairs: pair 1 0.95 to 0.93, pair 2
0.88 to 0.87, pair 4 0.84 to 0.80, pair 3 unchanged at 1.00. Quote the oriented figures.
