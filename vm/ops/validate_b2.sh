#!/bin/bash
# VM-side: GPU occupant elapsed time, then build both batch-2 models, print params/GFLOPs.
cd /home/pranayp/yolo_ooi || exit 1
echo "== gpu apps =="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader || echo none
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null); do
  echo "pid $p elapsed_s: $(ps -o etimes= -p $p 2>/dev/null || echo gone)"
done
echo "== model build + info =="
python3 - <<'PY'
from ultralytics import YOLO
for f in ["experiments/baseline_obb.yaml", "experiments/depth_plus2_deep_obb.yaml"]:
    m = YOLO(f)
    params = sum(p.numel() for p in m.model.parameters())
    info = None
    try:
        info = m.model.info(verbose=False)
    except Exception as e:
        print("info fallback:", e)
    gflops = float(info[3]) if isinstance(info, (list, tuple)) and len(info) >= 4 else None
    print(f, "| params", params, "| gflops", gflops)
PY
