#!/bin/bash
set -u
# The two experiments the lead asked for on 2026-09-17, in order, for one launch:
#   A. the six highlighted classes with ResNet50            (~30 min)
#   B. the complete split with MultiLevelMultiScale (Arch 1) (~75 min)
#
# ResNet50 on the complete split already ran on 2026-09-17 (runs/), so it is not repeated.
#
# Run it when the GPU is free:
#   bash check_gpu_free.sh && setsid nohup bash run_next_experiments.sh \
#       > /home/pranayp/line_experiment_20260917/next_experiments.log 2>&1 &
#
# Nothing starts until the first python line runs, so launching it early is safe: it will
# simply queue behind whatever holds the GPU, which is why check_gpu_free.sh is in front.

EXPERIMENT=/home/pranayp/line_experiment_20260917

FREE_MB=$(df -m --output=avail /home | tail -1 | tr -d ' ')
echo "free space on /home: ${FREE_MB} MiB"
if [ "${FREE_MB:-0}" -lt 4000 ]; then
  echo "WARNING: under 4 GB free. Each run writes about 0.2 GB (ResNet50) or 0.5 GB"
  echo "         (multi-scale) of weights. Training still completes and the metrics and"
  echo "         confusion matrix are still written; only the weights can fail."
fi

echo "===== [$(date -u +%FT%TZ)] EXPERIMENTS START ====="
echo "--- A: six highlighted classes, ResNet50 ---"
bash "$EXPERIMENT/run_subset6_resnet50.sh"
echo "--- B: complete split, ResNet50-Inception MultiLevelMultiScale ---"
bash "$EXPERIMENT/run_multiscale_full.sh"
echo "===== [$(date -u +%FT%TZ)] EXPERIMENTS COMPLETE ====="
