#!/bin/bash
# OOI no-warmup rerun (2026-09-08) to verify the 2026-09-07 no-warmup numbers.
# Same params as yesterday: 50 epochs, batch 8, seed 42, NO --warmup flag.
DATA=/home/pranayp/OoI_dataset_single
BASE=/home/pranayp/ooi_no_warmup_20260908
ARCHS=(resnet18 resnet50 resnet50_inception resnet50_se)
mkdir -p "$BASE"
for arch in "${ARCHS[@]}"; do
  out="$BASE/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START OOI no-warm $arch ====="
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" > "$out/run.log" 2>&1
  echo "===== [$(date -u +%FT%T)] DONE OOI no-warm $arch rc=$? ====="
done
echo "ALL OOI NO-WARMUP RUNS COMPLETE $(date -u)"