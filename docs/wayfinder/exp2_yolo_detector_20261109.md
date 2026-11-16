---
title: Experiment 2 - lens head plus a YOLO26n detector for the seven object classes
date: 2026-11-10
type: protocol
status: active
where: docs/wayfinder/exp2_yolo_detector_20261109.md
---

# Experiment 2

## The directive

The lead's 5 November message asks for two experiments, both ending in a conditional pass/fail block:

1. fifteen lens-presentation tags plus eight object-of-interest tags in one multi-label CNN;
2. fifteen lens-presentation tags plus the object classes handed to a detector.

Experiment 1 is closed. Experiment 2 keeps the lens tags with the CNN and moves the seven learnable
object classes to a YOLO26n detector. Bubble and Bubble Cluster stay separate classes, calculated and
reported the same way as Experiment 1. The split, the truth and the pass/fail block do not change.

## What is fixed

- **Split:** `run/split_20261103_v8/split_70_15_15.csv`, md5 `1a71d66d2de384cf47a3fcf7d9115baa`.
  5,239 training, 1,110 validation, 1,121 test. Never build a new split.
- **Truth:** `run/eda_full_20261029/resolved_labels.csv`, rows with `shape_kind == box`.
- **Classes:** seven trained object classes. Surface Groove is the eighth guide class and has no
  pictures, so it stays a zero column and is excluded from every average.
- **Model family:** YOLO26n, the family already used in the September arena and in the crop
  comparison.
- **Rule:** the same pass/fail block, `experiments/multilabel_ooi/pass_fail_block.py`, fed by the
  detector's class list instead of the CNN's object columns.
- **Roles:** training only fits; validation chooses confidence cuts and any model choice; test is read
  once at the end.

## How the two models work together

Both models see the same frame. They are two specialists, not a relay.

| Model | Role | Trained on | Read by the block |
|---|---|---|---|
| CNN, the Experiment 1 nineteen-column head | Lens presentation | 12 lens tags, and in this checkpoint the 7 object classes as well | The 12 lens columns only |
| YOLO26n | Object detection | 7 object classes with boxes | The 7 class detections |

The CNN's object columns are ignored. It was trained on both label spaces, but in Experiment 2 it is
the lens specialist and its object outputs are dead. A CNN trained only on the 12 lens tags is a
different arm: its lens scores would change (0.836 against 0.882), so it would move two variables at
once. It is not this experiment.

YOLO is the only object authority. The CNN does not say "this is an object of interest" and YOLO
does not confirm a CNN object call. If a single object-present flag is needed for reporting, it is
derived from YOLO: any of the seven classes present.

The pass/fail block is the only place the two meet. It receives the 12 lens scores and the detector's
class list and applies the same rule. There is no routing, no sequential handoff and no second
opinion on the object side.

Why not the alternatives:

- **CNN classifies the objects, YOLO confirms.** Two object sources, so a change in the result can no
  longer be attributed to the detector. It is a different experiment.
- **CNN outputs one object tag, YOLO names the object.** A coarse tag fires on bubbles too, so it
  cannot make the pass decision. The flag arm in Experiment 1 would fail every bubble-only picture.
- **CNN routes only object pictures to YOLO.** A missed object never reaches the detector, and the
  object answer is needed for every picture.

## On the line

One decode, two resizes: the frame is decoded once, resized small for the CNN and large for YOLO.
Both models run on every frame, in parallel. Two checkpoints are versioned separately, the lens cuts
and the detector confidence cuts are separate, and the pass/fail rule is one shared function. The
total latency is measured in Experiment 2 against the 200 ms budget. Experiment 1's CNN path measured
29.2 ms on GPU and 53.9 ms on CPU; the YOLO forward pass is added to that and is not assumed.

A missed object or a missed lens tag is a separate failure mode. The per-class tables report the two
sides separately, which is why the block gets attribution and not just a verdict.

## Data and class map

The annotation has more codes than the seven classes. The builder folds them explicitly rather than
dropping rows silently:

| Detector class | Source codes | Note |
|---|---|---|
| Bubble | `bubble`, `bubble_irregular`, `stretched_bubble` | One class, as in Experiment 1 |
| Bubble Cluster | `bubble_cluster` | Kept separate |
| Wet Package | `wet_package` | |
| Fiber | `fiber` | Naming still provisional against Extraneous Polymer |
| Extraneous Polymer | `extraneous_polymer` | |
| HEMA | `hema_obstruction`, `hema_fragment` | Production boxes and September fragments together |
| Foreign Matter | `foreign_matter` | |
| Surface Groove | none | Zero pictures, excluded |

