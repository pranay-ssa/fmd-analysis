---
title: The 2026-09-22 annotation export, what it covers and what it changes
date: 2026-09-23
type: reference
status: active
where: docs/annotations_update_20260923.md
---

# The 2026-09-22 annotation export

Audit of `data/Updated Annotations 20260922.xml`, which arrived 2026-09-23 09:49. Built by
`experiments/annotations/audit_updated_annotations.py` (32 self-checks) and checked by
`experiments/annotations/verify_annotation_audit.py` (**33 checks, 0 failed**). Every figure
below comes from those two runs; the tables are in `run/annotations_audit_20260923/`.
Nothing in the file has been ingested into a dataset.

## 1. What arrived

| Property | Value |
|---|---|
| File | `data/Updated Annotations 20260922.xml`, 1,609,831 bytes |
| SHA-256 | `f08a9f34ad13aaec7e115df59c0589b5ecdcb910807785670062c14e15d662c1` |
| CVAT project | id 3, "ICube Data 20260915", created 2026-09-15 19:18:16Z, updated 2026-09-22 11:53:16Z |
| Dumped (export time) | 2026-09-22 11:53:56Z |
| Tasks / jobs | 11 tasks, 56 jobs |
| Labels defined | 22 |
| Images | 6,097, every one 2448 x 2048 |
| Annotations | 4,930 image-level tags, 183 boxes (179 of them rotated) |
| Annotator | `bbarrine` (same account as the older library), every tag and box marked `manual` |

This is a **second CVAT project, not an update of the old one.** The older file is project
id 2, "Sweta Annotations Defect Library": 435 images, 2,020 boxes, 0 tags, 10 labels. The
two projects share no label name and no task name. They share 46 image file names: 45 of
them sit in the new project's Extraneous Polymer task and one in its Low Dose task
(section 6).

The images the file refers to are **not on this machine**. `data/incoming/` held the ICube
library and was deleted 2026-09-17; the new drop lives on the VM at
`/home/amd100-user/FMD_Data_26082026/fmd_temp_images`. So this audit reads the annotation
file only: it counts what is annotated, not what the pixels show. Content identity between
the 46 shared file names and the old library's copies was not re-checked here for that
reason; `docs/armor_blob_transfer_20260916.md` records that 1,287 of the library's 1,465
files are byte-identical to files in the new drop.

## 2. The label set is a different scheme: 22 codes

The new project labels every annotation with a code, and the legend is not in this
repository, so the mapping below is derived (derivation in section 2.2). Eleven of the
codes are pinned outright by a CVAT task name sitting on a blob folder of that name.

### 2.1 What each label holds

| Code | Class (name our dataset uses) | Kind | Instances | Pictures | Where the pictures sit |
|---|---|---|---|---|---|
| P1_MPP | Missing Primary Package | tag | 1,552 | 1,427 | its own folder only |
| P1_ML | Multiple Lenses | tag | 1,442 | 1,442 | Multiple Lenses 1,435, plus 7 elsewhere |
| P2_LOC | Lens Off Center | tag | 803 | 803 | own folder 258, Multiple Lenses 538, HEMA Obstruction 7 |
| P1_NL | Missing Lens | tag | 325 | 325 | own folder 324, Dirty Camera 1 |
| P1_COC | Cavity Off Center | tag | 183 | 183 | its own folder only |
| P1_FL | Folded Lens | tag | 178 | 178 | Multiple Lenses only |
| P2_HMO | HEMA Obstruction | tag | 174 | 174 | its own folder only |
| P2_DC | Dirty Camera | tag | 125 | 125 | own folder 25, Multiple Lenses 95, Lens Off Center 4, Extraneous Polymer 1 |
| P2_LD | Low Dose Obstructing Region of Interest | tag | 100 | 100 | own folder 76, Multiple Lenses 11, HEMA Obstruction 7, Lens Off Center 6 |
| P2_DS | Dirty Strobe | tag | 42 | 42 | its own folder only |
| P2_BSC | Bubble Scatter | tag | 6 | 6 | own folder 5, Lens Off Center 1 |
| P1_PPM | Package Misalignment | tag | 0 | 0 | defined, never used |
| P2_FOV | View Obstructed | tag | 0 | 0 | defined, never used |
| P3_EP | Extraneous Polymer | box | 131 | 127 | Extraneous Polymer 121, Multiple Lenses 4, Missing Lens 2 |
| P2_BB | Bubble | box | 25 | 4 | Extraneous Polymer only |
| P3_FM | Foreign Matter | box | 9 | 6 | Extraneous Polymer only |
| P3_FIB | Fiber | box | 4 | 2 | Extraneous Polymer, Multiple Lenses |
| P2_BST | Stretched Bubble | box | 4 | 4 | Low Dose only |
| P3_HE | HEMA Fragment | box | 4 | 3 | Multiple Lenses only |
| P2_BC | Bubble Cluster | box | 3 | 1 | Extraneous Polymer only |
| P2_WP | Wet Package | box | 2 | 1 | Extraneous Polymer only |
| P2_BI | Bubble Irregular | box | 1 | 1 | Extraneous Polymer only |

