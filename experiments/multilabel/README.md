---
title: experiments/multilabel/ - the two-tier label space
date: 2026-09-21
type: protocol
status: active
where: experiments/multilabel/README.md
---

# experiments/multilabel/ - the two-tier label space

**Owner:** Pranay
**Scope:** the label space itself. What the data holds, how a picture with more than one label
is prepared, and how the results of such a run are read.
**Companion docs:** `reports/multilabel/MULTILABEL_STRATEGY_20260921.md` (the findings, the
options with costs, the pitfalls, the debt and the program). This README is the working protocol
for this folder.

## What is here

| File | Job |
|---|---|
| `two_tier_eda.py` | Measures the two-tier label space from the folder record and the box annotation file. Writes 11 CSVs plus a summary to `run/multilabel_eda/20260921/` |
| `verify_two_tier_eda.py` | Re-derives every published figure by a second route and diffs it. 102 checks, 0 failed. Exits non-zero on failure |

Run them in that order. Both are stdlib only and need no GPU.

## The rules this folder works to

1. **One label tier per model.** A frame-level tag goes to a classifier, an object-level label goes
   to a detector. A tag has never been given a box in this dataset (0 of the 2,020 boxes), because
   the annotation ran 10 tasks, one per box class.
2. **A picture with two labels is two rows in one file, never two copies of the picture.** The
   detection label file takes one row per object, and the class is per row. Duplicating a picture
   into two class folders doubles its weight in the loss and can move it across the split.
3. **No full-frame boxes for tags.** It teaches nothing about location, it covers real defects, and
   it enters the box metric.
4. **The split is built on the picture.** After two-tier preparation one picture appears in two
   inputs, and a per-class split can put it on both sides.
5. **The second label is recorded even when the arena uses one.** The drops are published in
   `run/multilabel_eda/20260921/3_dropped_labels.csv` so a later rule change can be evaluated on
   the same pictures.
6. **Never hand-type a number into a document or a registry row.** Read it from the script output,
   and check it with the verifier.

## What is measured, and what is not

Measured (2026-09-21, verified): the two tiers and their labels; 8,409 pictures; 6,243 with a tag,
2,179 with a box label, 13 with both; 55 pictures with two labels (0.65 per cent); the 42 two-box
and 13 tag-and-box shapes; the pair table; the 55 labels the single-label rule drops; the box tier
(435 images, 434 distinct pictures, 2,020 boxes, 0 pictures with two different box labels, 47
pictures whose second label the box file does not carry); the 10 annotation tasks; two labels with
no picture at all.

Not measured (recorded as debt in the strategy doc): whether any frame ever held two tags (the
folder layout is one label per folder, so the data cannot separate "never happened" from "never
recorded"); the size of the missing-box noise; the classifier's error split between naming and
recognition inside the debris family.

## Open decisions this folder is waiting on

1. Whether "Extraneous Polymer" and "Fiber" stay two classes. 33 of the 55 multi-label pictures are
   this one conflict, and the current rule trains 34 of the 36 Extraneous Polymer pictures as Fiber.
2. Whether the tag head replaces the 22-class head for the frame-level labels, or runs beside it.
3. Whether the client will confirm the tag tier was annotated as one tag per frame by design.

## Which comparison group each row belongs to

A number is only comparable with another number measured on the same pictures, the same test set and
the same settings. The registry records that group in its `arena` field, which is the schema's own
field name, so rows here read `data_arena`, `two_tier_tags` (the manifest and the tag head) or
`two_tier_production` (the cascade), or the group an existing run already sat in.
`debris_family_merge` uses `line_classifier_224` because it re-scores the per-line classifiers.
Numeric results stay comparable only inside one group, as `experiments/README.md` ADR-007 requires.
