"""Append the port-program rows to experiments/registry.json.

The port program carries the YOLO11 winners (changes inside the existing pathway) onto the YOLO26
multiclass arena, plus the seed-noise floor that decides which deltas are real. All rows are ideated:
nothing here is built or scheduled yet.
"""
import json
from pathlib import Path

P = Path("experiments/registry.json")
reg = json.loads(P.read_text(encoding="utf-8"))
ARENA = "multiclass_detect_1280_10cls"
BASE = "0.5355 / 0.3211 (mc_baseline, reproduced three times)"

new_rows = [
    {
        "id": "mc_noise_floor",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "nil (stock config, seeds 42 / 43 / 44)",
        "summary": "H0: the seed-noise floor. Run the stock config three times with different seeds and report the spread.",
        "axis": "measurement (variance)",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("Without the seed spread, no delta in this registry can be separated from run-to-run "
                       "variation. Everything so far is single-seed on 88 val images."),
        "results": None,
        "note": ("Do this before any of the port arms: three of their four expected deltas are 0.01 to 0.04, which "
                 "is exactly the range a seed change can produce. Cost: 3 runs, about 30 minutes."),
    },
    {
        "id": "mc_attention_port",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "experiments/yolo26/yolo26_mc_attention.yaml (to be written)",
        "summary": "H5a: backbone rows 6 and 8, C3k2 becomes C2PSA. Port of the winning YOLO11 attention change.",
        "axis": "architecture (attention, inside the pathway)",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("+0.02 to +0.06 mAP50 over " + BASE + ". Recall should rise more than precision, and any "
                       "gain should concentrate in the weak classes (Bubble On 123, Fiber, Bubble Cluster, "
                       "Bubble On Edge). Evidence: +0.059 mAP50 on the YOLO11 OBB arena, the best accuracy per "
                       "parameter of everything tried there, and the only variant that detected HEMA Fragment."),
        "results": None,
        "note": ("Highest-priority architecture change: it strengthens processing inside the existing pathway, "
                 "which is where every positive result came from, unlike the two failed input-bolt-on ideas. "
                 "Adds about 0.4M params (YOLO11 analogue 2.66M to 3.13M), so no param-matched control. "
                 "Preflight gate required; must keep the stock head keys."),
    },
    {
        "id": "mc_sppf_k7",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "experiments/yolo26/yolo26_mc_sppf_k7.yaml (to be written)",
        "summary": "H5b: backbone row 9 SPPF kernel 5 becomes 7. Zero params, zero compute, pure field of view.",
        "axis": "architecture (receptive field)",
        "theoretical_possible": True,
        "batch": 8,
        "params": 0,
        "status": "ideated",
        "hypothesis": "0.00 to +0.02 mAP50. Its YOLO11 value was +0.018 mAP50 and +0.007 mAP50-95, which sits at the edge of what 88 val images can resolve.",
        "results": None,
        "note": ("The arg form must stay complete: [1024, 7, 3, True], never [1024, 7]. Dropping the extra "
                 "arguments silently changes the block's behaviour (the trap that invalidated V1/V2). Run it "
                 "after the noise floor, and treat a positive result as suggestive rather than settled."),
    },
    {
        "id": "mc_p4_conv",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "experiments/yolo26/yolo26_mc_p4_conv.yaml (to be written)",
        "summary": "H5c: two extra plain Conv [512,3,1] at the P4 stage (after row 6, before row 7).",
        "axis": "architecture (depth at P4)",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("+0.01 to +0.04 mAP50. Evidence: +0.037 mAP50 on the YOLO11 line, where this change was "
                       "armB, and where extra depth at P4 helped while extra depth at P5 did not (LOCATION matters, "
                       "not TYPE)."),
        "results": None,
        "note": "Cheap. Read it against the noise floor before claiming anything: the expected range straddles it.",
    },
    {
        "id": "mc_consolidated",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "experiments/yolo26/yolo26_mc_consolidated.yaml (to be written)",
        "summary": "H5d: combine the H5 changes that individually cleared the noise floor.",
        "axis": "architecture (combination)",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": ("Roughly the sum of the parts if the changes act independently, less if they overlap. This "
                       "is the arm that would actually ship."),
        "results": None,
        "note": ("Build it only from changes that individually passed, and only after they have passed. The YOLO11 "
                 "line carries the analogue as the ideated row consolidated_obb."),
    },
    {
        "id": "mc_raw_p3_tap",
        "model_family": "YOLO26",
        "data_arena": ARENA,
        "file": "experiments/yolo26/yolo26_mc_raw_p3_tap.yaml (to be written)",
        "summary": "H2b: R1's raw backbone-P3 tap, re-run on the multiclass arena so raw and processed are ranked on identical ground.",
        "axis": "architecture (added low-layer input, control for H2)",
        "theoretical_possible": True,
        "batch": 8,
        "params": None,
        "status": "ideated",
        "hypothesis": "Both arms negative is the expectation; the open question is which is less bad.",
        "results": None,
        "note": ("R1 (raw, single-class crops) cost -0.0560 and H2 (processed, multiclass) cost -0.0992, and those "
                 "two numbers are NOT comparable because the arenas and baselines differ. This arm is the only "
                 "clean raw-versus-processed comparison. Control plus fork in one session."),
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

reg["updated"] = "2026-09-15 (port program rows: noise floor, attention port, SPPF k7, P4 Conv, consolidated, raw tap control)"
P.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

back = json.loads(P.read_text(encoding="utf-8"))
ids = [r["id"] for r in back["experiments"]]
print("rows now:", len(ids), "| added:", added)
print("duplicate ids:", len(ids) - len(set(ids)))
print("ideated count:", sum(1 for r in back["experiments"] if r["status"] == "ideated"))
for key in ("id", "model_family", "data_arena", "summary", "axis", "status", "hypothesis", "results", "note"):
    missing = [r["id"] for r in back["experiments"] if r["id"] in {x["id"] for x in new_rows} and key not in r]
    if missing:
        print("new rows missing", key, ":", missing)