The box tier is small and lopsided: **183 boxes over 137 pictures**, of which 124 pictures
and 167 boxes sit in the Extraneous Polymer task. Outside that one folder the whole file
holds 16 boxes on 13 pictures (4 in Low Dose, 2 in Missing Lens, 10 in Multiple Lenses).

### 2.2 How the codes were read, and the one that is inferred

The evidence, in the order it was used:

1. **Task name against folder name.** Each task covers exactly one blob folder. Task
   `P3_EP` sits on `Updated ICube Objects 20260915/Extraneous Polymer`, `P1_MPP` on
   `Missing Primary Package`, `P2_LD` on `Low Dose`, and so on for 11 tasks. That pins
   P3_EP, P1_COC, P1_DC, P1_DS, P2_LOC, P2_LD, P2_BSC, P2_HMO, P1_NL, P1_MPP and P1_ML.
2. **Acronyms** against the ontology's two annotation lists
   (`docs/Manufacturing Condition Ontology V1.docx`): P3_FIB Fiber, P3_FM Foreign Matter,
   P3_HE HEMA Fragment, P2_BB Bubble, P2_BC Bubble Cluster, P2_BI Bubble Irregular,
   P2_WP Wet Package, P1_PPM Primary Package Misalignment, P2_FOV Field Of View
   Obstructed, P1_FL Folded Lens.
3. **Elimination, for P2_BST.** It is the only box code left, and Stretched Bubble is the
   only ontology box name left that matches a "B-ST" abbreviation. Two ontology box names
   are left over with **no code at all**: Bubble On Edge and Bubble Over 123 Mark.

So one mapping (P2_BST = Stretched Bubble) is inferred rather than pinned. It is low risk
(the alternative readings need a code that does not exist), but it should be confirmed
with the client alongside the other questions in section 8.

### 2.3 Two box classes lost their label

The ontology lists 13 image-level (tag) labels and 11 object-level (box) labels. The new
project defines all 13 tags and 9 of the 11 box classes. **Bubble On Edge and Bubble Over
123 Mark have no label in this project.** The older library annotated both, 90 and 79
boxes respectively, and Bubble On 123 is the class our detectors fail on hardest
(AP50 0.132, 0% recall, 32 val instances).

The tag side is complete but the picture is the mirror image: the two tag labels that are
defined and never used, Package Misalignment and View Obstructed, are exactly the two
categorical blob folders with no task (293 and 117 images, section 3).

### 2.4 The label set against ours

The new project's 22 classes are the 22 classes our pooled split is built on, **minus
Bubble On 123 and Bubble On Edge, plus Folded Lens and Stretched Bubble.** Stretched
Bubble now has 4 boxes; it had none in the older library, and the ontology still says its
object-size statistics are being gathered.

## 3. What the export covers of the 2026-09-16 drop

The drop is 10,614 images in two folders (`docs/armor_blob_transfer_20260916.md`). This
export covers 6,097 of them, 57.4 per cent.

| Blob folder | Images in the drop | Images in this export | Covered |
|---|---|---|---|
| Updated ICube Categorical Classes 20260915 - Low Dose | 1,952 | 1,952 | 100% |
| ... Multiple Lenses | 1,439 | 1,437 | 99.9% |
| ... Missing Primary Package | 1,427 | 1,427 | 100% |
| ... Missing Lens | 324 | 324 | 100% |
| ... Package Misalignment | 293 | 0 | **0%** |
| ... Lens Off Center | 258 | 258 | 100% |
| ... Cavity Off Center | 183 | 183 | 100% |
| ... HEMA Obstruction | 175 | 175 | 100% |
| ... duplicates | 143 | 0 | not a class |
| ... View Obstructed | 117 | 0 | **0%** |
| ... Dirty Strobe | 42 | 42 | 100% |
| ... Dirty Camera | 25 | 25 | 100% |
| ... Bubble Scatter | 6 | 5 | 83% |
| Updated ICube Objects 20260915 - Extraneous Polymer | 267 | **269** | 101% |
| ... Clear | 2,333 | 0 | **0%** |
| ... Foreign Matter | 1,282 | 0 | **0%** |
| ... Fiber | 328 | 0 | **0%** |
| ... HEMA | 20 | 0 | **0%** |

Two things stand out:

- **The Objects folder is essentially unannotated.** Only Extraneous Polymer has a task.
  Clear, Foreign Matter, Fiber and HEMA (3,963 images) have none, so the folder that
  supplies Fiber, Foreign Matter and Extraneous Polymer to our detector has labels for one
  of its three classes.
