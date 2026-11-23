---
title: Frozen annotation dataset - coverage and counts
date: 2026-11-17
type: result
status: superseded
where: docs/frozen_dataset_eda_20261117.md
---

# Frozen annotation dataset: coverage and counts

> Superseded on 18 November 2026 by `docs/frozen_eda_workbook_20261118.md`. That workbook uses the
> 13,673 labelled-picture basis, adds the size-untagged PASS analysis and records the duplicate-pair
> options. This document remains the all-record 17 November pass.

Every number below is counted from the 92 annotation files in the frozen folder and checked against the
storage account. Nothing has been joined to a training matrix, and no label mapping has been written for
the four classes added in this export. Five open points remain and are listed at the end.

All counts are pictures unless the column says otherwise. One picture is one distinct file name inside
the frozen export. Codes are the annotation codes; names follow Draft 2. The long version, with the
counting rules and worked examples, is `docs/frozen_dataset_eda_walkthrough_20261117.md`.

## 1. What was checked

| Check | Result |
|---|---|
| Files in the frozen folder | 99: 92 annotation XML, 7 client analysis files |
| Local copies against the storage account | 99 of 99 identical, byte for byte |
| Image folders on the storage account | 4, see section 2 |
| Frozen pictures found in their declared image folder | 13,682 of 13,682 |
| Pictures with at least one mark | 13,635 |
| Pictures with no mark at all | 47 |
| Images in the consolidated store, hash-checked after copy | 13,682 of 13,682, 0 missing, 0 extra |

The three files that sit in the older image folder but are not named in the export are duplicate copies
of pictures that are annotated under a shorter name. They are not missing annotations.

## 2. What the frozen set covers

| Image folder | Files in storage | Named in the frozen export | Annotated |
|---|---|---|---|
| `PRODUCTION-20260925` | 10,438 | 10,435 | yes |
| `PRODUCTION-20261031` | 3,247 | 3,247 | yes |
| `PRODUCTION_20261106` | 3,500 | 0 | no |
| `PRODUCTION_20261113` | 4,064 | 0 | no |

The frozen export covers 13,682 pictures. The storage account holds 21,249 pictures in the four
folders, so 7,564 pictures in the two November folders have no annotation in this export. That is the
first open question.

The images are consolidated at `/data/FMD_Data_26082026/frozen_data_20261117/`: one `images/` folder of
13,682 files, the 92 XMLs and 7 client files, `manifest.csv`, `labels/`, and sha256 checksums.

## 3. Duplicates against the previous annotation

| Measure | Count |
|---|---|
| Frozen pictures also named in the previous annotation | 6,771 |
| Same picture under a different name (content identity) | 23 |
| Distinct pictures already annotated before | 6,794 |
| Frozen pictures never annotated before (by content) | 6,888 |
| - by name alone | 6,911: 3,247 new plus 3,664 old, and the 23 aliases sit in the 3,664 |
| - of which from the new upload | 3,247 |
| - of which from the old batch, on disk but never annotated | 3,641 |

Of the 6,771 pictures covered before, 3,269 carry the same label set in both annotations and 3,502
carry a different one. Under the lead's rule the frozen annotation is final for all of them. The
3,502 are the ones where our earlier label matrices no longer describe the picture.

Four pairs of pictures also appear twice inside the frozen set itself, under two names with the same
content (8 rows).
They are flagged in the manifest as content duplicates. One pair carries an identical label set; three
differ by a few boxes. Both rows are kept, and a pair must never be split across train and test.

## 4. Pictures the frozen export does not carry but the previous annotation does

| Measure | Count |
|---|---|
| Present in a previous annotation, absent from frozen, by name | 198 |
| - same content already in frozen under another name | 23 |
| - genuinely absent | 175 |
| - one picture counted twice, two names, two labels | 1 |
| **Distinct candidates** | **174** |
| - held pending client confirmation | 147 |
| - discarded (legacy reference classes) | 27 |

| Class in the previous annotation | Pictures | Decision |
|---|---|---|
| Bubble | 72 | Pending client |
| Wet Package | 24 | Pending client |
| Bubble Cluster | 21 | Pending client |
| Multiple Lens (`P1_ML`) | 3 | Pending client |
| Fiber | 1 | Pending client |
| Bubble Irregular | 26 | Pending client, folds into Bubble |
| Bubble On Edge | 14 | Discarded |
| Bubble On 123 | 13 | Discarded |

