---
title: "Ticket 036: documentation sweep"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/036-documentation-sweep.md
---
Type: docs, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Does the repo carry the whole point-4 trail without this session?

## Spec

- `docs/decisions/2026-11-04-ooi-class-vs-gate.md`: the class-versus-gate decision with
  the numbers that settled it, and the pass/fail rule with its truth counts.
- `docs/sessions/2026-W45.md`: the week's record, point 4 round by round.
- `HANDOFF.md` rewritten as state only; `docs/INDEX.md` regenerated with the tool, never
  by hand; `experiments/registry.json` regenerated from the run.json files.
- Map and tickets set to status done; the three fog items in the map reviewed: graduated
  into tickets if now specifiable, else left with a reason.
- `notiondocs.md` staged lines (draft, never pushed) for the round results.

## Done when

INDEX check passes, HANDOFF matches the artifacts on disk, and a fresh session could
resume from the repo alone.
