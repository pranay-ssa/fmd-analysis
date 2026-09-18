# Production line analysis of the defect image library, 2026-09-16

## 1. Why we did this analysis

The client asks one question: can a single model handle all production lines?

The test we propose is five models, not one. We train **five separate ResNet-50
models, one per production line**, each on its own line's data only, and score each
on held-out images from that same line. We then compare them on the classes that
three or more lines share. If the line-specific models agree on the classes they
have in common, the line carries no information and a single model is justified. The
premise being tested is that the capture method is the same everywhere, so an image
carries no trace of the line it came from.

The three folders label the same defect classes, so the analysis pools them by class
rather than by folder, and the unit of every table is one unique picture. Section 6
states the three rules that build the pool and gives the resulting 22-class matrix.
Pooling is what makes the comparison workable: on the older library alone only 4
classes are scorable on all five lines, and pooling raises that to 13.

This report holds the counts that test needs. It does not hold a model result.
Training is on hold until the open decisions in section 12 are settled.

## 2. The data

| Folder | Images | Classes or groups | Note |
|---|---|---|---|
| Updated ICube Objects | 4,230 | 5 | Groups images by object type, not by defect class |
| Updated ICube Categorical Classes | 6,384 | 13 | Groups images by defect class. One group is named `duplicates` |
| ICube Defects Library | 1,465 | 22 | The older library, and the source of the current 22-class set |
| **Total** | **12,079** | | |

Every image is a 2,048 by 2,448 pixel greyscale BMP of 5,014,582 bytes. The two
new folders hold no other file type. The older library also holds two files that
are not images: a CSV of box statistics and the annotation file.

The three folders hold 12,079 files but only 10,801 different file names. Section
8 gives the overlap. They are three sources of the same classes, not three datasets:
after removing repeated pictures, 8,401 unique pictures carry one of the 22 defect
classes, and 2,213 carry no defect label at all.

### The Updated Objects folder in detail

This folder groups images by object type rather than by defect class. It is the
third labeling of the same library.

| Group | L24 | L25 | L26 | L27 | L31 | Total | Lines carrying it |
|---|---|---|---|---|---|---|---|
| Clear | 1,550 | 22 | 348 | 276 | 137 | 2,333 | 5 |
| Foreign Matter | 291 | 84 | 162 | 550 | 195 | 1,282 | 5 |
| Fiber | 83 | 15 | 25 | 86 | 119 | 328 | 5 |
| Extraneous Polymer | 64 | 31 | 134 | 20 | 18 | 267 | 5 |
| HEMA | 9 | 1 | 0 | 0 | 10 | 20 | 3 |
| **Total** | **1,997** | **153** | **669** | **932** | **479** | **4,230** | |

Four facts about it:

1. **It is the cleanest folder for a per-line comparison.** All five of its groups
   appear on three or more lines, so its comparable set is 5 of 5, against 17 of 22
   in the older library and 11 of 13 in the new Categorical folder. It also holds
   no internal duplicates: its 4,230 files are 4,230 different pictures.
2. **Its labels are not defect classes.** Clear is 2,333 images, 55 percent of the
   folder, and it is not a class in the library taxonomy. HEMA holds 20 images and
   matches neither library class: 8 of its pictures are HEMA Fragment there and 4
   are HEMA Obstruction.
3. **Its labels contradict the library on the same pictures.** Clear holds pictures
   the library calls Wet Package (49), Bubble (38), Dirty Strobe (16), Bubble
   Irregular (16), Bubble Cluster (15) and Dirty Camera (10). Extraneous Polymer
   holds 33 pictures the library calls Fiber.
4. **Three of its groups duplicate classes the new Categorical folder does not
   carry:** Fiber, Foreign Matter and Extraneous Polymer, 1,877 images in total.

It therefore cannot serve as the defect-class dataset on its own, and it needs a
role assigned (section 12, decision 7).

## 3. How we read a production line from a file

