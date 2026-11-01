---
title: Blind scale, variation by folder group and production line (013a)
date: 2026-10-15
type: result
status: active
where: reports/eda_full/blind_scale_20261015.md
---

# Blind scale, variation by folder group and production line

Ticket 013a, the variation test. Ticket 008 found no usable blind nominal, so
the absolute test written in 013 cannot run and was not attempted. This test
leaves the client nominal out entirely: it measures the lens rim, and the cavity,
in PIXELS per folder group x production line, and asks whether the pixel scale
differs by group or by line. The lens is the same physical part on every line, so
a real difference in the measured rim pixels between strata would be a scale
difference.

Every microns-per-pixel figure below is the measured rim in pixels divided by our
own reference of 14,200 microns. It is at our own 14,200 micron reference, not an
independent check, and it is not blind. The value of this ticket is the pixel
comparison between strata, so the pixels are the headline and the microns figure
is a postscript.

## Method, fixed before any number was read

- The rim and cavity routine is reused verbatim from
  `/data/FMD_Data_26082026/measure_scale.py`, the routine that produced the
  published 783.8 px trimmed mean and 18.1165 microns per pixel. Same
  `radial_profile`, same `measure`, same `dip_prominence > 1.0` gate. No new
  measurement was invented, so the numbers are comparable with the published one.
- Pictures are 2,448 x 2,048, 8 bits, 5,014,582 bytes each. That was read from
  the files in this run, not assumed.
- Universe: `run/eda_full_20261015/picture_table.csv`, one row per distinct
  picture keyed on content md5, the winning path per picture.
- Folder group, by which folders hold a copy. Updated is either Updated folder
  together. Library is `ICube Defects Library`. A picture that sits in both is
  sampled in both, which is why 1,809 rows come from 1,727 distinct pictures.
- Line comes from the `_LNN_` form in the filename.
- 200 pictures per stratum, capped where the stratum has fewer. The sample is
  drawn with the fixed seed 20261015 and the exact list is written to
  `scale_sample.txt`, so it can be re-derived.
- Clean band 640 to 900 px. This was fixed from the pooled rim histogram, before
  any per-stratum stat was read, to separate the near-rim mode from the misfire
  tail. It is written into the aggregator so a second reader can repeat it.

## Sample size, cap, and the ticket's stated sizes

Achieved universe and cap are read from the picture table. The ticket's stated
sizes are shown beside them.

| Stratum | Universe (distinct) | Ticket stated | Target | Sampled | Capped |
|---|---|---|---|---|---|
| Updated L24 | 4,272 | 3,604 | 200 | 200 | no |
| Updated L25 | 948 | 839 | 200 | 200 | no |
| Updated L26 | 1,475 | 1,342 | 200 | 200 | no |
| Updated L27 | 1,610 | 1,524 | 200 | 200 | no |
| Updated L31 | 2,132 | 2,029 | 200 | 200 | no |
| Library L24 | 788 | 794 | 200 | 200 | no |
| Library L25 | 155 | 161 | 200 | 155 | yes |
| Library L26 | 205 | 254 | 200 | 200 | no |
| Library L27 | 115 | 115 | 200 | 115 | yes |
| Library L31 | 139 | 139 | 200 | 139 | yes |

Two corrections to the ticket's stated sizes. The Library figures track the
library folder file counts per line rather than distinct pictures, so they
overstate Library L25 and L26. And the Updated figures are below what the picture
table holds and cannot be reproduced from it. The only operational consequence is
which strata cap. Under the picture table only Library L25, L27 and L31 are
capped. Library L26 comes in at 205, just above the 200 target, so it is sampled
at 200 and is not capped, although the ticket listed it as one that would be.

The Library group is the weaker contrast. Of its 1,402 distinct pictures, 1,225
also sit in an Updated folder, so most Library rows measure the same images as
Updated rows. Only 177 picture are in the Library alone, and 112 of the 809
Library rows are those. The two folder groups are therefore not independent
samples and their agreement is expected.

## Measurement failures

Of the 1,727 distinct pictures measured, 47 would not measure: 30 gave `no_mask`
(too few bright pixels) and 17 gave `no_dip` (the rim dip was below the gate the
published method uses). At row level that is 48 failures out of 1,809 rows, 1,761
measured. No stratum dropped more than 10 pictures and none was silently shrunk:
the `failed_n` column carries every one.

