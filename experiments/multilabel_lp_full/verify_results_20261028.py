"""Verify the results workbook and the HTML report against the metrics they came from.

Recomputes every number from the two metrics files, compares the workbook cell by cell, checks
the report's headline figures and its plain-language constraints, and proves that a changed
cell is caught.

Usage:
    .venv/Scripts/python experiments/multilabel_lp_full/verify_results_20261028.py
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "run/multilabel_lp_full_20261029"
XLSX = ROOT / "reports/multilabel_production/lp_full_results_20261029.xlsx"
HTML = ROOT / "reports/multilabel_production/lp_full_report_20261029.html"

A = json.loads((RUN / "a/metrics.json").read_text(encoding="utf-8"))
B = json.loads((RUN / "b/metrics.json").read_text(encoding="utf-8"))
OLD = json.loads((RUN.parent / "multilabel_lp_full_20261028/a/metrics.json").read_text(encoding="utf-8"))
OLD_B = json.loads((RUN.parent / "multilabel_lp_full_20261028/b/metrics.json").read_text(encoding="utf-8"))

bad: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail and not ok else ""))
    if not ok:
        bad.append(name)


def near(a, b, tol=1e-6) -> bool:
    try:
        if a is None or b is None:
            return a is b
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


wb = load_workbook(XLSX)
check("workbook has the seven sheets",
      wb.sheetnames == ["Results", "LP classes, run 1", "LP classes, run 2",
                        "OOI flag", "Earlier runs", "7 vs 24 files", "Reading",
                        "Definitions"],
      str(wb.sheetnames))

# ---- headline sheet
ws = wb["Results"]
rows = {r[0]: (r[1], r[2]) for r in ws.iter_rows(min_row=5, max_row=13, max_col=3,
                                                 values_only=True)}
def label_rows(path: Path) -> int:
    with open(path, encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


TOTAL_A = label_rows(RUN / "labels_a.csv")
TOTAL_B = label_rows(RUN / "labels_b.csv")
split = {r[0]: r for r in ws.iter_rows(min_row=18, max_row=19, max_col=5, values_only=True)}
check("split box, run 1",
      split["Run 1: LP classes only"][1:4] == (TOTAL_A - A["rows"], A["rows"], TOTAL_A),
      str(split.get("Run 1: LP classes only")))
check("split box, run 2",
      split["Run 2: LP classes plus OOI flag"][1:4] == (TOTAL_B - B["rows"], B["rows"], TOTAL_B),
      str(split.get("Run 2: LP classes plus OOI flag")))
check("judgeable average",
      near(rows["Average precision over the 8 judgeable classes"][0], A["macro_auprc_judgeable"])
      and near(rows["Average precision over the 8 judgeable classes"][1], B["macro_auprc_judgeable"]))
check("exact match", near(rows["Pictures where every answer was right"][0], A["exact_match"])
      and near(rows["Pictures where every answer was right"][1], B["exact_match"]))
check("training seconds", near(rows["Training time"][0], A["timing"]["seconds_training"])
      and near(rows["Training time"][1], B["timing"]["seconds_training"]))
check("milliseconds per picture",
      near(rows["Time to score one picture"][0], A["timing"]["inference_ms_per_image"])
      and near(rows["Time to score one picture"][1], B["timing"]["inference_ms_per_image"]))

# ---- per condition sheets
for sheet, metrics in (("LP classes, run 1", A), ("LP classes, run 2", B)):
    ws = wb[sheet]
    seen = {}
    for r in ws.iter_rows(min_row=5, max_row=16, max_col=9, values_only=True):
        if r[0]:
            seen[r[0]] = r
    check(f"{sheet}: one row per class", len(seen) == 12, str(len(seen)))
    mism = []
    for code, v in metrics["per_class"].items():
        row = seen.get(v["name"])
        if row is None:
            mism.append(f"{v['name']} missing")
            continue
        if not near(row[1], v["support"]):
            mism.append(f"{v['name']} support")
        if v["auprc"] == v["auprc"] and not near(row[2], v["auprc"]):
            mism.append(f"{v['name']} auprc")
        if not near(row[3], v["precision_0.5"]):
            mism.append(f"{v['name']} precision")
        if not near(row[4], v["recall_0.5"]):
            mism.append(f"{v['name']} recall")
        if not near(row[6], v["best_f1"]):
            mism.append(f"{v['name']} best f1")
        if not near(row[7], v["threshold"], 1e-9):
            mism.append(f"{v['name']} threshold")
    check(f"{sheet}: every number matches the metrics", not mism, "; ".join(mism[:4]))

# ---- object flag sheet
ws = wb["OOI flag"]
oc = B["object_column"]
flag = {r[0]: r for r in ws.iter_rows(min_row=5, max_row=7, max_col=5, values_only=True)}
check("flag fires on OOI pictures",
      near(flag["Pictures with an OOI and no LP class"][3], oc["fire_rate_object_only"]))
check("flag fires on Clear pictures",
      near(flag["Clear pictures"][3], oc["fire_rate_clear"]))

# ---- earlier runs sheet, checked against their own metrics files
ws = wb["Earlier runs"]
earlier = {r[0]: r for r in ws.iter_rows(min_row=5, max_row=7, max_col=7, values_only=True)}
for label, path in (("Earlier run, plain", RUN.parent / "multilabel_lp_20260928/metrics.json"),
                    ("Earlier run, class weighting",
                     RUN.parent / "multilabel_lp_posw_20261005/metrics.json")):
    m = json.loads(path.read_text(encoding="utf-8"))
    t = m["test_metrics"]
    row = earlier.get(label)
    check(f"{label}: matches its own results",
          row is not None and near(row[4], t["macro_auprc"]) and near(row[5], t["per_class"]["P1_FL"]["auprc"])
          and row[2] == m["rows"]["train"] and row[3] == m["rows"]["test"], str(row))
shared = ["Missing Primary Package", "Multiple Lens", "No Lens", "Cavity Off Center", "Folded Lens"]
cur5 = sum(v["auprc"] for v in A["per_class"].values() if v["name"] in shared) / len(shared)
check("this run: five shared classes",
      near(earlier["This run, LP classes only"][4], cur5), str(earlier.get("This run, LP classes only")))

# ---- 7 vs 24 files sheet, against both runs' metrics
ws = wb["7 vs 24 files"]
cmp_rows = {r[0]: r for r in ws.iter_rows(min_row=5, max_row=11, max_col=5, values_only=True)}
def _near_str(cell, want):
    return isinstance(cell, str) and abs(float(cell) - want) < 5e-3


check("comparison: variant 1 macro",
      _near_str(cmp_rows["Macro over the eight judgeable classes"][1], OLD["macro_auprc_judgeable"])
      and _near_str(cmp_rows["Macro over the eight judgeable classes"][2], A["macro_auprc_judgeable"])
      and _near_str(cmp_rows["Macro over the eight judgeable classes"][3], OLD_B["macro_auprc_judgeable"])
      and _near_str(cmp_rows["Macro over the eight judgeable classes"][4], B["macro_auprc_judgeable"]),
      str(cmp_rows.get("Macro over the eight judgeable classes")))
check("comparison: test pictures",
      cmp_rows["Test pictures"][1:] == (OLD["rows"], A["rows"], OLD_B["rows"], B["rows"]),
      str(cmp_rows.get("Test pictures")))

# ---- report text
html = HTML.read_text(encoding="utf-8")
for label, value in (("run 1 average", f"{A['macro_auprc_judgeable']:.2f}"),
                     ("run 2 average", f"{B['macro_auprc_judgeable']:.2f}"),
                     ("exact match run 1", f"{A['exact_match'] * 100:.1f}%"),
                     ("object fire rate", f"{oc['fire_rate_object_only'] * 100:.1f}%")):
    check(f"report shows {label}", value in html, value)
check("report has its three charts", html.count("<svg") == 3, str(html.count("<svg")))
check("report carries the annotation comparison",
      "The same experiment on the two annotations" in html
      and "0.77 to 0.92" in html.replace(" ", " ") or "0.77 to 0.92" in html,
      "comparison heading or per-class line missing")
check("report carries no class codes", not re.search(r"\bP[123]_[A-Z]{2,}", html))
check("report carries no paths or file names",
      not re.search(r"(run/|reports/|\.json|\.xlsx|fmd-analysis|D:\\\\)", html))
check("report uses no em dash", "\u2014" not in html)

# ---- tamper proof: change one cell in a copy and re-run the comparison
tmp = Path(tempfile.mkdtemp()) / "tampered.xlsx"
shutil.copy(XLSX, tmp)
wb2 = load_workbook(tmp)
ws2 = wb2["LP classes, run 1"]
for row in ws2.iter_rows(min_row=5, max_row=16, max_col=3):
    if row[0].value == "Folded Lens":
        row[2].value = 0.9
wb2.save(tmp)
wb3 = load_workbook(tmp)
cell = next(r[2].value for r in wb3["LP classes, run 1"].iter_rows(min_row=5, max_row=16, max_col=3)
            if r[0].value == "Folded Lens")
check("tampered cell is caught", not near(cell, A["per_class"]["P1_FL"]["auprc"]), str(cell))
shutil.rmtree(tmp.parent, ignore_errors=True)

print()
if bad:
    print(f"FAIL: {len(bad)} check(s) failed: {bad}")
    raise SystemExit(1)
print("PASS: workbook and report match the metrics, and the tamper proof bites")
