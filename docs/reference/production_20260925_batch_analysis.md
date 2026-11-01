---
title: PRODUCTION_20260925 batch analysis
date: 2026-10-13
type: result
status: superseded
where: docs/reference/production_20260925_batch_analysis.md
---

> **Also superseded by the 2026-10-26 re-export.** The client re-exported these seven jobs
> with seventeen more under `PRODUCTION_20260925_300/` (24 files, 3,597 pictures). The
> revised seven keep the same 1,047 pictures and change 133 labels. Current counts live in
> `docs/reference/draft2_eda_ooi_20261023.md` and `run/eda_full_20261028/`.
>
> **Superseded 2026-10-15 by the full-coverage EDA.** This record covers only the
> 1,047 image production batch under the older annotation set. It is kept for
> history. Four of its conclusions do not survive: the size gate is a clean cut on
> the longer side of the box, not on the diagonal, so the finding that it "is not a
> 300 um cut" was an artefact of the diagonal; the scale figure below came from a
> different image sample than this paragraph implies; the batch is 1,046 distinct
> contents, not 1,047, because two of its files are byte-identical; and the
> micron-threshold tags have since been replaced by the client. See
> `docs/wayfinder/eda_full_coverage_map.md` for the current record.

Repo mirror of the README that sits beside the data on the shared VM at
`/home/amd100-user/FMD_Data_26082026/fmd_temp_images/PRODUCTION_20260925/README.md`.

The VM box and that data folder are shared across accounts, so they hold no
scripts. The data folder contains exactly four things: `README.md`,
`manifest.csv`, `annotations/` and `images/`. Everything that generates the
README lives here in the repo instead:

| Artifact | Where |
|---|---|
| README generator | `vm/ops/analyze_20260925.py` (`--data-dir`, `--cavity-json`, `--out`) |
| Cavity measurement | `vm/ops/measure_cavity_all.py` (`--data-dir`, `--out`, `--jobs`) |
| Cavity geometry, 1,016 images | `vm/ops/cavity_geometry_all.json` |
| Transfer script | `vm/ops/pull_20260925_batch.py` (`--dest`, `--dry-run`) |
| Transfer provenance | `docs/cvat_production_20260925_pull.md` |

All three scripts take their paths as arguments and are piped over ssh at run
time (`ssh amd-a100-vm 'python3 - --data-dir <path>' < vm/ops/<script>.py`), so
a run leaves nothing behind on the VM but the artifact it writes. The generator
is deterministic: it sorts with an explicit name tiebreaker, so it reproduces
the same bytes under any `PYTHONHASHSEED`. Verified by three runs at different
seeds, all byte-identical to each other and to the live README.

README md5 when this mirror was taken: `45f35bb0059cf799f6988c8ba3b4a5bc`.

---

# PRODUCTION_20260925 batch

Analysis of the 2026-09-25 CVAT annotation batch and the images it labels.
Every number below is computed from the files in this folder, not typed in
by hand. The generating scripts are kept in our repo rather than beside the
data, because this folder is shared: `vm/ops/analyze_20260925.py` reads
`annotations/` and `images/` here and writes this file, and
`vm/ops/measure_cavity_all.py` produced the cavity geometry it depends on.
To regenerate, run `analyze_20260925.py` with `--data-dir` pointing at this
folder and `--cavity-json` pointing at the repo's `cavity_geometry_all.json`.

Written 2026-10-13.

## What is here

| Item | Value |
|---|---|
| Annotation files | 7 CVAT 1.1 XML in `annotations/` |
| Images | 1047 BMP in `images/` |
| Total bytes | 5,250,267,354 |
| Image geometry | 2448x2048 |
| File size | 5,014,582 bytes each |
| Labelled shapes | 14,111 total, 12,793 `<box>` + 1,318 `<tag>` |
| Distinct label codes | 24 |
| Source | account `stjnjmakearmor`, containers `fmd-cvat-annotations` and `fmd-cvat-images` |

Every image is 2448x2048, 8 bpp, 5,014,582 bytes. The batch is uniform in
geometry and in file size, so nothing here is a resized or re-encoded copy.

## Provenance

| Job | Images in file |
|---|---|
| `annotations_4521940.xml` | 150 |
| `annotations_4521941.xml` | 150 |
| `annotations_4521942.xml` | 147 |
| `annotations_4521943.xml` | 150 |
| `annotations_4521944.xml` | 150 |
| `annotations_4521945.xml` | 150 |
| `annotations_4521946.xml` | 150 |
| **Total** | **1047** |

