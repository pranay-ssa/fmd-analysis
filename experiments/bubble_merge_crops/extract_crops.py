#!/usr/bin/env python3
"""Extract defect crops from the OOI bounding boxes of the FMD annotations.

New wing of the bubble merge experiment (2026-10-08). Reads both annotation
files, applies updated-first precedence, and cuts one crop per box using the
rotate-upright method (the boxes are rotated rectangles: 2,148 of 2,157 carry
a rotation angle).

DECISIONS (confirmed with the user):
  * Crop method      : rotate the patch so the box sits upright, then cut the
                       exact annotated rectangle (axis-aligned bbox of the
                       rotated rect is NOT used - that keeps background).
  * Precedence       : updated boxes replace old-library boxes per image
                       where the updated file has any box for that image.
  * Box label wins   : each crop carries its own box label. The one image
                       where the updated FOLDER says Foreign Matter and the
                       old box says Extraneous Polymer keeps the box label.
  * Stretched Bubble : excluded (4 boxes) - not in either target class list.
  * Split            : NOT done here. build_splits.py does one shared
                       image-level 70/30 split, seed 42, reused by both
                       experiments.

OUTPUT (under --out)
  crops/<RawClass>/<image_stem>_b<idx>.bmp   one file per box
  crops_manifest.csv                         one row per crop
  excluded.csv                               boxes we dropped, with reason

USAGE
  python extract_crops.py --annotations-old data/annotations.xml \
      --annotations-new "data/Updated Annotations 20260922.xml" \
      --images-root /data/FMD_Data_26082026/fmd_temp_images \
      --out run/bubble_merge_crops_20261008
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

# ---- class definitions ----------------------------------------------------

FOUR_BUBBLE = {"Bubble", "Bubble Irregular", "Bubble On 123", "Bubble On Edge"}
CLUSTER = "Bubble Cluster"
EXCLUDE_LABELS = {"Stretched Bubble"}          # not in either target list

# updated file uses P-codes; map to class names
CODE2NAME = {
    "P2_BB": "Bubble",
    "P2_BC": "Bubble Cluster",
    "P2_BI": "Bubble Irregular",
    "P2_BST": "Stretched Bubble",
    "P2_WP": "Wet Package",
    "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA Fragment",
    "P3_FM": "Foreign Matter",
}

# raw crop classes we keep (Stretched Bubble dropped)
KEEP = {
    "Bubble", "Bubble Irregular", "Bubble On 123", "Bubble On Edge",
    "Bubble Cluster", "Extraneous Polymer", "Fiber", "Foreign Matter",
    "HEMA Fragment", "Wet Package",
}


def load_boxes(path, code_map=None):
    """-> {image_basename: [box_dict, ...]} with pixel coords + rotation.

    NOTE (xml_unsafe_parse): stdlib ElementTree is used on trusted local
    annotation files from our own repo (data/), never on untrusted input.
    Same parser used throughout this session; no XXE risk in this context.
    """
    root = ET.parse(path).getroot()
    out = defaultdict(list)
    n_img = 0
    for im in root.iter("image"):
        n_img += 1
        name = os.path.basename(im.get("name", ""))
        w, h = int(im.get("width") or 0), int(im.get("height") or 0)
        for el in im:
            if el.tag != "box":
                continue
            lab = el.get("label", "")
            if code_map:
                lab = code_map.get(lab, lab)
            out[name].append({
                "label": lab,
                "xtl": float(el.get("xtl")),
                "ytl": float(el.get("ytl")),
                "xbr": float(el.get("xbr")),
                "ybr": float(el.get("ybr")),
                "rot": float(el.get("rotation") or 0.0),
                "width": w, "height": h,
            })
    return out, n_img


def rotated_rect_corners(b):
    """Corners of the box after rotating it about its own centre by `rot`
    degrees (CVAT convention: rotation in degrees, counter-clockwise)."""
    cx = (b["xtl"] + b["xbr"]) / 2.0
    cy = (b["ytl"] + b["ybr"]) / 2.0
    w = b["xbr"] - b["xtl"]
    h = b["ybr"] - b["ytl"]
    th = math.radians(b["rot"])
    cos, sin = math.cos(th), math.sin(th)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        rx = dx * cos - dy * sin
        ry = dx * sin + dy * cos
        pts.append((cx + rx, cy + ry))
    return pts, (cx, cy), (w, h)


def cut_crop(img, b, pad_frac=0.10):
    """Cut one defect crop, rotate-upright.

    Strategy: rotate the whole (padded) image about the box centre by -rot so
    the annotated rectangle becomes axis-aligned, then cut it.
    For speed we only rotate the padded axis-aligned bounding box of the
    rotated rectangle, not the full 2448x2048 frame.
    Returns a PIL image of size (w, h) at the box's own resolution.
    """
    from PIL import Image

    pts, (cx, cy), (w, h) = rotated_rect_corners(b)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bw = max(xs) - min(xs)
    bh = max(ys) - min(ys)
    pad = int(max(bw, bh) * pad_frac) + 2
    x0 = max(0, int(min(xs)) - pad)
    y0 = max(0, int(min(ys)) - pad)
    x1 = min(img.width, int(max(xs)) + pad)
    y1 = min(img.height, int(max(ys)) + pad)
    patch = img.crop((x0, y0, x1, y1))

    if abs(b["rot"]) > 1e-6:
        # rotate patch about the box centre (in patch-local coords) so the
        # annotated rectangle becomes axis-aligned.
        patch = patch.rotate(-b["rot"], resample=Image.BICUBIC,
                             center=(cx - x0, cy - y0))
    # now the rectangle sits at its ORIGINAL (unrotated) coords relative to
    # the original image; recompute its location inside the patch.
    left = b["xtl"] - x0
    top = b["ytl"] - y0
    crop = patch.crop((int(round(left)), int(round(top)),
                       int(round(left + w)), int(round(top + h))))
    return crop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations-old", required=True)
    ap.add_argument("--annotations-new", required=True)
    ap.add_argument("--images-root", required=True)
    ap.add_argument("--path-manifest", required=True,
                    help="CSV: class_folder,path (from scan) or index file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad-frac", type=float, default=0.10)
    args = ap.parse_args()

    old, n_old = load_boxes(args.annotations_old)
    new, n_new = load_boxes(args.annotations_new, CODE2NAME)
    print("old: %d images, %d boxes" % (len(old), sum(len(v) for v in old.values())))
    print("new: %d images, %d boxes" % (len(new), sum(len(v) for v in new.values())))

    # precedence: updated wins per image
    chosen = {}
    for nm in set(old) | set(new):
        if nm in new:
            chosen[nm] = ("updated", new[nm])
        else:
            chosen[nm] = ("old", old[nm])
    print("union with updated-first: %d images, %d boxes"
          % (len(chosen), sum(len(v[1]) for v in chosen.values())))

    # load image path manifest
    paths = {}
    with open(args.path_manifest, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            paths[row["basename"]] = row["path"]
    missing = [nm for nm in chosen if nm not in paths]
    if missing:
        print("WARNING: %d boxed images not in manifest, e.g. %s"
              % (len(missing), missing[:3]))

    os.makedirs(args.out, exist_ok=True)
    man_rows, excl_rows = [], []
    n_ok = n_fail = 0
    for nm, (src, boxes) in sorted(chosen.items()):
        p = paths.get(nm)
        if not p:
            for b in boxes:
                excl_rows.append([nm, b["label"], b["rot"], "image not in manifest"])
            continue
        if not os.path.exists(p):
            for b in boxes:
                excl_rows.append([nm, b["label"], b["rot"], "image file missing"])
            continue
        try:
            from PIL import Image
            with Image.open(p) as img:
                img = img.convert("RGB")
                for i, b in enumerate(boxes):
                    if b["label"] in EXCLUDE_LABELS:
                        excl_rows.append([nm, b["label"], b["rot"], "excluded label"])
                        continue
                    if b["label"] not in KEEP:
                        excl_rows.append([nm, b["label"], b["rot"], "not a target class"])
                        continue
                    if b["rot"] and (b["xbr"] - b["xtl"]) <= 0:
                        excl_rows.append([nm, b["label"], b["rot"], "degenerate box"])
                        continue
                    try:
                        crop = cut_crop(img, b, args.pad_frac)
                    except Exception as e:          # noqa: BLE001
                        excl_rows.append([nm, b["label"], b["rot"], "crop error: %s" % e])
                        n_fail += 1
                        continue
                    cls_dir = os.path.join(args.out, "crops", b["label"])
                    os.makedirs(cls_dir, exist_ok=True)
                    stem = os.path.splitext(nm)[0]
                    fn = "%s_b%02d.bmp" % (stem, i)
                    crop.save(os.path.join(cls_dir, fn))
                    man_rows.append({
                        "crop_file": "%s/%s" % (b["label"], fn),
                        "raw_class": b["label"],
                        "source_image": nm,
                        "source_path": p,
                        "box_index": i,
                        "rotation": b["rot"],
                        "box_w": round(b["xbr"] - b["xtl"], 2),
                        "box_h": round(b["ybr"] - b["ytl"], 2),
                        "crop_w": crop.width,
                        "crop_h": crop.height,
                        "annotation_source": src,
                    })
                    n_ok += 1
        except Exception as e:                      # noqa: BLE001
            for b in boxes:
                excl_rows.append([nm, b["label"], b["rot"], "open error: %s" % e])

    with open(os.path.join(args.out, "crops_manifest.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(man_rows[0].keys()))
        w.writeheader()
        w.writerows(man_rows)
    with open(os.path.join(args.out, "excluded.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["image", "label", "rotation", "reason"])
        w.writerows(excl_rows)

    # per-class count report
    per = defaultdict(lambda: [set(), 0])
    for r in man_rows:
        per[r["raw_class"]][0].add(r["source_image"])
        per[r["raw_class"]][1] += 1
    print("\n%-22s %6s %6s %8s" % ("class", "images", "crops", "avg/img"))
    for k in sorted(per, key=lambda x: -per[x][1]):
        i, c = per[k]
        print("%-22s %6d %6d %8.1f" % (k, len(i), c, c / len(i)))
    print("TOTAL crops=%d  excluded=%d  crop_errors=%d"
          % (n_ok, len(excl_rows), n_fail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
