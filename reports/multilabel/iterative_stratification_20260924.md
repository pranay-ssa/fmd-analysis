---
title: Iterative multi-label stratification: how it works and what it changed (2026-09-24)
date: 2026-09-24
type: report
status: active
where: reports/multilabel/iterative_stratification_20260924.md
---

# Iterative multi-label stratification: how it works and what it changed

Written after the lead asked how iterative multi-label stratification works, what it
gives us, and whether we can share it. Every number below was produced by running the
split on the label matrix and counting the result.

## The data the split runs on

The matrix holds one row per picture and five lens presentation tags as 0 or 1 columns.

| Lens presentation tag | Pictures carrying it |
|---|---:|
| Missing Primary Package | 1,427 |
| Multiple Lenses | 1,442 |
| Missing Lens | 325 |
| Cavity Off Center | 183 |
| Folded Lens | 178 |
| **Pictures in the matrix** | **3,377** |

3,377 pictures carry at least one of the five tags. 178 pictures carry two tags. Every
one of those 178 carries Folded Lens together with Multiple Lenses. No picture carries
three or more.

The delivered split is 80 train and 20 test: 2,700 pictures for training (79.95 per
cent) and 677 for testing (20.05 per cent), seed 42.

## Why an ordinary stratified split cannot be used

Three separate blockers, each of which alone is enough:

1. **The standard split needs one class per picture.** Our matrix has five columns per
   picture and up to two 1s in them. A function that expects a single class label
   raises an error when it is given five columns.
2. **The standard split makes one cut.** We need two cuts when a validation set is held
   out of the training data, and it offers only train or test.
3. **The standard split does not know about identical content.** Content hashing is the
   control for that: over the full 6,097-picture library, 34 pictures are stored in two
   folders and 27 are renamed twins, so a path-based split would put the same pixels on
   both sides. Inside this 3,377-picture set all 3,377 content hashes are distinct, so
   grouping is a no-op here, and the check still reports 0 groups crossing the boundary.

The usual workaround is to stratify on the exact combination of tags instead of on the
picture, which treats each combination as its own class. That workaround is discussed
further down.

## What a random split actually costs

Method: take the 3,377 rows, draw 677 of them for test at random, no stratification,
repeat for 1,000 different seeds, and record how far each tag's test count lands from
its target. The target is the test share multiplied by the tag's total, so 20.047 per
cent of 178 Folded Lens pictures is 35.7.

| Measure over 1,000 random 80/20 splits | Value |
|---|---:|
| Mean worst-tag drift from target | 17.83% |
| Median worst-tag drift | 17.21% |
| 95th percentile worst-tag drift | 33.56% |
| Worst drift seen in any seed | 54.13% |
| Splits where some tag drifted over 5% | 973 of 1,000 |
| Splits where some tag drifted over 10% | 843 of 1,000 |
| Folded Lens test count across seeds | 20 to 55 (target 35.7) |

The mechanism is small numbers. Folded Lens has 178 positives, so the test set should
hold 35.7 of them. A random draw put as few as 20 and as many as 55 in the test set.
A score measured against 20 positive pictures and the same score measured against 55
positive pictures are two different measurements, so the split alone would move the
reported number before the model changes anything.

Worst drift ever seen for each tag, over the same 1,000 seeds:

| Tag | Worst drift from target |
|---|---:|
| Folded Lens | 54.1% |
| Cavity Off Center | 41.7% |
| Missing Lens | 37.1% |
| Missing Primary Package | 16.8% |
| Multiple Lenses | 12.4% |

The three rare tags are the three worst-hit. That is the expected pattern: drift scales
with the scarcity of the tag, so the tags we most need to measure move the most.

## How iterative stratification works

The method is from Sechidis, Tsoumakas and Vlahavas, "On the Stratification of
Multi-label Data", ECML PKDD 2011, pages 145 to 158. It treats each tag independently
rather than treating each tag combination as a class.

The steps, in order:

1. Count how many pictures carry each tag: 178 carry Folded Lens, 1,442 carry Multiple
   Lenses, and so on.
2. For each split, work out the target count for each tag: the split's share multiplied
   by that tag's total. The test set at 20.047 per cent therefore targets 35.7 Folded
   Lens, 36.7 Cavity Off Center, 289.1 Multiple Lenses, 286.1 Missing Primary Package
   and 65.2 Missing Lens.
3. Walk the tags from rarest to most common, so Folded Lens is handled before Multiple
   Lenses.
4. While handling one tag, give its still-unassigned pictures to whichever split is
   furthest behind that tag's target. The gap between target and current count is the
   deficit, and the deficit decides the destination.
5. Track how full each split already is, so the sizes still land on 80 and 20.
6. A picture only moves while a tag it actually carries is being handled. Correcting one
   tag therefore cannot push another tag off target.

