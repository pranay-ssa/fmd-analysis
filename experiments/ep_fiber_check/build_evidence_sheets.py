#!/usr/bin/env python3
"""Build the client-facing evidence sheets for the Fiber against Extraneous Polymer read.

Reads the 68 crops already taken on the box and the verified verdict key, and lays them out so a
reader who has never seen the data can tell the two classes apart by eye:

  sheet 1  the three groups side by side, six objects each
  sheet 2  three objects per group, large, for detail
  sheet 3  all 34 contested objects, for completeness

The object shown in each group is chosen by the form the blind read recorded for the majority of
that group, so the caption says so and sheet 3 carries the whole contested set unfiltered.

Every block of text is measured and wrapped to the column it sits in. An earlier version wrapped by
character count, which ran the row labels under the image panels and clipped them.
"""
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CROPS = Path(r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch\epfiber_crops")
KEY = Path(r"D:\fmd-analysis\run\ep_fiber_check\20260921\sheet_verdicts.csv")
OUT = Path(r"D:\fmd-analysis\run\ep_fiber_check\20260922")
OUT.mkdir(parents=True, exist_ok=True)

BG = (245, 245, 245)
PANEL = (255, 255, 255)
INK = (25, 25, 25)
MUTED = (95, 95, 95)
RULE = (200, 200, 200)

FONT_DIR = Path(r"C:\Windows\Fonts")


def font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        p = FONT_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


GROUPS = [
    ("B_ref_extraneous_polymer", "Both folders say Extraneous Polymer",
     "17 objects in the data, 14 of them a thick mass"),
    ("C_ref_fiber", "Both folders say Fiber", "17 objects in the data, 13 of them a thin filament"),
    ("A_conflict", "Both folders disagree: the older library says Fiber, the newer folder says Extraneous Polymer",
     "33 pictures, 34 objects, 29 of them a thin filament"),
]

rows = list(csv.DictReader(open(KEY, encoding="utf-8")))
by_group = {g: [] for g, _, _ in GROUPS}
for r in rows:
    if r["group"] in by_group:
        by_group[r["group"]].append(
            (float(r["box_w"]) * float(r["box_h"]), r["file_name"], int(r["cell"]), r["verdict"]))

# the form our read put in the majority for each group, used to choose the cells shown
MAJORITY = {"B": "MASS", "C": "THIN", "A": "THIN"}

crop_path = {}
for p in CROPS.glob("*.bmp"):
    group, _, rest = p.name.partition("__")
    stem = rest.split("_", 1)[1].rsplit(".", 1)[0]
    crop_path[(group, stem)] = p

print("crops found:", len(crop_path), "| key rows:", len(rows))

MEASURE = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def wrap(text, f, max_w):
    """Break text into lines that fit max_w pixels with this font."""
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if not line or MEASURE.textlength(trial, font=f) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def pick(group, n, verdict=None, one_per_picture=True):
    """Return n (crop path, file name) pairs, largest annotated box first.

    one_per_picture keeps a picture from appearing twice, which is what sheets 1 and 2 want. Sheet 3
    turns it off so the count of cells equals the count of objects.
    """
    out, seen = [], set()
    for area, name, cell, v in sorted(by_group[group], key=lambda t: -t[0]):
        if verdict and v != verdict:
            continue
        stem = name.rsplit(".", 1)[0]
        if one_per_picture and stem in seen:
            continue
        p = crop_path.get((group, stem))
        if p is None:
            print("   missing crop:", group, stem)
            continue
        seen.add(stem)
        out.append((p, name))
        if len(out) == n:
            break
    return out


def fit(img, w, h, max_up=2.5):
    s = min(w / img.width, h / img.height, max_up)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)


