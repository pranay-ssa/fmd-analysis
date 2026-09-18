#!/usr/bin/env bash
# restore_new_laptop.sh — run this ON THE NEW LAPTOP (git-bash / MSYS), 2026-09-17.
#
# Takes the folder produced by pack_old_laptop.sh on the old laptop and puts its
# contents where they belong here, rewriting the old machine's paths.
#
#   bash docs/transfer/restore_new_laptop.sh /d/fmd-transfer/fmd-transfer-20260917_1530
#   bash docs/transfer/restore_new_laptop.sh            # auto-picks the newest bundle
#   DRYRUN=1 bash docs/transfer/restore_new_laptop.sh   # print what would happen
#
# It NEVER deletes or overwrites existing project work: data, weights and ssh land
# directly only where the target is absent or empty, and everything else goes to a
# staging folder for you to look at first.

set -u

# GNU tar on MSYS reads "C:/path" as a remote host named C and dies with
# "Cannot connect to C: resolve failed". Every path handed to a native tool must
# be in MSYS form (/c/path). The _WIN forms are kept for display and for rewriting
# the ssh config, which wants a Windows path.
nativise() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -u "$1"
  else echo "$1" | sed -E 's#^([A-Za-z]):#/\L\1#'; fi
}

REPO_WIN="${REPO:-D:/fmd-analysis}"
NEWHOME_WIN="${NEWHOME:-C:/Users/Abcom}"
OLDHOME_MARK="${OLDHOME_MARK:-C:/Users/HP}"
DRYRUN="${DRYRUN:-0}"
OUT_ROOT_WIN="${OUT_ROOT:-D:/fmd-transfer}"

REPO="$(nativise "$REPO_WIN")"
NEWHOME="$(nativise "$NEWHOME_WIN")"
OUT_ROOT="$(nativise "$OUT_ROOT_WIN")"

BUNDLE_WIN="${1:-}"
if [ -z "$BUNDLE_WIN" ]; then
  BUNDLE_WIN="$(ls -1d "$OUT_ROOT_WIN"/fmd-transfer-* 2>/dev/null | sort | tail -1)"
fi
BUNDLE="$(nativise "$BUNDLE_WIN")"
[ -n "$BUNDLE" ] && [ -d "$BUNDLE" ] || { echo "FATAL: no bundle. Pass its path as argument 1."; exit 1; }

STAGE="$OUT_ROOT/restored-from-old-$(basename "$BUNDLE")"
STAGE_WIN="$OUT_ROOT_WIN/restored-from-old-$(basename "$BUNDLE")"

