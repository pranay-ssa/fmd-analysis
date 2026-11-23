#!/usr/bin/env python3
"""Decide the 198 earlier-annotation-only pictures by CONTENT, not by name.

A picture the frozen export does not name can still be present in the frozen set under
another file name (the library saved the same content under several names). This script
joins both sides on md5 from the on-disk inventory, so a name difference is not counted
as a missing picture.

Read-only. Writes run/frozen_eda_20261117/previous_only_by_content.csv and prints a summary.
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
PROD = REPO / "data/PRODUCTION_20260925_300"
LEGACY = [REPO / "data/Updated Annotations 20260922.xml", REPO / "data/annotations.xml"]
OUT = REPO / "run/frozen_eda_20261117"


def base(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def scan(path: Path) -> dict[str, list[str]]:
    root = ET.parse(path).getroot()
    out = {}
    for img in root.findall("image"):
        labels = [t.get("label", "") for t in img.findall("tag")]
        labels += [b.get("label", "") for b in img.findall("box")]
        out[base(img.get("name", ""))] = labels
    return out


def main():
    frozen = {}
    for p in sorted(FROZEN.glob("annotations_*.xml")):
        for b, labels in scan(p).items():
            frozen[b] = labels
    prev = {}
    prev_file = {}
    for p in sorted(PROD.glob("annotations_*.xml")) + [p for p in LEGACY if p.exists()]:
        for b, labels in scan(p).items():
            prev.setdefault(b, []).extend(labels)
            prev_file.setdefault(b, []).append(p.name)

    name_md5: dict[str, set[str]] = defaultdict(set)
    md5_names: dict[str, set[str]] = defaultdict(set)
    md5_path: dict[str, str] = {}
    with (REPO / "run/eda_full_20261029/file_manifest.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            b = base(row["path"])
            name_md5[b].add(row["md5"])
            md5_names[row["md5"]].add(b)
            md5_path.setdefault(row["md5"], row["path"])

    frozen_md5 = set()
    for b in frozen:
        frozen_md5 |= name_md5.get(b, set())

    rows = []
    for b in sorted(set(prev) - set(frozen)):
        md5s = name_md5.get(b, set())
        alias_of = set()
        for m in md5s:
            alias_of |= md5_names.get(m, set()) & set(frozen)
        rows.append({
            "basename": b,
            "prev_files": ";".join(sorted(set(prev_file[b]))),
            "prev_labels": ";".join(sorted(set(prev[b]))),
            "md5_known": ";".join(sorted(md5s)),
            "md5_present_in_frozen": "yes" if (md5s & frozen_md5) else "no",
            "frozen_name_for_same_content": ";".join(sorted(alias_of)),
            "manifest_path": md5_path.get(next(iter(md5s)), "") if md5s else "",
        })

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "previous_only_by_content.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    s = {
        "previous_only_by_name": len(rows),
        "same_content_present_in_frozen": sum(1 for r in rows if r["md5_present_in_frozen"] == "yes"),
        "genuinely_absent_from_frozen": sum(1 for r in rows if r["md5_present_in_frozen"] == "no"),
        "carrying_labels": sum(1 for r in rows if r["prev_labels"]),
        "genuinely_absent_and_labelled": sum(
            1 for r in rows if r["md5_present_in_frozen"] == "no" and r["prev_labels"]),
        "by_prev_file": dict(Counter(r["prev_files"] for r in rows)),
        "label_counts": dict(Counter(
            lab for r in rows if r["md5_present_in_frozen"] == "no"
            for lab in r["prev_labels"].split(";") if lab)),
    }
    (OUT / "previous_only_by_content.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    print(json.dumps(s, indent=1))
    print("\nrows genuinely absent (first 20):")
    for r in [r for r in rows if r["md5_present_in_frozen"] == "no"][:20]:
        print(" ", r["basename"], "|", r["prev_labels"], "|", r["manifest_path"][:90])


if __name__ == "__main__":
    main()
