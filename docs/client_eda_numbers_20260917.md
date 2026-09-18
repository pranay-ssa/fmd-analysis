# Client EDA questions: numbers, method and verification (2026-09-17)

The client sent five display requirements for the EDA dashboard on 2026-09-17 and asked for
one Excel sheet per item. This record holds the numbers, the rules they depend on, the way
they were checked, and the figures they replace.

Workbook: `reports/library/FMD_Library_EDA_Counts_20260917.xlsx`
Scripts: `experiments/eda_client/client_eda_numbers.py` (the numbers),
`experiments/eda_client/build_client_eda_workbook.py` (the workbook),
`experiments/eda_client/verify_client_eda.py` (139 checks, 0 failed).

## The question

1. Confirm that every image in the older ICube Defects Library is also present in the two
   Updated folders, reading HEMA in the Updated Objects folder as HEMA Fragment.
2. Display, for the Updated folders first and the older library only where it holds images the
   Updated folders do not: (A) total images per folder, distinct images, production lines;
   (B) distinct images per production line; (C) distinct images per Lens Presentation tag;
   (D) distinct images per object-of-interest tag; (E) whether one image carries more than one
   tag. The Clear class is out of scope for now.

## The source

One row per image file across the three folders, with the content hash and byte size of each:
11,936 image files, 10,614 distinct pictures. Every number below is produced by a script from
that record. Nothing is typed by hand.

| Folder | Image files | Distinct pictures |
|---|---|---|
| Updated ICube Objects 20260915 | 4,230 | 4,230 |
| Updated ICube Categorical Classes 20260915 | 6,241 | 6,241 |
| ICube Defects Library (older library) | 1,465 | 1,402 |
| Three folders together | 11,936 | 10,614 |

## Rules fixed with the team before building

1. The two Updated folders are the dataset. The older library contributes only pictures that
   appear in neither Updated folder: **177 pictures**.
2. Clear is not a class, except for the **128 pictures** that also carry a defect label. Those
   128 stay, under the defect label. 2,205 Clear pictures carry no other label and are set aside.
3. HEMA in the Updated Objects folder reads as HEMA Fragment.
4. Name variants treated as one tag: Low Dose and Low Dose Obstructing Region of Interest,
   Multiple Lenses and Multiple Lens, Package Misalignment and Primary Package Misalignment,
   View Obstructed and Field Of View Obstructed.
5. A distinct image is a distinct picture, identified by content hash, never by file name.
6. The `duplicates` subfolder is excluded: every file in it repeats a picture already in the
   same folder.

## The answer to each item

**Q1 coverage.** 1,287 of the older library's 1,465 files carry content that is already in an
Updated folder (1,225 distinct pictures). 178 files, holding **177 distinct pictures**, are in
neither Updated folder. Matched by file name the figure is lower, 1,249 files, so 38 library files
are the same picture as an Updated-folder file under a different name. The uncovered pictures by
library class:
Bubble 72, Wet Package 27, Bubble Irregular 26, Bubble Cluster 21, Bubble On 123 14, Bubble On
Edge 14, Bubble Scatter 1, Dirty Strobe 1, Fiber 1. Each of those 177 stays in the dataset under
its own tag, which is why sheets C and D list more tags than the Updated folders carry.

**A.** See the folder table above, plus: production lines **5** (L24, L25, L26, L27, L31), every
file carrying a line number and no exceptions. Dataset after rules 1 to 6: **8,409 distinct
pictures** (10,437 in the two Updated folders, plus 177 from the older library, less 2,205 Clear
pictures with no other label).

**B.** Distinct pictures per line: L24 2,853, L25 952, L26 1,220, L27 1,365, L31 2,019.

**C.** Distinct pictures per Lens Presentation tag: Low Dose Obstructing Region of Interest
1,952, Multiple Lenses 1,439, Missing Primary Package 1,427, Missing Lens 324, Package
Misalignment 293, Lens Off Center 258, Cavity Off Center 183, HEMA Obstruction 175, View
Obstructed 117, Dirty Strobe 43, Dirty Camera 25, Bubble Scatter 7. Column total 6,243, against
6,241 distinct pictures carrying at least one of these tags in the Updated folder: the older
library adds one Bubble Scatter and one Dirty Strobe picture that the Updated folder does not
hold.

