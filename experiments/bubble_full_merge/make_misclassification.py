#!/usr/bin/env python3
"""Phase 2 of bubble_full_merge: the misclassification export (2026-10-15).

Reads the run's predictions.csv and the crops manifest, takes every test crop
the model got wrong, converts it BMP -> PNG, and renames it to
<sno>_<true>_<pred>.png. sno is a globally unique integer, the primary key of
the manifest, so filenames stay short and the manifest resolves the original
name, source image and box.

DECISIONS (frozen with the user):
  * sno        : unique per misclassified CROP, not per image. Two bad crops
                 from one source image get two s.nos and two files; the
                 manifest's source_image column is what ties them together.
  * Filename   : <sno>_<true_slug>_<pred_slug>.png, slug = lowercase with
                 spaces -> underscores (e.g. 1_hema_fragment_extraneous_polymer.png).
  * Order      : sno is assigned after sorting by (true, pred, crop filename),
                 so the folder groups like errors together and the numbering
                 is deterministic across reruns.
  * Manifest   : sno (primary key), png filename, original crop file, source
                 image, source md5, crop bbox (xtl,ytl,xbr,ybr + rotation),
                 true label, predicted label. The bbox is the safeguard for
                 the multi-crop-per-image case.

Reads (under --base):
  runs2/bubble_full_merge/predictions.csv
  crops_manifest.csv
  exp/test/<class>/<crop>.bmp
Writes under --out:
  <sno>_<true>_<pred>.png   one per misclassified crop
  manifest.csv              one row per crop, sno ascending

USAGE (on the VM, as pranayp)
  python3 make_misclassification.py --base . --out misclassification
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter


def slug(name):
    return name.lower().replace(" ", "_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="bubble_full_merge dir")
    ap.add_argument("--pred", default=None,
                    help="predictions.csv (default <base>/runs2/bubble_full_merge/predictions.csv)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pred_path = args.pred or os.path.join(args.base, "runs2", "bubble_full_merge",
                                          "predictions.csv")
    man_path = os.path.join(args.base, "crops_manifest.csv")
    test_root = os.path.join(args.base, "exp", "test")

    # crops manifest: basename -> row (source image, md5, box)
    crops = {}
    with open(man_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            crops[os.path.basename(r["crop_file"])] = r
    print("crops manifest rows: %d" % len(crops))

    # misclassified test crops
    mis = []
    n_total = 0
    with open(pred_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            n_total += 1
            if r["true"] == r["pred"]:
                continue
            cropname = os.path.basename(r["file"])
            m = crops.get(cropname)
            if m is None:
                print("WARNING: no manifest row for %s" % cropname)
                continue
            mis.append((r["true"], r["pred"], cropname, r["file"], m))
    print("test crops: %d, misclassified: %d" % (n_total, len(mis)))

    # deterministic sno: sort by true, pred, crop filename
    mis.sort(key=lambda t: (t[0], t[1], t[2]))

    from PIL import Image
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for i, (true, pred, cropname, relpath, m) in enumerate(mis, start=1):
        src = os.path.join(args.base, relpath)
        if not os.path.exists(src):
            print("WARNING: missing crop file %s" % src)
            continue
        png = "%d_%s_%s.png" % (i, slug(true), slug(pred))
        with Image.open(src) as im:
            im.convert("RGB").save(os.path.join(args.out, png), "PNG")
        rows.append({
            "sno": i,
            "png": png,
            "original_crop": cropname,
            "source_image": m["source_image"],
            "source_md5": m["source_md5"],
            "xtl": m["xtl"], "ytl": m["ytl"],
            "xbr": m["xbr"], "ybr": m["ybr"],
            "rotation": m["rotation"],
            "true_label": true,
            "predicted_label": pred,
        })

    with open(os.path.join(args.out, "manifest.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- verification gates ----
    print("\nwritten: %d PNGs, %d manifest rows" % (len(rows), len(rows)))
    snums = [r["sno"] for r in rows]
    pngs = [f for f in os.listdir(args.out) if f.endswith(".png")]
    print("gate unique sno: %s (%d unique of %d)"
          % ("PASS" if len(set(snums)) == len(snums) else "FAIL",
             len(set(snums)), len(snums)))
    print("gate sno contiguous 1..N: %s"
          % ("PASS" if sorted(snums) == list(range(1, len(snums) + 1)) else "FAIL"))
    print("gate png count == rows: %s (%d vs %d)"
          % ("PASS" if len(pngs) == len(rows) else "FAIL", len(pngs), len(rows)))
    print("gate filename == manifest: %s"
          % ("PASS" if set(pngs) == {r["png"] for r in rows} else "FAIL"))

    print("\nerror pairs (true -> pred : crops, images):")
    pair_imgs = Counter()
    for r in rows:
        pair_imgs[(r["true_label"], r["predicted_label"])] = 1
    imgs = {}
    for r in rows:
        imgs.setdefault((r["true_label"], r["predicted_label"]), set()).add(r["source_image"])
    cnt = Counter((r["true_label"], r["predicted_label"]) for r in rows)
    for (t, p), c in cnt.most_common():
        print("  %-20s -> %-20s %4d crops  %3d images"
              % (t, p, c, len(imgs[(t, p)])))
    print("\ndistinct source images affected: %d"
          % len({r["source_image"] for r in rows}))
    print("wrote: %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
