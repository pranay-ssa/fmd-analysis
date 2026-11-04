---
title: "Ticket 030: verify round 1 and record the verdict"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/030-verify-round1.md
---
Type: verification, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Do the saved scores reproduce every round-1 number, and which arm wins under the
pre-registered rule 2?

## Spec

- Recompute from each arm's predictions.npz with independent code: per-class AP, F1 at
  0.5 and at chosen cuts, macro over the seven supported classes. Both arms are scored
  against the SAME class-level test truth; an arm is never graded on its own target.
- Recall-by-flag per gated class for both arms; the gate arm's Foreign Matter recall
  ceiling is 0.643 (72 of 112 test pictures).
- Verdict per rule 2: higher macro AP wins; a tie or a gap within 0.005 resolves to the
  class arm. Record the verdict as the resolution on this ticket and as a comment on the
  map card, with the full comparison table.
- Tamper check: alter one cell of a copy of a metrics file and require the check to name it.
- If verification fails, block ticket 031 with the defect named instead of flowing forward.

## Done when

Every round-1 number is reproduced, the verdict is recorded, and ticket 031 is unblocked.
