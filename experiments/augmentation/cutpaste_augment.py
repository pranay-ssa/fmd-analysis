#!/usr/bin/env python3
"""Cut-paste defect augmentation on the local defect library.

Offline twin of the teammate's VM preview script
(`vm/teammates/augment_srikanth.py`), running against the local copy of the
library (`data/incoming/`) and `data/annotations.xml`, so the idea can be
tested and tuned here before anything runs on the VM.

Implements the 5 steps end to end:

    1. select the image        deterministic sample per class (seed)
    2. mark the defect region  CVAT rotated box (xtl,ytl,xbr,ybr,rotation) -> filled mask
    3. remove the defect       mask blacked out
    4. inpaint the region      cv2.inpaint, Telea (classical; no learned inpainter)
    5. reinsert the defect     feathered paste: original position (sanity check)
                               and jittered position (the actual new sample)

Deliberate differences from the teammate's preview, all recorded in
`experiments/augmentation/README.md`:

  * labels are emitted (`labels.json`, `labels_yolo_obb.txt`,
    `labels_yolo_aabb.txt`) so the output can feed a detector, not just an eye
  * every annotated box can be pasted (`--paste all`), not only the largest
  * the sampling stream is shared with the Part-A style universal augmentations,
    so all variants of one source image live in one folder
  * the gate is evaluated on the largest single defect, not on the union mask,
    so a frame with many small defects is not rejected for their total area
  * the realized paste offset is recorded after frame clipping, so labels and
    manifest always agree with the pixels
  * a QA contact sheet per class, for inspection without opening 1000 PNGs

USAGE
    python experiments/augmentation/cutpaste_augment.py \
        --library data/incoming --annot data/annotations.xml \
        --out run/augment/preview_20260915 \
        --classes Bubble "Bubble On 123" Fiber --per-class 3 \
        --paste all --emit-labels

    # geometry self-check only (compares our CVAT-verified corner math against
    # cv2.boxPoints on every annotated box; both must give the same mask)
    python experiments/augmentation/cutpaste_augment.py --selftest

OUTPUT (under --out)
    manifest.csv              one row per written file
    summary.json              parameters, per-class counts, skip reasons
    <class>/<stem>/           01_mark.png 02_removed.png 03_inpainted.png
                              04_reinsert_original_pos.png 05_reinsert_jittered_pos.png
                              original.png + labels.json + labels_yolo_*.txt (--emit-labels)
    sheets/<class>.jpg        QA contact sheet of the 5 steps (first processed sample)
    classes.txt               class index order used by labels_yolo_*.txt
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "yolo_ooi"))

# Reuse the repo's visually verified CVAT rotation convention rather than
# re-deriving it: see src/yolo_ooi/common.py docstring (confirmed 2026-09-07).
from common import obb_corners_self_checked  # noqa: E402

IMG_EXTS = (".bmp", ".png", ".jpg", ".jpeg", ".tif", ".tiff")
DEFAULT_GATE = 0.02          # dilated defect area / image area, above which Telea smears
DEFAULT_JITTER = 0.08        # fraction of image width/height
DEFAULT_DILATE = 0.25        # dilation of the box in rect space, before masking
INPAINT_RADIUS = 7
FEATHER_K_MAX = 7
FEATHER_K_MIN = 3


def feather_kernel(min_side_px: float) -> int:
    """Feather kernel for a defect of this size, always odd.

    A fixed 7 px kernel is wider than a 5 px bubble, so the blend thins the defect
    instead of just softening its border: measured opacity at the core was 0.924
    median / 0.540 worst for defects up to 5 px, against 0.999 for defects over
    11 px (measure_paste_fidelity.py). Scaling the kernel with the defect keeps
    the ratio between feather and defect roughly constant, so a small defect keeps
    its contrast while a large one still gets a soft edge.
    """
    k = 2 * int(round(0.3 * min_side_px)) + 1
    return int(max(FEATHER_K_MIN, min(FEATHER_K_MAX, k)))


# --------------------------------------------------------------------------- #
# annotations
# --------------------------------------------------------------------------- #
def load_annotations(xml_path: Path) -> dict[str, list[dict]]:
    """Return {image basename: [box dicts]} for every image with at least one box."""
    root = ET.parse(xml_path).getroot()
    by_name: dict[str, list[dict]] = {}
    for im in root.findall("image"):
        boxes = []
        for b in im.findall("box"):
            a = b.attrib
            boxes.append({
                "label": a["label"],
                "xtl": float(a["xtl"]), "ytl": float(a["ytl"]),
                "xbr": float(a["xbr"]), "ybr": float(a["ybr"]),
                "rotation": float(a.get("rotation", 0.0)),
            })
        if boxes:
            by_name[os.path.basename(im.attrib["name"])] = boxes
    return by_name


def box_corners(box: dict, dilate: float) -> np.ndarray:
    """Dilated rotated box as 4 corners, using the repo's CVAT convention."""
    w = (box["xbr"] - box["xtl"]) * (1.0 + dilate)
    h = (box["ybr"] - box["ytl"]) * (1.0 + dilate)
    cx = (box["xtl"] + box["xbr"]) / 2.0
    cy = (box["ytl"] + box["ybr"]) / 2.0
    corners, _ok = obb_corners_self_checked(cx - w / 2, cy - h / 2,
                                            cx + w / 2, cy + h / 2,
                                            box["rotation"])
    return np.asarray(corners, dtype=np.float32)


