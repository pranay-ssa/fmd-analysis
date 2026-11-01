---
title: Scale provenance sweep
date: 2026-10-15
type: reference
status: active
where: docs/reference/scale_provenance_20261015.md
---

# Scale provenance sweep

Phase 0 of the scale plan. Read-only sweep of the shared VM to establish
where four numbers in circulation came from. Nothing was measured, no scale was
computed, no image was touched. Every command was a read.

Primary area: `/data/FMD_Data_26082026/`. Secondary area: `/home/amd100-user/`.
This is the same tree the current record calls "the earlier micron-per-pixel
experiment".

## The four numbers, each with its outcome

### 1. 14,200 microns, the nominal lens diameter

Outcome: (a) FOUND.

The number is the hardcoded constant that every scale figure divides into.

- `/data/FMD_Data_26082026/measure_scale.py`, line 9:

      NOMINAL_LENS_DIAMETER_UM = 14_200.0

  This routine is the shipped source of the published scale. It carries no
  comment on where the value came from.

- `/data/FMD_Data_26082026/eda_size_um.py`, lines 22 to 24:

      UM_PER_PX = 18.25          # estimated from contact-lens edge diameter, +/- ~6%
      LENS_DIAM_PX = 778.0       # measured (two methods: 774 / 786)
      NOMINAL_LENS_DIAM_UM = 14200.0

- `/data/FMD_Data_26082026/eda_methodology.html`, section 21.3, line 393:

      NOMINAL_LENS_DIAMETER_UM = 14 200      (soft daily contact lens; spec range 14.0–14.3 mm)

So the prior EDA does state a rationale for 14,200: it is presented as the
nominal diameter of a "soft daily contact lens" whose "spec range" is
14.0 to 14.3 mm. That rationale is an assumption about the product. It is not
a measurement and it cites no manufacturer document. No source document on the
VM backs it. See number 4 for the spec range itself.

### 2. 18.1165 microns per pixel, our published scale

Outcome: (a) FOUND.

- `/data/FMD_Data_26082026/scale_estimate.json`, lines 4 to 13 and 2:

      "lens_diam_px_trimmed_mean": 783.8,
      "lens_diam_px_median": 786.0,
      ...
      "um_per_px": 18.1165,

- `/data/FMD_Data_26082026/measure_scale.py`, line 63, the division:

      um_per_px = NOMINAL_LENS_DIAMETER_UM / lens_px

  With `lens_px` the 15 percent trimmed mean of the accepted lens diameters,
  this is 14,200 / 783.8 = 18.1165.

- `/data/FMD_Data_26082026/eda_methodology.html`, section 21.2, line 382,
  records detector B (the same dark-ring dip, shipped in `measure_scale.py`) as
  "783.8 px (sigma 42, IQR 764–804)".

This matches our current record exactly. `measure_scale.py` samples 200 random
frames matching `*Pass1*` from
`fmd_temp_images/20260826_T24_Production_Sample/sample folder`, a separate
production-sample drop, not the annotated batch and not the library folders.

### 3. 18.25 microns per pixel

Outcome: (a) FOUND, with an arithmetic origin.

- `/data/FMD_Data_26082026/eda_size_um.py`, lines 22 to 24 (quoted above):
  `UM_PER_PX = 18.25`, `LENS_DIAM_PX = 778.0`, `NOMINAL_LENS_DIAM_UM = 14200.0`.
  Line 23 also carries the teammate's note in the file itself:
  `# measured (two methods: 774 / 786)`.

- `/data/FMD_Data_26082026/eda_size_um.json`, lines 2 to 7:

      "um_per_px": 18.25,
      "mm_per_px": 0.01825,
      "px_per_mm": 54.79,
      "lens_diam_px_measured": 778.0,
      "nominal_lens_diameter_um": 14200.0,

- `/data/FMD_Data_26082026/eda_methodology.html`, section 21.3, line 394:

      UM_PER_PX  =  14 200 / 778   ≈  18.25 µm / px

So 18.25 is not a document figure and not a fresh measurement. It is
14,200 divided by a 778 px lens edge. 14,200 / 778 = 18.2519. The teammate's
778 px note is correct and its source is `eda_size_um.py` line 23, which itself
records it as the pick between two detector readings, 774 and 786 px (the file
does not show where 774 and 786 came from; it does not ship that sample).

- `/data/FMD_Data_26082026/eda_defect_size_um.html`, lines 66 and 79, is the
  rendered report built from `eda_size_um.json` and repeats the same figure:
  "an in-image estimate of 18.25 µm/px (+-6%)".

