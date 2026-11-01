---
title: Ring identity, which ring in the image is the lens edge
date: 2026-10-15
type: result
status: active
where: reports/eda_full/ring_identity_20261015.md
---

# Ring identity, which ring in the image is the lens edge

Phase 1 of the scale plan. The question is pure pixels: a radial intensity
profile through the cavity carries more than one dark feature, and a method that
takes the single most prominent dip can lock onto the wrong one. Four earlier
detectors agreed near 772 to 786 px, a least-squares circle fit said 848 px. This
phase decides which ring is the lens, using two discriminators that need no
nominal, and reports the lens diameter in PIXELS with its spread.

**No micron figure appears anywhere in this report, in the new scripts or in the
new JSON.** Nothing here divides by the client nominal or by any other
micrometre constant. The micrometre side is Phase 2 and Phase 3 and is
deliberately out of scope.

## What was measured, and how

Everything reuses the shipped routines so the numbers stay comparable.

- Cavity centre and radius: `vm/ops/measure_cavity_library.py`, unchanged (bright
  blob at `0.45 * p99.5`, half-max column and row widths, divided by 4.0).
- The annular radial profile: `radial_profile` copied verbatim from
  `/data/FMD_Data_26082026/measure_scale.py`, mean intensity per integer radius.
- The dip-argmax method: copied verbatim from the same file, same band
  (0.50 to 0.92 of the cavity radius), same 7 px smoothing, same 25 px
  rolling-max baseline, same `dip_prominence > 1.0` gate.
- Candidate rings: every true local minimum of the smoothed profile, with the
  depth taken as the topographic prominence, that is the drop from the lower of
  the two enclosing local maxima. This replaced an earlier rolling-max baseline,
  which invents a ring wherever the profile simply falls (a monotone tail has no
  minimum, but a rolling-max baseline still reports one at the edge of the
  search band).
- Ring geometry: 360 rays from the cavity centre, bilinear sampled. For each
  ring the per-ray dip gives its own radius, the offset of its own centre from
  the cavity centre, and the fraction of rays on which it was found.
- The profile runs to 1.08 of the cavity radius rather than 1.05, because the
  cavity wall edge sits at about 1.04 and a 1.05 cut truncates it mid drop.

One image, one row per candidate ring and one row per method, 15 and 13 columns.
The scanner is read only and is piped over ssh base64 encoded; nothing was
written to the shared VM.

## The sample

| Population | Stated | Drawn | Where |
|---|---|---|---|
| A, library | 2,000, 400 per line | 2,000, 400 each on L24 L25 L26 L27 L31 | the three library folders of `picture_table.csv` |
| B, production drop | 500, 100 per line | 500, all of them L24 | `20260826_T24_Production_Sample/sample folder`, `*Pass1*` only |
| Repro | the prior 200 frames | 200, L24 | same drop, `random.seed(7)` and the same glob as `measure_scale.py` |

All joins are on content md5, never on a path.

Two facts about the data that had to be faced rather than smoothed over.

1. **The production drop is a single line.** All 7,164 `*Pass1*` frames in
   `sample folder` carry `_L24_`. The stated 100 per line collapses to 100, so
   population B was topped up to its stated 500 from the same pool. There is no
   second line in that drop to stratify on.
2. **The two discriminator labels only exist on library pictures.** The frozen
   resolution in `resolved_labels.csv` carries `P1_NL` on 325 pictures and
   `P2_LOC` on 957, and all of them sit in the Updated folders. In the drawn
   sample that is 53 missing-lens and 199 off-centre pictures. They are compared
   against the 2,407 sampled pictures that carry neither tag.

Achieved and measured:

- 2,700 sample rows, 2,682 distinct contents, 18 contents drawn twice (the repro
  set overlaps population B), 2,659 with a measured cavity, 23 refused as
  `low_bright` (dark frames). No picture was dropped silently.
- 3,483 detected rings, one row each in `ring_inventory.csv`.

## Candidate rings

