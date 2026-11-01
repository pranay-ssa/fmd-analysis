#!/usr/bin/env python3
"""Multiple-Lenses and second-ruler scanner, run ON the shared VM, READ ONLY.

Phase 4 of the scale plan. Two questions, both pixel only, no nominal used and
no micron figure produced anywhere in this file:

  1. Multiple Lenses (the P1_ML class, 1,439 pictures). If a frame really holds
     two lenses, the two rim circles give a within-frame repeatability of the
     lens diameter that no single-lens frame can give, and they tell us whether
     the lens or the cavity is the stable reference. This scanner measures, per
     picture: the Phase-1 rim circle fit (single circle), a two-circle split of
     the same rim edge points with its residual, the full dark-ring inventory
     with per-ring ray geometry, and a count of rings in the cavity interior.

  2. A second ruler. If a frame shows more than one cavity, or the tray or the
     package edge, the spacing between those features is a length that needs no
     lens nominal. This scanner measures the bright connected components of the
     whole frame (the cavity disc is one of them) and whether the largest one
     touches the frame border, so the builder can count multi-cavity and
     package-edge frames and measure their separation.

Every routine is reused from the shipped code so the numbers stay comparable:
the bright-blob cavity, the annular radial profile, the boxcar smoothing, the
rolling-max baseline, the 360-ray edge stack and the least-squares circle fit
with outlier rejection are all copied from vm/ops/scan_rings.py (which itself
reuses measure_scale.py and measure_cavity_library.py).

The script is carried to the VM base64-encoded (never written to the VM tree) so
the picture list can ride on stdin:

    C:/Windows/System32/OpenSSH/ssh.exe -o BatchMode=yes amd-a100-vm \
      "python3 -c \"import base64;exec(base64.b64decode('<blob>'))\" --root <root>" \
      < list.tsv > out.tsv

stdin is a TSV, one row per picture:  tag <TAB> relpath
stdout is a TSV of three row kinds:

  P <TAB> tag <TAB> md5 <TAB> relpath <TAB> cx <TAB> cy <TAB> Rcav <TAB> flag
    <TAB> rim_diam <TAB> rim_rms <TAB> n_rings <TAB> n_interior
    <TAB> n_interior_coherent <TAB> two_improve_ratio <TAB> n_glob
    <TAB> g1_area <TAB> g1_cy <TAB> g1_cx <TAB> g1_w <TAB> g1_h <TAB> g1_touch
    <TAB> g2_area <TAB> g2_cy <TAB> g2_cx <TAB> g2_sep <TAB> g3_area
  R <TAB> md5 <TAB> idx <TAB> radius <TAB> depth <TAB> norm <TAB> ring_R
    <TAB> frac_ray
  G <TAB> md5 <TAB> idx <TAB> area <TAB> cy <TAB> cx <TAB> w <TAB> h <TAB> touch

flag is ok, low_bright, no_mask, missing or err:<type>. Numeric fields are left
empty when a method refused the picture. Areas are in coarse cells (image
downsampled by CC_STEP) and can be scaled back by CC_STEP squared.

This script only reads image files.
"""
import hashlib
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

ROOT_DEFAULT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"

BOX = 7
RMAX_FRAC = 1.08
NRAY = 360
CIRC_RIM_LO = 0.80
CIRC_RIM_HI = 0.96
CIRC_OUTLIER_PASSES = 2
RING_LO_FRAC = 0.35
RING_HI_FRAC = 1.06
RING_MIN_PROM = 1.0
RAY_WIN_MIN = 15
RAY_WIN_FRAC = 0.06
RAY_PROM_FLOOR = 2.0
RAY_PROM_REL = 0.4
# A ring found on at least this fraction of the 360 rays is treated as a
# coherent circular boundary rather than noise.
COHERENT_FRAC = 0.5
INTERIOR_HI = 0.80      # normalised radius below which a ring counts as interior
CC_STEP = 8             # bright-mask downsample for connected components
CC_MIN_AREA = 40        # coarse-cell area floor for a reported component
W = 25


def radial_profile(im, cx, cy, rmax):
    H, Wd = im.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.int32).ravel()
    keep = r < rmax
    r = r[keep]
    v = im.ravel()[keep]
    return np.divide(np.bincount(r, weights=v, minlength=rmax),
                     np.maximum(np.bincount(r, minlength=rmax), 1))


