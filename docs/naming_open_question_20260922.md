---
title: The Fiber and Extraneous Polymer naming question, and why the current results stand
date: 2026-09-22
type: reference
status: active
where: docs/naming_open_question_20260922.md
---

# The Fiber and Extraneous Polymer naming question

## The open question

**When the older library and the newer folder give the same picture different class names, which name
is authoritative?** 33 pictures are named Extraneous Polymer in the newer folder and Fiber in the older
library. The question went to the client through the lead on 2026-09-22 and is unanswered.

Until it is answered, the Fiber and Extraneous Polymer per-class figures in every result we hold are
stated on the older library's naming and are provisional. Nothing else is provisional.

## What the model is actually shown

| Step | What happens today | Why it does not damage the result |
|---|---|---|
| The detector's labels | come from the older library's box annotations. 30 of the 33 pictures are in that file and every one is marked Fiber. The other 3 carry no boxes at all, so no model sees them. | the model is shown a fiber and told Fiber, which is what the frames show |
| The classifier's class folders | the dataset builder ranks the three folders and takes the first that holds a picture, older library first. All 33 sit in the Fiber class. | same answer as the detector, and no picture sits in two class folders |
| The tag tier | Extraneous Polymer is a box class and never a frame-level tag | there is no path where a picture is fed as a tag and learns a box class |
| Two classes on one picture | 0 of the 434 annotated pictures carry two classes in the box file | nothing was ever trained as two things at once |

## Why the results are not useless

1. **No model learned the disputed name.** Both pipelines take the older library's name, so those 33
   pictures trained as Fiber. There is no run in which a fiber object was labelled Extraneous Polymer.
2. **The frames agree with the label the models were given.** Of the 34 contested objects, 29 read as
   thin filaments, which is the Fiber description. The label learned matches the pixels.
3. **Training and test use the same rule.** A test picture and a training picture of the same kind of
   object are named the same way, so the numbers are internally consistent and comparable with each
   other. A difference between two source folders cannot flatter a score in this setup.
4. **The exposure is two classes, not the dataset.** The pictures, the boxes, the tag tier, the other
   eight detection classes and the multi-label finding are untouched by the answer.

## What the answer would change

| | Today, older library naming | If the client rules for the newer folder |
|---|---|---|
| Fiber, annotated detection set | 61 pictures | 31 pictures |
| Extraneous Polymer, annotated detection set | 17 pictures | 47 pictures |
| Fiber, pooled classifier set | 362 pictures | 328 pictures |
| Extraneous Polymer, pooled classifier set | 268 pictures | 302 pictures |

34 labels move: 33 of them assigned to Fiber today, plus 1 assigned to Bubble. That is 12.7 percent of
the pictures carrying the Extraneous Polymer name and 9.4 percent of those carrying Fiber. The per-line
split assigns pictures to train and test by class, so moving them also moves them across the split,
which means both classes' numbers would be re-run rather than recalculated by hand.

## What we do until then

- Any report quoting a Fiber or Extraneous Polymer per-class figure says it is on the older library's
  naming, and that the class boundary is pending the client's answer.
- We do not quote the newer folder's picture count for that class as if it were the class we train on.
  The class we train on is the older library's definition of it.
- We do not change the class mapping on a guess. The change is one mapping, and the affected models are
  re-run once the answer arrives: same pictures, same boxes. Registry entry `R4` carries it.

## Where the evidence sits

| What | Where |
|---|---|
| The blind read of the 34 contested objects against the two agreed groups | `run/ep_fiber_check/20260921/` |
| The evidence sheets, four of them, plus one png per contested frame | `run/ep_fiber_check/20260922/` |
| The class counts, the labels dropped and the pictures involved | `run/multilabel_eda/20260921/` |
| The message the lead took to the client | `reports/multilabel/teams_message_correction_20260922.md` |
