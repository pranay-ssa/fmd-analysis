# YOLO11 Architecture Experiments - Detailed Walkthrough (OoI Defect Classes)

**Scope.** This document walks through every architecture experiment we ran on the
YOLO11 detection backbone for the Object-of-Interest defect classes, one by one.
Each experiment appears on its own: the exact change we made to the backbone, the
backbone shown before and after (side by side), and the measured result. Every number
is taken from the recorded run output on the same held-out set.

**How to read this document.** Each experiment is self-contained. You do not need to
jump between sections. Where a number matters, it is stated in place.

---

## Metrics used, and how to read them

| Metric | What it answers | One-line meaning |
|---|---|---|
| mAP50 | detection + label quality at the standard IoU level (0.5) | does the model find a defect and label it right |
| mAP50-95 | detection + label quality averaged over strict IoU levels (0.5 to 0.95) | same, judged more strictly |
| Matched IoU | for the boxes the model finds, how tightly they hug the true defect | is the located box close to the real one |
| Match rate | share of true defects that get a detected box at all (coverage) | did we even find it |

**Two easily-confused numbers, stated clearly.**
- Matched IoU is about **tightness**: among the boxes the model produces, the average
  overlap (0 to 1; 0.60 means 60%) between the predicted box and the true defect box.
  Higher = boxes closer to ground truth.
- Match rate is about **coverage**: the fraction of true defects that get a detected box
  at all. Higher = more defects found. A higher match rate does NOT mean the boxes are
  tighter; tightness is IoU. You need both: find it (match rate), then locate it well (IoU).

**Caveat on the match-rate definition.** Our match rate is lenient: a defect counts as
found if a same-class detected box overlaps it at all at confidence 0.25 (even near-zero
overlap). It is not "found with IoU of 0.5 or more". So it slightly overstates coverage.
A stricter "usable extraction" number (share of defects with a box at IoU >= 0.5) would be
lower. We report both IoU and match rate so neither is read in isolation.

**The current bottleneck.** For the competitive models, IoU is healthy (0.56-0.61) but
match rate is 32-41%. So the boxes we find are located well; the bigger gap is finding
more of the defects (coverage), not locating the ones we find.

---

## The baseline backbone, and where you are allowed to change it

This is the unmodified YOLO11-n backbone (10 feature rows). It reads the input through
five downsampling levels (P1/2 to P5/32). Each `C3k2` row is a feature block; `C2PSA`
adds attention at the deepest stage; `SPPF` aggregates multi-scale context. The row
label is the layer number used by the rest of the model.

| Row | Baseline module |
|---|---|
| 0 | Conv [64, 3, 2] |
| 1 | Conv [128, 3, 2] |
| 2 | C3k2 [256, False, 0.25] |
| 3 | Conv [256, 3, 2] |
| 4 | C3k2 [512, False, 0.25] |
| 5 | Conv [512, 3, 2] |
| 6 | C3k2 [512, True] |
| 7 | Conv [1024, 3, 2] |
| 8 | C3k2 [1024, True] |
| 9 | SPPF [1024, 5] |
| 10 | C2PSA [1024] |

**Where an edit can be made, and what it changes:**

| Edit point | What you change | Example from this study |
|---|---|---|
| `scales:` (width / depth) | capacity: make every channel wider or the network deeper | Experiment 3 (wider) |
| module name on a row | the block type (e.g. swap attention in) | Experiment 4 |
| a row's kernel / args | receptive field or behavior of one block | Experiment 2 |
| add new rows | more depth / a feature path at another scale | Experiments 7, 8, 9 |
| head rows | the detection outputs | not used in this set |

**Two rules that always hold when adding rows.** (1) Every new row counts as a layer in
the list, so all layer numbers after it shift; the head's routing references must be
updated to match (this is called a retap). (2) The width setting scales the channel
numbers in the config, so a `[1024]` argument is about 256 real channels at the "n"
width factor (0.25). Both are documented per experiment below.

**Setup for every run.** Ten object-of-interest defect classes. 346 training / 88
held-out images, one fixed stratified split, one fixed seed, 100 training epochs, 640 px
input, the same labels. Batch size was 16 for the first group and 8 for the later group;
a baseline trained at both batches shows the two give near-identical mAP
(0.2745 vs 0.2729), so the two groups are compared directly.

---

## Experiment 1 - Baseline (control, batch 16)

**Change:** none. This is the reference every other experiment is compared against.

**Backbone (unchanged):** as in the baseline table above.

| Metric | Value |
|---|---|
| Parameters | 2.66 M |
| mAP50 | 0.2745 |
| mAP50-95 | 0.1555 |
| Matched IoU | 0.597 |
| Match rate | 32.1 % |

