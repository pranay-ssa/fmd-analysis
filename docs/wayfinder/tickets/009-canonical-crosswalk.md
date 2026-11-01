---
title: "Ticket 009: canonical crosswalk across the three annotation vocabularies"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/009-canonical-crosswalk.md
---

# 009: Canonical crosswalk

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: nothing.

## Resolution (2026-10-15)

Done, after one correction. Record: `docs/reference/defect_crosswalk.md`.
Artifact: `data/crosswalk.csv`, md5 `a33b1d96d6fc1ac0021a8d1372f4d875`.

- 28 canonical rows: 12 box, 12 tag, 4 gate. Every code used on any shape in all
  9 files is present in its column: 10 in project 2, 20 in the Sep-22 project,
  24 in the production files, 0 missing.
- Both collisions are flagged and never merged: `P3_HE` (HEMA Fragment in the
  Sep-22 project, HEMA Obstruction in the production files) and `F2_FOV` against
  `P2_FOV` for View Obstructed.
- The four gate codes are asserted and checked as strict subsets of their base
  codes: FM 171 of 171, Fiber 136 of 136, Extraneous Polymer 33 of 33, HEMA 95
  of 95.
- Builder 10 self-checks, 0 failed. Verifier 32 checks, 0 failed, on an
  independent `iterparse` parsing route.

**Correction made before freeze.** The first build stated `kind = box` for HEMA
Obstruction. `P2_HMO` is a whole-image TAG with 174 instances in the Sep-22
project; only `P3_HE` in the production files is a box. A single `box` would have
moved tag instances into the box tier of every later count. The crosswalk now
carries the shape kind per source, plus `used_*` columns, and both the builder and
the verifier derive those from the exports rather than trusting the table, so the
same class of error fails a check. The row now reads `box|tag` with
`kind_conflict = yes`, and it is the only source-dependent row.

Also recorded: the production files hold 1,487 `<tag>` shapes, not the 1,318 in
`docs/cvat_production_20260925_pull.md`. The difference is 169, which is exactly
the net the newer files added (+118 Foreign Matter gate, +51 Fiber gate, +1
Extraneous Polymer gate, -1 Multiple Lenses). That reconciles the update.

**Waiting on:** the user's freeze from ticket 009's acceptance check 3, since
ticket 010 onwards are counting tickets.

## Question

What is one row per defect, mapping every code and every plain name across the
three annotation sources to a single canonical entry, with the collisions kept
visible rather than merged?

## Known collisions to carry

- `P3_HE` is HEMA Fragment (box) in the Sep-22 project and HEMA Obstruction
  (tag) in the 7 production files. One code, two meanings.
- View Obstructed is `P2_FOV` in the Sep-22 project and `F2_FOV` in the
  production files.
- `P2_HMO` and `P2_BSC` are used only by the Sep-22 project.
- `F2_FOV`, `P1_PPM` and the four `*_MICRON_THRESHOLD` codes are used only by
  the production files.
- The old library uses plain names and is the only source for Bubble On Edge and
  Bubble Over 123 Mark.

## Deliverable

`data/crosswalk.csv` plus `docs/reference/defect_crosswalk.md`: one row per
canonical defect, holding its code in each project, its plain library name, its
kind (box or tag), whether it is a size gate, and a flag column for collisions.

## Acceptance

1. Every code in every one of the 9 annotation files appears in the crosswalk,
   proved by a script that reads the files and diffs against the crosswalk.
2. Collisions are flagged, never merged, and each one names the client question
   it raises.
3. The crosswalk is frozen by the user before any counting ticket starts.
4. A verifier re-derives the code list from the XMLs independently of the
   builder.
