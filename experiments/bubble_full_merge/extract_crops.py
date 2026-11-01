#!/usr/bin/env python3
"""Extract defect crops for the bubble_full_merge experiment (2026-10-15).

Extends the 20261008 crops extractor to the new annotation vintage:
three sources with winner-takes-all precedence per image MD5, and the
settled 6-class frame (docs/decisions/2026-10-15-exp-b-label-frame.md).

DECISIONS (confirmed with the user):
  * Precedence   : production 20260925 beats updated 20260922 beats old
                   library, per image MD5. One source owns an image's boxes.
  * Dedup key    : MD5 (content hash), NOT basename. Production images use
                   different basenames than the library images they match by
                   content; basename dedup inflates the union by ~20.
  * Classes      : 6. The whole bubble family (Bubble, Cluster, Irregular,
                   On Edge, On 123, Scatter / P2_BST) consolidates into
                   "Bubble". P3_HE in the production files reads as
                   HEMA Fragment (code collision resolved for Fragment).
  * Excluded     : P2_HMO (tag-only in every source), cavity-state codes,
                   micron-threshold tags, and any label outside the map.
  * Crop method  : unchanged rotate-upright exact-rectangle cut, pad 0.10.
  * No size calculation anywhere.

OUTPUT (under --out)
  crops/<Class>/<image_stem>_b<idx>.bmp
  crops_manifest.csv   one row per crop, with raw_class AND merged class
  excluded.csv         dropped boxes with reason
  source_census.json   images/boxes per source, for the verification gate
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

# ---- the 6-class frame ------------------------------------------------------

BUBBLE_FAMILY = {
    # old library names (annotations.xml)
    "Bubble", "Bubble Cluster", "Bubble Irregular",
    "Bubble On Edge", "Bubble On 123", "Bubble Scatter",
    # updated / production P-codes
    "P2_BB", "P2_BC", "P2_BI", "P2_BST",
}

CODE2CLASS = {
    # updated + production P-codes -> merged class
    "P2_BB": "Bubble", "P2_BC": "Bubble", "P2_BI": "Bubble",
    "P2_BST": "Bubble",
    "P2_WP": "Wet Package",
    "P3_FM": "Foreign Matter",
    "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA Fragment",
}

NAME2CLASS = {
    # old library class names -> merged class
    "Bubble": "Bubble", "Bubble Cluster": "Bubble",
    "Bubble Irregular": "Bubble", "Bubble On Edge": "Bubble",
    "Bubble On 123": "Bubble", "Bubble Scatter": "Bubble",
    "Wet Package": "Wet Package",
    "Foreign Matter": "Foreign Matter",
    "Fiber": "Fiber",
    "Extraneous Polymer": "Extraneous Polymer",
    "HEMA Fragment": "HEMA Fragment",
}

CLASSES = ["Bubble", "Wet Package", "Foreign Matter", "Fiber",
           "Extraneous Polymer", "HEMA Fragment"]

# merged map: production/updated use P-codes, old library uses class names.
# Keys do not overlap, so one dict serves all three sources.
FULL_MAP = {**CODE2CLASS, **NAME2CLASS}


def load_md5_index(path):
    """-> {basename: md5} from the md5 records CSV."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) >= 4:
                out[row[2]] = row[3]   # basename -> md5
    return out


def load_boxes(path, name_map):
    """-> ({basename: [box, ...]}, n_images, n_boxes). Boxes only; tags and
    non-box shapes are ignored (that drops P2_HMO tags and micron-threshold
    tags by construction).

    NOTE (xml_unsafe_parse): stdlib ElementTree is used on trusted local
    annotation files from our own repo (data/), never on untrusted input.
    Same parser and same justification as extract_crops.py (20261008 wing);
    no XXE risk in this context.
    """
    root = ET.parse(path).getroot()
    out = defaultdict(list)
    n_img = n_box = 0
    for im in root.iter("image"):
        n_img += 1
        name = os.path.basename(im.get("name", ""))
        w, h = int(im.get("width") or 0), int(im.get("height") or 0)
        for el in im:
            if el.tag != "box":
                continue
            lab = el.get("label", "")
            n_box += 1
            cls = name_map.get(lab)
            if cls is None:
                continue
            out[name].append({
                "raw": lab, "class": cls,
                "xtl": float(el.get("xtl")), "ytl": float(el.get("ytl")),
                "xbr": float(el.get("xbr")), "ybr": float(el.get("ybr")),
                "rot": float(el.get("rotation") or 0.0),
                "width": w, "height": h,
            })
    return out, n_img, n_box


