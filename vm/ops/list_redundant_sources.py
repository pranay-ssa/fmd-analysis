#!/usr/bin/env python3
"""List every file outside the store whose content is already in the store.

A file is reported as redundant when its md5 equals the md5 of the store picture with the same
basename. A same-name file with different content is reported separately, because deleting it
would lose a picture that the annotation does not cover.

Reads only. Writes one CSV and one JSON beside the store.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/data/FMD_Data_26082026")
STORE = ROOT / "frozen_data_20261117"
IMAGES = STORE / "images"
IMG_EXTS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    (STORE / "audit").mkdir(parents=True, exist_ok=True)
    manifest = {}
    with (STORE / "manifest.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            manifest[row["basename"]] = row["picture_key"]

    rows = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        here = Path(dirpath)
        if here.resolve() == STORE.resolve():
            dirnames[:] = []
            continue
        for name in filenames:
            if Path(name).suffix.lower() not in IMG_EXTS:
                continue
            path = here / name
            want = manifest.get(name)
            if want is None:
                continue  # not a frozen picture, out of scope for this list
            st = path.stat()
            got = md5_file(path)
            if got == want:
                status = "redundant_content_in_store"
            else:
                status = "same_name_different_content"
            rows.append({
                "path": str(path),
                "basename": name,
                "bytes": st.st_size,
                "md5": got,
                "store_md5": want,
                "status": status,
                "top_folder": str(path.relative_to(ROOT)).split(os.sep)[0],
            })

    rows.sort(key=lambda r: (r["status"], r["top_folder"], r["path"]))
    out = STORE / "audit" / "redundant_sources.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    by_status = Counter(r["status"] for r in rows)
    by_folder = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["status"] == "redundant_content_in_store":
            by_folder[r["top_folder"]][0] += 1
            by_folder[r["top_folder"]][1] += r["bytes"]
    summary = {
        "rows": len(rows),
        "by_status": dict(by_status),
        "redundant_files": by_status.get("redundant_content_in_store", 0),
        "redundant_bytes": sum(r["bytes"] for r in rows
                               if r["status"] == "redundant_content_in_store"),
        "redundant_by_folder": {k: {"files": v[0], "bytes": v[1]}
                                for k, v in sorted(by_folder.items(),
                                                   key=lambda kv: -kv[1][1])},
        "store_distinct_pictures": len({r["picture_key"] for r in
                                        csv.DictReader((STORE / "manifest.csv").open(encoding="utf-8"))}),
    }
    (STORE / "audit" / "redundant_sources.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
