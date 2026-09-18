# Line splits revised under the clarified rules (2026-09-17)

The class-wise 70:30 splits published on 2026-09-16 were built from a 22-class pool of 8,401
pictures. The client's clarification of 2026-09-17 changes the pool, so the splits were rebuilt.
This record holds what moved, what did not, and the way it was checked.

Workbook: `reports/lines/FMD_class_split_70_30_20260917.xlsx` and
`reports/lines/FMD_class_split_70_30_vs_80_20_20260917.xlsx`
Generator: `src/make_line_splits.py` (new; the 2026-09-16 split CSVs had no committed generator)
Verifier: `experiments/eda_client/verify_line_splits.py` (790 checks, 0 failed)

## Why the pool changed

The client said HEMA in the Updated Objects folder reads as HEMA Fragment. The 2026-09-16 pool
treated HEMA as "not a class", which dropped the 8 HEMA pictures that carry no other label. Under
the new rule those 8 become HEMA Fragment pictures, so the pool is **8,409**, not 8,401. Nothing
else in the pool changed: Clear was already excluded except for the 128 pictures that carry a
defect label, and the duplicates subfolder was already out.

## The rules the rebuilt pool applies

1. Clear and duplicates are not classes. A picture that carries a defect label elsewhere takes that
   label and stays in the pool.
2. HEMA in the Updated Objects folder reads as HEMA Fragment.
3. Name equivalences: Low Dose with Low Dose Obstructing Region of Interest, Multiple Lenses with
   Multiple Lens, Package Misalignment with Primary Package Misalignment, View Obstructed with
   Field Of View Obstructed.
4. A picture is counted once, by content hash, never by file name.
5. One class per picture. Where a picture carries two labels the older ICube Defects Library
   decides; where the library is silent the Updated Objects folder decides, then the categorical
   folder. Rules 1 to 5 reproduce the 2026-09-16 pool cell for cell.
6. The duplicates subfolder is excluded.

The split itself is unchanged from 2026-09-16, so no cell moves for a method reason: inside each
class inside each line, test = round-half-up(pictures x ratio) and train = pictures - test. That
rule was recovered from the 2026-09-16 CSV and reproduces all 93 per-class rows and all five line
totals exactly. The script reports this in `--diff` mode.

## What moved

Two cells, both HEMA Fragment. Every other cell is identical to the 2026-09-16 split.

| Cell | Was (2026-09-16) | Now | Why |
|---|---|---|---|
| L25 HEMA Fragment | class absent (the picture read as HEMA and was dropped) | 1 picture, 1 train, 0 test | rule 2 |
| L31 HEMA Fragment | 3 pictures, 2 train, 1 test | 10 pictures, 7 train, 3 test | rule 2 |

Per line, at 70:30:

| Line | Pictures | Train | Test | Classes | Scorable |
|---|---|---|---|---|---|
| L24 | 2,853 (no change) | 1,995 | 858 | 21 | 19 |
| L25 | 952 (was 951) | 665 (was 664) | 287 (no change) | 19 (was 18) | 17 |
| L26 | 1,220 (no change) | 855 | 365 | 19 | 17 |
| L27 | 1,365 (no change) | 956 | 409 | 16 | 15 |
| L31 | 2,019 (was 2,012) | 1,411 (was 1,406) | 608 (was 606) | 19 | 19 |
| **All lines** | **8,409 (was 8,401)** | **5,882 (was 5,876)** | **2,527 (was 2,525)** | **94 (was 93)** | **87 (no change)** |

What the revision does not change: the 87 scorable class-line cells, the 35 thin cells
(L24 4, L25 7, L26 8, L27 7, L31 9), the 17-class comparison set of classes scorable on three or
more lines, and the class list itself, 22 classes. At 80:20 the totals move to 6,732 train and
1,677 test from 6,725 and 1,676.

