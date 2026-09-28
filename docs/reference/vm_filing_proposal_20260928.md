---
title: Proposed VM filing architecture for pranayp home
date: 2026-09-28
type: reference
status: active
where: docs/reference/vm_filing_proposal_20260928.md
---

# Proposed VM filing architecture

Status: PROPOSAL ONLY. Nothing on the VM has been moved, renamed or created.
Written from a read-only survey of `/home/pranayp` on 2026-09-28. Execution
happens only after sign-off, in one maintenance window with no run active.

## 1. What the survey found (the problems being solved)

1. **The root folder is a misnomer.** `~/yolo_ooi` holds detection runs, CNN
   classifiers, the multilabel ResNet, five datasets and an EDA report. Nothing
   about the name says what lives there, and every new task type makes it
   worse.
2. **Loose-file sprawl.** About 30 loose scripts, logs, tarballs and JSON
   summaries sit in `yolo_ooi/` root, and about 50 more items sit in the home
   root (`model_runs`, `lens_warmup`, `ooi_warmup`, `run_*.sh`, weights, a
   `misc/`). New work lands wherever the terminal happens to be.
3. **Two parallel evidence trees.** `run/` (datasets and reports) and `runs/`
   (model output) differ by one letter and hold unrelated things.
4. **Anonymous increment folders.** `runs/detect/val` through `runs/detect/val-9`
   and `runs/obb/val-2..4` are ultralytics default names from unset
   `project`/`name` args. Nothing in the name says which run produced them.
5. **Date discipline is inconsistent.** Some folders carry `_20260908` or
   `_20260917`; most carry nothing. Age is unguessable from the name.
6. **Runs are not self-contained.** A run's config lives in the driver script
   at the root, its log at the root, its summary JSON at the root, its weights
   under `runs/<family>/<arm>/`. Reassembling one run means hunting four
   places.

## 2. The proposed tree (broad, flat, three levels deep maximum)

```
/home/pranayp/fmd/
├── data/                      datasets built FROM the masters
│   ├── det-obb/               (was dataset_obb)
│   ├── det-multiclass/        (was dataset_multiclass)
│   ├── det-crops/             (was crop_detect_dataset)
│   ├── cls-combined22/        (was combined_dataset_single_20260908)
│   ├── cls-lp/                (was lens_presentation_dataset_*, OoI_dataset_single)
│   ├── splits-line/           (was dataset_test_line_split, dataset_test_picture_split)
│   └── pretrained/            (was yolo26n.pt, yolo11n.pt loose + weights/)
├── code/                      every script and launcher, flat, verb-prefixed
│   ├── run_*.py  run_*.sh     drivers (launch a run)
│   ├── build_*.py             dataset builders
│   ├── eval_*.py  per_class*.py iou_*.py   evaluation
│   ├── verify_*.py  preflight_*.py         gates and audits
│   └── measure_*.py  diag_*.py             diagnostics
├── runs/                      THE unit of filing: one folder per run
│   └── 20260928-mllp-resnet50-base/
│       ├── run.json           args, seed, data paths, driver name, machine
│       ├── train.log          the full log
│       ├── metrics.json       the numbers
│       └── artifacts/         weights, history, prediction dumps
├── eval/                      cross-run analyses and verification output
│   └── 20260928-<name>/       same date-first naming
└── archive/                   tarballs and superseded runs; parked, never deleted
```

The bulk masters (`/data/FMD_Data_26082026/...`, the fmd_temp_images tree) are
NOT copied here; `data/` holds only derived datasets, and pixels stay with
amd100-user exactly as today.

## 3. Naming grammar (the one rule that replaces nesting)

A run folder is `YYYYMMDD-<family>-<model>-<arm>`, lowercase, hyphens, no
spaces, date-first so an `ls` sorts chronologically:

- **family** (broad on purpose, five values today, room for more):
  `det` detection, `cls` single-label classification, `mllp` multi-label,
  `eda` measurement-only, `ops` transfers and maintenance.
- **model**: `yolo26n`, `yolo11n`, `resnet50`, `resnet18`, `multiscale`, ...
- **arm**: the experiment name: `base`, `posw`, `reliable`, `r1-p3tap`,
  `sppf-k7`, `warmup`, `no-warmup`, `line24`...

