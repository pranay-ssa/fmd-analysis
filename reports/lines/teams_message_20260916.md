# Teams message: the pooled class-by-line plan (2026-09-16)

Copy from below the line. No local paths, no cross-references; every claim carries its
number in the same sentence.

Design: five ResNet-50 models, one per production line, compared on the classes three or
more lines share.

---

**Can one model handle every production line? The evidence, class by class**

**How we now read the data.** The three source folders label the same defect classes, so we pool them by class rather than by folder, and count each picture once. The pool holds **8,401 different pictures** across the **22 defect classes**, with **2,213 pictures excluded** because their only label is Clear or HEMA and neither is a defect class. Three rules build the pool: "Low Dose" and "Low Dose Obstructing Region of Interest" are one class (86 pictures carry both names); Clear, HEMA and the duplicates folder are not classes; and the 51 pictures that carry two defect classes take the class the older library assigns, which is the canonical taxonomy. We verified the pool: 1,226 pictures appear in more than one folder, and not one of them disagrees on its line number.

**What we have.** The three folders hold **12,079 files**, which are **10,614 different pictures** once repeats are removed, across **five lines: L24, L25, L26, L27, L31**. Every picture carries its line number, so no picture is unassigned. We counted twice, once from the storage listing and once from the files themselves, and the two counts matched exactly, row for row.

**Every class on every line.** Unique pictures, one row per picture.

| Class | L24 | L25 | L26 | L27 | L31 | Total | Lines scorable | Thinnest line | Test images |
|---|---|---|---|---|---|---|---|---|---|
| Low Dose Obstructing Region of Interest | 108 | 57 | 14 | 464 | 1,307 | 1,950 | 5 | 4 | 584 |
| Multiple Lenses | 335 | 276 | 674 | 54 | 97 | 1,436 | 5 | 16 | 431 |
| Missing Primary Package | 1,147 | 189 | 7 | 12 | 72 | 1,427 | 5 | 2 | 429 |
| Foreign Matter | 287 | 84 | 162 | 549 | 196 | 1,278 | 5 | 25 | 384 |
| Fiber | 86 | 37 | 26 | 90 | 120 | 359 | 5 | 8 | 108 |
| Missing Lens | 183 | 6 | 3 | 81 | 51 | 324 | 5 | 1 | 97 |
| Package Misalignment | 32 | 176 | 24 | 11 | 50 | 293 | 5 | 3 | 88 |
| Lens Off Center | 195 | 5 | 8 | 27 | 20 | 255 | 5 | 2 | 77 |
| Extraneous Polymer | 59 | 9 | 134 | 16 | 16 | 234 | 5 | 3 | 71 |
| Cavity Off Center | 93 | 40 | 24 | 13 | 13 | 183 | 5 | 4 | 55 |
| HEMA Obstruction | 151 | 18 | 2 | 2 | 2 | 175 | 5 | 1 | 53 |
| View Obstructed | 19 | 16 | 33 | 11 | 38 | 117 | 5 | 3 | 35 |
| Bubble | 82 | 18 | 13 | 0 | 0 | 113 | 3 | 4 | 34 |
| Wet Package | 10 | 2 | 52 | 0 | 2 | 66 | 4 | 1 | 21 |
| Bubble Irregular | 13 | 1 | 7 | 21 | 2 | 44 | 4 | 1 | 13 |
| Dirty Strobe | 0 | 12 | 31 | 0 | 0 | 43 | 2 | 4 | 13 |
| Bubble Cluster | 18 | 2 | 4 | 10 | 2 | 36 | 5 | 1 | 11 |
| Dirty Camera | 25 | 0 | 0 | 0 | 0 | 25 | 1 | 8 | 8 |
| Bubble On 123 | 1 | 0 | 0 | 0 | 13 | 14 | 1 | 4 | 4 |
| Bubble On Edge | 3 | 3 | 1 | 1 | 6 | 14 | 3 | 1 | 4 |
| HEMA Fragment | 5 | 0 | 0 | 0 | 3 | 8 | 2 | 1 | 3 |
| Bubble Scatter | 1 | 0 | 1 | 3 | 2 | 7 | 2 | 1 | 2 |
| **Total** | **2,853** | **951** | **1,220** | **1,365** | **2,012** | **8,401** | | | **2,525** |

"Lines scorable" is the number of lines that hold enough pictures of that class to place at least one in a test set. "Thinnest line" is the test count on the line with the fewest for that class, and it bounds every comparison for that class, because a pair is only as strong as its weaker side. "Test images" is the total across the lines.

