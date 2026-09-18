#!/usr/bin/env python3
"""
Re-measure inference per image for the five per-line models, with the warmup the
earlier protocol used, from the saved weights.

Why: the training runs recorded inference_per_image_ms without a warmup pass, so
that figure carries the one-time XLA graph trace and cuDNN autotune cost and is
not comparable with the six-architecture table. Weights were saved for exactly
this reason, so no retraining is needed.

Two numbers per line, both reported:
  * end to end, decode included: reads each test frame from disk, decodes the BMP,
    resizes to 224, runs the model. This is the operational number.
  * model only: the same test set already decoded and in memory, so the figure
    covers batch assembly and the forward pass. This is the one comparable with
    the crop-based table, where decoding was also in the pipeline but the files
    were small crops rather than 5 MB frames.

    python3 measure_line_inference.py --experiment /home/pranayp/line_experiment_20260917 \
        --out /home/pranayp/line_experiment_20260917/inference_warm.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

import numpy as np
import tensorflow as tf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_line_model import arch_resnet50, make_ds, read_split  # noqa: E402

LINES = ["L24", "L25", "L26", "L27", "L31"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    results = {}
    for line in LINES:
        run = os.path.join(args.experiment, "runs", line, "epochs_50")
        split = os.path.join(args.experiment, "splits", "line_{0}".format(line), "split.csv")
        weights = os.path.join(run, "weights.weights.h5")
        metrics = json.load(open(os.path.join(run, "metrics.json")))
        classes = metrics["class_names"]
        index = {c: i for i, c in enumerate(classes)}
        _, test_rows, _ = read_split(split)
        n = len(test_rows)

        tf.keras.utils.set_random_seed(args.seed)
        model = arch_resnet50(len(classes))
        model.load_weights(weights)

        # end to end: fresh file reads, decode, resize, forward pass
        ds_raw = make_ds(test_rows, index, False, args.batch_size, args.seed, cache=False)
        _ = model.predict(ds_raw, verbose=0)
        t0 = time.perf_counter()
        _ = model.predict(ds_raw, verbose=0)
        end_to_end = time.perf_counter() - t0

        # model only: the same set decoded once and served from memory
        ds_cached = make_ds(test_rows, index, False, args.batch_size, args.seed, cache=True)
        _ = model.predict(ds_cached, verbose=0)
        t1 = time.perf_counter()
        _ = model.predict(ds_cached, verbose=0)
        model_only = time.perf_counter() - t1

        results[line] = {
            "test_images": n,
            "classes": len(classes),
            "inference_end_to_end_ms": round(end_to_end / n * 1000, 3),
            "inference_model_only_ms": round(model_only / n * 1000, 3),
            "recorded_without_warmup_ms": metrics["inference_per_image_ms"],
            "batch_size": args.batch_size,
        }
        print("{0}: test {1}, end to end {2} ms/img, model only {3} ms/img, recorded without warmup {4} ms/img".format(
            line, n, results[line]["inference_end_to_end_ms"], results[line]["inference_model_only_ms"],
            results[line]["recorded_without_warmup_ms"]))
        sys.stdout.flush()

    with open(args.out, "w") as fh:
        json.dump({"protocol": "warm: one discarded real-pipeline pass before each timed pass",
                   "note": "end to end includes reading and decoding a 5 MB BMP per image",
                   "lines": results}, fh, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
