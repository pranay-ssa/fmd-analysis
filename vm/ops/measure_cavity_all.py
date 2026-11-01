#!/usr/bin/env python3
"""Per-image cavity geometry for all 1,047 images, then the box positions
recomputed relative to the MEASURED cavity centre rather than the image centre.

Lives in the repo (vm/ops/), NOT beside the data: the VM folder is shared, so we
keep only README.md, manifest.csv, annotations/ and images/ there. Run it by
piping it over ssh, which leaves no file behind on the VM:

    ssh amd-a100-vm 'python3 - < vm/ops/measure_cavity_all.py' > cavity_geometry_all.json

Writes cavity_geometry_all.json to --out (default: cwd), so the artifact lands
in the repo rather than in the shared data folder.
"""
import argparse
import glob
import json
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image
import xml.etree.ElementTree as ET

DEFAULT_DATA_DIR = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images/PRODUCTION_20260925"

_p = argparse.ArgumentParser(description=__doc__)
_p.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                help="folder holding annotations/ and images/")
_p.add_argument("--out", default="cavity_geometry_all.json",
                help="where to write the result")
_p.add_argument("--jobs", type=int, default=8)
_args = _p.parse_args()

HERE = os.path.abspath(_args.data_dir)
IMG = os.path.join(HERE, "images")
ANN = os.path.join(HERE, "annotations")


def measure(path):
    try:
        im = np.asarray(Image.open(path)).astype(np.float32)
        hi = np.percentile(im, 99.5)
        if hi < 20:
            return None
        mask = im > 0.45 * hi
        ys, xs = np.nonzero(mask)
        if xs.size < 50_000:
            return None
        col = mask.sum(0)
        rowp = mask.sum(1)
        R = (np.count_nonzero(col > 0.5 * col.max())
             + np.count_nonzero(rowp > 0.5 * rowp.max())) / 4.0
        return (os.path.basename(path), float(xs.mean()), float(ys.mean()), float(R))
    except Exception:
        return None


paths = sorted(glob.glob(os.path.join(IMG, "*.bmp")))
print("measuring %d images" % len(paths), flush=True)

geo = {}
with ThreadPoolExecutor(max_workers=_args.jobs) as pool:
    for i, res in enumerate(pool.map(measure, paths), 1):
        if res:
            geo[res[0]] = {"cx": res[1], "cy": res[2], "R": res[3]}
        if i % 200 == 0:
            print("  %d/%d" % (i, len(paths)), flush=True)

print("measured: %d / %d" % (len(geo), len(paths)), flush=True)

# ---- boxes relative to the measured cavity --------------------------------
tot = 0
inside_lens = inside_cav = outside_cav = far_out = 0
ratio_list = []
per_label_out = {}
unmeasurable = 0

for x in sorted(glob.glob(os.path.join(ANN, "*.xml"))):
    # Parser safety: these are our own team's CVAT exports sitting in a folder we
    # created on this VM, not untrusted input. Switch to defusedxml if this is
    # ever pointed at a vendor-supplied file.
    root = ET.parse(x).getroot()
    for im in root.iter("image"):
        base = os.path.basename(im.get("name"))
        g = geo.get(base)
        if not g:
            unmeasurable += 1
            continue
        for b in im.findall("box"):
            xtl, ytl = float(b.get("xtl")), float(b.get("ytl"))
            xbr, ybr = float(b.get("xbr")), float(b.get("ybr"))
            bx, by = (xtl + xbr) / 2.0, (ytl + ybr) / 2.0
            d = ((bx - g["cx"]) ** 2 + (by - g["cy"]) ** 2) ** 0.5
            tot += 1
            ratio_list.append(d / g["R"])
            lab = b.get("label")
            per_label_out.setdefault(lab, [0, 0])
            if d > g["R"]:
                outside_cav += 1
                per_label_out[lab][1] += 1
            else:
                inside_cav += 1
                per_label_out[lab][0] += 1
            if d > g["R"] * 1.5:
                far_out += 1
            if d <= g["R"] * (783.8 / 896.0):
                inside_lens += 1

s = sorted(ratio_list)


def pct(v, q):
    k = (len(v) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


R = np.array([g["R"] for g in geo.values()])
OFFX = np.array([g["cx"] - 1224.0 for g in geo.values()])
OFFY = np.array([g["cy"] - 1024.0 for g in geo.values()])
OFF = np.sqrt(OFFX ** 2 + OFFY ** 2)

summary = {
    "images_measured": len(geo),
    "images_not_measurable": unmeasurable,
    "boxes_total": tot,
    "cavity_radius_px_median": round(float(np.median(R)), 1),
    "cavity_radius_px_p25": round(float(np.percentile(R, 25)), 1),
    "cavity_radius_px_p75": round(float(np.percentile(R, 75)), 1),
    "cavity_radius_px_std": round(float(R.std()), 1),
    "centre_offset_px_median": round(float(np.median(OFF)), 1),
    "centre_offset_px_p95": round(float(np.percentile(OFF, 95)), 1),
    "centre_offset_px_max": round(float(OFF.max()), 1),
    "offset_x_median": round(float(np.median(OFFX)), 1),
    "offset_y_median": round(float(np.median(OFFY)), 1),
    "boxes_inside_cavity": inside_cav,
    "boxes_outside_cavity": outside_cav,
    "boxes_outside_1_5x_cavity": far_out,
    "boxes_inside_lens_radius": inside_lens,
    "dist_over_cavity_radius_p50": round(pct(s, .5), 3),
    "dist_over_cavity_radius_p75": round(pct(s, .75), 3),
    "dist_over_cavity_radius_p95": round(pct(s, .95), 3),
    "dist_over_cavity_radius_max": round(s[-1], 3),
}
print(json.dumps(summary, indent=2), flush=True)

per_label = {k: {"inside": v[0], "outside": v[1],
                 "outside_pct": round(100.0 * v[1] / (v[0] + v[1]), 1)}
             for k, v in sorted(per_label_out.items(), key=lambda kv: -kv[1][0] - kv[1][1])}
print(json.dumps(per_label, indent=2), flush=True)

json.dump({"summary": summary, "per_label": per_label,
           "per_image": geo}, open(_args.out, "w"), indent=1)
print("wrote %s" % os.path.abspath(_args.out), flush=True)
