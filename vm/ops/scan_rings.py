#!/usr/bin/env python3
"""Ring-identity scanner, run ON the shared VM, READ ONLY.

Phase 1 of the scale plan. The question is pure pixels: which ring in the radial
intensity profile is the actual lens edge. No nominal is used and no micron
figure is produced anywhere in this file. NOMINAL_LENS_DIAMETER_UM exists only so
the dip-argmax method can be reproduced verbatim from
/data/FMD_Data_26082026/measure_scale.py; it never reaches any output.

What one picture gets, all from the cavity centre found by the shipped cavity
method (the same bright-blob mask, 0.45 * p99.5 threshold and /4.0 radius rule as
vm/ops/measure_cavity_library.py):

  1. the annular mean-intensity radial profile at 1 px resolution
     (radial_profile, reused verbatim from measure_scale.py);
  2. EVERY local dark feature in that profile (candidate rings). A feature is a
     true local minimum of the profile and its depth is the topographic
     prominence: the drop from the lower of the two enclosing local maxima. That
     definition cannot invent a ring on a monotone ramp, which a rolling-max
     baseline does at the edge of the search band. Each ring carries its radius,
     depth, full width at half depth and a sharpness (depth / width);
  3. the three competing methods on the same picture: dip-argmax (verbatim
     measure_scale.py), gradient (max |dI/dr| of the smoothed annular profile)
     and a least-squares circle fit to 360 radial edge points with outlier
     rejection, in a wide band and in a lens-rim band;
  4. for every candidate ring, its own geometry from 360 rays: its radius, the
     offset of its centre from the cavity centre, and the fraction of rays on
     which the ring was actually found.

The profile runs to 1.08 * R_cav, not 1.05, because the cavity-wall edge sits at
about 1.04 * R_cav and a 1.05 cut truncates it mid-drop.

The script is carried to the VM base64-encoded (never written to the VM tree) so
the picture list can ride on stdin:

    python3 -c "import base64;exec(base64.b64decode('<blob>'))" --root <root> \
        < sample.tsv > rings_raw.tsv

stdin is a TSV, one row per picture:  tag <TAB> relpath
tag is lib, prod or repro. stdout is a TSV of two row kinds, 16 and 13 columns:

  P <TAB> tag <TAB> md5 <TAB> relpath <TAB> cx <TAB> cy <TAB> Rcav <TAB> flag
    <TAB> dip_r <TAB> dip_prom <TAB> grad_r <TAB> circ_r <TAB> circ_n
    <TAB> circ_rms <TAB> circ_rim_r <TAB> n_rings
  R <TAB> md5 <TAB> idx <TAB> radius <TAB> depth <TAB> width <TAB> sharp
    <TAB> ring_R <TAB> dx <TAB> dy <TAB> ecc <TAB> frac_ray <TAB> norm
  C <TAB> md5 <TAB> u <TAB> prom <TAB> detrate <TAB> ecc <TAB> sd_r <TAB> r_mean

The C rows are the band-free per-radius curve the two discriminators are read
off: for every normalised radius u in [0.35, 1.06] at 0.02 steps, the annular dip
strength, the fraction of the 360 rays on which a dark ring was found there, the
offset of that ring's centre from the cavity centre, and the angular spread of
its radius.

flag is ok, low_bright, no_mask, missing or err:<type>. Numeric fields are left
empty when a method refused the picture. --emit-repro prints the 200 relpaths the
prior script selects (random.seed(7) over the *Pass1* glob) and measures nothing.

This script only reads image files.
"""
import glob
import hashlib
import io
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

ROOT_DEFAULT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
PROD_SUBDIR = "20260826_T24_Production_Sample/sample folder"

# Reproduced from measure_scale.py line 9. Used ONLY to keep the dip-argmax
# method bit-comparable with the shipped routine. No output divides by it.
NOMINAL_LENS_DIAMETER_UM = 14_200.0

