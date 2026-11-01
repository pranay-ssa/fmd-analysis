#!/usr/bin/env python3
"""Ticket 012 cavity measurement over the EDA library census, run ON the shared
VM, read-only.

The cavity-measurement routine is reused verbatim from the 2026-10-13 run
(`vm/ops/measure_cavity_all.py`, which measured only the 1,047 production-batch
images) so the numbers stay comparable with the published batch analysis. The
same bright-blob mask, the same 0.45 * p99.5 threshold, the same
half-max column/row width rule and the same /4.0 radius. Nothing new is
invented here.

The list of pictures to measure is read from stdin, one winning path per line
(relative to the data root). One TSV row is printed per input path:

    path <TAB> cx <TAB> cy <TAB> R_px <TAB> flag

cx, cy and R_px are the cavity centre and radius in pixels. They are left empty
when the method refused the picture; the flag names the failure class:
  ok          measured
  low_bright  p99.5 intensity below 20, nothing to threshold (dark frame)
  no_mask     fewer than 50,000 bright pixels after threshold
  missing     file not found under the data root
  err:<type>  an unexpected exception, reported as-is, never invented past

The script is carried to the VM base64-encoded so the picture list can ride on
stdin (the plain `python3 -` form would put the script and the list on the same
stream), and nothing is ever written to the shared VM tree:

    C:/Windows/System32/OpenSSH/ssh.exe -o BatchMode=yes amd-a100-vm \\
      "python3 -c \\"import base64;exec(base64.b64decode('<blob>'))\\" --root <root>" \\
      < paths.txt > cavity_raw.tsv

This script only reads image files.
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

ROOT_DEFAULT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"


def measure(path):
    """Cavity centre and radius in pixels. Reused from measure_cavity_all.py.

    Returns (cx, cy, R, None) on success, or (None, None, None, reason) where
    reason is the failure class, so the caller can name it instead of dropping
    the picture silently.
    """
    im = np.asarray(Image.open(path)).astype(np.float32)
    hi = np.percentile(im, 99.5)
    if hi < 20:
        return None, None, None, "low_bright"
    mask = im > 0.45 * hi
    ys, xs = np.nonzero(mask)
    if xs.size < 50_000:
        return None, None, None, "no_mask"
    cx, cy = float(xs.mean()), float(ys.mean())
    col = mask.sum(0)
    rowp = mask.sum(1)
    R = (np.count_nonzero(col > 0.5 * col.max())
         + np.count_nonzero(rowp > 0.5 * rowp.max())) / 4.0
    return cx, cy, float(R), None


def one(args):
    path, root = args
    full = os.path.join(root, path)
    try:
        if not os.path.exists(full):
            return path, "", "", "", "missing"
        a, b, r, err = measure(full)
        if err is not None:
            return path, "", "", "", err
        return path, ("%.6f" % a), ("%.6f" % b), ("%.6f" % r), "ok"
    except Exception as exc:  # report the real failure, never invent a number
        return path, "", "", "", "err:" + type(exc).__name__


def main():
    argv = sys.argv[1:]
    root = ROOT_DEFAULT
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]
    jobs = 8
    if "--jobs" in argv:
        jobs = int(argv[argv.index("--jobs") + 1])

    paths = []
    for raw in sys.stdin:
        p = raw.rstrip("\n").rstrip("\r")
        if p.strip():
            paths.append(p)

    done = 0
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for res in pool.map(one, ((p, root) for p in paths)):
            sys.stdout.write("\t".join(res) + "\n")
            done += 1
            if done % 500 == 0:
                sys.stdout.flush()
                sys.stderr.write("measured %d / %d\n" % (done, len(paths)))
                sys.stderr.flush()
    sys.stdout.flush()


if __name__ == "__main__":
    main()