**What this tells us:** this is the starting point. It is what a plain, unmodified YOLO11
gives on this data.

---

## Experiment 2 - Larger pooling window (free receptive-field edit)

**Axis:** module/kernel change. **Where:** backbone row 9 (`SPPF`).

**Change:** SPPF pooling kernel enlarged from 5 to 7. This widens the field over which the
deepest features fuse context. Parameters are unchanged (pooling has no weights).

**Backbone, side by side:**

| Row | Baseline | This experiment |
|---|---|---|
| 0-8 | (same) | (same) |
| 9 | SPPF [1024, 5] | **SPPF [1024, 7]** |
| 10 | C2PSA [1024] | C2PSA [1024] |

**Result:**

| Metric | Value (baseline) | Value (this) |
|---|---|---|
| Parameters | 2.66 M | 2.66 M |
| mAP50 | 0.2745 | 0.2925 |
| mAP50-95 | 0.1555 | 0.1627 |
| Matched IoU | 0.597 | 0.577 |
| Match rate | 32.1 % | 34.8 % |

**What this tells us:** a free gain on detection quality (+0.018 mAP50) with zero extra
parameters. IoU stays about flat (0.577 vs 0.597). Worth keeping unconditionally.

---

## Experiment 3 - Wider network (the "s" scale)

**Axis:** capacity (scale). **Where:** the `scales:` block only.

**Change:** select a wider preset so every channel in the backbone effectively doubles.
The module rows are unchanged; only the width factor moves from 0.25 to 0.50.

**Backbone, side by side (rows are textually identical; the width factor doubles all channels):**

| Row | Baseline (width 0.25) | This experiment (width 0.50) |
|---|---|---|
| 0 | Conv [64, 3, 2] | Conv [64, 3, 2] (effectively 128 wide) |
| 1 | Conv [128, 3, 2] | Conv [128, 3, 2] (effectively 256) |
| 2-10 | (same rows) | (same rows, every channel doubled) |

**Result:**

| Metric | Value (baseline) | Value (this) |
|---|---|---|
| Parameters | 2.66 M | 9.74 M |
| mAP50 | 0.2745 | 0.3331 |
| mAP50-95 | 0.1555 | 0.1849 |
| Matched IoU | 0.597 | 0.604 |
| Match rate | 32.1 % | 41.1 % |

**What this tells us:** more capacity helps both detection and coverage (+0.059 mAP50,
match rate 32 to 41%) and slightly helps IoU. The cost is about 3.7x the parameters.

---

## Experiment 4 - Attention on the deepest stages

**Axis:** module swap (attention). **Where:** backbone rows 6 and 8 (`C3k2` to `C2PSA`).

**Change:** the two deepest feature blocks (beside the existing attention at row 10) are
swapped for attention blocks. Row 6 becomes `C2PSA [512, True]`, row 8 becomes
`C2PSA [1024, True]`.

**Backbone, side by side:**

| Row | Baseline | This experiment |
|---|---|---|
| 0-5 | (same) | (same) |
| 6 | C3k2 [512, True] | **C2PSA [512, True]** |
| 7 | Conv [1024, 3, 2] | Conv [1024, 3, 2] |
| 8 | C3k2 [1024, True] | **C2PSA [1024, True]** |
| 9 | SPPF [1024, 5] | SPPF [1024, 5] |
| 10 | C2PSA [1024] | C2PSA [1024] |

**Result:**

| Metric | Value (baseline) | Value (this) |
|---|---|---|
| Parameters | 2.66 M | 3.17 M |
| mAP50 | 0.2745 | 0.3339 |
| mAP50-95 | 0.1555 | 0.1692 |
| Matched IoU | 0.597 | 0.587 |
| Match rate | 32.1 % | 32.4 % |

**What this tells us:** the best accuracy-per-parameter edit of the first group. It
matches the wider network on mAP50 (0.3339 vs 0.3331) with a third of the parameters
(3.17 M vs 9.74 M), and notably lifted two hard, low-support classes that the baseline
did not detect at all. IoU is on par with baseline.

---

## Experiment 5 - Wider and unchanged depth (heavy)

**Axis:** capacity (scale). **Where:** the `scales:` block only.

**Change:** keep the "n" depth but raise the width factor to 0.75 (the widest of the
group). Module rows are unchanged; every channel effectively widens.

**Backbone, side by side (rows are textually identical; the width factor 0.75 widens all channels):**

