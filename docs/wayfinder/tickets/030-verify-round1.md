---
title: "Ticket 030: verify round 1 and record the verdict"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/tickets/030-verify-round1.md
---
Type: verification, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Do the saved scores reproduce every round-1 number, and which arm wins under the
pre-registered rule 2?

## Spec

- Recompute from each arm's predictions.npz with independent code: per-class AP, F1 at
  0.5 and at chosen cuts, macro over the seven supported classes. Both arms are scored
  against the SAME class-level test truth; an arm is never graded on its own target.
- Recall-by-flag per gated class for both arms; the gate arm's Foreign Matter recall
  ceiling is 0.643 (72 of 112 test pictures).
- Verdict per rule 2: higher macro AP wins; a tie or a gap within 0.005 resolves to the
  class arm. Record the verdict as the resolution on this ticket and as a comment on the
  map card, with the full comparison table.
- Tamper check: alter one cell of a copy of a metrics file and require the check to name it.
- If verification fails, block ticket 031 with the defect named instead of flowing forward.

## Done when

Every round-1 number is reproduced, the verdict is recorded, and ticket 031 is unblocked.

## Resolution (recorded 2026-11-04 by the round-1 verifier)

**Verdict under rule 2: the class arm wins round 2.** Macro average precision over the
seven supported classes on class-level test truth is 0.495537 for the class arm and
0.439136 for the gate arm. The gap is 0.056401, which is far outside the 0.005 tie band,
so the tie rule does not come into play and round 2 trains the class target. Rule 3 also
fired: on Fiber the class arm loses 0.107 F1 at the chosen cut (0.264 against 0.371), so
that drop is surfaced with the round-2 numbers and round 3 still runs.

### How the numbers were re-derived

Every figure below was recomputed from each arm's `predictions.npz` with code written
for this ticket. None of the trainer's functions were reused. The recomputed values match
`metrics.json` and `thresholds.json` field for field: to 1e-9 for AP, F1, precision,
recall, supports and macro values, and to 1e-6 for the recall-by-flag fields, which are
stored at six decimals. The 14 chosen cuts were re-selected from the validation split
with the November rule (grid 0.05 to 0.95 step 0.05, highest F1, ties to the higher cut,
guard of 10 validation positives) against class-level validation truth, and all 14 match
both saved files. The gate arm's cuts also come from class truth: gate-truth selection
would give Foreign Matter 0.95 instead of the recorded 0.15.

Shared-truth checks, all passed:
- The label table and the frozen split agree on the split label of all 7,470 rows, and
  the split file md5 is `1a71d66d2de384cf47a3fcf7d9115baa`.
- Both arms' `test_true` arrays are identical to each other and to the table's class
  columns, row for row, and both arms' gate arrays match the table's gate columns.
- Test positives 325 / 170 / 112 / 58 / 47 / 27 / 17; validation positives 326 / 170 /
  110 / 60 / 47 / 25 / 19; gated and un-gated test positives 72/40, 56/2, 17/0, 27/0.
- The Bubble/Cluster nesting reads 1,110 of 1,132 cluster pictures across the whole
  split, and 160 of 170 cluster pictures on the test side.
- Four of the five pulled artifacts per arm (metrics, thresholds, predictions, train log)
  are in the tree and md5-identical to the VM copies, and both run.json files are
  md5-identical to the VM copies. The fifth, `final.pt`, is missing locally; see the
  defect below.
