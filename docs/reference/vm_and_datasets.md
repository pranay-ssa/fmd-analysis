---
title: The VM, its environment and the dataset layouts
date: 2026-09-23
type: reference
status: active
where: docs/reference/vm_and_datasets.md
---

# The VM, its environment and the dataset layouts

The stable operational facts: how to reach the machines, what is installed, where the data
sits, and the mandatory gate before any training launch. Moved here from `HANDOFF.md` on
2026-09-23, because a handoff holds state and this holds facts that do not change weekly.
Section numbers below are the ones the old handoff used.

## 2. Key facts / credentials (redacted)

- **VM:** `pranayp@20.253.232.255` (azure VM `vm-amd-a100-westus2`). SSH key `C:/Users/HP/.ssh/pranayp-vm-amd-a100-keyfile` is **passphrase-protected**; there is **no ssh-agent** on the Windows host.
  - The same host has a second account, `amd100-user`, which owns the source data. Use the alias `amd-a100-vm` (user `amd100-user`, key `C:/Users/HP/.ssh/vm-amd-a100-westus2-srv_amd100-user_key`, also passphrase-protected). The two aliases point at the same VM: same HostName, same port, one HostName in `known_hosts`. Run data work as `amd100-user`.
  - `ControlMaster` multiplexing fails on this Windows/MSYS ssh build ("Failed to connect to new control master"), so plan one passphrase entry per invocation. Chain the remote work into as few invocations as possible.
  - **Armor blob access (added 2026-09-16):** downloader `vm/ops/download_armor_blobs.py`, VM copy `~/download_armor_blobs.py`. Key file `C:/Users/HP/.fmd/armor_blob_conn` locally and `/home/amd100-user/armor_blob_conn` on the VM (mode 600), also readable from `$ARMOR_BLOB_CONNECTION_STRING`. Record: `docs/armor_blob_transfer_20260916.md`.
  - To connect: start an interactive PTY (`terminal(background=true, pty=true)`), then answer the passphrase prompt with `process_manage(action="submit", ...)`. The passphrase must be re-requested from the user each session and must never be written to a file.
  - The `fmd-vm` alias in `~/.ssh/config` resolves correctly (HostName 20.253.232.255, User pranayp, IdentityFile as above, IdentitiesOnly yes).
  - VM keras 3.15.1, keras-hub 0.31.1, sklearn 1.9.0, GPU = A100 80GB.
  - VM ultralytics: `torch==2.6.0+cu124`, `ultralytics==8.4.142`. BiFPN is NOT a built-in module.
- **Shared VM:** other teammate homes exist (`amd100-user` 63G incl. 56G source data on `/data`, `srikantht`, `swetap`). Do not delete other users' files.
- **VM data + run paths (all under `/home/pranayp/yolo_ooi/`):**
  - `dataset_obb/` — canonical OBB dataset (10 classes, 346/88 split, images + labels)
  - `dataset_multiclass/` — AABB conversion of the OBB labels (nc=10)
  - `crop_detect_dataset/` — single-class detection (nc=1, axis-aligned crops)
  - `runs/yolo26_arch/` — YOLO26 architecture experiments (baseline, feat_concat, feat_concat_v2)
  - `runs/yolo26_multiclass/` — YOLO26 multiclass experiments
  - `runs/crop_repro/` — auto vs fixed LR experiments
  - **Fork yaml layout on the VM differs from the repo:** `experiments/yolo26_feat_concat.yaml` (flat) and `yolo26_feat_concat_v2.yaml` (project root). In the local repo both live in `experiments/yolo26/`. The drivers reference the VM paths.
  - Drivers: `run_yolo26_feat_concat.py`, `run_yolo26_v2.py`, `run_yolo26_multiclass.py`, `run_crop_repro.py`, `per_class_simple.py`
  - Logs: `yolo26_feat_concat.log` (V1), `yolo26_v2.log` (V2), `yolo26_mc.log`, `crop_repro.log` (auto arms), `crop_repro_fixedlr.log` (the mislabeled arms)
  - **R1/R2 artifacts (new 2026-09-11):** `experiments/yolo26/` now exists on the VM (mirrors the repo) and holds `yolo26_feat_concat_r1.yaml` plus its `.preflight.json`; `runs/yolo26_arch_r1/` holds `r1_control_stock` and `r1_fork_p3tap`; `r1_feat_concat.log`, `r1_feat_concat_summary.json`, `crop_repro_summary_fixedlr_flat.json`, `verify_scale.out` are all in the project root.
  - **New gate + drivers:** `preflight_fork.py` (mandatory fork gate), `run_yolo26_feat_concat_r1.py` (control + fork in one run, matched init, has `--smoke`), `verify_defect_scale.py`, `verify_yolo26_claims.py`, `verify_yolo26_lr_trajectory.py`. Repo copies live in `vm/ops/` and `vm/drivers/`.
  - **Environment note:** this VM's `python3` has **no pandas**. Drivers must be stdlib-only (use the `csv` module for `results.csv`), or the launch dies before training starts.
  - **Working layout rule:** on the VM, `YOLO` wrapper vs network: the head is `model.model.model[-1]` (the wrapper is `model`, the DetectionModel is `model.model`, the module list is `model.model.model`).
