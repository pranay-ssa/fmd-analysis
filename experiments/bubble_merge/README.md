---
title: experiments/bubble_merge - Task 1, four bubble classes merged, Clear added
date: 2026-10-06
type: protocol
status: active
where: experiments/bubble_merge/README.md
---

# Bubble merge arena (Task 1)

**Question.** The client email asks us to fold Bubble, Bubble On 123, Bubble
On Edge and Bubble Irregular into one Bubble class, add Clear as a class for
the images that carry no tag, then run ResNet50 and MultiScale on the result
and report, per class, how the merged reading compares with the four separate
classes. One tag per image, and the count table split by LP tag and OOI tag.

## Decisions taken with the user, 2026-10-06

1. **Pool**: the 8,409 tagged pictures plus the 2,205 Clear-only pictures,
   10,614 distinct pictures in total, under the pool rules frozen on
   2026-09-17.
2. **Merge scope**: only the four classes named in the email. Bubble Cluster
   and Bubble Scatter stay separate.
3. **Clear**: every picture whose only label anywhere is Clear, counted once
   by content hash. Pictures carrying any tag keep the tag.
4. **One tag per picture**: the folder-priority rule, CHANGED 2026-10-07 on
   client confirmation: the updated folders (Updated Objects, then Updated
   Categorical) outrank the older ICube Defects Library. The 33 pictures the
   old library calls Fiber are Extraneous Polymer under the new annotation,
   as the client confirmed. The 20261006 outputs are the old-order record;
   `run/bubble_merge/20261007/` holds the new-order labels, split and count
   tables (67 verifier checks pass). Every run before 2026-10-07, including
   the four bubble_merge runs of 2026-10-07 morning, used the old order.
5. **Split**: one fresh 70:30 split inside each class, md5-grouped, seed 42,
   shared by all four runs so the comparison is paired.
6. **Training scope**: one pooled model over all five lines (not per line).
7. **Input**: the native 2448x2048 frame resized to 224x224, matching the
   earlier CNN lines, because the first iteration is about the class merge
   and not about preprocessing.

## What is built and verified (local only, 2026-10-06)

| Piece | File | Status |
|---|---|---|
| Labels for both variants plus split | `build_labels.py` -> `run/bubble_merge/20261006/` | 62 checks pass, rerun byte-identical |
| Independent verifier | `verify_labels.py` | 62 checks, 0 failed |
| Train/test tree builder for the trainer | `build_vm_trees.py` | full strict build pass on synthetic sources; missing-source test fails loudly |
| Prediction + confusion dump | `../cnn/dump_outputs.py` | 6 unit tests pass (`tests/test_dump_outputs.py`) |
| Trainer flags to switch the dump on | `../cnn/model_training.py` `--dump`, `--save-model` | compiles; TF path only testable on the VM |
| Count table record | `reports/bubble_merge/count_table_20261006.md` | written, numbers from the verified CSVs |

Dataset facts, all checked: 10,614 pictures, 8,409 tagged, 2,205 Clear,
23 classes become 20 under the merge, train 7,428 / test 3,186, merged Bubble
185 pictures (130 train, 55 test).

The verifier reproduces the published figures by independent routes: every
class-line cell of the 2026-09-17 split, the 12 LP and 11 OOI tag counts of
the client EDA, the Clear arithmetic (2,333 = 128 + 2,205), the two-tag count
of 55, and a picture-by-picture comparison against the frozen rule builder.

## Procedure for the VM (nothing has been run there yet)

1. **md5 both machines first**: labels.csv, both count tables, the split file,
   `build_vm_trees.py`, `model_training.py`, `dump_outputs.py`. Push only
   after the pairs match; the launcher gates on the same hashes.
2. **Build the trees** (symlinks, sources stay untouched):

   ```
   python build_vm_trees.py --image-root /data/FMD_Data_26082026/fmd_temp_images \
       --out <run-root> --variant both --mode symlink --strict
   ```

   Expected: `separate linked 10614 ... PASS` and `merged linked 10614 ...
   PASS`. A picture with no source under the root exits non-zero.
3. **Micro-run gate before any real run**: a 2-class, ~10-image tree, 1 epoch,
   `--dump` on. This is the only place the new trainer code path can be
   exercised cheaply, and it proves predictions.csv and confusion.json are
   written before 50 epochs of GPU are staked on it.
4. **Four runs, one at a time**, checking `nvidia-smi
   --query-compute-apps` first: architecture in {resnet50,
   resnet50_inception} x variant in {separate, merged}, 50 epochs, batch 8,
   seed 42, `--dump`, one outdir per run.
5. **Mirror back** metrics.json, confusion.json, predictions.csv and the
   confusion PNG for each run, md5 the pairs, then fill the registry rows.

## The readout rule (fixed before running, in registry.json)

Merged and separate are always reported side by side on the same test
pictures, per class and macro, for each architecture. If the merged Bubble
class reads worse than the four separate classes did, the confusion cells
must name the class responsible: which class the merged Bubble pictures are
predicted as, and which class's pictures are predicted as Bubble. Any delta
is quoted against the single-run noise band, and no run is quoted alone.

## Open items

- The trainer still does not save weights (the long-standing CNN open item);
  `--save-model` is there but off by default.
- The seed band on this dataset has never been measured, so a small delta
  between merged and separate stays inconclusive until a repeat run says
  otherwise.
- Whether the merged class should also absorb Bubble Cluster is not decided;
  it is one label file away if the client asks.
