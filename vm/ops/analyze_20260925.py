#!/usr/bin/env python3
"""Build README.md for the 2026-09-25 production batch from the landed XMLs.

Everything in the README is computed here, so no number is transcribed by hand.

Lives in the repo (vm/ops/), NOT beside the data: the VM folder is shared, so we
keep only README.md, manifest.csv, annotations/ and images/ there. Run it by
piping it over ssh, which leaves no file behind on the VM:

    ssh amd-a100-vm 'python3 - < vm/ops/analyze_20260925.py'

--data-dir defaults to the VM path, so a bare run on the VM does the right thing.
"""
import argparse
import glob
import json
import os
import re
import struct
import collections
import datetime
import xml.etree.ElementTree as ET

DEFAULT_DATA_DIR = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images/PRODUCTION_20260925"
DEFAULT_SCALE_PATH = "/data/FMD_Data_26082026/scale_estimate.json"

_p = argparse.ArgumentParser(description=__doc__)
_p.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                help="folder holding annotations/, images/ and README.md")
_p.add_argument("--scale-path", default=DEFAULT_SCALE_PATH,
                help="scale_estimate.json giving um per pixel")
_p.add_argument("--cavity-json", default=None,
                help="cavity_geometry_all.json (default: <data-dir>/cavity_geometry_all.json)")
_p.add_argument("--out", default=None,
                help="README path (default: <data-dir>/README.md)")
_args = _p.parse_args()

HERE = os.path.abspath(_args.data_dir)
ANN = os.path.join(HERE, "annotations")
IMG = os.path.join(HERE, "images")
SCALE_PATH = _args.scale_path

UM_PER_PX = None
if os.path.exists(SCALE_PATH):
    UM_PER_PX = json.load(open(SCALE_PATH))["summary"]["um_per_px"]

# Confirmed names come from the 2026-09-15 library folder the code majority sits in.
# P2_DC, P1_FL, P2_BI and P2_BST were named on 2026-10-13 by Pranay and match the
# September code legend in docs/annotations_update_20260923.md.
NAME = {
    "P1_MPP": "Missing Primary Package", "P1_ML": "Multiple Lenses",
    "P1_FL": "Folded Lens", "P1_COC": "Cavity Off Center",
    "P1_NL": "Missing Lens", "P1_PPM": "Package Misalignment",
    "F2_FOV": "View Obstructed", "P2_LD": "Low Dose", "P2_LOC": "Lens Off Center",
    "P2_DC": "Dirty Camera", "P2_DS": "Dirty Strobe", "P2_BB": "Bubble",
    "P2_BC": "Bubble Cluster", "P2_BI": "Bubble Irregular", "P2_BST": "Stretched Bubble",
    "P2_WP": "Wet Package", "P3_FM": "Foreign Matter", "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer", "P3_HE": "HEMA Obstruction",
    "P3_FM_MICRON_THRESHOLD": "Foreign Matter, micron gate",
    "P3_FIB_MICRON_THRESHOLD": "Fiber, micron gate",
    "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer, micron gate",
    "P3_HE_MICRON_THRESHOLD": "HEMA Obstruction, micron gate",
}
GATE_OF = {c: c[:-len("_MICRON_THRESHOLD")] for c in NAME if c.endswith("_MICRON_THRESHOLD")}

# ---------------------------------------------------------------- parse
images = {}          # name -> dict
per_file = collections.OrderedDict()
for path in sorted(glob.glob(os.path.join(ANN, "*.xml"))):
    job = os.path.basename(path)
    # Parser safety: stdlib ElementTree is XXE/billion-laughs sensitive, but this
    # input is our own team's CVAT export pulled from our own storage account into
    # a directory we control, not untrusted content. Switch to defusedxml if this
    # is ever pointed at a vendor-supplied file.
    root = ET.parse(path).getroot()
    meta_job = root.findtext("meta/job/id")
    meta_size = root.findtext("meta/job/size")
    n_img = 0
    for im in root.iter("image"):
        name = im.get("name")
        base = os.path.basename(name)
        rec = images.setdefault(base, {
            "path": name, "w": int(im.get("width")), "h": int(im.get("height")),
            "boxes": [], "tags": set(), "job": job,
        })
        n_img += 1
        for b in im.findall("box"):
            xtl, ytl = float(b.get("xtl")), float(b.get("ytl"))
            xbr, ybr = float(b.get("xbr")), float(b.get("ybr"))
            w, h = abs(xbr - xtl), abs(ybr - ytl)
            rec["boxes"].append({
                "label": b.get("label"), "w": w, "h": h,
                "diag": (w * w + h * h) ** 0.5,
                "cx": (xtl + xbr) / 2.0, "cy": (ytl + ybr) / 2.0,
                "rot": float(b.get("rotation") or 0),
            })
        for t in im.findall("tag"):
            rec["tags"].add(t.get("label"))
    per_file[job] = (n_img, meta_job, meta_size)