DIP_PROMINENCE_MIN = 1.0      # the gate measure_scale.py uses
DIP_LO_FRAC = 0.50            # measure_scale.py band
DIP_HI_FRAC = 0.92
GRAD_LO_FRAC = 0.50           # gradient-method band
GRAD_HI_FRAC = 1.00
CIRC_LO_FRAC = 0.50           # circle-fit band, wide
CIRC_HI_FRAC = 1.06
CIRC_RIM_LO = 0.80            # circle-fit band, lens rim
CIRC_RIM_HI = 0.96
RMAX_FRAC = 1.08              # profile reach, see module docstring
RING_LO_FRAC = 0.35           # candidate-ring search band
RING_HI_FRAC = 1.06
RING_MIN_PROM = 1.0           # a candidate ring must drop this far below baseline
W = 25                        # rolling-max half-window, measure_scale.py value
BOX = 7                       # boxcar smoothing width, measure_scale.py value
NRAY = 360
RAY_WIN_MIN = 15              # px either side of a ring when finding it on a ray
RAY_WIN_FRAC = 0.06
RAY_PROM_FLOOR = 2.0          # per-ray dip gate, absolute floor
RAY_PROM_REL = 0.4            # per-ray dip gate, fraction of the annular depth
CIRC_OUTLIER_PASSES = 2
CURVE_LO = 0.35               # per-radius ring curve, normalised radius
CURVE_HI = 1.06
CURVE_STEP = 0.02
CURVE_WIN_FRAC = 0.025        # half-window for the per-ray dip search
CURVE_RAY_GATE = 2.0          # per-ray dip gate for the curve


def radial_profile(im, cx, cy, rmax):
    """Mean intensity per integer radius. Reused verbatim from measure_scale.py."""
    H, Wd = im.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.int32).ravel()
    keep = r < rmax
    r = r[keep]
    v = im.ravel()[keep]
    return np.divide(np.bincount(r, weights=v, minlength=rmax),
                     np.maximum(np.bincount(r, minlength=rmax), 1))


def cavity(im):
    """Cavity centre and radius in pixels. Reused from measure_cavity_library.py."""
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
    """Boxcar smoothing along axis 1 of a 2-D array."""
    pad = k // 2
    P = np.pad(M, ((0, 0), (pad, pad)), mode="edge")
    c = np.cumsum(P, axis=1)
    c = np.concatenate([np.zeros((P.shape[0], 1), dtype=c.dtype), c], axis=1)
    return (c[:, k:] - c[:, :-k]) / k


def rolling_max(a, w):
    """max over [i-w, i+w]. The measure_scale.py baseline, same window."""
    n = len(a)
    out = np.empty(n, dtype=a.dtype)
    for i in range(n):
        out[i] = a[max(0, i - w):i + w + 1].max()
    return out


def prominence_minima(ps, lo, hi, min_prom):
    """Every local minimum of ps in [lo, hi) whose topographic prominence is at
    least min_prom.

    For a local minimum i the enclosing maxima are the first local maxima found
    walking left and right. The saddle that has to be crossed to leave the dip is
    the lower of those two, so that is the baseline and the prominence is
    baseline - ps[i]. On a monotone ramp one side never rises above ps[i] inside
    the search band, so the prominence comes out negative and no ring is
    invented.
    """
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
                half = ps[i] + 0.5 * prom
                a = i
                while a - 1 >= j and ps[a - 1] < half:
                    a -= 1
                b = i
                while b + 1 <= k and ps[b + 1] < half:
                    b += 1
                wpx = float(b - a + 1)
                rings.append({"radius": float(i), "depth": prom, "width": wpx,
                              "sharp": prom / max(wpx, 1.0)})
            i += 1
        else:
            i += 1
    return rings


def ray_stack(im, cx, cy, rmax):
    """(rs, v): intensity along NRAY rays from (cx, cy), shape (NRAY, len(rs))."""
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
    """Algebraic least-squares circle (Kasa). Returns (cx, cy, R)."""
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    ccx = sol[0] / 2.0
    ccy = sol[1] / 2.0
    rr = np.sqrt(max(sol[2] + ccx * ccx + ccy * ccy, 0.0))
    return float(ccx), float(ccy), float(rr)


