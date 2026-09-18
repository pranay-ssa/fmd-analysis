#!/bin/bash
# Combined 22-class training matrix (2026-09-08): all 4 architectures, 50 epochs,
# batch 8, seed 42, with corrected warmup so ms/img is the true forward pass.
DATA=/home/pranayp/combined_dataset_single_20260908
BASE=/home/pranayp/combined_22_runs
ARCHS=(resnet18 resnet50 resnet50_inception resnet50_se)
mkdir -p "$BASE"
for arch in "${ARCHS[@]}"; do
  out="$BASE/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START combined22 $arch ====="
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" --warmup > "$out/run.log" 2>&1
  echo "===== [$(date -u +%FT%T)] DONE combined22 $arch rc=$? ====="
done
echo "ALL COMBINED-22 RUNS COMPLETE $(date -u)"