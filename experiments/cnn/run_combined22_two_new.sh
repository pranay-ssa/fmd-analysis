#!/bin/bash
# Combined 22-class training, the two NEW architectures only (2026-09-15).
# FMD arch 3 = resnet50_inception_attention  (Inception blocks with SE attention per branch)
# FMD arch 4 = resnet50_inception_refine     (Inception blocks + bicubic upsample + depthwise refinement on L5)
# Everything else matches run_combined_22.sh: same dataset, 50 epochs, batch 8,
# seed 42, warmup on, and the same output tree so the landing-pad workbook finds them.
DATA=/home/pranayp/combined_dataset_single_20260908
BASE=/home/pranayp/combined_22_runs
MASTER="$BASE/two_new_master.log"
ARCHS=(resnet50_inception_attention resnet50_inception_refine)
mkdir -p "$BASE"
for arch in "${ARCHS[@]}"; do
  out="$BASE/${arch}/epochs_50"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START combined22 $arch =====" | tee -a "$MASTER"
  python3 /home/pranayp/model_training.py --arch "$arch" --data "$DATA" \
    --epochs 50 --batch-size 8 --seed 42 --outdir "$out" --warmup > "$out/run.log" 2>&1
  rc=$?
  echo "===== [$(date -u +%FT%T)] DONE combined22 $arch rc=$rc =====" | tee -a "$MASTER"
done
echo "ALL TWO-NEW RUNS COMPLETE $(date -u)" | tee -a "$MASTER"
