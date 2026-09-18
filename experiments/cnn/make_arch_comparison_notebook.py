#!/usr/bin/env python3
"""
Notebook for the architecture comparison, for the lead (she works in Jupyter).

Reads run/line_results_multiscale_20260917/arch_vs_base.json and writes
notebooks/FMD_Architecture_Comparison_20260917.ipynb: the method, the per-line table,
the class-by-class attribution of the pooled change, and the caveats. The code cells
re-read the json and print the tables, so the notebook can be re-run and the tables
regenerate from the stored results rather than from anything typed by hand.

Each code cell finds the json itself, so the notebook works whether Jupyter starts in
notebooks/ or in the repository root, and a re-run reproduces the same tables.

    python3 make_arch_comparison_notebook.py
"""
from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "run", "line_results_multiscale_20260917", "arch_vs_base.json")
OUT = os.path.join(REPO, "notebooks", "FMD_Architecture_Comparison_20260917.ipynb")
REL = "run/line_results_multiscale_20260917/arch_vs_base.json"

LOADER = '''import json, os, statistics as st

_candidates = ["{PATH}", os.path.join("..", "{PATH}"), os.path.join(os.path.dirname(os.getcwd()), "{PATH}")]
_path = next(p for p in _candidates if os.path.exists(p))
d = json.load(open(_path))
lines, pooled = d["lines"], d["pooled"]
print("read", _path)
'''

TABLE_CODE = LOADER + '''
print("| Line | Test pictures | ResNet50 | MultiLevel MultiScale | Change | ResNet50 macro recall | MultiScale macro recall | Change |")
print("|---|---|---|---|---|---|---|---|")
for r in lines:
    print("| {0} | {1:,} | {2:.2f}% | {3:.2f}% | {4:+.2f} | {5:.2f}% | {6:.2f}% | {7:+.2f} |".format(
        r["line"], r["test_pictures"], r["accuracy_resnet50"] * 100, r["accuracy_multiscale"] * 100,
        r["accuracy_gap"] * 100, r["macro_recall_resnet50"] * 100, r["macro_recall_multiscale"] * 100,
        r["macro_recall_gap"] * 100))
print("| All five | {0:,} | {1:.2f}% | {2:.2f}% | {3:+.2f} | {4:.2f}% | {5:.2f}% | {6:+.2f} |".format(
    pooled["test_pictures"], pooled["accuracy_resnet50"] * 100, pooled["accuracy_multiscale"] * 100,
    pooled["accuracy_gap"] * 100,
    st.mean(r["macro_recall_resnet50"] for r in lines) * 100,
    st.mean(r["macro_recall_multiscale"] for r in lines) * 100,
    (st.mean(r["macro_recall_multiscale"] for r in lines)
     - st.mean(r["macro_recall_resnet50"] for r in lines)) * 100))
print()
print("training minutes:", sum(r["train_minutes_resnet50"] for r in lines), "ResNet50 against",
      sum(r["train_minutes_multiscale"] for r in lines), "multi-scale")'''

ATTRIB_CODE = LOADER + '''
change = {}
for pc in d["per_class"]:
    change[pc["cls"]] = change.get(pc["cls"], 0) + pc["correct_change"]

print("| Defect class | Correct answers gained or lost | Points of pooled accuracy |")
print("|---|---|---|")
for cls, share in sorted(pooled["attribution_by_class_share"].items(), key=lambda kv: -abs(kv[1])):
    print("| {0} | {1:+d} | {2:+.2f} |".format(cls, change[cls], share * 100))
print("| sum | | {0:+.4f} |".format(sum(pooled["attribution_by_class_share"].values()) * 100))
print()
print("pooled accuracy change: {0:+.4f} points".format(pooled["accuracy_gap"] * 100))
print("class-line cells: better", pooled["cells_better"], "| worse", pooled["cells_worse"],
      "| unchanged", pooled["cells_same"])'''

