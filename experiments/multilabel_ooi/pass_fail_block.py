"""The pass/fail block, one rule with two interchangeable object sources.

WHAT THIS IS
------------
The conditional block both next-phase experiments have to end with. The rule is
already decided (docs/decisions/2026-11-04-ooi-class-vs-gate.md):

    a picture PASSES only when it is Clear, or when every column that fires is a
    bubble class (Bubble, Bubble Cluster). Anything else FAILS.

The rule is deliberately not duplicated per phase. Phase 1 (fifteen lens tags plus
the eight object classes, one multi-label head) feeds it the CNN's object columns.
Phase 2 (fifteen lens tags plus one coarse object flag, object classes handed to a
detector) feeds it the detector's class list plus the CNN's lens columns. Same
rule, same cuts, one implementation: that is what makes the two phases comparable.
A second implementation would let the comparison differ by the block rather than
by the model, which is the confound this file exists to prevent.

Column roles
------------
  fail columns   the twelve lens classes + the six object classes that fail a
                 picture (Wet Package, Foreign Matter, Fiber, Extraneous Polymer,
                 HEMA, Surface Groove)
  pass columns   Bubble, Bubble Cluster. They may fire and the picture still passes.

Surface Groove has no pictures in the record and is never a model output; the name
is carried here so the detector adapter can map it if it ever appears.

HOW TO RUN IT
-------------
Reproduce the published point-4 numbers from the saved scores (no GPU, no images,
this laptop):

    .venv/Scripts/python.exe experiments/multilabel_ooi/pass_fail_block.py \
        --predictions run/multilabel_ooi_20261104/combined/predictions.npz \
        --thresholds run/multilabel_ooi_20261104/combined/thresholds.json \
        --split test --mode 0.5

Rule self-test (no artifacts needed):

    .venv/Scripts/python.exe experiments/multilabel_ooi/pass_fail_block.py --selftest

One picture at inference time (the conditional block as it would run in line), with
either source:

    --one '{"P1_ML": 0.91, "class_bubble": 0.99}'            # phase 1, CNN columns
    --one '{"P1_ML": 0.91}' --detections '[{"class":"Bubble","score":0.88}]'   # phase 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LENS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD", "P1_COC",
        "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]

PASS_OBJ = ["class_bubble", "class_bubble_cluster"]
FAIL_OBJ = ["class_wet_package", "class_foreign_matter", "class_fiber",
            "class_extraneous_polymer", "class_hema", "class_surface_groove"]

FAIL_COLUMNS = LENS + FAIL_OBJ
PASS_COLUMNS = PASS_OBJ

# Detector labels (annotation guide names) to the block's column names. Bubble
# Irregular and Stretched Bubble are the same class as Bubble by the frozen rule.
DETECTOR_ALIASES = {
    "Bubble": "class_bubble",
    "Bubble Irregular": "class_bubble",
    "Stretched Bubble": "class_bubble",
    "Bubble Cluster": "class_bubble_cluster",
    "Wet Package": "class_wet_package",
    "Foreign Matter": "class_foreign_matter",
    "Fiber": "class_fiber",
    "Extraneous Polymer": "class_extraneous_polymer",
    "HEMA": "class_hema",
    "HEMA Fragment": "class_hema",
    "Surface Groove": "class_surface_groove",
}

DEFAULT_CUT = 0.5
RULE_ID = "pass = clear-or-bubble-only/v1"


def decide(scores: dict, cuts: dict | None = None, cut: float = DEFAULT_CUT,
           fail_columns: list | None = None, pass_columns: list | None = None,
           object_columns: list | None = None) -> dict:
    """Decide one picture.

    scores: column name -> score in [0, 1]. Missing columns read 0.
    cuts:   column name -> threshold; used where present, else `cut`.
    fail_columns / pass_columns: optional rule variant. Defaults are the rule as
    run in Experiment 1. The only-Bubble variant passes `pass_columns=["class_bubble"]`
    and adds `class_bubble_cluster` to `fail_columns`.
    object_columns: which fired columns count as an object cause. Defaults to
    FAIL_OBJ; the only-Bubble variant adds `class_bubble_cluster`.
    Returns the verdict plus the attribution a reviewer needs: every column that
    fired, which of them caused the fail, and the box/flag provenance.
    """
    cuts = cuts or {}
    fail_columns = FAIL_COLUMNS if fail_columns is None else list(fail_columns)
    pass_columns = PASS_COLUMNS if pass_columns is None else list(pass_columns)
    object_columns = FAIL_OBJ if object_columns is None else list(object_columns)
    fired, cause = [], []
    for column in fail_columns:
        score = float(scores.get(column) or 0.0)
        threshold = float(cuts.get(column, cut))
        if score >= threshold:
            fired.append((column, score, threshold))
            if column in object_columns:
                cause.append(column)
    bubble_fired = [(c, float(scores.get(c) or 0.0), float(cuts.get(c, cut)))
                    for c in pass_columns if float(scores.get(c) or 0.0) >= float(cuts.get(c, cut))]

    verdict = "fail" if fired else "pass"
    # Cause names the object columns first: when an object fails the picture the
    # lens findings are secondary, and the routing question is always the object.
    driver = cause[0] if cause else (fired[0][0] if fired else None)
    if verdict == "pass":
        reading = "clear" if not bubble_fired else "bubble-only"
    else:
        reading = "object" if cause else "lens"

    return {
        "verdict": verdict,
        "reading": reading,
        "driver": driver,
        "fired": [{"column": c, "score": round(s, 4), "cut": t} for c, s, t in fired],
        "bubble_fired": [{"column": c, "score": round(s, 4), "cut": t} for c, s, t in bubble_fired],
        "rule": RULE_ID,
    }


def from_detector(detections, lens_scores: dict | None = None,
                  cuts: dict | None = None, cut: float = DEFAULT_CUT,
                  fail_columns: list | None = None,
                  pass_columns: list | None = None,
                  object_columns: list | None = None) -> dict:
    """Phase 2 adapter: fold a detector's boxes into the same score dict.

    A detection contributes its confidence per class; a class with several boxes
    contributes its highest. Unknown labels are rejected rather than dropped, so a
    renamed class cannot silently stop failing pictures. `lens_scores` comes from
    the CNN in phase 2; in phase 1 pass the CNN's object columns instead and call
    `decide` directly.
    """
    scores = dict(lens_scores or {})
    unknown = []
    for det in detections or []:
        label = det.get("class") or det.get("name")
        column = DETECTOR_ALIASES.get(label)
        if column is None:
            unknown.append(label)
            continue
        scores[column] = max(float(scores.get(column) or 0.0), float(det.get("score") or 0.0))
    if unknown:
        raise ValueError("detector labels not in the guide mapping: " + ", ".join(sorted(set(unknown))))
    return decide(scores, cuts=cuts, cut=cut, fail_columns=fail_columns,
                  pass_columns=pass_columns, object_columns=object_columns)


def load_cuts(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {c: float(v["threshold"]) for c, v in data["per_class"].items()}


def truth_readings(npz) -> tuple[list[str], list[str]]:
    """Truth population per test row, from the saved truth matrix.

    fail: any fail column positive. bubble-only: Bubble or Bubble Cluster positive
    and no fail column. clear: nothing positive. The saved truth carries the
    nineteen model columns; Surface Groove has no pictures, so nothing is lost.
    """
    columns = [str(c) for c in npz["columns"]]
    truth = npz["test_true"]
    fail_idx = [columns.index(c) for c in FAIL_COLUMNS if c in columns]
    bubble_idx = [columns.index(c) for c in PASS_COLUMNS if c in columns]
    readings = []
    for row in truth:
        if any(row[i] for i in fail_idx):
            readings.append("fail")
        elif any(row[i] for i in bubble_idx):
            readings.append("bubble-only")
        else:
            readings.append("clear")
    return readings, columns


def load_arm(predictions: Path, thresholds: Path | None, split: str, mode: str):
    """One arm's columns, scores, truth and cuts, from the saved run record."""
    import numpy as np

    # No allow_pickle: predictions.npz is a zip of plain .npy arrays (strings,
    # floats, ints), so nothing here needs object unpickling.
    npz = np.load(predictions)
    scores = npz[f"{split}_score"]
    truth = npz[f"{split}_true"]
    frac, columns = truth_readings(npz)
    cuts = load_cuts(thresholds) if (mode == "chosen" and thresholds) else {}
    if mode == "chosen" and not cuts:
        raise SystemExit("--mode chosen needs --thresholds")
    return columns, scores, truth, frac, cuts


