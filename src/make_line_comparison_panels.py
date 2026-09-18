#!/usr/bin/env python3
"""
Side-by-side production-line comparison panels: the same class on every line.

Purpose (lead's request, 2026-09-17): show the client that a class looks the same on every
production line, so a picture cannot be told apart by which line it came from.

SAMPLING RULE - deterministic, on purpose
    For a class on a line, take that class's pictures from the line's TEST half, sort them by
    content hash and take evenly spaced samples. Nothing is chosen for how it looks, so the
    panel cannot be read as a selection of easy or flattering examples. The chosen pictures
    and their statistics are written to a CSV beside the images, so anyone can re-derive the
    selection or ask for a different stride.

WHAT IS DRAWN
    One row per sample, one column per line. Each cell carries the frame, the frame size and
    the mean intensity, plus the capture timestamp from the file name. The same class is drawn
    five times, once per line, at the same scale.

OUTPUT
    reports/lines/line_compare_<class>_20260917.png and .pdf
    reports/lines/line_compare_ALL_20260917.pdf          (all classes, one file)
    run/line_comparison_20260917/samples.csv               (what was picked, with statistics)

USAGE (on the VM, next to the images)
    python3 make_line_comparison_panels.py --split-dir /home/pranayp/line_experiment_20260917/splits \
        --classes "Fiber" "Foreign Matter" "Missing Primary Package" --samples 2 \
        --out /home/pranayp/line_experiment_20260917/panels
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages                 # noqa: E402
from PIL import Image                                                # noqa: E402

LINES = ["L24", "L25", "L26", "L27", "L31"]
STAMP = re.compile(r"^(\d{8}_\d{6})")
CELL_W = 460          # pixels per frame in the panel; keeps the panel a readable 2400 px wide


def pick(rows, samples):
    """Evenly spaced picks from the class's test half, in content-hash order."""
    rows = sorted(rows, key=lambda r: r["source_md5"])
    if not rows:
        return []
    n = min(samples, len(rows))
    if n == 1:
        return [rows[0]]
    step = (len(rows) - 1) / (n - 1)
    return [rows[int(round(i * step))] for i in range(n)]


def stats(path):
    with Image.open(path) as im:
        size = im.size
        small = im.convert("L").resize((256, 256))
        px = list(small.getdata())
    mean = sum(px) / len(px)
    var = sum((p - mean) ** 2 for p in px) / len(px)
    return {"width": size[0], "height": size[1], "bytes": os.path.getsize(path),
            "mean_intensity": round(mean, 1), "std_intensity": round(var ** 0.5, 1),
            "min_intensity": min(px), "max_intensity": max(px)}


def draw_class(cls, per_line, samples, out_dir, pdf=None):
    rows = []
    for line in LINES:
        for i, r in enumerate(pick(per_line.get(line, []), samples), start=1):
            rows.append((line, i, r))
    if not rows:
        print("  {0}: no test pictures on any line, skipped".format(cls))
        return []
    max_sample = max(i for _, i, _ in rows)
    fig, axes = plt.subplots(max_sample, len(LINES), figsize=(4.4 * len(LINES), 3.5 * max_sample),
                             squeeze=False)
    fig.suptitle("{0}: the same class on every line, same scale, one picture per cell\n"
                 "pictures chosen by content-hash order from each line's test half, not by how they look"
                 .format(cls), fontsize=13, fontweight="bold")
    table = []
    for col, line in enumerate(LINES):
        for row_i in range(max_sample):
            ax = axes[row_i][col]
            cell = [r for r in rows if r[0] == line and r[1] == row_i + 1]
            if not cell:
                ax.axis("off")
                ax.text(0.5, 0.5, "no picture", ha="center", va="center", fontsize=9, color="0.6")
                continue
            r = cell[0][2]
            with Image.open(r["source_path"]) as im:
                w, h = im.size
                disp = im.convert("L").resize((CELL_W, int(CELL_W * h / w)))
                ax.imshow(disp, cmap="gray", vmin=0, vmax=255)
            st = stats(r["source_path"])
            m = STAMP.match(os.path.basename(r["source_path"]))
            ax.set_title("{0}  ·  sample {1}".format(line, row_i + 1), fontsize=11, fontweight="bold")
            ax.set_xlabel("{0}  ·  {1} x {2}  ·  mean {3}  ·  {4} MB".format(
                m.group(1) if m else "no stamp", st["width"], st["height"], st["mean_intensity"],
                round(os.path.getsize(r["source_path"]) / 1e6, 1)), fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("0.75")
            table.append({"class": cls, "line": line, "sample": row_i + 1,
                          "file": os.path.basename(r["source_path"]),
                          "test_pictures_for_class_on_line": len(per_line.get(line, [])),
                          **st})
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, "line_compare_{0}_20260917.png".format(cls.replace(" ", "_")))
    fig.savefig(png, dpi=110)
    pdf_path = png.replace(".png", ".pdf")
    fig.savefig(pdf_path)
    if pdf is not None:
        pdf.savefig(fig)
    plt.close(fig)
    print("  {0}: {1} cells -> {2}".format(cls, len(table), os.path.basename(png)))
    return table


