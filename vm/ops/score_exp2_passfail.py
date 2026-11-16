#!/usr/bin/env python3
"""Score the Experiment 2 detector through the shared pass/fail block.

Inputs are the Experiment 1 lens scores (12 columns) and the YOLO detector's
per-picture class maxima. The object cuts are chosen on validation only; test is
scored once. Both rule variants are reported:

    A  Clear, or Bubble and Bubble Cluster may fire
    B  Clear, or Bubble only; Cluster counts as a fail

The detector AP itself lives in the run's run.json; this script only turns the
detections into picture-level verdicts.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments" / "multilabel_ooi"))
import pass_fail_block as block  # noqa: E402

DET_TO_COL = {
    "Bubble": "class_bubble",
    "Bubble Cluster": "class_bubble_cluster",
    "Wet Package": "class_wet_package",
    "Fiber": "class_fiber",
    "Extraneous Polymer": "class_extraneous_polymer",
    "HEMA": "class_hema",
    "Foreign Matter": "class_foreign_matter",
}
CLASSES = list(DET_TO_COL)


def read_detections(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    out = {}
    for row in rows:
        out[row["md5"].strip()] = row
    return out


def load_split(npz, split: str):
    columns = [str(c) for c in npz["columns"]]
    lens_idx = [columns.index(c) for c in block.LENS]
    obj_idx = {c: columns.index(c) for c in DET_TO_COL.values()}
    return columns, lens_idx, obj_idx


def scores_for(split, npz, dets):
    columns = [str(c) for c in npz["columns"]]
    lens_idx = [columns.index(c) for c in block.LENS]
    scores = npz[f"{split}_score"]
    truth = npz[f"{split}_true"]
    md5s = [str(x) for x in npz[f"{split}_md5"]]
    rows = []
    missing = []
    for i, md5 in enumerate(md5s):
        det = dets.get(md5)
        if det is None:
            missing.append(md5)
            continue
        values = {c: float(scores[i, lens_idx[j]]) for j, c in enumerate(block.LENS)}
        for name, column in DET_TO_COL.items():
            values[column] = float(det[f"{name}_max"])
        rows.append({"md5": md5, "scores": values, "truth": truth[i]})
    if missing:
        raise SystemExit(f"{split}: {len(missing)} pictures missing from detections, first {missing[:3]}")
    return rows


def truth_reading(row_truth, columns):
    fail_idx = [columns.index(c) for c in block.FAIL_COLUMNS if c in columns]
    bubble_idx = [columns.index(c) for c in block.PASS_OBJ if c in columns]
    cluster_i = columns.index("class_bubble_cluster") if "class_bubble_cluster" in columns else None
    bubble_i = columns.index("class_bubble") if "class_bubble" in columns else None
    out = []
    for row in row_truth:
        is_fail = any(row[i] for i in fail_idx)
        is_bubble = any(row[i] for i in bubble_idx)
        cluster_only = bool(cluster_i is not None and bubble_i is not None
                            and row[cluster_i] and not row[bubble_i])
        if is_fail:
            out.append(("fail", False))
        elif is_bubble:
            out.append(("bubble-only", cluster_only))
        else:
            out.append(("clear", False))
    return out


def choose_cut(values, positives, min_positives=10):
    positives = np.asarray(positives, dtype=bool)
    n_pos = int(positives.sum())
    if n_pos < min_positives:
        return 0.5, None, n_pos
    values = np.asarray(values, dtype=float)
    best_f1, best_cut = -1.0, 0.5
    for cut in np.arange(0.99, 0.0, -0.01):
        fires = values >= cut
        tp = int((fires & positives).sum())
        fp = int((fires & ~positives).sum())
        fn = int((~fires & positives).sum())
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
        if f1 > best_f1 + 1e-12:
            best_f1, best_cut = f1, float(cut)
    return round(best_cut, 2), round(best_f1, 4), n_pos


def tally(rows, columns, cuts, cut, rule_b=False):
    verdicts, readings = [], []
    cluster_only = []
    for row in rows:
        if rule_b:
            result = block.decide(
                row["scores"], cuts=cuts, cut=cut,
                pass_columns=["class_bubble"],
                fail_columns=block.FAIL_COLUMNS + ["class_bubble_cluster"],
                object_columns=block.FAIL_OBJ + ["class_bubble_cluster"],
            )
        else:
            result = block.decide(row["scores"], cuts=cuts, cut=cut)
        verdicts.append(result["verdict"])
        readings.append(result["reading"])

    truth, cluster_flags = zip(*truth_reading([r["truth"] for r in rows], columns))
    fail_n = truth.count("fail")
    clear_n = truth.count("clear")
    bubble_n = truth.count("bubble-only")
    cluster_n = sum(1 for x in cluster_flags if x)

    fail_caught = sum(1 for v, t in zip(verdicts, truth) if v == "fail" and t == "fail")
    clear_wrong = sum(1 for v, t in zip(verdicts, truth) if v == "fail" and t == "clear")
    bubble_wrong = sum(1 for v, t in zip(verdicts, truth) if v == "fail" and t == "bubble-only")

    if rule_b:
        bubble_only_only = [i for i, (t, c) in enumerate(zip(truth, cluster_flags))
                            if t == "bubble-only" and not c]
        b_only_n = len(bubble_only_only)
        b_only_passed = sum(1 for i in bubble_only_only if verdicts[i] == "pass")
        cluster_passed = sum(1 for i, c in enumerate(cluster_flags)
                             if c and verdicts[i] == "pass")
        pass_population = clear_n + b_only_n
        passed = (clear_n - clear_wrong) + b_only_passed
        return {
            "rule": "only Bubble passes",
            "population": {"fail": fail_n, "clear": clear_n, "bubble-family": bubble_n,
                           "pass": pass_population, "cluster-only-excluded": cluster_n},
            "fail_pictures_caught": f"{fail_caught} of {fail_n}",
            "clear_passed": f"{clear_n - clear_wrong} of {clear_n}",
            "clear_wrongly_failed": clear_wrong,
            "bubble_only_passed": f"{b_only_passed} of {b_only_n}",
            "cluster_only_passed_unexpectedly": cluster_passed,
            "pictures_passed_overall": f"{passed} of {pass_population}",
        }

    pass_population = clear_n + bubble_n
    passed = (clear_n - clear_wrong) + (bubble_n - bubble_wrong)
    return {
        "rule": "Bubble and Bubble Cluster pass",
        "population": {"fail": fail_n, "clear": clear_n, "bubble-only": bubble_n,
                       "pass": pass_population},
        "fail_pictures_caught": f"{fail_caught} of {fail_n}",
        "clear_passed": f"{clear_n - clear_wrong} of {clear_n}",
        "clear_wrongly_failed": clear_wrong,
        "bubble_only_passed": f"{bubble_n - bubble_wrong} of {bubble_n}",
        "pictures_passed_overall": f"{passed} of {pass_population}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--thresholds", required=True)
    ap.add_argument("--detections-val", required=True)
    ap.add_argument("--detections-test", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    out_dir = Path(args.out) if args.out else run_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    npz = np.load(args.predictions)
    columns = [str(c) for c in npz["columns"]]
    val = scores_for("val", npz, read_detections(Path(args.detections_val)))
    test = scores_for("test", npz, read_detections(Path(args.detections_test)))

    object_cuts, cut_rows = {}, {}
    for name, column in DET_TO_COL.items():
        idx = columns.index(column)
        cut, f1, n_pos = choose_cut(
            [r["scores"][column] for r in val],
            [r["truth"][idx] for r in val],
        )
        object_cuts[column] = cut
        cut_rows[column] = {"cut": cut, "val_f1": f1, "val_positives": n_pos}

    raw = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    lens_cuts = {c: float(raw["per_class"][c]["threshold"]) for c in block.LENS}
    chosen_cuts = {**lens_cuts, **object_cuts}

    result = {
        "source": "Experiment 2 detector, all pictures, validation-chosen object cuts",
        "test_population": {
            "pictures": len(test),
            "fail": sum(1 for r in test if truth_reading([r["truth"]], columns)[0][0] == "fail"),
            "clear": sum(1 for r in test if truth_reading([r["truth"]], columns)[0][0] == "clear"),
            "bubble-only": sum(1 for r in test if truth_reading([r["truth"]], columns)[0][0] == "bubble-only"),
        },
        "object_cut_selection": cut_rows,
        "lens_cuts": lens_cuts,
        "rule_a_0.5": tally(test, columns, {}, 0.5, rule_b=False),
        "rule_a_chosen": tally(test, columns, chosen_cuts, 0.5, rule_b=False),
        "rule_b_0.5": tally(test, columns, {}, 0.5, rule_b=True),
        "rule_b_chosen": tally(test, columns, chosen_cuts, 0.5, rule_b=True),
    }
    text = json.dumps(result, indent=2)
    (out_dir / "passfail_metrics.json").write_text(text + "\n", encoding="utf-8")
    (out_dir / "thresholds_exp2.json").write_text(
        json.dumps({"lens": lens_cuts, "object": object_cuts}, indent=2) + "\n",
        encoding="utf-8",
    )

    with (out_dir / "passfail_test.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["md5", "truth", "rule_a_chosen", "rule_a_driver",
                         "rule_b_chosen", "rule_b_driver"])
        for row in test:
            a = block.decide(row["scores"], cuts=chosen_cuts)
            b = block.decide(
                row["scores"], cuts=chosen_cuts,
                pass_columns=["class_bubble"],
                fail_columns=block.FAIL_COLUMNS + ["class_bubble_cluster"],
                object_columns=block.FAIL_OBJ + ["class_bubble_cluster"],
            )
            truth = truth_reading([row["truth"]], columns)[0][0]
            writer.writerow([row["md5"], truth, a["verdict"], a["driver"],
                             b["verdict"], b["driver"]])

    print(text)
    print(f"\nwrote {out_dir / 'passfail_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
