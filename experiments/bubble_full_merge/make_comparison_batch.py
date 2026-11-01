#!/usr/bin/env python3
"""Side-by-side comparison images for misclassified crops (batch).

For each source image in the requested sno list:
  Left  : the ORIGINAL source frame, scaled, with each annotated (rotated)
          bbox drawn in red, using the same corner math as the extractor.
          Numbered badges (1, 2, ...) appear only when the image has more
          than one crop in the list.
  Right : the CROP(s) exactly as the misclassification folder holds them.
          One crop  -> centered in the panel.
          Several   -> stacked, each with its own true -> predicted line and
                       a matching number badge.
  Footer: original image name + annotated defect type, so the image stands
          alone when shared. No internal serial numbers on the image.

Reads:
  run/comparison_src/<source image>.bmp   the source frames
  run/comparison_crops/<sno>.png          the misclassified crops (from the VM)
  run/bubble_full_merge_20261015_misclassification_manifest.csv
  run/bubble_full_merge_crops_manifest.csv
  run/comparison_batch.json               the sno list to render
Writes:
  run/comparisons/comparison_<sno>.png    (or _<sno>_<sno> for grouped)
"""
import csv
import json
import math
import os
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont

MANIFEST = "run/bubble_full_merge_20261015_misclassification_manifest.csv"
CROPS_MAN = "run/bubble_full_merge_crops_manifest.csv"
SRC_DIR = "run/comparison_src"
CROP_DIR = "run/comparison_crops"
OUT_DIR = "run/comparisons"

RED = (220, 30, 30)
DARK = (25, 25, 25)
GREY = (120, 120, 120)
MARGIN = 48
GAP = 72
PANEL_H = 900
HEAD_H = 72
FOOT_H = 64
BADGE = 44


def font(sz):
    try:
        return ImageFont.load_default(sz)
    except TypeError:
        return ImageFont.load_default()


def corners(xtl, ytl, xbr, ybr, rot):
    cx, cy = (xtl + xbr) / 2.0, (ytl + ybr) / 2.0
    w, h = xbr - xtl, ybr - ytl
    th = math.radians(rot)
    cos, sin = math.cos(th), math.sin(th)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        rx = dx * cos - dy * sin
        ry = dx * sin + dy * cos
        pts.append((cx + rx, cy + ry))
    return pts


