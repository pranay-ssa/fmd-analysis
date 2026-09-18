"""Step 5: Visual preview of converted OBB over real crops (authoritative check).

Draws the converted YOLO-OBB polygons onto the actual single-size crop images
so orientation direction and geometry can be eyeballed.  CVAT rotation
semantics were confirmed visually on 2026-09-07 (base-rect + rotation), so this
is the final word on "does the box enclose the real defect".

Usage:
    python src/yolo_ooi/05_preview.py --ooi runs/yolo11/ooi_images.csv \
        --crop-base run/single-size_fixed_crop --labels runs/yolo11/labels \
        --out runs/yolo11/preview --per-class 3
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ooi", required=True, help="ooi_images.csv")
    ap.add_argument("--crop-base", required=True)
    ap.add_argument("--labels", required=True, help="dir of <stem>.txt YOLO-OBB labels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-class", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    crop_base = Path(args.crop_base)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    with open(args.ooi, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_class = {}
    for r in rows:
        by_class.setdefault(r["class"], []).append(r)

    # colors per class index (from classes.txt order)
    class_file = Path(args.ooi).parent / "classes.txt"
    class_idx = {name: i for i, name in enumerate(
        class_file.read_text(encoding="utf-8").splitlines())}
    palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
               (255, 0, 255), (0, 255, 255), (255, 128, 0), (128, 255, 0),
               (255, 0, 128), (128, 0, 255)]

    n_drawn = 0
    for cls, members in sorted(by_class.items()):
        chosen = rng.sample(members, min(args.per_class, len(members)))
        for r in chosen:
            stem = r["stem"]
            # crop path: crop_relpath is relative to crop_base
            crop_path = crop_base / r["crop_relpath"]
            if not crop_path.exists():
                print(f"  MISSING crop: {crop_path}")
                continue
            img = Image.open(crop_path).convert("RGBA")
            w, h = img.size
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            label_file = Path(args.labels) / f"{stem}.txt"
            if not label_file.exists():
                print(f"  MISSING label: {label_file}")
                continue
            for line in label_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                ci = int(parts[0])
                xy = [float(x) for x in parts[1:9]]
                pts = [(xy[i] * w, xy[i + 1] * h) for i in range(0, 8, 2)]
                d.polygon(pts, outline=palette[ci % len(palette)])
            comp = Image.alpha_composite(img, overlay).convert("RGB")
            dst = out / f"{cls.replace(' ', '_')}_{stem}.png"
            comp.save(dst)
            n_drawn += 1

    print(f"Drew previews          : {n_drawn}")
    print(f"Preview dir            : {out}")


if __name__ == "__main__":
    main()