#!/usr/bin/env python3
"""
FMD single-size usability EDA (updated folders).

Runs the EXACT detection pass of the production fixed_crop.py pipeline
(mask > THRESHOLD, CC, size >= MIN_BLOB_SIZE, mean >= MIN_BLOB_MEAN,
tier-2 fallback at RECOVERY_BLOB_MEAN, tier-3 blank) and checks whether
the canonical SINGLE-size window (which already embeds the 120px margin)
can contain each image's content bbox without triggering the no-loss
guard (content + CONTENT_MARGIN).

READ-ONLY: no crops are written. One detection pass per image, same as
the real run would do, so this doubles as a timing estimate.

Output: JSON + markdown table per source root:
  n, ok%, expanded (no-loss guard) count, recovered tier2/tier3 counts,
  and the largest content+45px extents seen (to judge if the canonical
  size could be bumped for the new data).
"""

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import numpy as np
from PIL import Image
from scipy import ndimage

BASE = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
ROOTS = [
    ("Updated ICube Categorical Classes 20260915", "categorical"),
    ("Updated ICube Objects 20260915", "objects"),
    ("ICube Defects Library", "old_library"),
]

# ---- production constants (src/config.py, fixed_crop.py) ----
THRESHOLD = 3
MIN_BLOB_SIZE = 500
MIN_BLOB_MEAN = 15.0
RECOVERY_BLOB_MEAN = 13.0
MIN_CONTENT_ROWS = 100
CONTENT_MARGIN = 45

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
}
NAME_MAP = {"Low Dose": "Low Dose Obstructing Region of Interest",
            "HEMA": "HEMA Fragment"}


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


def classify_one(path, canon):
    """Return status + needed window extents for one image."""
    try:
        img = np.array(Image.open(path).convert("L"))
    except Exception:
        return {"status": "error", "need_w": 0, "need_h": 0}
    H, W = img.shape
    bb = content_bbox(img, MIN_BLOB_MEAN)
    tier = 1
    if bb is None:
        bb = content_bbox(img, RECOVERY_BLOB_MEAN)
        tier = 2
    if bb is None:
        return {"status": "blank", "tier": 3, "need_w": 0, "need_h": 0}
    t, b, l, r = bb
    need_w = (r - l + 1) + 2 * CONTENT_MARGIN
    need_h = (b - t + 1) + 2 * CONTENT_MARGIN
    Wc, Hc = canon
    if need_w <= Wc and need_h <= Hc:
        return {"status": "ok", "tier": tier, "need_w": need_w, "need_h": need_h}
    # window fits frame but content too big -> no-loss guard would trigger
    return {"status": "expanded", "tier": tier, "need_w": need_w, "need_h": need_h}


def scan_folder(folder):
    out = []
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".bmp"):
            out.append(os.path.join(folder, name))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eda_usability.json")
    ap.add_argument("--limit", type=int, default=0, help="cap images per class (smoke)")
    ap.add_argument("--roots", nargs="*", default=None,
                    help="filter: categorical objects old_library")
    args = ap.parse_args()

    want = args.roots or [r[1] for r in ROOTS]
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "limit_per_class": args.limit or None, "roots": {}}
    md = ["# Single-size usability EDA (canonical windows, 120px margin embedded)", ""]

    for root_name, short in ROOTS:
        if short not in want:
            continue
        root_path = os.path.join(BASE, root_name)
        if not os.path.isdir(root_path):
            continue
        report["roots"][short] = {}
        md += [f"## {root_name}", "",
               "| class | n | ok | expanded | tier2 | tier3 | max need WxH | canonical | verdict |",
               "|---|---|---|---|---|---|---|---|---|"]
        for entry in sorted(os.listdir(root_path)):
            folder = os.path.join(root_path, entry)
            if not os.path.isdir(folder):
                continue
            canon_name = NAME_MAP.get(entry, entry)
            canon = CANONICAL_SINGLE.get(canon_name)
            files = scan_folder(folder)
            if not files:
                continue
            if args.limit:
                files = files[:args.limit]
            with ProcessPoolExecutor(max_workers=16) as ex:
                res = list(ex.map(classify_one, files, [canon or (0, 0)] * len(files)))
            n = len(res)
            ok = sum(1 for r in res if r["status"] == "ok")
            exp = sum(1 for r in res if r["status"] == "expanded")
            tier2_cnt = sum(1 for r in res if r.get("tier") == 2)
            t3 = sum(1 for r in res if r["status"] == "blank")
            mw = max((r["need_w"] for r in res), default=0)
            mh = max((r["need_h"] for r in res), default=0)
            if canon:
                cw, ch = canon
                if exp == 0:
                    verdict = "USABLE as-is"
                elif exp <= max(1, n // 20):
                    verdict = f"usable, {exp} no-loss-guard images ({exp}/{n})"
                else:
                    verdict = f"PROBLEM: {exp}/{n} would trigger no-loss guard"
                canon_str = f"{cw}x{ch}"
            else:
                verdict = "no canonical (new class) - skip"
                canon_str = "-"
            md.append(f"| {entry} | {n} | {ok} | {exp} | {tier2_cnt} | {t3} | {mw}x{mh} | {canon_str} | {verdict} |")
            report["roots"][short][entry] = {
                "n": n, "ok": ok, "expanded": exp, "max_need_w": mw, "max_need_h": mh,
                "canonical": canon_str, "verdict": verdict}
        md.append("")

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)
    text = "\n".join(md)
    with open(args.out.replace(".json", ".md"), "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
