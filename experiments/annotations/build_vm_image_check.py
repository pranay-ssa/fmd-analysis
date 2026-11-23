#!/usr/bin/env python3
"""Build a read-only VM check: are the frozen pictures already on the shared box?

Emits a script with the 13,682 frozen basenames compressed inside it, so nothing is written
on the VM. The script walks the data root, reports per-folder counts, and says how many frozen
names are present, missing, or present only under a different folder.

Run:
    ./.venv/Scripts/python.exe experiments/annotations/build_vm_image_check.py
    ssh amd-a100-vm 'python3 -' < run/frozen_eda_20261117/vm_image_check.py
"""

from __future__ import annotations

import base64
import gzip
import json
import os
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
OUT = REPO / "run/frozen_eda_20261117"

TEMPLATE = r'''#!/usr/bin/env python3
import base64, gzip, json, os
NAMES = json.loads(gzip.decompress(base64.b64decode("__NAMES__")).decode())
ROOT = "/data/FMD_Data_26082026"
IMG_EXTS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

by_base = {}
folders = Counter()
per_folder_base = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    keep = [f for f in filenames if os.path.splitext(f)[1].lower() in IMG_EXTS]
    if keep:
        rel = os.path.relpath(dirpath, ROOT)
        folders[rel] = len(keep)
        s = per_folder_base.setdefault(rel, set())
        for f in keep:
            s.add(f)
            by_base.setdefault(f, set()).add(rel)

frozen = set(NAMES["frozen"])
old = set(NAMES["old"])
new = set(NAMES["new"])

def report(label, names):
    present = {n for n in names if n in by_base}
    missing = sorted(names - present)
    where = Counter()
    multi = 0
    for n in present:
        locs = by_base[n]
        if len(locs) > 1:
            multi += 1
        top = sorted(locs)[0].split(os.sep)[0]
        where[top] += 1
    return {"label": label, "names": len(names), "present": len(present),
            "missing": len(missing), "missing_sample": missing[:15],
            "present_in_more_than_one_folder": multi,
            "top_folder_of_first_copy": dict(where)}

print(json.dumps({
    "root": ROOT,
    "image_files_found": sum(folders.values()),
    "unique_basenames": len(by_base),
    "folders_with_images": dict(sorted(folders.items(), key=lambda kv: -kv[1])[:25]),
    "frozen": report("frozen", frozen),
    "old_batch": report("old", old),
    "new_batch": report("new", new),
    "has_PRODCUTION_20261031": any("PRODUCTION-20261031" in k or "PRODUCTION_20261031" in k
                                     for k in folders),
}, indent=1))
'''


def main() -> None:
    names = {"frozen": set(), "old": set(), "new": set()}
    for p in sorted(FROZEN.glob("annotations_*.xml")):
        root = ET.parse(p).getroot()
        for el in root.findall("image"):
            name = el.get("name", "")
            b = name.rsplit("/", 1)[-1]
            folder = name.split("/")[1] if "/" in name else ""
            names["frozen"].add(b)
            names["old" if folder.startswith("PRODUCTION-20260925") else "new"].add(b)
    payload = {k: sorted(v) for k, v in names.items()}
    blob = base64.b64encode(gzip.compress(json.dumps(payload).encode())).decode()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "vm_image_check.py").write_text(TEMPLATE.replace("__NAMES__", blob), encoding="utf-8")
    print({k: len(v) for k, v in payload.items()}, "script bytes", len(blob))


if __name__ == "__main__":
    main()
