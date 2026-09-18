#!/usr/bin/env python3
"""Convert CVAT XML box annotations into single-size crop coordinates.

Two modes:
  - obb2aabb  -> axis-aligned YOLO labels (class cx cy w h, normalized)
                 Rotation attribute is dropped.
  - obb2obb  -> YOLO-OBB labels (class x1 y1 x2 y2 x3 y3 x4 y4, normalized)
                Uses the rotation attribute (CVAT: rotation spins the local
                unrotated rect about its center; the stored xtl/xbr/ybr/ybr
                is the pre-rotation rectangle, NOT the rotated AABB).

Both modes translate source coordinates (2448x2048) into the crop's own frame
using each image's manifest row (left, top, width, height).  Pure stdlib +
numpy; no ultralytics install needed.

Usage:
    python3 crop_coords.py obb2aabb \
        --xml <path>/annotations.xml \
        --crop-base /home/pranayp/fmd_crop_output/single-size_fixed_crop \
        --out /home/pranayp/teammate_ooi/labels_aabb

    python3 crop_coords.py obb2obb \
        --xml <path>/annotations.xml \
        --crop-base /home/pranayp/fmd_crop_output/single-size_fixed_crop \
        --out /home/pranayp/teammate_ooi/labels_obb

    # Same but render visual previews into <out>/_preview/:
    python3 crop_coords.py obb2aabb --xml ... --crop-base ... --out ... --preview
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- #
# XML parsing
# --------------------------------------------------------------------------- #
def parse_xml(xml_path: Path):
    """Return list of images, each dict with name/stem/class/width/height/boxes."""
    txt = xml_path.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<image\b([^>]*)>(.*?)</image>", txt, re.DOTALL):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        name = attrs.get("name", "")
        if "ICube Defects Library" not in name:
            continue
        rel = name.split("ICube Defects Library/", 1)[1]
        parts = rel.split("/")
        cls = parts[0]
        stem = parts[-1].rsplit(".", 1)[0]
        boxes = []
        for bm in re.finditer(r"<box\b([^>]*)>", m.group(2)):
            a = dict(re.findall(r'(\w+)="([^"]*)"', bm.group(1)))
            if not all(k in a for k in ("xtl", "ytl", "xbr", "ybr")):
                continue
            boxes.append({
                "label": a.get("label", ""),
                "xtl": float(a["xtl"]), "ytl": float(a["ytl"]),
                "xbr": float(a["xbr"]), "ybr": float(a["ybr"]),
                "rotation": float(a.get("rotation", 0.0)),
            })
        out.append({
            "name": name, "class": cls, "stem": stem,
            "width": int(attrs.get("width", 0)),
            "height": int(attrs.get("height", 0)),
            "boxes": boxes,
        })
    return out


def parse_manifest(manifest_csv: Path):
    out = {}
    if not manifest_csv.exists():
        return out
    with open(manifest_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[Path(row["file"]).stem] = row
    return out


def load_class_index(xml_images) -> dict:
    """class -> 0-based index, by order of first appearance across all boxes."""
    idx = {}
    for im in xml_images:
        for b in im["boxes"]:
            if b["label"] not in idx:
                idx[b["label"]] = len(idx)
    return idx


# --------------------------------------------------------------------------- #
# Math
# --------------------------------------------------------------------------- #
def corners(xtl, ytl, xbr, ybr, deg):
    """4 corners of the CVAT rotated box in (rotated) pixel coords."""
    cx, cy = (xtl + xbr) / 2, (ytl + ybr) / 2
    w, h = xbr - xtl, ybr - ytl
    rad = math.radians(deg)
    rel = np.array([[-w / 2, -h / 2], [w / 2, -h / 2],
                    [w / 2, h / 2], [-w / 2, h / 2]])
    yaw = np.array([[math.cos(rad), -math.sin(rad)],
                    [math.sin(rad),  math.cos(rad)]])
    return rel @ yaw.T + np.array([cx, cy])


def corners_yolo_obb_str(xtl, ytl, xbr, ybr, deg, img_w, img_h):
    pts = corners(xtl, ytl, xbr, ybr, deg)
    pts[:, 0] /= img_w
    pts[:, 1] /= img_h
    return " ".join(f"{v:.6f}" for v in pts.ravel())


def aabb_yolo_str(xtl, ytl, xbr, ybr, img_w, img_h):
    cx = ((xtl + xbr) / 2) / img_w
    cy = ((ytl + ybr) / 2) / img_h
    w = (xbr - xtl) / img_w
    h = (ybr - ytl) / img_h
    return f"{cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


# --------------------------------------------------------------------------- #
# Optional preview
# --------------------------------------------------------------------------- #
def try_pillow():
    try:
        from PIL import Image, ImageDraw
        return Image, ImageDraw
    except ImportError:
        return None, None


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["obb2aabb", "obb2obb"],
                    help="obb2aabb drops rotation; obb2obb keeps it (YOLO-OBB)")
    ap.add_argument("--xml", required=True)
    ap.add_argument("--crop-base", required=True)
    ap.add_argument("--out", required=True, help="output dir for <stem>.txt labels")
    ap.add_argument("--preview", action="store_true",
                    help="also draw polygons on the crops into <out>/_preview/")
    args = ap.parse_args()

    crop_base = Path(args.crop_base)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_dir = out_dir / "_preview"
    if args.preview:
        preview_dir.mkdir(parents=True, exist_ok=True)

    images = parse_xml(Path(args.xml))
    class_idx = load_class_index(images)

    n_labels = 0
    n_outside = 0
    n_missing_manifest = 0
    Image, ImageDraw = (None, None)
    if args.preview:
        Image, ImageDraw = try_pillow()
        if Image is None:
            print("WARN: --preview requested but Pillow not available; skipping previews.")

    palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
               (255, 0, 255), (0, 255, 255), (255, 128, 0), (128, 255, 0),
               (255, 0, 128), (128, 0, 255)]

    for img in images:
        if not img["boxes"]:
            continue
        manifests = sorted(crop_base.glob(f"{img['class']}_*/crop_manifest.csv"))
        if not manifests:
            n_missing_manifest += 1
            continue
        man = parse_manifest(manifests[0])
        m = man.get(img["stem"])
        if m is None:
            n_missing_manifest += 1
            continue

        ox, oy = float(m["left"]), float(m["top"])
        cw, ch = float(m["width"]), float(m["height"])

        lines = []
        polygons_for_preview = []
        for b in img["boxes"]:
            if b["label"] not in class_idx:
                continue
            xi = class_idx[b["label"]]
            xtl = b["xtl"] - ox
            ytl = b["ytl"] - oy
            xbr = b["xbr"] - ox
            ybr = b["ybr"] - oy
            # bounds in crop
            eps = 0.5
            if (min(xtl, xbr) < -eps or max(xtl, xbr) > cw + eps
                    or min(ytl, ybr) < -eps or max(ytl, ybr) > ch + eps):
                n_outside += 1
                continue
            if args.mode == "obb2obb":
                tail = corners_yolo_obb_str(xtl, ytl, xbr, ybr, b["rotation"], cw, ch)
                polygons_for_preview.append((xi, corners(xtl, ytl, xbr, ybr, b["rotation"])))
            else:
                tail = aabb_yolo_str(xtl, ytl, xbr, ybr, cw, ch)
                polygons_for_preview.append((xi, np.array([[xtl, ytl], [xbr, ytl],
                                                           [xbr, ybr], [xtl, ybr]])))
            lines.append(f"{xi} {tail}")
            n_labels += 1

        if lines:
            (out_dir / f"{img['stem']}.txt").write_text("\n".join(lines) + "\n",
                                                       encoding="utf-8")

        if args.preview and polygons_for_preview and Image is not None:
            crop_path = crop_base / m["file"].rsplit("/", 1)[0].rsplit("\\", 1)[0]
            # m["file"] is just the stem.bmp; the dir is manifests[0].parent.name
            crop_path = crop_base / manifests[0].parent.name / f"{img['stem']}_crop.bmp"
            if not crop_path.exists():
                continue
            im = Image.open(crop_path).convert("RGBA")
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            for ci, pts in polygons_for_preview:
                d.polygon([(float(p[0]), float(p[1])) for p in pts],
                          outline=palette[ci % len(palette)])
            Image.alpha_composite(im, overlay).convert("RGB").save(
                preview_dir / f"{img['class'].replace(' ', '_')}_{img['stem']}.png")

    print(f"mode                 : {args.mode}")
    print(f"output dir           : {out_dir}")
    print(f"total label lines    : {n_labels}")
    print(f"boxes outside crop   : {n_outside}")
    print(f"images missing man/n : {n_missing_manifest}")
    if args.preview:
        print(f"previews in          : {preview_dir}")


if __name__ == "__main__":
    main()