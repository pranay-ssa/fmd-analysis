"""Shared helpers for the YOLO-OBB OoI pipeline.

Pure stdlib + numpy; no ultralytics import (keeps this lightweight and runnable
locally on dev machines without a heavy torch install).
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- #
# CVAT XML annotation parsing (source of truth: data/annotations.xml, READ-ONLY)
# --------------------------------------------------------------------------- #
def parse_annotations(xml_path: Path):
    """Return list of images, each:

    {
      "name": "ICube Defects Library/<Class>/<stem>.bmp",
      "class": "<Class>",
      "stem": "<stem>",
      "width": int, "height": int,
      "boxes": [ {"label":str, "xtl":f,"ytl":f,"xbr":f,"ybr":f,"rotation":f}, ... ],
    }
    """
    txt = xml_path.read_text(encoding="utf-8")
    images = []
    img_re = re.compile(r"<image\b([^>]*)>(.*?)</image>", re.DOTALL)
    for m in img_re.finditer(txt):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        name = attrs.get("name", "")
        if not name or "ICube Defects Library" not in name:
            continue
        rel = name.split("ICube Defects Library/", 1)[1] if "ICube Defects Library/" in name else name
        parts = rel.split("/")
        cls = parts[0] if len(parts) > 1 else ""
        stem_bmp = parts[-1]
        stem = stem_bmp.rsplit(".", 1)[0]
        boxes = []
        for bm in re.finditer(r"<box\b([^>]*)>", m.group(2)):
            a = dict(re.findall(r'(\w+)="([^"]*)"', bm.group(1)))
            if not ("xtl" in a and "xbr" in a and "ytl" in a and "ybr" in a):
                continue
            boxes.append({
                "label": a.get("label", ""),
                "xtl": float(a["xtl"]), "ytl": float(a["ytl"]),
                "xbr": float(a["xbr"]), "ybr": float(a["ybr"]),
                "rotation": float(a.get("rotation", 0.0)),
            })
        images.append({
            "name": name, "class": cls, "stem": stem,
            "width": int(attrs.get("width", 0)), "height": int(attrs.get("height", 0)),
            "boxes": boxes,
        })
    return images


# --------------------------------------------------------------------------- #
# OBB angle -> 4 corners
# --------------------------------------------------------------------------- #
def rotated_rect_corners(xtl, ytl, xbr, ybr, rotation_deg, convention="+y-down"):
    """Recover the 4 corners of a CVAT rotated box.

    CVAT stores the UNROTATED local rectangle in (xtl,ytl,xbr,ybr) and a separate
    `rotation` angle (degrees) applied about the rectangle center.  The stored
    values are NOT the AABB of the rotated shape; they are the base rect before
    rotation.  Verified VIA VISUAL GROUND TRUTH (2026-09-07): rotating the base
    rect about its center by `rotation` reproduced the actual diagonal defect on
    a Fiber sample, while treating the stored box as the rotated AABB did not.

    convention selects spin direction.  +y-down = clockwise in image row-space
    (y increases downward).  Reversed sign mirrors the corners; geometry is the
    same, only ordering flips.  Consistent order across labels is what matters.

    Returns np.ndarray (4,2) in pixel coords (base rect corners, rotated).
    """
    cx = (xtl + xbr) / 2.0
    cy = (ytl + ybr) / 2.0
    w = xbr - xtl
    h = ybr - ytl
    rad = math.radians(rotation_deg)
    rel = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    if convention == "-y-down":
        yaw = np.array([[math.cos(rad), math.sin(rad)], [-math.sin(rad), math.cos(rad)]])
    else:  # "+y-down"
        yaw = np.array([[math.cos(rad), -math.sin(rad)], [math.sin(rad), math.cos(rad)]])
    return rel @ yaw.T + np.array([cx, cy])


def obb_corners_self_checked(xtl, ytl, xbr, ybr, rotation_deg, tol=1.5):
    """Return (corners, ok).

    Any finite rotated base-rect is a valid OBB (rotation preserves the
    parallelogram), so this mainly guards against NaN/Inf corners.  Real
    orientation correctness is verified visually in step-5 preview, which is
    the authoritative check (CVAT rotation semantics confirmed visually on
    2026-09-07).  On a non-finite degenerate case, falls back to the unrotated
    axis-aligned rect and reports ok=False.
    """
    pts = rotated_rect_corners(xtl, ytl, xbr, ybr, rotation_deg, convention="+y-down")
    if not np.all(np.isfinite(pts)):
        return (np.array([[xtl, ytl], [xbr, ytl], [xbr, ybr], [xtl, ybr]]), False)
    return pts, True


def corners_to_yolo_obb(corners, img_w, img_h):
    """Normalize 4 corners to a YOLO-OBB label line [x1 y1 x2 y2 x3 y3 x4 y4] in [0,1].

    Corners are in image pixel coords; img_w/img_h are the crop dims.
    Returns the space-separated string of 8 floats.
    """
    pts = np.asarray(corners, dtype=float)
    pts[:, 0] /= img_w
    pts[:, 1] /= img_h
    return " ".join(f"{v:.6f}" for v in pts.ravel())


def parse_manifest(manifest_csv: Path):
    """Return {stem: row-dict} from a crop_manifest.csv (one per class dir)."""
    out = {}
    if not manifest_csv.exists():
        return out
    with open(manifest_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[Path(row["file"]).stem] = row
    return out


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)