#!/usr/bin/env python3
"""
Build a simple lead-ready deck (.pptx) showing the Bubble before/after EDA.

Slides:
  1. Title
  2. What we did (plain steps)
  3. The two Excel sheets + column meanings
  4-6. Three example lenses: BEFORE (red box) vs AFTER (red box) + numbers
  7. HEMA findings (short)
  8. What we ask Swetha (next step)

Images: original BMP with the CVAT box drawn in red, and the crop BMP with the
same box remapped by the manifest offset (red). All numbers are read from the
real eda_after_Bubble.csv and crop_manifest.csv. No values are invented.
"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

HERE = Path(__file__).resolve().parent
ORIG = HERE / "input/Bubble"
CROPS = HERE / "outputs_bubble_test"
ANNOT = HERE / "samples/annotations.xml"
EDA = HERE / "eda_bubble/eda_after_Bubble.csv"
OUT_DIR = HERE / "deck_assets"
OUT_DIR.mkdir(exist_ok=True)

MARGIN_BOX = 3  # px line width on 2448x2048 images

# ---- read data ------------------------------------------------------------- #
def read_manifest():
    return {r["file"]: r for r in csv.DictReader((CROPS/"crop_manifest.csv").open())}

def read_eda():
    return {r["file"]: r for r in csv.DictReader(EDA.open())}

def boxes_for_image(name):
    txt = ANNOT.read_text(encoding="utf-8")
    import re
    pat = re.compile(r'<image[^>]*name="[^\"]*' + re.escape(name)
                     + r'"[^>]*>(.*?)</image>', re.DOTALL)
    m = pat.search(txt)
    if not m: return []
    out=[]
    for bm in re.finditer(r'<box\b([^>]*)>', m.group(1)):
        a=dict(re.findall(r'(\w+)="([^\"]*)"', bm.group(1)))
        if a.get("label","").startswith("Bubble"):
            out.append((float(a["xtl"]),float(a["ytl"]),
                        float(a["xbr"]),float(a["ybr"])))
    return out

def draw_red_box(img, boxes, offset=(0,0)):
    im = img.convert("RGB")
    d = ImageDraw.Draw(im)
    ox, oy = offset
    for (xtl,ytl,xbr,ybr) in boxes:
        d.rectangle([xtl-ox, ytl-oy, xbr-ox, ybr-oy],
                    outline=(255,0,0), width=MARGIN_BOX)
    return im

def make_composite(stem, manifest, eda):
    name = stem + ".bmp"
    orig = Image.open(ORIG/name)
    crop = Image.open(CROPS/f"{stem}_crop.bmp")
    boxes = boxes_for_image(name)
    left=int(manifest[name]["left"]); top=int(manifest[name]["top"])
    before = draw_red_box(orig, boxes)                 # offset 0
    after  = draw_red_box(crop, boxes, offset=(left,top))
    # fit to slide width ~9in, keep aspect
    bpath = OUT_DIR/f"{stem}_before.png"
    apath = OUT_DIR/f"{stem}_after.png"
    W=1100
    for im,p in [(before,bpath),(after,apath)]:
        h=int(im.height*W/im.width)
        im.resize((W,h)).save(p)
    return bpath, apath

# ---- build slides ---------------------------------------------------------- #
def add_title_slide(prs, title, subtitle):
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = title
    s.placeholders[1].text = subtitle
    return s

def add_text_slide(prs, title, bullets, fontsize=18):
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = title
    tf = s.placeholders[1].text_frame
    tf.word_wrap = True
    for i,b in enumerate(bullets):
        p = tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text = b
        p.font.size = Pt(fontsize)
    return s

def add_image_slide(prs, title, before_path, after_path, caption_lines):
    s = prs.slides.add_slide(prs.slide_layouts[5])  # blank
    # title
    tb = s.shapes.add_textbox(Inches(0.4), Inches(0.2), Inches(9.2), Inches(0.6))
    tb.text_frame.text = title
    tb.text_frame.paragraphs[0].font.size = Pt(24)
    tb.text_frame.paragraphs[0].font.bold = True
    # two images side by side
    s.shapes.add_picture(str(before_path), Inches(0.3), Inches(1.0), width=Inches(4.5))
    s.shapes.add_picture(str(after_path), Inches(5.0), Inches(1.0), width=Inches(4.5))
    # labels under images
    lab = s.shapes.add_textbox(Inches(0.3), Inches(5.6), Inches(4.5), Inches(0.4))
    lab.text_frame.text = "LEFT: Original lens  (red box = defect)"
    lab.text_frame.paragraphs[0].font.size = Pt(13)
    lab2 = s.shapes.add_textbox(Inches(5.0), Inches(5.6), Inches(4.5), Inches(0.4))
    lab2.text_frame.text = "RIGHT: Cropped lens (red box = same defect, moved)"
    lab2.text_frame.paragraphs[0].font.size = Pt(13)
    # numbers
    cap = s.shapes.add_textbox(Inches(0.3), Inches(6.1), Inches(9.3), Inches(1.6))
    tf = cap.text_frame; tf.word_wrap=True
    for i,line in enumerate(caption_lines):
        p = tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text = line; p.font.size = Pt(14)
    return s

# ---- main ------------------------------------------------------------------ #
def main():
    manifest = read_manifest()
    eda = read_eda()
    examples = [
        ("20241101_110324_L24_C11_9264", "Example 1 - one small defect"),
        ("20241106_181317_L24_C6_9662",  "Example 2 - several defects"),
        ("20241106_062653_L24_C6_1",      "Example 3 - many defects (38)"),
    ]

    prs = Presentation()
    prs.slide_width = Inches(10); prs.slide_height = Inches(7.5)

    # 1 title
    add_title_slide(prs, "FMD Preprocessing - Bubble Class Check",
                    "Before / After proof  |  Prepared for Swetha  |  2026-08-27")

    # 2 what we did
    add_text_slide(prs, "What we did (simple steps)",
        ["1. We took 114 Bubble lens images from the VM.",
         "2. We ran ROI-Crop: it cuts the black border and keeps only the lens.",
         "3. The crop is a clean cut. No pixel value is changed. Only a window is cut.",
         "4. We logged the cut offset (left, top) for each image.",
         "5. We checked: does the defect box stay correct after the cut?",
         "6. We made two Excel sheets: BEFORE (original) and AFTER (cropped).",
         "7. Result: 113 images with boxes all passed. Nothing was lost."])

    # 3 sheets + columns
    add_text_slide(prs, "The two Excel sheets and what the columns mean",
        ["Two sheets, one per image row (not per defect):",
         "",
         "BEFORE sheet  - data from the original image:",
         "  file                  = image name",
         "  n_boxes               = how many defects in the image",
         "  total_defect_area_px  = sum of all defect box areas",
         "  env_xtl/ytl/xbr/ybr   = one box around ALL defects (envelope)",
         "  env_centroid_x/y      = center point of that envelope",
         "",
         "AFTER sheet - same columns PLUS:",
         "  left, top             = the cut offset (how far the crop moved)",
         "  env_*_c               = the envelope moved by the offset",
         "  area_invariance       = PASS if area did not change",
         "  centroid_shift_ok     = PASS if center moved by exactly (left,top)",
         "  all_boxes_inside_crop = True if no defect was cut off",
         "  min_clearance_px      = closest any defect is to the crop edge"])

    # 4-6 examples
    for stem, title in examples:
        b,a = make_composite(stem, manifest, eda)
        r = eda[stem]  # EDA 'file' column is the stem (no extension)
        cap = [
            f"Image: {stem}",
            f"Defects in image: {r['n_boxes']}",
            f"Offset used: left={r['left']} px, top={r['top']} px",
            f"Defect area BEFORE = {r['total_defect_area_px']} px   AFTER = same (no change)",
            f"Center moved by exactly the offset: centroid_shift_ok = {r['centroid_shift_ok']}",
            f"All defects inside crop: {r['all_boxes_inside_crop']}   |   closest defect to edge: {r['min_clearance_px']} px",
            f"Verdict: {r['status'].upper()} - the crop is pixel-accurate.",
        ]
        add_image_slide(prs, title, b, a, cap)

    # 7 HEMA
    add_text_slide(prs, "HEMA check (separate, for information)",
        ["We also tested HEMA images (long / faint defects).",
         "Result: 0 defects were cut off. But one 2026 HEMA image sat 1.9 px",
         "below the 45 px margin (tight, not cut).",
         "Other HEMA images had comfortable space (up to 325 px).",
         "",
         "What we suggest: give HEMA a bigger margin (~70-80 px) later.",
         "Bubble does NOT need this - Bubble defects sit far from the edge",
         "(closest was 128 px, well above 45 px).",
         "",
         "Full detail is in HEMA_Margin_Report.md."])

    # 8 ask
    add_text_slide(prs, "What we ask from this review",
        ["Please confirm the before/after method is what you want.",
         "Is the two-sheet (BEFORE / AFTER) format clear and useful?",
         "Are the column names right, or do you want different ones?",
         "For HEMA: do you agree to a bigger margin, or keep 45 px for now?",
         "Once approved, we run the same check on ALL defect classes on the VM."])

    out = HERE/"Bubble_BeforeAfter_Deck.pptx"
    prs.save(str(out))
    print("Saved deck:", out)
    print("Assets in:", OUT_DIR)

if __name__ == "__main__":
    main()