Each file name carries the line number in the form `_L<number>_`. Examples:

```
20241101_105743_L24_C15_9265.bmp                       -> line L24
20260828_174529_L31_PalletGHH0828222203_...bmp          -> line L31
```

We searched every file name in all three folders with that pattern.

| Finding | Result |
|---|---|
| Lines found | 5: L24, L25, L26, L27, L31 |
| File names with more than one line marker | 0 |
| Other spellings of a line marker | none |
| Images with no line marker (orphans) | 0 |

Every one of the 12,079 images carries a line. The orphan question is closed. The
older library holds two files with no line marker, but both are non-image files.

## 4. Verification

We counted the images twice, from two independent sources, and then a third time
from a third source. The counts must agree, or the numbers are not usable.

| Pass | Source | What it measures |
|---|---|---|
| 1 | The blob container listing | What the source account holds |
| 2 | The files on the VM disk | What the training runs will read |
| 3 | Our local copy of the older library | An independent copy of the same data |

| Check | Result |
|---|---|
| Rows compared, pass 1 against pass 2 | 12,079 against 12,079 |
| SHA-256 over all rows, pass 1 | `51ae788b74f27280b99ad0ad34df2ebfb492bf9ecdcaea48c287e7d3a72454ec` |
| SHA-256 over all rows, pass 2 | `51ae788b74f27280b99ad0ad34df2ebfb492bf9ecdcaea48c287e7d3a72454ec` |
| Class and line cells compared | 40 |
| Cells that disagree | 0 |
| Rows present in one pass only | 0 |
| Library files, pass 2 against pass 3 | 1,465 against 1,465, identical class and file name sets |

The two hash values are equal. The counts in this report are therefore confirmed
by two independent measurements, with a third confirming the older library.

## 5. Images per line

| Line | Updated Objects | Updated Categorical Classes | Older library | Total |
|---|---|---|---|---|
| L24 | 1,997 | 2,324 | 794 | 5,115 |
| L25 | 153 | 819 | 161 | 1,133 |
| L26 | 669 | 896 | 254 | 1,819 |
| L27 | 932 | 678 | 115 | 1,725 |
| L31 | 479 | 1,667 | 141 | 2,287 |
| **Total** | **4,230** | **6,384** | **1,465** | **12,079** |

The lines are not equally supplied. L24 alone holds 42 percent of all images. L25
holds 9 percent. The share of each line also differs by folder: the older library
is 54 percent L24, while the new Categorical folder is 36 percent L24 and 26
percent L31.

Because each of the five models trains on one line only, the volume in this table
sets what each model can learn. The thin lines bound how strong those models can be.

## 6. The defect classes, pooled across the folders, line by line

The three folders label the same 22 defect classes, so the analysis pools them by class rather than by
folder. The unit of the table below is one unique picture, counted once even when a copy of it sits in two
folders. Three rules build the pool, and every number in this report depends on them.

1. **Low Dose and Low Dose Obstructing Region of Interest are one class.** 86 pictures carry both names.
2. **Clear, HEMA and duplicates are not defect classes.** 2,213 pictures carry no other label and fall
   outside the 22-class set. The `duplicates` folder holds no picture that is not already in a class folder.
3. **A picture with two defect classes takes the class the older library assigns.** That rule settles 51
   pictures, of which 33 are Extraneous Polymer against Fiber. The older library is the canonical taxonomy.

Verification of the pool: 1,226 pictures have copies in more than one folder, and none of them disagree on
their line number. All 8,401 pictures in the pool carry a line.

