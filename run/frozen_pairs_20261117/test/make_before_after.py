import importlib.util, sys
from pathlib import Path
from PIL import Image, ImageDraw
spec = importlib.util.spec_from_file_location("obo", "experiments/annotations/draw_frozen_pairs_obb.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

rec = m.parse_annotations()["20241102_004906_L24_C5_9471.bmp"]
hema = [b for b in rec["boxes"] if b["code"] == "P3_HE"][0]
img = Image.open("run/frozen_pairs_20261117/src_images/20241102_004906_L24_C5_9471.bmp").convert("RGB")
crop = (800, 800, 1160, 1780)
piece = img.crop(crop)
W, H = piece.size
f = m.font(19, True)
g = m.font(17)
sheet = Image.new("RGB", (2 * W + 30, H + 84), (250, 250, 250))
d = ImageDraw.Draw(sheet)
for k, (label, sub, aabb, colour) in enumerate((
        ("Drawn upright", "xb: xtl, ytl, xbr, ybr taken as an upright rectangle", True, (214, 39, 40)),
        ("Drawn oriented", "the same numbers rotated by the stored angle", False, (140, 40, 170)))):
    x = k * (W + 30)
    sheet.paste(piece, (x, 64))
    d.text((x, 12), label, font=f, fill=(24, 24, 24))
    d.text((x, 36), sub, font=g, fill=(110, 110, 110))
    pts = [(px - crop[0] + x, py - crop[1] + 64) for px, py in m.corners(hema, aabb=aabb)]
    d.line(pts + [pts[0]], fill=colour, width=4)
sheet.save("run/frozen_pairs_20261117/test/hema_before_after.png")
print("ok", sheet.size)