Excluded on purpose: `bubble_on_edge` and `bubble_on_123`. They are legacy codes outside the current
guide and do not appear on the frozen split (the 62 legacy-only pictures were dropped at split time);
the builder rejects them if they ever appear.

Boxes on the frozen split, pictures and boxes:

| Class | Train | Validation | Test |
|---|---:|---:|---:|
| Bubble | 1,520 / 20,154 | 326 / 4,338 | 325 / 4,249 |
| Bubble Cluster | 792 / 2,397 | 170 / 529 | 170 / 493 |
| Foreign Matter | 576 / 1,905 | 110 / 249 | 112 / 400 |
| Fiber | 274 / 567 | 60 / 90 | 58 / 83 |
| Wet Package | 220 / 987 | 47 / 153 | 47 / 202 |
| HEMA | 102 / 107 | 25 / 27 | 27 / 27 |
| Extraneous Polymer | 106 / 116 | 19 / 21 | 17 / 18 |

Pictures carrying at least one object box: 1,563 train, 341 validation, 343 test. The rest of the
split (3,676 train, 769 validation, 778 test) carries lens tags only or is Clear.

Images live on the VM at `/data/FMD_Data_26082026/fmd_temp_images/{winning_path}` and are 2448 by
2048 grayscale. The builder reads each image's size rather than assuming it.

YOLO is trained on boxes and class labels only. It is not trained on the lens tags, the pass/fail
verdict, Clear, or the size gate. The size flag can be reported later as a subset, but it is not a
training label. The CNN that supplies the lens scores was trained on both label spaces; only its lens
outputs are read.

## Dataset build

The builder and verifier live under `vm/ops/` and run through ssh stdin, so nothing is left loose on
the box:

- `vm/ops/build_fmd_detector_dataset.py`
- `vm/ops/verify_fmd_detector_dataset.py`

Output under `/data/FMD_Data_26082026/fmd_detector_20261110/`:

```
images/{train,val,test}/<md5>.bmp     symlink to the original picture
labels/{train,val,test}/<md5>.txt     YOLO detect labels: class cx cy w h
data_all.yaml                         all split pictures
data_objects.yaml                     only pictures with at least one object box
manifest.csv                          md5, split, source path, class, boxes
counts.json                           pictures and boxes per class and split
```

The image name is the content md5, so duplicate file names across source folders cannot collide and
the label lookup is exact. Labels are normalized by the picture's own width and height, clamped to
the frame, and boxes with zero or negative area are rejected rather than written.

The verifier must prove, before any GPU time:

- every one of the 7,470 split rows resolves to a readable image;
- every label file belongs to an image in the same split and no image is in two splits;
- per-class picture and box counts equal the table above;
- no excluded code appears in a label file;
- every box has positive width and height and lies inside the frame;
- the image and label stems match one to one.

## Training

| Item | Setting |
|---|---|
| Weights | `yolo26n.pt` |
| Task | detect |
| Image size | 1280 |
| Batch | 8 |
| Epochs | 100 |
| Patience | 50 |
| Seed | 42 |
| Optimizer | auto |
| Workers | 8 |
| Device | GPU 0 |
| Augmentation | Ultralytics defaults, so the run is comparable with the September recipe |

A one-epoch smoke test comes first, to measure seconds per epoch and confirm memory. Batch is reduced
only if the smoke test runs out of memory; that change is recorded. The full run writes `run.json`
inside the arm folder with `status`, `metrics.primary` set to mAP50-95, per-class AP and the training
time. A crashed run still writes `status: crashed` and the traceback path.

The September arena is not a baseline for this run. It used 346 training and 88 validation pictures,
older annotation and two legacy classes. Any phase-2 number comes from the current split.

## Evaluation

Two layers, because detection quality and the pass decision are different questions.

**Detector layer**

- mAP50 and mAP50-95 overall and per class on the test split, once.
- Picture-level precision, recall and F1 per class at the chosen confidence, because the block asks
  whether a class is present in a picture, not where every box is.
- Bubble and Bubble Cluster confusion: both, Cluster only, Bubble only, neither. The two are close to
  nested in this record, so the result is reported as a pair, not as two independent classes.

**Pass/fail layer**

