---
title: Multi-class and multi-label FMD data: what the data holds, what YOLO can do, and what to run
date: 2026-09-21
type: report
status: active
where: reports/multilabel/MULTILABEL_STRATEGY_20260921.md
---

# Multi-class and multi-label FMD data (2026-09-21)

> **Open question, 2026-09-22.** 33 pictures are named Extraneous Polymer in the newer folder and Fiber
> in the older library. Every model here takes the older library's name, so the Fiber and Extraneous
> Polymer per-class figures in this document are stated on that naming and are provisional until the
> client rules which folder is authoritative. The pictures, the boxes and the other classes are not
> affected. Detail: `docs/naming_open_question_20260922.md`.

This document answers the three questions left open at the meeting on 2026-09-21: how to prepare
data that holds more than one label per picture, whether YOLO26 can be used for it at all, and
whether YOLO can take two bounding boxes of different classes on one picture at training time. It
also records what the data actually holds, the options with their costs, the rules for reading the
results, the conflicts between documents that are in force today, the pitfalls, and the technical
debt.

Every number here is measured. The measurement is `experiments/multilabel/two_tier_eda.py`, its
output is `run/multilabel_eda/20260921/`, and
`experiments/multilabel/verify_two_tier_eda.py` re-derives each figure by a second route and
compares it with the published output: **102 checks, 0 failed**. The box counts are additionally
checked against the client's own counts in its ontology document, and they match on all 10 labels.

Statements about the tool come from the source of the exact build we train on
(`ultralytics` 8.4.142), read at that version, not from memory. Section 14 lists the files read.

---

## 1. The three questions and the short answers

| # | Question as it was put | Short answer | The evidence in one line |
|---|---|---|---|
| 1 | Can YOLO assign two bounding-box labels to one picture during training? | **Yes, and it needs no code change.** It is the documented normal case. | One label file per picture, **one row per object**, a class on each row. The tool's own format example is a picture holding two people and a tie. |
| 2 | Can YOLO26 work with multi-class / multi-label data, or do we move to a multi-level CNN? | **It depends on the label type, not on the count.** Detection: yes, natively. Classification (the image-level tags): no, not in 8.4.142. | Detection reads every row of the label file, and the only class collapse in the code is the `single_cls` flag we do not set. Classification wraps a folder-per-class reader and trains with a cross-entropy loss on one integer per picture. |
| 3 | How do we prepare multi-label data? | **Split the work by label tier.** A picture with two defect boxes is one detection file with two rows. A picture with one frame-level tag and one defect is two files, one per head. | 42 pictures hold two box labels and 13 hold one tag plus one box label, out of 8,409. The recipe for each case is in section 6. |

Two corrections to the framing in the meeting, both measured:

- The volume is small. **55 pictures out of 8,409 carry more than one label, which is 0.65 per
  cent.** Multi-label is not the shape of this dataset today. It is the shape production will
  have, and it is already the shape of the classification results, which is a different argument.
- The lead's reading, that YOLO will not do better with multi-class data, is **correct for the
  image-level tags and incorrect for the boxes**. The tags cannot be boxes because no one has ever
  drawn a box for one: the annotation job ran as 10 tasks, one per box label, and **no tag label
  appears as a box label anywhere in the 2,020 boxes**. A detector is not the right tool for a
  property of the whole frame, so the question "will YOLO do better" does not apply to them.

---

## 2. The words this document uses

Five words in the meeting were doing more than one job each. They are fixed here.

| Word | Means here |
|---|---|
| **Tag** | An image-level label. It describes the whole frame and has no location. "Low Dose Obstructing Region of Interest" is a tag: the frame was under-dosed. |
| **Box label** | An object-level label. It always carries a rectangle. "Fiber" is a box label: there is debris, and it is there. |
| **Tier** | Which of the two label families a label belongs to. The client's ontology defines exactly two. |
| **Multi-instance** | More than one object of the **same** class on one picture. Already everywhere: 216 of the 434 annotated pictures hold two or more boxes, and one holds 38. Nothing needs to change for this. |
| **Multi-label** | More than one **different** label on one picture, in any tier. This is the 55 pictures. |
| **Multi-class** | In the meeting this meant "a picture can hold a tag and a defect at once". Measured: 13 pictures. It is the same measurement as multi-label, so this document counts one thing, not two. |

