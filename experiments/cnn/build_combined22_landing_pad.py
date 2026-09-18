#!/usr/bin/env python3
"""Build the combined 22-class, 50-epoch-only landing-pad workbook in the same
format as ContactLensDefectResults_single50.xlsx / build_single50_landing_pad.py.

One row per architecture (4 rows), epochs = 50 for all. Adds a Recall (%) column
per 22-class code across both the former OOI and Lens Presentation sets.

Auto-fills from a metrics tree (as build_landing_pad.py):
    --metrics DIR/<arch_key>/epochs_50/metrics.json
(or a flat DIR/<arch_key>.json).

USAGE
    python3 scripts/build_combined22_landing_pad.py \
        --out      samples/ContactLensDefectResults_combined22.xlsx \
        --metrics  run/combined22_metrics
"""
import argparse
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from build_landing_pad import (ARCHITECTURES as LP_ARCHITECTURES,
                               ARCH_KEYS as LP_ARCH_KEYS,
                               CENTER, BORDER, HEADER_FILL)

# The combined-22 sheet has six architectures. The first four are shared with
# the 12-class landing pad (imported above, not modified there); the last two are
# the 2026-09-15 additions from FMD_ResNet50Architectures.
ARCHITECTURES = list(LP_ARCHITECTURES) + [
    "ResNet50-Inception-SE  (Branch attention) ***",
    "ResNet50-Inception-Refine  (Bicubic upsample) ****",
]
ARCH_KEYS = dict(LP_ARCH_KEYS)
ARCH_KEYS["ResNet50-Inception-SE  (Branch attention) ***"] = \
    "resnet50_inception_attention"
ARCH_KEYS["ResNet50-Inception-Refine  (Bicubic upsample) ****"] = \
    "resnet50_inception_refine"

EPOCH = 50

# One-time cold-start cost per architecture, in seconds, taken from our own 2026-09-08
# decomposition (reports/cnn/OOI_CNN_Analysis_CORRECTED_20260908.md): the difference
# between the no-warmup and the warm total on the 87-image OOI test set.
#   ResNet18   0.8214 - 0.0847 = 0.7367 s
#   ResNet50   2.2934 - 0.1212 = 2.1722 s
#   Inception  3.2531 - 0.1530 = 3.1001 s
#   SE         2.5845 - 0.1517 = 2.4328 s
# The two 2026-09-15 architectures are Inception-pattern builds, so they borrow the
# Inception figure. The ESTIMATED cold-start column ("~") is the warm time plus this
# one-time cost divided by the run's test-set size. The real measurement on this split
# is still to do; see experiments/cnn/README.md. The teammate's no-warmup run agrees
# with these figures within about 25 percent (ResNet50 matches to 2 percent), but their
# numbers are NOT used here: they are a different split.
COLD_ONETIME_SEC = {
    "resnet18": 0.7367,
    "resnet50": 2.1722,
    "resnet50_inception": 3.1001,
    "resnet50_se": 2.4328,
    "resnet50_inception_attention": 3.1001,
    "resnet50_inception_refine": 3.1001,
}
# All 22 defect classes (10 OOI + 12 Lens Presentation), alphabetical so codes
# and per-class columns line up with the metrics.json per_class keys.
ALL_22_CLASSES = [
    "Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123",
    "Bubble On Edge", "Bubble Scatter", "Cavity Off Center", "Dirty Camera",
    "Dirty Strobe", "Extraneous Polymer", "Fiber", "Foreign Matter",
    "HEMA Fragment", "HEMA Obstruction", "Lens Off Center",
    "Low Dose Obstructing Region of Interest", "Missing Lens",
    "Missing Primary Package", "Multiple Lenses", "Package Misalignment",
    "View Obstructed", "Wet Package",
]
CLASS_CODES = [
    "BB", "BC", "BI", "B123", "BOE", "BS", "COC", "DC", "DS", "EP", "FB",
    "FM", "HF", "HO", "LOC", "LDO", "ML", "MPP", "MUL", "PM", "VO", "WP",
]
DATASET_LABEL = ("Datasetver (Combined 22-class, single-scale 20260903 fixed "
                 "crops, 80-20 stratified split, train+test = single-size, batch 8)")


def _find_metrics(metrics_dir: Path, key: str) -> Path | None:
    """Locate a run's metrics.json: nested or flat."""
    nested = metrics_dir / key / f"epochs_{EPOCH}" / "metrics.json"
    if nested.exists():
        return nested
    flat = metrics_dir / f"{key}.json"
    if flat.exists():
        return flat
    return None


