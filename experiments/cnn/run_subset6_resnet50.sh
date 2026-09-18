#!/bin/bash
set -u
# Experiment A: ResNet50 on the six classes the lead highlighted, per line.
#
#   classes: Missing Primary Package, Multiple Lenses, Foreign Matter, Lens Off Center,
#            Missing Lens, HEMA Obstruction
#   split  : run/class_subset_6_20260917 -> /home/pranayp/line_experiment_20260917/subset6/splits
#   config : batch 4, 50 epochs, seed 42, raw frames resized to 224 (same as the full run)
#
# Estimated GPU time: about 30 minutes for all five lines (3,424 train pictures).

EXPERIMENT=/home/pranayp/line_experiment_20260917
SPLITS=$EXPERIMENT/subset6/splits
OUT=$EXPERIMENT/subset6/runs
TRAINER=$EXPERIMENT/train_line_model.py
PY=python3
ARCH=resnet50
EPOCHS=50
BATCH=4

mkdir -p "$OUT"
for line in L24 L25 L26 L27 L31; do
  run="$OUT/$line/epochs_50"
  mkdir -p "$run"
  echo "===== [$(date -u +%FT%TZ)] START subset6 $line arch=$ARCH ====="
  "$PY" "$TRAINER" --line "$line" --arch "$ARCH" \
    --split-csv "$SPLITS/line_$line/split.csv" \
    --epochs "$EPOCHS" --batch-size "$BATCH" --seed 42 \
    --outdir "$run" > "$run/run.log" 2>&1
  rc=$?
  echo "===== [$(date -u +%FT%TZ)] DONE subset6 $line rc=$rc ====="
done
echo "SUBSET6 RUNS COMPLETE [$(date -u +%FT%TZ)]"
