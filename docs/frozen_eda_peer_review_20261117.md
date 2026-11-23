---
title: Frozen EDA - reconciliation against the independent audit
date: 2026-11-17
type: report
status: active
where: docs/frozen_eda_peer_review_20261117.md
---

# Frozen EDA: reconciliation against the independent audit

> Update, 18 November: the workbook uses 13,673 labelled pictures, one copy per pair, as a working
> basis, not a decision. The audit's 13,674 is the both-copies-excluded base on the workbook's Duplicate
> sensitivity sheet. See `docs/frozen_eda_workbook_20261118.md`.

The independent audit of the frozen annotation reproduces our counts. Every table it publishes matches
ours to the unit once one choice is applied: it removes all eight images that belong to the four
content-duplicate pairs, where we keep both copies and flag them. There are two accounting points to
correct and one population to label; none of them changes a class count.

## 1. The one choice that explains every difference

The audit works on 13,674 images: 13,682 paths, 13,678 distinct contents, then both copies of the four
content-duplicate pairs removed (8 images). We keep 13,682 rows and flag the pairs.

| Figure | Audit (13,674) | Ours (13,682) | Difference | Cause |
|---|---|---|---|---|
| LP images | 9,250 | 9,252 | -2 | 2 of the 8 removed images carry LP tags |
| LP tag instances | 12,248 | 12,252 | -4 | those 2 images carry 2 tags each |
| OOI images | 10,024 | 10,032 | -8 | all 8 removed images carry boxes |
| OOI boxes | 119,197 | 119,292 | -95 | 75 Bubble, 6 Bubble Cluster, 6 HEMA, 4 Fiber, 2 EP, 2 FM |
| Size gate images | 3,736 | 3,742 | -6 | 12 gate tags on 6 of the 8 images |
| LP single-tag | 7,237 | 7,237 | 0 | the 8 removed images all carry two or more classes |
| LP multi-tag | 2,013 | 2,015 | -2 | |
| LP no tag | 4,424 | 4,430 | -6 | |
| Combined single-class | 4,111 | 4,111 | 0 | |
| Combined multi-class | 9,516 | 9,524 | -8 | |
| Prior-only candidates | 174 | 174 | 0 | same rule, same result |
| Clear | 42, plus 5 other unmarked | 42, plus 5 | 0 | same picture set |

Recomputed on the same 13,674 rows, our per-code LP table (all 15 codes, single / two / three) and the
size-band table (four classes, four bands, boxes and images) match the audit cell for cell. The audit's
size bands also confirm the 300 and 647 micron boundaries at 15.3 microns per pixel.

## 2. The duplicate count is 23 short

The audit reports 6,768 shared images. Our manifest gives 6,771 shared by name and 6,767 distinct
contents, so their number is our name match, deduplicated, plus one extra hash match they flag.

What is missing is the 23 pictures that are the same content under a different name. The audit already
accounts for them on the other side: it turns 198 prior-only names into 175 genuinely absent, which is
only possible by removing the same 23. They are simply not added back to the shared count.

| Measure | Count |
|---|---|
| Shared by name | 6,771 |
| Shared by content (6,771 + 23 aliases) | 6,794 |
| Audit's shared figure | 6,768 |
| Frozen-only by content (13,682 - 6,794) | 6,888 |
| Frozen-only implied by the audit (13,682 - 6,768) | 6,914 |

The 26-picture gap is an accounting omission, not a data disagreement: the 23 aliases are already
identified in the audit's own prior-only step.

## 3. "172 changed annotations" is a different population

The audit says 3,597 paths are shared with the 26 earlier production XMLs, 172 of them with changed
annotations. That comparison is against a subset of earlier production exports, not against the library
annotation. Our figure of 3,502 changed label sets is on the 6,771 shared library pictures.

| Comparison | Population | Changed |
|---|---|---|
| Audit, earlier production XMLs | 3,597 paths | 172 (our recount from the local 24 files: 170) |
| Ours, library annotation | 6,771 pictures | 3,502 |

Both can be true. The 172 must not be quoted as the number of frozen pictures whose label changed,
because it covers less than a third of the shared set and a different source.

## 4. What the audit confirms

- 13,682 paths resolve to 13,678 distinct contents: matches our store exactly.
- All image and manifest checksums verify: matches our checksum files.
- 16,306 tag rows and 119,292 box rows match our label exports. Its note that the raw XML has six more
  tag entries closes our open six-row gap: those are the repeated tags on four pictures.
- 147 held and 27 discarded sum to 174: matches our decision file.
- 42 Clear plus 5 other unmarked: matches our split of the 47 unmarked pictures.

## 5. Decision this creates

The working picture count is now one of three, and the lead should pick one:

| Option | Count | Meaning |
|---|---|---|
| Keep the store as is | 13,682 | every named picture, duplicates flagged |
| Keep one of each pair | 13,678 | distinct content, one annotation per picture |
| Audit's choice | 13,674 | both copies of every conflicting pair removed |

Recommendation: quote 13,674 for any label statistic, because the four pairs carry conflicting boxes
and neither copy is trustworthy, and keep 13,682 as the store count because it holds every picture the
annotation names. State both numbers together so the two never get mixed.

## 6. Corrections made to our own docs

The duplicate table previously said 6,911 pictures were never annotated before, which is the by-name
figure and wrongly counts the 23 aliases as new. It now says 6,888 by content, with 6,911 by name shown
alongside, and the old-batch never-annotated figure moves from 3,664 to 3,641.