def reproduce(predictions: Path, thresholds: Path | None, split: str, mode: str) -> dict:
    columns, scores, truth, frac, cuts = load_arm(predictions, thresholds, split, mode)

    verdicts, drivers = [], []
    for row in scores:
        result = decide({c: float(row[i]) for i, c in enumerate(columns)}, cuts=cuts)
        verdicts.append(result["verdict"])
        drivers.append(result["driver"])

    def count(pred_verdict, truth_reading):
        return sum(1 for v, t in zip(verdicts, frac) if v == pred_verdict and t == truth_reading)

    fail_n = frac.count("fail")
    clear_n = frac.count("clear")
    bubble_n = frac.count("bubble-only")
    fail_caught = count("fail", "fail")
    clear_wrong = count("fail", "clear")
    bubble_wrong = count("fail", "bubble-only")
    pass_n = clear_n + bubble_n

    top_driver: dict = {}
    for v, d in zip(verdicts, drivers):
        if v == "fail" and d:
            top_driver[d] = top_driver.get(d, 0) + 1

    return {
        "rule": RULE_ID,
        "source": f"{split} split, {mode} cuts",
        "population": {"fail": fail_n, "clear": clear_n, "bubble-only": bubble_n,
                       "pass": pass_n},
        "fail_pictures_caught": f"{fail_caught} of {fail_n}",
        "clear_passed": f"{clear_n - clear_wrong} of {clear_n}",
        "clear_wrongly_failed": clear_wrong,
        "bubble_only_passed": f"{bubble_n - bubble_wrong} of {bubble_n}",
        "pictures_passed_overall": f"{pass_n - clear_wrong - bubble_wrong} of {pass_n}",
        "drivers_on_failed_pictures": dict(sorted(top_driver.items(), key=lambda kv: -kv[1])),
    }


