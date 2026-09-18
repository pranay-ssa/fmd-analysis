# Repository reset for the work account (2026-09-18)

The project moved to the work account `pranay-ssa`. This document records the archive taken
before the old history was removed, how to restore it, and what the new repository holds.

## 1. Why the reset

The history was built while the project lived under the personal account. Every commit in it is
authored by `pranaypudota <137995201+pranaypudota@users.noreply.github.com>` (29 commits) or by
`Pranay <pranay@local>` (3 commits). The remote pointed at
`https://github.com/pranaypudota/FMD-Preprocess.git`, a leftover of the rename to fmd-analysis,
and that address answers 404 to every caller.

The work repository is `https://github.com/pranay-ssa/fmd-analysis.git`. It starts from the
current tree as one commit authored by `pranay-ssa <pranay.pudota@soothsayeranalytics.com>`.

## 2. The archive, taken before the reset

| Item | Location | Size | Proof |
|---|---|---|---|
| Git bundle, every ref | `D:/fmd-analysis-backups-20260918/history-all-refs.bundle` | 8.5 MB | `git bundle verify` reports "The bundle records a complete history" |
| Byte copy of the old `.git` | `D:/fmd-analysis-backups-20260918/gitdir-copy/` | 9.1 MB | copied with `cp -r` before the removal |
| SHA-256 of the bundle | `247f792b63a0e81909ed38def94b8bcc7e8a9e2c815088b5dc7e25900f56195b` | | `sha256sum` |

The archive holds **35 commits**: the 22 committed before this session, the 10 that were never
published, and the 3 committed on 2026-09-18 while grouping the arrival. The oldest carried
commit is `c6f419a`, the last one that ever reached a remote.

### Restore

```bash
git clone D:/fmd-analysis-backups-20260918/history-all-refs.bundle fmd-analysis-old
```

Restoring was tested, not assumed: a clone of the bundle into a temporary folder returned 35
commits, the tip `c12d657`, 198 tracked files, and `git fsck` reported nothing.

## 3. What the reset touches

| | Effect |
|---|---|
| Git history | Replaced. The old history lives only in the archive above. |
| Working tree | Untouched. Every file, including the folders git ignores, stays where it is. |
| `runs/` (75 MB of YOLO11 logs, 32 MB of CNN runs) | Untouched on disk, still ignored by git. |
| `.venv/`, `run/augment/`, `data/incoming/` | Untouched on disk, still ignored by git. |
| `experiments/cnn/model_training 2.py` | Moved out of the tree to `D:/fmd-analysis-backups-20260918/scratch/`. It is a copy collision: an earlier draft of `model_training.py` that matches neither the committed version nor the live one. |

## 4. A limit worth knowing before the first clone

The `runs/` rule in `.gitignore` keeps the line-run evidence out of git: the confusion matrices,
`metrics.json` and `history.json` for the five per-line models, the six highlighted classes and the
multi-scale architecture. Those files are the raw evidence for the published workbooks, and
`experiments/cnn/verify_line_results.py` reads them directly.

A fresh clone therefore cannot re-run the verifiers, because the evidence does not travel with the
repository. The verification results recorded in `ARRIVAL_CHECK_20260918.md` were produced from this
disk, where the files exist.

Two ways to close that gap, both one change:

- Narrow the rule so the line-run folders travel, for example ignore `runs/*` and then re-include
  `runs/cnn/lines`, `runs/cnn/lines_subset6` and `runs/cnn/lines_multiscale`. This adds about 7 MB.
- Or copy the same files under `run/`, which git already versions.

## 5. The first push

```bash
git push -u origin master
```

The credential manager opens a browser sign-in on the first push. It must be signed in as
`pranay-ssa`, not as the personal account, or the push fails against the work repository.

## 6. The state after the reset, verified

| Check | Result |
|---|---|
| Commits | 1, the initial commit |
| Author and committer | `pranay-ssa <pranay.pudota@soothsayeranalytics.com>` |
| Tracked files | 312 |
| Working tree | clean, no untracked entries outside the ignore rules |
| Remote | `https://github.com/pranay-ssa/fmd-analysis.git`, both fetch and push |
| Ignored folders on disk | `runs/` 32 MB of CNN runs, `.venv/` 366 MB, `run/augment/` 448 MB, all untouched |
| Old history | recoverable from the bundle, verified after the removal |

The count moved from 198 tracked files to 312 because the reset committed everything the old
repository tracked plus the 114 files it did not: 113 files of carried work and this record. Five
files stay out of git on purpose: the 4 files of the root `.obsidian` config, now ignored, and the
copy collision, moved to `D:/fmd-analysis-backups-20260918/scratch/`.