| Class | L24 | L25 | L26 | L27 | L31 | Total | Lines scorable | Comparisons | Thinnest line | Test images |
|---|---|---|---|---|---|---|---|---|---|---|
| Low Dose Obstructing Region of Interest | 108 | 57 | 14 | 464 | 1,307 | 1,950 | 5 | 10 | 4 | 584 |
| Multiple Lenses | 335 | 276 | 674 | 54 | 97 | 1,436 | 5 | 10 | 16 | 431 |
| Missing Primary Package | 1,147 | 189 | 7 | 12 | 72 | 1,427 | 5 | 10 | 2 | 429 |
| Foreign Matter | 287 | 84 | 162 | 549 | 196 | 1,278 | 5 | 10 | 25 | 384 |
| Fiber | 86 | 37 | 26 | 90 | 120 | 359 | 5 | 10 | 8 | 108 |
| Missing Lens | 183 | 6 | 3 | 81 | 51 | 324 | 5 | 10 | 1 | 97 |
| Package Misalignment | 32 | 176 | 24 | 11 | 50 | 293 | 5 | 10 | 3 | 88 |
| Lens Off Center | 195 | 5 | 8 | 27 | 20 | 255 | 5 | 10 | 2 | 77 |
| Extraneous Polymer | 59 | 9 | 134 | 16 | 16 | 234 | 5 | 10 | 3 | 71 |
| Cavity Off Center | 93 | 40 | 24 | 13 | 13 | 183 | 5 | 10 | 4 | 55 |
| HEMA Obstruction | 151 | 18 | 2 | 2 | 2 | 175 | 5 | 10 | 1 | 53 |
| View Obstructed | 19 | 16 | 33 | 11 | 38 | 117 | 5 | 10 | 3 | 35 |
| Bubble | 82 | 18 | 13 | 0 | 0 | 113 | 3 | 3 | 4 | 34 |
| Wet Package | 10 | 2 | 52 | 0 | 2 | 66 | 4 | 6 | 1 | 21 |
| Bubble Irregular | 13 | 1 | 7 | 21 | 2 | 44 | 4 | 6 | 1 | 13 |
| Dirty Strobe | 0 | 12 | 31 | 0 | 0 | 43 | 2 | 1 | 4 | 13 |
| Bubble Cluster | 18 | 2 | 4 | 10 | 2 | 36 | 5 | 10 | 1 | 11 |
| Dirty Camera | 25 | 0 | 0 | 0 | 0 | 25 | 1 | 0 | 8 | 8 |
| Bubble On 123 | 1 | 0 | 0 | 0 | 13 | 14 | 1 | 0 | 4 | 4 |
| Bubble On Edge | 3 | 3 | 1 | 1 | 6 | 14 | 3 | 3 | 1 | 4 |
| HEMA Fragment | 5 | 0 | 0 | 0 | 3 | 8 | 2 | 1 | 1 | 3 |
| Bubble Scatter | 1 | 0 | 1 | 3 | 2 | 7 | 2 | 1 | 1 | 2 |
| **Total** | **2,853** | **951** | **1,220** | **1,365** | **2,012** | **8,401** | | | | **2,525** |

Columns: **Lines scorable** is the number of lines that hold enough pictures of that class to place at
least one in a test set. **Comparisons** is the number of line pairs that can be compared, which is the
scorable count taken two at a time. **Thinnest line** is the test count on the line with the fewest, and it
bounds every comparison for that class: a pair is only as strong as its weaker side. **Test images** is the
total across the lines.

### What each line would train and test on, at 70:30

| Line | Pictures | Classes present | Classes scorable | Test images | Train images | Thin cells |
|---|---|---|---|---|---|---|
| L24 | 2,853 | 21 | 19 | 858 | 1,995 | 4 |
| L25 | 951 | 18 | 17 | 287 | 664 | 7 |
| L26 | 1,220 | 19 | 17 | 365 | 855 | 8 |
| L27 | 1,365 | 16 | 15 | 409 | 956 | 7 |
| L31 | 2,012 | 19 | 19 | 606 | 1,406 | 9 |
| **All lines** | **8,401** | | | **2,525** | **5,876** | **35** |

### How the classes are distributed on each line

Each line takes two rows: classes counted by pictures, then the same classes counted by the test images
they produce. The band columns count classes.

