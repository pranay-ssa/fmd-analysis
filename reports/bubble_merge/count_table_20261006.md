---
title: Count table: images per class and tag, bubbles merged and separate
date: 2026-10-06
type: result
status: active
where: reports/bubble_merge/count_table_20261006.md
---

# Count table for Task 1: images per class, LP tag and OOI tag

The client email for Task 1 asks for one table showing how many images sit in
each class, label and tag, read against the Lens Presentation (LP) tag family
and the object-of-interest (OOI) tag family, with Clear added as a class. It
asks for two readings: the classes as they stand today, and the four bubble
classes of the email (Bubble, Bubble On 123, Bubble On Edge, Bubble Irregular)
merged into a single Bubble class. Both readings are below.

Every number counts distinct pictures identified by content hash, never file
name. Every number was recomputed by an independent verification script on
2026-10-06 and checked against the figures the client was already given
(per-class and per-line counts of 2026-09-17, the Clear arithmetic of
2026-09-16, and the two-tag count of 2026-09-17): 62 checks, 0 failed, and a
second build produced byte-identical output.

## Rules the numbers rest on

1. A picture is counted once, by content hash, never by file name.
2. One tag per picture. Where a picture carries two tags the older ICube
   Defects Library decides, then the Updated Objects folder, then the Updated
   Categorical Classes folder.
3. Clear is a class now: a picture whose only label anywhere is Clear becomes
   Clear, and a picture that carries any other tag keeps that tag. The 128
   pictures that carry Clear and a defect stay under the defect.
4. The merge folds exactly the four classes named in the email. Bubble
   Cluster and Bubble Scatter stay separate.
5. Train and test come from one split shared by every run: 70:30 inside each
   class, seed 42, so a picture sits on the same side in both readings.

## Column meanings

- **Pictures carrying the tag**: every distinct picture that carries the tag
  in any folder. This is the column the client's own charts use.
- **Dataset**: after one tag per picture, so a picture carrying two tags is
  counted once, under the tag the rule assigns.
- **Train / test**: the shared split above.

## Table A: classes as they stand (23 classes, 10,614 pictures)

| Class | Tag family | Pictures carrying the tag | Dataset | Train | Test |
|---|---|---|---|---|---|
| Bubble Scatter | LP tag | 7 | 7 | 5 | 2 |
| Cavity Off Center | LP tag | 183 | 183 | 128 | 55 |
| Dirty Camera | LP tag | 25 | 25 | 17 | 8 |
| Dirty Strobe | LP tag | 43 | 43 | 30 | 13 |
| HEMA Obstruction | LP tag | 175 | 175 | 122 | 53 |
| Lens Off Center | LP tag | 258 | 255 | 178 | 77 |
| Low Dose Obstructing Region of Interest | LP tag | 1,952 | 1,950 | 1,365 | 585 |
| Missing Lens | LP tag | 324 | 324 | 227 | 97 |
| Missing Primary Package | LP tag | 1,427 | 1,427 | 999 | 428 |
| Multiple Lenses | LP tag | 1,439 | 1,436 | 1,005 | 431 |
| Package Misalignment | LP tag | 293 | 293 | 205 | 88 |
| View Obstructed | LP tag | 117 | 117 | 82 | 35 |
| **LP tag subtotal** | | | **6,235** | | |
| Bubble | OOI tag | 113 | 113 | 79 | 34 |
| Bubble Cluster | OOI tag | 36 | 36 | 25 | 11 |
| Bubble Irregular | OOI tag | 44 | 44 | 31 | 13 |
| Bubble On 123 | OOI tag | 14 | 14 | 10 | 4 |
| Bubble On Edge | OOI tag | 14 | 14 | 10 | 4 |
| Extraneous Polymer | OOI tag | 268 | 234 | 164 | 70 |
| Fiber | OOI tag | 362 | 359 | 251 | 108 |
| Foreign Matter | OOI tag | 1,283 | 1,278 | 895 | 383 |
| HEMA Fragment | OOI tag | 20 | 16 | 11 | 5 |
| Wet Package | OOI tag | 67 | 66 | 46 | 20 |
| **OOI tag subtotal** | | | **2,174** | | |
| Clear | Clear | 2,333 | 2,205 | 1,543 | 662 |
| **Total** | | | **10,614** | **7,428** | **3,186** |

Folded Lens carries no picture in this data (it exists only as an annotation
tag, never as a folder), which is why it is not a row.

## Table B: four bubbles merged (20 classes, same 10,614 pictures)

Rows not listed in full are unchanged from Table A.

| Class | Tag family | Pictures carrying the tag | Dataset | Train | Test |
|---|---|---|---|---|---|
| **Bubble (merged: Bubble, Bubble On 123, Bubble On Edge, Bubble Irregular)** | OOI tag | **185** | **185** | **130** | **55** |
| Bubble Cluster | OOI tag | 36 | 36 | 25 | 11 |
| Extraneous Polymer | OOI tag | 268 | 234 | 164 | 70 |
| Fiber | OOI tag | 362 | 359 | 251 | 108 |
| Foreign Matter | OOI tag | 1,283 | 1,278 | 895 | 383 |
| HEMA Fragment | OOI tag | 20 | 16 | 11 | 5 |
| Wet Package | OOI tag | 67 | 66 | 46 | 20 |
| **OOI tag subtotal** | | | **2,174** | | |
| 12 LP tag rows | LP tag | unchanged | 6,235 | | |
| Clear | Clear | 2,333 | 2,205 | 1,543 | 662 |
| **Total** | | | **10,614** | **7,428** | **3,186** |

Merged Bubble = 113 + 44 + 14 + 14 = 185 pictures, and no picture carries two
of those four tags, so the tag count and the dataset count are the same
number. Bubble Cluster and Bubble Scatter are not folded in.

## Why the two count columns differ

A picture that carries two tags appears in two tag columns but only one
dataset row, so the tag column is always at least the dataset column. The gap
across the whole table is 55 pictures, which is the number of pictures that
carry two tags (the same 55 the client was given on 2026-09-17); the Clear row
adds a further 128, the pictures that carry Clear and a defect and are counted
under the defect. The largest single gaps are Extraneous Polymer (268 tagging
pictures against 234 assigned), Foreign Matter (1,283 against 1,278) and
Fiber (362 against 359).

## How each number was checked

- Per class and per production line: the table reproduces the split file every
  earlier line-model result was quoted on, cell by cell, including the line
  totals 2,853 / 952 / 1,220 / 1,365 / 2,019.
- Tag columns: the 12 LP tag counts and the 11 OOI tag counts match the
  figures published to the client on 2026-09-17, exactly.
- One tag per picture: every picture's assigned class was compared picture by
  picture against the frozen rule of the line-split builder, with zero
  differences.
- Clear: 2,333 Clear-tagged pictures, of which 128 also carry a defect and
  keep it, leaving 2,205, which is the arithmetic the client was given.
- Merge: the merged Bubble count equals the sum of its four members, every
  other class keeps its count, and 23 classes become 20.
- Split: one row per picture, no picture on both sides, per-class test counts
  equal to round-half-up of 30 per cent, totals 7,428 / 3,186.

---

*Internal record (not part of the client-facing table): built by
`experiments/bubble_merge/build_labels.py`, checked by
`experiments/bubble_merge/verify_labels.py`, outputs in
`run/bubble_merge/20261006/` (labels.csv, count_table_separate.csv,
count_table_merged.csv, split_70_30_seed42.csv, summary.json).*
