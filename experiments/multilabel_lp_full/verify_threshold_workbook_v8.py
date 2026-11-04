"""Verify the threshold workbook against the saved scores, independently of its builder.

It recomputes every number from the score archive with its own code, then reads the workbook
and compares cell by cell. It also tampers with a copy and requires that the check notices,
so a green run means the check was exercised, not merely that the file opened.

Run:
    .venv/Scripts/python.exe experiments/multilabel_lp_full/verify_threshold_workbook_v8.py
Exit 0 = every number matches and the tamper proof caught its own edit.
"""
import csv
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
PRED = ROOT / "run/multilabel_lp_v8_20261103/b/predictions.npz"
LABELS = ROOT / "run/multilabel_lp_v8_20261103/labels_b.csv"
BOOK = ROOT / "reports/multilabel_production/lp_thresholds_20261103.xlsx"

GRID = [round(0.01 * i, 2) for i in range(1, 100)]
CURVE_GRID = [round(0.05 * i, 2) for i in range(1, 20)]
NAMES = {
    "P1_MPP": "Missing Primary Package", "P1_ML": "Multiple Lens",
    "P2_LOC": "Lens Off Center", "P2_DC": "Dirty Camera", "P1_NL": "No Lens",
    "P1_FL": "Folded Lens", "P2_LD": "Low Dose", "P1_COC": "Cavity Off Center",
    "P2_DS": "Dirty Strobe", "P2_FOV": "View Obstructed",
    "P2_BSC": "Bubble Scatter", "P1_PPM": "Package Misalignment",
}