| Line and measure | 1 | 2-4 | 5-9 | 10-24 | 25-99 | 100+ | Total |
|---|---|---|---|---|---|---|---|
| L24, class pictures | 2 | 1 | 1 | 4 | 6 | 7 | 2,853 |
| L24, test images | 1 | 3 | 3 | 2 | 8 | 2 | 858 |
| L25, class pictures | 1 | 3 | 3 | 4 | 4 | 3 | 951 |
| L25, test images | 3 | 4 | 3 | 3 | 4 | 0 | 287 |
| L26, class pictures | 2 | 3 | 3 | 4 | 4 | 3 | 1,220 |
| L26, test images | 3 | 5 | 4 | 2 | 2 | 1 | 365 |
| L27, class pictures | 1 | 2 | 0 | 7 | 4 | 2 | 1,365 |
| L27, test images | 2 | 5 | 3 | 2 | 1 | 2 | 409 |
| L31, class pictures | 0 | 6 | 1 | 4 | 5 | 3 | 2,012 |
| L31, test images | 6 | 3 | 2 | 4 | 3 | 1 | 606 |

The second row of each pair is the one that matters, because it is what the model is scored on. L27 has 7
classes and L31 has 9 classes producing fewer than five test images.

### For the record, what each folder holds on its own

| Folder | Files | Class folders | Notes |
|---|---|---|---|
| Older ICube Defects Library | 1,465 | 22 | the canonical class names; 794 of its files are on L24 |
| Updated ICube Categorical Classes | 6,384 | 13 | 12 defect classes plus `duplicates`; 9 classes appear on all five lines |
| Updated ICube Objects | 4,230 | 5 | object types, not classes: Clear, Foreign Matter, Fiber, Extraneous Polymer, HEMA |

The Objects folder cannot serve as the defect-class dataset, because Clear is 2,333 of its pictures and is
not a class in the taxonomy, and HEMA is 20 pictures that split between two library classes (8 HEMA
Fragment, 4 HEMA Obstruction). Where it does help is with three classes the new Categorical folder does not
carry at all, and pooling raises them sharply: Fiber from 61 pictures in the library to 359, Foreign Matter
from 71 to 1,278, Extraneous Polymer from 17 to 234.

## 7. The comparison set: classes that three or more lines share

The comparison between the five models rests on the classes that more than two lines can score, because a
class on two lines yields a single line pair and a class on one line yields nothing.

| Scorable lines | Classes | Line pairs each | Names |
|---|---|---|---|
| 5 | 13 | 10 | Low Dose Obstructing Region of Interest, Multiple Lenses, Missing Primary Package, Foreign Matter, Fiber, Missing Lens, Package Misalignment, Lens Off Center, Extraneous Polymer, Cavity Off Center, HEMA Obstruction, View Obstructed, Bubble Cluster |
| 4 | 2 | 6 | Wet Package, Bubble Irregular |
| 3 | 2 | 3 | Bubble, Bubble On Edge |
| 2 | 3 | 1 | Dirty Strobe, HEMA Fragment, Bubble Scatter |
| 1 | 2 | 0 | Dirty Camera, Bubble On 123 |

The comparable set is 17 classes at three or more lines. Widening it to two or more lines would add 3
classes, each of which yields a single line pair, so the useful cut is three.

The comparison is further bounded by the thin cells. 35 class-line cells hold fewer than five test images
(L24 4, L25 7, L26 8, L27 7, L31 9), and the weakest of all are Missing Lens, HEMA Obstruction, Wet Package,
Bubble Irregular, Bubble Cluster, Bubble On Edge, HEMA Fragment and Bubble Scatter, which on some line have
a single test image. A comparison involving those cells cannot be read as evidence either way.

The five training sets are unequal (L24 1,995 pictures against L25 664), so the sets must be matched before
any gap between the models can be attributed to the line rather than to the volume. The five models also
carry different class lists, so overall accuracy is not comparable between them; the comparable quantity is
per-class recall on the shared classes.

