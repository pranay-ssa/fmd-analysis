"""The arm pipeline: one entry point from saved scores to a decided run record.

WHY THIS FILE EXISTS
--------------------
An arm is not finished when training stops. It is finished when the model's scores
have been turned into picture verdicts and recorded beside the model's own metrics.
Until now those two halves lived apart: metrics.json in the run folder, verdicts in
a workbook. This is the stage that joins them, so one arm produces one record.

WHY IT IS NOT ONE SCRIPT WITH THE TRAINER
-----------------------------------------
Three modules, one pipeline:

  train_multilabel.py  (VM, torch)     pictures -> scores, thresholds on validation
  pass_fail_block.py   (no torch)      scores + cuts -> pass or fail, with attribution
  run_arm.py           (no torch)      the stages in order, and the record they write

Keeping the rule out of the trainer is deliberate:

- the block has to run where torch is not installed: the line runner, the workflow
  verifier, a laptop re-checking a sent workbook. A rule welded into a training
  script cannot be imported by any of them without dragging torch and a GPU in;
- phase 2 feeds the same rule from a detector instead of the CNN. That path must
  not import the trainer;
- the three layers change at different rates. The rule changes when a decision
  changes, the cuts change when the data changes, the model changes when the recipe
  changes. Welded together, a threshold change means touching a training script,
  and the project has already paid for exactly that kind of silent divergence
  once (per-arm metrics files that no registry could rebuild from).

The unit the lead cares about is a phase, and a phase is train plus decide. That is
what this file makes true: one command, one record.

HOW TO RUN IT
-------------
An arm that already has saved scores (no GPU, this laptop):

    .venv/Scripts/python.exe experiments/multilabel_ooi/run_arm.py \
        --arm-dir run/multilabel_ooi_20261104/combined --mode both

It writes decision.json beside the arm's artifacts and merges a `decision` section
into that arm's run.json, leaving every existing key untouched. It then reads the
file back and prints what it found, so a silent overwrite cannot pass unnoticed.

A fresh arm on the VM runs the same two stages after training:

    .venv/bin/python experiments/multilabel_ooi/run_arm.py --arm-dir <arm> --mode both

Stage order for a fresh arm: train (train_multilabel.py) -> this -> report.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pass_fail_block as block

MODES = {"0.5": "0.5", "chosen": "chosen", "both": "both"}


def decide_arm(arm_dir: Path, thresholds: Path | None, split: str, mode: str) -> dict:
    """Run the block over one arm's saved scores at one operating point."""
    import numpy as np

    present = {str(c) for c in np.load(arm_dir / "predictions.npz")["columns"]}
    required = set(block.PASS_OBJ) | (set(block.FAIL_OBJ) - {"class_surface_groove"})
    missing = sorted(required - present)
    if missing:
        raise SystemExit(
            f"{arm_dir.name}: this arm has no columns {missing}, so it cannot be decided.\n"
            "A lens-only head would read every object-only picture as clear: on the test\n"
            "split that is 120 pictures passing while they carry an object. Decide only an\n"
            "arm that carries the object columns (--columns combined)."
        )
    payload = {
        "rule": block.RULE_ID,
        "operating_point": mode,
        "split": split,
        "headline": block.reproduce(arm_dir / "predictions.npz", thresholds, split, mode),
        "per_class": block.per_class_tally(arm_dir / "predictions.npz", thresholds, split, mode),
    }
    return payload


def merge_record(arm_dir: Path, decision: dict) -> dict:
    """Put the decision beside the model metrics, never over them."""
    record_path = arm_dir / "run.json"
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding="utf-8"))
    else:
        record = {
            "schema_version": 1,
            "run_id": f"{arm_dir.parent.name}__{arm_dir.name}",
            "family": "cnn",
            "arm": arm_dir.name,
            "status": "ok",
            "notes": "record created by run_arm.py from the arm's saved artifacts; "
                     "training fields unknown",
        }
    before = set(record)
    record["decision"] = decision
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    back = json.loads(record_path.read_text(encoding="utf-8"))
    lost = before - set(back)
    if lost:
        raise SystemExit(f"run.json lost keys while merging: {sorted(lost)}")
    if back["decision"]["rule"] != block.RULE_ID:
        raise SystemExit("run.json decision did not read back as written")
    return back


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm-dir", required=True)
    ap.add_argument("--thresholds", default="",
                    help="defaults to <arm-dir>/thresholds.json")
    ap.add_argument("--split", choices=["val", "test"], default="test")
    ap.add_argument("--mode", choices=list(MODES), default="both")
    ap.add_argument("--write", action="store_true",
                    help="write decision.json and merge into run.json (default: print only)")
    args = ap.parse_args()

    arm_dir = Path(args.arm_dir)
    predictions = arm_dir / "predictions.npz"
    if not predictions.is_file():
        raise SystemExit(f"no saved scores at {predictions}; run the scoring stage first")
    thresholds = Path(args.thresholds) if args.thresholds else arm_dir / "thresholds.json"
    if not thresholds.is_file():
        thresholds = None

    modes = ["0.5", "chosen"] if args.mode == "both" else [args.mode]
    decision = {
        "rule": block.RULE_ID,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "split": args.split,
        "thresholds_file": thresholds.name if thresholds else None,
        "stages": {
            "score": "train_multilabel.py (VM, torch)",
            "decide": "pass_fail_block.py (no torch)",
            "record": "run_arm.py",
        },
        "operating_points": {},
    }
    for mode in modes:
        decision["operating_points"][mode] = decide_arm(arm_dir, thresholds, args.split, mode)

    for mode, payload in decision["operating_points"].items():
        head = payload["headline"]
        print(f"[{mode}] caught {head['fail_pictures_caught']}, "
              f"clear passed {head['clear_passed']}, "
              f"bubble-only passed {head['bubble_only_passed']}, "
              f"passed overall {head['pictures_passed_overall']}")

    if args.write:
        (arm_dir / "decision.json").write_text(json.dumps(decision, indent=2) + "\n",
                                               encoding="utf-8")
        record = merge_record(arm_dir, decision)
        print(f"\nwrote {arm_dir / 'decision.json'}")
        print(f"run.json keys: {sorted(record)}")
        print(f"run.json decision rule: {record['decision']['rule']}, "
              f"operating points: {sorted(record['decision']['operating_points'])}")
    else:
        print("\n(dry run; pass --write to record it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
