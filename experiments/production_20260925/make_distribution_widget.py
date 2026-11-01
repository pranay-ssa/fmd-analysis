#!/usr/bin/env python3
"""Render the distribution charts as a self-contained HTML widget.

Reads batch_numbers.json and writes one HTML file. No external assets, no
JavaScript libraries: the bars are laid out with CSS and the numbers are baked
in, so the file renders anywhere.

The point of the widget is the multi-code tail, so it leads with the answer
rather than the chart: which image reaches the maximum, what its codes are, and
how many of them are derived size-gate flags rather than distinct defects.

Usage:
  python make_distribution_widget.py --numbers batch_numbers.json --out widget.html
"""
from __future__ import annotations

import argparse
import html
import json
import os


def esc(s):
    return html.escape(str(s))


def bar_row(label, value, vmax, width, fmt="%d", right=None, second=None):
    """One labelled bar. second adds a second series drawn under the first."""
    pct = (100.0 * value / vmax) if vmax else 0.0
    out = ['<div class="r">']
    out.append('<div class="lab">%s</div>' % esc(label))
    out.append('<div class="track">')
    out.append('<div class="bar" style="width:%.2f%%"></div>' % pct)
    if second is not None:
        spct = (100.0 * second / vmax) if vmax else 0.0
        out.append('<div class="bar2" style="width:%.2f%%"></div>' % spct)
    out.append("</div>")
    out.append('<div class="val">%s</div>' % esc(fmt % value))
    out.append("</div>")
    return "".join(out)


