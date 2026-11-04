#!/usr/bin/env python
"""Verify the point-4 workbook cell by cell against the saved scores.

This script shares no code with the builder. It reads the frozen label table and the
saved predictions of the winning arm and of the November reference run, recomputes
every numeric cell of the workbook from those files alone, and compares cell by cell.
A cell that does not match is named with its sheet, coordinate, row label and column
header, and the script exits 1. It also checks the sheet list, the required headings,
and that no cell carries a path, a script name, an internal column id or an em dash.

Usage:  python verify_point4_workbook.py [workbook.xlsx]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(r"D:\fmd-analysis")
ARM = ROOT / "run" / "multilabel_ooi_20261104" / "combined"
NOV = ROOT / "run" / "multilabel_lp_v8_20261103" / "b"
LABELS = ROOT / "run" / "ooi_matrix_20261104" / "ooi_labels.csv"
DEFAULT_WB = ROOT / "reports" / "multilabel_production" / "ooi_point4_workbook_20261104.xlsx"

SHEETS = ["Summary", "Object classes", "Thresholds", "F1 against the cut",
          "Pass-fail", "Method notes", "Definitions"]
SPLIT_N, VAL_N, TEST_N = 7470, 1110, 1121
GUARD = 10
GRID = [round(0.05 * i, 2) for i in range(1, 20)]
TOL = 1e-9

LENS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD", "P1_COC",
        "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]
LENS_NAME = {
    "P1_MPP": "Missing Primary Package", "P1_ML": "Multiple Lenses",
    "P2_LOC": "Lens Off Center", "P2_DC": "Dirty Camera", "P1_NL": "No Lens",
    "P1_FL": "Folded Lens", "P2_LD": "Low Dose", "P1_COC": "Cavity Off Center",
    "P2_DS": "Dirty Strobe", "P2_FOV": "View Obstructed", "P2_BSC": "Bubble Scatter",
    "P1_PPM": "Package Misalignment",
}
OBJ = ["class_bubble", "class_bubble_cluster", "class_foreign_matter", "class_fiber",
       "class_wet_package", "class_hema", "class_extraneous_polymer"]
OBJ_NAME = {
    "class_bubble": "Bubble", "class_bubble_cluster": "Bubble Cluster",
    "class_foreign_matter": "Foreign Matter", "class_fiber": "Fiber",
    "class_wet_package": "Wet Package", "class_hema": "HEMA",
    "class_extraneous_polymer": "Extraneous Polymer",
    "class_surface_groove": "Surface Groove",
}
FAIL_OBJ = ["class_wet_package", "class_foreign_matter", "class_fiber",
            "class_extraneous_polymer", "class_hema", "class_surface_groove"]
GATED = ["class_foreign_matter", "class_fiber", "class_extraneous_polymer",
         "class_hema"]

FAIL_ROLE = "Fails the picture"
PASS_ROLE = "Pass class, never fails a picture"
TUNED = "Tuned on validation: best F1, ties to the higher cut"
GUARDED = "Held at 0.5 by the guard: fewer than 10 validation pictures"
NOT_TRAINED = "Not trained: no positive pictures anywhere in the split"

BANNED = [".py", ".npz", ".csv", ".xlsx", ".json", "D:", "\\", "run/", "experiments/",
          "docs/", "predictions", "P1_", "P2_", "class_", "gate_", "md5", "—",
          "train_multilabel", "build_point4", "verify_point4", "ticket", "metrics",
          "thresholds.json", "ooi_labels"]


# ---------------------------------------------------------------- recomputation
def ap(y, s):
    """Average precision: mean precision at the rank of each true positive."""
    order = np.argsort(-s, kind="stable")
    yt = y[order]
    cum = np.cumsum(yt)
    rank = np.arange(1, len(yt) + 1)
    return float((cum / rank)[yt == 1].mean()) if int(yt.sum()) else float("nan")


def f1(y, s, cut):
    hit = s >= cut
    tp = int(np.count_nonzero(hit & (y == 1)))
    fp = int(np.count_nonzero(hit & (y == 0)))
    fn = int(np.count_nonzero(~hit & (y == 1)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def columns_firing(score, cols, cut_names, cuts, mode):
    """OR over the named columns, looked up in the model's own column list."""
    out = np.zeros(score.shape[0], dtype=bool)
    for name in cut_names:
        cut = 0.5 if mode == "0.5" else cuts[name]
        out = out | (score[:, cols.index(name)] >= cut)
    return out


