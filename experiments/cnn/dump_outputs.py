#!/usr/bin/env python3
"""Prediction + confusion dumps for the CNN trainer (Task 1 readout).

Why this exists: model_training.py printed the confusion matrix and the
per-class numbers but persisted neither the matrix cells nor the per-image
predictions, so "which class is eating the merged Bubble class" could not be
answered from a finished run without retraining. These two writers add that
evidence with no change to the training recipe.

Pure Python on purpose: no tensorflow import, so this module is unit-tested
locally (experiments/bubble_merge/test_dump_outputs.py) before the VM sees it.

Outputs, both written next to metrics.json when the trainer is run with
--dump:

    predictions.csv   file, true, pred, then one probability column per class
    confusion.json    class_names, matrix (rows = true, cols = pred), support
"""
from __future__ import annotations

import csv
import json
import os


def test_file_paths(data_root, class_names):
    """Rebuild the exact file order image_dataset_from_directory uses with
    shuffle=False: classes sorted, filenames sorted inside each class."""
    paths, labels = [], []
    for ci, cls in enumerate(class_names):
        d = os.path.join(data_root, cls)
        if not os.path.isdir(d):
            # Only a truncated build (the --limit smoke tree) misses a class
            # in test while the trainer's class list came from train. Skip it:
            # the caller's order check then decides whether the derived labels
            # still agree with the trainer's, and falls back to index rows if
            # the class sets differ enough to shift the numbering.
            continue
        for fname in sorted(os.listdir(d)):
            paths.append(os.path.join(d, fname))
            labels.append(ci)
    return paths, labels


def dump_outputs(outdir, class_names, y_true, y_pred, y_prob, file_paths=None):
    """Write predictions.csv and confusion.json. Returns the paths written.

    If file_paths does not line up with y_true (ordering rule changed), the
    predictions fall back to an index row instead of silently mislabelling
    images, and order_match records that in confusion.json.
    """
    y_true = [int(v) for v in y_true]
    y_pred = [int(v) for v in y_pred]
    n = len(y_true)
    if len(y_pred) != n or len(y_prob) != n:
        raise ValueError("y_true %d, y_pred %d, y_prob %d: length mismatch"
                         % (n, len(y_pred), len(y_prob)))

    order_match = None
    if file_paths is not None and len(file_paths) == n:
        order_match = True     # caller has already compared derived labels
    elif file_paths is not None:
        order_match = False
        file_paths = None

    k = len(class_names)
    for row in y_prob:
        if len(row) != k:
            raise ValueError("probability row has %d columns, expected %d"
                             % (len(row), k))

    pred_path = os.path.join(outdir, "predictions.csv")
    with open(pred_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "file", "true", "pred"] +
                   ["p_%s" % c for c in class_names])
        for i in range(n):
            w.writerow([i,
                        file_paths[i] if file_paths else "",
                        class_names[y_true[i]], class_names[y_pred[i]]] +
                       ["%.6f" % float(v) for v in y_prob[i]])

    matrix = [[0] * k for _ in range(k)]
    for t, p in zip(y_true, y_pred):
        matrix[t][p] += 1
    conf_path = os.path.join(outdir, "confusion.json")
    with open(conf_path, "w", encoding="utf-8") as fh:
        json.dump({
            "class_names": list(class_names),
            "matrix": matrix,
            "support": [sum(r) for r in matrix],
            "n": n,
            "order_match": order_match,
        }, fh, indent=2)
    return pred_path, conf_path
