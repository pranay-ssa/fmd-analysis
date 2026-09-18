# Machine move: old laptop → new laptop (2026-09-17)

The project moved from the old laptop (`C:/Users/HP`, repo at `D:/02-SSA/fmd-analysis`) to this
one (`C:/Users/Abcom`, repo at `D:/fmd-analysis`). This is the record of what travelled, what did
not, and the exact commands that close the gap.

**Written by inspection of the new laptop only.** Every "missing" claim below is verified against
this machine; nothing about the old laptop's current contents is verified, because it was not read.

---

## 1. What already travelled (verified here)

| Item | State | Evidence |
|---|---|---|
| Git history | Intact, `git fsck` clean (2 dangling blobs, harmless) | `git fsck`, `git log` |
| Unpushed commits | **10 commits ahead of `origin/master`** (last pushed 2026-09-04 `c6f419a`) | `git log origin/master..master` |
| Tracked code, docs, specs, registry | Complete | `experiments/registry.json` (65 KB, 48 rows), `reports/` 2.7 MB |
| Uncommitted workstream | 7 modified files + 26 untracked entries — **78 files**, because git reports a directory as one entry | `git status --short`, `git ls-files --others` |
| Obsidian knowledge vault | Complete, 44 notes, 209 KB | `.obsidian-vault/` (8 folders: Overview, Defect Taxonomy, Requirements, Glossary, Diagrams) |
| Augmentation previews | `run/augment/` 448 MB, six preview runs + diagnostics | `du -sh run/augment` |
| Line/EDA outputs | `run/line_eda/` 3.3 MB, `run/client_eda/` 44 KB | present |
| YOLO11 run logs and metrics | `runs/yolo11/` 75 MB — 9 arm dirs with `results.csv` and `metrics.json` | `find runs/yolo11/yolo_arch` |
| CNN results | `runs/cnn/` 3.7 MB, six `epochs_50/metrics.json` + confusion matrices | present |
| Python env | **was broken, now repaired** (see §2.7) | `uv sync`, `cv2 5.0.0` |

## 2. What did NOT travel (the gap)

| # | Missing | Old path | Size | What it blocks | Recovery |
|---|---|---|---|---|---|
| 1 | **Source image library** — 1,465 BMPs, 22 class folders, all 2448×2048 mode L | `data/incoming/` | ~7 GB | The whole local augmentation workstream (`experiments/augmentation/`). Also required to regenerate crops. Only `New Text Document.txt` is present here. | Copy from the old laptop, or re-download the 10,614-image blob drop and re-derive (§4 route C) |
| 2 | Crop outputs | `run/single-size_fixed_crop/`, `run/multi-size_fixed_crop/` | ~6.4 GB | Nothing structural — regenerable | `uv run src/fixed_crop.py --all --modes both` (needs item 1, and hours of CPU) |
| 3 | Model weights | `runs/yolo11/yolo_arch/*/weights/*.pt` | small | Re-evaluating or re-scoring trained YOLO11 arms | Copy, or retrain (GPU on the VM) |
| | Only **2** `.pt` files survived: `baseline_obb/weights/best.pt` and `last.pt`. Missing for `attention_backbone_obb` (the +0.059 winner), `sppf_cspc_obb`, `scale_wider_only_obb`, `yolo11s-obb`, `armA_residual_deep`, `armB_conv_p4`, `depth_plus2_deep`, `baseline_b8` | | | | |
| 4 | **SSH material** — no `~/.ssh` exists on this machine at all | `C:/Users/HP/.ssh/` | tiny | Every VM operation: training, the datasets, the YOLO26 runs, the 10,614-image library | Copy (§4 A), or generate a new keypair and install its public half on the VM via the Azure portal |
| | Contents needed: `pranayp-vm-amd-a100-keyfile`, `vm-amd-a100-westus2-srv_amd100-user_key`, `config` (the `fmd-vm` and `amd-a100-vm` aliases), `known_hosts` | | | | |
| 5 | **Armor blob connection string** | `C:/Users/HP/.fmd/armor_blob_conn` (mode 600) | tiny | Re-downloading image drops from `stjnjmakearmor` / `fmd-temp` | Copy, or re-issue from the Azure portal |
| 6 | **GitHub credential** — no `credential.helper` configured here | Windows Credential Manager on the old laptop | tiny | Pushing the 10 unpushed commits | Copy the credential, or issue a new PAT, or create a new repo |
| 7 | **Hermes agent state** — `memories/` is empty and no project skills exist | `C:/Users/HP/AppData/Local/hermes/` | ~MB | The agent here starts with no memory of this project: no `yolo-obb-pipeline`, no `remote-ssh-access`, no session history | Copy `memories/`, `skills/`, `sessions/`, `state.db`, `SOUL.md` |
| 8 | SSH key passphrases | never stored anywhere, by design | — | Decrypting the keys | Only you have them. If lost: rotate — generate a new key and add it to the VM |
| 9 | `.venv` | — | 292 MB | was unusable | **Fixed 2026-09-17**: it pointed at `C:\Users\HP\AppData\Roaming\uv\python\cpython-3.12.11-...\python.exe`, which does not exist here. Rebuilt with `uv venv --python 3.12 && uv sync` → Python 3.12.14, cv2 5.0.0 (same major as the VM) |

