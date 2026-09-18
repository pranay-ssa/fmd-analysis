#!/bin/bash
# OOI with warmup
DATA=/home/pranayp/OoI_dataset_single
BASE=/home/pranayp/ooi_warmup
ARCHS=(resnet18 resnet50 resnet50_inception resnet50_se)
mkdir -p "$BASE"
for arch in "${ARCHS[@]}"; do
  out="$BASE/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START $arch ====="
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" --warmup > "$out/run.log" 2>&1
  echo "===== [$(date -u +%FT%T)] DONE $arch rc=${PIPESTATUS[0]} ====="
done
# Lens presentation with warmup
DATA2=/home/pranayp/lens_presentation_dataset_single_20260903
BASE2=/home/pranayp/lens_warmup
mkdir -p "$BASE2"
for arch in "${ARCHS[@]}"; do
  out="$BASE2/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START $arch ====="
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA2" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" --warmup > "$out/run.log" 2>&1
  echo "===== [$(date -u +%FT%T)] DONE $arch rc=${PIPESTATUS[0]} ====="
done
echo "ALL WARMUP RUNS COMPLETE $(date -u)"