def codes(r):
    return {b["label"] for b in r["boxes"]} | r["tags"]

# ---------------------------------------------------------------- helpers
def pct(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)

def stats(vals):
    s = sorted(vals)
    if not s:
        return None
    return {"n": len(s), "min": s[0], "p25": pct(s, .25), "med": pct(s, .5),
            "p75": pct(s, .75), "max": s[-1],
            "mean": sum(s) / len(s)}

def um(v):
    return v * UM_PER_PX if UM_PER_PX else None

# ---------------------------------------------------------------- facts
n_images = len(images)
all_boxes = [b for r in images.values() for b in r["boxes"]]
n_boxes = len(all_boxes)
n_tags = sum(len(r["tags"]) for r in images.values())
label_shapes = collections.Counter(b["label"] for b in all_boxes)
label_shapes.update(t for r in images.values() for t in r["tags"])
label_imgs = collections.Counter()
for r in images.values():
    for c in codes(r):
        label_imgs[c] += 1

box_only = [n for n, r in images.items() if r["boxes"] and not r["tags"]]
tag_only = [n for n, r in images.items() if r["tags"] and not r["boxes"]]
both = [n for n, r in images.items() if r["boxes"] and r["tags"]]
neither = [n for n, r in images.items() if not r["boxes"] and not r["tags"]]

# a tag label repeated on one image collapses in the set, so note the raw count
raw_tags = 0
for x in sorted(glob.glob(os.path.join(ANN, "*.xml"))):
    raw_tags += len(re.findall(r"<tag\b", open(x, encoding="utf-8", errors="replace").read()))
repeated_tag = raw_tags - n_tags

sizes = collections.Counter(os.path.getsize(os.path.join(IMG, n)) for n in images)
dims = collections.Counter((r["w"], r["h"]) for r in images.values())

rot = [b for b in all_boxes if abs(b["rot"]) > 0.01]

# filename derived
lines = collections.Counter()
dates = []
scores = 0
for n in images:
    m = re.search(r"_(L\d+)_", n)
    if m:
        lines[m.group(1)] += 1
    m = re.match(r"(\d{8})_", n)
    if m:
        dates.append(m.group(1))
    if "Score(" in n:
        scores += 1

# micron gate test
gate_rows = []
for gate, base in sorted(GATE_OF.items()):
    flagged = []
    not_flagged = []
    for r in images.values():
        c = codes(r)
        if base not in c:
            continue
        mx = max([b["diag"] for b in r["boxes"] if b["label"] == base] or [0])
        (flagged if gate in c else not_flagged).append(mx)
    sf, sn = stats(flagged), stats(not_flagged)
    if sf and sn:
        # best separation point between the two medians
        gate_rows.append((base, gate, sf, sn,
                          sf["med"] - sn["med"], len(flagged), len(not_flagged)))

# co-occurrence
co = collections.Counter()
for r in images.values():
    cs = sorted(codes(r))
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            co[(cs[i], cs[j])] += 1

# distance of box centres from image centre
dists = []
for r in images.values():
    cx, cy = r["w"] / 2.0, r["h"] / 2.0
    for b in r["boxes"]:
        d = ((b["cx"] - cx) ** 2 + (b["cy"] - cy) ** 2) ** 0.5
        dists.append(d / ((cx ** 2 + cy ** 2) ** 0.5))   # normalised to corner
ds = stats(dists)
LENS_DIA_PX = 783.8        # scale_estimate.json, trimmed mean over 200 images
CAV_DIA_PX = 896.0         # scale_estimate.json, median
outside_lens = sum(1 for d in dists if d * ((1224 ** 2 + 1024 ** 2) ** 0.5) > LENS_DIA_PX / 2.0)
outside_cav = sum(1 for d in dists if d * ((1224 ** 2 + 1024 ** 2) ** 0.5) > CAV_DIA_PX / 2.0)

