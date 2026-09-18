#!/bin/bash
# Wait until one more line has finished in the per-line run, then print that line's
# headline numbers and exit. Run it as a tracked background process with notify so
# the report arrives as soon as the line lands.
#
#   bash watch_line_run.sh <lines-already-finished>
#
# The run itself is a detached job on the VM; this only reads files, it never
# touches the training process.

SOCK="C:/Users/HP/.ssh/agent/s.1qvpj8J9ic.agent.bnM5w1zYjb"
export SSH_AUTH_SOCK="$SOCK"
EXPERIMENT=/home/pranayp/line_experiment_20260917
SEEN=${1:-0}
INTERVAL=45
MAX_TRIES=60          # 45 min cap per watcher

report() {
  cat <<'EOF'
--- master.log ---
EOF
  ssh -q -T fmd-vm "cat $EXPERIMENT/runs/master.log"
  cat <<'EOF'
--- finished lines, headline numbers ---
EOF
  ssh -q -T fmd-vm "python3 - <<'PY'
import json, os, glob
root = '/home/pranayp/line_experiment_20260917/runs'
for line in ('L24', 'L25', 'L26', 'L27', 'L31'):
    p = os.path.join(root, line, 'epochs_50', 'metrics.json')
    if not os.path.exists(p):
        print(line, 'still running or not started')
        continue
    d = json.load(open(p))
    print('{0}: acc {1:.2%}  macro F1 {2:.2%}  weighted F1 {3:.2%}  train {4} / test {5}  {6} classes  {7:.1f} min'.format(
        line, d['overall_accuracy'], d['macro']['f1'], d['weighted']['f1'],
        d['num_train_images'], d['num_test_images'], d['num_classes'],
        d['training_time_sec'] / 60.0))
    weak = sorted(d['per_class'].items(), key=lambda kv: kv[1]['f1'])[:4]
    print('    weakest by F1:', ', '.join('{0} {1:.2f} (n={2})'.format(k, v['f1'], v['support']) for k, v in weak))
PY"
}

for i in $(seq 1 $MAX_TRIES); do
  N=$(ssh -q -T fmd-vm "grep -c DONE $EXPERIMENT/runs/master.log" 2>/dev/null | tr -d '\r')
  if [ -n "$N" ] && [ "$N" -gt "$SEEN" ] 2>/dev/null; then
    echo "line-finished event: master.log now holds $N finished line(s)"
    report
    exit 0
  fi
  sleep $INTERVAL
done
echo "watcher timed out without a new finished line (still $SEEN)"
exit 1
