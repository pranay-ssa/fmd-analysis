---
title: "Ticket 010: label resolution and the disagreement table"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/010-label-resolution.md
---

# 010: Label resolution and the disagreement table

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 007, 009.

## Resolution (2026-10-15)

Done. Record: `docs/reference/eda_full_label_resolution.md`.

- Every picture the files list resolves to exactly ONE source of record: level 1
  (the 7 production files) 1,046, level 2 (the Sep-22 export) 5,387, level 3 (the
  old library) 257. No picture carries labels from two sources, asserted rather
  than assumed.
- **The distinction that matters downstream:** 6,690 is a MENTION count. Only
  **4,782** of those pictures carry at least one shape; 1,908 resolved to a file
  that lists them with no label, and 5,832 census pictures are not mentioned at
  all. The builder's first summary called all 6,690 "annotated", which was
  corrected in the record before anything downstream read it.
- Surviving shapes: 20,014, of which 14,182 are boxes and 5,832 are tags.
- Disagreement table: 886 rows. The Sep-22 file mentions 709 pictures a higher
  file won (594 of them with real labels); the old library file mentions 177, all
  with real labels. The earlier basename estimates of 708 and 116 are reconciled:
  the gaps come from renamed duplicates invisible to basename matching, and from
  the 708 counting 115 shape-less mentions.
- The 170-picture delta against the 2026-10-13 production files was re-derived
  read-only from the VM and agreed exactly: 170 of 1,047 pictures changed, all
  tag-only, +118 `P3_FM_MICRON_THRESHOLD`, +51 `P3_FIB_MICRON_THRESHOLD`, +1
  `P3_EP_MICRON_THRESHOLD`, -1 `P1_ML`, no geometry touched.
- Builder 14 checks, verifier 35 checks, 0 failed, and a byte-identical rebuild.

**Carried forward.** 187 basenames hold a content that also exists under a second
name, so a count done by path rather than by content hash will undercount. Tickets
011, 012 and 015 must key on content md5.

## Question

Under the priority rule, what are the final labels for every picture, and where
exactly do the older sources disagree with the winner?

## The rule, fixed in the grill

Priority order is: the 7 CVAT production files (`annotations_4521940` to
`4521946`), then `Updated Annotations 20260922.xml`, then `annotations.xml`.
The highest-priority file that mentions a picture supplies all of that picture's
labels. Lower-priority files are silent for it. Every picture therefore has
exactly one source of record.

## Deliverable

- `run/eda_full_20261015/resolved_labels.csv`: one row per picture per shape,
  carrying the source file, the code, the canonical defect, the kind and the
  geometry where there is any.
- `run/eda_full_20261015/disagreement.csv`: every picture where a lower-priority
  file holds labels for a picture the higher file won, with both label sets side
  by side. The known size of this is 708 pictures from the Sep-22 file and 116
  from the old library file, and any difference from those numbers is a finding.
- `run/eda_full_20261015/resolution.json`: counts per source file, per priority
  level, and per canonical defect.

## Acceptance

1. Every picture in the census resolves to exactly one source, and the counts add
   up to the census total.
2. No picture carries labels from two sources.
3. The disagreement table names all 708 and all 116; a mismatch is investigated,
   not rounded away.
4. The 170 pictures whose production labels changed between 2026-10-13 and now
   resolve on the new files, proved by a spot check on the added gate tags.
5. A rerun is byte-identical.
