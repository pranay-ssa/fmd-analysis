---
title: Resolved label census and multi-label analysis
date: 2026-10-15
type: result
status: active
where: reports/eda_full/label_census_20261015.md
---

# Resolved label census and multi-label analysis

Ticket 011 of the full-coverage EDA map. It redoes the 2026-10-13 multi-label
analysis at full coverage, on the resolved labels from ticket 010, and counts
every canonical defect two ways: how many pictures carry it and how many shapes
carry it, split by folder group and by production line, with the box tier and
the tag tier always kept apart.

Builder and verifier:

```bash
./.venv/Scripts/python.exe experiments/eda_full/label_census.py
./.venv/Scripts/python.exe experiments/eda_full/verify_label_census.py
```

## What is counted, and the two words that are never confused

The census holds **10,614 distinct pictures** (keyed on content md5). Of them:

- **6,690 pictures are MENTIONED** by some annotation file, so they resolve to a
  source of record. This is a mention count.
- **4,782 pictures carry at least one SHAPE.** This is a shape count. The other
  1,908 of the mentioned pictures resolve to a file that lists them with no
  shape at all (a clear image), so they are a mention and not a label.
- **3,924 pictures are mentioned NOWHERE**, so they have no source of record and
  no label of any kind.

The surviving shapes number **20,014**, split by the two tiers the client's own
ontology defines:

| tier | shapes | pictures carrying it |
|---|---|---|
| box (a localised defect) | 14,182 | 1,130 |
| tag (a whole-image flag) | 5,832 | 4,329 |
| total | 20,014 | 4,782 |

The two tiers are annotated to very different depths and are never pooled
without saying so. The tag tier covers more pictures but is thin: the 4,329
pictures that carry a tag hold a median of one canonical code each (3,652 of them
carry a tag and nothing else). The box tier covers fewer pictures but is dense:
the 1,130 pictures that carry a box hold a median of three canonical codes each.

Counting rules, all non-negotiable and all enforced in code:

- **Every join is keyed on the content md5, never on a path.** 187 basenames hold
  a content that also exists under a second name, so a path-based count
  undercounts. `resolved_labels.csv` and `picture_table.csv` are both keyed on
  the picture md5, so every join here is a content join by construction.
- A `defined_only` crosswalk cell is not an instance. `P2_BSC` in production, and
  `P1_PPM` and `P2_FOV` in Sep-22, are defined but carried by no shape, and are
  never counted.
- The four gate tags are size flags, not separate defects, and are reported as
  strict subsets of their base codes (below).

## Per canonical defect

Picture counts and shape counts, over every picture that carries at least one
shape. `Updated` is the two Updated folders; `Library` is ICube Defects Library.
The `Updated` and `Library` columns are picture counts and sum to the `pictures`
column for every row.

