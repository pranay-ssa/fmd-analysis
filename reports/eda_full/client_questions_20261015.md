---
title: Client questions from the full-coverage EDA
date: 2026-10-15
type: report
status: active
where: reports/eda_full/client_questions_20261015.md
---

# Client questions from the full-coverage EDA

Ticket 018. A draft for the lead, to be sent in the user's own voice. Three items
need a decision and five need a confirmation. Question 1 changes what we can quote.
No local paths, no internal references, no file names appear below on purpose.

---

**Update on the full-coverage defect review, and three things we need from you**

We have finished the pass over all 10,614 images in the three ICube libraries, with
every label resolved against the newest annotation export. Most of it is clean and
the workbook follows separately. Three items need your input, and the first one
matters most.

**1. The micron scale does not reconcile, and this one changes what we can quote.**

We had been using about 18.12 microns per pixel, and 18.25 was mentioned in a
meeting. Both trace back to our own estimate of the lens diameter. That diameter is
not stated in any document we hold.

The annotations disagree with both. The size gate in the new export switches on at a
boundary that works out to about 15.3 microns per pixel. The older 647 micron gate
switches on at a boundary that gives the same 15.3. Two independent boundaries, taken
five weeks apart, agree with each other and agree with neither of our figures.

Two readings are possible. Either the 300 micron cut is not exactly 300 microns as
applied, or our published scale is wrong by about 18 percent, which would put the
lens diameter nearer 12,000 microns than the 14,200 we assumed.

What we need: the lens diameter you consider correct, or the annotation guide, or any
document stating the real size of something visible in the frame. Until we have it,
every micron figure we publish carries an 18 percent question mark, and we would
rather flag that than quote a number we cannot stand behind. Pixel figures are
unaffected.

**2. One code is used for two different defects.**

In the older annotation project that code is HEMA Fragment and it is drawn as a box.
In the new production export the same code is HEMA Obstruction, also drawn as a box,
while HEMA Obstruction is a whole-image flag in the older project. We have kept the
two as separate entries and not merged them, so nothing is hidden, but the counts
depend on which reading is right. Please confirm.

Related, and smaller: View Obstructed is coded `P2_FOV` in the older project and
`F2_FOV` in the new export. The usual pattern is P1, P2 and P3, so `F2` stands out.
Please confirm the intended code and whether they are one class.

**3. Two data hygiene items.**

One image is annotated twice, under two file names whose contents are byte-identical.
Both records carry the same eight shapes. One of the two should probably be dropped,
or the duplication explained.

The 113 figure we gave you for images the library folders label differently was
computed by file name. Measured by content, the overlap is larger, not smaller,
because some pictures were renamed between folders, so a name-based count cannot see
them. We are keeping the 113 labelled as the name-based figure it is and reporting the
content figures beside it. Tell us which view you want quoted.

**Confirmations we also need, all small**

- Does the 300 micron rule gate Foreign Matter and Fiber as well as Extraneous
  Polymer? The data shows it does, and it shows HEMA Obstruction is flagged on every
  image that carries it, so that class is not size gated at all. Confirm both.
- Are Bubble On Edge and Bubble Over 123 Mark still live classes? Both newer
  annotation exports dropped them and only the older library holds them. One of the
  two is the class our detection performs worst on, so it matters.
- Are the Low Dose and Extraneous Polymer annotation tasks finished? Each carries
  annotation inside one short block of its folder and nothing outside it, which reads
  as a partly worked task rather than a rare class.
- Is `P2_BST` Stretched Bubble? We inferred it rather than confirmed it.