**D.** Distinct pictures per object-of-interest tag, all 11 object-level tags of the naming
document, the four the Updated Objects folder carries first: Foreign Matter 1,283, Fiber 362,
Extraneous Polymer 268, HEMA Fragment 20, Bubble 113, Wet Package 67, Bubble Irregular 44,
Bubble Cluster 36, Bubble On 123 14, Bubble On Edge 14, Stretched Bubble 0 (the library holds no
images for it). 2,179 pictures carry at least one of the 11. Restricting the table to the four
tags the client's chart plots would leave 174 kept pictures untagged, which is why all 11 are
listed.

**E.** Yes, but rarely, and the count depends on how the name variants are treated:

| View | Pictures | Of which carry three tags |
|---|---|---|
| Name variants treated as one tag, Clear and duplicates not tags | 55 | 0 |
| As above but Low Dose against Low Dose Obstructing Region of Interest counts as two | 153 | 2 |
| Counting every label including Clear and duplicates | 418 | 8 |

The strict view's 55 pairs: Extraneous Polymer with Fiber 33, HEMA Fragment with HEMA Obstruction
4, Lens Off Center with Wet Package 3, Bubble with Fiber 2, Bubble Irregular with Foreign Matter
2, Low Dose with Wet Package 2, Multiple Lenses with Wet Package 2, and seven single pairs.
Separately, in the bounding-box annotation file no one of its 435 images carries more than one
box label.

## Differences against the client's two bar charts

Our figures are the folder file counts, from the same record. Four of the 16 cells differ by one
or two images: Dirty Strobe 43 against 42, Lens Off Center 259 against 258, Extraneous Polymer
269 against 267, Foreign Matter 1,280 against 1,282. A read-only listing of the source storage on
2026-09-17 agrees with our column in all 16 cells, so the differences sit in the charts. The
workbook's last sheet shows both columns.

## How the numbers were checked

1. **Every published figure is re-derived and diffed against the workbook cell.**
   `verify_client_eda.py` re-reads the source record, recomputes each number by a separate route
   (including an independent line-number parser) and compares it with the cell: 139 checks, 0
   failed.
2. **The source storage was re-listed read-only on 2026-09-17** and agrees with every per-class
   figure in sheets A to D. It also shows that the `duplicates` folder and the 31-byte
   `cross_directory_duplicates.csv` have since been removed on the source side.
3. **The VM copy was re-inventoried read-only on 2026-09-17.** It still holds the 2026-09-16
   download unchanged: 4,230 and 6,384 image files, byte totals 21,211,681,860 and
   32,013,091,488, equal to the record written at transfer, plus the `duplicates` folder.
4. **The 143 removed files were checked in both directions by content hash.** None of them is a
   picture that exists only in that folder, and no repeated picture sits outside it, so removing
   them does not change any count of distinct pictures.

## Superseded numbers

Do not reuse these.

| Retired | Correct | What happened |
|---|---|---|
| Updated Categorical Classes folder as 6,384 image files | **6,241 image files** | 143 duplicate copies were removed on the source side. Changing the file count changes no count of distinct pictures, because every one of the 143 repeats a picture already in the folder. The workbook quotes 6,241 and says so. |
| Dataset of 8,281 distinct pictures | **8,409** | Leaving out the 128 Clear pictures that carry a defect label as well. The client asked for them to be kept. |
| "130 images common with the other defects" | **128 distinct pictures** | 130 is the count of class assignments; two pictures carry two defect labels each, so the pictures behind them number 128. |
| 6,241 as the count of pictures carrying a Lens Presentation tag | **6,243** | 6,241 is the Updated folder alone; the older library adds one Bubble Scatter and one Dirty Strobe picture. |

## Open items

1. The lead was asked whether to quote the folder as 6,241 (source as it stands today) or 6,384
   (our 2026-09-16 snapshot). The workbook uses 6,241.
2. Four chart cells differ from ours and the source agrees with us. The client may want the chart
   regenerated.
3. `Removed: Clear pictures that carry no defect label` in sheet A is 2,205, and the 128 that stay
   are counted under their defect label. If Clear later returns as a class, every number in sheets
   B to D changes.
