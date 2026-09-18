#!/bin/bash
DATA=/home/pranayp/OoI_dataset_single
BASE=/home/pranayp/ooi_single_model_runs
ARCHS=(resnet18 resnet50 resnet50_inception resnet50_se)
EPOCHS=(50)
mkdir -p "$BASE"
for arch in "${ARCHS[@]}"; do
  for ep in "${EPOCHS[@]}"; do
    out="$BASE/${arch}/epochs_${ep}"
    mkdir -p "$out"
    echo "===== [$(date -u +%FT%T)] START single-scale $arch epochs=$ep ====="
    python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA" \
      --epochs "$ep" --batch-size 8 --seed 42 --outdir "$out" > "$out/run.log" 2>&1
    echo "===== [$(date -u +%FT%T)] DONE $arch epochs=$ep rc=${PIPESTATUS[0]} ====="
  done
done
echo "ALL SINGLE-SCALE RUNS COMPLETE $(date -u)"