def sheet(path, per_group, cell, title, subtitle, note, cols=None, dedupe=True, forms=None):
    pad, label_w, gap = 46, 640, 26
    cols = cols or per_group
    width = pad + label_w + cols * (cell[0] + gap) + pad
    content_w = width - 2 * pad

    f_title, f_sub, f_row, f_note, f_small = font(50, True), font(28), font(26, True), font(30, True), font(22)

    title_lines = wrap(title, f_title, content_w)
    sub_lines = wrap(subtitle, f_sub, content_w)
    note_lines = wrap(note, f_note, content_w)

    blocks = []
    for group, row_label, row_note in GROUPS:
        grid_rows = (per_group + cols - 1) // cols
        lab = wrap(row_label, f_row, label_w - 12)
        nte = wrap(row_note, f_small, label_w - 12)
        text_h = len(lab) * 34 + 8 + len(nte) * 28
        blocks.append({"group": group, "lab": lab, "nte": nte,
                       "h": max(grid_rows * (cell[1] + 74), text_h) + 26})

    title_h = 30 + len(title_lines) * 60 + 10 + len(sub_lines) * 36 + 34
    height = title_h + sum(b["h"] for b in blocks) + 30 + len(note_lines) * 40 + 34

    im = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(im)

    y = 30
    for t in title_lines:
        d.text((pad, y), t, font=f_title, fill=INK)
        y += 60
    y += 10
    for t in sub_lines:
        d.text((pad, y), t, font=f_sub, fill=MUTED)
        y += 36

    y = title_h
    for b in blocks:
        d.line([(pad, y - 14), (width - pad, y - 14)], fill=RULE)
        ly = y + 6
        for t in b["lab"]:
            d.text((pad, ly), t, font=f_row, fill=INK)
            ly += 34
        ly += 8
        for t in b["nte"]:
            d.text((pad, ly), t, font=f_small, fill=MUTED)
            ly += 28
        drawn = pick(b["group"], per_group, forms[b["group"][0]] if forms else None, one_per_picture=dedupe)
        print("   cells for %-26s %d" % (b["group"], len(drawn)))
        for j, (p, name) in enumerate(drawn):
            r, c = divmod(j, cols)
            img = Image.open(p).convert("L").convert("RGB")
            fitted = fit(img, cell[0] - 12, cell[1] - 12)
            cx = pad + label_w + c * (cell[0] + gap)
            cy = y + r * (cell[1] + 74)
            d.rectangle([cx, cy, cx + cell[0], cy + cell[1]], fill=PANEL, outline=RULE)
            im.paste(fitted, (cx + (cell[0] - fitted.width) // 2, cy + (cell[1] - fitted.height) // 2))
        y += b["h"]

    y += 30
    for t in note_lines:
        d.text((pad, y), t, font=f_note, fill=INK)
        y += 40

    try:
        im.save(path)
    except OSError as exc:
        # a viewer or the app's preview can hold the file open, so fall back to a new name
        alt = path.with_name(path.stem + "_v2" + path.suffix)
        im.save(alt)
        print("   %s was locked (%s), wrote %s instead" % (path.name, exc.strerror, alt.name))
        path = alt
    print("wrote", path.name, im.size, "| title lines", len(title_lines), "| note lines", len(note_lines))
    return path


sheet(OUT / "ep_fiber_evidence_1_groups.png", 6, (320, 320),
      "Fiber or Extraneous Polymer: one object, two folder names",
      "Objects cut from the frames at their annotated box, largest first, keeping the form the read put in the majority for that group.",
      "The two groups the folders agree on separate by eye. The contested objects follow the Fiber group: 29 of the 34 read as thin filaments. The whole contested set is on sheet 3.", forms=MAJORITY)

sheet(OUT / "ep_fiber_evidence_2_closeup.png", 3, (560, 460),
      "Fiber or Extraneous Polymer: detail, three objects from each group",
      "The clearest three from each group, chosen on form. Counts for every object in each group are on sheet 1.",
      "A thick mass of varying width against a thin filament of near constant width. 14 of 17 agreed Extraneous Polymer objects read as a mass, 13 of 17 agreed Fiber objects as a filament, 29 of 34 contested as filaments.", forms=MAJORITY)

sheet(OUT / "ep_fiber_evidence_3_all_objects.png", 34, (200, 200),
      "Every object in the check: 68 objects, all three groups",
      "The two groups the folders agree on come first, then all 34 contested objects. Nothing is filtered out of this sheet.",
      "For completeness, so a reader who does not trust the selection on sheets 1 and 2 can work from this one. It includes the 2 contested objects that read as a mass and the 3 that read unclear.",
      cols=9, dedupe=False)
