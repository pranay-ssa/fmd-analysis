#!/usr/bin/env python3
"""
Test Script: Multi-Size vs Single-Size Crop Modes
==================================================

Runs both crop modes on a class folder and compares results.
Outputs go to separate folders under run/ (NOT run/crops/).

USAGE
-----
    # Test a single class:
    uv run tests/test_crop_modes.py --class "Wet Package"

    # Test multiple classes:
    uv run tests/test_crop_modes.py --class "Wet Package" "Fiber" "Bubble"

    # Test all classes in data/incoming/:
    uv run tests/test_crop_modes.py --all

    # Custom input/output base:
    uv run tests/test_crop_modes.py --class "Fiber" --input-base data/incoming --output-base run

WHAT IT DOES
------------
1. For each class, runs ROI-Crop with multi-size margins (per-class from config)
2. For each class, runs ROI-Crop with single-size margin (120px fixed)
3. Saves to separate folders:
   - run/multi_size_crop/<Class>_<YYYYMMDD>/
   - run/single_size_crop/<Class>_<YYYYMMDD>/
4. Compares file sizes between the two modes
5. Generates a summary report

REQUIREMENTS
------------
- numpy, pillow, scipy (same as main pipeline)
- src/config.py with margin settings
- src/preprocess.py for the core algorithm
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from PIL import Image
from scipy import ndimage

from config import (
    THRESHOLD, MIN_BLOB_SIZE, MIN_BLOB_MEAN, RECOVERY_BLOB_MEAN, MIN_CONTENT_ROWS,
    BORDER_ASSERT_FRAC, PIPELINE_VERSION, INPUT_EXTENSIONS,
    MANIFEST_COLUMNS, get_margin, get_mode_description,
    PER_CLASS_MARGINS, DEFAULT_MARGIN, SINGLE_SIZE_MARGIN
)


def _detect_box(img: np.ndarray, mean_floor: float, margin: int):
    """Return (top, bot, left, right) box or None if no blob passes the
    size/brightness filter with the given mean floor."""
    H, W = img.shape
    mask = img > THRESHOLD
    lbl, n_blobs = ndimage.label(mask)
    sizes = np.bincount(lbl.ravel())
    sizes[0] = 0
    sums = np.bincount(lbl.ravel(), weights=img.ravel())
    sums[0] = 0.0
    means = np.divide(sums, sizes, out=np.zeros_like(sums, dtype=float),
                      where=sizes > 0)
    keep_ids = np.where((sizes >= MIN_BLOB_SIZE) & (means >= mean_floor))[0]
    if keep_ids.size == 0:
        return None, n_blobs, int(keep_ids.size), int(sizes.max()) if n_blobs else 0
    keep_mask = np.isin(lbl, keep_ids)
    rows_any = np.where(keep_mask.any(axis=1))[0]
    cols_any = np.where(keep_mask.any(axis=0))[0]
    if (rows_any[-1] - rows_any[0] < MIN_CONTENT_ROWS
            or cols_any[-1] - cols_any[0] < MIN_CONTENT_ROWS):
        return None, n_blobs, int(keep_ids.size), int(sizes.max()) if n_blobs else 0
    top = max(int(rows_any[0]) - margin, 0)
    bot = min(int(rows_any[-1]) + margin, H - 1)
    left = max(int(cols_any[0]) - margin, 0)
    right = min(int(cols_any[-1]) + margin, W - 1)
    return (top, bot, left, right), n_blobs, int(keep_ids.size), \
        int(sizes.max()) if n_blobs else 0


def process_image(path: Path, out_dir: Path, margin: int, crop_mode: str,
                  center_size: tuple[int, int] | None = None) -> dict:
    """
    Run ROI-Crop on one image with a three-tier recovery fallback.
    Same logic as preprocess.py but with crop_mode tracking.

    Tier 1: standard detection at MIN_BLOB_MEAN (unchanged, deterministic).
    Tier 2: if nothing detected, retry that same image at RECOVERY_BLOB_MEAN
            (recovers dim-but-real content without touching Tier-1 images).
    Tier 3: if still nothing (true blank frame), center-crop the frame at the
            class-typical crop size. Correct for blank by design.
    """
    row = {
        "file": path.name, "status": "failed", "left": "", "top": "",
        "width": "", "height": "", "orig_width": "", "orig_height": "",
        "blobs_total": "", "blobs_kept": "", "largest_blob_px": "",
        "border_lit_frac": "", "crop_mode": crop_mode, "margin_used": margin,
        "recovered": ""
    }

    # 1. LOAD
    img = np.array(Image.open(path).convert("L"))
    H, W = img.shape
    row["orig_width"], row["orig_height"] = W, H

    # TIER 1: standard detection
    box, n_blobs, kept, largest = _detect_box(img, MIN_BLOB_MEAN, margin)
    row["blobs_total"] = n_blobs
    row["blobs_kept"] = kept
    row["largest_blob_px"] = largest
    recovered = ""

    if box is None:
        # TIER 2: relaxed floor for dim content
        box, _, _, _ = _detect_box(img, RECOVERY_BLOB_MEAN, margin)
        if box is not None:
            recovered = "tier2_blob13"

    if box is None and center_size is not None:
        # TIER 3: true blank frame -> class-typical center crop
        cw, ch = center_size
        cw = min(cw, W); ch = min(ch, H)
        left = max((W - cw) // 2, 0)
        top = max((H - ch) // 2, 0)
        right = min(left + cw, W) - 1
        bot = min(top + ch, H) - 1
        box = (top, bot, left, right)
        recovered = "tier3_center"

    if box is None:
        return row

    top, bot, left, right = box

    # 8. BORDER ASSERT
    ring = np.ones((H, W), dtype=bool)
    ring[top:bot + 1, left:right + 1] = False
    lit_in_ring = float((img[ring] > THRESHOLD).sum()) / max(ring.sum(), 1)
    row["border_lit_frac"] = round(lit_in_ring, 6)
    row["status"] = "warning" if lit_in_ring > BORDER_ASSERT_FRAC else "ok"
    row["recovered"] = recovered

    # 9. CROP + SAVE
    crop = img[top:bot + 1, left:right + 1]
    out_path = out_dir / f"{path.stem}_crop{path.suffix.lower()}"
    Image.fromarray(crop).save(out_path)

    row["left"], row["top"] = left, top
    row["width"], row["height"] = int(crop.shape[1]), int(crop.shape[0])
    row["right"] = left + int(crop.shape[1]) - 1
    row["bottom"] = top + int(crop.shape[0]) - 1

    # Store file size for comparison
    row["output_file_size_bytes"] = out_path.stat().st_size

    return row


def run_crop_mode(
    class_name: str,
    input_dir: Path,
    output_base: Path,
    crop_mode: str,
    date_stamp: str
) -> list[dict]:
    """
    Run one crop mode on all images in a class folder.
    Returns list of result dicts.
    """
    # Create output folder
    out_dir = output_base / f"{class_name}_{date_stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get files
    exts = INPUT_EXTENSIONS
    files = sorted(p for p in input_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in exts)
    
    if not files:
        print(f"  No images found in {input_dir}")
        return []

    # Get margin for this class/mode
    margin = get_margin(class_name, crop_mode)
    
    print(f"\n{'='*72}")
    print(f"CROP MODE: {crop_mode.upper()}")
    print(f"CLASS: {class_name}")
    print(f"MARGIN: {margin}px")
    print(f"INPUT: {input_dir} ({len(files)} files)")
    print(f"OUTPUT: {out_dir}")
    print(f"{'='*72}")

    # Pre-pass: compute the class-typical (median) detected crop size so
    # tier-3 center-crop fallback has a sensible target for true blank frames.
    detected_sizes = []
    for p in files:
        try:
            img = np.array(Image.open(p).convert("L"))
            box = _detect_box(img, MIN_BLOB_MEAN, margin)[0]
            if box is None:
                box = _detect_box(img, RECOVERY_BLOB_MEAN, margin)[0]
            if box is not None:
                top, bot, left, right = box
                detected_sizes.append((right - left + 1, bot - top + 1))
        except Exception:
            continue
    center_size = None
    if detected_sizes:
        ws = sorted(s[0] for s in detected_sizes)
        hs = sorted(s[1] for s in detected_sizes)
        center_size = (ws[len(ws) // 2], hs[len(hs) // 2])
    if center_size:
        print(f"CENTER-SIZE (tier-3 target): {center_size[0]}x{center_size[1]} "
              f"from {len(detected_sizes)} detected crops")
    else:
        print("CENTER-SIZE: not set (no detected crops; tier-3 disabled)")

    # Process all images
    results = []
    t0 = time.perf_counter()
    
    for i, p in enumerate(files, 1):
        print(f"  [{i:3d}/{len(files)}] {p.name}...", end=" ", flush=True)
        try:
            row = process_image(p, out_dir, margin, crop_mode, center_size)
            results.append(row)
            if row["status"] == "failed":
                print("FAILED")
            else:
                size_kb = row.get("output_file_size_bytes", 0) / 1024
                rec = f" [{row['recovered']}]" if row.get("recovered") else ""
                print(f"{row['status'].upper()} -> {row['width']}x{row['height']} "
                      f"({size_kb:.1f} KB){rec}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({"file": p.name, "status": "failed", "crop_mode": crop_mode,
                            "recovered": ""})

    dt = time.perf_counter() - t0
    
    # Write manifest
    manifest_path = out_dir / "crop_manifest.csv"
    with manifest_path.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        wtr.writeheader()
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for r in results:
            r.setdefault("pipeline_version", PIPELINE_VERSION)
            r.setdefault("processed_at_utc", stamp)
            wtr.writerow(r)

    # Write run report
    ok = [r for r in results if r["status"] == "ok"]
    warn = [r for r in results if r["status"] == "warning"]
    failed = [r for r in results if r["status"] == "failed"]
    recovered = [r for r in results if r.get("recovered")]
    t2 = sum(1 for r in results if r.get("recovered") == "tier2_blob13")
    t3 = sum(1 for r in results if r.get("recovered") == "tier3_center")
    
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "crop_mode": crop_mode,
        "margin": margin,
        "class_name": class_name,
        "processed_at_utc": stamp,
        "input_dir": str(input_dir),
        "output_dir": str(out_dir),
        "counts": {"total": len(results), "ok": len(ok),
                   "warning": len(warn), "failed": len(failed),
                   "recovered_tier2": t2, "recovered_tier3": t3,
                   "recovered_total": len(recovered)},
        "center_size": center_size,
        "results": results,
    }
    (out_dir / "run_report.json").write_text(json.dumps(report, indent=2))

    print(f"\nSUMMARY: {len(ok)} ok, {len(warn)} warning, {len(failed)} failed, "
          f"recovered {len(recovered)} (tier2={t2}, tier3={t3}) in {dt:.1f}s")
    
    return results


def compare_file_sizes(multi_results: list[dict], single_results: list[dict]) -> dict:
    """
    Compare file sizes between multi-size and single-size modes.
    Returns comparison stats.
    """
    multi_sizes = [r.get("output_file_size_bytes", 0) for r in multi_results 
                   if r.get("status") in ("ok", "warning")]
    single_sizes = [r.get("output_file_size_bytes", 0) for r in single_results 
                    if r.get("status") in ("ok", "warning")]
    
    if not multi_sizes or not single_sizes:
        return {"error": "No successful crops to compare"}
    
    # Pair by filename
    multi_by_file = {r["file"]: r for r in multi_results}
    single_by_file = {r["file"]: r for r in single_results}
    
    paired = []
    for fname in multi_by_file:
        if fname in single_by_file:
            m = multi_by_file[fname]
            s = single_by_file[fname]
            if m.get("status") in ("ok", "warning") and s.get("status") in ("ok", "warning"):
                m_size = m.get("output_file_size_bytes", 0)
                s_size = s.get("output_file_size_bytes", 0)
                paired.append({
                    "file": fname,
                    "multi_size_bytes": m_size,
                    "single_size_bytes": s_size,
                    "difference_bytes": s_size - m_size,
                    "difference_pct": ((s_size - m_size) / m_size * 100) if m_size > 0 else 0,
                    "multi_margin": m.get("margin_used"),
                    "single_margin": s.get("margin_used"),
                })
    
    if not paired:
        return {"error": "No paired files to compare"}
    
    # Compute stats
    diffs = [p["difference_bytes"] for p in paired]
    pcts = [p["difference_pct"] for p in paired]
    
    return {
        "total_paired": len(paired),
        "avg_difference_bytes": sum(diffs) / len(diffs),
        "avg_difference_pct": sum(pcts) / len(pcts),
        "max_difference_bytes": max(diffs),
        "min_difference_bytes": min(diffs),
        "multi_avg_bytes": sum(p["multi_size_bytes"] for p in paired) / len(paired),
        "single_avg_bytes": sum(p["single_size_bytes"] for p in paired) / len(paired),
        "details": paired[:10],  # First 10 for brevity
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Test multi-size vs single-size crop modes"
    )
    ap.add_argument("--class", nargs="+", dest="classes",
                    help="Class name(s) to test (e.g. 'Wet Package' 'Fiber')")
    ap.add_argument("--all", action="store_true",
                    help="Test all classes in input-base")
    ap.add_argument("--input-base", type=Path, default=Path("data/incoming"),
                    help="Base input directory (default: data/incoming)")
    ap.add_argument("--output-base", type=Path, default=Path("run"),
                    help="Base output directory (default: run)")
    ap.add_argument("--date", default=time.strftime("%Y%m%d"),
                    help="Date stamp for output folders (default: YYYYMMDD)")
    args = ap.parse_args(argv)

    # Determine which classes to test
    if args.all:
        classes = [d.name for d in args.input_base.iterdir() if d.is_dir()]
    elif args.classes:
        classes = args.classes
    else:
        print("ERROR: Specify --class or --all")
        return 1

    print(f"FMD Preprocess Crop Mode Test")
    print(f"Pipeline: {PIPELINE_VERSION}")
    print(f"Date stamp: {args.date}")
    print(f"Classes to test: {len(classes)}")
    print(f"Multi-size margins: {PER_CLASS_MARGINS} (default: {DEFAULT_MARGIN}px)")
    print(f"Single-size margin: {SINGLE_SIZE_MARGIN}px")

    all_comparisons = {}
    
    for class_name in classes:
        input_dir = args.input_base / class_name
        if not input_dir.exists():
            print(f"\nWARNING: {input_dir} does not exist, skipping")
            continue

        print(f"\n{'#'*72}")
        print(f"# CLASS: {class_name}")
        print(f"{'#'*72}")

        # Run multi-size mode
        multi_out = args.output_base / "multi_size_crop"
        multi_results = run_crop_mode(
            class_name, input_dir, multi_out, "multi-size", args.date
        )

        # Run single-size mode
        single_out = args.output_base / "single_size_crop"
        single_results = run_crop_mode(
            class_name, input_dir, single_out, "single-size", args.date
        )

        # Compare
        comparison = compare_file_sizes(multi_results, single_results)
        all_comparisons[class_name] = comparison

        # Print comparison
        print(f"\n{'='*72}")
        print(f"FILE SIZE COMPARISON: {class_name}")
        print(f"{'='*72}")
        if "error" in comparison:
            print(f"  {comparison['error']}")
        else:
            print(f"  Files compared: {comparison['total_paired']}")
            print(f"  Multi-size avg: {comparison['multi_avg_bytes']/1024:.1f} KB")
            print(f"  Single-size avg: {comparison['single_avg_bytes']/1024:.1f} KB")
            print(f"  Avg increase: {comparison['avg_difference_pct']:.1f}% "
                  f"(+{comparison['avg_difference_bytes']/1024:.1f} KB)")
            print(f"  Max increase: {comparison['max_difference_bytes']/1024:.1f} KB")
            
            # Show sample details
            if comparison["details"]:
                print(f"\n  Sample files:")
                for d in comparison["details"][:5]:
                    print(f"    {d['file'][:50]:50s} "
                          f"multi={d['multi_size_bytes']/1024:7.1f}KB "
                          f"single={d['single_size_bytes']/1024:7.1f}KB "
                          f"diff={d['difference_pct']:+.1f}%")

    # Save overall comparison report
    report_path = args.output_base / f"crop_mode_comparison_{args.date}.json"
    report_path.write_text(json.dumps(all_comparisons, indent=2))
    print(f"\n{'='*72}")
    print(f"Comparison report saved to: {report_path}")
    print(f"{'='*72}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
