#!/usr/bin/env python3
"""Generate the reader-facing Jupyter notebook with all six CNN architectures.

Audience: the lead, who works in notebooks and supplied the original four architecture cells. So the
notebook is organised and worded the way hers is: one self-contained cell per architecture (block
definition plus model build), her architectures first and numbered in her order, then the two baselines
we added. No local file paths, no internals; what she needs to read is the architecture and its result.

The architecture cells are extracted programmatically from experiments/cnn/model_training.py with `ast`,
so the notebook can never drift from the code that produced the results. Re-run this script after any
trainer change.

Local only: writes notebooks/FMD_CNN_6Architectures.ipynb, touches nothing on the VM.

USAGE
    python3 experiments/cnn/make_notebook.py
"""
from __future__ import annotations

import ast
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
TRAINER = HERE / "model_training.py"
OUT = HERE.parent.parent / "notebooks" / "FMD_CNN_6Architectures.ipynb"

SRC = TRAINER.read_text(encoding="utf-8")
TREE = ast.parse(SRC)
FUNCS = {n.name: n for n in TREE.body if isinstance(n, ast.FunctionDef)}


def seg(name: str) -> str:
    """Verbatim source of a top-level function in the trainer."""
    return ast.get_source_segment(SRC, FUNCS[name]).rstrip() + "\n"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.strip().splitlines(True)}


# key -> (display accuracy, fused parameter count) as measured on the 22-class set
RESULTS = {
    "resnet50_inception": ("88.05", "58,547,094"),
    "resnet50_se": ("87.37", "50,544,246"),
    "resnet50_inception_attention": ("86.01", "58,744,051"),
    "resnet50_inception_refine": ("88.05", "45,988,758"),
    "resnet18": ("82.94", None),
    "resnet50": ("88.40", "25,716,630"),
}

# Her four architectures first, in her order, then the two baselines we added.
ARCH_CELLS = [
    ("resnet50_inception", "arch_resnet50_inception", ["inception_block"],
     "1. ResNet50 MultiLevel MultiScale  (your Architecture 1)",
     "An Inception block on each of the L3, L4 and L5 taps. The three levels are brought to a common "
     "size, concatenated, pooled, and classified through the same head in every cell of this notebook."),
    ("resnet50_se", "arch_resnet50_se", ["se_block"],
     "2. ResNet50 MultiLevel Attention  (your Architecture 2)",
     "The same three taps, each passed through a Squeeze-and-Excitation block first, so the channels "
     "are re-weighted before fusion."),
    ("resnet50_inception_attention", "arch_resnet50_inception_attention",
     ["se_block", "inception_attention_block"],
     "3. Inception with attention inside every branch  (your Architecture 3)",
     "Your Architecture 1 with a Squeeze-and-Excitation block inside each Inception branch, so attention "
     "acts before the concatenation rather than after it."),
    ("resnet50_inception_refine", "arch_resnet50_inception_refine", ["inception_block"],
     "4. Inception with a refined decode path  (your Architecture 4)",
     "Your Architecture 1 with a different decoder for the deepest level: bicubic upsampling, then a "
     "depthwise spatial refinement and a 1x1 channel mixer, instead of a transposed convolution."),
    ("resnet18", "arch_resnet18", [],
     "5. ResNet18  (baseline we added)",
     "A small backbone with a single pooling and dense head, included so the comparison covers a lighter "
     "model as well."),
    ("resnet50", "arch_resnet50", [],
     "6. ResNet50 plain  (baseline we added)",
     "The plain ResNet50 classifier: pooling on the final feature map, one dense layer, softmax. No "
     "multi-level fusion, included as the reference point for the four architectures above."),
]

TITLE = """
# FMD lens defect classifier: six architectures

This notebook holds the six architectures trained on the 22-class dataset, one cell each, in the same
form as the four architecture cells you supplied: every cell defines its block and then builds the
model, so the cells can be stepped through and the layers inspected directly.

Four of the six are your architectures, unchanged. Two baselines were added so the comparison covers the
whole matrix.

| # | Architecture | Where it comes from | Accuracy on the 22-class set |
|---|---|---|---|
| 1 | ResNet50 MultiLevel MultiScale | your Architecture 1, unchanged | 88.05 |
| 2 | ResNet50 MultiLevel Attention (SE) | your Architecture 2, unchanged | 87.37 |
| 3 | Inception with attention inside every branch | your Architecture 3, unchanged | 86.01 |
| 4 | Inception with a refined decode path | your Architecture 4, unchanged | 88.05 |
| 5 | ResNet18 | baseline we added | 82.94 |
| 6 | ResNet50 plain | baseline we added | 88.40 |

Training settings are identical for all six: 50 epochs, batch 8, seed 42, input 224x224, SGD with learning
rate 1e-4, momentum 0.9 and Nesterov, on the same train and test split. Per-class recall for all 22
classes, plus training time, is in the results workbook.

One note on the code: the architecture cells here are read straight out of the training script, so they
cannot drift from what was actually trained. The only edit to your code is forced by the framework
version, where Keras 3 removed the `alpha` argument of LeakyReLU, so it reads `negative_slope=0.1`.
That is the same value under the new name.
"""

SETUP = '''
# Setup: run this first. It loads the libraries and fixes the seed.
import os
import random
import time

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
import keras
import keras_hub
from sklearn.metrics import (accuracy_score, confusion_matrix, ConfusionMatrixDisplay,
                             precision_recall_fscore_support)

SEED = 42
NUM_CLASSES = 22        # 10 defect classes from the OOI set plus 12 from Lens Presentation

# Only needed for the optional training cell at the end.
DATA_DIR = "/path/to/dataset"   # folder containing train/ and test/


def apply_seed(seed=SEED):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass


apply_seed()
print("TensorFlow", tf.__version__, "| classes:", NUM_CLASSES)
'''

