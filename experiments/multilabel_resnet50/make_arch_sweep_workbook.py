#!/usr/bin/env python3
"""Workbook for the 2026-09-29 multilabel architecture sweep.

Reads run/multilabel_lp_archs_20260929/runs/<arch>_20260929/{metrics.json,history.csv,
test_predictions.npz} and writes reports/multilabel/FMD_MultiLabel_ArchSweep_20260929.xlsx.

Sheets
  Sweep summary   one row per architecture, the headline numbers
  Folded Lens     the ask: per-class numbers for Folded Lens, plus a threshold sweep
                  read from the saved scores (no re-run needed)
  Per class       every architecture x every class, with confusion counts
  Timing          training and inference time, with what the no-warmup number includes
  Epoch history   per-epoch training loss and seconds
  Method          what ran, the recipe, and the rules for reading the table

Reader-facing names and class names only: no local paths, no repo filenames.
    python experiments/multilabel_resnet50/make_arch_sweep_workbook.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train as T  # noqa: E402

RUN = Path("run/multilabel_lp_archs_20260929/runs")
OUT = Path("reports/multilabel/FMD_MultiLabel_ArchSweep_20260929.xlsx")

# Reader-facing short names, in the order the lead meets them.
SHORT = {
    T.ARCH_RESNET50: "ResNet50 (baseline)",
    T.ARCH_MULTISCALE: "ResNet50 MultiLevel MultiScale",
    T.ARCH_MULTILVL_ATTENTION: "ResNet50 MultiLevel Attention (SE)",
    T.ARCH_INCEPTION_ATTENTION: "ResNet50 Inception + branch attention",
    T.ARCH_INCEPTION_REFINE: "ResNet50 Inception + refined decode",
}
ARCH_NOTE = {
    T.ARCH_RESNET50: "the control: plain ResNet50 with a 5-output head",
    T.ARCH_MULTISCALE: "Architecture 1 of the notebook: four-branch Inception filters on three depth levels, fused at 14x14",
    T.ARCH_MULTILVL_ATTENTION: "Architecture 2: squeeze-and-excitation attention on the three depth levels, no Inception",
    T.ARCH_INCEPTION_ATTENTION: "Architecture 3: Architecture 1 with SE attention inside every Inception branch",
    T.ARCH_INCEPTION_REFINE: "Architecture 4: Architecture 1 with the deepest level decoded by bicubic upsample plus depthwise refinement",
}
CLASS_NAME = {
    "P1_COC": "Cavity Off Center",
    "P1_FL": "Folded Lens",
    "P1_ML": "Multiple Lenses",
    "P1_MPP": "Missing Primary Package",
    "P1_NL": "Missing Lens",
}
ORDER = [T.ARCH_RESNET50, T.ARCH_MULTISCALE, T.ARCH_MULTILVL_ATTENTION,
         T.ARCH_INCEPTION_ATTENTION, T.ARCH_INCEPTION_REFINE]
THRESHOLDS = [0.5, 0.3, 0.2, 0.1]

HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")
TITLE = Font(bold=True, size=12)


def load():
    data = {}
    for arch in ORDER:
        d = RUN / ("%s_20260929" % arch)
        m = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
        npz = np.load(d / "test_predictions.npz", allow_pickle=False)
        hist = []
        with open(d / "history.csv", newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                hist.append((int(row["epoch"]), float(row["train_loss"]), float(row["seconds"])))
        data[arch] = {"m": m, "tm": m["test_metrics"], "timing": m["timing"],
                      "y_true": npz["y_true"].astype(int), "y_score": npz["y_score"],
                      "hist": hist}
    return data


def write_sheet(ws, title, header, rows, widths, caption=""):
    r = 1
    ws.cell(row=r, column=1, value=title).font = TITLE
    r += 2
    if caption:
        for line in caption.split("\n"):
            ws.cell(row=r, column=1, value=line)
            r += 1
        r += 1
    for c, name in enumerate(header, start=1):
        cell = ws.cell(row=r, column=c, value=name)
        cell.font = Font(bold=True)
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    r += 1
    for row in rows:
        for c, value in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=value)
        r += 1
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return r


def main():
    data = load()
    wb = Workbook()

    ws = wb.active
    ws.title = "Sweep summary"
    rows = []
    for arch in ORDER:
        tm = data[arch]["tm"]
        ti = data[arch]["timing"]
        rows.append([
            SHORT[arch], ARCH_NOTE[arch], data[arch]["m"]["params_total"],
            tm["macro_auprc"], tm["macro_f1"], tm["micro_precision"], tm["micro_recall"],
            tm["hamming_loss"], tm["exact_match_ratio"],
            ti["inference_ms_per_image_cold"], ti["inference_ms_per_image_steady_median"],
            ti["train_seconds_total"], ti["train_seconds_per_epoch_mean"],
        ])
    write_sheet(
        ws, "Multi-label architecture sweep, test set of 677 images",
        ["Architecture", "What it is", "Parameters", "Macro AUPRC", "Macro F1",
         "Micro precision", "Micro recall", "Hamming loss", "Exact match",
         "Inference ms/image (no warmup)", "Inference ms/image (repeats, for reference)",
         "Training time (s)", "Training s/epoch"],
        rows, [34, 62, 12, 11, 10, 11, 11, 11, 11, 16, 18, 13, 11],
        caption=("Five models, same data, same split, same recipe, one at a time on one GPU.\n"
                 "Metrics at threshold 0.5. Macro AUPRC is the metric of record.\n"
                 "The inference figure to read is the no-warmup one: the first pass over the test set\n"
                 "as it comes, with no warmup pass of any kind, so one-time costs are inside it.\n"
                 "Folded Lens, the question that started this, is on the next sheet."))

    ws = wb.create_sheet("Folded Lens")
    rows = []
    for arch in ORDER:
        d = data[arch]
        j = T.LP_TAGS.index("P1_FL")
        pc = d["tm"]["per_class"]["P1_FL"]
        line = [SHORT[arch], pc["support"], pc["tp"], pc["fp"], pc["fn"], pc["tn"],
                pc["precision"], pc["recall"], pc["f1"], pc["auprc"]]
        for th in THRESHOLDS:
            pred = (d["y_score"][:, j] >= th).astype(int)
            line.append(int(((d["y_true"][:, j] == 1) & (pred == 1)).sum()))
        rows.append(line)
    write_sheet(
        ws, "Folded Lens: does any architecture lift the weak class?",
        ["Architecture", "Images with Folded Lens", "Correctly found", "Fired wrongly",
         "Missed", "Correctly not fired", "Precision", "Recall", "F1", "AUPRC"]
        + ["Found at 0.5", "Found at 0.3", "Found at 0.2", "Found at 0.1"],
        rows, [34, 13, 13, 12, 9, 14, 10, 10, 9, 9, 11, 11, 11, 11],
        caption=("Folded Lens is the class that fails: in this data every Folded Lens picture also carries\n"
                 "Multiple Lenses, so a model can learn the co-occurrence and never fire the separate\n"
                 "Folded Lens output. The last four columns lower the decision threshold on the Folded Lens\n"
                 "score only, read from the saved scores, and show how much signal is in the scores.\n"
                 "The threshold drop is a reading of the model, not a second model."))

    ws = wb.create_sheet("Per class")
    rows = []
    for arch in ORDER:
        for tag in T.LP_TAGS:
            pc = data[arch]["tm"]["per_class"][tag]
            rows.append([SHORT[arch], "%s (%s)" % (CLASS_NAME[tag], tag), pc["support"],
                         pc["tp"], pc["fp"], pc["fn"], pc["tn"], pc["precision"],
                         pc["recall"], pc["f1"], pc["auprc"]])
    write_sheet(
        ws, "Every class, every architecture",
        ["Architecture", "Class", "Images with the class", "Correctly found", "Fired wrongly",
         "Missed", "Correctly not fired", "Precision", "Recall", "F1", "AUPRC"],
        rows, [34, 28, 13, 13, 12, 9, 14, 10, 10, 9, 9],
        caption=("Four of the five classes sit at or near ceiling for every model, so the whole table\n"
                 "turns on Folded Lens. AUPRC is the area under the precision-recall curve for that class,\n"
                 "which is the fair summary when one class has far fewer examples than another."))

    ws = wb.create_sheet("Timing")
    rows = []
    for arch in ORDER:
        t = data[arch]["timing"]
        rows.append([SHORT[arch], data[arch]["m"]["params_total"], t["device"], t["batch"],
                     t["images"], t["inference_ms_per_image_cold"], t["inference_total_seconds_cold"],
                     t["inference_first_batch_ms_cold"], t["inference_ms_per_image_steady_median"],
                     " / ".join("%.2f" % v for v in t["inference_ms_per_image_steady_repeats"]),
                     t["model_only_ms_per_image_warm"], t["train_seconds_total"],
                     t["train_seconds_per_epoch_mean"], t["amp"], t["warmup_used"]])
    write_sheet(
        ws, "Training and inference time",
        ["Architecture", "Parameters", "Device", "Batch", "Images",
         "Inference ms/image (no warmup)", "Inference total (s, no warmup)",
         "First batch (ms, no warmup)", "Inference ms/image (repeat median)",
         "Repeat values", "Forward only ms/image (warmed)", "Training time (s)",
         "Training s/epoch", "Mixed precision", "Warmup used"],
        rows, [34, 12, 24, 7, 8, 16, 14, 14, 15, 24, 14, 14, 12, 11, 9],
        caption=("No warmup anywhere: the headline inference number is the first pass over the test set,\n"
                 "so library and one-time costs are inside it. The repeat median and the forward-only\n"
                 "column are given only so the numbers can be read against earlier runs that used warmup;\n"
                 "they are not the headline. Training time is the sum of the 50 epoch times.\n"
                 "One model ran on the GPU at a time, so the timings are not sharing the device."))

    ws = wb.create_sheet("Epoch history")
    rows = []
    for arch in ORDER:
        for epoch, loss, secs in data[arch]["hist"]:
            rows.append([SHORT[arch], epoch, loss, secs])
    write_sheet(ws, "Per-epoch training loss",
                ["Architecture", "Epoch", "Training loss", "Seconds"],
                rows, [34, 8, 14, 10],
                caption="50 epochs, fixed schedule, no early stopping (the split is two-way: train and test only).")

    ws = wb.create_sheet("Method")
    lines = [
        "What ran",
        "",
        "One single-label run per architecture: five models, all on the same 3,377 lens-presentation images,",
        "the same frozen 80/20 split, and the same training recipe. The only difference between any two rows",
        "is the architecture.",
        "",
        "The question this answers is the lead's: does the MultiLevel MultiScale architecture lift Folded Lens",
        "recall. The four architectures are the four in the architecture notebook; the plain ResNet50 is the",
        "control, re-run in the same session so every row shares one device, one session and one recipe.",
        "",
        "Recipe (identical for all five)",
        "",
        "  Input               224x224, ImageNet-pretrained backbone, no augmentation",
        "  Head                the notebook's own fully connected head; the final output is 5 independent",
        "                      scores (one per lens-presentation condition), not a single-answer softmax,",
        "                      because one picture can carry more than one condition",
        "  Loss                binary cross-entropy over the 5 outputs",
        "  Optimizer           SGD, learning rate 1e-4, momentum 0.9, Nesterov, no warmup schedule",
        "  Epochs 50, batch 8, seed 42, fixed schedule, no early stopping",
        "  Split               two-way 80/20 (2,700 train, 677 test), grouped by image content hash so the",
        "                      same picture can never appear on both sides",
        "",
        "How to read the table",
        "",
        "1. Macro AUPRC is the metric of record. Accuracy is meaningless here: 2 of the 5 classes carry",
        "   most of the labels.",
        "2. Four classes are at ceiling for every model, so any difference between rows is Folded Lens.",
        "3. One seed per row. Nothing here separates a small architecture difference from run-to-run",
        "   variation; only a clear, repeated pattern should be read as an architecture effect.",
        "4. Folded Lens never appears alone in this data: all 178 images that carry it also carry",
        "   Multiple Lenses. A model can therefore learn the pair and never fire the separate Folded",
        "   Lens output, which is what the baseline does. No architecture change removes that structure;",
        "   it is a property of how the data was annotated.",
        "5. The port. The four architectures were written for another framework and were rebuilt here for",
        "   the training framework actually used. Every filter count, tap, fusion width and head layer is",
        "   the notebook's; the only change is the final layer, which is 5 scores instead of a softmax",
        "   over the notebook's class count. The rebuild was checked by parameter count against the",
        "   notebook's own models as built earlier in the other framework: the four agree to the last",
        "   parameter once the two frameworks' known counting differences are accounted for.",
    ]
    r = 1
    for line in lines:
        ws.cell(row=r, column=1, value=line)
        r += 1
    ws.column_dimensions["A"].width = 110

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
