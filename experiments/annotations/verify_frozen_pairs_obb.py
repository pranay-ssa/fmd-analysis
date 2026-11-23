#!/usr/bin/env python3
"""Verify the duplicate-pair sheets against the annotation file.

Four independent checks, so a pass means the picture agrees with the record:

1. record   - box count and class codes per record equal the frozen manifest,
              which was built by a different script from the same XML.
2. geometry - for every box, the drawn quad has the annotated side lengths,
              area, centre and rotated extent.
3. raster   - in the finished PNG, every box corner carries its class colour,
              and no pixel of that colour sits away from an annotated edge.
4. content  - the grey level inside each box in the panel equals the grey level
              inside the same box on the source picture, so the box sits on the
              same part of the image it was annotated on.

Outputs run/frozen_pairs_20261117/verify.json and verify_boxes.csv.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports/frozen_pairs_20261117"
RUN = REPO / "run/frozen_pairs_20261117"
MODULE = REPO / "experiments/annotations/draw_frozen_pairs_obb.py"
MANIFEST = REPO / "run/frozen_eda_20261117/store/manifest.csv"
SRC = RUN / "src_images"

TOL_COLOUR = 8          # exact drawing colour; small tolerance for PNG round-trip
GREY_TOL = 10.0         # panel vs source grey level, resampling slack


def load_drawer():
    spec = importlib.util.spec_from_file_location("drawer", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quad_numpy(b, flip=False):
    """Same convention, different code path: explicit rotation matrix."""
    cx, cy = (b["xtl"] + b["xbr"]) / 2.0, (b["ytl"] + b["ybr"]) / 2.0
    w, h = b["xbr"] - b["xtl"], b["ybr"] - b["ytl"]
    ang = math.radians(b["rot"])
    sgn = -1.0 if flip else 1.0
    rot = np.array([[math.cos(ang), -sgn * math.sin(ang)],
                    [sgn * math.sin(ang), math.cos(ang)]])
    local = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    return local @ rot.T + np.array([cx, cy])


def shoelace(pts) -> float:
    pts = np.asarray(pts, dtype=float)
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def mask_at(img_arr, polygon, bbox_limit=None):
    """Boolean mask of a polygon on an image array, optionally inside a bbox."""
    h, w = img_arr.shape[:2]
    pts = np.asarray(polygon, dtype=float)
    if bbox_limit is None:
        x0 = max(0, int(math.floor(pts[:, 0].min())) - 2)
        y0 = max(0, int(math.floor(pts[:, 1].min())) - 2)
        x1 = min(w, int(math.ceil(pts[:, 0].max())) + 3)
        y1 = min(h, int(math.ceil(pts[:, 1].max())) + 3)
    else:
        x0, y0, x1, y1 = [int(v) for v in bbox_limit]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return None, (0, 0)
    m = Image.new("1", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(m).polygon([(px - x0, py - y0) for px, py in pts], fill=1)
    return np.asarray(m, dtype=bool), (x0, y0)


def shrink(polygon, factor=0.6):
    pts = np.asarray(polygon, dtype=float)
    c = pts.mean(axis=0)
    return (pts - c) * factor + c


def seg_distance(px, py, a, b):
    """Distance from points (px, py) to segment a-b, vectorised."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return np.hypot(px - ax, py - ay)
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def count_blobs(mask):
    """8-connected components of a boolean mask, pure numpy + union-find."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return 0
    index = {(int(y), int(x)): i for i, (y, x) in enumerate(zip(ys, xs))}
    parent = list(range(len(xs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for (y, x), i in index.items():
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                j = index.get((y + dy, x + dx))
                if j is not None:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[ri] = rj
    return len({find(i) for i in range(len(xs))})


def main():
    draw = load_drawer()
    names = draw.class_names()
    records = draw.parse_annotations()
    pairs = draw.duplicate_pairs()

    sheet_path = OUT / "pairs_obb.png"
    meta_path = OUT / "pairs_obb_meta.json"
    sheet = np.asarray(Image.open(sheet_path).convert("RGB")).astype(int)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    manifest = {r["basename"]: r for r in csv.DictReader(MANIFEST.open(encoding="utf-8"))}

    checks = {"record": [], "geometry": [], "raster": [], "content": []}
    rows = []
    colour_of = {code: draw.COLOUR.get(code, draw.FALLBACK_COLOUR) for code in names}

    for mpair in meta:
        want = next(p for p in pairs if p["a"] == mpair["record_a"])
        for panel in mpair["panels"]:
            base = panel["basename"]
            rec = records[base]
            mrow = manifest[base]

            # 1. record: annotation vs the frozen manifest
            codes = sorted({b["code"] for b in rec["boxes"]})
            ok_count = int(mrow["n_boxes"]) == len(rec["boxes"])
            ok_codes = set(mrow["box_codes"].split(";")) == set(codes)
            checks["record"].append(ok_count and ok_codes)

            crop = panel["crop"]
            scale = panel["scale"]
            ox, oy = panel["x"], panel["y"]
            pw, ph = panel["w"], panel["h"]
            line_px = panel["line_px"]

            source = np.asarray(Image.open(SRC / base).convert("L"))

            # pixels of each class colour inside this panel
            panel_px = sheet[oy:oy + ph, ox:ox + pw]
            colour_masks = {}
            for code in codes:
                cr, cg, cb = colour_of[code]
                colour_masks[code] = (
                    (np.abs(panel_px[:, :, 0] - cr) <= TOL_COLOUR)
                    & (np.abs(panel_px[:, :, 1] - cg) <= TOL_COLOUR)
                    & (np.abs(panel_px[:, :, 2] - cb) <= TOL_COLOUR)
                )

            panel_quads, source_quads = [], []
            for b in rec["boxes"]:
                gq = np.array(draw.corners(b))
                nq = quad_numpy(b)

                # 2. geometry
                sides = sorted([b["xbr"] - b["xtl"], b["ybr"] - b["ytl"]])
                drawn_sides = sorted([
                    float(np.linalg.norm(gq[1] - gq[0])), float(np.linalg.norm(gq[3] - gq[0]))])
                area_ok = abs(shoelace(gq) - sides[0] * sides[1]) < 1e-4
                side_ok = max(abs(drawn_sides[0] - sides[0]), abs(drawn_sides[1] - sides[1])) < 1e-6
                centre_ok = np.allclose(gq.mean(axis=0),
                                        [(b["xtl"] + b["xbr"]) / 2, (b["ytl"] + b["ybr"]) / 2])
                ang = math.radians(b["rot"])
                aabb_w = abs((b["xbr"] - b["xtl"]) * math.cos(ang)) + abs((b["ybr"] - b["ytl"]) * math.sin(ang))
                aabb_h = abs((b["xbr"] - b["xtl"]) * math.sin(ang)) + abs((b["ybr"] - b["ytl"]) * math.cos(ang))
                ext = gq.max(axis=0) - gq.min(axis=0)
                extent_ok = max(abs(ext[0] - aabb_w), abs(ext[1] - aabb_h)) < 1e-6
                same_as_matrix = float(np.abs(gq - nq).max()) < 1e-6
                checks["geometry"].append(bool(area_ok and side_ok and centre_ok and extent_ok
                                               and same_as_matrix))

                # panel-space quad and source-space quad
                pq = np.column_stack([(gq[:, 0] - crop["x0"]) * scale,
                                      (gq[:, 1] - crop["y0"]) * scale])
                panel_quads.append(pq + np.array([ox, oy]))
                source_quads.append(gq)

                # 3. raster: a corner of this class must exist at each expected corner
                cmask = colour_masks[b["code"]]
                corner_hits = 0
                for cx, cy in pq:
                    x0 = int(max(0, round(cx) - (line_px + 1)))
                    x1 = int(min(pw, round(cx) + (line_px + 2)))
                    y0 = int(max(0, round(cy) - (line_px + 1)))
                    y1 = int(min(ph, round(cy) + (line_px + 2)))
                    if x1 > x0 and y1 > y0 and cmask[y0:y1, x0:x1].any():
                        corner_hits += 1
                inside = bool(((pq[:, 0] >= -1) & (pq[:, 0] <= pw + 1)
                               & (pq[:, 1] >= -1) & (pq[:, 1] <= ph + 1)).all())
                checks["raster"].append(corner_hits == 4 and inside)

                # 4. content: mean grey inside the box, panel vs source.
                # Below ~14 px the drawn outline is wider than the box itself,
                # so there is no clean interior left to compare at this scale.
                short_px = min(np.linalg.norm(pq[1] - pq[0]), np.linalg.norm(pq[3] - pq[0]))
                if short_px < 14:
                    content_state = "n/a (too small at this scale)"
                    diff = None
                    pmv = smv = None
                else:
                    inner = shrink(pq, 0.55)
                    pm, poff = mask_at(panel_px, inner)
                    sm, soff = mask_at(source, shrink(gq, 0.55))
                    pmv = panel_px[poff[1]:poff[1] + pm.shape[0],
                                   poff[0]:poff[0] + pm.shape[1]][pm].mean() if pm is not None else None
                    smv = source[soff[1]:soff[1] + sm.shape[0],
                                 soff[0]:soff[0] + sm.shape[1]][sm].mean() if sm is not None else None
                    diff = abs(float(pmv) - float(smv)) if pmv is not None and smv is not None else 999.0
                    content_state = "ok" if diff <= GREY_TOL else "mismatch"
                    checks["content"].append(content_state == "ok")

                rows.append({
                    "record": base, "class": names.get(b["code"], b["code"]),
                    "code": b["code"], "rotation": b["rot"],
                    "xtl": b["xtl"], "ytl": b["ytl"], "xbr": b["xbr"], "ybr": b["ybr"],
                    "corners_in_panel": inside, "corner_hits": corner_hits,
                    "panel_grey": None if pmv is None else round(float(pmv), 2),
                    "source_grey": None if smv is None else round(float(smv), 2),
                    "grey_diff": None if diff is None else round(diff, 2),
                    "content": content_state,
                })

            # stray colour: every pixel of a class colour must lie on an annotated edge
            for code in codes:
                quads = [np.array(draw.corners(b)) for b in rec["boxes"] if b["code"] == code]
                pqs = [np.column_stack([(q[:, 0] - crop["x0"]) * scale,
                                        (q[:, 1] - crop["y0"]) * scale]) for q in quads]
                ys, xs = np.nonzero(colour_masks[code])
                stray, worst = 0, 0.0
                if len(xs):
                    dist = np.full(len(xs), 1e9)
                    for q in pqs:
                        for i in range(4):
                            dist = np.minimum(dist, seg_distance(xs.astype(float), ys.astype(float),
                                                                 q[i], q[(i + 1) % 4]))
                    # a 3 px outline plus mitred corners reaches ~line_px + 2 px
                    worst = float(dist.max())
                    stray = int((dist > line_px + 2).sum())
                blobs = count_blobs(colour_masks[code])
                checks.setdefault("stray", []).append(stray == 0)
                rows.append({"record": base, "class": names.get(code, code), "code": code,
                             "edges_ok": stray == 0, "stray_px": stray,
                             "worst_dist_px": round(worst, 2),
                             "blobs": blobs, "boxes": len(quads)})
                if blobs != len(quads):
                    rows[-1]["note"] = "blobs do not equal box count (boxes may touch)"

    summary = {k: {"passed": int(sum(v)), "total": len(v)} for k, v in checks.items() if v}
    summary["content_not_measured"] = sum(
        1 for r in rows if str(r.get("content", "")).startswith("n/a"))
    summary["all_passed"] = all(sum(v) == len(v) for v in checks.values() if v)

    out_json = RUN / "verify.json"
    out_json.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    with (RUN / "verify_boxes.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader()
        w.writerows(rows)

    print(json.dumps(summary, indent=1))
    bad = [r for r in rows
           if r.get("corner_hits", 4) != 4
           or r.get("content") == "mismatch"
           or r.get("edges_ok") is False]
    for r in bad[:12]:
        print("needs a look:", r)
    print(out_json)


if __name__ == "__main__":
    main()
