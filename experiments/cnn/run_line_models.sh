#!/bin/bash
set -u          # an unset variable must stop the script, not run an empty command
# Step 4: five per-line ResNet50 models, 70:30, batch 4, 50 epochs.
#
# One model per production line, trained on that line's train half and scored on
# its test half. Input is the raw 2448x2048 frame resized to 224x224 (no crop),
# per the instruction of 2026-09-17; the earlier combined-22 run used fixed-size
# crops, so the two are not directly comparable.
#
# Runs are sequential on purpose: the box is shared and one A100 is the resource.
#
#   nohup bash run_line_models.sh > runs/master.log 2>&1 &

ROOT=/data/FMD_Data_26082026
EXPERIMENT=/home/pranayp/line_experiment_20260917
SPLITS=$EXPERIMENT/splits
OUT=$EXPERIMENT/runs
TRAINER=$EXPERIMENT/train_line_model.py
PY=python3
EPOCHS=50
BATCH=4

mkdir -p "$OUT"
for line in L24 L25 L26 L27 L31; do
  run="$OUT/$line/epochs_50"
  mkdir -p "$run"
  echo "===== [$(date -u +%FT%TZ)] START $line  (epochs $EPOCHS, batch $BATCH) ====="
  "$PY" "$TRAINER" --line "$line" \
    --split-csv "$SPLITS/line_$line/split.csv" \
    --epochs "$EPOCHS" --batch-size "$BATCH" --seed 42 \
    --outdir "$run" > "$run/run.log" 2>&1
  rc=$?
  echo "===== [$(date -u +%FT%TZ)] DONE $line rc=$rc ====="
done
echo "ALL FIVE LINE RUNS COMPLETE [$(date -u +%FT%TZ)]"
