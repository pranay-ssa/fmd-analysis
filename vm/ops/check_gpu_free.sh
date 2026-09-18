#!/bin/bash
# Is the A100 free for us to use?
#
#   bash check_gpu_free.sh          -> prints the state and exits 0 only when nothing is running
#
# Exit 0: no compute process on the GPU, memory used below 1 GB, safe to start training.
# Exit 1: somebody is using it (or memory is held), wait.
#
# The box is shared with srikantht and swetap; no job here ever pre-empts another.

USED_MB=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader | head -1 | tr -d ' ')
PROCS=$(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader)

echo "GPU memory used : ${USED_MB} MiB"
echo "GPU utilisation : ${UTIL}"
if [ -n "$PROCS" ]; then
  echo "compute processes:"
  echo "$PROCS" | sed 's/^/  /'
else
  echo "compute processes: none"
fi

if [ -n "$PROCS" ]; then
  echo "RESULT: BUSY (a compute process holds the GPU)"
  exit 1
fi
if [ "${USED_MB:-99999}" -gt 1000 ]; then
  echo "RESULT: BUSY (memory still held: ${USED_MB} MiB)"
  exit 1
fi
echo "RESULT: FREE"
exit 0
