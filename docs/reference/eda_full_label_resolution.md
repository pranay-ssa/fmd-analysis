---
title: Label resolution and the disagreement table
date: 2026-10-15
type: result
status: active
where: docs/reference/eda_full_label_resolution.md
---

# Label resolution and the disagreement table

> **Current run 2026-10-28.** The client re-exported the production annotation, so the rule
> below now runs over the revised seven files into `run/eda_full_20261028/`
> (`EDA_RUN_DIR=run/eda_full_20261028`). The rule itself is unchanged. The 2026-10-15 run
> stays on disk for provenance, and every figure in this document describes it.

Ticket 010 of the full-coverage EDA map. Every picture in the census is resolved
to exactly one source of record under the winner-takes-all rule, and the pictures
where a lower-priority file still holds labels are listed side by side.

## The rule

Priority order, fixed with the user in the grill:

1. the 7 CVAT production files, `annotations_4521940.xml` to `annotations_4521946.xml`;
2. `Updated Annotations 20260922.xml` (the Sep-22 project);
3. `annotations.xml` (the old ICube Defects Library, project 2).

The highest-priority file that mentions a picture supplies all of that picture's
labels. Every lower-priority file is silent for it. No picture carries labels
from two sources.

An annotation image is resolved to a picture by its basename, looked up in the
census built from `run/eda_full_20261015/file_manifest.csv` (one row per file on
disk, keyed on content md5). Every basename in the whole census maps to exactly
one md5, so the lookup is deterministic, and every annotation image in all 9
files resolves. The reason the census is the key, and not `picture_table.csv`'s
`winning_path` column alone, is the next section.

## The resolution

| Source of record | Priority level | Pictures won |
|---|---|---|
| `annotations_4521940.xml` | 1 | 149 |
| `annotations_4521941.xml` | 1 | 150 |
| `annotations_4521942.xml` | 1 | 147 |
| `annotations_4521943.xml` | 1 | 150 |
| `annotations_4521944.xml` | 1 | 150 |
| `annotations_4521945.xml` | 1 | 150 |
| `annotations_4521946.xml` | 1 | 150 |
| `Updated Annotations 20260922.xml` | 2 | 5387 |
| `annotations.xml` | 3 | 257 |

- Census: 10,614 distinct pictures (`run/eda_full_20261015/picture_table.csv`).
- Pictures **listed** in at least one of the 9 files, so resolved to one source of
  record: **6,690**. This is a MENTION count, not an annotated count.
- Of those, pictures that actually **carry at least one shape**: **4,782**. The
  other **1,908** resolved to a source that lists them with no label at all
  (1,906 of them to the Sep-22 file, and 1 each to the production files and the old
  library file). Every count downstream must say "mentioned" or "carries a shape",
  and must never say "annotated" without saying which.
- Pictures with no mention in any file, so no source of record and no label:
  **5,832** (10,614 less 4,782).
- The surviving shapes number **20,014**: 14,182 boxes and 5,832 tags.
- Wins by level: level 1 = 1,046, level 2 = 5,387, level 3 = 257. The per-file
  wins sum to 6,690, the resolved total. Pictures with a shape by level: level 1 =
  1,045, level 2 = 3,481, level 3 = 256.
- **Alias caveat.** 187 basenames hold a content that also exists under a second
  file name, so they are invisible to a winning-path lookup. The census key for this
  ticket is the manifest basename, not the winning path. Any later ticket that
  counts by path rather than by content hash will undercount by up to those 187.

The 7 production jobs are disjoint (149 + 150 + 147 + 150 + 150 + 150 + 150 =
1,046) and cover all 1,046 distinct production pictures, so no picture is won by
two production files.

`run/eda_full_20261015/resolved_labels.csv` is one row per surviving shape:
picture md5, winning path, source file, source group, priority level, code,
canonical id, shape kind, is-size-gate, and the box geometry (xtl, ytl, xbr, ybr,
rotation) where the shape is a box. 20,014 rows.

`run/eda_full_20261015/resolution.json` carries counts per source file, per
priority level, per canonical defect, the win counts, and the checks.

## The disagreement table

`run/eda_full_20261015/disagreement.csv` has one row per (picture, losing file)
pair where a lower-priority file also mentions a picture a higher file won. Both
label sets are side by side in the row (`winning_labels` and `lower_labels`, each
a sorted list of `CODE:kind` tokens). 886 rows.

| Losing file | Level | Pictures mentioned | Of which carry at least one label |
|---|---|---|---|
| `Updated Annotations 20260922.xml` | 2 | 709 | 594 |
| `annotations.xml` | 3 | 177 | 177 |

A picture that a losing file mentions but carries no shape for holds no labels,
so it is a mention and not a lost label. The Sep-22 file annotates 2,021 of its
6,097 images as clear (no shape). All 177 old-library mentions carry at least one
box.

### Reconciliation of the 708 and 116 estimates

The map's decision 5 and the ticket quoted 708 Sep-22 pictures and 116 old-library
pictures. Those were basename-based: they matched the basename of each annotation
image against the set of basenames appearing in the 7 production annotation files.
That estimate is reproduced exactly here (708 and 116), but it is not the real
number, for three reasons.

