#!/bin/bash
set -u
BASE=/home/pranayp/merge_analysis/bubble_full_merge
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_NUM_INTRAOP_THREADS=5
export TF_NUM_INTEROP_THREADS=2
export PYTHONPATH="/home/pranayp:${PYTHONPATH:-}"
cd "$BASE" || exit 11
mkdir -p runs2
echo "===== $(date -u +%FT%T) launch bubble_full_merge run2 (dump+save) ====="
nohup python3 /home/pranayp/model_training.py \
  --arch resnet50_inception --data exp \
  --epochs 50 --batch-size 8 --seed 42 \
  --dump --save-model \
  --outdir runs2/bubble_full_merge > runs2/bubble_full_merge.log 2>&1 &
echo "PID=$!"
echo "===== launched $(date -u +%FT%T) ====="
