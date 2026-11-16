"""Check that every image in an Experiment 3.1 table resolves on the VM.

Reads the BMP header for the dimensions instead of decoding the picture, so 7,555 rows cost
seconds rather than a full disk read.

    python3.12 vm/ops/check_exp3_1_images.py \
        --table run/split_exp3_1_20261116/labels.csv \
        --image-root /data/FMD_Data_26082026/fmd_temp_images \
        --out run/split_exp3_1_20261116/stage_check.json
"""

from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path


def bmp_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        head = f.read(26)
    if len(head) < 26 or head[:2] != b"BM":
        raise ValueError("not a BMP")
    width, height = struct.unpack("<ii", head[18:26])
    return abs(width), abs(height)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--image-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", default="2448x2048")
    args = ap.parse_args()
    ew, eh = (int(v) for v in args.expect.split("x"))

    root = Path(args.image_root)
    rows = list(csv.DictReader(Path(args.table).open(newline="", encoding="utf-8")))
    missing, wrong_size, bad = [], [], []
    for r in rows:
        p = root / r["image_path"]
        try:
            if not p.is_file():
                missing.append(r["image_path"])
                continue
            if p.stat().st_size == 0:
                bad.append(r["image_path"])
                continue
            w, h = bmp_size(p)
            if (w, h) != (ew, eh):
                wrong_size.append({"path": r["image_path"], "size": f"{w}x{h}"})
        except Exception as exc:  # noqa: BLE001
            bad.append({"path": r["image_path"], "error": str(exc)})

    result = {
        "rows_checked": len(rows),
        "rows_ok": len(rows) - len(missing) - len(wrong_size) - len(bad),
        "missing": len(missing),
        "wrong_size": len(wrong_size),
        "unreadable": len(bad),
        "first_missing": missing[:20],
        "first_wrong_size": wrong_size[:20],
        "first_unreadable": bad[:20],
        "image_root": args.image_root,
        "expect": args.expect,
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not (missing or wrong_size or bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
