---
title: "Ticket 024 - Guide confusion table: what can be mislabeled as what"
date: 2026-10-22
type: task
status: done 2026-10-23
where: docs/wayfinder/tickets/024-guide-confusion-table.md
---

# Ticket 024: Guide confusion table

The Draft 2 guide states confusion and priority rules in text. Meeting
2026-10-22 asked for one table of them, to judge class balance and loss
weighting before the split.

## Question

Which class can be mislabeled as which other class, under what circumstance,
and why? Known examples in the guide: P1_COC vs P1_PPM (seating vs trigger
timing), P2_LOC vs P2_LD (lens movement vs low solution), P2_WP vs bubbles
(liquid gradient vs trapped air), uncertain Fiber/Extraneous Polymer defaults
to Fiber, Surface Groove vs Torn Lens vs Extraneous Polymer.

## Method

Read Draft 2 sections 3, 4 and 5 end to end. Extract every rule of these
forms: "commonly confused with", "do not apply when", "use instead",
"default to", "can be assumed". One row per rule. Record the guide section
for each row. Do not add confusions the guide does not state; model-observed
confusions are a separate, later source.

## Output

A table with columns: class, can be confused with, circumstance, guide
section, direction (one-way or two-way). Two companion columns: how often
each class occurs in our current labels, and whether the pair shares data in
our matrix. This turns the guide text into a balance and weighting input for
ticket 021.

## Feeds

Ticket 021: the class weighting and rare-column decisions.

## Resolution (2026-10-23)

The table is written: `docs/reference/guide_confusion_table_20261023.md`.
14 rules from Draft 2 (sections 1.3, 3, 4, 5), each with direction, guide
section, our matrix counts, and pair co-occurrence out of 6,785. Headline
pairs: WP 146 vs Bubble 862, 117 co-occur; LOC 953 vs LD 215, 17 co-occur;
ML and FL co-occur on 236 (a co-tag rule, not a confusion). Two non-target
look-alikes (Primary Package Marks, crater artifacts) recorded as systematic
false-positive sources for Fiber, FM and WP. Five Draft 2 classes (EBC, TL,
LR, SG, HEMA as P3_HE) have no pictures in our data yet. Numbers reported to
the user; the weighting decision stays with them.
