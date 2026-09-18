# FMD Preprocess: Fixed-Size Crop Pipeline

**Version:** 2.0.0
**Date:** 2026-09-03 (algorithm finalized)
**Method:** Per-class fixed-size crop, lens-centered (replaces variable-size ROI-Crop)
**Status:** Algorithm validated on full 22-class dataset, both modes. User-accepted.

## 1. Purpose

FMD inspection BMPs are 2448x2048 and 8-bit grayscale. They carry 60 to 75 percent pure-black border. This pipeline crops each image to a per-class fixed-size window centered on the detected lens content. The crop improves speed, storage, and signal-to-noise. It does not touch pixel values (pure window select; calibration preserved).

The fixed-size approach means every crop from the same class and mode has identical dimensions, so downstream training receives consistent input sizes without padding or resizing.

## 2. Repository layout

```
FMD-Preprocess/
├── src/
│   ├── fixed_crop.py         # Production crop engine (FINALIZED)
│   ├── config.py             # Canonical crop-size maps + thresholds
│   ├── preprocess.py         # OLD variable-size ROI-Crop (superseded, kept for reference)
│   ├── eda_before_after.py   # Before/after invariance EDA (separate tool)
│   └── make_deck.py          # Builds the lead-review deck (.pptx)
├── scripts/
│   ├── build_landing_pad.py          # Auto-fill 4-arch results into lead's workbook
│   └── build_single50_landing_pad.py # Auto-fill single-scale results
├── samples/
│   ├── model_training 2.py   # 4-arch training script (source of truth for VM runs)
│   ├── model_training.py     # Single-scale (epoch-50) training script
│   ├── FMD_ResNet50Architectures.ipynb  # ResNet50-Inception + SE arch definitions
│   ├── ResNet18.ipynb        # ResNet18 arch definition
│   ├── JnJ_CNN.ipynb         # ResNet50 base arch definition
│   └── ContactLensDefectResults.xlsx   # Lead's format reference (read-only)
├── data/
│   ├── annotations.xml       # Source-of-truth labels (CVAT, read-only)
│   └── incoming/<Class>/     # Raw BMPs, one folder per defect class (1465 images)
├── run/
│   ├── single-size_fixed_crop/<Class>_<date>/  # Production crops, single mode
│   ├── multi-size_fixed_crop/<Class>_<date>/   # Production crops, multi mode
│   ├── eda/                  # EDA scripts + analysis outputs
│   └── reports/
│       └── fixed_size_crop_spec.md  # FINALIZED algorithm spec (source of truth)
├── vm/
│   ├── build_lens_presentation_split.py       # Train/test split builder (multi mode)
│   ├── build_lens_presentation_split_single.py # Train/test split builder (single mode)
│   ├── setup_vm.sh            # VM environment setup
│   └── README.md              # VM connection + data paths
├── tests/
│   └── test_crop_modes.py     # Crop mode validation tests
├── ARCHITECTURE.md            # This file
├── INGEST.md                  # How to add a new defect class
├── HANDOFF.md                 # Current operational handoff
└── README.md
```

## 3. Pipeline flow

```
Source BMPs (2448x2048)
    │
    ▼
src/fixed_crop.py          Detect lens (threshold + blob filter),
    │                       center fixed-size window on content centroid,
    │                       no-loss guard for outliers.
    ▼
run/{single,multi}-size_fixed_crop/   Per-class fixed-size BMPs
    │
    ▼
vm/build_lens_presentation_split*.py  Split into train/test (hard-linked)
    │
    ▼
samples/model_training*.py            Train on VM (A100 GPU)
    │
    ▼
scripts/build_landing_pad*.py         Auto-fill results into lead's workbook
```

## 4. Algorithm (per image, detection runs once for both modes)

1. Load grayscale uint8 (2448x2048 source).
2. Tier-1 detect (mean >= 15); if no blob, tier-2 (mean >= 13). Content bbox = union of kept blob extents (no margin).
3. If no blob (blank frame): crop = class canonical window centered on FRAME center. Flag `blank`.
4. Else content bbox present. Center a fixed window of the class canonical W x H on the content bbox centroid, clamped to the frame:
   - If the content bbox fits fully inside that fixed window: emit fixed window.
   - If it does NOT fit (rare, ~0.5%): NO-LOSS GUARD: expand the window to content bbox + CONTENT_MARGIN, clamped to frame. Flag `expanded`; output dims exceed canonical. This is the only case that breaks strict fixed size, and it guarantees the lens is never clipped.
