---
title: Decks working folder and weekly cycle
date: 2026-11-05
type: reference
status: active
where: decks/README.md
---

# Decks working folder

## Current draft

`drafts/FMD_MultiLabel_2026W46_DRAFT.pptx` is the week-46 draft. It has 15 slides: a dark title, the
production rail, the nineteen-answer class-level screen, the object classes, the Bubble and Cluster
comparison, why classes rather than the size gate, one head with rare-class weighting, the AP chart,
the pass rule, the same-population pass result, the Cluster confusion cost, the 17-picture decision
table, the detector stage, the detector questions, and a dark closing. The PDF beside it is the review
copy; the spec and builder are in the same folder.

The wider Bubble + Cluster rule is compared on the same 353 pass candidates, not against the smaller
336 denominator. Experiment 2 numbers are not in the deck; the detector slides cover design and
expected questions only.

## Layout

- `drafts/` - the playground. Draft decks, their JSON specs, and scratch images live
  here. Nothing here is client-facing; it gets rebuilt into the office template.
- `weekly_decks/` - the presented decks, one per Monday, dropped in by Pranay after
  the presentation. Use these as the reference for tone and layout when drafting.
- `reference/` - extracted style notes and tokens from the presented decks. Reference only; no
  branding, logo or footer text goes into a draft.

## The weekly cycle (as run by Pranay)

1. Draft deck built in `drafts/` during the week, updated as work lands, so nothing
   is decided at the last moment.
2. Thursday evening: merged with Srikanth's part. He owns his slides, we own ours.
3. Friday: passed to the lead and higher-ups for proofreading. Changes come back as
   edits, which land in the draft.
4. Monday evening: presented. The final deck moves to `weekly_decks/`.

## Handoff rule

The draft deck is content and structure only. Pranay moves it into the office
template and fixes the layout himself, so the final deck reads as his own work.
Draft slides therefore carry the words and the numbers, not the branding.

## Style rules learned from the 2026-09-30 review

- The "how to read the results" slide read as AI-generated. Keep sentences short
  and direct, avoid stacked parallel bullet constructions, and put method
  explanations in speaker notes where they belong.
- Every number on a slide must be traceable to a repo doc (registry, run record or
  spec) before it enters a draft.
- Client commitments given verbally (e.g. the 5,000 annotated images, the edge
  pass/fail split from the URS) stay in speaker notes, marked unconfirmed, until
  the confirming email arrives.
