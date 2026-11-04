---
title: "Ticket 035: pass/fail read and the point-4 workbook"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/035-pass-fail-and-workbook.md
---
Type: build, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

What does the agreed pass/fail rule do on the winning arm's test predictions, and can the
whole point-4 result be handed over in one verified workbook?

## Spec

- Rule, agreed 2026-11-04: a picture passes only if it is clear or carries nothing but
  bubble classes (Bubble, Bubble Cluster); everything else fails, including all twelve
  lens tags, Wet Package, Foreign Matter, Fiber, Extraneous Polymer, HEMA, Surface Groove
  and Bubble Scatter. Truth: 2,117 clear + 196 bubble-only pass, 5,157 fail (test 768/353).
  A picture fails if any fail-class column fires at its cut; the OR is the rule, not a
  second model.
- Report caught, clear passed, clear wrongly failed at 0.5 and at the chosen cuts, against
  the November reference (86.1 percent caught, 12 clear wrongly failed at 0.5).
- Workbook via a builder and an independent verifier that recomputes from the saved
  predictions and catches a tampered cell. Sheets: summary, object class table with the
  prevalence floors, thresholds with the guard, curves for the supported classes, the
  pass/fail table, definitions. Client-safe: no paths, no script names, no internal ids;
  every count names its population.
- Also report the recall-by-flag diagnostic (gated versus un-gated) for the four gated
  classes in the workbook's method notes.

## Done when

Verifier exits 0 with the tamper proof caught; the workbook is written under
`reports/multilabel_production/` beside the November one.
