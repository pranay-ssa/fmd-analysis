---
title: Count reconciliation between the two EDA workbooks
date: 2026-10-23
type: result
status: active
where: reports/draft2_eda_20261023/workbook_reconciliation_20261023.md
---

# Count reconciliation between the two EDA workbooks

Both workbooks were read side by side, and every headline number was recomputed
directly from the nine annotation XML files. This report states where the numbers
differ, which stated assumption produces each difference, and which differences are
not yet explained. Neither workbook is treated as the reference; the annotation
files are.

Workbook A = the Draft 2 EDA workbook (edited version of the draft).
Workbook B = the onboarding EDA workbook.

## First result

Almost every difference between the two workbooks comes from four deliberate
counting choices, not from arithmetic mistakes. Recomputing from the annotation
files confirms the per-file totals in both workbooks. After the four choices are
aligned, the counts agree. Two items remain open: the HEMA Obstruction count
(86 vs 174) and small residual tag deltas of 1 to 14 pictures per class.

## The four counting choices

### 1. What counts as a labelled picture (largest gap: 6,785 vs 4,785)

Workbook A reports 6,785 pictures with usable labels; workbook B reports 4,785
labelled pictures. The gap is about 2,000 pictures and it is almost entirely the
Clear pictures. Workbook A counts an unannotated pass picture as usable (2,156
Clear pictures). Workbook B requires an explicit annotation, and only 177 Clear
pictures carry one; the other Clear-folder pictures sit in B's "not annotated"
pool (3,926 pictures). Same library, different definition of "labelled".

### 2. Which objects belong to a class (the bubble question)

The bubble numbers differ exactly as suspected: grouping.

- Workbook A keeps the older bubble labels separate. Pure Bubble: 746 pictures /
  10,070 objects; merged bubble class (Bubble + irregular + stretched): 750
  pictures / 10,205 objects. Bubble On Edge (14 pictures, 90 boxes) and Bubble On
  123 (13 pictures, 79 boxes) are kept as reference rows outside the class.
- Workbook B folds every older bubble label into Bubble: On Edge, On 123,
  Bubble Irregular, P2_BI, P2_BST and the old-library plain-name Bubble boxes.
  Result: 11,214 boxes in 889 pictures.

The raw annotation files contain 11,749 bubble-like box entries across all files
before any deduplication. Both published numbers are consistent subsets of that
raw total; B's grouping is wider and its population is the full library, A's is
narrower and its population is the filtered analysis set. Neither is "wrong";
they answer different questions. A decision is needed on which grouping is
canonical (the guide merges irregular and stretched but is silent on On Edge and
On 123).

The same choice affects the other object classes: workbook B maps the old
library's plain-name boxes into guide classes (for example Wet Package 663 = 593
coded + 70 plain-name), while workbook A counts only current-code objects
(Wet Package 593). For the size-flagged classes, workbook A counts the micron
threshold tags (Foreign Matter 171, Fiber 136, Extraneous Polymer 33, HEMA 95)
and workbook B counts every box of the class (625 / 245 / 150 / 103 boxes). The
threshold tag totals match the raw files exactly.

### 3. Deduplication and filtering (the 1 to 14 deltas per tag)

Lens presentation and image-condition tag counts, workbook A vs workbook B:
Missing Primary Package 1,426 vs 1,427; Multiple Lens 1,433 vs 1,444; Lens Off
Center 953 vs 967; No Lens 323 vs 326; Dirty Camera 326 vs 329; Low Dose 215 vs
216; Folded Lens 237 = 237; Dirty Strobe 43 = 43; Cavity Off Center 184 = 184;
Field of View 24 = 24; Bubble Scatter 6 = 6; Package Misalignment 2 = 2.

Both workbooks remove duplicate copies of the same picture, then apply their own
label-validity filter on top. Workbook A additionally drops pictures whose only
labels are outside the current class list, which removes a few pictures per class.
The classes with zero delta are the ones where every tagged picture survives both
filters. Both agree on the library size itself: 12,079 files, 10,614 unique
pictures, 1,465 duplicate copies.

### 4. Pair definition in the tag-combination tables

