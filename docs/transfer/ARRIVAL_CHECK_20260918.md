# Arrival check: the 2026-09-17 work, on this machine (2026-09-18)

The work done on the other machine on 15-17 September 2026 now sits in this repository. This
document records what arrived, what was checked, what was repaired, and what is still missing.
Every number below comes from a command run against the files on this disk.

## 1. What arrived

The copy landed on 2026-09-18 at 08:46 into these folders: `docs/`, `notebooks/`, `reports/`
(including `reports/cnn`, `reports/lines`, `reports/ops`, `reports/library`), `run/`, `runs/cnn/`,
`src/`, `vm/ops/`, `experiments/cnn/`, `experiments/augmentation/` and `docs/transfer/`.

Git counts it as **7 modified files and 178 untracked files**. The modified ones are `HANDOFF.md`,
`docs/INGEST.md`, `.gitignore`, `experiments/cnn/model_training.py`,
`experiments/cnn/build_combined22_landing_pad.py`, `notebooks/FMD_ResNet50Architectures.ipynb` and
`reports/cnn/ContactLensDefectResults_combined22.xlsx`. Each modified file is the newer layer on top
of the committed version, not an older version written over it: the diff of `HANDOFF.md` adds
sections 10 and 11 and the 17 September text, and the workbook in the tree is the six-architecture
version where the committed blob is the four-architecture one.

## 2. Integrity of the copy

A sweep over the whole tree (excluding `.git` and `.venv`) opened every machine-readable file:

| File type | Count | Result |
|---|---|---|
| Workbooks (`.xlsx`) | 18 | every one is a valid archive, every sheet name reads, 3 workbooks carry 5 embedded images each |
| Notebooks (`.ipynb`) | 8 | all parse as nbformat 4, 2 to 18 cells each |
| JSON | 166 | all parse |
| PNG | 509 | all have the PNG signature |
| JPEG | 202 | all have the JPEG signature |
| PDF | 17 | all start with `%PDF` |
| Python (`.py`) | 104 | all compile |
| Shell (`.sh`) | 24 | all pass `bash -n` |
| Weights (`.pt`) | 2 | both are valid archives |

Zero truncated files, zero zero-byte files, zero parse failures.

## 3. Do the published numbers come from the artifacts? Yes