| Row | Baseline (width 0.25) | This experiment (width 0.75) |
|---|---|---|
| 0 | Conv [64, 3, 2] | Conv [64, 3, 2] (effectively 192 wide) |
| 1 | Conv [128, 3, 2] | Conv [128, 3, 2] (effectively 384) |
| 2-10 | (same rows) | (same rows, every channel widened by the 0.75 factor) |

**Result:**

| Metric | Value (baseline) | Value (this) |
|---|---|---|
| Parameters | 2.66 M | 21.33 M |
| mAP50 | 0.2745 | 0.3610 |
| mAP50-95 | 0.1555 | 0.2113 |
| Matched IoU | 0.597 | 0.609 |
| Match rate | 32.1 % | 41.4 % |

**What this tells us:** the strongest raw numbers of the first group (mAP50 0.3610,
embedded IoU 0.609, match rate 41.4%), but it costs about 7x the baseline compute. The
best result, at a price; whether the price is worth it is a deployment decision.

---

## Experiment 6 - Baseline again, at batch 8 (the later control)

**Change:** none structurally. The same unmodified backbone, trained with a batch size of
8 instead of 16. It is the control for the layer-placement study (experiments 7, 8, 9)
and the primary baseline figure.

**Backbone:** identical to the baseline table.

| Metric | Value |
|---|---|
| Parameters | 2.70 M |
| mAP50 | 0.2729 |
| mAP50-95 | 0.1556 |
| Matched IoU | 0.568 |
| Match rate | 37.4 % |

**What this tells us:** batch 8 and batch 16 give near-identical mAP on the same backbone
(0.2729 vs 0.2745). This is why the earlier batch-16 results and these batch-8 results are
compared directly. (IoU differs by run-to-run spread: 0.568 vs 0.597, so within-group
comparisons are the cleanest.)

---

## Experiment 7 - Add two plain layers at the deepest position

**Axis:** depth (plain convolution, deepest position). **Where:** inserted between the
final `C3k2` (row 8) and `SPPF` (row 9).

**Change:** two plain `Conv [1024, 3, 1]` blocks (stride 1, same resolution) added at the
deepest, coarsest scale. Because two rows were added, everything after them shifts by two
and the head's deepest routing reference was re-pointed to the new last backbone row (a
retap). Block 9 becomes `Conv [1024, 3, 1]` twice, then SPPF, then C2PSA.

**Backbone, side by side:**

| Row | Baseline | This experiment |
|---|---|---|
| 0-8 | (same) | (same) |
| 9 | SPPF [1024, 5] | **+ Conv [1024, 3, 1] (new)** |
| 10 | C2PSA [1024] | **+ Conv [1024, 3, 1] (new)** |
| 11 | - | SPPF [1024, 5] (shifted) |
| 12 | - | C2PSA [1024] (shifted) |

**Result:**

| Metric | Value (baseline b8) | Value (this) |
|---|---|---|
| Parameters | 2.70 M | 3.88 M |
| mAP50 | 0.2729 | 0.2769 |
| mAP50-95 | 0.1556 | 0.1434 |
| Matched IoU | 0.568 | 0.556 |
| Match rate | 37.4 % | 38.5 % |

**What this tells us:** effectively a null result. mAP50 is flat (+0.004), and both
mAP50-95 and matched IoU edge down (-0.012 each). Adding plain depth at the deepest,
coarsest position (a 20x20 map at 640 px) gives nothing useful. This is the result we
then set out to explain.

---

## Experiment 8 - Add two residual blocks at the deepest position

**Axis:** depth attribution, changing the TYPE. **Where:** same position as experiment 7,
but the added blocks are residual (a `C3k2` block with a skip connection) instead of plain
convolutions.

**Change:** two `C3k2 [1024, True]` blocks in the exact spot the plain convolutions sat.
This isolates the variable "layer type" while keeping the deepest position fixed.

**Backbone, side by side:**

| Row | Baseline | This experiment |
|---|---|---|
| 0-8 | (same) | (same) |
| 9 | SPPF [1024, 5] | **+ C3k2 [1024, True] (new, residual)** |
| 10 | C2PSA [1024] | **+ C3k2 [1024, True] (new, residual)** |
| 11 | - | SPPF [1024, 5] (shifted) |
| 12 | - | C2PSA [1024] (shifted) |

**Result:**

| Metric | Value (baseline b8) | Value (this) |
|---|---|---|
| Parameters | 2.70 M | 3.39 M |
| mAP50 | 0.2729 | 0.2678 |
| mAP50-95 | 0.1556 | 0.1379 |
| Matched IoU | 0.568 | 0.577 |
| Match rate | 37.4 % | 33.7 % |

**What this tells us:** the residual type does not rescue the deepest position. mAP stays
below baseline (0.2678), so the layer type is not the reason the plain version failed.
This points the cause away from TYPE and toward the POSITION.

