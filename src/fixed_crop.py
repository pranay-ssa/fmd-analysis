#!/usr/bin/env python3
"""
FMD Fixed-Size Crop (v0.1 draft) — per-class fixed crop size, lens-centered.

Replaces variable-size ROI-Crop output with, per class and per crop mode, a FIXED
window size (from config.get_crop_size) positioned so the detected lens content
is centered in the window. Blank (no-blob) frames fall back to a window centered
on the frame center. A no-loss guard expands the window (content + CONTENT_MARGIN)
only when an image's content is too large for the fixed window, so the lens is
never clipped — that is the only case where the output size differs from canonical.

Key properties:
  * Detection runs ONCE per image even for --modes both; single & multi windows are
    placed from the same content bbox (the modes differ only in window size/margin).
  * Pure window select: no pixel is rescaled, so calibration is preserved.
  * CPU-heavy: detection is scipy.ndimage.label over 2448x2048; run a subset first,
    use --workers for parallel classes.

USAGE
    uv run src/fixed_crop.py --all --modes both --output-base run
    uv run src/fixed_crop.py --classes "Cavity Off Center" "Wet Package" --modes single-size
    uv run src/fixed_crop.py --classes "Missing Primary Package" --modes both

Output layout
    run/<mode>_fixed_crop/<Class>_<YYYYMMDD>/<stem>_crop.bmp
    run/<mode>_fixed_crop/<Class>_<YYYYMMDD>/crop_manifest.csv
    run/<mode>_fixed_crop/<Class>_<YYYYMMDD>/run_summary.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    THRESHOLD, MIN_BLOB_SIZE, MIN_BLOB_MEAN, RECOVERY_BLOB_MEAN,
    MIN_CONTENT_ROWS, CONTENT_MARGIN, get_crop_size, get_margin,
)

EXTS = {".bmp", ".tif", ".tiff", ".png"}
PIPELINE_VERSION = "Fixed-Crop 0.1.0"


def content_bbox(img: np.ndarray, mean_floor: float):
    """(top, bot, left, right) inclusive of all kept-blob content, or None."""
    H, W = img.shape
    mask = img > THRESHOLD
    lbl, _ = ndimage.label(mask)
    sizes = np.bincount(lbl.ravel()); sizes[0] = 0
    sums = np.bincount(lbl.ravel(), weights=img.ravel()); sums[0] = 0.0
    means = np.divide(sums, sizes, out=np.zeros_like(sums, float), where=sizes > 0)
    keep = np.where((sizes >= MIN_BLOB_SIZE) & (means >= mean_floor))[0]
    if keep.size == 0:
        return None
    km = np.isin(lbl, keep)
    rs = np.where(km.any(axis=1))[0]; cs = np.where(km.any(axis=0))[0]
    if rs[-1] - rs[0] < MIN_CONTENT_ROWS or cs[-1] - cs[0] < MIN_CONTENT_ROWS:
        return None
    return (int(rs[0]), int(rs[-1]), int(cs[0]), int(cs[-1]))


def place_fixed_window(content, Wc: int, Hc: int, W: int, H: int):
    """Place a Wc x Hc window centered on content, clamped to frame.
    Returns (top, bot, left, right, expanded). expanded=True when the fixed
    window cannot contain the content (no-loss guard triggered)."""
    if content is None:                       # blank frame -> frame-centered
        left = max((W - Wc) // 2, 0); top = max((H - Hc) // 2, 0)
        return top, top + Hc - 1, left, left + Wc - 1, False

    t, b, l, r = content
    cx = (l + r) / 2.0; cy = (t + b) / 2.0
    left = max(0, min(int(round(cx - Wc / 2.0)), W - Wc))
    top = max(0, min(int(round(cy - Hc / 2.0)), H - Hc))
    right = left + Wc - 1; bot = top + Hc - 1

    if left <= l and r <= right and top <= t and b <= bot:
        return top, bot, left, right, False
    # no-loss guard
    nl = max(0, l - CONTENT_MARGIN); nr = min(W - 1, r + CONTENT_MARGIN)
    nt = max(0, t - CONTENT_MARGIN); nb = min(H - 1, b + CONTENT_MARGIN)
    return nt, nb, nl, nr, True


def process_image(args):
    path, class_name, modes, out_dirs = args
    stem = path.stem
    err = {"file": path.name, "class": class_name, "status": "error",
           "error": "unreadable"}
    try:
        img = np.array(Image.open(path).convert("L"))
    except Exception:
        return [err]
    H, W = img.shape

    bb = content_bbox(img, MIN_BLOB_MEAN)
    tier = "tier1"
    if bb is None:
        bb = content_bbox(img, RECOVERY_BLOB_MEAN)
        tier = "tier2"
    blank = bb is None

    rows = []
    for mode in modes:
        Wc, Hc = get_crop_size(class_name, mode)
        margin = get_margin(class_name, mode)
        top, bot, left, right, expanded = place_fixed_window(bb, Wc, Hc, W, H)
        crop = img[top:bot + 1, left:right + 1]
        Image.fromarray(crop).save(out_dirs[mode] / f"{stem}_crop{path.suffix.lower()}")

        status = "blank" if blank else ("expanded" if expanded else "ok")
        if blank:
            off_x = off_y = ""
        else:
            off_x = round((bb[2] + bb[3]) / 2.0 - (W - 1) / 2.0, 1)
            off_y = round((bb[0] + bb[1]) / 2.0 - (H - 1) / 2.0, 1)
        rows.append({
            "file": path.name, "class": class_name, "crop_mode": mode,
            "margin_used": margin, "canonical": f"{Wc}x{Hc}", "status": status,
            "recovered_tier": "" if bb is None else tier,
            "width": int(crop.shape[1]), "height": int(crop.shape[0]),
            "left": left, "top": top, "right": right, "bottom": bot,
            "orig_width": W, "orig_height": H,
            "content_offset_x": off_x, "content_offset_y": off_y,
        })
    return rows


MANIFEST_COLS = ["file", "class", "crop_mode", "margin_used", "canonical",
                 "status", "recovered_tier", "width", "height", "left", "top",
                 "right", "bottom", "orig_width", "orig_height",
                 "content_offset_x", "content_offset_y"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Fixed-size per-class crop, lens-centered (FMD).")
    ap.add_argument("--input-base", default=str(Path("data/incoming").resolve()))
    ap.add_argument("--output-base", default=str(Path("run").resolve()))
    ap.add_argument("--classes", nargs="+", help="class names to crop")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--modes", nargs="+", default=["both"],
                    choices=["both", "single-size", "multi-size"])
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)

    modes = (["single-size", "multi-size"] if args.modes == ["both"]
             else list(args.modes))
    in_base = Path(args.input_base).resolve()
    out_base = Path(args.output_base).resolve()
    date_stamp = time.strftime("%Y%m%d")

    class_dirs = [d for d in sorted(in_base.iterdir()) if d.is_dir()]
    if args.classes:
        wanted = set(args.classes)
        class_dirs = [d for d in class_dirs if d.name in wanted]
        for m in sorted(wanted - {d.name for d in class_dirs}):
            print(f"  WARN: no class folder: {m}")
    elif not args.all:
        print("Provide --classes ... or --all.")
        return 1
    class_dirs = [d for d in class_dirs
                  if any(p.suffix.lower() in EXTS for p in d.iterdir())]
    if not class_dirs:
        print(f"No class folders with images under {in_base}")
        return 1

    out_dirs = {}
    for d in class_dirs:
        out_dirs[d.name] = {}
        for mode in modes:
            od = out_base / f"{mode}_fixed_crop" / f"{d.name}_{date_stamp}"
            od.mkdir(parents=True, exist_ok=True)
            out_dirs[d.name][mode] = od

    files = [(p, d.name, modes, out_dirs[d.name])
             for d in class_dirs
             for p in sorted(d.iterdir()) if p.is_file() and p.suffix.lower() in EXTS]
    n = len(files)
    print(f"Fixed-Crop {PIPELINE_VERSION} | {len(class_dirs)} classes | "
          f"{n} images | modes={modes} | workers={args.workers}")
    print(f"Output under {out_base}")
    t0 = time.perf_counter()

    all_rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, rows in enumerate(ex.map(process_image, files, chunksize=4), 1):
            all_rows.extend(rows)
            if i % 300 == 0 or i == n:
                print(f"  {i}/{n} ...", flush=True)

    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    by_class_mode = defaultdict(list)
    for r in all_rows:
        by_class_mode[(r.get("crop_mode"), r.get("class"))].append(r)

    for (mode, cn), sub in sorted(by_class_mode.items()):
        if mode is None:
            continue
        od = out_dirs[cn][mode]
        with (od / "crop_manifest.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=MANIFEST_COLS, extrasaction="ignore")
            w.writeheader()
            for r in sub:
                w.writerow(r)
        c = Counter(r["status"] for r in sub)
        sizes = Counter((r["width"], r["height"]) for r in sub
                        if r["status"] != "expanded")
        print(f"  [{mode}] {cn}: {len(sub)} | "
              f"{' '.join(f'{k}={v}' for k, v in sorted(c.items()))} | "
              f"fixed sizes {sorted(f'{w}x{h}' for w, h in sizes)}")
        (od / "run_summary.json").write_text(json.dumps(
            {"class": cn, "mode": mode, "counts": dict(c),
             "fixed_sizes_observed": sorted(f"{w}x{h}" for w, h in sizes),
             "generated_at_utc": stamp}, indent=2))

    dt = time.perf_counter() - t0
    print("-" * 72)
    print(f"{n} images in {dt:.1f}s ({dt / max(n, 1):.2f}s/img avg)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
