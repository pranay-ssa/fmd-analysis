#!/usr/bin/env python3
"""Ticket 012 box-geometry aggregation builder.

Reads the resolved label table, the picture table and the per-image cavity
measurement, and writes:

  run/eda_full_20261015/box_sizes.csv                one row per box shape
  run/eda_full_20261015/cavity_geometry_library.json per picture cavity + flag
  run/eda_full_20261015/size_by_stratum.json         defect x group x line stats

The size measure is the rectangle diagonal sqrt(w^2 + h^2), invariant to the
rotation attribute. Microns are reported at BOTH candidate scales, side by
side, and the scale is named in every table: 18.1165 (ours) and 18.25 (spoken
by the lead, written nowhere).

Joins are all keyed on content md5, never on a path, because 187 basenames hold
a content that also exists under a second name.

Run:  ./.venv/Scripts/python.exe experiments/eda_full/box_geometry.py
Stdlib only. The heavy image reading happens on the VM.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RUN = os.path.join(REPO, "run", "eda_full_20261015")
RESOLVED = os.path.join(RUN, "resolved_labels.csv")
PICTURE_TABLE = os.path.join(RUN, "picture_table.csv")
CAVITY_RAW = os.path.join(RUN, "cavity_raw.tsv")
BOX_SIZES = os.path.join(RUN, "box_sizes.csv")
CAVITY_JSON = os.path.join(RUN, "cavity_geometry_library.json")
BY_STRATUM = os.path.join(RUN, "size_by_stratum.json")

# The two candidate microns-per-pixel scales, named, never silently chosen.
SCALE_OURS = 18.1165
SCALE_LEAD = 18.25
SCALES = [("18.1165", SCALE_OURS), ("18.25", SCALE_LEAD)]

# The published lens rim diameter in pixels, for the P3_HE region caveat.
LENS_DIAMETER_PX = 783.8

UPDATED_FOLDERS = ("Updated ICube Objects 20260915",
                   "Updated ICube Categorical Classes 20260915")
LIBRARY_FOLDER = "ICube Defects Library"


def folder_group(winning_path):
    top = winning_path.split("/")[0]
    if top in UPDATED_FOLDERS:
        return "Updated"
    if top == LIBRARY_FOLDER:
        return "Library"
    return "other"


def percentile(sorted_vals, q):
    """Linear-interpolation percentile, matching statistics.quantiles(inclusive)."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    k = (n - 1) * q
    lo = int(k)
    hi = min(lo + 1, n - 1)
    return float(sorted_vals[lo]) + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def dist_stats(diags_px):
    s = sorted(diags_px)
    out = {"n": len(s)}
    for q, name in ((0.25, "p25"), (0.50, "p50"), (0.75, "p75")):
        v = percentile(s, q)
        out["diag_px_" + name] = round(v, 4) if v is not None else None
    for label, scale in SCALES:
        key_label = label.replace(".", "_")
        for name in ("p25", "p50", "p75"):
            px = out["diag_px_" + name]
            out["diag_um_at_%s_%s" % (key_label, name)] = (
                round(px * scale, 4) if px is not None else None)
    return out


