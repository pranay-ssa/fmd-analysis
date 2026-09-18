"""Diagnose the visible footprint of the remove+inpaint step on one preview_v3 sample.

Measures, from the artifacts themselves:
  * the pasted region      = |05_reinsert_jittered_pos - 03_inpainted| > thr
  * the removal footprint  = |original - 03_inpainted| > thr
  * whether the two overlap (source_overlap_px should be 0 for this sample)
  * local texture (high-pass std) inside the inpainted pixels against control
    regions of the same shape, shifted and clipped to stay in frame
  * the boundary step across the inpainted region's own contour
and writes a side-by-side crop of original / inpainted / pasted / pasted+outline.
"""
import json
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
SAMPLE = (REPO / "run" / "augment" / "preview_v3" / "Bubble Cluster"
          / "20241102_030253_L24_C12_9626")
OUT = REPO / "run" / "augment" / "diag_inpaint_footprint"
OUT.mkdir(parents=True, exist_ok=True)
THR = 2

orig = cv2.imread(str(SAMPLE / "original.png"), cv2.IMREAD_GRAYSCALE)
inp = cv2.imread(str(SAMPLE / "03_inpainted.png"), cv2.IMREAD_GRAYSCALE)
fin = cv2.imread(str(SAMPLE / "05_reinsert_jittered_pos.png"), cv2.IMREAD_GRAYSCALE)
assert orig is not None and inp is not None and fin is not None
H, W = orig.shape
print(f"image                        : {W}x{H}")


def bbox(mask):
    ys, xs = np.where(mask > 0)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), int((mask > 0).sum()))


paste_mask = (np.abs(fin.astype(np.int16) - inp.astype(np.int16)) > THR).astype(np.uint8)
remo_mask = (np.abs(orig.astype(np.int16) - inp.astype(np.int16)) > THR).astype(np.uint8)
print(f"pasted region   x0,y0,x1,y1,px: {bbox(paste_mask)}")
print(f"removal pixels  x0,y0,x1,y1,px: {bbox(remo_mask)}")
print(f"paste/removal overlap px      : {int(np.logical_and(paste_mask, remo_mask).sum())}")

meta = json.loads((SAMPLE / "labels.json").read_text())
print(f"jitter_realized / overlap_px  : {meta['jitter_realized']} / {meta['source_overlap_px']}")
print(f"paste_region / feather_k      : {meta['paste_region']} / {meta['feather_k']}")

# ---- the inpainted region as a solid shape -------------------------------- #
solid = cv2.morphologyEx(remo_mask * 255, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
n, lab, stats, _ = cv2.connectedComponentsWithStats(solid)
comps = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 3000]
print(f"\ninpainted blobs > 3000 px     : {len(comps)}")
for i in comps:
    x, y, w, h, a = stats[i]
    print(f"   blob area {a:>7} px  bbox {x},{y} {w}x{h}")

# texture inside the real inpainted pixels (dilate the sparse mask by 3)
core = remo_mask * 255                      # pixels the inpainter actually wrote
inp_region = cv2.dilate(core, np.ones((7, 7), np.uint8))
blur = cv2.GaussianBlur(fin, (0, 0), 2.0)
hp = np.abs(fin.astype(np.float32) - blur.astype(np.float32))


def stats_of(mask):
    v = hp[mask > 0]
    return (float(np.median(v)), float(np.percentile(v, 95)), int(v.size))


