---
title: PRODUCTION_20260925 batch: EDA, tags and micron findings
date: 2026-10-13
type: result
status: active
where: reports/production_20260925/batch_eda_findings_20261013.md
---

# PRODUCTION_20260925 batch: EDA, tags and micron findings

What the 1,047-image production batch annotated on 2026-09-25 contains, what its
labels mean, and how large each defect class actually is. The workbook holds the
detail; this page holds the findings.

## Deliverable

`FMD_Production_Batch_EDA_20261013.xlsx`, eight sheets:

| Sheet | Contents |
|---|---|
| Read me | Purpose, provenance, regeneration steps, headline findings, caveats |
| EDA | Batch composition, codes per image, shape provenance, rotation, filename covariates |
| Distributions | Five charts of the batch shape, plus the breakdown of the multi-code tail |
| Tags & codes | All 24 codes, one row each: meaning, confirmation state, shape type, counts, median size |
| Annotator email | The handover email checked against the delivered files: the rule behind the micron tags, the stated counts against what arrived, and whether the rule reproduces the flags |
| Micron | Box size per code in pixels and microns, the recorded thresholds, the size gate, size outliers |
| Per image | One row per image with codes, shape counts, line, date and measured cavity geometry |
| Checks | The invariants behind the summary numbers, each re-checkable |

Every figure is computed from the seven CVAT XML exports. Nothing is typed by
hand. `batch_numbers_20261013.json` beside the workbook is the computed record
the builder formats, and `experiments/production_20260925/` holds the
scripts (compute, build, verify, and two that test the threshold rule).
`verify_workbook.py` re-derives the counts by regex over the raw XML, a different
method from the ElementTree parse the compute step uses, and cross-checks the
the workbook cells, the sums, the gate subsets and the text; 39 checks, 0 failures.
`test_micron_metric.py` tests the stated threshold rule, and
`annotator_email_20261013.json` holds the email's counts verbatim so they can be
reconciled again later.

## EDA

The batch is 7 annotation jobs, 1,047 images, 12,793 boxes and 1,318 tags over
24 codes. All images are 2,448 by 2,048. It is a multi-label set: 743 of 1,047
images carry more than one code, the median image carries 3, and the busiest
carries 11. Only 303 images carry exactly one code.

One class dominates. `P2_BB` (Bubble) appears on 747 images, 71.3 percent of the
batch, and holds 10,075 of the 12,793 boxes. `P2_BC` (Bubble Cluster) is next on
407 images. A one-folder-per-class split would put most of the set in the Bubble
bin and would discard the co-occurring labels.

The codes that most often appear together are `P2_BB` + `P2_BC` on 406 images,
`P2_BB` + `P3_FM` on 276 and `P2_BB` + `P2_DC` on 200.

Annotation provenance is largely machine. 12,640 of the 12,793 boxes carry
source `file`, meaning they arrived with an imported annotation file, and 153
were drawn by hand. So most of this set is pre-annotation that a human reviewed,
not annotation a human created. Worth knowing before treating it as ground
truth.

The boxes are genuinely rotated. 12,135 of 12,793 boxes carry a rotation value,
658 carry none, and none of the rotated values is exactly zero. 11,600 of the
12,135, which is 95.6 percent, sit at an angle that is not a multiple of 90
degrees, and the values spread across all eight 45 degree buckets. Any pipeline
that assumes axis-aligned rectangles will mis-draw almost all of them.

Two filename families exist. 878 images use a legacy form carrying date, time,
line, cavity position and a serial number. The other 169 carry pallet, board id,
a fail count and a selection score as well. The line is available for every
image: L24 660, L26 237, L27 135, L25 15. The batch spans nine consecutive days,
2024-11-01 to 2024-11-09. The 169 scores run from 0.9001 to 1.0, so this batch
sits in the high-scoring tail of whatever upstream selection produced it. The
score is a sampling covariate, not a label.

## Distributions, and the multi-code tail

