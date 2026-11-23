"""Verify the frozen 17-class workbook against the source data.

Run from the repository root:

    uv run python experiments/frozen_data_experiments/multilabel_cnn/results/verify_workbook.py

Exits 0 only when every check passes. It reads the workbook values, not the
formatting, and compares them with workbook_data.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook

from workbook_data import load_data

HERE = Path(__file__).resolve().parent
PATH = HERE / "frozen_multilabel_results.xlsx"

checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def close(actual, expected, tol: float = 1e-9) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def pct(value: float) -> float:
    return round(float(value) * 100.0, 1)


def find_row(ws, column: int, text: str, start: int = 1) -> int:
    for row in range(start, ws.max_row + 1):
        value = ws.cell(row=row, column=column).value
        if value == text:
            return row
    raise AssertionError(f"{ws.title}: row with {text!r} not found")


def table_map(ws, header_row: int, key_col: int = 2) -> dict[str, int]:
    result = {}
    for row in range(header_row + 1, ws.max_row + 1):
        key = ws.cell(row=row, column=key_col).value
        if key:
            result[key] = row
    return result


def main() -> int:
    data = load_data()
    wb = load_workbook(PATH, data_only=True)
    expected_sheets = [
        "Read me",
        "Summary",
        "Pass fail",
        "Pass images",
        "Per class",
        "Class split",
        "Selected thresholds",
        "Threshold rule",
        "Scope and exclusions",
        "Method",
        "Definitions",
    ]
    check(wb.sheetnames == expected_sheets, f"sheet order {wb.sheetnames}")
    check(wb.properties.creator == "Pranay", "creator is not Pranay")

    for ws in wb.worksheets:
        check(ws.cell(row=1, column=1).value is not None, f"{ws.title}: no title")
        check(ws.cell(row=2, column=1).value is not None, f"{ws.title}: no opening line")
        check(bool(ws.print_area), f"{ws.title}: no print area")

    # Summary
    ws = wb["Summary"]
    check(len(ws._charts) == 1, f"Summary charts {len(ws._charts)}")
    header = find_row(ws, 1, "Measure")
    summary = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=2).value
        for row in range(header + 1, header + 7)
    }
    check(close(summary["Macro F1 (%)"], pct(data["macro"]["f1_05"])), f"Macro F1 {summary['Macro F1 (%)']}")
    check(close(summary["Macro precision (%)"], pct(data["macro"]["precision_05"])), "Macro precision")
    check(close(summary["Macro recall (%)"], pct(data["macro"]["recall_05"])), "Macro recall")
    check(close(summary["Macro AUROC"], round(data["macro"]["auroc"], 3)), "Macro AUROC")
    check(close(summary["Macro AUPRC"], round(data["macro"]["auprc"], 3)), "Macro AUPRC")
    check(close(summary["Inference per picture (ms)"], round(data["timing"]["inference_ms_per_image"], 2)), "Inference ms")
    check("Clear (42 pictures)" in ws.cell(row=3, column=1).value, "Summary scope missing Clear")
    check("281" in ws.cell(row=3, column=1).value, "Summary scope missing 281")
    for item in data["excluded"]:
        check(item["code"] in ws.cell(row=3, column=1).value, f"Summary scope missing {item['code']}")
    check("AUPRC" in ws.cell(row=12, column=1).value, "Summary missing AUPRC note")
    chosen = ws.cell(row=13, column=1).value
    for label, value in (
        ("F1", pct(data["macro"]["f1_chosen"])),
        ("precision", pct(data["macro"]["precision_chosen"])),
        ("recall", pct(data["macro"]["recall_chosen"])),
    ):
        check(f"{label} {value:.1f}%" in chosen, f"Summary chosen line missing {label}")

    # Pass/fail
    ws = wb["Pass fail"]
    pf = data["pass_fail"]
    counts = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=2).value
        for row in range(7, 12)
    }
    for label, value in (
        ("True Accept (TA)", pf["TA"]),
        ("False Reject (FR)", pf["FR"]),
        ("True Reject (TR)", pf["TR"]),
        ("False Accept (FA)", pf["FA"]),
        ("Total", data["test_pictures"]),
    ):
        check(counts[label] == value, f"Pass/fail count {label}")
    check(pf["TA"] + pf["FR"] + pf["TR"] + pf["FA"] == data["test_pictures"], "Pass/fail counts add")
    check(pf["TA"] + pf["FR"] == pf["actual_pass"], "Pass/fail actual pass")
    check(pf["TR"] + pf["FA"] == pf["actual_fail"], "Pass/fail actual fail")
    check(pf["TA"] + pf["FA"] == pf["predicted_pass"], "Pass/fail predicted pass")
    check(pf["TR"] + pf["FR"] == pf["predicted_fail"], "Pass/fail predicted fail")
    rates = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=3).value
        for row in range(15, 19)
    }
    for label, value in (
        ("TAR", pf["tar"]),
        ("TRR", pf["trr"]),
        ("FAR", pf["far"]),
        ("FRR", pf["frr"]),
    ):
        check(close(rates[label], pct(value)), f"Pass/fail rate {label}")
    check(close(pf["tar"] + pf["frr"], 1.0), "TAR and FRR do not add")
    check(close(pf["trr"] + pf["far"], 1.0), "TRR and FAR do not add")
    causes = {
        ws.cell(row=row, column=1).value: (
            ws.cell(row=row, column=2).value,
            ws.cell(row=row, column=3).value,
        )
        for row in range(23, 30)
    }
    for cause in pf["causes"]:
        check(
            causes[cause["label"]] == (cause["actual"], cause["predicted"]),
            f"Pass/fail cause {cause['label']}",
        )
    check(ws.cell(row=34, column=1).value == "Clear", "Pass/fail rule Clear")
    check(ws.cell(row=35, column=1).value == "Bubble only", "Pass/fail rule Bubble")
    check(ws.cell(row=35, column=2).value == "Pass", "Pass/fail Bubble verdict")
    check(ws.cell(row=36, column=1).value == "Bubble Cluster", "Pass/fail rule Cluster")
    check(ws.cell(row=36, column=2).value == "Fail", "Pass/fail Cluster verdict")

    # Per class
    ws = wb["Per class"]
    headers = [ws.cell(row=3, column=c).value for c in range(1, 14)]
    check(
        headers
        == [
            "Group",
            "Class",
            "Pass class",
            "Test pictures",
            "TA",
            "FR",
            "TR",
            "FA",
            "Precision (%)",
            "Recall (%)",
            "F1 (%)",
            "AUROC",
            "AUPRC",
        ],
        f"Per class headers {headers}",
    )
    check(ws.freeze_panes == "A4", "Per class freeze")
    check(ws.auto_filter.ref is None, "Per class filter")
    rows = {ws.cell(row=row, column=2).value: row for row in range(4, 21)}
    check(len(rows) == 17, f"Per class rows {len(rows)}")
    group_merges = [r for r in ws.merged_cells.ranges if r.min_col == 1 and r.max_col == 1]
    check(len(group_merges) == 3, f"Per class group merges {len(group_merges)}")
    previous_group = None
    for item in data["reader_rows"]:
        row = rows[item["name"]]
        if item["group"] != previous_group:
            check(ws.cell(row=row, column=1).value == item["group"], f"{item['name']} group")
        previous_group = item["group"]
        check(ws.cell(row=row, column=2).value == item["name"], f"{item['name']} name")
        check(ws.cell(row=row, column=3).value == item["pass_class"], f"{item['name']} pass class")
        check(ws.cell(row=row, column=4).value == item["support"], f"{item['name']} support")
        check(ws.cell(row=row, column=5).value == item["ta_05"], f"{item['name']} TA")
        check(ws.cell(row=row, column=6).value == item["fr_05"], f"{item['name']} FR")
        check(ws.cell(row=row, column=7).value == item["tr_05"], f"{item['name']} TR")
        check(ws.cell(row=row, column=8).value == item["fa_05"], f"{item['name']} FA")
        check(close(ws.cell(row=row, column=9).value, pct(item["precision_05"])), f"{item['name']} precision")
        check(close(ws.cell(row=row, column=10).value, pct(item["recall_05"])), f"{item['name']} recall")
        check(close(ws.cell(row=row, column=11).value, pct(item["f1_05"])), f"{item['name']} F1")
        check(close(ws.cell(row=row, column=12).value, round(item["auroc"], 3)), f"{item['name']} AUROC")
        check(close(ws.cell(row=row, column=13).value, round(item["auprc"], 3)), f"{item['name']} AUPRC")
        check(
            item["ta_05"] + item["fr_05"] + item["tr_05"] + item["fa_05"] == data["test_pictures"],
            f"{item['name']} counts do not add",
        )
    # The pass classes must occupy the first rows.
    pass_names = [item["name"] for item in data["reader_rows"] if item["pass_class"] != "Fail"]
    check(pass_names == [item["name"] for item in data["reader_rows"]][: len(pass_names)], "pass classes not first")
    check(ws.cell(row=4, column=3).value == "Pass", "first row is not Bubble")

    # Pass images
    ws = wb["Pass images"]
    headers = [ws.cell(row=5, column=c).value for c in range(1, 6)]
    check(
        headers == ["Class", "Pass class", "Pass pictures", "Predicted pass", "Predicted fail"],
        f"Pass images headers {headers}",
    )
    pass_rows = {ws.cell(row=row, column=1).value: row for row in range(6, 11)}
    check(len(pass_rows) == 5, f"Pass images class rows {len(pass_rows)}")
    for item in data["pass_images"]["by_class"]:
        if item["pass_class"] == "Fail":
            continue
        row = pass_rows[item["name"]]
        check(ws.cell(row=row, column=2).value == item["pass_class"], f"Pass images {item['name']} class")
        check(ws.cell(row=row, column=3).value == item["pictures"], f"Pass images {item['name']} pictures")
        check(ws.cell(row=row, column=4).value == item["predicted_pass"], f"Pass images {item['name']} pass")
        check(ws.cell(row=row, column=5).value == item["predicted_fail"], f"Pass images {item['name']} fail")
    check(ws.cell(row=11, column=1).value == "All truth-pass pictures", "Pass images total label")
    check(ws.cell(row=11, column=3).value == data["pass_images"]["total"], "Pass images total")
    check(ws.cell(row=11, column=4).value == data["pass_images"]["predicted_pass"], "Pass images total pass")
    check(ws.cell(row=11, column=5).value == data["pass_images"]["predicted_fail"], "Pass images total fail")

    headers = [ws.cell(row=16, column=c).value for c in range(1, 5)]
    check(
        headers == ["Class set of the picture", "Pass pictures", "Predicted pass", "Predicted fail"],
        f"Pass images set headers {headers}",
    )
    set_rows = {ws.cell(row=row, column=1).value: row for row in range(17, 21)}
    check(len(set_rows) == len(data["pass_images"]["by_set"]), f"Pass images set rows {len(set_rows)}")
    for item in data["pass_images"]["by_set"]:
        row = set_rows[item["label"]]
        check(ws.cell(row=row, column=2).value == item["pictures"], f"Pass set {item['label']} pictures")
        check(ws.cell(row=row, column=3).value == item["predicted_pass"], f"Pass set {item['label']} pass")
        check(ws.cell(row=row, column=4).value == item["predicted_fail"], f"Pass set {item['label']} fail")
    check(ws.cell(row=21, column=2).value == data["pass_images"]["total"], "Pass set total")
    check(ws.cell(row=21, column=3).value == data["pass_images"]["predicted_pass"], "Pass set total pass")
    check(ws.cell(row=21, column=4).value == data["pass_images"]["predicted_fail"], "Pass set total fail")

    # Class split
    ws = wb["Class split"]
    headers = [ws.cell(row=5, column=c).value for c in range(1, 7)]
    check(
        headers == ["Group", "Class", "Train", "Validation", "Test", "Total"],
        f"Class split headers {headers}",
    )
    split_rows = {ws.cell(row=row, column=2).value: row for row in range(6, 23)}
    check(len(split_rows) == 17, f"Class split rows {len(split_rows)}")
    group_merges = [r for r in ws.merged_cells.ranges if r.min_col == 1 and r.max_col == 1]
    check(len(group_merges) == 3, f"Class split group merges {len(group_merges)}")
    for item in data["class_split"]:
        row = split_rows[item["name"]]
        check(ws.cell(row=row, column=3).value == item["train"], f"Class split {item['name']} train")
        check(ws.cell(row=row, column=4).value == item["val"], f"Class split {item['name']} val")
        check(ws.cell(row=row, column=5).value == item["test"], f"Class split {item['name']} test")
        check(ws.cell(row=row, column=6).value == item["total"], f"Class split {item['name']} total")
    check(ws.cell(row=23, column=1).value == "All analysed pictures", "Class split total label")
    check(ws.cell(row=23, column=3).value == data["splits"]["train"], "Class split total train")
    check(ws.cell(row=23, column=4).value == data["splits"]["val"], "Class split total val")
    check(ws.cell(row=23, column=5).value == data["splits"]["test"], "Class split total test")
    check(ws.cell(row=23, column=6).value == data["analysed"], "Class split total pictures")

    headers = [ws.cell(row=28, column=c).value for c in range(1, 11)]
    check(
        headers
        == [
            "Class",
            "Train total",
            "Train tagged",
            "Train untagged",
            "Validation total",
            "Validation tagged",
            "Validation untagged",
            "Test total",
            "Test tagged",
            "Test untagged",
        ],
        f"Size split headers {headers}",
    )
    size_rows = {ws.cell(row=row, column=1).value: row for row in range(29, 33)}
    check(len(size_rows) == 4, f"Size split rows {len(size_rows)}")
    for item in data["size_split"]:
        row = size_rows[item["name"]]
        for col, key in enumerate(
            [
                "train_total",
                "train_tagged",
                "train_untagged",
                "val_total",
                "val_tagged",
                "val_untagged",
                "test_total",
                "test_tagged",
                "test_untagged",
            ],
            start=2,
        ):
            check(ws.cell(row=row, column=col).value == item[key], f"Size split {item['name']} {key}")

    # Selected thresholds
    ws = wb["Selected thresholds"]
    headers = [ws.cell(row=5, column=c).value for c in range(1, 16)]
    check(
        headers
        == [
            "Group",
            "Class",
            "Cut",
            "Validation pictures",
            "Validation precision (%)",
            "Validation recall (%)",
            "Validation F1 (%)",
            "Test precision (%)",
            "Test recall (%)",
            "Test F1 (%)",
            "Test TA",
            "Test FR",
            "Test TR",
            "Test FA",
            "Test pictures",
        ],
        f"Selected thresholds headers {headers}",
    )
    check("provisional" in ws.cell(row=3, column=1).value.lower(), "Selected thresholds not provisional")
    check(ws.freeze_panes == "A6", "Selected thresholds freeze")
    check(ws.auto_filter.ref is None, "Selected thresholds filter")
    rows = {ws.cell(row=row, column=2).value: row for row in range(6, 23)}
    check(len(rows) == 17, f"Selected thresholds rows {len(rows)}")
    group_merges = [r for r in ws.merged_cells.ranges if r.min_col == 1 and r.max_col == 1]
    check(len(group_merges) == 3, f"Selected thresholds group merges {len(group_merges)}")
    seen_groups = set()
    for item in data["rows"]:
        row = rows[item["name"]]
        if item["group"] not in seen_groups:
            check(ws.cell(row=row, column=1).value == item["group"], f"{item['name']} group")
            seen_groups.add(item["group"])
        check(close(ws.cell(row=row, column=3).value, round(item["cut"], 2)), f"{item['name']} cut")
        check(ws.cell(row=row, column=4).value == item["val_support"], f"{item['name']} val support")
        check(close(ws.cell(row=row, column=5).value, pct(item["val_precision_at_cut"])), f"{item['name']} val precision")
        check(close(ws.cell(row=row, column=6).value, pct(item["val_recall_at_cut"])), f"{item['name']} val recall")
        check(close(ws.cell(row=row, column=7).value, pct(item["val_f1_at_cut"])), f"{item['name']} val F1")
        check(close(ws.cell(row=row, column=8).value, pct(item["precision_chosen"])), f"{item['name']} test precision")
        check(close(ws.cell(row=row, column=9).value, pct(item["recall_chosen"])), f"{item['name']} test recall")
        check(close(ws.cell(row=row, column=10).value, pct(item["f1_chosen"])), f"{item['name']} test F1")
        check(ws.cell(row=row, column=11).value == item["ta_chosen"], f"{item['name']} test TA")
        check(ws.cell(row=row, column=12).value == item["fr_chosen"], f"{item['name']} test FR")
        check(ws.cell(row=row, column=13).value == item["tr_chosen"], f"{item['name']} test TR")
        check(ws.cell(row=row, column=14).value == item["fa_chosen"], f"{item['name']} test FA")
        check(ws.cell(row=row, column=15).value == item["support"], f"{item['name']} test support")

    # Threshold rule
    ws = wb["Threshold rule"]
    rule = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=2).value
        for row in range(5, 13)
    }
    check(rule["Selection split"] == "Validation", "rule selection split")
    check("0.05 to 0.95" in rule["Grid"], "rule grid")
    check("19 cuts" in rule["Grid"], "rule grid count")
    check(rule["Minimum validation pictures"] == "10", "rule min pictures")
    check(rule["Default if below minimum"] == "0.50", "rule default")
    check(rule["Seeds"] == "1", "rule seeds")
    check(rule["Classes left at 0.5"] == "None", "rule defaults")
    check("0.01-step" in ws.cell(row=14, column=1).value, "rule protocol gap")

    # Scope
    ws = wb["Scope and exclusions"]
    population = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=2).value
        for row in range(6, 13)
    }
    check(population["Records in the frozen store"] == data["records"], "population records")
    check(population["Duplicate records removed"] == -data["duplicates"], "population duplicates")
    check(population["Distinct pictures"] == data["distinct"], "population distinct")
    check(population["Pictures with no label removed"] == -data["unmarked"], "population unmarked")
    check(population["Labelled pictures"] == data["labelled"], "population labelled")
    check(population["Clear pictures excluded"] == -data["clear"], "population clear")
    check(population["Analysed pictures"] == data["analysed"], "population analysed")
    splits = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=2).value
        for row in range(16, 19)
    }
    check(splits["Train"] == data["splits"]["train"], "split train")
    check(splits["Validation"] == data["splits"]["val"], "split val")
    check(splits["Test"] == data["splits"]["test"], "split test")
    excluded = {
        ws.cell(row=row, column=1).value: (
            ws.cell(row=row, column=2).value,
            ws.cell(row=row, column=3).value,
        )
        for row in range(24, 30)
    }
    for item in data["excluded"]:
        check(excluded[item["code"]] == (item["name"], item["pictures"]), f"excluded {item['code']}")
    check(ws.cell(row=30, column=2).value == data["excluded_union"], "excluded union")
    check(ws.cell(row=31, column=2).value == data["excluded_only"], "excluded only")
    check("35 pictures, 36 annotations" in ws.cell(row=32, column=1).value, "annotation note")
    check("281" in ws.cell(row=33, column=1).value, "281 note")

    # Method
    ws = wb["Method"]
    method = {
        ws.cell(row=row, column=1).value: ws.cell(row=row, column=2).value
        for row in range(5, 20)
    }
    check(method["Model"] == "ResNet50", "method model")
    check(method["Input"] == "224 x 224 pixels", "method input")
    check(method["Training pictures"] == "9,537", "method train")
    check(method["Validation pictures"] == "2,049", "method val")
    check(method["Test pictures"] == "2,045", "method test")
    check(method["Epochs"] == "50", "method epochs")
    check(method["Batch size"] == "8", "method batch")
    check(method["Seed"] == "42", "method seed")
    check("3.05 ms per picture" in method["Test inference"], "method inference")
    check(method["Main threshold"] == "0.50", "method threshold")
    check("not model outputs" in ws.cell(row=21, column=1).value, "method size-flags note")

    # Definitions
    ws = wb["Definitions"]
    terms = {ws.cell(row=row, column=1).value for row in range(5, 24)}
    for term in ("Support", "Prevalence", "Precision", "Recall", "F1", "Macro", "AUROC", "AUPRC", "Threshold", "Size tag", "Clear", "Excluded class", "Pass class", "Truth pass, truth fail", "Predicted pass, predicted fail"):
        check(term in terms, f"definition missing {term}")

    banned = [
        "D:/",
        "C:/",
        "/home/",
        "/data/",
        "metrics.json",
        "predictions.npz",
        "thresholds.json",
        "stage_status",
        "frozen17",
        "20261119",
        "frozen_70_15_15",
        "watcher",
        "run.log",
        "run folder",
        "vm/",
    ]
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    for token in banned:
                        check(token not in cell.value, f"{ws.title}!{cell.coordinate} leaks {token}")

    print(f"{checks} checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