def per_class_tally(predictions: Path, thresholds: Path | None, split: str, mode: str) -> dict:
    """Per-column tally: how each class drives the block's outcome.

    Two readings per class, because "does this class fire" and "what does the
    picture end up doing" are different questions:

      truth_positives        pictures whose truth carries the class
      failed / escaped       of those, how many the block fails (caught) and how
                             many it passes anyway (escaped)
      false_fail_sole        pictures with no failing truth that fail only because
                             this class fired; these are the block's true cost
      false_fail_any         pictures with no failing truth that fail with this
                             class among the fired columns
    """
    import numpy as np

    columns, scores, truth, frac, cuts = load_arm(predictions, thresholds, split, mode)
    verdicts, fired_sets = [], []
    for row in scores:
        result = decide({c: float(row[i]) for i, c in enumerate(columns)}, cuts=cuts)
        verdicts.append(result["verdict"])
        fired_sets.append({f["column"] for f in result["fired"]})
    verdicts = np.array(verdicts)
    wrong = np.array([v == "fail" and f != "fail" for v, f in zip(verdicts, frac)])

    rows = []
    for i, column in enumerate(columns):
        is_true = truth[:, i] == 1
        cut = float(cuts.get(column, DEFAULT_CUT))
        fires = scores[:, i] >= cut
        pos = int(is_true.sum())
        tp = int((fires & is_true).sum())
        fp = int((fires & ~is_true).sum())
        role = "pass" if column in PASS_COLUMNS else "fail"
        rows.append({
            "column": column,
            "role": role,
            "cut": cut,
            "truth_positives": pos,
            "fires": int(fires.sum()),
            "precision": round(tp / int(fires.sum()), 4) if fires.sum() else None,
            "recall": round(tp / pos, 4) if pos else None,
            "truth_positives_failed": int((is_true & (verdicts == "fail")).sum()),
            "truth_positives_escaped": int((is_true & (verdicts == "pass")).sum()),
            "false_fail_sole": int(sum(1 for w, s in zip(wrong, fired_sets) if w and s == {column})),
            "false_fail_any": int(sum(1 for w, s in zip(wrong, fired_sets) if w and column in s)),
            "false_fires": fp,
        })
    rows.sort(key=lambda r: (r["role"] != "fail", -r["false_fail_any"], -r["truth_positives"]))

    firing_counts: dict = {}
    for s in fired_sets:
        if s:
            firing_counts[len(s)] = firing_counts.get(len(s), 0) + 1

    return {
        "rule": RULE_ID,
        "source": f"{split} split, {mode} cuts",
        "population": {"fail": frac.count("fail"), "clear": frac.count("clear"),
                       "bubble-only": frac.count("bubble-only")},
        "fired_fail_columns_per_failed_picture": dict(sorted(firing_counts.items())),
        "rows": rows,
    }


