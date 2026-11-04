---
title: "Ticket 031: round 2, class-weight arm on the round-1 winner"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/tickets/031-round2-pos-weight.md
---
Type: task, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Does the per-class weight (N - n) / n lift the rare object classes without wrecking
precision, on the target that won round 1?

## Spec

- One run: `--columns ooi --gated-target <round-1 winner> --pos-weight on`, weights computed
  on the training split only, recorded in run.json.
- Pull to `run/multilabel_ooi_20261104/<winner>-posw/`; same VM idioms and checks as 029.
- The comparison twin is the round-1 winner arm (same target, unweighted), so nothing is
  retrained here.

## Done when

Artifacts pulled and checked; numbers posted: per-class AP and F1 against the unweighted
twin, with the rare classes (HEMA 0.021, Extraneous Polymer 0.019, Wet Package 0.042
floors) called out.