def draw_box(draw, pts, width=6):
    draw.polygon(pts, outline=RED)
    for off in range(1, width // 2 + 1):
        draw.polygon([(x + off, y) for x, y in pts], outline=RED)
        draw.polygon([(x - off, y) for x, y in pts], outline=RED)
        draw.polygon([(x, y + off) for x, y in pts], outline=RED)
        draw.polygon([(x, y - off) for x, y in pts], outline=RED)


def badge(draw, xy, n, f):
    x, y = xy
    r = BADGE // 2
    draw.ellipse((x - r, y - r, x + r, y + r), fill=RED)
    t = str(n)
    bb = draw.textbbox((0, 0), t, font=f)
    draw.text((x - (bb[2] - bb[0]) / 2 - bb[0], y - (bb[3] - bb[1]) / 2 - bb[1]),
              t, fill=(255, 255, 255), font=f)


def build_group(src_path, items, f_head, f_cap, f_badge, f_foot):
    src = Image.open(src_path).convert("RGB")
    scale = PANEL_H / src.height
    left_w = int(round(src.width * scale))
    left = src.resize((left_w, PANEL_H), Image.LANCZOS)
    dl = ImageDraw.Draw(left)
    for i, it in enumerate(items, 1):
        pts = [(x * scale, y * scale) for x, y in
               corners(it["xtl"], it["ytl"], it["xbr"], it["ybr"], it["rot"])]
        draw_box(dl, pts)
        if len(items) > 1:
            top = min(p[1] for p in pts)
            cx = sum(p[0] for p in pts) / len(pts)
            badge(dl, (cx, max(BADGE // 2, top - BADGE // 2 - 6)), i, f_badge)

    crops = []
    for it in items:
        c = Image.open(it["png_path"]).convert("RGB")
        k = max(1, int(round(PANEL_H * 0.6 / max(c.height, 1))))
        disp = c.resize((c.width * k, c.height * k), Image.LANCZOS)
        if disp.height > PANEL_H * 0.6:
            kk = PANEL_H * 0.6 / disp.height
            disp = disp.resize((int(disp.width * kk), int(disp.height * kk)),
                               Image.LANCZOS)
        crops.append(disp)

    # the true -> pred line can be wider than the crop; reserve room for it
    # so the label never runs off the canvas
    pairs = ["%s  ->  %s" % (it["true"], it["pred"]) for it in items]
    pair_w = [max(1, int(round(f_cap.getlength(t)))) for t in pairs]
    stack_h = sum(c.height for c in crops) + (len(crops) - 1) * 96
    panel_w = max([left_w] + [c.width for c in crops] + pair_w)
    W = MARGIN * 2 + panel_w * 2 + GAP
    H = MARGIN + HEAD_H + PANEL_H + FOOT_H + 16
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    lx = MARGIN + (panel_w - left_w) // 2
    draw.text((lx, MARGIN), "Original", fill=DARK, font=f_head)
    canvas.paste(left, (lx, MARGIN + HEAD_H))

    rx0 = MARGIN + panel_w + GAP
    if len(crops) == 1:
        c = crops[0]
        rx = rx0 + (panel_w - c.width) // 2
        ry = MARGIN + HEAD_H + (PANEL_H - c.height) // 2
        canvas.paste(c, (rx, ry))
        tx = rx0 + (panel_w - pair_w[0]) // 2
        draw.text((tx, min(ry + c.height + 18,
                           MARGIN + HEAD_H + PANEL_H - 60)),
                  pairs[0], fill=RED, font=f_cap)
    else:
        y = MARGIN + HEAD_H + max(0, (PANEL_H - stack_h) // 2)
        for i, (c, it) in enumerate(zip(crops, items), 1):
            rx = rx0 + (panel_w - c.width) // 2
            canvas.paste(c, (rx, y))
            badge(draw, (rx - BADGE, y + BADGE // 2), i, f_badge)
            tx = rx0 + (panel_w - pair_w[i - 1]) // 2
            draw.text((tx, y + c.height + 8), pairs[i - 1],
                      fill=RED, font=f_cap)
            y += c.height + 96

    foot = "%s   |   %s" % (
        os.path.basename(src_path),
        " / ".join(sorted({it["true"] for it in items})))
    draw.text((MARGIN, H - FOOT_H - 4), foot, fill=DARK, font=f_foot)
    return canvas


def main():
    snos = json.load(open("run/comparison_batch.json"))
    rows = list(csv.DictReader(open(MANIFEST)))
    man = {m["crop_file"].split("/")[-1]: m
           for m in csv.DictReader(open(CROPS_MAN))}

    by_sno = {r["sno"]: r for r in rows}
    groups = defaultdict(list)
    for s in snos:
        r = by_sno[s]
        m = man[r["original_crop"]]
        groups[m["source_image"]].append({
            "sno": s,
            "png_path": os.path.join(CROP_DIR, "%s.png" % s),
            "true": r["true_label"], "pred": r["predicted_label"],
            "xtl": float(r["xtl"]), "ytl": float(r["ytl"]),
            "xbr": float(r["xbr"]), "ybr": float(r["ybr"]),
            "rot": float(r["rotation"]),
        })

    os.makedirs(OUT_DIR, exist_ok=True)
    f_head, f_cap = font(52), font(40)
    f_badge, f_foot = font(30), font(30)
    n = 0
    for img, items in groups.items():
        canvas = build_group(os.path.join(SRC_DIR, img), items,
                             f_head, f_cap, f_badge, f_foot)
        if len(items) == 1:
            out = os.path.join(OUT_DIR, "comparison_%s.png" % items[0]["sno"])
        else:
            out = os.path.join(OUT_DIR, "comparison_%s.png" %
                               "_".join(i["sno"] for i in items))
        canvas.save(out)
        n += 1
        print("wrote", out, canvas.size, "crops:", [i["sno"] for i in items])
    print("total images:", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