def build(out: Path, metrics_dir: Path | None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    n_cls = len(ALL_22_CLASSES)
    recall_first = 6
    recall_last = recall_first + n_cls - 1
    train_t = recall_last + 1
    infer_t = train_t + 1
    cold_t = infer_t + 1

    # ---- Header (rows 1-2) ----------------------------------------------
    ws["B1"] = "Dataset"
    ws["C1"] = "Architecture"
    ws["D1"] = "Overall Accuracy (%)"
    ws["E1"] = "Epochs"
    ws.merge_cells("B1:B2"); ws.merge_cells("C1:C2")
    ws.merge_cells("D1:D2"); ws.merge_cells("E1:E2")
    ws.cell(1, recall_first, "Recall (%)")
    ws.merge_cells(start_row=1, start_column=recall_first,
                   end_row=1, end_column=recall_last)
    ws.cell(1, train_t, "Training time (s)")
    ws.cell(1, infer_t, "Inference Time per Image(ms)")
    ws.cell(1, cold_t, "Inference per Image, cold start (ms, estimated)")
    ws.merge_cells(start_row=1, start_column=train_t, end_row=2, end_column=train_t)
    ws.merge_cells(start_row=1, start_column=infer_t, end_row=2, end_column=infer_t)
    ws.merge_cells(start_row=1, start_column=cold_t, end_row=2, end_column=cold_t)
    for i, code in enumerate(CLASS_CODES):
        ws.cell(2, recall_first + i, code)

    for r in (1, 2):
        for c in range(1, cold_t + 1):
            cell = ws.cell(r, c)
            cell.font = Font(bold=True)
            cell.alignment = CENTER
            cell.border = BORDER
            if cell.value is not None:
                cell.fill = HEADER_FILL

    # ---- Data rows: one per arch (all epoch 50) --------------------------
    row = 3
    for arch in ARCHITECTURES:
        ws.cell(row, 1, row - 2)
        ws.cell(row, 3, arch)
        ws.cell(row, 5, EPOCH)
        if metrics_dir is not None:
            key = ARCH_KEYS[arch]
            f = _find_metrics(metrics_dir, key)
            if f is not None:
                d = json.loads(f.read_text())
                ws.cell(row, 4, round(float(d["overall_accuracy"]) * 100, 2))
                for i, cls in enumerate(ALL_22_CLASSES):
                    pc = d["per_class"].get(cls)
                    ws.cell(row, recall_first + i,
                            round(float(pc["recall"]) * 100, 2) if pc else "")
                warm_ms = float(d["inference_per_image_ms"])
                cold_ms = warm_ms + (COLD_ONETIME_SEC[key] * 1000.0
                                     / float(d["num_test_images"]))
                ws.cell(row, train_t, round(float(d["training_time_sec"]), 2))
                ws.cell(row, infer_t, round(warm_ms, 2))
                ws.cell(row, cold_t, f"~{cold_ms:.1f}")
            else:
                ws.cell(row, 4, f"missing:{key}.json")
        row += 1

    last_data = row - 1
    ws.cell(3, 2, DATASET_LABEL)
    ws.merge_cells(start_row=3, start_column=2, end_row=last_data, end_column=2)

    for rr in range(3, last_data + 1):
        for cc in range(1, infer_t + 1):
            cell = ws.cell(rr, cc)
            cell.border = BORDER
            cell.alignment = CENTER

    fn_row = last_data + 2
    ws.cell(fn_row, 3, "* Multi-scale feature extraction architecture")
    ws.cell(fn_row + 1, 3, "** Channel-based attention architecture")
    ws.cell(fn_row + 2, 3, "*** Inception branches with Squeeze-and-Excitation "
                           "attention inside every branch")
    ws.cell(fn_row + 3, 3, "**** Inception with a bicubic-upsampled, "
                           "depthwise-refined L5 fusion path")

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 44
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 8
    for c in range(recall_first, recall_last + 1):
        ws.column_dimensions[get_column_letter(c)].width = 7
    ws.column_dimensions[get_column_letter(train_t)].width = 14
    ws.column_dimensions[get_column_letter(infer_t)].width = 16

    wb.save(out)
    mode = "AUTO-FILLED" if metrics_dir else "BLANK"
    print(f"Wrote {out}  [{mode}]  ({len(ARCHITECTURES)} arch x epoch {EPOCH}, "
          f"{n_cls} classes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",
                    default="samples/ContactLensDefectResults_combined22.xlsx",
                    type=Path)
    ap.add_argument("--metrics", type=Path, default=None,
                    help="dir with <arch_key>/epochs_50/metrics.json (or <arch_key>.json) "
                         "to auto-fill")
    args = ap.parse_args()
    build(args.out, args.metrics)