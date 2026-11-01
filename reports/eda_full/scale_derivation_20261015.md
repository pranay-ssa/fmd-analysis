---
title: The scale behind the micron columns, and the second measurement attempt
date: 2026-10-15
type: result
status: active
where: reports/eda_full/scale_derivation_20261015.md
---

# The scale behind the micron columns, and the second measurement attempt

This record settles what the two candidate scales are, where the published one
came from, and why a second attempt to measure the scale on the library folders
does not give a usable number. It backs the reworked `Box geometry` sheet of the
client workbook, which now carries three new blocks in this order: the scale
behind the micron columns, the second measurement per folder and per line, and
two corrections.

The sheet is rebuilt by `experiments/eda_full/build_workbook.py`, which imports
`experiments/eda_full/scale_section.py`. Every figure in the new sheet is
computed by that module from the run artifacts, not typed by hand. Run:

```bash
./.venv/Scripts/python.exe experiments/eda_full/build_workbook.py \
    --numbers reports/eda_full/full_numbers.json \
    --out reports/eda_full/FMD_Full_EDA_20261015.xlsx
./.venv/Scripts/python.exe experiments/eda_full/verify_deliverables.py
```

Nothing here reads or writes the shared VM. All inputs are under `run/`.

## The two scales

| Scale (microns per pixel) | The columns that use it | Status |
|---|---|---|
| 18.1165 | every column headed at 18.1165 | our published value, derived below |
| 18.25 | every column headed at 18.25 | spoken by the lead, written in no document we hold |

## How 18.1165 was derived, exactly

The routine that produced it is `/data/FMD_Data_26082026/measure_scale.py` on the
shared VM. Read on its own terms, it does this:

- It reads **200 random frames matching `*Pass1*`** from the folder
  `20260826_T24_Production_Sample/sample folder`. That folder holds 10,000
  images, of which 7,164 are `_Pass1`. So the scale was measured on 200
  machine-PASSED frames from a **separate production-sample drop dated
  2026-08-26**.
- That sample is **not** the 1,047 annotated batch and **not** the library
  folders. The scale was never measured on either.
- The nominal lens diameter, `NOMINAL_LENS_DIAMETER_UM = 14_200.0`, is
  **hardcoded in that routine** and appears in no document the client has given
  us. It is our own figure.
- The method: a bright mask at 0.45 of the 99.5th percentile; the cavity centre
  from the mask centroid; the cavity radius from the row and column profile
  widths; the radial intensity profile smoothed over 7 pixels; the most
  prominent dark dip searched between 0.50 and 0.92 of the cavity radius; the
  lens diameter taken as twice that radius; a frame accepted only when the dip
  prominence exceeds 1.0; finally a 15 percent trimmed mean over the accepted
  frames.
- Result: a lens rim diameter of **783.8 px**. And **14,200 / 783.8 = 18.1165**.
- The spread on the 200 frames: median **786 px**, standard deviation **41.6
  px**, interquartile range **764 to 804 px**, relative spread **5.3 percent**.

Because the 14,200 micron nominal is ours and sits in no client document, every
micron figure computed at either scale is a proportional size, not a calibrated
measurement. If the true lens diameter differs, every micron number moves by the
same factor.

## What is known about 18.25

18.25 is **written in no document we hold**. It exists only in our own notes
recording that the lead said it. No derivation, no sample and no nominal
supports it, so it cannot be checked against anything we have. The gap between
18.1165 and 18.25 is 0.7 percent. The spread of the 18.1165 measurement alone is
5.3 percent, so the two cannot be told apart by any measurement in this
workbook, and neither should be read as confirmed.

## The second measurement, on the library folders, does not behave

A second run applied the same rim and cavity method to the library folders. It
does not give a usable scale, and the reason is the method itself.

The method finds the rim dip between 0.50 and 0.92 of the cavity **radius**, so
the ratio `rim_px / cavity_px` must lie inside that window. A ratio pinned at the
window edge is the search hitting its limit, not a rim.

| Measure | Pictures |
|---|---|
| Sampled for this measurement | 1,727 |
| Measured (the method returned a value) | 1,680 |
| Pinned at the upper window edge (ratio at or above 0.915) | 332 |
| Below the lower window edge (ratio below 0.515) | 24 |
| Valid (ratio from 0.515 to 0.910) | 1,253 |
| Set aside by the window | 427 |

No measured ratio exceeds 0.918, and the highest is 0.9178. That confirms the
pinned rows are the search stopping at its own 0.92 limit, never a rim beyond
it. The 427 set aside are 25.4 percent of the 1,680 measured pictures, so the
method fails on about a quarter of this population by its own boundaries. The
counting unit is the distinct picture: the sample draws a picture once per
folder group it is held in, so 1,809 rows stand for 1,727 pictures.

