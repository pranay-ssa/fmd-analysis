#!/usr/bin/env python3
"""Build the misclassification manifest Excel for bubble_full_merge (phase 2).

Reads the manifest CSV written on the VM and produces a formatted .xlsx:
sno is the primary key, one row per misclassified test crop, with the original
crop name, source image, crop bbox and the true/predicted labels.

Run through uv when openpyxl is not in the project env:
  uv run --with openpyxl python make_misclassification_xlsx.py \
      --csv run/bubble_full_merge_20261015_misclassification_manifest.csv \
      --out run/bubble_full_merge_20261015_misclassification_manifest.xlsx
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv, newline="", encoding="utf-8")))
    print("manifest rows: %d" % len(rows))

    wb = Workbook()

    # ---- sheet 1: the manifest ----
    ws = wb.active
    ws.title = "Misclassification"

    header_fill = PatternFill("solid", fgColor="D9E1F2")
    thin = Side(style="thin", color="B0B0B0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(vertical="top", wrap_text=True)

    cols = [
        ("sno", 8), ("png", 44), ("original_crop", 62), ("source_image", 58),
        ("source_md5", 34), ("xtl", 10), ("ytl", 10), ("xbr", 10), ("ybr", 10),
        ("rotation", 10), ("true_label", 20), ("predicted_label", 20),
    ]
    ws.append([c[0] for c in cols])
    for i, (name, width) in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
        cell = ws.cell(row=1, column=i)
        cell.fill = header_fill
        cell.font = Font(bold=True)
        cell.border = border
        cell.alignment = wrap

    numcols = {"sno", "xtl", "ytl", "xbr", "ybr", "rotation"}
    for r in rows:
        ws.append([
            int(r["sno"]) if r["sno"].isdigit() else r["sno"],
            r["png"], r["original_crop"], r["source_image"], r["source_md5"],
            float(r["xtl"]), float(r["ytl"]), float(r["xbr"]), float(r["ybr"]),
            float(r["rotation"]), r["true_label"], r["predicted_label"],
        ])
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(cols)):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(cols)), ws.max_row)

    # ---- sheet 2: the error-pair summary ----
    ws2 = wb.create_sheet("Error pairs")
    cnt = Counter((r["true_label"], r["predicted_label"]) for r in rows)
    imgs = {}
    for r in rows:
        imgs.setdefault((r["true_label"], r["predicted_label"]), set()).add(r["source_image"])
    support = Counter(r["true_label"] for r in rows)

    ws2.append(["true_label", "predicted_label", "crops", "source_images",
                "true_class_total_crops", "share_of_true_class"])
    for i, w in enumerate([22, 22, 10, 14, 22, 18], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w
        c = ws2.cell(row=1, column=i)
        c.fill = header_fill
        c.font = Font(bold=True)
        c.border = border
    for (t, p), c in cnt.most_common():
        ws2.append([t, p, c, len(imgs[(t, p)]), support[t],
                    round(c / support[t], 4)])
    for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row, max_col=6):
        for cell in row:
            cell.border = border
    for cell in ws2["F"][1:]:
        cell.number_format = "0.0%"
    ws2.freeze_panes = "A2"

    # ---- sheet 3: read-me ----
    ws3 = wb.create_sheet("Read me", 0)
    ws3.column_dimensions["A"].width = 118
    lines = [
        "bubble full merge - misclassification manifest",
        "",
        "What this holds: every test crop the model got wrong, one row per crop.",
        "399 of 4,389 test crops (9.1%%), from 145 distinct source images of 340 in the test split.",
        "",
        "How to read it: sno is the primary key and is unique per misclassified CROP, not per image.",
        "The PNG in the misclassification folder is named <sno>_<true>_<pred>.png, so sno joins a",
        "file in that folder to its row here. Two bad crops from the same source image get two",
        "s.nos; source_image is what ties them together.",
        "",
        "The bbox columns (xtl, ytl, xbr, ybr, rotation) are the annotated box the crop was cut",
        "from, in the source frame's own pixels. They exist because several test images carry",
        "many crops, so source_image alone is not specific enough to locate the defect.",
        "",
        "Provenance: predictions from the resnet50_inception run (50 epochs, batch 8, seed 42) on",
        "the 70:30 image-level split of the 2026-10-15 dataset (1,132 defect images, 14,184 crops).",
        "Crops are rotate-upright cuts of the annotated boxes. This manifest describes the test",
        "split only; train crops are never predicted on.",
        "",
        "Naming note: class names in filenames are lowercase with spaces as underscores, e.g.",
        "hema_fragment_extraneous_polymer. Labels here are the model's own 6-class frame.",
    ]
    for i, line in enumerate(lines, start=1):
        ws3.cell(row=i, column=1, value=line)
    ws3.cell(row=1, column=1).font = Font(bold=True, size=13)
    for r in (5, 7, 12, 16, 20):
        ws3.cell(row=r, column=1).font = Font(bold=True)

    wb.save(args.out)
    print("wrote %s" % args.out)

    # verify by reading back
    from openpyxl import load_workbook
    rb = load_workbook(args.out)
    print("sheets: %s" % rb.sheetnames)
    m = rb["Misclassification"]
    print("manifest sheet: %d rows (incl header), %d cols" % (m.max_row, m.max_column))
    print("first data row: %s | %s | %s -> %s"
          % (m.cell(row=2, column=1).value, m.cell(row=2, column=2).value,
             m.cell(row=2, column=11).value, m.cell(row=2, column=12).value))
    s = rb["Error pairs"]
    print("error-pair sheet rows: %d (incl header)" % s.max_row)
    pair_total = sum(s.cell(row=i, column=3).value for i in range(2, s.max_row + 1))
    print("gate pair crops sum == 399: %s (%d)"
          % ("PASS" if pair_total == 399 else "FAIL", pair_total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