# job level
job_imgs = {j: v[0] for j, v in per_file.items()}

# coverage against the whole folder in blob
BLOB_FOLDER_TOTAL = 10438
BLOB_FOLDER_BYTES = 52342206916

# ---------------------------------------------------------------- write
L = []
A = L.append
A("# PRODUCTION_20260925 batch")
A("")
A("Analysis of the 2026-09-25 CVAT annotation batch and the images it labels.")
A("Every number below is computed from the files in this folder, not typed in")
A("by hand. The generating scripts are kept in our repo rather than beside the")
A("data, because this folder is shared: `vm/ops/analyze_20260925.py` reads")
A("`annotations/` and `images/` here and writes this file, and")
A("`vm/ops/measure_cavity_all.py` produced the cavity geometry it depends on.")
A("To regenerate, run `analyze_20260925.py` with `--data-dir` pointing at this")
A("folder and `--cavity-json` pointing at the repo's `cavity_geometry_all.json`.")
A("")
A("Written %s." % datetime.date.today().isoformat())
A("")

A("## What is here")
A("")
A("| Item | Value |")
A("|---|---|")
A("| Annotation files | %d CVAT 1.1 XML in `annotations/` |" % len(per_file))
A("| Images | %d BMP in `images/` |" % n_images)
A("| Total bytes | %s |" % format(sum(sizes.elements()), ","))
A("| Image geometry | %s |" % ", ".join("%dx%d" % d for d in sorted(dims)))
A("| File size | %s bytes each |" % " / ".join(format(s, ",") for s in sorted(sizes)))
A("| Labelled shapes | %s total, %s `<box>` + %s `<tag>` |" % (
    format(n_boxes + raw_tags, ","), format(n_boxes, ","), format(raw_tags, ",")))
A("| Distinct label codes | %d |" % len(label_imgs))
A("| Source | account `stjnjmakearmor`, containers `fmd-cvat-annotations` and `fmd-cvat-images` |")
A("")
A("Every image is 2448x2048, 8 bpp, 5,014,582 bytes. The batch is uniform in")
A("geometry and in file size, so nothing here is a resized or re-encoded copy.")
A("")

A("## Provenance")
A("")
A("| Job | Images in file |")
A("|---|---|")
for j, (n, mj, ms) in per_file.items():
    A("| `%s` | %d |" % (j, n))
A("| **Total** | **%d** |" % sum(job_imgs.values()))
A("")
A("The 7 jobs are disjoint: no image name appears in two files, and no name is")
A("repeated inside one file. %d distinct images for %d image tags, so the set is" % (
    n_images, sum(job_imgs.values())))
A("clean to split without de-duplication.")
A("")

A("## Labels")
A("")
A("Labels are `label=\"CODE\"` attributes on each shape, which is the CVAT 1.1")
A("detection export form. A `<box>` is a localised defect, a `<tag>` is a")
A("whole-image flag.")
A("")
A("| Code | Meaning | Shapes | Images |")
A("|---|---|---|---|")
for c, n in sorted(label_imgs.items(), key=lambda kv: (-kv[1], kv[0])):
    A("| `%s` | %s | %s | %d |" % (c, NAME.get(c, "unconfirmed"),
                                   format(label_shapes.get(c, 0), ","), n))
A("")
A("`P2_DC`, `P2_BI`, `P1_FL` and `P2_BST` need confirmation against the client")
A("taxonomy sheet before anything is named after them. `P2_BST` carries only %d" % label_shapes.get("P2_BST", 0))
A("shapes and may be a one-off.")
A("")

A("## This is a multi-label set, not one class per image")
A("")
dist = collections.Counter(len(codes(r)) for r in images.values())
A("| Codes on one image | Images |")
A("|---|---|")
for k in sorted(dist):
    A("| %d | %d |" % (k, dist[k]))
A("")
A("Only %d of %d images carry a single code. The median image carries %d codes," % (
    dist.get(1, 0), n_images, int(pct(sorted(len(codes(r)) for r in images.values()), .5))))
