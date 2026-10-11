---
title: "Ticket 003: VM readiness and the micro-run gate"
date: 2026-10-06
type: experiment
status: done
where: docs/wayfinder/tickets/003-vm-readiness-and-micro-gate.md
---

# 003: VM readiness and the micro-run gate

Type: task, AFK with a human go. Map: [Task 1 bubble merge](../task1_bubble_merge_map.md).
Blocked by: the user's go, work starts tomorrow (2026-10-07).

## Question

Get the frozen local inputs onto the VM and prove the whole path works before
any 50-epoch run is staked: hashes match on both machines, the train/test
trees build strictly, and the trainer's new dump code path writes
predictions.csv and confusion.json on a throwaway micro-run.

## Checklist

1. md5 on this machine and on the VM, pairs compared: `labels.csv`, both
   count tables, `split_70_30_seed42.csv`, `build_vm_trees.py`,
   `model_training.py`, `dump_outputs.py`. Push only where the pairs match.
2. `nvidia-smi --query-compute-apps` first: the A100 is shared, never launch
   over a teammate's job.
3. Build both trees:
   `python build_vm_trees.py --image-root /data/FMD_Data_26082026/fmd_temp_images --out <run-root> --variant both --mode symlink --strict`.
   Exit 0 means 10,614 linked per variant with counts matching the verified
   tables; any picture without a source fails loudly.
4. Micro-run: a 2-class tree of about 10 pictures, 1 epoch, `--dump`. Confirm
   metrics.json, confusion.json and predictions.csv appear and that
   predictions.csv rows equal the test picture count.
5. Record the run root, the hash pairs and the micro-run output on this
   ticket, then close it.

## Done when

Both trees exist with a PASS, the micro-run wrote all three files, and every
hash pair matches. Not done until then: no real training run starts.

## Result (2026-10-07, closed)

Run root `/home/pranayp/merge_analysis`, layout mirroring the repository
(experiments/, run/, src/, reports/, docs/, tests/). Everything below was
done as pranayp with `sudo -H -u pranayp` so the user-site TensorFlow loads.

1. **Hash pairs: all match.** The 12 pushed sources were md5'd on both
   machines: `build_labels.py` 2997d83a, `verify_labels.py` 933f3e6a,
   `build_vm_trees.py` 5ebad93a, `registry.json` 96311ca4, `README.md`
   f497381c, `model_training.py` 17fc2ce6 (before two fixes), `dump_outputs.py`
   ab43dc53 (before one fix), `make_line_splits.py` 2232cb23,
   `image_md5_records.csv` 1dcb19ec, `all_lines_class_split_70_30.csv`
   e508a16e, count table 9b76f087, two-tag doc cbb98004. Local outputs were
   pushed as a reference copy: `labels.csv`, both count tables and
   `split_70_30_seed42.csv` came back **byte-identical** (4 of 5);
   `summary.json` differs only in line endings (CRLF written on Windows, LF
   on Linux), every value identical. The verifier then passed on the VM:
   **62 checks, 0 failed**.
2. **GPU:** `nvidia-smi --query-compute-apps` was empty before every launch
   (24 CPUs, A100 80 GB idle).
3. **Trees:** both variants, `--mode symlink --strict`, exit 0: separate
   10,614 linked, merged 10,614 linked, "every label row linked once, splits
   and counts agree".
4. **Micro-runs found three real bugs, all fixed before any 50-epoch run:**
   the trainer crashed plotting the confusion matrix when a test batch missed
   a class (14 tick locations vs 17 labels, `confusion_matrix` called without
   `labels=`), which also silently misaligned the per-class printout; the dump
   crashed on a class directory absent from a truncated test tree; and four
   TensorFlow processes at once aborted (rc=134) because each tried to
   pre-allocate the whole card (`CUDA_ERROR_OUT_OF_MEMORY`), fixed with
   `TF_FORCE_GPU_ALLOW_GROWTH=true`. Fixes pushed and md5-matched:
   `model_training.py` f9e0a942, `dump_outputs.py` d801d9eb; the local unit
   tests are 6/6.
5. **Full-tree 1-epoch run** (`runs/run0_fullcheck`, merged variant): 7,428
   train / 3,186 test, all 20 classes on both sides, file-order check clean
   (no warning), metrics.json + predictions.csv + confusion.json + PNG all
   written, 58 s per epoch, 61.49 per cent test accuracy after one epoch.
   Three throwaway runs followed as the launcher's gate: all four 50-epoch
   runs started 2026-10-07 01:56-01:58 UTC under
   `runs/launch_all.sh` + `runs/launch_missing.sh`, logged in
   `runs/launch.log`.
