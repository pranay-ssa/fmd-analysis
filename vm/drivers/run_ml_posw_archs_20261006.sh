#!/bin/bash
# Pos-weight rerun of the four notebook architectures, 2026-10-06.
# Same recipe as ml_resnet50_posw (baseline + --pos-weight), one model at a time.
# The plain ResNet50 posw row already exists from 2026-10-05 and is not re-run.
# Sequential so timings stay clean. Output under runs/<arch>_posw_20261006/.
set -u
RUN=/home/pranayp/yolo_ooi/multilabel_lp_posw_20261005
ROOT=/home/amd100-user/FMD_Data_26082026/fmd_temp_images
ARCHS=(resnet50_inception resnet50_se resnet50_inception_attention resnet50_inception_refine)
mkdir -p "$RUN/logs_posw_archs"
cd "$RUN" || exit 1
for arch in "${ARCHS[@]}"; do
  out="$RUN/runs/${arch}_posw_20261006"
  mkdir -p "$out"
  echo "===== [$(date -u +%FT%T)] START $arch posw ====="
  python3 -u train.py \
    --arch "$arch" \
    --labels "$RUN/labels.csv" \
    --split "$RUN/splits/variant_80_20_two_way.csv" \
    --split-column split_named \
    --image-root "$ROOT" \
    --out "$out" \
    --epochs 50 --batch 8 --workers 8 \
    --optimizer sgd --lr 1e-4 --momentum 0.9 --weight-decay 1e-4 \
    --seed 42 \
    --pos-weight 2>&1 | tee "$RUN/logs_posw_archs/${arch}.log"
  rc=$?
  echo "===== [$(date -u +%FT%T)] DONE $arch posw rc=$rc ====="
done
echo "ALL POSW ARCH RUNS COMPLETE $(date -u)"
