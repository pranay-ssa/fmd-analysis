---
title: Cross-ticket verification gate for the full-coverage EDA
date: 2026-10-15
type: result
status: active
where: docs/reference/eda_full_verification.md
---

# Cross-ticket verification gate for the full-coverage EDA

> **Current run 2026-10-28.** The gate below was executed on the 2026-10-15 run. The
> annotation was re-exported on 2026-10-26 and resolved again into `run/eda_full_20261028/`;
> the resolver's own 14 checks pass there, and the splits and label tables built on it carry
> their own verifiers. The figures in this document describe the 2026-10-15 run.

Ticket 016 of the full-coverage EDA map. This is the last check before the numbers
reach a workbook and the client. It is not another per-ticket verifier. It is one
cross-cutting gate that stands over everything tickets 007, 008, 009, 010, 011,
012, 013a, 014 and 015 produced, and it does three things the map requires:

1. an independent second re-derivation of every headline figure, from the rawest
   inputs, by a route no per-ticket verifier uses;
2. a byte-identical rerun of the whole pipeline into a separate directory, diffed
   by md5 artifact by artifact;
3. a proof that the per-ticket verifiers actually bite, by corrupting one known
   value in a copy and showing the owning verifier exit non-zero.

The gate is `experiments/eda_full/verify_whole_eda.py`. It runs read-only against
the repo. Everything it writes is listed at the end.

## Result

- **142 independent re-derivations**, every one in agreement with the record it
  checks.
- **15 cross-artifact consistency checks**, every one passing.
- **157 assertions total, 0 failures.** The gate exits 0.
- **24 artifacts rerun and diffed, 24 byte-identical.**
- **5 verifiers shown to bite**, each exiting 0 on clean input and 1 on a single
  corrupted value.
- **The 15.34 microns-per-pixel inversion is independently reproduced.**

## Gate 1: an independent second re-derivation of every headline

The route reads only the rawest inputs: the 9 annotation XMLs, the raw
`run/eda_full_20261015/file_manifest.csv`, and the frozen `data/crosswalk.csv`.
It never calls a per-ticket verifier and never trusts a per-ticket intermediate.
For each figure the gate records the published value, the value its own route
produced, and whether they agree. The full table is in
`run/eda_full_20261015/verification.json` under
`gate1_independent_rerivation.figures`; the highlights by record:

| Record | Figures re-derived | Published value, at the source | My value | Agree |
|---|---|---|---|---|
| 007 census | files on disk | 13,126 | 13,126 | yes |
| | bytes on disk | 65,821,403,332 | 65,821,403,332 | yes |
| | distinct pictures | 10,614 | 10,614 | yes |
| | per-folder files (Objects, Categorical, Library, Production) | 4,230 / 6,384 / 1,465 / 1,047 | same | yes |
| | per-line files (L24, L25, L26, L27, L31) | 5,775 / 1,148 / 2,056 / 1,860 / 2,287 | same | yes |
| | per-line distinct pictures | 4,348 / 972 / 1,503 / 1,637 / 2,154 | same | yes |
| | copy distribution (1..5) | 8,940 / 972 / 607 / 54 / 41 | same | yes |
| | pictures in >1 folder | 1,609 | 1,609 | yes |
| | production files / distinct contents | 1,047 / 1,046 | 1,047 / 1,046 | yes |
| 009 crosswalk | canonical rows / defined-only cells / gates / collision flags | 28 / 3 / 4 / 2 | same | yes |
| 010 resolution | pictures mentioned | 6,690 | 6,690 | yes |
| | surviving shapes | 20,014 | 20,014 | yes |
| | pictures carrying a shape | 4,782 | 4,782 | yes |
| | pictures with no shape | 5,832 | 5,832 | yes |
| | pictures mentioned nowhere | 3,924 | 3,924 | yes |
| | box shapes / tag shapes | 14,182 / 5,832 | 14,182 / 5,832 | yes |
| | wins by level (1, 2, 3) | 1,046 / 5,387 / 257 | same | yes |
| | wins by file (7 production, Sep-22, old) | 149,150,147,150,150,150,150 / 5,387 / 257 | same | yes |
| | disagreement rows | 886 | 886 | yes |
| | Sep-22 mentions / with labels | 709 / 594 | 709 / 594 | yes |
| | old-library mentions / with labels | 177 / 177 | 177 / 177 | yes |
| | basenames only visible via the manifest | 187 | 187 | yes |
| | per-canonical picture and shape counts (28 defects) | the ticket 011 table | all agree | yes |
| 011 label census | pictures with a box / a tag | 1,130 / 4,329 | 1,130 / 4,329 | yes |
| | box-only / tag-only / both | 453 / 3,652 / 677 | same | yes |
| | codes per picture median, mean, p90, max | 1, 1.68005, 4, 11 | same | yes |
| | headline pair and triples | 664 / 167 / 164 | same | yes |
| 012 box geometry | box shapes | 14,182 | 14,182 | yes |
| | axis-aligned boxes | 660 | 660 | yes |
| | per-defect median diagonal (12 defects) | the ticket 012 table | all agree | yes |
| | median diagonal by folder group and line | the ticket 012 tables | all agree | yes |
| 014 micron gate | gate pictures (FM, Fiber, EP, HEMA) | 171 / 136 / 33 / 94 | same | yes |
| | new 300 cut boundaries (FM, Fiber) | (19.250, 19.610] / (19.410, 19.900] | same | yes |
| | old 647 cut boundaries (FM, Fiber) | (41.780, 42.790] / (42.080, 44.170] | same | yes |
| | delta changed pictures | 170 | 170 | yes |
| | delta added tags (FM, Fiber, EP) | 118 / 51 / 1 | same | yes |
| | delta removed tags | P1_ML: 1 | P1_ML: 1 | yes |
| | delta geometry untouched | 0 | 0 | yes |
| 015 coverage | census / mentioned / with shape / no shape / nowhere | 10,614 / 6,690 / 4,782 / 5,832 / 3,924 | same | yes |
| | per-folder distinct, mentioned, shape | the ticket 015 table | all agree | yes |
| | per-group and per-line distinct, mentioned, shape | the ticket 015 tables | all agree | yes |
| | library-only pictures | 177 | 177 | yes |
| | library-only class breakdown | the 9-class table | all agree | yes |
| | folder disagreement content-all / content-batch / name-batch | 279 / 129 / 114 | 279 / 129 / 114 | yes |

