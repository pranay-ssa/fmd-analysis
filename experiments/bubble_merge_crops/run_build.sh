#!/bin/bash
# Full OOI crop extraction + split build (2026-10-08).
# Run as pranayp. Writes extract.log, split.log under bubble_merge_crops/.
set -u
BASE=/home/pranayp/merge_analysis/bubble_merge_crops
cd "$BASE" || exit 11

echo "===== START extract $(date -u +%FT%T) ====="
python3 extract_crops.py \
  --annotations-old annotations.xml \
  --annotations-new updated_annotations_20260922.xml \
  --images-root /data/FMD_Data_26082026/fmd_temp_images \
  --path-manifest /home/pranayp/merge_analysis/image_path_manifest.csv \
  --out . > extract.log 2>&1
rc1=$?
echo "extract rc=$rc1"
tail -15 extract.log

if [ "$rc1" -ne 0 ]; then
  echo "EXTRACT FAILED, stopping"
  exit "$rc1"
fi

echo "===== START split $(date -u +%FT%T) ====="
python3 build_splits.py --crops . --out . --seed 42 --test-ratio 0.30 > split.log 2>&1
rc2=$?
echo "split rc=$rc2"
tail -30 split.log

echo "===== ALL DONE $(date -u +%FT%T) rc=$rc2 ====="
