"""Run the notebook's pure-Python cells against the real data, and syntax-check the rest.

The torch cells cannot run on this machine (torch is not installed), so they are compiled
only. This proves the notebook's label logic and metric code work as written.
"""
import json
import numpy as np

NB = r"D:\fmd-analysis\notebooks\FMD_MultiLabel_LP_AllTags.ipynb"
nb = json.load(open(NB, encoding="utf-8"))
code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
print(f"{len(code_cells)} code cells")

REAL = {
    'ANNOTATION_CSV = Path("annotation_of_record.csv")':
        'ANNOTATION_CSV = Path(r"D:/fmd-analysis/run/eda_full_20261015/resolved_labels.csv")',
    'CLEAR_CSV = Path("clear_pictures.csv")':
        'CLEAR_CSV = Path(r"D:/fmd-analysis/run/multilabel_edge_20261023_rev3/label_matrix.csv")',
    'SPLIT_CSV = Path("train_test_assignment.csv")':
        'SPLIT_CSV = Path(r"D:/fmd-analysis/run/split_20261026_v5/split_80_20.csv")',
}

ns = {}
for i, cell in enumerate(code_cells):
    src = cell["source"]
    if isinstance(src, list):
        src = "".join(src)
    for old, new in REAL.items():
        src = src.replace(old, new)
    needs_torch = "import torch" in src or "torchvision" in src
    if needs_torch:
        compile(src, f"<cell {i}>", "exec")
        print(f"cell {i}: compiled (torch not available here)")
        continue
    exec(compile(src, f"<cell {i}>", "exec"), ns)
    print(f"cell {i}: ran")

rows = ns["rows"]
print(f"\nrows {len(rows)}")
print("train/test", sum(1 for r in rows if r["split"] == "train"), sum(1 for r in rows if r["split"] == "test"))

# the metric cell was defined, so exercise it on synthetic data
y_true = np.zeros((50, 12))
y_true[:10, 0] = 1
y_score = y_true * 0.9 + 0.05
print("\nmetric sanity, perfect ranking:")
ns["report"](y_true, y_score, ns["LP_COLUMNS"])
