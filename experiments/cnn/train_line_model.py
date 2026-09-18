#!/usr/bin/env python3
"""
Per-line ResNet50 classifier for the five production lines (step 4, 2026-09-17).

One model per line, trained on that line's pictures only, evaluated on held-out
pictures from the same line.

WHAT IT READS
    A split assignment built by src/build_line_split_assignments.py:
        <split-dir>/line_L24/split.csv
    columns: source_md5, source_path, class, line, split
    The source paths point at the raw 2448x2048 frames on the VM. No crops are
    used in this run, so the pipeline decodes the frame and resizes it to 224x224.

PROTOCOL (mirrors experiments/cnn/model_training.py so the numbers are comparable
in method, with the differences listed here)
    same   : ResNet50 ImageNet base, fully trainable, GAP + BatchNorm + Dense(1024)
             + Dropout(0.3) + softmax; SGD lr 1e-4, momentum 0.9, Nesterov; loss
             sparse categorical crossentropy; 50 epochs; seed 42; no validation
             split during training; evaluate on the test half only.
    differs: batch 4 (the lead's instruction; the frozen protocol was 8).
    differs: input is the raw frame resized to 224x224, not a fixed-size crop.
    differs: the images are decoded and resized once and cached, then served from
             memory for the remaining epochs. The pixels the model sees are
             identical; only disk traffic changes.
    adds   : the trained weights are saved (the earlier runs never saved them),
             the confusion matrix as CSV as well as PNG, and the loss curve.

OUTPUT (under --outdir)
    metrics.json                  everything the landing-pad workbook reads,
                                  plus the line, the split file, the history
    confusion_matrix_<line>.png   300 dpi, same style as the earlier runs
    confusion_matrix_<line>.csv   counts, rows = true class, columns = predicted
    history.json                  loss and accuracy per epoch
    weights.weights.h5            the trained model
    run.log                       the console log

USAGE
    python train_line_model.py --line L24 \
        --split-csv /data/.../line_splits_20260917/line_L24/split.csv \
        --epochs 50 --batch-size 4 --outdir /data/.../line_runs/L24/epochs_50
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time

import numpy as np
import tensorflow as tf
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, confusion_matrix,
                             precision_recall_fscore_support)

# The architectures come from the six-architecture trainer, not from a second copy here, so
# there is one definition of each and no chance of the two drifting apart.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_training import ARCH_BUILDERS, ARCH_LABELS  # noqa: E402

SEED = 42
IMG_SIZE = (224, 224)


def apply_seed(seed=SEED):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass


def arch_resnet50(num_classes):
    """Deprecated local copy. The architectures are imported from model_training.py.

    Kept only so an old import of this name does not break; use ARCH_BUILDERS["resnet50"].
    """
    return ARCH_BUILDERS["resnet50"](num_classes)


def read_split(path):
    """Return (train_rows, test_rows, class_names)."""
    train, test = [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            (train if row["split"] == "train" else test).append(row)
    classes = sorted({r["class"] for r in train} | {r["class"] for r in test})
    return train, test, classes


def decode(path, label):
    # The frames are 8-bit, 2448x2048, compression 0 BMPs (256-colour header).
    # tf.io.decode_bmp with channels=0 returns a single-channel tensor, and inside
    # a tf.data map its static channel size is None, so a Python shape test cannot
    # widen it: the model then receives (224, 224, 1) and ResNet50's strided slice
    # fails with "slice index 2 of dimension 3 out of bounds". Decode straight to
    # three channels, which is what the earlier image_dataset_from_directory
    # pipeline did with color_mode="rgb".
    raw = tf.io.read_file(path)
    img = tf.io.decode_bmp(raw, channels=3)
    img = tf.image.resize(img, IMG_SIZE, method="bilinear")
    return tf.cast(img, tf.float32), label


def make_ds(rows, class_index, shuffle, batch_size, seed, cache):
    paths = [r["source_path"] for r in rows]
    labels = [class_index[r["class"]] for r in rows]
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if cache:
        ds = ds.cache()
    ds = ds.map(decode, num_parallel_calls=tf.data.AUTOTUNE)
    if shuffle:
        ds = ds.shuffle(len(paths), seed=seed, reshuffle_each_iteration=True)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", required=True)
    ap.add_argument("--split-csv", required=True)
    ap.add_argument("--arch", default="resnet50", choices=sorted(ARCH_BUILDERS),
                    help="architecture to train; the builder comes from model_training.py")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--no-cache", action="store_true",
                    help="read and decode the frames again every epoch")
    args = ap.parse_args()

    apply_seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)

    train_rows, test_rows, class_names = read_split(args.split_csv)
    class_index = {c: i for i, c in enumerate(class_names)}
    num_classes = len(class_names)
    print("line            : {0}".format(args.line))
    print("architecture    : {0}  [{1}]".format(args.arch, ARCH_LABELS.get(args.arch, "")))
    print("split file      : {0}".format(args.split_csv))
    print("classes         : {0}".format(num_classes))
    print("train / test    : {0} / {1}".format(len(train_rows), len(test_rows)))
    print("batch / epochs  : {0} / {1}".format(args.batch_size, args.epochs))
    counts = {}
    for r in train_rows + test_rows:
        counts.setdefault(r["class"], [0, 0])
        counts[r["class"]][0 if r["split"] == "train" else 1] += 1
    for c in class_names:
        print("   {0:48s} train {1:5d}  test {2:5d}".format(c, counts[c][0], counts[c][1]))
    sys_stdout_flush()

    train_ds = make_ds(train_rows, class_index, True, args.batch_size, args.seed,
                       not args.no_cache)
    test_ds = make_ds(test_rows, class_index, False, args.batch_size, args.seed,
                      not args.no_cache)

    tf.keras.utils.set_random_seed(args.seed)
    model = ARCH_BUILDERS[args.arch](num_classes)
    model.compile(
        optimizer=tf.keras.optimizers.SGD(learning_rate=1e-4, momentum=0.9, nesterov=True),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    print("parameters      : {0:,}".format(model.count_params()))

    start_time = time.perf_counter()
    history = model.fit(train_ds, epochs=args.epochs)
    training_time = time.perf_counter() - start_time
    print("Total Training Time : {0:.2f} seconds".format(training_time))

    y_true = np.concatenate([labels.numpy() for _, labels in test_ds], axis=0)
    num_test_images = sum(images.shape[0] for images, _ in test_ds)

    start = time.perf_counter()
    y_pred_prob = model.predict(test_ds, verbose=1)
    total_time = time.perf_counter() - start
    y_pred = np.argmax(y_pred_prob, axis=1)

    accuracy = accuracy_score(y_true, y_pred)
    time_per_image = total_time / num_test_images
    print("Overall Accuracy : {0:.2f}%".format(accuracy * 100))
    print("Inference/image  : {0:.3f} ms".format(time_per_image * 1000))

    cm = confusion_matrix(y_true, y_pred, labels=list(range(num_classes)))
    class_accuracy = np.divide(cm.diagonal(), cm.sum(axis=1),
                               out=np.zeros(num_classes, dtype=float), where=cm.sum(axis=1) > 0)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(num_classes)), zero_division=0)
    macro_p, macro_r, macro_f1 = precision.mean(), recall.mean(), f1.mean()
    weighted_p = float(np.average(precision, weights=support))
    weighted_r = float(np.average(recall, weights=support))
    weighted_f1 = float(np.average(f1, weights=support))
    print("\nPer-class precision / recall / f1:")
    for cls, p, r, f, s in zip(class_names, precision, recall, f1, support):
        print("  {0:48s} prec={1:6.2f}%  rec={2:6.2f}%  f1={3:6.2f}%  n={4}".format(
            cls, p * 100, r * 100, f * 100, int(s)))
    print("\nMacro    precision={0:.2f}%  recall={1:.2f}%  f1={2:.2f}%".format(
        macro_p * 100, macro_r * 100, macro_f1 * 100))
    print("Weighted precision={0:.2f}%  recall={1:.2f}%  f1={2:.2f}%".format(
        weighted_p * 100, weighted_r * 100, weighted_f1 * 100))

    run_metrics = {
        "line": args.line,
        "arch": args.arch,
        "arch_label": ARCH_LABELS.get(args.arch, args.arch),
        "split_csv": os.path.abspath(args.split_csv),
        "preprocessing": "raw frame resized to 224x224 bilinear, no crop",
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "num_classes": num_classes,
        "class_names": class_names,
        "num_train_images": len(train_rows),
        "num_test_images": num_test_images,
        "per_class_support": {"train": {c: counts[c][0] for c in class_names},
                              "test": {c: counts[c][1] for c in class_names}},
        "overall_accuracy": round(float(accuracy), 4),
        "overall_recall": round(float(np.mean(class_accuracy)), 4),
        "training_time_sec": round(training_time, 2),
        "inference_total_sec": round(float(total_time), 4),
        "inference_per_image_ms": round(float(time_per_image * 1000), 3),
        "per_class": {cls: {"recall": round(float(r), 4), "precision": round(float(p), 4),
                            "f1": round(float(f), 4), "support": int(s)}
                      for cls, p, r, f, s in zip(class_names, precision, recall, f1, support)},
        "macro": {"precision": round(float(macro_p), 4), "recall": round(float(macro_r), 4),
                  "f1": round(float(macro_f1), 4)},
        "weighted": {"precision": round(weighted_p, 4), "recall": round(weighted_r, 4),
                     "f1": round(weighted_f1, 4)},
    }
    with open(os.path.join(args.outdir, "metrics.json"), "w") as fh:
        json.dump(run_metrics, fh, indent=2)
    with open(os.path.join(args.outdir, "history.json"), "w") as fh:
        json.dump({k: [float(x) for x in v] for k, v in history.history.items()}, fh, indent=2)

    with open(os.path.join(args.outdir, "confusion_matrix_{0}.csv".format(args.line)),
              "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["true\\predicted"] + class_names + ["support"])
        for i, cls in enumerate(class_names):
            w.writerow([cls] + list(cm[i]) + [int(cm[i].sum())])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 12))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    disp.plot(cmap="Blues", xticks_rotation=90, ax=ax, colorbar=False)
    plt.title("Confusion Matrix - {0} ({1}, raw frames, 70:30)".format(
        args.line, ARCH_LABELS.get(args.arch, args.arch)))
    plt.tight_layout()
    png = os.path.join(args.outdir, "confusion_matrix_{0}.png".format(args.line))
    plt.savefig(png, dpi=300, bbox_inches="tight")

    wpath = os.path.join(args.outdir, "weights.weights.h5")
    # Metrics, history and the confusion matrix are already on disk above. A full disk must
    # never cost a training run, so a failed weight write is a warning, not a failure.
    try:
        model.save_weights(wpath)
        print("Saved metrics, history, confusion matrix and weights to {0}".format(args.outdir))
    except Exception as exc:  # noqa: BLE001
        print("WARNING: metrics, history and confusion matrix are saved, but the weights could "
              "not be written to {0}: {1}".format(wpath, exc))
    return 0


def sys_stdout_flush():
    import sys
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
