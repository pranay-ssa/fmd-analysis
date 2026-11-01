#!/usr/bin/env python3
"""Pixel to micrometer conversion, standalone.

WHAT THIS DOES
--------------
Measures the contact-lens rim in pixels on a set of pictures, then divides a
nominal lens diameter by that measurement to get microns per pixel:

    microns_per_pixel = 14,200 um / measured lens diameter in pixels

The picture has no ruler in it, so the lens itself is the ruler.

THE METHOD, STEP BY STEP (identical to the routine behind the published scale)
------------------------------------------------------------------------------
 1. Read the picture as grayscale.
 2. Mark the bright area: every pixel brighter than 45 percent of the
    picture's peak brightness. That bright area is the lens.
 3. Average the positions of all bright pixels. That point is the centre.
 4. Measure how wide the bright area is (rows and columns). Half of that
    width is the cavity radius, the yardstick for the next steps.
 5. Walk outward from the centre and record average brightness at each
    distance. Smooth that curve over 7 pixels so small noise does not
    confuse the edge search.
 6. The lens edge shows up as a dark ring. Search for the biggest drop in
    brightness between 50 and 92 percent of the cavity radius.
 7. The drop's distance is the lens radius. Lens diameter = 2 x radius.
    A picture counts only if the drop is clear (prominence above 1.0).
    Blurry or obstructed pictures are rejected, never guessed.
 8. Over all accepted pictures: drop the top 7.5 percent and the bottom
    7.5 percent as outliers, then average the rest (a 15 percent trimmed
    mean). That average gives the final scale.

HOW TO RUN
----------
    python pixel_to_micron.py image1.bmp image2.bmp
    python pixel_to_micron.py --folder "path/to/pictures" --csv results.csv

Options:
    --lens-diameter-um  Nominal lens diameter in microns (default 14200).
    --csv PATH          Also write one row per picture to this CSV file.
    --convert-px N      Convert a length given in pixels to microns and print it.

CAVEAT
------
The 14,200 um lens size is our own assumption. No document we received
states it. If the true lens size differs, every converted number shifts
by the same factor.

Requires: numpy, pillow.
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import statistics
import sys

import numpy as np
from PIL import Image

# Our own reference, not a client document. Every micron figure produced
# here is proportional to this number.
NOMINAL_LENS_DIAMETER_UM = 14_200.0

# The rim dip must be deeper than this to count as a real edge.
# Below it the picture is rejected as "no clean edge".
DIP_PROMINENCE_MIN = 1.0


def radial_profile(im, cx, cy, rmax):
    """Brightness at each distance from the centre.

    For every whole-pixel radius 0, 1, 2, ... rmax, average the brightness
    of all pixels that lie at that distance. Returns one number per radius.
    """
    H, W = im.shape
    yy, xx = np.mgrid[0:H, 0:W]
    # Distance of every pixel from the centre, rounded to a whole number.
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.int32).ravel()
    keep = r < rmax
    r = r[keep]
    v = im.ravel()[keep]
    # Sum of brightness per radius / number of pixels per radius = mean.
    return np.divide(np.bincount(r, weights=v, minlength=rmax),
                     np.maximum(np.bincount(r, minlength=rmax), 1))


def measure_lens_rim(path):
    """Lens diameter and cavity diameter in pixels for one picture.

    Returns None when the picture is unusable (too dark, or the bright
    area is too small to be a lens).
    """
    # Step 1: load as grayscale (one brightness number per pixel).
    im = np.asarray(Image.open(path).convert("L")).astype(np.float32)

    # Step 2: mark the bright area. The cutoff sits at 45 percent of the
    # picture's peak brightness, so it adapts to bright and dim pictures.
    hi = np.percentile(im, 99.5)
    if hi < 20:
        return None  # picture is too dark to hold a lens
    mask = im > 0.45 * hi

    # Step 3: centre = average position of all bright pixels.
    ys, xs = np.nonzero(mask)
    if xs.size < 50_000:
        return None  # bright area too small to be a lens
    cx, cy = xs.mean(), ys.mean()

    # Step 4: cavity radius. Count how many columns and rows carry a wide
    # bright run, add the two counts, divide by 4. That lands on the
    # radius of the bright disc in pixels.
    col = mask.sum(0)   # bright pixels per column
    row = mask.sum(1)   # bright pixels per row
    r_cav = (np.count_nonzero(col > 0.5 * col.max())
             + np.count_nonzero(row > 0.5 * row.max())) / 4.0

    # Step 5: brightness curve walking outward from the centre, smoothed
    # with a 7-pixel moving average to quiet small noise.
    prof = radial_profile(im, cx, cy, int(r_cav * 1.05))
    smooth = np.convolve(prof, np.ones(7) / 7, mode="same")

    # Step 6: search for the dark ring (the lens edge) between 50 and 92
    # percent of the cavity radius.
    lo, hi_c = int(0.50 * r_cav), int(0.92 * r_cav)
    seg = smooth[lo:hi_c]

    # "Prominence" = how far the curve dips below its local surroundings.
    # For each point, compare against the brightest value within +/- 25
    # steps. A deep drop against bright surroundings = a real edge.
    w = 25
    base = np.array([seg[max(0, i - w):i + w + 1].max() for i in range(len(seg))])
    prom = base - seg

    # Step 7: the deepest drop is the lens edge radius.
    r_edge = lo + int(np.argmax(prom))
    return {"cavity_diam_px": 2.0 * float(r_cav),
            "lens_diam_px": 2.0 * r_edge,
            "dip_prominence": float(prom.max())}


def trimmed_mean(values, trim=0.15):
    """Average after dropping outliers.

    Sorts the values, drops trim/2 from the low end and trim/2 from the
    high end, then averages what is left. With trim=0.15 on 200 pictures
    that drops the 15 most extreme and averages the middle 185.
    """
    s = sorted(values)
    k = int(len(s) * trim / 2.0)
    core = s[k:len(s) - k] if k else s
    return sum(core) / len(core)


def main():
    # ---- read the command line -------------------------------------------
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("images", nargs="*", help="picture files to measure")
    ap.add_argument("--folder", help="measure every match of --pattern under this folder")
    ap.add_argument("--pattern", default="*.bmp")
    ap.add_argument("--lens-diameter-um", type=float, default=NOMINAL_LENS_DIAMETER_UM,
                    help="nominal lens diameter in microns (default 14200)")
    ap.add_argument("--csv", help="write one row per picture to this CSV file")
    ap.add_argument("--convert-px", type=float,
                    help="also convert this pixel length to microns at the final scale")
    args = ap.parse_args()

    # ---- collect the pictures to measure -----------------------------------
    paths = list(args.images)
    if args.folder:
        paths += sorted(glob.glob(os.path.join(args.folder, "**", args.pattern),
                                  recursive=True))
    if not paths:
        ap.error("give at least one picture or --folder")

    # ---- measure every picture ----------------------------------------------
    # One row per picture for the CSV. The flag says what happened:
    #   ok               -> measured, counts toward the final scale
    #   no_mask / no_dip -> rejected (too dark / no clear edge)
    #   missing / err:X  -> file problem, reported not guessed
    rows, accepted = [], []
    for p in paths:
        rim, flag = "", "ok"
        try:
            if not os.path.exists(p):
                flag = "missing"
            else:
                m = measure_lens_rim(p)
                if m is None:
                    flag = "no_mask"
                elif m["dip_prominence"] <= DIP_PROMINENCE_MIN:
                    flag = "no_dip"
                else:
                    rim = m["lens_diam_px"]
                    accepted.append(m["lens_diam_px"])
        except Exception as exc:
            flag = "err:" + type(exc).__name__
        rows.append({"image": p, "lens_diam_px": rim, "flag": flag})
        # live progress: one line per picture on the screen
        print(f"{p}\t{rows[-1]['lens_diam_px']}\t{flag}")

    # ---- combine into the final scale ----------------------------------------
    print(f"\naccepted {len(accepted)} of {len(paths)} pictures")
    if accepted:
        mean_px = trimmed_mean(accepted)             # outlier-resistant average
        um_per_px = args.lens_diameter_um / mean_px  # the conversion factor
        print(f"lens diameter, 15% trimmed mean : {mean_px:.1f} px")
        print(f"lens diameter, median           : {statistics.median(accepted):.1f} px")
        if len(accepted) >= 2:
            q1, q3 = statistics.quantiles(accepted, n=4)[0], statistics.quantiles(accepted, n=4)[-1]
            rel_spread = (q3 - q1) / (2 * statistics.median(accepted))
            print(f"interquartile relative spread  : {rel_spread:.1%}")
        print(f"nominal lens diameter          : {args.lens_diameter_um:.0f} um")
        print(f"SCALE = {args.lens_diameter_um:.0f} / {mean_px:.1f} = {um_per_px:.4f} um per pixel")
        if args.convert_px is not None:
            print(f"{args.convert_px:g} px = {args.convert_px * um_per_px:.1f} um")

    # ---- optional per-picture CSV ---------------------------------------------
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["image", "lens_diam_px", "flag"])
            w.writeheader()
            w.writerows(rows)
        print(f"\nper-picture rows written to {args.csv}")


if __name__ == "__main__":
    sys.exit(main())