So the meeting's two problem names are one problem, and it is 55 pictures wide.

---

## 3. What the data holds, measured 2026-09-21

### 3.1 The two tiers, and the pictures each label holds

| Label tier | Label | Pictures | Has a box anywhere |
|---|---|---|---|
| tag | Low Dose Obstructing Region of Interest | 1,952 | no |
| tag | Multiple Lenses | 1,439 | no |
| tag | Missing Primary Package | 1,427 | no |
| tag | Missing Lens | 324 | no |
| tag | Package Misalignment | 293 | no |
| tag | Lens Off Center | 258 | no |
| tag | Cavity Off Center | 183 | no |
| tag | HEMA Obstruction | 175 | no |
| tag | View Obstructed | 117 | no |
| tag | Dirty Strobe | 43 | no |
| tag | Dirty Camera | 25 | no |
| tag | Bubble Scatter | 7 | no |
| tag | Folded Lens | **0** | no |
| box | Foreign Matter | 1,283 | yes |
| box | Fiber | 362 | yes |
| box | Extraneous Polymer | 268 | yes |
| box | Bubble | 113 | yes |
| box | Wet Package | 67 | yes |
| box | Bubble Irregular | 44 | yes |
| box | Bubble Cluster | 36 | yes |
| box | HEMA Fragment | 20 | yes |
| box | Bubble On Edge | 14 | yes |
| box | Bubble On 123 | 14 | yes |
| box | Stretched Bubble | **0** | no |

Two labels in the client's ontology have no picture at all in this dataset: **Folded Lens** (tag)
and **Stretched Bubble** (box). A model trained today can never predict them. Any report that
claims coverage of the ontology has to say so.

### 3.2 The dataset by tier

| Measure | Pictures |
|---|---|
| Dataset, distinct pictures | **8,409** |
| with at least one tag | 6,243 |
| with at least one box label | 2,179 |
| with both tiers | **13** |
| tag only | 6,230 |
| box only | 2,166 |
| carrying more than one label, any tier | **55** (0.65 per cent) |
| labels per picture, tag tier | 1 tag: 6,243, 2 tags: 0 |
| labels per picture, box tier | 1 label: 2,137, 2 labels: 42 |

Four things in that table matter more than the multi-label count.

**The box data is 14 times smaller than the tag data, and the boxed set is the binding
constraint.** The annotation file holds 435 images, 434 distinct pictures, 2,020 boxes. Those 434
pictures are the entire detection training and validation set. The tag tier covers 6,243 pictures,
and the classifier line trains on 8,402. Every detection experiment is limited to 434 pictures, so
a new detection idea is tested on 88 validation pictures, not on thousands. This is the single
largest limitation on the detection line, and neither multi-label work nor a new architecture
moves it.

**Almost no picture holds both tiers.** Only 13 of 8,409 carry a tag and a box label. Of those 13,
**5 sit in the boxed set**. A model with two heads needs pictures where both heads have a target,
and this dataset offers 5. Two-head training is therefore not something this data can support
today; it is a design for the production set.

**No picture carries two tag labels.** The tag tier is single-label in this dataset: of 8,409
pictures, 6,243 carry exactly one tag and none carries two. Whether that is a property of the
frames or a property of the way the folders were built is an open question (section 12). The label
space permits it, and production can produce it, so the tag head should be built to allow it.

**The box file is single-label by workflow, not by nature.** Of the 434 annotated pictures, **47
carry more than one label in the pooled record** (42 with two box labels, 5 with a tag and a box),
while the annotation file gives every one of them exactly one box label. The annotation ran as 10
separate tasks, one per box label, and **no picture sits in two tasks**. An annotator working the
"Fiber" task could not label a bubble. The consequence is that co-occurring objects of another
class were never marked, which is missing-box noise, and it caps what recall can reach on any class
that shares frames with another.

### 3.3 The two shapes a multi-label picture takes

| Tier pattern | Reading | Pictures |
|---|---|---|
| two box labels | one picture, two different objects of two classes | 42 |
| one tag and one box label | one picture, one frame-level condition plus one object | 13 |

Every one of the 55 holds exactly two labels, so the pairs table and the picture table are the same
size.