- The same block, with the detector's class list as the object source and the lens columns unchanged.
- Both rules: the rule as run (Clear, or only Bubble and Bubble Cluster) and only Bubble passes.
- Caught, clear wrongly failed, bubble-only passed, passed overall, per-class fail drivers and the
  causes of false fails, at a fixed 0.5 confidence and at the validation-chosen cuts.
- Test is scored once. No cut is moved after the test result is seen.

**Confidence cuts**

For each detector class, sweep confidence on the validation pictures and choose the highest
picture-level F1, with the same guard as Experiment 1: a class with fewer than 10 validation
positives keeps a default cut and is marked default. The test split never chooses a cut. The report
shows the fixed 0.5 point beside the chosen point so the choice is visible.

**Latency**

Detector forward plus lens head plus block, one picture at a time, on GPU and on CPU if the CPU path
is needed for the line. Compare against the 200 ms budget already used for Experiment 1.

## Deliverables

- The spec, the dataset builder and the dataset verifier.
- `vm/drivers/run_yolo26_fmd_detector.py` and `vm/drivers/launch_exp2_training.sh`, writing the run
  record and artifacts under `/home/pranayp/fmd-analysis/run/detector_20261110/<arm>/`.
- `<arm>/run.json`, `<arm>/weights/best.pt`, and after the run `detections_val.jsonl`,
  `detections_test.jsonl`, `thresholds.json`.
- A workbook in the Experiment 1 style, under `reports/multilabel_production/`, with the detector
  layer, the lens layer, the Bubble/Cluster pair, both pass rules and the method.
- A session entry and a HANDOFF rewrite.

The run record is the handoff from the training step. The report and deck are a separate step after
the run; this spec does not authorise either.

## Acceptance

- The dataset verifier exits 0 with every check above passing.
- Training completes with `status: ok` in `run.json`, or a crashed run with its traceback recorded.
- Every reported detector number comes from the run's own artifacts, never hand-typed.
- The pass/fail numbers reproduce from the saved detections and cuts without a GPU.
- Both pass rules are reported; the Bubble/Cluster confusion is reported beside them.
- No test picture is used to choose a cut, a confidence or a model.
- The workbook passes the client-safe sweep: no paths, script names, class codes, ticket ids or role
  attribution, and no em dashes.

## Decisions taken (2026-11-09)

1. **Lens source.** Reuse the lens columns of the Experiment 1 nineteen-column head. Its object
   columns are ignored in Experiment 2, so the lens side is identical to Experiment 1 and the only
   changed variable is the object source.
2. **Background pictures.** Train on all 5,239 training pictures, with empty label files for the
   3,676 that carry no object box. The detector sees the real proportion of object-free pictures.
3. **Detector confidence.** Per-class cut chosen on validation, with the same guard as Experiment 1:
   a class with fewer than 10 validation positives keeps a default cut and is marked default. The
   fixed 0.5 point is reported beside the chosen point.
4. **Class set.** Seven classes, Bubble and Bubble Cluster separate. Bubble folds Bubble Irregular
   and Stretched Bubble; HEMA folds HEMA Obstruction and HEMA Fragment.
5. **Build timing.** The dataset is built and verified now; training waits for the lead's review.

## Build status (2026-11-09)

The dataset was built on the VM at `/data/FMD_Data_26082026/fmd_detector_20261110` and the verifier
exits 0. It holds 7,470 image symlinks and 7,470 label files, 41 MB in total. Pictures with boxes:
1,563 train, 341 validation, 343 test. Empty labels: 3,676 train, 769 validation, 778 test.
`data_all.yaml` and `data_objects.yaml` both load with `nc: 7` and the class order above. The run
record is `run/detector_20261110/dataset_counts.json` and the verifier output is
`run/detector_20261110/dataset_verify.txt`.

The dataset build used no GPU time. The training driver is
`vm/drivers/run_yolo26_fmd_detector.py`; the launcher is `vm/drivers/launch_exp2_training.sh`.

## Staged runs and results (2026-11-10)

The GPU was checked at 05:58 UTC on 10 November: 38,445 MiB in use at 94%, with srikantht's YOLO
training holding 35,920 MiB and a streamlit app holding 2,482 MiB. No pranayp process was on the GPU.
The GPU freed at 07:33 UTC; the watcher waited 10 minutes and started the all arm at 07:43 UTC
(PID 287348). It finished at 09:51 UTC after 7,760 s and 100 epochs.

