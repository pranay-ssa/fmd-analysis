---
title: Teams message: correction on the multi-label count, and what the frames show (2026-09-22)
date: 2026-09-22
type: report
status: active
where: reports/multilabel/teams_message_correction_20260922.md
---

# Teams message: correction on the multi-label count (2026-09-22)

Self-contained: no cross-references, no local paths, no script names. Every claim carries its number
in the same sentence. No em dashes. Technical terms are explained the first time they appear. Four
images are attached to the message and each is described at the end.

---

**Correction on the multi-label count, and what the pictures show**

In our discussion I reported that 55 pictures carry more than one defect label. **The count is right.
The reading of it was wrong, and I would rather correct it now than let it stand.** Three things I
need from you are at the end, with the evidence in between.

**What the 55 actually are**

Each of the 55 sits in **both** label sources: the older defect library and the newer objects folder.
The two sources name the same picture differently, and that difference is what our tooling counted as
a second label.

| What the two labels are | Pictures | Is there a second defect on the frame? |
|---|---|---|
| One object under two names: named Extraneous Polymer in one source, Fiber in the other | 33 | No. One object, two names |
| One object under two names across the two label tiers: HEMA Fragment and HEMA Obstruction | 4 | No. One ring of material, two names |
| The two sources name different classes on the same frame | 9 | One frame shows it, eight do not |
| A whole-picture condition beside an object label | 9 | No. The whole-picture label needs no rectangle |

So **37 of the 55 are one object under two names**, and **none of the 55 shows two defects we can
point at**. A box is the marked area around one defect, and **0 of the 434 pictures that hold boxes
carry two classes in their annotation**.

**The pictures settle the Fiber question**

For the 33 pictures the two sources disagree about, we cut the object out of the frame and judged it
blind against two reference groups taken from the same sources. The groups separate cleanly: of the
17 objects both sources call Extraneous Polymer, 14 are a thick mass of varying width; of the 17 both
call Fiber, 13 are a thin filament of near-constant width. **Of the 34 contested objects, 29 are thin
filaments**, which is the Fiber description. The frames side with the older library.

The same read reaches the 9 pictures where the two sources pick different classes. With the known
boxes drawn on the frame, the second class is **not visible as a separate object in 8 of the 9**. One
frame holds a dark particle away from its boxes, which would fit the Foreign Matter family.

**What this changes**

A second label that comes from a filing difference is not a second defect, so it cannot teach a model
anything about pictures with two defects. There is currently **no confirmed picture with two defects
anywhere in our data**, so the short proof run we planned, where one picture is written with two
classes and trained, cannot run on today's data as it stands. It moves to the first production data we
receive.

Those pictures also cannot carry a model on their own. Trained on just the 47 of the 55 that hold
boxes, the detector scores **0.47** when the test pictures share the capture session of the training
pictures, and **0.08** when a whole production line is held out. The drop is the finding: at that size
the higher number is the model recognising a session it has already seen, not detecting.

The whole-picture labels are untouched: **6,243 pictures carry at least one**, and the change that
lets a classifier return two of them at once is unaffected.

**What we need from you**

1. **When the two sources disagree, which name should we train on?** On the 33, our evidence points to
   the older library's Fiber. We can keep applying that rule, but the naming authority is yours to
   confirm. It is not a small edge: the rule we apply when a picture carries two names drops the
   Extraneous Polymer name from 34 of the 268 pictures that carry it.
2. **Were those 9 pictures meant to record a second defect?** One frame carries a dark particle away
   from its boxes. The other 8 show nothing of the second class outside the marked areas.
3. **Can the unverified Extraneous Polymer pictures be confirmed?** **217 of the 267** pictures the
   newer folder calls Extraneous Polymer have no counterpart in the older library, so no second source
   has ever checked their name. If the same filing difference happened there, that class is affected
   at a scale we cannot see from our side.

**What we cannot claim yet**

- The form read is one pass, on 68 objects, by one reader. The originals are available for any frame
  that is challenged.
- Nothing here says the newer folder is wrong in general. It says the two sources disagree on the
  pictures both hold, and on the 33 the frames side with the older library.

**Key takeaways**

- 55 pictures carry two labels, and 37 of those are one object under two names. The count was never
  wrong; the meaning was.
- 0 of the 434 pictures with boxes carry two classes of object, so the two-defect case has no example
  in our data today.
- On the 33, the older library's Fiber name matches the frames: 29 of the 34 contested objects read as
  thin filaments.

**The four images attached**

1. **Three groups of objects side by side.** Six objects from each group: the ones both sources call
   Extraneous Polymer, the ones both call Fiber, and the contested ones. The two agreed groups
   separate by eye and the contested objects follow the Fiber group.
2. **Three objects from each group, larger.** The same comparison at a size where the difference in
   form is plain: a thick mass of varying width against a thin filament.
3. **Every object in the check, 68 in total.** The whole set with nothing filtered out, so the group
   counts can be checked against the images directly.
4. **The nine frames where the two sources name different classes.** Each frame is shown with the
   boxes that exist drawn on it and the second name written beneath, so you can see for yourself
   whether a second object is there.

Tell me which of these you want taken forward and which naming should be treated as correct, and I
will write it up properly with the numbers behind it.
