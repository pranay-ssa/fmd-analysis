---
title: FM and Debris scope, and what strict PASS allows
date: 2026-11-23
type: decision
status: active
where: docs/decisions/2026-11-23-fm-debris-scope.md
---

# FM and Debris scope, and what strict PASS allows

## Decisions (lead, 23 November 2026)

1. **"FM and Debris" means the four size-tagged classes:** Foreign Matter, Fiber, Extraneous Polymer
   and HEMA. This confirms the class list already written in
   `2026-11-20-pass-fail-rule.md`. It is not a new rule.
2. **Strict PASS allows an untagged object of another debris class.** A picture passes when none of the
   four classes carries a size tag, even if a box of one of those classes is present. The pass holds
   only while the picture also carries no presentation tag, no Bubble Cluster and no Wet Package.

## Measured on the frozen split

The open doubt was that this case might not exist in the data. It does, and it is not rare. Counted on
the 13,631 pictures of the frozen split (`split.csv`), class columns from `labels_17.csv`, size flags
from `gates_4.csv`:

| Measure | Pictures | Train | Validation | Test |
|---|---:|---:|---:|---:|
| At least one of the four classes present, no size flag at all | 755 | 531 | 107 | 117 |
| ...and passes strict PASS: no presentation tag, no Bubble Cluster, no Wet Package | 244 | 175 | 37 | 32 |
| ...and carries no Bubble box either | 18 | 16 | 0 | 2 |
| At least one gated class untagged while another class carries a tag, so the picture still fails | 282 | 201 | 40 | 41 |
| At least one untagged gated instance, whether or not a tag is also set | 1,037 | 732 | 147 | 158 |

Untagged instances counted per class, over the whole split: Foreign Matter 966, Fiber 90, Extraneous
Polymer 4, HEMA 0.

Two things follow.

- The 244 passing pictures are 1.8 percent of the frozen split and 32 of them sit in the test split, so
  the strict rule changes the pass count, not only a rounding.
- The 18 pictures that carry no Bubble box still pass, because nothing on them fails. If an empty or
  Bubble-free object set should not pass, that needs a sentence in the rule.

The workbook's earlier 243 pass figure was counted on the EDA population of 13,677 labelled pictures.
This recount runs on the 13,631 split rows, so the one-picture difference comes from the population,
not from a rule change.

## Still open

- **Surface Groove.** 88 pictures carry it, it has no object boxes, and it is not one of the 17 columns.
  The pass/fail rule does not mention it, so under the current text a Surface Groove picture passes
  unless it also carries another fail class. The lead has not ruled on whether it is a defect.
- **The model limit still stands.** This run has no size output, so a predicted gated class is a
  predicted fail and only the truth uses the flag. The 244 figure is a truth-side count.
