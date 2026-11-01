---
title: Picture census and content identity across the three ICube libraries
date: 2026-10-15
type: result
status: active
where: docs/reference/eda_full_picture_census.md
---

# Picture census and content identity across the three ICube libraries

Ticket 007. This record gives one row per file and one row per distinct
picture for the three library folders, plus the production image folder.
The pictures stay on the shared VM. The tables were built from a full md5
of every file, so identity is by content, not by name.

## What the run produced

| Artifact | Rows | What it holds |
|---|---|---|
| `run/eda_full_20261015/file_manifest.csv` | 13,126 | one row per BMP on disk: path, folder, folder group, bytes, md5 |
| `run/eda_full_20261015/picture_table.csv` | 10,614 | one row per distinct picture (keyed on content md5) |
| `run/eda_full_20261015/census.json` | - | headline counts per folder, per folder group, per line |
| `vm/ops/census_hash.py` | - | the read-only script that hashed the files and built the tables |

Both tables are folded into the run directory, which is local only. The
script has two modes. `hash` walks the folders and prints the manifest.
`aggregate` reads the manifest alone and writes the other two files.

## Headline counts

Files on disk: 13,126. Bytes on disk: 65,821,403,332. Every file is
2,448 by 2,048 at 8 bits, and every file is 5,014,582 bytes, so no file is
a resized or re-encoded copy.

| Folder | Files | Bytes | Group |
|---|---|---|---|
| Updated ICube Objects 20260915 | 4,230 | 21,211,681,860 | Updated |
| Updated ICube Categorical Classes 20260915 | 6,384 | 32,013,091,488 | Updated |
| ICube Defects Library | 1,465 | 7,346,362,630 | Library |
| PRODUCTION_20260925/images | 1,047 | 5,250,267,354 | Production (not a library) |

The three library folders hold 12,079 files and 60,571,135,978 bytes. The
Updated group (both Updated folders together) holds 10,614 files. The
Library group (`ICube Defects Library`) holds 1,465 files.

Distinct pictures, keyed on content md5: 10,614. Every one of them sits in
a library folder. The production image folder adds no picture that is not
already in the library, so the distinct-picture count for the libraries
and for the whole disk is the same: 10,614.

## Winning path and copies

The `winning_path` of a picture is its copy in the first library folder
that holds it, in this fixed order: Updated ICube Objects, then Updated
ICube Categorical Classes, then ICube Defects Library. Within one folder
the tiebreak is the path, sorted as text, so the choice is stable.

| Copies per picture | Pictures |
|---|---|
| 1 | 8,940 |
| 2 | 972 |
| 3 | 607 |
| 4 | 54 |
| 5 | 41 |

1,674 distinct pictures have more than one copy. 1,609 distinct pictures
appear in more than one folder. The copy counts sum to 13,126, which
equals the file count, so every file is placed.

## Duplicates accounting

The `duplicates` subfolder under Updated ICube Categorical Classes holds
143 files in 143 distinct contents. All 143 contents also sit somewhere
else in the library. None of the 143 is a picture that the library does
not already hold. This is the open item on the 143 files: they are exact
content copies, not new pictures, so the picture census counts them once.

Cross-folder duplicates are separate from the `duplicates` subfolder. 1,609
distinct pictures have copies in more than one folder. Both facts come
from the same md5 keying.

## Production batch match

The production folder holds 1,047 files in 1,046 distinct contents (two of
its files share one content).

| Match | Count |
|---|---|
| Production files whose content md5 is in the library | 1,047 |
| Production distinct contents whose md5 is in the library | 1,046 |
| Production files that match a library file by basename only (name matches, content does not) | 0 |
| Production files whose content is not in the library | 0 |

The match by content hash covers all 1,047 files. The match by basename
alone is 0, so no production file rests on a name match. All 1,047
basenames also appear among library basenames, and every one of those
name matches is backed by a content match. The production batch adds no
new picture. This settles the claim with content, not with names.

## Per production line

Line comes from the filename only, as the `_L24_` form. Capture date comes
from the leading `YYYYMMDD` in the filename.

| Line | Files | Distinct pictures |
|---|---|---|
| L24 | 5,775 | 4,348 |
| L25 | 1,148 | 972 |
| L26 | 2,056 | 1,503 |
| L27 | 1,860 | 1,637 |
| L31 | 2,287 | 2,154 |

The file counts sum to 13,126 and the picture counts sum to 10,614. No
file lacks a line tag, and no file lacks a capture date. There is nothing
to report as a guess.

## How the numbers were checked

Triple check, as the map requires.

1. A second and independent disk reading. A fresh `find ... -printf` over
   the same four folders, run as its own command with no python, returned
   13,126 files and 65,821,403,332 bytes. The manifest holds 13,126 rows
   and the same byte total, so every file on disk is in the manifest.
2. The distinct-picture count is reproducible from the manifest alone.
   The `aggregate` step reads only `file_manifest.csv`. A count of the
   unique md5 values in that one file gives 10,614, which equals the
   picture-table row count.
3. Byte-identical rerun at a different hash seed. The `aggregate` step ran
   three times, once with `PYTHONHASHSEED=0`, once with
   `PYTHONHASHSEED=987654`, and once with the default. All three
   `picture_table.csv` files share the md5
   `a03ddeead53bae370c17bd8ea15c0df0`, and all three `census.json` files
   share `a99c8724350194c73a7511591dbdffea`. Every collection is written
   in an explicit sort order, and the winning-path tiebreak is the path
   name, so no set or dict order can leak into the output.
4. The production match is stated two ways, by content hash and by
   basename, in the table above.

Artifact hashes for this run:

| Artifact | md5 |
|---|---|
| file_manifest.csv | 97ab4eded84bba28a1c113949d08ce7c |
| picture_table.csv | a03ddeead53bae370c17bd8ea15c0df0 |
| census.json | a99c8724350194c73a7511591dbdffea |

## Method

The script reads only. It md5s each file in 1 MiB chunks, so memory stays
flat over the 65 GB set. It reads the filename for line and date, and it
never decodes the pixels. The manifest is sorted by folder priority and
path. The picture table is sorted by md5. No timestamp is written into any
output, so a rerun is byte-identical.