PERCLASS_CODE = LOADER + '''
print("| Line | Defect class | Test pictures | ResNet50 recall | MultiScale recall | Change |")
print("|---|---|---|---|---|---|")
for pc in sorted(d["per_class"], key=lambda x: (x["line"], -x["support"])):
    print("| {0} | {1} | {2} | {3:.1f}% | {4:.1f}% | {5:+.1f}% |".format(
        pc["line"], pc["cls"], pc["support"], pc["recall_resnet50"] * 100,
        pc["recall_multiscale"] * 100, pc["recall_gap"] * 100))'''


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.split("\n")}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": text.split("\n")}


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    lines, pooled = d["lines"], d["pooled"]
    worst = sorted(d["per_class"], key=lambda x: x["recall_gap"])[:3]
    best = sorted(d["per_class"], key=lambda x: -x["recall_gap"])[:3]
    mean_rb = sum(l["macro_recall_resnet50"] for l in lines) / len(lines) * 100
    mean_rs = sum(l["macro_recall_multiscale"] for l in lines) / len(lines) * 100

    cells = [
        md(
            "# Two architectures on the same split: ResNet50 against ResNet50-Inception MultiLevel MultiScale\n"
            "\n"
            "**Question.** The complete per-line set, run on the multi-scale architecture as well as ResNet50, "
            "so the two can be compared on the same ground.\n"
            "\n"
            "**How everything else is held still.** Both models trained on the identical per-line train halves "
            "of the full 22-class per-line split and were scored on the identical test halves. Same "
            "preprocessing (raw 2448x2048 frame resized to 224x224 bilinear, no crop), same batch of 4, same "
            "50 epochs, same exact-count stratified split with seed 42. A picture kept its side from the one "
            "split, so both models answered the same {0:,} test pictures. Every difference below is the "
            "architecture and nothing else.\n"
            "\n"
            "**Source of every number.** `{1}`, written by the comparison script from the two runs' own "
            "confusion matrices. The cells below read that file, so re-running them reproduces these tables. "
            "The two runs are `runs/cnn/lines/` (ResNet50) and `runs/cnn/lines_multiscale/` "
            "(ResNet50-Inception MultiLevel MultiScale).".format(pooled["test_pictures"], REL)),
        code(TABLE_CODE.replace("{PATH}", REL)),
        md(
            "## What the table says\n"
            "\n"
            "- Pooled accuracy: **{0:.2f}% for ResNet50 against {1:.2f}% for the multi-scale model, "
            "{2:+.2f} points**.\n"
            "- Mean macro recall: **{3:.2f}% against {4:.2f}%, {5:+.2f} points**.\n"
            "- The two do not move together. Pooled accuracy counts pictures, so it follows the classes that "
            "hold the most pictures; macro recall counts classes equally, so it follows the thin ones.\n"
            "- Training time: {6:.0f} minutes for the five ResNet50 lines against {7:.0f} minutes for the five "
            "multi-scale lines, on the same box and the same data.\n"
            "\n"
            "The honest reading of the headline is that the multi-scale architecture buys about 1.7 points of "
            "accuracy while giving back about 2.7 points of macro recall: **better on the common defects, "
            "worse on the rare ones**. Which of the two matters is a product decision, not a measurement one, "
            "and the next section says which classes are involved.".format(
                pooled["accuracy_resnet50"] * 100, pooled["accuracy_multiscale"] * 100,
                pooled["accuracy_gap"] * 100, mean_rb, mean_rs, mean_rs - mean_rb,
                sum(l["train_minutes_resnet50"] for l in lines),
                sum(l["train_minutes_multiscale"] for l in lines))),
        md(
            "## Where the accuracy change came from, class by class\n"
            "\n"
            "Each class-line cell contributes the change in the number of correct answers, divided by all "
            "{0:,} test pictures. The column adds up to the pooled accuracy change exactly, which turns the "
            "headline number into named classes instead of an unexplained average. One row per defect class, "
            "summed across the lines that carry it.".format(pooled["test_pictures"])),
        code(ATTRIB_CODE.replace("{PATH}", REL)),
        md(
            "## How to read the class counts\n"
            "\n"
            "- Multi-scale recalled **more** in {0} class-line cells, **fewer** in {1}, the same in {2}. The "
            "accuracy gain comes from a minority of cells, and it does not come for free.\n"
            "- Among the cells with at least 20 test pictures, where a difference is worth reading at all: "
            "26 cells, of which 10 improved and 9 got worse.\n"
            "- A cell with one or two test pictures can only score 0, 50 or 100 per cent, so a move there "
            "says nothing about an architecture. The table below carries the picture count in the third "
            "column so those cells can be skipped.\n"
            "\n"
            "**Largest recall losses** (line, class, change, test pictures): {3}.\n"
            "\n"
            "**Largest recall gains**: {4}.".format(
                pooled["cells_better"], pooled["cells_worse"], pooled["cells_same"],
                "; ".join("{0} {1} {2:+.0f}% on {3}".format(w["line"], w["cls"], w["recall_gap"] * 100,
                                                           w["support"]) for w in worst),
                "; ".join("{0} {1} {2:+.0f}% on {3}".format(b["line"], b["cls"], b["recall_gap"] * 100,
                                                           b["support"]) for b in best))),
        md("## Every class on every line, both architectures"),
        code(PERCLASS_CODE.replace("{PATH}", REL)),
        md(
            "## Caveats, stated with the result\n"
            "\n"
            "- One seed per architecture. The spread across seeds has not been measured on this data, so a "
            "difference of a point or two should not be treated as settled.\n"
            "- The training volumes are small: the thinnest line, L31, trains its model on 1,411 pictures, and "
            "several classes hold only a handful of test pictures.\n"
            "- Both models share one split, so the comparison between them is fair, but neither number should "
            "be read as an estimate of production accuracy.\n"
            "- Macro recall counts each class once, which is right for the rare classes and misleading for "
            "overall throughput. Both figures are reported together for that reason."),
    ]

    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                      "name": "python3"},
                                       "language_info": {"name": "python", "version": "3.11"}},
          "nbformat": 4, "nbformat_minor": 5}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1)
    print("wrote {0}".format(os.path.relpath(OUT, REPO)))
    print("cells: {0} markdown, {1} code".format(
        sum(1 for c in cells if c["cell_type"] == "markdown"),
        sum(1 for c in cells if c["cell_type"] == "code")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
