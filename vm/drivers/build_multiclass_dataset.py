#!/usr/bin/env python3
"""Build multiclass detection dataset from OBB labels (AABB conversion, 10 classes)."""
from pathlib import Path

SRC = Path("/home/pranayp/yolo_ooi/dataset_obb")
DST = Path("/home/pranayp/yolo_ooi/dataset_multiclass")

# Class names (from the OBB dataset, 10 defect types)
CLASS_NAMES = [
    "Bubble Cluster", "Bubble", "Bubble On 123", "Bubble Irregular",
    "Bubble On Edge", "Extraneous Polymer", "Fiber", "Foreign Matter",
    "HEMA Fragment", "Wet Package"
]

def obb_to_aabb(x1,y1,x2,y2,x3,y3,x4,y4):
    xs = [x1,x2,x3,x4]; ys = [y1,y2,y3,y4]
    xmin,xmax = min(xs),max(xs); ymin,ymax = min(ys),max(ys)
    cx = (xmin+xmax)/2; cy = (ymin+ymax)/2
    w = xmax-xmin; h = ymax-ymin
    return cx,cy,w,h

def convert_labels():
    for split in ("train","val"):
        outdir = DST / "labels" / split
        outdir.mkdir(parents=True, exist_ok=True)
        srcdir = SRC / "labels" / split
        n_files = n_boxes = n_classes = 0
        classes_seen = set()
        for lbl in sorted(srcdir.glob("*.txt")):
            lines = []
            for line in lbl.read_text().splitlines():
                parts = line.split()
                if len(parts) != 9: continue
                cls = int(parts[0])
                coords = [float(x) for x in parts[1:]]
                cx,cy,w,h = obb_to_aabb(*coords)
                cx,cy,w,h = max(0,min(1,cx)),max(0,min(1,cy)),max(0,min(1,w)),max(0,min(1,h))
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                classes_seen.add(cls)
            if lines:
                (outdir / lbl.name).write_text("\n".join(lines)+"\n")
                n_files += 1
                n_boxes += len(lines)
        print(f"{split}: {n_files} files, {n_boxes} boxes, classes seen: {sorted(classes_seen)}")

def write_yaml():
    names_str = "\n".join(f"  {i}: {n}" for i,n in enumerate(CLASS_NAMES))
    (DST / "data.yaml").write_text(
        f"path: {DST}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: {len(CLASS_NAMES)}\n"
        f"names:\n{names_str}\n"
    )
    print(f"Wrote data.yaml with {len(CLASS_NAMES)} classes")

if __name__ == "__main__":
    # Symlink images (reuse from dataset_obb)
    for split in ("train","val"):
        dest = DST / "images" / split
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() or dest.is_symlink(): dest.unlink()
        dest.symlink_to(SRC / "images" / split, target_is_directory=True)
    print("Symlinked images")
    convert_labels()
    write_yaml()
    print("Done ->", DST)
