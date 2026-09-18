#!/bin/bash
# VM-side: GPU occupants + built-model params for the batch-3 ablation forks.
cd /home/pranayp/yolo_ooi || exit 1
echo "== gpu apps =="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader || echo none
echo "== params =="
python3 - <<'PY'
from ultralytics import YOLO
for f in ["experiments/armA_residual_deep_obb.yaml", "experiments/armB_conv_p4_obb.yaml"]:
    m = YOLO(f)
    p = sum(x.numel() for x in m.model.parameters())
    print(f, "| params", p)
PY