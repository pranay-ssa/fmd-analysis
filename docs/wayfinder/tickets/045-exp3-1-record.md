---
title: "Ticket 045: record Experiment 3.1 and rewrite the handoff"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/045-exp3-1-record.md
---
Type: docs, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

Is the pilot's result recorded so the next session can resume without re-deriving anything?

## Spec

- `docs/decisions/2026-11-16-exp3-1-size-gate.md`: the split rule and why it is a union, the two
  arms, the numbers, what is not comparable to Experiment 1 and why, and what was rejected.
  Status active.
- `docs/sessions/2026-W46.md`: append the Experiment 3.1 section, dated, with the counts and the
  run ids.
- `HANDOFF.md`: rewrite as state only. Resume point, what is in flight, what is next, the open
  question for the lead. Never append.
- Update the wayfinder map's status line and mark tickets 037 to 045 done in their own headers.
- Do not edit `docs/INDEX.md` by hand; the orchestrator regenerates it.
- Do not write to Notion and do not stage a `notiondocs.md` entry until the user marks the result
  verified.

## Done when

The decision file exists with the five-line header, the session doc carries the section, HANDOFF
is a rewrite, and the ticket headers say done. Report the three paths.