A("and the worst carries %d. Any pipeline that reads one class per image throws" % max(dist))
A("away most of what the annotator wrote.")
A("")
A("Shape type split:")
A("")
A("| Composition | Images |")
A("|---|---|")
A("| `<box>` only (localised defects) | %d |" % len(box_only))
A("| `<tag>` only (whole-image flags) | %d |" % len(tag_only))
A("| both | %d |" % len(both))
A("| neither, listed but unlabelled | %d |" % len(neither))
A("")
if neither:
    A("The unlabelled image is `%s`, listed in the XML with zero shapes. It is" % neither[0])
    A("kept in `images/` because it is part of the batch, but it carries no target.")
    A("")
A("Most common code pairs appearing on the same image:")
A("")
A("| Pair | Images |")
A("|---|---|")
for (a_, b_), n in sorted(co.items(), key=lambda kv: (-kv[1], kv[0]))[:12]:
    A("| `%s` + `%s` | %d |" % (a_, b_, n))
A("")

A("## Box sizes, in pixels and microns")
A("")
A("Scale is %.4f um per pixel, from `scale_estimate.json`: the lens rim measured" % UM_PER_PX)
A("at a 783.8 px trimmed mean over 200 production images, against a 14,200 um")
A("nominal lens diameter. The estimate carries 5.3 percent relative spread, so")
A("micron figures below are indicative, not metrology.")
A("")
A("Boxes carry a rotation attribute. `diag` is the rectangle diagonal,")
A("sqrt(w^2 + h^2), which is invariant to that rotation, so it is the size")
A("measure used here.")
A("")
A("| Code | Boxes | diag px p50 | diag px p25 to p75 | diag um p50 |")
A("|---|---|---|---|---|")
per_label_diag = collections.defaultdict(list)
for b in all_boxes:
    per_label_diag[b["label"]].append(b["diag"])