- Git HEAD is unchanged at `5ab3467ff31b93870f6f50fde92f8eee67d9102c`; the only tracked
  edits in the tree are the two pre-existing ones (the index line for ticket 027 and
  ticket 027's own file) plus this ticket's resolution.

### Per-class comparison, class-level test truth, 1,121 test pictures

| Class | Support | Class AP | Gate AP | Floor | Class F1 @0.5 | Class F1 @cut (cut) | Gate F1 @0.5 | Gate F1 @cut (cut) |
|---|---|---|---|---|---|---|---|---|
| Bubble | 325 | 0.935 | 0.940 | 0.291 | 0.955 | 0.951 (0.20) | 0.943 | 0.943 (0.25) |
| Bubble Cluster | 170 | 0.656 | 0.611 | 0.152 | 0.575 | 0.679 (0.15) | 0.545 | 0.659 (0.20) |
| Foreign Matter | 112 | 0.545 | 0.462 | 0.107 | 0.286 | 0.560 (0.15) | 0.000 | 0.526 (0.15) |
| Fiber | 58 | 0.266 | 0.315 | 0.052 | 0.000 | 0.264 (0.25) | 0.000 | 0.371 (0.10) |
| Wet Package | 47 | 0.390 | 0.217 | 0.042 | 0.000 | 0.400 (0.15) | 0.000 | 0.306 (0.15) |
| HEMA | 27 | 0.569 | 0.448 | 0.021 | 0.000 | 0.567 (0.15) | 0.000 | 0.484 (0.10) |
| Extraneous Polymer | 17 | 0.109 | 0.082 | 0.019 | 0.000 | 0.149 (0.10) | 0.000 | 0.091 (0.10) |
| **macro over the seven** | | **0.4955** | **0.4391** | | **0.259** | **0.510** | **0.213** | **0.483** |

Every AP sits above its prevalence floor in both arms. The class arm is ahead on five of
seven classes; the gate arm is ahead on two: Bubble (by 0.005) and Fiber (by 0.049).

### Recall by flag, gated classes, at the chosen cut

Class positives split by the gate flag, both arms graded on class-level test truth:

| Class | Gated / un-gated n | Class arm gated / un-gated | Gate arm gated / un-gated | Class arm at 0.5 | Gate arm at 0.5 |
|---|---|---|---|---|---|
| Foreign Matter | 72 / 40 | 0.958 / 0.900 | 0.764 / 0.800 | 0.222 / 0.125 | 0.000 / 0.000 |
| Fiber | 56 / 2 | 0.286 / 0.500 | 0.875 / 1.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Extraneous Polymer | 17 / 0 | 0.529 / na | 0.118 / na | 0.000 / na | 0.000 / na |
| HEMA | 27 / 0 | 0.704 / na | 0.556 / na | 0.000 / na | 0.000 / na |

Class-truth recall at the chosen cut, whole class: class arm Foreign Matter 105/112
(0.938), Fiber 17/58 (0.293), Extraneous Polymer 9/17 (0.529), HEMA 19/27 (0.704); gate
arm 87/112 (0.777), 51/58 (0.879), 2/17 (0.118), 15/27 (0.556).

### Bubble/Cluster confusion at the chosen cut

Rows are the truth pair, columns the predicted pair, order both / bubble-only /
cluster-only / neither. Neither arm ever predicts a cluster without a bubble:

| Class arm | both | bubble-only | cluster-only | neither |
|---|---|---|---|---|
| both | 154 | 3 | 0 | 3 |
| bubble-only | 135 | 29 | 0 | 1 |
| cluster-only | 8 | 1 | 0 | 1 |
| neither | 10 | 10 | 0 | 766 |

| Gate arm | both | bubble-only | cluster-only | neither |
|---|---|---|---|---|
| both | 144 | 16 | 0 | 0 |
| bubble-only | 127 | 36 | 0 | 2 |
| cluster-only | 8 | 1 | 0 | 1 |
| neither | 12 | 16 | 0 | 758 |

The 0.5 confusion cells were recomputed as well and match the saved file for both arms.

### Corrections to the spec's expectations

1. **The 0.643 Foreign Matter figure is a share, not a ceiling.** The anchor reproduces
   exactly: 72 of 112 test Foreign Matter pictures carry the gate flag, 72/112 =
   0.642857. As an upper bound on the gate arm's measured recall it is wrong. At the
   chosen cut the gate arm recalls 87 of 112 class Foreign Matter positives (0.777),
   because it also catches 32 of the 40 un-gated positives (un-gated recall 0.800), and
   un-gated positives count as true positives on class truth. The 0.643 number holds only
   for a perfect gate scorer that never fires on an un-gated picture. The round-1 numbers
   themselves are unaffected: the parent report already read 0.764 / 0.800 by flag.
2. **AP definition.** The saved AP is the sum of precision at each positive rank. That
   implementation reproduces all 14 APs and both macro values to 1e-9. The tie-grouped
   variant of average precision differs by at most 0.0025 (largest single gap: the class
   arm on HEMA, 0.5663 against 0.5688) and moves the macro gap only from 0.056401 to
   0.056277, so the rule-2 verdict is the same under either definition.

### Tamper proof

The checker recomputes every metrics field from `predictions.npz` and exits non-zero
naming the cell that differs. Three runs:

- Untouched class-arm file: exit 0, every cell reproduces.
- Untouched gate-arm file: exit 0, every cell reproduces.
- Copy with `per_class.class_fiber.auprc` changed from 0.2658123958460663 to 0.315812:
  exit 1, failure names `per_class.class_fiber.auprc`.
- Copy with `bubble_cluster_confusion.at_chosen.neither.neither` changed from 758 to 751:
  exit 1, failure names `bubble_cluster_confusion.at_chosen.neither.neither`.

### Defect found: the model weights were never pulled

Round 1 reported "all five artifacts per arm pulled and md5-identical to the VM". Four
are true: metrics, thresholds, predictions and the train log sit in the tree for both
arms and their md5s match the VM copies exactly (class `34fd40f9` / `ce6d1560` /
`c6c66d1d` / `24be8221`, gate `8fec3bc0` / `1fdcf1f2` / `e7a915a5` / `1680aadc`), and
both run.json files match too (`864a8ea2`, `cfba1a10`). The fifth is not true. The VM
holds `final.pt` for both arms at 94,389,811 bytes with md5 `8b3fdd4d42a37ad1656fa0bbc1a4e1e9`
(class) and `0c4d366ac8d712e6e2c7de7ba62f3291` (gate), both matching the hashes round 1
recorded, but no `final.pt` exists anywhere in this repository (searched the whole tree
and the drive to depth 5). Each run.json points `artifacts.weights` at
`run/multilabel_ooi_20261104/<arm>/final.pt`, a path that does not exist locally, and
each run.json note claims the weights were pulled and md5-identical. That claim is
contradicted by the tree.

Disposition: this does not block ticket 031. Round 2 compares against the unweighted
twin through metrics, thresholds and predictions, all present and verified, and it does
not read the weights. The gap is a pull of two 94.4 MB files, not a number defect, so it
is tracked on its own card for the machine-learning runner instead of holding up the
round. Every round-1 number this ticket had to reproduce did reproduce, so the rule-2
verdict stands and ticket 031 unblocks.

### Hygiene

No credential patterns in the tracked diff, and none in the 17 untracked files (the
label table, the trainer and verifier scripts, and the round-1 run artifacts). The
verification scripts live in this task's scratch workspace, not in the repository, and
nothing was left behind in the tree.