### 4. The lens diameter spec of 14.0 to 14.3 mm

Outcome: (c) FOUND BUT INCONSISTENT.

The range is written, but only in our own generated artifacts, and it is in
none of the three documents the client gave us and in no received document.

- `/data/FMD_Data_26082026/eda_methodology.html`, section 21.3, line 393:

      NOMINAL_LENS_DIAMETER_UM = 14 200      (soft daily contact lens; spec range 14.0–14.3 mm)

- `/data/FMD_Data_26082026/eda_methodology.html`, section 21.3, line 397 to 398,
  the uncertainty is built on the same range:

      Uncertainty ≈ ±6%: measurement spread on the lens rim (±4–5%) plus the 14.0–14.3 mm spec
      range (±1.5%) plus a possible small outward bias in the auto-detected rim.

- `/data/FMD_Data_26082026/build_size_dashboard.py`, lines 120 to 121, the
  generator of the size dashboard, holds it as literal prose:

      Divide the nominal soft-lens diameter (14.2 mm, spec range
      14.0–14.3) by that.

- `/data/FMD_Data_26082026/eda_defect_size_um.html`, lines 86 to 87, the
  rendered copy of that prose:

      (two independent detectors: 774 and 786 px, IQR 764–804). Divide the nominal soft-lens diameter (14.2 mm, spec range
      14.0–14.3) by that.

Why this is (c): the number exists, so it is not "not found". But it is
presented as a product spec with no citation in any artifact, and it is not
reflected in our current record. `docs/reference/received_docs_nominals.md`
states that a lens diameter "is written in no received document present here"
and that the 14,200 we use "is our own figure". The prior EDA, by contrast,
writes the 14.0 to 14.3 mm range as if it were a known product spec and folds it
into the stated uncertainty. The contradiction is between the prior EDA's
framing (a spec range) and the current record and the received set (no such
document). The user's guess that this came from an earlier experiment is
correct: its only home is this earlier EDA, `eda_methodology.html` and its two
generated children.

## Every physical dimension with a unit in this prior EDA

| Dimension | Value | Unit | File and where |
|---|---|---|---|
| Nominal lens diameter | 14,200 (14.2) | microns (mm) | `measure_scale.py` line 9; `eda_size_um.py` line 24; `eda_methodology.html` section 21.3 |
| Lens spec range | 14.0 to 14.3 | mm | `eda_methodology.html` section 21.3 line 393; `build_size_dashboard.py` lines 120 to 121; `eda_defect_size_um.html` lines 86 to 87 |
| Lens edge measured, trimmed mean | 783.8 | pixels | `scale_estimate.json` line 4; `eda_methodology.html` section 21.2 line 382 |
| Lens edge, median | 786.0 | pixels | `scale_estimate.json` line 5 |
| Lens edge, standard deviation | 41.6 | pixels | `scale_estimate.json` line 6 |
| Lens edge, interquartile range | 764 to 804 | pixels | `scale_estimate.json` line 7 |
| Lens edge adopted for the um EDA | 778.0 | pixels | `eda_size_um.py` line 23; `eda_size_um.json` line 6 |
| Two detector readings | 774 and 786 | pixels | `eda_size_um.py` line 23; `eda_defect_size_um.html` line 86 |
| Gradient cross-check | 772.5 (sigma 30, p10 to p90 730 to 810) | pixels | `eda_methodology.html` section 21.2 line 382 |
| Cavity disc diameter | about 896 (sigma about 13) | pixels | `eda_methodology.html` section 21.2 line 375 |
| Field of view | 44.7 x 37.4 | mm | `eda_size_um.json` `calibration.fov_mm`; `eda_methodology.html` section 21.3 line 396 |
| Image frame | 2448 x 2048 | pixels | `eda_report.md` line 25; `eda_methodology.html` section 21.3 |
| Scale | 18.25 | microns per pixel | `eda_size_um.py` line 22; `eda_size_um.json` line 3 |
| Scale | 0.01825 | mm per pixel | `eda_size_um.json` line 4 |
| Scale | 54.79 | pixels per mm | `eda_size_um.json` line 5 |
| Scale | 18.1165 | microns per pixel | `scale_estimate.json` line 13 |
| Defect size bands | under 300; 300 to 500; 500 to 647; 647 and up | microns | `eda_size_um.py` lines 25 to 27 |
| Band edges in pixels on the major axis | 16.4 / 27.4 / 35.5 | pixels | `eda_size_um.json` `calibration.band_edges_px_major`; `eda_defect_size_um.html` line 82 |

