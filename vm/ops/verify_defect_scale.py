#!/usr/bin/env python3
"""Read-only verification of the defect-scale comparison (crops vs teammate's native frames).

Checks:
  1. The teammate's data.yaml + split counts (the dataset behind run_bbox_experiments.py).
  2. Image dimensions for both datasets (are our crops ~1556x1536? are theirs 2448x2048?).
  3. Ground-truth box size distribution in PIXELS for both, plus the effective box size at
     imgsz=1280 after each pipeline's resize.

Run: python3 -u /home/pranayp/yolo_ooi/verify_defect_scale.py
"""
import math
import statistics as st
from collections import Counter
from pathlib import Path

from PIL import Image

THEIR = Path("/data/FMD_Data_26082026/fmd_temp_images/YOLO26_ICube_Defects")
THEIR_DS = THEIR / "dataset"
OURS = Path("/home/pranayp/yolo_ooi")
IMGSZ = 1280


def banner(t):
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


def img_dim_counter(d, limit=120):
    c = Counter()
    n = 0
    for p in sorted(d.glob("*")):
        if p.suffix.lower() not in {".bmp", ".jpg", ".jpeg", ".png"}:
            continue
        try:
            with Image.open(p) as im:
                c[im.size] += 1
        except Exception as exc:  # noqa: BLE001
            c[("ERR", str(exc)[:40])] += 1
        n += 1
        if n >= limit:
            break
    return c, n


def poly_area_px(parts, W, H):
    xs = [float(parts[i]) * W for i in (1, 3, 5, 7)]
    ys = [float(parts[i]) * H for i in (2, 4, 6, 8)]
    a = 0.0
    for i in range(4):
        j = (i + 1) % 4
        a += xs[i] * ys[j] - xs[j] * ys[i]
    return abs(a) / 2.0


def box_stats(label_dir, W, H, kind):
    """kind: 'obb' -> 9 fields (class + 8), 'aabb' -> 5 fields (class + 4)."""
    sides = []
    n_boxes = 0
    n_files = 0
    bad = 0
    for f in sorted(label_dir.glob("*.txt")):
        n_files += 1
        for line in f.read_text().splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                if kind == "obb" and len(parts) >= 9:
                    area = poly_area_px(parts, W, H)
                elif kind == "aabb" and len(parts) >= 5:
                    area = float(parts[3]) * W * float(parts[4]) * H
                else:
                    bad += 1
                    continue
            except ValueError:
                bad += 1
                continue
            n_boxes += 1
            sides.append(math.sqrt(max(area, 0.0)))
    return n_files, n_boxes, bad, sides


def describe(name, sides, scale):
    if not sides:
        print(f"  {name}: no boxes")
        return
    sides_sorted = sorted(sides)
    med = st.median(sides_sorted)
    print(f"  {name}: n={len(sides_sorted)}")
    print(f"    sqrt(area) px         : min={sides_sorted[0]:.2f} p10={sides_sorted[len(sides_sorted)//10]:.2f} "
          f"median={med:.2f} mean={st.mean(sides_sorted):.2f} p90={sides_sorted[9*len(sides_sorted)//10]:.2f} "
          f"max={sides_sorted[-1]:.2f}")
    print(f"    frac < 12 px          : {sum(1 for s in sides_sorted if s < 12) / len(sides_sorted):.3f}")
    print(f"    effective at {IMGSZ}px (x{scale:.4f}): median={med * scale:.2f} px, mean={st.mean(sides_sorted) * scale:.2f} px")


banner("1. TEAMMATE DATASET: data.yaml + split counts")
dy = THEIR / "data.yaml"
print(f"exists={dy.exists()}")
if dy.exists():
    print(dy.read_text().strip())
for split in ("train", "val"):
    imgs = list((THEIR_DS / "images" / split).glob("*")) if (THEIR_DS / "images" / split).exists() else []
    lbls = (list((THEIR_DS / "labels" / split).glob("*.txt"))
            if (THEIR_DS / "labels" / split).exists()
            else list((THEIR_DS / "images" / split).glob("*.txt")))
    print(f"  {split}: {len(imgs)} image entries, {len(lbls)} label files")
    print(f"    images dir exists={(THEIR_DS / 'images' / split).exists()}  labels dir exists={(THEIR_DS / 'labels' / split).exists()}")
sample = next(iter(sorted((THEIR_DS / "labels" / "val").glob("*.txt"))), None) if (THEIR_DS / "labels" / "val").exists() else None
if sample:
    print(f"  sample label {sample.name}:")
    for line in sample.read_text().splitlines()[:3]:
        print("   ", line)
else:
    print("  labels dir layout differs; listing entries:")
    for d in sorted(THEIR_DS.iterdir())[:10]:
        print("   ", d.name, "(dir)" if d.is_dir() else "")

banner("2. IMAGE DIMENSIONS")
tdims, tn = img_dim_counter(THEIR_DS / "images" / "val")
print(f"  teammate val ({tn} sampled): {dict(tdims)}")
odims, on = img_dim_counter(OURS / "dataset_obb" / "images" / "val")
print(f"  our dataset_obb val ({on} sampled): {dict(odims)}")
cdims, cn = img_dim_counter(OURS / "crop_detect_dataset" / "images" / "val" if (OURS / "crop_detect_dataset" / "images" / "val").exists() else OURS / "crop_detect_dataset" / "images" / "train")
print(f"  our crop_detect_dataset ({cn} sampled): {dict(cdims)}")

banner("3. GT BOX SIZES (pixels) AND EFFECTIVE SIZE AT imgsz=1280")
tW, tH = (max(tdims, key=tdims.get) if tdims else (2448, 2048))
tW, tH = int(tW), int(tH)
tf, tb, tbad, tsides = box_stats(THEIR_DS / "labels" / "val", tW, tH, "obb")
print(f"  teammate val: {tf} label files, {tb} boxes, {tbad} unparsed  (assuming {tW}x{tH})")
tscale = IMGSZ / max(tW, tH)
describe("teammate val (native frames)", tsides, tscale)
print(f"    pipeline scale to {IMGSZ}: {tscale:.4f}")

if cdims:
    cW, cH = max(cdims, key=cdims.get)
    cW, cH = int(cW), int(cH)
    print(f"  our crops: most common dim {cW}x{cH} of {len(cdims)} distinct sizes sampled")
    cf, cb, cbad, csides = box_stats(OURS / "crop_detect_dataset" / "labels" / "val", cW, cH, "aabb")
    print(f"  our crop val: {cf} label files, {cb} boxes, {cbad} unparsed")
    describe("our crops (single-class)", csides, IMGSZ / max(cW, cH))
    print(f"    pipeline scale to {IMGSZ}: {IMGSZ / max(cW, cH):.4f}")
    if tsides and csides:
        print(f"  ratio of medians (ours/theirs) at native px : {st.median(csides) / st.median(tsides):.3f}")
        ratio_eff = (st.median(csides) * IMGSZ / max(cW, cH)) / (st.median(tsides) * tscale)
        print(f"  ratio of medians at {IMGSZ}px (ours/theirs)  : {ratio_eff:.3f}")

banner("4. ALL DISTINCT CROP DIMENSIONS SEEN IN dataset_obb (val, sampled)")
for (w, h), n in sorted(odims.items(), key=lambda kv: -kv[1])[:15]:
    print(f"  {w}x{h}  x{n}")

banner("DONE")