| canonical defect | name | tier | library only | pictures | shapes | box shapes | tag shapes | pics Updated | pics Library |
|---|---|---|---|---|---|---|---|---|---|
| bubble | Bubble | box | no | 819 | 10869 | 10869 | 0 | 747 | 72 |
| bubble_cluster | Bubble Cluster | box | no | 428 | 1182 | 1182 | 0 | 407 | 21 |
| bubble_irregular | Bubble Irregular | box | no | 147 | 169 | 169 | 0 | 121 | 26 |
| bubble_on_123 | Bubble On 123 | box | **yes** | 13 | 79 | 79 | 0 | 0 | 13 |
| bubble_on_edge | Bubble On Edge | box | **yes** | 14 | 90 | 90 | 0 | 0 | 14 |
| extraneous_polymer | Extraneous Polymer | box | no | 144 | 150 | 150 | 0 | 144 | 0 |
| fiber | Fiber | box | no | 178 | 245 | 245 | 0 | 177 | 1 |
| foreign_matter | Foreign Matter | box | no | 331 | 626 | 626 | 0 | 331 | 0 |
| hema_fragment | HEMA Fragment | box | no | 7 | 8 | 8 | 0 | 7 | 0 |
| stretched_bubble | Stretched Bubble | box | no | 6 | 7 | 7 | 0 | 6 | 0 |
| wet_package | Wet Package | box | no | 146 | 662 | 662 | 0 | 122 | 24 |
| hema_obstruction | HEMA Obstruction | box+tag | no | 180 | 181 | 95 | 86 | 180 | 0 |
| bubble_scatter | Bubble Scatter | tag | no | 6 | 6 | 0 | 6 | 6 | 0 |
| cavity_off_center | Cavity Off Center | tag | no | 184 | 184 | 0 | 184 | 184 | 0 |
| dirty_camera | Dirty Camera | tag | no | 329 | 329 | 0 | 329 | 329 | 0 |
| dirty_strobe | Dirty Strobe | tag | no | 43 | 43 | 0 | 43 | 43 | 0 |
| folded_lens | Folded Lens | tag | no | 237 | 237 | 0 | 237 | 237 | 0 |
| lens_off_center | Lens Off Center | tag | no | 957 | 957 | 0 | 957 | 957 | 0 |
| low_dose | Low Dose | tag | no | 215 | 215 | 0 | 215 | 215 | 0 |
| missing_lens | Missing Lens | tag | no | 325 | 325 | 0 | 325 | 325 | 0 |
| missing_primary_package | Missing Primary Package | tag | no | 1426 | 1551 | 0 | 1551 | 1426 | 0 |
| multiple_lenses | Multiple Lenses | tag | no | 1439 | 1439 | 0 | 1439 | 1439 | 0 |
| package_misalignment | Package Misalignment | tag | no | 2 | 2 | 0 | 2 | 2 | 0 |
| view_obstructed | View Obstructed | tag | no | 24 | 24 | 0 | 24 | 24 | 0 |
| extraneous_polymer_micron_gate | Extraneous Polymer micron gate | gate | no | 33 | 33 | 0 | 33 | 33 | 0 |
| fiber_micron_gate | Fiber micron gate | gate | no | 136 | 136 | 0 | 136 | 136 | 0 |
| foreign_matter_micron_gate | Foreign Matter micron gate | gate | no | 171 | 171 | 0 | 171 | 171 | 0 |
| hema_micron_gate | HEMA micron gate | gate | no | 94 | 94 | 0 | 94 | 94 | 0 |

The two **library-only classes** (Bubble On 123, Bubble On Edge) stay visible
under their own names. They carry no code in either newer project, and all 27 of
their pictures sit in ICube Defects Library.

`hema_obstruction` straddles both tiers, which is the one `box|tag` row in the
crosswalk. It is a **tag** in the Sep-22 project (`P2_HMO`, 86 tag shapes on 86
pictures) and a **box** in the production files (`P3_HE`, 95 box shapes on 95
pictures). It is never merged with `hema_fragment`, which is the other reading of
`P3_HE` and a separate row.

## Per production line

Shape counts with picture counts in parentheses, per canonical defect. Each
picture sits on exactly one line, so the line columns sum to the `shapes`
column of the table above for every row.

