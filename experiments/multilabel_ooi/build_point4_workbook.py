#!/usr/bin/env python
"""Build the point-4 workbook: the pass/fail rule, the guide object classes, the cuts.

Reads the winning arm's saved predictions, the frozen label table and the November
reference run, recomputes every number from those files, and writes one workbook
under reports/multilabel_production/. The verifier (verify_point4_workbook.py)
recomputes the same cells independently and fails on a tampered cell.

Client-safe rules enforced on the finished workbook: no paths, no script names, no
internal column ids, no em dashes, every count names its population.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(r"D:\fmd-analysis")
ARM_DIR = ROOT / "run" / "multilabel_ooi_20261104" / "combined"
NOV_DIR = ROOT / "run" / "multilabel_lp_v8_20261103" / "b"
LABELS = ROOT / "run" / "ooi_matrix_20261104" / "ooi_labels.csv"
OUT = ROOT / "reports" / "multilabel_production" / "ooi_point4_workbook_20261104.xlsx"

SPLIT_N = 7470
TRAIN_N, VAL_N, TEST_N = 5239, 1110, 1121
GUARD = 10
GRID = [round(0.05 * i, 2) for i in range(1, 20)]
BAND = 0.01

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

# ---------------------------------------------------------------- style helpers
TITLE_FONT = Font(bold=True, size=13)
H2_FONT = Font(bold=True, size=11)
HEAD_FONT = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="365F91")
NOTE_FONT = Font(italic=True, size=10, color="404040")
THIN = Side(style="thin", color="B0B0B0")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


# ---------------------------------------------------------------- computations
def average_precision(y, s):
    """Sum of precision at each positive rank, positives in descending score order."""
    order = np.argsort(-s, kind="stable")
    yt = y[order]
    tp = np.cumsum(yt)
    ranks = np.arange(1, len(yt) + 1)
    return float((tp / ranks)[yt == 1].mean()) if yt.sum() else float("nan")


def f1_at(y, s, cut):
    pred = s >= cut
    tp = int(np.sum(pred & (y == 1)))
    fp = int(np.sum(pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1)))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def fire_mask(score, cols, cut_names, cuts, mode):
    """True where a fail column is at or above its cut for this operating point."""
    mask = np.zeros(score.shape[0], dtype=bool)
    idx = [cols.index(c) for c in cut_names]
    cut_vec = np.array([0.5 if mode == "0.5" else cuts[c] for c in cut_names])
    by_index = (score[:, idx] >= cut_vec).any(axis=1)
    for i, c in zip(idx, cut_names):
        cut = 0.5 if mode == "0.5" else cuts[c]
        mask |= score[:, i] >= cut
    assert np.array_equal(mask, by_index), "column indexing disagrees"
    return mask


def pass_fail(fire, fail_truth, clear):
    """The four measures of the rule, each with its population."""
    fail_n = int(fail_truth.sum())
    clear_n = int(clear.sum())
    pass_n = int((~fail_truth).sum())
    caught = int(np.sum(fire & fail_truth))
    wrongly = int(np.sum(fire & clear))
    clear_passed = clear_n - wrongly
    pass_passed = int(np.sum(~fire & ~fail_truth))
    return {
        "caught_n": caught, "caught_den": fail_n, "caught": caught / fail_n,
        "clear_passed_n": clear_passed, "clear_den": clear_n,
        "clear_passed": clear_passed / clear_n,
        "clear_wrong_n": wrongly,
        "pass_passed_n": pass_passed, "pass_den": pass_n,
        "pass_passed": pass_passed / pass_n,
        "bubble_only_passed_n": pass_passed - clear_passed,
        "bubble_only_den": pass_n - clear_n,
    }


def load_label_table():
    with open(LABELS, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    def col(name):
        return np.array([int(r[name]) for r in rows])

    split = np.array([r["split"] for r in rows])
    lens = np.stack([col(c) for c in LENS], axis=1)
    fail_obj = np.stack([col(c) for c in FAIL_OBJ], axis=1)
    return {
        "rows": rows,
        "md5": np.array([r["picture_md5"] for r in rows]),
        "split": split,
        "clear": col("clear").astype(bool),
        "lens": lens,
        "fail_obj": fail_obj,
        "obj": np.stack([col(c) for c in OBJ], axis=1),
        "fail": (lens.sum(1) + fail_obj.sum(1)) > 0,
    }


def main():
    lab = load_label_table()
    rows, md5, split = lab["rows"], lab["md5"], lab["split"]
    fail_all, clear_all = lab["fail"], lab["clear"]

    # ---- frozen split counts, asserted against the agreed rule
    split_fail = int(fail_all.sum())
    split_pass = int((~fail_all).sum())
    split_clear = int(clear_all.sum())
    split_bubble_only = int(((~fail_all) & (~clear_all)).sum())
    assert (split_fail, split_pass, split_clear, split_bubble_only) == (5157, 2313,
                                                                       2117, 196), \
        (split_fail, split_pass, split_clear, split_bubble_only)

    # ---- winning arm
    d = np.load(ARM_DIR / "predictions.npz", allow_pickle=False)
    cols = [str(c) for c in d["columns"]]
    gated_cols = [str(c) for c in d["gated_columns"]]
    order = {m: i for i, m in enumerate(md5)}
    idx = np.array([order[str(m)] for m in d["test_md5"]])
    vidx = np.array([order[str(m)] for m in d["val_md5"]])
    score = d["test_score"]
    true = d["test_true"]
    vscore = d["val_score"]
    vtrue = d["val_true"]
    gate = d["test_gate"]
    assert set(d["test_md5"]) == set(md5[split == "test"])

    with open(ARM_DIR / "thresholds.json", encoding="utf-8") as fh:
        arm_th = json.load(fh)
    with open(ARM_DIR / "metrics.json", encoding="utf-8") as fh:
        arm_met = json.load(fh)
    cuts = {c: float(arm_th["per_class"][c]["threshold"]) for c in cols}
    for c in cols:
        assert abs(cuts[c] - float(arm_th["per_class"][c]["threshold"])) < 1e-12

    fail_t = fail_all[idx]
    clear_t = clear_all[idx]
    pass_t = ~fail_t
    n_fail, n_clear, n_pass = int(fail_t.sum()), int(clear_t.sum()), int(pass_t.sum())
    n_bubble_only = n_pass - n_clear
    assert (n_fail, n_clear, n_bubble_only) == (768, 317, 36), (n_fail, n_clear,
                                                                n_bubble_only)

    fail_cols = LENS + [c for c in FAIL_OBJ if c in cols]
    assert len(fail_cols) == 17 and "class_surface_groove" not in cols

    arm_05 = fire_mask(score, cols, fail_cols, cuts, "0.5")
    arm_cut = fire_mask(score, cols, fail_cols, cuts, "chosen")
    arm_pf_05 = pass_fail(arm_05, fail_t, clear_t)
    arm_pf_cut = pass_fail(arm_cut, fail_t, clear_t)

    # ---- November reference run
    dn = np.load(NOV_DIR / "predictions.npz", allow_pickle=False)
    ncols = [str(c) for c in dn["columns"]]
    norder = {m: i for i, m in enumerate(md5)}
    nidx = np.array([norder[str(m)] for m in dn["test_md5"]])
    nscore = dn["test_score"]
    ntrue = dn["test_true"]
    with open(NOV_DIR / "thresholds.json", encoding="utf-8") as fh:
        nov_th = json.load(fh)
    ncuts = {c: float(nov_th["per_class"][c]["threshold"]) for c in ncols}
    nov_fail_t = fail_all[nidx]
    nov_clear_t = clear_all[nidx]
    nov_05 = fire_mask(nscore, ncols, ncols, ncuts, "0.5")
    nov_cut = fire_mask(nscore, ncols, ncols, ncuts, "chosen")
    nov_pf_05 = pass_fail(nov_05, nov_fail_t, nov_clear_t)
    nov_pf_cut = pass_fail(nov_cut, nov_fail_t, nov_clear_t)

    # reference as recorded: the twelve lens tags at 0.5, lens scope
    lens_fire = (nscore[:, :12] >= 0.5).any(1)
    lens_truth = ntrue[:, :12].sum(1) > 0
    lens_clear = ~lens_truth
    ref = pass_fail(lens_fire, lens_truth, lens_clear)
    assert (ref["caught_n"], ref["caught_den"], ref["clear_den"],
            ref["clear_wrong_n"]) == (589, 684, 437, 12), ref
    assert round(ref["caught"] * 100, 1) == 86.1
    assert round(ref["clear_passed"] * 100, 1) == 97.3

    # ---- object class table
    obj_rows = []
    aps, f1_05s, f1_cuts, floors = [], [], [], []
    for c in OBJ:
        i = cols.index(c)
        y, s = true[:, i], score[:, i]
        npos = int(y.sum())
        val_pos = int(vtrue[:, i].sum())
        split_pos = int(lab["obj"][:, OBJ.index(c)].sum())
        ap = average_precision(y, s)
        a05 = f1_at(y, s, 0.5)
        ach = f1_at(y, s, cuts[c])
        aps.append(ap)
        f1_05s.append(a05)
        f1_cuts.append(ach)
        floors.append(npos / TEST_N)
        obj_rows.append({
            "name": OBJ_NAME[c], "test_n": npos, "val_n": val_pos,
            "split_n": split_pos, "floor": npos / TEST_N, "ap": ap,
            "f1_05": a05, "f1_cut": ach, "cut": cuts[c],
        })
    assert abs(float(np.mean(aps)) - arm_met["macro_ap_supported"]) < 1e-9
    macro = {
        "floor": float(np.mean(floors)), "ap": float(np.mean(aps)),
        "f1_05": float(np.mean(f1_05s)), "f1_cut": float(np.mean(f1_cuts)),
    }

    # ---- lens side, judgeable by test support of at least 20
    lens_test_n = {c: int(true[:, cols.index(c)].sum()) for c in LENS}
    judgeable = sorted([c for c in LENS if lens_test_n[c] >= 20])
    assert judgeable == sorted(arm_met["lens"]["judgeable_classes"]), judgeable
    arm_lens_macro = float(np.mean([average_precision(true[:, cols.index(c)],
                                                      score[:, cols.index(c)])
                                    for c in judgeable]))
    assert abs(arm_lens_macro - arm_met["lens"]["macro_auprc_judgeable"]) < 1e-9
    nov_lens_macro = float(np.mean([average_precision(ntrue[:, ncols.index(c)],
                                                      nscore[:, ncols.index(c)])
                                    for c in judgeable]))
    with open(NOV_DIR / "metrics.json", encoding="utf-8") as fh:
        nov_met = json.load(fh)
    assert abs(nov_lens_macro - nov_met["macro_auprc_judgeable"]) < 1e-9
    lens_delta = arm_lens_macro - nov_lens_macro

    # ---- F1 against the cut, seven supported classes
    curves = {}
    for c in OBJ:
        i = cols.index(c)
        curves[c] = [f1_at(true[:, i], score[:, i], t) for t in GRID]

    # ---- bubble and cluster confusion on the test split
    bi, ci = cols.index("class_bubble"), cols.index("class_bubble_cluster")

    def pair_category(b, cl):
        if b and cl:
            return "both"
        if b:
            return "bubble_only"
        if cl:
            return "cluster_only"
        return "neither"

    confusion = {}
    for mode, c_b, c_cl in (("0.5", 0.5, 0.5),
                            ("chosen", cuts["class_bubble"],
                             cuts["class_bubble_cluster"])):
        table = {}
        for tb in (True, False):
            for tcl in (True, False):
                tkey = pair_category(tb, tcl)
                mask_t = ((true[:, bi] == 1) == tb) & ((true[:, ci] == 1) == tcl)
                pb = score[:, bi] >= c_b
                pcl = score[:, ci] >= c_cl
                row = {}
                for pbv in (True, False):
                    for pclv in (True, False):
                        row[pair_category(pbv, pclv)] = int(
                            np.sum(mask_t & (pb == pbv) & (pcl == pclv)))
                table[tkey] = row
        confusion[mode] = table
    assert confusion["0.5"] == arm_met["bubble_cluster_confusion"]["at_0.5"]
    assert confusion["chosen"] == arm_met["bubble_cluster_confusion"]["at_chosen"]

    # ---- thresholds table
    th_rows = []
    for c in LENS + OBJ:
        rec = arm_th["per_class"][c]
        val_pos = int(vtrue[:, cols.index(c)].sum())
        test_pos = int(true[:, cols.index(c)].sum())
        tuned = val_pos >= GUARD
        assert (rec["source"] == "val") == tuned, (c, rec["source"], val_pos)
        th_rows.append({
            "name": LENS_NAME[c] if c in LENS else OBJ_NAME[c],
            "role": FAIL_ROLE if (c in LENS or c in FAIL_OBJ) else PASS_ROLE,
            "val_n": val_pos, "test_n": test_pos, "cut": cuts[c],
            "source": ("Tuned on validation: best F1, ties to the higher cut"
                       if tuned else
                       "Held at 0.5 by the guard: fewer than 10 validation pictures"),
            "val_f1": f1_at(vtrue[:, cols.index(c)], vscore[:, cols.index(c)],
                            cuts[c]),
            "guard_ok": tuned,
        })

    # ---- recall by flag, gated versus un-gated class positives
    rbf = {}
    for c in GATED:
        i = cols.index(c)
        j = gated_cols.index(c.replace("class_", "gate_"))
        y = true[:, i] == 1
        g = gate[:, j] == 1
        entry = {}
        for name, mask in (("gated", y & g), ("ungated", y & ~g)):
            n_p = int(mask.sum())
            entry[name] = {
                "n": n_p,
                "recall_05": (float(np.mean(score[mask, i] >= 0.5)) if n_p else None),
                "recall_cut": (float(np.mean(score[mask, i] >= cuts[c]))
                               if n_p else None),
            }
        rbf[c] = entry
    for c in GATED:
        rec = arm_met["recall_by_flag"][c]
        for name in ("gated", "ungated"):
            assert rbf[c][name]["n"] == rec[name]["n"], (c, name)
            for key, mine in (("recall_0.5", "recall_05"),
                              ("recall_chosen", "recall_cut")):
                theirs = rec[name][key]
                if theirs is None:
                    assert rbf[c][name][mine] is None, (c, name, key)
                else:
                    assert abs(rbf[c][name][mine] - theirs) < 1e-6, (c, name, key)

    print("pass/fail, winning arm: at 0.5 %s; at chosen cuts %s"
          % ({k: arm_pf_05[k] for k in ("caught_n", "caught", "clear_wrong_n",
                                        "clear_passed", "pass_passed_n")},
             {k: arm_pf_cut[k] for k in ("caught_n", "caught", "clear_wrong_n",
                                         "clear_passed", "pass_passed_n")}))
    print("pass/fail, November model under the rule: at 0.5 %s; at its cuts %s"
          % ({k: nov_pf_05[k] for k in ("caught_n", "caught", "clear_wrong_n")},
             {k: nov_pf_cut[k] for k in ("caught_n", "caught", "clear_wrong_n")}))
    print("recorded reference: caught %d of %d (%.4f), clear passed %d of %d (%.4f), "
          "wrongly failed %d"
          % (ref["caught_n"], ref["caught_den"], ref["caught"],
             ref["clear_passed_n"], ref["clear_den"], ref["clear_passed"],
             ref["clear_wrong_n"]))
    print("object macro AP %.6f (floor %.4f); lens judgeable macro AP %.6f vs %.6f "
          "(%+.4f)" % (macro["ap"], macro["floor"], arm_lens_macro, nov_lens_macro,
                       lens_delta))

    build_workbook(locals())


# ---------------------------------------------------------------- workbook
def build_workbook(ctx):
    g = ctx
    wb = Workbook()

    # ============================================================ Summary
    ws = wb.active
    ws.title = "Summary"
    r = 1
    ws.cell(row=r, column=1, value="Point-4 workbook: the pass/fail rule on the "
                                   "winning model").font = TITLE_FONT
    r += 1
    for line in [
        "Built 2026-11-04 from the saved scores of one multi-label model. Every count "
        "in this workbook names its population.",
        "Populations: one frozen split of 7,470 pictures, 5,239 train, 1,110 "
        "validation, 1,121 test. Rates in this workbook are on the 1,121 test pictures "
        "unless the heading says otherwise.",
        "Under the agreed rule the test split holds 768 pictures that fail, 353 that "
        "pass: 317 clear and 36 carrying nothing but bubble classes.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    r += 1

    ws.cell(row=r, column=1, value="Pass/fail under the agreed rule, test split"
            ).font = H2_FONT
    r += 1
    heads = ["Model and operating point",
             "Fail pictures caught (share of the 768 test pictures that fail the rule)",
             "Clear pictures passed (share of the 317 clear test pictures)",
             "Clear wrongly failed (count out of the 317 clear test pictures)",
             "Pass pictures predicted pass (share of the 353 test pictures that pass "
             "the rule)"]
    start = r
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    for label, pf in (("Point-4 model at 0.5", g["arm_pf_05"]),
                      ("Point-4 model at its chosen cuts", g["arm_pf_cut"]),
                      ("November model at 0.5", g["nov_pf_05"]),
                      ("November model at its chosen cuts", g["nov_pf_cut"])):
        vals = [label, pf["caught"], pf["clear_passed"], pf["clear_wrong_n"],
                pf["pass_passed"]]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            if j > 1:
                c.number_format = "0" if j == 4 else "0.0%"
        r += 1
    r += 1

    ws.cell(row=r, column=1, value="November reference as recorded, lens scope"
            ).font = H2_FONT
    r += 1
    heads = ["Operating point",
             "Fail pictures caught (share of the 684 lens-tagged test pictures)",
             "Clear pictures passed (share of the 437 test pictures without a lens tag)",
             "Clear wrongly failed (count out of the 437 test pictures without a lens "
             "tag)"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    vals = ["November reference at 0.5", g["ref"]["caught"], g["ref"]["clear_passed"],
            g["ref"]["clear_wrong_n"]]
    for j, v in enumerate(vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        if j > 1:
            c.number_format = "0" if j == 4 else "0.0%"
    r += 1
    ws.cell(row=r, column=1,
            value="This reference counts only the twelve lens tags as the defect and "
                  "only pictures without a lens tag as clear, so it is not on the same "
                  "population as the rule above. The November model read under the same "
                  "rule appears in the table above and in the pass/fail sheet."
            ).alignment = WRAP
    r += 2

    ws.cell(row=r, column=1, value="Object classes and lens tags, test split"
            ).font = H2_FONT
    r += 1
    heads = ["Measure", "Value", "What it is measured against"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    n_above = sum(1 for row in g["obj_rows"] if row["ap"] > row["floor"])
    summary_rows = [
        ("Macro average precision, seven supported object classes", g["macro"]["ap"],
         "0.0000", "Macro prevalence floor over the same seven classes"),
        ("Macro prevalence floor, seven supported object classes", g["macro"]["floor"],
         "0.0000", "Share of the 1,121 test pictures carrying the class, averaged"),
        ("Object classes scoring above their own floor", n_above, "0",
         "Of the seven supported object classes on the test split"),
        ("Macro average precision, eight judgeable lens classes, this model",
         g["arm_lens_macro"], "0.0000",
         "November reference on the same eight classes"),
        ("Macro average precision, eight judgeable lens classes, November reference",
         g["nov_lens_macro"], "0.0000",
         "Recomputed from the November run's own saved scores"),
        ("Change in the lens macro average precision", g["lens_delta"], '"+"0.0000',
         "Stability band of 0.01 agreed before the runs"),
        ("Stability band", BAND, "0.0000",
         "Change beyond the band is reported as a move"),
    ]
    for label, value, fmt, against in summary_rows:
        ws.cell(row=r, column=1, value=label).alignment = WRAP
        c = ws.cell(row=r, column=2, value=value)
        c.number_format = fmt
        ws.cell(row=r, column=3, value=against).alignment = WRAP
        for j in range(1, 4):
            ws.cell(row=r, column=j).border = BOX
        r += 1
    verdict = ("Outside the band: the lens head moved and the move is reported, "
               "not held." if abs(g["lens_delta"]) > BAND
               else "Inside the band: the lens head is held.")
    ws.cell(row=r, column=1, value="Lens stability verdict").border = BOX
    ws.cell(row=r, column=2, value=verdict).alignment = WRAP
    ws.cell(row=r, column=2).border = BOX
    ws.cell(row=r, column=3, value="Rule agreed before the runs").border = BOX
    r += 2

    ws.cell(row=r, column=1, value="How to read this workbook").font = H2_FONT
    r += 1
    for line in [
        "A picture passes only when it is clear or carries nothing but the bubble "
        "classes. A picture fails as soon as any fail class fires at its cut. The rule "
        "is an OR over the columns the model already has, not a second model.",
        "The object classes score well above their prevalence floors, but the floors "
        "are low, so a low score is close to guessing: Extraneous Polymer and HEMA "
        "carry 17 and 27 of the 1,121 test pictures.",
        "At 0.5 the rule fails 1 of the 317 clear test pictures and 28 of the 36 "
        "bubble-only test pictures. The bubble columns never fail a picture; those "
        "false fails come from lens tags and object classes firing on pictures that "
        "carry nothing but bubbles.",
        "The single object flag of the earlier runs cannot tell a bubble from a "
        "defect, which is why the recorded reference is reported on its own lens "
        "scope rather than on this rule.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    for col, width in ((1, 62), (2, 26), (3, 46), (4, 30), (5, 34)):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ============================================================ Object classes
    ws = wb.create_sheet("Object classes")
    r = 1
    ws.cell(row=r, column=1,
            value="Guide object classes on the 1,121 test pictures, with their "
                  "prevalence floors").font = TITLE_FONT
    r += 2
    heads = ["Class", "Test pictures with the class (of 1,121)",
             "Validation pictures with the class (of 1,110)",
             "Split pictures with the class (of 7,470)",
             "Prevalence floor for average precision, test (share of 1,121)",
             "Average precision, test", "F1 at 0.5, test",
             "F1 at the chosen cut, test", "Chosen cut"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    header_row = r
    r += 1
    for row in g["obj_rows"]:
        vals = [row["name"], row["test_n"], row["val_n"], row["split_n"],
                row["floor"], row["ap"], row["f1_05"], row["f1_cut"], row["cut"]]
        fmts = [None, "0", "0", "0", "0.0000", "0.0000", "0.0000", "0.0000", "0.00"]
        for j, (v, f) in enumerate(zip(vals, fmts), start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            if f:
                c.number_format = f
        r += 1
    macro_vals = ["Macro over the seven supported classes", None, None, None,
                  g["macro"]["floor"], g["macro"]["ap"], g["macro"]["f1_05"],
                  g["macro"]["f1_cut"], None]
    for j, v in enumerate(macro_vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        c.font = Font(bold=True)
        if j in (5, 6, 7, 8):
            c.number_format = "0.0000"
    r += 1
    groove_vals = ["Surface Groove", 0, 0, 0, 0.0, None, None, None, None]
    for j, v in enumerate(groove_vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        if j in (5,):
            c.number_format = "0.0000"
    r += 1
    ws.cell(row=r, column=1,
            value="Surface Groove has no positive pictures in the split, so it has no "
                  "trained column, it is left out of every average, and it never "
                  "fires in the pass/fail rule.").alignment = WRAP
    r += 2

    ws.cell(row=r, column=1,
            value="Bubble and Bubble Cluster confusion on the 1,121 test pictures"
            ).font = H2_FONT
    r += 1
    for mode, label in (("0.5", "At 0.5"), ("chosen", "At the chosen cuts")):
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        r += 1
        heads = ["Truth pair", "Predicted both", "Predicted Bubble only",
                 "Predicted Cluster only", "Predicted neither"]
        for j, h in enumerate(heads, start=1):
            c = ws.cell(row=r, column=j, value=h)
            c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
        r += 1
        for key, label2 in (("both", "Truth both"), ("bubble_only", "Truth Bubble only"),
                            ("cluster_only", "Truth Cluster only"),
                            ("neither", "Truth neither")):
            vals = [label2] + [g["confusion"][mode][key][k]
                               for k in ("both", "bubble_only", "cluster_only",
                                         "neither")]
            for j, v in enumerate(vals, start=1):
                c = ws.cell(row=r, column=j, value=v)
                c.border = BOX
                if j > 1:
                    c.number_format = "0"
            r += 1
        r += 1
    for col, width in ((1, 34), (2, 18), (3, 20), (4, 20), (5, 22), (6, 18),
                       (7, 16), (8, 18), (9, 12)):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ============================================================ Thresholds
    ws = wb.create_sheet("Thresholds")
    r = 1
    ws.cell(row=r, column=1, value="Chosen cuts and the guard").font = TITLE_FONT
    r += 1
    for line in [
        "Cut rule agreed before the runs: on the validation split try every cut from "
        "0.05 to 0.95 in steps of 0.05, take the cut with the highest F1 for that "
        "class, send ties to the higher cut, and keep 0.5 when the class has fewer "
        "than 10 validation pictures. That floor of 10 is the guard.",
        "A class held at 0.5 by the guard is recorded as untuned, not as tuned to 0.5.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    r += 1
    heads = ["Class", "Role in the pass/fail rule",
             "Validation pictures with the class (of 1,110)",
             "Test pictures with the class (of 1,121)", "Chosen cut",
             "Where the cut came from", "Validation F1 at the chosen cut"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    for row in g["th_rows"]:
        vals = [row["name"], row["role"], row["val_n"], row["test_n"], row["cut"],
                row["source"], row["val_f1"]]
        fmts = [None, None, "0", "0", "0.00", None, "0.0000"]
        for j, (v, f) in enumerate(zip(vals, fmts), start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            c.alignment = WRAP
            if f:
                c.number_format = f
        r += 1
    groove = ["Surface Groove", FAIL_ROLE, 0, 0, None,
              "Not trained: no positive pictures anywhere in the split", None]
    for j, v in enumerate(groove, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        c.alignment = WRAP
    r += 2
    ws.cell(row=r, column=1,
            value="Bubble and Bubble Cluster are pass classes: their cut shapes the "
                  "bubble columns but never fails a picture.").alignment = WRAP
    for col, width in ((1, 30), (2, 34), (3, 20), (4, 18), (5, 12), (6, 52),
                       (7, 20)):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ============================================================ F1 against the cut
    ws = wb.create_sheet("F1 against the cut")
    r = 1
    ws.cell(row=r, column=1,
            value="F1 for the seven supported object classes on the 1,121 test "
                  "pictures, at every cut").font = TITLE_FONT
    r += 2
    heads = ["Score cut"] + [OBJ_NAME[c] for c in OBJ]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    vals = ["Chosen cut"] + [g["cuts"][c] for c in OBJ]
    for j, v in enumerate(vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        if j > 1:
            c.number_format = "0.00"
    r += 1
    vals = ["F1 at the chosen cut"] + [
        f1_at(g["true"][:, g["cols"].index(c)], g["score"][:, g["cols"].index(c)],
              g["cuts"][c])
        for c in OBJ]
    for j, v in enumerate(vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        if j > 1:
            c.number_format = "0.0000"
    r += 1
    for k, t in enumerate(GRID):
        vals = [t] + [g["curves"][c][k] for c in OBJ]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            if j == 1:
                c.number_format = "0.00"
            else:
                c.number_format = "0.0000"
        r += 1
    r += 1
    ws.cell(row=r, column=1,
            value="Every cut on this sheet is applied to the same 1,121 test "
                  "pictures; the curve shows how F1 moves as the cut moves.").alignment \
        = WRAP
    ws.column_dimensions["A"].width = 24
    for j in range(2, 9):
        ws.column_dimensions[get_column_letter(j)].width = 17

    # ============================================================ Pass/fail
    ws = wb.create_sheet("Pass-fail")
    r = 1
    ws.cell(row=r, column=1, value="The pass/fail rule read on saved scores"
            ).font = TITLE_FONT
    r += 1
    ws.cell(row=r, column=1,
            value="Block A is on the rule's own populations: the 768 test pictures "
                  "that fail the rule, the 317 clear test pictures, the 36 bubble-only "
                  "test pictures and the 353 test pictures that pass the rule.").alignment \
        = WRAP
    r += 2
    heads = ["Model and operating point",
             "Fail pictures caught (count of the 768)",
             "Fail pictures caught (share of the 768)",
             "Clear pictures passed (count of the 317)",
             "Clear pictures passed (share of the 317)",
             "Clear wrongly failed (count of the 317)",
             "Bubble-only pictures passed (count of the 36)",
             "Pass pictures predicted pass (count of the 353)",
             "Pass pictures predicted pass (share of the 353)"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    for label, pf in (("Point-4 model at 0.5", g["arm_pf_05"]),
                      ("Point-4 model at its chosen cuts", g["arm_pf_cut"]),
                      ("November model at 0.5", g["nov_pf_05"]),
                      ("November model at its chosen cuts", g["nov_pf_cut"])):
        vals = [label, pf["caught_n"], pf["caught"], pf["clear_passed_n"],
                pf["clear_passed"], pf["clear_wrong_n"], pf["bubble_only_passed_n"],
                pf["pass_passed_n"], pf["pass_passed"]]
        fmts = [None, "0", "0.0%", "0", "0.0%", "0", "0", "0", "0.0%"]
        for j, (v, f) in enumerate(zip(vals, fmts), start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            if f:
                c.number_format = f
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Block B: the November reference as recorded"
            ).font = H2_FONT
    r += 1
    ws.cell(row=r, column=1,
            value="Block B is on the reference's own lens scope: the 684 lens-tagged "
                  "test pictures as the fail population and the 437 test pictures "
                  "without a lens tag as the clear population.").alignment = WRAP
    r += 2
    heads = ["Operating point",
             "Fail pictures caught (count of the 684 lens-tagged test pictures)",
             "Fail pictures caught (share of the 684 lens-tagged test pictures)",
             "Clear pictures passed (count of the 437 test pictures without a lens tag)",
             "Clear pictures passed (share of the 437 test pictures without a lens tag)",
             "Clear wrongly failed (count of the 437 test pictures without a lens tag)"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    vals = ["November reference at 0.5", g["ref"]["caught_n"], g["ref"]["caught"],
            g["ref"]["clear_passed_n"], g["ref"]["clear_passed"],
            g["ref"]["clear_wrong_n"]]
    fmts = [None, "0", "0.0%", "0", "0.0%", "0"]
    for j, (v, f) in enumerate(zip(vals, fmts), start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BOX
        if f:
            c.number_format = f
    r += 2
    ws.cell(row=r, column=1, value="Reading the two blocks").font = H2_FONT
    r += 1
    for line in [
        "The reference counts only the twelve lens tags as the defect, so its caught "
        "rate and block A's caught rate sit on different populations. The comparable "
        "row is the November model read under the same rule, which block A gives.",
        "A picture is caught when a class it truly carries fires at that class's cut. "
        "A clear picture is wrongly failed when any fail class fires on a picture that "
        "carries nothing at all.",
        "The rule fires on any one of the 17 trained fail columns, so false positives "
        "add up across columns: that is why pass pictures predicted pass sits below "
        "clear pictures passed.",
        "The bubble columns are pass classes and never fail a picture, so bubble-only "
        "test pictures fail only when a lens tag or an object class fires on them.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    for col, width in ((1, 46), (2, 24), (3, 24), (4, 24), (5, 24), (6, 26),
                       (7, 26), (8, 26), (9, 26)):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ============================================================ Method notes
    ws = wb.create_sheet("Method notes")
    r = 1
    ws.cell(row=r, column=1, value="Method notes").font = TITLE_FONT
    r += 2
    ws.cell(row=r, column=1, value="The rule").font = H2_FONT
    r += 1
    for line in [
        "Agreed 2026-11-04. A picture passes only if it is clear or carries nothing "
        "but the bubble classes, Bubble and Bubble Cluster. Everything else fails: the "
        "twelve lens tags including Bubble Scatter, Wet Package, Foreign Matter, "
        "Fiber, Extraneous Polymer, HEMA and Surface Groove.",
        "A picture fails as soon as any fail class column fires at that column's cut. "
        "The OR is the rule, not a second model: no new scores are trained for the "
        "decision.",
        "Truth on the frozen split: 2,117 clear and 196 bubble-only pictures pass, "
        "5,157 fail. On the test split: 353 pass, 317 of them clear and 36 bubble-only, "
        "and 768 fail.",
        "Surface Groove has no positive pictures in the split, so it has no trained "
        "column and never fires; it is listed as a fail class because it stays one.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="Cut rule").font = H2_FONT
    r += 1
    for line in [
        "Cuts come from the validation split only: every cut from 0.05 to 0.95 in "
        "steps of 0.05, highest F1 per class, ties to the higher cut, and a guard of "
        "10 validation pictures below which the class keeps 0.5 and is recorded as "
        "untuned.",
        "The test split is never used to choose a cut. F1 against the cut curves in "
        "this workbook are reported on the test split for reading only.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    r += 1
    ws.cell(row=r, column=1,
            value="Recall by flag: gated versus un-gated class positives, test split"
            ).font = H2_FONT
    r += 1
    ws.cell(row=r, column=1,
            value="The micron gate flag splits a class, it does not add a class. Each "
                  "row below splits that class's test pictures by whether the gate "
                  "flag is set, and reports recall at 0.5 and at the class's chosen "
                  "cut. Populations are the class's own test pictures.").alignment = WRAP
    r += 2
    heads = ["Class",
             "Gated test pictures with the class",
             "Recall on gated test pictures at 0.5",
             "Recall on gated test pictures at the chosen cut",
             "Un-gated test pictures with the class",
             "Recall on un-gated test pictures at 0.5",
             "Recall on un-gated test pictures at the chosen cut"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    for c in GATED:
        e = g["rbf"][c]
        vals = [OBJ_NAME[c], e["gated"]["n"], e["gated"]["recall_05"],
                e["gated"]["recall_cut"], e["ungated"]["n"], e["ungated"]["recall_05"],
                e["ungated"]["recall_cut"]]
        fmts = [None, "0", "0.000", "0.000", "0", "0.000", "0.000"]
        for j, (v, f) in enumerate(zip(vals, fmts), start=1):
            c2 = ws.cell(row=r, column=j, value=v)
            c2.border = BOX
            c2.alignment = WRAP
            if f and v is not None:
                c2.number_format = f
        r += 1
    r += 1
    ws.cell(row=r, column=1,
            value="Extraneous Polymer and HEMA have no un-gated test pictures, so "
                  "their un-gated recall cells are empty rather than zero. Fiber has "
                  "2 un-gated test pictures, so its un-gated recalls rest on 2 "
                  "pictures and are not a stable reading.").alignment = WRAP
    r += 2
    ws.cell(row=r, column=1, value="Reading limits").font = H2_FONT
    r += 1
    for line in [
        "Any one of the 17 trained fail columns firing fails the picture, so the false "
        "fail rate of the rule grows with the number of columns read, even when each "
        "column is well behaved on its own.",
        "The recorded November reference is on a lens-only scope, so it is not "
        "comparable line for line with the rule's own populations; the comparable row "
        "is the November model read under this rule.",
        "The lens macro average precision over the eight judgeable lens classes rose "
        "from 0.8182 to 0.8815, a change of 0.0633 against a band of 0.01, so the lens "
        "head moved rather than held.",
        "Prevalence floors are low for the rare classes, so an average precision near "
        "the floor is a weak signal: Extraneous Polymer has 17 test pictures and HEMA "
        "27.",
        "Recall by flag compares populations of very different size: Foreign Matter "
        "splits 72 and 40 test pictures, Fiber 56 and 2, Extraneous Polymer 17 and 0, "
        "HEMA 27 and 0.",
    ]:
        ws.cell(row=r, column=1, value=line).alignment = WRAP
        r += 1
    for col, width in ((1, 50), (2, 22), (3, 24), (4, 26), (5, 24), (6, 26),
                       (7, 28)):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ============================================================ Definitions
    ws = wb.create_sheet("Definitions")
    r = 1
    ws.cell(row=r, column=1, value="Definitions").font = TITLE_FONT
    r += 2
    heads = ["Term", "Definition"]
    for j, h in enumerate(heads, start=1):
        c = ws.cell(row=r, column=j, value=h)
        c.font, c.fill, c.alignment, c.border = HEAD_FONT, HEAD_FILL, WRAP, BOX
    r += 1
    defs = [
        ("Frozen split", "The one picture split used for every run in this effort: "
                         "7,470 pictures, 5,239 train, 1,110 validation, 1,121 test. "
                         "It is never rebuilt."),
        ("Test split", "The 1,121 pictures held out of training and validation. Every "
                       "rate in this workbook is measured on them unless the heading "
                       "says otherwise."),
        ("Validation split", "The 1,110 pictures used only to choose cuts. Nothing in "
                             "this workbook reports a validation rate except the cut "
                             "sheet's validation F1."),
        ("Clear picture", "A picture that carries no label at all: no lens tag, no "
                          "object class, no gate flag."),
        ("Bubble-only picture", "A picture that carries Bubble or Bubble Cluster and "
                                "nothing else."),
        ("Pass picture", "A clear picture or a bubble-only picture. Under the rule "
                         "these are the pictures that should receive no flag."),
        ("Fail picture", "Any other picture: one carrying a lens tag or one of the "
                         "fail object classes."),
        ("Fail classes", "The twelve lens tags, including Bubble Scatter, plus Wet "
                         "Package, Foreign Matter, Fiber, Extraneous Polymer, HEMA and "
                         "Surface Groove. Any one of them firing fails the picture."),
        ("Pass classes", "Bubble and Bubble Cluster. Their columns never fail a "
                         "picture."),
        ("Fires", "A column's score is at or above that column's cut."),
        ("Caught", "A fail picture with at least one of the classes it truly carries "
                   "firing at that class's cut."),
        ("Clear pictures passed", "Clear pictures with no fail class firing, out of "
                                  "the clear pictures in that population."),
        ("Clear wrongly failed", "Clear pictures with at least one fail class firing, "
                                 "out of the clear pictures in that population."),
        ("Pass pictures predicted pass", "Pass pictures with no fail class firing, out "
                                         "of the pass pictures in that population."),
        ("Average precision", "The mean precision taken at the rank of every true "
                              "positive when the pictures are ordered by descending "
                              "score. For a constant score it equals the prevalence, "
                              "which is why every score is reported next to its "
                              "floor."),
        ("Prevalence floor", "The share of the measured population carrying the class. "
                             "It is the average precision a model that guesses one "
                             "number for every picture would get."),
        ("F1", "Twice precision times recall divided by precision plus recall, with "
               "0 when both are 0."),
        ("Chosen cut", "The cut picked on the validation split for that class: highest "
                       "F1 from 0.05 to 0.95 in steps of 0.05, ties to the higher "
                       "cut."),
        ("Guard", "The floor of 10 validation pictures per class. Below it the class "
                  "keeps 0.5 and is recorded as untuned rather than tuned to 0.5."),
        ("Gated test picture", "A test picture whose gate flag is set for that class. "
                               "The gate flag is a subset of the class column, never "
                               "a second class."),
        ("Un-gated test picture", "A test picture that carries the class without the "
                                  "gate flag."),
        ("Judgeable class", "A lens class carried by at least 20 test pictures. The "
                            "eight judgeable lens classes make the lens macro average "
                            "precision."),
        ("Supported object class", "An object class with positive pictures in the "
                                   "split. Seven are supported; Surface Groove is "
                                   "not."),
        ("Macro", "The unweighted mean over the classes named in the same line."),
        ("Lens tags", "The twelve defect classes read from the lens: Missing Primary "
                      "Package, Multiple Lenses, Lens Off Center, Dirty Camera, No "
                      "Lens, Folded Lens, Low Dose, Cavity Off Center, Dirty Strobe, "
                      "View Obstructed, Bubble Scatter, Package Misalignment."),
        ("Guide object classes", "The eight object classes that replace the single "
                                 "object flag: Bubble, Bubble Cluster, Foreign Matter, "
                                 "Fiber, Wet Package, HEMA, Extraneous Polymer and "
                                 "Surface Groove."),
        ("Stability band", "The 0.01 gap agreed before the runs: a macro average "
                           "precision change inside the band is held, a change beyond "
                           "it is reported as a move."),
    ]
    for term, text in defs:
        ws.cell(row=r, column=1, value=term).alignment = WRAP
        ws.cell(row=r, column=2, value=text).alignment = WRAP
        ws.cell(row=r, column=1).border = BOX
        ws.cell(row=r, column=2).border = BOX
        r += 1
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 96

    # ---- client-safe sweep before writing
    banned = [".py", ".npz", ".csv", ".xlsx", "D:", "\\", "run/", "experiments/",
              "predictions", "P1_", "P2_", "class_", "gate_", "md5", "—",
              "train_multilabel", "build_", "verify_", "ticket", "metrics.json",
              "thresholds.json"]
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    low = cell.value
                    for token in banned:
                        if token in low:
                            raise SystemExit("client-safe breach in %s!%s: %r"
                                             % (sheet.title, cell.coordinate, token))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
