---
title: Split v8 (70/15/15) sharing package
date: 2026-11-03
type: reference
status: active
where: handover/split_20261103_v8/README.md
---

# Split v8, 70/15/15, for sharing

One three-way split of the lens-presentation population, built 2026-11-03. This folder is
self-contained: the split file, the table it was built from, and the label table with the
split already joined.

## Files

| File | What it is |
|---|---|
| `split_70_15_15.csv` | one row per picture: `picture_md5`, `group_id`, `split` |
| `meta.json` | counts, per-class counts, the recipe, and the md5 of the input record |
| `labels_b.csv` | the variant b label table, 7,470 rows, with `split` already in it |
| `requirements-lock.txt` | exact package versions from the machine that ran it |
| `environment.txt` | Python, torch, CUDA and GPU versions |

## If you only need the split

`split_70_15_15.csv` is keyed on `picture_md5`, the md5 of the image file content. Join it to
your own picture table on that column. It covers 7,470 pictures:

| Split | Pictures | Share |
|---|---|---|
| train | 5,239 | 70.1% |
| val | 1,110 | 14.9% |
| test | 1,121 | 15.0% |

Use `val` for one thing only, choosing a decision threshold per class. Read `test` once, at
the end. Anything else is selection on the test set, which is the problem this split exists
to remove.

## If you want to train straight away

`labels_b.csv` already has the split joined, so you do not need to join anything:

- `md5`, `image_path` (relative to the data root), `split`
- the twelve lens-presentation columns, then `object_present`
- `has_lp`, `has_object`, `is_clear` (used for the subset reporting)

Filter on `split` and train on `train`. Variant a (no object column, 6,747 rows) can be built
from the same split with the script named below.

## Checksums

| File | md5 |
|---|---|
| `split_70_15_15.csv` | `1a71d66d2de384cf47a3fcf7d9115baa` |
| `labels_b.csv` | `764a412597aad359f644eb1414d31cda` |
| `meta.json` | see `meta.json` itself |

Built from this annotation record, and only this one:

| Input | md5 |
|---|---|
| `run/eda_full_20261029/resolved_labels.csv` | `f61ea0b90df095ebe52d1332f8bfdb8a` |
| `run/eda_full_20261029/picture_table.csv` | `a03ddeead53bae370c17bd8ea15c0df0` |

If your annotation copy has a different md5, the split will not line up with your picture
table. Stop and ask for the matching record rather than guessing.

## How it was built

Iterative stratification (Sechidis 2011), three-way, content-md5 groups, deterministic, so a
rebuild is byte-identical. The counting rules are the frozen ones of 2026-10-26: label space
is the Draft 2 codes plus Clear, legacy names are excluded, and the four gated object classes
are positive on the micron-gate tag only. 62 legacy-only and 85 debris-without-gate pictures
are outside the split because they carry no positive to train on.

The builder and its verifier are `build_split_v8.py` and `verify_split_v8.py` in
`experiments/multilabel_edge/`.

## Two things to know before quoting per-class numbers

- Folded Lens got 9.9% of its pictures in val rather than 15%, so its threshold rests on 33
  val positives. Its val curve is flat from 0.35 to 0.45 and falls sharply above 0.50.
- Dirty Strobe, Bubble Scatter and Package Misalignment have too few pictures anywhere to
  tune a threshold. Keep 0.5 for them and say they are untuned.

## Environment

While you run on the shared A100, the environment is already the one the run used: call
`/home/pranayp/fmd-analysis/.venv/bin/python` directly and install nothing. That interpreter is
read-only for the shared account, so a stray `pip install` cannot change it. Copy any code you
need to edit into your own home and write outputs there.

The lock file matters the day you move to a personal box. `requirements.txt` alone is not enough
to reproduce the numbers, because it does not pin torch, torchvision, numpy, the CUDA build or
the Python version, and pip resolves to whatever is current that day. Install from
`requirements-lock.txt` on Python 3.12 and expect the cu126 wheel. Details in `environment.txt`.
