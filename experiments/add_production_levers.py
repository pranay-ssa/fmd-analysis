"""Append the 'food for thought' idea rows to experiments/registry.json.

These are ideated only (status: ideated, results: null). Nothing here is run or scheduled; the point is
to have every angle documented with its cost and its expected value, so the ones the production data can
actually decide are ready to launch.
"""
import json
from pathlib import Path

P = Path("experiments/registry.json")
reg = json.loads(P.read_text(encoding="utf-8"))

ARENA = "production_size_and_data_levers"
reg["protocols_by_arena"].setdefault(ARENA, {
    "task": "same task and metrics as the arena each idea is compared against; not yet run",
    "imgsz": "grid (1280 / 1568 / native frame width)",
    "epochs": 100,
    "seed": 42,
    "note": ("Planned arena. Every row here is ideated and waits for the production-grade set, because on "
             "346 training images effects below about 0.02 cannot be separated from run-to-run variation and "
             "the noise floor is still unmeasured."),
})

new_rows = [
    {
        "id": "res_input_size_native_crops",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "nil (protocol change: imgsz 1568 instead of 1280)",
        "summary": "Train the multiclass baseline at native crop size (about 1568 px) instead of 1280.",
        "axis": "input resolution",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("Smaller gain than the full-frame case. Our crop already hands the model about 11 px of "
                       "defect at 1280, against about 7 px for a full frame at 1280, so the remaining step is "
                       "1.22x of linear detail, not 1.86x. Expected +0.02 to +0.05 mAP50, unproven."),
        "results": None,
        "note": ("Cost is the attraction: about 1.5x training time (566 s to roughly 850 s per 100-epoch arm) and "
                 "1.38x inference (7.65 to 10.57 ms per image, measured 2026-09-15). Deferred to the production "
                 "set; the decision belongs on a measured size-versus-score-versus-time curve."),
    },
    {
        "id": "res_crop_margin_tight",
        "model_family": "any",
        "data_arena": ARENA,
        "file": "nil (preprocessing change, no model change)",
        "summary": ("Tighten the crop margin so the defect occupies a larger share of the input, at identical "
                    "model and inference cost."),
        "axis": "input resolution (free detail, preprocessing only)",
        "theoretical_possible": True,
        "batch": None,
        "params": 0,
        "status": "ideated",
        "hypothesis": ("If score scales with defect pixels, reducing empty border raises the defect's share for "
                       "free. The multi-size crop mode is already tighter than the single-size mode used for "
                       "detection, so the material exists."),
        "results": None,
        "note": ("Cheapest idea on the list: no GPU cost for the crop itself, one training run to test. Watch the "
                 "trade: a tighter crop risks cutting defects that sit near the border."),
    },
    {
        "id": "res_two_stage_cascade",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "nil (two-stage pipeline)",
        "summary": ("Stage one detects on the 1280 crop, stage two re-runs only the candidate regions at native "
                    "resolution."),
        "axis": "input resolution at compute parity",
        "theoretical_possible": True,
        "batch": None,
        "params": 0,
        "status": "ideated",
        "hypothesis": ("Pays the native-resolution price only on a few small regions instead of the whole image, "
                       "so most of the +26% quality could arrive without the 3x inference cost."),
        "results": None,
        "note": ("Needs a harness and a second model pass, so it is the most engineering of the resolution ideas. "
                 "Matters most if deployment lands on an edge device."),
    },
    {
        "id": "data_iou_ceiling",
        "model_family": "nil (data measurement)",
        "data_arena": ARENA,
        "file": "nil",
        "summary": ("Measure the annotation ceiling: re-annotate a subset of frames independently and compute the "
                    "overlap between the two label sets."),
        "axis": "data quality (label noise floor)",
        "theoretical_possible": True,
        "batch": None,
        "params": 0,
        "status": "ideated",
        "hypothesis": ("Median overlap between a found box and the correct box is stuck at about 0.80 across every "
                       "model, setting and pipeline, which points at the labels rather than the model. If human "
                       "annotators disagree at about 0.80 on the same defect, box precision is at its ceiling."),
        "results": None,
        "note": ("No GPU cost and it tests our main blocker directly. The decisive experiment for the box-precision "
                 "claim; it turns that claim from inference into a number."),
    },
    {
        "id": "aug_small_object",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "nil (training config)",
        "summary": ("Augmentation aimed at small objects: scale jitter, copy-paste of defect patches, mosaic on "
                    "against off."),
        "axis": "data augmentation",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("At 13 px defects the model is starved of defect pixels. Scale jitter and copy-paste "
                       "manufacture defect detail without new annotation, so they should raise recall before any "
                       "architecture edit does."),
        "results": None,
        "note": "Cheap in GPU time and orthogonal to every architecture idea, so it can run in parallel with them.",
    },
    {
        "id": "model_scale_s",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "yolo26s.yaml (stock)",
        "summary": "One capacity step up, from the nano model to the small model, stock architecture.",
        "axis": "model capacity",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("We have spent weeks editing the nano architecture; on small defects a larger model may buy "
                       "more than the edits did. Compare against the +0.059 best architecture result."),
        "results": None,
        "note": "Costs about 2-3x the training time of the nano model. A cheap way to find out where the ceiling is.",
    },
    {
        "id": "res_seed_ensemble",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "nil (3 seeds on the same config)",
        "summary": "Three seeds of the baseline, evaluated individually and as a merged ensemble.",
        "axis": "variance and ensembling",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("Two results for one cost: the spread across seeds gives the noise floor we have never "
                       "measured, and the ensemble itself usually beats a single architecture edit on a small set."),
        "results": None,
        "note": ("This is the experiment that makes every other delta in this registry interpretable. Highest "
                 "priority of the list once GPU time is available."),
    },
]

have = {r["id"] for r in reg["experiments"]}
added = 0
for row in new_rows:
    if row["id"] in have:
        print("skip (exists):", row["id"])
        continue
    reg["experiments"].append(row)
    added += 1

reg["updated"] = "2026-09-15 (reference LR/resolution economics + 7 ideated production-data levers)"
P.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

# validate
back = json.loads(P.read_text(encoding="utf-8"))
print("rows now:", len(back["experiments"]), "| added:", added)
missing = [r["id"] for r in back["experiments"] if not all(k in r for k in
           ("id", "model_family", "data_arena", "summary", "axis", "status", "hypothesis", "results", "note"))]
print("rows missing required keys:", missing or "none")
print("duplicate ids:", len(back["experiments"]) - len({r["id"] for r in back["experiments"]}))