Rings are pooled on radius divided by the cavity radius. That ratio is scale
free and assumes no ring identity. Candidate centres are the peaks of the 0.02
step, 3-bin smoothed detection-rate curve that clear three times the interior
floor (the floor over 0.35 to 0.75 is a detection rate of 0.019). Two candidates
clear it. A picture's deepest ring within plus or minus 0.06 of a centre is its
member ring. Rings outside both windows are reported separately, not discarded.

| Candidate | Radius / cavity | Median radius px | IQR px | Relative spread | Detection rate | Median depth | Median width px | Median sharpness |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.89 | 393.0 | 380.8 to 404.3 | 5.98 % | 0.459 | 3.03 | 9.0 | 0.337 |
| 1 | 1.01 | 445.0 | 428.0 to 459.0 | 6.97 % | 0.436 | 4.92 | 10.0 | 0.481 |
| unclustered | 0.35 to 1.06 | 330.5 | | | 0.408 | | | |

The 1,084 unclustered rings are a flat floor, not a ring: their radii spread
across the whole interior with no mode.

Median radius by population and line, so the reader can see whether the two
populations agree.

| Candidate | library | production sample | repro 200 | L24 | L25 | L26 | L27 | L31 |
|---|---|---|---|---|---|---|---|---|
| 0 | 388.0 | 396.0 | 399.0 | 397.0 | 391.5 | 395.0 | 378.0 | 385.0 |
| 1 | 438.0 | 458.0 | 452.0 | 455.0 | 447.0 | 436.0 | 445.0 | 420.0 |

Both candidates sit about 10 px further out in the production drop than in the
library, which is the same population offset the earlier work saw.

## Discriminator 1, the missing lens

The tag `P1_NL` marks pictures where the lens is absent. If a ring is the lens
edge it must be present in ordinary frames and gone, or fundamentally altered,
when the lens is missing.

| Candidate | detection rate, ordinary frames (n 2,407) | detection rate, missing lens (n 53) | median radius, missing lens |
|---|---|---|---|
| 0, at 0.89 R_cav | 0.4819 | 0.0000 | none measured |
| 1, at 1.01 R_cav | 0.4616 | 0.0000 | none measured |

Supporting numbers on the same two groups:

- Detected rings per picture: 1.351 in ordinary frames, 0.019 when the lens is
  missing. A missing-lens frame has essentially no dark ring anywhere between
  0.35 and 1.06 of the cavity radius; its profile falls monotonically from the
  centre to the wall edge.
- The shipped detector's own prominence, the statistic `measure_scale.py` gates
  on, has median 4.91 in ordinary frames and 2.17 in missing-lens frames. It
  still clears its 1.0 gate on 71.7 percent of missing-lens frames, which is
  exactly why that method misfires: it reports a plausible-looking rim diameter
  on frames that have no lens.

**Outcome of discriminator 1: decisive for the ring family, not for a single
ring.** Both candidates, and every other outer dark ring, exist only when a lens
is present. Nothing in this dataset produces a dark annular feature without a
lens. So the whole outer ring family is lens generated, and no member of it can
be the moulding or the well wall.

## Discriminator 2, the lens off centre

The tag `P2_LOC` marks 957 pictures where the lens sits off centre relative to
the cavity. In those frames the lens and the cavity should move independently, so
a lens ring should show a larger centre offset from the cavity centre than a
ring that belongs to the well.

| Candidate | centre offset, ordinary frames | centre offset, off centre frames | median radius, ordinary | median radius, off centre |
|---|---|---|---|---|
| 0, at 0.89 R_cav | 10.37 px (n 1,160) | 10.55 px (n 60) | 392.0 | 396.0 |
| 1, at 1.01 R_cav | 12.03 px (n 1,111) | 11.96 px (n 48) | 445.0 | 439.0 |

The offsets are the same in the two groups to within a pixel, and the radii move
in opposite directions for the two candidates. An independent 451 picture probe
that fitted the rim circle and the wall circle separately and compared their
centres found the same thing: the rim to wall centre distance is 14.4 px in
ordinary frames and 10.9 px in off centre frames, that is smaller, not larger.