def cavity(im):
    hi = np.percentile(im, 99.5)
    if hi < 20:
        return None, "low_bright"
    mask = im > 0.45 * hi
    ys, xs = np.nonzero(mask)
    if xs.size < 50_000:
        return None, "no_mask"
    cx, cy = float(xs.mean()), float(ys.mean())
    col = mask.sum(0)
    rowp = mask.sum(1)
    R = (np.count_nonzero(col > 0.5 * col.max())
         + np.count_nonzero(rowp > 0.5 * rowp.max())) / 4.0
    return (cx, cy, R), None


def boxcar(a, k):
    return np.convolve(a, np.ones(k) / k, mode="same")


def boxcar_rows(M, k):
    pad = k // 2
    P = np.pad(M, ((0, 0), (pad, pad)), mode="edge")
    c = np.cumsum(P, axis=1)
    c = np.concatenate([np.zeros((P.shape[0], 1), dtype=c.dtype), c], axis=1)
    return (c[:, k:] - c[:, :-k]) / k


def ray_stack(im, cx, cy, rmax):
    H, Wd = im.shape
    rs = np.arange(0.0, float(rmax) + 1.0, 1.0)
    th = np.arange(NRAY) * (2.0 * np.pi / NRAY)
    X = cx + np.outer(np.cos(th), rs)
    Y = cy + np.outer(np.sin(th), rs)
    X = np.clip(X, 0, Wd - 1)
    Y = np.clip(Y, 0, H - 1)
    x0 = np.floor(X).astype(np.int32)
    y0 = np.floor(Y).astype(np.int32)
    x1 = np.minimum(x0 + 1, Wd - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    fx = (X - x0).astype(np.float32)
    fy = (Y - y0).astype(np.float32)
    v = (im[y0, x0] * (1 - fx) * (1 - fy) + im[y0, x1] * fx * (1 - fy)
         + im[y1, x0] * (1 - fx) * fy + im[y1, x1] * fx * fy)
    return rs, v


def circle_fit(x, y):
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    ccx = sol[0] / 2.0
    ccy = sol[1] / 2.0
    rr = np.sqrt(max(sol[2] + ccx * ccx + ccy * ccy, 0.0))
    return float(ccx), float(ccy), float(rr)


def fit_with_rejection(x, y):
    keep = np.ones(len(x), dtype=bool)
    R = float("nan")
    n = 0
    rms = float("nan")
    for _ in range(CIRC_OUTLIER_PASSES + 1):
        if keep.sum() < 8:
            break
        ccx, ccy, R = circle_fit(x[keep], y[keep])
        d = np.sqrt((x - ccx) ** 2 + (y - ccy) ** 2)
        res = d - R
        sd = float(res[keep].std())
        keep = np.abs(res) < max(3.0 * sd, 6.0)
        n = int(keep.sum())
        rms = float(np.sqrt(np.mean(res[keep] ** 2))) if n else float("nan")
    return R, n, rms


def prominence_minima(ps, lo, hi, min_prom):
    n = len(ps)
    lo = max(1, int(lo))
    hi = min(n - 1, int(hi))
    rings = []
    i = lo
    while i < hi:
        if ps[i] <= ps[i - 1] and ps[i] < ps[i + 1]:
            j = i - 1
            while j - 1 >= 0 and ps[j - 1] >= ps[j]:
                j -= 1
            k = i + 1
            while k + 1 < n and ps[k + 1] >= ps[k]:
                k += 1
            base = min(ps[j], ps[k])
            prom = float(base - ps[i])
            if prom >= min_prom:
                rings.append({"radius": float(i), "depth": prom})
            i += 1
        else:
            i += 1
    return rings


def cc_label(mask, min_area):
    """4-connected components of a boolean array; returns
    [(area, cy, cx, w, h)] for components of at least min_area cells."""
    h, w = mask.shape
    visited = np.zeros_like(mask)
    out = []
    for i in range(h):
        row = mask[i]
        for j in range(w):
            if row[j] and not visited[i, j]:
                stack = [(i, j)]
                visited[i, j] = True
                n = 0
                sy = sx = 0
                ymin = ymax = i
                xmin = xmax = j
                while stack:
                    a, b = stack.pop()
                    n += 1
                    sy += a
                    sx += b
                    if a < ymin:
                        ymin = a
                    if a > ymax:
                        ymax = a
                    if b < xmin:
                        xmin = b
                    if b > xmax:
                        xmax = b
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x2, y2 = a + da, b + db
                        if 0 <= x2 < h and 0 <= y2 < w and mask[x2, y2] and not visited[x2, y2]:
                            visited[x2, y2] = True
                            stack.append((x2, y2))
                if n >= min_area:
                    out.append((n, sy / n, sx / n, xmax - xmin + 1, ymax - ymin + 1))
    return out


def two_means(pts, seed=3):
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(pts), 2, replace=False)
    c = pts[idx].astype(float)
    g = None
    for _ in range(25):
        d0 = ((pts - c[0]) ** 2).sum(1)
        d1 = ((pts - c[1]) ** 2).sum(1)
        g = (d1 < d0).astype(int)
        if g.sum() == 0 or g.sum() == len(pts):
            return None
        c = np.array([pts[g == 0].mean(0), pts[g == 1].mean(0)])
    return g