Not present anywhere in this prior EDA: a package size, a cavity size in
microns, a pixel pitch, a working distance, or a magnification. The methodology
states these are absent by design, section 21.1: "nor `annotations.xml` nor
`Box Stats.csv` has a mm/µm field, a magnification, a working distance, or a
fiducial." The only cavity figure is the about 896 px disc, in pixels only.

## Whether any prior artifact states HOW 14,200 was arrived at

Yes, one does. `eda_methodology.html` section 21.3 line 393 states the
rationale: 14,200 microns is the "soft daily contact lens" nominal, with a
stated "spec range 14.0–14.3 mm". By category that is an assumption about the
product, not a manufacturer spec we hold and not a measurement. `measure_scale.py`
hardcodes the same value with no comment at all. So the recorded chain is:
an assumed product diameter (14.2 mm, midpoint of a claimed 14.0 to 14.3 mm
range) divided by a measured 778 or 783.8 px lens rim.

## Earlier sampling of images for scale work

- `measure_scale.py`: 200 random frames matching `*Pass1*`, drawn by
  `random.seed(7)` from
  `fmd_temp_images/20260826_T24_Production_Sample/sample folder`. That folder
  holds 10,000 images, of which 7,164 are `_Pass1`. This is the 200-frame sample
  behind 18.1165.
- `eda_methodology.html` section 21.2 line 374 describes the same population:
  "a sample of ~200 production \"Pass1\" images (centred, unobstructed, single
  lens)". Its detector B is 783.8 px and its gradient cross-check is 772.5 px
  over the same sample.
- `eda_size_um.py` does not ship its own lens sample; it adopts 778 px and runs
  the um size EDA over the CVAT annotations in
  `fmd_temp_images/ICube Defects Library/annotations.xml`. Per
  `eda_size_um.json`, that EDA covers 434 annotated images and 2,020 boxes.

## Artifacts that conflict with our current record

1. `eda_methodology.html` section 21.3, `build_size_dashboard.py` lines 120 to
   121, and `eda_defect_size_um.html` lines 86 to 87 assert a lens "spec range
   14.0–14.3 mm". Our current record,
   `docs/reference/received_docs_nominals.md`, says the lens diameter is written
   in no received document and that 14,200 is our own figure. The prior EDA
   presents the range as a known product spec and never cites a source.
2. `eda_size_um.json` publishes 18.25 microns per pixel with a stated
   uncertainty of 6 percent, while `scale_estimate.json` publishes 18.1165. The
   prior EDA consciously adopted a 778 px lens edge (the midpoint of two
   detector readings, 774 and 786) instead of the 783.8 px trimmed mean that the
   later published scale uses. The two scales and their two different lens
   samples sit side by side on the VM with no reconciliation. This is the
   arithmetic root of the 18.1165 against 18.25 gap.

## What was NOT examined (stated boundary)

- No image file was opened or read. No `.bmp` was touched. No measurement was
  re-run and no scale was computed.
- Inside `fmd_temp_images/`, only directory names were used. `sample
  metadata.csv`, `annotations.xml` and `Box Stats.csv` were not opened.
- `/data/FMD_Data_26082026/.venv` was not opened.
- The tarballs in the home (`merge_push.tgz`, `merge_ref.tgz`,
  `runs_artifacts.tgz`, `ooi_samples.tar`) were not opened. The one binary that
  is not a tarball, `ooi_samples.tar`, and the `push20261007/` CSVs were grepped
  for the four numbers and returned no scale hits.
- `/data/resnet18_fmd` was not swept. It is a model-training tree, not part of
  the micron-per-pixel experiment.
- Other people's homes were listed but not opened, per the privacy rule:
  `ksurampudi`, `pranayp`, `srikantht`, `swetap` are world-readable (`drwxr-xr-x`)
  but their files were not read. `linuxadmin` is not readable by us at all
  (`drwxr-x---`, mode 750, owned by `linuxadmin`).
- In `/home/amd100-user/`, `.cache`, `.local`, `.config`, `.claude`,
  `.vscode-server`, `.keras`, `.copilot`, `.nv` and `.ipynb` were not searched.
  `.bash_history` was read: it records `download_fmd.py`, `migrate_fmd_to_shield.py`,
  `blob_migrate_two.py` and the venv setup, and nothing scale related.

## Provenance verdict in one line

14,200 microns has a stated origin in one prior artifact
(`eda_methodology.html` section 21.3) as an assumed product-spec diameter, so
it is documented as an assumption rather than as a sourced manufacturer figure,
and that origin is itself the uncited 14.0 to 14.3 mm range.
