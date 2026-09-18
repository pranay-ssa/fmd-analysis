"""Diagnose the OOI-vs-lens inference time gap (ResNet50, batch 8).

Decomposes model.predict(test_ds) wall time into:
  A) full predict, pipeline cold (current model_training.py method after dummy warmup)
  B/C) pure data-pipeline iterate cost (trace+init vs warm decode)
  D) full predict, pipeline warm
  E) predict on pre-decoded in-RAM arrays (GPU + dispatch only)

Goal: prove the per-run fixed cost (real-file pipeline trace/init) dominates and
is not removed by the dummy-data warmup, and that it is ~equal across datasets.

Run on the VM A100:  python3 diag_pipeline_timing.py
"""
import os
import sys
import time
import json
import numpy as np
import tensorflow as tf
import keras
import keras_hub

sys.path.insert(0, os.path.expanduser("~"))
from model_training import arch_resnet50, apply_seed

apply_seed(42)
print("TF", tf.__version__, "GPUs", len(tf.config.list_physical_devices("GPU")), flush=True)

# One model, reused for both datasets (content-agnostic for timing; imagenet weights).
model = arch_resnet50(10)
model.compile(optimizer="sgd", loss="sparse_categorical_crossentropy", metrics=["accuracy"])


def measure(name, path):
    print("\n##### " + name + " #####", flush=True)
    test_ds = tf.keras.utils.image_dataset_from_directory(
        f"{path}/test", image_size=(224, 224), batch_size=8, shuffle=False)
    class_names = test_ds.class_names
    n = sum(len(os.listdir(os.path.join(f"{path}/test", c))) for c in class_names)
    nb = (n + 7) // 8
    print(f"  n={n}  full_batches={n // 8}  last_partial_or_rounded={nb}", flush=True)

    # Model warmup exactly like model_training.py --warmup (dummy from_tensor_slices, batch 8)
    dummy = tf.data.Dataset.from_tensor_slices(
        (tf.random.normal((64, 224, 224, 3)), tf.zeros((64,), dtype=tf.int32))).batch(8)
    _ = model.predict(dummy, verbose=0)
    _ = model.predict(dummy, verbose=0)
    print("  [model warmed via DUMMY data, like --warmup]", flush=True)

    t0 = time.perf_counter(); model.predict(test_ds, verbose=0); t1 = time.perf_counter()
    cold = t1 - t0
    print(f"  A full predict, pipeline COLD (current method): {cold:.3f}s  {cold*1000/n:.2f} ms/img  {cold/nb*1000:.1f} ms/batch", flush=True)

    # Warm the REAL file pipeline by iterating once
    t0 = time.perf_counter(); X = []; Y = []
    for im, lab in test_ds:
        X.append(im.numpy()); Y.append(lab.numpy())
    t1 = time.perf_counter(); it0 = t1 - t0
    X = np.concatenate(X, 0); Y = np.concatenate(Y, 0)
    print(f"  B iterate pipeline once (trace+init+decode): {it0:.3f}s  {it0*1000/n:.2f} ms/img", flush=True)

    t0 = time.perf_counter()
    for im, lab in test_ds:
        pass
    t1 = time.perf_counter(); itw = t1 - t0
    print(f"  C iterate pipeline again (warm decode only): {itw:.3f}s  {itw*1000/n:.2f} ms/img  {itw/nb*1000:.1f} ms/batch", flush=True)

    t0 = time.perf_counter(); model.predict(test_ds, verbose=0); t1 = time.perf_counter()
    fullw = t1 - t0
    print(f"  D full predict, pipeline WARM: {fullw:.3f}s  {fullw*1000/n:.2f} ms/img  {fullw/nb*1000:.1f} ms/batch", flush=True)

    dsXY = tf.data.Dataset.from_tensor_slices((X, Y)).batch(8)
    t0 = time.perf_counter(); model.predict(dsXY, verbose=0); t1 = time.perf_counter()
    gpu = t1 - t0
    print(f"  E predict on pre-decoded arrays (GPU+dispatch only): {gpu:.3f}s  {gpu*1000/n:.2f} ms/img  {gpu/nb*1000:.1f} ms/batch", flush=True)

    return dict(n=n, nb=nb, cold=cold, iter_first=it0, iter_warm=itw, warm_full=fullw, gpu=gpu)


res = {}
res["OOI"] = measure("OOI", os.path.expanduser("~/OoI_dataset_single"))
res["LENS"] = measure("LENS", os.path.expanduser("~/lens_presentation_dataset_single_20260903"))

print("\n===== SUMMARY =====", flush=True)
for k, v in res.items():
    print(k, {kk: round(vv, 4) for kk, vv in v.items()}, flush=True)
with open(os.path.expanduser("~/diag_pipeline_result.json"), "w") as fh:
    json.dump(res, fh, indent=2)
print("saved ~/diag_pipeline_result.json", flush=True)
