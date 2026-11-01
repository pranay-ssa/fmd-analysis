#!/usr/bin/env python3
"""Verifier for Phase 2, 3 and 4 of the scale plan.

It re-derives the headline intervals and the falsification numbers by a second
route, written independently of experiments/eda_full/scale_phase234.py: its own
parsing of the raw scanner output, its own arithmetic for every interval, its own
tension and box-margin computation. It also proves the builder rebuilds byte
identically and that the labelling, the interval form and the doc header all hold.

Writes nothing except when it re-runs the builder for the determinism check,
which is the point of that check.

Run:
    python experiments/eda_full/verify_scale_phase234.py
Exit 0 when every check passes.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "run" / "eda_full_20261015"
CAND = RUN / "scale_candidates.json"
FALS = RUN / "falsification.json"
SCALE = RUN / "scale_intervals.json"
RAW = RUN / "ml_raw.tsv"
SAMPLE = RUN / "ml_sample.txt"
RING = RUN / "ring_identity.json"
GATE = RUN / "gate_scale_estimate.json"
DOC = REPO / "reports" / "eda_full" / "scale_phase234_20261015.md"
AGENT = REPO / "experiments" / "eda_full" / "scale_phase234.py"
PROV = REPO / "docs" / "reference" / "scale_provenance_20261015.md"

GATE_SWITCH = (19.41, 19.61)

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str) -> None:
    CHECKS.append((name, bool(ok), note))


def med(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    cand = json.loads(CAND.read_text(encoding="utf-8"))
    fals = json.loads(FALS.read_text(encoding="utf-8"))
    scale = json.loads(SCALE.read_text(encoding="utf-8"))
    ring = json.loads(RING.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))

    # -- 1. the pixel side is the Phase-1 headline ---------------------------
    rv = ring["verdict"]["lens_diameter_px"]
    check("pixel_side_matches_phase1_median",
          cand["pixel_side"]["median_diam_px"] == rv["median_diam_px"],
          "scale_candidates median %s, ring_identity %s"
          % (cand["pixel_side"]["median_diam_px"], rv["median_diam_px"]))
    check("pixel_side_matches_phase1_iqr",
          cand["pixel_side"]["p25_diam_px"] == rv["p25_diam_px"]
          and cand["pixel_side"]["p75_diam_px"] == rv["p75_diam_px"],
          "IQR %s-%s against %s-%s"
          % (cand["pixel_side"]["p25_diam_px"], cand["pixel_side"]["p75_diam_px"],
             rv["p25_diam_px"], rv["p75_diam_px"]))

    # -- 2. the lens-implied scale interval, second route --------------------
    px = rv["median_diam_px"]
    endpoints = [14200.0 / 809.5, 14200.0 / 764.4, 14200.0 / px,
                 14200.0 / 760.0, 14200.0 / 777.3]
    lo2, hi2 = min(endpoints), max(endpoints)
    lens = [c for c in cand["candidates"] if c["id"] == "lens_diameter_14200_um"][0]
    got = lens["implied_scale"]["interval_um_per_px"]
    check("lens_interval_second_route",
          abs(got[0] - lo2) < 0.01 and abs(got[1] - hi2) < 0.01,
          "second route %.4f-%.4f, JSON %.4f-%.4f" % (lo2, hi2, got[0], got[1]))
    check("lens_central_second_route",
          abs(lens["implied_scale"]["central_um_per_px"] - 14200.0 / px) < 0.001,
          "14200/%s = %.4f, JSON %.4f" % (px, 14200.0 / px,
                                          lens["implied_scale"]["central_um_per_px"]))
    check("lens_is_labelled_assumed",
          lens["class"] == "assumed" and lens["is_documented"] is False,
          "class %s, is_documented %s" % (lens["class"], lens["is_documented"]))

    # -- 3. the gate inversion interval, second route ------------------------
    g_new_lo, g_new_hi = 300.0 / 19.61, 300.0 / 19.41
    g_old_lo, g_old_hi = 647.0 / 42.79, 647.0 / 42.08
    comb_lo, comb_hi = max(g_new_lo, g_old_lo), min(g_new_hi, g_old_hi)
    gs = gate["scale_estimate"]["implied_scale_combined"]
    check("gate_interval_second_route",
          abs(comb_lo - gs["scale_um_per_px_low"]) < 0.001
          and abs(comb_hi - gs["scale_um_per_px_high"]) < 0.001,
          "second route %.4f-%.4f, gate_scale_estimate %.4f-%.4f"
          % (comb_lo, comb_hi, gs["scale_um_per_px_low"], gs["scale_um_per_px_high"]))
    gate_cand = [c for c in cand["candidates"] if c["id"] == "client_cut_300_um_inverted"][0]
    check("gate_candidate_is_labelled_documented",
          gate_cand["class"] == "documented" and gate_cand["is_documented"] is True,
          "class %s, is_documented %s" % (gate_cand["class"], gate_cand["is_documented"]))
    check("gate_candidate_interval_matches",
          abs(gate_cand["implied_scale"]["interval_um_per_px"][0] - comb_lo) < 0.001
          and abs(gate_cand["implied_scale"]["interval_um_per_px"][1] - comb_hi) < 0.001,
          "candidate interval %s against second route %.4f-%.4f"
          % (gate_cand["implied_scale"]["interval_um_per_px"], comb_lo, comb_hi))
    check("gate_agrees_with_neither_candidate_scale",
          gs["agrees_with_18_1165"] is False and gs["agrees_with_18_25"] is False,
          "agreement %s" % gs["agreement"])

    # -- 4. the tension, stated with numbers and not resolved ----------------
    lens_c = lens["implied_scale"]["central_um_per_px"]
    gate_c = gate_cand["implied_scale"]["central_um_per_px"]
    gap_below = 100.0 * (lens_c - gate_c) / lens_c
    gap_above = 100.0 * (lens_c - gate_c) / gate_c
    hl = scale["headline"]
    check("tension_both_sides_present",
          abs(hl["lens_central_um_per_px"] - lens_c) < 0.01
          and abs(hl["gate_central_um_per_px"] - gate_c) < 0.01,
          "lens %.4f gate %.4f" % (lens_c, gate_c))
    check("tension_near_15_percent",
          abs(hl["tension_pct_gate_below_lens"] - gap_below) < 0.2,
          "gate below lens %.1f percent (JSON %.1f), lens above gate %.1f percent"
          % (gap_below, hl["tension_pct_gate_below_lens"], gap_above))
    check("tension_not_resolved",
          "NOT resolved" in hl["resolution"] and hl["resolution"].startswith("NOT resolved"),
          "resolution field %r" % hl["resolution"])
    check("tension_names_two_readings", len(scale["the_two_readings"]) == 2,
          "%d readings listed" % len(scale["the_two_readings"]))
    check("tension_names_separating_evidence",
          len(scale["evidence_that_would_separate_them"]) >= 2,
          "%d separating-evidence items" % len(scale["evidence_that_would_separate_them"]))

    # -- 5. the gate read back at each scale, and every figure names its scale
    bands = scale["gate_read_back_at_each_scale"]
    all_named = all("scale_um_per_px" in row for row in bands.values())
    check("every_reverse_gate_row_names_its_scale", all_named,
          "rows %s" % list(bands.keys()))
    b18 = bands["lens_measurement_central"]
    check("reverse_gate_at_lens_scale_second_route",
          abs(b18["cut_um_for_switch_low"] - GATE_SWITCH[0] * (14200.0 / px)) < 0.15
          and abs(b18["cut_um_for_switch_high"] - GATE_SWITCH[1] * (14200.0 / px)) < 0.15,
          "second route %.1f-%.1f um, JSON %.1f-%.1f"
          % (GATE_SWITCH[0] * (14200.0 / px), GATE_SWITCH[1] * (14200.0 / px),
             b18["cut_um_for_switch_low"], b18["cut_um_for_switch_high"]))
    bg = bands["gate_inversion_central"]
    check("reverse_gate_at_gate_scale_is_about_300",
          abs(bg["cut_um_for_switch_low"] - 300.0) < 5.0
          and abs(bg["cut_um_for_switch_high"] - 300.0) < 5.0,
          "cut at the gate scale reads %.1f-%.1f microns"
          % (bg["cut_um_for_switch_low"], bg["cut_um_for_switch_high"]))

    # -- 6. the box margin, second route -------------------------------------
    rows = fals["test_4_box_margin"]["rows"]
    for name, S in (("lens_14200_central_18.0", 18.0), ("gate_inversion_15.337", 15.3369),
                    ("published_18.1165", 18.1165), ("spoken_18.25", 18.25)):
        debris = 300.0 / S
        m_px = [GATE_SWITCH[0] - debris, GATE_SWITCH[1] - debris]
        box_mid = (GATE_SWITCH[0] + GATE_SWITCH[1]) / 2.0
        m_pct = [100.0 * g / box_mid for g in m_px]
        check("box_margin_%s_second_route" % name,
              abs(rows[name]["required_margin_px"][0] - m_px[0]) < 0.01
              and abs(rows[name]["required_margin_pct_of_box"][1] - m_pct[1]) < 0.05,
              "second route %.3f-%.3f px, %.2f-%.2f percent; JSON %.3f-%.3f px, %.2f-%.2f percent"
              % (m_px[0], m_px[1], m_pct[0], m_pct[1],
                 rows[name]["required_margin_px"][0], rows[name]["required_margin_px"][1],
                 rows[name]["required_margin_pct_of_box"][0], rows[name]["required_margin_pct_of_box"][1]))
    check("box_margin_reports_px_and_percent_at_every_scale",
          all("required_margin_px" in r and "required_margin_pct_of_box" in r
              and "scale_um_per_px" in r for r in rows.values()),
          "scales %s" % list(rows.keys()))

    # -- 7. the Multiple Lenses finding, second route ------------------------
    tags = {}
    for line in SAMPLE.read_text(encoding="utf-8").splitlines()[1:]:
        f = line.split(",")
        if len(f) >= 4:
            tags[f[2] or f[3]] = f[0]
    rims_ml, rims_ctrl = [], []
    ringnorm = defaultdict(list)
    for line in RAW.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if f[0] == "R":
            if len(f) > 6 and f[5]:
                ringnorm[f[1]].append(float(f[5]))
        elif f[0] == "P" and len(f) > 8 and f[7] == "ok" and f[8]:
            key = f[2] or f[3]
            if tags.get(key) == "ml":
                rims_ml.append(float(f[8]))
            elif tags.get(key) == "ctrl":
                rims_ctrl.append(float(f[8]))
    m = fals["test_2_multiple_lenses"]["measured"]
    check("ml_median_second_route",
          abs(med(rims_ml) - m["multiple_lenses"]["median_lens_diam_px"]) < 0.1,
          "second route %.1f px, JSON %.1f px"
          % (med(rims_ml), m["multiple_lenses"]["median_lens_diam_px"]))
    check("ctrl_median_second_route",
          abs(med(rims_ctrl) - m["single_lens_control_clear_folder"]["median_lens_diam_px"]) < 0.1,
          "second route %.1f px, JSON %.1f px"
          % (med(rims_ctrl), m["single_lens_control_clear_folder"]["median_lens_diam_px"]))
    ml_keys = {k for k, v in tags.items() if v == "ml"}

    def interior_frac(keys):
        if not keys:
            return None
        return sum(1 for k in keys if any(x < 0.80 for x in ringnorm.get(k, []))) / len(keys)
    check("ml_interior_ring_fraction_second_route",
          abs(interior_frac(ml_keys)
              - m["multiple_lenses"]["frac_with_interior_ring"]) < 0.01,
          "second route %.3f, JSON %.3f"
          % (interior_frac(ml_keys), m["multiple_lenses"]["frac_with_interior_ring"]))
    finding = fals["test_2_multiple_lenses"]["finding"]
    check("ml_finding_concludes_no_two_lenses",
          "does not present two resolvable full lens circles" in finding["result"],
          finding["result"])

    # -- 8. the second ruler finding -----------------------------------------
    sec = fals["test_3_second_ruler"]
    check("second_ruler_has_result",
          sec.get("result") == "no second ruler available" and sec["n_sec_ok"] > 0,
          "result %r over %d frames" % (sec.get("result"), sec["n_sec_ok"]))
    check("second_ruler_reports_multi_cavity_counts",
          "n_frames_second_component_half_or_more_of_largest" in sec
          and "n_frames_largest_component_touches_frame_border" in sec,
          "second half-or-more %s, border-touch %s"
          % (sec["n_frames_second_component_half_or_more_of_largest"],
             sec["n_frames_largest_component_touches_frame_border"]))

    # -- 9. the lens-spec test ends in a result ------------------------------
    t1 = fals["test_1_lens_spec"]
    check("lens_spec_test_has_result",
          "result" in t1 and t1["result"].startswith("not available"),
          t1["result"][:70])
    check("lens_spec_test_searched_received_docs",
          any("URS" in s for s in t1["searched"]) and any("Ontology" in s for s in t1["searched"]),
          "searched %d sources" % len(t1["searched"]))

    # -- 10. every candidate is labelled, none assumed shown as documented ----
    documented = [c for c in cand["candidates"] if c["class"] == "documented"]
    assumed = [c for c in cand["candidates"] if c["class"] == "assumed"]
    notfound = [c for c in cand["candidates"] if c["class"] == "not_found"]
    check("candidate_labels_present_and_consistent",
          all(c["class"] in ("documented", "assumed", "not_found") for c in cand["candidates"])
          and all(c["is_documented"] for c in documented)
          and all(not c["is_documented"] for c in assumed + notfound),
          "documented %d, assumed %d, not_found %d"
          % (len(documented), len(assumed), len(notfound)))
    check("no_assumed_nominal_presented_as_documented",
          all("documented" not in c["documented_or_assumed"] or c["is_documented"]
              for c in cand["candidates"]),
          "all assumed rows carry a not-documented label")
    check("the_source_says_14200_is_ours",
          "no received document" in PROV.read_text(encoding="utf-8")
          or "our own figure" in PROV.read_text(encoding="utf-8"),
          "scale_provenance_20261015.md backs the assumed labelling")

    # -- 11. doc header -------------------------------------------------------
    head = DOC.read_text(encoding="utf-8").splitlines()[:6]
    check("doc_five_line_header",
          len(head) >= 6 and head[0] == "---" and head[1].startswith("title:")
          and head[2] == "date: 2026-10-15" and head[3] == "type: result"
          and head[4] == "status: active"
          and head[5] == "where: reports/eda_full/scale_phase234_20261015.md",
          "header %r" % (head,))

    # -- 12. byte identical rebuild ------------------------------------------
    before = {p.name: md5(p) for p in (CAND, FALS, SCALE)}
    subprocess.run([sys.executable, str(AGENT), "--aggregate"],
                   cwd=str(REPO), capture_output=True, check=True)
    after = {p.name: md5(p) for p in (CAND, FALS, SCALE)}
    check("aggregation_rebuild_is_byte_identical", before == after,
          "before %s after %s" % (before, after))

    failed = [c for c in CHECKS if not c[1]]
    for name, okk, note in CHECKS:
        print("[%s] %s: %s" % ("ok" if okk else "FAIL", name, note))
    print("checks: %d, failed: %d" % (len(CHECKS), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
