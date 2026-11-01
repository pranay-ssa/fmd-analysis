"""Diff the current workbook against the builder spec (read-only)."""
import json, sys
from openpyxl import load_workbook

SPEC = "D:/fmd-analysis/reports/draft2_eda_20261023/EDA_Draft2_20261026_spec.json"
WB = sys.argv[1] if len(sys.argv) > 1 else "D:/fmd-analysis/reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx"

spec = json.load(open(SPEC, encoding="utf-8"))
wb = load_workbook(WB, data_only=True)


def val(c):
    return c["value"] if isinstance(c, dict) else c


for sh in spec:
    ws = wb[sh["name"]]
    want = [[val(c) for c in row] for row in sh["rows"]]
    got = [list(r) for r in ws.iter_rows(min_col=1, max_col=8, values_only=True)]
    while got and all(v is None for v in got[-1]):
        got.pop()
    if len(want) != len(got):
        print(f"{sh['name']}: rows {len(want)} -> {len(got)}")
    for i, (a, b) in enumerate(zip(want, got), 1):
        a = [None if v == "" else v for v in a]
        b = b[:max(len(a), 8)]
        diffs = [(j + 1, x, y) for j, (x, y) in enumerate(zip(a, b)) if x != y and not (x is None and y is None)]
        if diffs:
            print(f"  {sh['name']} row {i}: " +
                  str([(j, str(x)[:45], str(y)[:45]) for j, x, y in diffs[:4]]))