Examples: `20260928-mllp-resnet50-base` (today's run),
`20260915-det-yolo26n-mc-processed-p3`, `20260917-cls-resnet50-line24`.

A second run of the same arm same day gets `-b` suffixed
(`20260928-mllp-resnet50-base-b`), never a `-2`.

## 4. The rules (few, enforceable, future-proof)

1. **One run = one folder = one ID.** Config, log, metrics and weights live in
   that folder. Nothing about a run lives outside it except the index row.
2. **Nothing loose in any root.** A new file goes into `code/`, an existing run
   folder, or a new dated folder under `eval/`. If it fits nowhere, that is a
   sign the family list needs a new value, which is allowed (the grammar flexes,
   the rule does not).
3. **Drivers set `project` and `name` explicitly.** Every ultralytics driver
   gains `project=/home/pranayp/fmd/runs`, `name=<run id>`, which kills the
   `val-2..val-9` pattern at the source.
4. **`runs/INDEX.csv` is the catalogue.** One row per run:
   `id,date,family,model,arm,seed,epochs,status,headline_metric,metric_value,path`.
   Each driver appends its own row at completion (one helper function; today's
   `train.py` already writes `metrics.json`, this is one more line). A 30-second
   scan of the CSV answers "what have we run and what scored what" without
   opening a single folder.
5. **Never delete; supersede into `archive/`.** Disk is 55G free; tarballs and
   dead arms get parked, not removed.
6. **Scratch is quarantined.** `~/tmp/` for throwaway probes, pruned weekly,
   never indexed.

## 5. Migration map (old to new, executed only at sign-off)

| Today | Becomes |
|---|---|
| `~/yolo_ooi/dataset_obb` | `fmd/data/det-obb/` |
| `~/yolo_ooi/dataset_multiclass` | `fmd/data/det-multiclass/` |
| `~/yolo_ooi/crop_detect_dataset` | `fmd/data/det-crops/` |
| `~/combined_dataset_single_20260908` | `fmd/data/cls-combined22/` |
| `~/lens_presentation_dataset_20260903`, `lens_presentation_dataset_single_20260903`, `OoI_dataset_single` | `fmd/data/cls-lp/` |
| `~/yolo_ooi/dataset_test_line_split`, `dataset_test_picture_split` | `fmd/data/splits-line/` |
| `~/yolo26n.pt`, `~/yolo_ooi/yolo11n.pt`, `~/yolo_ooi/weights/` | `fmd/data/pretrained/` |
| `~/yolo_ooi/*.py`, `*.sh` and `~/*.py`, `~/*.sh` (all loose scripts) | `fmd/code/` |
| `~/yolo_ooi/runs/yolo_arch`, `yolo26_arch`, `yolo26_arch_r1`, `yolo26_mc_arch` | `fmd/runs/2026xxxx-det-yolo*-<arm>/` (one folder per arm) |
| `~/yolo_ooi/runs/crop_repro/*`, `yolo26_multiclass`, `baseline_obb` | `fmd/runs/2026xxxx-det-*/` |
| `~/yolo_ooi/runs/multi55`, `multilabel_test` | `fmd/runs/2026092x-det-yolo26n-multi55-*/` |
| `~/yolo_ooi/multilabel_lp_20260928` | `fmd/runs/20260928-mllp-resnet50-base/` |
| `~/combined_22_runs`, `model_runs`, `model_runs_single50`, `ooi_single_model_runs`, `lens_warmup*`, `ooi_warmup*`, `lens_single_rerun`, `ooi_no_warmup_20260908`, `line_experiment_20260917` | `fmd/runs/2026xxxx-cls-*/` (one per line/study) |
| `~/yolo_ooi/run/` (datasets + report) | contents split into `fmd/data/` and `fmd/eval/` |
| root logs `*.log` and summary `*.json` | moved into their run folder; orphans without a run go to `fmd/eval/20260928-log-sweep/` |
| `baseline_obb_run.tar.gz`, `batch1_light.tar.gz`, `model_metrics.tar.gz`, `single50_metrics.tar.gz` | `fmd/archive/` |
| `~/fmd_crop_output`, `~/crop`, `~/misc`, `~/__pycache__` | `fmd/archive/` (pycache just deleted at migration) |

Migration mechanics, when approved: one script, `mv` not `cp`, every move
recorded to `fmd/MIGRATION_2026xxxx.csv` (old path, new path, md5 before and
after), drivers' hard-coded paths updated in the same pass, and a post-migration
smoke of one driver per family before anything trains again. Run history is not
disturbed: no run folder is ever renamed inside `runs/`, so the registry's VM
path references are updated once, by the same script.

## 6. What this deliberately does NOT do

- It does not mimic the local repo's 7-zone depth. Local is deep because it is
  also documentation; the VM tree is only data, code and runs, so it stays
  three levels deep.
- It does not touch amd100-user's home, the blob connection, or the bulk
  masters.
- It does not force existing runs into perfect grammar where the original date
  is uncertain; those keep a best-known date and stay findable via the index.

## 7. Decision needed

1. Approve the tree and grammar as-is, or adjust the family list first.
2. Pick the maintenance window (needs a quiet GPU day; the move itself is
   minutes, the driver-path updates and smoke tests about an hour).
