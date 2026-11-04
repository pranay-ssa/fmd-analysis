---
title: "Ticket 034: verify round 3 and the lens-stability check"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/tickets/034-verify-round3.md
---
Type: verification, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

Are the combined-run numbers real, and did the lens head hold still?

## Spec

- Recompute from predictions.npz: the seven object classes as in 030/032, and the twelve
  lens classes against the November reference. Stability statement: judgeable macro AP
  within 0.01 of 0.8182 counts as held; anything beyond is reported as a move, not buried.
- Cross-check the object columns of the combined head against the round-2 winner's
  object-only scores on the same test pictures; large drift is reported.
- Record the verdict; also record the recommendation on retiring or keeping the single
  object flag (map fog item), for the user to decide.

## Done when

Numbers reproduced, stability statement recorded, ticket 035 unblocked.

## Resolution (recorded 2026-11-04 by the round-3 verifier)

**Verdict: the numbers are verified, and the lens head did NOT hold still. Rule 4 reads this
as a move, not as held: judgeable lens macro AP 0.8815 against the November reference 0.8182,
delta +0.0633, four times the 0.01 held band.** The move is an improvement, it is disclosed by
the round-3 worker, and it is reported here rather than buried.

### How the numbers were re-derived

Every figure below was recomputed from `predictions.npz` with code written for this ticket;
no trainer function was imported. Totals: 361 recorded-value comparisons across the three
runs, 0 failures; 1,121 test rows x 19 columns of truth matched row-for-row against the label
table with 0 mismatches; all 19 pos_weight train-positives and weights re-derived from the
label table, 0 mismatches.

Two early failures were defects in my checker, not in the artifacts, and both were run to
ground before anything was accepted: my threshold tie-break gave ties to the lower cut (the
November rule sends them to the higher one, after which all 19 cuts re-select exactly), and
I read the lens `macro_f1_0.5` / `macro_f1_chosen` fields as 12-class means when they are
judgeable-8 scoped (all-12 mean is 0.7137, judgeable-8 mean matches to 1e-15). The field
names do not say "judgeable" while `macro_auprc_judgeable` does; the arithmetic is right and
the label is loose, so read those two fields as judgeable-8.

Reproduced exactly: the seven object APs and floors (Bubble 0.9474/0.291, Cluster 0.5881/0.152,
Foreign Matter 0.5082/0.107, Fiber 0.3786/0.052, Wet Package 0.5403/0.042, HEMA 0.9905/0.021,
Extraneous Polymer 0.5132/0.019), every AP above its floor, macro AP supported 0.6380419266;
all 19 lens and object APs, F1 at 0.5 and at chosen cuts, supports, both Bubble/Cluster
confusion matrices at 0.5 and at cut, and all 42 recall-by-flag cells against metrics.json and
run.json. All 19 cuts re-select from validation with the November rule (grid 0.05 to 0.95,
ties to the higher cut, guard 10), matching both saved files; the four untuned lens classes
(Dirty Strobe, View Obstructed, Bubble Scatter, Package Misalignment) sit at 0.5 default in
this run and in the November run, confirmed from November's own thresholds.json. The
November reference was recomputed from ITS OWN predictions.npz: judgeable macro AP
0.8182347079, equal to the recorded 0.8182347078510195, and its judgeable list re-derives as
the eight classes with test support >= 20.

### Stability statement (rule 4): a move

| Lens class | Sup | F1@0.5 combined | F1@0.5 November | Delta | AP combined | AP November | AP delta |
|---|---|---|---|---|---|---|---|
| Missing Primary Package | 214 | 0.9906 | 0.9906 | +0.0000 | 0.9999 | 0.9999 | +0.0000 |
| Multiple Lens | 214 | 0.9524 | 0.9276 | +0.0248 | 0.9768 | 0.9728 | +0.0040 |
| Lens Off Center | 180 | 0.7646 | 0.7581 | +0.0065 | 0.8165 | 0.7855 | +0.0310 |
| Dirty Camera | 86 | 0.6341 | 0.1875 | +0.4466 | 0.7328 | 0.4557 | +0.2771 |
| No Lens | 49 | 0.9245 | 0.8049 | +0.1197 | 0.9988 | 0.9719 | +0.0269 |
| Folded Lens | 51 | 0.5818 | 0.4146 | +0.1672 | 0.6412 | 0.4950 | +0.1462 |
| Low Dose | 102 | 0.8282 | 0.8737 | -0.0455 | 0.9447 | 0.9220 | +0.0227 |
| Cavity Off Center | 28 | 0.9630 | 0.8333 | +0.1296 | 0.9413 | 0.9430 | -0.0017 |
| Dirty Strobe | 2 | 0.4444 | 0.0000 | +0.4444 | 1.0000 | 0.0060 | +0.9940 |
| View Obstructed | 10 | 0.9474 | 0.0000 | +0.9474 | 0.9500 | 0.9013 | +0.0487 |
| Bubble Scatter | 1 | 0.0000 | 0.0000 | +0.0000 | 0.1250 | 0.0010 | +0.1240 |
| Package Misalignment | 5 | 0.5333 | 0.0000 | +0.5333 | 0.8909 | 0.2536 | +0.6373 |

