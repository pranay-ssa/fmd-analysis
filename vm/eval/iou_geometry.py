#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Torch-free OBB geometry: polygon IoU (Sutherland-Hodgman + shoelace), GT parsing,
greedy one-to-one class-aware matching. Shared by vm/iou_eval.py and local sanity tests.
"""
import numpy as np


def poly_area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def cross2(u, v):
    """2D cross product u x v (numpy 2.x np.cross requires 3D vectors)."""
    return u[0] * v[1] - u[1] * v[0]


def clip_poly(subject, clip):
    """Sutherland-Hodgman clip of convex subject polygon by convex clip polygon."""
    out = subject
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        edge = b - a
        def inside(p):
            return cross2(edge, p - a) >= 0
        inp = out
        out = []
        if len(inp) == 0:
            break
        s = inp[-1]
        for e in inp:
            denom = cross2(edge, s - e)
            if inside(e):
                if not inside(s):
                    if denom != 0:
                        t = s + (e - s) * cross2(edge, s - a) / denom
                    else:
                        t = e
                    out.append(t)
                out.append(e)
            elif inside(s):
                if denom != 0:
                    t = s + (e - s) * cross2(edge, s - a) / denom
                else:
                    t = s
                out.append(t)
            s = e
    return np.array(out) if len(out) >= 3 else None


def poly_iou(p, q):
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    ap, aq = poly_area(p), poly_area(q)
    if ap <= 0 or aq <= 0:
        return 0.0
    inter = clip_poly(p, q)
    if inter is None:
        return 0.0
    ai = poly_area(inter)
    return ai / (ap + aq - ai + 1e-12)


def parse_gt(path, w, h):
    """YOLO-OBB label line: cls x1 y1 x2 y2 x3 y3 x4 y4, normalized, CW from top-left."""
    boxes = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 9:
            continue
        c = int(parts[0])
        pts = np.array([[float(parts[i]) * w, float(parts[i + 1]) * h]
                        for i in range(1, 9, 2)])
        boxes.append((c, pts))
    return boxes


def greedy_match(preds, gts):
    """preds: (cls, pts, conf); gts: (cls, pts). Greedy one-to-one, same class."""
    matches = []
    used_gt = set()
    for pcls, ppts, pconf in sorted(preds, key=lambda x: -x[2]):
        best_iou, best_gi = 0.0, -1
        for gi, (gcls, gpts) in enumerate(gts):
            if gi in used_gt or gcls != pcls:
                continue
            iou = poly_iou(ppts, gpts)
            if iou > best_iou:
                best_iou, best_gi = iou, gi
        if best_gi >= 0 and best_iou > 0:
            used_gt.add(best_gi)
            matches.append((best_iou, pcls))
    return matches
