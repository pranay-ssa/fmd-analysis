#!/usr/bin/env bash
# Watch the shared A100 and launch the frozen 17-column CNN when it is quiet.
#
#   bash vm/drivers/launch_frozen17_training.sh wait
#   bash vm/drivers/launch_frozen17_training.sh now
#   DRY_RUN=1 bash vm/drivers/launch_frozen17_training.sh now
#
# Wait mode starts after QUIET_SECONDS (default 600) below 10,000 MiB used,
# below 20% utilisation, and no compute process that was not present at start.
# A new compute process resets the window.
#
# Run as pranayp. To survive the SSH session:
#   setsid nohup bash vm/drivers/launch_frozen17_training.sh wait \
#     >> .../nohup.out 2>&1 < /dev/null &
#
# Stop: kill "$(cat .../watcher.pid)" or touch .../watcher.stop
set -euo pipefail
cd /home/pranayp/fmd-analysis

MODE="${1:-wait}"
case "$MODE" in
  wait|now) ;;
  *) echo "usage: $0 <wait|now>" >&2; exit 2 ;;
esac

OUT="/home/pranayp/frozen_data_experiments/multilabel_cnn/runs/20261119_resnet50_224_seed42"
TABLE="/home/pranayp/frozen_data_experiments/splits/frozen_70_15_15_20261119/labels_17.csv"
IMAGES="/data/FMD_Data_26082026/frozen_data_20261117/images"
PYTHON="/home/pranayp/fmd-analysis/.venv/bin/python"
LOG="$OUT/watcher.log"
RUN_LOG="$OUT/run.log"
STATUS="$OUT/watcher_status.json"
PIDFILE="$OUT/watcher.pid"
STOPFILE="$OUT/watcher.stop"
QUIET="${QUIET_SECONDS:-600}"
CHECK="${CHECK_SECONDS:-60}"
MAX_WAIT="${MAX_WAIT_SECONDS:-43200}"

mkdir -p "$OUT"
exec 9>"$OUT/watcher.lock"
flock -n 9 || { echo "$(date -Is) another watcher holds the lock" >> "$LOG"; exit 1; }

STARTED="$(date -Is)"
START_EPOCH="$(date +%s)"
LAST_MEM=""
LAST_UTIL=""
LAST_QUIET=0
echo $$ > "$PIDFILE"

log() { echo "$(date -Is) $*" >> "$LOG"; }

write_status() {
  local status="$1" mem="${2:-}" util="${3:-}" quiet="${4:-0}" launched="${5:-}"
  local mem_json="${mem:-null}" util_json="${util:-null}" launched_json="null"
  [ -n "$launched" ] && launched_json="\"$launched\""
  cat > "$STATUS" <<EOF
{
 "pid": $$,
 "status": "$status",
 "started_at": "$STARTED",
 "checked_at": "$(date -Is)",
 "mode": "$MODE",
 "policy": {"quiet_seconds": $QUIET, "check_seconds": $CHECK, "max_wait_seconds": $MAX_WAIT, "memory_ceiling_mib": 10000, "utilization_ceiling_pct": 20},
 "gpu": {"memory_used_mib": $mem_json, "utilization_pct": $util_json, "quiet_seconds_so_far": $quiet},
 "launched_at": $launched_json,
 "log": "$LOG",
 "run_log": "$RUN_LOG"
}
EOF
}

trap 'log "terminated by signal"; write_status "terminated" "$LAST_MEM" "$LAST_UTIL" "$LAST_QUIET"; exit 0' INT TERM

log "watcher pid=$$ mode=$MODE host=$(hostname) started=$STARTED"
log "policy: quiet ${QUIET}s, check ${CHECK}s, max wait ${MAX_WAIT}s, mem<10000 MiB, util<20%, new PID resets"
write_status "watching"

if [ "$MODE" = "wait" ]; then
  baseline="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits | tr -d ' ' | sort | tr '\n' ' ')"
  log "baseline compute pids: ${baseline:-none}"
  free_since=""
  while true; do
    now="$(date +%s)"
    if [ -f "$STOPFILE" ]; then
      log "stop file found: $STOPFILE"
      write_status "stopped" "$LAST_MEM" "$LAST_UTIL" "$LAST_QUIET"
      exit 0
    fi
    if [ "$MAX_WAIT" -gt 0 ] && [ $((now - START_EPOCH)) -ge "$MAX_WAIT" ]; then
      log "max wait ${MAX_WAIT}s reached without a quiet window"
      write_status "timed_out" "$LAST_MEM" "$LAST_UTIL" "$LAST_QUIET"
      exit 0
    fi
    line="$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ' ')"
    mem="${line%,*}"; util="${line#*,}"
    LAST_MEM="$mem"; LAST_UTIL="$util"
    pids="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits | tr -d ' ' | sort)"
    new_pid=""
    for pid in $pids; do
      case " $baseline " in *" $pid "*) ;; *) new_pid="$pid" ;; esac
    done
    busy=0
    [ "$mem" -ge 10000 ] && busy=1
    [ "$util" -ge 20 ] && busy=1
    [ -n "$new_pid" ] && busy=1
    if [ "$busy" -eq 0 ]; then
      [ -z "$free_since" ] && { free_since="$now"; log "GPU quiet, quiet window starts"; }
      waited=$((now - free_since))
      LAST_QUIET="$waited"
      log "quiet ${waited}s/${QUIET} mem=${mem}MiB util=${util}% new=none"
      write_status "watching" "$mem" "$util" "$waited"
      [ "$waited" -ge "$QUIET" ] && { log "quiet window complete, launching"; break; }
    else
      if [ -n "$free_since" ]; then log "busy again, quiet window reset (new=${new_pid:-none})"; fi
      free_since=""
      LAST_QUIET=0
      log "busy mem=${mem}MiB util=${util}% new=${new_pid:-none}"
      write_status "watching" "$mem" "$util" 0
    fi
    sleep "$CHECK"
  done
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  log "dry run: training not started"
  write_status "dry_run"
  exit 0
fi

LAUNCHED="$(date -Is)"
write_status "launched" "$LAST_MEM" "$LAST_UTIL" "$LAST_QUIET" "$LAUNCHED"
log "launch $LAUNCHED columns=frozen17 table=$TABLE"
exec env PYTHONUNBUFFERED=1 "$PYTHON" experiments/multilabel_ooi/train_multilabel.py \
  --columns frozen17 \
  --table "$TABLE" \
  --image-root "$IMAGES" \
  --out "$OUT" \
  --arch resnet50 \
  --imgsz 224 \
  --batch 8 \
  --epochs 50 \
  --lr 1e-4 \
  --seed 42 \
  --pos-weight on \
  --expect-counts on \
  --workers 8 >> "$RUN_LOG" 2>&1
