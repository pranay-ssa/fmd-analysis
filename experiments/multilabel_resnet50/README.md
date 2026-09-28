---
title: experiments/multilabel_resnet50/ - multi-label LP classification with ResNet50
date: 2026-09-23
type: experiment
status: scaffold
where: experiments/multilabel_resnet50/README.md
---

# multilabel_resnet50: multi-label ResNet50 on the 5 LP tags

Scaffold for a multi-label image classifier over the 5 lens-presentation (LP) tags:
`P1_COC`, `P1_FL`, `P1_ML`, `P1_MPP`, `P1_NL`. Design, registry entry and this README
were written before any pipeline code was executed. No training run has been launched.

Design details live in `DESIGN.md`. The machine-readable plan lives in `registry.json`
(status `planned` rows only).

## Files

| File | What it does |
|---|---|
| `DESIGN.md` | ideation and design doc (question, labels, split, recipe, risks) |
| `registry.json` | experiment registry entry, config frozen before running |
| `build_labels.py` | reads the CVAT XML, writes `labels.csv` (multi-hot + md5 + flags) |
| `make_splits.py` | group-aware 70/15/15 splitter, writes `splits/seed42.csv` |
| `make_split_variants.py` | builds the three candidate splits over the 3,377 LP rows: `splits/variant_70_15_15.csv`, `variant_70_30.csv`, `variant_80_20.csv` (+ `.meta.json` each) |
| `make_lead_choice.py` | builds the two candidate dataframes (`labels_178_multitag.csv`, `labels_3377_lp_tagged.csv`) and `label_matrix_options.xlsx` |
| `lp_dataframe_80_20.ipynb` | the dataframe + 80:20 stratified split notebook, sent for review before training |
| `train.py` | ResNet50 trainer, BCEWithLogitsLoss, early stop on macro AUPRC |
| `labels.csv` | generated label matrix (do not edit by hand) |
| `dataframe_3377_lp_labels.csv` | generated deliverable: `image_path` + the 5 LP columns only, 3,377 rows |
| `final_80_20_dataframe.csv` | generated deliverable: the same rows plus `split` / `split_named` |
| `label_matrix_options.xlsx` | 178-row vs 3,377-row comparison workbook for the lead |
| `splits/seed42.csv` | generated split assignment over all 6,097 rows (do not edit by hand) |

## Run order (from the repo root)

```bash
python experiments/multilabel_resnet50/build_labels.py
python experiments/multilabel_resnet50/make_splits.py
python experiments/multilabel_resnet50/train.py \
  --image-root <image root> --epochs 30 --batch 32
```

Paths to inputs (`data/Updated Annotations 20260922.xml`,
`run/line_eda/20260916/image_md5_records.csv`) are resolved relative to the repo root,
so the commands work from anywhere inside the repo. Outputs land inside this folder.

## Labels

`labels.csv` columns: `image_path`, `P1_COC`, `P1_FL`, `P1_ML`, `P1_MPP`, `P1_NL`
(binary, 0/1), `md5`, `task_id`, `task_name`, `n_tags`, `has_any_tag`,
`negatives_reliable`.

- 6,097 rows, one per image element in the export. All task images are included.
- Duplicate tags on the same image are de-duplicated (125 images carry `P1_MPP` twice),
  so each column is set membership, never a count.
- Grouping for the split is the `md5` column. Rows whose file is not in the md5 record
  fall back to a path-based group key; the builder prints how many that was.

## Negatives caveat (important)

`negatives_reliable` is `True` only when the image carries at least one tag (a human
looked at it) or it belongs to a fully finished task folder (every image in the task
annotated). The Low Dose task is 76 of 1,952 done, so untagged Low Dose images are
**unreliable negatives** and must not be read as confirmed absences. The same holds for
the partially annotated Extraneous Polymer task. All 6,097 images are kept in the data;
the flag is the switch. Train with `--reliable-only` to exclude unreliable rows, and
report headline metrics on the reliable subset too.

## Split

- `splits/seed42.csv`, seed 42, 70/15/15, one row per image with `md5`, `split` and the
  flag columns.
- Groups are content md5 values, so the 34 pictures stored in two folders and the 27
  renamed twins can never straddle two splits.