TRAIN_CELL = '''
# Optional: train and evaluate whichever architecture is in `model`, with the settings used for every
# number in this project. Set DATA_DIR above first.
EPOCHS, BATCH, WARMUP = 50, 8, True

train_ds = tf.keras.utils.image_dataset_from_directory(
    f"{DATA_DIR}/train", image_size=(224, 224), batch_size=BATCH, shuffle=True, seed=SEED)
test_ds = tf.keras.utils.image_dataset_from_directory(
    f"{DATA_DIR}/test", image_size=(224, 224), batch_size=BATCH, shuffle=False)
class_names = train_ds.class_names
num_classes = len(class_names)

model.compile(
    optimizer=tf.keras.optimizers.SGD(learning_rate=1e-4, momentum=0.9, nesterov=True),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"])

t0 = time.perf_counter()
history = model.fit(train_ds, epochs=EPOCHS)
print(f"Training time : {time.perf_counter() - t0:.2f} seconds")

y_true = np.concatenate([labels.numpy() for _, labels in test_ds], axis=0)
n_test = sum(images.shape[0] for images, _ in test_ds)

if WARMUP:
    # Two dummy passes warm the graph; the third warms the real file pipeline and is discarded.
    # Without them a one-time start-up cost lands inside the timed prediction and inflates the
    # per-image time. Accuracy is unaffected either way.
    dummy = tf.data.Dataset.from_tensor_slices(
        (tf.random.normal((64, 224, 224, 3)), tf.zeros((64,), dtype=tf.int32))).batch(BATCH)
    model.predict(dummy, verbose=0)
    model.predict(dummy, verbose=0)
    model.predict(test_ds, verbose=0)

start = time.perf_counter()
y_pred = np.argmax(model.predict(test_ds, verbose=1), axis=1)
elapsed = time.perf_counter() - start

print(f"Overall accuracy : {accuracy_score(y_true, y_pred) * 100:.2f}%")
print(f"Inference per image : {elapsed / n_test * 1000:.3f} ms")

p, r, f1, support = precision_recall_fscore_support(
    y_true, y_pred, labels=list(range(num_classes)), zero_division=0)
for cls, pi, ri, fi, si in zip(class_names, p, r, f1, support):
    print(f"  {cls}: precision={pi*100:.2f}%  recall={ri*100:.2f}%  f1={fi*100:.2f}%  n={int(si)}")

cm = confusion_matrix(y_true, y_pred)
fig, ax = plt.subplots(figsize=(10, 10))
ConfusionMatrixDisplay(cm, display_labels=class_names).plot(
    cmap="Blues", xticks_rotation=90, ax=ax, colorbar=False)
plt.title("Confusion matrix")
plt.tight_layout()
plt.show()
'''

OPEN_ITEMS = """
## Open items, for when this work is picked up again

- **Save the trained model.** The training script records the metrics and a confusion matrix but not the
  weights, so a finished run cannot be reused or re-checked without retraining it.
- **Measure the cold-start inference time.** The workbook shows an estimate for it, marked with a tilde,
  rather than a measured number.
- **A second split.** Between the two splits we have compared, one class moved by more than 20 points, so a
  second split would show how much of any difference is the split rather than the model. Until then, only
  comparisons made within one split should be read as architecture results.
"""


def build_cells() -> list:
    cells = [md(TITLE), md("## Setup"), code(SETUP)]
    for key, fn, helpers, heading, blurb in ARCH_CELLS:
        acc, params = RESULTS[key]
        bits = [blurb,
                f"Accuracy on the 22-class set: **{acc}**." +
                (f" Parameters: {params}." if params else "")]
        body = "\n\n".join(seg(h) for h in helpers)
        if body:
            body += "\n\n"
        body += seg(fn) + f"\n\nmodel = {fn}(NUM_CLASSES)\nmodel.summary()"
        cells.append(md(f"## {heading}\n\n" + "\n\n".join(bits)))
        cells.append(code(body))
    cells.append(md("## Optional: run the training settings used for the results above\n\n"
                    "Set `DATA_DIR` in the setup cell, run one architecture cell, then run this one."))
    cells.append(code(TRAIN_CELL))
    cells.append(md(OPEN_ITEMS))
    return cells


NOTEBOOK = {
    "cells": build_cells(),
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(NOTEBOOK, indent=1) + "\n", encoding="utf-8")

    # verify: valid JSON, all code cells compile, all six builders defined and built once
    back = json.loads(OUT.read_text(encoding="utf-8"))
    defined, built, n_code = set(), [], 0
    for i, c in enumerate(back["cells"]):
        src = "".join(c["source"])
        assert src.strip(), f"cell {i} is empty"
        if c["cell_type"] != "code":
            continue
        n_code += 1
        try:
            compile(src, f"cell{i}", "exec")
        except SyntaxError as e:
            raise SystemExit(f"cell {i} does not compile: line {e.lineno}: {e.msg}")
        for n in ast.parse(src).body:
            if isinstance(n, ast.FunctionDef):
                defined.add(n.name)
        if "model = arch_" in src:
            built.append("arch_" + src.split("model = arch_")[1].split("(")[0])

    want = sorted(f for _, f, _, _, _ in ARCH_CELLS)
    assert sorted(built) == want, f"build mismatch: {sorted(built)} vs {want}"
    assert all(f in defined for f in want), "a builder is missing from the notebook"
    print(f"wrote {OUT} | cells: {len(back['cells'])} ({n_code} code) | "
          f"six builders defined and built once | all code cells compile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