### 3.4 Where the 55 come from, which changes what they mean

The 55 are produced by the folder structure, not by an annotator marking two defects. A picture
that sits in two folders is indexed under two labels. The largest group by far is one class pair
under two names:

| Label A | Label B | Pictures |
|---|---|---|
| Extraneous Polymer | Fiber | **33** |
| HEMA Fragment | HEMA Obstruction | 4 |
| Lens Off Center | Wet Package | 3 |
| Bubble | Fiber | 2 |
| Bubble Irregular | Foreign Matter | 2 |
| Low Dose Obstructing Region of Interest | Wet Package | 2 |
| Multiple Lenses | Wet Package | 2 |
| seven further pairs, one picture each | | 7 |
| **Total** | | **55** |

**33 of the 55 are one disagreement between two folders, and the frames settle it.** The newer folder
files those 33 pictures under "Extraneous Polymer"; the older library files the same 33 under
"Fiber". Each holds one object, so it is not two defects on one lens. Which of the two names is
right was tested against the pixels rather than assumed: the object was cropped from every one of
the 33 (34 boxes) and judged blind against two reference groups drawn from the same folders. Where
a folder agrees with itself the two classes separate cleanly: of the 17 pictures both folders call
Extraneous Polymer, 14 read as a thick strand or lump of varying width, and of the 17 both call
Fiber, 13 read as a thin constant-width filament. On the contested 33, 29 of the 34 objects read as
thin filaments, which is the Fiber description, not the Extraneous Polymer one. The likely reading
is therefore that the newer folder's name is wrong on these pictures rather than an alternative
word for the same object, so the question for the client is whether they were misfiled, not which
vocabulary wins. That matters past the 33: 267 pictures carry the Extraneous Polymer name in the
newer folder and 217 of them have no copy in the older library, so no second source has ever
checked their name.

The rest divide into genuinely mixed cases: 4 HEMA pairs (the same ring of excess monomer recorded
as an obstruction in one folder and as a bounded fragment in the other) and 9 pairs where a
frame-level condition sits on a picture that also holds a defect.

---

## 4. Why the tier decides the model, not the number of labels

A tag is a statement about the frame. "Low Dose Obstructing Region of Interest" says the saline
dose was short, which is true of the whole picture and of no object in it. There is nothing to
draw a rectangle around. A box label is the opposite: there is a thing, at a place, and its
location is part of the claim.

The client's ontology already makes this split, in its own words, in the section called
"Annotation Specification". It lists an "Image Level Labels (TAG)" set of 13 and an "Object-Level
Labels (Bounding Box)" set of 11. Our measured data matches it exactly, with two labels that have
no picture and no label in the wrong tier (0 of the 10 box labels used anywhere is a tag label).

So the honest reading of the meeting's question is:

| Label tier | Right tool | What it produces | What can be measured |
|---|---|---|---|
| tag | A classifier on the whole frame | one probability per tag, several can be high | per-tag precision and recall, macro over tags |
| box | A detector | boxes with class and position | per-class AP, matched IoU |

YOLO is a detector. It is the right tool for one tier and the wrong tool for the other, whatever
the number of labels per picture is. That is the whole of the answer to question 2.

---

## 5. What YOLO26 can and cannot do, checked against the pinned build

### 5.1 Detection: two classes on one picture is the normal case

The published format is one text file per picture, **one row per object**, each row
`class x_center y_center width height` in normalized coordinates. The documentation's own example
label file holds two people, class 0, and a tie, class 27, on a single picture.

The code agrees. In `verify_image_label` (the function that reads a detection label file at build
8.4.142), the reader takes every non-empty line as a separate object, requires exactly 5 columns
per line, and checks only that the largest class index stays below the number of classes. There is
no rule anywhere that the rows of one file must share a class. The only place classes are collapsed
is the `single_cls` flag, which we set only in the single-class crop arena and never in the
multiclass arena.

Two details of that reader are worth knowing, because both are silent:

- Identical rows are removed (`np.unique` over whole rows). Writing the same box twice with the
  same class loses one copy. The same box written under two different classes survives, because
  the rows differ.
- A picture with no label file is skipped by the trainer rather than treated as a background
  picture. One of our 435 annotated images has no box.

