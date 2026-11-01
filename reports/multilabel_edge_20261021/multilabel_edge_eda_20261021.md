---
title: Multi-label Edge EDA - report for approval
date: 2026-10-21
type: report
status: active
where: reports/multilabel_edge_20261021/multilabel_edge_eda_20261021.md
---

# Multi-label Edge EDA: report for approval

This report is self-contained. Every number below was computed from the built
label matrix (one row per distinct picture, content-hash keyed) and is
re-derivable from the workbook that accompanies it. It is the approval gate
for the train/test split: nothing is split until this report is accepted.

## 1. The experiment frame

The experiment mirrors the client's edge algorithm: for Foreign Matter, Fiber,
Extraneous Polymer and HEMA, the micron gate tag IS the class. A picture that
carries one of those four defect families without the matching gate tag does
not qualify for the class; a picture whose only defect content is such a plain
family is outside the dataset entirely. The label frame has 23 columns:

- 4 gate classes: Foreign Matter micron gate (171 pictures), Fiber micron gate
  (168, of which 137 carry the gate tag and 31 are the flipped EP/Fiber
  pictures), Extraneous Polymer micron gate (33), HEMA micron gate (94).
- 7 defect classes: Bubble 862 (Bubble Irregular and Stretched Bubble folded
  in, per Draft 2), Bubble Cluster 430, Bubble On 123 13, Bubble On Edge 14,
  Wet Package 146, Bubble Scatter 6, HEMA Obstruction 86 (legacy; see section
  5).
- 11 presentation tags: Missing Primary Package 1,426, Multiple Lens 1,433,
  No Lens 323, Cavity Off Center 184, Folded Lens 237, Lens Off Center 953,
  Dirty Camera 326, Dirty Strobe 43, Low Dose 215, View Obstructed 24,
  Primary Package Misalignment 2.
- Clear 2,166: folder-derived, see section 2.

Class names and codes follow Draft 2 of the FMC Annotation Guide; the workbook
carries the legend sheet and the previous-name to new-tag change table.

## 2. What Clear means, and how many pictures are usable

Clear is a folder-derived class, not a computed absence. A picture belongs to
Clear when its canonical path sits in a Clear class folder of the two Updated
libraries; 2,333 pictures do. Defect annotations from the older annotation
vintages rescue a folder picture into its defect class (84 pictures carry such
rescued labels; most were already defect-labeled by their winning file, and
the rescue added 2 genuinely new Bubble Cluster labels). Pictures outside the
Clear folders are not Clear, whatever their annotation state.

The universe is the 10,614 distinct pictures of the three libraries, labeled
by winner-takes-all resolution (newest annotation files first, then the Sep-22
update, then the old library). Three drops take it to the usable set:

- 153 pictures whose only defects are plain-family FM/Fiber/EP/HEMA with no
  gate tag.
- 3,676 unannotated pictures: 1,907 are name-listed by the Sep-22 export with
  zero shapes drawn (0 tags = no tags), and 1,769 appear in no annotation
  file at all. Dropped per the user's ruling that unannotated pictures are
  not required for a multi-label experiment.

That leaves the final usable set: **6,785 pictures = 4,619 labeled (defect or
presentation tag) + 2,166 Clear.** Every Clear row is reliable by folder
membership.

## 3. The multi-label distribution

- 5,383 pictures carry exactly one label, 673 two, 424 three, 207 four, 71
  five, 20 six, 5 seven, 2 eight.
- The matrix has **192 distinct label vectors** over 23 columns: ample strata
  for the stratifier and no empty-class problem. The rarest column, Primary
  Package Misalignment, has 2 positives and will be reported as
  untrainable-by-count with its exact test counts when the split lands.
- 1,069 pictures carry at least one defect class; 637 carry two or more. The
  multi-defect pictures are the reason this is a multi-label experiment and
  not a single-label one.
- 4,048 pictures carry at least one presentation tag. Low Dose carries an
  additional reliability flag because that task is only partially annotated.

Subset check (a column whose positives never appear without another column):
every HEMA-gate picture also carries a Bubble box (94 of 94; 768 Bubble
pictures carry no HEMA gate, so the negative supervision exists and this is a
training consideration, not a data wall). The presentation-tag subsets from
earlier drafts disappeared under the folder rule for Clear.

## 4. The EP/Fiber ruling, applied

The client's ruling is that ambiguous EP/Fiber cases count as Fiber. The
affected set was verified picture by picture: exactly 33 pictures were
annotated Fiber in the old library and EP in a newer vintage, and this set
matches, one for one, the earlier blind-review effort whose verdicts read 29
of 34 boxes as thin filaments, that is, Fiber. The EP micron gate also sits
on 33 pictures, but only 2 of those are in the flip set; the equality of the
two counts is a coincidence and was never used as evidence. In the EDA
reading the 33 count as Fiber; in the split reading the 31 that carry no gate
tag drop out.

## 5. Discrepancies carried forward, not resolved here

1. Draft 2 deprecates Bubble On Edge and Bubble On "123" as labels. This
   experiment keeps both as their own classes on the user's decision; folding
   them in would move 27 library-only pictures into Bubble.
2. Draft 2 retires HEMA Obstruction with no successor tag. The column is kept
   as a legacy class (86 legacy tags). The production HEMA boxes belong to
   the HEMA gate column, not here; the first matrix build conflated the two
   and was corrected.
3. The `P3_HE` code collision (HEMA Fragment in one vintage, boxes in
   another) and the `F2_FOV` alias remain unmerged per the frozen crosswalk;
   the client questions on them are still out.

## 6. What happens on approval

The split is built on the 6,785-picture usable set minus the 106 gate-less
plain carriers still in the matrix (75 mixed plus the 31 flipped): a split
universe of **6,679 pictures**. 70/30 two-way, iterative stratification over
the 23-column matrix, seed 42, grouped on content md5 so content twins cannot
cross splits, saved as a split file with a recipe record. Rare classes
(Bubble On 123: 13, Bubble On Edge: 14, Primary Package Misalignment: 2, and
any column under about 30 positives) will be reported with their exact test
counts and wide-interval warnings. Verification follows the standing triple
check: hand-typed expected values, a byte-identical rerun, and an independent
second derivation of every headline.

## 7. Verification status of this report

- The full image inventory was re-verified against the shared VM on
  2026-10-21: all 12,079 library bitmaps hash byte-identical to the local
  manifest (0 mismatches, 0 coverage gaps), and their distinct content-hash
  count is exactly 10,614. Nothing was written to the VM tree.
- The matrix reproduces the known census anchors: Bubble Cluster 428 plus the
  2 rescued labels, Bubble Scatter 6, and the gate-tag counts for Foreign
  Matter (171) and Extraneous Polymer (33).
- Items parked for the verification ticket, not silently accepted: the Fiber
  gate-tag picture count reads 137 against the crosswalk's 136 (a one-picture
  identity question); Folded Lens reads 237 against the Sep-22-only 178
  because the production files also use the code; and the 84-picture rescue
  set is to be re-derived picture by picture from the raw exports.
