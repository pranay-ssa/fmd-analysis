---
title: "Ticket 018: client questions out"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/018-client-questions.md
---

# 018: Client questions out

Type: task, HITL. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: none.

## Resolution (2026-10-15)

The draft is written at `reports/eda_full/client_questions_20261015.md`. Sending it
is the user's, since the user sends lead-facing messages directly.

Eight questions, in the order they change what we can say:

0. The scale itself, which is now the top item. The client's own gate inverts to about
   15.34 microns per pixel and agrees with neither 18.1165 nor 18.25, so either the
   declared cut is not exactly 300 microns or our published scale is wrong by about 18
   percent.
1. A written lens diameter, the annotation guide, or any document naming the real
   size of something in the frame. This is the only thing that settles item 0.
2. The code that means two different defects.
3. The `F2_FOV` naming anomaly.
4. Whether Bubble On Edge and Bubble Over 123 Mark are still live classes.
5. Whether the Low Dose and Extraneous Polymer annotation tasks are finished.
6. Whether `P2_BST` is Stretched Bubble.
7. Whether the 300 micron rule gates Foreign Matter and Fiber as well as Extraneous
   Polymer, and whether HEMA Obstruction stays unconditional.
8. The two data hygiene items: the picture annotated twice, and which view of the 113
   figure the client wants quoted.

The draft carries no local path, no file name and no internal reference, and no em
dashes.

## Question

Which questions have to reach the client, in what order, so that the answers
arrive before the tickets that depend on them finish?

## The questions, in priority order

0. **The scale itself, and this is now the top question.** The client's own gate
   inverts to about **15.34 microns per pixel**, from two independent boundaries
   taken five weeks apart. That is about 18 percent below the 18.1165 we have
   published and about 16 percent below the 18.25 the lead quoted, and it agrees with
   neither. Two readings are possible and only the client can settle which: either
   the declared cut is not exactly 300 microns, or our published scale is wrong,
   which would also mean the 14,200 micron lens diameter it rests on is nearer 12,024
   microns. Everything we have quoted in microns moves by that 18 percent if it is
   our number that is wrong.
1. **A written lens diameter, or the FMD Annotation Guide.** Ticket 008 found that
   no received document states the real size of anything pictured. Ask for the lens
   diameter the client considers correct, or the annotation guide, or any document
   naming the real size of a feature in the image. This is the only thing that
   settles question 0 outright.
2. **The `P3_HE` collision.** The same code means HEMA Fragment in the Sep-22
   project and HEMA Obstruction in the production files. Which reading is right,
   and should the code change?
2. **`F2_FOV`.** The usual scheme is `P1_`, `P2_`, `P3_`. The production files use
   `F2_FOV` for View Obstructed where the Sep-22 project defines `P2_FOV`. Which
   is canonical?
3. **Bubble On Edge and Bubble Over 123 Mark.** Both newer projects dropped these
   labels. The old library holds 90 and 79 boxes. Are they still classes?
4. **The Low Dose and Extraneous Polymer tasks.** 76 of 1,952 Low Dose images
   carry the tag and 124 of 269 Extraneous Polymer images are boxed, each inside a
   single contiguous job. Are those tasks finished?
5. **`P2_BST`.** Still inferred as Stretched Bubble, never confirmed.
6. **The 300 micron rule's scope.** Does it gate Foreign Matter and Fiber as well
   as Extraneous Polymer, and does HEMA Obstruction stay unconditional?
7. **The 113 feature disagreement.** The published figure was name-based. On content
   identity the overlap between the library folders is larger, not smaller, because
   renamed duplicates are invisible to a name route. The corrected figures are
   reported beside the published one rather than replacing it. Confirm which view
   the client wants quoted.
8. **One picture is annotated twice.** `20241102_004906_L24_C5_9471.bmp` and
   `20241102_004906_L24_C5_9471_0.6629.bmp` are byte-identical files and both carry
   the same eight shapes. One of the two should be dropped from the annotation set,
   or the duplication explained.
7. **Extraneous Polymer against Fiber.** The 33-picture disagreement, still open
   since 2026-09-22, and the email's "when in doubt call it Fiber" guidance bears
   directly on it.

## Deliverable

A short message for the lead, in the user's own voice, that asks these in one
pass and states what each answer changes.

## Acceptance

1. Each question states what changes when it is answered, so the client can
   prioritise.
2. The message carries no local paths and no internal ticket numbers.
3. The answers, when they arrive, are recorded as a new line rather than by
   editing anything already sent.
