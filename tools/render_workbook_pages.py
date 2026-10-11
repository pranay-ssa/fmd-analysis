#!/usr/bin/env python3
"""Render a workbook the way Excel renders it, so a deliverable can be looked at.

Structural openpyxl checks cannot see overlapping labels, clipped cell text or a chart
whose axis title swallowed the first category. This renders the real thing through the
installed Excel: every chart to its own PNG, and every sheet to a one-page-wide PDF that
is rasterised page by page. Then look at the PNGs.

    uv run --with pywin32 --with pymupdf python tools/render_workbook_pages.py <xlsx> <outdir>

Windows with Excel installed only. Read-only: the workbook is never modified.
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # pymupdf
import win32com.client as win32

try:  # pymupdf renamed the module; keep both import paths working
    import pymupdf as fitz
except ImportError:
    import fitz


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    xlsx = Path(argv[1]).resolve()
    outdir = Path(argv[2]).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    excel = win32.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(str(xlsx), ReadOnly=True)

        # charts, at their own size
        for ws in wb.Worksheets:
            for i in range(1, ws.Shapes.Count + 1):
                try:
                    chart = ws.Shapes(i).Chart
                except Exception:
                    continue
                name = "%s_%d_chart.png" % (str(ws.Name).replace(" ", "_"), i)
                chart.Export(str(outdir / name), "PNG")

        # sheets, one page wide, rasterised
        for ws in wb.Worksheets:
            ws.PageSetup.Zoom = False
            ws.PageSetup.FitToPagesWide = 1
            ws.PageSetup.FitToPagesTall = False
            ws.PageSetup.Orientation = 2  # landscape
            stem = str(ws.Name).replace(" ", "_")
            pdf = outdir / ("%s.pdf" % stem)
            ws.ExportAsFixedFormat(0, str(pdf))
            doc = fitz.open(str(pdf))
            for page_no, page in enumerate(doc):
                page.get_pixmap(dpi=110).save(str(outdir / ("%s_p%d.png" % (stem, page_no + 1))))
            doc.close()
        wb.Close(False)
    finally:
        excel.Quit()

    for path in sorted(outdir.glob("*.png")):
        print("%8d  %s" % (path.stat().st_size, path.name))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