def measure(path):
    raw = open(path, "rb").read()
    md5 = hashlib.md5(raw).hexdigest()
    im = np.asarray(Image.open(io.BytesIO(raw))).astype(np.float32)
    cav, err = cavity(im)
    if err is not None:
        return md5, {"flag": err}
    cx, cy, Rcav = cav
    rmax = int(Rcav * RMAX_FRAC)
    prof = radial_profile(im, cx, cy, rmax)
    ps = boxcar(prof, BOX)

    rings = prominence_minima(ps, RING_LO_FRAC * Rcav,
                              min(RING_HI_FRAC * Rcav, len(ps) - 1), RING_MIN_PROM)

    rs, rv = ray_stack(im, cx, cy, rmax)
    S = boxcar_rows(rv, BOX)
    G = np.abs(np.gradient(S, axis=1))
    th = np.arange(NRAY) * (2.0 * np.pi / NRAY)
    cos_t, sin_t = np.cos(th), np.sin(th)

    rlo, rhi = int(CIRC_RIM_LO * Rcav), min(int(CIRC_RIM_HI * Rcav), S.shape[1] - 2)
    kk = np.argmax(G[:, rlo:rhi], axis=1)
    rr = rs[rlo + kk]
    pts = np.column_stack([cx + rr * cos_t, cy + rr * sin_t])
    rim_R, rim_n, rim_rms = fit_with_rejection(pts[:, 0], pts[:, 1])

    # two-circle split of the same rim edge points
    two_ratio = ""
    g = two_means(pts, seed=3)
    if g is not None and g.sum() >= 30 and (g == 0).sum() >= 30:
        Ra, nA, rmsA = fit_with_rejection(pts[g == 0, 0], pts[g == 0, 1])
        Rb, nB, rmsB = fit_with_rejection(pts[g == 1, 0], pts[g == 1, 1])
        if nA and nB and rmsA == rmsA and rmsB == rmsB:
            dA = np.sqrt((pts[g == 0, 0] - cx) ** 2 + (pts[g == 0, 1] - cy) ** 2) - Ra
            dB = np.sqrt((pts[g == 1, 0] - cx) ** 2 + (pts[g == 1, 1] - cy) ** 2) - Rb
            rms2 = float(np.sqrt((np.concatenate([dA, dB]) ** 2).mean()))
            if rms2 > 0:
                two_ratio = rim_rms / rms2

    # per-ring ray geometry (frac_ray, ring_R) as in scan_rings.py
    for ring in rings:
        r0 = ring["radius"]
        win = int(max(RAY_WIN_MIN, RAY_WIN_FRAC * r0))
        wlo = max(0, int(r0 - win))
        whi = min(S.shape[1], int(r0 + win) + 1)
        gate = max(RAY_PROM_FLOOR, RAY_PROM_REL * ring["depth"])
        seg2 = S[:, wlo:whi]
        p2 = seg2.max(axis=1, keepdims=True) - seg2
        k2 = np.argmax(p2, axis=1)
        pk = p2[np.arange(NRAY), k2]
        good = pk > gate
        rth = rs[wlo + k2][good]
        if rth.size >= 30:
            ring["ring_R"] = float(rth.mean())
        else:
            ring["ring_R"] = ""
        ring["frac_ray"] = float(rth.size) / NRAY
        ring["norm"] = float(r0) / Rcav

    n_interior = sum(1 for r in rings if r["norm"] < INTERIOR_HI)
    n_interior_coherent = sum(1 for r in rings
                              if r["norm"] < INTERIOR_HI
                              and r["frac_ray"] >= COHERENT_FRAC)

    # bright components over the whole frame, coarse
    hi = np.percentile(im, 99.5)
    mask = im > 0.45 * hi
    ds = mask[::CC_STEP, ::CC_STEP]
    comps = cc_label(ds, CC_MIN_AREA)
    comps = sorted(comps, reverse=True)
    Hc, Wc = ds.shape
    glob = []
    for (n, ccy, ccx, w, h) in comps[:3]:
        touch = 1 if (ccy - h / 2 <= 0.5 or ccy + h / 2 >= Hc - 0.5
                      or ccx - w / 2 <= 0.5 or ccx + w / 2 >= Wc - 0.5) else 0
        glob.append((n, ccy, ccx, w, h, touch))
    g2_sep = ""
    if len(glob) >= 2:
        g2_sep = float(np.hypot(glob[0][1] - glob[1][1], glob[0][2] - glob[1][2])) * CC_STEP

    pic = {"cx": cx, "cy": cy, "Rcav": Rcav, "rim_diam": 2.0 * rim_R,
           "rim_rms": rim_rms, "n_rings": len(rings), "n_interior": n_interior,
           "n_interior_coherent": n_interior_coherent, "two_ratio": two_ratio,
           "n_glob": len(comps), "glob": glob, "g2_sep": g2_sep}
    return md5, {"flag": "ok", "pic": pic, "rings": rings}


