---
title: Decision - Experiment B label frame and the HEMA code collision
date: 2026-10-15
type: decision
status: active
where: docs/decisions/2026-10-15-exp-b-label-frame.md
---

# Decision: Experiment B label frame and the HEMA code collision

Decided in the discussion phase on 2026-10-15.

## The frame

Experiment B uses exactly six classes, with the bubble family consolidated:

1. Bubble (consolidated) - plain Bubble, Bubble Cluster, Bubble Irregular,
   Bubble On Edge, Bubble On 123, Bubble Scatter merged.
2. Wet Package
3. Foreign Matter
4. Fiber
5. Extraneous Polymer
6. HEMA Fragment

## The HEMA reading

`P3_HE` collides across sources: it means HEMA Fragment in the Sep-22 project
but labels boxes in the 7 production files. Decision: the production `P3_HE`
boxes are HEMA Fragment. Verified counts:

- HEMA Fragment totals 102 pictures / 103 boxes (7 pictures / 8 boxes from the
  old sources, 95 pictures / 95 boxes from the production files).
- HEMA Obstruction (`P2_HMO`) has zero boxes in any source; it is tags only
  (86 distinct pictures after winner-takes-all) and stays out of the defect
  frame. It is LP-side metadata, not one of the six classes.

## The universe

- Defect-picture universe: 1,132 distinct pictures (teammate EDA reports 1,130;
  the delta of 2 is Foreign Matter 331 vs 330 and Wet Package 146 vs 147).
- The new production set contributes 758 defect pictures of its 1,047; the
  other 289 carry cavity-state tags (missing primary package, cavity
  off-center, view obstructed, package misalignment, missing lens, dirty
  camera) and sit outside the six classes.
- Consolidating the bubble classes changes the label frame only, not the
  picture set: every bubble-variant picture is already inside the union.

## Client email inputs carried into the experiment

- The 300 micron pass/fail threshold replaces 647 microns for debris; the
  client states their XMLs and micron-threshold tags are updated. Our derived
  cut is reported beside their tags, never instead of them.
- Ambiguous EP/Fiber cases are classified as Fiber, per the client's updated
  annotation guide. Note this shifts some old-vintage labels from EP to Fiber,
  so old-vs-new Fiber/EP counts are not directly comparable.

## Open questions

- Whether the 300 micron gate only filters pass/fail reporting or also drops
  sub-300 micron boxes from training.
- Whether the 289 cavity-state pictures stay in the training set as an
  out-of-frame bucket or drop out.
- Confirm the `P3_HE` reading with the client in ticket 018.
