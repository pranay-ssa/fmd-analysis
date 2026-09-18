#!/bin/bash
set -u
# Experiment B: the complete per-line split with ResNet50-Inception MultiLevel MultiScale
# (the lead's Architecture 1, the "MultiLevelMultiScale" model), per line.
#
#   split  : the same five split.csv files the ResNet50 run used, unchanged
#   config : batch 4, 50 epochs, seed 42, raw frames resized to 224
#
# Estimated GPU time: about 75 minutes for all five lines (5,875 train pictures; the
# multi-scale architecture cost 495 s against ResNet50's 345 s on the earlier combined run,
# so about 1.4 times ResNet50 per picture).

EXPERIMENT=/home/pranayp/line_experiment_20260917
SPLITS=$EXPERIMENT/splits
OUT=$EXPERIMENT/multiscale/runs
TRAINER=$EXPERIMENT/train_line_model.py
PY=python3
ARCH=resnet50_inception
EPOCHS=50
BATCH=4

mkdir -p "$OUT"
for line in L24 L25 L26 L27 L31; do
  run="$OUT/$line/epochs_50"
  mkdir -p "$run"
  echo "===== [$(date -u +%FT%TZ)] START multiscale $line arch=$ARCH ====="
  "$PY" "$TRAINER" --line "$line" --arch "$ARCH" \
    --split-csv "$SPLITS/line_$line/split.csv" \
    --epochs "$EPOCHS" --batch-size "$BATCH" --seed 42 \
    --outdir "$run" > "$run/run.log" 2>&1
  rc=$?
  echo "===== [$(date -u +%FT%TZ)] DONE multiscale $line rc=$rc ====="
done
echo "MULTISCALE RUNS COMPLETE [$(date -u +%FT%TZ)]"
