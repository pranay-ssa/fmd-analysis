# Augmentation arena - cut-paste defect synthesis (local, pre-VM)

Testing the **cut-paste defect augmentation** idea on the local copy of the defect
library before anything is generated at scale on the VM.

The idea, as stated: select an image, mark the defect region, remove the defect,
inpaint the hole with lens pixels, reinsert the defect. It came from the teammate's
VM preview script, kept here for reference as `vm/teammates/augment_srikanth.py`.

## Where it runs

Locally, against the library already in the repo:

| Item | Local value |
|---|---|
| Images | `data/incoming/<Class>/`, 1465 BMPs, all 2448x2048, mode L (8-bit grayscale) |
| Labels | `data/annotations.xml`, 435 images, 434 with boxes, 2020 boxes, 2015 of them rotated |
| Classes with boxes | 10 of the 12 object-of-interest classes; `Bubble Scatter` and `HEMA Obstruction` have none |
| Environment | `.venv` with `opencv-python-headless` (cv2 5.0.0), the same cv2 major version as the VM |

## Files

| File | Role |
|---|---|
| `cutpaste_augment.py` | the pipeline: 5 steps, per-step images, label export, manifest, summary, QA sheets |
| `check_labels.py` | verifies the emitted labels against the pixels, and measures the patch-border step and the defect-vs-box overlap |
| `measure_paste_fidelity.py` | measures the opacity each pasted defect was laid down at, bucketed by defect size |

## How to run

```bash
# 5-step preview with labels, 3 images per class
.venv/Scripts/python.exe experiments/augmentation/cutpaste_augment.py \
    --classes Bubble "Bubble On 123" Fiber --per-class 3 --paste all --emit-labels

# label check (+ optional full-resolution zoom crops around each paste)
.venv/Scripts/python.exe experiments/augmentation/check_labels.py \
    --out run/augment/preview_20260915 --zoom 3

# paste fidelity
.venv/Scripts/python.exe experiments/augmentation/measure_paste_fidelity.py \
    --out run/augment/preview_20260915

# geometry self-check: our CVAT corner math vs cv2.boxPoints on every annotated box
.venv/Scripts/python.exe experiments/augmentation/cutpaste_augment.py --selftest
```

Outputs land in `run/augment/<name>/` (gitignored, regenerable). One directory per
source image holds `original.png`, the five steps, `labels.json` and
`labels_yolo_obb.txt` / `labels_yolo_aabb.txt`.

## Differences from the teammate's preview, and why

| Change | Reason |
|---|---|
| Labels are emitted | his preview produced images only; a detector needs geometry, and the jitter offset was only in a manifest `note` field |
| `--paste all` (every annotated box) | he pasted only the largest box; the small classes have 79-1298 boxes per class and the largest is rarely representative |
| Gate evaluated on the largest single defect | he gated on the union mask, which rejects a frame holding many small defects for their combined area |
| One sampling stream for all variants | his Part A and Part B sampled with different seeds, so an image's cut-paste folder usually had no `original.png` beside it |
| Realized paste offset recorded after frame clipping | his recorded `dx,dy` could disagree with the pixels when the paste was clipped at the frame edge |
| QA sheet per class, label checker, fidelity meter | inspection and verification without opening hundreds of PNGs |

## Verified numbers (2026-09-15, local)

Three runs of the same 6 classes x 3 images, each fixing one measured defect.
`run/augment/preview_v3` is the current one.

| Check | v1 (first working) | v3 (current) |
|---|---|---|
| Geometry self-test, 2020 boxes | worst mask IoU vs `cv2.boxPoints` = **1.000000** | unchanged |
| Preview run | 18 sampled, 13 processed, 5 gate-skipped, 88 files, 11.6 s | same |
| Labels vs pixels | recall median 0.754, fill 0.801 | recall median 0.761, fill 0.865 |
| Patch border step (0 = invisible) | worst mean 0.571, worst max **21** grey levels | **0 at every border** |
| Defect opacity at the core, defects <= 5 px | median **0.924**, worst **0.540**, 0% fully opaque | median **1.000**, worst 0.769, **83%** fully opaque |
| Defect opacity, all 70 defects | 63% fully opaque | **96%** fully opaque |

Interpretation of the opacity column: the paste is `alpha * patch + (1-alpha) * background`,
so alpha at a defect's own pixels is the factor its contrast is multiplied by. A
median of 0.924 for 5 px defects meant the blend was thinning them, and 0.540 in the
worst case halved one. With the size-aware feather that is now 1.000.

### Three defects found and fixed, each caught by an instrument rather than by eye