**Pooling is what makes the comparison workable.** On the older library alone only 4 classes were scorable on all five lines; after pooling, 13 are. The reason is arithmetic: the new folders carry the same classes as the library, so they add pictures to a class rather than adding classes. Fiber rises from 61 pictures to 359, Foreign Matter from 71 to 1,278, Extraneous Polymer from 17 to 234, because the Objects folder carries those three classes and the new Categorical folder does not.

**What each line would train and test on, at 70:30.**

| Line | Pictures | Classes present | Classes scorable | Test images | Train images | Thin cells |
|---|---|---|---|---|---|---|
| L24 | 2,853 | 21 | 19 | 858 | 1,995 | 4 |
| L25 | 951 | 18 | 17 | 287 | 664 | 7 |
| L26 | 1,220 | 19 | 17 | 365 | 855 | 8 |
| L27 | 1,365 | 16 | 15 | 409 | 956 | 7 |
| L31 | 2,012 | 19 | 19 | 606 | 1,406 | 9 |
| **All lines** | **8,401** | | | **2,525** | **5,876** | **35** |

**Split choice.** A 70:30 split leaves a test image for **87 class-and-line cells**, against **78** at 80:20, and scores the models on **2,525 test pictures** against **1,676**. Nothing is discarded either way, because every picture that is not a test picture trains. Choosing 80:20 would add 849 training pictures out of 8,401, which will not change what the models learn, and it would cost 9 cells that can no longer be measured at all, 5 of them on L31.

**Which classes can actually be compared.** **13 classes are scorable on all five lines**, 2 on four lines (Wet Package, Bubble Irregular) and 2 on three lines (Bubble, Bubble On Edge), so **17 of the 22 support the comparison**. Two classes give nothing: Dirty Camera, with 25 pictures on L24 alone, and Bubble On 123, with 14 pictures split between L24 and L31. Three classes give a single line pair: Dirty Strobe (12 on L25, 31 on L26), HEMA Fragment (5 on L24, 3 on L31) and Bubble Scatter (7 pictures across three lines).

**The thin cells bound what we can claim.** **35 class-and-line cells hold fewer than five test images**, of which L27 has 7 and L31 has 9. Eight classes have a single test image on at least one line: Bubble Cluster, Wet Package, HEMA Obstruction, Missing Lens, Bubble Irregular, Bubble Scatter, HEMA Fragment and Bubble On Edge. A comparison resting on one of those cells cannot be read as evidence either way, so a declared tolerance, for example recall within five points, or a confidence interval per recall, is needed before any difference there is called real.

**Two things make the five models hard to compare, and both are fixable.**

1. **The training sets are unequal.** L24 would train on 1,995 pictures while L25 would train on 664, so a gap between those models could come from the training volume rather than from the line. Matching the five sets, by taking the same number of pictures per class per line, makes any difference attributable to the line.
2. **The five models carry different class lists**, so their overall accuracy figures are not directly comparable: a model with 16 classes has a different chance level from one with 21. The comparable quantity is the per-class recall on the 17 shared classes.

**A direct test of the premise, which costs one short run.** Train a classifier to predict the line from the pooled pictures. All 12,079 files are the same format, 2,048 by 2,448 greyscale, so there is no resolution difference to find. If that classifier cannot beat chance, the "no line signature" premise holds and the single-model conclusion rests on much firmer ground.

**Questions we need answered.**

1. Do the 7 classes that exist only in the older library still count? They hold 313 pictures, of which 175 exist nowhere else, and pooling does not answer this because no other folder labels them.
2. If Clear is later ruled to be a class, it returns as a 23rd class: 2,213 pictures carry Clear as their only label and sit outside the pool today. Every per-line number would then change.
3. Is a test set of 287 to 858 pictures per line enough, given that 35 class-and-line cells hold fewer than five test images and on L27 and L31 that is 7 and 9 classes?
4. Confirm the four classes that cannot support the line-by-line comparison: Dirty Camera and Bubble On 123 are scorable on one line only, and Dirty Strobe and HEMA Fragment on two lines, so their numbers stand alone.
5. Full line data, or volume-matched sets where every line trains on the same 664 pictures?
6. What tolerance counts as "the same" for the recall comparison?

**What this means.**

- The question is answerable: every picture carries its line number, and 17 of the 22 classes appear on three or more lines, which is what a line-to-line comparison needs.
- Pooling the folders by class is what makes it workable: the classes scorable on all five lines rise from 4 on the older library alone to 13 on the pool.
- Five line-specific models give a direct answer, because they can be compared class by class on the classes they share.
- The result is only conclusive if the five training sets are matched, the comparison is per-class recall rather than overall accuracy, and a tolerance is set in advance. Without those three, "similar" cannot be demonstrated either way.
- Dirty Camera and Bubble On 123 cannot be cross-checked between lines at all, so their numbers stand alone.
- Training is on hold until the questions above are answered.
