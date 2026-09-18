#!/bin/bash
# Remote env/readiness check for the batch-2 run (executed via: ssh fmd-vm 'bash -s' < vm_check.sh)
echo "== host =="
hostname
echo "== gpu =="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader || echo "nvidia-smi FAILED"
echo "== python/env =="
python3 -V
python3 -c "import ultralytics, torch; print('ultralytics', ultralytics.__version__); print('torch', torch.__version__); print('cuda_avail', torch.cuda.is_available())" || echo "import FAILED"
echo "== yolo_ooi dir =="
ls /home/pranayp/yolo_ooi/ | head -40
echo "== experiments =="
ls /home/pranayp/yolo_ooi/experiments/ 2>/dev/null || echo "NO experiments dir"
echo "== dataset_obb =="
ls /home/pranayp/yolo_ooi/dataset_obb/ 2>/dev/null
echo "val images: $(ls /home/pranayp/yolo_ooi/dataset_obb/images/val 2>/dev/null | wc -l)"
echo "val labels: $(ls /home/pranayp/yolo_ooi/dataset_obb/labels/val 2>/dev/null | wc -l)"
echo "== running procs =="
ps aux | grep -c "[r]un_batch" || true
ps aux | grep "[y]olo" | grep -v grep | head -5 || true
