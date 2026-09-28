---
title: Reverse EDA, does every picture in the September drop carry an annotation
date: 2026-09-23
type: report
status: active
where: docs/reverse_eda_annotation_coverage_20260923.md
---

# Reverse EDA: annotation coverage of the September drop

This reads the annotation files against the image inventory instead of the other way round. The
question it answers is whether the pictures that carry no annotation are pictures the older library
already annotated, which would mean they need no further work.

**Answer: almost none of them are. 380 of the 10,614 pictures in the drop are rescued by the older
library file. 6,158 pictures carry no annotation in either file, and 6,000 of those have no copy in
the older library at all.**

## 1. The three records and how they join

| Record | What it holds |
|---|---|
| Image inventory of 2026-09-16 | one row per image file with its content hash: 12,079 rows, 11,936 of them the dataset (the 143 files in the duplicates subfolder are held back) |
| New annotation file, 2026-09-22 | 6,097 image elements, 4,930 tags, 183 boxes |
| Older annotation file, 2026-08-25 | 435 images, 2,020 boxes |

The join key is the picture itself, the content hash of the file, not the file name. One picture can
sit in more than one folder, and the same picture can carry a different file name in two folders.
Matching on the name alone would miss 38 of the older library's files, because the drop copies of
those carry a score suffix the library copy does not: for example the library's
`20241110_060953_L24_C6_9354.bmp` sits in the drop as `20241110_060953_L24_C6_9354_0.9821_0.5907.bmp`.

The universe is 10,614 distinct pictures, which is the figure the client EDA of 2026-09-17 reached
by the same rule: 4,230 files in the Objects folder, 6,241 in the Categorical folder, and 177
pictures that appear in neither and come from the older library.

Every count below was recomputed by a second script that parses the files a different way and joins
on file names instead of folder paths. 93 checks, 0 failed.

## 2. The headline

| | Pictures | Of the drop |
|---|---|---|
| Carry a new annotation, tag and/or box | 4,076 | 38.4% |
| No new annotation, but the older file boxes them | 380 | 3.6% |
| No annotation in either file | 6,158 | 58.0% |
| **With an annotation of some kind** | **4,456** | **42.0%** |

The 4,076 breaks down into 3,939 pictures carrying a tag only, 124 carrying a box only, and 13
carrying both. The new file holds 6,097 image elements, and 2,021 of them are empty, which is how
4,076 pictures and 6,097 elements reconcile.

## 3. Where the 6,158 sit, and why each is missing

| Folder | Class | Pictures with nothing |
|---|---|---|
| Objects | Clear | 2,206 |
| Categorical | Low Dose | 1,875 |
| Objects | Foreign Matter | 1,208 |
| Objects | Fiber | 298 |
| Categorical | Package Misalignment | 293 |
| Objects | Extraneous Polymer | 144 |
| Categorical | View Obstructed | 117 |
| Objects | HEMA | 8 |
| Older library only, no copy in an Updated folder | | 6 |
| Categorical | Multiple Lenses | 2 |
| Categorical | Bubble Scatter | 1 |

Those 6,158 split by cause, and the split is the useful part:

- **2,022 sit in a class folder the new file has a task for.** These are Low Dose (1,875),
  Extraneous Polymer (144), Multiple Lenses (2) and Bubble Scatter (1). The task exists and the
  frames were not worked, so this is unfinished work inside a task, not an absence of scope.
- **4,130 sit in a class folder with no task at all, and 6 more sit only in the older library
  folder.** The 4,130 are Clear, Foreign Matter, Fiber, HEMA, Package Misalignment and View
  Obstructed. No task was created, so these need a scope decision before they need an annotator.
- **164 of the 6,158 have a copy somewhere in the older library, and in every one of those 164 cases
  the library copy is itself unannotated.** That is the whole of the answer to the question this
  report was asked: the older file has nothing to lend to the gap.

## 4. The older library is not a safety net for this gap

The older library holds 1,465 files and 1,402 distinct pictures, and 1,287 of those files carry
content that is already in one of the two Updated folders. Its 435 annotated pictures are spread
over 10 class folders. What that means for coverage:

| | Pictures | Annotated in the new file | Only in the older file | Nowhere |
|---|---|---|---|---|
| The picture has a copy in the older library | 1,402 | 864 | 380 | 158 |
| The picture has no copy in the older library | 9,212 | 3,212 | 0 | 6,000 |