### 2.7 The venv fix, in detail

```bash
cd /d/fmd-analysis
rm -rf .venv
uv venv --python 3.12          # 3.12, not the newest: cv2/tensorflow wheels and the VM's 3.12.11
uv sync                        # from uv.lock: numpy, pillow, python-pptx, scipy, xlsxwriter, lxml
uv pip install opencv-python-headless matplotlib openpyxl pyyaml azure-storage-blob
```

Verified afterwards: `python 3.12.14`, `cv2 5.0.0`, `numpy 2.5.2`, `azure-storage-blob` importable.

Note for the record: `opencv-python-headless`, `matplotlib`, `openpyxl`, `pyyaml` and
`azure-storage-blob` are imported by repo scripts but are **absent from `pyproject.toml`**. They were
installed by hand into the old venv. Anyone rebuilding the environment from the manifest alone gets a
venv that fails on the first `import cv2`. Adding them to `pyproject.toml` is a one-line-each fix,
left to the user because it changes a tracked file.

## 3. The one urgent risk

`origin/master` is 10 commits behind the local branch, and
`https://api.github.com/repos/pranaypudota/FMD-Preprocess` returns **404 to an unauthenticated
caller** (the user account itself is public, so the repo is private or deleted). There is no
`credential.helper` on this machine.

**Consequence: the 10 commits reachable only from this disk and the old laptop's disk are not backed
up anywhere.** They carry the entire YOLO26 result set: the R1/R2 corrections, the H2 falsification,
the resolution economics, the port program, the CNN six-architecture matrix, the production-line EDA
and the 2026-09-17 split revision. Closing this gap costs one push and is worth doing before any data
transfer.

Update 2026-09-17 (user answers): the account is fine — it publishes 6 other repos — but
`FMD-Preprocess` is **not among its public repos**, so the 404 means private (a credential is all
that is missing) or renamed/deleted; the user is not sure which. This machine has
`credential.helperselector.selected = manager` but **no stored credential**, so the first
`git push` will open Credential Manager's browser sign-in. If the push still says *Repository not
found* after a successful sign-in, the repo is gone and needs recreating.

## 4. Three routes

| Route | When it applies | What moves | Cost |
|---|---|---|---|
| **A. Direct copy** | The old laptop is alive and reachable — same network, or an external drive | Everything, including the 13 GB of images and crops | One script run, one file copy, one restore |
| **B. Bundle over the network** | Both laptops alive, not on the same LAN | Same, minus the regenerable crops if you prefer | Same, slower |
| **C. Re-derive** | The old laptop is gone | Only what the VM and Azure still hold | Hours of recompute; the unpushed commits and the SSH passphrase are unrecoverable this way |

### Route A / B — steps

0. **Get the kit onto the old laptop first** — these two scripts were written here and the old
   laptop does not have them. Copy `docs/transfer/` (two small `.sh` files, 18 KB together) by email,
   USB stick or cloud drive. They read the old repo and write only to their own output folder.
1. **On the old laptop** (git-bash), from anywhere:
   `bash pack_old_laptop.sh` — see `docs/transfer/pack_old_laptop.sh`. It produces one dated folder
   with: a git bundle of every ref, a tar of the untracked working-tree files, the uncommitted diff,
   `~/.ssh`, the blob connection file, the Hermes profile, `data/incoming`, all
   `runs/**/weights/*.pt`, and a SHA-256 manifest. Override the defaults with
   `REPO=... OUT=... OLDHOME=...`.
2. **Copy** that folder to this laptop. External drive, LAN share, `scp`, OneDrive — anything. The
   small pieces (git, creds, hermes, weights) are a few MB; `data/incoming` is 7 GB.
3. **On this laptop**: `bash restore_new_laptop.sh /d/fmd-transfer/fmd-transfer-<timestamp>` — it
   unpacks the pieces, rewrites the old `C:/Users/HP` paths to `C:/Users/Abcom`, sets key modes to
   600, and verifies. See `docs/transfer/restore_new_laptop.sh`.
