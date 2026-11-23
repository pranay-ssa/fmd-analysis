# Frozen dataset store

The single home for the frozen annotation set of 2026-11-17. Every picture named in the frozen
annotation is here, under its original name, with a manifest that is the join key for every downstream
step.

Built 2026-11-17. Store owner on the box: the account that ran the build. Read-only in practice:
nothing writes into `images/`.

## What is in it

| Measure | Count |
|---|---|
| Pictures in the store | 13,682 |
| With at least one tag or box | 13,635 |
| With no mark at all | 47 |
| From the known batch (`PRODUCTION-20260925`) | 10,435 |
| From the new line batch (`PRODUCTION-20261031`) | 3,247 |
| Already covered by the previous annotation | 6,771 |
| Old batch, on disk but never annotated before | 3,664 |
| New upload, never annotated before | 3,247 |
| Clear-folder pictures | 2,333 |
| - of those, still with no mark | 42 |
| Content duplicates inside the set | 4 pairs (8 rows) |

Labels: 16,306 tag rows (15 LP codes plus 4 size gates) and 119,292 box rows (8 object classes).

Total size 64 GB.

## Layout

```
frozen_data_20261117/
  README.md                     this file
  manifest.csv                  one row per picture, the join key
  addback_candidates.csv        175 pictures in the earlier annotation but not in frozen; NOT in images/
  images/                       13,682 files, original names
  annotations/
    xml/                        92 CVAT exports, as received
    client_supplied/            7 files produced by the client (counts, converted table, model output, notebook, workbook)
  labels/
    tags.csv                    picture_key, basename, code, kind (tag or gate), instances
    boxes.csv                   picture_key, basename, code, xtl, ytl, xbr, ybr, rotation
  audit/                        build and verification records, not data
    build_report.json           counts from the image consolidation
    missing_from_copy.csv       empty: nothing was missing
    pull_report.json            new-batch pull counts
    pull_verification.csv       per-file hash record for the pull
    redundant_sources.csv       every file outside the store whose content is already here
    redundant_sources.json      summary of the above
  checksums/
    images.sha256               13,682 lines, sha256 of every file
    manifest.sha256             sha256 of manifest.csv
```

`audit/` holds records only. Nothing in it is needed to read the data, and it can be removed without
affecting a training run. `checksums/` holds the two files a verifier needs.

## Manifest columns

| Column | Meaning |
|---|---|
| `picture_key` | md5 of the picture content. The identity to join on |
| `basename` | File name in `images/`. Original, never changed |
| `bytes` | File size |
| `source_batch` | `PRODUCTION-20260925` or `PRODUCTION-20261031` |
| `source_folder` | Library folder of the picture (for the old batch) or the upload folder |
| `capture_date` | From the picture table, or the file name prefix for the new batch |
| `job_id` | CVAT job the picture was annotated in |
| `has_marks` | `yes` if the picture carries a tag or a box |
| `n_tags`, `tag_codes` | LP presentation tags only |
| `n_boxes`, `box_codes` | Object boxes, one class per distinct code |
| `gate_codes` | The four size flags, separately from the tags |
| `is_clear_source` | `yes` if the picture's library folder is Clear |
| `prev_annotation_status` | `duplicate`, `new_old_batch`, `new_upload` |
| `in_previous_annotation` | `yes` for the 6,771 pictures the earlier record also covered |
| `content_duplicate`, `duplicate_of` | Set for the 4 pairs below |

## Rules

- `images/` is immutable. Nothing writes into it. Derived files go elsewhere.
- Consumers join on `picture_key`, or on `basename` after checking it against the manifest. A path is
  never built from a class name.
- A class folder layout is not used and must not be added. Most pictures carry more than one class.
- Splits are assignment files, never copies of images. Any split built before this store is stale for
  the 3,502 pictures whose frozen label set differs from the earlier annotation.
- New batches are appended with a new `source_batch` value and a new annotation export hash.

## Verification

- Every one of the 13,682 files was compared with its manifest md5 after copying: 13,682 of 13,682
  match. 0 missing, 0 extra, 0 non-BMP.
- `images.sha256` was written from the same read that verified the copy, and spot-checked.
- The old batch was verified against the storage account by content hash before the restructure:
  10,438 of 10,438 blobs matched a local file, 0 missing, 0 mismatch.
- The new batch was downloaded and verified against the blob's Content-MD5: 3,247 of 3,247. An
  independent second pass re-hashed all 3,247: 0 size and 0 hash mismatches.
- The 92 annotation files are byte-identical to the export (99 of 99 files, including the 7 client
  files).

## Known issues

- **Four content-duplicate pairs.** The same picture appears twice under two names in the same job:
  `20241102_004906_L24_C5_9471` and its `_0.6629` copy, `20241109_174228_L24_C4_9649` and `_0.9824`,
  `20241110_024940_L24_C13_9997` and `_0.6242`, and the `20260918` pair. One pair has identical labels;
  three differ by a few boxes. Both rows are kept because both are annotated. Never split a pair across
  train and test. Decide later whether to keep one.
- **47 pictures with no mark.** 42 are Clear-folder pictures, 5 are unfinished rows. They are in
  `images/` and flagged by `has_marks=no`.
- **175 add-backs are not here.** They exist in the earlier annotation but not in frozen. The list is
  in `addback_candidates.csv`, waiting for the lead. Do not add them to a training set yet.
- **Two uploads are not here.** `PRODUCTION_20261106` (3,500) and `PRODUCTION_20261113` (4,064) are in
  storage and carry no annotation in this export. They are out of scope until the lead rules.
- **Job 4522010 is missing** from the export although the client's own table covers it.
- **`F2_FOV` is the code in the data**; the guide's `P2_FOV` never appears. Class names follow the
  crosswalk, and the Draft 2 variants are recorded in the walkthrough.

## Where the reasoning lives

`docs/frozen_dataset_eda_20261117.md` (result) and
`docs/frozen_dataset_eda_walkthrough_20261117.md` (study guide). Build scripts live in the repository
under `vm/ops/` and `experiments/annotations/`.
