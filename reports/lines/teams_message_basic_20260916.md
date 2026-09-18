# Teams message, basic version (2026-09-16)

Short, postable version for the lead. Self-contained: no cross-references, every claim carries
its number in the same sentence. No local paths, no em dashes.

---

**Can one model handle every production line? Where we are**

We pooled the three image folders by defect class, because they label the same classes rather than different
ones, and counted every picture once. The 12,079 files are **10,614 different pictures**, and **8,401** of
them carry one of the 22 defect classes. The other 2,213 have Clear or HEMA as their only label, and neither
is a defect class, so they sit outside the set. In addition, 1,287 files in the older library are repeats of
pictures we already have, so the new folders add pictures to a class rather than adding new classes.

The pooling is what makes the comparison possible: **13 of the 22 classes appear on all five lines, and 17
appear on three or more**, so 17 classes can be compared line by line. On the older library alone only 4
classes appeared on all five lines.

**The plan.** Five ResNet-50 models, one per line, each trained on its own line's data only and scored on
that line's held-out pictures, then compared on per-class recall across the 17 shared classes.

| Line | Pictures | Classes present | Test pictures at 70:30 | Training pictures |
|---|---|---|---|---|
| L24 | 2,853 | 21 | 858 | 1,995 |
| L25 | 951 | 18 | 287 | 664 |
| L26 | 1,220 | 19 | 365 | 855 |
| L27 | 1,365 | 16 | 409 | 956 |
| L31 | 2,012 | 19 | 606 | 1,406 |

**Two limits on what the comparison can show.**

1. **Some classes are tested on only a few pictures.** Of the 87 class and line combinations we can score,
   **35 are left with fewer than five test pictures**, and L27 and L31 account for 7 and 9 of them. A class
   with four test pictures can score 3 out of 4 or 4 out of 4, so one picture moves its score by 25 points.
   Without an agreed tolerance (for example, treat a recall gap of five points or less as the same), one
   lucky picture will read as a real difference between two lines.
2. **The five models would not train on equal amounts of data.** L24 would train on 1,995 pictures and L25 on
   664, three times fewer. If L25's model scored lower, we could not tell whether L25's pictures are harder
   or its model simply saw less data. We propose training every line on the same 664 pictures, taken in
   proportion to each line's own class mix. The stricter option, equal numbers of pictures per class per
   line, would leave every line with about 181 pictures, because some classes hold a single picture on their
   scarcest line, so we do not recommend it.

**What we need from you**

1. Do the 7 classes that only the older library carries still count? They hold 313 pictures, of which 175
   exist nowhere else.
2. Is a test set of 287 to 858 pictures per line enough, given that 35 combinations are left with fewer than
   five test pictures?
3. Confirm the four classes that cannot be compared across lines: Dirty Camera (L24 only), Bubble On 123 (L24
   and L31), Dirty Strobe (L25 and L26), HEMA Fragment (L24 and L31).
4. Confirm the split at 70:30, which leaves 87 class and line combinations scorable, against 78 at 80:20.
5. Confirm that we train every line on the same 664 pictures rather than on all of its own data.

Training stays on hold until these five are answered.