## 8. Overlap between the folders

The folders are not disjoint. The same picture often appears in more than one
folder, under the same file name.

| Pair | Shared file names |
|---|---|
| Updated Objects against Updated Categorical Classes | 27 |
| Updated Objects against the older library | 272 |
| Updated Categorical Classes against the older library | 1,002 |
| Older library files that also appear in the new drop | 1,247 of 1,463 distinct names |

The older library holds 1,465 files and 1,463 distinct names. Of those names,
1,247 also appear in the new drop, and 216 do not appear in the new drop at all.

Checked by content fingerprint rather than by name, the picture is this: the three
folders hold 10,614 different images, so 1,465 files are repeated copies. Of the
1,247 names shared with the new drop, every one is the same image, byte for byte.
A further 187 images are stored under two different file names.

If all three folders are used as one training set, then 1,465 of the 12,079 files
are copies of a picture already counted: 1,278 are found by comparing names (1,247
library names that reappear in the new drop, 27 names in both new folders, 4 names
inside a single folder) and the remaining 187 are the same picture filed under a
second name, which a name comparison cannot see. That inflates the count of a line. In a per-line study it is
worse than that: one picture can end up in the train half and the test half of the
same line, or in two different lines' models.

If the older library is dropped, 177 unique images are lost. They sit in 9 library
class folders, led by Bubble (72), Wet Package (28) and Bubble Irregular (26).
Separately, 7 classes exist only in the library and hold 313 images between them.
Of those 313 images, 175 are unique to the library and the other 138 are the same
pictures that the new drop files under a different class, most often Clear (118).
So those 7 classes bring 175 new images, not 313.

## 9. Files with two class labels

Four files sit in two class folders at once, under the same file name. These are
label conflicts. A training set can use only one label for such a file.

| Folder | File | Class folders |
|---|---|---|
| Older library | `..._L31_..._Score(0.9998156).bmp` | Foreign Matter, Low Dose Obstructing Region of Interest |
| Older library | `..._L31_..._Score(0.9927453).bmp` | Low Dose Obstructing Region of Interest, Wet Package |
| Updated Categorical Classes | `..._L24_..._Score(0.9998984).bmp` | Dirty Camera, duplicates |
| Updated Categorical Classes | `..._L24_..._Score(0.9999898).bmp` | Dirty Camera, duplicates |

Counted across the folders, 418 images carry two different class labels. The most
common pairs are Low Dose against Low Dose Obstructing Region of Interest (86
images, a naming difference), Cavity Off Center against duplicates (70), Multiple
Lenses against duplicates (54), Bubble against Clear (37), Extraneous Polymer
against Fiber (33) and Clear against Wet Package (32). In 128 of the 418 cases the
image is Clear in the new folder and carries a defect label in the older library.

The new Categorical folder also holds a file named `cross_directory_duplicates.csv`.
It is 31 bytes and holds only its header row. It records no duplicates, so it
cannot be used as evidence. The counts above come from our own check.

The three pool rules in section 6 resolve these 418 cases, and the arithmetic closes.
86 are the Low Dose pair and are one class, 271 involve Clear or duplicates, which
are not classes at all, and 10 pair HEMA with a defect class, which leaves one class
standing. That leaves 51 pictures with two defect classes, and the older library
decides those, which is why the pooled set in section 6 can count every picture once
and still give it a single label.

## 10. The five per-line models and their splits

Each line gets its own model and its own split, so a model is scored only on pictures from its own line.
The split is made inside each class inside each line. One class-and-line pair is a cell, and a cell is
**scorable** when a plain proportional share leaves it at least one test image. Nothing is discarded: every
picture that is not a test image trains, including the cells that hold a single picture and can never be
scored.

