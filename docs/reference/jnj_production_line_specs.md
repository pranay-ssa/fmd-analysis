---
title: JnJ production line vision specs
date: 2026-10-12
type: reference
status: active
where: docs/reference/jnj_production_line_specs.md
---

# JnJ production line vision specs

Reference only. The JnJ team shared these specs on 2026-10-12 as their response to a
question about the 200 ms time constraint on the edge algorithm. We record them here so
they are on hand when this project reaches the production-integration phase.

**Do not change code, model design, or the plan in the multi-task research report to
accommodate these specs without explicit approval from the user.** The specs are
recorded, not acted on. The GPU/hardware analysis below is a readiness note, not a
work item.

## The three line setups

The same inspection task runs on three hardware configurations. All three inspect each
primary package right before foil placement. If at least one package in an array fails,
the whole array is rejected.

| Area | 2GT setup | 3GT setup | 4GT Hybrid / 5GT setup |
|---|---|---|---|
| Inspection location | Before foil placement, array rejected if any package fails | Before foil placement, images taken in buffer before solution filling (Legacy) or after dose (Flex) | Before foil placement, returns per-package pass/fail to post-hydration control; 45 lenses dosed, saline-checked, FMD-inspected per index |
| Camera arrangement | One 5-wide MVM, five cameras; 7-wide variant on Ireland 2GT Line 27 | Legacy: five cameras. Flex: one camera. Install docs describe six-camera hardware | Two mirrored 4-wide MVM sets, eight cameras total |
| Camera model | FLIR Blackfly BFS-PGE-88S6M-C, 8 MP global shutter, GigE | Legacy/multi-cam: Lucid TRI120S-MC, 12 MP GigE. Single-cam: Lucid TRI050S-MC, 5 MP mono GigE | FLIR Blackfly BFS-PGE-88S6M-C, 8 MP global shutter, GigE |
| Optics | 12 mm f/8 fixed focal, shim-set focus | Multi-cam: 75 mm C-mount + 2x extender + red bandpass + acrylic window. Single-cam: 6 mm C-mount + 2x extender | 25 mm lenses, preset focus, adjusted via MVM bracket slot |
| Backlight | 625 nm red, CL261-625C1-8M (5-wide) or XPT-296 (7-wide), Lexan shield | 660 nm: CL264 (six-cam), CL265 (five-cam), CL269-660C5-001 (single-cam) | One 625 nm collimated red, CL271-625C1, under I-Tray/MagneMotion layer |
| Light controller | Two DCS-100E controllers | Pulsar 320 (multi-cam), Pulsar 320E (single-cam) | Three DCS-100E controllers (Strobes 1-3) |
| Trigger | Two Keyence PR-MB15P3 sensors + Keyence KV-N14DTP Trigger PLC | Balluff BES01YU (multi-cam) or Omron EE-SX872P (single-cam); camera output drives exposure triggering | IFM IE5346 inductive sensor per pallet row; trigger via GPIO to cameras and DCS to backlight; no separate Trigger PLC |
| Camera power/trigger cabling | One custom GPIO head, single cable to all cameras in MVM | Power/I/O, image-trigger, light-power cables from vision control enclosure | One GPIO head per 4-wide set; one external vision cable splits internally |
| Camera networking | Netgear 10G switch to two-port 10G PCIe card; static IPs identify positions | Two four-port GigE NICs, camera-specific ports, static IP subnets (multi-cam). Dedicated ports for camera/PLC/strobe (single-cam) | Eight cameras direct to two four-port Ethernet cards; each camera must use its assigned port |
| PC hardware | Tower PC, one Nvidia Titan V or RTX GPU, one two-port 10G PCIe card | Multi-cam: Dell Precision 5820, two Quadro P5000 GPUs, two four-port GigE cards. Single-cam: Supermicro PC, one Quadro P5000, one four-port GigE card | Tower PC, two Nvidia RTX GPUs, two four-port Ethernet cards |
| Electrical | 110-240 V, dual-PSU capable | At least 20 A at 24 VDC for panel, external network, 120 V for PC | 110-240 VAC, 50-60 Hz |
| Software emphasis | EZ Eye with FMD + optional MMLS, missing/multiple-lens stats, Trigger PLC diagnostics | Lucid ArenaView config, Pulsar utility, FMD PC stats, HMI yield diagnostics | EZ Eye, eight-camera diagnostics, three DCS connections, 135-value pallet test pattern, 45-cavity stats |
| Maintenance | Shift-start Lexan check, monthly backlight clean, optical window + cavity clean | Daily GMP guarding, weekly light, monthly lens | Optical window + I-Tray clean, bi-weekly image archiving, thermal-paste return every 3 years |