Max |delta| per lens, class named: largest F1@0.5 move over all twelve is View Obstructed
(P2_FOV) +0.9474; largest judgeable-only F1@0.5 move is Dirty Camera (P2_DC) +0.4466; largest
AP move over all twelve is Dirty Strobe (P2_DS) +0.9940; largest judgeable AP move is Dirty
Camera (P2_DC) +0.2771. The only judgeable F1@0.5 decline is Low Dose (P2_LD) -0.0455, and its
threshold-free AP rose +0.0227 in the same direction as the macro, so that single decline is a
score-scale and cut-placement move, not lost ranking ability. The only AP decline of any kind
is Cavity Off Center -0.0017, which is inside noise.

### Cross-check: combined head's object columns against the round-2 winner

Same 1,121 test pictures (test md5 vectors identical across combined, class-posw and the
November run; truth identical column for column). Macro AP 0.6330 (0.633048) for the
round-2 winner against 0.6380 (0.638042) for the combined head, delta +0.0050. Per class,
AP drift: Extraneous Polymer +0.0857 (largest, an improvement), Fiber +0.0332, HEMA +0.0280,
Bubble -0.0172, Foreign Matter -0.0202, Wet Package -0.0319, Bubble Cluster -0.0427 (largest
decline). F1 at the chosen cut moves at most 0.019 in either direction (Wet Package -0.0192
is the largest), so at operating cuts there is no large drift anywhere. At the fixed 0.5 cut
three classes move about 0.05: Wet Package -0.0573, HEMA -0.0561, Extraneous Polymer -0.0465.
The two arms select different cuts (for example Bubble 0.10 for the winner against 0.65 for
the combined head), because each run re-selects thresholds on validation; that is expected
and is not drift in the scores.

### The single object flag (map fog item) - recommendation, not the decision

The November flag is exactly reproducible: `object_present` equals `has_object` equals the OR
of the seven object columns on all 7,470 rows, 0 mismatches, so it carries no information the
seven columns do not already hold. On the combined head the OR of the seven columns at 0.5
fires on 117 of the 120 object-only test pictures (97.5 percent) against the November flag's
118 of 120 (98.3 percent), a one-picture difference; picture-level agreement between the
model's OR-of-seven and the flag truth is 1,092 of 1,121 (97.4 percent), with 6 flag-positives
missed and 23 flag-negatives fired.

**Recommendation:** retire the single flag as a stored column in the production label table
and keep it as a derived view (the OR of the seven columns) for anything downstream that
wants one boolean, so the two can never drift apart through one side being edited. If a future
annotation vintage annotates the flag independently at source, capture that at intake as a
quality-control signal, because then a disagreement with the seven columns would mean a
labeling error. The decision belongs to the user.

### Tamper proof

The checker recomputes every number this verdict relies on from `predictions.npz` and exits
non-zero naming the cell that differs. Three runs: untouched file, exit 0, all 66 cells
reproduce; copy with `lens.per_class.P2_DC.auprc` raised from 0.732849 to 0.782849, exit 1,
naming `lens.per_class.P2_DC.auprc`; copy with `macro_ap_supported` raised from 0.638042 to
0.678042, exit 1, naming `macro_ap_supported`.

### Artifacts, run record, crash disclosure

All seven files are md5-identical between this tree and the VM, and match the round-3
worker's recorded hashes: metrics `c6ea49a0`, thresholds `7a4d174a`, predictions `b0c4c975`,
final.pt `0bce7432`, train.log `86738bd2`, run.json `8ecc4682`, crash log `9ecb80f6`. The
trainer matches both ends at `c1a46c5eefc55d473e5914dea8897771`, the post-fix hash the worker
recorded. run.json parses, reads status ok, names run `cnn__combined__50__20261104-1028`,
records 50 epochs and config `columns=combined, gated_target=class, weight_mode=on` (the
round-2 verdict), carries git_sha equal to this repo's HEAD, its primary reproduces from
predictions.npz to 1e-9, and its three artifact paths resolve. The train log runs all 50
epochs at 29.3 s/epoch. The crash disclosure checks out: crash1_train.log ends in
`KeyError: 'f1'` at `train_multilabel.py line 594, in evaluate_test`, exactly as reported.

### Reading limits carried forward

1. The combined arm trains with pos_weight on across all 19 columns while the November
   reference was trained unweighted across 13. Rule 4 pre-registered the round-2 winner's
   weighting, so head width and weighting are confounded by design: the +0.0633 move cannot
   be attributed to adding the object columns alone.
2. Four lens classes are below the validation guard in both runs and sit at the 0.5 default;
   their deltas measure score scale, not a tuned operating point.
3. The lens `macro_f1_0.5` and `macro_f1_chosen` fields are judgeable-8 means despite names
   that do not say so.

### Diff scope and hygiene

HEAD unchanged at `5ab3467ff31b93870f6f50fde92f8eee67d9102c`. The five modified tracked files
(.gitignore, docs/INDEX.md, tickets 027, 030, 032) predate this ticket; this ticket's
resolution is the only edit the verification made, plus one deterministic regeneration of
docs/INDEX.md by its own `--check`, which exits 0. Untracked: 28 files (three scripts, the
four run folders' artifacts, the label-table folder), none created by this ticket. Secret
scan of the tracked diff and all 28 untracked files: 0 hits, 0 false positives, on API-key
and private-key patterns, passwords and connection strings. No .bak, swap or scratch files in
the repository; the verification scripts live in this task's scratch workspace.