**What this means for our arena.** The multiclass arena already trains the harder half of the
problem: 1,643 training boxes sit on 346 pictures, several per picture, one class each. Adding a
second class to a picture's label file changes nothing in the pipeline. **What our data does not
yet contain is a single picture with two boxes of two different classes: 0 of 434.** The 42
pictures that hold two box labels in the folder record carry one box label in the annotation file.
So the capability is present and untested on our own data, and testing it costs one small
experiment, not a rebuild (section 13, step 2).

### 5.2 Classification: multi-label is not supported in 8.4.142

`ClassificationDataset` wraps `torchvision.datasets.ImageFolder`. Its samples are
`(path, class_index)` pairs, and the training loss for the task is
`F.cross_entropy(preds, batch["cls"])` on a single integer per picture. A picture cannot hold two
class indexes in that structure, and a cross-entropy target cannot express two correct answers.
Multi-label classification is therefore not available in the build we train on, and it is not a
configuration flag.

Upstream status, for the record: there is an open feature request for exactly this
(`multi_label` flag, sigmoid head, binary cross-entropy), and it lists four earlier attempts going
back more than two years, none merged. A second team asked the same design question in the same
tracker in the same period: whether to duplicate an image into several class folders for a
single-label pipeline, or to move to a multi-hot vector with a sigmoid loss. Their problem is our
problem, and their instinct matches the recommendation in section 7.

**We do not need YOLO for the tags.** The classifier line is ours, it is Keras, and changing its
last layer to a sigmoid with a binary cross-entropy loss is a small, local change. That is the
cheapest real capability we can add this week.

### 5.3 The three answers again, as a table for the lead

| Question | Answer | Why |
|---|---|---|
| Two box labels on one picture at training time | Supported today, no code change | One row per object in the label file; the class is per row |
| Multi-class multi-label detection | Supported, and it is the normal case | The detector has no concept of "one class per picture" |
| Multi-label classification of the tags | Not supported in our build | Folder-per-class reader, one integer label, cross-entropy loss |
| Tags as detection targets | Not possible with this data | No tag has ever been given a box, because the annotation ran one task per box class |

---

## 6. The four pictures that exist, and the preparation for each

| # | The picture | Pictures now | What the training input holds | Model and loss |
|---|---|---|---|---|
| 1 | one box label, one or more boxes | 434 (annotated), 2,137 in the pool | one label file, one row per object, one class | detector, detection loss (running today) |
| 2 | **two box labels on one picture** | **42** | the **same** label file, two rows, two different class numbers | detector, unchanged. No duplication, no second pass |
| 3 | one tag plus one box label | 13 | the picture appears in **both** inputs: once with its box label file, once as a row of the tag manifest | detector for the boxes, classifier for the tag |
| 4 | tag only, no box label | 6,230 | one row of the tag manifest, one column per tag | classifier with a sigmoid output |

Two further cases to design for, which the data does not hold yet but production will:

- **Two tags on one picture.** Zero today. The tag head must allow it, which rules out a softmax
  output: a softmax distributes one probability across the tags and cannot return two high values.
- **A picture with no label of a tier.** Every tagged picture is unlabelled for the box tier and
  the reverse, which is the normal state here. A two-head model has to mask the loss of the head
  that has no target for that picture, or it will learn "no object" from pictures nobody checked.

### Rules for the preparation

1. **Never duplicate a picture to express a second label.** Copying an image into two class
   folders doubles its weight in the loss and biases the class it was copied into. It also breaks
   the split if the split is rebuilt per class, because the copies can land on different sides.
2. **Never give a tag a full-frame box to force it into the detector.** It teaches nothing about
   location, it puts a rectangle over every real defect in the same label space, and it enters the
   box metric, so it will lower AP while looking like it added coverage.
3. **Build the split on the picture, not on the class folder.** After two-tier preparation one
   picture belongs to two lists, and a per-class split can put it on both sides.
4. **Record the second label even when the arena uses only one.** Today the single-label rule
   silently drops 55 labels. The drop list is published in
   `run/multilabel_eda/20260921/3_dropped_labels.csv` so that a later rule change can be evaluated
   on the same pictures without a rebuild.