def mask_from_boxes(shape, boxes, dilate: float) -> np.ndarray:
    """Union of the filled rotated boxes, as a uint8 {0,255} mask."""
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for b in boxes:
        cv2.fillConvexPoly(mask, box_corners(b, dilate).astype(np.int32), 255)
    return mask


def single_mask_area_frac(shape, box, dilate: float, scratch: np.ndarray | None = None) -> float:
    """Dilated area of ONE defect as a fraction of the frame.

    Uses a real mask rasterisation (not a polygon area) so a box hanging over the
    frame edge is clipped exactly like the removal mask will be.
    """
    h, w = shape[:2]
    m = scratch if scratch is not None else np.zeros((h, w), np.uint8)
    m[:] = 0
    cv2.fillConvexPoly(m, box_corners(box, dilate).astype(np.int32), 255)
    return cv2.countNonZero(m) / float(h * w)


# --------------------------------------------------------------------------- #
# the 5 steps
# --------------------------------------------------------------------------- #
def feather_alpha(mask: np.ndarray, k: int) -> np.ndarray:
    return cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (k, k), 0)


def paste(bg: np.ndarray, patch: np.ndarray, alpha: np.ndarray,
          x: int, y: int) -> tuple[np.ndarray, int, int]:
    """Alpha-paste `patch` so its top-left lands at (x, y), clipped to the frame.

    Returns (image, placed_x, placed_y). The caller turns the placement into an
    offset against the ORIGINAL placement, so labels describe where the pixels
    actually went even when clipping shifted the paste.
    """
    H, W = bg.shape[:2]
    ph, pw = patch.shape[:2]
    x1 = int(np.clip(x, 0, W - pw))
    y1 = int(np.clip(y, 0, H - ph))
    out = bg.copy()
    roi = out[y1:y1 + ph, x1:x1 + pw].astype(np.float32)
    out[y1:y1 + ph, x1:x1 + pw] = (alpha * patch.astype(np.float32) + (1 - alpha) * roi).astype(np.uint8)
    return out, x1, y1