## GPU and PC hardware vs the 200 ms edge-algo constraint

The edge algorithm is the binary pass/fail head. It is a small model. The analysis below
answers one question: is the shipped GPU/PC hardware powerful enough to hit 200 ms?

### Verdict per setup

| Setup | GPU | Adequate for 200 ms | Dominant bottleneck |
|---|---|---|---|
| 2GT | 1x Titan V (or unspecified RTX) + 10G NIC | Yes, comfortably. Titan V is overkill (110 TFLOPS FP16) | Not GPU. 10G ingest is fast (~7 ms for 8 MP) |
| 3GT multi-cam (Legacy) | 2x Quadro P5000 (Dell 5820) | Yes, but tightest of the three | GigE image transfer (~105 ms for 12 MP) eats most of the 200 ms |
| 3GT single-cam (Flex) | 1x Quadro P5000 (Supermicro) | Yes, trivially. 5 MP, single camera | Transfer ~43 ms + inference ~10 ms |
| 4GT/5GT | 2x RTX (unspecified) + 2x 4-port NICs | Yes, most capable | 8 dedicated ports keep per-camera transfer ~69 ms |

### The numbers

GPU compute is not the constraint for a YOLO-n/s class model at 640x640 (TensorRT FP16):

| GPU | FP32 / FP16 tensor | YOLO-n/s inference |
|---|---|---|
| Titan V (Volta, HBM2) | 7.8 TF / 110 TF | ~2-5 ms |
| Quadro P5000 (Pascal, no tensor cores) | 8.9 TF / ~18 TF eff. FP16 | ~5-15 ms |
| RTX (any modern generation) | 6-30+ TF / 40-200+ TF | ~2-10 ms |

Even tiling a full 8 MP frame into 10x 640x640 crops, a P5000 handles 10 tiles in
~40-100 ms, still inside 200 ms. Every line's GPU has headroom.

The real constraint is GigE image-ingest, not the GPU:

| Camera | Frame size (8bpp) | Transfer over 1 GbE (~117 MB/s) | Over 10G |
|---|---|---|---|
| FLIR 8 MP (2GT, 4/5GT) | ~8.1 MB | ~69 ms | ~7 ms |
| Lucid 12 MP (3GT Legacy) | ~12.3 MB | ~105 ms | ~10 ms |
| Lucid 5 MP (3GT Flex) | ~5.0 MB | ~43 ms | ~4 ms |

3GT Legacy (12 MP, GigE) is the tightest: ~105 ms transfer + ~10 ms inference leaves
~80 ms headroom. It fits, but only if the pipeline is async (ingest overlaps compute).
If the 200 ms is trigger-to-decision including transfer, this line has the least margin.

4/5GT is strongest on ingest: 8 cameras, each on its own dedicated NIC port, no shared
bandwidth, ~69 ms per camera in parallel. 2GT's 10G switch is even better (~7 ms ingest).

## Gaps to close with the JnJ team

1. Exact RTX model for 2GT and 4/5GT. "Titan V or RTX GPU" names no model. The floor
   (RTX 2060) and ceiling (RTX 6000 Ada) differ by ~10x.
2. 4/5GT NIC type. "Two four-port Ethernet cards" does not say 10G like the 2GT row.
   If 1 GbE, per-camera transfer is ~69 ms (fine, not 7 ms). If 10G, ingest is a
   non-issue.
3. 200 ms definition. Trigger-to-pass/fail-decision (includes transfer, exposure,
   compute, PLC write) or compute-only? This decides whether 3GT Legacy's ~105 ms
   GigE transfer is inside the budget (tight) or not (comfortable).
4. Trigger rate (Hz) and images per trigger. The table gives camera counts but no cycle
   time. The 200 ms must hold at burst, not just single-frame latency.
5. Inference engine. Pascal (P5000) has no tensor cores. Hitting larger-model or
   tiled-ROI budgets needs TensorRT FP16, not PyTorch eager.

## Tie-back to the FMD multi-task direction

The 200 ms edge algo is the binary pass/fail head. The back-office dual-head YOLO from
`docs/research/yolo_multitask_architecture.md` (detect + LP classify, YOLO-n/s class)
has the same compute profile (~5-30 ms inference on these GPUs). The Titan V and RTX
cards can host both the edge algo and the back-office model inside the 200 ms window.
The dual P5000 setup can split cameras across the two GPUs, leaving both cards well
under 200 ms even with the back-office model added. This hardware does not block the
"reduce number of models/CNNs on the line" goal. The constraint is data-ingest
bandwidth and pipeline scheduling, not GPU throughput.

**Reminder: this section is analysis for readiness. No code or design change to
accommodate these specs proceeds without the user's approval.**