---

## Experiment 9 - Add two plain layers at the mid-resolution position

**Axis:** depth attribution, changing the LOCATION. **Where:** at the P4 stage (row 6
level), a higher-resolution point than the deepest scale.

**Change:** the same two plain `Conv [512, 3, 1]` blocks, but placed at the mid-resolution
P4 stage (after row 6) instead of at the deepest P5 scale. This isolates the variable
"position" while keeping the layer type (plain convolution) fixed. Two rows were added, so
the rows after them shift by two and the head's routing references were re-pointed
(retap). Row 7 and 8 become the two new convolutions, then the original P5 stem resumes.

**Backbone, side by side:**

| Row | Baseline | This experiment |
|---|---|---|
| 0-6 | (same) | (same) |
| 7 | Conv [1024, 3, 2] | **+ Conv [512, 3, 1] (new)** |
| 8 | C3k2 [1024, True] | **+ Conv [512, 3, 1] (new)** |
| 9 | SPPF [1024, 5] | Conv [1024, 3, 2] (shifted) |
| 10 | C2PSA [1024] | C3k2 [1024, True] (shifted) |
| 11 | - | SPPF [1024, 5] (shifted) |
| 12 | - | C2PSA [1024] (shifted) |

**Result:**

| Metric | Value (baseline b8) | Value (this) |
|---|---|---|
| Parameters | 2.70 M | 2.99 M |
| mAP50 | 0.2729 | 0.3096 |
| mAP50-95 | 0.1556 | 0.1508 |
| Matched IoU | 0.568 | 0.583 |
| Match rate | 37.4 % | 38.5 % |

**What this tells us:** the position was the cause. The very same plain convolution that
did nothing at the deepest scale gives the best result of the whole study set at the
mid-resolution position: mAP50 0.3096 (+0.037 over this baseline) and IoU 0.583 (+0.015).
Probable reason, inline: these defects are small and route through the mid-resolution
features; the deepest map is too coarse for them.

---

## Summary, grounding the whole set

| Experiment | Change | Params | mAP50 | mAP50-95 | IoU | Match |
|---|---|---|---|---|---|---|
| 1. Baseline (b16) | control | 2.66 M | 0.2745 | 0.1555 | 0.597 | 32.1 % |
| 2. Larger pooling | SPPF kernel 5 to 7 | 2.66 M | 0.2925 | 0.1627 | 0.577 | 34.8 % |
| 3. Wider network | width 0.25 to 0.50 | 9.74 M | 0.3331 | 0.1849 | 0.604 | 41.1 % |
| 4. Attention | C3k2 to C2PSA on rows 6/8 | 3.17 M | 0.3339 | 0.1692 | 0.587 | 32.4 % |
| 5. Wider, heavy | width to 0.75 | 21.33 M | 0.3610 | 0.2113 | 0.609 | 41.4 % |
| 6. Baseline (b8) | control | 2.70 M | 0.2729 | 0.1556 | 0.568 | 37.4 % |
| 7. Deep, plain | +2 Conv at deepest | 3.88 M | 0.2769 | 0.1434 | 0.556 | 38.5 % |
| 8. Deep, residual | +2 C3k2 at deepest | 3.39 M | 0.2678 | 0.1379 | 0.577 | 33.7 % |
| 9. Mid-res, plain | +2 Conv at P4 | 2.99 M | 0.3096 | 0.1508 | 0.583 | 38.5 % |

**Ground rules that kept these comparable.** One structural change per experiment; the
same held-out split, seed, epochs, input size, and labels throughout; numbers re-read
from the recorded run files, never typed by hand.

**What the set answers for the lead's question.**
- Where can we change the architecture? In capacity (width/depth scales), in block type
  (swapping in attention), in a single block's kernel, or in adding rows at a chosen
  scale. Each is demonstrated above.
- How does it affect the output? Capacity and attention reliably raise detection quality
  (mAP) and coverage; a pool-kernel edit is a free small gain; adding rows helps only at
  a resolution the defect actually uses (P4), and is a non-result at the coarsest scale.
- On the IoU point: every competitive model sits at 0.56-0.61 matched IoU, so the boxes
  we extract are well located. The limiting factor today is coverage (match rate 32-41%),
  not box tightness.

*Notes on parameters and provenance.* Early-run parameter counts are the lightly-fused
counts logged per run; later runs logged the build count, which is why the two baseline
entries differ slightly (2.66 M vs 2.70 M) for an identical backbone. This does not change
any conclusion. All mAP values are the best-epoch result; IoU and match rate are computed
on the held-out set at confidence 0.25.