def process_image(img: np.ndarray, boxes: list[dict], args, rng: random.Random,
                  out_dir: Path) -> dict:
    """Run steps 2-5 for one image. Returns a per-image record."""
    H, W = img.shape[:2]
    out_dir.mkdir(parents=True, exist_ok=True)
    rec: dict = {"boxes": len(boxes), "gate_skipped": False, "files": {}}

    def save(name: str, array: np.ndarray) -> None:
        p = out_dir / name
        cv2.imwrite(str(p), array)
        rec["files"][name] = str(p)

    save("original.png", img)

    # 2. mark
    mask = mask_from_boxes(img.shape, boxes, args.dilate)
    overlay = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    overlay[mask > 0] = (0, 0, 255)
    overlay = cv2.addWeighted(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), 0.6, overlay, 0.4, 0)
    save("01_mark.png", overlay)

    # gate: largest single defect after dilation, not the union of all defects
    scratch = np.zeros(img.shape[:2], np.uint8)
    frac_max = max(single_mask_area_frac(img.shape, b, args.dilate, scratch) for b in boxes)
    rec["dilated_area_frac_max"] = round(frac_max, 5)
    if frac_max > args.gate:
        rec["gate_skipped"] = True
        rec["note"] = (f"largest defect covers {frac_max * 100:.2f}% of the image after "
                       f"{int(args.dilate * 100)}% dilation (> {args.gate * 100:.1f}% gate): "
                       f"classical Telea inpainting smears at this size")
        return rec

    # 3. remove
    removed = img.copy()
    removed[mask > 0] = 0
    save("02_removed.png", removed)

    # 4. inpaint
    inpainted = cv2.inpaint(img, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)
    save("03_inpainted.png", inpainted)

    # 5. reinsert: one patch carrying the whole defect layout, so relative
    # positions of multiple defects survive the paste.
    # The pad must exceed the feather's support (kernel//2, now size-aware),
    # otherwise the alpha is truncated at the patch rectangle and a visible
    # rectangular step is left around the pasted defect. Verified by measurement:
    # check_labels.py "patch border step" reported worst max 21 grey levels when
    # the pad was 2 px against a 7 px kernel, and 0 at every border with this pad.
    xs = [box_corners(b, args.dilate) for b in boxes]
    k = feather_kernel(min(min(b["xbr"] - b["xtl"], b["ybr"] - b["ytl"]) for b in boxes))
    pad = k // 2 + 2
    rec["feather_k"] = k
    x0 = int(np.clip(min(p[:, 0].min() for p in xs) - pad, 0, W - 1))
    y0 = int(np.clip(min(p[:, 1].min() for p in xs) - pad, 0, H - 1))
    x1 = int(np.clip(max(p[:, 0].max() for p in xs) + pad + 1, 1, W))
    y1 = int(np.clip(max(p[:, 1].max() for p in xs) + pad + 1, 1, H))
    patch = img[y0:y1, x0:x1]
    if patch.shape[0] < 3 or patch.shape[1] < 3:
        rec["note"] = "degenerate patch extent, skipped"
        return rec
    alpha = feather_alpha(mask[y0:y1, x0:x1], k)

    # 5a. original position: reproduces the source, a reconstruction sanity check
    same, _, _ = paste(inpainted, patch, alpha, x0, y0)
    save("04_reinsert_original_pos.png", same)
    rec["reconstruction_max_abs_diff"] = int(np.abs(same.astype(np.int16) - img.astype(np.int16))[mask > 0].max())

    # 5b. jittered position: the new sample.
    # The offset is drawn so the pasted defect does not land on the region it was
    # just removed from: with a large defect and a small jitter the two overlap,
    # the "new" sample is close to a translation of the source, and the defect
    # ends up sitting on reconstructed background instead of real lens surface.
    src_mask = mask
    best = None
    for _try in range(args.jitter_tries):
        cdx = int(round(rng.uniform(-args.jitter, args.jitter) * W))
        cdy = int(round(rng.uniform(-args.jitter, args.jitter) * H))
        cjx, cjy = x0 + cdx, y0 + cdy
        px0, py0 = int(np.clip(cjx, 0, W - patch.shape[1])), int(np.clip(cjy, 0, H - patch.shape[0]))
        dest = np.zeros_like(src_mask)
        dest[py0:py0 + patch.shape[0], px0:px0 + patch.shape[1]] = mask[y0:y0 + patch.shape[0], x0:x0 + patch.shape[1]]
        overlap_px = int(cv2.countNonZero(cv2.bitwise_and(dest, src_mask)))
        cand = (overlap_px, cdx, cdy, cjx, cjy)
        if best is None or overlap_px < best[0]:
            best = cand
        if overlap_px == 0:
            break
    overlap_px, dx, dy, cjx, cjy = best
    rec["jitter_tries_used"] = _try + 1
    rec["source_overlap_px"] = overlap_px
    jit, jx, jy = paste(inpainted, patch, alpha, cjx, cjy)
    save("05_reinsert_jittered_pos.png", jit)
    # offset the pixels really moved by: the placed origin minus the original one
    rdx, rdy = jx - x0, jy - y0
    rec["jitter_requested"] = [dx, dy]
    rec["jitter_realized"] = [rdx, rdy]
    rec["paste_region"] = {"x": jx, "y": jy, "w": int(patch.shape[1]), "h": int(patch.shape[0]),
                           "dilate": args.dilate,
                           "note": ("the changed region is the box dilated by --dilate, so it is "
                                    "wider than the emitted labels by design")}
    # the pasted defects are the source boxes translated by the REALIZED offset
    rec["boxes_pasted"] = [{"label": b["label"],
                            "xtl": b["xtl"] + rdx,
                            "ytl": b["ytl"] + rdy,
                            "xbr": b["xbr"] + rdx,
                            "ybr": b["ybr"] + rdy,
                            "rotation": b["rotation"]} for b in boxes]
    return rec