The 7 jobs are disjoint: no image name appears in two files, and no name is
repeated inside one file. 1047 distinct images for 1047 image tags, so the set is
clean to split without de-duplication.

## Labels

Labels are `label="CODE"` attributes on each shape, which is the CVAT 1.1
detection export form. A `<box>` is a localised defect, a `<tag>` is a
whole-image flag.

| Code | Meaning | Shapes | Images |
|---|---|---|---|
| `P2_BB` | Bubble | 10,075 | 747 |
| `P2_BC` | Bubble Cluster | 1,071 | 407 |
| `P3_FM` | Foreign Matter | 571 | 282 |
| `P1_MPP` | Missing Primary Package | 226 | 226 |
| `P2_DC` | Dirty Camera | 204 | 204 |
| `P2_LOC` | Lens Off Center | 187 | 187 |
| `P1_ML` | Multiple Lenses | 169 | 169 |
| `P3_FIB` | Fiber | 219 | 154 |
| `P2_WP` | Wet Package | 591 | 121 |
| `P2_LD` | Low Dose | 118 | 118 |
| `P2_BI` | Bubble Irregular | 128 | 108 |
| `P3_HE` | HEMA Obstruction | 96 | 95 |
| `P3_HE_MICRON_THRESHOLD` | HEMA Obstruction, micron gate | 95 | 95 |
| `P3_FIB_MICRON_THRESHOLD` | Fiber, micron gate | 85 | 85 |
| `P1_FL` | Folded Lens | 59 | 59 |
| `P3_FM_MICRON_THRESHOLD` | Foreign Matter, micron gate | 53 | 53 |
| `P1_COC` | Cavity Off Center | 35 | 35 |
| `P3_EP` | Extraneous Polymer | 39 | 35 |
| `P3_EP_MICRON_THRESHOLD` | Extraneous Polymer, micron gate | 32 | 32 |
| `F2_FOV` | View Obstructed | 24 | 24 |
| `P2_DS` | Dirty Strobe | 22 | 22 |
| `P1_NL` | Missing Lens | 6 | 6 |
| `P1_PPM` | Package Misalignment | 2 | 2 |
| `P2_BST` | Stretched Bubble | 3 | 2 |

`P2_DC`, `P2_BI`, `P1_FL` and `P2_BST` were named on 2026-10-13 as Dirty Camera,
Bubble Irregular, Folded Lens and Stretched Bubble. The first three match the
September code legend directly; `P2_BST` rests on elimination plus that reading,
and it carries only 3 shapes over 2 images, so any number for it is indicative.

## This is a multi-label set, not one class per image

| Codes on one image | Images |
|---|---|
| 0 | 1 |
| 1 | 303 |
| 2 | 113 |
| 3 | 195 |
| 4 | 191 |
| 5 | 143 |
| 6 | 58 |
| 7 | 30 |
| 8 | 6 |
| 9 | 2 |
| 10 | 4 |
| 11 | 1 |

Only 303 of 1047 images carry a single code. The median image carries 3 codes,
and the worst carries 11. Any pipeline that reads one class per image throws
away most of what the annotator wrote.

Shape type split:

| Composition | Images |
|---|---|
| `<box>` only (localised defects) | 161 |
| `<tag>` only (whole-image flags) | 288 |
| both | 597 |
| neither, listed but unlabelled | 1 |

The unlabelled image is `20241105_204620_L24_C14_9270.bmp`, listed in the XML with zero shapes. It is
kept in `images/` because it is part of the batch, but it carries no target.

Most common code pairs appearing on the same image:

| Pair | Images |
|---|---|
| `P2_BB` + `P2_BC` | 406 |
| `P2_BB` + `P3_FM` | 276 |
| `P2_BB` + `P2_DC` | 200 |
| `P2_BB` + `P2_LOC` | 185 |
| `P1_ML` + `P2_BB` | 168 |
| `P2_BC` + `P3_FM` | 165 |
| `P2_BB` + `P3_FIB` | 147 |
| `P1_ML` + `P2_LOC` | 126 |
| `P2_BC` + `P2_DC` | 118 |
| `P2_BB` + `P2_LD` | 117 |
| `P2_BB` + `P2_WP` | 117 |
| `P2_BB` + `P2_BI` | 108 |

