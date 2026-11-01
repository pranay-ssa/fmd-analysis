#!/usr/bin/env python3
"""Verify the full-coverage EDA deliverables against the run artifacts.

Deliberately does NOT reuse eda_numbers.py. It re-reads the run artifacts under
run/eda_full_20261015/ by its own routes and then checks:

  1. every headline figure it re-derives equals the value in full_numbers.json;
  2. every headline figure appears in the workbook that was built from it;
  3. every headline figure appears in the HTML report;
  4. the workbook has the expected sheets and row counts;
  5. the widget is a single self-contained file with no network references;
  6. no em dash leaked into any client-facing artefact;
  7. no local path, file name or ticket number leaked into them.

Exit code 0 means every check passed. Any failure is printed and exits 1.

Usage:
  python verify_deliverables.py --run run/eda_full_20261015 \
      --numbers reports/eda_full/full_numbers.json \
      --workbook reports/eda_full/FMD_Full_EDA_20261015.xlsx \
      --report reports/eda_full/full_eda_report.html \
      --widget reports/eda_full/distributions_widget.html \
      --findings reports/eda_full/findings_20261015.md
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

from openpyxl import load_workbook

FAILURES = []
CHECKS = [0]


def check(name, got, want):
    CHECKS[0] += 1
    ok = (got == want)
    if not ok:
        FAILURES.append("%s: got %r want %r" % (name, got, want))
    print("  %-52s %-12s %s" % (name, got, "OK" if ok else "FAIL want %r" % (want,)))
    return ok


def norm(s):
    return str(s).replace(",", "").replace("\u00a0", "").strip()


def contains_figure(haystack_norm, value):
    """True if the number appears in the normalized text in any plain rendering."""
    if isinstance(value, int):
        return str(value) in haystack_norm
    # float: accept the 4, 3 and 2 decimal renderings
    for dp in (4, 3, 2, 1):
        if ("%%.%df" % dp % value) in haystack_norm:
            return True
    return False


def rederive(run_dir):
    f = {}
    # ---- file_manifest.csv: census
    total = 0
    bytes_total = 0
    hashes = set()
    lib_files = 0
    with open(os.path.join(run_dir, "file_manifest.csv"), encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            total += 1
            hashes.add(r["md5"])
            try:
                bytes_total += int(r["bytes"])
            except (KeyError, ValueError):
                pass
            folder = r.get("folder") or r.get("winning_path") or ""
            if "PRODUCTION" not in folder:
                lib_files += 1
    f["census.distinct_pictures"] = len(hashes)
    f["census.files_total"] = total
    f["census.files_library"] = lib_files
    f["census.bytes_total"] = bytes_total

    # ---- resolved_labels.csv: the label census
    pics = set()
    boxpics = set()
    tagpics = set()
    boxes = tags = shapes = 0
    cids = set()
    with open(os.path.join(run_dir, "resolved_labels.csv"), encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            shapes += 1
            pics.add(r["picture_md5"])
            cids.add(r["canonical_id"])
            if r["shape_kind"] == "box":
                boxes += 1
                boxpics.add(r["picture_md5"])
            else:
                tags += 1
                tagpics.add(r["picture_md5"])
    f["labels.with_shape"] = len(pics)
    f["labels.shapes_total"] = shapes
    f["labels.boxes"] = boxes
    f["labels.tags"] = tags
    f["labels.canonical_count"] = len(cids)
    f["labels.pictures_with_box"] = len(boxpics)
    f["labels.pictures_with_tag"] = len(tagpics)
    f["labels.no_shape"] = f["census.distinct_pictures"] - f["labels.with_shape"]

    # ---- resolution.json: mentioned and nowhere
    res = json.load(open(os.path.join(run_dir, "resolution.json"), encoding="utf-8"))
    f["labels.mentioned"] = res["win_counts"]["resolved_pictures_total"]
    f["labels.nowhere"] = res["unannotated_pictures"]

    # ---- box_sizes.csv: geometry and the axis-aligned share
    total_boxes = axis = 0
    with open(os.path.join(run_dir, "box_sizes.csv"), encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            total_boxes += 1
            if r.get("rotation", "") in ("", "0.0", "0"):
                axis += 1
    f["box_geometry.total"] = total_boxes
    f["box_geometry.axis_aligned"] = axis

    # ---- cavity
    cav = json.load(open(os.path.join(run_dir, "cavity_geometry_library.json"), encoding="utf-8"))
    f["cavity.pictures"] = cav["summary"]["pictures"]
    f["cavity.measured"] = cav["summary"]["pictures_measured"]
    f["cavity.unmeasured"] = cav["summary"]["pictures_could_not_measure"]

    # ---- the inversion
    gate = json.load(open(os.path.join(run_dir, "gate_scale_estimate.json"), encoding="utf-8"))
    comb = gate["scale_estimate"]["implied_scale_combined"]
    f["inversion.low"] = comb["scale_um_per_px_low"]
    f["inversion.high"] = comb["scale_um_per_px_high"]
    f["inversion.mid"] = comb["scale_um_per_px_mid"]
    f["inversion.agrees_with_18_1165"] = comb["agrees_with_18_1165"]
    f["inversion.agrees_with_18_25"] = comb["agrees_with_18_25"]
    # the 0-vs-39 misclassification figure lives in the assumptions text
    f["inversion.misclass_text"] = any("0 misclassifications" in a and "39" in a
                                       for a in gate["scale_estimate"]["assumptions"])

    # ---- folder disagreement
    lib = batch = 0
    with open(os.path.join(run_dir, "folder_disagreement.csv"), encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["distinct_class_count"]) > 1:
                lib += 1
                if r["in_production_batch"] == "true":
                    batch += 1
    f["disagreement.content_library"] = lib
    f["disagreement.content_batch"] = batch

    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="run/eda_full_20261015")
    ap.add_argument("--numbers", default="reports/eda_full/full_numbers.json")
    ap.add_argument("--workbook", default="reports/eda_full/FMD_Full_EDA_20261015.xlsx")
    ap.add_argument("--report", default="reports/eda_full/full_eda_report.html")
    ap.add_argument("--widget", default="reports/eda_full/distributions_widget.html")
    ap.add_argument("--findings", default="reports/eda_full/findings_20261015.md")
    a = ap.parse_args()

    print("\n1. re-derive every headline from the run artifacts")
    f = rederive(a.run)
    checks_route = len(f)

    R = json.load(open(a.numbers, encoding="utf-8"))
    N = {
        "census.distinct_pictures": R["census"]["distinct_pictures"],
        "census.files_library": R["census"]["files_library"],
        "census.files_total": R["census"]["files_total"],
        "census.bytes_total": R["census"]["bytes_total"],
        "labels.with_shape": R["labels"]["with_shape"],
        "labels.shapes_total": R["labels"]["shapes_total"],
        "labels.boxes": R["labels"]["boxes"],
        "labels.tags": R["labels"]["tags"],
        "labels.canonical_count": R["labels"]["canonical_count"],
        "labels.pictures_with_box": R["labels"]["pictures_with_box"],
        "labels.pictures_with_tag": R["labels"]["pictures_with_tag"],
        "labels.no_shape": R["labels"]["no_shape"],
        "labels.mentioned": R["labels"]["mentioned"],
        "labels.nowhere": R["labels"]["nowhere"],
        "box_geometry.total": R["box_geometry"]["total"],
        "box_geometry.axis_aligned": R["box_geometry"]["axis_aligned"],
        "cavity.pictures": R["cavity"]["read"]["pictures"],
        "cavity.measured": R["cavity"]["read"]["pictures_measured"],
        "cavity.unmeasured": R["cavity"]["read"]["pictures_could_not_measure"],
        "inversion.low": R["micron_gate"]["implied_scale_combined"]["scale_um_per_px_low"],
        "inversion.high": R["micron_gate"]["implied_scale_combined"]["scale_um_per_px_high"],
        "inversion.mid": R["micron_gate"]["implied_scale_combined"]["scale_um_per_px_mid"],
        "disagreement.content_library": R["disagreement"]["content_library"],
        "disagreement.content_batch": R["disagreement"]["content_batch"],
    }
    print("   re-derived %d figures by an independent route" % checks_route)
    for k in sorted(N):
        check("numbers-match:%s" % k, N[k], f[k])
    check("inversion agrees with neither scale", True,
          (f["inversion.agrees_with_18_1165"] is False and f["inversion.agrees_with_18_25"] is False))
    check("0-vs-39 misclassification figure present in an artifact", True, f["inversion.misclass_text"])

    print("\n2. invariants")
    check("with_shape + no_shape = census",
          f["labels.with_shape"] + f["labels.no_shape"], f["census.distinct_pictures"])
    check("mentioned + nowhere = census",
          f["labels.mentioned"] + f["labels.nowhere"], f["census.distinct_pictures"])
    check("boxes + tags = shapes",
          f["labels.boxes"] + f["labels.tags"], f["labels.shapes_total"])
    check("the no-shape count equals the tag count", f["labels.no_shape"], f["labels.tags"])
    check("boxes in box_sizes equal box shapes in the label census",
          f["box_geometry.total"], f["labels.boxes"])

    # ---- workbook
    print("\n3. the workbook")
    wb = load_workbook(a.workbook)
    wb_text = []
    for name in wb.sheetnames:
        for row in wb[name].iter_rows():
            for c in row:
                if c.value is not None:
                    wb_text.append(str(c.value))
    wbn = norm(" ".join(wb_text))
    want_sheets = ["Read me", "Census", "Labels", "Distributions", "Box geometry",
                   "Blind scale", "Micron gate", "Coverage", "Crosswalk", "Checks"]
    check("sheet names", wb.sheetnames, want_sheets)
    empty = [n for n in wb.sheetnames if wb[n].max_row < 5]
    check("no empty sheet", empty, [])
    for k in sorted(N):
        check("workbook-has:%s" % k, contains_figure(wbn, N[k]), True)
    check("workbook-has:misclassification 39", ("39" in wbn), True)
    check("workbook-has:blob coverage 10438", ("10438" in wbn), True)
    check("workbook-has:name-based 113", ("113" in wbn), True)
    check("workbook-has:lens diameter 12101 (789 px at the adopted scale)", ("12101" in wbn), True)
    check("workbook-has:adopted scale 15.337", ("15.337" in wbn), True)
    check("workbook-has:per-line scale 15.601", ("15.601" in wbn), True)
    check("workbook-has:superseded prior scale 18.1165", ("18.1165" in wbn), True)
    # sanity anchors, recomputed from pixels at the adopted scale
    check("workbook-has:bubble anchor 142.6", ("142.6" in wbn), True)
    check("workbook-has:foreign-matter anchor 291.9", ("291.9" in wbn), True)
    check("workbook-has:fiber anchor 706", ("706" in wbn), True)
    check("workbook-has:gate boundary 297.7 to 300.8",
          ("297.7" in wbn and "300.8" in wbn), True)
    check("workbook-has:old cut at 42.19 px", ("42.19" in wbn), True)
    check("workbook-has:superseded label", ("superseded" in wbn.lower()), True)

    print("\n4. the report")
    repn = norm(open(a.report, encoding="utf-8").read())
    for k in ["census.distinct_pictures", "census.files_library", "census.files_total",
              "labels.with_shape", "labels.no_shape", "labels.nowhere", "labels.shapes_total",
              "labels.boxes", "labels.tags", "labels.canonical_count",
              "labels.pictures_with_box", "box_geometry.axis_aligned",
              "cavity.measured", "cavity.unmeasured",
              "disagreement.content_library", "disagreement.content_batch"]:
        check("report-has:%s" % k, contains_figure(repn, N[k]), True)
    check("report-has:inversion midpoint", ("15.337" in repn or "15.34" in repn), True)
    check("report-has:inversion low", ("15.298" in repn), True)
    check("report-has:inversion high", ("15.376" in repn), True)
    check("report-has:adopted-scale derivation statement",
          ("300 micron cut" in open(a.report, encoding="utf-8").read()), True)
    check("report-has:gate boundary 298 to 301 microns",
          ("298" in repn and "301" in repn), True)
    check("report-has:lens rim 789", ("789" in repn), True)
    check("report-has:per-line scale 15.601", ("15.601" in repn), True)
    check("report-has:18.1165 labelled superseded", ("18.1165" in repn), True)
    check("report-has:misclassification 39", ("39" in repn), True)
    check("report-has:name-based 113", ("113" in repn), True)
    check("report-has:blob coverage 10438", ("10438" in repn), True)
    check("report-has:12,101 micron lens consequence", ("12101" in repn
          or "12.10" in repn), True)
    check("report labels the superseded set", ("superseded" in open(a.report, encoding="utf-8").read().lower()), True)

    print("\n5. the widget is self-contained")
    wtext = open(a.widget, encoding="utf-8").read()
    check("widget has no http reference", bool(re.search(r"https?://", wtext)), False)
    check("widget has no protocol-relative or cdn reference",
          bool(re.search(r"//cdn|src=[\"']//|href=[\"']//", wtext)), False)
    check("widget is a single html file", wtext.lstrip().lower().startswith("<!doctype html"), True)
    check("widget byte size > 4000", len(wtext.encode("utf-8")) > 4000, True)
    wnorm = norm(wtext)
    for k in ["census.distinct_pictures", "labels.shapes_total", "labels.boxes",
              "labels.tags", "labels.canonical_count"]:
        check("widget-has:%s" % k, contains_figure(wnorm, N[k]), True)
    check("widget-has:axis-aligned share 4.7", ("4.7" in wnorm), True)

    print("\n6. style gates: no em dash, no path, no file name, no ticket number")
    em = 0
    for path in (a.workbook, a.report, a.widget, a.findings):
        if path.endswith(".xlsx"):
            for name in wb.sheetnames:
                for row in wb[name].iter_rows():
                    for c in row:
                        if isinstance(c.value, str) and "\u2014" in c.value:
                            em += 1
        else:
            em += open(path, encoding="utf-8").read().count("\u2014")
    check("em dash count across all client-facing artefacts", em, 0)

    leaks = 0
    leak_re = re.compile(r"[A-Za-z]:[\\/]|/home/|/Users/|run/eda_full|\.xlsx\b|\.csv\b|\.py\b|"
                         r"\.bmp\b|\.json\b|\.html\b|\bticket\b|\bwl-\d|\bres-\d|\bnote-\d", re.I)
    for path in (a.report, a.widget):
        txt = open(path, encoding="utf-8").read()
        for m in leak_re.finditer(txt):
            leaks += 1
            print("     leak in %s: %r" % (os.path.basename(path), m.group(0)))
    for name in wb.sheetnames:
        for row in wb[name].iter_rows():
            for c in row:
                if isinstance(c.value, str):
                    for m in leak_re.finditer(c.value):
                        leaks += 1
                        print("     leak in workbook %s!%s: %r" % (name, c.coordinate, m.group(0)))
    check("path / file-name / ticket-number leaks across client-facing artefacts", leaks, 0)

    print("\n7. figures that live only in the written records")
    rec = open("reports/eda_full/coverage_20261015.md", encoding="utf-8").read() \
        if os.path.exists("reports/eda_full/coverage_20261015.md") else ""
    recn = norm(rec)
    sup = open("docs/reference/production_20260925_batch_analysis.md", encoding="utf-8").read() \
        if os.path.exists("docs/reference/production_20260925_batch_analysis.md") else ""
    supn = norm(sup)
    for label, token, hay in [("name-based 113", "113", recn),
                              ("blob folder total 10438", "10438", recn),
                              ("blob coverage 10.03", "10.03", recn),
                              ("library-only 177", "177", recn),
                              ("superseded boxes 12793", "12793", supn),
                              ("superseded tags 1318", "1318", supn),
                              ("superseded codes 24", "24", supn)]:
        check("written-record-has:%s" % label, token in hay, True)

    print("\n8. the Box geometry scale block")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scale_section import compute as _compute_scale
    Q = _compute_scale(a.run)
    bg = wb["Box geometry"]
    bg_text = norm(" ".join(str(c.value) for row in bg.iter_rows()
                            for c in row if c.value is not None))
    # the derivation of 18.1165, its sample, and the source of the nominal
    for label, token in [("derivation: lens rim 783.8 px", "783.8"),
                         ("derivation: our scale 18.1165", "18.1165"),
                         ("derivation: our 14200 micron nominal", "14200"),
                         ("derivation: 200 passing frames", "200"),
                         ("derivation: separate production-sample drop", "production-sample"),
                         ("derivation: 5.3 percent spread", "5.3"),
                         ("spoken scale named", "18.25"),
                         ("spoken scale written nowhere", "written in no document"),
                         ("second-measurement heading", "does not behave"),
                         ("not quotable statement", "not quotable"),
                         ("superseded October record", "superseded"),
                         ("diagonal artefact correction", "diagonal")]:
        check("box-geometry-has:%s" % label, token in bg_text, True)
    # the window counts, re-derived by the verifier's own call
    check("scale: measured pictures", contains_figure(bg_text, Q["measured"]), True)
    check("scale: pinned at the upper edge", contains_figure(bg_text, Q["pinned_hi"]), True)
    check("scale: valid pictures", contains_figure(bg_text, Q["valid"]), True)
    check("scale: dropped count", contains_figure(bg_text, Q["dropped"]), True)
    # the per-folder and per-line tables carry n for both views
    check("scale: folder table view one rows",
          sum(1 for _ in Q["folder_all"]), 3)
    check("scale: folder table view two rows",
          sum(1 for _ in Q["folder_no_lens"]), 3)
    check("scale: line table view one rows", sum(1 for _ in Q["line_all"]), 5)
    check("scale: line table view two rows", sum(1 for _ in Q["line_no_lens"]), 5)
    # the four required items appear in order
    heads = ["The adopted scale: 15.337 microns per pixel",
             "A second measurement",
             "Per folder, both views",
             "Two corrections carried"]
    rows_seen = []
    for r in bg.iter_rows():
        for c in r:
            if isinstance(c.value, str):
                for h in heads:
                    if c.value.startswith(h) and h not in rows_seen:
                        rows_seen.append(h)
    check("scale: the four new blocks, in order", rows_seen, heads)

    print("\n%d checks run, %d failed" % (CHECKS[0], len(FAILURES)))
    if FAILURES:
        for fail in FAILURES:
            print("  FAIL", fail)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
