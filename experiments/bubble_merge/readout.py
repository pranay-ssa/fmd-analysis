#!/usr/bin/env python3
"""Merged-versus-separate readout for Task 1 (wayfinder ticket 005).

Reads the four finished runs' metrics.json, confusion.json and
predictions.csv and writes one report that answers the question the readout
rule in registry.json fixes before running:

  * per architecture, the merged variant against the separate variant on the
    identical test pictures: overall accuracy, macro F1, per-class precision
    / recall / F1 / support;
  * the Bubble family (185 pictures, 55 in test) pooled across the four
    separate classes against the single merged Bubble class;
  * if the merged Bubble reads worse, the class responsible, named from the
    confusion cells in both readings: which class absorbs the merged Bubble
    pictures, and whose pictures get predicted as Bubble.

Pure Python (csv/json only), so it runs locally on pulled artifacts and on
the VM alike. Usage:

    python readout.py --runs <dir> --labels <labels.csv> --out <report.md>

where <dir> holds one subdirectory per run id containing the three artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import os

FAMILY = ["Bubble", "Bubble On 123", "Bubble On Edge", "Bubble Irregular"]
RUNS = [
    ("bubble_merge_resnet50_separate", "ResNet50", "separate"),
    ("bubble_merge_resnet50_merged", "ResNet50", "merged"),
    ("bubble_merge_multiscale_separate", "MultiScale", "separate"),
    ("bubble_merge_multiscale_merged", "MultiScale", "merged"),
]
# Single-run noise band for macro F1, measured on this project's line models
# (same config, same seed, new session): 0.037. Quoted beside every delta.
NOISE_BAND_MACRO_F1 = 0.037


def load_run(runs_dir, run_id):
    d = os.path.join(runs_dir, run_id)
    out = {"id": run_id, "dir": d}
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as fh:
        out["metrics"] = json.load(fh)
    with open(os.path.join(d, "confusion.json"), encoding="utf-8") as fh:
        out["confusion"] = json.load(fh)
    pred = os.path.join(d, "predictions.csv")
    out["predictions"] = []
    if os.path.exists(pred):
        with open(pred, newline="", encoding="utf-8") as fh:
            out["predictions"] = list(csv.DictReader(fh))
    return out


def prf(matrix, idx):
    tp = matrix[idx][idx]
    col = sum(matrix[r][idx] for r in range(len(matrix)))
    row = sum(matrix[idx])
    p = tp / col if col else 0.0
    r = tp / row if row else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f, row


def family_stats(run, names):
    """Pool the four separate classes (or the one merged class) over the
    bubble-family test pictures of this run's own labelling."""
    cm = run["confusion"]
    cls = cm["class_names"]
    mat = cm["matrix"]
    idx = [i for i, c in enumerate(cls) if c in names]
    if not idx:
        return None
    tp = sum(mat[i][i] for i in idx)            # exact-class hits
    support = sum(sum(mat[i]) for i in idx)
    in_family = sum(mat[r][c] for r in range(len(cls)) for c in idx
                    if r in idx)                # predicted as any member
    pred_as = sum(mat[r][i] for r in range(len(cls)) for i in idx)
    correct = tp
    return {"support": support, "exact_correct": correct,
            "family_correct": in_family,
            "precision": correct / pred_as if pred_as else 0.0,
            "recall": correct / support if support else 0.0,
            "family_recall": in_family / support if support else 0.0,
            "per_class": {cls[i]: prf(mat, i) for i in idx}}


def top_confusions(run, cls_name, limit=5):
    cm = run["confusion"]
    cls = cm["class_names"]
    if cls_name not in cls:
        return []
    i = cls.index(cls_name)
    row = [(cm["matrix"][i][j], cls[j]) for j in range(len(cls))]
    row = [(n, c) for n, c in row if n > 0 and c != cls_name]
    row.sort(reverse=True)
    return row[:limit]


def leaks_into(run, cls_name, limit=5):
    """Which classes' pictures are predicted as cls_name."""
    cm = run["confusion"]
    cls = cm["class_names"]
    if cls_name not in cls:
        return []
    j = cls.index(cls_name)
    col = [(cm["matrix"][i][j], cls[i]) for i in range(len(cls))]
    col = [(n, c) for n, c in col if n > 0 and c != cls_name]
    col.sort(reverse=True)
    return col[:limit]


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100.0 * x)


