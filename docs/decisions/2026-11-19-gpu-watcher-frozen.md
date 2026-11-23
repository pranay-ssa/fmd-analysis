---
title: GPU watcher policy for the frozen run
date: 2026-11-19
type: decision
status: active
where: docs/decisions/2026-11-19-gpu-watcher-frozen.md
---

# GPU watcher policy for the frozen run

The shared A100 is launched for the frozen 17-column run by `vm/drivers/launch_frozen17_training.sh wait`.

The watcher starts when the GPU has been quiet for 600 seconds: memory below 10,000 MiB, utilization below 20 percent, and no compute process that was not present at watcher start. A new compute process resets the window. The two long-running streamlit services are in the baseline and do not block.

The watcher runs as `pranayp` in the tmux session `frozen17`, so it survives SSH disconnects and laptop closure. It does not survive a VM reboot. It writes `watcher.log` and `watcher_status.json` in the run folder. It stops with `watcher.stop` or by killing the pid in `watcher.pid`. The first watcher had a 12-hour limit. It was restarted on 19 November at 16:15Z with a 44,100-second limit, so it ends at 10:00 IST on 20 November.

The run itself is the staged frozen17 command: ResNet50, 224 px, 50 epochs, seed 42, inverse-frequency weighting.

The watcher launched the run at 19:24Z on 19 November and finished with it at 19:51Z. No watcher is running.
