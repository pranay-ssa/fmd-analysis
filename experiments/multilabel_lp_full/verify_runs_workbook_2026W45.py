"""Verify the two-run workbook against the saved run records.

The workbook is a presentation artifact; this script is the check that its numbers still
match the records. It recomputes every headline and every per-class cell from the two
metrics and threshold files, then reads the workbook back and compares.

Run:
    .venv/Scripts/python.exe experiments/multilabel_lp_full/verify_runs_workbook_2026W45.py
    .venv/Scripts/python.exe experiments/multilabel_lp_full/verify_runs_workbook_2026W45.py <copy.xlsx>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
RUN_A = ROOT / "run/multilabel_lp_v8_20261105/a"
RUN_B = ROOT / "run/multilabel_lp_v8_20261103/b"
LABELS = ROOT / "run/multilabel_lp_v8_20261103/labels_b.csv"
DEFAULT_OUT = ROOT / "reports/multilabel_production/FMD_MultiLabel_Runs_2026W45.xlsx"

CLASS_ORDER = [
    "P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL",
    "P2_LD", "P1_COC", "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM",
]
RUN_LABELS = ("Lens only", "Lens + object flag")


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def split_counts():
    counts = {code: {"train": 0, "val": 0, "test": 0} for code in CLASS_ORDER}
    counts["object_present"] = {"train": 0, "val": 0, "test": 0}
    counts["is_clear"] = {"train": 0, "val": 0, "test": 0}
    totals = {"train": 0, "val": 0, "test": 0}
    with LABELS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            split = row["split"]
            totals[split] += 1
            for code in CLASS_ORDER:
                if row[code] == "1":
                    counts[code][split] += 1
            if row["object_present"] == "1":
                counts["object_present"][split] += 1
            if row["is_clear"] == "1":
                counts["is_clear"][split] += 1
    return counts, totals


def class_data(metrics, thresholds, counts):
    rows = {}
    for code in CLASS_ORDER:
        pc = metrics["per_class"][code]
        th = thresholds["per_class"][code]
        rows[code] = {
            "name": pc["name"], "test": pc["support"], "val": th["val_support"],
            "auprc": pc["auprc"], "f1_0.5": pc["f1_0.5"], "f1_thr": pc["f1_val_thr"],
            "threshold": pc["threshold"], "source": pc["threshold_source"],
            "val_f1_thr": th["val_f1_at_threshold"], "val_f1_0.5": th["val_f1_at_0.5"],
        }
    if "object_present" in thresholds["per_class"]:
        th = thresholds["per_class"]["object_present"]
        rows["object_present"] = {
            "name": "Any object (one flag)", "test": counts["object_present"]["test"],
            "val": th["val_support"], "threshold": th["threshold"], "source": th["source"],
            "auprc": None, "f1_0.5": None, "f1_thr": None,
            "val_f1_thr": th["val_f1_at_threshold"], "val_f1_0.5": th["val_f1_at_0.5"],
        }
    return rows


def main(path: Path) -> int:
    a_metrics = load_json(RUN_A / "metrics.json")
    a_thresholds = load_json(RUN_A / "thresholds.json")
    b_metrics = load_json(RUN_B / "metrics.json")
    b_thresholds = load_json(RUN_B / "thresholds.json")
    counts, totals = split_counts()
    a_rows = class_data(a_metrics, a_thresholds, counts)
    b_rows = class_data(b_metrics, b_thresholds, counts)

    wb = load_workbook(path, data_only=True)
    failures = []
    checks = 0

    def close(got, want, tol=1e-6):
        if isinstance(want, (int, float)) and isinstance(got, (int, float)):
            return abs(float(got) - float(want)) <= tol
        return got == want

    def check(where, field, got, want, tol=1e-6):
        nonlocal checks
        checks += 1
        if not close(got, want, tol):
            failures.append(f"{where}: {field} got {got!r}, want {want!r}")

    expected_sheets = ["Summary", "Per-class results", "Thresholds", "Threshold rule", "Routing", "Split", "Definitions and method"]
    check("workbook", "sheet names", wb.sheetnames, expected_sheets)

    # ---------------------------------------------------------------- Summary
    ws = wb["Summary"]
    summary = {}
    for r in range(1, ws.max_row + 1):
        label = ws.cell(r, 1).value
        b = ws.cell(r, 2).value
        c = ws.cell(r, 3).value
        d = ws.cell(r, 4).value
        if isinstance(label, str) and all(isinstance(v, (int, float)) for v in (b, c, d)):
            summary[label] = (b, c, d)

    a_judge = a_metrics["macro_auprc_judgeable"]
    b_judge = b_metrics["macro_auprc_judgeable"]
    a_f1_half = a_metrics["macro_f1_0.5"]
    b_f1_half = b_metrics["macro_f1_0.5"]
    a_f1_thr = a_metrics["macro_f1_val_thr"]
    b_f1_thr = b_metrics["macro_f1_val_thr"]
    a_exact_half = a_metrics["exact_match"]
    b_exact_half = b_metrics["exact_match"]
    a_exact_thr = a_metrics["exact_match_val_thr"]
    b_exact_thr = b_metrics["exact_match_val_thr"]
    a_ms = a_metrics["timing"]["inference_ms_per_image"]
    b_ms = b_metrics["timing"]["inference_ms_per_image"]

    expected_summary = {
        "Answers per picture": (12, 13, 1),
        "Lens AUPRC, 8 classes in the average": (a_judge, b_judge, b_judge - a_judge),
        "Macro F1 at 0.5": (a_f1_half, b_f1_half, b_f1_half - a_f1_half),
        "Macro F1 at chosen thresholds": (a_f1_thr, b_f1_thr, b_f1_thr - a_f1_thr),
        "Exact match at 0.5": (a_exact_half, b_exact_half, b_exact_half - a_exact_half),
        "Exact match at chosen thresholds": (a_exact_thr, b_exact_thr, b_exact_thr - a_exact_thr),
        "Inference time per picture (ms)": (a_ms, b_ms, round(b_ms - a_ms, 2)),
        "Lens AUPRC, all 12 classes": (a_metrics["macro_auprc_all"], b_metrics["macro_auprc_all"],
                                        b_metrics["macro_auprc_all"] - a_metrics["macro_auprc_all"]),
        "Hamming loss at 0.5": (a_metrics["hamming_loss"], b_metrics["hamming_loss"],
                                 b_metrics["hamming_loss"] - a_metrics["hamming_loss"]),
        "Hamming loss at chosen thresholds": (a_metrics["hamming_loss_val_thr"], b_metrics["hamming_loss_val_thr"],
                                               b_metrics["hamming_loss_val_thr"] - a_metrics["hamming_loss_val_thr"]),
    }
    for label, want in expected_summary.items():
        got = summary.get(label)
        if got is None:
            failures.append(f"Summary: missing row {label!r}")
            continue
        for index, field in enumerate(("Lens only", "Lens + object flag", "Difference")):
            tol = 0.005 if label == "Inference time per picture (ms)" and field == "Difference" else 1e-6
            check(f"Summary {label!r}", field, got[index], want[index], tol)

    # ---------------------------------------------------------------- Per-class
    ws = wb["Per-class results"]
    expected = {}
    for run_label, rows in (("Lens only", a_rows), ("Lens + object flag", b_rows)):
        for code in CLASS_ORDER:
            expected[(run_label, rows[code]["name"])] = rows[code]
    seen = set()
    for r in range(5, ws.max_row + 1):
        run = ws.cell(r, 1).value
        if run not in RUN_LABELS:
            break
        name = ws.cell(r, 2).value
        item = expected.get((run, name))
        if item is None:
            failures.append(f"Per-class: unexpected row {run!r}, {name!r}")
            continue
        seen.add((run, name))
        where = f"Per-class {run!r} {name!r}"
        check(where, "test pictures", ws.cell(r, 3).value, item["test"])
        check(where, "in lens average", ws.cell(r, 4).value, "Yes" if item["test"] >= 20 else "No")
        check(where, "AUPRC", ws.cell(r, 5).value, item["auprc"])
        check(where, "F1 at 0.5", ws.cell(r, 6).value, item["f1_0.5"])
        check(where, "F1 at chosen", ws.cell(r, 7).value, item["f1_thr"])
        check(where, "threshold", ws.cell(r, 8).value, item["threshold"])
    check("Per-class", "row count", len(seen), 24)

    # ---------------------------------------------------------------- Thresholds
    ws = wb["Thresholds"]
    expected = {}
    for run_label, rows in (("Lens only", a_rows), ("Lens + object flag", b_rows)):
        for code in CLASS_ORDER + (["object_present"] if "object_present" in rows else []):
            expected[(run_label, rows[code]["name"])] = rows[code]
    seen = set()
    for r in range(5, ws.max_row + 1):
        run = ws.cell(r, 1).value
        if run not in RUN_LABELS:
            break
        name = ws.cell(r, 2).value
        item = expected.get((run, name))
        if item is None:
            failures.append(f"Thresholds: unexpected row {run!r}, {name!r}")
            continue
        seen.add((run, name))
        where = f"Thresholds {run!r} {name!r}"
        check(where, "validation pictures", ws.cell(r, 3).value, item["val"])
        check(where, "test pictures", ws.cell(r, 4).value, item["test"])
        check(where, "threshold", ws.cell(r, 5).value, item["threshold"])
        basis = "Default, under 10" if item["source"] == "default" else "Chosen on validation"
        check(where, "basis", ws.cell(r, 6).value, basis)
        check(where, "validation F1 at threshold", ws.cell(r, 7).value, item["val_f1_thr"])
        check(where, "validation F1 at 0.5", ws.cell(r, 8).value, item["val_f1_0.5"])
        check(where, "change", ws.cell(r, 9).value, item["val_f1_thr"] - item["val_f1_0.5"])
    check("Thresholds", "row count", len(seen), 25)

    # ---------------------------------------------------------------- Routing
    ws = wb["Routing"]
    obj = b_metrics["object_column"]
    routing = {
        "Object, no lens condition": (obj["pictures_object_only"],
                                      round(obj["fire_rate_object_only_0.5"] * obj["pictures_object_only"]),
                                      obj["fire_rate_object_only_0.5"],
                                      round(obj["fire_rate_object_only"] * obj["pictures_object_only"]),
                                      obj["fire_rate_object_only"]),
        "Lens condition and object": (obj["pictures_mixed"],
                                      round(obj["fire_rate_mixed_0.5"] * obj["pictures_mixed"]),
                                      obj["fire_rate_mixed_0.5"],
                                      round(obj["fire_rate_mixed"] * obj["pictures_mixed"]),
                                      obj["fire_rate_mixed"]),
        "Clear": (obj["pictures_clear"],
                  round(obj["fire_rate_clear_0.5"] * obj["pictures_clear"]),
                  obj["fire_rate_clear_0.5"],
                  round(obj["fire_rate_clear"] * obj["pictures_clear"]),
                  obj["fire_rate_clear"]),
    }
    seen = set()
    for r in range(5, ws.max_row + 1):
        group = ws.cell(r, 1).value
        if group not in routing:
            break
        seen.add(group)
        want = routing[group]
        where = f"Routing {group!r}"
        check(where, "test pictures", ws.cell(r, 2).value, want[0])
        check(where, "fires at 0.5", ws.cell(r, 3).value, want[1])
        check(where, "share at 0.5", ws.cell(r, 4).value, want[2])
        check(where, "fires at 0.55", ws.cell(r, 5).value, want[3])
        check(where, "share at 0.55", ws.cell(r, 6).value, want[4])
    check("Routing", "row count", len(seen), 3)

    # ---------------------------------------------------------------- Split
    ws = wb["Split"]
    seen = set()
    for r in range(5, ws.max_row + 1):
        name = ws.cell(r, 1).value
        if name == "All pictures":
            check("Split 'All pictures'", "training", ws.cell(r, 2).value, totals["train"])
            check("Split 'All pictures'", "validation", ws.cell(r, 3).value, totals["val"])
            check("Split 'All pictures'", "test", ws.cell(r, 4).value, totals["test"])
            check("Split 'All pictures'", "all", ws.cell(r, 5).value, sum(totals.values()))
            break
        if name == "Any object (one flag)":
            want = counts["object_present"]
        elif name == "Clear pictures":
            want = counts["is_clear"]
        else:
            code = next((c for c in CLASS_ORDER if a_rows[c]["name"] == name), None)
            if code is None:
                break
            want = counts[code]
        seen.add(name)
        check(f"Split {name!r}", "training", ws.cell(r, 2).value, want["train"])
        check(f"Split {name!r}", "validation", ws.cell(r, 3).value, want["val"])
        check(f"Split {name!r}", "test", ws.cell(r, 4).value, want["test"])
        check(f"Split {name!r}", "all", ws.cell(r, 5).value, want["train"] + want["val"] + want["test"])
    check("Split", "row count", len(seen), 14)

    # ---------------------------------------------------------------- No internal names
    tokens = ("variant", "run/", "P1_", "P2_", "md5", ".json", ".npz", "predictions", "labels_", "A/B", "\u2014")
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    for token in tokens:
                        if token in cell.value:
                            failures.append(f"{sheet.title} {cell.coordinate}: internal token {token!r}")
                            break

    if failures:
        print(f"FAILED {len(failures)} of {checks} checks")
        for failure in failures[:40]:
            print(" -", failure)
        return 1
    print(f"verified {checks} checks across {len(wb.sheetnames)} sheets")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    raise SystemExit(main(target))