| Stratum | Sampled | Measured ok | Failed | Flags |
|---|---|---|---|---|
| Updated L24 | 200 | 199 | 1 | no_dip 1 |
| Updated L25 | 200 | 197 | 3 | no_mask 3 |
| Updated L26 | 200 | 194 | 6 | no_dip 4, no_mask 2 |
| Updated L27 | 200 | 190 | 10 | no_dip 9, no_mask 1 |
| Updated L31 | 200 | 195 | 5 | no_mask 5 |
| Library L24 | 200 | 189 | 11 | no_dip 3, no_mask 8 |
| Library L25 | 155 | 153 | 2 | no_mask 2 |
| Library L26 | 200 | 200 | 0 | none |
| Library L27 | 115 | 105 | 10 | no_mask 10 |
| Library L31 | 139 | 139 | 0 | none |

## Pixel distributions by stratum

Rim is the lens rim diameter in pixels. p25, p50 and p75 are reported, not a
single mean.

| Stratum | n ok | rim p25 | rim p50 | rim p75 | rim mean | rim sd | rim rel spread |
|---|---|---|---|---|---|---|---|
| Updated L24 | 199 | 595 | 748 | 786 | 688.9 | 125.7 | 18.2 % |
| Updated L25 | 197 | 572 | 722 | 778 | 674.4 | 136.7 | 20.3 % |
| Updated L26 | 194 | 688 | 760 | 784 | 715.6 | 105.1 | 14.7 % |
| Updated L27 | 190 | 682 | 735 | 762 | 712.3 | 80.3 | 11.3 % |
| Updated L31 | 195 | 716 | 750 | 770 | 728.2 | 73.0 | 10.0 % |
| Library L24 | 189 | 492 | 688 | 762 | 640.1 | 137.7 | 21.5 % |
| Library L25 | 153 | 498 | 756 | 790 | 661.0 | 169.7 | 25.7 % |
| Library L26 | 200 | 718 | 763 | 790 | 732.8 | 103.5 | 14.1 % |
| Library L27 | 105 | 606 | 688 | 762 | 658.4 | 135.2 | 20.5 % |
| Library L31 | 139 | 708 | 750 | 774 | 721.1 | 90.0 | 12.5 % |

Every stratum has a long lower tail. The pooled histogram has its mode at 750 to
799 px, with 624 of 1,761 values there, and a tail that runs down to 100 px. That
tail is the method locking onto a dark feature inside the lens band instead of
the rim. It is a measurement misfire, not a small lens.

## Between-stratum spread against within-stratum spread

- Raw rim p50 runs from 688 to 763 px across the ten strata. Between-stratum
  range 75 px, 10.2 percent of the mean p50.
- Within-stratum rim sd runs from 73.0 to 169.7 px. Within-stratum relative
  spread runs from 10.0 to 25.7 percent.
- So the between-stratum spread of the median is smaller than the within-stratum
  spread in the wide strata and only comparable in the tightest ones. The
  between does not clearly exceed the noise.
- The raw p50 differences track the misfire rate, not the line. The correlation
  between a stratum's raw p50 and its contamination percentage is minus 0.63.
  The strata whose rim finder misfires most (Library L24 at 41.8 percent, Library
  L27 at 30.5 percent) have the lowest p50. The cleanest strata (Library L26 at
  11.5 percent, Updated L31 at 12.8 percent) have the highest.
- Restricted to the clean band 640 to 900 px, the ten strata agree closely. Clean
  p50 runs from 728 to 780 px, a range of 52 px, 6.8 percent, and the clean
  within-stratum sd runs from 32.8 to 51.7 px. The between-stratum difference on
  the clean subset is the same size as the within-stratum spread, and no line or
  group stands apart.

| Stratum | clean n | clean p25 | clean p50 | clean p75 | clean sd | contamination |
|---|---|---|---|---|---|---|
| Updated L24 | 135 | 744 | 774 | 802 | 46.2 | 32.2 % |
| Updated L25 | 129 | 728 | 768 | 796 | 46.1 | 34.5 % |
| Updated L26 | 153 | 742 | 770 | 792 | 40.2 | 21.1 % |
| Updated L27 | 163 | 708 | 744 | 770 | 41.6 | 14.2 % |
| Updated L31 | 170 | 732 | 758 | 772 | 32.8 | 12.8 % |
| Library L24 | 110 | 712 | 756 | 786 | 48.1 | 41.8 % |
| Library L25 | 104 | 752 | 780 | 800 | 42.1 | 32.0 % |
| Library L26 | 177 | 740 | 770 | 792 | 40.3 | 11.5 % |
| Library L27 | 73 | 684 | 728 | 772 | 51.7 | 30.5 % |
| Library L31 | 115 | 732 | 756 | 778 | 38.3 | 17.3 % |

