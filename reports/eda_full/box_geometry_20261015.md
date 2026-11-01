---
title: Box geometry and micron size distributions
date: 2026-10-15
type: result
status: active
where: reports/eda_full/box_geometry_20261015.md
---

# Box geometry and micron size distributions

Ticket 012 of the full-coverage EDA map. Box size in pixels and in microns, per
canonical defect, per folder group and per production line, with the cavity
measured per image rather than assumed, at both candidate scales.

## What is measured, and at which scale

The size measure is the rectangle diagonal `sqrt(w^2 + h^2)`, invariant to the
rotation attribute that most boxes carry. Boxes come from
`run/eda_full_20261015/resolved_labels.csv`, `shape_kind == box`. Pictures are
resolved to folder group and line through `picture_table.csv`, keyed on content
md5, never on a path, because 187 basenames hold a content that also exists
under a second name.

Two microns-per-pixel scales are in circulation:

- **18.1165** microns per pixel, ours, the published value from the production
  sample.
- **18.25** microns per pixel, spoken by the lead and written nowhere (ticket
  008). Ticket 013a established that the 0.07 percent gap between them is far
  inside the measurement noise, so neither can be distinguished by measurement.

Both appear side by side in every table below and the scale is named in the same
table. The pixel columns are primary. The micron columns are for completeness.
Folder group is Updated (both Updated folders together) or Library
(`ICube Defects Library`), taken from the top folder of the picture's winning
path. Line comes from `picture_table.csv`.

## Counts, and the excluded tags

| Class | Count |
|---|---|
| Boxes (this analysis) | 14,182 |
| Tags excluded | 5,832 |
| Distinct pictures carrying at least one box | 1,130 |

All 20,014 surviving shapes split into 14,182 boxes and 5,832 tags. Only the
14,182 boxes enter every distribution here. Every box in `resolved_labels.csv`
appears exactly once in `box_sizes.csv`; the verifier proves the multisets are
identical.

## Rotation, and the axis-aligned share

The rotation attribute is carried by most boxes and absent on the rest. An
axis-aligned box is one whose rotation is absent or exactly 0.0.

| Measure | Count | Share |
|---|---|---|
| Axis-aligned (rotation absent or 0) | 660 | 4.65 percent |
| Rotated | 13,522 | 95.35 percent |
| Total | 14,182 | 100 percent |

No box carries an explicit 0.0: all 660 axis-aligned boxes have an absent
rotation attribute, and no box with a written rotation is exactly zero. The
diagonal is invariant to rotation, so the size measure does not depend on this
split.

## The cavity, measured per image

The cavity is measured, not assumed, because its centre is not the image centre.
The routine is reused verbatim from the 2026-10-13 run
(`vm/ops/measure_cavity_all.py`), carried to the VM as
`vm/ops/measure_cavity_library.py`: the bright-blob mask, the 0.45 times p99.5
threshold, the half-max column and row width rule and the divide-by-four radius.

| Scope | Pictures |
|---|---|
| Census measured (every distinct picture in `picture_table.csv`) | 10,614 |
| Measured, flag `ok` | 10,470 |
| Could not measure | 144 |

The 144 failures are one named class, `low_bright`: the p99.5 intensity is below
20, so there is no bright blob to threshold. Every one of them is a dark or
obstructed frame (the View Obstructed library folder, for example). They are
counted and named, not dropped. No picture failed for `no_mask`, `missing` or an
exception.

The 2026-10-13 cavity output (`vm/ops/cavity_geometry_all.json`) covered only
the 1,047 production-batch images, 1,016 of them measurable. It did not cover
the library. This run covers the whole census.

Cavity radius, in pixels, over the 10,470 measured pictures:

| Radius (px) | p25 | p50 | p75 |
|---|---|---|---|
| Cavity radius | 417.25 | 433.50 | 444.50 |

Cavity centre offset from the image centre (1,224, 1,024), over the same
pictures: median 132.0 px (x 94.0 px, y 20.9 px), p95 221.8 px, max 935.8 px.
The cavity is not centred, which is why it has to be measured per image.

## Box size per canonical defect

Diagonals in pixels and in microns. Both scales, named, side by side. p25, p50
and p75, never a bare mean. Defects are ordered by box count.

