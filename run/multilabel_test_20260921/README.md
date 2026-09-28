---
title: run/multilabel_test_20260921 - YOLO26n trained on the pictures with more than one label
date: 2026-09-21
type: result
status: active
where: run/multilabel_test_20260921/README.md
---

# What the multi-label pictures can carry, measured

> **Open question, 2026-09-22.** 33 pictures are named Extraneous Polymer in the newer folder and Fiber
> in the older library. Every model here takes the older library's name, so the Fiber and Extraneous
> Polymer per-class figures in this document are stated on that naming and are provisional until the
> client rules which folder is authoritative. The pictures, the boxes and the other classes are not
> affected. Detail: `docs/naming_open_question_20260922.md`.

The asked-for job: split the pictures that carry more than one defect label, then train YOLO26n at
the usual settings. It ran on the a100 box as pranayp on 2026-09-21. The two trainings took 200 s of
GPU time together.

## The split, and why 70 and 30 rather than 80 and 20

**47 of the 55 pictures can enter a detection split.** 8 carry no box anywhere and are held out,
with the reason recorded for each: 4 are a HEMA Fragment against HEMA Obstruction pair, 2 are
Multiple Lenses against Wet Package, and 2 are Low Dose against Wet Package. Detection needs boxes,
so the unit is 47 pictures.

At 47 pictures the training side is flat. 34 or 38 training pictures are both far below the 346 the
existing detection set uses, so the model lands near its floor either way and six fewer pictures
change little. The measurement is what is fragile at this size. At 80 and 20 the test set holds 9
pictures, almost all of them Fiber, so five of the six classes would score by absence and the one
number that came out would carry an interval wide enough to hide any real difference. At 70 and 30
the test set holds 14 pictures, which covers the classes we have, at a cost the training side does
not notice.

The outcome: 34 train and 13 test, 85 boxes against 32. The test set holds 10 Fiber pictures, 2 Wet
Package and 1 Bubble. Four pictures carry a class with fewer than three examples in the whole
subset, and those went to the training side, because a class that appears only in the test set
teaches nothing.

## The two tests, and the one variable between them

Same weights, same settings, same seed, same session. The only change is which pictures sit in the
test set.

| | Training side | Test side | The question it answers |
|---|---|---|---|
| **Test 1** | 34 pictures | 13 pictures | the split that was asked for |
| **Test 2** | 24 pictures from lines 24, 26, 27 and 31 | 23 pictures from line 25 | does the score survive a group the model has never seen |

Line 25 is a real production line. Each frame name carries the line it came from, and this data
covers lines 24, 25, 26, 27 and 31. Most of the multi-label pictures came off line 25 on one day,
from one pallet and one cavity, so a plain random split puts near-identical frames of the same setup
on both sides. The model can then score well by recognising a setup it has already seen. Test 2
removes that: every picture from line 25 goes to the test side and the training side keeps the other
lines.

Settings, taken from the usual run: YOLO26n, 100 epochs, imgsz 1280, batch 8, patience 50, seed 42.
Test 1 ran all 100 epochs in 117 s. Test 2 stopped itself at 87 epochs in 84 s, because its score
stopped improving.

## Results

On the test set built for each test:

| Test | Precision | Recall | mAP50 (detection score) | mAP50-95 |
|---|---|---|---|---|
| **Test 1** | 0.3383 | 0.6555 | **0.4741** | 0.1991 |
| **Test 2** | 0.0103 | 0.3409 | **0.0758** | 0.0140 |

The per class rows, and both models scored on the shared 88-picture test set, are in
`results_per_class.csv`. Precision is the share of the boxes the model drew that were a real defect.
Recall is the share of real defects the model found.

**The result is the gap, not either number.** The same pictures, the same settings and the same seed
score 0.4741 when the test pictures come from the session the model trained on, and 0.0758 when that
session is held out, a factor of 6.2. Test 2's precision of 0.0103 against its recall of 0.3409 is
what that failure looks like: the model draws boxes widely at anything fiber-like and is almost
never right. A good number from a plain split of these pictures therefore measures memory of one
session, not detection.

Per class, Test 1: Bubble 0.5509 from 17 defects on one picture, Fiber 0.3906 from 10 pictures, Wet
Package 0.4807 from 5 defects on 2 pictures. Test 2: Fiber 0.1516 from 22 pictures, Wet Package
0.0000 from one picture.

On the shared 88-picture test set, which holds mostly classes this training never saw, Test 1 scored
0.0863 and Test 2 scored 0.0299.

## Why these results stand while the naming question is open

