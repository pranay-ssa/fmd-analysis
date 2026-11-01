# Lens Presentation Defect Classifier - Inference Package

This package runs one image through the trained defect-classification model and
prints a score (0 to 1) for each defect class, plus a flag when the score
passes that class's threshold.

## Contents

- `final.pt` - the trained model weights (provided separately; keep the
  filename or point to it in the config).
- `predict.py` - the scoring script.
- `config.json` - settings: which weights file to use, which image to score,
  and each class's name and threshold.
- `requirements.txt` - the Python packages needed.
- `README.md` - this file.

## Setup

Python 3.9 or newer is required.

```
pip install -r requirements.txt
```

## Scoring an image

Open `config.json` and set the two paths:

- `checkpoint`: path to the weights file (for example `final.pt`).
- `image_path`: path to the image to score (JPG or PNG).

Then run:

```
python predict.py
```

A different config file can be passed with `python predict.py --config other_config.json`.

## Reading the output

Each row shows one class's code, plain name, score, and flag. The score is the
model's confidence that the defect is present. A class is `FLAGGED` when the
score passes the threshold listed for it in `config.json`. Thresholds differ
per class because they were tuned per class on held-out data.

The 13 output columns, in the order the model produces them:

| Code | Class |
|---|---|
| P1_MPP | Missing Primary Package |
| P1_ML | Multiple Lens |
| P2_LOC | Lens Off Center |
| P2_DC | Dirty Camera |
| P1_NL | No Lens |
| P1_FL | Folded Lens |
| P2_LD | Low Dose |
| P1_COC | Cavity Off Center |
| P2_DS | Dirty Strobe |
| P2_FOV | View Obstructed |
| P2_BSC | Bubble Scatter |
| P1_PPM | Package Misalignment |
| object_present | Object Present |

## Notes

- Images are resized to 224 x 224 and normalized with ImageNet statistics
  inside the script; no separate preprocessing is needed.
- The first run takes a few extra seconds while the model loads; each
  additional image scores in well under a second on a normal CPU.
- `predict.py` expects an RGB image (JPEG, PNG, or BMP). Other formats should
  be converted first.