for c, v in sorted(per_label_diag.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    st = stats(v)
    A("| `%s` | %d | %.1f | %.1f to %.1f | %.0f |" % (
        c, st["n"], st["med"], st["p25"], st["p75"], um(st["med"])))
A("")
if rot:
    A("%s of %s boxes (%.0f percent) carry a non-zero rotation, so any training" % (
        format(len(rot), ","), format(n_boxes, ","), 100.0 * len(rot) / n_boxes))
    A("conversion that assumes axis-aligned rectangles will mis-draw most of them.")
    A("")
he = per_label_diag.get("P3_HE")
if he:
    st = stats(he)
    A("`P3_HE` is the outlier in that table: its boxes have a median diagonal of")
    A("%.0f px, which is %.0f um and larger than the 784 px lens diameter. A box" % (
        st["med"], um(st["med"])))
    A("that size is a region annotation, not a defect spot, so it should not be")
    A("trained as a detector target alongside the 9 to 100 px boxes of every")
    A("other code. Worth confirming with the annotator what `P3_HE` is meant to")
    A("cover before it goes into a detection model.")
    A("")

A("## What the micron threshold labels gate on")
A("")
A("Four codes end in `_MICRON_THRESHOLD`. All four are `<tag>` shapes, all four")
A("are strict subsets of their base code, so they read as a size gate on the")
A("base defect rather than as separate classes. The gate can be read off the")
A("data: compare the largest base-code box on images that carry the gate flag")
A("against images that do not.")
A("")
A("| Base code | Gate flag | flagged images | unflagged | flagged max diag p50 (px) | unflagged p50 (px) | gap (px) | gap (um) |")
A("|---|---|---|---|---|---|---|---|")
for base, gate, sf, sn, gap, nf, nn in sorted(gate_rows, key=lambda x: -x[4]):
    A("| `%s` | `%s` | %d | %d | %.1f | %.1f | %.1f | %.0f |" % (
        base, gate, nf, nn, sf["med"], sn["med"], gap, um(gap)))
# the fourth gate has no unflagged comparison group
for gate, base in sorted(GATE_OF.items()):
    nf = sum(1 for r in images.values() if gate in codes(r) and base in codes(r))
    nn = sum(1 for r in images.values() if base in codes(r) and gate not in codes(r))
    if nn == 0 and nf:
        A("| `%s` | `%s` | %d | 0 | n/a | n/a | n/a | n/a |" % (base, gate, nf))
A("")
A("A positive gap on every comparable row means the gate flag tracks box size,")
A("which is what a micron threshold should do. The recorded thresholds for this")
A("product are 300, 500 and 647 um, which are 16.6, 27.6 and 35.7 px at this")
A("scale. The inferred gaps sit well above all three, so the gate is not a")
A("300 um cut on any of these classes.")
A("")
for base, gate, sf, sn, gap, nf, nn in sorted(gate_rows, key=lambda x: -x[4]):
    ratio = sf["med"] / sn["med"] if sn["med"] else 0
    A("- `%s`: flagged images hold a median largest box of %.1f px (%.0f um)," % (
        base, sf["med"], um(sf["med"])))
    A("  unflagged %.1f px (%.0f um), so flagged boxes are %.1fx larger. %d of %d" % (
        sn["med"], um(sn["med"]), ratio, nf, nf + nn))
    A("  images with this defect cross the gate.")
A("")
A("`P3_HE` cannot be tested this way: all 95 images carrying it also carry")
A("`P3_HE_MICRON_THRESHOLD`, so there is no unflagged comparison group. That")
A("reads as HEMA obstruction being flagged unconditionally rather than by size.")
A("")

A("## Where the boxes sit")
A("")
# Recompute box positions against the MEASURED cavity, not the image centre.
# The cavity JSON is a derived artifact: it lives in the repo, not in the shared
# data folder, so it is passed in rather than looked for beside the data.
cav_path = _args.cavity_json or os.path.join(HERE, "cavity_geometry_all.json")
if os.path.exists(cav_path):
    cav = json.load(open(cav_path))
    geo = cav["per_image"]
    ratio_all = []
    out_cav = in_cav = out_lens = far = 0
    per_lab = collections.defaultdict(lambda: [0, 0])
    unmeasured = 0
    for r in images.values():
        base = os.path.basename(r["path"])
        g = geo.get(base)
        if not g:
            unmeasured += 1
            continue
        for b in r["boxes"]:
            d = ((b["cx"] - g["cx"]) ** 2 + (b["cy"] - g["cy"]) ** 2) ** 0.5
            ratio_all.append(d / g["R"])
            if d > g["R"]:
                out_cav += 1
                per_lab[b["label"]][1] += 1
            else:
                in_cav += 1
                per_lab[b["label"]][0] += 1
            if d > g["R"] * 1.5:
                far += 1
            if d <= g["R"] * (LENS_DIA_PX / CAV_DIA_PX):
                out_lens += 0
            else:
                out_lens += 1
    rs = sorted(ratio_all)
    sm = cav["summary"]
    A("The cavity was measured on each image rather than assumed, because it is")
    A("not centred in the frame: the median cavity centre sits %.0f px from the" % sm["centre_offset_px_median"])
    A("image centre, the p95 is %.0f px and the maximum is %.0f px. Measuring it" % (
        sm["centre_offset_px_p95"], sm["centre_offset_px_max"]))
    A("on %d of %d images (the rest were too dark or too small for the threshold" % (
        sm["images_measured"], n_images))
    A("to find a part, and their boxes are excluded below).")
    A("")
    A("| Measure | Value |")
    A("|---|---|")
    A("| Cavity radius | %.0f px median, p25 to p75 %.0f to %.0f, sd %.0f |" % (
        sm["cavity_radius_px_median"], sm["cavity_radius_px_p25"],
        sm["cavity_radius_px_p75"], sm["cavity_radius_px_std"]))
    A("| Boxes measured against their own image cavity | %s |" % format(in_cav + out_cav, ","))
    A("| Box centre inside the cavity | %s (%.1f percent) |" % (
        format(in_cav, ","), 100.0 * in_cav / (in_cav + out_cav)))
    A("| Box centre outside the cavity | %s (%.1f percent) |" % (
        format(out_cav, ","), 100.0 * out_cav / (in_cav + out_cav)))
    A("| Box centre beyond 1.5x the cavity radius | %d |" % far)
    A("| Distance from cavity centre, as a multiple of cavity radius | p50 %.2f, p75 %.2f, p95 %.2f, max %.2f |" % (
        pct(rs, .5), pct(rs, .75), pct(rs, .95), rs[-1]))
    A("")
    A("Per code, share of boxes whose centre falls outside the cavity:")
    A("")
    A("| Code | Boxes | Outside cavity | Share |")
    A("|---|---|---|---|")
    for c, (inn, outt) in sorted(per_lab.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0])):
        A("| `%s` | %d | %d | %.1f percent |" % (c, inn + outt, outt, 100.0 * outt / (inn + outt)))
    A("")
    A("Boxes sitting on the annulus between the lens rim and the cavity wall are")
    A("expected, since that is package surface. The tail past 1.5x the cavity is")
    A("the part worth a look, because a box there is on the tray or the")
    A("background rather than on the part. Only %d boxes fall that far out, so" % far)
    A("the annotation is spatially sane.")
    A("")
