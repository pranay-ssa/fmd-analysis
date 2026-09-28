#!/usr/bin/env python3
"""The doubtful cells of group A, at their own resolution, for a human to look at.

The verdicts that were not a clean thin filament: 3 unclear and 2 thick mass objects out of the 34
on the contested pictures. The crops are already at native resolution, so they are pasted at their
own size here rather than fitted into a cell.
"""
import csv
import os
from PIL import Image, ImageDraw, ImageFont

SCR = r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch"
REPO = r"D:\fmd-analysis"
OUT = os.path.join(REPO, "run", "ep_fiber_check", "20260921", "sheet_3_doubtful.png")

verdicts = {int(r["cell"]): r for r in csv.DictReader(
    open(os.path.join(SCR, "sheet_verdicts.csv"), newline="", encoding="utf-8"))}
key = {int(r["cell"]): r for r in csv.DictReader(
    open(os.path.join(SCR, "sheet_key.csv"), newline="", encoding="utf-8"))}

picked = [c for c, v in verdicts.items() if v["group"] == "A_conflict" and v["verdict"] != "THIN"]
picked.sort(key=lambda c: (verdicts[c]["verdict"], c))
print("doubtful cells:", [(c, verdicts[c]["verdict"]) for c in picked])

try:
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
except Exception:
    font = ImageFont.load_default()

tiles = []
for c in picked:
    src = None
    for f in os.listdir(os.path.join(SCR, "epfiber_crops")):
        if f.startswith("A_conflict__%s_" % key[c]["box_idx"]) and \
                key[c]["file_name"].rsplit(".", 1)[0] in f:
            src = os.path.join(SCR, "epfiber_crops", f)
            break
    if src is None:
        print("   no crop for cell", c)
        continue
    tiles.append((c, Image.open(src).convert("RGB")))

pad = 8
cols = 3
cell_w = max(t.width for _, t in tiles) + 2 * pad
cell_h = max(t.height for _, t in tiles) + 2 * pad + 34
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (18, 18, 18))
d = ImageDraw.Draw(sheet)
for k, (c, tile) in enumerate(tiles):
    x, y = (k % cols) * cell_w, (k // cols) * cell_h
    v = verdicts[c]
    label = "cell %d  read as %s  box %s x %s px" % (c, v["verdict"], v["box_w"], v["box_h"])
    d.text((x + pad, y + 6), label, font=font, fill=(255, 210, 60))
    sheet.paste(tile, (x + pad, y + 34))
sheet.save(OUT)
print("wrote", OUT, sheet.size)