| defect | L24 | L25 | L26 | L27 | L31 | total |
|---|---|---|---|---|---|---|
| bubble | 6126 (428) | 274 (30) | 2882 (232) | 1587 (129) | 0 (0) | 10869 |
| bubble_cluster | 630 (216) | 14 (6) | 258 (116) | 277 (88) | 3 (2) | 1182 |
| bubble_irregular | 82 (70) | 7 (5) | 45 (37) | 34 (34) | 1 (1) | 169 |
| bubble_on_123 | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 79 (13) | 79 |
| bubble_on_edge | 14 (3) | 23 (3) | 4 (1) | 9 (1) | 40 (6) | 90 |
| extraneous_polymer | 74 (70) | 30 (30) | 11 (10) | 21 (20) | 14 (14) | 150 |
| fiber | 128 (97) | 16 (12) | 66 (47) | 25 (13) | 10 (9) | 245 |
| foreign_matter | 303 (169) | 18 (14) | 93 (69) | 181 (48) | 31 (31) | 626 |
| hema_fragment | 3 (2) | 1 (1) | 0 (0) | 0 (0) | 4 (4) | 8 |
| stretched_bubble | 0 (0) | 0 (0) | 1 (1) | 2 (1) | 4 (4) | 7 |
| wet_package | 157 (46) | 186 (6) | 316 (91) | 3 (3) | 0 (0) | 662 |
| hema_obstruction | 157 (156) | 17 (17) | 3 (3) | 2 (2) | 2 (2) | 181 |
| bubble_scatter | 2 (2) | 0 (0) | 0 (0) | 3 (3) | 1 (1) | 6 |
| cavity_off_center | 93 (93) | 40 (40) | 25 (25) | 13 (13) | 13 (13) | 184 |
| dirty_camera | 170 (170) | 17 (17) | 53 (53) | 85 (85) | 4 (4) | 329 |
| dirty_strobe | 0 (0) | 11 (11) | 32 (32) | 0 (0) | 0 (0) | 43 |
| folded_lens | 44 (44) | 3 (3) | 169 (169) | 13 (13) | 8 (8) | 237 |
| lens_off_center | 316 (316) | 76 (76) | 433 (433) | 63 (63) | 69 (69) | 957 |
| low_dose | 26 (26) | 1 (1) | 19 (19) | 96 (96) | 73 (73) | 215 |
| missing_lens | 185 (185) | 5 (5) | 3 (3) | 81 (81) | 51 (51) | 325 |
| missing_primary_package | 1249 (1146) | 201 (189) | 12 (7) | 17 (12) | 72 (72) | 1551 |
| multiple_lenses | 337 (337) | 278 (278) | 672 (672) | 53 (53) | 99 (99) | 1439 |
| package_misalignment | 2 (2) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 2 |
| view_obstructed | 19 (19) | 0 (0) | 0 (0) | 5 (5) | 0 (0) | 24 |
| extraneous_polymer_micron_gate | 26 (26) | 0 (0) | 4 (4) | 3 (3) | 0 (0) | 33 |
| fiber_micron_gate | 77 (77) | 4 (4) | 42 (42) | 13 (13) | 0 (0) | 136 |
| foreign_matter_micron_gate | 95 (95) | 7 (7) | 36 (36) | 33 (33) | 0 (0) | 171 |
| hema_micron_gate | 93 (93) | 0 (0) | 1 (1) | 0 (0) | 0 (0) | 94 |

The distinct **pictures carrying a shape per line** are L24 2,519, L25 617,
L26 881, L27 361, L31 404, which sums to the 4,782 pictures with a shape.

## Codes per picture

Over the 4,782 pictures that carry at least one shape. The counts are the number
of distinct canonical defects on the picture, not the number of shapes, so a
picture with several boxes of one class counts once.

| codes on the picture | pictures |
|---|---|
| 1 | 3371 |
| 2 | 575 |
| 3 | 341 |
| 4 | 210 |
| 5 | 157 |
| 6 | 70 |
| 7 | 36 |
| 8 | 14 |
| 9 | 2 |
| 10 | 3 |
| 11 | 3 |

| statistic | value |
|---|---|
| median | 1 |
| mean | 1.68005 |
| 90th percentile | 4 |
| maximum | 11 |
| pictures with more than one code | 1411 |

A size gate is a flag on its base defect, so counting the four gate tags as their
own codes overstates the defect count. With each gate merged into its base the
histogram tightens to a median of 1, a mean of 1.589293, a 90th percentile of 3
and a maximum of 9, with just 1,407 pictures carrying more than one code. Both
variants are in `codes_per_image.csv`; the raw one is the headline.

## Picture composition by tier

| composition | pictures | of the census |
|---|---|---|
| box only | 453 | 4.3 percent |
| tag only | 3652 | 34.4 percent |
| both tiers | 677 | 6.4 percent |
| no shape at all | 5832 | 54.9 percent |

The no-shape row is 5,832 pictures out of the 10,614 census pictures, and it is
two different things in one number: 1,908 pictures that a file MENTIONS with no
shape (a mention, not a label) and 3,924 pictures that are mentioned NOWHERE and
so have no source of record. That 5,832 equals the 5,832 tag SHAPES in the tier
table by coincidence only; it is a picture count here and a shape count there.
The tag-only tier is large because the Sep-22
project flagged whole jobs with an image-level tag; the box tier is thin.

## The pairs and the triples on one picture

