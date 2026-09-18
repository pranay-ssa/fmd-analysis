# FMD Preprocess

Fixed-size per-class crop pipeline for FMD inspection images. Replaces black-border area with a consistent per-class window centered on the detected lens content.

## Quick start

```bash
# Setup (once)
uv sync

# Crop all classes, both modes
uv run src/fixed_crop.py --all --modes both

# Crop specific classes
uv run src/fixed_crop.py --classes "Bubble" "Cavity Off Center" --modes single-size

# Run before/after EDA (proves nothing was distorted)
uv run src/eda_before_after.py --class "Bubble" \
    --annot data/annotations.xml \
    --crops run/single-size_fixed_crop/Bubble_20260903 \
    --out run/eda/Bubble_20260903 \
    --orig-images data/incoming/Bubble
```

## Pipeline

```
data/incoming/<Class>/*.bmp  (1465 source BMPs, 22 classes)
        │
        ▼
src/fixed_crop.py + src/config.py
        │
        ▼
run/single-size_fixed_crop/   (per-class fixed-size BMPs, 120px border)
run/multi-size_fixed_crop/    (per-class fixed-size BMPs, 45/80px border)
        │
        ▼
vm/build_lens_presentation_split*.py  (train/test split)
        │
        ▼
samples/model_training*.py            (train on VM)
        │
        ▼
scripts/build_landing_pad*.py         (results workbook)
```

## Layout

```
FMD-Preprocess/
├── src/
│   ├── fixed_crop.py         # Production crop engine
│   ├── config.py             # Canonical crop-size maps + thresholds
│   ├── eda_before_after.py   # Before/after invariance EDA
│   └── make_deck.py          # Lead-review deck builder
├── scripts/
│   ├── build_landing_pad.py          # 4-arch results workbook
│   └── build_single50_landing_pad.py # Single-scale results workbook
├── samples/
│   ├── model_training 2.py   # 4-arch training script (VM source of truth)
│   ├── model_training.py     # Single-scale training script
│   ├── FMD_ResNet50Architectures.ipynb  # ResNet50-Inception + SE arch
│   ├── ResNet18.ipynb        # ResNet18 arch
│   ├── JnJ_CNN.ipynb         # ResNet50 base arch
│   └── ContactLensDefectResults.xlsx   # Lead's format reference (read-only)
├── data/
│   ├── annotations.xml       # Source-of-truth labels (read-only)
│   └── incoming/<Class>/     # Raw BMPs, one folder per defect class
├── run/
│   ├── single-size_fixed_crop/  # Production crops, single mode
│   ├── multi-size_fixed_crop/   # Production crops, multi mode
│   ├── eda/                  # EDA scripts + analysis outputs
│   └── reports/
│       └── fixed_size_crop_spec.md  # Finalized algorithm spec
├── vm/
│   ├── build_lens_presentation_split.py       # Split builder (multi)
│   ├── build_lens_presentation_split_single.py # Split builder (single)
│   ├── setup_vm.sh          # VM setup
│   └── README.md            # VM docs
├── tests/
│   └── test_crop_modes.py   # Crop mode validation
├── ARCHITECTURE.md          # Pipeline design + parameters
├── HANDOFF.md               # Current operational handoff
├── INGEST.md                # How to add a new defect class
└── README.md                # This file
```

## Rules

- The crop never changes pixel values. It is a pure window cut.
- `annotations.xml` is never edited by code. It is the ground truth.
- Each run gets its own dated folder. We never overwrite a prior run.
- Images are git-ignored (heavy). Code, docs, and samples are committed.
- Presentation-tag images (no bbox) are held out of the EDA.

## Key files

| File | Role |
|---|---|
| `src/fixed_crop.py` | Production crop engine (finalized) |
| `src/config.py` | Canonical crop-size maps + thresholds |
| `reports/preprocessing/fixed_size_crop_spec.md` | Full algorithm spec (source of truth) |
| `reports/yolo26/yolo26_arch_experiments_spec.md` | YOLO26 detect experiment log (single source of truth for that line) |
| `reports/yolo26/DOC_CORRECTIONS_20260911.md` | Corrections audit trail from the 2026-09-11 verification (evidence + C1-C43 + R1/R2) |
| `reports/yolo26/ROOT_CAUSE_20260911.md` | Why the wrong conclusions entered the record, and the rules that block each failure mode |
| `experiments/registry.json` | Experiment registry: results, provenance per row, pending re-runs |
| `experiments/README.md` | Experiment governance: dos and don'ts, pitfalls, ADRs, blast radius |
| `samples/model_training 2.py` | 4-arch training script |
| `scripts/build_landing_pad.py` | Results workbook builder |
| `HANDOFF.md` | Current operational handoff |
