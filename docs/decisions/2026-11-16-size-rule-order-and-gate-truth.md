---
title: Rule order and size truth for the Experiment 1 redo
date: 2026-11-16
type: decision
status: active
where: docs/decisions/2026-11-16-size-rule-order-and-gate-truth.md
---

# Rule order and size truth for the Experiment 1 redo

Two changes, recorded together because they land in the same pass/fail number.

## 1. Rule order

The two rules were both counted in Experiment 1 and have not changed. What changed is which one
leads.

- **Primary (new order, client and lead feedback):** pass = Clear, Bubble, and untagged pictures of
  the four size-flagged classes. Bubble Cluster fails. Everything else fails.
- **Secondary (the position held from 4 November):** the same, with Bubble Cluster moved to the
  pass side.

Both are computed by one implementation and reported primary first. No numbers are recomputed for
Experiment 1; the earlier counts stand and the order is a presentation change.

## 2. Size truth for the four gated classes

In Experiment 1 the four gated classes failed on class presence. In the redo they fail on the size
flag, so a Foreign Matter object below the cut passes. An untagged picture passes on that class
and only that class; a lens condition or Wet Package still fails it.

This is the only arithmetic change against Experiment 1. In the redo it moves exactly two pictures
from fail to pass on the 1,121 test pictures.

## 3. Shape of the redo

Two specialists, combined at the verdict:

- The condition model reads the twelve lens conditions plus Bubble, Bubble Cluster and Wet Package,
  on the frozen picture assignment.
- The size model reads the four gated classes, trained on size-tagged pictures only, tested on
  untagged ones plus a small tagged guard.

The picture assignment is carried over so the lens results compare with Experiment 1. No Experiment
1 checkpoint is read.

## Result of the two changes

On the same 1,121 test pictures as Experiment 1:

| Step | Fail pictures | Pass pictures |
|---|---|---|
| The earlier reading, object present is enough to fail, measured with the same two models | 768 | 353 |
| After the size correction (secondary rule) | 766 | 355 |
| After the new order (primary rule) | 784 | 337 |

The 768 matches the Experiment 1 number exactly, so the two changes are measured from a known
starting point. The size correction accounts for 2 pictures and the order for 18.

Caught 778 of 784 (99.2%), passed 311 of 337 (92.3%) under the primary rule. Under the primary
rule the Bubble Cluster column drives 15 of the 26 wrongly failed pictures; under the secondary
rule the Foreign Matter size call drives 17 of 30.

## What this does not decide

Whether the pass set is client-confirmed. The order is a working reading taken from the lead's
feedback, and it is reversible: swapping the two rule identifiers changes the headline back without
re-running anything.
