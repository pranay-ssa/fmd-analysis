# Fixed-Size Crop Spec — FMD Preprocess (v0.1 FINALIZED 2026-09-03)

Status: FINALIZED. Algorithm validated on full 22-class dataset, both modes, by the user. Per-class/per-mode fixed-size, lens box-centered crop with a no-loss guard as the only size exception. Supersedes variable-size ROI-Crop output as the local production crop.

## Goal
Replace the variable-size ROI-Crop output (each image has its own crop size) with a
**per-class, per-mode FIXED crop size**, and center the lens within it, so every crop a
class produces is identical in dimensions and the lens is centered. Keeps the
multi-size (tight) vs single-size (120px border) distinction the pipeline already uses.

## Non-goals
- No pixel rescaling / intensity change. Crop is a pure window select (calibration
  integrity) except the no-loss guard may return a LARGER window for rare outliers.
- No circle/ellipse masking (measured 2026-08-31: ROI corners already near-black).
- Does not change blob detection thresholds (THRESHOLD=3, MIN_BLOB_SIZE=500,
  MIN_BLOB_MEAN=15, tier-2 RECOVERY_BLOB_MEAN=13).

## Grounding measurements (2026-09-03, all 1465 source BMPs, data/incoming)
Full distributions: `run/eda/crop_size_analysis.md` / `.json`.
Canonical derivation: `run/eda/canonical_for_mode.py` (p99 of the mode's crop
dims, rounded up to 4). Single-size canonical >= multi-size canonical per class
(~150px = 2*(120 - multi_margin)) because content bbox is identical; only the
black frame differs.

Per-class canonical (W x H):

| Class | n | multi canon | single canon | multi m | single m |
|---|---|---|---|---|---|
| Bubble | 114 | 1412x1380 | 1560x1532 | 45 | 120 |
| Bubble Cluster | 36 | 1444x1432 | 1596x1584 | 45 | 120 |
| Bubble Irregular | 44 | 1404x1372 | 1556x1524 | 45 | 120 |
| Bubble On 123 | 14 | 1392x1388 | 1540x1540 | 45 | 120 |
| Bubble On Edge | 14 | 1412x1416 | 1564x1564 | 45 | 120 |
| Bubble Scatter | 7 | 1396x1368 | 1548x1516 | 45 | 120 |
| Cavity Off Center | 98 | 1556x1416 | 1704x1564 | 45 | 120 |
| Dirty Camera | 25 | 1732x1564 | 1876x1716 | 45 | 120 |
| Dirty Strobe | 43 | 1420x1672 | 1572x1788 | 45 | 120 |
| Extraneous Polymer | 17 | 1424x1376 | 1576x1524 | 45 | 120 |
| Fiber | 61 | 1560x1528 | 1560x1528 | 120 | 120 |
| Foreign Matter | 71 | 1408x1668 | 1556x1784 | 45 | 120 |
| HEMA Fragment | 8 | 1464x1440 | 1544x1520 | 80 | 120 |
| HEMA Obstruction | 105 | 1432x1384 | 1584x1532 | 45 | 120 |
| Lens Off Center | 30 | 1432x1408 | 1580x1560 | 45 | 120 |
| Low Dose Obstructing Region of Interest | 93 | 1400x1376 | 1548x1528 | 45 | 120 |
| Missing Lens | 21 | 1396x1376 | 1544x1524 | 45 | 120 |
| Missing Primary Package | 315 | 1372x1364 | 1520x1516 | 45 | 120 |
| Multiple Lenses | 207 | 1440x1440 | 1592x1592 | 45 | 120 |
| Package Misalignment | 37 | 1872x1992 | 2020x2048 | 45 | 120 |
| View Obstructed | 22 | 1344x1144 | 1496x1296 | 45 | 120 |
| Wet Package | 83 | 1472x1460 | 1552x1540 | 80 | 120 |

Loss vs original frame (2448x2048): single ~45-55%, multi ~8-9pp more (~53-63%).
Package Misalignment lowest (17-26%) because object near-fills the frame; its
single canon H=2048 = full frame height (vertical centering is a no-op there).

## Center-offset evidence (run/eda/center_offset_eda.py)
Content (lit) centroid minus frame center, px:
- Most classes ~100px off (mainly vertical Y).
- Cavity Off Center: med 353px, up to 604px; 71/93 >200px.
- Dirty Camera: 25/25 >100px, med 247px, up to 301px.
- View Obstructed: 6/22 detectable; 1 image 662px off; 16 blank.
Conclusion: blind frame-center cropping clips real lens on these classes. Crop must
anchor on the detected content centroid.