def main():
    # ------------------------------------------------------------- pictures
    pictures = {}
    with open(PICTURE_TABLE, newline="") as fh:
        for r in csv.DictReader(fh):
            pictures[r["md5"]] = {
                "winning_path": r["winning_path"],
                "line": r["line"],
                "folder_group": folder_group(r["winning_path"]),
            }
    path_to_md5 = {v["winning_path"]: k for k, v in pictures.items()}
    assert len(path_to_md5) == len(pictures), "winning_path is not unique per md5"

    # -------------------------------------------------------------- cavity
    cavity = {}          # md5 -> {cx,cy,R_px,measured,flag,winning_path}
    flag_counts = {}
    with open(CAVITY_RAW, newline="") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            path, cx, cy, rr, flag = line.split("\t")
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
            md5 = path_to_md5.get(path)
            ok = flag == "ok"
            rec = {
                "winning_path": path,
                "cx": float(cx) if ok else None,
                "cy": float(cy) if ok else None,
                "R_px": float(rr) if ok else None,
                "measured": ok,
                "flag": flag,
            }
            if md5 is not None:
                cavity[md5] = rec
    # every census picture gets an entry, even if the display join missed it
    for md5, pic in pictures.items():
        if md5 not in cavity:
            cavity[md5] = {"winning_path": pic["winning_path"], "cx": None,
                           "cy": None, "R_px": None, "measured": False,
                           "flag": "not_in_run"}

    measured_n = sum(1 for c in cavity.values() if c["measured"])
    failed_n = len(cavity) - measured_n
    radii = sorted(c["R_px"] for c in cavity.values() if c["measured"])
    cavity_doc = {
        "meta": {
            "method": "vm/ops/measure_cavity_library.py, reused verbatim from "
                      "vm/ops/measure_cavity_all.py (2026-10-13 batch run)",
            "universe": "every distinct picture in picture_table.csv (the census), "
                        "keyed on content md5",
            "note": "the 2026-10-13 cavity_geometry_all.json covered only the "
                    "1,047 production-batch images, not the library",
            "root": "/home/amd100-user/FMD_Data_26082026/fmd_temp_images",
        },
        "summary": {
            "pictures": len(cavity),
            "pictures_measured": measured_n,
            "pictures_could_not_measure": failed_n,
            "failure_classes": dict(sorted(flag_counts.items())),
            "cavity_radius_px_p25": round(percentile(radii, 0.25), 4) if radii else None,
            "cavity_radius_px_p50": round(percentile(radii, 0.50), 4) if radii else None,
            "cavity_radius_px_p75": round(percentile(radii, 0.75), 4) if radii else None,
        },
        "per_picture": {md5: cavity[md5] for md5 in sorted(cavity)},
    }

    # ------------------------------------------------------------ box sizes
    boxes = []
    tags_excluded = 0
    with open(RESOLVED, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["shape_kind"] != "box":
                tags_excluded += 1
                continue
            boxes.append(r)

    rows = []
    for r in boxes:
        md5 = r["picture_md5"]
        pic = pictures[md5]
        xtl, ytl = float(r["xtl"]), float(r["ytl"])
        xbr, ybr = float(r["xbr"]), float(r["ybr"])
        w = abs(xbr - xtl)
        h = abs(ybr - ytl)
        diag = (w * w + h * h) ** 0.5
        rot = r["rotation"].strip()
        axis = 1 if (rot == "" or float(rot) == 0.0) else 0
        rows.append({
            "picture_md5": md5,
            "winning_path": pic["winning_path"],
            "source_file": r["source_file"],
            "priority_level": r["priority_level"],
            "canonical_id": r["canonical_id"],
            "w_px": round(w, 4),
            "h_px": round(h, 4),
            "diag_px": round(diag, 4),
            "rotation": r["rotation"],
            "is_axis_aligned": axis,
            "folder_group": pic["folder_group"],
            "line": pic["line"],
            "diag_um_at_18_1165": round(diag * SCALE_OURS, 4),
            "diag_um_at_18_25": round(diag * SCALE_LEAD, 4),
            "_xtl": xtl, "_ytl": ytl, "_xbr": xbr, "_ybr": ybr,
        })

    rows.sort(key=lambda d: (d["picture_md5"], d["canonical_id"], d["source_file"],
                             d["_xtl"], d["_ytl"], d["_xbr"], d["_ybr"]))

    cols = ["picture_md5", "winning_path", "source_file", "priority_level",
            "canonical_id", "w_px", "h_px", "diag_px", "rotation",
            "is_axis_aligned", "folder_group", "line",
            "diag_um_at_18_1165", "diag_um_at_18_25"]
    with open(BOX_SIZES, "w", newline="") as fh:
        wcsv = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        wcsv.writeheader()
        for d in rows:
            wcsv.writerow(d)

    # --------------------------------------------------- axis-aligned share
    n_axis = sum(d["is_axis_aligned"] for d in rows)
    n_rot = len(rows) - n_axis
    axis_block = {
        "boxes": len(rows),
        "n_axis_aligned": n_axis,
        "n_rotated": n_rot,
        "share_axis_aligned": round(n_axis / len(rows), 6) if rows else None,
        "rule": "axis-aligned = rotation attribute absent or exactly 0.0",
    }

    # ------------------------------------------------------ per-curve stats
    def group_stats(keyfn, universe):
        acc = {}
        for d in universe:
            acc.setdefault(keyfn(d), []).append(d["diag_px"])
        return {k: dist_stats(v) for k, v in sorted(acc.items())}

    by_defect = group_stats(lambda d: d["canonical_id"], rows)
    by_group = group_stats(lambda d: d["folder_group"], rows)
    by_line = group_stats(lambda d: d["line"], rows)

    acc = {}
    for d in rows:
        acc.setdefault((d["canonical_id"], d["folder_group"], d["line"]), []).append(d)
    triples = []
    for (cid, grp, ln), ds in sorted(acc.items()):
        st = dist_stats([d["diag_px"] for d in ds])
        triples.append({"canonical_id": cid, "folder_group": grp, "line": ln, **st})

    # ------------------------------------------------- cavity containment
    def cavity_share(universe):
        n_meas = n_out = n_far = n_unmeas = 0
        for d in universe:
            c = cavity[d["picture_md5"]]
            if not c["measured"]:
                n_unmeas += 1
                continue
            w = (d["_xtl"] + d["_xbr"]) / 2.0
            h = (d["_ytl"] + d["_ybr"]) / 2.0
            dist = ((w - c["cx"]) ** 2 + (h - c["cy"]) ** 2) ** 0.5
            n_meas += 1
            if dist > c["R_px"]:
                n_out += 1
            if dist > c["R_px"] * 1.5:
                n_far += 1
        return {
            "n_boxes_measured": n_meas,
            "n_boxes_unmeasured_cavity": n_unmeas,
            "n_outside_cavity": n_out,
            "share_outside_cavity": round(n_out / n_meas, 6) if n_meas else None,
            "n_beyond_1_5x_cavity": n_far,
            "share_beyond_1_5x_cavity": round(n_far / n_meas, 6) if n_meas else None,
        }

    cav_overall = cavity_share(rows)
    cav_by_defect = {cid: cavity_share([d for d in rows if d["canonical_id"] == cid])
                     for cid in sorted({d["canonical_id"] for d in rows})}

    # ------------------------------------------------------ P3_HE caveat
    p3he = [d for d in rows if d["canonical_id"] in ("hema_obstruction",
                                                     "hema_fragment")]
    p3he_stats = {}
    for cid in ("hema_obstruction", "hema_fragment"):
        sub = [d["diag_px"] for d in rows if d["canonical_id"] == cid]
        if sub:
            st = dist_stats(sub)
            st["median_over_lens"] = round(st["diag_px_p50"] / LENS_DIAMETER_PX, 3)
            p3he_stats[cid] = st
    all_sub = [d["diag_px"] for d in p3he]
    p3he_block = {
        "note": "HEMA Obstruction and HEMA Fragment share the P3_HE code and their "
                "boxes are region annotations, not defect spots: the median diagonal "
                "is far larger than the lens diameter, so they must not be read as "
                "detector targets.",
        "lens_diameter_px": LENS_DIAMETER_PX,
        "boxes_combined": len(p3he),
        "combined_diag_px_p50": round(percentile(sorted(all_sub), 0.5), 4) if all_sub else None,
        "combined_median_over_lens": round(percentile(sorted(all_sub), 0.5) / LENS_DIAMETER_PX, 3) if all_sub else None,
        "per_defect": p3he_stats,
    }

    doc = {
        "meta": {
            "ticket": "012",
            "date": "2026-10-15",
            "size_measure": "rectangle diagonal sqrt(w^2 + h^2)",
            "folder_group_rule": "top folder of winning_path; Updated is either "
                                 "Updated folder, Library is ICube Defects Library",
            "scales_um_per_px": {"18.1165": SCALE_OURS, "18.25": SCALE_LEAD},
            "scale_note": "the 0.07 percent gap between the scales is far inside "
                          "the measurement noise (ticket 013a); pixel columns are "
                          "primary, micron columns are for completeness",
        },
        "counts": {
            "boxes": len(rows),
            "tags_excluded": tags_excluded,
            "pictures_with_boxes": len({d["picture_md5"] for d in rows}),
        },
        "axis_aligned": axis_block,
        "by_defect": by_defect,
        "by_folder_group": by_group,
        "by_line": by_line,
        "by_defect_folder_group_line": triples,
        "cavity_containment": {
            "overall": cav_overall,
            "by_defect": cav_by_defect,
        },
        "p3_he_region_annotation": p3he_block,
    }
    with open(BY_STRATUM, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(CAVITY_JSON, "w") as fh:
        json.dump(cavity_doc, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print("boxes %d  tags_excluded %d  pictures_with_boxes %d"
          % (len(rows), tags_excluded, len({d["picture_md5"] for d in rows})))
    print("axis-aligned %d / %d = %.4f" % (n_axis, len(rows), n_axis / len(rows)))
    print("cavity measured %d  could_not_measure %d  %s"
          % (measured_n, failed_n, dict(sorted(flag_counts.items()))))
    print("cavity overall outside %.4f  beyond 1.5x %.4f"
          % (cav_overall["share_outside_cavity"], cav_overall["share_beyond_1_5x_cavity"]))
    print("wrote %s, %s, %s" % (BOX_SIZES, CAVITY_JSON, BY_STRATUM))


if __name__ == "__main__":
    main()
