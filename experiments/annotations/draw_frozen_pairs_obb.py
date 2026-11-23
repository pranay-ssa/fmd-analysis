#!/usr/bin/env python3
"""Redraw the four frozen duplicate pairs with oriented boxes (OBB).

The earlier pair sheets drew every annotation as an upright rectangle over
(xtl, ytl, xbr, ybr).  CVAT stores those four numbers as the UNROTATED base
rectangle and carries the angle separately in `rotation`, so the upright
rectangle is not the shape the annotator marked.  This script applies the
rotation about the base rectangle centre (same convention as
`src/yolo_ooi/common.py`, confirmed against the pictures on 2026-09-07) and
draws the four corners of the real box.

Outputs, under reports/frozen_pairs_20261117/:
    pairs_obb.png          all four pairs on one canvas, two pairs per row
    pair_<n>_obb.png       one pair on its own canvas, drawn large
    pairs_obb_meta.json    crop windows, box counts and match metrics

Source pictures are expected in run/frozen_pairs_20261117/src_images/
(pulled once from the frozen store; run/ is never pushed).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
MANIFEST = REPO / "run/frozen_eda_20261117/store/manifest.csv"
LABELS = [REPO / "run/frozen_eda_20261118/ooi_labels.csv",
          REPO / "run/frozen_eda_20261118/lp_labels.csv"]
SRC = REPO / "run/frozen_pairs_20261117/src_images"
OUT = REPO / "reports/frozen_pairs_20261117"

# One colour per defect class, carried over from the earlier pair sheets.
COLOUR = {
    "P2_BB": (214, 39, 40),     # Bubble
    "P2_BC": (255, 127, 14),    # Bubble Cluster
    "P3_FIB": (30, 150, 60),    # Fiber
    "P3_HE": (140, 40, 170),    # HEMA
    "P3_FM": (44, 80, 200),     # Foreign Matter
    "P3_EP": (0, 160, 190),     # Extraneous Polymer
}
FALLBACK_COLOUR = (200, 0, 200)

# The four size gates are tags, not boxes.  They are stated in the record line.
GATE_NAME = {
    "P3_HE_MICRON_THRESHOLD": "HEMA size flag",
    "P3_FIB_MICRON_THRESHOLD": "Fiber size flag",
    "P3_FM_MICRON_THRESHOLD": "Foreign Matter size flag",
    "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer size flag",
}

INK = (24, 24, 24)
MUTED = (110, 110, 110)
CARD = (255, 255, 255)
RULE = (205, 205, 205)

# Set by --flip; the default draw is the project convention.
FLIP = False


# --------------------------------------------------------------------------- #
# text
# --------------------------------------------------------------------------- #
def _font_file(bold: bool) -> str | None:
    for p in (("C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
              if bold else
              ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
        if Path(p).exists():
            return p
    return None


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _font_file(bold)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def text_w(draw: ImageDraw.ImageDraw, s: str, f) -> float:
    return draw.textlength(s, font=f)


def fit_text(draw: ImageDraw.ImageDraw, s: str, f, limit: int) -> str:
    """Shorten with an ascii ellipsis until it fits `limit` pixels."""
    if text_w(draw, s, f) <= limit:
        return s
    while s and text_w(draw, s + "...", f) > limit:
        s = s[:-1]
    return s.rstrip() + "..."


def fit_text_middle(draw: ImageDraw.ImageDraw, s: str, f, limit: int) -> str:
    """Shorten from the middle, keeping 60% of the head and 40% of the tail.

    The two records of a duplicate pair usually differ only in the tail of the
    name, so the tail must survive.
    """
    if text_w(draw, s, f) <= limit:
        return s
    best, lo, hi = "...", 0, len(s) - 1
    while lo <= hi:
        keep = (lo + hi) // 2
        head = int(keep * 0.6)
        tail = keep - head
        cand = s[:head] + "..." + (s[len(s) - tail:] if tail else "")
        if text_w(draw, cand, f) <= limit:
            best, lo = cand, keep + 1
        else:
            hi = keep - 1
    return best


# --------------------------------------------------------------------------- #
# labels and annotations
# --------------------------------------------------------------------------- #
def class_names() -> dict[str, str]:
    names = {}
    for path in LABELS:
        if not path.exists():
            continue
        for row in csv.DictReader(path.open(encoding="utf-8")):
            names.setdefault(row["code"], row["class"])
    names.update({"P3_HE": "HEMA", "P3_FIB": "Fiber", "P3_FM": "Foreign Matter",
                  "P3_EP": "Extraneous Polymer"})
    return names


def parse_annotations() -> dict[str, dict]:
    """basename -> {tags: [...], boxes: [{code, xtl, ytl, xbr, ybr, rot}]}"""
    # Local client export, already verified by hash against the frozen store;
    # stdlib parsing of these files is intentional (trusted, not network input).
    import xml.etree.ElementTree as ET

    out: dict[str, dict] = {}
    for path in sorted(FROZEN.glob("annotations_*.xml")):
        root = ET.parse(path).getroot()
        job = root.findtext("meta/job/id") or path.stem.replace("annotations_", "")
        for im in root.findall("image"):
            base = im.get("name", "").rsplit("/", 1)[-1]
            boxes = []
            for b in im.findall("box"):
                boxes.append({
                    "code": b.get("label", ""),
                    "xtl": float(b.get("xtl")), "ytl": float(b.get("ytl")),
                    "xbr": float(b.get("xbr")), "ybr": float(b.get("ybr")),
                    "rot": float(b.get("rotation") or 0.0),
                })
            out[base] = {"tags": [t.get("label", "") for t in im.findall("tag")],
                         "boxes": boxes, "job": job,
                         "width": int(im.get("width", 0)), "height": int(im.get("height", 0))}
    return out


def duplicate_pairs() -> list[dict]:
    """The four content-duplicate pairs, in manifest order.

    Both rows of a duplicate are flagged, and the first one names itself as its
    own duplicate, so pairs are grouped by picture key and only two-name groups
    are kept.
    """
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    groups: dict[str, list[str]] = {}
    for r in rows:
        if r.get("content_duplicate") == "yes":
            names = groups.setdefault(r["picture_key"], [])
            if r["basename"] not in names:
                names.append(r["basename"])
    pairs = []
    for key, names in groups.items():
        if len(names) != 2:
            raise SystemExit(f"expected two records for {key}, found {len(names)}: {names}")
        pairs.append({"a": names[0], "b": names[1], "key": key})
    return pairs


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #
def corners(box: dict, flip: bool = False, aabb: bool = False) -> list[tuple[float, float]]:
    """Four corners of the annotated rectangle in image pixels.

    CVAT stores the base rectangle in (xtl, ytl, xbr, ybr) and the angle that
    was applied to it about its centre.  `flip` reverses the spin direction and
    exists only to re-check the convention against a picture; the project
    convention is flip=False (clockwise in row space, y downward).
    """
    xtl, ytl, xbr, ybr = box["xtl"], box["ytl"], box["xbr"], box["ybr"]
    if aabb or not box["rot"]:
        return [(xtl, ytl), (xbr, ytl), (xbr, ybr), (xtl, ybr)]
    cx, cy = (xtl + xbr) / 2.0, (ytl + ybr) / 2.0
    w, h = xbr - xtl, ybr - ytl
    rad = math.radians(box["rot"])
    # Same spin as src/yolo_ooi/common.py (confirmed against the pictures on
    # 2026-09-07): x' = dx*cos - dy*sin, y' = dx*sin + dy*cos, clockwise on
    # screen because y runs downward.
    sgn = -1.0 if (flip or FLIP) else 1.0
    c, s = math.cos(rad), math.sin(rad)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append((cx + dx * c - sgn * dy * s, cy + sgn * dx * s + dy * c))
    return pts


def _signed_area(poly: list[tuple[float, float]]) -> float:
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _ccw(poly):
    return poly if _signed_area(poly) > 0 else list(reversed(poly))


def _clip(subject, clipper):
    """Sutherland-Hodgman, both polygons convex and counter-clockwise."""
    out = subject
    for i in range(len(clipper)):
        if not out:
            return []
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

        new = []
        for j in range(len(out)):
            p, q = out[j], out[(j + 1) % len(out)]
            pin, qin = inside(p), inside(q)
            if pin and qin:
                new.append(q)
            elif pin and not qin:
                new.append(_intersect(p, q, a, b))
            elif not pin and qin:
                new.append(_intersect(p, q, a, b))
                new.append(q)
        out = new
    return out


def _intersect(p, q, a, b):
    px, py = p
    qx, qy = q
    ax, ay = a
    bx, by = b
    rx, ry = qx - px, qy - py
    sx, sy = bx - ax, by - ay
    denom = rx * sy - ry * sx
    if abs(denom) < 1e-12:
        return q
    t = ((ax - px) * sy - (ay - py) * sx) / denom
    return (px + t * rx, py + t * ry)


def poly_area(poly) -> float:
    return abs(_signed_area(poly))


def poly_iou(a, b) -> float:
    a, b = _ccw(a), _ccw(b)
    inter = _clip(a, b)
    if not inter:
        return 0.0
    ia = poly_area(inter)
    union = poly_area(a) + poly_area(b) - ia
    return ia / union if union > 0 else 0.0


def corner_shift(a, b) -> float:
    """Mean corner distance between two matched boxes, best of the four
    orderings so a 90-degree multiple cannot inflate an identical box."""
    best = float("inf")
    for k in range(4):
        shifted = b[k:] + b[:k]
        d = sum(math.dist(p, q) for p, q in zip(a, shifted)) / 4.0
        best = min(best, d)
    return best


def match(boxes_a, boxes_b, aabb=False):
    """Greedy same-class matching by descending IoU."""
    cand = []
    for i, a in enumerate(boxes_a):
        for j, b in enumerate(boxes_b):
            if a["code"] != b["code"]:
                continue
            ca, cb = corners(a, aabb=aabb), corners(b, aabb=aabb)
            cand.append((poly_iou(ca, cb), i, j))
    cand.sort(reverse=True)
    used_a, used_b, out = set(), set(), []
    for iou, i, j in cand:
        if i in used_a or j in used_b or iou <= 0.0:
            continue
        used_a.add(i)
        used_b.add(j)
        out.append({"iou": iou,
                    "shift": corner_shift(corners(boxes_a[i], aabb=aabb),
                                          corners(boxes_b[j], aabb=aabb)),
                    "code": boxes_a[i]["code"]})
    return out


def median(values):
    v = sorted(values)
    if not v:
        return 0.0
    m = len(v) // 2
    return v[m] if len(v) % 2 else 0.5 * (v[m - 1] + v[m])


# --------------------------------------------------------------------------- #
# sheet
# --------------------------------------------------------------------------- #
class Sheet:
    def __init__(self, width: int, height: int):
        self.img = Image.new("RGB", (width, height), (250, 250, 250))
        self.d = ImageDraw.Draw(self.img)
        self.f = {}

    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self.f:
            self.f[key] = font(size, bold)
        return self.f[key]

    def text(self, xy, s, size, bold=False, fill=INK, anchor="la"):
        self.d.text(xy, s, font=self.font(size, bold), fill=fill, anchor=anchor)


def crop_window(boxes: list[dict], width: int, height: int, pad_frac=0.06) -> tuple[int, int, int, int]:
    xs, ys = [], []
    for b in boxes:
        for x, y in corners(b):
            xs.append(x)
            ys.append(y)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pad = max(24.0, pad_frac * max(x1 - x0, y1 - y0))
    x0 = max(0, int(math.floor(x0 - pad)))
    y0 = max(0, int(math.floor(y0 - pad)))
    x1 = min(width, int(math.ceil(x1 + pad)))
    y1 = min(height, int(math.ceil(y1 + pad)))
    return x0, y0, x1, y1


def record_line(rec: dict, names: dict[str, str]) -> str:
    parts = []
    for tag in rec["tags"]:
        parts.append(GATE_NAME.get(tag, names.get(tag, tag)))
    s = f"{len(rec['boxes'])} boxes"
    return s + ("; " + ", ".join(parts) if parts else "")


def draw_panel(sheet: Sheet, x, y, w, h, image, crop, boxes, colour_by_code, line_px, aabb=False):
    x0, y0, x1, y1 = crop
    piece = image.crop(crop)
    cw, ch = piece.size
    scale = min(w / cw, h / ch)
    tw, th = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    ox = x + (w - tw) // 2
    oy = y + (h - th) // 2
    sheet.d.rectangle([ox - 1, oy - 1, ox + tw, oy + th], fill=CARD, outline=RULE)
    sheet.img.paste(piece.resize((tw, th), Image.LANCZOS), (ox, oy))

    for b in boxes:
        pts = [((px - x0) * scale + ox, (py - y0) * scale + oy) for px, py in corners(b, aabb=aabb)]
        colour = colour_by_code.get(b["code"], FALLBACK_COLOUR)
        # Colour only: a pale inner rim washed out the small marks it enclosed.
        sheet.d.polygon(pts, fill=None, outline=colour, width=line_px)

    # panel geometry, used by the verifier to find every drawn box again
    return {"x": ox, "y": oy, "w": tw, "h": th, "scale": scale}


def build_sheet(pairs, records, images, names, out_path, panel_w, panel_h,
                per_pair=False, aabb=False, title=None):
    margin, pair_label_h, head_h, info_h, foot_h = 40, 34, 60, 34, 46
    title_h, sub_h, legend_h = 40, 24, 46
    inner_gap, pair_gap, row_gap = 12, 34, 22

    classes = []
    for p in pairs:
        for rec in (records[p["a"]], records[p["b"]]):
            for b in rec["boxes"]:
                if b["code"] not in classes:
                    classes.append(b["code"])
    classes.sort(key=lambda c: names.get(c, c))
    colour_by_code = {c: COLOUR.get(c, FALLBACK_COLOUR) for c in classes}

    cols = 1 if per_pair else 2
    rows = math.ceil(len(pairs) / cols)
    cell_w = 2 * panel_w + inner_gap
    width = 2 * margin + cols * cell_w + (cols - 1) * pair_gap
    cell_h = pair_label_h + head_h + panel_h + info_h
    height = (margin + title_h + sub_h + legend_h + rows * cell_h
              + (rows - 1) * row_gap + foot_h + margin)

    sheet = Sheet(width, height)
    line_px = max(2, int(round(panel_w / 220)))

    y = margin
    sheet.text((margin, y), title or "Four duplicate pairs: one picture, two annotation records", 25, bold=True)
    y += title_h
    sheet.text((margin, y),
               "Each pair is the same picture filed twice; the two records were annotated separately. "
               "Boxes are drawn as annotated: rotated rectangles, not upright ones.", 15, fill=MUTED)
    y += sub_h + 10

    # legend
    lx = margin
    for code in classes:
        sheet.d.rectangle([lx, y + 3, lx + 18, y + 15], outline=colour_by_code[code], width=max(2, line_px - 1))
        label = names.get(code, code)
        sheet.text((lx + 26, y), label, 15)
        lx += 26 + int(text_w(sheet.d, label, sheet.font(15))) + 28
    y += legend_h

    meta = []
    for idx, pair in enumerate(pairs):
        col, row = idx % cols, idx // cols
        px = margin + col * (cell_w + pair_gap)
        py = y + row * (cell_h + row_gap)

        rec_a, rec_b = records[pair["a"]], records[pair["b"]]
        all_boxes = rec_a["boxes"] + rec_b["boxes"]
        w_img, h_img = rec_a["width"] or 2448, rec_a["height"] or 2048
        crop = crop_window(all_boxes, w_img, h_img)

        sheet.text((px, py), f"Pair {pair.get('no', idx + 1)}", 20, bold=True)

        panels = []
        for k, (tag, rec, base) in enumerate((("Record A", rec_a, pair["a"]), ("Record B", rec_b, pair["b"]))):
            x = px + k * (panel_w + inner_gap)
            sheet.text((x, py + pair_label_h), tag, 15, bold=True)
            sheet.text((x + panel_w, py + pair_label_h + 1),
                       f"{len(rec['boxes'])} boxes", 14, fill=MUTED, anchor="ra")
            # The two records of a pair often differ only in a numeric suffix, so
            # a plain cut at the right edge hides the one part that tells them
            # apart: shorten from the middle instead.
            sheet.text((x, py + pair_label_h + 21),
                       fit_text_middle(sheet.d, base, sheet.font(12), panel_w), 12, fill=MUTED)
            sheet.text((x, py + pair_label_h + 37),
                       fit_text_middle(sheet.d, record_line(rec, names), sheet.font(12), panel_w),
                       12, fill=MUTED)
            geom = draw_panel(sheet, x, py + pair_label_h + head_h, panel_w, panel_h,
                              images[base], crop, rec["boxes"], colour_by_code, line_px, aabb=aabb)
            panels.append({"record": tag, "basename": base,
                           "crop": {"x0": crop[0], "y0": crop[1], "x1": crop[2], "y1": crop[3]},
                           "line_px": line_px, **geom})

        m = match(rec_a["boxes"], rec_b["boxes"], aabb=aabb)
        ious = [x["iou"] for x in m]
        shifts = [x["shift"] for x in m]
        info = (f"{len(m)} matched boxes, median IoU {median(ious):.2f}, "
                f"median corner shift {median(shifts):.1f} px "
                f"(largest {max(shifts) if shifts else 0.0:.1f} px).")
        iy = py + pair_label_h + head_h + panel_h + 10
        sheet.text((px, iy), info, 15)

        meta.append({
            "pair": pair.get("no", idx + 1),
            "record_a": pair["a"], "record_b": pair["b"],
            "boxes_a": len(rec_a["boxes"]), "boxes_b": len(rec_b["boxes"]),
            "crop": {"x0": crop[0], "y0": crop[1], "x1": crop[2], "y1": crop[3]},
            "matched": len(m),
            "median_iou": round(median(ious), 4),
            "median_corner_shift_px": round(median(shifts), 3),
            "largest_corner_shift_px": round(max(shifts), 3) if shifts else 0.0,
            "boxes_only_in_a": len(rec_a["boxes"]) - len(m),
            "boxes_only_in_b": len(rec_b["boxes"]) - len(m),
            "job": rec_a.get("job", ""),
            "mode": "axis-aligned" if aabb else "oriented",
            "panels": panels,
        })

    # footer, kept apart from the last pair so it cannot read as part of it
    rule_y = height - margin - 34
    sheet.d.line([margin, rule_y, width - margin, rule_y], fill=RULE, width=1)
    sheet.text((margin, rule_y + 8),
               "Two records per pair come from the same annotation job. "
               "Box outlines follow the annotated rectangle; nothing is redrawn by hand.", 13, fill=MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.img.save(out_path)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", type=int, help="draw one pair only, large (1-4)")
    ap.add_argument("--panel", type=int, default=700, help="panel width in pixels on the four-pair canvas")
    ap.add_argument("--aabb", action="store_true", help="draw upright rectangles instead (before/after check)")
    ap.add_argument("--flip", action="store_true", help="reverse the spin direction (convention re-check only)")
    ap.add_argument("--out", type=Path, help="output png")
    ap.add_argument("--meta", type=Path, help="output json")
    args = ap.parse_args()

    names = class_names()
    records = parse_annotations()
    pairs = duplicate_pairs()
    for i, p in enumerate(pairs, 1):
        p["no"] = i
    if args.pair:
        pairs = [pairs[args.pair - 1]]

    needed = {p[k] for p in pairs for k in ("a", "b")}
    missing = [n for n in needed if not (SRC / n).exists()]
    if missing:
        raise SystemExit("source picture missing from %s:\n  %s" % (SRC, "\n  ".join(sorted(missing))))
    images = {n: Image.open(SRC / n).convert("L") for n in needed}

    if args.pair:
        panel = 760
        out = args.out or OUT / f"pair_{args.pair}_obb.png"
        title = f"Pair {args.pair}: one picture, two annotation records"
    else:
        panel = args.panel
        out = args.out or OUT / ("pairs_aabb.png" if args.aabb else "pairs_obb.png")
        title = "Four duplicate pairs: one picture, two annotation records"

    # convention guard: --flip renders the mirrored geometry for a visual check
    global FLIP
    FLIP = args.flip
    if args.flip:
        out = out.with_name(out.stem.split("_flip")[0] + "_mirror" + out.suffix)

    meta = build_sheet(pairs, records, images, names, out, panel, panel,
                       per_pair=bool(args.pair), aabb=args.aabb, title=title)
    mpath = args.meta or out.with_name(out.stem + "_meta.json")
    mpath.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(out)
    for m in meta:
        print(f"pair {m['pair']}: {m['boxes_a']} / {m['boxes_b']} boxes, "
              f"{m['matched']} matched, median IoU {m['median_iou']:.2f}")


if __name__ == "__main__":
    main()
