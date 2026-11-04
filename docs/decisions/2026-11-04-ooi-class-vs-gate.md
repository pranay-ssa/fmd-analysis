---
title: Object classes, not the size gate, and a pass/fail rule built on them
date: 2026-11-04
type: decision
status: active
where: docs/decisions/2026-11-04-ooi-class-vs-gate.md
---

# Object classes, not the size gate, and a pass/fail rule built on them

## Decision

The multi-label head trains on **object classes**, not on the micron size gate, with the loss
weighted by inverse training frequency, in one **nineteen-column** head that also carries the twelve
lens classes. The gate survives only as a reporting subset ("of which size-flagged"). Pass/fail is
computed from the same head: a picture fails if any fail-class column fires at its cut.

## Why the class labels

Round 1 trained two arms on identical truth, identical recipe, identical seed. Scored on class-level
test truth, the class arm wins by a margin no tie rule could absorb.

| Arm | Macro AP (7 classes) | F1 at cut |
|---|---|---|
| class labels | **0.4955** | 0.5100 |
| gate labels | 0.4391 | 0.4828 |

The gate arm's cost is real but narrower than predicted: Foreign Matter −0.083 AP, Wet Package
−0.173, HEMA −0.121. An earlier expectation that the gate would cap Foreign Matter recall at 0.643
was wrong: the gate-trained model scored 0.800 recall on un-gated test pictures, because it
generalises from gated examples to objects it was never labelled on. The gate costs ranking quality,
not coverage.

## Why the weight

The unweighted class arm left four classes near-useless at any sane cut. Inverse-frequency weight
on the training split only:

| | unweighted | weighted |
|---|---|---|
| Macro AP | 0.4955 | **0.6330** |
| Macro F1 at 0.5 | 0.2594 | 0.6143 |
| HEMA AP | 0.569 | 0.963 |
| Extraneous Polymer AP | 0.109 | 0.428 |
| Wet Package AP | 0.390 | 0.572 |
| Fiber AP | 0.266 | 0.345 |

Cost: Foreign Matter −0.016 AP, Bubble Cluster −0.025, both inside seed noise.

## Why one head

The combined head (twelve lens + seven object = nineteen trained columns; Surface Groove is zero
pictures and excluded) holds both jobs without either degrading. Object macro AP 0.6380 against
0.6330 without the lens columns; lens macro AP over the eight judgeable classes 0.8815 against the
November 0.8182, a gain of 0.063 that sits outside the pre-agreed 0.01 stability band and is
therefore reported as a move, not as stability.

## The pass/fail rule

A picture **passes** only if it is clear or carries nothing but Bubble and Bubble Cluster. Everything
else fails. Truth on the frozen split: 2,117 clear plus 196 bubble-only pass, 5,157 fail; test split
768 fail, 353 pass (317 clear, 36 bubble-only).

On the test split, at 0.5:

| Measure | Value |
|---|---|
| Fail pictures caught | 760 of 768 (98.96%) |
| Clear pictures passed | 316 of 317 |
| Clear wrongly failed | 1 |
| Bubble-only pictures passed | 8 of 36 |
| Pictures passed overall | 324 of 353 (91.8%) |

At the validation-chosen cuts: 759 caught, 1 clear wrongly failed, 9 of 36 bubble-only passed.

Under the same nineteen-column rule the November model catches 710 of 768 (92.4%) and wrongly fails
3 clear pictures, so the gain is on identical footing rather than a change of scope. The recorded
86.1 percent / 12 clear figure is a lens-only scope and is not comparable.

**Known weakness, accepted for now:** 28 of 36 bubble-only pictures are wrongly failed, 23 of them
because Foreign Matter fires and 11 because Fiber does. Bubble texture reads as small-particle
contamination. The fix is hard negatives drawn from bubble-only pictures, or a specificity term on
those two classes; it is the first experiment queued after this decision.

## Consequences

- The gate column stays in the label table as a subset (`gate_*`), never as a second class, and no
  run ever reads both groups for the same class.
- Surface Groove stays in the tables as a zero column and is excluded from every average. Any count
  that says twenty columns is wrong; nineteen are trained.
- Thresholds are chosen on validation only, grid 0.05 to 0.95, highest F1, ties to the higher cut.
  Cuts at 0.95 (HEMA, No Lens) sit on the grid boundary and need a 0.99 extension before they are
  quoted as maxima.
- Every number here is reproducible from `run/multilabel_ooi_20261104/{class,gate,class-posw,combined}/`
  and was re-derived independently by a verifier card per round.