### Figures not independently reached, and why

Four groups of figures cannot be reached by this route without a fresh read of
the shared VM or a per-ticket join, so they are named here rather than skipped:

- **The cavity measurement (10,470 measured, 144 low_bright, the cavity radius
  and centre statistics).** This needs the pixel data of 10,614 images
  re-thresholded on the shared VM. The raw output `cavity_raw.tsv` from ticket
  012 is reused as a gate input, and the containment shares are re-derived by
  `verify_box_geometry.py`, not here.
- **The blind-scale per-stratum rim medians and the um/px table.** This needs
  the VM rim measurement; `rim_raw.tsv` from ticket 013a is reused, and the
  per-stratum medians are re-derived by `verify_scale.py`, not here.
- **The coverage per-canonical-defect share table (28 rows).** This needs the
  join of each defect to its nominal library class folder population, which
  ticket 015 owns and `verify_coverage.py` second-routes. The partitioning
  figures (per folder, group, line) are re-derived here.
- **Every published pair and triple in `pairs.csv`.** The full combinatorial
  table is reproduced by `verify_label_census.py`; this gate re-derives the
  three headline combinations.

## The inversion is independently reproduced

Ticket 014 concluded that the client's own micron gate inverts to about 15.34
microns per pixel, which agrees with neither 18.1165 nor 18.25. The gate
reproduces this from scratch: it reads the box geometry straight from the 9
production XMLs and the 7 read-only 2026-10-13 XMLs, keys everything on content
md5, uses the longer side `max(w, h)` of the largest base-code box per image, and
inverts the flagged-versus-unflagged boundary. `box_sizes.csv` is not used.

| Boundary | Pixels | Implied scale (um/px) |
|---|---|---|
| New 300 cut, FM and Fiber intersected | (19.410, 19.610] | 15.2983 to 15.4560 |
| Old 647 cut, FM and Fiber intersected | (42.080, 42.790] | 15.1204 to 15.3755 |
| Combined (new and old intersected) | - | 15.2983 to 15.3755, midpoint 15.337 |

The combined interval does not contain 18.1165 and does not contain 18.25.
**The inversion stands.** The two boundaries, the brackets, and the about 15.34
midpoint are all reproduced, and the published claim that the result agrees with
neither candidate scale is confirmed.

## Gate 2: the byte-identical rerun

Every local builder was re-run from scratch in dependency order into a separate
output tree (`C:/Users/Abcom/AppData/Local/hermes/cache/scratch/v16/repo`),
reading only the transcribed inputs. Every generated artifact was then diffed
against the committed one by md5. **All 24 artifacts are byte-identical.** The
per-artifact table is `run/eda_full_20261015/rerun_md5s.txt` and
`verification.json` under `gate2_rerun.artifacts`.

Rerun by this gate, into the separate tree:

| Builder | Artifacts |
|---|---|
| `build_crosswalk.py` (009) | `crosswalk.csv`, `crosswalk_evidence.json` |
| `resolve_labels.py` (010) | `resolved_labels.csv`, `disagreement.csv`, `resolution.json` |
| `label_census.py` (011) | `label_census.csv`, `codes_per_image.csv`, `pairs.csv` |
| `box_geometry.py` (012) | `box_sizes.csv`, `size_by_stratum.json`, `cavity_geometry_library.json` |
| `micron_gate.py` (014) | `gate_analysis.csv`, `gate_delta.csv`, `gate_scale_estimate.json` |
| `coverage.py` (015) | `coverage.csv`, `folder_disagreement.csv` |
| `verify_scale.py --aggregate` and `--build-sample` (013a) | `scale_samples.csv`, `scale_by_stratum.json`, `scale_sample.txt` |

