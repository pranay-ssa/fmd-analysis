"""Add the 16 November size-gate rows to experiments/registry.json from run artifacts.

Results are read from the run records and the scored tables, never typed. Safe to re-run: an id
already present is refreshed in place, not duplicated.

    python experiments/add_exp3_rows.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "experiments" / "registry.json"


def load_run(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float) -> float:
    return round(float(value) * 100, 1)


def main() -> int:
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = doc["experiments"]
    new_ids = ("size_gate_pilot_four_classes", "exp1_redo_two_specialists")
    rows[:] = [r for r in rows if r["id"] not in new_ids]

    pilot = load_run(REPO / "run/exp3_1_gate4_224_20261117/run.json")
    pilot_448 = load_run(REPO / "run/exp3_1_gate4_448_20261117/run.json")
    redo = load_run(REPO / "run/exp3_2_cond15_20261116/run.json")
    scores = json.loads((REPO / "run/exp3_2_scores_20261116/summary.json").read_text(encoding="utf-8"))

    rows.append({
        "id": "size_gate_pilot_four_classes",
        "model_family": "cnn (resnet50, four gate columns)",
        "data_arena": "pilot split, 4,964 / 1,058 / 1,533, flagged only in train and validation",
        "file": "experiments/multilabel_ooi/score_exp3_1.py",
        "summary": ("Can a CNN see the micron size cut? Four gated classes, trained on flagged "
                    "pictures only, tested on untagged pictures with a tagged guard."),
        "axis": "size separability of the four gated classes",
        "theoretical_possible": True,
        "batch": None,
        "params": pilot["config"],
        "status": "done",
        "hypothesis": ("A model trained only above the cut can place below-cut pictures lower than "
                       "a model trained on class presence does, if size is learnable at 224 px."),
        "results": {
            "foreign_matter_auroc": round(pilot["metrics"]["primary"]["value"], 3),
            "foreign_matter_auroc_448": round(pilot_448["metrics"]["primary"]["value"], 3),
            "stage0_foreign_matter_auroc": 0.613,
            "stage0_false_fire_all": 0.845,
            "gate4_false_fire_all": 0.495,
            "gate4_recall": 0.835,
            "pass_fail_decisive": {"baseline": "13 of 98 fail", "gate4_224": "9 of 98",
                                   "gate4_448": "4 of 98"},
        },
        "note": ("Size-bin curve is the finding: the old model's score falls with box size, the gate "
                 "arm's rises across the cut at about 19.5 native pixels. No pre-registered bar. "
                 "Records: run/exp3_1_gate4_224_20261117/run.json and "
                 "run/exp3_1_gate4_448_20261117/run.json; workbook "
                 "reports/multilabel_production/size_gate_pilot_20261116.xlsx."),
    })

    rows.append({
        "id": "exp1_redo_two_specialists",
        "model_family": "cnn (resnet50, 15 condition columns + 4 size columns)",
        "data_arena": "same 1,121 test pictures as Experiment 1 for the verdict; 1,533 for the size read",
        "file": "experiments/multilabel_ooi/score_exp3_2.py",
        "summary": ("Experiment 1 redone with the pass/fail order the client and lead now use, and "
                    "with size decided by the flag: two specialists, one verdict."),
        "axis": "pass/fail rule order and size truth",
        "theoretical_possible": True,
        "batch": None,
        "params": redo["config"],
        "status": "done",
        "hypothesis": ("Reordering the rule moves only Bubble Cluster pictures and treating an "
                       "untagged gated picture as a pass moves only below-cut pictures, so the "
                       "headline rates should barely move against Experiment 1."),
        "results": {
            "macro_ap_condition_15": round(redo["metrics"]["primary"]["value"], 4),
            "primary_rule": {r["rule"]: {"fail": int(r["fail_pictures"]),
                                         "caught": int(r["caught"]),
                                         "pass": int(r["passed_ok"]) + int(r["wrongly_failed"]),
                                         "passed": int(r["passed_ok"]),
                                         "wrongly_failed": int(r["wrongly_failed"]),
                                         "share_fail_caught": pct(r["share_fail_caught"]),
                                         "share_pass_passed": pct(r["share_pass_passed"])}
                             for r in scores["pass_fail"]},
            "class_truth_starting_point": {"fail": 768, "pass": 353},
            "effect_of_size_correction": "2 pictures",
            "effect_of_rule_order": "18 pictures, all Bubble Cluster",
        },
        "note": ("The 768 reproduces Experiment 1 exactly when the earlier reading is applied to "
                 "the same two models. Rules: "
                 "docs/decisions/2026-11-16-size-rule-order-and-gate-truth.md. Workbook "
                 "reports/multilabel_production/size_gate_redo_20261116.xlsx."),
    })

    doc["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    tmp.replace(REGISTRY)
    print(f"registry rows: {len(rows)}; added or refreshed "
          f"{[r['id'] for r in rows if r['id'].startswith(('size_gate_pilot', 'exp1_redo'))]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