| Claim in `docs/next_experiments_20260917.md` | Recomputed from the run files | Match |
|---|---|---|
| Six highlighted classes, pooled 96.26 per cent over 1,471 test pictures | 1,416 of 1,471 = 96.26 per cent | yes |
| Full model restricted to the same six classes: 90.34 per cent | 1,329 of 1,471 = 90.35 per cent (the file's own pooled block says 0.9034) | yes, to rounding |
| L31 +17.4 points on 132 pictures, L27 +12.8 on 218, level on L26 | +17.43, +12.84, 0.00 | yes |
| Macro recall up 6.8 points | 69.12 to 75.96 = +6.85 | yes |
| Multi-scale pooled 89.47 per cent against ResNet50 87.77 on 2,527 pictures, +1.70 | 0.894737 against 0.877721, gap +0.017016 | yes |
| Mean macro recall falls 2.67 points, 59.26 to 56.60 | 56.596 against 59.262 = -2.67 | yes |
| 26 class-line combinations recalled less, 20 more, 41 unchanged | 26, 20, 41 | yes |
| Six-class split: 4,895 pictures, 3,424 train, 1,471 test | per-line totals sum to 4,895 = 3,424 + 1,471; every line matches the table | yes |
| Full per-line split: 8,402 pictures, 5,875 train, 2,527 test | the five split files hold 8,402 rows, 2,527 on the test side | yes |
| Line comparison: 1,579 pictures measured, one frame size, one byte size | 35 class-line rows sum to 1,579; one frame size (2448x2048), one byte size | yes |
| L26 is the darkest line for Fiber, Foreign Matter, Multiple Lenses and HEMA Obstruction | 11.68, 11.09, 11.27 and 10.78, the lowest of the five lines in each class | yes |

Two independent harnesses also pass on this machine, reading the copied workbooks against the
copied run metrics:

| Command | Result |
|---|---|
| `experiments/cnn/verify_line_results.py` | 1088 checks, 0 failed |
| `experiments/cnn/verify_multiscale_workbook.py` | PASS 31 of 31 checks |

## 4. Repaired: the virtual environment

`./.venv/Scripts/python.exe` did not run. The environment pointed at
`C:\Users\HP\AppData\Roaming\uv\python\cpython-3.12.11-windows-x86_64-none`, the other machine's
interpreter, which does not exist here. `MACHINE_MOVE_20260917.md` section 2.7 records this as
fixed on 17 September; the file on disk shows the repair did not survive, so section 2.7 describes
an intention rather than the current state.

Rebuilt on 2026-09-18 with `uv venv --python 3.12`, `uv sync` and the five extra packages the
manifest does not name. Verified after the rebuild: Python 3.12.14, numpy 2.5.2, cv2 5.0.0,
openpyxl 3.1.5, matplotlib 3.11.2, pyyaml 6.0.3, azure-storage-blob imports.

The manifest gap is real: `pyproject.toml` names numpy, pillow, python-pptx and scipy, but scripts
import cv2, matplotlib, openpyxl, pyyaml and azure-storage-blob. A rebuild from the manifest alone
fails at the first `import cv2`.

## 5. Still missing

| Item | State on this disk | What it blocks |
|---|---|---|
| Source image library | `data/incoming/` holds one text file, no class folders | Every local image job: crops, augmentation, EDA regeneration, the crop-mode test |
| Crop outputs | `run/single-size_fixed_crop/`, `run/multi-size_fixed_crop/` absent | Nothing structural; both are regenerable from the library |
| Model weights | 2 of the 16 or more | Re-scoring any trained YOLO11 arm except the baseline |
| Armor blob connection file | `C:/Users/Abcom/.fmd/` does not exist | Re-downloading image drops from the blob account |
| GitHub credential | helper configured, no stored credential; `git ls-remote` answers "Repository not found" | Publishing the 10 unpushed commits, which still exist only on two disks |

## 6. Arrived since the move: SSH access

`C:/Users/Abcom/.ssh/` now holds both keys, `known_hosts`, and a `config` rewritten to the new home
directory (the two aliases `fmd-vm` and `amd-a100-vm`, both pointing at the VM host). A connection
test reaches the VM and stops at `Permission denied (publickey)` under `BatchMode`, which is the
expected result for a passphrase-protected key with prompting disabled. VM access needs the
passphrase and nothing else.

The folder also holds a socket left by the other machine's agent. It is dead here and can be deleted.

## 7. Two items for a decision

1. `experiments/cnn/model_training 2.py` is a 14 KB leftover from a copy collision. The live file is
   `model_training.py` at 23 KB, dated 17 September. The leftover is an earlier draft: it matches
   neither the committed version (15 KB) nor the live one, byte for byte. It should stay out of any
   commit, and the simplest way to keep it out is to delete it.
2. Nothing has been committed. The 7 modified and 178 untracked files are all unpublished, and the
   branch is 10 commits ahead of a remote that cannot be reached. Committing locally costs one
   command and takes the work out of reach of a disk failure.

## 8. Git identity and remote, changed 2026-09-18

The machine had no git identity at all: `user.name` and `user.email` were both unset, and the
history carries `pranaypudota <137995201+pranaypudota@users.noreply.github.com>` (29 commits) plus
`Pranay <pranay@local>` (3 commits).

Set on 2026-09-18, in the global config so every future repository on this machine uses it:

| Setting | Value |
|---|---|
| `user.name` | `pranay-ssa` |
| `user.email` | `pranay.pudota@soothsayeranalytics.com` |

Proof that new commits carry it: `git var GIT_AUTHOR_IDENT` returns
`pranay-ssa <pranay.pudota@soothsayeranalytics.com>`. Commits already in the history keep their old
author; nothing was rewritten.

The remote moved off the personal account, whose repository answers 404 to every caller:

| | Value |
|---|---|
| Previous | `https://github.com/pranaypudota/FMD-Preprocess.git` (404, a leftover of the rename to fmd-analysis) |
| Current | `https://github.com/pranay-ssa/fmd-analysis.git` |

The work account `pranay-ssa` exists on GitHub (account id 275686102, one public repository named
`skills`). The `fmd-analysis` repository does not exist yet and must be created empty, with no
README and no licence, before the first push. The push will open the credential manager's browser
sign-in and must be signed in as `pranay-ssa`, not as the personal account.

The 10 unpublished commits and everything arrived on 18 September stay on this disk until that push.
The old remote URL is kept in `MACHINE_MOVE_20260917.md` and in this section, so nothing is lost by
repointing it.