def rotated_rect_corners(b):
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
        patch = patch.rotate(-b["rot"], resample=Image.BICUBIC,
                             center=(cx - x0, cy - y0))
    left = b["xtl"] - x0
    top = b["ytl"] - y0
    return patch.crop((int(round(left)), int(round(top)),
                       int(round(left + w)), int(round(top + h))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", required=True, nargs="+",
                    help="XML files, highest precedence FIRST (production updated old)")
    ap.add_argument("--md5-records", required=True,
                    help="CSV: image_md5_records.csv (basename->md5)")
    ap.add_argument("--images-root", required=True)
    ap.add_argument("--path-manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad-frac", type=float, default=0.10)
    args = ap.parse_args()

    base2md5 = load_md5_index(args.md5_records)
    print("md5 index: %d basenames" % len(base2md5))

    # load sources in precedence order; first source to hold an image (by md5) wins
    chosen = {}   # md5 -> (rank, boxes, basename, source_file)
    census = []
    for rank, path in enumerate(args.annotations):
        boxes, n_img, n_box = load_boxes(path, FULL_MAP)
        won = 0
        for nm, bl in boxes.items():
            md5 = base2md5.get(nm)
            if md5 and md5 not in chosen:
                chosen[md5] = (rank, bl, nm, os.path.basename(path))
                won += 1
        census.append({
            "file": os.path.basename(path), "rank": rank,
            "images": n_img, "boxes_total": n_box,
            "images_with_class_boxes": len(boxes),
            "images_won": won,
        })
    print("precedence census:")
    for c in census:
        print("  rank=%d %-38s images=%5d boxes=%5d won=%5d"
              % (c["rank"], c["file"], c["images"], c["boxes_total"], c["images_won"]))
    print("union images (by md5): %d, boxes: %d"
          % (len(chosen), sum(len(v[1]) for v in chosen.values())))

    # load path manifest: basename -> path
    paths = {}
    with open(args.path_manifest, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            paths[row["basename"]] = row["path"]
    missing = [v[2] for v in chosen.values() if v[2] not in paths]
    if missing:
        print("WARNING: %d winning images not in manifest, e.g. %s"
              % (len(missing), missing[:3]))

    os.makedirs(args.out, exist_ok=True)
    man_rows, excl_rows = [], []
    n_ok = n_fail = 0
    for md5, (rank, boxes, basename, src_file) in sorted(chosen.items()):
        p = paths.get(basename)
        if not p or not os.path.exists(p):
            for b in boxes:
                excl_rows.append([basename, md5, b["raw"], b["class"], b["rot"],
                                  "image not in manifest or file missing"])
            continue
        try:
            from PIL import Image
            with Image.open(p) as img:
                img = img.convert("RGB")
                for i, b in enumerate(boxes):
                    if (b["xbr"] - b["xtl"]) <= 0 or (b["ybr"] - b["ytl"]) <= 0:
                        excl_rows.append([basename, md5, b["raw"], b["class"],
                                          b["rot"], "degenerate box"])
                        continue
                    try:
                        crop = cut_crop(img, b, args.pad_frac)
                    except Exception as e:          # noqa: BLE001
                        excl_rows.append([basename, md5, b["raw"], b["class"],
                                          b["rot"], "crop error: %s" % e])
                        n_fail += 1
                        continue
                    cls_dir = os.path.join(args.out, "crops", b["class"])
                    os.makedirs(cls_dir, exist_ok=True)
                    stem = os.path.splitext(basename)[0]
                    fn = "%s_b%02d.bmp" % (stem, i)
                    crop.save(os.path.join(cls_dir, fn))
                    man_rows.append({
                        "crop_file": "%s/%s" % (b["class"], fn),
                        "class": b["class"],
                        "raw_class": b["raw"],
                        "source_image": basename,
                        "source_md5": md5,
                        "source_path": p,
                        "source_rank": rank,
                        "source_file": src_file,
                        "box_index": i,
                        "xtl": b["xtl"], "ytl": b["ytl"],
                        "xbr": b["xbr"], "ybr": b["ybr"],
                        "rotation": b["rot"],
                        "crop_w": crop.width, "crop_h": crop.height,
                    })
                    n_ok += 1
        except Exception as e:                      # noqa: BLE001
            for b in boxes:
                excl_rows.append([basename, md5, b["raw"], b["class"],
                                  b["rot"], "open error: %s" % e])

    with open(os.path.join(args.out, "crops_manifest.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(man_rows[0].keys()))
        w.writeheader()
        w.writerows(man_rows)
    with open(os.path.join(args.out, "excluded.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["image", "md5", "raw_label", "class", "rotation", "reason"])
        w.writerows(excl_rows)

    per = defaultdict(lambda: [set(), 0])
    for r in man_rows:
        per[r["class"]][0].add(r["source_md5"])
        per[r["class"]][1] += 1
    print("\n%-22s %7s %7s %8s" % ("class", "images", "crops", "avg/img"))
    for k in sorted(per, key=lambda x: -per[x][1]):
        i, c = per[k]
        print("%-22s %7d %7d %8.1f" % (k, len(i), c, c / len(i)))
    print("TOTAL crops=%d  excluded=%d  crop_errors=%d" % (n_ok, len(excl_rows), n_fail))

    with open(os.path.join(args.out, "source_census.json"), "w", encoding="utf-8") as fh:
        json.dump({"sources": census, "crops": n_ok,
                   "excluded": len(excl_rows), "crop_errors": n_fail}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