def build(R):
    D = R["distributions"]
    s = D["summary"]
    S = R["summary"]
    n_img = S["images"]
    n_boxes = S["boxes"]
    tail = D["tail_images"]
    top = R["codes"][:12]

    h = []
    A = h.append

    A('<div class="wrap">')
    A('<div class="h1">Codes per image</div>')
    A('<div class="sub">%d images, %d boxes and %s tags. A code counts once per image even '
      'when it appears on several shapes.</div>'
      % (n_img, n_boxes, format(S["tag_elements"], ",")))

    # stat strip
    A('<div class="stats">')
    for lab, val in [
        ("median", "%g" % s["median_codes"]),
        ("mean", "%.2f" % s["mean_codes"]),
        ("90th pct", "%g" % s["p90_codes"]),
        ("95th pct", "%g" % s["p95_codes"]),
        ("maximum", "%d" % s["max_codes"]),
        ("max excl. size flags", "%d" % s["max_base_codes"]),
    ]:
        A('<div class="chip"><div class="cv">%s</div><div class="cl">%s</div></div>' % (esc(val), esc(lab)))
    A("</div>")

    # ---- chart 1
    vmax = max(n for _, n in D["codes_per_image"])
    A('<div class="sec">Images by number of codes</div>')
    A('<div class="chart">')
    for k, n in D["codes_per_image"]:
        A(bar_row("%d" % k, n, vmax, 100))
    A("</div>")
    A('<div class="cap">The shape is a spike at one code and a shoulder out to four, then a short '
      'tail. %d of %d images sit at three or four codes.</div>'
      % (dict(D["codes_per_image"]).get(3, 0) + dict(D["codes_per_image"]).get(4, 0), n_img))

    # ---- chart 2
    bmax = max(n for _, n in D["base_codes_per_image"])
    A('<div class="sec">Same count, with the four derived size-gate flags removed</div>')
    A('<div class="chart">')
    for k, n in D["base_codes_per_image"]:
        A(bar_row("%d" % k, n, bmax, 100))
    A("</div>")
    A('<div class="cap">A size flag such as <code>P3_EP_MICRON_THRESHOLD</code> is derived from a '
      'box code already counted, so it inflates the label count without adding a distinct defect. '
      'Dropping the four flags moves the maximum from %d to %d and the mean from %.2f to %.2f.'
      % (s["max_codes"], s["max_base_codes"], s["mean_codes"], s["mean_base_codes"]))

    # ---- chart 3, two series
    bmap = dict(D["box_codes_per_image"])
    tmap = dict(D["tag_codes_per_image"])
    kmax = max(max(bmap), max(tmap))
    vmax3 = max(max(bmap.values()), max(tmap.values()))
    A('<div class="sec">The two code families, which is why the tail has two components</div>')
    A('<div class="legend">'
      '<span class="k1"></span>box codes, localised defects'
      '<span class="k2"></span>tag codes, whole-image flags'
      '</div>')
    A('<div class="chart">')
    for k in range(0, kmax + 1):
        b = bmap.get(k, 0)
        t = tmap.get(k, 0)
        A('<div class="r two">')
        A('<div class="lab">%d</div>' % k)
        A('<div class="track">'
          '<div class="bar" style="width:%.2f%%"></div>'
          '<div class="bar2" style="width:%.2f%%"></div>'
          '</div>' % (100.0 * b / vmax3 if vmax3 else 0,
                      100.0 * t / vmax3 if vmax3 else 0))
        A('<div class="val">%s / %s</div>' % (b, t))
        A("</div>")
    A("</div>")
    A('<div class="cap">Reading the pair as box codes then tag codes. An image&rsquo;s code count is '
      'these two added together, and the mean image has %.2f box codes and %.2f tag codes. The %d '
      'tail images average %.1f and %.1f, so they are high on both at once.</div>'
      % (s["mean_box_codes"], s["mean_tag_codes"], s["tail_images"],
         sum(len(t["box_codes"]) for t in tail) / len(tail),
         sum(len(t["tag_codes"]) for t in tail) / len(tail)))

    # ---- chart 4
    vmax4 = max(c["images"] for c in top)
    A('<div class="sec">Images carrying each code, top %d</div>' % len(top))
    A('<div class="chart">')
    for c in top:
        A(bar_row(c["code"], c["images"], vmax4, 100))
    A("</div>")
    A('<div class="cap"><code>%s</code> alone is on %.1f%% of the batch. Images carrying it average '
      '%.2f codes; images without it average %.2f. One ubiquitous code is most of the spread.</div>'
      % (esc(R["codes"][0]["code"]), 100 * R["codes"][0]["image_share"],
         s["with_bubble_mean_codes"], s["without_bubble_mean_codes"]))

    # ---- size histogram
    A('<div class="sec">Box size across the whole batch, diagonal in micrometres</div>')
    hmax = max(b["boxes"] for b in D["size_histogram"])
    A('<div class="chart">')
    for b in D["size_histogram"]:
        if b["lo_um"] == 0:
            lab = "&lt;%d" % b["hi_um"]
        elif b["hi_um"] is None:
            lab = "%d+" % b["lo_um"]
        else:
            lab = "%d&ndash;%d" % (b["lo_um"], b["hi_um"])
        A(bar_row(lab, b["boxes"], hmax, 100))
    A("</div>")
    A('<div class="cap">Concentrated in the 100 to 200 micrometre band, with a long tail. The '
      '647 micrometre cut the annotator&rsquo;s script uses sits in the %d to %d bucket, which '
      'holds %s boxes.</div>'
      % (500, 647,
         format([b for b in D["size_histogram"] if b["lo_um"] == 500][0]["boxes"], ",")))

    # ---- the answer
    f = tail[0]
    A('<div class="sec">The image with %d codes</div>' % f["codes"])
    A('<div class="answer">')
    A('<div class="fname">%s</div>' % esc(f["basename"]))
    A('<div class="sub2">%d boxes and %d tags on one image, %s, %s</div>'
      % (f["boxes"], f["tags"], esc(f["line"]), esc(f["basename"].split("_")[0])))
    A('<div class="split">')
    A('<div class="col"><div class="ct">Localised defects, %d</div>' % len(f["box_codes"]))
    for c in f["box_codes"]:
        A('<div class="cl2">%s</div>' % esc(c))
    A("</div>")
    A('<div class="col"><div class="ct">Whole-image flags, %d</div>' % len(f["tag_codes"]))
    for c in f["tag_codes"]:
        mark = ' <span class="der">derived</span>' if c.endswith("_MICRON_THRESHOLD") else ""
        A('<div class="cl2">%s%s</div>' % (esc(c), mark))
    A("</div>")
    A("</div>")
    A('<div class="cap">Of the %d codes, %d are size-gate flags echoing a box code already '
      'counted, so the distinct problems number %d: %d localised defects and %d whole-image '
      'flags.</div>'
      % (f["codes"], f["gate_codes"], f["base_codes"], len(f["box_codes"]),
         len(f["tag_codes"]) - f["gate_codes"]))
    A("</div>")

    # ---- tail table
    A('<div class="sec">Every image with %d or more codes, %d of %d</div>'
      % (s["tail_cut"], len(tail), n_img))
    A('<table><thead><tr><th>File</th><th class="n">Codes</th><th class="n">Base</th>'
      '<th class="n">Derived</th><th>Codes carried</th></tr></thead><tbody>')
    for t in tail:
        A('<tr><td class="mono">%s</td><td class="n">%d</td><td class="n">%d</td>'
          '<td class="n">%d</td><td class="mono small">%s</td></tr>'
          % (esc(t["basename"]), t["codes"], t["base_codes"], t["gate_codes"],
             esc(", ".join(t["box_codes"] + t["tag_codes"]))))
    A("</tbody></table>")
    A('<div class="cap">%d images, %.1f%% of the batch, hold %.1f%% of all shape placements, so the '
      'tail is not driving the set.</div>'
      % (s["tail_images"], 100 * s["tail_share_of_images"], 100 * s["tail_share_of_shapes"]))

    A('<div class="foot">'
      '<button class="btn" data-hermes-send="Draft the Teams reply to Bryce asking which size '
      'metric the 647-micron threshold script uses, whether the micron tags were hand-edited '
      'during validation, and what P3_HE should cover.">'
      'Draft the Teams reply to Bryce</button>'
      '<span class="hint">Numbers recomputed from the annotation files by batch_numbers.py.</span>'
      '</div>')
    A("</div>")

    css = """
.wrap{width:880px;text-align:left;color:var(--foreground)}
.h1{font-size:16px;font-weight:700;margin:0 0 2px}
.sub{font-size:12px;color:var(--muted-foreground);margin:0 0 12px}
.sub2{font-size:11px;color:var(--muted-foreground);margin:0 0 8px}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px}
.chip{border:1px solid var(--border);border-radius:6px;padding:6px 10px;min-width:74px}
.cv{font-size:15px;font-weight:700;line-height:1.1}
.cl{font-size:10px;color:var(--muted-foreground)}
.sec{font-size:12px;font-weight:700;margin:16px 0 6px}
.chart{display:block}
.r{display:grid;grid-template-columns:70px 1fr 64px;align-items:center;gap:8px;margin:2px 0}
.lab{font-size:11px;color:var(--muted-foreground);text-align:right}
.track{height:14px;position:relative;border-left:1px solid var(--border)}
.bar{height:14px;background:var(--accent);border-radius:0 2px 2px 0;position:absolute;top:0;left:0}
.bar2{height:6px;background:var(--muted-foreground);opacity:.55;border-radius:0 2px 2px 0;position:absolute;top:15px;left:0}
.r.two .track{height:22px}
.val{font-size:11px;color:var(--muted-foreground);font-variant-numeric:tabular-nums}
.cap{font-size:11px;color:var(--muted-foreground);margin:6px 0 0;line-height:1.45}
code{font-size:11px;border:1px solid var(--border);border-radius:3px;padding:0 3px}
.legend{font-size:11px;color:var(--muted-foreground);margin:0 0 6px;display:flex;align-items:center;gap:6px}
.k1{width:18px;height:8px;background:var(--accent);display:inline-block}
.k2{width:18px;height:6px;background:var(--muted-foreground);opacity:.55;display:inline-block;margin-left:10px}
.answer{border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin:6px 0 0}
.fname{font-size:12px;font-weight:700;font-family:ui-monospace,Menlo,Consolas,monospace}
.split{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:8px 0 0}
.ct{font-size:11px;font-weight:700;margin:0 0 4px}
.cl2{font-size:11px;font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--muted-foreground);line-height:1.5}
.der{font-family:inherit;font-size:9px;border:1px solid var(--border);border-radius:3px;padding:0 3px}
table{border-collapse:collapse;width:100%;margin:6px 0 0}
th{font-size:10px;text-align:left;color:var(--muted-foreground);border-bottom:1px solid var(--border);padding:3px 6px;font-weight:700}
td{font-size:11px;border-bottom:1px solid var(--border);padding:3px 6px;vertical-align:top}
th.n,td.n{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
.small{font-size:10px;color:var(--muted-foreground)}
.foot{margin:14px 0 0;display:flex;align-items:center;gap:10px}
.btn{border:1px solid var(--border);background:transparent;color:var(--foreground);font:inherit;
     font-size:11px;border-radius:6px;padding:5px 10px;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.hint{font-size:10px;color:var(--muted-foreground)}
"""
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<style>%s</style></head><body>%s</body></html>" % (css, "".join(h)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--numbers", default="batch_numbers.json")
    ap.add_argument("--out", default="distributions_widget.html")
    a = ap.parse_args()
    R = json.load(open(a.numbers, encoding="utf-8"))
    if "distributions" not in R:
        raise SystemExit("batch_numbers.json has no distributions block; re-run batch_numbers.py")
    out = build(R)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("wrote %s (%d bytes)" % (os.path.abspath(a.out), len(out)))


if __name__ == "__main__":
    main()
