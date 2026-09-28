---
title: Experiment design: multi-label ResNet50 on lens-presentation tags
date: 2026-09-23
type: decision
status: active
where: experiments/multilabel_resnet50/DESIGN.md
---

# Experiment design: multi-label ResNet50 on lens-presentation (LP) tags

Date ideated: 2026-09-23
Status: scaffold only (design frozen, no training launched)
Owner: Pranay
Registry: `experiments/multilabel_resnet50/registry.json`

## 1. Question

Can a single ResNet50 classifier predict the 5 lens-presentation (LP) conditions on a lens
inspection image as a multi-label problem, where the same picture may carry more than one
LP condition at once?

This is the classification companion to the detection line. It is deliberately a
multi-label problem, not a 5-way softmax: 178 images carry two LP tags at the same time
and the two tags are always Folded Lens + Multiple Lenses.

## 2. Data source

- Annotation export: `data/Updated Annotations 20260922.xml` (CVAT format, 11 tasks,
  6,097 image elements).
- Image names in the export are relative paths into the two drop folders
  (`Updated ICube Categorical Classes 20260915/<class>/<file>.bmp` and
  `Updated ICube Objects 20260915/<class>/<file>.bmp`), so an image root directory plus
  the relative path is enough to open any picture.
- Content hashes come from `run/line_eda/20260916/image_md5_records.csv`
  (columns: folder, class, filename, md5, bytes; the file has no header row).
- Image pixels are NOT on this machine. The drop folders live with the bulk data on the
  VM copy of the source drop (see `docs/armor_blob_transfer_20260916.md` and
  `docs/reference/vm_and_datasets.md`). Training therefore needs an image root supplied at
  run time (`--image-root` or the `FMD_IMAGE_ROOT` environment variable). Every step that
  does not need pixels (label matrix, split, code review) runs locally.

## 3. Label space

| Code | Class | Images with the tag |
|---|---|---|
| P1_COC | Cavity Off Center | 183 |
| P1_FL | Folded Lens | 178 |
| P1_ML | Multiple Lenses | 1,442 |
| P1_MPP | Missing Primary Package | 1,427 |
| P1_NL | Missing Lens | 325 |

Facts taken from `run/annotations_audit_20260923/multi_label_lp_analysis.json` and
reproduced by `build_labels.py`:

- 3,377 of 6,097 images carry at least one LP tag.
- 178 images carry exactly 2 LP tags, all of them Folded Lens + Multiple Lenses.
- 125 images carry a duplicate `P1_MPP` tag twice. Tags are de-duplicated per image
  before the multi-hot vector is written, so a tag is a set membership, not a count.
- 2,145 images carry no tag at all (any task, not just LP).

Label matrix format (`labels.csv`): image_path, the 5 binary columns, content md5, plus
provenance columns (task_id, task_name, n_tags, has_any_tag, negatives_reliable).

## 4. Negatives policy (read this before trusting any metric)

A zero in a label column can mean two different things: a confirmed absence, or an image
that nobody has classified yet. The two are not interchangeable.

Rule used here: `negatives_reliable = True` when the image carries at least one tag
(any task tag, so a human did look at it) OR the image belongs to a fully finished task
folder (every image in that task carries at least one annotation).

The Low Dose task is the live counterexample: 76 of 1,952 images are done, so its
untagged images are unreliable negatives. With this rule 2,143 of the 2,145 untagged
images are flagged unreliable (1,876 in Low Dose plus 267 in the partially annotated
Extraneous Polymer task); the remaining 2 sit in fully annotated tasks and are trusted.
Consequences:

- Every image is kept (all 6,097), so the split and the label matrix stay complete.
- The `negatives_reliable` column is the switch: training can filter to reliable rows
  (`train.py --reliable-only`) or keep everything (default), and any headline number
  should be reported on the reliable subset as well.
- Class imbalance is severe (P1_FL 178 vs P1_ML 1,442), so macro AUPRC is the metric of
  record and raw accuracy is meaningless here.

## 5. Split design (leakage control)

- Group key = content md5. 34 pictures are stored in two folders and 27 library pictures
  are renamed twins, so a per-path split would leak identical pixels across train and
  test. Images with no md5 match fall back to a path-based group key and are counted in
  the run log.
- Ratio 70/15/15 (train/val/test), seed 42, deterministic.
- Strategy: iterative multi-label stratification over groups (each group reduced to the
  OR of its members' labels) when `iterstrat` is installable; otherwise the documented
  fallback: stratify on the label-powerset (exact combination pattern) with group-aware
  assignment, capacities tracked by image count. Which strategy ran is recorded in
  `splits/seed42.csv`'s companion log line and in `registry.json`.
- Fractions are exact at group level; because roughly 60 groups hold 2 images, image
  fractions can differ from 70/15/15 by about one percent. The run prints both.
- The split file is written to disk (`splits/seed42.csv`) and never regenerated during
  training, so any two runs see the same data.

## 6. Model and training recipe

- Base: ResNet50 from torchvision, ImageNet weights by default, classifier head replaced
  by `Linear(2048, 5)`.
- Loss: `BCEWithLogitsLoss`, with an optional `--pos-weight` switch that sets per-class
  positive weights from the train split (off by default so the first run is the plain
  baseline).
- Input: 224 x 224, standard normalization, **no augmentation** (decision 2026-09-24:
  geometric transforms change what the defect is, and nothing lighter was asked for).
- Optimization: SGD, lr 1e-4, momentum 0.9, Nesterov, 50 epochs, batch 8, seed 42 -
  the same recipe as the previous single-label CNN runs, so the only difference against
  them is the multi-label head, loss, target, metric and inference.
- Early stopping on macro AUPRC (mean of the 5 per-class average precision values) with
  configurable patience; best checkpoint and per-epoch history written to the run dir.
- Metrics of record: macro AUPRC. Diagnostics: per-class AUPRC, per-class precision and
  recall at 0.5, unreliable-negative breakdown.

## 7. Planned runs (registry rows, ideated before execution)

1. `ml_resnet50_base`: plain baseline, all images, no pos_weight. Control.
2. `ml_resnet50_reliable`: same config, `--reliable-only`. Measures how much the
   unreliable negatives were dragging the baseline.
3. `ml_resnet50_posw`: baseline plus `--pos-weight`. Measures the imbalance lever.

Nothing in this list has been run. Rows stay `planned` until metrics artifacts exist.

## 8. Risks and open questions

- No pixels on this machine, so the model path cannot be smoke tested end to end here.
  The 2-step model smoke is gated on torch plus an image root and is reported as blocked
  until one of them exists.
- Unreliable negatives may inflate or deflate per-class AUPRC; always read the reliable
  subset next to the headline number.
- Folded Lens never appears without Multiple Lenses in this export (178 of 178), so
  P1_FL is effectively a subset pattern. A model may learn the co-occurrence instead of
  the folded-lens appearance; per-class AUPRC plus a manual image review of the FL
  predictions is the planned check.
- Grouping by md5 collapses duplicate pixels but not near-duplicates (resaved or
  cropped versions of the same picture). The 27 renamed twins are content identical and
  are covered; anything else is not.