def pair_block(name, sep, mrg):
    lines = []
    sm, mm = sep["metrics"], mrg["metrics"]
    d_acc = mm["overall_accuracy"] - sm["overall_accuracy"]
    d_f1 = mm["macro"]["f1"] - sm["macro"]["f1"]
    lines.append("| metric | separate | merged | delta |")
    lines.append("|---|---|---|---|")
    lines.append("| test pictures | %d | %d | %d |"
                 % (sm["num_test_images"], mm["num_test_images"],
                    mm["num_test_images"] - sm["num_test_images"]))
    lines.append("| classes | %d | %d | %d |"
                 % (sm["num_classes"], mm["num_classes"],
                    mm["num_classes"] - sm["num_classes"]))
    lines.append("| overall accuracy | %.4f | %.4f | %+.4f |"
                 % (sm["overall_accuracy"], mm["overall_accuracy"], d_acc))
    lines.append("| macro F1 | %.4f | %.4f | %+.4f |"
                 % (sm["macro"]["f1"], mm["macro"]["f1"], d_f1))
    lines.append("| macro F1 noise band | | | +/-%.3f |"
                 % NOISE_BAND_MACRO_F1)
    lines.append("")
    # Bubble family, pooled
    fs = family_stats(sep, FAMILY)
    fm = family_stats(mrg, ["Bubble"])
    lines.append("Bubble family on the identical test pictures (family "
                 "recall = predicted as any member of the merged family; "
                 "in the merged view the family is the single Bubble "
                 "class):")
    lines.append("")
    lines.append("| reading | classes pooled | support | exact correct "
                 "| exact recall | family recall | precision |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append("| separate | 4 | %d | %d | %s | %s | %s |"
                 % (fs["support"], fs["exact_correct"], pct(fs["recall"]),
                    pct(fs["family_recall"]), pct(fs["precision"])))
    lines.append("| merged | 1 (Bubble) | %d | %d | %s | %s | %s |"
                 % (fm["support"], fm["exact_correct"], pct(fm["recall"]),
                    pct(fm["family_recall"]), pct(fm["precision"])))
    lines.append("")
    return lines, fs, fm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="dir holding the 4 run dirs")
    ap.add_argument("--out", required=True, help="report markdown path")
    ap.add_argument("--labels", default=None,
                    help="labels.csv, for the truth behind the join")
    args = ap.parse_args()

    runs = {}
    missing = []
    for rid, arch, variant in RUNS:
        try:
            runs[rid] = load_run(args.runs, rid)
        except FileNotFoundError:
            missing.append(rid)
    if missing:
        print("MISSING RUNS: %s" % ", ".join(missing))
        return 1

    md = []
    md.append("# Task 1 readout: merged versus separate bubbles")
    md.append("")
    md.append("Generated by `experiments/bubble_merge/readout.py` from the "
              "four runs under `%s`." % args.runs)
    md.append("Test pictures are identical between variants (one shared "
              "70:30 split, seed 42): 3,186 pictures, 7,428 train. The "
              "macro F1 noise band of +/-%.3f is the measured same-seed "
              "re-run band of this project's line models." % NOISE_BAND_MACRO_F1)
    md.append("")

    fam = {}
    for arch, sid, mid in (("ResNet50", "bubble_merge_resnet50_separate",
                            "bubble_merge_resnet50_merged"),
                           ("MultiScale", "bubble_merge_multiscale_separate",
                            "bubble_merge_multiscale_merged")):
        md.append("## %s" % arch)
        md.append("")
        block, fs, fm = pair_block(arch, runs[sid], runs[mid])
        md += block
        fam[arch] = (runs[sid], runs[mid], fs, fm)

    md.append("## Attribution: which class is responsible")
    md.append("")
    for arch in ("ResNet50", "MultiScale"):
        sep, mrg, fs, fm = fam[arch]
        md.append("### %s" % arch)
        md.append("")
        md.append("Merged Bubble pictures lost to other classes "
                  "(merged confusion, row Bubble):")
        for n, c in top_confusions(mrg, "Bubble"):
            md.append("- %d of %d predicted as %s"
                      % (n, fm["support"], c))
        md.append("")
        md.append("Non-bubble pictures swallowed by the merged Bubble "
                  "(column Bubble):")
        for n, c in leaks_into(mrg, "Bubble"):
            md.append("- %s: %d pictures" % (c, n))
        md.append("")
        md.append("Separate reading, where the four bubble classes leak "
                  "(rows of the four):")
        for b in FAMILY:
            for n, c in top_confusions(sep, b):
                md.append("- %s -> %s: %d" % (b, c, n))
        md.append("")

    md.append("## Per-class detail")
    md.append("")
    md.append("| arch | variant | class | support | precision | recall "
              "| f1 |")
    md.append("|---|---|---|---|---|---|---|")
    for arch, sid, mid in (("ResNet50", "bubble_merge_resnet50_separate",
                            "bubble_merge_resnet50_merged"),
                           ("MultiScale", "bubble_merge_multiscale_separate",
                            "bubble_merge_multiscale_merged")):
        for rid, variant in ((sid, "separate"), (mid, "merged")):
            cm = runs[rid]["confusion"]
            for i, c in enumerate(cm["class_names"]):
                p, r, f, s = prf(cm["matrix"], i)
                md.append("| %s | %s | %s | %d | %.3f | %.3f | %.3f |"
                          % (arch, variant, c, s, p, r, f))
    md.append("")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md) + "\n")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
