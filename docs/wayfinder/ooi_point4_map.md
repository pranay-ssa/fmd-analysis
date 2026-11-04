---
title: "Map: OOI point 4 - class versus gate, then the pass/fail rule"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/ooi_point4_map.md
---

# Map: OOI point 4 - class versus gate, then the pass/fail rule

## Destination

The single object-of-interest flag replaced by the eight guide object classes,
with the class-versus-gate question answered by two identically trained arms
scored on identical truth; a trained OOI head with one run record per arm; the
lens numbers proven stable under the combined head; and the picture-level
pass/fail rule applied to the winning arm and reported in a verified workbook.
Every number lands in the repo with a builder and a verifier; no number is
reported that a verifier cannot recompute.

## Notes

- Domain: FMD lens inspection, repo `D:/fmd-analysis`, VM tree
  `/home/pranayp/fmd-analysis`, images only on the VM at
  `/data/FMD_Data_26082026/fmd_temp_images`. Local work runs under
  `.venv/Scripts/python.exe`.
- The split is frozen and reused: `run/split_20261103_v8/split_70_15_15.csv`,
  7,470 rows, 5,239 / 1,110 / 1,121, md5
  `1a71d66d2de384cf47a3fcf7d9115baa`. No new split is built; only the label
  columns change.
- Training recipe is fixed: resnet50, 224, batch 8, 50 epochs, no early
  stopping, SGD lr 1e-4 momentum 0.9, seed 42, BCEWithLogitsLoss, about
  29.3 s/epoch, so about 25 minutes per arm on the A100.
- Thresholds follow the November rule: grid 0.05 to 0.95 step 0.05 on
  validation, highest F1 per class, ties to the higher cut, guard of 10
  validation positives, below it keep 0.5 and record untuned.
- Eight object classes in the split population: Bubble 2,171 (val 326 /
  test 325), Bubble Cluster 1,132 (170/170), Foreign Matter 798 (110/112),
  Fiber 392 (60/58), Wet Package 314 (47/47), HEMA 154 (25/27), Extraneous
  Polymer 142 (19/17), Surface Groove 0. Bubble folds Bubble Irregular and
  Stretched Bubble. HEMA is production boxes plus fragments and gate rows;
  the single obstruction-tag-only picture is excluded, and the verifier pins
  this. Surface Groove stays an all-zero column, excluded from training
  effect and from every average, listed at zero.
- Gate versus class: the micron flag partitions the class, never a second
  class. Gate positives: Foreign Matter 454, Fiber 362, Extraneous Polymer
  135, HEMA 151, each a subset of the class column. Un-gated: 344 / 30 / 7 /
  3. The gate column exists in the table for the gate arm, for the
  recall-by-flag diagnostic, and for the verifier's subset check; no model
  ever trains on both.
- Bubble Cluster is nested in Bubble: 1,110 of 1,132 Cluster pictures also
  carry Bubble, 22 are Cluster-only. Predict both and report the confusion.
- Pass/fail truth under the agreed rule: pass is Clear (2,117) or
  bubble-classes-only (196); everything else fails (5,157, 69.0 percent of
  the split; test 768 fail / 353 pass). Fail classes: all twelve lens tags
  plus Wet Package, Foreign Matter, Fiber, Extraneous Polymer, HEMA, Surface
  Groove, and Bubble Scatter. 1,997 pictures carrying a bubble still fail,
  so the rule is "nothing but bubbles", never "bubble present".
- AP floor for a constant score is prevalence: Bubble 0.291, Cluster 0.152,
  Foreign Matter 0.107, Fiber 0.052, Wet Package 0.042, HEMA 0.021,
  Extraneous Polymer 0.019. Every AP is reported beside its floor.
- Skills every session consults: `fmd-coordination` (VM idioms, handoff
  proof), `kanban-orchestrator` (routing), `verifier` (recompute, tamper
  proof), `fmd-label-space` (counting rules), `simple-english` (shared
  prose).
- Standing rules: numbers go to the user as soon as they are read;
  verification runs in parallel and a correction follows if it contradicts;
  one executor per file; nothing loose left on the VM; reports carry no
  internal names.

### Pre-registered decision rules (agreed with the user, 2026-11-04)

1. Rounds run autonomously under these rules; numbers are shown after each
   round; the user can steer mid-run.
2. Round 2 target = the round-1 arm with the higher macro AP over the seven
   supported classes on class-level test truth. A tie or a gap within 0.005
   resolves to the class arm, because the class target is the one the
   pass/fail rule needs.
3. If the class arm drops more than 0.03 F1 against the gate arm on Fiber,
   Extraneous Polymer or HEMA, round 3 still runs, but the drop is surfaced
   to the user in the round-2 numbers.
4. Round 3 uses the round-2 winner's weighting and target, in combined
   nineteen-column mode; its job is to prove the lens numbers did not move
   (macro AP judgeable 0.8182 and the per-class November table are the
   reference).
5. Verification gates the next round: a verify ticket that fails blocks its
   round ticket rather than flowing a defect forward.
6. Reporting: per-class AP with floor, per-class F1 at 0.5 and at chosen
   cuts, Bubble/Cluster confusion, and the pass/fail view (caught, clear
   passed, clear wrongly failed) against the November 13-column reference
   (86.1 percent caught, 12 clear wrongly failed at 0.5).

## Decisions so far

- [027: OOI label table](tickets/027-ooi-label-table.md): both column groups
  in one table, class and gate, subset-checked.
- [028: train_multilabel.py](tickets/028-train-multilabel.md): one trainer,
  two column groups, two modes, pos_weight switch.

## Route

027 and 028 build in parallel; 029 trains both round-1 arms; 030 verifies and
records the verdict; 031 trains the weight arm on the winner; 032 verifies;
033 trains the combined head; 034 verifies lens stability; 035 applies the
pass/fail rule and builds the workbook; 036 sweeps the documentation.

## Not yet specified

- The deployment threshold recommendation for the OOI head: cannot be written
  until the weight and combined rounds land.
- The client-facing shape of the point-4 workbook beyond the tables named in
  rule 6: depends on whether Bubble Cluster separates.
- Whether the single object flag is retired from the production label table
  or kept beside the eight columns as a redundancy check: decided after
  round 3.

## Out of scope

- Box-level detection. The parked item is picture-level presence; a detector
  is a separate effort.
- Any rerun on a new annotation vintage, and any change to the frozen split.
- Deployment integration and any client-facing deck beyond the workbook.
- The five-class line and the October 13-column runs; they are references,
  not work.