| Line | Pictures | Scorable 70:30 | Scorable 80:20 | Train (70%) | Test (30%) | Train (80%) | Test (20%) |
|---|---|---|---|---|---|---|---|
| L24 | 2,853 | 19 | 19 | 1,995 | 858 | 2,282 | 571 |
| L25 | 951 | 17 | 15 | 664 | 287 | 762 | 189 |
| L26 | 1,220 | 17 | 16 | 855 | 365 | 976 | 244 |
| L27 | 1,365 | 15 | 14 | 956 | 409 | 1,093 | 272 |
| L31 | 2,012 | 19 | 14 | 1,406 | 606 | 1,612 | 400 |
| **All lines** | **8,401** | **87** | **78** | **5,876** | **2,525** | **6,725** | **1,676** |

**Split each line at 70:30.** It leaves a test image for 87 class-line cells against 78 at 80:20, and scores
the models on 2,525 test images against 1,676. The 849 pictures that 80:20 buys back out of 8,401 will not
change what the models learn, and they cost 9 cells that can no longer be measured at all, 5 of them on L31
alone.

### Thin cells

A thin cell is a class on a line that a proportional 70:30 split leaves with between one and four test
images. There are 35 of them, and they are the cells where a result will be inconclusive rather than
informative. The count in brackets is the test images.

| Line | Thin cells | Classes, with test images in brackets |
|---|---|---|
| L24 | 4 | Bubble On Edge (1), HEMA Fragment (2), Wet Package (3), Bubble Irregular (4) |
| L25 | 7 | Bubble Cluster (1), Wet Package (1), Bubble On Edge (1), Lens Off Center (2), Missing Lens (2), Extraneous Polymer (3), Dirty Strobe (4) |
| L26 | 8 | HEMA Obstruction (1), Missing Lens (1), Bubble Cluster (1), Bubble Irregular (2), Missing Primary Package (2), Lens Off Center (2), Bubble (4), Low Dose Obstructing Region of Interest (4) |
| L27 | 7 | HEMA Obstruction (1), Bubble Scatter (1), Bubble Cluster (3), Package Misalignment (3), View Obstructed (3), Missing Primary Package (4), Cavity Off Center (4) |
| L31 | 9 | Bubble Cluster (1), Bubble Irregular (1), Bubble Scatter (1), HEMA Obstruction (1), Wet Package (1), HEMA Fragment (1), Bubble On Edge (2), Bubble On 123 (4), Cavity Off Center (4) |

Eight classes have a single test image on at least one line: Bubble Cluster, Wet Package, HEMA Obstruction,
Missing Lens, Bubble Irregular, Bubble Scatter, HEMA Fragment and Bubble On Edge. A comparison that rests
on one of those cells cannot be read as evidence either way, which is why a stated tolerance or a
confidence interval per recall is needed before any difference there is called real.

Not every cell with few pictures is thin. A class on a line with a single picture produces no test image at
all, so it trains and is never scored, and it is excluded from the thin count rather than counted as a
weak cell.

### A direct test of the premise

The case for one model rests on the capture method being identical, so that a picture carries no trace of
its line. All 12,079 files are the same format, 2,048 by 2,448 greyscale BMP of 5,014,582 bytes, so there
is no resolution difference to find. Whether anything else in the pixels marks the line is testable in one
short run: train a classifier to predict the line from the pooled pictures. If it cannot beat chance, the
premise holds and the single-model conclusion rests on solid ground.

## 11. What this means

1. **The pool is what makes the comparison workable.** Pooling the folders by defect class gives 8,401
   pictures across 22 classes, which raises the classes scorable on all five lines from 4 (older library
   alone) to 13, and the test images per line from 34 to 239 up to 287 to 858. The reason is arithmetic: the
   new folders carry the same classes, so they add pictures to a class rather than adding classes.
2. **Run the line-predictability check before the five models.** It costs one short run, and if a classifier
   cannot tell which line a picture came from, the premise behind one model is confirmed at the pixel level
   rather than inferred from five results.
3. **Split each line at 70:30.** It leaves a test image for 87 class-line cells against 78 at 80:20, and
   scores on 2,525 test images against 1,676. The 849 pictures that 80:20 buys back are not worth the 9
   cells it costs.