So the older file rescues 380 pictures, which is 3.6 per cent of the drop. The 6,000 pictures that
carry nothing are pictures the older library has never held. They are new material and the older
file cannot speak for them.

One more limit on the older file, found while doing this and worth checking with the client. Its
task list names 462 frames across its ten tasks, but the export carries 435 image elements. Wet
Package accounts for 23 of the 27 absent frames, Foreign Matter 2, Bubble 1, Bubble On 123 1. If
those frames are annotated on the platform and simply did not come out in the export, the rescue
figure of 380 is understated by up to 27.

## 5. Where the older library's pictures sit in the drop

This is the cross-tab that matters for the class-boundary work, one location per row.

| Older library class | Folder in the drop | Status in the new file | Pictures |
|---|---|---|---|
| Fiber | Extraneous Polymer | boxed in the new file | 33 |
| Fiber | Fiber | only in the older file | 27 |
| Foreign Matter | Foreign Matter | only in the older file | 68 |
| Bubble | Clear | only in the older file | 37 |
| Wet Package | Clear | only in the older file | 31 |
| Extraneous Polymer | Extraneous Polymer | boxed in the new file | 15 |
| Bubble Irregular | Clear | only in the older file | 16 |
| Bubble Cluster | Clear | only in the older file | 15 |
| HEMA Fragment | HEMA | only in the older file | 8 |
| Wet Package | Lens Off Center | tag in the new file | 3 |
| eleven further rows, below 3 pictures each | | | 13 |

The rows add to 266 locations for the 435 annotated pictures of the older library. A picture can sit
in two folders, so a row counts locations, not distinct pictures.

Two readings follow from this, and neither should be treated as settled:

- The 60 Fiber pictures of the older library that appear in the two Updated folders split almost
  cleanly: 33 now sit in the Objects Extraneous Polymer folder and carry new boxes there, and 27 sit
  in the Objects Fiber folder where the new file has nothing. The new file therefore votes for the
  newer folder's name on the same 33 objects that our own blind pixel read called Fiber. How the
  Fiber and Extraneous Polymer boundary is drawn is still with the lead.
- A block of the older library's defect pictures sits inside the Objects Clear folder: 37 Bubble, 31
  Wet Package, 16 Bubble Irregular, 15 Bubble Cluster. These carry boxes in the older file and
  nothing in the new one. If Clear is meant to be the rest class, pictures of named defects sitting
  inside it is a label conflict worth naming, not a gap worth filling.

## 6. What this changes

- The 6,097 images of the new file cover 4,076 pictures. The figure to quote for annotation coverage
  of the drop is 4,076 of 10,614, or 38 per cent, and 4,456 of 10,614, or 42 per cent, once the older
  file is allowed to count.
- The two unfinished tasks keep their finding: 2,022 pictures sit in a task folder with an empty
  frame, and the Low Dose task accounts for 1,875 of them.
- Nothing here depends on the Fiber and Extraneous Polymer decision. The counts are the same
  whichever way that boundary lands, only the class name on the 33 objects changes.

## 7. Questions this adds

1. Does the older file carry every frame of its own tasks? Its task list names 462 frames and the
   export carries 435, with Wet Package short 23.
2. Are the Objects Clear folder's pictures ones the library has already named as Bubble, Wet
   Package, Bubble Irregular or Bubble Cluster? If yes, is Clear intended to hold them?
3. For the 4,136 pictures in class folders with no task, is annotation intended at all, or are those
   folders to be treated as bulk negatives?
4. For the 2,022 pictures inside a task with an empty frame, is the work outstanding or were those
   frames viewed and left empty on purpose?

## 8. Where the numbers live

- Builder: `experiments/annotations/reverse_eda_annotation_coverage.py`, 51 self-checks, 0 failed.
- Verifier: `experiments/annotations/verify_reverse_eda.py`, 93 checks, 0 failed.
- Tables: `run/annotations_reverse_eda_20260923/`, holding `summary.json`,
  `picture_coverage.csv` (one row per picture), `folder_x_coverage.csv`, `gap_by_folder.csv`,
  `library_coverage.csv`, `library_pictures_in_drop.csv`, `duplication_axis.csv`,
  `library_same_picture_different_name.csv` and `verification.json`.
- The client EDA this was cross-checked against is in `run/client_eda/20260917/`.
