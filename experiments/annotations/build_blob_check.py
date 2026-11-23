#!/usr/bin/env python3
"""Build a read-only verification script for the VM: does the blob match the frozen export?

Three checks, all read-only against the storage account:

  1. every frozen image name exists in its declared image prefix, and list the extras
  2. the local annotation XMLs are byte-identical to the blob copies
  3. the extra image prefixes on the blob that no frozen annotation references

The frozen name lists are compressed into the emitted script, so nothing is written on
the VM and no second file has to be pushed.

Run:
    ./.venv/Scripts/python.exe experiments/annotations/build_blob_check.py
    ssh amd-a100-vm 'python3 -' < run/frozen_eda_20261117/blob_check.py
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
OUT = REPO / "run/frozen_eda_20261117"

TEMPLATE = r'''#!/usr/bin/env python3
"""Read-only blob verification for the frozen annotation export."""
import base64, gzip, hashlib, json, os
from collections import Counter
from azure.storage.blob import BlobServiceClient

NAMES = json.loads(gzip.decompress(base64.b64decode("__NAMES__")).decode())
XML = json.loads(gzip.decompress(base64.b64decode("__XML__")).decode())

conn = open(os.path.expanduser("~/armor_blob_conn")).read().strip()
if "AccountName=" not in conn:
    conn = ("DefaultEndpointsProtocol=https;AccountName=stjnjmakearmor;AccountKey=%s;"
            "EndpointSuffix=core.windows.net" % conn)
svc = BlobServiceClient.from_connection_string(conn)

img = svc.get_container_client("fmd-cvat-images")
report = {"prefixes": {}, "annotations": {}}

for prefix, expected in NAMES.items():
    expected = set(expected)
    actual = set()
    sizes = {}
    for b in img.list_blobs(name_starts_with=prefix):
        name = b.name.rsplit("/", 1)[-1]
        actual.add(name)
        sizes[name] = b.size
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    report["prefixes"][prefix] = {
        "expected": len(expected), "blob": len(actual),
        "missing_from_blob": len(missing), "extra_in_blob": len(extra),
        "missing_sample": missing[:15], "extra_sample": extra[:15],
        "extra_by_month": dict(sorted(Counter(n[:6] for n in extra).items())),
    }

ann = svc.get_container_client("fmd-cvat-annotations")
props = {}
for b in ann.list_blobs(name_starts_with="Frozen Annotation Dataset/"):
    props[b.name.rsplit("/", 1)[-1]] = b.size
mismatch = []
for name, (size, digest) in XML.items():
    if name not in props:
        mismatch.append([name, "absent_from_blob"])
        continue
    blob = ann.download_blob("Frozen Annotation Dataset/" + name).readall()
    if len(blob) != size or hashlib.sha256(blob).hexdigest() != digest:
        mismatch.append([name, "content_differs", size, len(blob)])
report["annotations"] = {
    "local_files": len(XML), "blob_files": len(props),
    "blob_only": sorted(set(props) - set(XML))[:15],
    "local_only": sorted(set(XML) - set(props))[:15],
    "content_mismatch_count": len(mismatch),
    "content_mismatch_sample": mismatch[:15],
}
print(json.dumps(report, indent=1))
'''


def main():
    names = {}
    for p in sorted(FROZEN.glob("annotations_*.xml")):
        root = ET.parse(p).getroot()
        for el in root.findall("image"):
            name = el.get("name", "")
            prefix = "/".join(name.split("/")[:2]) + "/"
            names.setdefault(prefix, []).append(name.rsplit("/", 1)[-1])
    names = {k: sorted(v) for k, v in names.items()}

    xml = {}
    for p in sorted(FROZEN.glob("*")):
        if p.suffix.lower() in {".xml", ".csv", ".xlsx", ".ipynb"}:
            xml[p.name] = [p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()]

    blob_names = base64.b64encode(gzip.compress(json.dumps(names).encode())).decode()
    blob_xml = base64.b64encode(gzip.compress(json.dumps(xml).encode())).decode()
    script = TEMPLATE.replace("__NAMES__", blob_names).replace("__XML__", blob_xml)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blob_check.py").write_text(script, encoding="utf-8")
    print("prefixes:", {k: len(v) for k, v in names.items()})
    print("files fingerprinted:", len(xml))
    print("script bytes:", len(script))


if __name__ == "__main__":
    main()
