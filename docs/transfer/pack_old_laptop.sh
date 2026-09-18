#!/usr/bin/env bash
# pack_old_laptop.sh — run this ON THE OLD LAPTOP (git-bash / MSYS), 2026-09-17.
#
# It collects everything the new laptop cannot get from git: the untracked working
# tree, the uncommitted diff, credentials, the image library, model weights, and the
# Hermes agent profile. Output is one dated folder you copy across.
#
#   bash pack_old_laptop.sh
#   REPO="D:/02-SSA/fmd-analysis" OLDHOME="C:/Users/HP" OUT="E:/fmd-transfer" bash pack_old_laptop.sh
#   SKIP_DATA=1 bash pack_old_laptop.sh        # skip the 7 GB library (re-derive it instead)
#   SKIP_CROPS=1 bash pack_old_laptop.sh       # skip the 6.4 GB crops (default: skipped)
#
# Nothing here is destructive. Every command reads only.

set -u

# GNU tar on MSYS reads "C:/path" as a remote host named C and dies with
# "Cannot connect to C: resolve failed". Every path handed to a native tool must
# be in MSYS form (/c/path). Display strings keep the Windows form.
nativise() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -u "$1"
  else echo "$1" | sed -E 's#^([A-Za-z]):#/\L\1#'; fi
}

REPO_WIN="${REPO:-D:/02-SSA/fmd-analysis}"
OLDHOME_WIN="${OLDHOME:-C:/Users/HP}"
OUT_WIN="${OUT:-D:/fmd-transfer}"
REPO="$(nativise "$REPO_WIN")"
OLDHOME="$(nativise "$OLDHOME_WIN")"
OUT="$(nativise "$OUT_WIN")"
SKIP_DATA="${SKIP_DATA:-0}"
SKIP_CROPS="${SKIP_CROPS:-1}"   # crops are regenerable; opt in with SKIP_CROPS=0

TS="$(date +%Y%m%d_%H%M)"
DEST="$OUT/fmd-transfer-$TS"
DEST_WIN="$OUT_WIN/fmd-transfer-$TS"

echo "=============================================================="
echo " FMD pack — old laptop"
echo "   repo     : $REPO_WIN"
echo "   home     : $OLDHOME_WIN"
echo "   output   : $DEST_WIN"
echo "   data     : $([ "$SKIP_DATA" = 1 ] && echo SKIPPED || echo INCLUDED)"
echo "   crops    : $([ "$SKIP_CROPS" = 1 ] && echo SKIPPED || echo INCLUDED)"
echo "=============================================================="

[ -d "$REPO/.git" ] || { echo "FATAL: no git repo at $REPO"; exit 1; }
mkdir -p "$DEST"/{git,creds,data,weights,hermes,notes} || exit 1

# ---------------------------------------------------------------- 1. git state
echo "--- [1/7] git state"
cd "$REPO" || exit 1
git bundle create "$DEST/git/fmd-all-refs.bundle" --all 2>&1 | tail -3
git log --oneline -40                     > "$DEST/git/log.txt"
git log --oneline origin/master..HEAD 2>/dev/null > "$DEST/git/unpushed-commits.txt"
git status --porcelain                    > "$DEST/git/status.txt"
git diff                                  > "$DEST/git/uncommitted.diff"
git diff --stat                          >> "$DEST/git/uncommitted.diff"
git ls-files --others --exclude-standard  > "$DEST/git/untracked-files.txt"
git remote -v                             > "$DEST/creds/remotes.txt"
git config --global --list 2>/dev/null    > "$DEST/creds/git-global-config.txt"

# the untracked files are NOT in the bundle, so tar them explicitly
N_UNTRACKED=$(wc -l < "$DEST/git/untracked-files.txt" | tr -d ' ')
echo "    untracked files: $N_UNTRACKED"
if [ "$N_UNTRACKED" -gt 0 ]; then
  tar -czf "$DEST/git/untracked-work.tar.gz" -T "$DEST/git/untracked-files.txt" 2>/dev/null \
    && echo "    -> git/untracked-work.tar.gz" \
    || echo "    WARN: untracked tar incomplete; the file list is in git/untracked-files.txt"
fi

# ------------------------------------------------------- 2. credentials and ssh
echo "--- [2/7] credentials and ssh"
if [ -d "$OLDHOME/.ssh" ]; then
  mkdir -p "$DEST/creds/ssh"
  cp -p "$OLDHOME/.ssh/"* "$DEST/creds/ssh/" 2>/dev/null
  echo "    -> creds/ssh: $(ls "$DEST/creds/ssh" | tr '\n' ' ')"
else
  echo "    WARN: no $OLDHOME/.ssh"
fi
if [ -f "$OLDHOME/.fmd/armor_blob_conn" ]; then
  cp -p "$OLDHOME/.fmd/armor_blob_conn" "$DEST/creds/armor_blob_conn"
  echo "    -> creds/armor_blob_conn"
else
  echo "    WARN: no $OLDHOME/.fmd/armor_blob_conn"
fi
# Do the GitHub credential: it lives in Windows Credential Manager, not in a file.
cmd.exe /c "cmdkey /list" > "$DEST/creds/windows-credentials.txt" 2>/dev/null \
  && echo "    -> creds/windows-credentials.txt (names only, no secrets)"
echo "    NOTE: the SSH passphrase and the GitHub token/credential are NOT collected." \
     "They are read from your head / Windows Credential Manager. See" \
     "docs/transfer/MACHINE_MOVE_20260917.md section 3." \
     > "$DEST/creds/READ-ME-passphrases-and-tokens.txt"