Pairs of canonical defects that share a picture, count of pictures. The pairs
where a gate tag sits on its own base defect are listed apart, because they are
the gate relationship and not a co-occurrence of two defects.

| defect A | defect B | tiers | pictures |
|---|---|---|---|
| lens_off_center | multiple_lenses | tag + tag | 664 |
| bubble | bubble_cluster | box + box | 405 |
| bubble | foreign_matter | box + box | 276 |
| folded_lens | multiple_lenses | tag + tag | 236 |
| bubble | dirty_camera | box + tag | 200 |
| bubble | lens_off_center | box + tag | 185 |
| bubble | multiple_lenses | box + tag | 168 |
| bubble | foreign_matter_micron_gate | box + gate | 167 |
| bubble_cluster | foreign_matter | box + box | 165 |
| folded_lens | lens_off_center | tag + tag | 148 |
| bubble | fiber | box + box | 147 |
| bubble_cluster | dirty_camera | box + tag | 118 |
| bubble | low_dose | box + tag | 117 |

Gate and base, which is the size flag and not a second defect:

| defect | gate | pictures |
|---|---|---|
| foreign_matter | foreign_matter_micron_gate | 171 |
| fiber | fiber_micron_gate | 136 |
| hema_obstruction | hema_micron_gate | 94 |
| extraneous_polymer | extraneous_polymer_micron_gate | 33 |

The three triples worth naming, all of them a folder class plus one more:

| A | B | C | pictures | reading |
|---|---|---|---|---|
| bubble | bubble_cluster | foreign_matter | 164 | three box classes on one Foreign Matter picture |
| folded_lens | lens_off_center | multiple_lenses | 147 | the Multiple Lenses folder plus two annotator tags |
| bubble | lens_off_center | multiple_lenses | 125 | a box class plus a folder tag |

Every pair and triple above a small floor is written to `pairs.csv`, with its
tier for each code.

## The four gate codes

Each gate tag is a production-only tag and a strict subset of its base box code:
every picture that carries the gate also carries its base code, and the base
carries strictly more pictures. This is asserted picture by picture in the
builder and re-derived in the verifier, not assumed.

| gate | base | pictures with the gate | also carry the base | base on | strict subset |
|---|---|---|---|---|---|
| foreign_matter_micron_gate | foreign_matter | 171 | 171 | 331 | yes |
| fiber_micron_gate | fiber | 136 | 136 | 178 | yes |
| extraneous_polymer_micron_gate | extraneous_polymer | 33 | 33 | 144 | yes |
| hema_micron_gate | hema_obstruction | 94 | 94 | 180 | yes |

So they are a size gate on the base defect, not a defect of their own. The
hema_micron_gate base is hema_obstruction, the production reading of `P3_HE`, and
in production every `P3_HE` image carries the tag, so HEMA Obstruction is
unconditional and not size gated.

## Folder-derived labels versus the annotator's own work

The Sep-22 project applied each folder's class to whole jobs, so a picture that
the Sep-22 project owns gets its folder's class as a single label with nothing
else. Which classes are folder-derived, plainly:

- **Folder-derived (22 classes):** bubble, bubble_cluster, bubble_irregular,
  bubble_on_123, bubble_on_edge, bubble_scatter, cavity_off_center, dirty_camera,
  dirty_strobe, extraneous_polymer, fiber, foreign_matter, hema_fragment,
  hema_obstruction, lens_off_center, low_dose, missing_lens,
  missing_primary_package, multiple_lenses, package_misalignment, view_obstructed,
  wet_package. Each names a library folder, and the Sep-22 job for that folder
  labelled the whole job with that class.
- **Not folder-derived (6 classes):** folded_lens and stretched_bubble (neither
  names a folder; folded_lens is a tag the annotator added on Multiple Lenses
  pictures, stretched_bubble is a Sep-22-only box class with no folder) and the
  four micron gates (production-only size flags).

How much of the multi-label story is the folder versus the annotator:

| reading, over the 4,782 pictures with a shape | pictures | share |
|---|---|---|
| carries exactly its folder's class, nothing else | 3323 | 69.5 percent |
| carries its folder's class plus at least one more | 1229 | 25.7 percent |
| does not carry its folder's class at all | 230 | 4.8 percent |