4. **Match the five training sets.** L24 would train on 1,995 pictures and L25 on 664. An unmatched
   comparison would confound the line with the training volume, and no result could be attributed to either.
5. **Compare per-class recall on the shared classes, not overall accuracy.** The five models carry
   different class lists, so a model with 16 classes has a different chance level from one with 21. The
   comparison set is the 17 classes that three or more lines can score.
6. **State the tolerance before the run.** 35 class-line cells hold fewer than five test images, so only a
   declared tolerance or a confidence interval can turn the result into a yes or a no.
7. **Report the classes that cannot be compared separately.** Dirty Camera and Bubble On 123 are scorable on
   one line, and Dirty Strobe, HEMA Fragment and Bubble Scatter on two, so their numbers stand alone and
   must not be read as a cross-line result.
8. **Record the three pool rules and keep them fixed.** Every number in this report depends on the rename of
   Low Dose, on Clear, HEMA and duplicates not being classes (2,213 pictures excluded), and on the older
   library deciding the class for the 51 pictures that carry two.

## 12. Open decisions

Training is held until these are answered. The first group we can decide ourselves.

**For us to decide**

1. **Confirm the three pool rules.** They are the rename of Low Dose, the exclusion of Clear, HEMA and
   duplicates (2,213 pictures), and the older library deciding the class for the 51 pictures that carry two.
   Every number here depends on them.
2. **Matched or full training sets for the five models?** Matched sets, taking the same number of pictures
   per class per line, make a gap attributable to the line rather than to the volume.
3. **What counts as similar?** An explicit tolerance for the recall comparison, for example within five
   points, or non-overlapping confidence intervals.
4. **Keep the comparable cut at three or more lines?** That is 17 of the 22 classes, giving between three
   and ten line pairs each. Another 3 classes are scorable on exactly two lines, and widening the cut would
   add them, each with a single line pair.
5. **Do we run the line-predictability check?** One short run, and it tests the premise directly.

**For the client or the lead**

1. **Do the 7 classes that only the older library carries still count?** They hold 313 pictures, of which
   175 exist nowhere else. Pooling does not answer this, because no other folder labels them.
2. **If Clear is later ruled to be a class, it returns as a 23rd class.** 2,213 pictures carry Clear as
   their only label, and they are excluded from the pool today. If they come back, every per-line number
   here changes.
3. **Is a test set of 287 to 858 images per line enough, given the thin cells?** 35 class-line cells still
   hold fewer than five test images, and on L27 and L31 that is 7 and 9 classes.
4. **Four classes cannot support the line-by-line comparison.** Dirty Camera and Bubble On 123 are scorable
   on one line only, and Dirty Strobe, HEMA Fragment and Bubble Scatter on two lines, so their results stand
   alone. Confirm that is acceptable.

## Appendix A: where the data and the scripts live (internal)

| Item | Location |
|---|---|
| The three image folders | VM `fmd_temp_images/`, folders `Updated ICube Objects 20260915`, `Updated ICube Categorical Classes 20260915`, `ICube Defects Library` |
| Line table, one row per image | `run/line_eda/20260916/image_line_tags.csv` |
| One class by line matrix per folder | `run/line_eda/20260916/class_by_line__<folder>.csv` |
| Content fingerprints, one row per image | `run/line_eda/20260916/image_md5_records.csv` |
| Folder overlap | `run/line_eda/20260916/folder_overlap.csv` |
| Reader-facing page | `reports/lines/line_report_20260916.html`, built by `src/make_line_report.py` |
| Message for the lead | `reports/lines/teams_message_20260916.md` |
| Count from the VM filesystem | VM `~/line_eda_vm.py`, output `~/line_eda_vm.csv` |
| Provenance of the new drop | `docs/armor_blob_transfer_20260916.md` |

A part of this report may be shared with the client. Remove this appendix before
you share it. The main body holds no internal path.