def fmt(v):
    if v == "" or v is None:
        return ""
    if isinstance(v, float) and not np.isfinite(v):
        return ""
    if isinstance(v, float):
        return "%.4f" % v
    return str(v)


def one(args):
    tag, relpath, root = args
    full = os.path.join(root, relpath)
    if not os.path.exists(full):
        return ["\t".join(["P", tag, "", relpath] + [""] * 6 + ["missing"] + [""] * 16)]
    try:
        md5, res = measure(full)
    except Exception as exc:
        return ["\t".join(["P", tag, "", relpath] + [""] * 6
                          + ["err:" + type(exc).__name__] + [""] * 16)]
    if res["flag"] != "ok":
        return ["\t".join(["P", tag, md5, relpath] + [""] * 6
                          + [res["flag"]] + [""] * 16)]
    p = res["pic"]
    gl = p["glob"] + [(0, 0, 0, 0, 0, 0)] * 3
    rows = ["\t".join(["P", tag, md5, relpath, fmt(p["cx"]), fmt(p["cy"]),
                       fmt(p["Rcav"]), "ok", fmt(p["rim_diam"]), fmt(p["rim_rms"]),
                       str(p["n_rings"]), str(p["n_interior"]),
                       str(p["n_interior_coherent"]), fmt(p["two_ratio"]),
                       str(p["n_glob"]),
                       fmt(gl[0][0]), fmt(gl[0][1]), fmt(gl[0][2]), fmt(gl[0][3]),
                       fmt(gl[0][4]), str(gl[0][5]),
                       fmt(gl[1][0]), fmt(gl[1][1]), fmt(gl[1][2]), fmt(p["g2_sep"]),
                       fmt(gl[2][0])])]
    for i, r in enumerate(res["rings"]):
        rows.append("\t".join(["R", md5, str(i), fmt(r["radius"]),
                               fmt(r["depth"]), fmt(r["norm"]),
                               fmt(r.get("ring_R", "")), fmt(r["frac_ray"])]))
    for i, (n, ccy, ccx, w, h, touch) in enumerate(p["glob"]):
        rows.append("\t".join(["G", md5, str(i), str(n), fmt(ccy), fmt(ccx),
                               str(w), str(h), str(touch)]))
    return rows


def main():
    argv = sys.argv[1:]
    root = ROOT_DEFAULT
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]
    jobs = 12
    if "--jobs" in argv:
        jobs = int(argv[argv.index("--jobs") + 1])
    items = []
    for raw in sys.stdin:
        line = raw.rstrip("\n").rstrip("\r")
        if not line.strip():
            continue
        tag, relpath = line.split("\t", 1)
        items.append((tag, relpath, root))
    done = 0
    out = sys.stdout
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for rows in pool.map(one, items):
            for row in rows:
                out.write(row + "\n")
            done += 1
            if done % 100 == 0:
                out.flush()
                sys.stderr.write("measured %d / %d\n" % (done, len(items)))
                sys.stderr.flush()
    out.flush()


if __name__ == "__main__":
    main()