Reused as raw read-only inputs, never re-read (the two VM legs):

| Artifact | Leg |
|---|---|
| `file_manifest.csv`, `picture_table.csv`, `census.json` | ticket 007 hash and aggregate of the 65 GB picture set |
| `rim_raw.tsv` | ticket 013a VM rim measurement of 1,727 pictures |
| `cavity_raw.tsv` | ticket 012 VM cavity measurement of 10,614 pictures |

So 19 artifacts were genuinely regenerated locally and are byte-identical; the
5 raw VM outputs were reused and their md5s are unchanged (the rerun tree binds
the same bytes the committed run used). No artifact failed the diff, and no
legitimate exception was needed, because no builder writes a timestamp.

## Gate 3: the verifiers bite

One known value was corrupted in a copy of an artifact inside the rerun tree,
the owning verifier was run, and its exit code recorded. Clean input exits 0;
corrupted input must exit non-zero. Corruption happened only on copies; the repo
artifacts were untouched.

| Verifier | Corrupted artifact | Clean exit | Corrupted exit |
|---|---|---|---|
| `verify_crosswalk.py` | `data/crosswalk.csv` (a production code renamed) | 0 | 1 |
| `verify_resolution.py` | `resolution.json` (resolved total 6,690 to 6,691) | 0 | 1 |
| `verify_label_census.py` | `label_census.csv` (bubble picture count 819 to 818) | 0 | 1 |
| `verify_coverage.py` | `coverage.csv` (a folder stratum value renamed) | 0 | 1 |
| `verify_micron_gate.py` | `gate_analysis.csv` (FM flagged n 171 to 170) | 0 | 1 |

All five verifiers bite. A verifier that could not be made to fail would not be
a verifier.

## Cross-artifact consistency

Five claims span tickets, and no single ticket owned them. The gate checks each:

1. **14,182 boxes and 5,832 tags sum to 20,014 shapes, identically in
   `resolved_labels.csv`, `label_census.csv` and `box_sizes.csv`.** Re-derived
   in all three files: 14,182 + 5,832 = 20,014, and `box_sizes.csv` holds 14,182
   rows. Agree.
2. **10,614 census, 4,782 with a shape, 5,832 with no shape, 6,690 mentioned,
   3,924 mentioned nowhere, mutually consistent.** 4,782 + 5,832 = 10,614 and
   6,690 + 3,924 = 10,614. `picture_table.csv` holds 10,614 rows;
   `resolution.json` carries 10,614, 6,690 and 3,924; `coverage.csv` folder rows
   sum to 10,614 / 6,690 / 4,782 / 5,832 / 3,924. All agree. The two "unannotated"
   figures are never swapped: 5,832 is the no-shape picture count and 3,924 is
   the no-mention picture count.
3. **The four gate codes are strict subsets of their base codes, at 171, 136, 33
   and 94 distinct pictures.** Re-derived from the production XML directly, and
   from `resolved_labels.csv`, and from `label_census.csv`. Every gate image also
   carries its base code. Agree.
4. **The 170-picture delta reconciles per base code.** 169 pictures gain a gate
   tag (118 Foreign Matter, 51 Fiber, 1 Extraneous Polymer) and 1 picture loses a
   `P1_ML` tag; geometry is untouched. The added-gate counts per base match.
5. **No picture carries labels from two sources anywhere in
   `resolved_labels.csv`.** Every picture's rows name exactly one `source_file`.
   Zero violations.

## How to run

```bash
# the rerun (into a separate tree), then the gate
./.venv/Scripts/python.exe experiments/eda_full/verify_whole_eda.py
```

The gate expects the rerun tree at `RERUN_DIR` (default the v16 scratch tree
above) and the read-only 2026-10-13 XMLs at `OLD_PROD_DIR` (default the local
scratch copy). It reruns nothing itself; the rerun is a separate, transcribed
step, and the gate diffs the result. With the rerun tree absent, the gate reports
the rerun as not run and still performs gates 1 and the cross-artifact checks.

## Files and artifacts

| Artifact | What it is |
|---|---|
| `experiments/eda_full/verify_whole_eda.py` | the cross-ticket gate |
| `run/eda_full_20261015/verification.json` | per figure: published value, my value, agree; the rerun md5 table; the corrupt-copy results and exit codes; the inversion |
| `run/eda_full_20261015/rerun_md5s.txt` | every artifact, md5 before and after the rerun |

Nothing was written to the shared VM. No existing artifact, builder, verifier or
doc was modified; corruption happened only on copies in the scratch tree, and
`git status` shows no artifact change.
