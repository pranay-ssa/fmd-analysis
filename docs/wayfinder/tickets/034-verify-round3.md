---
title: "Ticket 034: verify round 3 and the lens-stability check"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/034-verify-round3.md
---
Type: verification, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Are the combined-run numbers real, and did the lens head hold still?

## Spec

- Recompute from predictions.npz: the seven object classes as in 030/032, and the twelve
  lens classes against the November reference. Stability statement: judgeable macro AP
  within 0.01 of 0.8182 counts as held; anything beyond is reported as a move, not buried.
- Cross-check the object columns of the combined head against the round-2 winner's
  object-only scores on the same test pictures; large drift is reported.
- Record the verdict; also record the recommendation on retiring or keeping the single
  object flag (map fog item), for the user to decide.

## Done when

Numbers reproduced, stability statement recorded, ticket 035 unblocked.