def measures(fire, is_fail, is_clear):
    fail_n = int(np.count_nonzero(is_fail))
    clear_n = int(np.count_nonzero(is_clear))
    pass_n = int(np.count_nonzero(~is_fail))
    caught = int(np.count_nonzero(fire & is_fail))
    wrongly = int(np.count_nonzero(fire & is_clear))
    pass_kept = int(np.count_nonzero(~fire & ~is_fail))
    return {
        "caught_n": caught, "caught": caught / fail_n,
        "clear_passed_n": clear_n - wrongly,
        "clear_passed": (clear_n - wrongly) / clear_n,
        "clear_wrong_n": wrongly,
        "bubble_only_n": pass_kept - (clear_n - wrongly),
        "pass_kept_n": pass_kept, "pass_kept": pass_kept / pass_n,
    }


def expected_claims():
    """Every numeric cell of the workbook, recomputed from the saved scores."""
    with open(LABELS, newline="", encoding="utf-8") as fh:
        lab = list(csv.DictReader(fh))

    def vec(name):
        return np.array([int(r[name]) for r in lab])

    split = np.array([r["split"] for r in lab])
    md5 = np.array([r["picture_md5"] for r in lab])
    lens_true = np.stack([vec(c) for c in LENS], axis=1)
    fail_obj_true = np.stack([vec(c) for c in FAIL_OBJ], axis=1)
    obj_true = np.stack([vec(c) for c in OBJ], axis=1)
    clear_all = vec("clear").astype(bool)
    fail_all = (lens_true.sum(axis=1) + fail_obj_true.sum(axis=1)) > 0

    # ---- winning arm
    arm = np.load(ARM / "predictions.npz", allow_pickle=False)
    cols = [str(c) for c in arm["columns"]]
    gate_cols = [str(c) for c in arm["gated_columns"]]
    where = {m: i for i, m in enumerate(md5)}
    trow = np.array([where[str(m)] for m in arm["test_md5"]])
    score = arm["test_score"]
    truth = arm["test_true"]
    vscore = arm["val_score"]
    vtruth = arm["val_true"]
    gate = arm["test_gate"]
    cuts = {}
    import json
    with open(ARM / "thresholds.json", encoding="utf-8") as fh:
        th = json.load(fh)
    for name in cols:
        cuts[name] = float(th["per_class"][name]["threshold"])

    fail_t = fail_all[trow]
    clear_t = clear_all[trow]
    pass_t = ~fail_t
    n_fail = int(np.count_nonzero(fail_t))
    n_clear = int(np.count_nonzero(clear_t))
    n_pass = int(np.count_nonzero(pass_t))
    assert (n_fail, n_clear, n_pass - n_clear) == (768, 317, 36)

    fail_cols = LENS + [c for c in FAIL_OBJ if c in cols]
    arm_cut_fire = columns_firing(score, cols, fail_cols, cuts, "chosen")
    # the OR at the chosen cuts, column by column, using the model's own column list
    arm_chosen = np.zeros(score.shape[0], dtype=bool)
    for name in fail_cols:
        arm_chosen |= score[:, cols.index(name)] >= cuts[name]
    arm_half = np.zeros(score.shape[0], dtype=bool)
    for name in fail_cols:
        arm_half |= score[:, cols.index(name)] >= 0.5
    assert np.array_equal(arm_cut_fire, arm_chosen)
    arm_half_m = measures(arm_half, fail_t, clear_t)
    arm_chosen_m = measures(arm_chosen, fail_t, clear_t)

    # ---- November run
    nov = np.load(NOV / "predictions.npz", allow_pickle=False)
    ncols = [str(c) for c in nov["columns"]]
    nwhere = {m: i for i, m in enumerate(md5)}
    nrow = np.array([nwhere[str(m)] for m in nov["test_md5"]])
    nscore = nov["test_score"]
    ntruth = nov["test_true"]
    with open(NOV / "thresholds.json", encoding="utf-8") as fh:
        nth = json.load(fh)
    ncuts = {c: float(nth["per_class"][c]["threshold"]) for c in ncols}
    nov_fail_t = fail_all[nrow]
    nov_clear_t = clear_all[nrow]
    nov_half = np.zeros(nscore.shape[0], dtype=bool)
    nov_chosen = np.zeros(nscore.shape[0], dtype=bool)
    for i, name in enumerate(ncols):
        nov_half |= nscore[:, i] >= 0.5
        nov_chosen |= nscore[:, i] >= ncuts[name]
    nov_half_m = measures(nov_half, nov_fail_t, nov_clear_t)
    nov_chosen_m = measures(nov_chosen, nov_fail_t, nov_clear_t)

    # recorded reference: twelve lens tags at 0.5, lens scope
    ref_half = np.zeros(nscore.shape[0], dtype=bool)
    for i in range(12):
        ref_half |= nscore[:, i] >= 0.5
    ref_truth = ntruth[:, :12].sum(axis=1) > 0
    ref_m = measures(ref_half, ref_truth, ~ref_truth)
    assert (ref_m["caught_n"], int(np.count_nonzero(ref_truth)),
            int(np.count_nonzero(~ref_truth)), ref_m["clear_wrong_n"]) == \
        (589, 684, 437, 12), ref_m

    # ---- object classes
    obj = {}
    ap_list, f_half_list, f_chosen_list, floor_list = [], [], [], []
    for name in OBJ:
        i = cols.index(name)
        y, s = truth[:, i], score[:, i]
        npos = int(np.count_nonzero(y == 1))
        entry = {
            "test_n": npos,
            "val_n": int(np.count_nonzero(vtruth[:, i] == 1)),
            "split_n": int(np.count_nonzero(obj_true[:, OBJ.index(name)] == 1)),
            "floor": npos / TEST_N,
            "ap": ap(y, s),
            "f1_05": f1(y, s, 0.5),
            "f1_cut": f1(y, s, cuts[name]),
            "cut": cuts[name],
        }
        obj[OBJ_NAME[name]] = entry
        ap_list.append(entry["ap"])
        f_half_list.append(entry["f1_05"])
        f_chosen_list.append(entry["f1_cut"])
        floor_list.append(entry["floor"])
    macro = {
        "floor": float(np.mean(floor_list)), "ap": float(np.mean(ap_list)),
        "f1_05": float(np.mean(f_half_list)), "f1_cut": float(np.mean(f_chosen_list)),
    }
    n_above = sum(1 for name in OBJ if obj[OBJ_NAME[name]]["ap"]
                  > obj[OBJ_NAME[name]]["floor"])

    # ---- lens macros, judgeable by at least 20 test pictures
    judgeable = [c for c in LENS if int(np.count_nonzero(
        truth[:, cols.index(c)] == 1)) >= 20]
    arm_lens = float(np.mean([ap(truth[:, cols.index(c)], score[:, cols.index(c)])
                              for c in judgeable]))
    nov_lens = float(np.mean([ap(ntruth[:, ncols.index(c)], nscore[:, ncols.index(c)])
                              for c in judgeable]))

    # ---- F1 against the cut
    curves = {}
    for name in OBJ:
        i = cols.index(name)
        curves[OBJ_NAME[name]] = [f1(truth[:, i], score[:, i], t) for t in GRID]

    # ---- confusion, truth pair against predicted pair
    bi, ci = cols.index("class_bubble"), cols.index("class_bubble_cluster")

    def pair(b, cl):
        if b and cl:
            return "both"
        if b:
            return "bubble_only"
        if cl:
            return "cluster_only"
        return "neither"

    confusion = {}
    for tag, cb, cc in (("0.5", 0.5, 0.5),
                        ("chosen", cuts["class_bubble"],
                         cuts["class_bubble_cluster"])):
        block = {}
        for tb in (True, False):
            for tcl in (True, False):
                row_mask = ((truth[:, bi] == 1) == tb) & ((truth[:, ci] == 1) == tcl)
                pb = score[:, bi] >= cb
                pc = score[:, ci] >= cc
                cells = {}
                for pv in (True, False):
                    for qv in (True, False):
                        cells[pair(pv, qv)] = int(np.count_nonzero(
                            row_mask & (pb == pv) & (pc == qv)))
                block[pair(tb, tcl)] = cells
        confusion[tag] = block

    # ---- thresholds
    th_rows = []
    for name in LENS + OBJ:
        i = cols.index(name)
        val_pos = int(np.count_nonzero(vtruth[:, i] == 1))
        tuned = val_pos >= GUARD
        th_rows.append({
            "name": LENS_NAME[name] if name in LENS else OBJ_NAME[name],
            "role": FAIL_ROLE if (name in LENS or name in FAIL_OBJ) else PASS_ROLE,
            "val_n": val_pos,
            "test_n": int(np.count_nonzero(truth[:, i] == 1)),
            "cut": cuts[name],
            "source": TUNED if tuned else GUARDED,
            "val_f1": f1(vtruth[:, i], vscore[:, i], cuts[name]),
        })

    # ---- recall by flag
    rbf = {}
    for name in GATED:
        i = cols.index(name)
        j = gate_cols.index(name.replace("class_", "gate_"))
        positives = truth[:, i] == 1
        flagged = gate[:, j] == 1
        entry = {}
        for side, mask in (("gated", positives & flagged),
                           ("ungated", positives & ~flagged)):
            n = int(np.count_nonzero(mask))
            entry[side] = {
                "n": n,
                "recall_05": (float(np.mean(score[mask, i] >= 0.5)) if n else None),
                "recall_cut": (float(np.mean(score[mask, i] >= cuts[name]))
                               if n else None),
            }
        rbf[OBJ_NAME[name]] = entry

    claims = {}

    def put(sheet, row_label, col_header, value):
        claims[(sheet, str(row_label), col_header)] = value

    # ---------------- Summary
    s1 = ["Fail pictures caught (share of the 768 test pictures that fail the rule)",
          "Clear pictures passed (share of the 317 clear test pictures)",
          "Clear wrongly failed (count out of the 317 clear test pictures)",
          "Pass pictures predicted pass (share of the 353 test pictures that pass "
          "the rule)"]
    for label, m in (("Point-4 model at 0.5", arm_half_m),
                     ("Point-4 model at its chosen cuts", arm_chosen_m),
                     ("November model at 0.5", nov_half_m),
                     ("November model at its chosen cuts", nov_chosen_m)):
        for head, key in zip(s1, ("caught", "clear_passed", "clear_wrong_n",
                                  "pass_kept")):
            put("Summary", label, head, m[key])
    s2 = ["Fail pictures caught (share of the 684 lens-tagged test pictures)",
          "Clear pictures passed (share of the 437 test pictures without a lens tag)",
          "Clear wrongly failed (count out of the 437 test pictures without a lens tag)"]
    for head, key in zip(s2, ("caught", "clear_passed", "clear_wrong_n")):
        put("Summary", "November reference at 0.5", head, ref_m[key])
    s3 = {
        "Macro average precision, seven supported object classes": macro["ap"],
        "Macro prevalence floor, seven supported object classes": macro["floor"],
        "Object classes scoring above their own floor": n_above,
        "Macro average precision, eight judgeable lens classes, this model": arm_lens,
        "Macro average precision, eight judgeable lens classes, November reference":
            nov_lens,
        "Change in the lens macro average precision": arm_lens - nov_lens,
        "Stability band": 0.01,
    }
    s3_against = {
        "Macro average precision, seven supported object classes":
            "Macro prevalence floor over the same seven classes",
        "Macro prevalence floor, seven supported object classes":
            "Share of the 1,121 test pictures carrying the class, averaged",
        "Object classes scoring above their own floor":
            "Of the seven supported object classes on the test split",
        "Macro average precision, eight judgeable lens classes, this model":
            "November reference on the same eight classes",
        "Macro average precision, eight judgeable lens classes, November reference":
            "Recomputed from the November run's own saved scores",
        "Change in the lens macro average precision":
            "Stability band of 0.01 agreed before the runs",
        "Stability band": "Change beyond the band is reported as a move",
    }
    for label, value in s3.items():
        put("Summary", label, "Value", value)
        put("Summary", label, "What it is measured against", s3_against[label])

    # ---------------- Object classes
    obj_head = ["Test pictures with the class (of 1,121)",
                "Validation pictures with the class (of 1,110)",
                "Split pictures with the class (of 7,470)",
                "Prevalence floor for average precision, test (share of 1,121)",
                "Average precision, test", "F1 at 0.5, test",
                "F1 at the chosen cut, test", "Chosen cut"]
    for name in OBJ:
        e = obj[OBJ_NAME[name]]
        for head, key in zip(obj_head,
                             ("test_n", "val_n", "split_n", "floor", "ap", "f1_05",
                              "f1_cut", "cut")):
            put("Object classes", OBJ_NAME[name], head, e[key])
    macro_row = {"Prevalence floor for average precision, test (share of 1,121)":
                 macro["floor"], "Average precision, test": macro["ap"],
                 "F1 at 0.5, test": macro["f1_05"],
                 "F1 at the chosen cut, test": macro["f1_cut"]}
    for head in ("Test pictures with the class (of 1,121)",
                 "Validation pictures with the class (of 1,110)",
                 "Split pictures with the class (of 7,470)", "Chosen cut"):
        macro_row[head] = None
    for head, value in macro_row.items():
        put("Object classes", "Macro over the seven supported classes", head, value)
    groove_row = {"Test pictures with the class (of 1,121)": 0,
                  "Validation pictures with the class (of 1,110)": 0,
                  "Split pictures with the class (of 7,470)": 0,
                  "Prevalence floor for average precision, test (share of 1,121)": 0.0,
                  "Average precision, test": None, "F1 at 0.5, test": None,
                  "F1 at the chosen cut, test": None, "Chosen cut": None}
    for head, value in groove_row.items():
        put("Object classes", "Surface Groove", head, value)
    conf_head = ["Predicted both", "Predicted Bubble only", "Predicted Cluster only",
                 "Predicted neither"]
    truth_labels = [("Truth both", "both"), ("Truth Bubble only", "bubble_only"),
                    ("Truth Cluster only", "cluster_only"),
                    ("Truth neither", "neither")]
    for tag, block_label in (("0.5", "At 0.5"), ("chosen", "At the chosen cuts")):
        for row_label, key in truth_labels:
            for head, pkey in zip(conf_head,
                                  ("both", "bubble_only", "cluster_only", "neither")):
                put("Object classes", f"{block_label}|{row_label}", head,
                    confusion[tag][key][pkey])

    # ---------------- Thresholds
    th_head = ["Role in the pass/fail rule",
               "Validation pictures with the class (of 1,110)",
               "Test pictures with the class (of 1,121)", "Chosen cut",
               "Where the cut came from", "Validation F1 at the chosen cut"]
    for row in th_rows:
        for head, key in zip(th_head,
                             ("role", "val_n", "test_n", "cut", "source", "val_f1")):
            put("Thresholds", row["name"], head, row[key])
    put("Thresholds", "Surface Groove", "Role in the pass/fail rule", FAIL_ROLE)
    put("Thresholds", "Surface Groove", "Validation pictures with the class "
        "(of 1,110)", 0)
    put("Thresholds", "Surface Groove", "Test pictures with the class (of 1,121)", 0)
    put("Thresholds", "Surface Groove", "Chosen cut", None)
    put("Thresholds", "Surface Groove", "Where the cut came from", NOT_TRAINED)
    put("Thresholds", "Surface Groove", "Validation F1 at the chosen cut", None)

    # ---------------- F1 against the cut
    for name in OBJ:
        label = OBJ_NAME[name]
        i = cols.index(name)
        put("F1 against the cut", "Chosen cut", label, cuts[name])
        put("F1 against the cut", "F1 at the chosen cut", label,
            f1(truth[:, i], score[:, i], cuts[name]))
    for k, t in enumerate(GRID):
        for name in OBJ:
            put("F1 against the cut", t, OBJ_NAME[name], curves[OBJ_NAME[name]][k])

    # ---------------- Pass-fail
    pf_head = ["Fail pictures caught (count of the 768)",
               "Fail pictures caught (share of the 768)",
               "Clear pictures passed (count of the 317)",
               "Clear pictures passed (share of the 317)",
               "Clear wrongly failed (count of the 317)",
               "Bubble-only pictures passed (count of the 36)",
               "Pass pictures predicted pass (count of the 353)",
               "Pass pictures predicted pass (share of the 353)"]
    for label, m in (("Point-4 model at 0.5", arm_half_m),
                     ("Point-4 model at its chosen cuts", arm_chosen_m),
                     ("November model at 0.5", nov_half_m),
                     ("November model at its chosen cuts", nov_chosen_m)):
        for head, key in zip(pf_head, ("caught_n", "caught", "clear_passed_n",
                                       "clear_passed", "clear_wrong_n", "bubble_only_n",
                                       "pass_kept_n", "pass_kept")):
            put("Pass-fail", label, head, m[key])
    pf2 = ["Fail pictures caught (count of the 684 lens-tagged test pictures)",
           "Fail pictures caught (share of the 684 lens-tagged test pictures)",
           "Clear pictures passed (count of the 437 test pictures without a lens tag)",
           "Clear pictures passed (share of the 437 test pictures without a lens tag)",
           "Clear wrongly failed (count of the 437 test pictures without a lens tag)"]
    for head, key in zip(pf2, ("caught_n", "caught", "clear_passed_n", "clear_passed",
                               "clear_wrong_n")):
        put("Pass-fail", "November reference at 0.5", head, ref_m[key])

    # ---------------- Method notes
    rb_head = ["Gated test pictures with the class",
               "Recall on gated test pictures at 0.5",
               "Recall on gated test pictures at the chosen cut",
               "Un-gated test pictures with the class",
               "Recall on un-gated test pictures at 0.5",
               "Recall on un-gated test pictures at the chosen cut"]
    for name in GATED:
        e = rbf[OBJ_NAME[name]]
        for head, value in zip(rb_head, (e["gated"]["n"], e["gated"]["recall_05"],
                                         e["gated"]["recall_cut"],
                                         e["ungated"]["n"],
                                         e["ungated"]["recall_05"],
                                         e["ungated"]["recall_cut"])):
            put("Method notes", OBJ_NAME[name], head, value)

    return claims