# ------------------------------------------------------------- 3. image library
echo "--- [3/7] image library (data/incoming)"
if [ "$SKIP_DATA" = 1 ]; then
  echo "    SKIPPED by SKIP_DATA=1"
elif [ -d "$REPO/data/incoming" ]; then
  tar -cf "$DEST/data/data-incoming.tar" -C "$REPO/data" incoming \
    && echo "    -> data/data-incoming.tar ($(du -sh "$DEST/data/data-incoming.tar" | cut -f1))" \
    || echo "    WARN: tar failed"
else
  echo "    WARN: no $REPO/data/incoming"
fi

# ------------------------------------------------------------------- 4. crops
echo "--- [4/7] crop outputs"
if [ "$SKIP_CROPS" = 1 ]; then
  echo "    SKIPPED (regenerable: uv run src/fixed_crop.py --all --modes both)"
else
  for d in single-size_fixed_crop multi-size_fixed_crop; do
    if [ -d "$REPO/run/$d" ]; then
      tar -cf "$DEST/data/$d.tar" -C "$REPO/run" "$d" \
        && echo "    -> data/$d.tar ($(du -sh "$DEST/data/$d.tar" | cut -f1))"
    fi
  done
fi

# ----------------------------------------------------------------- 5. weights
echo "--- [5/7] model weights"
WT_LIST="$DEST/weights/weights-list.txt"
( cd "$REPO" && find runs -path '*/weights/*.pt' -o -path '*/weights/*.pth' ) 2>/dev/null | sort > "$WT_LIST"
W_N=$(wc -l < "$WT_LIST" | tr -d ' ')
if [ "$W_N" -gt 0 ]; then
  ( cd "$REPO" && tar -czf "$DEST/weights/runs-weights.tar.gz" -T "$WT_LIST" ) 2>/dev/null \
    && echo "    -> weights/runs-weights.tar.gz ($W_N files, $(du -sh "$DEST/weights/runs-weights.tar.gz" | cut -f1))"
else
  echo "    WARN: no .pt/.pth under runs/"
fi

# ------------------------------------------------------- 6. hermes agent profile
echo "--- [6/7] Hermes agent profile"
HROOT="$OLDHOME/AppData/Local/hermes"
HK="$DEST/hermes"
if [ -d "$HROOT" ]; then
  for d in skills memories; do
    [ -d "$HROOT/$d" ] && cp -rp "$HROOT/$d" "$HK/" 2>/dev/null && echo "    -> hermes/$d"
  done
  for f in SOUL.md config.yaml; do
    [ -f "$HROOT/$f" ] && cp -p "$HROOT/$f" "$HK/" 2>/dev/null && echo "    -> hermes/$f"
  done
  [ -f "$HROOT/state.db" ] && cp -p "$HROOT/state.db" "$HK/state.db" 2>/dev/null \
    && echo "    -> hermes/state.db (session history; REFERENCE ONLY, do not overwrite the new install)"
  [ -d "$HROOT/cron" ] && cp -rp "$HROOT/cron" "$HK/" 2>/dev/null && echo "    -> hermes/cron"
else
  echo "    WARN: no $HROOT"
fi

# ------------------------------------------------------- 7. inventory + manifest
echo "--- [7/7] inventory and checksums"
{
  echo "# inventory of what the new laptop is missing, packed $TS"
  echo
  echo "## sizes on the old laptop"
  du -sh "$REPO/data/incoming" 2>/dev/null
  du -sh "$REPO/run/single-size_fixed_crop" "$REPO/run/multi-size_fixed_crop" 2>/dev/null
  du -sh "$REPO/runs" "$REPO/run" 2>/dev/null
  echo
  echo "## counts (the new laptop should match these after the restore)"
  echo "data/incoming BMPs      : $(find "$REPO/data/incoming" -type f -iname '*.bmp' 2>/dev/null | wc -l | tr -d ' ')"
  echo "data/incoming class dirs: $(find "$REPO/data/incoming" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
  echo "runs/**/weights .pt     : $W_N"
  echo "untracked files         : $N_UNTRACKED"
  echo "unpushed commits        : $(wc -l < "$DEST/git/unpushed-commits.txt" | tr -d ' ')"
  echo
  echo "## every file git ignores in data/ and run/ (sizes)"
  ( cd "$REPO" && du -ah --max-depth=1 data run 2>/dev/null | sort -h | tail -20 )
} > "$DEST/notes/INVENTORY.txt"
cat "$DEST/notes/INVENTORY.txt"

( cd "$DEST" && find . -type f ! -name SHA256SUMS -print0 | xargs -0 sha256sum ) \
  > "$DEST/SHA256SUMS" 2>/dev/null
echo "    -> SHA256SUMS ($(wc -l < "$DEST/SHA256SUMS" | tr -d ' ') files)"

echo
echo "=============================================================="
echo " DONE. Pack size: $(du -sh "$DEST" | cut -f1)"
echo " Copy this whole folder to the new laptop:"
echo "   $DEST_WIN"
echo " Then on the new laptop:"
echo "   bash docs/transfer/restore_new_laptop.sh <that folder>"
echo
echo " IF THE SSH PASSPHRASE OR THE GITHUB CREDENTIAL ARE UNKNOWN,"
echo " read notes/INVENTORY.txt and section 3 of"
echo " docs/transfer/MACHINE_MOVE_20260917.md before you wipe anything."
echo "=============================================================="