Codes per image are right-skewed with a short tail: median 3, mean 3.12, 90th
percentile 5, 95th percentile 6, and a maximum of 11. Counts of 3 and 4 together
hold 386 of the 1,047 images, so the peak sits at the middle and the tail is
thin. 13 images carry 8 or more codes, which is 1.2 percent of the batch, and
they hold 3.3 percent of all shape placements, so a handful of busy files is not
driving the set.

The 11-code image will be the one that gets questioned, and it has a clean
answer. Three of its codes are derived. It carries six localised defects
(`P2_BB`, `P2_BC`, `P2_BI`, `P3_EP`, `P3_FIB`, `P3_HE`) and five whole-image
flags, and three of those five flags are `_MICRON_THRESHOLD` tags that merely
say one of the box codes already counted is oversized. So its distinct problems
number 8, not 11.

That generalises. Excluding the four derived size-gate flags, the maximum falls
from 11 to 9 codes and the mean from 3.12 to 2.87. The reason the apparent count
runs high is structural: an image's codes are the union of two independent
families, localised defects carried as boxes and whole-image flags carried as
tags, and the mean image has 1.86 of the first and 1.26 of the second. The tail
images average 5.2 box codes and 3.8 tag codes, so they are high on both at once
rather than being an artefact of one family.

One code drives most of the spread. `P2_BB` is on 747 images, 71.3 percent of the
batch, and images carrying it average 3.94 codes against 1.08 for images without
it. Bubble is the common condition, and its presence pulls most of the set into
the multi-label region.

All of this is charted on the Distributions sheet of the workbook, which also
lists every image at 8 or more codes with the breakdown, so the tail can be
inspected rather than assumed.

## Tags

All 24 codes are catalogued in the workbook with their meaning and confirmation
state. Two structural facts matter more than the names.

First, a code is either a box or a tag, never both. Nine codes carry boxes and
describe localised defects (`P2_BB`, `P2_BC`, `P3_FM`, `P3_FIB`, `P2_WP`,
`P2_BI`, `P3_HE`, `P3_EP`, `P2_BST`). Fifteen are whole-image flags with no
location at all, including `P1_MPP` on 226 images, `P2_DC` on 204, `P2_LOC` on
187, `P1_ML` on 169 and `P2_LD` on 118. A tag-only code cannot be a detector
target; it can only be an image-level label.

Second, all 24 codes now carry a name. Four of them were placeholders until
2026-10-13, when they were named as `P2_DC` Dirty Camera (204 images), `P2_BI`
Bubble Irregular (108), `P1_FL` Folded Lens (59) and `P2_BST` Stretched Bubble
(2). The first three match the September code legend directly, and `P2_BST`
rests on elimination plus that same reading, so it is the one still worth a
client check before a class list goes out.

Four codes ending `_MICRON_THRESHOLD` are a size gate on their base code rather
than separate classes. The annotator's handover email confirms this and gives the
rule: the four gated codes are exactly the four P3 (foreign material) codes, and
the tags mark images containing debris that exceeds the 647-micron size
threshold. The email asks that these images be fed into the edge algorithm
training process.

The gate is visible in the data. On the images carrying the base code, the
largest base-code box has a much bigger median when the gate flag is present:

| Base code | Flagged images | Unflagged images | Flagged median | Unflagged median | Ratio |
|---|---|---|---|---|---|
| `P3_EP` | 32 | 3 | 143.2 px / 2,595 um | 19.2 px / 348 um | 7.46x |
| `P3_FIB` | 85 | 69 | 75.3 px / 1,364 um | 31.0 px / 561 um | 2.43x |
| `P3_FM` | 53 | 229 | 58.1 px / 1,053 um | 23.4 px / 423 um | 2.49x |
| `P3_HE` | 95 | 0 | 1,224.5 px / 22,183 um | none | not testable |