**Outcome of discriminator 2: INCONCLUSIVE.** The off centre label does not move
either candidate's centre relative to the cavity centre in this instrument. No
ring can be assigned by motion. The reason is stated rather than worked around:
whatever the `P2_LOC` annotation marks, it is not a rigid displacement of the
lens within the cavity large enough to move the measured rim centre by more than
the 10 px measurement noise.

## Which ring is the lens edge, and the structural argument

Discriminator 1 eliminates every ring as "something that exists without a lens"
but does not separate the two candidates from each other. What separates them is
where the cavity wall already is, which the shipped mask measures directly and
which needs no nominal.

- The bright disc ends at a median 438.5 px radius, 877 px diameter. That is the
  cavity wall, by the definition of the mask the whole pipeline uses.
- Candidate 1 sits at 445.0 px radius, 1.01 of that. It is at the wall. A ring at
  the wall cannot be a lens rim sitting free in the cavity: a lens whose rim
  coincided with the well wall would fill the cavity exactly, which the existence
  of a Lens Off Center class, and of an ordinary centred population, both
  contradict. Candidate 1 is the wall shoulder, the saline meniscus where the
  fluid meets the moulded wall, with a median depth of 4.92 and a median
  sharpness of 0.481, the sharpest and deepest feature in the profile because it
  is a real fluid and moulding boundary.
- Candidate 0 sits at 393.0 px radius, 0.89 of the wall, clear of it.

**Verdict: the lens edge is candidate 0, the dark ring at 0.89 of the cavity
radius.** Its median radius is 393.0 px, its interquartile range 380.8 to 404.3
px, its relative spread 5.98 percent. It is present in 48.2 percent of ordinary
frames as a directly detected profile minimum and in 0.0 percent of missing-lens
frames. It is the only ring that is both lens dependent and clear of the wall.

## The lens diameter in pixels

The headline measurement is not the raw ring inventory but the least-squares
circle fit to the 360 radial edge points, restricted to the band that holds
candidate 0 (0.80 to 0.96 of the cavity radius) and outlier rejected. That is the
same family of measurement the 848 px figure came from, with the band chosen from
the independently found ring mode rather than by hand.

| Quantity | Value |
|---|---|
| Lens diameter, median | **789.0 px** |
| Interquartile range | 764.4 to 809.5 px |
| Relative spread, IQR over median | 5.71 % |
| p10 to p90 | 720.7 to 823.8 px |
| Standard deviation | 61.8 px |
| n | 2,659 images |
| Cross check, 2 x the ring inventory median radius | 786.0 px |

Error budget, all in pixels.

| Source | Size |
|---|---|
| Frame to frame spread of the rim fit, IQR | 45.1 px, 5.71 % |
| Frame to frame spread, p10 to p90 | 103.1 px, 13.1 % |
| Method disagreement on the same images | 760.0 to 789.0 px, 29 px, 3.7 % |
| Population, library against production drop | 777.3 against 809.5 px, 32.2 px, 4.0 % |
| Statistical, standard error of the median | 1.50 px |

A defensible single figure is **789 px with an uncertainty of about 3 percent
from method and population, rising to about 6 percent if the frame to frame
interquartile spread is included**. Nothing in this phase turns that into
microns.

## The three methods, on identical images

Every method ran on the same 2,659 pictures. This is what attributes the
disagreement instead of guessing at it.

| Method, all on the same images | Median diameter | n | Population medians, library / production / repro |
|---|---|---|---|
| Dip-argmax, verbatim `measure_scale.py` | 760.0 px | 2,659 | |
| Its 15 percent trimmed mean over the whole sample | 749.4 px | 2,659 | |
| Gradient, max abs dI/dr of the smoothed annular profile | 768.0 px | 2,659 | |
| Circle fit, wide band 0.50 to 1.06 R_cav | 841.4 px | 2,659 | 826.7 / 870.3 / 870.0 |
| Circle fit, rim band 0.80 to 0.96 R_cav | 789.0 px | 2,659 | 777.3 / 809.5 / 811.6 |

