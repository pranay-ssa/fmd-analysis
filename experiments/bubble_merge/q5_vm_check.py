#!/usr/bin/env python3
"""Q5, VM side: did any previous split follow the '178 Folded Lens deducted
from Multiple Lenses' rule?

Read-only. For every previous split on the VM:
  * is Folded Lens a class anywhere?
  * how many rows does Multiple Lenses have, and is that number 178 below its
    tag-presence figure (1442 in the audit, 1439 in the frozen pool)?
A deduction would show 1264 / 1261 / 1258.
"""
import csv
import glob
import os

SPLITS = [
    "/home/pranayp/combined_dataset_single_20260908/split.csv",
    "/home/pranayp/lens_presentation_dataset_20260903/split.csv",
    "/home/pranayp/lens_presentation_dataset_single_20260903/split.csv",
    "/home/pranayp/OoI_dataset_single/split.csv",
    "/home/pranayp/yolo_ooi/run/yolo_ooi/split.csv",
    "/home/pranayp/line_experiment_20260917/subset6/_smoke_L25/split.csv",
    "/home/pranayp/line_experiment_20260917/splits/line_L24/split.csv",
    "/home/pranayp/line_experiment_20260917/splits/line_L25/split.csv",
    "/home/pranayp/line_experiment_20260917/splits/line_L26/split.csv",
    "/home/pranayp/line_experiment_20260917/splits/line_L27/split.csv",
    "/home/pranayp/line_experiment_20260917/splits/line_L31/split.csv",
]
DATASET_ROOTS = [
    "/home/pranayp/combined_dataset_single_20260908",
    "/home/pranayp/lens_presentation_dataset_20260903",
    "/home/pranayp/lens_presentation_dataset_single_20260903",
    "/home/pranayp/OoI_dataset_single",
]

print("=== previous splits ===")
grand_ml = 0
for path in SPLITS:
    if not os.path.exists(path):
        print("MISSING", path)
        continue
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("%-70s empty" % path)
        continue
    cols = list(rows[0].keys())
    cls_col = None
    for c in ("class", "label", "cls", "name", "category"):
        if c in cols:
            cls_col = c
            break
    if cls_col is None:          # yolo split: class may sit elsewhere
        cls_col = cols[1] if len(cols) > 1 else cols[0]
    counts = {}
    for r in rows:
        v = (r.get(cls_col) or "").strip()
        counts[v] = counts.get(v, 0) + 1
    fl = [k for k in counts if "fold" in k.lower()]
    ml = sum(v for k, v in counts.items()
             if k in ("Multiple Lenses", "Multiple Lens"))
    is_pool = "line_experiment_20260917/splits" in path
    if is_pool:
        grand_ml += ml
    flag = ""
    if fl:
        flag = "  <-- FOLDED LENS CLASS: %s" % fl
    ded = "  <-- DEDUCTED?" if ml in (1264, 1261, 1258, 1257, 1255) else ""
    print("%-70s rows=%-6d classes=%-3d cols=%-22s ML=%-5d%s%s"
          % (os.path.relpath(path, "/home/pranayp"), len(rows), len(counts),
             cls_col, ml, flag, ded))
    if len(counts) <= 30 and is_pool is False:
        print("      classes: %s" % sorted(counts))

print("\npooled line-split Multiple Lenses rows (5 lines): %d "
      "(undeducted pool would be 1436-1439; a 178 deduction would be "
      "1258-1261)" % grand_ml)

print("\n=== dataset roots: class directories ===")
for root in DATASET_ROOTS:
    if not os.path.isdir(root):
        print("MISSING", root)
        continue
    for split in ("train", "test"):
        d = os.path.join(root, split)
        if not os.path.isdir(d):
            continue
        classes = sorted(os.listdir(d))
        fl_dirs = [c for c in classes if "fold" in c.lower()]
        ml_n = 0
        ml_dir = os.path.join(d, "Multiple Lenses")
        if os.path.isdir(ml_dir):
            ml_n = len(os.listdir(ml_dir))
        print("%-62s %-5s classes=%-3d ML=%-5d fold_dirs=%s"
              % (os.path.relpath(root, "/home/pranayp"), split,
                 len(classes), ml_n, fl_dirs or "none"))

print("\n=== image root: any Folded Lens folder in any library? ===")
hits = []
for pat in ("/data/FMD_Data_26082026/fmd_temp_images/*/Folded*",
            "/data/FMD_Data_26082026/fmd_temp_images/*/*/Folded*",
            "/home/pranayp/*/Folded*"):
    hits += glob.glob(pat)
print(hits or "none found")

print("\nQ5_VM_CHECK_DONE")
