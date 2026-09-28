---
title: Multi-label split strategy for the ResNet50 classifier, and how it differs from a YOLO split
date: 2026-09-23
type: method
status: active
where: docs/multilabel_split_strategy_20260923.md
---

# Split strategy: multi-label ResNet50 versus YOLO

## Recommendation first

Split with **iterative stratification (Sechidis et al.) over the multi-label matrix, plus group-aware
assignment keyed on content md5, seed 42, 70/15/15, and a saved split file reused for every run.**
Basis: the 2026-09-22 export, 6,097 images, 5 LP classes, 3,377 with an LP tag.

## 1. The split problem

A row here is an image carrying a multi-hot vector, not one class: of 6,097 images, 3,377 carry at least
one LP tag, 178 carry exactly two, and 667 of the 3,952 tagged images carry two or more tags from any
family. A naive random split fails twice: label frequencies drift, since Folded Lens exists only 178
times, and rows are not independent, since 34 pictures sit in two class folders and 27 older-library
pictures are content-identical twins, so one copy can land in train and the other in test. Every split
must hold label frequencies steady **and** keep all records of one content hash in one split.

## 2. Recommended approach and why each ingredient is needed

| Ingredient | Why this data needs it |
|---|---|
| Iterative stratification (Sechidis et al.) | Holds each label's count proportional in all three splits. LP counts are 183 / 178 / 1,442 / 1,427 / 325, and 178 images carry the only LP combo, Folded Lens + Multiple Lenses. Single-label stratification cannot see that pair, so a naive split can strand the 178 Folded Lens examples |
| Group-aware assignment keyed on content md5 | The 34 twice-stored pictures and the 27 renamed twins are assigned as one unit, so content twins can never land in different splits |
| Fixed seed 42 | An unseeded rerun moves rare examples between splits and two runs stop being comparable |
| Split file saved | Rare-class test counts are about 27 images, so results must tie to one recorded assignment, not an unrepeatable shuffle |

## 3. Fallback: label powerset stratification

Stratify on the **label powerset**, the distinct label combination per image, with group-aware assignment
on content md5. On the LP head it works nearly as well, since only one real combo exists: Folded Lens +
Multiple Lenses, 178 images, giving 7 strata (empty, 5 singletons, 1 combo), each large enough to divide
three ways. The tradeoff is on the wider tag space: 15 distinct pairs there run down to a count of 1
(Missing Lens + Dirty Camera = 1), so strata fragment into single images that cannot appear in all three
splits, and individual label counts drift.

## 4. How this differs from a YOLO split

YOLO trains one class per box, so at box level the problem is single-label and its split only balances
class counts per box, one box being one row. Here one image carries a multi-hot vector of up to 4 tags
(667 of 3,952 tagged images carry 2+, top pair Multiple Lenses + Lens Off Center, 538), so the split must
balance up to 5 LP marginals plus the tag marginals over the same rows.

If the team considered YOLO for the tags: **forced**, a box per tag, which invents geometry for the
absence tags Missing Lens (325 images) and Missing Primary Package (1,427 images), which have no
location. **Lost**, image-level negative supervision, because unboxed regions train as background instead
of "this tag is absent"; the 667 multi-tag images become independent boxes instead of one joint target;
and evaluation moves from per-image multi-label F1 to per-box mAP. Box-level balancing counts an image's
boxes separately, so they can land in two splits unless grouped by image.

## 5. Concrete recipe

- **70/15/15**, seed **42**, group id = content md5, iterative stratification on the LP multi-hot matrix,
  over 6,097 grouped rows: about 4,268 / 915 / 915 images. The saved split file has one row per image:
  content hash, group id, split name.

| LP class | All images | Train 70% | Val 15% | Test 15% |
|---|---|---|---|---|
| Cavity Off Center | 183 | 128 | 27 | 27 |
| Folded Lens | 178 | 125 | 27 | 27 |
| Multiple Lenses | 1,442 | 1,009 | 216 | 216 |
| Missing Primary Package | 1,427 | 999 | 214 | 214 |
| Missing Lens | 325 | 228 | 49 | 49 |

- Rounded proportions; grouping can shift a few images. The two rare classes land at **26 to 27 test
  images each**, so report confidence intervals with every test metric (90% recall on 27 positives has a
  95% interval of about plus or minus 11 points), or run repeated splits and report the spread.
- **Negatives policy.** An image may serve as an LP-negative only if it carries at least one tag from
  another family, or sits in a finished task folder. The 2,145 images with no tag at all are not automatic
  negatives, and untagged Low Dose images are flagged unreliable: that task is only 76 of 1,952 frames
  finished, so no tag there means "not yet looked at", not "no defect".

## 6. Open question

The Fiber versus Extraneous Polymer naming conflict is unresolved and pending the official SME answer, so
any label set involving those two names stays provisional. The 5 LP classes and every count above do not
depend on it; regenerate the split file if the answer renames those pictures.
