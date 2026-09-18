#!/usr/bin/env python3
"""Verify cut-paste labels against the pixels they claim to describe.

The label files are only useful if they bracket the defect that was actually
pasted. This checker does not trust the writer: it recovers the pasted region
from the images themselves and compares it with the emitted boxes.

    pasted = |05_reinsert_jittered_pos.png - 03_inpainted.png| > threshold

`recall`    = share of changed pixels that fall inside the emitted boxes
`fill`      = share of emitted box area that is changed pixels (feathering and
              the box-vs-mask difference keep this below 1.0 by design; a value
              near zero means the label is somewhere else entirely)

Also writes a visual overlay (changed pixels outlined, emitted boxes drawn) to
<out>/label_check/, so a disagreement can be looked at rather than argued about.

USAGE
    python experiments/augmentation/check_labels.py --out run/augment/preview_20260915
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

AABB = "labels_yolo_aabb.txt"


def read_aabb(path: Path, w: int, h: int) -> list[tuple[int, int, int, int, int]]:
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text().strip().splitlines():
        if not line.strip():
            continue
        cls, xc, yc, bw, bh = line.split()
        xc, yc, bw, bh = float(xc) * w, float(yc) * h, float(bw) * w, float(bh) * h
        boxes.append((int(cls), int(round(xc - bw / 2)), int(round(yc - bh / 2)),
                      int(round(xc + bw / 2)), int(round(yc + bh / 2))))
    return boxes


def box_poly(box: dict, dilate: float, dx: int = 0, dy: int = 0) -> np.ndarray:
    """Rotated box polygon (cv2 convention, verified identical to our CVAT math)."""
    w = (box["xbr"] - box["xtl"]) * (1.0 + dilate)
    h = (box["ybr"] - box["ytl"]) * (1.0 + dilate)
    cx = (box["xtl"] + box["xbr"]) / 2.0 + dx
    cy = (box["ytl"] + box["ybr"]) / 2.0 + dy
    return cv2.boxPoints(((cx, cy), (w, h), box["rotation"])).astype(np.int32)


def junction_metric(a03: np.ndarray, b05: np.ndarray, meta: dict) -> dict | None:
    """Brightness step across the pasted region's own boundary.

    The patch is the DILATED mask, so the visible junction is the mask boundary,
    which sits inside the patch rectangle. A border metric on the rectangle can
    therefore read clean while a tone step is still visible where the pasted
    background meets the background it landed on.
    """
    h, w = b05.shape[:2]
    d = float((meta.get("paste_region") or {}).get("dilate", 0.25))
    rdx, rdy = meta.get("jitter_realized") or (0, 0)
    mask = np.zeros((h, w), np.uint8)
    for bx in meta.get("source_boxes", []):
        cv2.fillConvexPoly(mask, box_poly(bx, d, rdx, rdy), 255)
    if cv2.countNonZero(mask) == 0:
        return None
    k3 = np.ones((3, 3), np.uint8)
    inside = cv2.bitwise_and(mask, cv2.bitwise_not(cv2.erode(mask, k3, iterations=2)))
    outside = cv2.bitwise_and(cv2.dilate(mask, k3, iterations=4),
                              cv2.bitwise_not(cv2.dilate(mask, k3, iterations=1)))
    if cv2.countNonZero(inside) < 8 or cv2.countNonZero(outside) < 8:
        return None
    ring = a03[outside > 0].astype(np.float32)
    step = abs(float(b05[inside > 0].mean()) - float(ring.mean()))
    noise = float(np.std(ring))
    return {"step_grey": round(step, 3), "local_noise_sd": round(noise, 3),
            "step_over_noise": round(step / noise, 2) if noise > 0 else None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--diff-threshold", type=int, default=2)
    ap.add_argument("--zoom", type=int, default=0,
                    help="also write a full-resolution crop around the paste region, "
                         "magnified by this factor, for judging seams and feathering")
    args = ap.parse_args()

    rows, checked = [], 0
    for lab in sorted(args.out.glob("*/*/" + AABB)):
        stem_dir = lab.parent
        p03 = stem_dir / "03_inpainted.png"
        p05 = stem_dir / "05_reinsert_jittered_pos.png"
        if not (p03.exists() and p05.exists()):
            continue
        a = cv2.imread(str(p03), cv2.IMREAD_GRAYSCALE)
        b = cv2.imread(str(p05), cv2.IMREAD_GRAYSCALE)
        h, w = b.shape[:2]
        diff = (cv2.absdiff(a, b) > args.diff_threshold).astype(np.uint8)
        boxes = read_aabb(lab, w, h)

        # seam metric: the patch rectangle border must be invisible. The feather
        # needs room to decay inside the patch, so a 1-2 px border ring with a
        # non-zero step means the alpha was truncated at the rectangle edge.
        seam = None
        junction = None
        lab_json = stem_dir / "labels.json"
        if lab_json.exists():
            meta = json.loads(lab_json.read_text())
            junction = junction_metric(a, b, meta)
            pr = (meta.get("paste_region") or {})
            if pr.get("x") is not None:
                px, py, pw, ph = int(pr["x"]), int(pr["y"]), int(pr["w"]), int(pr["h"])
                x0, y0 = max(px - 1, 0), max(py - 1, 0)
                x1, y1 = min(px + pw + 1, w), min(py + ph + 1, h)
                raw = cv2.absdiff(a, b).astype(np.int16)
                ring = np.zeros_like(raw)
                ring[y0:y1, x0:x1] = 1
                ring[max(py + 1, 0):max(py + ph - 1, 0), max(px + 1, 0):max(px + pw - 1, 0)] = 0
                vals = raw[ring > 0]
                if vals.size:
                    seam = {"mean_abs_step": round(float(vals.mean()), 4),
                            "max_abs_step": int(vals.max()),
                            "p99_abs_step": int(np.percentile(vals, 99))}
        union = np.zeros_like(diff)
        for _c, x0, y0, x1, y1 in boxes:
            union[max(y0, 0):y1, max(x0, 0):x1] = 1
        dpx = int(diff.sum())
        inside = int((diff & union).sum())
        bpx = int(union.sum())
        recall = inside / dpx if dpx else 0.0
        fill = inside / bpx if bpx else 0.0
        rows.append((stem_dir.parent.name, stem_dir.name, len(boxes), dpx, bpx, recall, fill, seam, junction))
        checked += 1

        vis = cv2.cvtColor(b, cv2.COLOR_GRAY2BGR)
        cnts, _ = cv2.findContours(diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, (255, 0, 0), 3)
        for i, (_c, x0, y0, x1, y1) in enumerate(boxes):
            cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 2)
        vis = cv2.resize(vis, None, fx=0.35, fy=0.35, interpolation=cv2.INTER_AREA)
        cv2.putText(vis, f"recall(in-box)={recall:.3f}", (12, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)
        outdir = args.out / "label_check"
        outdir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(outdir / f"{stem_dir.parent.name}_{stem_dir.name}.jpg"), vis,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])

        if args.zoom:
            lab_json = stem_dir / "labels.json"
            if lab_json.exists():
                meta = json.loads(lab_json.read_text())
                pr = meta.get("paste_region") or {}
                if pr.get("x") is not None:
                    pad = 45
                    x0 = max(int(pr["x"]) - pad, 0)
                    y0 = max(int(pr["y"]) - pad, 0)
                    x1 = min(int(pr["x"]) + int(pr["w"]) + pad, w)
                    y1 = min(int(pr["y"]) + int(pr["h"]) + pad, h)
                    # Two panels at the DESTINATION, so the comparison isolates the
                    # paste: the rebuilt background just before pasting, and the same
                    # area after. Comparing `original` against `pasted` instead mixes
                    # the removal (a bright inpainted footprint carrying the straight
                    # edges of the annotation box) into a judgement about the paste,
                    # which is exactly how that comparison misleads.
                    a03 = cv2.imread(str(p03), cv2.IMREAD_GRAYSCALE)
                    panels = []
                    for src_img, title in ((a03, "before paste"), (b, "after paste")):
                        crop = src_img[y0:y1, x0:x1].copy()
                        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
                        for bx in meta.get("boxes", []):
                            pts = cv2.boxPoints(((float(bx["xtl"] + bx["xbr"]) / 2,
                                                  float(bx["ytl"] + bx["ybr"]) / 2),
                                                 (bx["xbr"] - bx["xtl"], bx["ybr"] - bx["ytl"]),
                                                 bx["rotation"]))
                            pts = (pts - [x0, y0]).astype(np.int32)
                            cv2.polylines(crop, [pts], True, (0, 255, 0), 1)
                        crop = cv2.resize(crop, None, fx=args.zoom, fy=args.zoom,
                                          interpolation=cv2.INTER_NEAREST)
                        cv2.putText(crop, title, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                                    (0, 255, 255), 2, cv2.LINE_AA)
                        panels.append(crop)
                    gap = np.full((panels[0].shape[0], 8, 3), 255, np.uint8)
                    cv2.imwrite(str(outdir / f"zoom_{stem_dir.parent.name}_{stem_dir.name}.jpg"),
                                np.hstack([panels[0], gap, panels[1]]),
                                [cv2.IMWRITE_JPEG_QUALITY, 92])

    if not checked:
        print(f"no labelled samples found under {args.out}")
        return 1

    rec = [r for r in rows if r[5] > 0]
    print(f"samples checked        : {checked}")
    print(f"recall (changed px in emitted boxes): min {min(r[5] for r in rows):.3f}  "
          f"median {np.median([r[5] for r in rows]):.3f}")
    print(f"fill   (box area that changed)      : min {min(r[6] for r in rows):.3f}  "
          f"median {np.median([r[6] for r in rows]):.3f}")
    sm = [r[7] for r in rows if r[7]]
    if sm:
        print(f"patch border step (0 = invisible)   : median mean {np.median([s['mean_abs_step'] for s in sm]):.3f}  "
              f"worst mean {max(s['mean_abs_step'] for s in sm):.3f}  "
              f"worst max {max(s['max_abs_step'] for s in sm)}")
    jm = [r[8] for r in rows if r[8]]
    if jm:
        son = [j["step_over_noise"] for j in jm if j["step_over_noise"] is not None]
        print(f"paste junction step (grey levels)   : median {np.median([j['step_grey'] for j in jm]):.2f}  "
              f"worst {max(j['step_grey'] for j in jm):.2f}  |  "
              f"step/noise median {np.median(son):.2f}  worst {max(son):.2f}  "
              f"(>1 means the junction stands out from the surface texture)")
    bad = sorted(rows, key=lambda r: r[5])[:5]
    print("\nlowest recall:")
    for c, s, nb, dpx, bpx, rc, fl, _seam, _jm in bad:
        print(f"  {rc:.3f}  {c:<20} {s[:34]:<36} boxes={nb:<3} changed_px={dpx}")
    worst_seam = sorted([r for r in rows if r[7]], key=lambda r: -r[7]["mean_abs_step"])[:4]
    if worst_seam:
        print("\nhighest patch border step:")
        for c, s, nb, dpx, bpx, rc, fl, seam, _jm in worst_seam:
            print(f"  mean={seam['mean_abs_step']:<7} max={seam['max_abs_step']:<4} "
                  f"{c:<20} {s[:34]}")
    worst_j = sorted([r for r in rows if r[8]], key=lambda r: -r[8]["step_grey"])[:5]
    if worst_j:
        print("\nhighest paste junction step:")
        for c, s, nb, dpx, bpx, rc, fl, _seam, jm_i in worst_j:
            print(f"  step={jm_i['step_grey']:<7} noise_sd={jm_i['local_noise_sd']:<6} "
                  f"ratio={jm_i['step_over_noise']:<6} {c:<18} {s[:30]}")
    (args.out / "label_check" / "label_check.json").write_text(json.dumps(
        [{"class": r[0], "stem": r[1], "boxes": r[2], "changed_px": r[3],
          "box_px": r[4], "recall": round(r[5], 4), "fill": round(r[6], 4),
          "patch_border_step": r[7], "paste_junction": r[8]} for r in rows], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
