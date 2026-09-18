#!/bin/bash
# Watch a run log on the VM and report each line as it finishes.
#
#   bash watch_run_log.sh <log path on the VM> <marker> <final marker>
#   bash watch_run_log.sh /home/pranayp/line_experiment_20260917/subset6_run.log subset6 "SUBSET6 RUNS COMPLETE"
#
# Prints a line only when a new completion appears, so a notification means something happened
# rather than "the watcher is still alive". Exits when the final marker appears or after the
# guard loop runs out.

LOG="${1:?log path required}"
MARKER="${2:-DONE}"
FINAL="${3:-COMPLETE}"
SSH_HOST="${4:-fmd-vm}"
GUARD=${GUARD:-90}          # 90 polls of 45 s is about 68 minutes

seen=0
for _ in $(seq 1 "$GUARD"); do
  n=$(ssh -q -T "$SSH_HOST" "grep -c 'DONE $MARKER' '$LOG' 2>/dev/null || echo 0" 2>/dev/null)
  n=${n:-$seen}
  if [ "$n" -gt "$seen" ] 2>/dev/null; then
    ssh -q -T "$SSH_HOST" "grep 'DONE $MARKER' '$LOG' | tail -n $((n - seen))" 2>/dev/null
    seen=$n
  fi
  if ssh -q -T "$SSH_HOST" "grep -q '$FINAL' '$LOG' 2>/dev/null" 2>/dev/null; then
    echo "WATCHER: $FINAL seen, run finished"
    exit 0
  fi
  sleep 45
done
echo "WATCHER: guard ran out after $GUARD polls, last seen $seen completed lines"
