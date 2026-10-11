#!/bin/bash
# OOI crops wing: two MultiScale runs (2026-10-08).
# exp_a = 7 classes (cluster separate), exp_b = 6 classes (cluster merged).
# Frozen recipe: 50 epochs, batch 8, seed 42, SGD lr 1e-4, 224x224, NO warmup.
# Shared image-level split (seed 42) -> identical test images in both runs.
set -u
BASE=/home/pranayp/merge_analysis/bubble_merge_crops
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_NUM_INTRAOP_THREADS=5
export TF_NUM_INTEROP_THREADS=2
cd "$BASE" || exit 11

mkdir -p runs
echo "===== $(date -u +%FT%T) launch both ====="

nohup python3 /home/pranayp/model_training.py \
  --arch resnet50_inception --data exp_a \
  --epochs 50 --batch-size 8 --seed 42 \
  --outdir runs/exp_a > runs/exp_a.log 2>&1 &
echo "exp_a PID=$!"

nohup python3 /home/pranayp/model_training.py \
  --arch resnet50_inception --data exp_b \
  --epochs 50 --batch-size 8 --seed 42 \
  --outdir runs/exp_b > runs/exp_b.log 2>&1 &
echo "exp_b PID=$!"

echo "===== launched $(date -u +%FT%T) ====="