# ---------------------------------------------------------------- comparison
def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, int) and isinstance(b, int):
            return a == b
        return abs(float(a) - float(b)) <= TOL
    return str(a) == str(b)


def fmt(v):
    if v is None:
        return "empty"
    if isinstance(v, float):
        return "%.10g" % v
    return repr(v)


def read_tables(ws, headers):
    """Row indices where the exact header tuple appears in the sheet."""
    hits = []
    width = len(headers)
    for row in ws.iter_rows():
        values = [c.value for c in row[:width]]
        if values == list(headers):
            hits.append(row[0].row)
    return hits


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_WB
    if not path.exists():
        print("workbook not found:", path)
        return 1
    wb = load_workbook(path, data_only=True)
    errors = []
    checked = [0]
    compared = set()

    if wb.sheetnames != SHEETS:
        errors.append("sheet list is %r, expected %r" % (wb.sheetnames, SHEETS))

    claims = expected_claims()

    # ---- tables, in the workbook's own layout
    tables = [
        ("Summary",
         ["Model and operating point",
          "Fail pictures caught (share of the 768 test pictures that fail the rule)",
          "Clear pictures passed (share of the 317 clear test pictures)",
          "Clear wrongly failed (count out of the 317 clear test pictures)",
          "Pass pictures predicted pass (share of the 353 test pictures that pass "
          "the rule)"],
         ["Point-4 model at 0.5", "Point-4 model at its chosen cuts",
          "November model at 0.5", "November model at its chosen cuts"], None),
        ("Summary",
         ["Operating point",
          "Fail pictures caught (share of the 684 lens-tagged test pictures)",
          "Clear pictures passed (share of the 437 test pictures without a lens tag)",
          "Clear wrongly failed (count out of the 437 test pictures without a lens tag)"],
         ["November reference at 0.5"], None),
        ("Summary", ["Measure", "Value", "What it is measured against"], None,
         "summary"),
        ("Object classes",
         ["Class", "Test pictures with the class (of 1,121)",
          "Validation pictures with the class (of 1,110)",
          "Split pictures with the class (of 7,470)",
          "Prevalence floor for average precision, test (share of 1,121)",
          "Average precision, test", "F1 at 0.5, test",
          "F1 at the chosen cut, test", "Chosen cut"],
         ["Bubble", "Bubble Cluster", "Foreign Matter", "Fiber", "Wet Package",
          "HEMA", "Extraneous Polymer", "Macro over the seven supported classes",
          "Surface Groove"], None),
        ("Object classes",
         ["Truth pair", "Predicted both", "Predicted Bubble only",
          "Predicted Cluster only", "Predicted neither"],
         ["Truth both", "Truth Bubble only", "Truth Cluster only",
          "Truth neither"], "confusion"),
        ("Thresholds",
         ["Class", "Role in the pass/fail rule",
          "Validation pictures with the class (of 1,110)",
          "Test pictures with the class (of 1,121)", "Chosen cut",
          "Where the cut came from", "Validation F1 at the chosen cut"],
         [LENS_NAME[c] for c in LENS] + [OBJ_NAME[c] for c in OBJ] + ["Surface Groove"],
         None),
        ("F1 against the cut", ["Score cut"] + [OBJ_NAME[c] for c in OBJ],
         ["Chosen cut", "F1 at the chosen cut"] + GRID, "f1"),
        ("Pass-fail",
         ["Model and operating point",
          "Fail pictures caught (count of the 768)",
          "Fail pictures caught (share of the 768)",
          "Clear pictures passed (count of the 317)",
          "Clear pictures passed (share of the 317)",
          "Clear wrongly failed (count of the 317)",
          "Bubble-only pictures passed (count of the 36)",
          "Pass pictures predicted pass (count of the 353)",
          "Pass pictures predicted pass (share of the 353)"],
         ["Point-4 model at 0.5", "Point-4 model at its chosen cuts",
          "November model at 0.5", "November model at its chosen cuts"], None),
        ("Pass-fail",
         ["Operating point",
          "Fail pictures caught (count of the 684 lens-tagged test pictures)",
          "Fail pictures caught (share of the 684 lens-tagged test pictures)",
          "Clear pictures passed (count of the 437 test pictures without a lens tag)",
          "Clear pictures passed (share of the 437 test pictures without a lens tag)",
          "Clear wrongly failed (count of the 437 test pictures without a lens tag)"],
         ["November reference at 0.5"], None),
        ("Method notes",
         ["Class", "Gated test pictures with the class",
          "Recall on gated test pictures at 0.5",
          "Recall on gated test pictures at the chosen cut",
          "Un-gated test pictures with the class",
          "Recall on un-gated test pictures at 0.5",
          "Recall on un-gated test pictures at the chosen cut"],
         ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"], None),
    ]

    for sheet, headers, labels, kind in tables:
        if sheet not in wb.sheetnames:
            errors.append("missing sheet: %s" % sheet)
            continue
        ws = wb[sheet]
        hits = read_tables(ws, headers)
        if not hits:
            errors.append("%s: header row not found, first header %r"
                          % (sheet, headers[0]))
            continue

        if kind == "summary":
            labels = [ws.cell(row=r, column=1).value
                      for r in range(hits[0] + 1, hits[0] + 8)]
            labels = [x for x in labels if x is not None]
            expected_labels = [
                "Macro average precision, seven supported object classes",
                "Macro prevalence floor, seven supported object classes",
                "Object classes scoring above their own floor",
                "Macro average precision, eight judgeable lens classes, this model",
                "Macro average precision, eight judgeable lens classes, November "
                "reference",
                "Change in the lens macro average precision", "Stability band"]
            if labels != expected_labels:
                errors.append("%s: measure rows are %r, expected %r"
                              % (sheet, labels, expected_labels))
                continue
        elif kind == "confusion":
            labels = ["Truth both", "Truth Bubble only", "Truth Cluster only",
                      "Truth neither"]
            # two blocks: at 0.5 first, at the chosen cuts second
            if len(hits) != 2:
                errors.append("%s: found %d confusion tables, expected 2"
                              % (sheet, len(hits)))
                continue
        elif kind == "f1":
            labels = ["Chosen cut", "F1 at the chosen cut"] + GRID
            if len(hits) != 1:
                errors.append("%s: found %d curve tables, expected 1"
                              % (sheet, len(hits)))
                continue
        elif labels is None:
            errors.append("%s: no label list for header %r" % (sheet, headers[0]))
            continue

        block_starts = hits if kind == "confusion" else hits[:1]
        for block_no, start in enumerate(block_starts):
            if kind == "confusion":
                tag = "0.5" if block_no == 0 else "chosen"
                block_label = "At 0.5" if block_no == 0 else "At the chosen cuts"
                above = ws.cell(row=start - 1, column=1).value
                if above != block_label:
                    errors.append("%s!%s: block heading is %r, expected %r"
                                  % (sheet, ws.cell(row=start - 1, column=1).coordinate,
                                     above, block_label))
            for k, label in enumerate(labels):
                row_i = start + 1 + k
                lab_cell = ws.cell(row=row_i, column=1)
                want = label
                got = lab_cell.value
                if isinstance(want, float):
                    label_ok = (isinstance(got, (int, float))
                                and abs(float(got) - want) <= TOL)
                else:
                    label_ok = got == want
                if not label_ok:
                    errors.append("%s!%s: row label is %s, expected %s"
                                  % (sheet, lab_cell.coordinate, fmt(got),
                                     fmt(want)))
                    continue
                claim_key_label = label
                if kind == "confusion":
                    claim_key_label = "%s|%s" % (block_label, label)
                for j, head in enumerate(headers[1:], start=2):
                    cell = ws.cell(row=row_i, column=j)
                    key = (sheet, str(claim_key_label), head)
                    if key not in claims:
                        errors.append("%s!%s: no recomputed value for %r / %r"
                                      % (sheet, cell.coordinate, claim_key_label,
                                         head))
                        continue
                    want_v = claims[key]
                    got_v = cell.value
                    checked[0] += 1
                    compared.add(key)
                    if not same(got_v, want_v):
                        errors.append(
                            "%s!%s [%s / %s]: workbook %s, recomputed %s"
                            % (sheet, cell.coordinate, claim_key_label, head,
                               fmt(got_v), fmt(want_v)))

    # ---- every recomputed value must have been read back from the workbook
    unread = sorted(set(claims) - compared)
    for sheet, label, head in unread[:20]:
        errors.append("%s: not read back from the workbook: %s / %s"
                      % (sheet, label, head))
    if len(unread) > 20:
        errors.append("%s more recomputed values not read back" % (len(unread) - 20))

    # ---- required headings
    required = {
        "Summary": ["Point-4 workbook", "How to read this workbook",
                    "November reference as recorded, lens scope"],
        "Object classes": ["Guide object classes",
                           "Bubble and Bubble Cluster confusion"],
        "Thresholds": ["Chosen cuts and the guard"],
        "F1 against the cut": ["F1 for the seven supported object classes"],
        "Pass-fail": ["Block A", "Block B: the November reference as recorded"],
        "Method notes": ["Recall by flag: gated versus un-gated class positives",
                         "Reading limits"],
        "Definitions": ["Definitions"],
    }
    for sheet, fragments in required.items():
        if sheet not in wb.sheetnames:
            continue
        texts = [str(c.value) for row in wb[sheet].iter_rows() for c in row
                 if c.value is not None]
        for frag in fragments:
            if not any(frag in t for t in texts):
                errors.append("%s: required heading missing: %r" % (sheet, frag))

    # ---- definitions sheet must carry every term
    if "Definitions" in wb.sheetnames:
        ws = wb["Definitions"]
        terms = [ws.cell(row=r, column=1).value
                 for r in range(1, ws.max_row + 1)]
        for term in ["Frozen split", "Test split", "Clear picture", "Pass picture",
                     "Fail picture", "Fail classes", "Pass classes", "Caught",
                     "Clear pictures passed", "Clear wrongly failed",
                     "Average precision", "Prevalence floor", "F1", "Chosen cut",
                     "Guard", "Judgeable class", "Stability band"]:
            if term not in terms:
                errors.append("Definitions: term missing: %r" % term)

    # ---- client-safe sweep
    for sheet in wb.sheetnames:
        for row in wb[sheet].iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    for token in BANNED:
                        if token in cell.value:
                            errors.append("%s!%s: client-safe breach, %r in %r"
                                          % (sheet, cell.coordinate, token,
                                             cell.value[:70]))

    print("checked %d numeric cells against the saved scores" % checked[0])
    if errors:
        print("FAILED: %d problem(s)" % len(errors))
        for e in errors[:40]:
            print("  -", e)
        if len(errors) > 40:
            print("  ... %d more" % (len(errors) - 40))
        return 1
    print("OK: every checked cell reproduces from the saved scores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
