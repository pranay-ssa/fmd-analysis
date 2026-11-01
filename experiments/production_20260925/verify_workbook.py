#!/usr/bin/env python3
"""Independently verify the PRODUCTION_20260925 workbook.

Deliberately does NOT reuse batch_numbers.py. It counts shapes by regex over the
raw XML text (a different method from the ElementTree parse the numbers module
uses), then checks:

  1. the raw counts match the numbers JSON,
  2. the numbers JSON matches the cells actually present in the workbook,
  3. the invariant sums hold (per-image distribution, size table, gate subsets),
  4. the thresholds in the workbook agree with the scale estimate's own
     pre-computed pixel values,
  5. no em dashes leaked into any text cell.

Exit code 0 means every check passed. Any failure is printed and exits 1.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys

from openpyxl import load_workbook

FAILURES = []
CHECKS = [0]


def check(name, got, want, tol=None):
    CHECKS[0] += 1
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    if not ok:
        FAILURES.append("%s: got %r want %r" % (name, got, want))
    print("  %-58s %-10s %s" % (name, got, "OK" if ok else "FAIL want %r" % (want,)))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotations", required=True)
    ap.add_argument("--numbers", required=True)
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--scale", default=None)
    a = ap.parse_args()

    R = json.load(open(a.numbers, encoding="utf-8"))
    S = R["summary"]

    print("\n1. raw text counts vs the numbers JSON")
    n_img = n_box = n_tag = 0
    for p in sorted(glob.glob(os.path.join(a.annotations, "*.xml"))):
        t = open(p, encoding="utf-8", errors="replace").read()
        n_img += len(re.findall(r"<image\b", t))
        n_box += len(re.findall(r"<box\b", t))
        n_tag += len(re.findall(r"<tag\b", t))
    check("images by regex", n_img, S["images"])
    check("boxes by regex", n_box, S["boxes"])
    check("tag elements by regex", n_tag, S["tag_elements"])

    print("\n2. invariants inside the numbers JSON")
    check("codes-per-image sums to the image count",
          sum(n for _, n in R["codes_per_image_distribution"]), S["images"])
    check("per-image rows equal the image count", len(R["per_image"]), S["images"])
    check("per-image box column sums to the box count",
          sum(r["n_boxes"] for r in R["per_image"]), S["boxes"])
    check("per-image tag column sums to the tag element count",
          sum(r["n_tags"] for r in R["per_image"]), S["tag_elements"])
    check("size table sums to the box count (minus gate codes, which hold no boxes)",
          sum(s["n"] for s in R["sizes"]), S["boxes"])
    check("box source splits add up",
          R["box_source"].get("file", 0) + R["box_source"].get("manual", 0), S["boxes"])
    check("codes per image, max, matches the summary",
          max(k for k, _ in R["codes_per_image_distribution"]), S["max_codes_per_image"])

    print("\n3. gate subsets: every gate's images are a subset of its base code")
    by_code = {c["code"]: c for c in R["codes"]}
    for g in R["gates"]:
        check("%s images <= %s images" % (g["gate"], g["base"]),
              by_code[g["gate"]]["images"], min(by_code[g["gate"]]["images"],
                                                by_code[g["base"]]["images"]))

    print("\n4. thresholds agree with the scale estimate's own pixel values")
    if a.scale and os.path.exists(a.scale):
        st = json.load(open(a.scale))["summary"]
        for i, t in enumerate(R["thresholds"]):
            check("threshold %s um in px" % t["threshold_um"],
                  round(t["threshold_px"], 2), round(st["thresh_px_linear"][i], 2))
        check("um per pixel", S["um_per_px"], st["um_per_px"])

    print("\n5. workbook structure and key cells")
    wb = load_workbook(a.workbook)
    want_sheets = ["Read me", "EDA", "Distributions", "Tags & codes", "Annotator email",
                   "Micron", "Per image", "Checks"]
    check("sheet names", wb.sheetnames, want_sheets)

    ws = wb["Per image"]
    # header row is row 5; data starts row 6
    check("per-image data rows",
          ws.max_row - 5, S["images"])
    hdr = [c.value for c in ws[5]]
    check("per-image first header", hdr[0], "File name")
    datarow = [c.value for c in ws[6]]
    check("first data row has a filename", bool(re.match(r".*\.bmp$", str(datarow[0]))), True)

    ws = wb["Tags & codes"]
    rows = [[c.value for c in r] for r in ws.iter_rows(min_row=1, max_row=ws.max_row)]
    code_rows = [r for r in rows if r[0] in by_code and isinstance(r[5], int)]
    check("catalogue rows equal the distinct code count", len(code_rows), S["distinct_codes"])
    tot_img = sum(r[5] for r in code_rows)
    check("catalogue image column sums to the per-code total",
          tot_img, sum(c["images"] for c in R["codes"]))
    tot_box = sum(r[7] for r in code_rows)
    check("catalogue box column sums to the box count", tot_box, S["boxes"])
    tot_tag = sum(r[8] for r in code_rows)
    check("catalogue tag column sums to the tag element count", tot_tag, S["tag_elements"])

    D = R["distributions"]
    ds = D["summary"]
    check("codes-per-image distribution sums to the image count",
          sum(n for _, n in D["codes_per_image"]), S["images"])
    check("base-code distribution sums to the image count",
          sum(n for _, n in D["base_codes_per_image"]), S["images"])
    check("box-code distribution sums to the image count",
          sum(n for _, n in D["box_codes_per_image"]), S["images"])
    check("tag-code distribution sums to the image count",
          sum(n for _, n in D["tag_codes_per_image"]), S["images"])
    # the split must reconstruct the total: per image, box codes + tag codes == codes
    bad = [p["basename"] for p in R["per_image"]
           if p["n_box_codes"] + p["n_tag_codes"] != p["n_codes"]]
    check("box codes plus tag codes equals codes on every image", len(bad), 0)
    if bad:
        print("     offenders:", bad[:5])
    # base codes = codes minus the gate flags, and the gate flags are a subset
    bad = [p["basename"] for p in R["per_image"]
           if p["n_base_codes"] != p["n_codes"] - p["n_gate_codes"]]
    check("base codes equal codes minus gate codes on every image", len(bad), 0)
    check("max codes is the top of the per-image distribution",
          ds["max_codes"], max(p["n_codes"] for p in R["per_image"]))
    check("max base codes matches the per-image rows",
          ds["max_base_codes"], max(p["n_base_codes"] for p in R["per_image"]))
    check("tail table lists every image at or above the cut",
          len(D["tail_images"]),
          sum(1 for p in R["per_image"] if p["n_codes"] >= ds["tail_cut"]))
    check("charts on the Distributions sheet", len(wb["Distributions"]._charts), 5)
    check("size histogram sums to the box count",
          sum(b["boxes"] for b in D["size_histogram"]), S["boxes"])
    # a gate flag must correspond to a box code present on the same image
    bad = []
    for p in R["per_image"]:
        gates = [c for c in p["tag_codes"].split("; ") if c.endswith("_MICRON_THRESHOLD")]
        bases = set(p["box_codes"].split("; "))
        for g in gates:
            if g[:-len("_MICRON_THRESHOLD")] not in bases:
                bad.append((p["basename"], g))
    check("every gate flag has its base box code on the same image", len(bad), 0)
    if bad:
        print("     offenders:", bad[:5])

    if R.get("email"):
        em = R["email"]
        ws = wb["Annotator email"]
        vals = [r for r in ws.iter_rows(values_only=True)]
        codes_in_sheet = {r[0] for r in vals if r and r[0] in {x["email_code"] for x in em["rows"]}}
        check("every email code has a reconciliation row",
              len(codes_in_sheet), len(em["rows"]))
        # the delivered column must equal the numbers JSON, not the email
        # the delivered column must equal the numbers JSON, not the email.
        # target the reconciliation table only: its second column is the code,
        # whereas the micron table's second column is the stated count.
        bad = []
        for r in vals:
            if (r and isinstance(r[1], str) and r[1] in by_code
                    and isinstance(r[3], int) and r[3] != by_code[r[1]]["shapes"]):
                bad.append((r[1], r[3], by_code[r[1]]["shapes"]))
        check("delivered shape counts on the email sheet match the computed counts",
              len(bad), 0)
        if bad:
            print("     offenders:", bad[:5])
        stated = sum(x["stated"] for x in em["rows"])
        check("email stated totals are positive", stated > 0, True)

    print("\n6. no em dashes anywhere in the workbook text")
    bad = []
    for name in wb.sheetnames:
        for row in wb[name].iter_rows():
            for c in row:
                if isinstance(c.value, str) and "\u2014" in c.value:
                    bad.append("%s!%s" % (name, c.coordinate))
    check("em dash count", len(bad), 0)
    if bad:
        print("     offenders:", bad[:10])

    print("\n7. no placeholders left in text")
    susp = []
    for name in wb.sheetnames:
        for row in wb[name].iter_rows():
            for c in row:
                if isinstance(c.value, str) and ("None" == c.value.strip()
                                                 or "nan" == c.value.strip()):
                    susp.append("%s!%s" % (name, c.coordinate))
    check("cells that are literally None or nan", len(susp), 0)
    if susp:
        print("     offenders:", susp[:10])

    print("\n%d checks run, %d failed" % (CHECKS[0], len(FAILURES)))
    if FAILURES:
        for f in FAILURES:
            print("  FAIL", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
