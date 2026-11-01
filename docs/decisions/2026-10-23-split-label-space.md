---
title: "Decision: split label space is Draft 2 codes plus Clear only"
date: 2026-10-23
type: decision
status: active
where: docs/decisions/2026-10-23-split-label-space.md
---

# Decision: split label space is Draft 2 codes plus Clear only

Decided by the user on 2026-10-23, revising the split of ticket 021.

## The decision

1. The split stratifies ONLY on classes that exist in the Draft 2 guide,
   plus Clear. Everything else is out of the label space.
2. Excluded as classes: Bubble On 123, Bubble On Edge, HEMA Obstruction.
   They were kept in the EDA as separate legacy columns (meeting 2026-10-22)
   but never enter the split or the training classes.
3. For the four gated plain families (Foreign Matter, Fiber, Extraneous
   Polymer, HEMA) only pictures carrying the specific micron-gate tag count
   as that class. This is how the matrix columns already work; restated here
   so no later reading widens it back.
4. The merged Bubble class stands as decided on 2026-10-21: Bubble Irregular
   and Stretched Bubble fold into Bubble (measured 2026-10-23: all 108 BI
   pictures also carry P2_BB, so the fold adds only 4 BST-only pictures to
   the shape line; 746 strict-code becomes 750 merged, 862 in the matrix
   with rescues).

## Measured effect

- Eligible universe: 6,679 to 6,574. The 105 dropped rows carried ONLY
  excluded-class labels: 78 HEMA-obstruction-only, 13 On-123-only,
  14 On-Edge-only.
- 8 surviving rows also carry an excluded label; they stay and the excluded
  label is ignored.
- Split v2: 4,572 train / 2,002 test, seed 42, recipe unchanged.
  Artifacts: run/split_20261023_v2/, builder
  experiments/multilabel_edge/build_split_v2.py, verifier
  experiments/multilabel_edge/verify_split_v2.py (hand-typed expected
  values, independent second derivation, byte-identical rerun, corrupted-
  input proof - all pass). Split v1 is superseded but kept on disk.
