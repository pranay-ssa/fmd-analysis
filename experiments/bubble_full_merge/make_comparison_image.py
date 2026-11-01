#!/usr/bin/env python3
"""Side-by-side comparison image for one misclassified crop (sno 86 first).

Left  : the ORIGINAL source frame, scaled, with the annotated (rotated) bbox
        drawn on it in red, using the same corner math as the extractor.
Right : the CROP exactly as the misclassification folder holds it, with the
        true label -> predicted label written below.
White background, one PNG.

Reads (local copies, md5-verified against the VM):
  run/sno86_source.bmp   the source frame
  run/sno86_crop.png     the misclassified crop (86_extraneous_polymer_fiber)
and the manifest row for geometry + labels.
"""
import csv
import math

from PIL import Image, ImageDraw, ImageFont

MANIFEST = "run/bubble_full_merge_20261015_misclassification_manifest.csv"
SRC = "run/sno86_source.bmp"
CROP = "run/sno86_crop.png"
OUT = "run/sno86_comparison.png"

SNO = "86"
RED = (220, 30, 30)
DARK = (25, 25, 25)
GREY = (120, 120, 120)
MARGIN = 48
GAP = 72
PANEL_H = 900          # rendered height of the source frame
HEAD_H = 72            # heading band
CAP_H = 110            # caption band under each panel


def font(sz, bold=False):
    try:
        f = ImageFont.load_default(sz)
    except TypeError:
        f = ImageFont.load_default()
    return f


def main():
    row = [r for r in csv.DictReader(open(MANIFEST)) if r["sno"] == SNO][0]
    xtl, ytl = float(row["xtl"]), float(row["ytl"])
    xbr, ybr = float(row["xbr"]), float(row["ybr"])
    rot = float(row["rotation"])
    true_lab, pred_lab = row["true_label"], row["predicted_label"]

    src = Image.open(SRC).convert("RGB")
    crop = Image.open(CROP).convert("RGB")

    # ---- geometry: same corner math as extract_crops.rotated_rect_corners
    cx, cy = (xtl + xbr) / 2.0, (ytl + ybr) / 2.0
    w, h = xbr - xtl, ybr - ytl
    th = math.radians(rot)
    cos, sin = math.cos(th), math.sin(th)
    corners_src = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        rx = dx * cos - dy * sin
        ry = dx * sin + dy * cos
        corners_src.append((cx + rx, cy + ry))

    # ---- panels
    scale = PANEL_H / src.height
    left_w = int(round(src.width * scale))
    left_img = src.resize((left_w, PANEL_H), Image.LANCZOS)
    d = ImageDraw.Draw(left_img)
    pts = [(x * scale, y * scale) for x, y in corners_src]
    d.polygon(pts, outline=RED)
    # thicker outline: draw the polygon several times with small offsets
    for off in (1, -1, 2, -2):
        d.polygon([(x + off, y) for x, y in pts], outline=RED)
        d.polygon([(x, y + off) for x, y in pts], outline=RED)

    # crop scaled to a similar visual size as the defect region in the panel
    crop_scale = max(2, int(round((w * scale) / crop.width * 2)))
    crop_disp = crop.resize((crop.width * crop_scale, crop.height * crop_scale),
                            Image.LANCZOS)
    # cap the displayed crop so it never dwarfs the frame panel
    if crop_disp.height > PANEL_H * 0.7:
        k = PANEL_H * 0.7 / crop_disp.height
        crop_disp = crop_disp.resize((int(crop_disp.width * k),
                                      int(crop_disp.height * k)), Image.LANCZOS)

    f_head = font(52, bold=True)
    f_cap = font(40)
    f_small = font(30)

    panel_w = max(left_w, crop_disp.width)
    W = MARGIN * 2 + panel_w * 2 + GAP
    H = MARGIN * 2 + HEAD_H + PANEL_H + CAP_H
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # left panel
    lx = MARGIN + (panel_w - left_w) // 2
    draw.text((lx, MARGIN), "Original", fill=DARK, font=f_head)
    canvas.paste(left_img, (lx, MARGIN + HEAD_H))
    draw.text((lx, MARGIN + HEAD_H + PANEL_H + 16),
              "source frame, annotated box in red", fill=GREY, font=f_small)

    # right panel
    rx = MARGIN + panel_w + GAP + (panel_w - crop_disp.width) // 2
    draw.text((rx, MARGIN), "Misclassified", fill=DARK, font=f_head)
    canvas.paste(crop_disp, (rx, MARGIN + HEAD_H))
    cy_img = MARGIN + HEAD_H + crop_disp.height + 24
    draw.text((rx, cy_img), "%s  ->  %s" % (true_lab, pred_lab),
              fill=RED, font=f_cap)
    draw.text((rx, cy_img + 54),
              "true label -> predicted label", fill=GREY, font=f_small)

    canvas.save(OUT)
    print("wrote", OUT, canvas.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
