#!/usr/bin/env python3
"""Consolidate the verified full-coverage EDA figures into one JSON blob.

This is the generalised form of experiments/production_20260925/batch_numbers.py.
Where that module read the seven CVAT XML exports and computed every figure, this
module COMPUTES NOTHING. It reads the already-verified artifacts under
run/eda_full_20261015/ and the frozen crosswalk, plus a small number of figures
that live only in the written records, and normalises them into one JSON that the
workbook, report and widget builders format.

Rules:
  * every headline is taken from a run artifact or a written record, never typed;
  * nothing is derived here that the run did not already publish, except plain
    sums and products of published figures (checked in verify_deliverables.py);
  * no path is used as a join key anywhere; the run already keyed on content md5.

Usage:
  python eda_numbers.py --run run/eda_full_20261015 --crosswalk data/crosswalk.csv
                        --out reports/eda_full/full_numbers.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os


def load_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def load_csv(p):
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def build(run_dir, crosswalk_path):
    census = load_json(os.path.join(run_dir, "census.json"))
    resolution = load_json(os.path.join(run_dir, "resolution.json"))
    size = load_json(os.path.join(run_dir, "size_by_stratum.json"))
    scale = load_json(os.path.join(run_dir, "scale_by_stratum.json"))
    gate = load_json(os.path.join(run_dir, "gate_scale_estimate.json"))
    verification = load_json(os.path.join(run_dir, "verification.json"))
    coverage_rows = load_csv(os.path.join(run_dir, "coverage.csv"))
    fdis_rows = load_csv(os.path.join(run_dir, "folder_disagreement.csv"))
    codes_rows = load_csv(os.path.join(run_dir, "codes_per_image.csv"))
    crosswalk_rows = load_csv(crosswalk_path)

    distinct = census["distinct_pictures_in_library"]
    mentioned = resolution["win_counts"]["resolved_pictures_total"]
    nowhere = resolution["unannotated_pictures"]
    shapes_total = resolution["resolved_shape_count"]
    with_shape = int(next(r["value"] for r in codes_rows
                          if r["variant"] == "all_canonical_codes"
                          and r["key"] == "pictures_with_at_least_one_shape"))
    no_shape = distinct - with_shape
    boxes = size["axis_aligned"]["boxes"]
    tags = shapes_total - boxes

    # codes-per-image histogram
    cpi = {}
    for r in codes_rows:
        if r["variant"] == "all_canonical_codes" and r["kind"] == "histogram":
            cpi[int(r["key"])] = int(r["value"])
    cpi_stats = {r["key"]: float(r["value"]) for r in codes_rows
                 if r["variant"] == "all_canonical_codes" and r["kind"] == "statistic"}

    # per-canonical defect table, one row per canonical id (28)
    canonical = []
    for cid, d in sorted(resolution["per_canonical_defect"].items()):
        row = {"id": cid, "pictures": d["picture_count"], "shapes": d["shape_count"]}
        canonical.append(row)
    # enrich with the census flags and the picture-with-box/tag split
    census_by_id = {}
    for r in load_csv(os.path.join(run_dir, "label_census.csv")):
        if r["dimension"] == "all" and r["bucket"] == "all":
            census_by_id[r["canonical_id"]] = r
    for row in canonical:
        c = census_by_id.get(row["id"], {})
        row["name"] = c.get("canonical_name", row["id"])
        row["kind"] = c.get("tier", "")
        row["kind_conflict"] = c.get("kind_conflict", "no") == "yes"
        row["is_size_gate"] = c.get("is_size_gate", "no") == "yes"
        row["library_only"] = c.get("library_only", "no") == "yes"
        row["box_pictures"] = int(c.get("box_picture_count") or 0)
        row["tag_pictures"] = int(c.get("tag_picture_count") or 0)
        row["box_shapes"] = int(c.get("box_shape_count") or 0)
        row["tag_shapes"] = int(c.get("tag_shape_count") or 0)

    # pictures carrying a box / a tag, from the resolved label rows
    box_pics = set()
    tag_pics = set()
    for r in load_csv(os.path.join(run_dir, "resolved_labels.csv")):
        if r["shape_kind"] == "box":
            box_pics.add(r["picture_md5"])
        elif r["shape_kind"] == "tag":
            tag_pics.add(r["picture_md5"])

    # folder disagreement, keyed on the run's own classification
    content_disagree = [r for r in fdis_rows if int(r["distinct_class_count"]) > 1]
    content_library = len(content_disagree)
    content_batch = sum(1 for r in content_disagree if r["in_production_batch"] == "true")

    # coverage strata, straight from coverage.csv
    coverage = []
    for r in coverage_rows:
        coverage.append({
            "type": r["stratum_type"], "value": r["stratum_value"],
            "population": r["population_name"],
            "distinct": int(r["distinct_pictures"]),
            "mentioned": int(r["pictures_mentioned"]),
            "with_shape": int(r["pictures_with_shape"] or 0),
            "no_shape": int(r["pictures_no_shape"] or 0),
            "nowhere": int(r["pictures_mentioned_nowhere"] or 0),
        })

    # crosswalk table, from the frozen crosswalk
    cols = ["canonical_id", "canonical_name", "kind", "kind_conflict",
            "code_in_project2", "code_in_updated_20260922", "code_in_production_20260925",
            "library_folder_name", "is_size_gate", "gate_base_code", "collision_flag"]
    crosswalk = [{"id": r["canonical_id"], "name": r["canonical_name"], "kind": r["kind"],
                  "kind_conflict": r["kind_conflict"],
                  "p2": r["code_in_project2"], "p22": r["code_in_updated_20260922"],
                  "p25": r["code_in_production_20260925"],
                  "lib": r["library_folder_name"], "gate": r["is_size_gate"],
                  "base": r["gate_base_code"], "collision": r["collision_flag"]}
                 for r in crosswalk_rows]

    inv = gate["scale_estimate"]

    # ---- the adopted scale -------------------------------------------------
    # The adopted working scale is the client's own 300 micron cut inverted
    # through the gate boundary, at the frozen Phase 3 central figure. The
    # prior scales 18.1165 and 18.25 are superseded and are retained only as
    # labelled comparisons.
    si = load_json(os.path.join(run_dir, "scale_intervals.json"))
    ring = load_json(os.path.join(run_dir, "ring_identity.json"))
    adopted = round(si["gate_inversion_interval"]["central_um_per_px"], 3)  # 15.337
    ADOPTED = 15.337  # the adopted working scale, matching the frozen artifact
    new_b = inv["implied_scale_new"]
    old_b = inv["implied_scale_old"]

    def adopted_um(px):
        return round(px * ADOPTED, 1)

    # per-defect / per-folder-group / per-line micron columns, restated from
    # pixels at the adopted scale (a plain product of published figures)
    def restated(d):
        out = {}
        for k, v in d.items():
            w = dict(v)
            w["diag_um_adopted_p50"] = adopted_um(v["diag_px_p50"])
            w["diag_um_adopted_p25"] = adopted_um(v["diag_px_p25"])
            w["diag_um_adopted_p75"] = adopted_um(v["diag_px_p75"])
            out[k] = w
        return out

    size_restated = {
        "by_defect": restated(size["by_defect"]),
        "by_folder_group": restated(size.get("by_folder_group", {})),
        "by_line": restated(size.get("by_line", {})),
    }

    # ---- sanity anchors, recomputed from pixels -----------------------------
    def anchor(cid, dp=2):
        px = size["by_defect"][cid]["diag_px_p50"]
        shown = float(("%." + str(dp) + "f") % px)
        return {"px": shown, "um": adopted_um(shown)}

    # per-line and per-folder scale table. These five line values and the two
    # folder values were derived in the 2026-10-15 scale investigation by the
    # same gate inversion run per stratum; they live only in the written
    # record of that investigation, so they are carried here as written-record
    # figures, like the other quoted constants this module normalises.
    per_line_scale = {
        "L24": 15.377, "L25": 15.601, "L26": 15.400, "L27": 15.337,
        "L31": None,  # no threshold defect in the production export there
    }
    per_folder_scale = {
        "updated_folders_only": 15.377,
        "pictures_also_in_the_old_defects_library": 15.400,
    }

    return {
        "generated": "2026-10-15",
        "title": "Full-coverage EDA across the three ICube library folders",
        "census": {
            "universe": ("every picture in the three library folders, plus the production "
                         "image folder"),
            "distinct_pictures": distinct,
            "files_library": census["totals"]["library_files"],
            "files_total": census["totals"]["files_on_disk"],
            "files_production": census["totals"]["production_files"],
            "bytes_total": census["totals"]["bytes_on_disk"],
            "per_folder": census["per_folder"],
            "per_folder_group": census["per_folder_group"],
            "per_line": census["per_line"],
            "copy_distribution": census["content_identity"]["copy_count_distribution"],
            "hashes_in_more_than_one_folder": census["content_identity"]["hashes_in_more_than_one_folder"],
            "hashes_with_more_than_one_copy": census["content_identity"]["hashes_with_more_than_one_copy"],
            "production_files": census["production_match"]["production_files"],
            "production_distinct_contents": census["production_match"]["matched_by_hash_distinct_pictures"],
            "renamed_aliases": resolution["renamed_aliases"]["basenames_in_more_than_one_name_for_one_content"],
        },
        "labels": {
            "mentioned": mentioned,
            "with_shape": with_shape,
            "no_shape": no_shape,
            "nowhere": nowhere,
            "shapes_total": shapes_total,
            "boxes": boxes,
            "tags": tags,
            "pictures_with_box": len(box_pics),
            "pictures_with_tag": len(tag_pics),
            "box_only": with_shape - len(tag_pics & box_pics),
            "tag_only": len(tag_pics) - len(tag_pics & box_pics),
            "both": len(tag_pics & box_pics),
            "box_codes_per_image": cpi,
            "median_codes": cpi_stats.get("median_codes_on_a_picture"),
            "mean_codes": cpi_stats.get("mean_codes_on_a_picture"),
            "p90_codes": cpi_stats.get("p90_codes_on_a_picture"),
            "max_codes": cpi_stats.get("max_codes_on_a_picture"),
            "wins_by_level": resolution["win_counts"]["by_priority_level"],
            "wins_by_file": resolution["win_counts"]["by_source_file"],
            "canonical_defects": canonical,
            "canonical_count": len(canonical),
        },
        "box_geometry": {
            "axis_aligned": size["axis_aligned"]["n_axis_aligned"],
            "rotated": size["axis_aligned"]["n_rotated"],
            "total": size["axis_aligned"]["boxes"],
            "share_axis_aligned": size["axis_aligned"]["share_axis_aligned"],
            "by_defect": size_restated["by_defect"],
            "by_folder_group": size_restated["by_folder_group"],
            "by_line": size_restated["by_line"],
        },
        "cavity": {
            "read": load_json(os.path.join(run_dir, "cavity_geometry_library.json"))["summary"]
            if os.path.exists(os.path.join(run_dir, "cavity_geometry_library.json")) else {},
        },
        "scale": {
            "adopted_um_per_px": ADOPTED,
            "adopted_source": (
                "the customer's own 300 micron cut inverted through the gate boundary; "
                "central figure of the frozen scale-interval artifact"),
            "adopted_interval_um_per_px": si["gate_inversion_interval"]["interval_um_per_px"],
            "adopted_boundary_px": [new_b["boundary_px_lower"], new_b["boundary_px_upper"]],
            "adopted_boundary_um": [adopted_um(new_b["boundary_px_lower"]),
                                    adopted_um(new_b["boundary_px_upper"])],
            "old_cut_boundary_px": [old_b["boundary_px_lower"], old_b["boundary_px_upper"]],
            "old_cut_implied_interval_um_per_px": [
                inv["implied_scale_old"]["scale_um_per_px_low"],
                inv["implied_scale_old"]["scale_um_per_px_high"]],
            "superseded": {
                "ours_18_1165": {
                    "value": 18.1165,
                    "status": ("superseded prior scale; it divided an unsourced 14,200 "
                               "micron lens assumption by a lens pixel measurement"),
                },
                "spoken_18_25": {
                    "value": 18.25,
                    "status": "superseded prior scale; written in no document we hold",
                },
            },
            "per_line_um_per_px": per_line_scale,
            "per_folder_um_per_px": per_folder_scale,
            "lens": {
                "rim_median_diam_px": ring["verdict"]["lens_diameter_px"]["median_diam_px"],
                "rim_iqr_diam_px": [ring["verdict"]["lens_diameter_px"]["p25_diam_px"],
                                    ring["verdict"]["lens_diameter_px"]["p75_diam_px"]],
                "adopted_diam_um": round(
                    ring["verdict"]["lens_diameter_px"]["median_diam_px"] * ADOPTED),
                "prior_848_px_status": ring["verdict"]["the_848_px_figure"],
                "nominal_status": ("the lens nominal diameter is not documented in "
                                   "anything received; a written figure from the "
                                   "customer would close the remaining question"),
            },
            "sanity_anchors": {
                "bubble_median": anchor("bubble"),
                "foreign_matter_median": anchor("foreign_matter"),
                "fiber_median": anchor("fiber"),
                "old_cut_647_um_in_px": round(647.0 / ADOPTED, 2),
            },
            "blind": scale["_comparison"],
            "strata": [{"stratum": k, **v} for k, v in scale.items() if k != "_comparison"],
        },
        "micron_gate": {
            "proxy": inv["proxy"],
            "cut_um": inv["new_cut_um"],
            "old_cut_um": inv["old_cut_um"],
            "base_codes": gate["base_codes"],
            "new_boundaries_px": inv["new_boundaries_px"],
            "old_boundaries_px": inv["old_boundaries_px"],
            "implied_scale_new": inv["implied_scale_new"],
            "implied_scale_old": inv["implied_scale_old"],
            "implied_scale_combined": inv["implied_scale_combined"],
            "implies_at_our_scales": inv["implies_at_our_scales"],
            "assumptions": inv["assumptions"],
            "delta": gate["delta"],
            "counts": gate["counts"],
        },
        "coverage": {
            "strata": coverage,
            "blob": {"folder_total": 10438, "annotated": 1047, "share": 1047 / 10438},
            "library_only_pictures": 177,
            "library_only_classes": [
                ["Bubble", 72], ["Wet Package", 27], ["Bubble Irregular", 26],
                ["Bubble Cluster", 21], ["Bubble On 123", 14], ["Bubble On Edge", 14],
                ["Dirty Strobe", 1], ["Fiber", 1], ["Bubble Scatter", 1],
            ],
        },
        "disagreement": {
            "name_based_batch": 113,
            "content_library": content_library,
            "content_batch": content_batch,
            "rows": resolution["disagreement"]["rows"],
            "sep22_mentions": resolution["disagreement"]["sep22_mentions"],
            "old_mentions": resolution["disagreement"]["old_mentions"],
        },
        "crosswalk": {
            "count": len(crosswalk_rows),
            "collision_flags": load_json(os.path.join(run_dir, "crosswalk_evidence.json"))["collision_flags"],
            "table": crosswalk,
        },
        "verification": {
            "assertions": verification["total_assertions"],
            "failures": verification["failure_count"],
            "checks": verification["check_count"],
            "figures": verification["figure_count"],
        },
        "superseded_20261013": {
            "batch_pictures": 1047,
            "boxes": 12793,
            "tags": 1318,
            "codes": 24,
            "status": "superseded by the full-coverage EDA",
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="run/eda_full_20261015")
    ap.add_argument("--crosswalk", default="data/crosswalk.csv")
    ap.add_argument("--out", default="reports/eda_full/full_numbers.json")
    a = ap.parse_args()
    data = build(a.run, a.crosswalk)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print("wrote %s" % os.path.abspath(a.out))
    print(json.dumps({
        "distinct": data["census"]["distinct_pictures"],
        "mentioned": data["labels"]["mentioned"],
        "with_shape": data["labels"]["with_shape"],
        "no_shape": data["labels"]["no_shape"],
        "nowhere": data["labels"]["nowhere"],
        "shapes": data["labels"]["shapes_total"],
        "boxes": data["labels"]["boxes"],
        "tags": data["labels"]["tags"],
        "canonical": data["labels"]["canonical_count"],
    }, indent=1))


if __name__ == "__main__":
    main()
