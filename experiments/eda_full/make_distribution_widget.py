#!/usr/bin/env python3
"""Render the distributions as a self-contained HTML widget.

Generalised from experiments/production_20260925/make_distribution_widget.py.
Reads full_numbers.json and writes one HTML file. No external assets, no
JavaScript libraries, no network references of any kind: the bars are laid out
with CSS and the numbers are baked in, so the file renders anywhere offline.

Usage:
  python make_distribution_widget.py --numbers full_numbers.json --out distributions_widget.html
"""
from __future__ import annotations

import argparse
import html
import json
import os


def esc(s):
    return html.escape(str(s))


def bar_row(label, value, vmax, second=None, fmt="%d"):
    pct = (100.0 * value / vmax) if vmax else 0.0
    out = ['<div class="r two">' if second is not None else '<div class="r">']
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
    C, L, G = R["census"], R["labels"], R["box_geometry"]
    cpi = {int(k): v for k, v in L["box_codes_per_image"].items()}
    h = []
    A = h.append

    A('<div class="wrap">')
    A('<div class="h1">Distributions of the full-coverage label set</div>')
    A('<div class="sub">%s distinct pictures across the three library folders, %s shapes '
      '(%s boxes and %s tags) across %d canonical defects.</div>'
      % (format(C["distinct_pictures"], ","), format(L["shapes_total"], ","),
         format(L["boxes"], ","), format(L["tags"], ","), L["canonical_count"]))

    A('<div class="stats">')
    for lab, val in [
        ("pictures", format(C["distinct_pictures"], ",")),
        ("with a shape", format(L["with_shape"], ",")),
        ("no shape", format(L["no_shape"], ",")),
        ("mentioned nowhere", format(L["nowhere"], ",")),
        ("median codes", "%g" % L["median_codes"]),
        ("mean codes", "%.2f" % L["mean_codes"]),
        ("maximum codes", "%d" % L["max_codes"]),
        ("axis-aligned", "%.1f%%" % (100 * G["share_axis_aligned"])),
    ]:
        A('<div class="chip"><div class="cv">%s</div><div class="cl">%s</div></div>'
          % (esc(val), esc(lab)))
    A("</div>")

    # chart 1: codes per picture
    vmax = max(cpi.values())
    A('<div class="sec">Pictures by number of codes</div>')
    A('<div class="chart">')
    for k in sorted(cpi):
        A(bar_row("%d" % k, cpi[k], vmax))
    A("</div>")
    A('<div class="cap">A code counts once per picture even when it appears on several '
      'shapes. The median picture carries %g code and the busiest carries %d, so the '
      'shape is a spike at one and a short tail.</div>'
      % (L["median_codes"], int(L["max_codes"])))

    # chart 2: shape kinds
    tot = L["with_shape"]
    A('<div class="sec">Pictures by shape kind</div>')
    A('<div class="chart">')
    for lab, v in [("box and tag", L["both"]), ("tag only", L["tag_only"]), ("box only", L["box_only"])]:
        A(bar_row(lab, v, tot))
    A("</div>")
    A('<div class="cap">%s pictures carry at least one box and %s carry at least one tag, '
      'of the %s that carry any shape at all.</div>'
      % (format(L["pictures_with_box"], ","), format(L["pictures_with_tag"], ","),
         format(tot, ",")))

    # chart 3: pictures per defect
    byd = sorted(L["canonical_defects"], key=lambda d: -d["pictures"])
    dmax = max(d["pictures"] for d in byd)
    A('<div class="sec">Pictures carrying each canonical defect</div>')
    A('<div class="chart">')
    for d in byd:
        A(bar_row(d["name"], d["pictures"], dmax))
    A("</div>")
    A('<div class="cap">One class dominates: the largest is on %s pictures, so a '
      'one-folder-per-class split would put most of the set in that one bin.</div>'
      % format(byd[0]["pictures"], ","))

    # chart 4: box size by defect in microns (adopted scale, superseded comparison)
    A('<div class="sec">Median box size by defect, microns at the adopted scale</div>')
    A('<div class="legend"><span class="k1"></span>at 15.337 (adopted)'
      '<span class="k2"></span>at 18.1165 (superseded prior scale)</div>')
    A('<div class="chart">')
    byn = sorted(G["by_defect"].items(), key=lambda kv: -kv[1]["diag_um_adopted_p50"])
    umax = max(v["diag_um_adopted_p50"] for _, v in byn)
    for cid, v in byn:
        A(bar_row(cid, v["diag_um_adopted_p50"], umax,
                  second=v["diag_um_at_18_1165_p50"], fmt="%d"))
    A("</div>")
    A('<div class="cap">Every micron figure is the pixel median times the adopted scale '
      'of 15.337, derived from the customer\'s documented 300 micron cut. The grey bar is '
      'the superseded 18.1165 prior scale, kept only for comparison.</div>')

    A('<div class="foot"><span class="hint">Every number is read from a verified analysis '
      'artifact. The file is self-contained: no external styles, fonts or scripts.</span>'
      '</div>')
    A("</div>")

    css = """
.wrap{width:880px;text-align:left;color:var(--foreground)}
.h1{font-size:16px;font-weight:700;margin:0 0 2px}
.sub{font-size:12px;color:var(--muted-foreground);margin:0 0 12px}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px}
.chip{border:1px solid var(--border);border-radius:6px;padding:6px 10px;min-width:90px}
.cv{font-size:15px;font-weight:700;line-height:1.1}
.cl{font-size:10px;color:var(--muted-foreground)}
.sec{font-size:12px;font-weight:700;margin:16px 0 6px}
.chart{display:block}
.r{display:grid;grid-template-columns:150px 1fr 70px;align-items:center;gap:8px;margin:2px 0}
.lab{font-size:11px;color:var(--muted-foreground);text-align:right}
.track{height:16px;position:relative;border-left:1px solid var(--border)}
.bar{height:16px;background:var(--accent);border-radius:0 2px 2px 0;position:absolute;top:0;left:0}
.bar2{height:6px;background:var(--muted-foreground);opacity:.55;border-radius:0 2px 2px 0;position:absolute;top:17px;left:0}
.r.two .track{height:24px}
.val{font-size:11px;color:var(--muted-foreground);font-variant-numeric:tabular-nums}
.cap{font-size:11px;color:var(--muted-foreground);margin:6px 0 0;line-height:1.45}
.legend{font-size:11px;color:var(--muted-foreground);margin:0 0 6px;display:flex;align-items:center;gap:6px}
.k1{width:18px;height:9px;background:var(--accent);display:inline-block}
.k2{width:18px;height:6px;background:var(--muted-foreground);opacity:.55;display:inline-block;margin-left:10px}
.foot{margin:16px 0 0}
.hint{font-size:10px;color:var(--muted-foreground)}
"""
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Full-coverage EDA distributions</title>"
            "<style>%s</style></head><body>%s</body></html>" % (css, "".join(h)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--numbers", default="full_numbers.json")
    ap.add_argument("--out", default="distributions_widget.html")
    a = ap.parse_args()
    R = json.load(open(a.numbers, encoding="utf-8"))
    for key in ("labels", "census", "box_geometry"):
        if key not in R:
            raise SystemExit("full_numbers.json has no %s block; re-run the consolidator" % key)
    out = build(R)
    assert "\u2014" not in out, "em dash found in the widget"
    assert ".bmp" not in out and ".json" not in out and ":\\\\" not in out
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("wrote %s (%d bytes)" % (os.path.abspath(a.out), len(out.encode("utf-8"))))


if __name__ == "__main__":
    main()