## Obstructed-lens bias (known limitation)
A dark obstruction over half a lens means only the lit half is detected, so the
content centroid is biased toward the lit side. Exposure is small (View Obstructed
has 6 detectable images total); content-centroid is still the best available anchor
and beats frame-center. Not addressed in v0.1.

## Algorithm (per image, detection runs once for both modes)
1. Load grayscale uint8 (2448x2048 source).
2. Tier-1 detect (mean>=15); if no blob, tier-2 (mean>=13). Content bbox = union of
   kept blob extents (no margin).
3. If no blob (blank frame): crop = class canonical window centered on FRAME center.
   Flag `blank`.
4. Else content bbox present. Center a fixed window of the class canonical W x H on
   the content bbox centroid, clamped to the frame:
   - If the content bbox fits fully inside that fixed window -> emit fixed window.
   - If it does NOT fit (rare, ~0.5%: content span > canonical or content pinned to a
     frame edge) -> NO-LOSS GUARD: expand the window to content bbox + CONTENT_MARGIN,
     clamped to frame. Flag `expanded`; output dims exceed canonical. This is the only
     case that breaks strict fixed size, and it guarantees the lens is never clipped.
5. Write crop; log actual W x H, window origin, flags.

No pixel value changes. Multi and single windows are placed from the SAME content
bbox (single is a wider frame), so detection is done once per image.

## Constants (config.py)
- PER_CLASS_CROP_SINGLE, PER_CLASS_CROP_MULTI: per-class canonical maps (table above).
- CONTENT_MARGIN: guard pad around content when the fixed window can't fit it. = 45.
- get_crop_size(class, mode) -> (W, H); unknown class -> nearest-default (single 1560x1532
  or multi 1440x1440 fallback), and is logged.

## CLI (src/fixed_crop.py)
- Input base = dir of class folders (`data/incoming`), layout `<base>/<Class>/*.bmp`.
- `--classes A B ...` or `--all`; `--modes single-size|multi-size|both` (default both).
- `--output-base` (default `run`). Output:
  `run/<mode>_fixed_crop/<Class>_<YYYYMMDD>/<stem>_crop.bmp`
  plus `crop_manifest.csv` + `run_report.json` (actual dims, window coords, flags).
- Detection of each image runs once even for `--modes both`.

## Validation plan (local, CPU-heavy; parallelize 8 workers)
1. Representative subset: Wet Package (tight), Bubble (tight), Cavity Off Center
   (off-center + blanks), View Obstructed (blank-heavy), Missing Primary Package
   (outlier / guard trigger) -> both modes.
2. Visual checks: lens centered; crop dims == canonical (except expected `expanded`);
   single bigger than multi by ~150px; blank frames are centered black+any lens.
3. Confirm guard triggers only on the known outliers (8 images: Bubble x1, HEMA
   Obstruction x1, MPP x3, Multiple Lenses x3) and nothing is clipped.
4. Full 22-class run once visual OK.

## Resolved items
- Option A (separate per-mode canonical sizes) — USED. Single and multi each have
  their own per-class fixed size; multi stays tight, single keeps the 120px border.
- No-loss guard behavior — ACCEPTED after user visual inspection. The <1% guard
  cases keep their lens; no clipping.
- hard-class skip-blob list — NOT USED. Detection runs on every image; blank frames
  (no blob) fall back to a frame-centered crop at the class canonical size.
- Centering anchor — box-centering of the lit-content bbox KEPT. A/B test
  (run/eda/ab_center.py) showed core-vs-box drift is negligible: Bubble Cluster
  med 4.2px / max 27.8px; Dirty Camera med 27.4px / max 37.0px; Foreign Matter
  med 2.9px / max 15.0px (<= ~2% of crop). Pure intensity-centering was REJECTED:
  specular lens glare drags it ~400px off, firing the guard on ~100% of images.
- PENDING human visual inspection (below) — now DONE (user eyeballed samples and
  the full run; algorithm accepted).
## Local test results (2026-09-03, 5-class subset, both modes)
Ran `src/fixed_crop.py` on Wet Package, Bubble, Cavity Off Center, View Obstructed,
Missing Primary Package (632 images) in both modes. Output under
`run/{single-size,multi-size}_fixed_crop/<Class>_20260903/`.