def prf(true, score, cut):
    pred = score >= cut
    tp = int((pred & (true == 1)).sum())
    fp = int((pred & (true == 0)).sum())
    fn = int((~pred & (true == 1)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def recompute():
    d = np.load(PRED, allow_pickle=False)
    columns = [str(c) for c in d["columns"]][:12]
    truth, score = d["test_true"], d["test_score"]
    rows = {}
    for i, code in enumerate(columns):
        t, s = truth[:, i], score[:, i]
        f1, cut = max(((prf(t, s, g)[2], g) for g in GRID), key=lambda x: (x[0], x[1]))
        p, r, _ = prf(t, s, cut)
        rows[code] = {"pictures": int(t.sum()), "cut": cut, "p": p, "r": r, "f1": f1,
                      "f1_half": prf(t, s, 0.5)[2],
                      "curve": {g: prf(t, s, g)[2] for g in CURVE_GRID}}

    def scope(tuned):
        cuts = np.array([rows[c]["cut"] if c in tuned else 0.5 for c in columns])
        pred = (score[:, :12] >= cuts).astype(int)
        real = truth[:, :12].astype(int)
        judge = [i for i in range(12) if real[:, i].sum() >= 20]
        fail_true = real.sum(axis=1) > 0
        fail_pred = pred.sum(axis=1) > 0
        clear = ~fail_true
        return {
            "moved": len(tuned),
            "macro": float(np.mean([prf(truth[:, i], score[:, i], cuts[i])[2] for i in judge])),
            "exact": float((pred == real).all(axis=1).mean()),
            "hamming": float((pred != real).mean()),
            "caught": float((fail_pred & fail_true).sum() / fail_true.sum()),
            "passed": float((~fail_pred & clear).sum() / clear.sum()),
            "wrong": int((fail_pred & clear).sum()),
            "clear": int(clear.sum()),
        }

    scopes = {
        "fixed": scope(set()),
        "all12": scope(set(columns)),
        "nine": scope({c for c in columns if rows[c]["pictures"] >= 8}),
        "eight": scope({c for c in columns if rows[c]["pictures"] >= 20}),
    }
    return columns, rows, scopes, int(len(truth)), int((truth[:, :12].sum(axis=1) > 0).sum())


def header_map(ws, must_have):
    for r in range(1, 40):
        values = [ws.cell(row=r, column=j).value for j in range(1, 12)]
        if must_have in values:
            return r, {str(v): j + 1 for j, v in enumerate(values) if v is not None}
    return None, None


def close(a, b, tol=1e-9):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def guard_counts():
    """Validation and test positives per column, read straight from the label table."""
    with open(LABELS, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = [c for c in reader.fieldnames
                if c not in ("md5", "image_path", "split", "has_lp", "has_object", "is_clear")]
        val = {c: 0 for c in cols}
        test = {c: 0 for c in cols}
        for row in reader:
            if row["split"] == "val":
                for c in cols:
                    if row[c] == "1":
                        val[c] += 1
            elif row["split"] == "test":
                for c in cols:
                    if row[c] == "1":
                        test[c] += 1
    return val, test


def verify(path):
    problems = []
    columns, rows, scopes, n_pictures, n_fail = recompute()
    wb = load_workbook(path)

    expected_sheets = ["Summary", "Class thresholds", "How a cut is chosen", "What changes",
                       "Threshold curves", "Definitions"]
    if wb.sheetnames != expected_sheets:
        problems.append(f"sheets {wb.sheetnames} != {expected_sheets}")
        return problems

    # ---- Class thresholds
    ws = wb["Class thresholds"]
    head_row, cols = header_map(ws, "Best cut")
    if not head_row:
        problems.append("Class thresholds: header row not found")
        return problems
    if len(rows) != 12:
        problems.append(f"recompute produced {len(rows)} classes, expected 12")
    row_of = {}
    for r in range(head_row + 1, head_row + 13):
        row_of[ws.cell(row=r, column=cols["Class"]).value] = r
    for code in columns:
        r = row_of.get(NAMES[code])
        if r is None:
            problems.append(f"Class thresholds: row for {NAMES[code]!r} not found")
            continue
        want = rows[code]
        got_name = ws.cell(row=r, column=cols["Class"]).value
        if got_name != NAMES[code]:
            problems.append(f"Class thresholds row {r}: name {got_name!r} != {NAMES[code]!r}")
        pairs = [("Pictures with the class", want["pictures"]),
                 ("Best cut", want["cut"]),
                 ("Precision", want["p"]),
                 ("Recall", want["r"]),
                 ("F1 at the best cut", want["f1"]),
                 ("F1 at 0.5", want["f1_half"]),
                 ("Change in F1", want["f1"] - want["f1_half"])]
        for header, value in pairs:
            col = None
            for h, j in cols.items():
                if h.startswith(header):
                    col = j
                    break
            if col is None:
                problems.append(f"Class thresholds: column {header!r} missing")
                continue
            cell = ws.cell(row=r, column=col)
            if not close(cell.value, value):
                problems.append(f"Class thresholds!{cell.coordinate} {code} {header}: "
                                f"{cell.value!r} != {value!r}")

    # ---- How a cut is chosen: the guard, its counts and its flags
    ws = wb["How a cut is chosen"]
    head_row, cols = header_map(ws, "Validation pictures")
    if not head_row:
        problems.append("How a cut is chosen: header row not found")
    else:
        val, test = guard_counts()
        row_of = {}
        for r in range(head_row + 1, head_row + 15):
            name = ws.cell(row=r, column=cols["Class"]).value
            if name:
                row_of[name] = r
        for code in columns:
            r = row_of.get(NAMES[code])
            if r is None:
                problems.append(f"How a cut is chosen: row for {NAMES[code]!r} not found")
                continue
            checks = [("Validation pictures", val[code], True),
                      ("Test pictures", test[code], True),
                      ("Cut set at 10", "Yes" if val[code] >= 10 else "No", False),
                      ("Cut set at 8", "Yes" if val[code] >= 8 else "No", False)]
            for header, want, numeric in checks:
                cell = ws.cell(row=r, column=cols[header])
                ok = close(cell.value, want) if numeric else cell.value == want
                if not ok:
                    problems.append(f"How a cut is chosen!{cell.coordinate} {code} {header}: "
                                    f"{cell.value!r} != {want!r}")
        r = row_of.get("Any object present (routing flag)")
        if r is None:
            problems.append("How a cut is chosen: object row not found")
        else:
            for header, want in [("Validation pictures", val["object_present"]),
                                 ("Test pictures", test["object_present"])]:
                cell = ws.cell(row=r, column=cols[header])
                if not close(cell.value, want):
                    problems.append(f"How a cut is chosen!{cell.coordinate} object {header}: "
                                    f"{cell.value!r} != {want!r}")
        text = " ".join(str(c.value) for row in ws.iter_rows() for c in row
                        if isinstance(c.value, str))
        for needle in ("View Obstructed with 9", "Dirty Strobe with 8"):
            if needle not in text:
                problems.append(f"How a cut is chosen: prose missing {needle!r}")

    # ---- What changes, and the same numbers on Summary
    def check_scope_sheet(name, first_data_row, cols, problems):
        ws2 = wb[name]
        order = [("fixed", "Fixed 0.5"), ("all12", "Best on all 12"),
                 ("nine", "9 classes"), ("eight", "8 classes")]
        for k, (key, label) in enumerate(order):
            s = scopes[key]
            r = first_data_row + k
            pairs = [("Classes moved", s["moved"]), ("Macro F1", s["macro"]),
                     ("Exact match", s["exact"]), ("Hamming", s["hamming"]),
                     ("Defects caught", s["caught"]), ("Clear pictures passed", s["passed"])]
            for header, value in pairs:
                col = next((j for h, j in cols.items() if h.startswith(header)), None)
                if col is None:
                    problems.append(f"{name}: column {header!r} missing")
                    continue
                cell = ws2.cell(row=r, column=col)
                if not close(cell.value, value):
                    problems.append(f"{name}!{cell.coordinate} {key} {header}: "
                                    f"{cell.value!r} != {value!r}")
            col = next((j for h, j in cols.items() if h.startswith("Clear wrongly")), None)
            cell = ws2.cell(row=r, column=col)
            if str(cell.value) != f"{s['wrong']} of {s['clear']}":
                problems.append(f"{name}!{cell.coordinate} {key} clear wrongly failed: "
                                f"{cell.value!r} != '{s['wrong']} of {s['clear']}'")

    ws = wb["What changes"]
    head_row, cols = header_map(ws, "Classes moved")
    check_scope_sheet("What changes", head_row + 1, cols, problems)

    ws = wb["Summary"]
    head_row, cols = header_map(ws, "Classes moved")
    check_scope_sheet("Summary", head_row + 1, cols, problems)

    # ---- Curves
    ws = wb["Threshold curves"]
    head_row, cols = header_map(ws, "Cut")
    eight = [c for c in columns if rows[c]["pictures"] >= 20]
    for k, g in enumerate(CURVE_GRID):
        r = head_row + 1 + k
        if not close(ws.cell(row=r, column=1).value, g):
            problems.append(f"Threshold curves row {r}: cut {ws.cell(row=r, column=1).value!r} != {g}")
        for code in eight:
            col = cols.get(NAMES[code])
            if col is None:
                problems.append(f"Threshold curves: column {NAMES[code]!r} missing")
                continue
            cell = ws.cell(row=r, column=col)
            if not close(cell.value, rows[code]["curve"][g]):
                problems.append(f"Threshold curves!{cell.coordinate} {code} at {g}: "
                                f"{cell.value!r} != {rows[code]['curve'][g]!r}")

    # ---- The Summary prose must carry the same headline numbers
    summary = wb["Summary"]
    summary_text = " ".join(str(summary.cell(row=r, column=1).value) for r in range(1, 16)
                            if summary.cell(row=r, column=1).value)
    for needle in (f"{scopes['fixed']['macro']:.3f}", f"{scopes['eight']['macro']:.3f}",
                   f"{scopes['fixed']['exact']:.3f}", f"{scopes['all12']['exact']:.3f}"):
        if needle not in summary_text:
            problems.append(f"Summary prose does not contain the number {needle}")

    # ---- Population line
    lead = str(summary.cell(row=2, column=1).value)
    if f"{n_pictures:,}" not in lead or f"{n_fail:,}" not in lead:
        problems.append(f"Summary lead does not name the population: {lead!r}")

    return problems


def main():
    problems = verify(BOOK)
    if problems:
        print("FAIL")
        for p in problems:
            print("  ", p)
        sys.exit(1)
    print(f"PASS: every cell in {BOOK.name} matches a recomputation from the scores")

    # Tamper proof: change one real number in a copy and require the check to name it.
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / "tampered.xlsx"
        shutil.copy(BOOK, copy)
        wb = load_workbook(copy)
        ws = wb["Class thresholds"]
        head_row, cols = header_map(ws, "Best cut")
        target = None
        for r in range(head_row + 1, head_row + 13):
            if ws.cell(row=r, column=cols["Class"]).value == "Dirty Camera":
                target = ws.cell(row=r, column=cols["F1 at the best cut"])
                break
        if target is None:
            print("FAIL: could not find the row to tamper with")
            sys.exit(1)
        original = target.value
        target.value = float(original) + 0.05
        coordinate = target.coordinate
        wb.save(copy)
        found = verify(copy)
        if not found:
            print("FAIL: the tampered copy verified clean")
            sys.exit(1)
        if not any(coordinate in p for p in found):
            print(f"FAIL: tamper at {coordinate} was caught but not named: {found[:2]}")
            sys.exit(1)
        print(f"tamper proof: {coordinate} changed by 0.05 and caught as expected")


if __name__ == "__main__":
    main()
