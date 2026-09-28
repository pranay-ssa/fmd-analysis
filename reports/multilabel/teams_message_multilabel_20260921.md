---
title: Teams message: multi-class and multi-label data, the three questions answered (2026-09-21)
date: 2026-09-21
type: report
status: superseded
where: reports/multilabel/teams_message_multilabel_20260921.md
---

Superseded on 2026-09-22 by reports/multilabel/teams_message_correction_20260922.md. That message
corrects this one in two places: the 42 pictures it calls two object labels are two sources naming one
object, and the 55 as a whole is a filing difference between two sources rather than evidence of
pictures with two defects. These notes did not leave the office and were never sent.

# Teams message: multi-class and multi-label data, the three questions answered (2026-09-21)

Self-contained: no cross-references, no local paths, no images, every claim carries its number in
the same sentence. No em dashes. Jargon is defined the first time it appears.

---

**Multi-class and multi-label data: what we found**

Three questions came out of today's meeting. Here are the answers, each with the number behind it.

**1. Can YOLO be given two bounding boxes of different classes on one picture at training time?**

Yes. It needs no change to our code. The label file holds one line per object and each line carries
its own class, so a picture holding a fiber and a bubble is two lines with two class numbers. This
is the documented normal case for the tool, and its own format example is a picture holding two
people and a tie.

Our data holds no such picture yet: **0 of the 434 annotated pictures carries two boxes of two
different classes.** We do already train many boxes of one class on a single picture (1,643 boxes
on 346 training pictures, and one picture carries 38 boxes), so the pipeline handles the harder
half already. We will prove the two-class case with a short run rather than leave it as a claim.

**2. Can YOLO26 work with multi-class and multi-label data, or do we move to a multi-level CNN?**

It depends on the label type, not on how many labels a picture holds. Our labels sit in two tiers,
and the client's own ontology document already splits them that way:

| Tier | Labels | Pictures | Right tool |
|---|---|---|---|
| Frame-level tags (dose, focus, package position) | 13 | 6,243 | a classifier on the whole image |
| Object labels, each with a bounding box | 11 | 2,179 | a detector |

**Detection: yes, already.** A detector treats every object on a picture as its own case, so two
objects of two classes need nothing new.

**Classification of the tags: no, not in the version we run.** The classification side of the tool
reads one folder per class and trains with a single-answer loss, so it cannot return two tags for
one picture. This is a known gap in the tool rather than a mistake in our setup, and the request
for it has been open upstream for more than two years without a merged fix. We do not need it: our
own classifier code can be switched to a two-answer output, which is a small and local change, and
it is the cheapest real step available to us.

**A tag cannot be turned into a detector target.** No tag has ever been given a bounding box. The
annotation work ran as ten separate jobs, one per box label, so "under-dosed" never had a rectangle
to learn.

**3. How do we prepare multi-label data?**

By label tier, not by count:

| The picture | Pictures | What the training input holds |
|---|---|---|
| One object label | 434 | one label file, one line per object |
| **Two object labels** | **42** | the **same** label file, two lines, two class numbers |
| One tag plus one object | 13 | the picture appears in both inputs, once with boxes and once as a tagged row |
| Tag only | 6,230 | one row of the tag list, one column per tag |

Two rules we will hold to. We never copy a picture into two class folders to express a second
label, because that doubles the picture's weight during training and can move it across the train
and test split. And we never give a tag a full-frame box, because it would teach the detector
nothing about location and would overlap every real defect.

**How big is this in our data?**

**55 of our 8,409 pictures carry more than one label, which is 0.65 per cent.** It is not the shape
of this dataset today. It is the shape production will have, and that is the reason to prepare now
rather than later.

Of those 55, **33 are one disagreement between two folders rather than two defects on one lens**.
The newer folder files them under "Extraneous Polymer", the older library files the same pictures
under "Fiber". There is one object per picture, so it is not two defects, but we did not assume the
two names were interchangeable: we cropped the object out of all 33 and judged them blind against
two reference groups taken from the same folders. Where a folder agrees with itself the classes
separate cleanly (14 of the 17 agreed Extraneous Polymer objects are a thick mass of varying width,
13 of the 17 agreed Fiber objects are a thin filament), and 29 of the 34 contested objects read as
thin filaments. So these look like fibers that the newer folder named Extraneous Polymer, and the
question for you is whether they were filed wrongly, not which of two vocabularies should win. The
same question reaches wider than these 33: 217 of the 267 pictures the newer folder calls
Extraneous Polymer have no counterpart in the older library, so no second source has ever checked
their name.

A second number points at the same place. In the five per-line classifier run, **142 of the 309
misclassified test pictures sit in the Foreign Matter, Fiber and Extraneous Polymer family**, and
the record already notes that those three labels overlap in the dataset itself. We want to measure
how much of that error is naming rather than recognition, and the measurement is cheap.

One finding to carry forward: the annotation job ran one task per class, so **47 of the 434
annotated pictures carry a second label in the folder record that the box file does not carry**.
Objects of another class in the same frame were never marked. We do not know how many, and it sets
a ceiling on what recall can reach for classes that share frames.

**What this means**

- The multi-label question has two different answers: detection can do it today, classification
  cannot in our build, and the label tier decides which answer applies.
- The rule matters more than the count. 0.65 per cent of pictures are affected now, and production
  is not guaranteed to give us one defect per image.
- The binding limit is not label style but data volume for boxes: box annotations cover 434
  pictures while the tags cover 6,243, so every detection result rests on 88 validation pictures.
- The first steps are cheap and do not touch the detector: build a tag list with one column per
  tag, switch the classifier to a two-answer output, and prove the two-class picture with a short
  training run.
- Two labels in the ontology have no pictures at all today (Folded Lens and Stretched Bubble), so
  no model can predict them yet, and no report should imply otherwise.