## Answer

The lines and the two folder groups agree. No line and no folder group shows a
pixel scale that differs from another by more than the noise of the measurement
shown here. Where the raw medians differ, by at most 75 px or 10.2 percent, the
difference is explained by how often the rim finder misfired in that stratum, and
it disappears once the misfires are set aside. On the clean band the ten strata
agree to within 6.8 percent, which is the size of the within-stratum spread
itself. The folder-group contrast is further weakened by overlap, since 1,225 of
the 1,402 Library-group pictures also sit in the Updated group.

The gap this ticket was originally aimed at, 18.12 against 18.25, is 0.7 percent.
The within-stratum spread measured here is 10 to 26 percent, and even the
published single-sample estimate carried 5.3 percent. The gap is far inside the
noise, so no version of this measurement, published or here, can resolve it. That
is itself the finding.

## Implied microns per pixel, at our own 14,200 micron reference

These are the measured rim in pixels divided by our own 14,200 micron reference.
They are at our own 14,200 micron reference, not an independent check, and must
not be quoted as blind.

| Stratum | um/px from p50 | um/px from clean p50 |
|---|---|---|
| Updated L24 | 18.98 | 18.35 |
| Updated L25 | 19.67 | 18.49 |
| Updated L26 | 18.68 | 18.44 |
| Updated L27 | 19.32 | 19.09 |
| Updated L31 | 18.93 | 18.73 |
| Library L24 | 20.64 | 18.78 |
| Library L25 | 18.78 | 18.21 |
| Library L26 | 18.61 | 18.44 |
| Library L27 | 20.64 | 19.51 |
| Library L31 | 18.93 | 18.78 |

For orientation, the published value from the production sample was 18.1165, at
the same non-blind reference. The clean-band figures cluster near that value; the
raw-p50 figures scatter upward because the misfire tail drags the median down.
But since none of these is independent of our 14,200, none of them checks that
reference or the 18.25 claim.

## Files and verification

| Artifact | What it is |
|---|---|
| `vm/ops/measure_rim_strata.py` | the read-only measuring script, piped over ssh |
| `run/eda_full_20261015/scale_sample.txt` | the exact sampled picture paths, 1,727 |
| `run/eda_full_20261015/scale_samples.csv` | one row per measured picture, 1,809 |
| `run/eda_full_20261015/scale_by_stratum.json` | per-stratum stats and the comparison block |
| `experiments/eda_full/verify_scale.py` | the sampler, the aggregator and the verifier |
| `run/eda_full_20261015/rim_raw.tsv` | the raw per-picture output for the 1,727 pictures |

Nothing was written to the shared VM. The measuring script and the raw output are
read-only against the picture files.

Checked, with the numbers:

1. The sample reproduces from seed 20261015 and matches `scale_sample.txt`
   exactly, 1,727 paths. Achieved n per stratum is in the first table against the
   200 target with the cap stated.
2. The aggregation was run twice and is byte-identical.
   `scale_samples.csv` md5 `07bf5fac5f4e1f74e0ce0ab7fd056575` both times,
   `scale_by_stratum.json` md5 `276168f3b9ce047077537f86792b36c2` both times.
   `scale_sample.txt` md5 `1f60c5a569a6b093ebbe9c29247472fb`,
   `rim_raw.tsv` md5 `f47b3830d3b8cdb6f8f52baad6e1adef`.
3. The verifier re-derives the per-stratum medians and means from
   `scale_samples.csv` by a second route, with `statistics.median` and
   `statistics.fmean` rather than the interpolating percentile used to build the
   JSON, and diffs them against `scale_by_stratum.json`: zero mismatches. It also
   re-reads 30 of the measured pictures from the VM, three per stratum, with an
   independently written re-implementation of the same rim definition and
   checks the recorded rim and cavity. Worst rim delta 0.0 px, worst cavity delta
   0.0 px, zero disagreements. `python experiments/eda_full/verify_scale.py`
   exits 0.
