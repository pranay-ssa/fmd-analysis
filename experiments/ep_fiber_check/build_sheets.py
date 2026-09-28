#!/usr/bin/env python3
"""Build the comparison sheets, with the group hidden behind a number.

Every crop is fitted into a cell of the same size, so a hair-thin filament and a fat translucent
mass are shown at a comparable apparent size. That is the property being judged, so the fitting
matters more than the resolution. The number in the corner is the only label on the sheet and the
number to group map goes to a separate file, so the verdicts can be recorded first.

Also checks, before any verdict is given:
  * the hash of every source picture on the VM against the local record
  * that every box sits inside its frame
"""
import csv
import glob
import os
import random
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

SCR = r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch"
CROPS = os.path.join(SCR, "epfiber_crops")
REPO = r"D:\fmd-analysis"
CELL_W, CELL_H = 320, 240
COLS, ROWS = 6, 6

# the local record of every file the pipeline has ever seen
rec = {}
for r in csv.reader(open(os.path.join(REPO, "run", "line_eda", "20260916",
                                      "image_md5_records.csv"), newline="", encoding="utf-8-sig")):
    if r and r[0]:
        rec.setdefault(os.path.basename(r[2]), set()).add(r[3])

# the manifest the crop job printed on the VM, parsed by hand so duplicate names cannot collapse
man = []
for line in open(os.path.join(SCR, "epfiber_manifest.csv"), encoding="utf-8"):
    p = line.rstrip("\n").split(",")
    if len(p) == 9 and p[0] != "group":
        man.append(p)
by_name = {}
for g, f, md5, fb, w, h, bpp, cw, ch in man:
    by_name.setdefault(f, set()).add(md5)
bad = [f for f, ms in by_name.items() if not (ms & rec.get(f, set()))]
print("source pictures pulled: %d distinct, manifest rows %d" % (len(by_name), len(man)))
print("hash check: %d mismatched against the local record" % len(bad))
for f in bad[:5]:
    print("   MISMATCH", f, sorted(by_name[f]))
print("frame geometry as reported by the VM: %s x %s, %s bit"
      % ({p[4] for p in man}, {p[5] for p in man}, {p[6] for p in man}))

box_rows = list(csv.DictReader(open(os.path.join(SCR, "ep_fiber_boxes.csv"), newline="", encoding="utf-8")))
oob = [r["file_name"] for r in box_rows
       if float(r["xtl"]) < 0 or float(r["ytl"]) < 0
       or float(r["xbr"]) > float(r["img_w"]) or float(r["ybr"]) > float(r["img_h"])]
print("boxes outside their frame: %d of %d" % (len(oob), len(box_rows)))
boxes = {(r["group"], r["box_idx"], r["file_name"].rsplit(".", 1)[0]): r for r in box_rows}

files = sorted(glob.glob(os.path.join(CROPS, "*.bmp")))
random.seed(20260921)
random.shuffle(files)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
except Exception:
    font = ImageFont.load_default()

legend, cells = [], []
for n, path in enumerate(files, 1):
    base = os.path.basename(path)[:-4]
    group, rest = base.split("__", 1)
    idx, stem = rest.split("_", 1)
    if (group, idx, stem) not in boxes:
        print("   crop with no box row:", base)
        continue
    im = Image.open(path).convert("L")
    s = min(CELL_W / im.width, CELL_H / im.height)
    small = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    cell = Image.new("L", (CELL_W, CELL_H), 30)
    cell.paste(small, ((CELL_W - small.width) // 2, (CELL_H - small.height) // 2))
    cell = cell.convert("RGB")
    d = ImageDraw.Draw(cell)
    d.rectangle([0, 0, CELL_W - 1, CELL_H - 1], outline=(70, 70, 70))
    d.rectangle([0, 0, 46, 30], fill=(0, 0, 0))
    d.text((6, 3), str(n), font=font, fill=(255, 210, 60))
    b = boxes[(group, idx, stem)]
    legend.append([n, group, b["file_name"], idx, im.width, im.height,
                   round(abs(float(b["xbr"]) - float(b["xtl"])), 1),
                   round(abs(float(b["ybr"]) - float(b["ytl"])), 1)])
    cells.append((n, cell))

per_sheet = COLS * ROWS
for s_i in range((len(cells) + per_sheet - 1) // per_sheet):
    chunk = cells[s_i * per_sheet:(s_i + 1) * per_sheet]
    sheet = Image.new("RGB", (COLS * CELL_W, ROWS * CELL_H), (18, 18, 18))
    for k, (n, cell) in enumerate(chunk):
        sheet.paste(cell, ((k % COLS) * CELL_W, (k // COLS) * CELL_H))
    out = os.path.join(SCR, "sheet_%d.png" % (s_i + 1))
    sheet.save(out)
    mix = Counter(g for nn, g, *_ in legend if chunk[0][0] <= nn <= chunk[-1][0])
    print("wrote %s   cells %d to %d   mixture %s" % (out, chunk[0][0], chunk[-1][0], dict(mix)))

with open(os.path.join(SCR, "sheet_key.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cell", "group", "file_name", "box_idx", "crop_w", "crop_h", "box_w", "box_h"])
    w.writerows(sorted(legend))
print("key written to sheet_key.csv   groups: %s" % dict(Counter(g for _, g, *_ in legend)))