4. **Push the 10 commits** (the urgent item): either restore the old credential, or
   `git remote set-url origin <new-repo-url>` and push there.

### Route C — the recovery path if the old laptop is gone

| Lost item | Recovery |
|---|---|
| The 10 unpushed commits | **Unrecoverable from GitHub unless the private repo still exists.** If it does and you can authenticate, `git fetch` recovers everything up to `c6f419a` only — the 10 commits still need the old disk or a backup |
| `data/incoming` (1,465 BMPs) | The old library also lives on the VM as `/data/FMD_Data_26082026/fmd_temp_images` (`amd100-user`, 56 GB source data). Needs VM access, i.e. a new SSH key |
| The 10,614-image new drop | Re-download from the `stjnjmakearmor` blob account (`vm/ops/download_armor_blobs.py`) once the connection string is re-issued from the Azure portal |
| SSH access | Generate a keypair here (`ssh-keygen -t ed25519`), then install the public half on the VM: Azure portal → the VM → *Reset password* / *Run command*, or ask whoever holds `pranayp` / `amd100-user` |
| Crops (6.4 GB) | `uv run src/fixed_crop.py --all --modes both`, after `data/incoming` is back |
| Hermes memory and skills | Documents only. `HANDOFF.md` and the 44-note vault carry the project knowledge; the agent's own notes are lost |

## 5. What is verified after the move — run this

```bash
cd /d/fmd-analysis
git log --oneline -1 origin/master          # the pushed tip should advance past c6f419a
git status --short                          # no surprise deletions
ls /c/Users/Abcom/.ssh                      # the keys, a config with fmd-vm and amd-a100-vm, known_hosts
ls /c/Users/Abcom/.fmd/armor_blob_conn      # mode 600
ls data/incoming | wc -l                    # 22 class folders, 1465 BMPs
find runs -name '*.pt' | wc -l              # 16+ weights, not 2
./.venv/Scripts/python.exe -c "import cv2; print(cv2.__version__)"
ssh -o BatchMode=yes fmd-vm true && echo VM OK     # fails clean on a wrong passphrase by design
```

## 6. Decisions (answered 2026-09-17)

1. Old laptop available? **Yes** — USB drive or the same network. → **Route A**, see the printable
   `docs/transfer/USB_CHECKLIST.md`.
2. SSH key passphrases known? **Yes.** → the keys are worth transferring; no keypair needs
   regenerating.
3. `pranaypudota/FMD-Preprocess`: the account is alive (6 public repos) but this repo is not among
   them, so it is private or gone; the user is not sure. → the first authenticated `git push` settles
   it.
4. Copy the 7 GB library or re-derive it? **Copy it** — the old laptop is in hand, so re-deriving
   costs hours to reproduce something that is sitting on a disk.

## 7. How this kit was tested (2026-09-17, on this laptop)

Both scripts were run end to end against a synthetic bundle in
`%LOCALAPPDATA%\Temp\fmd-transfer-test` — never against real data, and the sandbox is deleted now.

| Test | Result |
|---|---|
| `bash -n` on both scripts | pass |
| `pack_old_laptop.sh` against the real repo, output to a temp folder | all seven sections produced output; pack size 17 MB; SHA-256 manifest with 351 files; weights tar 9.7 MB (2 `.pt`); untracked tar built from 81 files; inventory reported the same 10 unpushed commits |
| `restore_new_laptop.sh --dry-run` | checksums verified; every action printed, nothing written |
| `restore_new_laptop.sh` (real) against the synthetic bundle | checksums OK; 2 keys + config installed; config rewritten from `C:/Users/HP/.ssh/...` to the new home, key modes 600, `config` 644; `data/incoming` extracted; weights extracted; untracked classified **1 new, 1 differing, 1 identical** (correct on all three); skill merged no-clobber; memories/state.db staged instead of merged |
| Bug found and fixed during the test | GNU tar on MSYS reads `C:/path` as a remote host and dies with `Cannot connect to C: resolve failed`. Both scripts now convert every path with `cygpath -u` before handing it to a native tool, while the display and the ssh config keep the Windows form |

Still untested, because it needs the old laptop: the real `data/incoming` tar (7 GB), the actual
`~/.ssh` contents, a real ssh connection with the passphrase, and whether `pack` sees more untracked
files than this copy has. The pack script writes `notes/INVENTORY.txt` precisely so those numbers can
be compared rather than assumed.
