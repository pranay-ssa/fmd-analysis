---
title: Pass/fail rule for the frozen run, with TA/FR/TR/FA labels
date: 2026-11-20
type: decision
status: active
where: docs/decisions/2026-11-20-pass-fail-rule.md
---

# Pass/fail rule for the frozen run, with TA/FR/TR/FA labels

## Decision

The workbook uses the URS labels **TA, FR, TR and FA** instead of TP, TN, FP and FN.

The pass/fail verdict is one per picture, under this rule and no other:

| Picture | Verdict |
|---|---|
| Clear | Outside this experiment (excluded) |
| Bubble only | Pass |
| Bubble Cluster | Fail |
| Any lens presentation tag | Fail |
| Wet Package | Fail |
| Size-gated class below the cut (untagged) | Pass |
| Size-gated class above the cut (tagged) | Fail |

The size-gated classes are Foreign Matter, Fiber, Extraneous Polymer and HEMA. Clear is excluded from
the frozen set, so it does not enter the counts.

Per class, the four counts are one-versus-rest: for that class, TA is class absent and predicted
absent; FR is class absent and predicted present; TR is class present and predicted present; FA is
class present and predicted absent. Each class row uses all 2,045 test pictures. These rows are not
additive across classes, because one picture can carry several classes.

The overall pass/fail block is a separate, picture-level 2x2. It is not the sum of the per-class rows.

## Why

The URS uses TA, FR, TR and FA, so the workbook uses the same letters to stay readable beside it.

Bubble is a pass condition. Bubble Cluster has no explicit pass instruction, so it fails. Clear was
already excluded from this experiment. A size-gated class is a pass when no size tag is set and a fail
when the tag is set. No second rule is applied.

## The model limit

This run predicts class presence, not size. A predicted size-gated class therefore counts as a
predicted fail; the size tag changes only the truth. The pass/fail block is an object-presence proxy
for the size rule, not a size-model verdict. A size specialist would be needed to read the size rule
directly.

## Consequences

- The workbook has a `Pass fail` sheet with the picture-level counts, TAR, TRR, FAR and FRR, the
  failure causes and the rule.
- The per-class sheet and the selected-threshold sheet use TA, FR, TR and FA.
- The 4 November decision's Bubble Cluster pass reading remains the historical Experiment 1 rule; this
  decision is the rule for the frozen run from 20 November.
- At 0.5, the frozen test gives TA 11, FR 137, TR 1,896, FA 1; TAR 7.4 percent, TRR 99.9 percent,
  FAR 0.1 percent, FRR 92.6 percent. These are object-presence results under the limit above.