| Canonical defect | n | diag px p25 | p50 | p75 | um p50 at 18.1165 | um p50 at 18.25 |
|---|---|---|---|---|---|---|
| bubble | 10,869 | 7.86 | 9.30 | 12.57 | 168.53 | 169.77 |
| bubble_cluster | 1,182 | 12.38 | 16.77 | 25.75 | 303.85 | 306.09 |
| wet_package | 662 | 23.99 | 51.99 | 112.50 | 941.93 | 948.87 |
| foreign_matter | 626 | 10.73 | 19.03 | 34.21 | 344.77 | 347.31 |
| fiber | 245 | 29.21 | 46.03 | 75.31 | 833.90 | 840.05 |
| bubble_irregular | 169 | 20.61 | 58.11 | 114.81 | 1,052.70 | 1,060.46 |
| extraneous_polymer | 150 | 96.89 | 279.89 | 618.39 | 5,070.69 | 5,108.06 |
| hema_obstruction | 95 | 1,068.76 | 1,224.48 | 1,348.54 | 22,183.30 | 22,346.77 |
| bubble_on_edge | 90 | 8.98 | 13.97 | 19.69 | 253.07 | 254.93 |
| bubble_on_123 | 79 | 6.23 | 7.57 | 9.75 | 137.17 | 138.18 |
| hema_fragment | 8 | 444.42 | 617.77 | 681.84 | 11,191.85 | 11,274.32 |
| stretched_bubble | 7 | 59.29 | 101.62 | 368.07 | 1,840.97 | 1,854.53 |

The full p25 and p75 micron figures at both scales, per defect, folder group and
line, are in `run/eda_full_20261015/size_by_stratum.json`.

## Box size per folder group

| Folder group | n | diag px p25 | p50 | p75 | um p50 at 18.1165 | um p50 at 18.25 |
|---|---|---|---|---|---|---|
| Updated | 13,019 | 8.13 | 10.26 | 16.29 | 185.90 | 187.27 |
| Library | 1,163 | 8.79 | 12.20 | 23.77 | 221.11 | 222.74 |

## Box size per production line

| Line | n | diag px p25 | p50 | p75 | um p50 at 18.1165 | um p50 at 18.25 |
|---|---|---|---|---|---|---|
| L24 | 7,611 | 8.05 | 10.12 | 15.48 | 183.31 | 184.66 |
| L25 | 569 | 9.67 | 14.76 | 37.09 | 267.39 | 269.36 |
| L26 | 3,677 | 8.29 | 10.51 | 17.53 | 190.40 | 191.80 |
| L27 | 2,139 | 8.28 | 10.47 | 17.19 | 189.61 | 191.01 |
| L31 | 186 | 7.57 | 15.16 | 41.85 | 274.62 | 276.65 |

The line and folder-group p50 values sit between 10 and 15 px, except the thin
strata (L25 569 boxes, L31 186 boxes) which are pulled up by a small tail. These
are box-size differences between the defect mixes in each stratum, not a scale
difference: ticket 013a showed the pixel scale itself does not vary by line or
group beyond noise.

## Share of boxes outside the cavity

Distance is from the box CENTRE to the MEASURED cavity centre, compared with the
MEASURED cavity radius for that picture. All 14,182 boxes have a measured cavity
(no box picture fell in the `low_bright` class), so nothing is excluded here.

Overall: 4,074 of 14,182 boxes (28.73 percent) have their centre outside the
cavity, and 3 boxes (0.02 percent) sit beyond 1.5 times the cavity radius.

| Canonical defect | n | outside cavity | share outside | beyond 1.5x | share beyond 1.5x |
|---|---|---|---|---|---|
| bubble | 10,869 | 3,078 | 28.32 % | 2 | 0.02 % |
| bubble_cluster | 1,182 | 426 | 36.04 % | 0 | 0.00 % |
| wet_package | 662 | 217 | 32.78 % | 1 | 0.15 % |
| foreign_matter | 626 | 154 | 24.60 % | 0 | 0.00 % |
| fiber | 245 | 56 | 22.86 % | 0 | 0.00 % |
| bubble_irregular | 169 | 76 | 44.97 % | 0 | 0.00 % |
| extraneous_polymer | 150 | 30 | 20.00 % | 0 | 0.00 % |
| hema_obstruction | 95 | 4 | 4.21 % | 0 | 0.00 % |
| bubble_on_edge | 90 | 23 | 25.56 % | 0 | 0.00 % |
| bubble_on_123 | 79 | 5 | 6.33 % | 0 | 0.00 % |
| hema_fragment | 8 | 1 | 12.50 % | 0 | 0.00 % |
| stretched_bubble | 7 | 4 | 57.14 % | 0 | 0.00 % |