- **Verification scripts:** `vm/ops/verify_yolo26_claims.py`, `vm/ops/verify_yolo26_lr_trajectory.py` (read-only; copies also live on the VM under `/home/pranayp/yolo_ooi/`).
- **Local repo:** `D:/02-SSA/fmd-analysis` (7-zone layout, git tracked)

---

## 3. VM environment setup

```bash
# Connect to VM (interactive passphrase prompt - there is no ssh-agent)
ssh -i C:/Users/HP/.ssh/pranayp-vm-amd-a100-keyfile fmd-vm

# VM env (already installed)
torch==2.6.0+cu124, ultralytics==8.4.142, pillow-heif==1.7.0

# GPU check before any training
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader

# Agent pattern: terminal(background=true, pty=true) + process_manage(action="submit")
# Passphrase: request from the user each session, never store in a file

# MANDATORY gate before any training launch (2026-09-11 onward)
python3 preflight_fork.py experiments/yolo26/<fork>.yaml      # structure + head identity, exits non-zero on fail
python3 -u <driver>.py --smoke                                # build both models, no training
# then launch: python3 -u <driver>.py  (control and variant in the SAME run, matched init)
```

Two gate rules, both learned the hard way on 2026-09-11:

1. A fork is not allowed to train until `preflight_fork.py` says PASS. It asserts the stock keys are present, the SPPF arg form matches, the built head is stock (`reg_max=1` with the `one2one` branch), and it prints the row diff so an accidental extra edit is visible.
2. Every driver has a `--smoke` mode. A build error must cost seconds, not a launch cycle.

---

## 4. Dataset layouts on the VM

| Dataset | Path | nc | Labels | Split |
|---|---|---|---|---|
| OBB (canonical) | `dataset_obb/` | 10 | OBB (8 coords) | 346/88, seed 42 |
| Single-class detect | `crop_detect_dataset/` | 1 | AABB (4 coords, class 0) | 346/88 (symlinked images) |
| Multiclass detect | `dataset_multiclass/` | 10 | AABB (4 coords, class 0-9) | 346/88 (symlinked images) |

**Important:** `dataset_multiclass/` was built by `build_multiclass_dataset.py` — converts OBB corners to AABB via min/max. Images are symlinked from `dataset_obb/`. Labels are new files in `labels/{train,val}/`.

### 4.1 New source image drop, 2026-09-16

Two folders moved from the Armor blob account `stjnjmakearmor`, container `fmd-temp`, into `fmd_temp_images/` on the VM. That path is a symlink to `/data/FMD_Data_26082026/fmd_temp_images`.

| Blob folder | Images | GB |
|---|---|---|
| `Updated ICube Objects 20260915` | 4,230 | 19.8 |
| `Updated ICube Categorical Classes 20260915` | 6,384 | 29.8 |
| **Total** | **10,614** | **49.6** |

Every file is a 2,448 x 2,048 8-bit BMP of 5,014,582 bytes, so the byte total is exact. That is width
by height, and it matches the annotation file's record for the older library. A crop job that read
the header of 67 of these files on 2026-09-21 reported 2448 x 2048 for all of them, which is the
check that settles the order. The transfer
ran on 2026-09-16 with 0 failures, about 8.6 minutes at 102.7 MB/s. Verification: every file was read
from disk again and MD5-checked against the service value, 10,614 of 10,614 OK, and the on-disk byte
total matches the source listing exactly. Two points need a decision before training: 143 images sit in
a `duplicates/` subfolder, and 27 image names appear in both folders. The full record, the script
detail and the re-run commands are in `docs/armor_blob_transfer_20260916.md`.

---

