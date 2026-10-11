#!/usr/bin/env python3
"""
Build a combined manifest for ALL single-size crops (one CSV per root +
one master CSV) from the per-class manifests. Read-only over per-class data.

Run as amd100-user on the A100 box:
  python3 build_combined_manifest.py
Writes into the crops/single_size/ top level:
  manifest_categorical.csv / manifest_objects.csv / manifest_old_library.csv
  manifest_ALL.csv
  (root column + source_root column added for unambiguous joins)
"""

import csv
import os

BASE = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images/crops/single_size"
ROOTS = [
    ("Updated ICube Categorical Classes 20260915_crop", "categorical"),
    ("Updated ICube Objects 20260915_crop", "objects"),
    ("ICube Defects Library_crop", "old_library"),
]

# per-class manifest columns, in order
SRC_COLS = ["file", "class", "status", "recovered_tier", "canonical",
            "width", "height", "left", "top", "right", "bottom",
            "orig_width", "orig_height"]
OUT_COLS = ["source_root", "class", "file", "status", "recovered_tier",
            "canonical", "width", "height", "left", "top", "right", "bottom",
            "orig_width", "orig_height", "crop_file", "crop_relpath"]


def main():
    master = []
    for root_dir, short in ROOTS:
        root_path = os.path.join(BASE, root_dir)
        if not os.path.isdir(root_path):
            print(f"skip missing root: {root_dir}")
            continue
        rows_root = []
        for entry in sorted(os.listdir(root_path)):
            cls_dir = os.path.join(root_path, entry)
            mf = os.path.join(cls_dir, "manifest.csv")
            if not (os.path.isdir(cls_dir) and os.path.isfile(mf)):
                continue
            with open(mf, newline="") as f:
                for r in csv.DictReader(f):
                    out = {"source_root": short, "class": r.get("class", ""),
                           "crop_file": r["file"][:-4] + "_crop.bmp",
                           "crop_relpath": os.path.join(root_dir, entry,
                                                        r["file"][:-4] + "_crop.bmp")}
                    for c in SRC_COLS:
                        out[c] = r.get(c, "")
                    rows_root.append(out)
        # per-root csv
        out_path = os.path.join(BASE, f"manifest_{short}.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows_root)
        print(f"{out_path}: {len(rows_root)} rows")
        master.extend(rows_root)

    out_path = os.path.join(BASE, "manifest_ALL.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(master)
    print(f"{out_path}: {len(master)} rows")

    # integrity: row count must equal crop count on disk
    n_bmp = 0
    for root_dir, _ in ROOTS:
        rp = os.path.join(BASE, root_dir)
        if not os.path.isdir(rp):
            continue
        for entry in os.listdir(rp):
            d = os.path.join(rp, entry)
            if os.path.isdir(d):
                n_bmp += sum(1 for x in os.listdir(d) if x.endswith("_crop.bmp"))
    ok = n_bmp == len(master)
    print(f"crops on disk: {n_bmp} vs manifest rows: {len(master)} -> "
          f"{'OK' if ok else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
