#!/usr/bin/env python3
"""
FMD Preprocess - Black-Border Removal Pipeline (ROI-Crop)
===========================================================

WHAT THIS SCRIPT DOES
---------------------
FMD inspection cameras save 2448x2048 8-bit grayscale BMPs that are ~60-75%
pure black: the part under inspection sits somewhere in the middle and
everything around it is empty black border. This script finds the region of
interest (ROI) in each image and crops the border away.

The crop is a PURE WINDOW SELECT: no pixel value is changed, moved,
rescaled or recalibrated, so any downstream intensity measurements remain
exactly as calibrated. Only the (left, top) offset changes, and that offset
is logged to outputs/crop_manifest.csv so later annotations can be mapped
back to original coordinates:  x_orig = x_crop + left.

THE ALGORITHM ("ROI-Crop", chosen after testing 7 alternatives)
----------------------------------------------------------------
Per image:

  1. LOAD        grayscale uint8 (color inputs are converted).
  2. THRESHOLD   mask = img > THRESHOLD (fixed 3, NOT Otsu - see PITFALLS).
                 Every pixel brighter than 3 becomes "lit".
  3. LABEL       scipy.ndimage.label groups touching lit pixels into blobs
                 (connected components - like coloring islands on a map).
                 Typical counts: 500-2000 blobs (the object + hundreds of
                 tiny sensor-noise specks).
  4. FILTER      keep a blob only if BOTH:
                   size  >= MIN_BLOB_SIZE   (real object: >1.2M px.
                                              noise specks: <=84 px)
                   mean  >= MIN_BLOB_MEAN   (real object: mean ~60.
                                              faint noise streaks: mean ~5-7)
                 Size alone is NOT enough - one sample had a 1,236 px faint
                 streak that passes a size filter. Brightness alone is not
                 enough either (a lone bright speck). Both together give a
                 ~15,000x size gap AND an ~8x brightness gap to real content.
  5. BOX         bounding box of ALL kept blobs. Using all kept blobs (not
                 just the largest) means the crop still works if a future
                 capture ever fragments the object into several pieces.
  6. MARGIN      pad the box by MARGIN px on every side, clipped to frame.
  7. BLANK GUARD if nothing passes the filter, or surviving content spans
                 fewer than MIN_CONTENT_ROWS rows, the image is declared
                 FAILED: no crop is written. A blank camera frame must fail
                 loudly, never silently produce a nonsense crop.
  8. BORDER ASSERT quality check: the discarded ring (everything outside the
                 final crop window) must be almost perfectly black. If more
                 than BORDER_ASSERT_FRAC of its pixels are lit, the image is
                 cropped anyway but flagged "warning" in the manifest - that
                 pattern means the scene has drifted (camera/pallet moved).
  9. SAVE        outputs/<image name>_crop.bmp  +  one manifest row.

WHY THESE PARAMETERS ARE SAFE TO TRUST (measured on 3 real samples)
-------------------------------------------------------------------
  noise blob size max ......... 84 px        object ........ 1,262,040 px
  noise blob mean intensity ... 4.7-7.2     object ........ 60.3 (max 118)
Any tuning within an order of magnitude of these cutoffs yields identical
output boxes - there is no knife-edge here.

PITFALLS THIS DESIGN AVOIDS (all empirically tested on real samples)
--------------------------------------------------------------------
  * Otsu / auto-threshold picks t~35 on these dark captures, which lands
    INSIDE the object (its dim rim peaks below 35) and cuts the rim
    off. Hence a fixed low threshold.
  * Row/column "density" filtering (an earlier design) is fooled by noise
    that stacks vertically: a clump of tiny specks produced a column with
    72 lit pixels, beating a >=20 density cutoff and stretching the crop
    244 px past the object. Blob MASS cannot stack - hence ROI-Crop.
  * Margin 25 was visually verified to clip the object rim. We ship 45.

USAGE
-----
    uv run preprocess.py                     # standard run (input/ -> outputs/)
    python preprocess.py --input DIR --output DIR --margin 45
Requires: numpy, pillow, scipy (see requirements.txt / pyproject.toml).

Exit codes: 0 = at least one image succeeded. 1 = fatal or all failed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

# ---------------------------------------------------------------------------
# CONFIG - the only knobs you need to touch
# ---------------------------------------------------------------------------
THRESHOLD = 3            # "lit" pixel cutoff (0-255). Fixed on purpose.
MIN_BLOB_SIZE = 500      # px. Biggest known noise blob: 84. Object: 1.26M.
MIN_BLOB_MEAN = 15.0     # mean intensity. Noise streaks: ~5-7. Object: ~60.
MARGIN = 45              # px padding added around the detected box.
MIN_CONTENT_ROWS = 100   # blank-frame guard: fewer -> declare image failed.
BORDER_ASSERT_FRAC = 0.005   # >0.5% lit pixels in discarded ring -> warning.
                             # Measured noise floors on samples 1-3: 0.0008-0.146%
                             # (the rejected faint streak in sample 3 accounts for
                             # the high end). Real camera/pallet drift lights
                             # several % of the ring at once.
PIPELINE_VERSION = "ROI-Crop 1.0.0"

MANIFEST_COLUMNS = [
    "file", "status", "left", "top", "width", "height",
    "right", "bottom",                      # derived: right=left+width-1, bottom=top+height-1 (inclusive pixels)
    "orig_width", "orig_height",
    "blobs_total", "blobs_kept", "largest_blob_px",
    "border_lit_frac", "pipeline_version", "processed_at_utc",
]


def process_image(path: Path, out_dir: Path, margin: int = MARGIN) -> dict:
    """Run ROI-Crop on one image.

    Returns a result dict matching MANIFEST_COLUMNS (minus bookkeeping cols),
    with status one of: "ok", "warning", "failed".
    Writes outputs/<stem>_crop.bmp only for ok/warning.
    """
    row = {"file": path.name, "status": "failed", "left": "", "top": "",
           "width": "", "height": "", "orig_width": "", "orig_height": "",
           "blobs_total": "", "blobs_kept": "", "largest_blob_px": "",
           "border_lit_frac": ""}

    # -- 1. LOAD -----------------------------------------------------------
    img = np.array(Image.open(path).convert("L"))       # grayscale uint8
    H, W = img.shape
    row["orig_width"], row["orig_height"] = W, H

    # -- 2. THRESHOLD ------------------------------------------------------
    mask = img > THRESHOLD

    # -- 3. LABEL BLOBS ----------------------------------------------------
    lbl, n_blobs = ndimage.label(mask)
    sizes = np.bincount(lbl.ravel())
    sizes[0] = 0                                        # background isn't a blob

    # mean intensity per blob in one pass: sum(values)/count via bincount
    sums = np.bincount(lbl.ravel(), weights=img.ravel())
    sums[0] = 0.0
    means = np.divide(sums, sizes, out=np.zeros_like(sums, dtype=float),
                      where=sizes > 0)

    # -- 4. FILTER BLOBS (size AND brightness) ------------------------------
    keep_ids = np.where((sizes >= MIN_BLOB_SIZE) & (means >= MIN_BLOB_MEAN))[0]
    row["blobs_total"] = int(n_blobs)
    row["blobs_kept"] = int(keep_ids.size)
    row["largest_blob_px"] = int(sizes.max()) if n_blobs else 0

    # -- 7a. BLANK GUARD ----------------------------------------------------
    if keep_ids.size == 0:
        print(f"  FAIL {path.name}: no blob passes size/brightness filter "
              f"(blank or corrupt frame?)")
        return row

    keep_mask = np.isin(lbl, keep_ids)

    # -- 5. BOUNDING BOX over ALL kept blobs ---------------------------------
    rows_any = np.where(keep_mask.any(axis=1))[0]
    cols_any = np.where(keep_mask.any(axis=0))[0]

    # -- 7b. BLANK GUARD (degenerate content) -------------------------------
    if (rows_any[-1] - rows_any[0] < MIN_CONTENT_ROWS
            or cols_any[-1] - cols_any[0] < MIN_CONTENT_ROWS):
        print(f"  FAIL {path.name}: content span "
              f"({rows_any[-1]-rows_any[0]+1}x{cols_any[-1]-cols_any[0]+1}) "
              f"below guard ({MIN_CONTENT_ROWS} rows)")
        return row

    # -- 6. MARGIN + clip to frame ------------------------------------------
    top = max(int(rows_any[0]) - margin, 0)
    bot = min(int(rows_any[-1]) + margin, H - 1)
    left = max(int(cols_any[0]) - margin, 0)
    right = min(int(cols_any[-1]) + margin, W - 1)

    # -- 8. BORDER ASSERT: discarded ring must be ~pure black ----------------
    ring = np.ones((H, W), dtype=bool)
    ring[top:bot + 1, left:right + 1] = False
    lit_in_ring = float((img[ring] > THRESHOLD).sum()) / max(ring.sum(), 1)
    row["border_lit_frac"] = round(lit_in_ring, 6)
    row["status"] = "warning" if lit_in_ring > BORDER_ASSERT_FRAC else "ok"
    if row["status"] == "warning":
        print(f"  WARN {path.name}: {lit_in_ring*100:.3f}% of the discarded "
              f"border is lit (> threshold {BORDER_ASSERT_FRAC*100:.1f}%) - "
              f"scene drift?")

    # -- 9. CROP + SAVE (pure window select - values untouched) --------------
    crop = img[top:bot + 1, left:right + 1]
    out_path = out_dir / f"{path.stem}_crop{path.suffix.lower()}"
    Image.fromarray(crop).save(out_path)

    row["left"], row["top"] = left, top
    row["width"], row["height"] = int(crop.shape[1]), int(crop.shape[0])
    # right/bottom are DERIVED from left/top/width/height (inclusive pixel
    # count: +1). They are shown for visibility and sanity-checking only.
    row["right"] = left + int(crop.shape[1]) - 1
    row["bottom"] = top + int(crop.shape[0]) - 1
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Crop black borders from FMD inspection BMPs (ROI-Crop). "
                    "Drop images into input/, results appear in outputs/.")
    ap.add_argument("--input", default="input", type=Path,
                    help="folder containing source images (default: input/)")
    ap.add_argument("--output", default="outputs", type=Path,
                    help="folder for crops + manifest (default: outputs/)")
    ap.add_argument("--margin", default=MARGIN, type=int,
                    help=f"padding px around detected box (default {MARGIN})")
    args = ap.parse_args(argv)

    in_dir: Path = args.input.resolve()
    out_dir: Path = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    exts = {".bmp", ".tif", ".tiff", ".png"}
    files = sorted(p for p in in_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in exts)
    if not files:
        print(f"No images found in {in_dir}. Drop .bmp files there and rerun.")
        return 1

    print(f"FMD Preprocess {PIPELINE_VERSION} | {len(files)} file(s) | "
          f"margin={args.margin} | threshold>{THRESHOLD} | "
          f"blob>={MIN_BLOB_SIZE}px & mean>={MIN_BLOB_MEAN}")
    t0 = time.perf_counter()

    results, report_entries = [], []
    for p in files:
        try:
            row = process_image(p, out_dir, margin=args.margin)
        except Exception as exc:                     # unreadable/corrupt file
            print(f"  FAIL {p.name}: unhandled error: {exc}")
            row = {"file": p.name, "status": "failed"}
        results.append(row)

    # -- manifest (current batch, overwritten each run for a consistent
    #    schema; run_report.json is the timestamped historical record) -----
    manifest = out_dir / "crop_manifest.csv"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with manifest.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS,
                             extrasaction="ignore")
        wtr.writeheader()
        for r in results:
            r.setdefault("pipeline_version", PIPELINE_VERSION)
            r.setdefault("processed_at_utc", stamp)
            wtr.writerow(r)

    # -- machine-readable run report (overwritten each run) -------------------
    ok = [r for r in results if r["status"] == "ok"]
    warn = [r for r in results if r["status"] == "warning"]
    failed = [r for r in results if r["status"] == "failed"]
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "processed_at_utc": stamp,
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "params": {"threshold": THRESHOLD, "min_blob_size": MIN_BLOB_SIZE,
                   "min_blob_mean": MIN_BLOB_MEAN, "margin": args.margin},
        "counts": {"total": len(results), "ok": len(ok),
                   "warning": len(warn), "failed": len(failed)},
        "results": results,
    }
    (out_dir / "run_report.json").write_text(json.dumps(report, indent=2))

    # -- human summary ---------------------------------------------------------
    dt = time.perf_counter() - t0
    print("-" * 72)
    for r in results:
        if r["status"] == "failed":
            print(f"  {r['file']}: FAILED")
        else:
            print(f"  {r['file']}: {r['status'].upper()} -> "
                  f"{r['width']}x{r['height']} at (+{r['left']},+{r['top']}) "
                  f"[bbox orig: L{r['left']} T{r['top']} R{r['right']} B{r['bottom']}] "
                  f"[kept {r['blobs_kept']}/{r['blobs_total']} blobs, "
                  f"border-lit {float(r['border_lit_frac'])*100:.4f}%]")
    print("-" * 72)
    print(f"{len(ok)} ok, {len(warn)} warning, {len(failed)} failed "
          f"in {dt:.1f}s | manifest: {manifest}")
    return 0 if (ok or warn) else 1


if __name__ == "__main__":
    sys.exit(main())
