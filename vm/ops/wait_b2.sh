#!/bin/bash
# Wait up to N sec for depth_plus2_deep/results.csv to reach 101 lines (header + 100 epochs),
# and print "DONE" when both runs are complete per the driver log.
#
# NOTE: historical script from the pre-reorg batch-2 runs; the paths below belong to the old
# layout (`runs/yolo_arch/`). Kept for the record, not for reuse.
#
# SECURITY: no passphrase in this file. Supply it per session (HANDOFF section 3):
#   export VM_SSH_PASSPHRASE='...'   # or let it prompt once
MAX="${1:-300}"

PASS="${VM_SSH_PASSPHRASE:-}"
if [ -z "$PASS" ]; then
  read -r -s -p "VM passphrase for fmd-vm: " PASS
  echo
fi
ASK="$(mktemp "${TMPDIR:-/tmp}/vm_ask.XXXXXX")"
trap 'rm -f "$ASK"' EXIT
printf '#!/bin/bash\nprintf "%%s\\n" %q\n' "$PASS" > "$ASK"
chmod 700 "$ASK"
unset PASS
export SSH_ASKPASS="$ASK" SSH_ASKPASS_REQUIRE=force DISPLAY=:0

lines=0
while [ "${lines:-0}" -lt 101 ]; do
  now=$(date +%s)
  lines=$(ssh -o ConnectTimeout=10 fmd-vm "wc -l < /home/pranayp/yolo_ooi/runs/yolo_arch/depth_plus2_deep/results.csv" 2>/dev/null | tr -d ' ')
  echo "[$(date +%H:%M:%S)] depth_plus2_deep/results.csv lines=$lines"
  if [ "${lines:-0}" -ge 101 ]; then
    echo "DEPTH_CSV_DONE"
    break
  fi
  if ssh -o ConnectTimeout=10 fmd-vm "grep -q 'ALL RUNS COMPLETE' /home/pranayp/yolo_ooi/batch2_b8.log" 2>/dev/null; then
    echo "ALL_RUNS_COMPLETE"
    break
  fi
  sleep 20
done
