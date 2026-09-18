# Single-Size Crop — Usage Guide for VM Teammates

**Audience:** anyone using the single-size fixed crops on the VM at
`/home/pranayp/fmd_crop_output/single-size_fixed_crop/`.

**Goal:** make it obvious *what these crops are*, *how they were made*, and *how to
map any annotation back into the crop coordinate system* without reading code.

---

## 1. What's in a crop folder

Each class folder is named `<Class>_<YYYYMMDD>` and contains:

```
<Bubble>_<20260903>/
  <stem>_crop.bmp        # one cropped image per source BMP, 8-bit grayscale
  crop_manifest.csv      # crop-window metadata (the key file)
  run_summary.json       # run-level totals + observed fixed sizes
```

Example:
```
/home/pranayp/fmd_crop_output/single-size_fixed_crop/
  Bubble_20260903/
    20241101_110324_L24_C11_9264_crop.bmp
    20241101_111504_L24_C5_9476_crop.bmp
    crop_manifest.csv
    run_summary.json
  Fiber_20260903/
    ...
```

The BMP is just the **window cut** of the original 2448x2048 lens image. No
pixel values are touched; only a spatial crop.

## 2. How the crop window was chosen (what `left/top` mean)

For each source image the pipeline ran **once**:

1. Detect lens content (fixed threshold 3, blob filter, min blob size 500).
2. Find the **content bounding box** — the union of kept blob extents.
3. Take the **per-class canonical size** from `PER_CLASS_CROP_SINGLE`
   (e.g. `Bubble -> 1560x1532`, `Fiber -> 1560x1528`, etc., p99 of observed
   crop dimensions, rounded up to a multiple of 4).
4. **Center** that fixed window on the content centroid.
5. **Clamp** to the source 2448x2048 frame.

The window position is `(left, top)`. **The same image, regardless of crop
mode, gets the same content bbox — the modes only differ in window size.** So
the single-size and multi-size windows for the same image share an origin
(`left`, `top`).

### Special cases (read the `status` column before assuming the canonical size)

| `status` | What happened | Crop dims |
|---|---|---|
| `ok` | Content fits the canonical window. | **Equal to `canonical`** (e.g. 1560x1532). |
| `expanded` | Content too large for canonical window — pipeline expanded to `content + CONTENT_MARGIN(45)` so nothing is clipped. | **Bigger than canonical.** `width`/`height` columns tell you the actual size. |
| `blank` | No blob detected (no lens in frame). Crop = canonical window centered on **frame center** (1224, 1024), not on any content. | Equal to canonical. |

These are the only three cases. There is no padding/resize, no rotation.

## 3. The manifest columns you'll actually need

`crop_manifest.csv` (one row per cropped image):

| Column | Meaning |
|---|---|
| `file` | Source BMP stem (with `.bmp`). Pair with `<stem>_crop.bmp` for the cropped file. |
| `class` | Defect class. |
| `crop_mode` | `single-size` here. |
| `margin_used` | 120 for single-size. |
| `canonical` | The fixed WxH this class targets, e.g. `1560x1532`. |
| `status` | `ok`, `expanded`, or `blank`. See Section 2. |
| `width`, `height` | **Actual crop dimensions.** May exceed `canonical` if `status=expanded`. |
| `left`, `top` | Top-left of the crop window **in source 2448x2048 coordinates**. |
| `right`, `bottom` | Bottom-right of the crop window in source coords. |
| `orig_width`, `orig_height` | Source dims (2448, 2048) — handy when you want to reconstruct the crop from source. |
| `content_offset_x`, `content_offset_y` | Content centroid minus window center, in source px. Useful if you want to recover the lens position. |

Read `width/height` for the crop's actual size; do not assume `canonical`.

## 4. Mapping XML annotations into the crop coordinate system

The CVAT `data/annotations.xml` annotations are stored in **source 2448x2048
pixel coordinates**. To convert a source box into the crop's coordinate system:

```
xtl_crop = xtl_src - left
ytl_crop = ytl_src - top
xbr_crop = xbr_src - left
ybr_crop = ybr_src - top
```

That's it. The `left`/`top` from the manifest row of that stem is your origin.

**Sanity check:** the source box's `(xtl_src, ytl_src, xbr_src, ybr_src)` must
all lie inside `[left, top, right, bottom]` from the same manifest row. If not,
either your XML is from a different version of the data or the manifest is for a
different run — confirm the date suffix (`<Class>_20260903`).

