"""Build the weekly draft deck from a JSON spec.

Content and structure only: no template, no logo, no brand colours. The user
moves the result into the office template and fixes the layout by hand.

Usage:
    .venv/Scripts/python.exe decks/drafts/build_draft.py \
        decks/drafts/spec_2026W45_draft1.json \
        decks/drafts/FMD_MultiLabel_2026W45_DRAFT.pptx
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x6B, 0x72, 0x80)
LINE = RGBColor(0x9C, 0xA3, 0xAF)
LIGHT = RGBColor(0xF3, 0xF4, 0xF6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEADER = RGBColor(0x37, 0x41, 0x51)
ZEBRA = RGBColor(0xF9, 0xFA, 0xFB)


def rgb(value: str | None, default: RGBColor) -> RGBColor:
    if not value:
        return default
    value = value.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def align_of(value: str | None):
    return {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER,
            "right": PP_ALIGN.RIGHT}.get(value or "left", PP_ALIGN.LEFT)


def anchor_of(value: str | None):
    return {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE,
            "bottom": MSO_ANCHOR.BOTTOM}.get(value or "top", MSO_ANCHOR.TOP)


def style_run(run, size=None, bold=None, color=None, italic=None, font="Calibri"):
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run.font.name = font


def add_text(slide, item):
    box = slide.shapes.add_textbox(Inches(item["l"]), Inches(item["t"]),
                                   Inches(item["w"]), Inches(item["h"]))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor_of(item.get("anchor"))
    lines = str(item.get("text", "")).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align_of(item.get("align"))
        if item.get("spacing"):
            p.space_after = Pt(item["spacing"])
        run = p.add_run()
        run.text = line
        style_run(run, item.get("size", 12), item.get("bold", False),
                  rgb(item.get("color"), INK), item.get("italic", False))
    return box


def add_bullets(slide, item):
    box = slide.shapes.add_textbox(Inches(item["l"]), Inches(item["t"]),
                                   Inches(item["w"]), Inches(item["h"]))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor_of(item.get("anchor"))
    size = item.get("size", 14)
    numbered = item.get("numbered", False)
    bullet = item.get("bullet", "\u2022")
    for i, entry in enumerate(item["items"]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(item.get("space", 10))
        p.line_spacing = item.get("line_spacing", 1.05)
        prefix = f"{i + 1}.  " if numbered else f"{bullet}  "
        if isinstance(entry, dict):
            lead = p.add_run()
            lead.text = prefix + entry["lead"]
            style_run(lead, size, True, rgb(item.get("color"), INK))
            rest = p.add_run()
            rest.text = entry.get("text", "")
            style_run(rest, size, False, rgb(item.get("color"), INK))
        else:
            run = p.add_run()
            run.text = prefix + str(entry)
            style_run(run, size, False, rgb(item.get("color"), INK))
    return box


def add_rect(slide, item):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if item.get("kind") in ("rect", "pill") \
        else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(item["l"]), Inches(item["t"]),
                                   Inches(item["w"]), Inches(item["h"]))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(item.get("fill"), WHITE)
    shape.line.color.rgb = rgb(item.get("line"), LINE)
    shape.line.width = Pt(item.get("line_width", 0.9))
    shape.shadow.inherit = False
    if shape_type == MSO_SHAPE.ROUNDED_RECTANGLE:
        shape.adjustments[0] = item.get("radius", 0.5 if item["kind"] == "pill" else 0.08)
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    lines = str(item.get("text", "")).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align_of(item.get("align", "center"))
        run = p.add_run()
        run.text = line
        style_run(run, item.get("size", 11), item.get("bold", False),
                  rgb(item.get("color"), INK), item.get("italic", False))
    return shape


def add_line(slide, item):
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(item["x1"]),
                                      Inches(item["y1"]), Inches(item["x2"]),
                                      Inches(item["y2"]))
    line.line.color.rgb = rgb(item.get("color"), LINE)
    line.line.width = Pt(item.get("width", 1.0))
    return line


def add_arrow(slide, item):
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(item["x1"]),
                                      Inches(item["y1"]), Inches(item["x2"]),
                                      Inches(item["y2"]))
    line.line.color.rgb = rgb(item.get("color"), MUTED)
    line.line.width = Pt(item.get("width", 1.4))
    ln = line._element.spPr.get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    return line


def add_bar(slide, item):
    # track
    track = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(item["l"]),
                                   Inches(item["t"]), Inches(item["w"]),
                                   Inches(item["h"]))
    track.fill.solid()
    track.fill.fore_color.rgb = rgb(item.get("track"), LIGHT)
    track.line.fill.background()
    track.shadow.inherit = False
    frac = max(0.0, min(1.0, float(item.get("frac", 0.0))))
    if frac > 0:
        fill = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(item["l"]),
                                      Inches(item["t"]), Inches(item["w"] * frac),
                                      Inches(item["h"]))
        fill.fill.solid()
        fill.fill.fore_color.rgb = rgb(item.get("fill"), HEADER)
        fill.line.fill.background()
        fill.shadow.inherit = False
    return track


def add_table(slide, item):
    rows = item["rows"]
    n_rows, n_cols = len(rows), len(rows[0])
    frame = slide.shapes.add_table(n_rows, n_cols, Inches(item["l"]), Inches(item["t"]),
                                   Inches(item["w"]), Inches(item["h"]))
    table = frame.table
    table.horz_banding = False
    table.first_row = True
    tbl_pr = table._tbl.tblPr
    style = tbl_pr.find(qn("a:tableStyleId"))
    if style is None:
        style = etree.SubElement(tbl_pr, qn("a:tableStyleId"))
    style.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"
    for j, width in enumerate(item["col_widths"]):
        table.columns[j].width = Inches(width)
    for i, row in enumerate(rows):
        if item.get("row_h"):
            table.rows[i].height = Inches(item["row_h"])
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.07)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if item.get("header", True) and i == 0:
                cell.fill.fore_color.rgb = HEADER
            else:
                cell.fill.fore_color.rgb = WHITE if i % 2 else ZEBRA
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = align_of(item.get("align") or ("left" if j == 0 else "center"))
            run = p.add_run()
            run.text = str(value)
            header = item.get("header", True) and i == 0
            pending = str(value).strip().lower() == "pending"
            style_run(run, item.get("font", 11), header or pending,
                      WHITE if header else (MUTED if pending else INK),
                      pending)
    return table


def add_slide(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    if not spec.get("bare"):
        add_text(slide, {"l": 0.5, "t": 0.3, "w": 12.33, "h": 0.62,
                         "text": spec.get("title", ""), "size": 25, "bold": True})
        if spec.get("subtitle"):
            add_text(slide, {"l": 0.5, "t": 0.98, "w": 12.33, "h": 0.42,
                             "text": spec["subtitle"], "size": 12.5, "color": "#6B7280"})
    for item in spec.get("items", []):
        kind = item.get("kind", "text")
        if kind == "text":
            add_text(slide, item)
        elif kind == "bullets":
            add_bullets(slide, item)
        elif kind in ("rect", "pill"):
            add_rect(slide, item)
        elif kind == "line":
            add_line(slide, item)
        elif kind == "arrow":
            add_arrow(slide, item)
        elif kind == "bar":
            add_bar(slide, item)
        elif kind == "table":
            add_table(slide, item)
        else:
            raise SystemExit(f"unknown item kind: {kind}")
    if spec.get("notes"):
        slide.notes_slide.notes_text_frame.text = spec["notes"]
    if not spec.get("bare"):
        add_text(slide, {"l": 12.45, "t": 7.12, "w": 0.55, "h": 0.25,
                         "text": str(len(prs.slides)), "size": 9,
                         "color": "#9CA3AF", "align": "right"})
    return slide


def main() -> None:
    spec_path = Path(sys.argv[1] if len(sys.argv) > 1
                     else "decks/drafts/spec_2026W45_draft1.json")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2
                    else "decks/drafts/FMD_MultiLabel_2026W45_DRAFT.pptx")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    prs = Presentation()
    prs.slide_width = Inches(spec.get("slide_size", [13.333, 7.5])[0])
    prs.slide_height = Inches(spec.get("slide_size", [13.333, 7.5])[1])
    for slide_spec in spec["slides"]:
        add_slide(prs, slide_spec)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)
    print(f"wrote {out_path} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