# --------------------------------------------------------------------------- #
# labels
# --------------------------------------------------------------------------- #
def write_labels(out_dir: Path, img: np.ndarray, rec: dict, class_idx: int) -> None:
    H, W = img.shape[:2]
    pasted = rec.get("boxes_pasted", [])
    (out_dir / "labels.json").write_text(json.dumps({
        "image": "05_reinsert_jittered_pos.png",
        "width": W, "height": H,
        "class_index": class_idx,
        "class_labels": [b["label"] for b in pasted],
        "boxes": pasted,
        "source_boxes": rec.get("source_boxes", []),
        "jitter_realized": rec.get("jitter_realized"),
        "source_overlap_px": rec.get("source_overlap_px"),
        "feather_k": rec.get("feather_k"),
        "paste_region": rec.get("paste_region"),
        "note": ("Source region is inpainted in the pasted image, so the source boxes "
                 "are NOT valid labels for 05; only `boxes` are."),
    }, indent=2))

    obb, aabb = [], []
    for b in pasted:
        c, ok = obb_corners_self_checked(b["xtl"], b["ytl"], b["xbr"], b["ybr"], b["rotation"])
        c = np.asarray(c, dtype=float)
        if not ok:
            continue
        obb.append("{} ".format(class_idx) + " ".join(
            f"{v:.6f}" for v in np.column_stack([c[:, 0] / W, c[:, 1] / H]).ravel()))
        x0, y0 = max(c[:, 0].min(), 0), max(c[:, 1].min(), 0)
        x1, y1 = min(c[:, 0].max(), W - 1), min(c[:, 1].max(), H - 1)
        if x1 <= x0 or y1 <= y0:
            continue
        aabb.append(f"{class_idx} {((x0 + x1) / 2) / W:.6f} {((y0 + y1) / 2) / H:.6f} "
                    f"{(x1 - x0) / W:.6f} {(y1 - y0) / H:.6f}")
    (out_dir / "labels_yolo_obb.txt").write_text("\n".join(obb) + ("\n" if obb else ""))
    (out_dir / "labels_yolo_aabb.txt").write_text("\n".join(aabb) + ("\n" if aabb else ""))


