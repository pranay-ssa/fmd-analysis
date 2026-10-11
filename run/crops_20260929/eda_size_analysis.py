#!/usr/bin/env python3
"""
FMD size EDA: BMP header dimension scan for the updated defect folders.

Reads ONLY the BMP file header (offset 18/22, BITMAPINFOHEADER) - no decode,
no modification of any source file. Pure read-only walk.

For each class folder it reports:
  n images, unique (W,H) dims, min / p50 / p99 / max width & height

And compares against the canonical per-class SINGLE-size crop windows
(PER_CLASS_CROP_SINGLE, 2026-09-03, src/config.py) to answer:
  "are the previously fixed sizes still usable for the updated folders?"

Usage:
  python3 eda_size_analysis.py --out <output.json>
"""

import argparse
import json
import os
import statistics
from datetime import datetime, timezone

BASE = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
ROOTS = [
    "Updated ICube Categorical Classes 20260915",
    "Updated ICube Objects 20260915",
    "ICube Defects Library",  # old baseline, for comparison
]

# Canonical single-size crop windows (W, H) from src/config.py 2026-09-03
CANONICAL_SINGLE = {
    "Bubble": (1560, 1532),
    "Bubble Cluster": (1596, 1584),
    "Bubble Irregular": (1556, 1524),
    "Bubble On 123": (1540, 1540),
    "Bubble On Edge": (1564, 1564),
    "Bubble Scatter": (1548, 1516),
    "Cavity Off Center": (1704, 1564),
    "Dirty Camera": (1876, 1716),
    "Dirty Strobe": (1572, 1788),
    "Extraneous Polymer": (1576, 1524),
    "Fiber": (1560, 1528),
    "Foreign Matter": (1556, 1784),
    "HEMA Fragment": (1544, 1520),
    "HEMA Obstruction": (1584, 1532),
    "Lens Off Center": (1580, 1560),
    "Low Dose Obstructing Region of Interest": (1548, 1528),
    "Missing Lens": (1544, 1524),
    "Missing Primary Package": (1520, 1516),
    "Multiple Lenses": (1592, 1592),
    "Package Misalignment": (2020, 2048),
    "View Obstructed": (1496, 1296),
    "Wet Package": (1552, 1540),
}

# Folder name -> canonical class name (updated folders use short forms)
NAME_MAP = {
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "HEMA": "HEMA Fragment",  # Objects root: HEMA (20 imgs); verify against old HEMA Fragment (8)
}


def bmp_header_dims(path):
    """Return (width, height) from BMP header, or None if unreadable."""
    with open(path, "rb") as f:
        head = f.read(26)
    if len(head) < 26 or head[:2] != b"BM":
        return None
    w = int.from_bytes(head[18:22], "little", signed=True)
    h = int.from_bytes(head[22:26], "little", signed=True)
    if w <= 0:
        return None
    return (w, abs(h))


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def scan_folder(folder):
    dims = []
    files = sorted(os.listdir(folder))
    for name in files:
        if not name.lower().endswith(".bmp"):
            continue
        d = bmp_header_dims(os.path.join(folder, name))
        if d:
            dims.append(d)
    return dims


def summarize(dims):
    ws = sorted(d[0] for d in dims)
    hs = sorted(d[1] for d in dims)
    uniq = sorted(set(dims))
    return {
        "n": len(dims),
        "unique_dims": [{"w": w, "h": h} for (w, h) in uniq],
        "width": {"min": ws[0], "p50": round(pct(ws, 50)), "p99": round(pct(ws, 99)), "max": ws[-1]},
        "height": {"min": hs[0], "p50": round(pct(hs, 50)), "p99": round(pct(hs, 99)), "max": hs[-1]},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eda_size_analysis.json")
    args = ap.parse_args()

    report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "roots": {}}
    lines = ["# FMD size EDA - updated folders vs canonical single-size windows", ""]

    for root in ROOTS:
        root_path = os.path.join(BASE, root)
        if not os.path.isdir(root_path):
            continue
        report["roots"][root] = {}
        lines.append(f"## Source: {root}")
        lines.append("")
        lines.append("| class | n | W min/p50/p99/max | H min/p50/p99/max | canonical (W,H) | verdict |")
        lines.append("|---|---|---|---|---|---|")
        for entry in sorted(os.listdir(root_path)):
            folder = os.path.join(root_path, entry)
            if not os.path.isdir(folder):
                continue
            dims = scan_folder(folder)
            if not dims:
                continue
            s = summarize(dims)
            canon_name = NAME_MAP.get(entry, entry)
            canon = CANONICAL_SINGLE.get(canon_name)
            report["roots"][root][entry] = {"canonical_class": canon_name, "canonical_size": canon, **s}

            if canon:
                cw, ch = canon
                # usable if: every source frame >= canonical window (window must fit
                # inside the frame) AND p99 of needed window is covered. A source
                # frame SMALLER than the canonical window forces pad-or-shrink.
                fits = s["width"]["max"] >= cw and s["height"]["max"] >= ch
                p99_ok = s["width"]["p99"] >= cw and s["height"]["p99"] >= ch
                if fits and p99_ok:
                    verdict = "OK"
                elif fits:
                    verdict = "CHECK (p99 < canonical)"
                else:
                    verdict = f"SMALLER FRAMES (min {s['width']['min']}x{s['height']['min']} < {cw}x{ch})"
                canon_str = f"{cw}x{ch}"
            else:
                verdict = "NO CANONICAL (new class)"
                canon_str = "-"

            def fmt(d):
                return f"{d['min']}/{d['p50']}/{d['p99']}/{d['max']}"

            lines.append(f"| {entry} | {s['n']} | {fmt(s['width'])} | {fmt(s['height'])} | {canon_str} | {verdict} |")
        lines.append("")

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)
    md = "\n".join(lines)
    with open(args.out.replace(".json", ".md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
