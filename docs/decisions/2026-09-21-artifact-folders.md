---
title: One name for model-training output: runs/ renamed to model_runs/
date: 2026-09-21
type: decision
status: active
where: docs/decisions/2026-09-21-artifact-folders.md
---

# Artifact folder naming: `run/` and `runs/`

## Decision

`run/` keeps its name and its job (pipeline artifacts). `runs/` was renamed to `model_runs/` on
2026-09-21, filesystem move plus reference rewrite. Nothing was deleted or merged.

Rejected: collapsing both into a single `run/`. The two folders hold different things, and 58 files
under `run/` are tracked evidence, so a merge would have forced the `.gitignore` rules to be rewritten
and would have moved tracked evidence into a folder whose siblings are all ignored.

Rejected: renaming `run/` instead. That needs `git mv` on 58 tracked files and a rewrite of 137
references, against 153 for the other direction, and it would have retired the name that
`docs/ARCHITECTURE.md`, `docs/INGEST.md`, `README.md` and the `src/fixed_crop.py --output-base`
default all use.

## Why this was worth doing

The two names differ by one letter, both were live, and `run/x` against `runs/x` is easy to confuse in
a command, in a doc and in review. They are not duplicates:

| | `run/` | `runs/` (now `model_runs/`) |
|---|---|---|
| Contents | crops, EDA tables, split CSVs, per-line results | YOLO11 and YOLO26 run dirs, CNN `epochs_50` dirs |
| In git | 58 files tracked | nothing tracked |
| Size at rename | 455 MB | 107 MB, 726 files |

They were also not cleanly separated in the code. `src/yolo_ooi/01`, `02`, `05` and `07` read crops
from `run/single-size_fixed_crop` and write labels under `runs/yolo11/`, so one command crossed both
names. That, rather than size or content, is what made the collision a real defect.

## What changed

- The folder moved: `runs/` to `model_runs/`, 726 files, 110,553,513 bytes, verified byte-identical
  after the move against a pre-move manifest of every path and size.
- 113 path references in 31 files were rewritten (`runs/...` to `model_runs/...`) across `src/`,
  `experiments/`, `vm/ops/`, `notebooks/`, `reports/`, `docs/`, `README.md`, `HANDOFF.md`,
  `AGENTS.md` and `experiments/registry.json`.
- 10 references in 7 files used the segmented form (`os.path.join(REPO, "runs", ...)` or
  `REPO / "runs" / ...`) and were rewritten the same way, including `tools/index_docs.py`, whose skip
  list would otherwise have started sweeping `model_runs/` into `docs/INDEX.md`.
- `.gitignore`: the `runs/` rule became `model_runs/`. The nine fine-grained rules that guard inside
  `run/` are unchanged.

## Deliberately not changed

1. `vm/` paths. `vm/drivers`, `vm/ops` and `vm/eval` build paths from the VM's own project root
   (`/home/pranayp/yolo_ooi/runs/...`), not from this repository, so they still resolve on that
   machine. The `vm/ops` scripts that document the local pipeline were updated with the rest.
2. Three historic mentions are left as written, because each quotes a past state rather than pointing
   at a folder: `HANDOFF.md` and `reports/yolo26/DOC_CORRECTIONS_20260911.md` both describe the
   2026-09-15 commit whose `.gitignore` said `runs/`, and `docs/transfer/pack_old_laptop.sh` is the
   script that packed the old laptop.
3. `experiments/registry.json` rows whose `results_source` names `runs/crop_repro/...`,
   `runs/yolo26_arch/...`, `runs/yolo26_multiclass/...` or `runs/yolo26_mc_arch/...` are VM rows and
   were left alone. The nine rows that name this machine's mirror now read `model_runs/yolo11/...`.

## Fixed while in the area

`experiments/update_registry.py:26` read `REPO / "run" / "yolo_ooi" / "runs" / "yolo_arch"`, a path
that does not exist on this machine; the same file's line 115 already wrote
`runs/yolo11/yolo_arch/...`, and that is the real local mirror. It now reads
`REPO / "model_runs" / "yolo11" / "yolo_arch"`. This was pre-existing and is unrelated to the rename.

## Verification

- The move was checked against a manifest written before it: 726 of 726 files present, 0 size
  mismatches, byte total identical, old path absent.
- Every edited Python file compiles; `experiments/registry.json` parses; the edited shell scripts pass
  `bash -n`.
- `tools/index_docs.py` was re-run so `docs/INDEX.md` reflects the tree.

## Open

- The VM's tree still uses `runs/`. Renaming it there is a separate change, and until it is done the
  `vm/` scripts and the registry's VM rows keep the old name on that machine.
- `AGENTS.md` line 52 still reads "`notiondocs.md` and anything under `run/`, `model_runs/`,
  `.obsidian-vault/` or `data/incoming/`", which overstates the case: 58 files under `run/` are
  tracked and pushed. `AGENTS.md` is a protected file and the edit was refused, so the replacement
  wording is held here until someone applies it:

  ```
  ## Never pushed

  `notiondocs.md`, `.obsidian-vault/` and `data/incoming/`. The repository's `.gitignore` is the
  source of truth: it decides, path by path, what travels.

  ## The two output folders

  Both hold generated artifacts, but only one of them travels.

  - `run/` - pipeline artifacts: crops, EDA tables, split CSVs, per-line results. The dated folders
    the docs cite (`run/line_eda/...`, `run/line_splits_.../`, `run/line_results_.../`) are tracked
    evidence and are pushed. `run/augment/` and the crop folders are ignored, being regenerable.
  - `model_runs/` - model-training output: the YOLO11/YOLO26 run directories and the CNN
    `epochs_50` folders (weights, per-epoch logs, metrics, confusion matrices). Ignored in full,
    never pushed.

  Renamed 2026-09-21: `model_runs/` was `runs/` before that date, so docs dated earlier name it that
  way. Paths inside `vm/` are VM-local (`/home/pranayp/yolo_ooi/runs/...`) and keep the old name on
  that machine.
  ```

One further consequence to settle: `--check` on `tools/index_docs.py` compares against the folder
skip list, and that list now names `model_runs`. Nothing else in the tooling refers to the old name.

