---
title: "Ticket 032: verify round 2 and record the weighting verdict"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/tickets/032-verify-round2.md
---
Type: verification, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Do the saved scores reproduce the weight-arm numbers, and does the weight earn its place
under the pre-registered rules 3 and 4?

## Spec

- Recompute from predictions.npz: per-class AP and F1 against the unweighted twin, macro
  over the seven supported classes, plus the pass/fail preview (caught, clear passed,
  clear wrongly failed at 0.5 and at chosen cuts) for both weightings.
- Rule 3 check: if the round-1 class arm dropped more than 0.03 F1 against the gate arm on
  Fiber, Extraneous Polymer or HEMA, surface that drop to the user in these numbers.
- Record which weighting proceeds to round 3; a tie resolves to the simpler unweighted run
  unless the weight lifts any supported rare class by 0.05 AP or more.

## Done when

Numbers reproduced, weighting verdict recorded, ticket 033 unblocked.

## Resolution (2026-11-04, ticket 032)

Verified with code written for this check only (no trainer code imported). Every recorded
field in all three arms' metrics.json and thresholds.json was recomputed from
predictions.npz: 135 comparisons, 0 failures. Artifacts match the round-2 worker's md5s
locally and on the VM (all six files, both ends, identical); the round-1 twin's four files
match ticket 030's recorded md5 prefixes. Both run folders hold exactly six files.

### Per-class numbers (weight arm vs unweighted twin, class-level test truth, 1,121 pictures)

| Class (floor) | AP weight / twin | F1 at 0.5 weight / twin | F1 at cut weight / twin | Cut weight / twin |
|---|---|---|---|---|
| Bubble (0.291) | 0.9646 / 0.9348 | 0.948 / 0.955 | 0.949 / 0.951 | 0.10 / 0.20 |
| Bubble Cluster (0.152) | 0.6308 / 0.6560 | 0.651 / 0.575 | 0.677 / 0.679 | 0.20 / 0.15 |
| Foreign Matter (0.107) | 0.5284 / 0.5446 | 0.562 / 0.286 | 0.567 / 0.560 | 0.15 / 0.15 |
| Fiber (0.052) | 0.3454 / 0.2658 | 0.372 / 0.000 | 0.390 / 0.264 | 0.35 / 0.25 |
| Wet Package (0.042) | 0.5722 / 0.3901 | 0.538 / 0.000 | 0.554 / 0.400 | 0.55 / 0.15 |
| HEMA (0.021) | 0.9625 / 0.5688 | 0.839 / 0.000 | 0.906 / 0.567 | 0.95 / 0.15 |
| Extraneous Polymer (0.019) | 0.4275 / 0.1086 | 0.390 / 0.000 | 0.421 / 0.149 | 0.55 / 0.10 |

Macro over the seven supported classes: AP 0.6330 vs 0.4955 (+0.1375); F1 at 0.5
0.6143 vs 0.2594; F1 at cut 0.6375 vs 0.5100. All 14 cuts re-selected from validation
with the November rule (grid 0.05 to 0.95, ties to the higher cut, guard 10); all 14
equal the saved cuts. Support, floors, prevalence, both Bubble/Cluster confusion
matrices and the recall-by-flag block reproduce for all three arms. Tie-grouped AP sits
within 0.008 of the plain AP on every class, so the tie convention changes no verdict.

### Pass/fail preview (test split: 768 fail / 353 pass = 317 clear + 36 bubble-only; split: 5,157 fail / 2,313 pass = 2,117 clear + 196 bubble-only, both derived from the label table and equal to the map's counts)

Predicted fail = any of the five predicted fail classes (Foreign Matter, Fiber, Wet
Package, HEMA, Extraneous Polymer) above the cut. A picture passes when nothing but
bubbles is predicted.

| Arm, cuts | Caught | Clear passed | Clear wrongly failed | All-pass predicted pass |
|---|---|---|---|---|
| Weight at 0.5 | 219/768 (28.5%) | 317/317 | 0 | 340/353 |
| Weight at cut | 248/768 (32.3%) | 317/317 | 0 | 333/353 |
| Twin at 0.5 | 34/768 (4.4%) | 317/317 | 0 | 352/353 |
| Twin at cut | 238/768 (31.0%) | 317/317 | 0 | 328/353 |

Reading limit, stated with the number: only 197 of the 768 test failures carry any fail
class this head predicts. The other 571 fail on lens tags only, which a seven-column
object head cannot see. Of the 197 catchable failures the weight arm catches 171 at 0.5
and 187 at cut (94.9 percent); the twin catches 31 at 0.5 and 188 at cut. The twin's
4.4 percent at 0.5 and the weight arm's 28.5 percent both sit far below the November
13-column reference of 86.1 percent, because that model sees the lens tags. The 13 and
20 false fires of the weight arm land on bubble-only pass pictures; no clear picture
fails under either arm at either cut.

### Rule 3: the drop fires on Fiber, and it is large

Round-1 class arm vs gate arm, F1 on Fiber at the chosen cut: 0.2636 vs 0.3709, a drop
of 0.1073 against the 0.03 threshold. This is the same drop ticket 030 surfaced; it
still stands. Extraneous Polymer (0.1488 vs 0.0909) and HEMA (0.5672 vs 0.4839) go the
other way, the class arm ahead. At 0.5 all three pairs are 0.0000 vs 0.0000, so no drop
at that cut.

### Weighting verdict (rule 4): the weight proceeds to round 3

AP lift, weight minus twin: HEMA +0.3937, Extraneous Polymer +0.3189, Wet Package
+0.1820, Fiber +0.0796. Four supported classes lift by 0.05 or more, three of them the
flagged rare classes (floors 0.021, 0.019, 0.042), so the weight clears the rule-4 bar.
Losses: Bubble Cluster -0.0252 and Foreign Matter -0.0162; Bubble +0.0297. Ticket 033
runs with `--pos-weight on`.

### Tamper check

On copies of the weight arm's metrics.json: the untouched copy passes (exit 0). Raising
class_fiber.auprc by 0.05 fails with exit 1 naming `class-posw.class_fiber.auprc`;
lowering the at_chosen neither/neither confusion cell by 7 fails with exit 1 naming
`class-posw.confusion.at_chosen.neither.neither`. The checker recomputes every cell from
predictions.npz.

### Diff scope and hygiene

HEAD unchanged at 5ab3467ff31b93870f6f50fde92f8eee67d9102c. The four modified tracked
files predate this ticket (.gitignore plus four lines for the weight files, docs/INDEX.md,
tickets 027 and 030); this ticket's resolution is the only edit this verification made.
Untracked: the three round folders (22 files) plus this ticket's scripts in the scratch
workspace, none in the repo. Secret scan of the tracked diff and all 22 untracked files:
0 hits (API-key and private-key patterns, passwords, connection strings). No .bak, swap
or scratch files in the repo.
