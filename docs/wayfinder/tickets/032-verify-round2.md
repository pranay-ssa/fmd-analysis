---
title: "Ticket 032: verify round 2 and record the weighting verdict"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/032-verify-round2.md
---
Type: verification, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Do the saved scores reproduce the weight-arm numbers, and does the weight earn its place
under the pre-registered rules 3 and 4?

## Spec

- Recompute from predictions.npz: per-class AP and F1 against the unweighted twin, macro
  over the seven supported classes, plus the pass/fail preview (caught, clear passed,
  clear wrongly failed at 0.5 and at chosen cuts) for both weightings.
- Rule 3 check: if the round-1 class arm dropped more than 0.03 F1 against the gate arm on
  Fiber, Extraneous Polymer or HEMA, surface that drop to the user in these numbers.
- Record which weighting proceeds to round 3; a tie resolves to the simpler unweighted run
  unless the weight lifts any supported rare class by 0.05 AP or more.

## Done when

Numbers reproduced, weighting verdict recorded, ticket 033 unblocked.
