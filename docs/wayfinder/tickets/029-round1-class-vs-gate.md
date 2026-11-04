---
title: "Ticket 029: round 1, class arm versus gate arm"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/tickets/029-round1-class-vs-gate.md
---
Type: task, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

On identical everything else, what does training on the gate subset cost against the class
target, measured on the same class-level test truth?

## Spec

- Two sequential runs on the A100, one at a time: arm `class`
  (`--columns ooi --gated-target class --pos-weight off`) and arm `gate`
  (`--columns ooi --gated-target gate --pos-weight off`).
- Push the label table and trainer in one hop as pranayp
  (`ssh amd-a100-vm 'sudo -u pranayp tee <target>' < local_file`); md5 both ends for the
  table and trainer before launching; launch inside
  `sudo -u pranayp bash -c "cd /home/pranayp/fmd-analysis && nohup setsid .venv/bin/python -u ... > <log> 2>&1 < /dev/null &"`.
- Pull metrics, thresholds, predictions and logs to `run/multilabel_ooi_20261104/{class,gate}/`
  with absolute remote paths in scp; write one run.json per arm.
- Report per class: AP with its prevalence floor, F1 at 0.5 and at the chosen cut,
  and the Bubble/Cluster confusion; then the round-1 comparison table on class-level truth,
  including recall-by-flag for the four gated classes (test gated/un-gated: FM 72/40,
  Fiber 56/2, EP 17/0, HEMA 27/0). About 25 minutes per arm.

## Done when

Both arms' artifacts are pulled, md5-checked and summarised; numbers are posted for the
user as soon as they are read.
