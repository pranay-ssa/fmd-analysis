#!/usr/bin/env bash
# Launch one Experiment 3.1 gate4 training arm on the VM.
#
#   ./launch_exp3_1_gate4.sh 224 wait
#   ./launch_exp3_1_gate4.sh 448 now
#
# Run as pranayp. Wait mode starts after QUIET_SECONDS of a free GPU (default 60, not the
# 600 used by the detector launcher, because this run is on a two-hour deadline).
set -euo pipefail
cd /home/pranayp/fmd-analysis

ARM="${1:?usage: $0 <224|448> <wait|now>}"
MODE="${2:-wait}"
case "$ARM" in
  224|448) ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac

OUT="run/exp3_1_gate4_${ARM}_20261117"
mkdir -p "$OUT"
LOG="${OUT}/launch.log"
echo "arm=${ARM} mode=${MODE} host=$(hostname) started=$(date -Is)" >> "$LOG"

if [ "$MODE" = "wait" ]; then
  baseline="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits | tr -d ' ' | sort | tr '\n' ' ')"
  # A queued second arm must treat every process as a newcomer, including one that was
  # already running when it was queued. Set BASELINE_EMPTY=1 for the queued arm.
  if [ "${BASELINE_EMPTY:-0}" = "1" ]; then baseline=""; fi
  free_since=""
  grace="${QUIET_SECONDS:-60}"
  check="${CHECK_SECONDS:-20}"
  while true; do
    line="$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr -d ' ')"
    mem="${line%,*}"; util="${line#*,}"
    pids="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits | tr -d ' ' | sort)"
    new_pid=""
    for pid in $pids; do
      case " $baseline " in *" $pid "*) ;; *) new_pid="$pid" ;; esac
    done
    busy=0
    [ "$mem" -ge 10000 ] && busy=1
    [ "$util" -ge 20 ] && busy=1
    [ -n "$new_pid" ] && busy=1
    now="$(date +%s)"
    if [ "$busy" -eq 0 ]; then
      [ -z "$free_since" ] && { free_since="$now"; echo "$(date -Is) GPU free, quiet window starts" >> "$LOG"; }
      waited=$((now - free_since))
      echo "$(date -Is) free ${waited}s/${grace} mem=${mem}MiB util=${util}% new=none" >> "$LOG"
      [ "$waited" -ge "$grace" ] && { echo "$(date -Is) starting training" >> "$LOG"; break; }
    else
      free_since=""
      echo "$(date -Is) busy mem=${mem}MiB util=${util}% new=${new_pid:-none}" >> "$LOG"
    fi
    sleep "$check"
  done
fi

echo "launch $(date -Is) arm=${ARM} imgsz=${ARM}" >> "$LOG"
exec /usr/bin/python3.12 experiments/multilabel_ooi/train_multilabel.py \
  --columns gate4 \
  --table run/split_exp3_1_20261116/labels.csv \
  --arch resnet50 \
  --imgsz "$ARM" \
  --batch 8 \
  --epochs 50 \
  --lr 1e-4 \
  --seed 42 \
  --pos-weight on \
  --workers 8 \
  --image-root /data/FMD_Data_26082026/fmd_temp_images \
  --out "$OUT" >> "$LOG" 2>&1