Two arms are ready:

| Arm | Data | Name | Command |
|---|---|---|---|
| All pictures, primary | `data_all.yaml` | `yolo26n_fmd_7cls_all` | `launch_exp2_training.sh all wait` |
| Boxed pictures only, comparison | `data_objects.yaml` | `yolo26n_fmd_7cls_objects` | `launch_exp2_training.sh objects wait` |

The all arm finished at 09:51 UTC; the boxed-only arm started at 10:10 UTC and finished at 10:57 UTC
after 2,815 s. Run as pranayp. The `wait` mode checks the GPU every
minute. It starts after a 10-minute quiet window below 10,000 MiB used and 20% utilisation with no new
compute process, and resets the window if a process appears. `now` skips the wait and is only for an
already free GPU. The check, the watcher and both commands are recorded in
`run/detector_20261110/stage_status.json`.

The all-pictures arm scored test mAP50-95 0.1707, mAP50 0.3317, precision 0.412 and recall 0.383 on
1,121 test pictures and 5,472 boxes. Per-class AP50-95: Bubble 0.388, HEMA 0.498, Wet Package 0.158,
Foreign Matter 0.073, Bubble Cluster 0.051, Fiber 0.023, Extraneous Polymer 0.004. Validation best was
epoch 96 at 0.1478. The per-class rows in `run.json` were repaired after the driver asked for summary
keys ultralytics 8.4 does not return; the overall numbers are unchanged.

Through the pass/fail block, with object cuts chosen on validation: Bubble and Cluster pass gives
746 of 768 failing pictures caught and 340 of 353 overall at the chosen cuts; only Bubble passes gives
751 of 768 and 326 of 343. The chosen Cluster cut is 0.03, so under the only-Bubble rule nearly every
bubble picture also fires Cluster and fails. The cut objective for that rule is still open.

The boxed-only arm scored test mAP50-95 0.1475, mAP50 0.2624, precision 0.290 and recall 0.424, with
best epoch 82. It trades precision for recall: Bubble falls from 0.388 to 0.187, while HEMA rises from
0.498 to 0.589 on 27 test instances. Through the block, Bubble and Cluster pass at 0.5 gives 738 of
768 fails caught, 307 of 317 clear passed and 328 of 353 overall, against 730, 316 and 337 for the all
arm; at the chosen cuts it gives 743, 270 and 293, against 746, 316 and 340. Only Bubble at the chosen
cuts gives 752 of 768, 141 of 317 and 153 of 343.

The background pictures are doing specificity work. Removing them makes the detector fire on empty
frames, and that appears as Clear false fails: 47 against 1 at the chosen Bubble-and-Cluster cuts.
The all-pictures arm stays the production choice. At 100 epochs the boxed arm also takes 196 batches
per epoch against 655, so the comparison is the practical recipe, not a pure background ablation.

The Experiment 2 workbook is built at `reports/multilabel_production/FMD_Experiment2_Detector_20261110.xlsx`.
It has six sheets and four charts, is set up for A3 landscape printing, and passes the client-safe
token scan. It waits for the user's review before sharing.


## Risks

- **Bubble dominates the label set.** 20,154 training boxes against 2,397 for Cluster and 116 for
  Extraneous Polymer. The detector may over-predict Bubble and under-fit the rare classes. Per-class
  AP and picture-level precision are the read, not the overall mAP alone.
- **Cluster is nearly nested in Bubble.** 22 Cluster-only pictures exist across the split, 10 in
  test. The detector may learn Cluster as a subset of Bubble. Report the confusion and do not claim
  independent separability.
- **HEMA is small.** 102 training pictures and 107 boxes. A weak AP is expected and is a data limit,
  not necessarily a model failure.
- **Downscaling.** 2448 by 2048 to 1280 reduces the long side by 1.9 times. Small objects near the
  size gate may lose. If recall on Foreign Matter or Fiber is poor, a 1536 arm is the next variable,
  run as a separate arm rather than changed mid-run.
- **Backgrounds may dilute the loss.** If the all-pictures arm learns slowly, a capped background
  set is the fallback, and the change is recorded as an arm difference.
- **The block's false fails may persist.** Experiment 1 failed 28 of 36 bubble-only pictures because
  Foreign Matter and Fiber fired on bubble texture. A detector may reduce this or reproduce it; the
  result is the finding either way.
