#!/usr/bin/env python3
"""
FMD single-size fixed crop for the updated defect folders (VM).

Production algorithm = src/fixed_crop.py (Fixed-Crop 0.1.0), single-size mode:
  detection: mask > 3, CC, size >= 500, mean >= 15; tier-2 retry at mean >= 13;
  tier-3 blank -> frame-centered canonical window.
  placement: canonical (W,H) window centered on content bbox, clamped to frame;
  no-loss guard: content bigger than window -> content + 45px pad (expanded).

READ-ONLY on sources. One crop per input image, guaranteed count parity.
Output: <out_base>/<root>_crop/<class>_single_crop/<stem>_crop.bmp + manifest.csv

Usage:
  python3 crop_single_size.py --classes duplicates          # smoke test
  python3 crop_single_size.py --all                         # real run
"""

import argparse
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

SRC_BASE = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
OUT_BASE = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images/crops/single_size"
ROOTS = [
    "Updated ICube Categorical Classes 20260915",
    "Updated ICube Objects 20260915",
    "ICube Defects Library",
]

# ---- production constants (src/config.py) ----
THRESHOLD = 3
MIN_BLOB_SIZE = 500
MIN_BLOB_MEAN = 15.0
RECOVERY_BLOB_MEAN = 13.0
MIN_CONTENT_ROWS = 100
CONTENT_MARGIN = 45

# canonical single-size windows (W, H) - 2026-09-03 set, unchanged (EDA 2026-09-29:
# usable across updated folders; Missing Lens stays per decision 1a -> no-loss
# guard expands oversized images; Clear assigned 1680x1644 per decision 2).
CANONICAL_SINGLE = {
    "Bubble": (1560, 1532), "Bubble Cluster": (1596, 1584),
    "Bubble Irregular": (1556, 1524), "Bubble On 123": (1540, 1540),
    "Bubble On Edge": (1564, 1564), "Bubble Scatter": (1548, 1516),
    "Cavity Off Center": (1704, 1564), "Dirty Camera": (1876, 1716),
    "Dirty Strobe": (1572, 1788), "Extraneous Polymer": (1576, 1524),
    "Fiber": (1560, 1528), "Foreign Matter": (1556, 1784),
    "HEMA Fragment": (1544, 1520), "HEMA Obstruction": (1584, 1532),
    "Lens Off Center": (1580, 1560),
    "Low Dose Obstructing Region of Interest": (1548, 1528),
    "Missing Lens": (1544, 1524), "Missing Primary Package": (1520, 1516),
    "Multiple Lenses": (1592, 1592), "Package Misalignment": (2020, 2048),
    "View Obstructed": (1496, 1296), "Wet Package": (1552, 1540),
    "Clear": (1680, 1644),                      # new class, decision 2
    "duplicates": (1560, 1532),                 # smoke-test only, default canonical
}
NAME_MAP = {"Low Dose": "Low Dose Obstructing Region of Interest",
            "HEMA": "HEMA Fragment"}
DEFAULT_CROP = (1560, 1532)

MANIFEST_COLS = ["file", "class", "status", "recovered_tier", "canonical",
                 "width", "height", "left", "top", "right", "bottom",
                 "orig_width", "orig_height"]


def content_bbox(img, mean_floor):
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


