#!/bin/bash
# Multilabel LP architecture sweep, 2026-09-29.
# Four notebook architectures plus a plain ResNet50 control re-run, one at a time on
# the A100 (sequential so the per-image inference timings are not polluted by a
# second job). Same recipe as ml_resnet50_base: SGD lr 1e-4 Nesterov, no warmup in the
# optimizer sense (there is none in the recipe), batch 8, 50 epochs, seed 42, 224x224,
# no augmentation, two-way 80/20 split (split_named), all 3,377 LP rows.
set -u
RUN=/home/pranayp/yolo_ooi/multilabel_lp_archs_20260929
ROOT=/home/amd100-user/FMD_Data_26082026/fmd_temp_images
ARCHS=(resnet50 resnet50_inception resnet50_se resnet50_inception_attention resnet50_inception_refine)
mkdir -p "$RUN/logs"
cd "$RUN" || exit 1
for arch in "${ARCHS[@]}"; do
  out="$RUN/runs/${arch}_20260929"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START $arch ====="
  python3 -u train.py \
    --arch "$arch" \
    --labels "$RUN/labels.csv" \
    --split "$RUN/splits/variant_80_20_two_way.csv" \
    --split-column split_named \
    --image-root "$ROOT" \
    --out "$out" \
    --epochs 50 --batch 8 --workers 8 \
    --optimizer sgd --lr 1e-4 --momentum 0.9 --weight-decay 1e-4 \
    --seed 42 2>&1 | tee "$RUN/logs/${arch}.log"
  rc=$?
  echo "===== [$(date -u +%FT%T)] DONE $arch rc=$rc ====="
done
echo "ALL ARCH RUNS COMPLETE $(date -u)"
