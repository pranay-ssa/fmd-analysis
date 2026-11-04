---
title: "Ticket 033: round 3, combined twenty-column head"
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/tickets/033-round3-combined.md
---
Type: task, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Does adding the object columns disturb the lens numbers that were reported in November?

## Spec

- One run: `--columns combined --gated-target <winner> --pos-weight <round-2 verdict>`.
- Pull to `run/multilabel_ooi_20261104/combined/`; same VM idioms as 029.
- The reference is the November 13-column run: macro AP judgeable 0.8182, and the
  per-class F1 at 0.5 table (MPP 0.991, ML 0.928, LOC 0.758, DC 0.188, NL 0.805,
  FL 0.415, LD 0.874, COC 0.833, object flag fires 98.3 percent on object-only pictures).

## Done when

Artifacts pulled and checked; lens-side numbers posted next to the November reference.
