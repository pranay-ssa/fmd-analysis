#!/usr/bin/env python3
"""Compose the nine cross-folder frames with their annotated boxes drawn, for the client.

Each of the nine frames sits in the older library under one box class and in the newer folder under
a different box class. The annotation file carries the older library's class only, so the second
name has no box anywhere. The sheet shows the frame, the boxes that exist, and the name that has
none, so a reader can see for themselves whether a second object is there.
"""
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRATCH = Path(r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch")
FRAMES = SCRATCH / "crossframes/data/FMD_Data_26082026/fmd_temp_images"
REPORT = SCRATCH / "pull_report.csv"
XML = Path(r"D:\fmd-analysis\data\annotations.xml")
OUT = Path(r"D:\fmd-analysis\run\ep_fiber_check\20260922")

INK, MUTED, RED, PANEL, BG = (20, 20, 20), (90, 90, 90), (220, 40, 40), (255, 255, 255), (245, 245, 245)
FONT_DIR = Path(r"C:\Windows\Fonts")


def font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        if (FONT_DIR / name).exists():
            return ImageFont.truetype(str(FONT_DIR / name), size)
    return ImageFont.load_default()


# boxes, keyed by the base name the annotation file uses (no score fields, same as the file on disk)
boxes = {}
for im in ET.parse(XML).getroot().iter("image"):
    n = im.get("name").split("/")[-1]
    boxes[n] = [(b.get("label"), float(b.get("xtl")), float(b.get("ytl")),
                 float(b.get("xbr")), float(b.get("ybr"))) for b in im.findall("box")]

rows = list(csv.DictReader(open(REPORT, encoding="utf-8")))
panels = []
for r in rows:
    rec = r["file_name"]
    older = Path(r["older_library_folder"]).name
    newer = Path(r["newer_folder"]).name
    folder = FRAMES / r["older_library_folder"]
    cands = sorted(folder.glob(rec[:15] + "*"))
    if len(cands) != 1:
        print("SKIP", rec, "candidates:", [c.name for c in cands])
        continue
    path = cands[0]
    bs = boxes.get(path.name) or boxes.get(rec) or []
    panels.append({"path": path, "record_name": rec, "older": older, "newer": newer, "boxes": bs})

print("panels:", len(panels), "| boxes drawn:", [len(p["boxes"]) for p in panels])

CELL = (700, 620)
PAD, GAP, CAP = 46, 24, 118
cols = 3
rows_n = (len(panels) + cols - 1) // cols
W = PAD + cols * (CELL[0] + GAP) + PAD
H = 210 + rows_n * (CELL[1] + CAP + GAP) + 110
sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)
f_title, f_sub, f_cap, f_small, f_note = font(46, True), font(26), font(23, True), font(21), font(26)

d.text((PAD, 40), "Nine frames where the two folders name different classes", font=f_title, fill=INK)
d.text((PAD, 104), "Each frame is filed under one class in the older library and another class in the newer folder.",
       font=f_sub, fill=MUTED)
d.text((PAD, 142), "The annotation file carries the older library's class only, so the second name has no box anywhere.",
       font=f_sub, fill=MUTED)

for i, p in enumerate(panels):
    r, c = divmod(i, cols)
    x = PAD + c * (CELL[0] + GAP)
    y = 210 + r * (CELL[1] + CAP + GAP)
    img = Image.open(p["path"]).convert("L").convert("RGB")
    scale = min((CELL[0] - 8) / img.width, (CELL[1] - 8) / img.height)
    small = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    sd = ImageDraw.Draw(small)
    for label, x1, y1, x2, y2 in p["boxes"]:
        sd.rectangle([x1 * scale, y1 * scale, x2 * scale, y2 * scale], outline=RED, width=2)
    d.rectangle([x, y, x + CELL[0], y + CELL[1]], fill=PANEL, outline=(205, 205, 205))
    sheet.paste(small, (x + 4, y + 4))
    lines = ["older library: %s, %d box%s drawn" % (p["older"], len(p["boxes"]), "" if len(p["boxes"]) == 1 else "es"),
             "newer folder: %s, no box" % p["newer"],
             p["record_name"][:44]]
    for j, t in enumerate(lines):
        d.text((x, y + CELL[1] + 8 + j * 30), t, font=(f_cap if j == 1 else f_small),
               fill=(RED if j == 1 else INK))
    p["cell"] = (x, y, CELL[0], CELL[1], scale)
    Image.open(p["path"]).convert("L").convert("RGB").resize(
        (int(2448 * 0.5), int(2048 * 0.5)), Image.LANCZOS).save(OUT / ("frame_%02d_%s.png" % (i + 1, p["record_name"][:19])))

d.text((PAD, H - 76), "Frames are 2448 by 2048 and are shown scaled. The red boxes are the ones the annotation file holds.",
       font=f_note, fill=MUTED)
sheet.save(OUT / "ep_fiber_evidence_4_cross_folder_frames.png")
print("wrote", OUT / "ep_fiber_evidence_4_cross_folder_frames.png", sheet.size)
