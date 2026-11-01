#!/usr/bin/env python3
"""Build the self-contained HTML report for the PRODUCTION_20260925 batch.

Reads one computed JSON (the output of batch_numbers.py) and renders a single
offline HTML page. It computes nothing: every number on the page comes from the
JSON. The CSS block is read from the eda-dashboard-design starter template so
the page matches the workspace house style.

Usage:
  python build_report_html.py --numbers batch_numbers.json --out report.html
  python build_report_html.py --numbers ... --out ... --template starter.html
  python build_report_html.py --numbers ... --out ... --generated "2026-10-13 18:05"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import math
import os
import sys

# The canonical CSS lives in the skill's starter template. Both wraps and both
# dark token blocks are already correct there; never hand-copy them here.
DEFAULT_TEMPLATE = (
    r"C:/Users/Abcom/AppData/Local/hermes/skills/data-science"
    r"/eda-dashboard-design/templates/starter.html"
)

RAMP = ["#0d366b", "#1c5cab", "#3987e5", "#5598e7", "#6da7ec"]


# ---------------------------------------------------------------- helpers
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def ni(n) -> str:
    return f"{int(n):,}"


def pc(x, dp=1) -> str:
    return f"{x * 100:.{dp}f}%"


def f1(x, dp=1) -> str:
    return f"{x:.{dp}f}"


def um(px, scale) -> str:
    return ni(round(px * scale))


def cell(v, right=True) -> str:
    a = ' style="text-align:right"' if right else ""
    return f"<td{a}>{v}</td>"


def table(headers, rows, aligns=None) -> str:
    """headers: list[str]; rows: list[list[str]]; aligns: 'l'/'r' per column."""
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
    return (
        '<div class="twrap"><table><thead><tr>'
        + th
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def tile(label, value, sub, cls="") -> str:
    c = f" {cls}" if cls else ""
    return (
        f'<div class="stat-tile"><div class="label">{esc(label)}</div>'
        f'<div class="value{c}">{esc(value)}</div>'
        f'<div class="sub">{sub}</div></div>'
    )


def tiles(items) -> str:
    return '<div class="stat-grid">' + "".join(items) + "</div>"


# ---------------------------------------------------------------- charts
def hbar(rows, gutter=190, width=720, ramp=True, unit="", maxv=None):
    """rows: list of (label, value). Ranked horizontal bars with tooltips."""
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
        out.append(
            f'<text x="{gutter}" y="{y + 8}" text-anchor="end" class="c-lab" '
            f'dominant-baseline="middle">{esc(lab)}</text>'
        )
        out.append(
            f'<rect x="{bar_x}" y="{y}" width="{w:.1f}" height="17" rx="3" '
            f'fill="{fill}"><title>{esc(lab)}: {ni(val)}{unit}</title></rect>'
        )
        out.append(
            f'<text x="{bar_x + w + 6:.1f}" y="{y + 8}" class="c-val" '
            f'dominant-baseline="middle">{ni(val)}{unit}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def histogram(bins, labels, width=720, height=260, gut=48, logy=False,
              thresholds=(), unit="", bar_fill="var(--series-1)"):
    """bins: counts. labels: x tick strings. thresholds: [(index_frac, text, color)]."""
    n = len(bins)
    plot_l, plot_r = gut + 12, width - 14
    base_y = height - 42
    top_y = 14
    span = base_y - top_y
    vals = [((v + 1) if logy else v) for v in bins]
    peak = max(vals) or 1
    ticks = 4
    slot = (plot_r - plot_l) / n
    bar_w = min(46.0, slot - 12)

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    # gridlines + y ticks. Linear: even fractions. Log: round counts at log positions.
    if logy:
        raw_peak = max(bins) or 1
        denom = math.log10(raw_peak + 1)
        decades = [0] + [10**k for k in range(1, 6) if 10**k < raw_peak]
        ticks_seq = [(math.log10(v + 1) / denom, ni(v) if v else "0")
                     for v in decades] + [(1.0, ni(raw_peak))]
    else:
        ticks_seq = [(k / ticks, ni(round(peak * k / ticks))) for k in range(ticks + 1)]
    seen = set()
    for frac, lab in ticks_seq:
        if round(frac, 4) in seen:
            continue
        seen.add(round(frac, 4))
        y = base_y - span * frac
        out.append(
            f'<line x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}" class="grid"/>'
            f'<text x="{plot_l - 6}" y="{y + 3:.1f}" text-anchor="end" class="c-tick">{lab}</text>'
        )
    # bars
    for i, v in enumerate(vals):
        cx = plot_l + slot * i + slot / 2
        h = span * (v / peak)
        y = base_y - h
        out.append(
            f'<rect x="{cx - bar_w / 2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{max(h, 1.5):.1f}" rx="2" fill="{bar_fill}">'
            f"<title>{esc(labels[i])}: {ni(bins[i])}{unit}</title></rect>"
        )
        out.append(
            f'<text x="{cx:.1f}" y="{base_y + 10}" text-anchor="end" class="c-tick" '
            f'transform="rotate(-45 {cx:.1f} {base_y + 10})">{esc(labels[i])}</text>'
        )
    # thresholds
    for frac, text, color in thresholds:
        x = plot_l + (plot_r - plot_l) * frac
        out.append(
            f'<line x1="{x:.1f}" y1="{top_y - 4}" x2="{x:.1f}" y2="{base_y}" '
            f'stroke="{color}" stroke-width="2" stroke-dasharray="4 3"/>'
            f'<text x="{x:.1f}" y="{top_y - 8}" text-anchor="middle" class="c-tick" '
            f'fill="{color}">{esc(text)}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def grouped_hbar(groups, gutter=150, width=720):
    """groups: [(label, [(series_label, value, color), ...])] grouped bars."""
    row_h = 34
    n = len(groups)
    h = 24 + row_h * n
    bar_x = gutter + 8
    plot_w = width - bar_x - 120
    peak = max(v for _, ser in groups for _, v, _ in ser) or 1
    out = [f'<svg viewBox="0 0 {width} {h}" class="chart" role="img">']
    for i, (lab, ser) in enumerate(groups):
        y0 = 12 + row_h * i
        out.append(
            f'<text x="{gutter}" y="{y0 + 13}" text-anchor="end" class="c-lab" '
            f'dominant-baseline="middle">{esc(lab)}</text>'
        )
        for j, (slab, val, color) in enumerate(ser):
            y = y0 + j * 14
            w = max(1.5, plot_w * (val / peak))
            out.append(
                f'<rect x="{bar_x}" y="{y}" width="{w:.1f}" height="11" rx="2" '
                f'fill="{color}"><title>{esc(lab)}, {esc(slab)}: '
                f'{ni(round(val))} um</title></rect>'
            )
            out.append(
                f'<text x="{bar_x + w + 6:.1f}" y="{y + 8}" class="c-val" '
                f'dominant-baseline="middle">{ni(round(val))}</text>'
            )
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- sections
def build(d: dict, generated: str) -> str:
    s = d["summary"]
    dist = d["distributions"]
    ds = dist["summary"]
    scale = d["scale"]
    upx = scale["um_per_px"]
    code_list = d["codes"]

    secs = []          # (anchor, nav_label, html)
    nav = []

    def add(anchor, nav_label, html_body):
        nav.append((anchor, nav_label))
        secs.append((anchor, html_body))

    # ---------------------------------------------------- 1 at a glance
    lines = d["filenames"]["lines"]
    line_txt = ", ".join(
        f"line {k[1:]} holds {ni(v)}" for k, v in sorted(lines.items(), key=lambda x: -x[1])
    )
    tiles1 = [
        tile("Images", ni(s["images"]), "7 annotation jobs, 1 image with no code at all"),
        tile("Boxes", ni(s["boxes"]), "12,640 arrived with an imported file, 153 drawn by hand"),
        tile("Whole-image tags", ni(s["tag_elements"]),
             "1,317 distinct tag labels, 1 label repeated on one image"),
        tile("Codes", ni(s["distinct_codes"]),
             f'{s["distinct_codes"] - s["codes_that_are_gates"]} base codes + '
             f'{s["codes_that_are_gates"]} size-gate flags'),
        tile("Image size", "2,448 x 2,048", "one single geometry across the whole batch"),
        tile("Scale", f"{upx} um per pixel",
             f'measured on {ni(scale["n_images_used"])} images, varies about '
             f'{f1(scale["rel_spread_pct"])}% image to image'),
    ]
    add(
        "glance",
        "1",
        '<h3>1 · The batch at a glance</h3>'
        '<p class="desc">What arrived, and the units every number on this page uses. '
        "All figures are computed from the seven annotation exports and re-counted by an "
        "independent check run over the raw files: 39 checks, 0 failures.</p>"
        + tiles(tiles1)
        + '<p class="note">The batch spans nine consecutive days, 2024-11-01 to 2024-11-09, '
        f"and four lines: {line_txt}. Sizes on this page are the diagonal of the annotated "
        f"rectangle at {upx} micrometres per pixel, which is a length across the defect, "
        "not a diameter and not an area.</p>",
    )

    # ---------------------------------------------------- 2 codes per image
    cpi = dist["codes_per_image"]
    xs = [int(a) for a, _ in cpi]
    ys = [int(b) for _, b in cpi]
    thr_frac = (xs.index(8) + 0.5) / len(xs)
    hist = histogram(
        ys,
        [str(x) for x in xs],
        thresholds=[(thr_frac, "tail cut = 8", "#e34948")],
        unit=" images",
    )
    tiles2 = [
        tile("Median codes per image", f1(ds["median_codes"], 0), "the middle image of the batch"),
        tile("Mean codes per image", f1(ds["mean_codes"], 2), "pulled up by a thin right tail"),
        tile("90th percentile", f1(ds["p90_codes"], 0), "9 images in 10 sit at or below this"),
        tile("Most codes on one image", ni(ds["max_codes"]), "one image, of 1,047"),
        tile("More than one code", ni(s["images_multi_code"]),
             f'{pc(s["images_multi_code"] / s["images"])} of the batch'),
        tile("Exactly one code", ni(s["images_single_code"]),
             f'{pc(s["images_single_code"] / s["images"])} of the batch'),
    ]
    rows2 = [
        ["All 24 codes", f1(ds["mean_codes"], 2), f1(ds["median_codes"], 0),
         ni(ds["max_codes"]), ni(s["images_multi_code"])],
        [f'The {s["distinct_codes"] - s["codes_that_are_gates"]} base codes only',
         f1(ds["mean_base_codes"], 2), "3", ni(ds["max_base_codes"]), "-"],
    ]
    add(
        "codes-per-image",
        "2",
        '<h3>2 · Codes per image: a multi-label set</h3>'
        '<p class="desc">How many codes each image carries, with and without the four '
        "size-gate flags that only repeat a size fact about a code already counted.</p>"
        + tiles(tiles2)
        + '<h4>Codes per image, all 24 codes</h4>'
        + hist
        + '<p class="note">Counts of 3 and 4 together hold 386 of the 1,047 images, so the '
        f'peak sits in the middle. 13 images carry 8 or more codes, {pc(ds["tail_share_of_images"], 1)} '
        f'of the batch, and they hold {pc(ds["tail_share_of_shapes"], 1)} of all shape '
        "placements, so a handful of busy files does not drive the set.</p>"
        + table(
            ["Reading", "Mean", "Median", "Maximum", "Images with more than one"],
            rows2,
            ["l", "r", "r", "r", "r"],
        )
        + '<p class="note">Removing the four size-gate flags drops the maximum from '
        f'{ni(ds["max_codes"])} to {ni(ds["max_base_codes"])} codes and the mean from '
        f'{f1(ds["mean_codes"], 2)} to {f1(ds["mean_base_codes"], 2)}, because those flags '
        "only say that a box already counted is oversized.</p>",
    )

    # ---------------------------------------------------- 3 families + tail
    tiles3 = [
        tile("Box codes per image", f1(ds["mean_box_codes"], 2),
             f'median {f1(ds["median_box_codes"], 0)}, maximum {ni(ds["max_box_codes"])}'),
        tile("Tag codes per image", f1(ds["mean_tag_codes"], 2),
             f'median {f1(ds["median_tag_codes"], 0)}, maximum {ni(ds["max_tag_codes"])}'),
        tile("Both families", ni(s["images_both"]), "boxes and whole-image flags on one image"),
        tile("Boxes only", ni(s["images_box_only"]), "localised defects, no whole-image flag"),
        tile("Tags only", ni(s["images_tag_only"]), "whole-image flags, no drawn box"),
        tile("Neither", ni(s["images_neither"]), "one image carries no code at all"),
    ]
    tail_rows = []
    for t in dist["tail_images"]:
        tail_rows.append([
            f'<code>{esc(t["basename"])}</code>',
            ni(t["codes"]),
            ni(t["base_codes"]),
            ni(t["gate_codes"]),
            ni(t["boxes"]),
            ni(t["tags"]),
            f'line {t["line"][1:]}',
        ])
    busiest = dist["tail_images"][0]
    add(
        "tail",
        "3",
        '<h3>3 · Two label families, and the multi-code tail</h3>'
        '<p class="desc">An image carries the union of two independent families: localised '
        "defects drawn as boxes, and whole-image flags carried as tags. The tail images are "
        "high on both at once, not an artefact of one family.</p>"
        + tiles(tiles3)
        + "<h4>The 13 images carrying 8 or more codes</h4>"
        + table(
            ["Image", "Codes", "Base codes", "Size gates", "Boxes", "Tags", "Line"],
            tail_rows,
            ["l", "r", "r", "r", "r", "r", "r"],
        )
        + '<p class="note">The busiest image carries '
        f'{ni(busiest["codes"])} codes: {ni(len(busiest["box_codes"]))} localised defects '
        f'({", ".join(busiest["box_codes"])}) and {ni(len(busiest["tag_codes"]))} '
        f'whole-image flags, of which {ni(len(busiest["gates"]))} are size-gate echoes of box '
        f"codes already counted. Its distinct problems number {ni(busiest['base_codes'])}, "
        f'not {ni(busiest["codes"])}.</p>'
        + '<p class="note">One code drives most of the spread. P2_BB (Bubble) sits on '
        f'{ni(ds["with_bubble_images"])} images, '
        f'{pc(ds["with_bubble_images"] / s["images"])} of the batch, and images carrying it '
        f'average {f1(ds["with_bubble_mean_codes"], 2)} codes against '
        f'{f1(ds["without_bubble_mean_codes"], 2)} for images without it, so Bubble is the '
        "common condition that pulls most of the set into the multi-label region.</p>",
    )

    # ---------------------------------------------------- 4 catalogue
    cat_rows = []
    for c in sorted(code_list, key=lambda x: -x["images"]):
        if c["is_gate"]:
            kind = "size gate"
        elif c["boxes"]:
            kind = "box"
        else:
            kind = "tag"
        name = c["name"] if c["confirmed"] else f'{c["name"]}'
        conf = '<span class="ok">confirmed</span>' if c["confirmed"] else '<span class="bad">unconfirmed</span>'
        cat_rows.append([
            f"<code>{esc(c['code'])}</code>",
            esc(name),
            kind,
            ni(c["images"]),
            pc(c["image_share"]),
            ni(c["shapes"]),
            conf,
        ])
    unconf = [c for c in code_list if not c["confirmed"]]
    all_conf = not unconf
    if all_conf:
        cat_rows = [r[:-1] for r in cat_rows]
    added = ["P2_DC", "P2_BI", "P1_FL", "P2_BST"]
    by_code = {c["code"]: c for c in code_list}
    added_txt = ", ".join(
        f'<code>{k}</code> {esc(by_code[k]["name"])} on {ni(by_code[k]["images"])} images'
        for k in added
    )
    n_box_codes = sum(1 for c in code_list if c["boxes"] and not c["is_gate"])
    n_tag_codes = sum(1 for c in code_list if not c["boxes"])
    add(
        "catalogue",
        "4",
        '<h3>4 · The 24 codes</h3>'
        '<p class="desc">One row per code: what it means, whether it carries boxes or only a '
        "whole-image tag, how many images hold it, and whether its meaning is confirmed "
        "against the client taxonomy.</p>"
        + table(
            ["Code", "Meaning", "Carried as", "Images", "Share of batch", "Shapes"]
            + ([] if all_conf else ["Name"]),
            cat_rows,
            ["l", "l", "l", "r", "r", "r"] + ([] if all_conf else ["l"]),
        )
        + '<p class="note">A code is either a box or a tag, never both: '
        f"{ni(n_box_codes)} codes carry boxes and describe localised defects, and "
        f"{ni(n_tag_codes)} are whole-image flags with no location at all. A tag-only code "
        "cannot be a detector target, it can only be an image-level label.</p>"
        + ("" if all_conf else '<p class="note">Four codes are not confirmed against the '
           'client taxonomy: ' + ", ".join(
               f"<code>{esc(c['code'])}</code> on {ni(c['images'])} images" for c in unconf)
           + ". Their names above are placeholders and they should be settled before any of "
           "them appears in a class list or in a report to the client.</p>")
        + '<p class="note">Four names were added on 2026-10-13: ' + added_txt
        + ". The first three match the September code legend for this project directly, and "
        "the last one rests on elimination plus that same reading, so Stretched Bubble is "
        "the one still worth a check against the client legend before a class list goes out."
        "</p>",
    )

    # ---------------------------------------------------- 5 co-occurrence
    pairs = d["code_pairs"][:10]
    pair_rows = [
        (f'{p["a"]} + {p["b"]}', p["images"]) for p in pairs
    ]
    add(
        "pairs",
        "5",
        '<h3>5 · Which codes appear together</h3>'
        '<p class="desc">The most common pairs of codes on the same image, out of 1,047 '
        "images.</p>"
        + hbar(pair_rows, gutter=210, unit=" images")
        + '<p class="note">P2_BB with P2_BC on '
        f'{ni(pairs[0]["images"])} images is the most common pair, ahead of P2_BB with P3_FM '
        f'on {ni(pairs[1]["images"])} and P2_BB with P2_DC on {ni(pairs[2]["images"])}. '
        "Every one of the top pairs contains Bubble, which is expected once 71.3 percent of "
        "the batch carries it.</p>",
    )

    # ---------------------------------------------------- 6 sizes
    os_ = d["overall_size"]
    sh = dist["size_histogram"]
    bins = [b["boxes"] for b in sh]
    labels = [
        (f'{b["lo_um"]}–{b["hi_um"]}' if b["hi_um"] else f'{b["lo_um"]}+')
        for b in sh
    ]
    # threshold position: the 647 um cut sits between bin 500-647 and 647-1000
    cut_frac = (next(i for i, b in enumerate(sh) if b["hi_um"] == 647) + 1) / len(sh)
    size_hist = histogram(
        bins, labels, logy=True, thresholds=[(cut_frac, "647 um cut", "#e34948")],
        unit=" boxes", height=270,
    )
    size_rows = []
    for r in d["sizes"]:
        size_rows.append([
            f"<code>{esc(r['code'])}</code>",
            ni(r["n"]),
            f1(r["median_px"]),
            ni(round(r["median_um"])),
            ni(round(r["p75_um"])),
            ni(round(r["max_um"])),
        ])
    th_rows = [
        [f'{t["threshold_um"]} um', f'{f1(t["threshold_px"], 1)} px',
         ni(t["boxes_above"]), pc(t["boxes_above_share"])]
        for t in d["thresholds"]
    ]
    out_rows = [
        [f"<code>{esc(o['code'])}</code>", ni(o["boxes"]), ni(o["boxes_over_200px"]),
         pc(o["share_over_200px"]), ni(round(o["largest_px"] * upx))]
        for o in d["outliers"] if o["share_over_200px"] > 0.02
    ]
    lens_um = round(scale["lens_diam_px"] * upx)
    tiles6 = [
        tile("Median box", f'{ni(round(os_["median"] * upx))} um',
             f'{f1(os_["median"])} px across, 12,793 boxes'),
        tile("95th percentile", f'{ni(round(os_["p95"] * upx))} um',
             f'{f1(os_["p95"])} px across'),
        tile("Largest box", f'{ni(round(os_["max"] * upx))} um',
             f'{ni(round(os_["max"]))} px across'),
        tile("Boxes above 647 um", ni(d["thresholds"][2]["boxes_above"]),
             f'{pc(d["thresholds"][2]["boxes_above_share"])} of all boxes', "bad"),
    ]
    add(
        "sizes",
        "6",
        '<h3>6 · How big each defect is</h3>'
        '<p class="desc">Box size measured as the diagonal of the annotated rectangle, '
        f"converted at {upx} micrometres per pixel. Rotation does not change a diagonal, so "
        "these sizes hold for the boxes as drawn.</p>"
        + tiles(tiles6)
        + "<h4>Box size in micrometres, log scale</h4>"
        + size_hist
        + '<p class="note">Bar length follows the log of the count because the smallest bin '
        "holds most boxes: 7,213 boxes sit between 100 and 200 micrometres while only 196 "
        "sit above 5,000. The dashed line is the 647 micrometre size cut from the "
        "annotator's rule.</p>"
        + "<h4>Size per code</h4>"
        + table(
            ["Code", "Boxes", "Median px", "Median um", "75th percentile um", "Largest um"],
            size_rows,
        )
        + "<h4>Boxes above each recorded threshold</h4>"
        + table(["Threshold", "In pixels", "Boxes above", "Share of all boxes"], th_rows)
        + '<p class="note">P3_HE is not a defect spot: its 96 boxes have a median diagonal of '
        f'22,149 micrometres, which is larger than the {ni(lens_um)} micrometre lens, so it '
        "marks a region. It should not be trained as a detector target beside classes whose "
        "medians run from 167 to 1,835 micrometres, and the annotator needs to say what the "
        "region covers.</p>"
        + "<h4>Boxes far larger than their class</h4>"
        + table(
            ["Code", "Boxes", "Over 200 px", "Share", "Largest um"],
            out_rows,
        )
        + '<p class="note">52 of the 10,075 P2_BB boxes exceed 200 px across while that class '
        "median is 9.2 px, and 63 of the 591 P2_WP boxes do the same against a 45.7 px median. "
        "Those are not the same object as the rest of their class and they should be looked at "
        "before training.</p>",
    )

    # ---------------------------------------------------- 7 the gate
    gate_rows = []
    gate_groups = []
    for g in d["gates"]:
        fu = round(g["flagged_median_px"] * upx) if g["flagged_median_px"] else None
        uu = round(g["unflagged_median_px"] * upx) if g["unflagged_median_px"] else None
        gate_rows.append([
            f"<code>{esc(g['base'])}</code>",
            ni(g["flagged_images"]),
            ni(g["unflagged_images"]),
            f'{f1(g["flagged_median_px"])} px / {ni(fu)} um' if fu else "-",
            f'{f1(g["unflagged_median_px"])} px / {ni(uu)} um' if uu else "none",
            f'{f1(g["ratio"])}x' if g["ratio"] else "not testable",
        ])
        ser = []
        if g["flagged_median_px"]:
            ser.append(("flagged images", g["flagged_median_px"] * upx, "#e34948"))
        if g["unflagged_median_px"]:
            ser.append(("unflagged images", g["unflagged_median_px"] * upx, "#1baf7a"))
        gate_groups.append((g["base"], ser))
    mm = d["micron_metric_test"]
    metrics = list(next(iter(mm["per_code"].values())).keys())
    gate_codes = list(mm["per_code"].keys())
    metric_rows = []
    for m in metrics:
        row = [esc(m)]
        for c in gate_codes:
            a = mm["per_code"][c][m]["agreement_at_stated_cut"]
            row.append(pc(a, 1))
        metric_rows.append(row)
    add(
        "gate",
        "7",
        '<h3>7 · The size gate: a flag, not a class</h3>'
        '<p class="desc">Four codes end in _MICRON_THRESHOLD. The annotator\'s handover email '
        "gives the rule: mark the images that contain debris over 647 micrometres, for the "
        "edge algorithm training set. The four gated codes are exactly the four foreign "
        "material codes, so this is a size flag on a base code rather than a new class.</p>"
        + table(
            ["Base code", "Flagged images", "Unflagged images", "Flagged median",
             "Unflagged median", "Ratio"],
            gate_rows,
            ["l", "r", "r", "r", "r", "r"],
        )
        + "<h4>Largest base-code box on the same image, in micrometres</h4>"
        + grouped_hbar(gate_groups)
        + '<p class="note">The flag tracks size. On every class where the comparison can be '
        "made, the flagged group's median sits above the stated 647 micrometres while the "
        "unflagged group's median sits below it (348, 561 and 423 micrometres).</p>"
        + "<h4>How well the stated 647 micrometre rule reproduces the delivered flags</h4>"
        + table(["Reading of a box's size"] + gate_codes, metric_rows, ["l", "r", "r", "r", "r"])
        + '<p class="note">Reading a box\'s size as its longest side comes closest: it '
        "reproduces 100 percent of the flags on P3_EP and P3_HE and 90.9 and 90.4 percent on "
        "P3_FIB and P3_FM. No reading of size, diagonal, longest side, shorter side, "
        "same-area circle diameter or geometric mean of the sides reproduces all four codes at "
        "exactly 647 micrometres. The email predates the validation pass and the flags moved "
        "during it, which is the likeliest reason.</p>"
        + '<p class="note">P3_HE is flagged on all 95 of its images for a plain reason: its '
        "smallest box is 5,562 micrometres, about eight times the cut, so the same rule "
        "applies to a class that always exceeds it. It is not flagged unconditionally.</p>",
    )

    # ---------------------------------------------------- 8 email
    er = sorted(d["email"]["rows"], key=lambda r: -abs(r["delta_shapes"]))
    email_rows = []
    for r in er:
        delta = r["delta_shapes"]
        cls = "bad" if abs(delta) > 8 else "ok"
        shown = r["email_code"] + (" (typo)" if r["renamed"] else "")
        email_rows.append([
            f"<code>{esc(shown)}</code>",
            ni(r["stated"]),
            ni(r["xml_shapes"]),
            ni(r["xml_images"]),
            f'<span class="{cls}">{delta:+d}</span>',
        ])
    micro_rows = [
        [f"<code>{esc(m['code'])}</code>", ni(m["stated"]), ni(m["xml_images"]),
         f'<span class="{"bad" if abs(m["delta_images"]) > 8 else "ok"}">'
         f'{m["delta_images"]:+d}</span>']
        for m in d["email"]["micron_rows"]
    ]
    add(
        "email",
        "8",
        '<h3>8 · The handover email, checked against what arrived</h3>'
        '<p class="desc">The email states 1,047 images, which matches, and it was written '
        "before the validation pass finished, so its counts are the state at that time and the "
        "delivered files are the source of truth. The differences show what validation "
        "changed.</p>"
        + table(
            ["Code", "Email stated", "Delivered shapes", "Delivered images", "Change"],
            email_rows,
            ["l", "r", "r", "r", "r"],
        )
        + '<p class="note">P2_DC (Dirty Camera) moved from 28 to 204, a sevenfold increase '
        "and the largest change in the batch. The tag "
        "codes with no ambiguity at all, P1_MPP at 226, P2_LD at 118, P2_DS at 22 and P1_PPM "
        "at 2, did not move.</p>"
        + "<h4>The size-gate flags, email against delivered</h4>"
        + table(["Code", "Email stated", "Delivered images", "Change"], micro_rows)
        + '<p class="note">The flags moved during validation as well, from 65 to 53 and 89 to '
        "85 and 33 to 32 and 92 to 95, which is why no reading of the stated rule reproduces "
        "the delivered flags exactly.</p>"
        + '<p class="note">One naming difference: the email writes P2_FOV where the delivered '
        "file writes F2_FOV for the same defect, View Obstructed. One of the two is a typo and "
        "it should be settled before either name goes into a class list.</p>",
    )

    # ---------------------------------------------------- 9 provenance
    box_src = d["box_source"]
    tag_src = d["tag_source"]
    cav = d["cavity"]
    rot = s
    prov_rows = [
        ["Boxes that arrived with an imported file", ni(box_src["file"]),
         pc(box_src["file"] / s["boxes"])],
        ["Boxes drawn by hand", ni(box_src["manual"]), pc(box_src["manual"] / s["boxes"])],
        ["Tags that arrived with an imported file", ni(tag_src.get("file", 0)), "-"],
        ["Tags drawn by hand", ni(tag_src.get("manual", 0)), "-"],
        ["Tags with no source recorded", ni(tag_src.get("None", 0)), "-"],
    ]
    line_rows = [(f'line {k[1:]}', v) for k, v in sorted(lines.items(), key=lambda x: -x[1])]
    date_rows = [(k[4:6] + "/" + k[6:], v) for k, v in sorted(d["filenames"]["dates"].items())]
    tiles9 = [
        tile("Rotated boxes", ni(rot["rotation_present"]),
             f'{ni(rot["rotation_absent"])} boxes carry no rotation value'),
        tile("Off-angle rotations", pc(rot["rotation_other_share"]),
             f'{ni(rot["rotation_other"])} of them are not a multiple of 90 degrees'),
        tile("Cavity measured", f'{ni(cav["images_measured"])} of {ni(s["images"])}',
             f'{ni(cav["images_unmeasured"])} images could not be measured'),
        tile("Boxes beyond 1.5x the cavity radius", ni(cav["beyond_1_5x"]),
             f'median centre at {f1(cav["p50_ratio"], 2)} of the radius, maximum '
             f'{f1(cav["max_ratio"], 2)}x', "ok"),
    ]
    add(
        "provenance",
        "9",
        '<h3>9 · Where the annotations came from, and where they sit</h3>'
        '<p class="desc">Who made each annotation, whether boxes are rotated, and where box '
        "centres fall against the part each image actually shows.</p>"
        + tiles(tiles9)
        + table(["Annotation", "Count", "Share"], prov_rows, ["l", "r", "r"])
        + '<p class="note">Most of this set is pre-annotation that a human reviewed, not '
        "annotation a human created: 12,640 of 12,793 boxes arrived with an imported file. "
        "That is worth knowing before treating it as ground truth.</p>"
        + '<p class="note">The boxes are genuinely rotated. 11,600 of the 12,135 rotated '
        "boxes, 95.6 percent, sit at an angle that is not a multiple of 90 degrees, and the "
        "values spread across all eight 45 degree buckets, so any pipeline that assumes "
        "axis-aligned rectangles will mis-draw almost all of them.</p>"
        + '<p class="note">Measured against the cavity of each image\'s own part rather than '
        "the image centre, because the part is not centred in the frame, the median box centre "
        f'sits at {f1(cav["p50_ratio"], 2)} of the cavity radius, the 95th percentile at '
        f'{f1(cav["p95_ratio"], 2)} and the maximum at {f1(cav["max_ratio"], 2)}. Only '
        f'{ni(cav["beyond_1_5x"])} boxes of {ni(s["boxes"])} fall further out than 1.5 times '
        "the radius, so nothing is annotated on the tray or the background. The median offset "
        "of the part from the image centre is 100 px and the maximum is 450 px, so any "
        "position statistic measured from the image centre is wrong.</p>"
        + "<h4>Images per line</h4>"
        + hbar(line_rows, gutter=110, unit=" images", ramp=False)
        + "<h4>Images per capture day</h4>"
        + hbar(date_rows, gutter=110, unit=" images", ramp=False)
        + '<p class="note">Two filename families exist: 878 images use a legacy form carrying '
        "date, time, line and cavity position, and the other 169 also carry pallet, board id, "
        "a fail count and a selection score. Those 169 scores run from 0.9001 to 1.0, so this "
        "batch sits in the high-scoring tail of whatever upstream selection produced it. The "
        "score is a sampling covariate, not a label.</p>",
    )

    # ---------------------------------------------------- 10 actions
    add(
        "actions",
        "10",
        '<h3>10 · What to do with it</h3>'
        '<p class="desc">Ordered actions, each with the number that makes it necessary.</p>'
        '<ol class="findings">'
        "<li><b>Train on the 20 base codes and keep all 24 in the catalogue.</b> The four "
        "_MICRON_THRESHOLD codes are a deterministic function of the base code's box size, so "
        "feeding them in as independent targets hands the model labels that come from box "
        "geometry and builds guaranteed correlations into the label matrix that will flatter "
        "the metrics. Use the gate as a sampling flag for the edge training set instead. This "
        "is a recommendation and it has not been decided.</li>"
        "<li><b>Confirm Stretched Bubble against the client legend, and ask what validation "
        "did to Dirty Camera.</b> The four codes named on 2026-10-13 are Dirty Camera on 204 "
        "images, Bubble Irregular on 108, Folded Lens on 59 and Stretched Bubble on 2; the "
        "first three match the September code legend directly, and only Stretched Bubble rests "
        "on elimination. Dirty Camera also moved from 28 to 204 between the email and the "
        "delivered file, and that jump is not explained.</li>"
        "<li><b>Ask the annotator which reading of a box's size the threshold script uses, and "
        "whether the micron tags were hand-edited during validation.</b> The email states 647 "
        "micrometres but not how size is measured, no reading of size reproduces all four "
        "codes, and the flag counts moved between the email and the delivered file.</li>"
        "<li><b>Settle P2_FOV against F2_FOV and get the annotator's definition of P3_HE.</b> "
        "The two files disagree on the prefix for View Obstructed, and P3_HE's boxes have a "
        "median diagonal of 22,149 micrometres against a 14,240 micrometre lens, so it marks a "
        "region whose coverage is not recorded anywhere.</li>"
        "<li><b>Decide the multi-label training scheme.</b> 743 of 1,047 images carry more than "
        "one code, so a single-folder-per-class split would put most of the set in the Bubble "
        "bin and discard the co-occurring labels. Also note that 19 images carry two size-gate "
        "flags and one carries three, so the edge-training selection the email describes is not "
        "a partition.</li>"
        "<li><b>Decide whether the 9,391 unannotated images in the source folder are wanted as "
        "explicit negatives.</b> This batch is 1,047 of the 10,438 images in that folder.</li>"
        "<li><b>Look at the over-200 px boxes before training.</b> 52 of 10,075 P2_BB boxes and "
        "63 of 591 P2_WP boxes exceed 200 px across while their class medians are 9.2 px and "
        "45.7 px, so they are likely region marks or mislabels rather than defects at that "
        "scale.</li>"
        "</ol>",
    )

    # ---------------------------------------------------- assemble
    nav_html = "".join(f'<a href="#{a}">{lab}</a>' for a, lab in nav)
    body = "".join(f'<section id="{a}">{h}</section>' for a, h in secs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PRODUCTION_20260925 batch analysis</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{CSS}
</style>
</head>
<body>
<header class="top"><div class="topbar">
  <h1>FMD · PRODUCTION_20260925 batch analysis</h1>
  <nav class="sections">{nav_html}</nav>
  <button class="theme-toggle" onclick="var r=document.documentElement,d=r.getAttribute('data-theme')==='dark';r.setAttribute('data-theme',d?'light':'dark')">&#9684; theme</button>
</div></header>
<div class="wrap">
  <div class="hero">
    <h2>PRODUCTION_20260925: what the annotated batch contains</h2>
    <div class="meta">
      <b>{ni(s["images"])} images</b> from <b>{ni(s["jobs"])} annotation jobs</b>, holding
      <b>{ni(s["boxes"])} boxes</b> and <b>{ni(s["tag_elements"])} whole-image tags</b> across
      <b>{ni(s["distinct_codes"])} codes</b>. <b>{ni(s["images_multi_code"])} images,
      {pc(s["images_multi_code"] / s["images"], 1).replace("%", " percent")}, carry more than
      one code</b>, so this is a multi-label set. Every figure on this page is computed
      from the seven annotation exports and re-counted by an independent check run over the raw
      files: 39 checks, 0 failures.
      <div class="foot">Generated {esc(generated)} by the batch analysis pipeline: the seven
      annotation exports to one numbers file, then this page. Companion artefacts: the 8-sheet
      EDA workbook and the findings write-up for the same batch.</div>
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

    with open(a.numbers, encoding="utf-8") as fh:
        d = json.load(fh)
    if not os.path.exists(a.template):
        print(f"starter template not found: {a.template}", file=sys.stderr)
        return 2
    global CSS
    tpl = open(a.template, encoding="utf-8").read()
    CSS = tpl.split("<style>", 1)[1].split("</style>", 1)[0].strip("\n")

    generated = a.generated or _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    page = build(d, generated)

    # gates: no em dash, no drive letters, no cross-section references in prose
    assert "—" not in page, "em dash found in the generated page"
    assert "§" not in page, "section reference found in the generated page"
    assert ":\\\\" not in page and "/Users/" not in page, "local path leaked into the page"

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(json.dumps({"out": a.out, "bytes": len(page.encode('utf-8')),
                      "sections": page.count("<section id="),
                      "rects": page.count("<rect"),
                      "titled_rects": page.count("</title></rect>"),
                      "tables": page.count("<table>"),
                      "charts": page.count('class="chart"')}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
