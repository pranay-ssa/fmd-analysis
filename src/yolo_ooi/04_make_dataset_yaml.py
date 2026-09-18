"""Step 4: Write dataset.yaml for the OoI YOLO-OBB runs.

Follows the yolo-detection-pipeline rule: OMIT the `path:` key entirely.
`train:` / `val:` point at the .txt path-list files.  Ultralytics then resolves
image paths relative to this yaml's own directory.

Note: because train/val are .txt files listing RELATIVE image paths, this yaml
must live in (or be run with cwd at) the directory that contains the crop dirs.
On the VM we set that to the single-size crop base.  Certified by
check_det_dataset before training.

Usage:
    python src/yolo_ooi/04_make_dataset_yaml.py --classes-file runs/yolo11/classes.txt \
        --train-txt runs/yolo11/train.txt --val-txt runs/yolo11/val.txt \
        --out runs/yolo11/dataset.yaml
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes-file", required=True, help="one class per line, 0-based order")
    ap.add_argument("--train-txt", required=True)
    ap.add_argument("--val-txt", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    classes = []
    for line in Path(args.classes_file).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and line not in classes:
            classes.append(line)

    lines = ["# YOLO-OBB dataset for OoI architecture experiments",
             "# Created by src/yolo_ooi/04_make_dataset_yaml.py",
             "# NOTE: no `path:` key (portable across local + VM).",
             "# NOTE: train/val are bare txt names (they sit BESIDE this yaml);",
             "#       Ultralytics resolves them relative to this yaml's own dir.",
             f"train: {Path(args.train_txt).name}",
             f"val: {Path(args.val_txt).name}",
             f"nc: {len(classes)}",
             "names:"]
    for i, c in enumerate(classes):
        lines.append(f"  {i}: {c}")
    txt = "\n".join(lines) + "\n"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(txt, encoding="utf-8")
    print(f"nc     : {len(classes)}")
    print(f"classes: {classes}")
    print(f"Wrote  : {out}")


if __name__ == "__main__":
    main()