---
title: "Ticket 023 - Standalone-tag audit: P1_MPP, P1_PPM, P1_COC, P2_FOV"
date: 2026-10-22
type: task
status: done 2026-10-23
where: docs/wayfinder/tickets/023-standalone-tag-audit.md
---

# Ticket 023: Standalone-tag audit

The Draft 2 guide is explicit (sections 4.1 to 4.4): when P1_MPP, P1_PPM,
P1_COC or P2_FOV is assigned, no additional tags or labels apply to that
picture. Meeting 2026-10-22 asked us to check the annotations we hold against
this rule.

## Question

In the newest annotations on hand (the 2026-09-22 updated project and the
2026-09-25 production pull), for each of the four standalone tags:

1. How many pictures carry the tag?
2. How many of those carry at least one MORE tag or box?
3. Which extra codes appear, and how many times each?

## Method

Count from the raw annotation files by CODE (P1_MPP, P1_PPM, P1_COC, P2_FOV,
F2_FOV), never by display name. Join by the three-step name match (as written,
score fields stripped, then date-time-line glob) with a unique-hit check.
Resolve the known collisions: P2_FOV vs F2_FOV naming anomaly, and the P3_HE
shared code (do not count a micron-gate tag as a second tag; the four gate
tags are size flags, count them in a separate column).

## Output

One table: rows = the four standalone tags, columns = pictures tagged,
pictures with extra labels, per-extra-code counts (gates listed separately).
Plus the picture-level violation list (name, standalone tag, extra codes).
Report the numbers to the user as soon as they are read.

## Feeds

The label matrix rule for ticket 021: if violations exist, the matrix needs a
stated policy (keep co-tags, or strip them per the guide).

## Resolution (2026-10-23)

Two independent derivations agree: the resolved line (one winning source per
picture) and the raw parse of all eight newer annotation files with every
source counted, names joined to content md5 (zero label-bearing unmapped
names). Result: **zero violations**. Every picture carrying a standalone tag
carries only that label.

| Tag | Pictures tagged | Pictures with any extra label |
|---|---|---|
| P1_MPP | 1,426 (raw 1,427; one name maps to two distinct contents) | 0 |
| P1_PPM | 2 | 0 |
| P1_COC | 184 | 0 |
| P2_FOV | 0 (defined in the Sep-22 project, never used) | 0 |
| F2_FOV | 24 (production code for the same class) | 0 |

Not even the four micron-gate tags co-occur with a standalone tag. The guide's
standalone rule holds in the data as delivered, so the label matrix needs no
co-tag policy for these four: keep them as-is. Artifacts:
`run/multilabel_edge_20261023/standalone_audit.json`,
`standalone_violations_resolved.csv` (empty),
`standalone_violations_raw.csv` (empty). Script:
`experiments/multilabel_edge/standalone_audit.py`.