One picture appeared twice with two labels, Multiple Lens in the 22 September file and Wet Package in
the older file. The newer file wins, so Multiple Lens stands and the Wet Package row is dropped; that is
why the candidate count is 174 and Wet Package is 24.

Nothing here is added to the store. The working count is 13,682 until the 147 are confirmed.

## 5. LP presentation tags

All 15 LP classes carry pictures in this export. The three classes that had no data before (Edge
Bottle-Capped, Torn Lens, Lens Rupture) now have 24, 117 and 36 pictures.

| Code | Class | Tag instances | Pictures |
|---|---|---|---|
| P2_LD | Low Dose | 2,124 | 2,124 |
| P2_DC | Dirty Camera | 1,992 | 1,992 |
| P2_LOC | Lens Off Center | 1,571 | 1,570 |
| P1_ML | Multiple Lens | 1,514 | 1,511 |
| P1_MPP | Missing Primary Package | 1,427 | 1,427 |
| P1_PPM | Primary Package Misalignment | 1,055 | 1,055 |
| P1_COC | Cavity Off Center | 817 | 816 |
| P1_NL | No Lens | 721 | 721 |
| P1_FL | Folded Lens | 586 | 586 |
| F2_FOV | Field of View Obstructed | 223 | 222 |
| P1_TL | Torn Lens | 117 | 117 |
| P1_LR | Lens Rupture | 36 | 36 |
| P2_DS | Dirty Strobe | 33 | 33 |
| P1_EBC | Edge Bottle-Capped | 24 | 24 |
| P2_BSC | Bubble Scatter | 12 | 12 |
| **Total** | | **12,252** | **9,252** |

A picture can carry more than one tag, so the pictures column does not sum to the total: 9,252 distinct
pictures carry at least one LP tag. Four pictures carry the same tag twice, so the count of distinct
statements is 12,246 against 12,252 instances.

## 6. OOI boxes and size gates

All 8 object classes carry boxes. Surface Groove, which had no data before, has 88 pictures and 132
boxes.

| Code | Class | Pictures with a box | Boxes | Size gate tags | Size gate pictures |
|---|---|---|---|---|---|
| P2_BB | Bubble | 9,775 | 92,223 | - | - |
| P2_BC | Bubble Cluster | 4,991 | 14,700 | - | - |
| P3_FM | Foreign Matter | 2,367 | 4,813 | 1,400 | 1,400 |
| P3_FIB | Fiber | 1,396 | 2,830 | 1,306 | 1,306 |
| P3_EP | Extraneous Polymer | 1,018 | 1,084 | 1,014 | 1,014 |
| P2_WP | Wet Package | 813 | 3,159 | - | - |
| P3_HE | HEMA | 340 | 351 | 340 | 340 |
| P1_SG | Surface Groove | 88 | 132 | - | - |
| **Total** | | **10,032** | **119,292** | **4,060** | **3,742** |

A picture can carry several classes, so the pictures column does not sum to the total. Size gates exist
for the four contamination classes only. No gate sits on a picture without its class.

## 7. Single-tagged and multi-tagged pictures

Following the lead's definition, a class is either an LP presentation tag or an OOI object class, and a
size gate does not add a class. Clear is a folder label and is reported in section 8, not here.

| Classes on the picture | Pictures |
|---|---|
| 0 (five unannotated placeholders) | 5 |
| 1 | 4,111 |
| 2 | 4,236 |
| 3 | 2,756 |
| 4 | 1,263 |
| 5 | 716 |
| 6 | 361 |
| 7 | 155 |
| 8 | 33 |
| 9 | 4 |
| **Total** | **13,640** |

So there are **4,111 single-class pictures and 9,524 multi-class pictures**, out of 13,640. The other 42
pictures are Clear.

Single-class pictures split into 3,439 with one LP tag and 672 with one OOI class; 576 of the latter are
Bubble alone. The common single classes are Missing Primary Package 1,376, Primary Package Misalignment
958, Cavity Off Center 805, Bubble 576, Field of View Obstructed 221 and No Lens 45.

Two-class pictures, by composition:

| Composition | Pictures |
|---|---|
| OOI + OOI | 2,565 |
| LP + OOI | 1,507 |
| LP + LP | 164 |
| **Total** | **4,236** |

Three-class pictures, by composition:

| Composition | Pictures |
|---|---|
| 1 LP + 2 OOI | 1,529 |
| 3 OOI | 1,019 |
| 2 LP + 1 OOI | 208 |
| 3 LP | 0 |
| **Total** | **2,756** |