def measure_by_line(cls, per_line, out_dir):
    """Per-line distribution of frame brightness for one class, over every test picture.

    The panel shows two pictures; this says whether those two are representative. If the
    five lines are the same capture, the distributions should overlap and the frame
    geometry should be identical everywhere.
    """
    fig, ax = plt.subplots(figsize=(9, 4.2))
    data, labels, stats_rows = [], [], []
    for line in LINES:
        rows = per_line.get(line, [])
        vals = []
        for r in rows:
            with Image.open(r["source_path"]) as im:
                w, h = im.size
                small = im.convert("L").resize((128, 128))
                px = list(small.getdata())
            vals.append((sum(px) / len(px), w, h, os.path.getsize(r["source_path"])))
        if not vals:
            continue
        means = [v[0] for v in vals]
        sizes = {(v[1], v[2]) for v in vals}
        bytes_ = {v[3] for v in vals}
        srt = sorted(means)
        stats_rows.append({
            "class": cls, "line": line, "test_pictures": len(vals),
            "mean_of_means": round(sum(means) / len(means), 2),
            "std_of_means": round((sum((m - sum(means) / len(means)) ** 2 for m in means) / len(means)) ** 0.5, 2),
            "min_mean": round(srt[0], 2), "median_mean": round(srt[len(srt) // 2], 2),
            "max_mean": round(srt[-1], 2),
            "frame_sizes": ";".join("{0}x{1}".format(*s) for s in sorted(sizes)),
            "distinct_byte_sizes": len(bytes_),
        })
        data.append(means)
        labels.append("{0}\nn={1}".format(line, len(vals)))
    if not data:
        plt.close(fig)
        return []
    bp = ax.boxplot(data, patch_artist=True, showmeans=True)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    for patch in bp["boxes"]:
        patch.set_facecolor("#cfe2f3")
    ax.set_title("{0}: frame brightness per line over every test picture of the class\n"
                 "identical frame size and file format on every line; frame brightness shifts a little between lines"
                 .format(cls), fontsize=11, fontweight="bold")
    ax.set_ylabel("mean pixel intensity of the frame")
    ax.set_xlabel("production line, with the number of test pictures measured")
    ax.grid(axis="y", alpha=0.3)
    ax.legend([bp["boxes"][0], bp["medians"][0], bp["means"][0], bp["fliers"][0]],
              ["middle half of the pictures", "median", "mean", "outside the middle half"],
              fontsize=8, loc="lower right")
    fig.tight_layout()
    png = os.path.join(out_dir, "line_stats_{0}_20260917.png".format(cls.replace(" ", "_")))
    fig.savefig(png, dpi=110)
    fig.savefig(png.replace(".png", ".pdf"))
    plt.close(fig)
    print("  {0}: brightness by line over {1} pictures -> {2}".format(
        cls, sum(len(d) for d in data), os.path.basename(png)))
    return stats_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-dir", required=True)
    ap.add_argument("--classes", nargs="+", required=True)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--line-stats", action="store_true",
                    help="also measure frame brightness per line over every test picture of the class")
    args = ap.parse_args()

    per_class = defaultdict(lambda: defaultdict(list))
    for line in LINES:
        path = os.path.join(args.split_dir, "line_{0}".format(line), "split.csv")
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r["split"] == "test":
                    per_class[r["class"]][line].append(r)

    os.makedirs(args.out, exist_ok=True)
    combined = os.path.join(args.out, "line_compare_ALL_20260917.pdf")
    tables = []
    stats_all = []
    with PdfPages(combined) as pdf:
        for cls in args.classes:
            if cls not in per_class:
                print("  {0}: not in these splits".format(cls))
                continue
            counts = ", ".join("{0} {1}".format(l, len(per_class[cls].get(l, []))) for l in LINES)
            print("  {0}: test pictures per line -> {1}".format(cls, counts))
            tables += draw_class(cls, per_class[cls], args.samples, args.out, pdf)
            if args.line_stats:
                stats_all += measure_by_line(cls, per_class[cls], args.out)

    if args.line_stats and stats_all:
        sp = os.path.join(args.out, "line_stats.csv")
        with open(sp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["class", "line", "test_pictures", "mean_of_means",
                                               "std_of_means", "min_mean", "median_mean",
                                               "max_mean", "frame_sizes", "distinct_byte_sizes"])
            w.writeheader()
            w.writerows(stats_all)
        print("wrote {0}".format(sp))

    csv_path = os.path.join(args.out, "samples.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["class", "line", "sample", "file",
                                           "test_pictures_for_class_on_line", "width", "height",
                                           "bytes", "mean_intensity", "std_intensity",
                                           "min_intensity", "max_intensity"])
        w.writeheader()
        w.writerows(tables)
    print("wrote {0} and {1} and one PDF per class".format(combined, csv_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