The run answers a question about size and about capture session, not about class names. All 33 disputed
pictures sit in the Fiber class here, so no picture trained as two things and no box moved.

| What the open question touches | Does it change? |
|---|---|
| The gap between the two tests, a factor of 6.2 | No. The gap comes from which pictures sit on the test side, and that does not move |
| The number of training pictures, 34 and 24 | No. Same pictures, same boxes, same count |
| Extraneous Polymer as a class in this run | Barely present either way: 1 training picture and 0 test pictures |
| The Fiber per-class rows, 0.3906 in test 1 and 0.1516 in test 2 | Yes. Those rows are the disputed pictures: 10 of test 1's 13 test pictures, 22 of test 2's 23 |
| The Fiber and Extraneous Polymer rows on the shared 88-picture set, 0.0574 against 0.0026 and 0.0039 against 0.0000 | Yes, same reason |
| The conclusion that this subset cannot carry a detector | No. It rests on 34 training pictures and on one capture session, and renaming changes neither |

Read the Fiber row in either test as "the objects the older library calls Fiber, pending the naming
answer", not as a settled Fiber score. Everything else in the tables above stands as written, and the
0.5355 baseline is a separate measurement on different pictures.

## What this settles, with no new data

1. **Every detection number this project holds was measured on pictures with one class.** In the
   existing detection set, 0 of the 346 training pictures and 0 of the 88 test pictures carry two
   classes in their box file. The 0.5355 baseline has never seen a picture with two box classes.
2. **The multi-label pictures alone cannot carry a detector.** 0.4741 inside the session against
   0.0758 outside it, from 34 training pictures.
3. **The multi-label nature of these pictures lives in the folder record, not in the box file.**
   Each of the 47 has exactly one class in its box file, and only 6 of the 10 classes appear at all.
   So training on multi-label data cannot be exercised on this subset, because the second defect was
   never marked on the picture.
4. That makes the data request specific: **the second defect needs a box on the pictures that carry
   two labels.** No architecture change can supply a box that was never drawn.

## What this does not show

- **These numbers are floors on tiny sets, not a ranking.** They are not comparable to 0.5355:
  different pictures and a different test set. Read the gap between the two tests, not the level.
- **Test 1's own number is inflated by design**, because 10 of its 13 test pictures come from line
  25, the same session as most of its training pictures. Test 2 is the honest reading of the same
  question.
- **6 of the 10 classes were never trained here** (Bubble Cluster, Bubble On 123, Bubble On Edge,
  HEMA Fragment), so their absence is a property of the data, not of the model.
- **One picture disagrees between the two records.** The picture dated 20260805 on line 31, pallet
  GHF0805142455, cavity 8, coded Fail7, has 2 boxes in the annotation file and 1 in the detection
  set's own label file. Both trainings use the detection set's version. Unresolved, and reported
  rather than quietly averaged away.
- **A plotting thread threw once**, `ValueError: y1 must be greater than or equal to y0`, inside the
  plotting code. It is cosmetic: both trainings finished and wrote their numbers. The built label
  files hold 0 boxes of zero width or height, so the bad box came from an augmented training batch
  and not from the labels.
- **The whole job ran twice**, on the same box with the same seed. Both runs produced the same
  numbers to four decimals, and 100 and 87 epochs again. The numbers are reproducible, so the gap is
  not run noise.

## Files

| File | What it holds |
|---|---|
| `summary.json` | every number the run produced, written by the run itself |
| `train_log.txt` | the full training log for both tests |
| `results_per_class.csv` | one row per test, test set and class |
| `../multilabel_split_20260921/split.csv` | the split, including the 8 held-out pictures and the reason for each |

Scripts: `experiments/multilabel/make_test_split.py` writes the split,
`vm/drivers/build_test_dataset.py` builds the two sets on the box with symlinks and no copy, and
`vm/drivers/run_yolo26_multilabel.py` trains and scores both tests.

To rebuild and rerun, as pranayp on the a100 box:

```bash
python experiments/multilabel/make_test_split.py
scp run/multilabel_split_20260921/split.csv <box>:/tmp/test_split.csv
scp vm/drivers/build_test_dataset.py vm/drivers/run_yolo26_multilabel.py <box>:/tmp/
sudo -u pranayp -H python3.12 /tmp/build_test_dataset.py
sudo -u pranayp -H python3.12 /tmp/run_yolo26_multilabel.py
```

No image was copied to the box. Both sets hold symlinks to the crops the existing detection set
already uses, so the model sees byte-identical pictures to the recorded baseline's.