The multi-class population is driven by bubbles. Every common pair except one contains Bubble, and there
is no three-LP picture. The most frequent pairs overall are Bubble + Bubble Cluster 4,943, Bubble +
Foreign Matter 2,278, Bubble + Low Dose 2,073, Bubble + Dirty Camera 1,786 and Bubble + Lens Off Center
1,555. Multiple Lens + Lens Off Center appears on 1,220 pictures but on none with exactly two classes:
bubbles are always present as well.

For comparison, the earlier LP-only reading gave 7,237 single and 2,015 multi. It is kept in
`run/frozen_eda_20261117/{single,two,three}_tagged.csv` and is not the definition used above.

## 8. Clear lens pictures

Clear is not a code in the annotation. The project rule decides it: a Clear-folder picture with no
mark. That rule reproduces the previous record exactly (2,333 Clear-folder pictures, 2,117 with no
marks), so it is the definition used here.

All 2,333 Clear-folder pictures are in the frozen set, under production names. What the re-annotation
did to them:

| State of the 2,333 Clear-folder pictures | Pictures |
|---|---|
| No mark at all, still Clear | **42** |
| Bubble or Bubble Cluster boxes only | 1,712 |
| Another object box only (Foreign Matter, Wet Package, Fiber) | 255 |
| A presentation tag, usually with boxes | 324 |

**Clear is 42 pictures.** The folder did not lose its pictures: 2,291 moved into a class bucket and 42
stayed Clear. This is a re-labelling, not a loss.

Two points follow. The pass population did not vanish: 1,798 pictures carry nothing but Bubble or
Bubble Cluster boxes, and the pass rule already passes "Clear or bubble only". And Clear cannot be
computed for the 3,247 new pictures at all, because they have no library folder. If clear pictures
matter for the new batch, the annotation needs a Clear code or a folder convention.

## 9. Our counts against the client's own count table

The client's analysis includes a per-defect table over 71 jobs, job 4521940 to job 4522010, and two
totals files. Our export has 70 of those jobs: 4522010 is not in the frozen folder.

For the 70 shared jobs, our counts plus the client's own job 4522010 row reproduce their totals exactly
for Bubble, Bubble Cluster, Foreign Matter, Fiber, Extraneous Polymer, HEMA, Field of View Obstructed
and all four size gates. Five classes differ by a small amount: Cavity Off Center 1, Folded Lens 10,
Multiple Lens 2, Missing Primary Package 1, Dirty Camera 10. Those five are consistent with the frozen
files being a later export than the one the client counted from.

That agreement is the evidence that our parser and their counter read the same file format the same
way. It also means their totals describe 71 jobs and are not a count of the frozen set as delivered.

## 10. Open points

1. **Two unannotated uploads.** `PRODUCTION_20261106` (3,500 pictures) and `PRODUCTION_20261113`
   (4,064 pictures) are in storage but not in the frozen export. Are they part of the frozen set?
2. **Job 4522010.** It is in the client's own per-defect table but not in the frozen folder. Is one
   file missing from the export?
3. **`F2_FOV` and `P2_FOV`.** The export uses `F2_FOV` (223 tags). The guide's code `P2_FOV` never
   appears. Which code is the standard?
4. **The 47 pictures with no mark.** Fifteen are named `Fail` in the file name, 12 of those Clear-folder
   pictures. Annotate them, or drop them from the set?
5. **The 147 add-backs.** Held pending client confirmation. If approved, the set becomes 13,829
   pictures.

Settled on 17 November: Clear is 42 under the project rule; the 27 legacy reference pictures are
discarded; the one duplicate-label picture resolves to Multiple Lens.

## 11. Not done yet

- No label mapping exists for the four classes new to this export (Edge Bottle-Capped, Torn Lens,
  Lens Rupture, Surface Groove). The crosswalk predates them.
- The new upload has been hashed during the store build, but its content has not been compared against
  the old batch for duplicates. File names do not collide.
- No picture-level label matrix, split or training set has been built from this export.
- The 47 empty pictures and the 147 add-backs are unresolved, so the final picture count can still move.

## Where the numbers live

`run/frozen_eda_20261117/`: `eda_summary.json`, `coverage.json`, `inventory.json`, and one CSV per table
above. Composition tables are under `detail/`. Scripts: `experiments/annotations/frozen_inventory.py`,
`frozen_coverage.py`, `frozen_by_content.py`, `frozen_eda.py`, `frozen_eda_detail.py`,
`frozen_eda_by_composition.py`, `build_blob_check.py`, `verify_frozen_eda.py`,
`verify_frozen_detail.py`.
