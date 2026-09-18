"""Step 3: Stratified train/val split as CSV path lists (no image copies).

Reads ooi_images.csv, stratifies by class, writes:
  - runs/yolo11/train.txt   (one image path per line)
  - runs/yolo11/val.txt     (one image path per line)
  - runs/yolo11/split.csv   (image -> split label, for reproducibility)

The .txt lines are RELATIVE image paths (the crop_relpath column), so they are
portable.  Ultralytics resolves them relative to the dataset.yaml location when
no `path:` key is present (per yolo-detection-pipeline skill: OMIT path:).

Usage:
    python src/yolo_ooi/03_split_csv.py --images runs/yolo11/ooi_images.csv \
        --out-dir run/yolo_ooi --val-frac 0.20 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="ooi_images.csv from step 1")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--val-frac", type=float, default=0.20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(args.images, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # drop rows with no crop (they can't be used for training)
    useable = [r for r in rows if r["crop_relpath"]]
    by_class = {}
    for r in useable:
        by_class.setdefault(r["class"], []).append(r)

    train_lines, val_lines, split_rows = [], [], []
    for cls, members in sorted(by_class.items()):
        n_val = max(1, round(len(members) * args.val_frac))
        rng.shuffle(members)
        val = members[:n_val]
        tr = members[n_val:]
        for r in val:
            val_lines.append(r["crop_relpath"])
            split_rows.append({"class": r["class"], "stem": r["stem"],
                               "crop_relpath": r["crop_relpath"], "split": "val"})
        for r in tr:
            train_lines.append(r["crop_relpath"])
            split_rows.append({"class": r["class"], "stem": r["stem"],
                               "crop_relpath": r["crop_relpath"], "split": "train"})

    (out / "train.txt").write_text("\n".join(sorted(train_lines)) + "\n", encoding="utf-8")
    (out / "val.txt").write_text("\n".join(sorted(val_lines)) + "\n", encoding="utf-8")
    with open(out / "split.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["class", "stem", "crop_relpath", "split"])
        w.writeheader()
        w.writerows(split_rows)

    # per-class train/val tally
    print(f"Useable images         : {len(useable)}  (dropped with no crop: {len(rows)-len(useable)})")
    print(f"train                  : {len(train_lines)}")
    print(f"val                    : {len(val_lines)}")
    print(f"val fraction (overall) : {len(val_lines)/max(len(useable),1):.2%}")
    print("Per-class split:")
    for cls, members in sorted(by_class.items()):
        nv = sum(1 for r in split_rows if r["class"] == cls and r["split"] == "val")
        nt = len(members) - nv
        print(f"  {cls:28s} train={nt:4d} val={nv:3d} total={len(members)}")
    print(f"Wrote train.txt / val.txt / split.csv under {out}")


if __name__ == "__main__":
    main()