The 848 px figure is **reproduced**. A wide band least-squares circle fit to the
same 360 radial edge points gives a median 841.4 px over 2,659 images and 826.7
px over the library population alone, against the previously reported 848. It is
not reproduced as a single physical ring. The wide band spans both modes, the
lens rim at 0.89 R_cav and the wall shoulder at 1.01 R_cav, and with outlier
rejection it settles between them at 0.96 R_cav, which is 422 px radius, 844 px
diameter. The 848 px figure is the least-squares compromise between two different
rings, which is why it exceeds the lens rim by about 58 px. Restricted to the rim
band the identical fit gives 789.0 px.

The dip-argmax and gradient figures, 760.0 and 768.0 px, sit below the rim band
fit because their search band stops at 0.92 R_cav, inside the rim, and because
the annular average smears a rim that is not perfectly concentric.

## The earlier run, reproduced

| Quantity | Value |
|---|---|
| Frames taken | the exact 200 the prior script selects, same glob, `random.seed(7)` |
| Frames accepted by the 1.0 dip gate | 200 |
| Trimmed mean lens diameter, this implementation | 784.7 px |
| Published target | 783.8 px |
| Difference | 0.9 px |
| Within one pixel | yes |

The reimplementation agrees with the shipped routine to within a pixel, so the
cross population and cross method comparison in this report stands.

## What the other rings most likely are

- The ring at 1.01 of the cavity radius, 445.0 px radius, 890 px diameter, median
  depth 4.92 and median sharpness 0.481. The wall shoulder, that is the saline
  meniscus where the fluid meets the moulded wall, coincident with the boundary
  the bright-disc mask already puts at 438.5 px radius. It is the deepest and
  sharpest feature in the profile.
- The 1,084 unclustered rings, median radius 330.5 px, present in 40.8 percent of
  frames but with no mode, are lens surface artefacts and annular averaging
  noise: smears, droplets, HEMA and bubbles on the lens, each showing up as a
  shallow local minimum at whatever radius it happens to sit.
- There is no evidence in this data for a separate third structural ring. The
  profile between the rim and the wall carries only the flat interior floor.

## Files

| Artifact | What it is |
|---|---|
| `vm/ops/scan_rings.py` | the read only per image scanner, piped over ssh base64 encoded |
| `run/eda_full_20261015/ring_sample.txt` | the 2,700 row picture list, 2,682 distinct contents |
| `run/eda_full_20261015/ring_inventory.csv` | one row per detected ring, 3,483 rows |
| `run/eda_full_20261015/ring_candidates.json` | per candidate ring statistics, the detection rate curve, splits |
| `run/eda_full_20261015/ring_identity.json` | the discriminators, the method cross check, the verdict with its evidence |
| `run/eda_full_20261015/ring_raw.tsv` | the raw scanner output, 102,555 rows |
| `run/eda_full_20261015/ring_scan.log` | the scanner progress log |
| `run/eda_full_20261015/ring_pop_b_listing.txt` | the 7,164 `*Pass1*` basenames of the production drop, the sampling input |
| `run/eda_full_20261015/ring_repro_listing.txt` | the prior script's exact 200 frames, the reproduction input |
| `experiments/eda_full/ring_identity.py` | the sampler, the aggregator and the discriminators |
| `experiments/eda_full/verify_ring_identity.py` | the verifier |

Nothing was written to the shared VM. The scanner opens image files for reading
only.

## Verification

Checked, with the numbers:

1. The sample reproduces from its fixed seeds and matches `ring_sample.txt`
   exactly, 2,700 rows.
2. The aggregation was run twice and is byte identical. `ring_inventory.csv` md5
   `82535f95389fd3954979475e58bdd1a9`, `ring_candidates.json` md5
   `c3cf10e0a62a7e21ae39af31b1f09de9`, `ring_identity.json` md5
   `e56d6515447a94f19b19f64fd2f02852`, `ring_sample.txt` md5
   `185eadfcd89d7789653488d59b92f8e9`, all unchanged on the second run.
3. `python experiments/eda_full/verify_ring_identity.py` re-derives the headline
   numbers by a second route, exits 0, and reports its check and failure counts.
