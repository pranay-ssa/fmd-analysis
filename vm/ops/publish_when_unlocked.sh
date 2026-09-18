#!/bin/bash
# Publish a rebuilt file over a destination that a Windows application may hold open.
#
# A stale write is refused while Excel has the workbook (Excel keeps a ~$ lock file and
# holds the handle). Rather than overwrite a file someone is reading, poll until the
# handle is free, then copy.
#
#   bash publish_when_unlocked.sh <source> <destination> [max_minutes]

SRC="$1"
DEST="$2"
MINUTES="${3:-30}"
TRIES=$((MINUTES * 3))     # one attempt every 20 s

for i in $(seq 1 "$TRIES"); do
  if cp -f "$SRC" "$DEST" 2>/dev/null; then
    echo "published: $DEST (attempt $i)"
    ls -la "$DEST"
    exit 0
  fi
  sleep 20
done
echo "still locked after ${MINUTES} minutes, nothing published"
exit 1
