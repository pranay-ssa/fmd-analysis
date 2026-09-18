"""Step 2: Convert CVAT OBB boxes (source coords) -> YOLO-OBB .txt labels (crop coords).

For each OoI image, translate each <box> from the source 2448x2048 coordinate
system into the single-size fixed-crop window using the crop_manifest.csv
(left,top) origin, then rotate+normalize to a YOLO-OBB label line:
    class_index x1 y1 x2 y2 x3 y3 x4 y4   (all in [0,1], corners clockwise)

A self-check verifies each box's rotated corners reproduce the stored AABB
(angle direction ambiguity is resolved, not guessed).  Any box whose corners
fall outside the crop window after translation, or whose AABB does not
reconstruct within tolerance, is written to a diagnostics CSV rather than
silently dropped.

Usage:
    python src/yolo_ooi/02_xml_to_yolo_obb.py --annot data/annotations.xml \
        --crop-base run/single-size_fixed_crop --classes-file runs/yolo11/classes.txt \
        --out-dir runs/yolo11/labels --report runs/yolo11/convert_report.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import (parse_annotations, parse_manifest, write_csv,
                    obb_corners_self_checked, corners_to_yolo_obb)


def load_class_index(path: Path):
    """classes.txt -> {class_name: index} (0-based, insertion order)."""
    idx = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and line not in idx:
            idx[line] = len(idx)
    return idx


def translate_to_crop_xyxy(xtl, ytl, xbr, ybr, origin_x, origin_y):
    return xtl - origin_x, ytl - origin_y, xbr - origin_x, ybr - origin_y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annot", required=True)
    ap.add_argument("--crop-base", required=True, help="dir containing <Class>_<date>/crop_manifest.csv")
    ap.add_argument("--classes-file", required=True, help="classes.txt (one class per line)")
    ap.add_argument("--out-dir", required=True, help="where <stem>.txt labels are written")
    ap.add_argument("--report", required=True, help="diagnostics CSV")
    args = ap.parse_args()

    crop_base = Path(args.crop_base)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    class_idx = load_class_index(Path(args.classes_file))

    images = parse_annotations(Path(args.annot))
    report = []
    n_labels = 0
    n_unresolvable = 0
    n_outside = 0

    for img in images:
        if not img["boxes"]:
            continue
        # find the manifest for this class
        manifests = sorted(crop_base.glob(f"{img['class']}_*/crop_manifest.csv"))
        if not manifests:
            report.append({"image": img["stem"], "stage": "no-manifest",
                           "n_lines": 0, "detail": f"class dir not found for {img['class']}"})
            n_unresolvable += 1
            continue
        manifest = parse_manifest(manifests[0])
        mrow = manifest.get(img["stem"])
        if mrow is None:
            report.append({"image": img["stem"], "stage": "no-manifest-row",
                           "n_lines": 0, "detail": "stem missing from crop_manifest.csv"})
            n_unresolvable += 1
            continue

        origin_x = float(mrow["left"])
        origin_y = float(mrow["top"])
        crop_w = float(mrow["width"])
        crop_h = float(mrow["height"])

        lines = []
        for b in img["boxes"]:
            if b["label"] not in class_idx:
                report.append({"image": img["stem"], "stage": "unknown-label",
                               "n_lines": 0, "detail": b["label"]})
                n_unresolvable += 1
                continue
            xi = class_idx[b["label"]]
            xtl, ytl, xbr, ybr = translate_to_crop_xyxy(
                b["xtl"], b["ytl"], b["xbr"], b["ybr"], origin_x, origin_y)
            corners, ok = obb_corners_self_checked(
                xtl, ytl, xbr, ybr, b["rotation"])
            if not ok:
                n_unresolvable += 1
                report.append({"image": img["stem"], "stage": "degenerate",
                               "n_lines": 0, "detail": f"{b['label']} non-finite corners"})
                continue

            # bounds check in crop coords; allow tiny epsilon outside
            eps = 0.5
            inside = (corners[:, 0].min() >= -eps and corners[:, 0].max() <= crop_w + eps
                      and corners[:, 1].min() >= -eps and corners[:, 1].max() <= crop_h + eps)
            if not inside:
                n_outside += 1
                report.append({"image": img["stem"], "stage": "outside-crop",
                               "n_lines": 0,
                               "detail": f"{b['label']} corners out of crop window"
                                         f" ({corners[:,0].min():.0f},{corners[:,1].min():.0f})"
                                         f"-({corners[:,0].max():.0f},{corners[:,1].max():.0f})"})
                continue

            lbl = corners_to_yolo_obb(corners, crop_w, crop_h)
            lines.append(f"{xi} {lbl}")
            n_labels += 1
            report.append({"image": img["stem"], "stage": "ok",
                           "n_lines": 1,
                           "detail": f"{b['label']}"})

        if lines:
            (out_dir / f"{img['stem']}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    write_csv(Path(args.report), report,
              ["image", "stage", "n_lines", "detail"])

    print(f"Classes                : {len(class_idx)}")
    print(f"Total label lines      : {n_labels}")
    print(f"Unresolvable (no man/n) : {n_unresolvable}")
    print(f"Boxes outside crop     : {n_outside}")
    print(f"Label dir              : {out_dir}")
    print(f"Report                 : {Path(args.report)}")


if __name__ == "__main__":
    main()