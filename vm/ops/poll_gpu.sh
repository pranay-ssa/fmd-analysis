#!/bin/bash
# Bounded GPU poll: waits until no compute-app process is running on the A100.
# Usage: bash poll_gpu.sh [max_minutes]   (default 12)
#
# SECURITY: the VM key is passphrase-protected and there is no ssh-agent, but the
# passphrase must NEVER be stored in a file (repo rule, HANDOFF section 3). Supply it
# per session, either way:
#   export VM_SSH_PASSPHRASE='...'   # then run this script in the same shell
#   bash poll_gpu.sh                 # or let it prompt once with hidden input
# The askpass helper is created in a private (700) temp file and removed on exit.
MAX=$(( ${1:-12} * 60 ))

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
  apps=$(ssh -o ConnectTimeout=10 fmd-vm "nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader" 2>/dev/null)
  if [ -z "$apps" ]; then
    echo "GPU_FREE after $(( ($(date +%s)-start)/60 )) min"
    exit 0
  fi
  echo "[$(date +%H:%M:%S)] busy: $(echo "$apps" | tr '\n' ';')"
  now=$(date +%s)
  if [ $(( now-start )) -ge "$MAX" ]; then
    echo "TIMEOUT_GPU_BUSY after $MAX s: $apps"
    exit 2
  fi
  sleep 60
done
