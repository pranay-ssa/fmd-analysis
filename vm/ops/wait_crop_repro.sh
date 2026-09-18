#!/bin/bash
# Wait for crop_repro.py to finish both runs, then print the result summary.
# Usage: bash wait_crop_repro.sh [max_minutes]  (default 45)
#
# SECURITY: no passphrase in this file. Supply it per session (HANDOFF section 3):
#   export VM_SSH_PASSPHRASE='...'   # or let it prompt once with hidden input
MAX=$(( ${1:-45} * 60 ))

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

start=$(date +%s)
while :; do
  done=$(ssh -o ConnectTimeout=15 fmd-vm "grep -c 'ALL RUNS COMPLETE' /home/pranayp/yolo_ooi/crop_repro.log 2>/dev/null || true" 2>/dev/null | tr -d ' ')
  if [ "${done:-0}" -ge 1 ]; then
    echo "REPRO_DONE"
    ssh -o ConnectTimeout=15 fmd-vm "echo '=== crop_repro_summary.json ==='; cat /home/pranayp/yolo_ooi/crop_repro_summary.json 2>/dev/null; echo; ls /home/pranayp/yolo_ooi/runs/crop_repro/"
    exit 0
  fi
  now=$(date +%s)
  if [ $(( now-start )) -ge "$MAX" ]; then
    echo "TIMEOUT - not complete: $(ssh -o ConnectTimeout=15 fmd-vm "tail -n 3 /home/pranayp/yolo_ooi/crop_repro.log" 2>/dev/null)"
    exit 2
  fi
  sleep 45
done
