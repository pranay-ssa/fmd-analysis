#!/usr/bin/env python3
"""Phase 2, 3 and 4 of the scale plan: the builder.

Local only. It never talks to the VM and never writes to it.

Phase 2 enumerates every candidate external length that could turn pixels into
microns and labels each one documented or assumed, with its source and the
uncertainty it carries. Phase 3 turns the Phase-1 pixel measurement into a
scale INTERVAL for every candidate, never a bare point, propagates the Phase-1
error budget, reads the client gate back into microns at each candidate scale,
and states the tension between the lens measurement and the gate inversion
without resolving it. Phase 4 runs four falsification tests.

Run:
    python experiments/eda_full/scale_phase234.py --sample         # ml_sample.txt
    python experiments/eda_full/scale_phase234.py --scanner-input   # stdin for scanner
    python experiments/eda_full/scale_phase234.py --aggregate       # the two JSON files
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "run" / "eda_full_20261015"
REPORTS = REPO / "reports" / "eda_full"
DOCS = REPO / "docs"

PICTURE_TABLE = RUN / "picture_table.csv"
RING_IDENT = RUN / "ring_identity.json"
GATE_SCALE = RUN / "gate_scale_estimate.json"
PFT_LISTING = RUN / "pft_listing.txt"

OUT_SAMPLE = RUN / "ml_sample.txt"
RAW = RUN / "ml_raw.tsv"
OUT_CANDIDATES = RUN / "scale_candidates.json"
OUT_FALSIF = RUN / "falsification.json"

LIBRARY_FOLDERS = {
    "ICube Defects Library",
    "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
}
PROD_FOLDER = "PRODUCTION_20260925"
LINES = ["L24", "L25", "L26", "L27", "L31"]
SEED = 20261015
N_ML = 150
N_CTRL = 150
N_SEC_LIB = 120
N_SEC_PROD = 120

# The gate boundary, from run/eda_full_20261015/gate_scale_estimate.json.
GATE_SWITCH_PX = (19.41, 19.61)     # new 300 micron cut, FM and Fiber intersected
GATE_CUT_UM = 300.0
GATE_OLD_CUT_UM = 647.0
INTERIOR_HI = 0.80                  # normalised radius below which a ring is interior


def line_of(name: str) -> str:
    import re
    m = re.search(r"_L(\d+)_", name)
    return "L" + m.group(1) if m else ""


# ---------------------------------------------------------------------------
# sample
# ---------------------------------------------------------------------------

def build_sample() -> int:
    rows = list(csv.DictReader(PICTURE_TABLE.open(encoding="utf-8")))
    ml = [r for r in rows if "/Multiple Lenses/" in r["winning_path"]]
    clear = [r for r in rows if "/Clear/" in r["winning_path"]]
    lib = [r for r in rows if r["winning_path"].split("/", 1)[0] in LIBRARY_FOLDERS]
    pop_b = [l.strip() for l in (RUN / "ring_pop_b_listing.txt").read_text(
        encoding="utf-8").splitlines() if l.strip()] if (RUN / "ring_pop_b_listing.txt").exists() else []

    rng = random.Random(SEED)
    out = []
    for r in rng.sample(sorted(ml, key=lambda r: r["md5"]), N_ML):
        out.append(("ml", "ml", r["md5"], r["winning_path"]))
    for r in rng.sample(sorted(clear, key=lambda r: r["md5"]), N_CTRL):
        out.append(("ctrl", "ctrl", r["md5"], r["winning_path"]))
    for r in rng.sample(sorted(lib, key=lambda r: r["md5"]), N_SEC_LIB):
        out.append(("sec", "sec_lib", r["md5"], r["winning_path"]))
    for name in rng.sample(sorted(pop_b), min(N_SEC_PROD, len(pop_b))):
        out.append(("sec", "sec_prod", "",
                    "20260826_T24_Production_Sample/sample folder/" + name))
    if PFT_LISTING.exists():
        for rel in PFT_LISTING.read_text(encoding="utf-8").splitlines():
            if rel.strip():
                out.append(("sec", "pft", "", rel.strip()))

    with OUT_SAMPLE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["tag", "group", "md5", "relpath"])
        w.writerows(out)
    print("ml_sample.txt rows: %d" % len(out))
    return 0


def scanner_input() -> int:
    with OUT_SAMPLE.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sys.stdout.write(row["tag"] + "\t" + row["relpath"] + "\n")
    return 0


# ---------------------------------------------------------------------------
# phase 2 and phase 3: candidates and scale intervals
# ---------------------------------------------------------------------------

def load_phase1():
    rid = json.loads(RING_IDENT.read_text(encoding="utf-8"))
    d = rid["verdict"]["lens_diameter_px"]
    return {
        "median_diam_px": d["median_diam_px"],
        "p25_diam_px": d["p25_diam_px"],
        "p75_diam_px": d["p75_diam_px"],
        "rel_spread_pct": d["rel_spread_pct"],
        "p10_diam_px": d["p10_diam_px"],
        "p90_diam_px": d["p90_diam_px"],
        "n": d["n"],
        "source": "run/eda_full_20261015/ring_identity.json",
    }


def load_gate():
    return json.loads(GATE_SCALE.read_text(encoding="utf-8"))


def scale_interval_from_nominal(nominal_um, p1):
    """Implied microns per pixel for a nominal lens diameter, as an interval.

    nominal_um / lens_px, with the Phase-1 error budget carried through. Because
    the division is by the pixel value, the low microns per pixel goes with the
    HIGH pixel diameter and vice versa.
    """
    hi = p1["median_diam_px"]
    iqr_lo, iqr_hi = p1["p25_diam_px"], p1["p75_diam_px"]
    method_lo, method_hi = 760.0, 789.0       # Phase-1 method range on the same images
    pop_lib, pop_prod = 777.3, 809.5          # Phase-1 population medians
    central = nominal_um / hi
    from_frame = [nominal_um / iqr_hi, nominal_um / iqr_lo]
    from_method = [nominal_um / method_hi, nominal_um / method_lo]
    from_pop = [nominal_um / pop_prod, nominal_um / pop_lib]
    lo = min(from_frame[0], from_method[0], from_pop[0])
    hi_s = max(from_frame[1], from_method[1], from_pop[1])
    return {
        "central_um_per_px": round(central, 4),
        "interval_um_per_px": [round(lo, 4), round(hi_s, 4)],
        "error_budget_um_per_px": {
            "frame_spread_iqr": [round(from_frame[0], 4), round(from_frame[1], 4)],
            "method_range_760_789_px": [round(from_method[0], 4), round(from_method[1], 4)],
            "population_library_vs_production": [round(from_pop[0], 4), round(from_pop[1], 4)],
        },
        "lens_px_used": {"median": hi, "iqr": [iqr_lo, iqr_hi],
                         "method_range": [method_lo, method_hi],
                         "population": [pop_lib, pop_prod]},
    }


def candidates_doc(p1, gate):
    lens14200 = scale_interval_from_nominal(14200.0, p1)
    # nominal uncertainty, if the uncited 14.0 to 14.3 mm range is taken at face value
    nom_lo = 14200.0 * 14.0 / 14.2
    nom_hi = 14200.0 * 14.3 / 14.2
    with_nom = [14200.0 * 14.0 / 14.2 / 809.5, 14200.0 * 14.3 / 14.2 / 760.0]
    lens14200["with_uncited_spec_range"] = {
        "nominal_um_range": [round(nom_lo, 1), round(nom_hi, 1)],
        "interval_um_per_px": [round(with_nom[0], 4), round(with_nom[1], 4)],
        "note": "the 14.0 to 14.3 mm range is our own uncited figure; it is shown only "
                "so the reader can see how much it would widen the interval if believed.",
    }

    inv = gate["scale_estimate"]["implied_scale_combined"]
    gate_scale = {
        "central_um_per_px": inv["scale_um_per_px_mid"],
        "interval_um_per_px": [inv["scale_um_per_px_low"], inv["scale_um_per_px_high"]],
        "from_new_cut": [gate["scale_estimate"]["implied_scale_new"]["scale_um_per_px_low"],
                         gate["scale_estimate"]["implied_scale_new"]["scale_um_per_px_high"]],
        "from_old_cut": [gate["scale_estimate"]["implied_scale_old"]["scale_um_per_px_low"],
                         gate["scale_estimate"]["implied_scale_old"]["scale_um_per_px_high"]],
        "agreement": inv["agreement"],
    }

    candidates = [
        {
            "id": "lens_diameter_14200_um",
            "quantity": "nominal soft-lens diameter",
            "value_um": 14200.0,
            "class": "assumed",
            "documented_or_assumed": "working assumption",
            "is_documented": False,
            "source": "our own hardcoded constant, not a client document",
            "where_written": [
                "/data/FMD_Data_26082026/measure_scale.py line 9 NOMINAL_LENS_DIAMETER_UM = 14_200.0",
                "/data/FMD_Data_26082026/eda_size_um.py line 24 NOMINAL_LENS_DIAM_UM = 14200.0",
            ],
            "rationale_written_at": "/data/FMD_Data_26082026/eda_methodology.html section 21.3 line 393: 'soft daily contact lens; spec range 14.0 to 14.3 mm'",
            "rationale_class": "assumed product spec with no citation",
            "verified_against": "docs/reference/scale_provenance_20261015.md (Phase 0) and docs/reference/received_docs_nominals.md, which state the lens diameter is written in no received document",
            "nominal_uncertainty": "unquantified; the only spread ever attached to it is the uncited 14.0 to 14.3 mm range",
            "implied_scale": lens14200,
        },
        {
            "id": "client_cut_300_um_inverted",
            "quantity": "client stated 300 micron cut, inverted through the annotation gate boundary",
            "value_um": 300.0,
            "class": "documented",
            "documented_or_assumed": "documented",
            "is_documented": True,
            "source": "FM3 Edge Algorithm URS Final Draft, received, section 4.2 Nice to Haves item 1b: debris grouped by size range 300 to 500 microns; the annotator handover email of 2026-10-13 states the 300 micron cut",
            "where_written": [
                "docs/FM3 Edge Algorithm URS Final Draft .pdf, section 4.2 (bands under 300, 300 to 500, 500 to 647 microns)",
                "experiments/production_20260925/annotator_email_20261013.json, fields stated_rule and threshold_um",
            ],
            "reachable_by": "inverting the gate tag boundary: the flagged versus unflagged switch sits at 19.41 to 19.61 px on the 2026-10-15 files",
            "nominal_uncertainty": "the declared cut is taken as exact; the interval below carries the boundary width and the inversion assumptions, not a nominal spread",
            "implied_scale": gate_scale,
        },
        {
            "id": "client_cut_647_um_inverted",
            "quantity": "client foreign-matter threshold 647 microns, inverted through the older gate boundary",
            "value_um": 647.0,
            "class": "documented",
            "documented_or_assumed": "documented",
            "is_documented": True,
            "source": "FM3 Edge Algorithm URS Final Draft, received, section 1.1.1 and Requirement 1: non-lens material at or above 647 microns",
            "where_written": [
                "docs/FM3 Edge Algorithm URS Final Draft .pdf, section 1.1.1 p3, section 4.1 item 1 p7, section 6.2 p28",
            ],
            "reachable_by": "inverting the 2026-10-13 gate boundary, 42.08 to 42.79 px",
            "nominal_uncertainty": "as above; the boundary width carries the interval",
            "implied_scale": {
                "interval_um_per_px": gate_scale["from_old_cut"],
                "central_um_per_px": round(sum(gate_scale["from_old_cut"]) / 2.0, 4),
            },
        },
        {
            "id": "package_blister_cavity_tray_dimension",
            "quantity": "package, blister, cavity or tray dimension",
            "value_um": None,
            "class": "not_found",
            "documented_or_assumed": "not available",
            "is_documented": False,
            "source": "searched, none exists",
            "where_written": [],
            "note": "The JnJ production line specs (docs/reference/jnj_production_line_specs.md) carry camera models, focal lengths, backlight wavelength and PC hardware, but no package, blister, cavity or tray dimension. The received URS and Ontology carry no package dimension either. The prior EDA records only a cavity disc diameter in pixels (about 896 px), never in microns.",
            "implied_scale": None,
        },
        {
            "id": "camera_or_optics_object_space_scale",
            "quantity": "camera pixel pitch, working distance or magnification",
            "value_um": None,
            "class": "not_found",
            "documented_or_assumed": "not available",
            "is_documented": False,
            "source": "searched, none exists",
            "where_written": [],
            "note": "docs/reference/scale_provenance_20261015.md records that pixel pitch, working distance and magnification are explicitly absent; eda_methodology.html section 21.1 states no mm/um field, magnification, working distance or fiducial exists. The lens focal lengths (12, 75, 6, 25 mm) are camera parameters, not object-space scale, and no sensor pixel size or working distance is given to convert them.",
            "implied_scale": None,
        },
    ]
    return candidates, lens14200, gate_scale


def reverse_gate(gate_scale, gate_central, lens_median_px):
    """State what cut in microns the 19.41 to 19.61 px switch corresponds to at
    each candidate scale, and what a 300 micron debris spans in pixels. Every
    micron figure names the scale it was computed at."""
    scales = {
        "lens_measurement_central": 14200.0 / lens_median_px,
        "gate_inversion_central": gate_central,
        "published_18_1165": 18.1165,
        "spoken_18_25": 18.25,
    }
    out = {}
    for name, s in scales.items():
        out[name] = {
            "scale_um_per_px": round(s, 4),
            "cut_um_for_switch_low": round(GATE_SWITCH_PX[0] * s, 1),
            "cut_um_for_switch_high": round(GATE_SWITCH_PX[1] * s, 1),
            "debris_300um_in_px": round(300.0 / s, 2),
        }
    return out


def box_margin(gate_scale):
    """Phase 4 test 4. At a scale S the gate switches on a longest box side of
    19.41 to 19.61 px. A 300 micron debris at scale S spans 300/S px. The gap is
    the required annotation margin, in px and as a percent of the box."""
    rows = {}
    for name, S in (("lens_14200_central_18.0", 18.0),
                    ("gate_inversion_15.337", 15.3369),
                    ("published_18.1165", 18.1165),
                    ("spoken_18.25", 18.25)):
        debris_px = 300.0 / S
        gaps = [GATE_SWITCH_PX[0] - debris_px, GATE_SWITCH_PX[1] - debris_px]
        # percent of the box, box side is the switch interval midpoint
        box_mid = (GATE_SWITCH_PX[0] + GATE_SWITCH_PX[1]) / 2.0
        pct = [100.0 * g / box_mid for g in gaps]
        rows[name] = {
            "scale_um_per_px": S,
            "switch_px": list(GATE_SWITCH_PX),
            "debris_300um_px": round(debris_px, 3),
            "required_margin_px": [round(gaps[0], 3), round(gaps[1], 3)],
            "required_margin_pct_of_box": [round(pct[0], 2), round(pct[1], 2)],
        }
    return rows


# ---------------------------------------------------------------------------
# phase 4: raw scanner aggregation
# ---------------------------------------------------------------------------

def load_raw():
    pics = {}
    ring_norms = defaultdict(list)
    for raw in RAW.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        f = raw.split("\t")
        if f[0] == "R":
            if len(f) > 6 and f[5] not in ("", None):
                ring_norms[f[1]].append((float(f[5]), float(f[6]) if f[6] else None))
            continue
        if f[0] != "P":
            continue
        def num(i):
            return float(f[i]) if i < len(f) and f[i] not in ("", None) else None
        pics[f[2] or f[3]] = {
            "tag": f[1], "md5": f[2], "path": f[3], "flag": f[7],
            "Rcav": num(6), "rim_diam": num(8), "rim_rms": num(9),
            "n_rings": int(f[10]) if f[10] else None,
            "n_interior": int(f[11]) if f[11] else None,
            "n_interior_coherent": int(f[12]) if f[12] else None,
            "two_ratio": num(13), "n_glob": int(f[14]) if f[14] else None,
            "g1_area": num(15), "g1_touch": int(f[20]) if len(f) > 20 and f[20] else None,
            "g2_area": num(21), "g2_sep": num(24),
        }
    for key, p in pics.items():
        p["rings"] = ring_norms.get(p["md5"], [])
    return pics


def group_stats(pics, group):
    xs = [p for p in pics.values() if p["flag"] == "ok" and p["tag"] == group]
    rims = [p["rim_diam"] for p in xs if p["rim_diam"]]
    rms = [p["rim_rms"] for p in xs if p["rim_rms"]]
    interior = [1 if (p["n_interior"] or 0) >= 1 else 0 for p in xs]
    coh = [1 if (p["n_interior_coherent"] or 0) >= 1 else 0 for p in xs]
    inp = [r[0] for p in xs for r in p["rings"] if r[0] < INTERIOR_HI]
    two = [p["two_ratio"] for p in xs if p["two_ratio"]]
    if not xs:
        return {"n": 0}
    def q(v, pr):
        return statistics.quantiles(v, n=100)[pr - 1] if len(v) > 1 else v[0]
    return {
        "n_ok": len(xs),
        "median_lens_diam_px": round(statistics.median(rims), 1) if rims else None,
        "iqr_lens_diam_px": [round(q(rims, 25), 1), round(q(rims, 75), 1)] if len(rims) > 1 else None,
        "median_within_frame_rim_rms_px": round(statistics.median(rms), 1) if rms else None,
        "frac_with_interior_ring": round(statistics.fmean(interior), 3),
        "frac_with_coherent_interior_ring": round(statistics.fmean(coh), 3),
        "median_interior_ring_norm": round(statistics.median(inp), 3) if inp else None,
        "n_interior_rings": len(inp),
        "frac_two_circle_split_improves": round(statistics.fmean([1 if t > 1.0 else 0 for t in two]), 3) if two else None,
        "median_two_improve_ratio": round(statistics.median(two), 3) if two else None,
        "n_with_two_ratio": len(two),
    }


def second_ruler_stats(pics):
    sec = [p for p in pics.values() if p["flag"] == "ok" and p["tag"] == "sec"]
    multi = [p for p in sec if (p["n_glob"] or 0) >= 2 and p["g1_area"]
             and p["g2_area"] and p["g2_area"] >= 0.5 * p["g1_area"]]
    touch = [p for p in sec if p["g1_touch"] == 1]
    seps = [p["g2_sep"] for p in sec if p["g2_sep"]]
    more1 = [p for p in sec if (p["n_glob"] or 0) >= 2]
    return {
        "n_sec_ok": len(sec),
        "n_frames_more_than_one_bright_component": len(more1),
        "n_frames_second_component_half_or_more_of_largest": len(multi),
        "multi_frame_examples": [p["path"] for p in multi[:5]],
        "n_frames_largest_component_touches_frame_border": len(touch),
        "median_top2_separation_px": round(statistics.median(seps), 1) if seps else None,
        "n_frames_with_two_components_reported": len(seps),
        "result": "no second ruler available",
        "reason": "the two frames whose second component reaches half the largest are Package Misalignment frames where the field of view is partly blocked, not a second cavity; no frame has the largest bright component touching the frame border, so no package or tray edge is imaged in frame; the many small second components sit at a near-fixed position above the cavity and are package features of unknown real length, so they give no scale. Every frame is one cavity, matching the CavityNN naming of the production drop.",
    }


def aggregate() -> int:
    p1 = load_phase1()
    gate = load_gate()
    candidates, lens14200, gate_scale = candidates_doc(p1, gate)
    pics = load_raw()

    ml = group_stats(pics, "ml")
    ctrl = group_stats(pics, "ctrl")
    sec = second_ruler_stats(pics)

    lens_central = lens14200["central_um_per_px"]
    gate_central = gate_scale["central_um_per_px"]
    bands = reverse_gate(gate_scale, gate_central, p1["median_diam_px"])
    margin = box_margin(gate_scale)
    gap_above = 100.0 * (lens_central - gate_central) / gate_central
    gap_below = 100.0 * (lens_central - gate_central) / lens_central

    candidates_doc_out = {
        "phase": "2 of the scale plan",
        "rule": "every candidate is labelled documented or assumed; no assumed nominal is presented as documented",
        "pixel_side": p1,
        "gate_boundary_used": {"switch_px": list(GATE_SWITCH_PX),
                               "source": "run/eda_full_20261015/gate_scale_estimate.json",
                               "cut_um": GATE_CUT_UM, "old_cut_um": GATE_OLD_CUT_UM},
        "candidates": candidates,
        "counts": {
            "documented_nominals": sum(1 for c in candidates if c["is_documented"]),
            "assumed_nominals": sum(1 for c in candidates if c["class"] == "assumed"),
            "not_available": sum(1 for c in candidates if c["class"] == "not_found"),
        },
    }
    OUT_CANDIDATES.write_text(json.dumps(candidates_doc_out, indent=1), encoding="utf-8")

    falsif = {
        "phase": "4 of the scale plan",
        "test_1_lens_spec": test1_lens_spec(),
        "test_2_multiple_lenses": {
            "class": "Multiple Lenses (P1_ML), folder-derived tag on 1,439 pictures",
            "sample": OUT_SAMPLE.name,
            "measured": {"multiple_lenses": ml, "single_lens_control_clear_folder": ctrl},
            "finding": multiple_lenses_finding(ml, ctrl),
        },
        "test_3_second_ruler": sec,
        "test_4_box_margin": {
            "definition": "at a scale S the gate switches on a longest box side of 19.41 to 19.61 px; a 300 micron debris at scale S spans 300/S px; the gap is the required annotation margin",
            "rows": margin,
            "deciding_number": box_margin_deciding(margin),
        },
    }
    OUT_FALSIF.write_text(json.dumps(falsif, indent=1), encoding="utf-8")

    scale_out = {
        "phase": "3 of the scale plan",
        "headline": {
            "lens_pixel_measurement": {"median_diam_px": p1["median_diam_px"],
                                       "iqr_diam_px": [p1["p25_diam_px"], p1["p75_diam_px"]],
                                       "rel_spread_pct": p1["rel_spread_pct"],
                                       "n": p1["n"]},
            "lens_implied_scale_um_per_px": lens14200["interval_um_per_px"],
            "gate_inversion_scale_um_per_px": gate_scale["interval_um_per_px"],
            "lens_central_um_per_px": round(lens_central, 4),
            "gate_central_um_per_px": round(gate_central, 4),
            "tension_pct_lens_above_gate": round(gap_above, 1),
            "tension_pct_gate_below_lens": round(gap_below, 1),
            "tension_note": "the two central readings are about 15 percent apart measured as the gate value below the lens value (%.1f percent), and about 17 percent measured as the lens value above the gate value (%.1f percent)" % (gap_below, gap_above),
            "resolution": "NOT resolved; quantified below",
        },
        "lens_14200_interval": lens14200,
        "gate_inversion_interval": gate_scale,
        "gate_read_back_at_each_scale": bands,
        "box_margin": margin,
        "the_two_readings": [
            "reading A: the scale is the gate inversion, about %.2f microns per pixel (interval %.2f to %.2f). The 789 px lens would then be about %.1f mm, below the usual soft-lens range, and the client gate is a clean 300 micron cut."
            % (gate_central, gate_scale["interval_um_per_px"][0], gate_scale["interval_um_per_px"][1],
               gate_central * p1["median_diam_px"] / 1000.0),
            "reading B: the scale is the lens measurement, about %.2f microns per pixel (interval %.2f to %.2f) from our assumed 14.2 mm lens. The client gate boundary then reads as about %.0f to %.0f microns instead of 300, so the annotation boxes overshoot the debris by about %.0f percent."
            % (lens_central, lens14200["interval_um_per_px"][0], lens14200["interval_um_per_px"][1],
               GATE_SWITCH_PX[0] * lens_central, GATE_SWITCH_PX[1] * lens_central,
               100.0 * (GATE_SWITCH_PX[0] * lens_central - 300.0) / 300.0),
        ],
        "evidence_that_would_separate_them": [
            "a written lens diameter from the client (the FMD Annotation Guide named but not present, or any document naming the real lens size)",
            "any frame showing two genuine cavities or the package or tray edge, giving a second ruler independent of the lens",
            "a lens product name or part number that fixes the diameter",
        ],
    }
    (RUN / "scale_intervals.json").write_text(json.dumps(scale_out, indent=1), encoding="utf-8")

    print(json.dumps({"ml": ml, "ctrl": ctrl, "sec": sec, "margin": margin}, indent=1))
    return 0


def multiple_lenses_finding(ml, ctrl):
    if not ml.get("n_ok"):
        return {"result": "not available", "reason": "no scanner rows"}
    return {
        "result": "The class does not present two resolvable full lens circles, so it does not give the within-frame lens-diameter repeatability the test sought.",
        "numbers": [
            "sample: %d Multiple Lenses frames and %d single-lens Clear control frames, all measured ok"
            % (ml["n_ok"], ctrl["n_ok"]),
            "rim circle diameter: Multiple Lenses %.1f px (IQR %.1f to %.1f) against control %.1f px (IQR %.1f to %.1f)"
            % (ml["median_lens_diam_px"], ml["iqr_lens_diam_px"][0], ml["iqr_lens_diam_px"][1],
               ctrl["median_lens_diam_px"], ctrl["iqr_lens_diam_px"][0], ctrl["iqr_lens_diam_px"][1]),
            "a two-circle split of the rim edge points improves the residual on %.1f percent of Multiple Lenses frames and %.1f percent of control frames (median ratio rms1/rms2 %.2f against %.2f, always below 1, so the split always fits worse)"
            % (100 * (ml["frac_two_circle_split_improves"] or 0),
               100 * (ctrl["frac_two_circle_split_improves"] or 0),
               ml["median_two_improve_ratio"] or 0, ctrl["median_two_improve_ratio"] or 0),
            "at least one dark ring in the cavity interior (normalised radius below 0.80) appears on %.1f percent of Multiple Lenses frames against %.1f percent of control frames, %d rings against %d"
            % (100 * ml["frac_with_interior_ring"], 100 * ctrl["frac_with_interior_ring"],
               ml["n_interior_rings"], ctrl["n_interior_rings"]),
            "the interior ring sits at median normalised radius %.2f on Multiple Lenses against %.2f on control, so the extra boundary is a smaller partial circle, not a second full lens at the rim"
            % (ml["median_interior_ring_norm"], ctrl["median_interior_ring_norm"]),
            "within-frame rim residual (the repeatability of one rim measurement) is %.1f px on Multiple Lenses against %.1f px on control"
            % (ml["median_within_frame_rim_rms_px"], ctrl["median_within_frame_rim_rms_px"]),
        ],
        "repeatability": "not available from within-frame lens pairs, because no frame yields two resolved lens circles. The class does contain a second dark boundary on %d of %d frames, at median 0.58 of the cavity radius, consistent with the URS description of one lens plus an additional partial lens, but a partial lens at 0.58 R_cav is not a second full lens and yields no diameter pair." % (round(ml["frac_with_interior_ring"] * ml["n_ok"]), ml["n_ok"]),
        "stability_reference": "not answered by this class either: with no two resolved rims there is no second measure of the same part to compare against the cavity.",
    }


def test1_lens_spec():
    return {
        "test": "if the scale were the gate inversion, the 789 px lens would be about %.1f mm; is that plausible for the product" % (15.3369 * 789.0 / 1000.0),
        "searched": [
            "docs/FM3 Edge Algorithm URS Final Draft .pdf (received)",
            "docs/Manufacturing Condition Ontology V1.docx (received)",
            "docs/reference/received_docs_nominals.md",
            "docs/reference/scale_provenance_20261015.md (Phase 0)",
        ],
        "what_exists": [
            "the URS names the product only as a contact lens and describes it as HEMA based (section 5.2.1, excess lens material); it gives no diameter, no brand and no product name",
            "the Ontology gives no lens dimension, only annotation-box size statistics in pixels",
            "the received set carries no lens diameter, no soft or rigid label and no product identifier",
        ],
        "what_does_not_exist": [
            "no received document names the lens product, its size, its material beyond HEMA or its type (soft, rigid, daily, scleral)",
            "no document names a 14.2 mm diameter either; the 14.2 mm used in our work is our own assumed figure",
        ],
        "result": "not available from the received documents. No received document states a lens diameter, so the physical plausibility of 12.1 mm against 14.2 mm cannot be settled from our documents. The general product class does not favour 12.1 mm: a soft hydrogel contact lens is normally about 13.8 to 14.5 mm across, and a 12.1 mm lens would sit below the usual range, so 14.2 mm is the more plausible diameter for a soft lens while neither is documented here.",
    }


def box_margin_deciding(margin):
    at18 = margin["lens_14200_central_18.0"]
    at15 = margin["gate_inversion_15.337"]
    return {
        "result": "the margin test does not separate the readings, and it makes the 18 micron scale the more comfortable one rather than the less",
        "deciding_numbers": {
            "at_18_0_um_per_px": "the box would be %s to %s px larger than a 300 micron debris, that is %s to %s percent of the box, about %s px on each side"
            % (at18["required_margin_px"][0], at18["required_margin_px"][1],
               at18["required_margin_pct_of_box"][0], at18["required_margin_pct_of_box"][1],
               round((at18["required_margin_px"][0] + at18["required_margin_px"][1]) / 4.0, 2)),
            "at_15_337_um_per_px": "the box would be %s to %s px larger than a 300 micron debris, that is %s to %s percent of the box, essentially zero"
            % (at15["required_margin_px"][0], at15["required_margin_px"][1],
               at15["required_margin_pct_of_box"][0], at15["required_margin_pct_of_box"][1]),
        },
        "reading": "a hand-drawn box around a speck about 17 px across overshooting by about 2.8 px is a normal, small margin, so a 14 to 15 percent overshoot is plausible and does not falsify the lens-implied scale; a zero margin is also plausible, so the margin test is consistent with both readings and decides neither",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--scanner-input", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    if a.sample:
        return build_sample()
    if a.scanner_input:
        return scanner_input()
    if a.aggregate:
        return aggregate()
    ap.error("pick --sample, --scanner-input or --aggregate")


if __name__ == "__main__":
    sys.exit(main())