### Per folder, both views

View one uses every valid picture. View two removes the pictures whose canonical
defects include a missing lens, multiple lenses, a missing primary package, an
obstructed view or a folded lens. A picture with no resolved label is kept in
view two, because none of those five classes can be attributed to it.

| Folder | View | n | rim p50 (px) | implied microns per pixel at the 14,200 micron reference |
|---|---|---|---|---|
| Updated Objects | all valid pictures | 435 | 752.0 | 18.88 |
| Updated Categorical | all valid pictures | 730 | 666.0 | 21.32 |
| Library | all valid pictures | 88 | 754.0 | 18.83 |
| Updated Objects | excluding the five no-lens classes | 434 | 752.0 | 18.88 |
| Updated Categorical | excluding the five no-lens classes | 328 | 676.0 | 21.01 |
| Library | excluding the five no-lens classes | 88 | 754.0 | 18.83 |

### Per production line, both views

| Line | View | n | rim p50 (px) | implied microns per pixel at the 14,200 micron reference |
|---|---|---|---|---|
| L24 | all valid pictures | 307 | 682.0 | 20.82 |
| L25 | all valid pictures | 232 | 716.0 | 19.83 |
| L26 | all valid pictures | 270 | 742.0 | 19.14 |
| L27 | all valid pictures | 239 | 712.0 | 19.94 |
| L31 | all valid pictures | 205 | 728.0 | 19.51 |
| L24 | excluding the five no-lens classes | 147 | 760.0 | 18.68 |
| L25 | excluding the five no-lens classes | 139 | 724.0 | 19.61 |
| L26 | excluding the five no-lens classes | 160 | 750.0 | 18.93 |
| L27 | excluding the five no-lens classes | 232 | 712.0 | 19.94 |
| L31 | excluding the five no-lens classes | 172 | 730.0 | 19.45 |

### The join, and why the folders disagree

The canonical defect of each picture is read by matching its winning path in
`run/eda_full_20261015/resolved_labels.csv`. That match is a **path match, not a
content match**, because that file carries paths rather than content hashes. Of
the 1,680 measured pictures, **650 carry no resolved label** and so cannot be
classified; at row level **676 of the 1,809 sampled rows fail to match**. A
picture with no resolved label cannot be positively confirmed to hold a normal
lens, and is counted, not dropped.

The two Updated folders disagree sharply, and the disagreement survives removal
of the five classes. The categorical folder reads near 21 microns per pixel and
the other Updated folder near 19. That is a property of the pictures, not a real
scale difference. Many pictures in the categorical folder are classes where a
normal single lens is not present (missing lens, multiple lenses, missing
primary package, view obstructed, folded lens), so there is no rim to find and
the method returns a small or edge-pinned value. Image brightness also varies by
class, which moves the relative brightness mask and therefore the cavity radius
the method depends on.

**These numbers are not quotable as a scale.** They are shown only to make the
failure visible: the method fails on about a quarter of this population by
hitting its own search limit, so a scale read from them would be an artefact of
the method, not a measurement of the lens.

## Two corrections carried into the sheet

- The October batch analysis is superseded by the full-coverage analysis. It is
  kept for history, and its figures are not to be quoted.
- Its earlier statement that the size gate is not a 300 micron cut was an
  artefact of measuring the box diagonal. Measured on the box's longer side
  instead, the gate is a clean 300 micron cut: no picture sits on the wrong side
  of the boundary.

## Files

| Artifact | What it is |
|---|---|
| `reports/eda_full/FMD_Full_EDA_20261015.xlsx` | the client workbook, `Box geometry` sheet reworked in place |
| `experiments/eda_full/scale_section.py` | the module that computes and writes the new sheet block |
| `experiments/eda_full/build_workbook.py` | the workbook builder, now importing the module |
| `experiments/eda_full/verify_deliverables.py` | the deliverable verifier, extended to check the new block |
| `run/eda_full_20261015/scale_samples.csv` | the sampled rim and cavity measurement, 1,809 rows |
| `run/eda_full_20261015/resolved_labels.csv` | the resolved label table, the join source |

## Verification

The workbook was rebuilt from `build_workbook.py`. Only the `Box geometry` sheet
changed shape, from 58 to 121 rows; every other sheet is byte-for-byte unchanged
in shape and row count. `verify_deliverables.py` runs 127 checks with 0 failures
and exits 0, including a new block that checks the derivation tokens, the window
counts, the per-folder and per-line table rows, and the order of the four new
blocks. An em dash scan and a path, file-name and ticket-token scan across every
cell of every sheet both return 0. Nothing was written to the shared VM.