### 4a. Axis-aligned YOLO labels (drop rotation)

```
cx_crop = ((xtl_crop + xbr_crop) / 2) / width
cy_crop = ((ytl_crop + ybr_crop) / 2) / height
w_norm  = (xbr_crop - xtl_crop) / width
h_norm  = (ybr_crop - ytl_crop) / height
label_line = f"{class_idx} {cx_crop:.6f} {cy_crop:.6f} {w_norm:.6f} {h_norm:.6f}"
```

### 4b. YOLO-OBB labels (use the rotation attribute)

CVAT stores `<box rotation="<deg>">` as a **rotation applied to the local
unrotated rectangle about its center**. To get the 4 corner points:

```python
import math, numpy as np
def corners(xtl, ytl, xbr, ybr, deg, img_w, img_h):
    cx, cy = (xtl + xbr)/2, (ytl + ybr)/2
    w, h = xbr - xtl, ybr - ytl
    rad = math.radians(deg)
    rel = np.array([[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]])
    yaw = np.array([[math.cos(rad), -math.sin(rad)],
                    [math.sin(rad),  math.cos(rad)]])
    pts = rel @ yaw.T + np.array([cx, cy])
    # normalize
    pts[:, 0] /= img_w
    pts[:, 1] /= img_h
    return " ".join(f"{v:.6f}" for v in pts.ravel())
```

After converting each source box to `corners(...)`, the YOLO-OBB label line is
`f"{class_idx} {corners(xtl_crop, ytl_crop, xbr_crop, ybr_crop, deg, width, height)}"`.

`img_w` / `img_h` here = the **manifest's `width` and `height`**, not the
canonical.

### 4c. Ready-made converter

`vm/crop_coords.py` runs both conversions in one go over the OoI subset (the
434 images that have boxes). It also writes visual previews so you can eyeball
that the boxes actually sit on the defect.

```bash
# axis-aligned YOLO labels (rotation ignored)
python3 vm/crop_coords.py obb2aabb \
    --xml  /home/amd100-user/FMD_Data_26082026/annotations.xml \
    --crop-base /home/pranayp/fmd_crop_output/single-size_fixed_crop \
    --out /home/pranayp/teammate_ooi/labels_aabb

# YOLO-OBB labels (with rotation)
python3 vm/crop_coords.py obb2obb \
    --xml  /home/amd100-user/FMD_Data_26082026/annotations.xml \
    --crop-base /home/pranayp/fmd_crop_output/single-size_fixed_crop \
    --out /home/pranayp/teammate_ooi/labels_obb

# Add --preview to also write per-image OBB-overlay PNGs into <out>/_preview/
python3 vm/crop_coords.py obb2obb ... --out ... --preview
```

Path notes: on the VM the XML lives under `/home/amd100-user/FMD_Data_26082026/`
(not in this repo); crops live at `/home/pranayp/fmd_crop_output/single-size_fixed_crop/`.
Use absolute paths in `--out` (e.g. `/home/pranayp/teammate_ooi/labels_obb`) so
the labels are obvious to downstream tools.

The script is pure stdlib + numpy; Pillow is only needed when `--preview` is set.
Each run prints a one-line report (`total label lines`, `boxes outside crop`,
`images missing manifest`) — check `outside crop == 0` before trusting the labels.

## 5. Common pitfalls

- **Forgetting `status=expanded`.** Crop dims exceed `canonical` for ~0.27% of
  images. Reading `width/height` from the manifest (not `canonical`) prevents
  off-by-90-px label errors.
- **Wrong date suffix.** `single-size_fixed_crop/Bubble_20260902` is the OLD
  run. Use `..._20260903`.
- **`path:` in `dataset.yaml`.** Omit it (skill rule). See
  `docs.ultralytics.com/guides/model-yaml-config`.
- **Multi-line manifest.** Manifests have one row per image. Don't `wc -l` and
  think each line is one image — first line is the header.
- **Pallet/scoring characters in stems.** Some stems contain
  `(0.9879337)` or commas; they are valid BMP filenames on Linux.

## 6. Quick reference — the one-page mental model

> The crop is a window cut. The window's **top-left in source coords** is
> `(left, top)` from the manifest. **Subtract `(left, top)` from every
> annotation coordinate to put it in the crop's frame.** The crop's actual
> size is `(width, height)` from the manifest — usually equal to the class's
> canonical size, occasionally larger (the no-loss guard).