So the flag tracks size, and the flagged group's median sits above the stated 647
microns on every class while the unflagged group's median sits below it (348, 561
and 423 microns). What the stated rule does not do is reproduce every individual
flag. Reading a box's size as its longest side comes closest: cutting at 647
microns reproduces 100 percent of the flags on `P3_EP` and `P3_HE`, and 90.9 and
90.4 percent on `P3_FIB` and `P3_FM`. Read as the diagonal it is 100, 88.3, 85.8
and 100 percent. No reading of size, diagonal, longest side, shorter side,
same-area circle diameter or geometric mean of the sides, reproduces all four
codes at exactly 647 microns.

`P3_HE` is the case that looked odd before the email arrived, and the rule
explains it. Every one of its 95 images carries the flag because every one of its
boxes exceeds the threshold: its smallest box is 5,562 microns, about eight times
647 microns. So it is not flagged unconditionally, it is flagged by the same rule
applied to a class that always exceeds it.

## The handover email, checked against what arrived

The email states 1,047 images, which matches, and it predates the validation pass:
it says the author is still validating and will upload once complete. So its
per-code counts are the state at that time and the delivered XML is the source of
truth. The differences are still worth reading, because they show what validation
changed.

| Code | Email stated | Delivered shapes | Change |
|---|---|---|---|
| `P2_DC` | 28 | 204 | +176 |
| `P1_ML` | 221 | 170 | -51 |
| `P3_FM` | 604 | 571 | -33 |
| `P2_LOC` | 216 | 187 | -29 |
| `P3_EP` | 56 | 39 | -17 |
| `P2_BST` | 13 | 3 | -10 |
| `P3_FIB` | 229 | 219 | -10 |
| `P2_BB` | 10,060 | 10,075 | +15 |
| everything else | | | within 8 |

`P2_DC` (Dirty Camera) moved by more than any other code, a sevenfold increase.
The tag-only codes with no ambiguity
at all, `P1_MPP` at 226, `P2_LD` at 118, `P2_DS` at 22 and `P1_PPM` at 2, did not
move.

The micron flags moved too: `P3_FM_MICRON_THRESHOLD` from 65 to 53,
`P3_FIB_MICRON_THRESHOLD` from 89 to 85, `P3_EP_MICRON_THRESHOLD` from 33 to 32,
and `P3_HE_MICRON_THRESHOLD` from 92 to 95. Because the flags were edited after
the script ran, the delivered flags are not exactly what the stated rule
produces, which is the likeliest reason no read of the rule reproduces all four
codes exactly.

One naming difference: the email writes `P2_FOV` where the delivered file writes
`F2_FOV`, for the same defect, View Obstructed. One of the two is a typo and it
should be settled before either name goes into a class list.

## Micron measurements

Box size is the diagonal of the annotated rectangle, so it is a length across
the defect rather than a diameter or an area. Conversion is at 18.1165
micrometres per pixel, the same scale the crop pipeline uses. Rotation does not
change a diagonal, so these sizes hold for the boxes as drawn. The lens is 786
px across, which is 14,240 micrometres, and it varies about 5.3 percent image to
image.

| Code | Boxes | Median px | Median um | P75 um | Max um |
|---|---|---|---|---|---|
| `P2_BB` Bubble | 10,075 | 9.2 | 167 | 224 | 22,049 |
| `P2_BC` Bubble Cluster | 1,071 | 16.1 | 291 | 436 | 10,243 |
| `P2_WP` Wet Package | 591 | 45.7 | 829 | 1,843 | 22,698 |
| `P3_FM` Foreign Matter | 571 | 17.0 | 309 | 580 | 3,756 |
| `P3_FIB` Fiber | 219 | 43.2 | 783 | 1,231 | 21,734 |
| `P2_BI` Bubble Irregular | 128 | 37.2 | 673 | 1,526 | 14,244 |
| `P3_HE` HEMA Obstruction | 96 | 1,222.6 | 22,149 | 24,350 | 28,194 |
| `P3_EP` Extraneous Polymer | 39 | 101.3 | 1,835 | 4,032 | 19,416 |
| `P2_BST` | 3 | 37.3 | 676 | 1,259 | 1,841 |
| All boxes | 12,793 | 10.2 | 184 | 285 | 28,194 |

