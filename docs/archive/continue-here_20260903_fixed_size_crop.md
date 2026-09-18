---
context: default
task: algo-finalized
status: finalized
last_updated: 2026-09-03T07:35:11Z
---

# Continue Here — FMD-Preprocess Fixed-Size Crop

Local work is COMPLETE and the algorithm is FINALIZED and user-accepted. Next step is a
separate, new workstream: port to the VM and re-crop yesterday's data.

No blocking anti-patterns / methodology failures were discovered this session.

## Current State

Replaced the variable-size ROI-Crop output with a per-class, per-mode **fixed-size,
lens-centered crop** plus a no-loss guard. Built, validated on the full 22-class local
dataset (both modes, 1465 images), visually inspected and **accepted by the user**.
Source of truth: `reports/fixed_size_crop_spec.md` (FINALIZED).

The 4-day arc that got here (for context, not needed to redo):
1. Measured observed crop dims per class per mode (`run/eda/crop_size_analysis.*`).
2. Center-offset EDA proved lenses sit off frame-center (worst: Cavity Off Center,
   Dirty Camera, View Obstructed) -> box-centering needed, not blind frame-center.
3. Chose p99 per-class canonical sizes (Option A: separate single/multi maps).
4. Implemented + validated.

## Completed Work

- `src/fixed_crop.py` — new fixed-size crop CLI. Detect ONCE per image; emit both modes
  from one content bbox; window centered on lit-content bbox; blank -> frame-center;
  no-loss guard (`CONTENT_MARGIN=45`) expands only when content can't fit.
  Flags: `--input-base/--output-base/--classes/--all/--modes [both|single-size|multi-size]/--workers`.
  Output: `run/<mode>_fixed_crop/<Class>_<YYYYMMDD>/<stem>_crop.bmp` + `crop_manifest.csv`
  + `run_summary.json`. Parallel `--workers` (default 8).
- `src/config.py` — added `PER_CLASS_CROP_SINGLE`, `PER_CLASS_CROP_MULTI`
  (measured p99 maps, round-to-4), `CONTENT_MARGIN`, `get_crop_size(class, mode)`.
- `reports/fixed_size_crop_spec.md` — FULL spec, FINALIZED (status header updated).
  Contains canonical tables, center evidence, loss tables, full-run results, the 4 guard
  cases with cause analysis, and all final decisions.
- Exploratory/EDA scripts under `run/eda/` (all reproducible):
  `analyze_crop_sizes.py`, `canonical_for_mode.py`, `propose_canonical_sizes.py`,
  `center_offset_eda.py`, `probe_frame_center_fit.py`, `measure_center_drift.py`,
  `ab_center.py` (box vs core centering A/B), `qa_fixed_crops.py`, `analyze_guard_cases.py`.
- Sample + full crops present under `run/{single-size,multi-size}_fixed_crop/*_20260903/`.
  A/B centering pairs under `run/center_ab/`.

## Remaining Work (NOT done here — next workstream)

- Port the algorithm to the VM (`vm/` has self-contained `test_crop_modes_vm.py` +
  `setup_vm.sh`; the local script imports `config.py` which the VM scripts avoid).
- Re-crop yesterday's VM data with the new fixed-size algorithm.
- Wire downstream dataset builders (`build_lens_presentation_split.py` etc. currently
  read the OLD `run/multi_size_crop` / `run/single_size_crop` dirs) to the new
  `run/<mode>_fixed_crop/` output if fixed-size crops are to feed training/test.

## Decisions Made

- **Option A**: separate per-mode per-class canonical sizes (multi stays tight, single
  keeps 120px border). Confirmed by how the user/lead framed "fixed single and multi".
- **Canonical = p99** of the mode's observed crop dims, rounded up to 4 (robust cap,
  not raw max). Single-size dominates multi-size image-wise, so its numbers govern.
- **Centering = lit-content bbox center** (KEPT). A/B showed core-vs-box drift is
  negligible (med 4-27px, <= ~2% of crop). Pure intensity-centering REJECTED: specular
  glare drags it ~400px and would fire the guard on ~100% of images.
- **No-loss guard accepted**: only 4 images (0.27%) exceed canonical (2 causes: stray
  secondary blobs inflating the union box; content genuinely wider than the p99 window).
  All logged in the spec. Nothing clipped.
- **hard-class skip-blob list NOT used**: detection runs on every image; blank -> frame
  center. (View Obstructed x16, Cavity Off Center x5 are the only no-blob frames.)
- **Blanks = frame-centered** fixed crop (no lens to preserve) - replaces old tier-3
  median-hack.

## Blockers
None. Guard behavior on the 4 edge cases accepted by user after visual inspection.

## Required Reading (in order)
1. `reports/fixed_size_crop_spec.md` — the FINALIZED spec (canonical tables, guard
   cases, decisions). Read before touching the algorithm.
2. `src/fixed_crop.py` — the implementation (already validated; read if porting to VM).
3. `src/config.py` — canonical maps + `get_crop_size` / `get_margin`.
4. (If doing EDA again) `run/eda/*.md` / `*.json` outputs.

## Infrastructure State
- Local run: Windows, `uv` python 3.12 env with numpy 2.5.2 / scipy 1.18.1 / pillow.
- Full 22-class both-mode run takes ~6.5 min at 8 workers (387s for 1465 imgs, 0.26 s/img).
- Git: repo has many pre-existing untracked files; NOT committed as WIP (not requested).
  New/changed: `src/fixed_crop.py`, `src/config.py`, `reports/fixed_size_crop_spec.md`,
  `run/eda/*`, sample+full crop outputs under `run/*size_fixed_crop/`.

## Context
User wanted to confirm every centering idea was tested before fixing the algorithm, then
understand the guard-triggered images, then hand off before moving to the VM to re-crop
yesterday's data. All three done: A/B centering tested (negligible), guard causes
categorized, spec finalized. The fixed-size crop algorithm is the agreed production crop.

## Next Action
Start the VM workstream: port `src/fixed_crop.py` (self-contained, importing `config.py`
maps) to the VM alongside the existing `test_crop_modes_vm.py`, run on yesterday's data,
then re-wire dataset builders to the new `run/<mode>_fixed_crop/` output. Confirm the
VM's source path/classes first (see `vm/README.md`).
