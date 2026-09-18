#!/bin/bash
# Corrected warmup retrain: all 4 arches x (OOI + Lens), 50 epochs, batch 8, seed 42.
# Uses model_training.py --warmup (dummy passes + one real test-pipeline pass) so the
# measured ms/img excludes the one-time ~1.1s predict-graph re-trace.
DATA=/home/pranayp/OoI_dataset_single
BASE=/home/pranayp/ooi_warmup_corrected
ARCHS=(resnet18 resnet50 resnet50_inception resnet50_se)
mkdir -p "$BASE"
for arch in "${ARCHS[@]}"; do
  out="$BASE/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START OOI $arch ====="
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" --warmup > "$out/run.log" 2>&1
  echo "===== [$(date -u +%FT%T)] DONE OOI $arch rc=$? ====="
done
DATA2=/home/pranayp/lens_presentation_dataset_single_20260903
BASE2=/home/pranayp/lens_warmup_corrected
mkdir -p "$BASE2"
for arch in "${ARCHS[@]}"; do
  out="$BASE2/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START LENS $arch ====="
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA2" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" --warmup > "$out/run.log" 2>&1
  echo "===== [$(date -u +%FT%T)] DONE LENS $arch rc=$? ====="
done
echo "ALL CORRECTED WARMUP RUNS COMPLETE $(date -u)"