| Found by | Defect | Fix | Evidence |
|---|---|---|---|
| `check_labels.py` | realized jitter offset computed against the requested paste origin, not the original one, so labels sat at the source position while the pixels moved | placement returns where the patch landed; labels are the source boxes translated by the realized offset | first run: recall **0.000** on all 13 samples; after: 0.75 median |
| `check_labels.py` patch-border metric | patch padded by 2 px against a 7 px Gaussian feather, so the alpha was truncated at the patch rectangle and left a visible edge | pad = `kernel // 2 + 2` | border step worst max 21 grey levels -> **0** |
| `measure_paste_fidelity.py` | fixed 7 px feather on 3 px defects: no pixel of a small defect was ever pasted opaque | kernel scales with the defect (`2 * round(0.3 * side) + 1`, clamped to 3..7) | 5 px defects: 0% -> 83% fully opaque |

### An instrument that had to be thrown away

The first fidelity meter compared a defect's contrast against the mean of an annulus
around it. That reported retention ratios of -73 on this library, because:
(a) several classes here are bright rings or specks, so the mean over the box is not
a contrast at all, and the source contrast can be ~0.4 grey levels, making the ratio
explode; (b) on Bubble frames with up to 18 boxes the annulus of one defect contains
its neighbours. Both are properties of the data, not of the paste. The replacement
(opacity at the core) is deterministic and needs no image statistics.

One visual finding was also an artefact of a careless instrument: a 3x zoom comparing
`original` against `pasted` at the paste destination appeared to show a hard bright
rectangular seam. The destination overlapped the source defect region by 187 x 37 px
in that sample, so the panels were comparing the removed defect against its inpainted
replacement, and the straight edges belonged to the annotation box. `check_labels.py
--zoom` now compares the background *before* the paste against the same area *after*,
which isolates the paste.

## Known limitations and open decisions

1. **The paste junction shows a tone step (measured, not yet fixed).** The patch
   carries a rim of source background (the box dilated by 25%) and lays it onto a
   different part of the lens, so the seam is a brightness discontinuity even
   though no edge is truncated. `check_labels.py` reports a paste junction step of
   median **13.59** grey levels, worst **42.69**, which is median **1.48x** and
   worst **8.15x** the local surface noise. Next candidates, in order of cost:
   match the patch's low-frequency level to the destination before blending
   (offset/gain correction inside the feather ring, deterministic and stable at any
   defect size), or use `cv2.seamlessClone` (Poisson) above some defect size, which
   is what the teammate abandoned precisely because it fails on tiny masks. The
   junction metric is in place, so either fix can be accepted or rejected on a
   number rather than on an impression.
2. **The paste sometimes lands on its own old footprint.** The jitter is drawn
   from +/- 8% of the frame, and the sampled offset is redrawn up to 12 times to
   avoid the source region, but with `--paste all` the patch spans the union of
   every defect in the frame (up to 18 boxes, spread wide), so a small jitter
   cannot always clear it. Measured on the v3 run: 9 of 13 samples clear the
   source region completely, the worst still overlaps 24278 px. Overlapping is not
   fatal (the defect still moves), but it makes the sample closer to a translation
   of its source. Options: larger jitter, per-defect jitter instead of a rigid
   translation of the layout, or accept and report the overlap (the manifest
   carries `source_overlap_px` per sample either way).
3. **The 2% gate, with a 0.25 dilate, is really a 1.28% box-area gate** (2 / 1.25^2).
   Measured on the annotations: Fiber has 45 of 62 boxes over the 2% dilated gate,
   HEMA Fragment 25%, Extraneous Polymer 12%, and every other class under 2%. So the
   gate mainly excludes Fiber, and any class-level plan has to say whether Fiber
   stays classical or waits for a learned inpainer.
4. **Same-frame paste only.** The background and lighting are those of the source
   frame, so this buys placement diversity, not appearance diversity. For the
   classification task that is arguably correct (the lens presentation classes are
   scene properties, and pasting a defect onto another scene breaks the label); for
   a detector it is the weaker half of the copy-paste literature.
5. **The source region is left inpainted.** In the pasted image the defect has
   moved, so the source position is background. Labels describe only the pasted
   boxes; `labels.json` states this explicitly so nobody reuses the source boxes.
6. **Leakage.** A generated sample shares its source frame. Generation at scale
   must keep an augmented copy in the same split as its source, or validation
   scores inflate. `manifest.csv` carries `source_image` for exactly this.
7. **Opacity is not the whole story for large defects.** Every defect over 11 px is
   pasted at 1.000 opacity, so the paste cannot be blamed for those, but nothing
   here measures whether Telea's fill is *plausible* in a texture sense; that is
   what the gate exists to avoid, and the Fiber and HEMA Fragment classes still
   need a learned inpainer to be usable at all.

## Still to decide before generating on the VM

- Target arena: the 22-class classifier input (224x224 crops) or the detection
  crops at 1280 (multiclass `nc=10`, where `Bubble On 123` sits at AP50 0.132 with
  0% recall). The augmentation is most promising where recall is starved, which is
  detection, and the label export already supports it.
- Volume per class and whether the split is applied before or after generation.
- Whether Fiber and HEMA Fragment wait for a learned inpainer (LaMa), or run with
  the mark-only output the gate leaves behind.
