"""Class-conditional spatial support of the defects, and whether the paste respects it.

The ROI is the lit lens region. It is recovered with the pipeline's own constants
(THRESHOLD 3, blob >= 500 px, blob mean >= 15.0 from src/config.py), and its edge is
taken as the minimum enclosing circle of that blob: centre (cx, cy), radius R.

For every annotated box the script records the gap between the box centre and the ROI
edge, in pixels and as a fraction of R (0.0 = on the edge, 1.0 = at the centre).
That gives each class an empirical spatial envelope, which is what a jitter has to
respect: a class that never comes within 300 px of the edge must not be pasted there.

Then it re-reads a completed preview run and flags every pasted box that sits outside
its own class's historical envelope.

    .venv/Scripts/python.exe experiments/augmentation/roi_support.py \
        --out run/augment/preview_v3 --cache run/augment/roi_circles.json
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from config import MIN_BLOB_MEAN, MIN_BLOB_SIZE, THRESHOLD  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "data" / "incoming"
ANNOT = REPO / "data" / "annotations.xml"


# --------------------------------------------------------------------------- #
# ROI circle per image
# --------------------------------------------------------------------------- #
def roi_circle(path: str) -> tuple[str, float, float, float, float]:
    """Return (name, cx, cy, R, blob_area) for one image.

    Per-blob size and mean come from np.bincount over the label image (the same
    trick preprocess.py uses); indexing a 5 MP boolean mask per blob is far too slow.
    """
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return Path(path).name, -1, -1, -1, 0
    mask = (img > THRESHOLD).astype(np.uint8)
    n, lab = cv2.connectedComponents(mask, connectivity=8)
    if n <= 1:
        return Path(path).name, -1, -1, -1, 0
    flat = lab.ravel()
    counts = np.bincount(flat, minlength=n).astype(np.int64)
    sums = np.bincount(flat, weights=img.ravel().astype(np.float64), minlength=n)
    counts[0] = 0
    means = sums / np.maximum(counts, 1)
    keep = np.where((counts >= MIN_BLOB_SIZE) & (means >= MIN_BLOB_MEAN))[0]
    if not len(keep):
        return Path(path).name, -1, -1, -1, 0
    biggest = int(keep[np.argmax(counts[keep])])
    blob = (lab == biggest).astype(np.uint8)
    cnts, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnts, key=cv2.contourArea)
    (cx, cy), r = cv2.minEnclosingCircle(c)
    return Path(path).name, float(cx), float(cy), float(r), float(counts[biggest])


def load_annotations(path: Path) -> dict:
    import xml.etree.ElementTree as ET

    by_name: dict[str, list[dict]] = {}
    root = ET.parse(path).getroot()
    for im in root.findall("image"):
        name = Path(im.get("name", "")).name
        boxes = []
        for b in im.findall("box"):
            boxes.append({
                "label": b.get("label"),
                "xtl": float(b.get("xtl")), "ytl": float(b.get("ytl")),
                "xbr": float(b.get("xbr")), "ybr": float(b.get("ybr")),
                "rotation": float(b.get("rotation") or 0.0),
            })
        if boxes:
            by_name[name] = boxes
    return by_name


def build_circles(cache: Path, only: set[str] | None = None) -> dict:
    if cache.exists():
        return json.loads(cache.read_text())
    files = sorted(p for p in LIB.rglob("*") if p.suffix.lower() == ".bmp")
    if only:
        files = [f for f in files if f.name in only]
    print(f"resolving ROI circles for {len(files)} images (first run, cached after)", flush=True)
    out: dict[str, list] = {}
    with ProcessPoolExecutor() as ex:
        for i, (name, cx, cy, r, area) in enumerate(ex.map(roi_circle, [str(f) for f in files], chunksize=8)):
            out[name] = [cx, cy, r, area]
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(files)}", flush=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out))
    print(f"wrote {cache}", flush=True)
    return out


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None, help="a completed preview run to check")
    ap.add_argument("--cache", type=Path, default=REPO / "run" / "augment" / "roi_circles.json")
    ap.add_argument("--all-images", action="store_true",
                    help="resolve the circle for every BMP, not only the annotated ones")
    args = ap.parse_args()

    by_name = load_annotations(ANNOT)
    circles = build_circles(args.cache, None if args.all_images else set(by_name))

    # box centre -> (class, gap, u, name)
    rows: list[tuple[str, float, float, str]] = []
    missing = 0
    for name, boxes in by_name.items():
        c = circles.get(name) or circles.get(Path(name).stem + ".bmp")
        if not c or c[0] < 0:
            missing += 1
            continue
        cx, cy, r, _ = c
        for b in boxes:
            bx = (b["xtl"] + b["xbr"]) / 2.0
            by = (b["ytl"] + b["ybr"]) / 2.0
            d = float(np.hypot(bx - cx, by - cy))
            rows.append((b["label"], r - d, 1.0 - d / r if r else 0.0, name))
    print(f"boxes scored {len(rows)}  (images without an ROI circle: {missing})")

    classes = sorted({r[0] for r in rows})
    rs = np.array([v[2] for v in circles.values() if v[0] > 0])
    print(f"ROI radius from the blob's min enclosing circle: median {np.median(rs):.0f} px "
          f"(min {rs.min():.0f}, p95 {np.percentile(rs, 95):.0f}, max {rs.max():.0f})")
    print(f"\nGap from the box centre to the ROI edge, in px. u=1 at the centre, 0 on the edge.\n")
    print(f"{'class':<42}{'n':>4}{'min':>8}{'p05':>8}{'median':>8}{'p95':>8}{'max':>8}{'u<0.05':>8}")
    per_class: dict[str, list[float]] = {}
    for cls in classes:
        gaps = np.array([r[1] for r in rows if r[0] == cls])
        us = np.array([r[2] for r in rows if r[0] == cls])
        per_class[cls] = gaps
        print(f"{cls:<42}{len(gaps):>4}{gaps.min():>8.0f}"
              f"{np.percentile(gaps, 5):>8.0f}{np.median(gaps):>8.0f}"
              f"{np.percentile(gaps, 95):>8.0f}{gaps.max():>8.0f}"
              f"{(us < 0.05).sum():>8}")

    # ---- check a preview run against those envelopes ----------------------- #
    if args.out:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cutpaste_augment import box_corners  # the visually verified CVAT math

        run = REPO / args.out if not args.out.is_absolute() else args.out
        print(f"\nPasted boxes against the class envelope, in {run.name}:")
        print(f"envelope = gap from the box centre to the ROI edge; negative = centre outside the ROI\n")
        print(f"{'class':<20}{'samp':>5}{'boxes':>6}{'min gap':>8}{'cls min':>8}{'cls p05':>8}"
              f"{'<p05':>6}{'<min':>6}{'corner out':>11}{'px out':>8}{'px out %':>10}")
        tot_out = tot_pix = tot_pix_all = 0
        for clsdir in sorted(p for p in run.iterdir() if p.is_dir()):
            samples = [d for d in clsdir.iterdir() if (d / "labels.json").exists()]
            ref = per_class.get(clsdir.name, np.array([]))
            if not len(ref):
                continue
            centres, out_corner, pix_out, pix_tot, nboxes = [], 0, 0, 0, 0
            for s in samples:
                meta = json.loads((s / "labels.json").read_text())
                key = next((k for k in circles if Path(k).stem == s.name), None)
                c = circles.get(key) if key else None
                if not c or c[0] < 0:
                    continue
                cx, cy, r, _ = c
                for b in meta["boxes"]:
                    nboxes += 1
                    bcx = (b["xtl"] + b["xbr"]) / 2.0
                    bcy = (b["ytl"] + b["ybr"]) / 2.0
                    centres.append(r - float(np.hypot(bcx - cx, bcy - cy)))
                    corners = box_corners(b, 0.0)
                    if min(r - float(np.hypot(px - cx, py - cy)) for px, py in corners) < 0:
                        out_corner += 1
                a = cv2.imread(str(s / "03_inpainted.png"), cv2.IMREAD_GRAYSCALE)
                b_ = cv2.imread(str(s / "05_reinsert_jittered_pos.png"), cv2.IMREAD_GRAYSCALE)
                if a is None or b_ is None:
                    continue
                mask = np.abs(b_.astype(np.int16) - a.astype(np.int16)) > 2
                yy, xx = np.where(mask)
                d = np.hypot(xx - cx, yy - cy)
                pix_out += int((d > r).sum())
                pix_tot += int(mask.sum())
            if not centres:
                continue
            g = np.array(centres)
            lo, p05 = ref.min(), np.percentile(ref, 5)
            tot_out += out_corner
            tot_pix += pix_out
            tot_pix_all += pix_tot
            print(f"{clsdir.name:<20}{len(samples):>5}{nboxes:>6}{g.min():>8.0f}{lo:>8.0f}{p05:>8.0f}"
                  f"{int((g < p05).sum()):>6}{int((g < lo).sum()):>6}{out_corner:>11}"
                  f"{pix_out:>8}{100.0 * pix_out / max(pix_tot, 1):>9.2f}%")
        print(f"\nboxes with a corner outside the ROI edge : {tot_out}")
        print(f"pasted pixels outside the ROI edge       : {tot_pix} of {tot_pix_all} "
              f"({100.0 * tot_pix / max(tot_pix_all, 1):.2f}%)")

    # ---- the Bubble Cluster sample, source against destination ------------- #
    s = (REPO / "run" / "augment" / "preview_v3" / "Bubble Cluster"
         / "20241102_030253_L24_C12_9626")
    if (s / "labels.json").exists():
        meta = json.loads((s / "labels.json").read_text())
        key = next((k for k in circles if Path(k).stem == s.name), None)
        c = circles.get(key) if key else None
        if c:
            cx, cy, r, _ = c

            def gap(boxes):
                gs = [r - float(np.hypot((b["xtl"] + b["xbr"]) / 2 - cx,
                                         (b["ytl"] + b["ybr"]) / 2 - cy)) for b in boxes]
                return min(gs), float(np.median(gs))
            sg = gap(meta["source_boxes"])
            dg = gap(meta["boxes"])
            ref = per_class.get("Bubble Cluster", np.array([]))
            print(f"\nsample {s.name}  (ROI R = {r:.0f}, centre {cx:.0f},{cy:.0f})")
            print(f"  source cluster gap to ROI edge : min {sg[0]:.0f} px, median {sg[1]:.0f} px")
            print(f"  pasted cluster gap to ROI edge : min {dg[0]:.0f} px, median {dg[1]:.0f} px")
            print(f"  Bubble Cluster in the library  : min {ref.min():.0f} px, p05 "
                  f"{np.percentile(ref, 5):.0f} px, median {np.median(ref):.0f} px")
            print(f"  jitter realized                : {meta['jitter_realized']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
