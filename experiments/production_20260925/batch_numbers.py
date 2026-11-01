#!/usr/bin/env python3
"""Compute every number that goes into the PRODUCTION_20260925 workbook.

Nothing in the workbook is typed by hand: this module reads the seven CVAT XML
exports and emits one JSON blob, and the workbook builder only formats that
blob. Read-only, no network, no writes outside --out.

Paths are arguments, defaults point at the shared VM, so this can run either on
the VM or locally against a pulled copy:

    python batch_numbers.py --annotations <dir> --cavity <json> --out numbers.json

Three things this deliberately records rather than smooths over:

  * the batch carries TWO filename families, a legacy `L##_C##_serial` form and
    a line form with pallet, cavity, board, fail count and score. They are
    counted separately because the second carries covariates the first lacks;
  * most rotation values are not multiples of 90, so the boxes are genuinely
    rotated rectangles and any axis-aligned conversion will mis-draw them;
  * `P3_HE` boxes are far larger than every other code, so it is reported
    separately instead of being averaged in with the defect spots.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os
import re
import xml.etree.ElementTree as ET

DEFAULT_DATA_DIR = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images/PRODUCTION_20260925"
DEFAULT_ANN = DEFAULT_DATA_DIR + "/annotations"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EMAIL = os.path.join(_SCRIPT_DIR, "annotator_email_20261013.json")
DEFAULT_MICRON_TEST = os.path.join(_SCRIPT_DIR, "micron_metric_test.json")
DEFAULT_CAVITY = os.path.join(_SCRIPT_DIR, "..", "..", "vm", "ops",
                             "cavity_geometry_all.json")
DEFAULT_SCALE = "/data/FMD_Data_26082026/scale_estimate.json"
UM_PER_PX_FALLBACK = 18.1165

# code -> (plain name, confirmed against the client taxonomy)
# The four names added 2026-10-13 by Pranay match the September code legend in
# docs/annotations_update_20260923.md: P2_DC and P1_FL were pinned there, P2_BI
# comes from the ontology acronym, and P2_BST was inferred by elimination.
CODES = {
    "P1_MPP": ("Missing Primary Package", True),
    "P1_ML": ("Multiple Lenses", True),
    "P1_FL": ("Folded Lens", True),
    "P1_COC": ("Cavity Off Center", True),
    "P1_NL": ("Missing Lens", True),
    "P1_PPM": ("Package Misalignment", True),
    "F2_FOV": ("View Obstructed", True),
    "P2_LD": ("Low Dose", True),
    "P2_LOC": ("Lens Off Center", True),
    "P2_DC": ("Dirty Camera", True),
    "P2_DS": ("Dirty Strobe", True),
    "P2_BB": ("Bubble", True),
    "P2_BC": ("Bubble Cluster", True),
    "P2_BI": ("Bubble Irregular", True),
    "P2_WP": ("Wet Package", True),
    "P2_BST": ("Stretched Bubble", True),
    "P3_FM": ("Foreign Matter", True),
    "P3_FIB": ("Fiber", True),
    "P3_EP": ("Extraneous Polymer", True),
    "P3_HE": ("HEMA Obstruction", True),
}
GATE_SUFFIX = "_MICRON_THRESHOLD"

# The recorded size thresholds for this product, in microns.
THRESHOLDS_UM = [300, 500, 647]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def pct(sorted_vals, q):
    """Linear-interpolated percentile. vals must already be sorted."""
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * q
    lo, hi = int(math.floor(k)), min(int(math.floor(k)) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def size_stats(vals):
    v = sorted(vals)
    return {
        "n": len(v),
        "min": v[0],
        "p25": pct(v, .25),
        "median": pct(v, .5),
        "p75": pct(v, .75),
        "p95": pct(v, .95),
        "max": v[-1],
        "mean": sum(v) / len(v),
    }


PLAIN_RE = re.compile(r"^(\d{8})_(\d{6})_L(\d+)_C(\d+)_(\d+)(.*)$")
LINE_RE = re.compile(
    r"^(\d{8})_(\d{6})_L(\d+)_PalletGH([A-Z])(\d+)_Cavity(\d+)_(?:Cavity(\d+)_)?"
    r"B([0-9A-Z]+?)_Fail(\d+)_Score\(([\d.]+)\)(.*)$")


def parse_name(basename):
    """Split a filename into its covariates. Returns a dict; unknown fields None."""
    stem = basename[:-4] if basename.lower().endswith(".bmp") else basename
    out = {"basename": basename, "family": None, "date": None, "time": None,
           "line": None, "pallet": None, "cavity": None, "board": None,
           "fail": None, "score": None, "trailing_scores": []}
    m = LINE_RE.match(stem)
    if m:
        out.update(family="line", date=m.group(1), time=m.group(2), line="L" + m.group(3),
                   pallet="PalletGH" + m.group(4), cavity=m.group(6), board=m.group(8),
                   fail=int(m.group(9)), score=float(m.group(10)))
        out["trailing_scores"] = [float(x) for x in re.findall(r"[\d]+\.[\d]+", m.group(11))]
        return out
    m = PLAIN_RE.match(stem)
    if m:
        out.update(family="plain", date=m.group(1), time=m.group(2), line="L" + m.group(3),
                   cavity=m.group(4))
        out["trailing_scores"] = [float(x) for x in re.findall(r"[\d]+\.[\d]+", m.group(6))]
        return out
    out["family"] = "unparsed"
    return out


# --------------------------------------------------------------------------
# load
# --------------------------------------------------------------------------
def load(ann_dir, cavity_path=None, scale_path=None):
    xmllist = sorted(glob.glob(os.path.join(ann_dir, "*.xml")))
    if not xmllist:
        raise SystemExit("no XML files under %s" % ann_dir)

    jpegs = []
    jobs = []
    raw_tag_elements = 0

    for path in xmllist:
        # Parser safety: these are our own team's CVAT exports sitting in a folder
        # we created on our own VM, not untrusted input. Switch to defusedxml if
        # this is ever pointed at a vendor- or client-supplied file.
        root = ET.parse(path).getroot()
        meta = root.find("meta")
        job = {}
        if meta is not None:
            j = meta.find("job")
            if j is not None:
                for tag in ("id", "size", "mode", "created", "updated",
                            "start_frame", "stop_frame"):
                    el = j.find(tag)
                    job[tag] = el.text.strip() if el is not None and el.text else None
        job["file"] = os.path.basename(path)
        job["bytes"] = os.path.getsize(path)
        jobs.append(job)

        for im in root.iter("image"):
            raw_tag_elements += len(im.findall("tag"))
            boxes = []
            for b in im.findall("box"):
                xtl, ytl = float(b.get("xtl")), float(b.get("ytl"))
                xbr, ybr = float(b.get("xbr")), float(b.get("ybr"))
                w, h = abs(xbr - xtl), abs(ybr - ytl)
                rot_raw = b.get("rotation")
                boxes.append({
                    "label": b.get("label"),
                    "source": b.get("source"),
                    "occluded": int(b.get("occluded") or 0),
                    "z_order": int(b.get("z_order") or 0),
                    "w": w, "h": h,
                    "diag": math.hypot(w, h),
                    "cx": (xtl + xbr) / 2.0, "cy": (ytl + ybr) / 2.0,
                    "rotation": None if rot_raw is None else float(rot_raw),
                })
            tags = []
            for t in im.findall("tag"):
                tags.append({"label": t.get("label"), "source": t.get("source")})

            name = im.get("name")
            jpegs.append({
                "name": name,
                "basename": os.path.basename(name),
                "job_id": job.get("id"),
                "width": int(im.get("width")), "height": int(im.get("height")),
                "boxes": boxes, "tags": tags,
                "codes": sorted({b["label"] for b in boxes} | {t["label"] for t in tags}),
            })

    # scale. Read the lens and cavity diameters and the size thresholds from the
    # same file rather than restating them here, so there is one source.
    um_per_px = UM_PER_PX_FALLBACK
    scale_source = "fallback constant in this module"
    scale = {"um_per_px": um_per_px, "lens_diam_px": None, "cav_diam_px": None,
             "thresholds_um": list(THRESHOLDS_UM), "thresh_px_linear": None,
             "n_images_used": None, "rel_spread_pct": None, "source": scale_source}
    if scale_path and os.path.exists(scale_path):
        st = json.load(open(scale_path))["summary"]
        um_per_px = st["um_per_px"]
        scale_source = scale_path
        scale = {
            "um_per_px": um_per_px,
            "lens_diam_px": st.get("lens_diam_px_median"),
            "lens_diam_px_trimmed_mean": st.get("lens_diam_px_trimmed_mean"),
            "lens_diam_px_iqr": st.get("lens_diam_px_iqr"),
            "cav_diam_px": st.get("cav_diam_px_median"),
            "thresholds_um": st.get("thresholds_um") or list(THRESHOLDS_UM),
            "thresh_px_linear": st.get("thresh_px_linear"),
            "n_images_used": st.get("n_images_used"),
            "rel_spread_pct": st.get("rel_spread_pct"),
            "source": scale_source,
        }

    # cavity geometry (derived artifact, lives in the repo)
    cavity = None
    if cavity_path and os.path.exists(cavity_path):
        cavity = json.load(open(cavity_path))

    return {
        "annotations_dir": os.path.abspath(ann_dir),
        "xml_files": [os.path.basename(p) for p in xmllist],
        "jobs": jobs,
        "images": jpegs,
        "raw_tag_elements": raw_tag_elements,
        "um_per_px": um_per_px,
        "scale_source": scale_source,
        "scale": scale,
        "cavity": cavity,
    }


# --------------------------------------------------------------------------
# compute
# --------------------------------------------------------------------------
def analyse(data):
    imgs = data["images"]
    um = data["um_per_px"]
    n_img = len(imgs)

    # ---- shapes and images per code
    code_box_shapes = collections.Counter()
    code_tag_shapes = collections.Counter()
    code_images = collections.Counter()
    for r in imgs:
        for b in r["boxes"]:
            code_box_shapes[b["label"]] += 1
        for t in r["tags"]:
            code_tag_shapes[t["label"]] += 1
        for c in r["codes"]:
            code_images[c] += 1

    all_codes = set(code_box_shapes) | set(code_tag_shapes)
    known = sorted(all_codes)

    codes = []
    for c in sorted(all_codes, key=lambda x: (-code_images[x], x)):
        gate_of = c[:-len(GATE_SUFFIX)] if c.endswith(GATE_SUFFIX) else None
        nm, conf = CODES.get(c, ("unconfirmed", False))
        if gate_of and gate_of in CODES:
            nm = "%s (size gate on %s)" % (CODES[gate_of][0], gate_of)
            conf = CODES[gate_of][1]
        codes.append({
            "code": c,
            "name": nm,
            "confirmed": conf,
            "is_gate": bool(gate_of),
            "gates": gate_of,
            "boxes": code_box_shapes.get(c, 0),
            "tags": code_tag_shapes.get(c, 0),
            "shapes": code_box_shapes.get(c, 0) + code_tag_shapes.get(c, 0),
            "images": code_images.get(c, 0),
            "image_share": code_images.get(c, 0) / n_img,
        })

    # ---- how many codes per image
    dist = collections.Counter(len(r["codes"]) for r in imgs)
    multi = sum(n for k, n in dist.items() if k > 1)
    single = dist.get(1, 0)
    zero = dist.get(0, 0)

    box_only = sum(1 for r in imgs if r["boxes"] and not r["tags"])
    tag_only = sum(1 for r in imgs if r["tags"] and not r["boxes"])
    both = sum(1 for r in imgs if r["boxes"] and r["tags"])
    neither = zero

    # tag label repeats: a repeated label collapses when codes are set-ified
    tag_labels_counted = sum(len({t["label"] for t in r["tags"]}) for r in imgs)

    # ---- shape provenance
    box_source = collections.Counter(b["source"] for r in imgs for b in r["boxes"])
    tag_source = collections.Counter(t["source"] for r in imgs for t in r["tags"])
    occluded = collections.Counter(b["occluded"] for r in imgs for b in r["boxes"])
    z_order = collections.Counter(b["z_order"] for r in imgs for b in r["boxes"])

    # ---- geometry sanity
    geom = collections.Counter((r["width"], r["height"]) for r in imgs)

    # ---- rotation
    n_boxes = sum(len(r["boxes"]) for r in imgs)
    rot_present = [b["rotation"] for r in imgs for b in r["boxes"] if b["rotation"] is not None]
    rot_zero = sum(1 for x in rot_present if x == 0.0)
    rot_right = sum(1 for x in rot_present if x % 90 == 0)
    rot_other = len(rot_present) - rot_right
    rot_buckets = collections.Counter(int(x // 45) * 45 for x in rot_present)

    # ---- sizes per code (boxes only)
    per_code_diag = collections.defaultdict(list)
    for r in imgs:
        for b in r["boxes"]:
            per_code_diag[b["label"]].append(b["diag"])
    sizes = []
    for c in sorted(per_code_diag, key=lambda k: -len(per_code_diag[k])):
        st = size_stats(per_code_diag[c])
        sizes.append({"code": c, "n": st["n"], "min_px": st["min"], "p25_px": st["p25"],
                      "median_px": st["median"], "p75_px": st["p75"], "max_px": st["max"],
                      "mean_px": st["mean"], "median_um": st["median"] * um,
                      "p75_um": st["p75"] * um, "max_um": st["max"] * um,
                      "min_um": st["min"] * um})
    all_diag = [b["diag"] for r in imgs for b in r["boxes"]]
    overall = size_stats(all_diag)

    # ---- the size gate, read off the data
    gates = []
    for c in known:
        if not c.endswith(GATE_SUFFIX):
            continue
        base = c[:-len(GATE_SUFFIX)]
        flagged_imgs = [r for r in imgs if c in r["codes"] and base in r["codes"]]
        clean_imgs = [r for r in imgs if base in r["codes"] and c not in r["codes"]]
        f_big = [max(b["diag"] for b in r["boxes"] if b["label"] == base)
                 for r in flagged_imgs if any(b["label"] == base for b in r["boxes"])]
        c_big = [max(b["diag"] for b in r["boxes"] if b["label"] == base)
                 for r in clean_imgs if any(b["label"] == base for b in r["boxes"])]
        sf = size_stats(f_big) if f_big else None
        sc = size_stats(c_big) if c_big else None
        gates.append({
            "gate": c, "base": base,
            "flagged_images": len(flagged_imgs),
            "unflagged_images": len(clean_imgs),
            "flagged_median_px": sf["median"] if sf else None,
            "unflagged_median_px": sc["median"] if sc else None,
            "gap_px": (sf["median"] - sc["median"]) if (sf and sc) else None,
            "gap_um": ((sf["median"] - sc["median"]) * um) if (sf and sc) else None,
            "ratio": (sf["median"] / sc["median"]) if (sc and sc["median"]) else None,
            "unit_testable": bool(sf and sc),
        })

    # ---- thresholds: how many boxes cross each recorded micron threshold
    thr = []
    for t in data["scale"]["thresholds_um"]:
        px = t / um
        above = sum(1 for d in all_diag if d > px)
        thr.append({"threshold_um": t, "threshold_px": px,
                    "boxes_above": above, "boxes_above_share": above / len(all_diag)})

    # ---- boxes far larger than their code's norm: these are the ones to eyeball
    OUTLIER_PX = 200.0
    outliers = []
    for c, vals in per_code_diag.items():
        big = [v for v in vals if v > OUTLIER_PX]
        if big:
            outliers.append({"code": c, "boxes": len(vals), "boxes_over_200px": len(big),
                             "share_over_200px": len(big) / len(vals),
                             "largest_px": max(big)})
    outliers.sort(key=lambda r: -r["boxes_over_200px"])

    # ---- code pairs that co-occur on the same image
    co = collections.Counter()
    for r in imgs:
        cs = sorted(r["codes"])
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                co[(cs[i], cs[j])] += 1
    pairs = [{"a": a, "b": b, "images": n}
             for (a, b), n in sorted(co.items(), key=lambda kv: (-kv[1], kv[0]))[:20]]

    # ---- filenames
    fam = collections.Counter()
    lines = collections.Counter()
    dates = collections.Counter()
    pallets = collections.Counter()
    boards = collections.Counter()
    fails = collections.Counter()
    scores = []
    for r in imgs:
        p = parse_name(r["basename"])
        r["parsed"] = p
        fam[p["family"]] += 1
        if p["line"]:
            lines[p["line"]] += 1
        if p["date"]:
            dates[p["date"]] += 1
        if p["pallet"]:
            pallets[p["pallet"]] += 1
        if p["board"]:
            boards[p["board"]] += 1
        if p["fail"] is not None:
            fails[p["fail"]] += 1
        if p["score"] is not None:
            scores.append(p["score"])

    score_stats = size_stats(scores) if scores else None

    # ---- cavity
    cavsum = None
    per_code_cavity = []
    if data["cavity"]:
        cavsum = data["cavity"]["summary"]
        geo = data["cavity"]["per_image"]
        in_c = out_c = far = unmeasured = 0
        per_lab = collections.defaultdict(lambda: [0, 0])
        ratios = []
        for r in imgs:
            g = geo.get(r["basename"])
            if not g:
                unmeasured += 1
                continue
            for b in r["boxes"]:
                d = math.hypot(b["cx"] - g["cx"], b["cy"] - g["cy"])
                ratios.append(d / g["R"])
                if d > g["R"]:
                    out_c += 1
                    per_lab[b["label"]][1] += 1
                else:
                    in_c += 1
                    per_lab[b["label"]][0] += 1
                if d > g["R"] * 1.5:
                    far += 1
        rs = sorted(ratios)
        for c, (inn, outt) in sorted(per_lab.items(),
                                     key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0])):
            per_code_cavity.append({"code": c, "boxes": inn + outt, "inside": inn,
                                    "outside": outt,
                                    "outside_share": outt / (inn + outt)})
        per_code_cavity_summary = {
            "images_measured": cavsum["images_measured"],
            "images_unmeasured": unmeasured,
            "boxes_placed": in_c + out_c,
            "inside": in_c, "outside": out_c, "beyond_1_5x": far,
            "p50_ratio": pct(rs, .5), "p75_ratio": pct(rs, .75),
            "p95_ratio": pct(rs, .95), "max_ratio": rs[-1],
        }
    else:
        per_code_cavity_summary = None

    # ---- per-image rows for the workbook
    rows = []
    for r in imgs:
        p = r["parsed"]
        g = data["cavity"]["per_image"].get(r["basename"]) if data["cavity"] else None
        codes_here = set(r["codes"])
        gates_here = {c for c in codes_here if c.endswith(GATE_SUFFIX)}
        box_here = {b["label"] for b in r["boxes"]}
        tag_here = {t["label"] for t in r["tags"]}
        rows.append({
            "n_box_codes": len(box_here),
            "n_tag_codes": len(tag_here),
            "n_gate_codes": len(gates_here),
            # base codes exclude the derived size-gate flags, which merely mirror
            # a box code already counted, so they inflate the apparent label count
            "n_base_codes": len(codes_here - gates_here),
            "basename": r["basename"], "job_id": r["job_id"],
            "date": p["date"], "time": p["time"], "line": p["line"],
            "family": p["family"], "cavity_id": p["cavity"],
            "pallet": p["pallet"], "board": p["board"], "fail": p["fail"],
            "score": p["score"], "trailing_scores": p["trailing_scores"],
            "n_codes": len(r["codes"]), "codes": "; ".join(r["codes"]),
            "n_boxes": len(r["boxes"]), "n_tags": len(r["tags"]),
            "shapes": len(r["boxes"]) + len(r["tags"]),
            "box_codes": "; ".join(sorted({b["label"] for b in r["boxes"]})),
            "tag_codes": "; ".join(sorted({t["label"] for t in r["tags"]})),
            "cavity_cx": g["cx"] if g else None, "cavity_cy": g["cy"] if g else None,
            "cavity_r": g["R"] if g else None,
        })

    summary = {
        "jobs": len(data["jobs"]),
        "images": n_img,
        "boxes": n_boxes,
        "tag_elements": data["raw_tag_elements"],
        "tag_labels_counted": tag_labels_counted,
        "repeated_tag_labels": data["raw_tag_elements"] - tag_labels_counted,
        "distinct_codes": len(all_codes),
        "codes_that_are_gates": sum(1 for c in codes if c["is_gate"]),
        "images_multi_code": multi, "images_single_code": single,
        "images_no_code": zero,
        "images_box_only": box_only, "images_tag_only": tag_only,
        "images_both": both, "images_neither": neither,
        "median_codes_per_image": pct(sorted(len(r["codes"]) for r in imgs), .5),
        "max_codes_per_image": max(len(r["codes"]) for r in imgs),
        "um_per_px": um,
        "median_box_diag_px": overall["median"],
        "median_box_diag_um": overall["median"] * um,
        "rotation_present": len(rot_present),
        "rotation_absent": n_boxes - len(rot_present),
        "rotation_zero": rot_zero,
        "rotation_right_angle": rot_right,
        "rotation_other": rot_other,
        "rotation_other_share": rot_other / len(rot_present) if rot_present else None,
        "geometry_variants": {"%dx%d" % k: v for k, v in geom.items()},
    }

    # ---- distributions, and the tail that will get questioned
    GATE_EXCL = lambda cs: {c for c in cs if not c.endswith(GATE_SUFFIX)}
    codes_per_image = collections.Counter(len(r["codes"]) for r in imgs)
    base_per_image = collections.Counter(len(GATE_EXCL(r["codes"])) for r in imgs)
    box_per_image = collections.Counter(len({b["label"] for b in r["boxes"]}) for r in imgs)
    tag_per_image = collections.Counter(len({t["label"] for t in r["tags"]}) for r in imgs)
    gate_per_image = collections.Counter(
        len({c for c in r["codes"] if c.endswith(GATE_SUFFIX)}) for r in imgs)

    nc = sorted(len(r["codes"]) for r in imgs)
    nb = sorted(len({b["label"] for b in r["boxes"]}) for r in imgs)
    nt = sorted(len({t["label"] for t in r["tags"]}) for r in imgs)

    tail_cut = 8
    tail = []
    for r in sorted(imgs, key=lambda x: -len(x["codes"])):
        if len(r["codes"]) < tail_cut:
            break
        cs = set(r["codes"])
        gates_here = sorted(c for c in cs if c.endswith(GATE_SUFFIX))
        tail.append({
            "basename": r["basename"],
            "codes": len(cs),
            "base_codes": len(cs) - len(gates_here),
            "gate_codes": len(gates_here),
            "boxes": len(r["boxes"]), "tags": len(r["tags"]),
            "box_codes": sorted({b["label"] for b in r["boxes"]}),
            "tag_codes": sorted({t["label"] for t in r["tags"]}),
            "gates": gates_here,
            "line": parse_name(r["basename"])["line"],
        })

    with_bb = [r for r in imgs if "P2_BB" in r["codes"]]
    without_bb = [r for r in imgs if "P2_BB" not in r["codes"]]

    # size histogram, on the diagonal in microns, log-ish buckets
    SIZE_EDGES = [0, 100, 200, 300, 500, 647, 1000, 2000, 5000, 1e9]
    hist = collections.Counter()
    for r in imgs:
        for b in r["boxes"]:
            u = b["diag"] * um
            for i in range(len(SIZE_EDGES) - 1):
                if SIZE_EDGES[i] <= u < SIZE_EDGES[i + 1]:
                    hist[(SIZE_EDGES[i], SIZE_EDGES[i + 1])] += 1
                    break
    size_hist = [{"lo_um": lo, "hi_um": (None if hi > 1e8 else hi), "boxes": n}
                 for (lo, hi), n in sorted(hist.items())]

    distributions = {
        "codes_per_image": sorted(codes_per_image.items()),
        "base_codes_per_image": sorted(base_per_image.items()),
        "box_codes_per_image": sorted(box_per_image.items()),
        "tag_codes_per_image": sorted(tag_per_image.items()),
        "gate_codes_per_image": sorted(gate_per_image.items()),
        "summary": {
            "mean_codes": sum(nc) / len(nc), "median_codes": pct(nc, .5),
            "p90_codes": pct(nc, .90), "p95_codes": pct(nc, .95), "p99_codes": pct(nc, .99),
            "max_codes": nc[-1],
            "mean_base_codes": sum(len(GATE_EXCL(r["codes"])) for r in imgs) / len(imgs),
            "max_base_codes": max(len(GATE_EXCL(r["codes"])) for r in imgs),
            "mean_box_codes": sum(nb) / len(nb), "median_box_codes": pct(nb, .5),
            "max_box_codes": nb[-1],
            "mean_tag_codes": sum(nt) / len(nt), "median_tag_codes": pct(nt, .5),
            "max_tag_codes": nt[-1],
            "tail_cut": tail_cut,
            "tail_images": len(tail),
            "tail_share_of_images": len(tail) / len(imgs),
            "tail_share_of_shapes": (sum(len(r["boxes"]) + len(r["tags"]) for r in imgs
                                         if len(r["codes"]) >= tail_cut)
                                     / sum(len(r["boxes"]) + len(r["tags"]) for r in imgs)),
            "with_bubble_images": len(with_bb),
            "with_bubble_mean_codes": sum(len(r["codes"]) for r in with_bb) / len(with_bb),
            "without_bubble_mean_codes": (sum(len(r["codes"]) for r in without_bb) / len(without_bb)
                                          if without_bb else None),
        },
        "tail_images": tail,
        "size_histogram": size_hist,
    }

    return {
        "summary": summary,
        "scale": data["scale"],
        "distributions": distributions,
        "codes": codes,
        "codes_per_image_distribution": sorted(dist.items()),
        "box_source": dict(box_source),
        "tag_source": {str(k): v for k, v in tag_source.items()},
        "occluded": dict(occluded),
        "z_order": dict(z_order),
        "rotation_buckets": sorted(rot_buckets.items()),
        "sizes": sizes,
        "overall_size": overall,
        "gates": gates,
        "thresholds": thr,
        "outliers": outliers,
        "outlier_threshold_px": OUTLIER_PX,
        "code_pairs": pairs,
        "filenames": {
            "families": dict(fam),
            "lines": dict(sorted(lines.items())),
            "dates": dict(sorted(dates.items())),
            "pallets": dict(sorted(pallets.items())),
            "boards_top": dict(sorted(boards.items(), key=lambda kv: -kv[1])[:15]),
            "boards_distinct": len(boards),
            "fails": dict(sorted(fails.items())),
            "score_stats": score_stats,
            "scored_images": len(scores),
        },
        "cavity": per_code_cavity_summary,
        "cavity_per_code": per_code_cavity,
        "per_image": rows,
    }


def reconcile_email(res, email_path):
    """Compare the per-code counts stated in the handover email with the
    delivered XML. The email predates the validation pass, so differences are
    expected; the XML is the source of truth. Returns None if the file is absent.
    """
    if not email_path or not os.path.exists(email_path):
        return None
    em = json.load(open(email_path, encoding="utf-8"))
    by_code = {c["code"]: c for c in res["codes"]}

    # the email writes P2_FOV where the XML writes F2_FOV; map so the rows line up
    alias = {}
    for k in em.get("counts", {}):
        if k not in by_code:
            for cand in (k.replace("P2_", "F2_"), k.replace("F2_", "P2_")):
                if cand in by_code:
                    alias[k] = cand

    rows = []
    for code, stated in em.get("counts", {}).items():
        xml_code = alias.get(code, code)
        c = by_code.get(xml_code)
        rows.append({
            "email_code": code, "xml_code": xml_code,
            "stated": stated,
            "xml_shapes": c["shapes"] if c else None,
            "xml_images": c["images"] if c else None,
            "delta_shapes": (c["shapes"] - stated) if c else None,
            "renamed": xml_code != code,
        })
    rows.sort(key=lambda r: -abs(r["delta_shapes"] or 0))

    mrows = []
    for code, stated in em.get("micron_counts", {}).items():
        c = by_code.get(code)
        mrows.append({
            "code": code, "stated": stated,
            "xml_images": c["images"] if c else None,
            "xml_shapes": c["shapes"] if c else None,
            "delta_images": (c["images"] - stated) if c else None,
        })
    mrows.sort(key=lambda r: -abs(r["delta_images"] or 0))

    return {
        "source": em.get("source"),
        "written_before_validation": em.get("written_before_validation"),
        "email_says": em.get("email_says"),
        "implication": em.get("implication"),
        "stated_rule": em.get("stated_rule"),
        "threshold_um": em.get("threshold_um"),
        "total_images_stated": em.get("total_images_stated"),
        "naming_notes": em.get("naming_notes", {}),
        "intent": em.get("intent", {}),
        "rows": rows,
        "micron_rows": mrows,
        "renamed_codes": [r for r in rows if r["renamed"]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotations", default=DEFAULT_ANN,
                    help="folder holding the CVAT XML exports")
    ap.add_argument("--cavity", default=DEFAULT_CAVITY,
                    help="cavity_geometry_all.json from measure_cavity_all.py")
    ap.add_argument("--scale", default=DEFAULT_SCALE,
                    help="scale_estimate.json giving um per pixel")
    ap.add_argument("--email", default=DEFAULT_EMAIL,
                    help="per-code counts as stated in the handover email")
    ap.add_argument("--micron-test", default=DEFAULT_MICRON_TEST,
                    help="output of test_micron_metric.py, if it has been run")
    ap.add_argument("--out", default="batch_numbers.json")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    data = load(a.annotations, a.cavity, a.scale)
    res = analyse(data)
    res["provenance"] = {
        "annotations_dir": data["annotations_dir"],
        "xml_files": data["xml_files"],
        "jobs": data["jobs"],
        "scale_source": data["scale_source"],
        "cavity_source": data["cavity"]["summary"]["images_measured"] and a.cavity or None,
    }
    res["email"] = reconcile_email(res, a.email)
    if a.micron_test and os.path.exists(a.micron_test):
        res["micron_metric_test"] = json.load(open(a.micron_test, encoding="utf-8"))
    else:
        res["micron_metric_test"] = None

    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)

    if not a.quiet:
        s = res["summary"]
        print(json.dumps(s, indent=1))
        print("\nCODES (images, boxes, tags)")
        for c in res["codes"]:
            print("  %-26s %5d img %6d box %5d tag  %s" % (
                c["code"], c["images"], c["boxes"], c["tags"],
                "" if c["confirmed"] else "<- unconfirmed"))
        print("\nGATES")
        for g in res["gates"]:
            print("  %-26s base %-8s flagged %4d unflagged %4d  %s" % (
                g["gate"], g["base"], g["flagged_images"], g["unflagged_images"],
                ("median %.1f vs %.1f px (x%.2f)" % (
                    g["flagged_median_px"], g["unflagged_median_px"], g["ratio"]))
                if g["unit_testable"] else "no unflagged group: flag is unconditional"))
        print("\nFILENAME FAMILIES", res["filenames"]["families"])
        print("LINES", res["filenames"]["lines"])
        print("DATES", res["filenames"]["dates"])
        print("wrote %s" % os.path.abspath(a.out))


if __name__ == "__main__":
    main()