`P3_HE` is not a defect spot. Its 96 boxes have a median diagonal of 22,149
micrometres, which is larger than the 14,240 micrometre lens, so it marks a
region. It should not be trained as a detector target beside classes whose
medians run from 167 to 1,835 micrometres. This needs the annotator to say what
it is meant to cover.

Crossing the recorded thresholds, 2,972 boxes exceed 300 microns (23.2 percent
of all boxes), 1,598 exceed 500 microns (12.5 percent) and 1,230 exceed 647
microns (9.6 percent).

Sizes also have a long tail that is worth a look before training. 52 of the
10,075 `P2_BB` boxes are over 200 px in diagonal while that class median is 9.2
px, and 63 of the 591 `P2_WP` boxes are over 200 px. Those are not the same
object as the rest of their class.

Spatially the annotation is sane. Measured against the cavity of each image's
own part rather than the image centre, because the part is not centred in the
frame, the median box centre sits at 0.90 of the cavity radius, the 95th
percentile is 1.18 and the maximum is 1.54. Only 3 boxes of 12,793 fall further
out than 1.5 times the radius, so nothing is annotated on the tray or the
background. 29.3 percent of centres land just outside the measured radius, which
is a threshold effect: the radius is a slightly conservative estimate of the
package extent.

## Open questions

1. Ask which reading of a box's size the threshold script uses, since the email
   states 647 microns but not how size is measured, and no reading reproduces all
   four codes. Ask also whether the micron tags were hand-edited during
   validation, because their counts moved between the email and the delivered
   file.
2. Ask what happened to `P2_DC`, which went from 28 to 204 between the email and
   the delivered file. Its name, Dirty Camera, is settled now; the count change is
   not. `P2_BST` = Stretched Bubble is the only one of the four 2026-10-13 names
   that rests on elimination, so confirm that one against the client legend.
3. Settle `P2_FOV` against `F2_FOV`; the email and the XML disagree on the
   prefix.
4. Get the annotator's definition of `P3_HE`. Its size says it marks a region
   rather than a spot, and the 647 micron rule explains why it is always flagged,
   but what the region covers is not recorded. Settle whether its 96 region boxes
   stay in the detection set.
5. Decide whether the 9,391 unannotated images in the blob folder are wanted as
   explicit negatives. This batch is 1,047 of the 10,438.
6. Check the over-200 px outliers in `P2_BB` and `P2_WP`; they are likely region
   marks or mislabels rather than defects at that class's scale.
7. Decide how to handle multi-label training, since 743 of 1,047 images carry
   more than one code and a single-label split loses most of the signal. Note
   also that 19 images carry two micron tags and one carries three, so the
   edge-training selection the email describes is not a partition.

## Regenerating

```
python experiments/production_20260925/batch_numbers.py \
    --annotations <folder with the 7 XML> \
    --cavity vm/ops/cavity_geometry_all.json \
    --scale <path to scale_estimate.json> \
    --out batch_numbers.json
python experiments/production_20260925/build_workbook.py \
    --numbers batch_numbers.json \
    --out FMD_Production_Batch_EDA_20261013.xlsx
python experiments/production_20260925/test_micron_metric.py \
    --annotations <folder> --out micron_metric_test.json
python experiments/production_20260925/verify_workbook.py \
    --annotations <folder> --numbers batch_numbers.json \
    --workbook FMD_Production_Batch_EDA_20261013.xlsx
```

`batch_numbers.py` picks up `annotator_email_20261013.json` and
`micron_metric_test.json` from its own directory by default, so the workbook's
Annotator email sheet is built without extra flags.

The shared VM keeps only the data: `README.md`, `manifest.csv`,
`annotations/` and `images/`. No script is left there.
