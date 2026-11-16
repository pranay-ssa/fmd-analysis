---
title: "Ticket 038: stage the Experiment 3.1 split on the VM and verify every image resolves"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/038-exp3-1-stage-on-vm.md
---
Type: task, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

Are the split, the label table and all 7,555 images present and readable on the VM, so the
training and scoring tickets can run without a dataset copy?

## Spec

- The images live at `/data/FMD_Data_26082026/fmd_temp_images/{image_path}` and are not copied.
  The classification trainer reads that root directly.
- Push `run/split_exp3_1_20261116/{split.csv,labels.csv,picture_detail.csv,meta.json}` into
  `/home/pranayp/fmd-analysis/run/split_exp3_1_20261116/` with the tee idiom
  (`ssh amd-a100-vm 'sudo -u pranayp tee <path> > /dev/null' < local_file`), owned by `pranayp`.
  md5 both ends and record both lists.
- Run a resolver check as `pranayp` over all 7,555 rows: file exists, regular file, non-zero bytes,
  readable, and its size read from the image header equals 2448 by 2048. Do not assume the size.
- Write `run/split_exp3_1_20261116/stage_check.json` with: rows checked, rows failed (and the
  first 20 failures by path), image root, host, timestamp, the two md5 lists.
- Leave no loose script on the shared box: pipe the checker from `vm/ops/check_exp3_1_images.py`.

## Done when

7,555 of 7,555 resolve with zero failures, md5 identical both ends, `stage_check.json` written.
Report the count and the md5s.
