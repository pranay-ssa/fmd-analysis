#!/usr/bin/env python3
"""Ticket 013a lens-rim measurement, run ON the shared VM, read-only.

The rim-measurement routine is reused verbatim from
/data/FMD_Data_26082026/measure_scale.py so the numbers stay comparable with the
published 783.8 px trimmed mean and 18.1165 microns per pixel.

Piped over ssh, never written to the VM tree. The list of pictures to measure is
read from stdin, one winning path per line (relative to the data root). One TSV
row is printed per input path:

    path <TAB> rim_px <TAB> cavity_px <TAB> method_flags

rim_px is the lens rim diameter in pixels, cavity_px the cavity diameter in
pixels. rim_px is left empty when the method refused the picture; the flag says
why: ok, no_mask (too few bright pixels), no_dip (rim dip prominence <= 1.0, the
same gate the published method used), missing (file not found), err:<type>.

Usage (arg is optional, default root is the shared image root):
    ... 'python3 -c "...." --root /path/to/fmd_temp_images' < sample.txt > out.tsv
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT_DEFAULT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
NOMINAL_LENS_DIAMETER_UM = 14_200.0  # our own reference, not a client nominal

# The rim dip must reach this prominence to count, same gate as measure_scale.py.
DIP_PROMINENCE_MIN = 1.0


def radial_profile(im, cx, cy, rmax):
    """Mean intensity per integer radius. Reused from measure_scale.py."""
    H, W = im.shape
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.int32).ravel()
    keep = r < rmax
    r = r[keep]
    v = im.ravel()[keep]
    return np.divide(np.bincount(r, weights=v, minlength=rmax),
                     np.maximum(np.bincount(r, minlength=rmax), 1))


def measure(path):
    """Lens rim and cavity in pixels. Reused from measure_scale.py verbatim."""
    im = np.asarray(Image.open(path)).astype(np.float32)
    hi = np.percentile(im, 99.5)
    if hi < 20:
        return None
    mask = im > 0.45 * hi
    ys, xs = np.nonzero(mask)
    if xs.size < 50_000:
        return None
    cx, cy = xs.mean(), ys.mean()
    col = mask.sum(0)
    rowp = mask.sum(1)
    R_cav = (np.count_nonzero(col > 0.5 * col.max())
             + np.count_nonzero(rowp > 0.5 * rowp.max())) / 4.0
    rmax = int(R_cav * 1.05)
    prof = radial_profile(im, cx, cy, rmax)
    ps = np.convolve(prof, np.ones(7) / 7, mode="same")
    lo, hc = int(0.50 * R_cav), int(0.92 * R_cav)
    seg = ps[lo:hc]
    w = 25
    base = np.array([seg[max(0, i - w):i + w + 1].max() for i in range(len(seg))])
    prom = base - seg
    r_edge = lo + int(np.argmax(prom))
    return {"R_cav": float(R_cav),
            "cav_diam_px": 2 * float(R_cav),
            "lens_diam_px": 2.0 * r_edge,
            "dip_prominence": float(prom.max())}


def main():
    argv = sys.argv[1:]
    root = ROOT_DEFAULT
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]

    done = 0
    for raw in sys.stdin:
        path = raw.rstrip("\n").rstrip("\r")
        if not path.strip():
            continue
        done += 1
        full = os.path.join(root, path)
        rim = cav = ""
        try:
            if not os.path.exists(full):
                flag = "missing"
            else:
                m = measure(full)
                if m is None:
                    flag = "no_mask"
                else:
                    rim = "%g" % m["lens_diam_px"]
                    cav = "%g" % m["cav_diam_px"]
                    flag = "ok" if m["dip_prominence"] > DIP_PROMINENCE_MIN else "no_dip"
        except Exception as exc:  # report the real failure, never invent a number
            flag = "err:" + type(exc).__name__
        sys.stdout.write("\t".join([path, rim, cav, flag]) + "\n")
        sys.stdout.flush()
        if done % 100 == 0:
            sys.stderr.write("measured %d\n" % done)
            sys.stderr.flush()


if __name__ == "__main__":
    main()