Workbook A's combination table counts every picture carrying both tags, including
pictures that carry additional tags. Workbook B's headline table counts only
pictures whose tags are exactly that pair, and reports the inclusive number
separately (Multiple Lens + Lens Off Center: 445 exact vs 667 inclusive).
Workbook A reports 661 for the same inclusive measure. Recomputed from the raw
files at filename level the inclusive count is 664; the remaining 3-picture
difference is the deduplication filter. The same pattern holds for Dirty Camera +
Low Dose (A 72, B 64 exact / 72 inclusive) and Lens Off Center + Low Dose
(A 17, B 8 exact / 23 inclusive). One convention difference, not a data conflict.

## Rulings applied (2026-10-23)

The counting decisions are now fixed as follows, and the recomputed numbers confirm
workbook A's approach is in line with each one:

1. Clear: the meeting rule is confirmed. A Clear-folder picture carrying a defect
   tag counts under those defect tags only; defect-free Clear-folder pictures are
   Clear. Workbook A's 2,156 Clear pictures follow this rule. Workbook B's 177 is
   the explicitly annotated subset of the same folder, not a conflicting count.
2. Bubble: the Draft 2 merge is Bubble + Bubble Irregular + Bubble Stretched +
   P2_BB, and nothing else. Recomputed from the raw files: 11,580 merged-bubble box
   entries in 911 pictures before deduplication; Bubble On Edge and Bubble On 123
   (27 pictures) have zero overlap with the merged set, so keeping them separate is
   clean. Workbook A's 750 pictures / 10,205 objects is this merge after
   deduplication and filtering.
3. Guide adherence: F2_FOV is the only code used in the data (24 pictures, P2_FOV
   zero); workbook A already reports the two spellings as one class. No gap.
4. HEMA: the HEMA class is P3_HE (HEMA Fragment) boxes only; HEMA Obstruction
   (P2_HMO, 174 pictures in the raw files) stays a separate legacy tag. The two
   have zero overlap. The earlier 86 vs 174 difference is this deliberate
   separation, not an error; it is closed.
5. Workbook convention: future workbooks show exact-only and inclusive tag-pair
   tables as two separate tables, each header naming its definition. This rule is
   recorded in the project skill for every future deliverable.

## Residual notes

- Split convention: workbook A splits 70/30, workbook B 80/20. Both are stated
  openly; a single agreed ratio should be chosen before model work.

## The 1 to 14 per-class deltas: fully explained and verified

The image library was hashed on the storage server (12,079 files, 10,614 unique
contents, matching both workbooks), and the tag counts were recomputed through
every stage of the pipeline. Each stage reproduces one column of the two workbooks
exactly, so no delta is left unexplained:

| Stage | Multiple Lens | Lens Off Center | No Lens | Dirty Camera |
|---|---|---|---|---|
| 1. Raw union of all nine files, by filename | 1,611 | 990 | 331 | 329 |
| 2. After removing duplicate copies (content hash) | 1,444 | 967 | 326 | 329 |
| 3. After winner-takes-all resolution (newest file wins) | 1,439 | 957 | 325 | 329 |
| 4. After the analysed-set eligibility filter | 1,433 | 953 | 323 | 326 |

- Stage 2 reproduces workbook B's tag counts exactly, for every class (1,427
  Missing Primary Package, 1,444 Multiple Lens, 967 Lens Off Center, 326 No Lens,
  329 Dirty Camera, 216 Low Dose, 174 HEMA Obstruction).
- Stage 3 reproduces workbook A's "earlier full count" column exactly (1,439 /
  957 / 325 / 329).
- Stage 4 reproduces workbook A's published counts exactly: the recomputed matrix
  holds 6,785 pictures and every tag column matches the workbook (1,433 / 953 /
  323 / 326 / 215 / 1,426 / 237 / 184 / 43 / 6 / 2 / 86). The eligibility filter
  drops pictures whose labels are all in size-gated families without the required
  size flag, plus unlabelled rows.
- Clear: 2,333 pictures in the Clear folder, 177 of them annotated. The
  unannotated remainder is 2,156, exactly workbook A's Clear count; workbook B's
  177 is the annotated subset of the same folder.

So the difference between the two workbooks is: workbook B counts every label
anywhere in any file (union), workbook A counts one resolved label set per picture
under the current rules. Both are now verified against the raw data; neither is an
error.

## Verification method

Each of the nine annotation XML files was parsed and per-file image, tag and box
totals were recomputed. They match workbook B's annotation-file table exactly.
Tag, box and pair counts above were recomputed at filename level; content-level
(MD5) deduplication could not be reproduced without the image files, so the final
1 to 14 picture deltas per class are attributed to the documented filters rather
 than independently re-verified.
