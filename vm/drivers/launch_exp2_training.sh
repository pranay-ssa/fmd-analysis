#!/usr/bin/env bash
# Stage or launch one Experiment 2 training arm on the VM.
#
#   ./launch_exp2_training.sh all wait       # primary arm, wait for the GPU
#   ./launch_exp2_training.sh objects now    # boxed-only arm, GPU already free
#
# Run as pranayp. The wait mode checks for 10 GB free and 20% utilisation for
# three consecutive minutes before starting, so it does not contend with another
# user's job.
set -euo pipefail
cd /home/pranayp/fmd-analysis

ARM="${1:-all}"
MODE="${2:-wait}"
case "$ARM" in
  all)
    DATA="/data/FMD_Data_26082026/fmd_detector_20261110/data_all.yaml"
    NAME="yolo26n_fmd_7cls_all"
    ;;
  objects)
    DATA="/data/FMD_Data_26082026/fmd_detector_20261110/data_objects.yaml"
    NAME="yolo26n_fmd_7cls_objects"
    ;;
  *)
    echo "usage: $0 <all|objects> <wait|now>" >&2
    exit 2
    ;;
esac

mkdir -p run/detector_20261110
LOG="run/detector_20261110/${NAME}.log"
echo "arm=${ARM} mode=${MODE} host=$(hostname) started=$(date -Is)" >> "$LOG"

if [ "$MODE" = "wait" ]; then
  baseline="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits | tr -d ' ' | sort | tr '\n' ' ')"
  free_since=""
  grace="${GRACE_SECONDS:-600}"
  check="${CHECK_SECONDS:-60}"
  while true; do
    line="$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr -d ' ')"
    mem="${line%,*}"
    util="${line#*,}"
    pids="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits | tr -d ' ' | sort)"
    new_pid=""
    for pid in $pids; do
      case " $baseline " in
        *" $pid "*) ;;
        *) new_pid="$pid" ;;
      esac
    done
    busy=0
    if [ "$mem" -ge 10000 ]; then busy=1; fi
    if [ "$util" -ge 20 ]; then busy=1; fi
    if [ -n "$new_pid" ]; then busy=1; fi

    now="$(date +%s)"
    if [ "$busy" -eq 0 ]; then
      if [ -z "$free_since" ]; then
        free_since="$now"
        echo "$(date -Is) GPU free, 10-minute quiet window starts" >> "$LOG"
      fi
      waited=$((now - free_since))
      echo "$(date -Is) free ${waited}s/600 mem=${mem}MiB util=${util}% new=none" >> "$LOG"
      if [ "$waited" -ge "$grace" ]; then
        echo "$(date -Is) 10 minutes quiet, starting training" >> "$LOG"
        break
      fi
    else
      if [ -n "$free_since" ]; then
        echo "$(date -Is) another process started, quiet window reset" >> "$LOG"
      fi
      free_since=""
      echo "$(date -Is) busy mem=${mem}MiB util=${util}% new=${new_pid:-none}" >> "$LOG"
    fi
    sleep "$check"
  done
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "dry run: training not started" >> "$LOG"
  exit 0
fi

echo "launch $(date -Is) arm=${ARM}" >> "$LOG"
exec /usr/bin/python3.12 vm/drivers/run_yolo26_fmd_detector.py --data "$DATA" --name "$NAME" >> "$LOG" 2>&1