One consequence worth stating: **the number of classes that hold a single test image somewhere
falls from 8 to 7.** HEMA Fragment's weakest cell is now L24 with 2 test images, so it leaves that
list. The eight were HEMA Fragment, Bubble Cluster, Bubble Irregular, Bubble On Edge, Bubble
Scatter, HEMA Obstruction, Missing Lens and Wet Package; the seven that remain are the same list
without HEMA Fragment. HEMA Fragment still sits in the group scorable on only two lines, so the
comparison set is still 17 classes.

## A one-picture judgement call, disclosed

One picture sits in the Updated Objects folder as Extraneous Polymer and in the Updated Categorical
folder as Multiple Lenses, with no copy in the older library, so rule 5 decides it on a tie-break
rather than on evidence. The 2026-09-16 pool read it as Extraneous Polymer, and the rebuilt pool
keeps that, which is why L26 shows no movement. The alternative reading (the categorical label
wins) moves one picture from Extraneous Polymer to Multiple Lenses on L26 and one test image with
it; it is a one-line edit in `src/make_line_splits.py`.

## How it was checked

1. **The split rule was recovered, not assumed.** Candidate formulas were fitted against the
   2026-09-16 CSV: round-half-up on the test share reproduces all 93 per-class rows and all five
   line totals, where floor, ceiling and Python's banker's rounding each fail on 2 to 49 rows.
2. **The rebuilt pool reproduces the old one.** `--diff` compares all 94 class-line cells: exactly
   2 moved, both HEMA Fragment, both explained by rule 2.
3. **Every published figure is re-derived and diffed against the file.** `verify_line_splits.py`
   rebuilds the pool from the raw record with its own labelling pass, then checks every cell in
   both CSVs, both workbooks, every line total, the scorable flags, and the grand totals: 790
   checks, 0 failed.
4. **The pool size is confirmed by a second implementation.** The workbook of the client's five
   questions builds the dataset by a different route and also lands on 8,409.

## Superseded numbers

Do not reuse these.

| Retired | Correct | What happened |
|---|---|---|
| Pool of 8,401 pictures | **8,409** | HEMA now reads as HEMA Fragment, adding the 8 pictures that carry no other label. |
| L25 951 pictures, 664 train | **952, 665 train** | One HEMA Fragment picture added. |
| L31 2,012 pictures, 1,406 train, 606 test | **2,019, 1,411, 608** | Seven HEMA Fragment pictures added. |
| All lines 5,876 train, 2,525 test, 93 class-line cells | **5,882, 2,527, 94** | The same 8 pictures. |
| All lines 6,725 train, 1,676 test at 80:20 | **6,732 and 1,677** | The same 8 pictures. |
| Eight classes with a single test image somewhere | **Seven** | HEMA Fragment's weakest cell is now 2 test images. |
| HEMA Fragment 8 pictures across 2 lines | **16 pictures across 3 lines** | Rules 2 and 5. |

## Artifacts

| Item | Location |
|---|---|
| Split table, 70:30 | `run/line_eda/20260917/all_lines_class_split_70_30.csv` |
| Split table, both ratios | `run/line_eda/20260917/all_lines_class_split_70_30_and_80_20.csv` |
| Markdown record | `reports/lines/ALL_LINES_class_split_70_30_20260917.md` |
| Workbooks | `reports/lines/FMD_class_split_70_30_20260917.xlsx`, `reports/lines/FMD_class_split_70_30_vs_80_20_20260917.xlsx` |
| Generator | `src/make_line_splits.py` |
| Verifier | `experiments/eda_client/verify_line_splits.py` |

The 2026-09-16 files are kept beside these under the same names without the date. They are not
wrong for their rules; they are the earlier revision.

## Still open

1. The 2026-09-16 record and the lead message both quote 8,401 and the old per-line figures. If
   either has already gone to the client, it needs the corrected table from this document.
2. The rules are still not signed off as a set: matched or full per-line training sets, the
   similarity tolerance for the per-class comparison, and whether to run the line-predictability
   check. Training stays on hold.