All `ok` crops equal the canonical size exactly (no drift). Counts:
- Bubble / Wet Package / Missing Primary Package: centered to <1px (med 0.7px,
  p95 1.4px, max 1px). Border = canonical − content ≈ design margin.
- Missing Primary Package: 1 `expanded` (single) / 2 `expanded` (multi) — no-loss
  guard emitted a larger window (1747x1548 / 1481x1347, 1747x1548); lens intact.
- Blanks: View Obstructed 16, Cavity Off Center 5 — frame-centered (no lens).
- touch_edge = 0 across all 611 detected single crops; multi has 1 (View Obstructed
  content reaches the source frame edge — lens runs to original frame border, not
  truncation).

Known expected non-centered crops (QA offset p95 large): Cavity Off Center (max
~226px single / ~152px multi) and View Obstructed (~200px single / ~340px multi).
These are lenses that sit AT the physical frame edge; they cannot be centered
without leaving the frame, and nothing is clipped. Visual check confirms.

PENDING: human visual inspection of the sample crops before the full 22-class run.
## Full 22-class run (2026-09-03, both modes, 1465 images, 8 workers, 387s)
Every `ok` crop equals its canonical size exactly. Blanks (frame-centered): View
Obstructed ×16, Cavity Off Center ×5. All classes fully fixed-size except the 4
images below that triggered the no-loss guard (0.27% of images):

| Class | Mode | File | Canonical | Actual | Excess |
|---|---|---|---|---|---|
| Missing Primary Package | multi | 20241115_031728_L26_C11_9850.bmp | 1372x1364 | 1747x1548 | +375 x +184 |
| Missing Primary Package | single | 20241115_031728_L26_C11_9850.bmp | 1520x1516 | 1747x1548 | +227 x +32 |
| Missing Primary Package | multi | 20241115_031728_L26_C10_9515.bmp | 1372x1364 | 1481x1347 | +109 x -17 |
| Multiple Lenses | multi | 20260812_163734_..._Cavity14_B01BFRG_Fail7_Score(0.9995544).bmp | 1440x1440 | 1638x1498 | +198 x +58 |
| Multiple Lenses | multi | 20260813_091315_..._Cavity11_B01BJL1_Fail7_Score(0.9947544).bmp | 1440x1440 | 1598x1436 | +158 x -4 |

User eyeball: the two Missing Primary Package expansions are driven by a STRAY
LIGHT STREAK well outside the lens (not the lens); guard kept them (no clip).
Guard behavior accepted. Negative excess on one axis = guard rebuilt the window
around content+45px so it need not stay square.

Open consideration (not actioned): because content = union of ALL kept blobs, a
far stray streak can both enlarge the guard window and pull the center off the
lens. If lens-only centering is wanted later, exclude blobs whose centroid is far
from the largest/main lens blob before placing the window.

## Final decisions (2026-09-03)
- Crop = per-class per-mode FIXED window (config maps), centered on the lit-content
  bbox; blank frames frame-centered; no-loss guard expands only when content can't
  fit. Pure window select, calibration preserved. Algorithm ACCEPTED by user.
- Next step (NOT part of this local deliverable): port to the VM and re-crop
  yesterday's data with the new algorithm. New file set / script runbook to follow.

## Guard-cause analysis (2026-09-03, all 4 images; run/eda/analyze_guard_cases.py)
Two distinct causes; all are edge cases and logged:
- Reason 1 — stray/secondary lit blobs inflate the union box (lens alone fits):
  Missing Primary Package 20241115_031728_L26_C11_9850 (single + multi). Main lens
  spans 1085x1082 (fits both windows); a dim right-side streak + top speck push the
  union to 1657 wide. This is the "bigger crop is stray light, not lens" case the
  user eyeballed.
- Reason 2 — content genuinely wider than the p99 canonical window:
  Missing Primary Package 20241115_031728_L26_C10_9515 (multi): one lens 1391 wide
  vs 1372 window (+19px).
  Multiple Lenses 20260812_..._Cavity14 (multi): 1548 vs 1440 (+108px).
  Multiple Lenses 20260813_..._Cavity11 (multi): 1508 vs 1440 (+68px).
Guard correctly preserved all content; 0.27% of images; nothing clipped.
