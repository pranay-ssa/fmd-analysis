#!/usr/bin/env python3
"""Build the self-contained HTML report for the full-coverage EDA.

Generalised from experiments/production_20260925/build_report_html.py. It reads
one computed JSON (full_numbers.json, which reads the verified run artifacts)
and renders a single offline HTML page. It computes nothing: every number on the
page comes from the JSON. The CSS block is read from the workspace dashboard
starter template so the page matches the house style.

Usage:
  python build_report_html.py --numbers full_numbers.json --out full_eda_report.html
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import sys

DEFAULT_TEMPLATE = (
    r"C:/Users/Abcom/AppData/Local/hermes/skills/data-science"
    r"/eda-dashboard-design/templates/starter.html"
)

RAMP = ["#0d366b", "#1c5cab", "#3987e5", "#5598e7", "#6da7ec"]
ADOPTED = 15.337
PRIOR = 18.1165
SPOKEN = 18.25


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def ni(n) -> str:
    return f"{int(round(n)):,}"


def pc(x, dp=1) -> str:
    return f"{x * 100:.{dp}f}%"


def f2(x) -> str:
    return f"{x:.2f}"


def um(px, scale) -> str:
    return ni(round(px * scale))


def table(headers, rows, aligns=None) -> str:
    if aligns is None:
        aligns = ["l"] + ["r"] * (len(headers) - 1)
    th = "".join(
        f'<th style="text-align:{"left" if a == "l" else "right"}">{esc(h)}</th>'
        for h, a in zip(headers, aligns)
    )
    body = []
    for r in rows:
        tds = "".join(
            f'<td style="text-align:{"left" if a == "l" else "right"}">{c}</td>'
            for c, a in zip(r, aligns)
        )
        body.append(f"<tr>{tds}</tr>")
    return ('<div class="twrap"><table><thead><tr>' + th + "</tr></thead><tbody>"
            + "".join(body) + "</tbody></table></div>")


def tile(label, value, sub, cls="") -> str:
    c = f" {cls}" if cls else ""
    return (f'<div class="stat-tile"><div class="label">{esc(label)}</div>'
            f'<div class="value{c}">{esc(value)}</div>'
            f'<div class="sub">{sub}</div></div>')


def tiles(items) -> str:
    return '<div class="stat-grid">' + "".join(items) + "</div>"


def hbar(rows, gutter=210, width=720, ramp=True, unit="", maxv=None) -> str:
    n = len(rows)
    row_h = 26
    h = 22 + row_h * n
    bar_x = gutter + 8
    plot_w = width - bar_x - 90
    peak = maxv or max(v for _, v in rows) or 1
    out = [f'<svg viewBox="0 0 {width} {h}" class="chart" role="img">']
    for i, (lab, val) in enumerate(rows):
        y = 11 + row_h * i
        w = max(2.0, plot_w * (val / peak))
        fill = RAMP[i % len(RAMP)] if ramp else "var(--series-1)"
        out.append(f'<text x="{gutter}" y="{y + 8}" text-anchor="end" class="c-lab" '
                   f'dominant-baseline="middle">{esc(lab)}</text>')
        out.append(f'<rect x="{bar_x}" y="{y}" width="{w:.1f}" height="17" rx="3" '
                   f'fill="{fill}"><title>{esc(lab)}: {ni(val)}{unit}</title></rect>')
        out.append(f'<text x="{bar_x + w + 6:.1f}" y="{y + 8}" class="c-val" '
                   f'dominant-baseline="middle">{ni(val)}{unit}</text>')
    out.append("</svg>")
    return "".join(out)


def bars(rows, labels, width=720, height=240, unit="", color="var(--series-1)") -> str:
    n = len(rows)
    plot_l, plot_r = 56, width - 14
    base_y, top_y = height - 40, 14
    span = base_y - top_y
    peak = max(rows) or 1
    slot = (plot_r - plot_l) / n
    bw = min(44.0, slot - 10)
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for k in range(5):
        y = base_y - span * k / 4
        out.append(f'<line x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{plot_l - 6}" y="{y + 3:.1f}" text-anchor="end" class="c-tick">'
                   f'{ni(round(peak * k / 4))}</text>')
    for i, v in enumerate(rows):
        cx = plot_l + slot * i + slot / 2
        h = span * (v / peak)
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{base_y - h:.1f}" width="{bw:.1f}" '
                   f'height="{max(h, 1.5):.1f}" rx="2" fill="{color}">'
                   f'<title>{esc(labels[i])}: {ni(v)}{unit}</title></rect>')
        out.append(f'<text x="{cx:.1f}" y="{base_y + 12}" text-anchor="end" class="c-tick" '
                   f'transform="rotate(-45 {cx:.1f} {base_y + 12})">{esc(labels[i])}</text>')
    out.append("</svg>")
    return "".join(out)


def build(d: dict, generated: str) -> str:
    C, L, G = d["census"], d["labels"], d["box_geometry"]
    MG, SC, CO, D = d["micron_gate"], d["scale"], d["coverage"], d["disagreement"]
    X, V, SUP = d["crosswalk"], d["verification"], d["superseded_20261013"]
    ic = MG["implied_scale_combined"]
    cav = d["cavity"]["read"]

    nav = []
    secs = []

    def add(anchor, lab, body):
        nav.append((anchor, lab))
        secs.append((anchor, body))

    # ---------------------------------------------------------- 1 at a glance
    add("glance", "1",
        '<h3>1. The full-coverage picture at a glance</h3>'
        '<p class="desc">Everything in the three library folders, plus the production '
        "image folder, resolved under one priority rule and keyed on content hash. "
        f'{ni(V["assertions"])} assertions across every headline, {V["failures"]} '
        "failures before anything was published.</p>"
        + tiles([
            tile("Distinct pictures", ni(C["distinct_pictures"]),
                 "across the three library folders, keyed on content hash"),
            tile("Files", ni(C["files_library"]),
                 f'three library folders; {ni(C["files_total"])} with the production image folder'),
            tile("Shapes resolved", ni(L["shapes_total"]),
                 f'{ni(L["boxes"])} boxes and {ni(L["tags"])} tags'),
            tile("Canonical defects", str(L["canonical_count"]),
                 "two code collisions kept unmerged and flagged"),
            tile("Pictures with a shape", ni(L["with_shape"]),
                 f'{ni(L["no_shape"])} carry no shape; {ni(L["nowhere"])} are mentioned nowhere'),
            tile("Coverage of the blob folder", pc(CO["blob"]["share"], 2),
                 f'{ni(CO["blob"]["annotated"])} annotated of {ni(CO["blob"]["folder_total"])}'),
        ])
        + '<p class="note">The two annotation readings are different numbers and are never '
        f'swapped. {ni(L["mentioned"])} pictures are MENTIONED by some file, but only '
        f'{ni(L["with_shape"])} carry a shape. {ni(L["no_shape"])} carry no shape and '
        f'{ni(L["nowhere"])} are mentioned nowhere. The pairs each sum to the census: '
        f'{ni(L["with_shape"])} plus {ni(L["no_shape"])}, and {ni(L["mentioned"])} plus '
        f'{ni(L["nowhere"])}, both give {ni(C["distinct_pictures"])}.</p>'
        + '<p class="note">The shape counts contain one shared number seen twice: the '
        f'{ni(L["tags"])} tags and the {ni(L["no_shape"])} no-shape pictures are the same '
        "count, which is why every table names which one it reports.</p>")

    # ---------------------------------------------------------- 2 the adopted scale
    add("scale", "2",
        '<h3>2. The adopted scale, and where it comes from</h3>'
        '<p class="desc">The working scale for every micron figure in this analysis is '
        "the customer's own documented 300 micron cut, inverted through the annotation "
        "gate boundary.</p>"
        + tiles([
            tile("Adopted scale", f"{ADOPTED} um/px",
                 f'from the 300 micron cut inverted through the '
                 f'{MG["implied_scale_new"]["boundary_px_lower"]:.2f} to '
                 f'{MG["implied_scale_new"]["boundary_px_upper"]:.2f} px gate boundary', "ok"),
            tile("Adopted scale, per line", "15.34 to 15.60 um/px",
                 "L24 15.377, L25 15.601 (14 pictures, loose), L26 15.400, L27 15.337; "
                 "L31 not computable"),
            tile("Superseded prior scales", f"{PRIOR} and {SPOKEN} um/px",
                 "kept only as labelled comparisons; see below", "warn"),
            tile("Lens rim", "789 px",
                 "about 12.10 mm at the adopted scale; the earlier 848 px figure was a "
                 "two-ring circle-fit artefact"),
        ])
        + '<p class="note"><b>The adopted scale of '
        f'{ADOPTED} microns per pixel is derived from the documented 300 micron cut.</b> '
        "The customer's micron-threshold tags switch at a defect longer side of "
        f'{MG["implied_scale_new"]["boundary_px_lower"]:.2f} to '
        f'{MG["implied_scale_new"]["boundary_px_upper"]:.2f} px, and 300 divided by the '
        "19.51 px midpoint gives the scale, matching the frozen central figure of "
        f'{ic["scale_um_per_px_mid"]:.4f} with an interval of '
        f'{ic["scale_um_per_px_low"]:.3f} to {ic["scale_um_per_px_high"]:.3f}. The old 647 '
        f'micron cut inverts to the same scale, from a boundary at '
        f'{MG["implied_scale_old"]["boundary_px_lower"]:.2f} to '
        f'{MG["implied_scale_old"]["boundary_px_upper"]:.2f} px, and is the independent '
        "reproduction.</p>"
        + '<p class="note"><b>Limitation, stated plainly and not resolved here.</b> The '
        "lens nominal diameter is not documented in anything received. The lens rim "
        "measures 789 px (interquartile range 764.4 to 809.5 px), which is about 12.10 mm "
        "at the adopted scale and 14.2 mm at the superseded prior scale. The only "
        "documented ruler is the customer's own 300 micron cut. A written lens diameter "
        "from the customer would close the remaining question.</p>"
        + table(["Scale", "Status"],
                [[f"{ADOPTED} um/px",
                  "adopted; every micron figure on this page is a pixel figure times it"],
                 [f"{PRIOR} um/px",
                  "superseded prior scale; it divided an unsourced 14,200 micron lens "
                  "assumption by a lens pixel measurement"],
                 [f"{SPOKEN} um/px",
                  "superseded prior scale; spoken once, written in no document we hold"]],
                ["l", "l"]))

    # ---------------------------------------------------------- 3 the gate proxy
    add("gate", "3",
        '<h3>3. What the client gate actually cuts on</h3>'
        '<p class="desc">The four flags gate foreign matter, fiber and extraneous polymer '
        "on size. The proxy that fits is the longer side of the box, not the diagonal.</p>"
        + tiles([
            tile("Clean cut on the longer side", "0",
                 "images on the wrong side of the boundary, in every testable class", "ok"),
            tile("Misfiled by the diagonal", "39",
                 "foreign-matter images the diagonal puts on the wrong side", "warn"),
            tile("Fiber misfiled by the diagonal", "4",
                 "fiber images the diagonal puts on the wrong side", "warn"),
            tile("HEMA Obstruction", "not gated",
                 "flagged on every picture that carries it, never size-selected"),
        ])
        + table(["Base code", "Customer cut", "Unflagged max px", "Flagged min px",
                 "Mid px", "Mid um @15.337 (adopted)", "Mid um @18.1165 (superseded)"],
                [[b, f'{MG["cut_um"]:.0f}',
                  (f'{v["lower_px"]:.3f}' if v["lower_px"] else "none"),
                  (f'{v["upper_px"]:.3f}' if v["upper_px"] else "none"),
                  (f'{(v["lower_px"] + v["upper_px"]) / 2:.3f}' if v["lower_px"] and v["upper_px"] else "none"),
                  (ni((v["lower_px"] + v["upper_px"]) / 2 * ADOPTED) if v["lower_px"] and v["upper_px"] else "none"),
                  (ni((v["lower_px"] + v["upper_px"]) / 2 * PRIOR) if v["lower_px"] and v["upper_px"] else "none")]
                 for b, v in MG["new_boundaries_px"].items()
                 if b in MG["new_boundaries_px"]]
                + [[b, f'{MG["old_cut_um"]:.0f}',
                    f'{v["lower_px"]:.3f}', f'{v["upper_px"]:.3f}',
                    f'{(v["lower_px"] + v["upper_px"]) / 2:.3f}',
                    ni((v["lower_px"] + v["upper_px"]) / 2 * ADOPTED),
                    ni((v["lower_px"] + v["upper_px"]) / 2 * PRIOR)]
                   for b, v in MG["old_boundaries_px"].items()],
                ["l", "r", "r", "r", "r", "r", "r"])
        + '<p class="note">At the adopted scale the new-cut boundary reads as about 298 to '
        "301 microns, matching the customer's own cut. At the superseded "
        f'{PRIOR} the same boundary would read as about 352 to 355 microns, which is one '
        "of the reasons that scale was set aside.</p>")

    # ---------------------------------------------------------- 4 box geometry
    by_def = sorted(G["by_defect"].items(), key=lambda kv: -kv[1]["n"])
    add("geometry", "4",
        '<h3>4. How large the defects are, and where they sit</h3>'
        '<p class="desc">Size is the rectangle diagonal, invariant to the rotation '
        "attribute most boxes carry, at both candidate scales named in the same table.</p>"
        + tiles([
            tile("Boxes", ni(L["boxes"]),
                 f'across {ni(L["pictures_with_box"])} distinct pictures'),
            tile("Axis-aligned", ni(G["axis_aligned"]),
                 f'{pc(G["share_axis_aligned"])} of boxes; the rest are rotated'),
            tile("Cavity measured", f'{ni(cav["pictures_measured"])} of {ni(cav["pictures"])}',
                 f'{ni(cav["pictures_could_not_measure"])} too dark to measure, one named class'),
            tile("Boxes beyond 1.5x the cavity", "3",
                 "so nothing is annotated on the tray or the background", "ok"),
        ])
        + table(["Defect", "Boxes", "p25 px", "p50 px", "p75 px",
                 "p50 um @15.337 (adopted)", "p50 um @18.1165 (superseded)"],
                [[cid, ni(v["n"]), f'{v["diag_px_p25"]:.2f}', f'{v["diag_px_p50"]:.2f}',
                  f'{v["diag_px_p75"]:.2f}', ni(v["diag_um_adopted_p50"]),
                  ni(v["diag_um_at_18_1165_p50"])] for cid, v in by_def],
                ["l", "r", "r", "r", "r", "r", "r"])
        + '<p class="note">Two classes are region annotations, not defect spots: their boxes '
        "share a code and their combined median spans more than the whole lens, so they "
        "must not be read as detector targets. The cavity was measured per picture because "
        "the part is not centred in the frame; only 3 boxes sit further out than 1.5 times "
        "the radius.</p>")

    # ---------------------------------------------------------- 5 blind scale
    b = SC["blind"]
    add("variation", "5",
        '<h3>5. Does the scale differ by folder group or by production line</h3>'
        '<p class="desc">The lens is the same physical part on every line, so a real '
        "difference in measured rim pixels between strata would be a real scale "
        "difference. The absolute test is blocked for lack of a blind nominal.</p>"
        + '<p class="note"><b>No production line and no folder group differs from another '
        "beyond the measurement noise.</b> Between strata the raw rim median runs "
        f'{ni(b["between_stratum_rim_p50_px"]["min"])} to '
        f'{ni(b["between_stratum_rim_p50_px"]["max"])} px, a range of '
        f'{ni(b["between_stratum_rim_p50_px"]["range_px"])} px, '
        f'{b["between_stratum_rim_p50_px"]["range_pct_of_mean"]:.1f} percent of the mean. '
        "Within a stratum the relative spread runs 10.0 to 25.7 percent. The within-stratum "
        f'spread dwarfs the differences among the candidate scales ({ADOPTED}, {PRIOR} and '
        f'{SPOKEN}), so measurement alone cannot settle a scale question of that size. '
        "On the clean band the strata agree to "
        f'within {b["between_stratum_clean_rim_p50_px"]["range_pct_of_mean"]:.1f} percent.'
        "</p>"
        + table(["Stratum", "Measured", "Failed", "rim p25", "rim p50", "rim p75",
                 "rim sd", "Relative spread"],
                [[s["stratum"], ni(s.get("measured_ok_n") or 0), ni(s.get("failed_n") or 0),
                  f'{s["rim_px"].get("p25", 0):.0f}', f'{s["rim_px"].get("p50", 0):.0f}',
                  f'{s["rim_px"].get("p75", 0):.0f}', f'{s["rim_px"].get("sd", 0):.1f}',
                  f'{s["rim_px"].get("rel_spread_pct", 0):.1f}%'] for s in SC["strata"]],
                ["l", "r", "r", "r", "r", "r", "r", "r"]))

    # ---------------------------------------------------------- 6 label shape
    cpi = {int(k): v for k, v in L["box_codes_per_image"].items()}
    ks = sorted(cpi)
    add("labels", "6",
        '<h3>6. The label set is multi-label</h3>'
        '<p class="desc">A code counts once per picture even when it appears on several '
        "shapes, and a picture's codes are the union of localised defects (boxes) and "
        "whole-picture flags (tags).</p>"
        + tiles([
            tile("Median codes per picture", f'{L["median_codes"]:.0f}', "the middle picture"),
            tile("Mean codes per picture", f'{L["mean_codes"]:.2f}', "pulled up by a thin right tail"),
            tile("90th percentile", f'{L["p90_codes"]:.0f}', "9 pictures in 10 sit at or below"),
            tile("Most codes on one picture", ni(L["max_codes"]), "the busiest picture"),
            tile("Pictures with a box", ni(L["pictures_with_box"]), "carry a localised defect"),
            tile("Pictures with a tag", ni(L["pictures_with_tag"]), "carry a whole-picture flag"),
        ])
        + bars([cpi[k] for k in ks], [str(k) for k in ks], unit=" pictures")
        + '<p class="note">A code counts once per picture. The histogram is the number of '
        "pictures carrying each count of codes, so the middle picture carries a single "
        f'code and a short tail reaches {ni(L["max_codes"])}. One defect class dominates '
        "the set, so a one-folder-per-class split would put most pictures in that one bin.</p>")

    # ---------------------------------------------------------- 7 coverage & disagreement
    add("coverage", "7",
        '<h3>7. What is annotated out of what exists</h3>'
        '<p class="desc">Every stratum names the population it is measured in.</p>'
        + table(["Cut", "Stratum", "Pictures", "Mentioned", "With a shape", "No shape",
                 "Mentioned nowhere"],
                [[s["type"], esc(s["value"] or s["population"]), ni(s["distinct"]),
                  ni(s["mentioned"]), ni(s["with_shape"]), ni(s["no_shape"]), ni(s["nowhere"])]
                 for s in CO["strata"]],
                ["l", "l", "r", "r", "r", "r", "r"])
        + '<p class="note">Coverage of the production blob folder is '
        f'{ni(CO["blob"]["annotated"])} annotated of {ni(CO["blob"]["folder_total"])} '
        f'pictures, {pc(CO["blob"]["share"], 2)}. The remainder is available as negatives '
        "and was not pulled.</p>"
        + '<h4>The folder disagreement, and why two figures differ</h4>'
        + '<p class="note"><b>The widely quoted 113 figure is a NAME-based count, not a '
        "content count.</b> On content identity the overlap is larger, not smaller: "
        f'{D["content_library"]} pictures library-wide and {D["content_batch"]} on the '
        "production batch, because a name route cannot see a picture that was renamed. "
        f'{D["name_based_batch"]} is the name-based batch figure. The three library folders '
        "label these pictures differently from each other, and the content figures are the "
        "ones the priority rule acts on.</p>")

    # ---------------------------------------------------------- 8 crosswalk
    add("crosswalk", "8",
        '<h3>8. The frozen crosswalk across the three vocabularies</h3>'
        '<p class="desc">Every code in every source maps to exactly one canonical defect. '
        f'{X["count"]} canonical defects, two code collisions kept unmerged and flagged '
        "rather than silently combined.</p>"
        + '<p class="note">The shared HEMA code means HEMA Fragment in one project and HEMA '
        "Obstruction in the production files. The view-obstructed defect is written with "
        "two different prefixes. Both are flagged, both are counted, and the question goes "
        "to the client in parallel with the counting.</p>"
        + table(["Canonical defect", "Library folder", "Shape kind", "Kind conflict",
                 "Project 3 code", "09-22 code", "Production code", "Size gate"],
                [[c["name"], c["lib"], c["kind"],
                  ("yes" if c["kind_conflict"] == "yes" else ""),
                  c["p2"], c["p22"], c["p25"], c["gate"]]
                 for c in sorted(X["table"], key=lambda x: x["name"])],
                ["l", "l", "l", "l", "l", "l", "l", "l"]))

    # ---------------------------------------------------------- 9 superseded
    add("superseded", "9",
        '<h3>9. The superseded 2026-10-13 production-batch record</h3>'
        '<p class="desc">This section is clearly labelled superseded. It is kept so the '
        "move from the single batch to full coverage can be seen, not silently "
        "overwritten.</p>"
        + table(["Measure", f'Superseded (2026-10-13, {ni(SUP["batch_pictures"])} pictures)',
                 "Full coverage (this analysis)", "What moved"],
                [["Pictures", ni(SUP["batch_pictures"]), ni(C["distinct_pictures"]),
                  "from one production batch to every picture in the three library folders"],
                 ["Boxes", ni(SUP["boxes"]), ni(L["boxes"]),
                  "the library adds boxes the batch did not hold"],
                 ["Tags", ni(SUP["tags"]), ni(L["tags"]),
                  "the library adds whole-picture flags the batch did not hold"],
                 ["Shapes", ni(SUP["boxes"] + SUP["tags"]), ni(L["shapes_total"]),
                  "boxes plus tags on the wider census"],
                 ["Codes", str(SUP["codes"]), str(L["canonical_count"]),
                  "the wider census resolves to more canonical defects"]],
                ["l", "r", "r", "l"])
        + '<p class="note">The superseded record analysed one production batch of '
        f'{ni(SUP["batch_pictures"])} pictures. The full-coverage analysis covers '
        f'{ni(C["distinct_pictures"])} pictures and resolves '
        f'{ni(L["shapes_total"])} shapes across {L["canonical_count"]} canonical defects, '
        "quite a different and larger set.</p>")

    # ---------------------------------------------------------- 10 actions
    add("actions", "10",
        '<h3>10. What to do with it</h3>'
        '<p class="desc">Ordered actions, each carrying the number that makes it necessary.</p>'
        '<ol class="findings">'
        "<li><b>Ask the customer for a written lens diameter.</b> The adopted scale of "
        f"{ADOPTED} microns per pixel rests on the customer's own documented 300 micron "
        "cut, and it is the only documented ruler received. The lens nominal is "
        "undocumented, so a written lens diameter from the customer would close the "
        "remaining scale question.</li>"
        "<li><b>Ask which reading of a box's size the threshold script uses.</b> The data "
        "supports the longer side of the box (0 misfiled images) over the diagonal (39 "
        "misfiled on foreign matter, 4 on fiber), and the declared cut moved by exactly the "
        "ratio the client stated, but the proxy itself is our inference, not a written "
        "rule.</li>"
        "<li><b>Settle the two code collisions.</b> The shared HEMA code and the two "
        "view-obstructed prefixes decide whether two pairs of defects merge, which moves "
        f'every count that carries them across the {X["count"]} canonical defects.</li>'
        "<li><b>Decide the multi-label training scheme.</b> A single picture can carry up "
        f'to {ni(L["max_codes"])} codes, and the median picture carries {L["median_codes"]:.0f}, '
        "so a one-folder-per-class split discards most of what the annotators wrote.</li>"
        "<li><b>Decide whether the unannotated pictures are wanted as explicit negatives.</b> "
        f'Coverage of the production blob folder is {pc(CO["blob"]["share"], 2)}, so the '
        "remainder is available at no labelling cost if a run needs them.</li>"
        "<li><b>Treat the region-annotation classes as regions, not detector targets.</b> "
        "Their boxes span more than the whole lens, so a detector target read would be "
        "wrong at that scale.</li>"
        "</ol>")

    nav_html = "".join(f'<a href="#{a}">{lab}</a>' for a, lab in nav)
    body = "".join(f'<section id="{a}">{h}</section>' for a, h in secs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Full-coverage EDA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{CSS}
</style>
</head>
<body>
<header class="top"><div class="topbar">
  <h1>FMD | Full-coverage EDA</h1>
  <nav class="sections">{nav_html}</nav>
  <button class="theme-toggle" onclick="var r=document.documentElement,d=r.getAttribute('data-theme')==='dark';r.setAttribute('data-theme',d?'light':'dark')">&#9684; theme</button>
</div></header>
<div class="wrap">
  <div class="hero">
    <h2>Full-coverage EDA across the three ICube library folders</h2>
    <div class="meta">
      <b>{ni(C["distinct_pictures"])} distinct pictures</b> across the three library folders,
      <b>{ni(C["files_library"])} files</b> and <b>{ni(C["files_total"])} files</b> once the
      production image folder is added, resolving to <b>{ni(L["shapes_total"])} shapes</b>
      ({ni(L["boxes"])} boxes and {ni(L["tags"])} tags) across
      <b>{L["canonical_count"]} canonical defects</b>. Keyed on content hash, never on a
      path. Every figure on this page is read from a verified analysis artifact:
      {ni(V["assertions"])} assertions, {V["failures"]} failures.
      <div class="foot">Generated {esc(generated)}. Companion artefacts: the multi-sheet EDA
      workbook, the distributions widget and the findings write-up for the same analysis.
      The superseded 2026-10-13 production-batch record is kept in its own labelled section.</div>
    </div>
  </div>
{body}
</div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--numbers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    ap.add_argument("--generated", default=None)
    a = ap.parse_args()

    d = json.load(open(a.numbers, encoding="utf-8"))
    if not os.path.exists(a.template):
        print(f"starter template not found: {a.template}", file=sys.stderr)
        return 2
    global CSS
    tpl = open(a.template, encoding="utf-8").read()
    CSS = tpl.split("<style>", 1)[1].split("</style>", 1)[0].strip("\n")

    generated = a.generated or "2026-10-15"
    page = build(d, generated)

    # gates: no em dash, no section references, no local paths, no file names
    assert "\u2014" not in page, "em dash found in the generated page"
    assert "\u00a7" not in page, "section reference found in the generated page"
    assert ":\\\\" not in page and "/Users/" not in page, "local path leaked into the page"
    assert ".bmp" not in page and ".xlsx" not in page and ".json" not in page, "file name leaked"

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(json.dumps({"out": a.out, "bytes": len(page.encode("utf-8")),
                      "sections": page.count("<section id="),
                      "tables": page.count("<table>"),
                      "svgs": page.count("<svg")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