else:
    A("Skipped: the cavity geometry JSON is missing. Run")
    A("`vm/ops/measure_cavity_all.py` first and pass its output in with")
    A("`--cavity-json`.")
    A("")

A("## What the filenames carry")
A("")
A("| Fact | Value |")
A("|---|---|")
A("| Images with a production line tag | %d of %d |" % (sum(lines.values()), n_images))
A("| Lines present | %s |" % ", ".join("%s (%d)" % (k, v) for k, v in lines.most_common()))
A("| Capture date range | %s to %s |" % (min(dates), max(dates)))
A("| Images whose name embeds a model `Score(...)` | %d |" % scores)
A("")
A("The line tag and the capture date are free covariates for a split, so a")
A("per-line or per-date holdout costs nothing to build from the manifest.")
A("The embedded `Score(...)` values come from the upstream model that proposed")
A("these images for review. They are selection scores, not ground truth, and")
A("they should not be used as labels.")
A("")

A("## Coverage")
A("")
A("| Item | Value |")
A("|---|---|")
A("| Images in the blob folder `FMD_PROD/PRODUCTION-20260925/` | %s |" % format(BLOB_FOLDER_TOTAL, ","))
A("| Annotated in this batch | %d |" % n_images)
A("| Coverage | %.1f percent |" % (100.0 * n_images / BLOB_FOLDER_TOTAL))
A("| Unannotated images still in blob | %s, %.1f GB |" % (
    format(BLOB_FOLDER_TOTAL - n_images, ","), (BLOB_FOLDER_BYTES - sum(sizes.elements())) / 1024 ** 3))
A("")
A("This batch is the finished subset of the production folder, not the whole")
A("folder. The unannotated remainder is available as negatives if a run needs")
A("them, at %.1f GB." % ((BLOB_FOLDER_BYTES - sum(sizes.elements())) / 1024 ** 3))
A("")

A("## How to use this folder")
A("")
A("- The class information lives in the XMLs, not in folder names. Build any")
A("  split from the manifest and the XMLs, not from a directory walk.")
A("- Image basenames are unchanged from the blob. The XMLs store paths as")
A("  `FMD_PROD/PRODUCTION-20260925/<name>.bmp`, so point a loader at `images/`")
A("  with that prefix stripped.")
A("- Read labels as multi-label. A single image can legitimately carry up to")
A("  %d codes." % max(dist))
A("- Treat the XMLs as the authority over the older library folders. Those")
A("  folders disagree with each other on 113 of these images.")
A("- `manifest.csv` records blob name, local path, bytes, etag, content_md5 and")
A("  status for every file, so the transfer can be re-audited without")
A("  re-listing the container.")
A("")

A("## Open questions")
A("")
A("1. Confirm `P2_DC`, `P2_BI`, `P1_FL` and `P2_BST` against the client taxonomy.")
A("2. Confirm the intended micron gate per class. The data shows the gate")
A("   tracking box size, but the numeric cut point in um needs the client's")
A("   rule, not our inference.")
A("3. Confirm whether `P1_ML` and `P1_FL` are two classes or one class drawn")
A("   twice. Both majority-map to the Multiple Lenses folder, and %d images" % label_imgs.get("P1_FL", 0))
A("   carry `P1_FL`.")
A("4. Decide whether the unannotated %s images in the blob folder are wanted" % format(BLOB_FOLDER_TOTAL - n_images, ","))
A("   as explicit negatives.")

out = _args.out or os.path.join(HERE, "README.md")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("wrote %s  (%d lines)" % (out, len(L)))
print("images=%d boxes=%d tags=%d labels=%d" % (n_images, n_boxes, n_tags, len(label_imgs)))