# --------------------------------------------------------------------------- #
# QA sheet
# --------------------------------------------------------------------------- #
def contact_sheet(files: list[Path], out_path: Path, scale=0.30) -> bool:
    panels = []
    for p in files:
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if im is None:
            continue
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        cv2.putText(im, p.stem.split("_", 1)[-1][:22], (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
        panels.append(im)
    if not panels:
        return False
    h = min(p.shape[0] for p in panels)
    w = min(p.shape[1] for p in panels)
    row = np.hstack([p[:h, :w] for p in panels])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), row, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return True


# --------------------------------------------------------------------------- #
# self-test: our corner math vs cv2.boxPoints
# --------------------------------------------------------------------------- #
def selftest(annot: Path) -> int:
    by_name = load_annotations(annot)
    boxes = [(n, b) for n, bs in by_name.items() for b in bs]
    worst = 1.0
    worst_box = None
    for name, b in boxes:
        w = b["xbr"] - b["xtl"]
        h = b["ybr"] - b["ytl"]
        cx = (b["xtl"] + b["xbr"]) / 2.0
        cy = (b["ytl"] + b["ybr"]) / 2.0
        ours = box_corners(b, 0.0)
        theirs = np.asarray(cv2.boxPoints(((cx, cy), (w, h), b["rotation"])), dtype=np.float32)
        pad = 4
        xs = np.vstack([ours, theirs])
        W = int(xs[:, 0].max() - xs[:, 0].min()) + 2 * pad + 1
        H = int(xs[:, 1].max() - xs[:, 1].min()) + 2 * pad + 1
        ox, oy = xs[:, 0].min() - pad, xs[:, 1].min() - pad
        m1 = np.zeros((H, W), np.uint8)
        m2 = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(m1, (ours - [ox, oy]).astype(np.int32), 255)
        cv2.fillConvexPoly(m2, (theirs - [ox, oy]).astype(np.int32), 255)
        inter = cv2.countNonZero(cv2.bitwise_and(m1, m2))
        union = cv2.countNonZero(cv2.bitwise_or(m1, m2))
        iou = inter / union if union else 1.0
        if iou < worst:
            worst, worst_box = iou, (name, b)
    print(f"boxes checked          : {len(boxes)}")
    print(f"worst mask IoU vs cv2  : {worst:.6f}")
    if worst_box and worst < 0.999:
        print(f"worst box              : {worst_box[0]} rotation={worst_box[1]['rotation']}")
    print("PASS: our corner math and cv2.boxPoints agree" if worst > 0.99 else "FAIL")
    return 0 if worst > 0.99 else 1


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--library", type=Path, default=REPO / "data" / "incoming")
    ap.add_argument("--annot", type=Path, default=REPO / "data" / "annotations.xml")
    ap.add_argument("--out", type=Path, default=None,
                    help="output folder (default run/augment/preview_<YYYYMMDD>)")
    ap.add_argument("--classes", nargs="+", default=None,
                    help="classes to process (default: every class with boxes)")
    ap.add_argument("--per-class", type=int, default=4, help="source images sampled per class")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gate", type=float, default=DEFAULT_GATE)
    ap.add_argument("--jitter", type=float, default=DEFAULT_JITTER)
    ap.add_argument("--jitter-tries", type=int, default=12,
                    help="redraws attempted to keep the pasted defect off its own source region")
    ap.add_argument("--dilate", type=float, default=DEFAULT_DILATE)
    ap.add_argument("--paste", choices=["largest", "all"], default="all")
    ap.add_argument("--emit-labels", action="store_true")
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest(args.annot)
    if args.out is None:
        import datetime
        args.out = REPO / "run" / "augment" / f"preview_{datetime.date.today():%Y%m%d}"

    by_name = load_annotations(args.annot)
    have_boxes = sorted({b["label"] for bs in by_name.values() for b in bs})
    classes = args.classes or have_boxes
    unknown = [c for c in classes if c not in have_boxes]
    if unknown:
        print(f"NOTE: no boxes for {unknown}, nothing to paste; skipping", file=sys.stderr)
        classes = [c for c in classes if c in have_boxes]
    class_idx = {c: i for i, c in enumerate(classes)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "classes.txt").write_text("\n".join(classes) + "\n")

    rows, summary = [], {"params": {"seed": args.seed, "gate": args.gate, "jitter": args.jitter,
                                    "dilate": args.dilate, "paste": args.paste,
                                    "per_class": args.per_class, "inpaint": f"cv2 Telea r={INPAINT_RADIUS}",
                                    "cv2": cv2.__version__, "library": str(args.library),
                                    "annotation_file": str(args.annot)},
                          "classes": {}}

    for cls in classes:
        src_dir = args.library / cls
        files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(IMG_EXTS)) if src_dir.is_dir() else []
        with_boxes = [f for f in files if f in by_name]
        rng_pick = random.Random(f"{args.seed}/{cls}")
        picked = with_boxes if len(with_boxes) <= args.per_class else rng_pick.sample(with_boxes, args.per_class)
        c_rec = {"images_in_class": len(files), "images_with_boxes": len(with_boxes),
                 "sampled": len(picked), "processed": 0, "gate_skipped": 0, "samples": {}}
        sheet_done = False
        for fname in sorted(picked):
            img = cv2.imread(str(src_dir / fname), cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"  ! unreadable: {src_dir / fname}", file=sys.stderr)
                continue
            boxes = by_name[fname] if args.paste == "all" else [
                max(by_name[fname], key=lambda b: (b["xbr"] - b["xtl"]) * (b["ybr"] - b["ytl"]))]
            stem = Path(fname).stem
            rng = random.Random(hashlib.md5(fname.encode()).hexdigest())
            img_out = args.out / cls / stem
            rec = process_image(img, boxes, args, rng, img_out)
            rec["source_boxes"] = boxes
            if args.emit_labels and not rec["gate_skipped"]:
                write_labels(img_out, img, rec, class_idx[cls])
            if rec["gate_skipped"]:
                c_rec["gate_skipped"] += 1
            else:
                c_rec["processed"] += 1
                if not sheet_done and not args.no_sheets:
                    sheet_done = contact_sheet(
                        [Path(rec["files"][k]) for k in
                         ("01_mark.png", "02_removed.png", "03_inpainted.png",
                          "04_reinsert_original_pos.png", "05_reinsert_jittered_pos.png")
                         if k in rec["files"]],
                        args.out / "sheets" / f"{cls}.jpg")
            c_rec["samples"][fname] = rec
            for name, path in rec["files"].items():
                rows.append({"tag_group": "Object of Interest Tag", "class": cls,
                             "source_image": fname, "technique": name,
                             "output_path": os.path.relpath(path, args.out),
                             "box_count": rec["boxes"],
                             "dilated_area_frac_max": rec.get("dilated_area_frac_max", ""),
                             "dx_realized": (rec.get("jitter_realized") or ["", ""])[0],
                             "dy_realized": (rec.get("jitter_realized") or ["", ""])[1],
                             "source_overlap_px": rec.get("source_overlap_px", ""),
                             "note": rec.get("note", "")})
            print(f"  [{cls}] {fname} boxes={rec['boxes']} frac={rec.get('dilated_area_frac_max')}"
                  f"{' SKIPPED(gate)' if rec['gate_skipped'] else ''}")
        summary["classes"][cls] = {k: v for k, v in c_rec.items() if k != "samples"}
        summary["classes"][cls]["samples"] = c_rec["samples"]

    with open(args.out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["class"])
        w.writeheader()
        w.writerows(rows)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))

    tot = sum(c["processed"] for c in summary["classes"].values())
    skip = sum(c["gate_skipped"] for c in summary["classes"].values())
    print(f"\n{args.out}")
    print(f"  source images processed : {tot}")
    print(f"  gate-skipped (mark only): {skip}")
    print(f"  files written           : {len(rows)}")
    print(f"  manifest.csv / summary.json / classes.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