m, p, cnt = stats_of(inp_region)
print(f"\nhigh-pass |I-G(2)| inpainted  : median {m:.2f}  p95 {p:.2f}  ({cnt} px)")
mc, pc, cc = stats_of(core)
print(f"   strict core (no dilation)  : median {mc:.2f}  p95 {pc:.2f}  ({cc} px)")
bg = cv2.morphologyEx(255 - inp_region, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
mb, pb_, cb = stats_of(bg)
print(f"   untouched background       : median {mb:.2f}  p95 {pb_:.2f}  ({cb} px)")
for dx, dy in ((450, 0), (0, 500), (-450, 0)):
    shifted = np.zeros_like(inp_region)
    ys, xs = np.where(inp_region > 0)
    ys2, xs2 = ys + dy, xs + dx
    ok = (ys2 >= 0) & (ys2 < H) & (xs2 >= 0) & (xs2 < W)
    if ok.mean() < 0.95:
        print(f"   control dx={dx:>5} dy={dy:>4}      : skipped (leaves frame)")
        continue
    shifted[ys2[ok], xs2[ok]] = 255
    shifted[paste_mask > 0] = 0
    m, p, cnt = stats_of(shifted)
    print(f"   control dx={dx:>5} dy={dy:>4}      : median {m:.2f}  p95 {p:.2f}  ({cnt} px)")

# ---- boundary step across the inpaint contour ----------------------------- #
perim = cv2.morphologyEx(inp_region, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
inner = cv2.erode(inp_region, np.ones((7, 7), np.uint8))
outer = cv2.subtract(cv2.dilate(inp_region, np.ones((7, 7), np.uint8)), inp_region)


def ring_mean(img, mask):
    """Mean of img over mask, blurred, with normalisation so empty areas do not read as 0."""
    m = mask.astype(np.float32) / 255.0
    num = cv2.GaussianBlur(img.astype(np.float32) * m, (7, 7), 0)
    den = cv2.GaussianBlur(m, (7, 7), 0)
    return num / np.maximum(den, 1e-6)


steps = np.abs(ring_mean(fin, inner) - ring_mean(fin, outer))[perim > 0]
gx = cv2.Sobel(fin, cv2.CV_32F, 1, 0, ksize=3)
gy = cv2.Sobel(fin, cv2.CV_32F, 0, 1, ksize=3)
grad = np.hypot(gx, gy)
print(f"\nboundary step across inpaint  : median {np.median(steps):.2f}  "
      f"p95 {np.percentile(steps, 95):.2f}  max {steps.max():.2f}")
print(f"frame gradient (all pixels)   : median {np.median(grad):.2f}  p95 {np.percentile(grad, 95):.2f}")

# ---- is the fill level-plausible, and is any defect halo left behind? ------ #
far = cv2.subtract(cv2.dilate(inp_region, np.ones((61, 61), np.uint8)),
                   cv2.dilate(inp_region, np.ones((21, 21), np.uint8)))
near = cv2.subtract(cv2.dilate(inp_region, np.ones((21, 21), np.uint8)), inp_region)
for tag, m in (("fill core", core), ("ring 3-10 px out", near), ("ring 10-30 px out", far),
               ("untouched background", bg)):
    v = fin[m > 0]
    print(f"mean grey level, {tag:<21}: {v.mean():7.2f}  (sd {v.std():5.2f}, {v.size} px)")

# ---- visual: crop around BOTH footprints, four panels --------------------- #
allm = np.logical_or(paste_mask > 0, remo_mask > 0)
ys, xs = np.where(allm)
mg = 90
cx0, cy0 = max(0, xs.min() - mg), max(0, ys.min() - mg)
cx1, cy1 = min(W, xs.max() + mg), min(H, ys.max() + mg)
fig = fin.copy()
cnts, _ = cv2.findContours(inp_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(fig, cnts, -1, 255, 2)
panels = []
for im, tag in ((orig, "original"), (inp, "inpainted"), (fin, "pasted"), (fig, "pasted + outline")):
    crop = im[cy0:cy1, cx0:cx1]
    crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA)
    cv2.putText(crop, tag, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2, cv2.LINE_AA)
    panels.append(crop)
h = min(p.shape[0] for p in panels)
strip = np.hstack([p[:h] for p in panels])
cv2.imwrite(str(OUT / "footprint_strip.png"), strip)
print(f"\ncrop {cx0},{cy0}-{cx1},{cy1}  strip {strip.shape}")
print(f"wrote {OUT / 'footprint_strip.png'}")

# ---- 2x zoom of the source (filled) region, original beside inpainted ------ #
zy0, zy1 = max(0, ys.min() - 25), min(H, ys.max() + 25)
zx0, zx1 = max(0, xs.min() - 25), min(W, xs.max() + 25)
z = [cv2.cvtColor(orig[zy0:zy1, zx0:zx1], cv2.COLOR_GRAY2BGR),
     cv2.cvtColor(inp[zy0:zy1, zx0:zx1], cv2.COLOR_GRAY2BGR)]
z = [cv2.resize(p, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_NEAREST) for p in z]
cv2.putText(z[0], "original", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2, cv2.LINE_AA)
cv2.putText(z[1], "inpainted (the fill)", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2,
            cv2.LINE_AA)
hz = min(p.shape[0] for p in z)
zh = np.hstack([p[:hz] for p in z])
cv2.imwrite(str(OUT / "fill_zoom.png"), zh)
print(f"wrote {OUT / 'fill_zoom.png'}  {zh.shape}")