5. **Keep the label rule visible per picture.** The current rule is "the older library decides".
   It is right for comparability with everything measured so far, and it is the reason 34 of the 36
   pictures that carry an Extraneous Polymer label are trained as Fiber. That is a decision, not an
   accident, and it should be written next to the label rather than applied in code.

---

## 7. The options, with what is known about each

| Option | What it is | Evidence for | Cost | Prior |
|---|---|---|---|---|
| **A. Keep the flat single-label space** (current) | 22 classes, one per picture, softmax classifier and 10-class detector | Everything measured so far rests on it: detector mAP50 0.535, classifiers 87.77 per cent pooled | zero | Keep as the baseline. Record that it costs 55 labels |
| **B. Multi-label tag head** | Sigmoid output, binary cross-entropy, one column per tag, the existing backbone | The tag tier is 6,243 pictures, 14 times the box tier. Tags are not mutually exclusive in production. We own the code | one head change, one retrain | **Strongest near-term gain.** Also the only change that removes the softmax limitation |
| **C. Cascade** | Detector first, then the tag classifier on the frame, joined at the frame | Both halves already run: YOLO26n 0.535 mAP50 for boxes; ResNet50 87.77 per cent pooled for classes | integration only, no new modelling | **Recommended for the boxes plus tags question.** Nothing to invent |
| **D. Two heads, one backbone, trained jointly** | Shared backbone, detection head and tag head, loss masked where a label is absent | Matches the ontology exactly: one model, two tiers | a custom trainer, plus a masking rule | **Blocked by the data:** 5 pictures hold both tiers. Correct target design, wrong week |
| **E. Tags as full-frame boxes** | Give every tag a box covering the frame | none | low | **Rejected.** See rule 2 in section 6 |
| **F. Multi-level CNN** (the lead's fallback) | A multi-level classifier architecture | Already built twice in this project: MultiLevel MultiScale at 88.05 per cent and MultiLevel Attention (SE) at 87.37 per cent on the 22-class set | a re-labelling exercise, not an architecture exercise | Use it as the tag head if option B needs a bigger model. It is not a new build |

Recommended order: **B**, then **C**, then revisit **D** when the production pictures arrive. **A**
stays as the baseline for comparability. **E** is recorded and closed.

One thing to say plainly about the fallback: "Multi level CNN" was proposed as the thing we move
to if YOLO cannot be proved useful. Two multi-level architectures have already been trained and
scored in this project, so that option is not a new direction. It is the same classifier line with
a different last layer, and it has the same relationship to the tags: it can predict them, it
cannot localise them.

A second idea from the same meeting was noted as too much for now: use the boxes the detector finds
as features for the classifier. It is the same cascade as option C in its stronger form, where the
classifier sees a crop around the detected object rather than the whole frame. It already has a
registry row, `res_two_stage_cascade`, ideated and unrun since the resolution work. Its two known
costs, both measured elsewhere in this repository: the crop pipeline that supplies such features
already exists and already helps recall, and the second stage can only train on the 434 pictures
that carry boxes, which is the same ceiling the detector is under. It is a sound idea with no new
evidence needed, and it sits behind the tag head in the order for that reason.

---

## 8. Data preparation, in full

### 8.1 The detection input (box tier)

- One text file per picture, named after the picture, beside it or under a `labels/` tree.
- One row per object: `class x_center y_center width height`, normalized to 0 to 1.
- Several rows per file are normal. **Two rows with two different class numbers are the case the
  lead asked about, and they need no special handling.**
- One `data.yaml` per arena, with the class names in index order and `nc` matching the head.
- Do **not** set `single_cls: true` outside the single-class crop arena; it collapses every class
  to 0 and would silently destroy the multiclass comparison.
- Do not change `nc` on the locked baseline. The head is built for `nc` at build time, so a class
  list change invalidates every recorded number in the multiclass arena.
- Every future run over the 42 two-box pictures must record whether both labels were present.

### 8.2 The tag input (tag tier), which does not exist yet

- One row per picture: content hash, path, production line, and **one column per tag** holding 0 or
  1. A picture with two tags holds two 1s. This is the multi-hot form, not one column holding a
  class name.
- The file must be built from the folder record so that a picture that sits in two folders gets
  both 1s rather than the winner of the priority rule. That is the point of the exercise.
- Train with a sigmoid output and a binary cross-entropy loss. Do not read accuracy: with tags
  ranging from 7 to 1,952 pictures, a model that predicts "no tag" for everything scores well on
  accuracy and is useless.
- Metrics that mean something here: per-tag precision, recall and F1, the macro average over the 13
  tags, and the exact-match ratio (how often the whole set of tags on a picture is right). Report
  the decision threshold with every number, because sigmoid outputs need one.

### 8.3 The split

- Build the split on the picture. One picture has one side, and it keeps that side in every arena
  it appears in.
- The existing per-line assignment covers 8,402 pictures and stays valid for the detection arena,
  because the boxed set is a subset of it.
- If the tag manifest is built, its rows must take the side the picture already has. A separate
  random split would put some pictures in training and test at once across the two tiers and
  inflate the tag scores.

### 8.4 What to do with the 55

Keep both labels in the two-tier manifest. Where an arena still needs one label per picture, keep
the current rule and publish the drop. The drops, measured:

| Label dropped | Pictures |
|---|---|
| Extraneous Polymer | 34 |
| Foreign Matter | 5 |
| HEMA Fragment | 4 |
| Fiber | 3 |
| Multiple Lenses | 3 |
| Lens Off Center | 3 |
| Low Dose Obstructing Region of Interest | 2 |
| Wet Package | 1 |
| **Total** | **55** |

The classes the rule keeps for those pictures: Fiber 33, Wet Package 7, Bubble 4, HEMA Obstruction
4, Bubble Irregular 2, Foreign Matter 2, Extraneous Polymer 2, Low Dose 1.

### 8.5 The label rule to test

33 of the 55 conflicts are Extraneous Polymer against Fiber, and 34 of the 36 pictures carrying an
Extraneous Polymer label are trained as Fiber. Separately, the classification line reports that
**142 of its 309 misclassified test pictures sit in the Foreign Matter, Fiber and Extraneous
Polymer family**, and its own record calls those labels overlapping in the dataset. That is a real
hypothesis with a cheap test: score one stored model again with those three classes merged into a
single debris class, and see how much of the error is discrimination and how much is naming. If
most of it is naming, the fix is a label rule, not a model.

---

## 9. How to read the results

### 9.1 Detection metrics already survive multi-label

Average precision is computed per class over that class's instances, so a picture holding two
classes contributes one instance to each class independently. Nothing about the metric breaks.
What changes is the arithmetic: 42 extra instances on 2,020 boxes is about 2 per cent, far below
the run-to-run spread we have not measured yet, so a whole-arena number will not move. Read
per-class AP, and read both classes of a co-labelled picture together.

### 9.2 The support cliff is the first thing to check

The detection arena validates on 88 pictures holding 377 instances. A class tested on 2 to 4
instances can score 0 or 100 per cent, and one picture moves its score by 25 to 50 points. The
recorded multiclass baseline shows the effect at full size: HEMA Fragment scored AP50 0.270 with
recall 0.000 on 2 validation instances, and Extraneous Polymer 0.665 on 3. **Never read a
per-class delta under about 15 instances as a signal**, and say the instance count next to the
number whenever one is quoted.

### 9.3 Micro against macro

In the same baseline, Bubble holds 227 of the 377 validation instances. The overall mAP50 of 0.535
is therefore mostly a statement about Bubble. When the question is about the small classes, report
the macro average over classes and say which average is being quoted, or the number will be read
as something it is not.

### 9.4 The tag head reads differently, and there is no obvious single number

- Per tag: precision, recall, F1, and the threshold they were computed at.
- Across tags: the macro average, because the tags differ 280-fold in support (7 to 1,952).
- Whole picture: exact-match ratio, the share of pictures where every tag is right. A model that
  predicts one tag per picture cannot score on a two-tag picture even when it gets one right, so
  this number is the honest one for the production question.
- Never accuracy, for the reason in section 8.2.

### 9.5 Report the debris family separately, always

Foreign Matter, Fiber and Extraneous Polymer overlap in the dataset by record. Any confusion matrix
in this project should be read with those three split out, and any accuracy quoted should be
quoted with the family's share of the error given alongside.

---

## 10. Conflicts between documents and rules now in force

These cannot all be true at once. Each is stated with the two sides.

1. **One label per picture against two labels per picture.** The per-line split work states, and
   the client has been told, that the dataset is "one label per picture". The two-tier measurement
   finds 55 pictures with two. Both are right only because the second rule silently discards 55
   labels, and neither document says so.
2. **The ontology says a picture may hold both tiers; the pipeline keeps one.** The ontology
   defines an image-level set and an object-level set with no rule of exclusivity between them,
   and 13 pictures carry both. The pipeline's priority rule keeps one and drops the other.
3. **Two labels are live in the ontology and have no pictures.** Folded Lens and Stretched Bubble.
   The ontology reads as current, so a reader will assume we can detect them.
4. **Clear.** 2,333 pictures, of which 128 carry a defect label and 2,205 carry none. Clear is out
   of the classifier set, and production will be full of it. The decision to treat it as a review
   status rather than a 23rd class is still open, and it changes every per-line table.
5. **The lead's reading of the tool against the tool's behaviour.** "YOLO will not be able to do
   better with multiclass/multi-label" is right for the tag tier and wrong for the box tier. The
   two tiers need two different answers, and the record should not carry a single verdict.

---

## 11. Pitfalls

1. **A tag given a full-frame box** will train the detector to point at the frame, will overlap
   real defects, and will enter the box metric. Rejected in section 7 for these reasons.
2. **Duplicating a picture into two class folders** doubles its weight in the loss and can break
   the split. It is the shortcut a single-label pipeline invites, and other teams are asking
   whether to take it right now.
3. **A softmax tag head** cannot return two tags. It will look fine on this data, because no
   picture holds two tags today, and it will fail silently in production.
4. **Reading accuracy on the tag manifest** rewards predicting the majority answer.
5. **Splitting by class folder** after two-tier preparation puts one picture on two sides.
6. **`single_cls: true`** outside the crop arena collapses all classes to 0.
7. **Changing the class count** on the multiclass arena invalidates the locked baseline (0.535
   mAP50), because the head is built for the count at build time.
8. **Empty label files are not backgrounds.** The trainer skips unlabelled pictures; 1 of our 435
   annotated images has no box, and its behaviour should be recorded rather than assumed.
9. **Duplicate rows in a label file are removed silently.** A deliberate duplicate, for example to
   raise the weight of a class, does nothing.
10. **The 4 to 5 pixel annotation noise sets a box-quality ceiling** of about 0.80 median IoU, and
    no label change moves it. Work on recall, not on box quality.
11. **A per-class delta read where support is absent.** See section 9.2. This has already produced
    one wrong reading in this project; HEMA Fragment and Extraneous Polymer moved by more than 0.2
    on 2 and 3 images.
12. **A new label rule applied to only part of the pipeline.** If the detector trains on merged
    classes and the classifier does not, the two halves of a cascade disagree at the frame.

---

## 12. Technical debt, and what cannot be claimed yet

1. **No multi-hot tag manifest exists.** The tag tier is only ever read as one folder name per
   picture. Everything in section 8.2 has to be built.
2. **No multi-label output in the classifier line.** The heads are softmax.
3. **The 55 second labels are recorded nowhere except the folder record.** They are not in the
   annotation file, not in the split files, and not in the classifier manifests.
4. **The tag tier's single-label property is unexplained.** Is it that no frame held two
   conditions, or that the folder structure only kept one? The folder record shows no picture with
   two tag labels, and the folder structure is one label per folder, so the data cannot separate
   the two explanations. Worth one question to the client.
5. **Missing boxes for co-occurring classes.** Because each annotation task covered one class,
   other objects in the same frame were not marked. The size of this is unknown and it caps recall.
   A sample re-annotation of 30 to 50 boxed pictures, marking every class present, would put a
   number on it.
6. **No noise floor.** Every delta in this project is single-seed on 88 validation pictures. The
   seed-spread run is still the highest-value cheap experiment outstanding, and it comes before
   any new number below about 0.05.
7. **No matched-IoU for the multiclass arena** (mAP only).
8. **The classification line's debris-family error share (142 of 309) is recorded but not
   decomposed** by label rule.
9. **The 8 unlabelled HEMA pictures** and the two zero-picture labels are unresolved.
10. **Fourteen of the client's 16 chart cells disagree with our counts by one or two images.**
    The source agrees with us, and the charts have not been regenerated.

---

## 13. The program

Ordered, cheapest and highest value first. Each step states what it settles.

| # | Step | What it settles | Cost |
|---|---|---|---|
| 0 | **Seed-noise floor**, 3 seeds, stock config | The delta below which nothing can be claimed. Every other number depends on it | 3 runs, about 30 minutes of GPU |
| 1 | **Build the multi-hot tag manifest** from the folder record, one column per tag, with the line and the existing split side | The input for every tag experiment. Also removes the 55-label drop from the tag tier | hours, no GPU |
| 2 | **Prove the two-class picture on our own data**: take 4 to 6 of the 42 two-box pictures, write their real label lines (two rows, two classes), and run a short smoke train with the stock config | That the pipeline carries two classes on one picture end to end, not just in the format specification. Answers question 1 with our own run | minutes of GPU |
| 3 | **Train the tag head**: the existing ResNet50 with a sigmoid output and binary cross-entropy, on the manifest, and compare against the same backbone with softmax on the current single-tag assignment | The cost of the single-label assumption, in points of macro F1 and exact-match ratio. Option B | about 1 hour of GPU |
| 4 | **Re-score the debris family** with Foreign Matter, Fiber and Extraneous Polymer merged | How much of the 142-of-309 classification error is naming rather than discrimination. A label-rule answer if it is large | one retrain, or zero if a stored confusion matrix is re-read |
| 5 | **Cascade**: detector plus tag classifier joined at the frame, reported on the 13 both-tier pictures | Whether the two-tier design the ontology describes works in practice, and what each half contributes. Option C | integration, no new training |
| 6 | **Two-head joint training** | The target design. Needs the production pictures, because only 5 pictures here hold both tiers | after step 3 and step 5 |
| 7 | **Sample re-annotation** of 30 to 50 boxed pictures for all classes present | The size of the missing-box noise, which caps recall on co-occurring classes | annotation time, no GPU |

Steps 1 to 5 can be run without touching the detector, which matters because the detection line is
gated on the seed-noise floor and a 434-picture annotation set.

---

## 14. Evidence and sources

**Measured in this repository (2026-09-21).**

| What | Where |
|---|---|
| The two-tier measurement, 102 verified checks | `experiments/multilabel/two_tier_eda.py`, `experiments/multilabel/verify_two_tier_eda.py` |
| Its output: label space, tier table, the 55, the pairs, the drops, the box tier | `run/multilabel_eda/20260921/` (11 files) |
| The folder record it reads | `run/line_eda/20260916/image_md5_records.csv`, 12,079 rows |
| The box annotations | `data/annotations.xml`, 435 images, 2,020 boxes |
| The two label tiers, in the client's words | `docs/Manufacturing Condition Ontology V1.docx` |
| The per-label box counts we match against | the ontology's "Object Sizes" table |
| The 55 and the older library's priority rule, independently | `run/client_eda/20260917/`, `src/make_line_splits.py` |

**The tool, read at the version we train on (`ultralytics` 8.4.142).**

| Claim | Source read |
|---|---|
| One label file per picture, one row per object, class per row | the published detection dataset format, and its example with two people and a tie |
| The reader enforces 5 columns per row and no class per picture | `verify_image_label`, `ultralytics/data/utils.py` |
| Identical rows are removed silently | the same function |
| Classification reads folder-per-class and returns one index | `ClassificationDataset`, `ultralytics/data/dataset.py` |
| The classification loss is cross-entropy on one integer | `v8ClassificationLoss`, `ultralytics/utils/loss.py` |
| Multi-label classification is an open request, not a feature | the tracker's open request and the four earlier attempts it lists |

**Related workstream records this document depends on and does not repeat:**
`reports/yolo26/yolo26_mc_baseline_and_hypotheses.md` (the multiclass detector baseline and its
per-class table), `HANDOFF.md` section 10 (the classifier line, the pooled 87.77 per cent and the
142-of-309 figure), `experiments/README.md` (the governance, do and do not lists, and the arena
rule), and `reports/lines/LINE_TAG_ANALYSIS_20260916.md` (the pooled pool and the priority rule).

## 15. For the lead

A short, self-contained message covering the same three answers, with no local file names, is in
`reports/multilabel/teams_message_multilabel_20260921.md`. Delivery is the user's call.