def place_window(content, Wc, Hc, W, H):
    if content is None:
        left = max((W - Wc) // 2, 0); top = max((H - Hc) // 2, 0)
        return top, top + Hc - 1, left, left + Wc - 1, False
    t, b, l, r = content
    cx = (l + r) / 2.0; cy = (t + b) / 2.0
    left = max(0, min(int(round(cx - Wc / 2.0)), W - Wc))
    top = max(0, min(int(round(cy - Hc / 2.0)), H - Hc))
    right = left + Wc - 1; bot = top + Hc - 1
    if left <= l and r <= right and top <= t and b <= bot:
        return top, bot, left, right, False
    nl = max(0, l - CONTENT_MARGIN); nr = min(W - 1, r + CONTENT_MARGIN)
    nt = max(0, t - CONTENT_MARGIN); nb = min(H - 1, b + CONTENT_MARGIN)
    return nt, nb, nl, nr, True


def process_one(task):
    src_path, out_dir, class_name = task
    p = Path(src_path)
    try:
        img = np.array(Image.open(p).convert("L"))
    except Exception as e:
        return {"file": p.name, "class": class_name, "out_dir": out_dir,
                "status": "error", "error": str(e)}
    H, W = img.shape
    bb = content_bbox(img, MIN_BLOB_MEAN)
    tier = "tier1"
    if bb is None:
        bb = content_bbox(img, RECOVERY_BLOB_MEAN)
        tier = "tier2"
    blank = bb is None

    Wc, Hc = CANONICAL_SINGLE.get(class_name, DEFAULT_CROP)
    top, bot, left, right, expanded = place_window(bb, Wc, Hc, W, H)
    crop = img[top:bot + 1, left:right + 1]
    Image.fromarray(crop).save(os.path.join(out_dir, f"{p.stem}_crop.bmp"))

    status = "blank" if blank else ("expanded" if expanded else "ok")
    return {"file": p.name, "class": class_name, "out_dir": out_dir,
            "status": status, "recovered_tier": "" if blank else tier,
            "canonical": f"{Wc}x{Hc}",
            "width": int(crop.shape[1]), "height": int(crop.shape[0]),
            "left": left, "top": top, "right": right, "bottom": bot,
            "orig_width": W, "orig_height": H}


def build_tasks(classes=None, skip_duplicates=True):
    tasks = []
    for root in ROOTS:
        root_path = os.path.join(SRC_BASE, root)
        if not os.path.isdir(root_path):
            continue
        for entry in sorted(os.listdir(root_path)):
            folder = os.path.join(root_path, entry)
            if not os.path.isdir(folder):
                continue
            if skip_duplicates and entry == "duplicates":
                continue
            if classes and entry not in classes:
                continue
            files = sorted(f for f in os.listdir(folder)
                           if f.lower().endswith(".bmp"))
            if not files:
                continue
            out_dir = os.path.join(OUT_BASE, f"{root}_crop",
                                   f"{entry}_single_crop")
            os.makedirs(out_dir, exist_ok=True)
            for f in files:
                tasks.append((os.path.join(folder, f), out_dir, entry))
    return tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", nargs="*", default=None,
                    help="only these class folders (smoke test)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    tasks = build_tasks(args.classes, skip_duplicates=args.all)
    print(f"{len(tasks)} images queued, workers={args.workers}")
    t0 = time.time()

    dir_rows = defaultdict(list)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(process_one, tasks, chunksize=16)):
            dir_rows[res["out_dir"]].append(res)
            if (i + 1) % 1000 == 0:
                print(f"  {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")

    print(f"done in {time.time() - t0:.0f}s - parity check + manifests:")
    all_ok = True
    for out_dir in sorted(dir_rows):
        rows = dir_rows[out_dir]
        statuses = defaultdict(int)
        for r in rows:
            statuses[r["status"]] += 1
        with open(os.path.join(out_dir, "manifest.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MANIFEST_COLS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        # parity: queued images == crop files on disk == manifest rows
        src_n = len(rows)
        written = sum(1 for f in os.listdir(out_dir) if f.endswith("_crop.bmp"))
        ok = written == src_n
        all_ok &= ok
        cls = rows[0]["class"]
        print(f"  {cls:<42} in={src_n:<5} out={written:<5} "
              f"{'OK' if ok else 'MISMATCH'} {dict(statuses)}")

    if not all_ok:
        print("PARITY FAILURE - investigate before use")
        return 1
    print("ALL CLASS COUNTS PARITY OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