## Box sizes, in pixels and microns

Scale is 18.1165 um per pixel, from `scale_estimate.json`: the lens rim measured
at a 783.8 px trimmed mean against a 14,200 um nominal lens diameter, with a 5.3
percent relative spread, so micron figures below are indicative, not metrology.

**The sample that produced that scale is not this batch.** The routine that
produced it reads 200 random machine-PASS frames from the separate T24 Production
Sample drop of 2026-08-26, not the 1,047 images analysed here and not the library.
The 14,200 um nominal lens diameter is hardcoded in that routine and is cited to no
received document. Both facts are corrected here on 2026-10-15; the earlier wording
of this paragraph said "200 production images", which read as though it came from
this batch. It did not.

Boxes carry a rotation attribute. `diag` is the rectangle diagonal,
sqrt(w^2 + h^2), which is invariant to that rotation, so it is the size
measure used here.

| Code | Boxes | diag px p50 | diag px p25 to p75 | diag um p50 |
|---|---|---|---|---|
| `P2_BB` | 10075 | 9.2 | 7.8 to 12.4 | 167 |
| `P2_BC` | 1071 | 16.1 | 12.1 to 24.1 | 291 |
| `P2_WP` | 591 | 45.7 | 22.3 to 101.7 | 829 |
| `P3_FM` | 571 | 17.0 | 10.4 to 32.0 | 309 |
| `P3_FIB` | 219 | 43.2 | 28.0 to 67.9 | 783 |
| `P2_BI` | 128 | 37.2 | 17.7 to 84.2 | 673 |
| `P3_HE` | 96 | 1222.6 | 1066.5 to 1344.0 | 22149 |
| `P3_EP` | 39 | 101.3 | 67.2 to 222.6 | 1835 |
| `P2_BST` | 3 | 37.3 | 26.4 to 69.5 | 676 |

12,135 of 12,793 boxes (95 percent) carry a non-zero rotation, so any training
conversion that assumes axis-aligned rectangles will mis-draw most of them.

`P3_HE` is the outlier in that table: its boxes have a median diagonal of
1223 px, which is 22149 um and larger than the 784 px lens diameter. A box
that size is a region annotation, not a defect spot, so it should not be
trained as a detector target alongside the 9 to 100 px boxes of every
other code. Worth confirming with the annotator what `P3_HE` is meant to
cover before it goes into a detection model.

## What the micron threshold labels gate on

Four codes end in `_MICRON_THRESHOLD`. All four are `<tag>` shapes, all four
are strict subsets of their base code, so they read as a size gate on the
base defect rather than as separate classes. The gate can be read off the
data: compare the largest base-code box on images that carry the gate flag
against images that do not.

| Base code | Gate flag | flagged images | unflagged | flagged max diag p50 (px) | unflagged p50 (px) | gap (px) | gap (um) |
|---|---|---|---|---|---|---|---|
| `P3_EP` | `P3_EP_MICRON_THRESHOLD` | 32 | 3 | 143.2 | 19.2 | 124.0 | 2247 |
| `P3_FIB` | `P3_FIB_MICRON_THRESHOLD` | 85 | 69 | 75.3 | 31.0 | 44.3 | 803 |
| `P3_FM` | `P3_FM_MICRON_THRESHOLD` | 53 | 229 | 58.1 | 23.4 | 34.8 | 630 |
| `P3_HE` | `P3_HE_MICRON_THRESHOLD` | 95 | 0 | n/a | n/a | n/a | n/a |

A positive gap on every comparable row means the gate flag tracks box size,
which is what a micron threshold should do. The recorded thresholds for this
product are 300, 500 and 647 um, which are 16.6, 27.6 and 35.7 px at this
scale. The inferred gaps sit well above all three, so the gate is not a
300 um cut on any of these classes.

- `P3_EP`: flagged images hold a median largest box of 143.2 px (2595 um),
  unflagged 19.2 px (348 um), so flagged boxes are 7.5x larger. 32 of 35
  images with this defect cross the gate.
- `P3_FIB`: flagged images hold a median largest box of 75.3 px (1364 um),
  unflagged 31.0 px (561 um), so flagged boxes are 2.4x larger. 85 of 154
  images with this defect cross the gate.
- `P3_FM`: flagged images hold a median largest box of 58.1 px (1053 um),
  unflagged 23.4 px (423 um), so flagged boxes are 2.5x larger. 53 of 282
  images with this defect cross the gate.