- **The Extraneous Polymer task holds 269 images where our copy of the folder holds 267.**
  Two images in the task are not in our copy. The task's own size is 270, so one frame of
  the task is empty as well. This is a small number, but it means the export is not a
  subset of our copy of the folder, and it should be reconciled before the file is used.

The categorical side is close to complete: 5,828 of 6,384 images, and the 556 that are
missing are the two unannotated classes (410), the `duplicates` folder (143) and three
single images dropped from the Multiple Lenses and Bubble Scatter tasks.

## 4. Two tasks are unfinished, and the shape of the tags says so

Per task, measured against the class the task's own folder is named for:

| Task | Folder | Images | Carrying the folder's class | No annotation at all | Last update |
|---|---|---|---|---|---|
| 26 P1_MPP | Missing Primary Package | 1,427 | 1,427 (100%) | 0 | 2026-09-17 17:28 |
| 27 P1_ML | Multiple Lenses | 1,437 | 1,435 (99.9%) | 0 | 2026-09-22 11:53 |
| 25 P1_NL | Missing Lens | 324 | 324 (100%) | 0 | 2026-09-17 14:56 |
| 20 P2_LOC | Lens Off Center | 258 | 258 (100%) | 0 | 2026-09-17 13:13 |
| 16 P1_COC | Cavity Off Center | 183 | 183 (100%) | 0 | 2026-09-17 13:13 |
| 24 P2_HMO | HEMA Obstruction | 175 | 174 (99.4%) | 0 | 2026-09-17 14:00 |
| 19 P1_DS | Dirty Strobe | 42 | 42 (100%) | 0 | 2026-09-17 13:13 |
| 17 P1_DC | Dirty Camera | 25 | 25 (100%) | 0 | 2026-09-17 13:13 |
| 23 P2_BSC | Bubble Scatter | 5 | 5 (100%) | 0 | 2026-09-17 13:13 |
| 22 P2_LD | Low Dose | 1,952 | **76 (3.9%)** | **1,876** | 2026-09-17 13:13 |
| 15 P3_EP | Extraneous Polymer | 269 | **121 (45.0%)** | **145** | 2026-09-17 13:13 |

**The two low-coverage tasks are low in a way that a rare class cannot explain.** CVAT cuts
each task into jobs of about 125 frames, and in both tasks the annotation sits inside a
single contiguous job:

- **Low Dose (task 22, 16 jobs).** Jobs covering frames 0 to 1874 (15 jobs, 1,875 images)
  carry nothing at all. Job 42, frames 1875 to 1951, is 77 images and 76 of them carry the
  Low Dose tag. A class that was judged rare would be spread across the folder; 76 tags in
  one contiguous block of 77 images, with zero in the 1,875 before it, is one job having
  been worked.
- **Extraneous Polymer (task 15, 3 jobs).** Job 15, frames 0 to 124, holds 124 boxed images
  out of 125. Jobs 16 and 17, frames 125 to 269 (144 images), carry nothing.

This is an inference from the shape, not a statement from the annotator, and the honest
alternative is that both folders are pools where the class really is that rare. The shape
is against the alternative in both cases, and the pattern of the finished tasks is against
it too: in every completed categorical task almost every image carries the folder's class
(100% in seven of nine), which is what applying the folder's label to a whole job looks
like, not what grading each image individually looks like.

**Either way the operating consequence is the same: do not read the export as "the Low
Dose class has 76 pictures".** Read it as "Low Dose is annotated for frames 1875 to 1951 of
its task". One short answer from the annotation owner settles it.

Across the export, **2,021 of the 6,097 images carry no annotation at all** and 2,145 carry
no tag. Every one of those 2,021 sits in those two tasks; no other task in the file has a
single image with neither a tag nor a box.

## 5. The re-annotation overlap, which is the measurement we owed

46 file names appear in both annotation files. 45 of them carry boxes in both, giving 46
matched box pairs (one picture carries two boxes in the older library). Comparing each
older-library box with the new file's box on the same picture:

| Statistic | Value |
|---|---|
| Matched box pairs | 46 |
| Pairs with byte-identical geometry | **0** |
| IoU, minimum | 0.241 |
| IoU, 25th percentile | 0.585 |
| IoU, median | **0.719** |
| IoU, mean | 0.705 |
| IoU, 75th percentile | 0.849 |
| IoU, maximum | 0.967 |

**Zero of 46 pairs have the same coordinates**, so this is a genuinely independent second
pass over the same objects, not a re-export of the older library's boxes. Both passes are
by the same account (`bbarrine`), about three weeks apart, so what this measures is **one
annotator's repeatability**, not agreement between two annotators.