The share outside the cavity is in line with the 2026-10-13 batch result, where
9,042 of 12,793 boxes (29.3 percent) fell outside and 3 sat beyond 1.5 times.

## Caveat: P3_HE boxes are region annotations, not defect spots

HEMA Obstruction and HEMA Fragment share the P3_HE code, and their boxes are
region annotations rather than defect spots. Their median diagonal is far larger
than the lens diameter, so they must not be read as detector targets.

The published lens rim diameter is 783.8 px (ticket 013a, and the 2026-10-13
run).

| Defect (code P3_HE) | n | diag px p25 | p50 | p75 | p50 / lens diameter |
|---|---|---|---|---|---|
| hema_obstruction | 95 | 1,068.76 | 1,224.48 | 1,348.54 | 1.56 |
| hema_fragment | 8 | 444.42 | 617.77 | 681.84 | 0.79 |
| Combined | 103 | | 1,208.29 | | 1.54 |

The combined median of 1,208.29 px is 1.54 times the 783.8 px lens diameter:
the typical P3_HE box spans more than the whole lens. HEMA Obstruction drives
this (median 1,224.48 px, 22,183 um at 18.1165). HEMA Fragment is a small,
mixed set of 8 boxes whose median (617.77 px) is below the lens diameter but
whose p75 (681.84 px) still approaches it. Carried into this report from ticket
012: these boxes describe regions, and no detector-target reading should use
them.

## Files

| Artifact | What it is |
|---|---|
| `vm/ops/measure_cavity_library.py` | the read-only cavity measuring script, piped over ssh |
| `run/eda_full_20261015/cavity_raw.tsv` | raw per-picture VM output, 10,614 rows |
| `run/eda_full_20261015/cavity_geometry_library.json` | per picture: cavity centre, radius, flag |
| `run/eda_full_20261015/box_sizes.csv` | one row per box, 14,182 rows |
| `run/eda_full_20261015/size_by_stratum.json` | defect x folder group x line distributions |
| `experiments/eda_full/box_geometry.py` | the aggregation builder |
| `experiments/eda_full/verify_box_geometry.py` | the verifier |

Nothing was written to the shared VM. The measuring script and the raw output
are read-only against the picture files. `run/eda_full_20261015/_cavity_input_paths.txt`
is the intermediate census path list.

## How to run

```bash
./.venv/Scripts/python.exe experiments/eda_full/box_geometry.py
./.venv/Scripts/python.exe experiments/eda_full/verify_box_geometry.py
```

The cavity measurement is a one-time VM read. Its raw output
(`cavity_raw.tsv`) is the builder's input; re-measure by re-piping
`vm/ops/measure_cavity_library.py` over ssh with the picture list on stdin.

## Verification

Checked, with the numbers:

1. Every box in `resolved_labels.csv` appears exactly once in `box_sizes.csv`.
   The multisets match on (md5, canonical id, source file, rounded diagonal):
   14,182 rows, 0 mismatched. Tags excluded: 5,832, stated everywhere.
2. Axis-aligned share reported as a number: 660 of 14,182, 4.65 percent. The
   flag recomputes from the rotation attribute with 0 disagreeing rows.
3. The cavity measurement states 10,614 pictures, 10,470 measured and 144 in one
   named class, `low_bright`. No silent drop: 10,470 + 144 = 10,614.
4. The P3_HE region-annotation caveat is in this report with its numbers
   (combined median 1,208.29 px, 1.54 times the lens diameter).
5. Distributions are p25/p50/p75 throughout, never a bare mean.
6. A rebuild is byte-identical. `box_sizes.csv` md5
   `1a973be6d5dafdcbda4c65b2a373e823`, `size_by_stratum.json` md5
   `747b3dadc0615c7a25bcee72be6ee52b`, `cavity_geometry_library.json` md5
   `540a1b9b410ed2bf6989563ad9cd5754`, each on two consecutive runs.
7. The verifier re-derives the headline medians from `box_sizes.csv` by a second
   route (`statistics.median` and `statistics.quantiles` inclusive, not the
   builder's interpolating percentile) for per-defect, per-group, per-line and
   per-triple strata, and re-derives the cavity containment shares at 0
   mismatches. It also re-reads 12 pictures from the shared VM with an
   independently written cavity routine, 12 checks, 0 disagreements. Total: 31
   checks, 0 failures.