5. Write crop; log actual W x H, window origin, flags.

No pixel value changes. Multi and single windows are placed from the SAME content bbox (single is a wider frame), so detection is done once per image.

## 5. Parameters (src/config.py)

| Param | Value | Rationale |
|---|---|---|
| `THRESHOLD` | 3 | Fixed threshold (NOT Otsu). Captures dim rim; object peaks at 95-142. |
| `MIN_BLOB_SIZE` | 500 | Biggest noise blob observed: 84 px. |
| `MIN_BLOB_MEAN` | 15 | Noise means: 4.7-7.2. Object mean: ~60. |
| `RECOVERY_BLOB_MEAN` | 13 | Tier-2 recovery for borderline cases. |
| `MIN_CONTENT_ROWS` | 100 | Blank-frame guard. |
| `CONTENT_MARGIN` | 45 | Guard pad around content when fixed window can't fit it. |
| `PER_CLASS_CROP_SINGLE` | dict | Per-class canonical (W, H) for single-size mode (120px border). |
| `PER_CLASS_CROP_MULTI` | dict | Per-class canonical (W, H) for multi-size mode (45/80/120px border). |

## 6. Crop modes

| Mode | Margin | Purpose |
|---|---|---|
| **single-size** | 120px | Wider border around lens. Used for single-scale training. |
| **multi-size** | 45px (default), 80px (HEMA Fragment, Wet Package), 120px (Fiber) | Tighter crop. More black removed. Used for multi-scale training. |

Per-class canonical sizes are derived from p99 of observed crop dimensions (rounded up to 4). Single-size canonical >= multi-size canonical per class (~150px difference = 2 * (120 - multi_margin)).

## 7. Validation

- Full 22-class run: 1465 images, both modes, 8 workers, 387s (0.26 s/img).
- All `ok` crops equal canonical size exactly. 4 images (0.27%) triggered the no-loss guard (expanded). Guard behavior accepted by user after visual inspection.
- Blank frames: View Obstructed x16, Cavity Off Center x5 (frame-centered, no lens).
- Centering verified: A/B test showed box-centering is within 2-27px of core-centering (negligible). Pure intensity-centering rejected (specular glare drags ~400px).

## 8. Interfaces

- **In:** `.bmp` files in `data/incoming/<Class>/` (grayscale or color, converted to L).
- **Out:** `run/<mode>_fixed_crop/<Class>_<date>/<stem>_crop.bmp` + `crop_manifest.csv` + `run_summary.json`.
- **CLI:** `uv run src/fixed_crop.py --all --modes both --output-base run`

## 9. Audit rules

1. The crop is a pure window select. Pixel values stay untouched. Calibration stays intact.
2. Every crop logs `(file, left, top, width, height, right, bottom, status)` to the manifest.
3. One pipeline version runs a whole batch. The manifest records `pipeline_version`.
4. `annotations.xml` is never edited by code. It is the ground truth.

## 10. Pitfalls

- **Otsu / auto-threshold is dangerous.** It picks t=35, which lands mid-object and cuts the dim rim. Use fixed threshold only.
- **Margin 25 is too tight** on the left rim. Verified visually. 45 is the minimum safe margin.
- **Stray light streaks** can inflate the union box and pull the center off the lens. The no-loss guard handles this (expands, never clips). If lens-only centering is wanted later, exclude blobs far from the main lens blob.
- **Editing the import block of `model_training 2.py`** via the edit tool has silently dropped `import argparse` before. Always `py_compile` AND re-verify the full import block after edits.

## 11. Superseded (kept for reference)

- `src/preprocess.py` — old variable-size ROI-Crop engine. Replaced by `src/fixed_crop.py`.
- `vm/train_resnet*.py` — old individual trainers. Replaced by `samples/model_training 2.py`.