def fit_with_rejection(x, y):
    """Circle fit with iterative outlier rejection. Returns (R, n, rms)."""
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
        cut = max(3.0 * sd, 6.0)
        keep = np.abs(res) < cut
        n = int(keep.sum())
        rms = float(np.sqrt(np.mean(res[keep] ** 2))) if n else float("nan")
    return R, n, rms


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

    # ---- method 1, dip-argmax, verbatim from measure_scale.py --------------
    lo, hc = int(DIP_LO_FRAC * Rcav), int(DIP_HI_FRAC * Rcav)
    seg = ps[lo:hc]
    base = rolling_max(seg, W)
    prom = base - seg
    k = int(np.argmax(prom))
    dip_r = float(lo + k)
    dip_prom = float(prom[k])

    # ---- method 2, gradient on the smoothed annular profile -----------------
    g = np.abs(np.gradient(ps))
    glo, ghi = int(GRAD_LO_FRAC * Rcav), min(int(GRAD_HI_FRAC * Rcav), len(g))
    r_grad = float(glo + int(np.argmax(g[glo:ghi])))

    # ---- candidate rings, every dark feature -------------------------------
    rings = prominence_minima(ps, RING_LO_FRAC * Rcav,
                              min(RING_HI_FRAC * Rcav, len(ps) - 1),
                              RING_MIN_PROM)

    # ---- method 3 + ring geometry, 360 rays --------------------------------
    rs, rv = ray_stack(im, cx, cy, rmax)
    S = boxcar_rows(rv, BOX)
    G = np.abs(np.gradient(S, axis=1))
    th = np.arange(NRAY) * (2.0 * np.pi / NRAY)
    cos_t, sin_t = np.cos(th), np.sin(th)

    clo, chi = int(CIRC_LO_FRAC * Rcav), min(int(CIRC_HI_FRAC * Rcav), S.shape[1] - 2)
    kk = np.argmax(G[:, clo:chi], axis=1)
    rr = rs[clo + kk]
    pts = np.column_stack([cx + rr * cos_t, cy + rr * sin_t])
    circ_R, circ_n, circ_rms = fit_with_rejection(pts[:, 0], pts[:, 1])

    rlo, rhi = int(CIRC_RIM_LO * Rcav), min(int(CIRC_RIM_HI * Rcav), S.shape[1] - 2)
    kk = np.argmax(G[:, rlo:rhi], axis=1)
    rr = rs[rlo + kk]
    pts = np.column_stack([cx + rr * cos_t, cy + rr * sin_t])
    circ_rim_R, _, _ = fit_with_rejection(pts[:, 0], pts[:, 1])

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
            ring["dx"] = float(2.0 * np.mean(rth * cos_t[good]))
            ring["dy"] = float(2.0 * np.mean(rth * sin_t[good]))
            ring["ecc"] = float(np.hypot(ring["dx"], ring["dy"]))
        else:
            ring["ring_R"] = ""
            ring["dx"] = ""
            ring["dy"] = ""
            ring["ecc"] = ""
        ring["frac_ray"] = float(rth.size) / NRAY
        ring["norm"] = float(r0) / Rcav

    pic = {"cx": cx, "cy": cy, "Rcav": Rcav, "dip_r": dip_r, "dip_prom": dip_prom,
           "grad_r": r_grad, "circ_r": circ_R, "circ_n": float(circ_n),
           "circ_rms": circ_rms, "circ_rim_r": circ_rim_R}

    # ---- per-radius curve, band free ---------------------------------------
    # For every normalised radius the curve carries (a) the annular dip strength
    # the shipped method uses and (b) the per-ray geometry of any dark ring found
    # there: how often it is found, how far its centre sits from the cavity
    # centre, and how much its radius varies with angle. Nothing here is
    # restricted to a hand-picked band, which is what lets the two
    # discriminators be read off a curve rather than a chosen ring.
    curve = []
    u = CURVE_LO
    while u <= CURVE_HI + 1e-9:
        r_c = u * Rcav
        i_c = int(round(r_c))
        if 0 < i_c < len(ps):
            w = min(W, i_c)
            lo_i, hi_i = max(0, i_c - w), min(len(ps), i_c + w + 1)
            prom_u = float(ps[lo_i:hi_i].max() - ps[i_c])
        else:
            prom_u = float("nan")
        win = int(max(2.0, CURVE_WIN_FRAC * Rcav))
        wlo = max(0, int(r_c) - win)
        whi = min(S.shape[1], int(r_c) + win + 1)
        seg2 = S[:, wlo:whi]
        p2 = seg2.max(axis=1, keepdims=True) - seg2
        k2 = np.argmax(p2, axis=1)
        pk = p2[np.arange(NRAY), k2]
        good = pk > CURVE_RAY_GATE
        rth = rs[wlo + k2][good]
        if rth.size >= 30:
            dxu = float(2.0 * np.mean(rth * cos_t[good]))
            dyu = float(2.0 * np.mean(rth * sin_t[good]))
            ecc = float(np.hypot(dxu, dyu))
            sd_r = float(rth.std())
        else:
            ecc = float("nan")
            sd_r = float("nan")
        curve.append({"u": round(u, 3), "prom": prom_u,
                      "detrate": float(rth.size) / NRAY,
                      "ecc": ecc, "sd_r": sd_r,
                      "r_mean": float(rth.mean()) if rth.size else float("nan")})
        u += CURVE_STEP
    return md5, {"flag": "ok", "pic": pic, "rings": rings, "curve": curve}


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
        return ["\t".join(["P", tag, "", relpath, "", "", ""] + ["missing"] + [""] * 8)]
    try:
        md5, res = measure(full)
    except Exception as exc:  # report the real failure, never invent a number
        return ["\t".join(["P", tag, "", relpath, "", "", ""]
                          + ["err:" + type(exc).__name__] + [""] * 8)]
    if res["flag"] != "ok":
        return ["\t".join(["P", tag, md5, relpath, "", "", ""]
                          + [res["flag"]] + [""] * 8)]
    p = res["pic"]
    rows = ["\t".join(["P", tag, md5, relpath, fmt(p["cx"]), fmt(p["cy"]),
                       fmt(p["Rcav"]), "ok", fmt(p["dip_r"]), fmt(p["dip_prom"]),
                       fmt(p["grad_r"]), fmt(p["circ_r"]), fmt(p["circ_n"]),
                       fmt(p["circ_rms"]), fmt(p["circ_rim_r"]),
                       str(len(res["rings"]))])]
    for i, ring in enumerate(res["rings"]):
        rows.append("\t".join(["R", md5, str(i), fmt(ring["radius"]),
                               fmt(ring["depth"]), fmt(ring["width"]),
                               fmt(ring["sharp"]), fmt(ring.get("ring_R", "")),
                               fmt(ring.get("dx", "")), fmt(ring.get("dy", "")),
                               fmt(ring.get("ecc", "")), fmt(ring["frac_ray"]),
                               fmt(ring["norm"])]))
    for c in res["curve"]:
        rows.append("\t".join(["C", md5, fmt(c["u"]), fmt(c["prom"]),
                               fmt(c["detrate"]), fmt(c["ecc"]), fmt(c["sd_r"]),
                               fmt(c["r_mean"])]))
    return rows


def main():
    argv = sys.argv[1:]
    root = ROOT_DEFAULT
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]
    jobs = 12
    if "--jobs" in argv:
        jobs = int(argv[argv.index("--jobs") + 1])

    if "--emit-repro" in argv:
        # Reproduce the prior script's sample exactly: same glob form, same seed,
        # same call. Only the sampled relpaths are printed.
        random.seed(7)
        prod = glob.glob(os.path.join(root, PROD_SUBDIR, "*Pass1*.bmp"))
        for path in random.sample(prod, 200):
            sys.stdout.write(os.path.relpath(path, root) + "\n")
        return

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
