---
title: Draft-2 EDA workbooks, status
date: 2026-10-28
type: reference
status: active
where: reports/draft2_eda_20261023/README.md
---

# Draft-2 EDA workbooks, status

Read this before opening any workbook in this folder. The annotation was re-exported by the
client on 2026-10-26 and absorbed on 2026-10-28, so the workbooks here are **stale**. They are
kept because they are the record of what was sent, not because their numbers still hold.

## Current state

| File | Status |
|---|---|
| `EDA_Draft2_20261026.xlsx` | **Stale.** Built on `run/eda_full_20261015`. Nine sheets, verified at the time; superseded by the 2026-10-26 annotation re-export. |
| `Tag_Combinations_Answer_20261026.xlsx` | **Stale.** The reply workbook sent to the client, same basis. Its counts are what the client has seen; they are not the current counts. |
| `EDA_Draft2_20261023.xlsx`, `EDA_Draft2_rev3_20261023.xlsx` | Superseded by the 20261026 pair. Kept for history. |
| `EDA_Draft2_20261023_rev2_archive.xlsx`, `draft2_eda_20261023.xlsx` | Earlier drafts. History only. |
| `*_spec.json` | The cell-by-cell spec each workbook was generated from, so a rebuild is reproducible. |

## What changed under them

The revision moved 133 of the 1,047 pictures in the seven revised files and added seventeen
new files. Counts that no longer match the workbook: Foreign Matter 326 pictures with a gate of
166, Fiber 179 with a gate of 137, Extraneous Polymer gate 34, Bubble Cluster 427, Bubble 862
with 11,052 objects. The current annotation of record is
`run/eda_full_20261028/resolved_labels.csv`.

## What happens next

Both workbooks will be regenerated, not patched: first on the 2026-10-28 annotation, then again
once the twenty-four-file EDA is done, because the new pictures will move the distribution a
second time. Each has a builder and a verifier in `experiments/multilabel_edge/`
(`build_eda_draft2_v5.py` with `verify_eda_v5.py`, `build_answer_v2.py` with
`verify_answer_v2.py`); the verifier recomputes from the annotation and catches a tampered
cell, so a regenerated workbook is checked before it goes anywhere.

Until that rebuild lands, quote numbers from the annotation or from the reference docs, never
from these files.