say()  { echo "  $*"; }
run()  { if [ "$DRYRUN" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

echo "=============================================================="
echo " FMD restore — new laptop"
echo "   bundle : $BUNDLE_WIN"
echo "   repo   : $REPO_WIN"
echo "   home   : $NEWHOME_WIN"
echo "   staging: $STAGE_WIN"
echo "   dryrun : $DRYRUN"
echo "=============================================================="

# ------------------------------------------------------------- 0. verify integrity
echo "--- [0/7] verify checksums"
if [ -f "$BUNDLE/SHA256SUMS" ]; then
  ( cd "$BUNDLE" && sha256sum -c SHA256SUMS --quiet ) 2>&1 | head -20 \
    && echo "  all checksums OK" \
    || echo "  WARN: checksum mismatches above — the copy is damaged, re-copy before trusting it"
else
  echo "  WARN: no SHA256SUMS in the bundle"
fi

mkdir -p "$STAGE" || exit 1

# ---------------------------------------------------------------- 1. ssh material
echo "--- [1/7] ssh keys and config"
if [ -d "$BUNDLE/creds/ssh" ]; then
  run mkdir -p "$NEWHOME/.ssh"
  run cp -p "$BUNDLE/creds/ssh/"* "$NEWHOME/.ssh/" 2>/dev/null
  # rewrite the old machine's home path everywhere it appears
  if [ "$DRYRUN" = 0 ] && [ -f "$NEWHOME/.ssh/config" ]; then
    sed -i \
      -e "s#${OLDHOME_MARK}#${NEWHOME_WIN}#g" \
      -e "s#/c/Users/HP#/c/Users/Abcom#g" \
      -e "s#\\\\Users\\\\HP#\\\\Users\\\\Abcom#g" \
      "$NEWHOME/.ssh/config"
    chmod 600 "$NEWHOME/.ssh/config" 2>/dev/null
  fi
  for f in "$NEWHOME/.ssh"/*; do
    case "$f" in
      *config|*known_hosts|*.pub) chmod 644 "$f" 2>/dev/null ;;
      *)                          chmod 600 "$f" 2>/dev/null ;;
    esac
  done
  say "installed: $(ls "$NEWHOME/.ssh" 2>/dev/null | tr '\n' ' ')"
  say "keys with no passphrase knowledge are dead weight — see section 6 of the move doc"
else
  say "WARN: no creds/ssh in the bundle"
fi

# ------------------------------------------------------------ 2. blob credential
echo "--- [2/7] armor blob connection file"
if [ -f "$BUNDLE/creds/armor_blob_conn" ]; then
  run mkdir -p "$NEWHOME/.fmd"
  run cp -p "$BUNDLE/creds/armor_blob_conn" "$NEWHOME/.fmd/armor_blob_conn"
  run chmod 600 "$NEWHOME/.fmd/armor_blob_conn"
  say "-> $NEWHOME_WIN/.fmd/armor_blob_conn"
else
  say "WARN: no armor_blob_conn; download_armor_blobs.py will not run until it is re-issued"
fi

# ---------------------------------------------------------------- 3. image library
echo "--- [3/7] image library (data/incoming)"
if [ -f "$BUNDLE/data/data-incoming.tar" ]; then
  EXISTING=$(find "$REPO/data/incoming" -type f 2>/dev/null | wc -l | tr -d ' ')
  if [ "$EXISTING" -lt 10 ]; then
    if [ "$DRYRUN" = 1 ]; then
      say "would extract -> $REPO_WIN/data/incoming"
    else
      tar -xf "$BUNDLE/data/data-incoming.tar" -C "$REPO/data"
      say "extracted -> $REPO_WIN/data/incoming ($(find "$REPO/data/incoming" -type f -iname '*.bmp' 2>/dev/null | wc -l | tr -d ' ') BMPs)"
    fi
  else
    say "data/incoming already holds $EXISTING files — NOT overwriting."
    say "it was extracted to $STAGE/data-incoming instead; diff it yourself"
    run mkdir -p "$STAGE/data-incoming"
    run tar -xf "$BUNDLE/data/data-incoming.tar" -C "$STAGE/data-incoming"
  fi
else
  say "not in the bundle (SKIP_DATA was set, or the tar failed). Re-derive path:" \
      "the same library lives on the VM at /data/FMD_Data_26082026/fmd_temp_images"
fi

# ------------------------------------------------------------------- 4. crops
echo "--- [4/7] crop outputs"
FOUND=0
for d in single-size_fixed_crop multi-size_fixed_crop; do
  if [ -f "$BUNDLE/data/$d.tar" ]; then
    run mkdir -p "$REPO/run"
    run tar -xf "$BUNDLE/data/$d.tar" -C "$REPO/run"
    say "extracted -> $REPO/run/$d"; FOUND=1
  fi
done
[ "$FOUND" = 0 ] && say "none in the bundle (expected: crops are regenerable with src/fixed_crop.py)"

# ----------------------------------------------------------------- 5. weights
echo "--- [5/7] model weights"
if [ -f "$BUNDLE/weights/runs-weights.tar.gz" ]; then
  run tar -xzf "$BUNDLE/weights/runs-weights.tar.gz" -C "$REPO"
  say "extracted into $REPO/runs — now $(find "$REPO/runs" -name '*.pt' 2>/dev/null | wc -l | tr -d ' ') .pt files"
else
  say "WARN: no weights in the bundle; trained arms cannot be re-scored without retraining"
fi

# ------------------------------------------------- 6. working tree from the old PC
echo "--- [6/7] untracked work and the uncommitted diff -> STAGING (no overwrite)"
if [ -f "$BUNDLE/git/untracked-work.tar.gz" ]; then
  run mkdir -p "$STAGE/untracked"
  run tar -xzf "$BUNDLE/git/untracked-work.tar.gz" -C "$STAGE/untracked"
  if [ "$DRYRUN" = 1 ]; then
    say "would compare $(wc -l < "$BUNDLE/git/untracked-files.txt" | tr -d ' ') files against the repo (classification needs the real extraction)"
  else
    NEW=0; DIFF=0; SAME=0
    while IFS= read -r rel; do
      [ -z "$rel" ] && continue
      a="$STAGE/untracked/$rel"; b="$REPO/$rel"
      if   [ ! -e "$b" ]; then echo "  NEW    : $rel"; NEW=$((NEW+1))
      elif cmp -s "$a" "$b"; then SAME=$((SAME+1))
      else echo "  DIFFERS: $rel"; DIFF=$((DIFF+1)); fi
    done < "$BUNDLE/git/untracked-files.txt"
    echo "  --- untracked: $NEW new, $DIFF differing, $SAME identical ---"
  fi
  [ -d "$BUNDLE/git" ] && run cp -p "$BUNDLE/git/uncommitted.diff" "$STAGE/" 2>/dev/null
  say "staged at $STAGE_WIN/untracked (the differing ones need a human decision: task 'keep ours or theirs')"
else
  say "no untracked tar in the bundle"
fi
if [ -f "$BUNDLE/git/fmd-all-refs.bundle" ]; then
  say "git bundle present: to adopt the old laptop's refs, run"
  say "  git -C $REPO bundle verify $BUNDLE/git/fmd-all-refs.bundle"
  say "  git -C $REPO fetch $BUNDLE/git/fmd-all-refs.bundle 'refs/heads/*:refs/remotes/oldlaptop/*'"
  say "then compare with: git -C $REPO log --oneline --left-right master...oldlaptop/master"
fi

# ------------------------------------------------------- 7. Hermes agent profile
echo "--- [7/7] Hermes agent profile"
HK="$NEWHOME/AppData/Local/hermes"
if [ "$DRYRUN" = 0 ]; then
  mkdir -p "$STAGE/hermes"
  # skills: merge without clobbering the stock skills that ship with the install
  if [ -d "$BUNDLE/hermes/skills" ]; then
    mkdir -p "$HK/skills"
    cp -rn "$BUNDLE/hermes/skills/." "$HK/skills/" 2>/dev/null
    say "skills merged (no-clobber) into $HK/skills"
    say "new skills: $(cd "$BUNDLE/hermes/skills" && find . -name SKILL.md | sed 's#/SKILL.md##;s#^\./##' | tr '\n' ' ')"
  fi
  # memories, session history and config are reference material, kept out of the live install
  for f in memories state.db config.yaml SOUL.md cron; do
    [ -e "$BUNDLE/hermes/$f" ] && cp -rp "$BUNDLE/hermes/$f" "$STAGE/hermes/" 2>/dev/null
  done
  say "memories/state.db/config.yaml copied to $STAGE_WIN/hermes as reference (NOT merged:"
  say "state.db is this install's live database and the config paths are machine-specific)"
else
  echo "  [dry-run] would merge skills and stage memories/state.db/config.yaml"
fi

# ------------------------------------------------------------------- verification
echo
echo "=============================================================="
echo " VERIFY (these are the checks from MACHINE_MOVE_20260917.md section 5)"
echo "=============================================================="
cd "$REPO" 2>/dev/null && {
  echo "git tip            : $(git log --oneline -1)"
  echo "unpushed           : $(git log --oneline origin/master..HEAD 2>/dev/null | wc -l | tr -d ' ') commits (push them)"
  echo "data/incoming BMPs : $(find data/incoming -type f -iname '*.bmp' 2>/dev/null | wc -l | tr -d ' ')  (target 1465)"
  echo "model weights      : $(find runs -name '*.pt' 2>/dev/null | wc -l | tr -d ' ')  (was 2 before the move)"
  echo "ssh keys           : $(ls "$NEWHOME/.ssh" 2>/dev/null | grep -v -e config -e known_hosts | wc -l | tr -d ' ')"
}
[ -x "$REPO/.venv/Scripts/python.exe" ] \
  && echo "venv cv2           : $("$REPO/.venv/Scripts/python.exe" -c 'import cv2;print(cv2.__version__)' 2>&1)" \
  || echo "venv cv2           : BROKEN — run: cd $REPO && rm -rf .venv && uv venv --python 3.12 && uv sync && uv pip install opencv-python-headless matplotlib openpyxl pyyaml azure-storage-blob"
echo
echo " Staged for your review: $STAGE_WIN"
echo " Still outstanding after this script:"
echo "   - push the unpushed commits (section 3 of the move doc: the remote returns 404)"
echo "   - confirm the SSH passphrase works: ssh -o BatchMode=yes fmd-vm true"