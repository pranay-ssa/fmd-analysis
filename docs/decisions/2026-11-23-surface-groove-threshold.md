---
title: Surface Groove is not a fail class until it clears the 200-picture cut
date: 2026-11-23
type: decision
status: active
where: docs/decisions/2026-11-23-surface-groove-threshold.md
---

# Surface Groove is not a fail class until it clears the 200-picture cut

## Decision (lead, 23 November 2026)

Surface Groove (`P1_SG`) is **not** a fail class today. It is an object class with 88 pictures in the
frozen export, below the 200-picture cut that already removed six classes as columns, so it is neither a
model column nor a fail condition.

The class is expected to be augmented to about the 200-picture mark. **When it clears that cut it becomes
a fail class**, on the same terms as the other object classes, and it takes a column. No new decision is
needed when that happens; the cut is the trigger.

## Verdict precedence, restated

- A picture fails if any fail condition is present, whatever else is on the picture. Fail dominates.
- A picture passes only when no fail condition is present.
- The pass conditions are a Bubble box, or an untagged size-gated class. Either one alone is enough.
- There is no third verdict, and no picture is unclassified.

Checked against the frozen split: 833 pictures pass (568 train, 117 validation, 148 test), and every one
of them carries a pass condition: 815 a Bubble box, 18 an untagged size-gated class. No picture in the
split has an empty mark set, so the rule has no gap to fill.

## What the ruling changes today

Nothing in the reported numbers.

- 88 pictures carry a groove: 61 train, 15 validation, 12 test.
- 87 of them already fail for another reason: a presentation tag, Bubble Cluster, Wet Package or a size
  tag. All 12 test pictures are in that group.
- One train picture depends on the ruling: one groove box, seven Bubble boxes, no tags. It passes today,
  and it will fail once Surface Groove is a fail class.

## Why the column cut does not soften the rule

Five of the six classes removed as columns are lens presentation tags, and presentation tags fail
regardless of whether they have a column. No verdict depends on them: every picture carrying one of them
also carries a kept class. So the cut removes model columns, not fail conditions.

## When the class clears the cut

- The label space goes from 17 columns to 18.
- The picture-level split can be reused if the picture set is not changed, because the split is by
  picture and seed, not by column.
- The model has to be retrained on the 18-column set. Results are not directly comparable with the
  17-column run, and the comparison should say so.