- Stratifier: iterative multi-label stratification over groups when `iterstrat` is
  installed, otherwise the documented fallback (label-powerset pattern with
  group-aware assignment). The builder prints which one ran. Both are seeded and
  deterministic; the file on disk is the source of truth for every run.

## Training

`train.py` is code-complete: torchvision ResNet50, 224 x 224, `BCEWithLogitsLoss`,
configurable `--epochs` and `--batch`, AMP on CUDA, early stopping on macro AUPRC,
best checkpoint plus history written to `--out`. Useful flags: `--reliable-only`,
`--pos-weight`, `--smoke` (2 optimizer steps over a handful of real images),
`--smoke-synthetic` (2 steps on random tensors, no image files needed).

Image pixels are not stored in this repo. Supply the drop folder root with
`--image-root` or the `FMD_IMAGE_ROOT` environment variable; image paths inside
`labels.csv` are relative to that root. See `docs/reference/vm_and_datasets.md` for
where the bulk data lives.

## Decisions confirmed 2026-09-24

Settled in chat, superseding the open question of row scope:

- **Row set: all 3,377 LP-tagged images**, not the 178 multi-tag subset. The 178 are a
  property of the row set, not the row set itself.
- **Columns: the 5 LP tags only.** Object-of-Interest tags stay out; they belong to the
  YOLO line. Provenance columns (`md5`, `task_id`, `task_name`, `n_tags`, `has_any_tag`,
  `negatives_reliable`) are dropped from the delivered dataframe. The 0s in the label
  columns stay: they are the labels, and `pos_weight` is computed from them.
- **Split: 80:20, stratified.** `splits/variant_80_20.csv`, seed 42, iterative multi-label
  stratification, 0 group leaks, worst per-class drift 1.73%. The 20% test share is exact
  in `split_named`; inside the 80%, 15% of the total is held out as a validation set so
  early stopping never touches the test set.
- Two earlier candidates (70/15/15 and 70/30) remain on disk unselected.
- Deliverable for review: `lp_dataframe_80_20.ipynb`. Nothing trains until it is approved.

## Current status

**First real run complete, 2026-09-28:** `ml_resnet50_base` trained on the VM
(50 epochs, batch 8, SGD lr 1e-4 Nesterov, two-way 80/20) and verified. Test
set (677): macro AUPRC 0.90454, macro F1 0.80826. Four classes at or near
ceiling; Folded Lens is the one weak class (F1 0.103), the co-occurrence risk
of section 8 of DESIGN.md realised. Record:
`reports/multilabel/ml_resnet50_base_run_20260928.md`, registry row
`ml_resnet50_base` (done), mirror `run/multilabel_lp_20260928/`.

Smoke run of 2026-09-23 (label and split steps only, no pixels needed):

- `build_labels.py`: 6,097 rows, all 9 cross-checks matched (per-class counts,
  3,377 with any LP tag, 2,145 untagged, 125 duplicate `P1_MPP` tags removed).
  Unreliable negatives: 2,143, all in the two unfinished tasks (`P2_LD` 1,876 and
  `P3_EP` 267), so 3,954 images are trusted. md5 join: 6,095 exact, 2 images missing
  from the md5 record (both in the Extraneous Polymer folder), 0 key conflicts.
  Within this export the md5 grouping finds 6,094 groups, 1 group holding 2 images.
- `make_splits.py`: ran with the iterative strategy (`iterative-stratification` 0.1.9,
  installed into the project environment for this experiment) and the powerset
  fallback was exercised too. Final `splits/seed42.csv`: 4,267 / 915 / 915 images
  (69.99 / 15.01 / 15.01 percent), 0 groups crossing splits, byte-identical on a
  rerun, per-class positives tracked in every split.
- `train.py`: compiles, `--help` runs without torch installed, and its torch-free
  parts were verified (average precision matches sklearn to 1e-16, split join and
  the reliable-only filter return the counts above, a missing image root fails with
  a clear message). The 2-step model smoke is **blocked**: torch and torchvision are
  not installed, there is no NVIDIA runtime on this machine, and the image pixels are
  not present. Nothing has been trained and no metric exists yet, so the registry
  rows stay `planned`.
