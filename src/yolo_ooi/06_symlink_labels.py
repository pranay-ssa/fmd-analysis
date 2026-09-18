#!/usr/bin/env python3
"""Symlink each YOLO-OBB label into its image's parent dir (canonical
Ultralytics layout).  After this, Ultralytics can scan the dir and find
labels next to images without any path-list tricks.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels-dir", required=True, help="dir of <stem>.txt labels")
    ap.add_argument("--crop-base", required=True,
                    help="dir containing <Class>_<date>/<stem>_crop.bmp")
    ap.add_argument("--rel-list", required=True, nargs="+",
                    help="list files (train.txt/val.txt) of crop_relpaths to process")
    ap.add_argument("--suffix-mode", choices=["stem", "stem_crop"], default="stem_crop",
                    help="stem: <stem>.txt (matches <stem>_crop.bmp -> <stem>_crop.txt NOT <stem>.txt). "
                         "stem_crop: <stem>_crop.txt (matches Ultralytics' dir-scan convention)")
    args = ap.parse_args()

    crop_base = Path(args.crop_base)
    labels_dir = Path(args.labels_dir)

    stems = set()
    for lst in args.rel_list:
        for line in Path(lst).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            # line format: "<Class>_<date>/<stem>_crop.bmp"
            fname = Path(line).name
            stem = fname.rsplit("_crop.bmp", 1)[0]  # drop _crop.bmp suffix
            stems.add(stem)

    n_existing = 0
    n_created = 0
    n_missing = 0
    for stem in sorted(stems):
        for bmp in crop_base.rglob(f"{stem}_crop.bmp"):
            # The label name MUST match the image's filename with .bmp -> .txt
            # so Ultralytics' dir-scan can pair them.
            label_fname = f"{stem}_crop.txt"
            lbl = labels_dir / f"{stem}.txt"  # source-of-truth file
            if not lbl.exists():
                n_missing += 1
                continue
            target = bmp.parent / label_fname
            if target.exists() or target.is_symlink():
                n_existing += 1
                continue
            # relative path so the symlink survives moves
            rel = Path("../../../yolo_ooi/runs/yolo11/labels") / f"{stem}.txt"
            target.symlink_to(rel)
            n_created += 1

    print(f"stems seen       : {len(stems)}")
    print(f"symlinks created : {n_created}")
    print(f"already there    : {n_existing}")
    print(f"missing label    : {n_missing}")


if __name__ == "__main__":
    main()