That matters for a claim the project has been carrying: the "median IoU around 0.80 across
all conditions" figure has been described as a data limit from annotation noise of 4 to 5
pixels. This gives the first direct number behind that. Two passes by the same annotator on
the same objects land at a median IoU of 0.719, with a quarter of the pairs below 0.585.
That is the floor a detector is being scored against, and it sits below the ceiling the
models already reach, which is the same direction the 0.80 figure pointed in. It does not
by itself prove the whole gap: the model IoU is measured against a different and much
larger set of objects, and 46 pairs is a small sample, all 46 of them Extraneous Polymer
objects. The claim it supports is narrower and still worth having: two passes by the same
annotator on the same objects do not agree on the box, and the disagreement is at the scale
of the gap we have been calling a data limit. Worth a proper run against a wider class mix
once the images are reachable.

## 6. The Extraneous Polymer against Fiber boundary: third opinion, not a blind one

All 46 matched pairs are called **Extraneous Polymer** in the new file. Thirty of them are
pictures the older library files under **Fiber**; the other 16 the older library also
calls Extraneous Polymer.

Read against the open question in `docs/naming_open_question_20260922.md` (33 pictures are
Extraneous Polymer in the newer folder and Fiber in the older library, the answer is with
the client), this file adds a data point and **does not settle the question**:

- The annotator was working inside a CVAT task whose folder is named "Extraneous Polymer",
  so the class name was in front of them. A blind read it is not.
- The new pass nonetheless boxes 30 of the 30 contested pictures it holds as Extraneous
  Polymer objects, which is the newer folder's name, while our own blind read of the pixels
  found thin filaments in 29 of 34 contested objects, which is the older library's name.

The two sources therefore still disagree, and the disagreement now has a third vote for the
newer name that is worth recording rather than weighing. The rerun stays `R4`, one class
mapping, waiting on the client.

## 7. What this changes, and what it does not

**It changes nothing already published or trained.** No model has read this file. The
pooled 8,409-picture set, the 22 classes, the splits, the line models and every detection
number are built from the older library and the folders, and are untouched.

**It is the first new labelled data since the library.** What it offers, with the caveats
above:

| It can feed | Why, with the number |
|---|---|
| The re-annotation overlap measurement | 46 independent box pairs, median IoU 0.719 (section 5) |
| A larger box tier | 137 pictures against the 434 we train the detector on. The overlap by file name is 45, so the union is 526 pictures by name, not 571. The gain is real but modest, and it is 127 Extraneous Polymer pictures |
| A frame-level tag tier | 3,952 pictures carry at least one tag, over 11 of the 13 tag classes, every one `manual`. This is the tier the classifier's categorical classes were built from |
| The EP against Fiber rerun | 30 of the 33 contested pictures are in this file with fresh boxes (section 6) |
| Folded Lens and Stretched Bubble | 178 and 4 annotations on two classes that had none |

**It cannot feed a model as it stands, for three reasons.** Two of the 22 classes have no
label at all, so a dataset built from this file would silently lose Bubble On 123 and
Bubble On Edge, which is the worst class in our detection results. The Low Dose class is
annotated for 3.9 per cent of its folder. And the two Objects folders that carry Fiber and
Foreign Matter have no annotations, so pooling this file with the older library is where
its value sits.

## 8. Questions for the client, in priority order

1. **Is the Low Dose task finished?** 76 of 1,952 images carry the tag and all 76 sit in
   the task's last job.
2. **Is the Extraneous Polymer task finished?** 124 of 269 images are boxed and all of them
   sit in the task's first job.
3. **Confirm the code legend**, in particular `P2_BST` = Stretched Bubble.
4. **Why have Bubble On Edge and Bubble Over 123 Mark lost their labels?** The ontology
   keeps both and the older library annotated both.
5. **When are Package Misalignment (293 images) and View Obstructed (117 images)
   annotated?** Their labels exist in the project and have no annotations.
6. **Are the Objects folders to be annotated at all?** Clear 2,333, Foreign Matter 1,282,
   Fiber 328, HEMA 20.
7. **Why does the Extraneous Polymer task hold 269 images when our copy of the folder
   holds 267?**

## 9. Evidence

| What | Where |
|---|---|
| Builder (29 self-checks) | `experiments/annotations/audit_updated_annotations.py` |
| Verifier (33 checks, 0 failed, hand-typed expected values) | `experiments/annotations/verify_annotation_audit.py` |
| Protocol and pitfalls | `experiments/annotations/README.md` |
| Tables and the SHA-256 | `run/annotations_audit_20260923/` (10 files) |
| The drop's own record | `docs/armor_blob_transfer_20260916.md` |
| The open EP against Fiber question | `docs/naming_open_question_20260922.md` |
| The ontology the label set is measured against | `docs/Manufacturing Condition Ontology V1.docx` |
