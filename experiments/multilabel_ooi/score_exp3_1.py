"""Score Experiment 3.1 arms: AUROC, false-fire, recall, pass/fail on the decisive set.

Local, numpy only. Reads saved scores, never images or torch.

    .venv/Scripts/python.exe experiments/multilabel_ooi/score_exp3_1.py \
        --detail run/split_exp3_1_20261116/picture_detail.csv \
        --set stage0:run/exp3_1_stage0_20261117/predictions.npz:run/multilabel_ooi_20261104/combined/thresholds.json \
        --set gate4_224:run/exp3_1_gate4_224_20261117/predictions.npz:run/exp3_1_gate4_224_20261117/thresholds.json \
        --out run/exp3_1_scores_20261117

Rule, per the map: for the four gated classes the gate column is the fail column, Bubble and
Clear pass, every other class fails. On the decisive pictures no other fail label exists, so the
object-side verdict is exact. On the full test set the verdict is object side only and the
per_class.csv row says so.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CLASSES = [
    ("foreign_matter", "class_foreign_matter", "fm_gated", "fm_present", "decisive_fm", "largest_fm_px"),
    ("fiber", "class_fiber", "fiber_gated", "fiber_present", "decisive_fiber", "largest_fiber_px"),
    ("extraneous_polymer", "class_extraneous_polymer", "ep_gated", "ep_present", "decisive_ep", "largest_ep_px"),
    ("hema", "class_hema", "hema_gated", "hema_present", "decisive_hema", "largest_hema_px"),
]


def auroc(pos, neg):
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def read_detail(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["picture_md5"]] = r
    return rows


def thresholds_from(path, columns):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    per = data.get("per_class", data)
    return {c: float(per.get(c, {}).get("threshold", per.get(c, 0.5))) for c in columns}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", required=True)
    ap.add_argument("--set", action="append", required=True,
                    help="name|npz|thresholds (pipe, because Windows paths contain a colon)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import numpy as np

    detail = read_detail(args.detail)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_class, per_picture, size_rows, summary = [], [], [], {"sets": {}}
    for spec in args.set:
        name, npz_path, thr_path = spec.split("|", 2)
        d = np.load(npz_path, allow_pickle=True)  # trusted local artifact from our trainer
        # Stage 0 writes md5/score; the trainer writes test_md5/test_score.
        md5s = [str(x) for x in (d["md5"] if "md5" in d else d["test_md5"])]
        scores = d["score"] if "score" in d else d["test_score"]
        cols = [str(x) for x in d["columns"]]
        cuts = thresholds_from(thr_path, cols)
        idx = {c: cols.index(c) for c in cols}

        # align
        keep = [i for i, m in enumerate(md5s) if m in detail]
        md5s = [md5s[i] for i in keep]
        scores = scores[keep]

        set_summary = {"n": len(md5s), "classes": {}}
        for label, col, gate_key, present_key, decisive_key, px_key in CLASSES:
            # Experiment 1 columns are class_*; the gate4 arm's columns are the gate names.
            model_col = col if col in idx else (gate_key if gate_key in idx else None)
            if model_col is None:
                continue
            j = idx[model_col]
            cut = cuts[model_col]
            gated, unflagged, decisive = [], [], []
            for i, m in enumerate(md5s):
                r = detail[m]
                if r["split"] != "test":
                    continue
                s = float(scores[i, j])
                is_present = r[present_key] == "1"
                if not is_present:
                    continue
                if r[gate_key] == "1":
                    gated.append(s)
                else:
                    unflagged.append(s)
                    if r[decisive_key] == "1":
                        decisive.append(s)
            fire_all = sum(1 for s in unflagged if s >= cut) / len(unflagged) if unflagged else None
            fire_dec = sum(1 for s in decisive if s >= cut) / len(decisive) if decisive else None
            recall = sum(1 for s in gated if s >= cut) / len(gated) if gated else None
            if label == "hema":
                measurable = "not measurable: the unflagged pictures are unassessed September fragments, not below-cut production pictures"
            elif len(gated) >= 10 and len(unflagged) >= 10:
                measurable = "yes"
            elif not unflagged:
                measurable = "not measurable: no unflagged population"
            else:
                measurable = f"thin: gated {len(gated)}, unflagged {len(unflagged)}"
            row = {
                "set": name, "class": label, "cut": cut,
                "auroc": auroc(gated, unflagged),
                "gated_n": len(gated), "unflagged_n": len(unflagged),
                "decisive_n": len(decisive),
                "recall_at_cut": recall,
                "false_fire_all": fire_all,
                "false_fire_decisive": fire_dec,
                "measurable": measurable,
            }
            per_class.append(row)
            set_summary["classes"][label] = row

            for i, m in enumerate(md5s):
                r = detail[m]
                if r["split"] != "test" or r[present_key] != "1":
                    continue
                s = float(scores[i, j])
                size_rows.append({"set": name, "class": label, "md5": m,
                                  "largest_px": r[px_key], "score": s,
                                  "gated": r[gate_key], "decisive": r[decisive_key]})

        # pass/fail on decisive pictures: object side only, exact there
        fail_cols = [idx[c] if c in idx else idx[g]
                     for _, c, g, *_ in CLASSES if (c in idx or g in idx)]
        decisive_md5s = []
        for m in md5s:
            r = detail[m]
            if r["split"] != "test":
                continue
            # HEMA is left out on purpose: every production HEMA picture is flagged, so its
            # decisive set is 3 pictures and the class cannot be judged. The pass/fail table
            # therefore rests on FM, Fiber and EP only.
            if any(r[k] == "1" for k in ("decisive_fm", "decisive_fiber", "decisive_ep")):
                decisive_md5s.append(m)
        caught = passed = 0
        for m in decisive_md5s:
            i = md5s.index(m)
            fires = [cols[j] for j in fail_cols if float(scores[i, j]) >= cuts[cols[j]]]
            if fires:
                caught += 1
            else:
                passed += 1
        set_summary["pass_fail_decisive"] = {
            "population": len(decisive_md5s), "failed": caught, "passed": passed,
            "scope": "object side only; decisive pictures carry no other fail label",
        }
        for i, m in enumerate(md5s):
            r = detail[m]
            if r["split"] != "test":
                continue
            fires = [cols[j] for j in fail_cols if float(scores[i, j]) >= cuts[cols[j]]]
            per_picture.append({
                "set": name, "md5": m, "split": r["split"],
                **{c: f"{float(scores[i, idx[c if c in idx else g] ]):.6f}"
                   for _, c, g, *_ in CLASSES
                   if (c in idx or g in idx)},
                "fired": ";".join(fires), "verdict": "fail" if fires else "pass",
                "decisive": "1" if m in decisive_md5s else "0",
            })
        summary["sets"][name] = set_summary

    def write(name, rows):
        if not rows:
            return
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    # Behaviour view: mean score per box-size bin, per arm and class. This is the table that
    # shows whether the score rises with defect size or is flat.
    bins = [(0, 8), (8, 12), (12, 18), (18, 24), (24, 36), (36, 64), (64, 10**6)]
    size_bins = []
    for name in summary["sets"]:
        for label, *_ in CLASSES:
            rows_c = [r for r in size_rows if r["set"] == name and r["class"] == label
                      and r["largest_px"] not in ("", None)]
            if not rows_c:
                continue
            for lo, hi in bins:
                part = [float(r["score"]) for r in rows_c if lo <= float(r["largest_px"]) < hi]
                if not part:
                    continue
                size_bins.append({
                    "set": name, "class": label, "bin_px": f"{lo}-{hi if hi < 10**6 else 'max'}",
                    "n": len(part), "mean_score": sum(part) / len(part),
                    "share_above_0.5": sum(1 for s in part if s >= 0.5) / len(part),
                })

    write("per_class.csv", per_class)
    write("per_picture.csv", per_picture)
    write("size_curve.csv", size_rows)
    write("size_bins.csv", size_bins)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