1. Renamed duplicates. The same content is saved under more than one file name
   across folders, so a picture can be in the production batch under a name that
   the annotation basename does not match. The census has 187 basenames that
   `picture_table.csv`'s `winning_path` column alone cannot see.
   - Sep-22: content hash adds 1 picture. The Sep-22 and library copies of the
     HEMA Obstruction image `20241104_010614_L24_C7_9784.bmp` are stored in the
     production folder as `20241104_010614_L24_C7_9784_0.5637.bmp` (a score suffix
     was appended). Basename matching missed it. Real Sep-22 pictures that lost to
     production: 709, not 708.
   - Old library: content hash adds 15 pictures, for example
     `20241106_185031_L24_C15_9521.bmp`, `20241107_035652_L24_C13_9774.bmp`,
     `20241109_083707_L24_C11_9765.bmp`. Real old-library pictures that lost to
     production: 131, not 116.
2. The 116 ignores the Sep-22 winner. An old-library picture loses its labels when
   either a production file or the Sep-22 file wins it. 46 old-library pictures
   lose to Sep-22 and were not in the 116 framing at all.
3. The 708 counted mentions, not labels. 115 of the 709 Sep-22 lost pictures carry
   no shape in the Sep-22 file, so they have no label to lose; 594 do.

Real numbers: 709 Sep-22 pictures lost (594 with labels), and 177 old-library
pictures lost (131 to production, 46 to Sep-22; all 177 carry labels).

## The 2026-10-13 to 2026-10-15 delta

The 7 production files were replaced by the client on 2026-10-15. The
2026-10-13 versions were pulled read-only from the shared VM
(`/home/amd100-user/FMD_Data_26082026/fmd_temp_images/PRODUCTION_20260925/annotations/`)
into a local scratch directory and compared shape by shape with the current files.

Re-derived result, in agreement with the earlier independent check:

- 170 of the 1,047 production pictures changed.
- Added tags: `P3_FM_MICRON_THRESHOLD` on 118 pictures, `P3_FIB_MICRON_THRESHOLD`
  on 51, `P3_EP_MICRON_THRESHOLD` on 1.
- Removed tags: `P1_ML` on 1 picture.
- Only tags changed. No box geometry differs between the two versions.

The resolution reads the current (2026-10-15) files, so the added micron gate tags
are in `resolved_labels.csv` as production shapes at priority level 1.

## Acceptance checks

| Acceptance | Where it is proved | Result |
|---|---|---|
| 1. every annotated picture resolves to exactly one source, counts sum | builder check `per_source_wins_sum_to_resolved_total`, `every_picture_has_at_least_one_mention`; verifier `resolved_pictures`, `wins_by_level`, `wins_by_file` | 6,690 = 1,046 + 5,387 + 257 |
| 2. no picture carries labels from two sources | builder `no_picture_has_two_winning_files`, `resolved_rows_single_source_per_picture`, `no_lower_priority_shape_survives`; verifier `no_picture_two_winning_files`, `csv_single_source_per_picture` | 0 violations |
| 3. every annotation image resolves, unresolved counted and named | builder `annotations_resolve_completely`; verifier `unresolved_annotation_images` | 0 unresolved, listed empty |
| 4. disagreement table names the real numbers, 708 and 116 explained | builder `disagreement.by_lower_file`; verifier `sep22_mentions`, `sep22_with_labels`, `old_mentions`, `old_with_labels`, `basename_estimate_gap_sep22`, `basename_estimate_gap_old` | 709 / 594 and 177 (131 + 46) |
| 5. 170-picture delta re-derived on the newer tags | verifier `delta_changed_pictures`, `delta_added_tags`, `delta_removed_tags`, `delta_only_tags_changed`, `delta_geometry_untouched` | 170, agrees |
| 6. byte-identical rebuild and a second route | verifier reruns the counts with `iterparse` and diffs every headline and the hand-typed table | 35 checks, 0 failed |

Builder: 14 checks, 0 failed. Verifier: 35 checks, 0 failed, 0 skipped.

Byte-identical rebuild, md5 on two consecutive runs:

```
resolved_labels.csv  605aaaf75f450a0e8d5d4e94a88e58ee
disagreement.csv     bbc50968126211979d30d6a13fbf3479
resolution.json      362f22bb9c41550a576133798544b592
```

## How to run

```bash
./.venv/Scripts/python.exe experiments/eda_full/resolve_labels.py
./.venv/Scripts/python.exe experiments/eda_full/verify_resolution.py
```

The verifier reads the 2026-10-13 production files from `OLD_PROD_DIR` (default a
local scratch path) for the delta check. When that directory is absent the delta
checks are skipped, not failed.

## Pitfalls

- **`picture_table.csv`'s `winning_path` is one basename per picture, not all of
  them.** Resolve annotation images against the full census
  (`file_manifest.csv`), not against the winning path alone, or 187 aliased
  basenames are invisible. Every basename still maps to exactly one md5, so this
  is safe.
- **A `defined_only` crosswalk cell is not an instance.** `P2_BSC` in production,
  and `P1_PPM` and `P2_FOV` in Sep-22, are defined but carried by no shape, and
  are never counted here.
- **HEMA Obstruction is a tag in Sep-22 and a box in production.** Use
  `kind_updated_20260922` and `kind_production_20260925` for any box-versus-tag
  split; the union `kind` reads `box|tag`.
- **A mention is not a label.** A losing file can list a picture with no shape
  (a clear image). It is in `disagreement.csv` with `lower_has_labels=no`, and it
  has no label to lose.
- **The XMLs are trusted client exports.** They were pulled from a private blob
  store and made by the client's own account, so the standard library parser is
  used on purpose and the XXE warning is knowingly accepted. This is a deliberate
  choice on a trusted input.