def selftest() -> int:
    cases = [
        ("clear passes", {}, "pass", "clear"),
        ("bubble only passes", {"class_bubble": 0.99, "class_bubble_cluster": 0.8}, "pass", "bubble-only"),
        ("wet package fails", {"class_wet_package": 0.7}, "fail", "object"),
        ("foreign matter fails beside a bubble", {"class_bubble": 0.99, "class_foreign_matter": 0.6}, "fail", "object"),
        ("a lens condition fails", {"P1_ML": 0.9}, "fail", "lens"),
        ("bubble scatter fails", {"P2_BSC": 0.52}, "fail", "lens"),
        ("just under the cut passes", {"P1_ML": 0.4999}, "pass", "clear"),
        ("a high bubble does not mask a lens fault", {"class_bubble": 0.99, "P2_FOV": 0.99}, "fail", "lens"),
    ]
    bad = 0
    for name, scores, want_verdict, want_reading in cases:
        got = decide(scores)
        ok = got["verdict"] == want_verdict and got["reading"] == want_reading
        bad += 0 if ok else 1
        print(("ok   " if ok else "FAIL ") + name + f" -> {got['verdict']}/{got['reading']}"
              + ("" if ok else f", wanted {want_verdict}/{want_reading}"))

    phase2 = from_detector([{"class": "Bubble", "score": 0.9}], lens_scores={"P1_ML": 0.2})
    ok = phase2["verdict"] == "pass" and phase2["reading"] == "bubble-only"
    bad += 0 if ok else 1
    print(("ok   " if ok else "FAIL ") + "phase 2 adapter maps a detector label -> " + phase2["verdict"])

    try:
        from_detector([{"class": "Mystery Object", "score": 0.9}])
        print("FAIL phase 2 adapter accepted an unknown label")
        bad += 1
    except ValueError:
        print("ok   phase 2 adapter rejects an unknown label")

    print(f"\n{len(cases) + 2 - bad} of {len(cases) + 2} checks passed")
    return 0 if bad == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", default="")
    parser.add_argument("--thresholds", default="")
    parser.add_argument("--split", choices=["val", "test"], default="test")
    parser.add_argument("--mode", choices=["0.5", "chosen"], default="0.5")
    parser.add_argument("--one", default="", help="JSON score dict for a single picture (phase 1)")
    parser.add_argument("--detections", default="", help="JSON detector output for a single picture (phase 2)")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--per-class", action="store_true",
                        help="per-class tally: caught, escaped, false fails contributed")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if args.one or args.detections:
        lens = json.loads(args.one or "{}")
        if args.detections:
            result = from_detector(json.loads(args.detections), lens_scores=lens)
        else:
            result = decide(lens)
        print(json.dumps(result, indent=2))
        return 0
    if not args.predictions:
        parser.error("give --predictions, --one, or --selftest")

    if args.per_class:
        result = per_class_tally(Path(args.predictions),
                                 Path(args.thresholds) if args.thresholds else None,
                                 args.split, args.mode)
        head = ("class", "role", "cut", "truth", "failed", "escaped", "fires", "prec", "false fails")
        print(f"{args.split} split, {args.mode} cuts, population {result['population']}")
        print(f"fired fail columns per picture the block fails: "
              f"{result['fired_fail_columns_per_failed_picture']}\n")
        print("{:<28} {:<5} {:>4} {:>6} {:>7} {:>8} {:>6} {:>6} {:>6}".format(*head))
        for r in result["rows"]:
            print("{:<28} {:<5} {:>4.2f} {:>6} {:>7} {:>8} {:>6} {:>6} {:>6}".format(
                r["column"], r["role"], r["cut"], r["truth_positives"],
                r["truth_positives_failed"], r["truth_positives_escaped"], r["fires"],
                r["precision"] if r["precision"] is not None else "-",
                r["false_fail_any"]))
        if args.out:
            import csv
            with Path(args.out).open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(result["rows"][0].keys()))
                writer.writeheader()
                writer.writerows(result["rows"])
            print(f"\nwrote {args.out}")
        return 0

    result = reproduce(Path(args.predictions),
                       Path(args.thresholds) if args.thresholds else None,
                       args.split, args.mode)
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
