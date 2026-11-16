"""Independent check of the Experiment 3.2 workbook.

Recomputes every pass/fail count from the per-picture sheet's source and checks the workbook
cells, then sweeps every string cell for internal names a reader cannot resolve.

    .venv/Scripts/python.exe experiments/multilabel_ooi/verify_exp3_2_workbook.py \
        --book reports/multilabel_production/size_gate_redo_20261116.xlsx \
        --scores run/exp3_2_scores_20261116
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

FORBIDDEN = ["run/", "C:\\", "t_d", "t_c", "ticket", "exp3", "gate4", "stage0", "cond15",
             ".py", "rev2"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--scores", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--gate-meta", required=True)
    args = ap.parse_args()

    with open(Path(args.scores) / "per_picture.csv", newline="", encoding="utf-8") as f:
        pic = list(csv.DictReader(f))
    wb = load_workbook(args.book)
    problems = []

    def expect(label, got, want):
        if got != want:
            problems.append(f"{label}: workbook {got!r} != recomputed {want!r}")

    ws = wb["Pass-fail"]
    hdr = {ws.cell(row=4, column=j).value: j for j in range(1, 10)}
    for row in range(5, 7):
        rule = ws.cell(row=row, column=hdr["Rule"]).value
        sub = [r for r in pic if r["rule"] == rule]
        fail = sum(1 for r in sub if r["truth"] == "fail")
        caught = sum(1 for r in sub if r["truth"] == "fail" and r["predicted"] == "fail")
        missed = fail - caught
        passed = sum(1 for r in sub if r["truth"] == "pass" and r["predicted"] == "pass")
        wrong = sum(1 for r in sub if r["truth"] == "pass" and r["predicted"] == "fail")
        expect(f"{rule} pictures", ws.cell(row=row, column=hdr["Pictures"]).value, len(sub))
        expect(f"{rule} fail", ws.cell(row=row, column=hdr["Fail pictures"]).value, fail)
        expect(f"{rule} caught", ws.cell(row=row, column=hdr["Caught"]).value, caught)
        expect(f"{rule} missed", ws.cell(row=row, column=hdr["Missed"]).value, missed)
        expect(f"{rule} pass pictures",
               ws.cell(row=row, column=hdr["Pass pictures"]).value, passed + wrong)
        expect(f"{rule} wrong", ws.cell(row=row, column=hdr["Wrongly failed"]).value, wrong)

    # The condition sheet must carry fifteen rows, one per column, and the per-picture sheet
    # must have one row per picture per rule.
    cond = wb["Conditions"]
    cond_rows = [r for r in range(5, 26)
                 if isinstance(cond.cell(row=r, column=2).value, (int, float))]
    expect("condition rows", len(cond_rows), 15)

    # Every per-class count must agree with the tables the models were trained from.
    from build_exp3_2_workbook import COND_LABEL, SIZE_LABEL

    with open(args.labels, newline="", encoding="utf-8") as f:
        lab = list(csv.DictReader(f))
    rev = {v: k for k, v in COND_LABEL.items()}
    # The support column on the Conditions sheet is the test count of the same table.
    support = {row[0]: row[1] for row in cond.iter_rows(min_row=5, values_only=True)
               if row[0] in rev}
    for name, got in support.items():
        want = sum(1 for x in lab if x["split"] == "test" and x[rev[name]] == "1")
        expect(f"{name} support", got, want)
    per = wb["Pictures per class"]
    for row in per.iter_rows(min_row=4, values_only=True):
        if not row[0] or row[1] not in ("Lens condition", "Object class"):
            continue
        key = rev[row[0]]
        for col, side in ((2, "train"), (3, "val"), (4, "test")):
            want = sum(1 for x in lab if x["split"] == side and x[key] == "1")
            expect(f"{row[0]} {side}", row[col], want)
    meta = json.loads(Path(args.gate_meta).read_text(encoding="utf-8"))
    rev_size = {v: k for k, v in SIZE_LABEL.items()}
    size_key = {"Foreign Matter": "fm", "Fiber": "fiber", "Extraneous Polymer": "ep",
                "HEMA": "hema"}
    for row in per.iter_rows(min_row=4, values_only=True):
        if row[0] not in size_key:
            continue
        c = meta["by_class"][size_key[row[0]]]
        expect(f"{row[0]} train flagged", row[1], c["train_gated"])
        expect(f"{row[0]} val flagged", row[2], c["val_gated"])
        expect(f"{row[0]} test flagged", row[3], c["test_gated"])
        expect(f"{row[0]} test untagged", row[4], c["test_unflagged"])
    expect("per-picture rows", wb["Per picture"].max_row - 4, len(pic))

    # No internal names anywhere a reader can see.
    for sheet in wb.sheetnames:
        for row in wb[sheet].iter_rows(values_only=True):
            for cell in row:
                if isinstance(cell, str):
                    for token in FORBIDDEN:
                        if token in cell:
                            problems.append(f"{sheet}: forbidden {token!r} in {cell[:60]!r}")

    if problems:
        print("FAIL")
        for p in problems[:20]:
            print(" ", p)
        return 1
    print(f"OK: {len(pic)} per-picture rows, 15 condition rows, both rules recomputed, "
          f"no internal names in {len(wb.sheetnames)} sheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