Two properties follow from step 6 and they are the reason the method is used. Each tag's
imbalance ratio is preserved in every split, and every split keeps positive examples for
every tag. The paper states the matching trade: exact subset sizes are given up in
favour of preserving each label's ratio, and on two of its benchmark datasets only this
method produced subsets holding positive examples for all labels.

## What it produces on this data

The delivered 80/20 split, counted back from the file:

| Tag | In all 3,377 | Test target | Test got | Drift |
|---|---:|---:|---:|---:|
| Cavity Off Center | 183 | 36.7 | 37 | +0.85% |
| Folded Lens | 178 | 35.7 | 36 | +0.88% |
| Multiple Lenses | 1,442 | 289.1 | 289 | −0.03% |
| Missing Primary Package | 1,427 | 286.1 | 286 | −0.03% |
| Missing Lens | 325 | 65.2 | 65 | −0.24% |

Worst drift across all five tags: **0.88 per cent**, against 17.83 per cent as the mean
for a random split. Content groups crossing the boundary: **0**. Re-running the builder
with the same seed writes a byte-identical file.

One count is worth stating plainly because it looks like an arithmetic error. Twenty per
cent of 3,377 is 675.4, and the plain ceiling of that is 676, yet the split holds 677
test pictures. The stratifier counts its own test pool. The same call on a different
label matrix returns 676, so the single-picture difference comes from how the algorithm
allocates this particular label matrix, and not from anyone editing counts by hand.

## The simpler alternative, and the honest reason we do not use it

Stratifying on the exact tag combination is the other interpretation in the same paper.
On this matrix it works. Measured on the five-tag matrix: **5 distinct combinations**,
the smallest held by 178 pictures, the largest by 1,427, and no combination held by
fewer than 178. Run over the same 1,000 seeds it produced the same 0.88 per cent worst
drift on every seed, exactly as the iterative method did.

So on today's matrix both methods give identical counts, and only which pictures land in
which split changes with the seed. That is the honest comparison.

The method we keep is chosen for what happens when the matrix changes:

- Combination stratification needs every combination to be divisible. A combination held
  by one picture cannot be split, and the stratifier refuses to run.
- The wider defect taxonomy holds 22 classes, and the Clear tag would be the 23rd. Tag
  combinations multiply with every class added, so single-picture combinations appear
  quickly.
- The iterative method never looks at combinations. It holds each tag's count, so it does
  not care how the combinations are distributed.

## What stratification does not do

Each of these was checked against the data rather than assumed:

- **It does not fix class imbalance.** Folded Lens has 178 positives against 1,442 for
  Multiple Lenses, a ratio of about 1 to 8.1. Both ratios are preserved by the split, and
  both stay lopsided. Reweighting the loss handles that.
- **It does not stop identical pixels leaking across the split.** Content hashing does,
  and the check reports 0 groups crossing the boundary in this set.
- **It does not add training data.** The counts are what the library holds.
- **It does not choose the epoch.** A validation set does that. Holding 507 of the 2,700
  training pictures aside as validation does not change the 677 test pictures: both split
  files come from the same first cut, and the test membership was checked to be identical
  in both. So the choice between them costs 507 training pictures and buys the ability to
  pick the best epoch without touching the test set.

## How to reproduce it

Seed 42. Group rows by content hash, reduce each group to the logical OR of its members'
tags, run iterative stratification for a first cut at 20 per cent for test, then split
the remainder if a validation set is wanted. Record the seed, the per-tag drift and the
count of groups crossing the boundary in the split's companion log, and never regenerate
the file during training, so that two runs always see the same data.

Recorded for the delivered split: 2,700 train and 677 test, worst per-tag drift 0.88 per
cent, 0 groups crossing, byte-identical on rerun.

## Key Takeaways

- The five-tag matrix holds 3,377 pictures, and 178 of them carry two tags, all of them
  Folded Lens with Multiple Lenses.
- An ordinary stratified split cannot run on it: it needs one class per picture, makes one
  cut, and knows nothing about duplicate content.
- A random 80/20 split lands a rare tag's test count anywhere from 20 to 55 against a
  target of 35.7, measured over 1,000 seeds, and drifts over 5 per cent on 973 of those
  seeds.
- Iterative stratification holds every tag to within 0.88 per cent of target on this data,
  keeps positive examples of all five tags in both splits, and reproduces byte-for-byte
  from seed 42.
- Stratification preserves imbalance rather than removing it: Folded Lens still has 178
  positives against 1,442 for Multiple Lenses, so loss reweighting remains necessary.
- Stratifying on tag combinations gives the same counts today, because the matrix holds
  only 5 combinations and the smallest has 178 pictures. It stops working once a
  combination holds a single picture, which is why the tag-independent method is kept.
- The validation set and the split method solve different problems. Stratification
  controls composition, validation controls which epoch is reported, and the 677 test
  pictures are identical either way.