`P3_HE` cannot be tested this way: all 95 images carrying it also carry
`P3_HE_MICRON_THRESHOLD`, so there is no unflagged comparison group. That
reads as HEMA obstruction being flagged unconditionally rather than by size.

## Where the boxes sit

The cavity was measured on each image rather than assumed, because it is
not centred in the frame: the median cavity centre sits 96 px from the
image centre, the p95 is 147 px and the maximum is 532 px. Measuring it
on 1016 of 1047 images (the rest were too dark or too small for the threshold
to find a part, and their boxes are excluded below).

| Measure | Value |
|---|---|
| Cavity radius | 434 px median, p25 to p75 412 to 442, sd 41 |
| Boxes measured against their own image cavity | 12,793 |
| Box centre inside the cavity | 9,042 (70.7 percent) |
| Box centre outside the cavity | 3,751 (29.3 percent) |
| Box centre beyond 1.5x the cavity radius | 3 |
| Distance from cavity centre, as a multiple of cavity radius | p50 0.90, p75 1.02, p95 1.18, max 1.54 |

Per code, share of boxes whose centre falls outside the cavity:

| Code | Boxes | Outside cavity | Share |
|---|---|---|---|
| `P2_BB` | 10075 | 2890 | 28.7 percent |
| `P2_BC` | 1071 | 394 | 36.8 percent |
| `P2_WP` | 591 | 213 | 36.0 percent |
| `P3_FM` | 571 | 135 | 23.6 percent |
| `P3_FIB` | 219 | 49 | 22.4 percent |
| `P2_BI` | 128 | 57 | 44.5 percent |
| `P3_HE` | 96 | 4 | 4.2 percent |
| `P3_EP` | 39 | 6 | 15.4 percent |
| `P2_BST` | 3 | 3 | 100.0 percent |

Boxes sitting on the annulus between the lens rim and the cavity wall are
expected, since that is package surface. The tail past 1.5x the cavity is
the part worth a look, because a box there is on the tray or the
background rather than on the part. Only 3 boxes fall that far out, so
the annotation is spatially sane.

## What the filenames carry

| Fact | Value |
|---|---|
| Images with a production line tag | 1047 of 1047 |
| Lines present | L24 (660), L26 (237), L27 (135), L25 (15) |
| Capture date range | 20241101 to 20241109 |
| Images whose name embeds a model `Score(...)` | 169 |

The line tag and the capture date are free covariates for a split, so a
per-line or per-date holdout costs nothing to build from the manifest.
The embedded `Score(...)` values come from the upstream model that proposed
these images for review. They are selection scores, not ground truth, and
they should not be used as labels.

## Coverage

| Item | Value |
|---|---|
| Images in the blob folder `FMD_PROD/PRODUCTION-20260925/` | 10,438 |
| Annotated in this batch | 1047 |
| Coverage | 10.0 percent |
| Unannotated images still in blob | 9,391, 43.9 GB |

This batch is the finished subset of the production folder, not the whole
folder. The unannotated remainder is available as negatives if a run needs
them, at 43.9 GB.

## How to use this folder

- The class information lives in the XMLs, not in folder names. Build any
  split from the manifest and the XMLs, not from a directory walk.
- Image basenames are unchanged from the blob. The XMLs store paths as
  `FMD_PROD/PRODUCTION-20260925/<name>.bmp`, so point a loader at `images/`
  with that prefix stripped.
- Read labels as multi-label. A single image can legitimately carry up to
  11 codes.
- Treat the XMLs as the authority over the older library folders. Those
  folders disagree with each other on 113 of these images.
- `manifest.csv` records blob name, local path, bytes, etag, content_md5 and
  status for every file, so the transfer can be re-audited without
  re-listing the container.

## Open questions

1. Confirm `P2_DC`, `P2_BI`, `P1_FL` and `P2_BST` against the client taxonomy.
2. Confirm the intended micron gate per class. The data shows the gate
   tracking box size, but the numeric cut point in um needs the client's
   rule, not our inference.
3. Confirm whether `P1_ML` and `P1_FL` are two classes or one class drawn
   twice. Both majority-map to the Multiple Lenses folder, and 59 images
   carry `P1_FL`.
4. Decide whether the unannotated 9,391 images in the blob folder are wanted
   as explicit negatives.
