---
title: "Ticket 007: picture census and content identity"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/007-picture-census.md
---

# 007: Picture census and content identity

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: nothing.

## Resolution (2026-10-15)

Done. Record: `docs/reference/eda_full_picture_census.md`.

- 13,126 files hashed, 65,821,403,332 bytes, all 2,448 x 2,048 at 5,014,582 bytes.
- Three library folders: 12,079 files. Updated group 10,614 files, old library
  1,465 files.
- **10,614 distinct pictures in the whole universe.** The Updated group holds
  10,437 distinct; the old library holds 1,402 distinct, of which **177 are in
  neither Updated folder**, which independently reproduces the published
  2026-09-17 figure.
- **The 1,047 production pictures are all present in the library folders**, and
  all 1,047 match by CONTENT HASH. Zero rest on a basename match alone. The
  production image folder adds no picture.
- The production batch holds 1,046 distinct contents, not 1,047: two files share
  one content, `20241102_004906_L24_C5_9471.bmp` and
  `20241102_004906_L24_C5_9471_0.6629.bmp`. This corrects the 2026-10-13
  statement of "1047 distinct images for 1047 image tags".
- `duplicates/` subfolder: 143 files, 143 distinct contents, all 143 repeat a
  picture already in the library, 0 unique. The open item on those files is
  closed.
- Per-line distinct pictures: L24 4,348, L25 972, L26 1,503, L27 1,637,
  L31 2,154. No file lacks a line tag or a capture date.
- Checked three ways: a second independent disk reading agrees on file count and
  byte total; the distinct count is reproducible from the manifest alone; and the
  aggregate step is byte-identical under three different `PYTHONHASHSEED` values.

Artifact md5: `file_manifest.csv` `97ab4eded84bba28a1c113949d08ce7c`,
`picture_table.csv` `a03ddeead53bae370c17bd8ea15c0df0`, `census.json`
`a99c8724350194c73a7511591dbdffea`.

## Question

How many distinct pictures are in the three library folders, and what is each
one's winning path, line, capture date and copies?

## Why it is first

Every count in every later ticket hangs off this table. It also settles, with
evidence rather than a name match, the claim that all 1,047 production pictures
already sit in the library folders.

## Deliverable

A run directory `run/eda_full_20261015/` holding:

- `picture_table.csv`, one row per distinct picture: content hash, winning path,
  every folder that holds a copy, byte size, production line from the filename,
  capture date from the filename, and whether the production tree also holds it.
- `file_manifest.csv`, one row per file on disk: path, bytes, md5, folder group.
- `census.json`, the headline counts per folder, per folder group and per line.

## Method

Stream over the three folders on the VM, md5 every file, and key the table on
the content hash. Read the filenames for line and date, never the pixel data.

## Acceptance

1. Every file on disk appears in the manifest, and the byte total matches a
   fresh disk reading.
2. The distinct-picture count is reproducible from the manifest alone.
3. The 1,047 production pictures are matched to library pictures by content hash,
   not only by basename, and the result is stated either way.
4. The `duplicates` subfolder and any cross-directory duplicate list are accounted
   for explicitly, since a decision was owed on the 143 files.
5. A rerun at a different `PYTHONHASHSEED` is byte-identical.