The 1,229 pictures with extras are where the multi-label comes from: the folder
supplies one guaranteed class and the annotator (or a second folder) adds the
rest. The extras are dominated by lens_off_center (689), bubble (551),
bubble_cluster (292), dirty_camera (249) and folded_lens (236). The gate tags
also appear among the extras, but each is a size flag on a base that is already
on the picture, so they are not a second defect. The 230 pictures
that do not carry their folder class are almost all the 177 Clear-folder
pictures plus the folder-versus-source collisions at the HEMA folder, where the
production reading of `P3_HE` is HEMA Obstruction and the Sep-22 reading is HEMA
Fragment.

By source of record, the fraction of pictures whose label set is exactly the
folder's class: Sep-22 2,798 of 3,481, production 286 of 1,045, old library 239 of
256. The Sep-22 project is the folder-derived one; the production files are the
client's own CVAT jobs, which read across folders.

**The old library file carries exactly one box label per picture and 0 tags.**
Its 256 resolved pictures carry 1,264 box shapes over exactly one distinct
canonical box class each, and no tag tier at all. So the older library adds no
multi-label of its own; it is a single box class per picture.

## Acceptance checks

| Acceptance | Where it is proved | Result |
|---|---|---|
| 1. picture counts per defect agree with the per-line and per-folder-group tables, parts sum to whole | builder asserts both sums for every defect and both fields (`parts_sum_to_whole_on_every_defect`, 56 sums); verifier `published_parts_sum_to_whole` | 224 census rows, 0 disagreements |
| 2. box and tag tiers reported separately, totals stated | tier column on every row; `box plus tag shapes = shapes` checked; totals 14,182 box and 5,832 tag | stated |
| 3. library-only classes visible under their own names | bubble_on_123 (13 pictures, 79 shapes) and bubble_on_edge (14, 90) kept as their own rows; verifier `library_only_visible_*` | visible |
| 4. every gate a strict subset of its base, counts shown | builder `gate_subset__*` for all four; verifier `gate_pictures__*`, `gate_is_strict_subset__*` | 171/171, 136/136, 33/33, 94/94 |
| 5. unlabelled or empty picture count stated, mention versus shape distinguished | the 5,832 no-shape sentence above splits mention (1,908) from mentioned-nowhere (3,924); verifier `mentioned_but_shapeless`, `mentioned_nowhere` | stated |
| 6. byte-identical rebuild, second route with check and failure counts | md5 on two consecutive runs (below); `verify_label_census.py` re-derives every headline by a positional second route | 48 checks, 0 failed |

Byte-identical rebuild, md5 on two consecutive runs:

```
label_census.csv     1dbcd56f6732409ad715107d11461572
codes_per_image.csv  ce6087a3ec0f27c00253ceeef9debc8a
pairs.csv            335fc9f5c7a6ecaa597855a402462ebd
```

Builder: 10 checks, 0 failed. Verifier: 48 checks, 0 failed. The verifier also
cross-checks the per-defect counts against ticket 010's `resolution.json` and
recomputes every published pair and triple by a second route.

## Pitfalls

- **A mention is not a label.** 6,690 pictures are mentioned, only 4,782 carry a
  shape. Any count that says "annotated" without saying which is wrong.
- **Key on content md5, never on a path.** The 187 aliased basenames are invisible
  to a winning-path count.
- **Do not pool the two tiers.** The box tier is 14,182 shapes over 1,130
  pictures; the tag tier is 5,832 shapes over 4,329 pictures. They are annotated
  to different depths.
- **A gate is a subset, not a defect.** Counting the gate tags as codes inflates
  the codes-per-picture mean from 1.589293 (merged) to 1.68005 (raw).
- **`hema_obstruction` is `box|tag`.** Read the tier and the shape_kind, never the
  bare canonical name, when splitting the tiers.
- **The XMLs are trusted client CVAT exports.** They were pulled from a private
  blob store and made by the client's own account, so where any XML is read the
  standard library parser is used on purpose and the XXE warning is knowingly
  accepted. These two scripts read only `resolved_labels.csv`, so no XML is
  opened here.
