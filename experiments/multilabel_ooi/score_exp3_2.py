"""Experiment 3.2, Option B: combine the condition specialist and the size specialist.

One verdict from two models. The condition model settles the twelve lens conditions plus Bubble,
Bubble Cluster and Wet Package. The size model settles the four gated classes, where an untagged
picture is a pass.

Two rules, same two models:

  primary   pass = clear, or bubble only, or untagged gated pictures; Bubble Cluster fails
  secondary the same, with Bubble Cluster moved to the pass side

    python experiments/multilabel_ooi/score_exp3_2.py \
        --labels run/split_exp3_2_20261116/labels_19.csv \
        --cond run/exp3_2_cond15_20261116/predictions.npz:run/exp3_2_cond15_20261116/thresholds.json \
        --size run/exp3_1_gate4_224_20261117/predictions.npz:run/exp3_1_gate4_224_20261117/thresholds.json \
        --out run/exp3_2_scores_20261116
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

LENS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL",
        "P2_LD", "P1_COC", "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]
COND_OBJECT = ["class_bubble", "class_bubble_cluster", "class_wet_package"]
GATES = ["fm_gated", "fiber_gated", "ep_gated", "hema_gated"]
CLASS_OF = {"fm_gated": "class_foreign_matter", "fiber_gated": "class_fiber",
            "ep_gated": "class_extraneous_polymer", "hema_gated": "class_hema"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cuts_from(path, columns, prefix_map=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    per = data.get("per_class", data)
    out = {}
    for c in columns:
        key = prefix_map(c) if prefix_map else c
        entry = per.get(key, {})
        out[c] = float(entry.get("threshold", 0.5)) if isinstance(entry, dict) else float(entry)
    return out


def auroc(pos, neg):
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall, (2 * precision * recall / (precision + recall)
                               if (precision + recall) else 0.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--cond", required=True, help="npz|thresholds (pipe, Windows paths have colons)")
    ap.add_argument("--size", required=True, help="npz|thresholds")
    ap.add_argument("--out", required=True)
    ap.add_argument("--truth", choices=["gate", "class"], default="gate",
                    help="gate = a size-flagged class fails only above the cut; "
                         "class = it fails on presence, the Experiment 1 reading")
    args = ap.parse_args()

    import numpy as np

    rows = {r["picture_md5"]: r for r in read_csv(args.labels)}
    test = [r for r in rows.values() if r["split"] == "test"]

    def load(spec):
        npz_path, thr_path = spec.split("|", 1)
        d = np.load(npz_path, allow_pickle=True)  # trusted local artifact from our trainer
        md5 = [str(x) for x in (d["md5"] if "md5" in d else d["test_md5"])]
        score = d["score"] if "score" in d else d["test_score"]
        cols = [str(x) for x in d["columns"]]
        return md5, score, cols, cuts_from(thr_path, cols)

    c_md5, c_score, c_cols, c_cut = load(args.cond)
    s_md5, s_score, s_cols, s_cut = load(args.size)
    c_at = {m: i for i, m in enumerate(c_md5)}
    s_at = {m: i for i, m in enumerate(s_md5)}

    # Only pictures that are test for both models: all of the 1,121, since the size model
    # never saw any of them and the condition model never saw them either.
    pop = [r["picture_md5"] for r in test if r["picture_md5"] in c_at and r["picture_md5"] in s_at]
    if not pop:
        raise SystemExit("no overlapping test pictures between the two models")

    def fires(md5, kind, rule):
        """Predicted fail labels for one picture under one rule."""
        out = []
        r = rows[md5]
        i = c_at[md5]
        for c in LENS:
            if c in c_cols and float(c_score[i, c_cols.index(c)]) >= c_cut[c]:
                out.append(c)
        if "class_wet_package" in c_cols:
            j = c_cols.index("class_wet_package")
            if float(c_score[i, j]) >= c_cut["class_wet_package"]:
                out.append("class_wet_package")
        if "class_bubble_cluster" in c_cols and rule == "primary":
            j = c_cols.index("class_bubble_cluster")
            if float(c_score[i, j]) >= c_cut["class_bubble_cluster"]:
                out.append("class_bubble_cluster")
        k = s_at[md5]
        for g in GATES:
            if g in s_cols and float(s_score[k, s_cols.index(g)]) >= s_cut[g]:
                out.append(g)
        return out

    def truth_fail(md5, rule):
        r = rows[md5]
        out = [c for c in LENS if r[c] == "1"]
        if r["class_wet_package"] == "1":
            out.append("class_wet_package")
        if r["class_bubble_cluster"] == "1" and rule == "primary":
            out.append("class_bubble_cluster")
        if args.truth == "class":
            out += [g for g, c in CLASS_OF.items() if r.get(c) == "1"]
        else:
            out += [g for g in GATES if r[g] == "1"]
        return out

    results, detail = [], []
    for rule in ("primary", "secondary"):
        tp = fp = fn = tn = 0
        for m in pop:
            t = bool(truth_fail(m, rule))
            p = bool(fires(m, rule, rule))
            if t and p:
                tp += 1
            elif t and not p:
                fn += 1
            elif not t and p:
                fp += 1
            else:
                tn += 1
            detail.append({"rule": rule, "md5": m, "truth": "fail" if t else "pass",
                           "predicted": "fail" if p else "pass",
                           "truth_labels": ";".join(truth_fail(m, rule)),
                           "fired": ";".join(fires(m, rule, rule))})
        results.append({"rule": rule, "population": len(pop), "fail_pictures": tp + fn,
                        "caught": tp, "missed": fn, "passed_ok": tn,
                        "wrongly_failed": fp,
                        "share_fail_caught": round(tp / (tp + fn), 4) if (tp + fn) else None,
                        "share_pass_passed": round(tn / (tn + fp), 4) if (tn + fp) else None})

    # Condition columns on the same population: AP, AUROC, F1 at the chosen cut.
    cond_rows = []
    for c in LENS + COND_OBJECT:
        if c not in c_cols:
            continue
        j = c_cols.index(c)
        pos = [float(c_score[c_at[m], j]) for m in pop if rows[m][c] == "1"]
        neg = [float(c_score[c_at[m], j]) for m in pop if rows[m][c] == "0"]
        pred_pos = sum(1 for m in pop if float(c_score[c_at[m], j]) >= c_cut[c])
        tp = sum(1 for m in pop if rows[m][c] == "1" and float(c_score[c_at[m], j]) >= c_cut[c])
        fp = pred_pos - tp
        fn_ = len(pos) - tp
        precision, recall, f1 = prf(tp, fp, fn_)
        cond_rows.append({"class": c, "population": len(pop), "support": len(pos),
                          "auroc": auroc(pos, neg), "threshold": c_cut[c],
                          "precision": round(precision, 4), "recall": round(recall, 4),
                          "f1": round(f1, 4)})

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    def write(name, data):
        if not data:
            return
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    write("pass_fail.csv", results)
    write("per_picture.csv", detail)
    write("conditions.csv", cond_rows)
    summary = {"population": len(pop), "pass_fail": results, "conditions": cond_rows,
               "note": ("Both rules use the same two models. The primary rule fails Bubble "
                        "Cluster; the secondary rule passes it.")}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
