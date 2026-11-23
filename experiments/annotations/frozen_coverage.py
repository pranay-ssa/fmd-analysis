#!/usr/bin/env python3
"""Join the frozen export to the earlier annotation record and to the picture inventory.

Answers four questions, each in its own section, with the population named:

  1. coverage   how many frozen images the earlier annotation already covered
  2. additions  pictures in the earlier annotation that the frozen export does not mention
  3. knownness  frozen image names against the on-disk picture inventory
  4. empties    frozen images that carry no shape

Read-only. Writes CSV/JSON under --out.
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


def scan(path: Path) -> dict:
    root = ET.parse(path).getroot()
    meta = root.find("meta/job")
    jid = meta.findtext("id") if meta is not None else ""
    rec = {"file": path.name, "job_id": jid, "images": {}}
    for img in root.findall("image"):
        name = img.get("name", "")
        labels = [t.get("label", "") for t in img.findall("tag")]
        labels += [b.get("label", "") for b in img.findall("box")]
        rec["images"][base(name)] = {"name": name, "labels": labels}
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = [scan(p) for p in sorted(FROZEN.glob("annotations_*.xml"))]
    prev = [scan(p) for p in sorted(PROD.glob("annotations_*.xml"))]
    prev += [scan(p) for p in LEGACY if p.exists()]

    # group by source folder in the image name
    frozen_names = {}
    for rec in frozen:
        for b, info in rec["images"].items():
            folder = info["name"].split("/")[1] if "/" in info["name"] else ""
            frozen_names[b] = {"folder": folder, "labels": info["labels"],
                               "job": rec["job_id"]}

    prev_names = {}
    for rec in prev:
        for b, info in rec["images"].items():
            prev_names.setdefault(b, {"labels": [], "files": []})
            prev_names[b]["labels"].extend(info["labels"])
            prev_names[b]["files"].append(rec["file"])

    # on-disk inventory
    manifest_names = set()
    manifest_md5_of = {}
    with (REPO / "run/eda_full_20261029/file_manifest.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            b = base(row["path"])
            manifest_names.add(b)
            manifest_md5_of.setdefault(b, set()).add(row["md5"])

    table_names = set()
    with (REPO / "run/eda_full_20261029/picture_table.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table_names.add(base(row["winning_path"]))

    fset, pset = set(frozen_names), set(prev_names)
    both = fset & pset
    only_f = fset - pset
    only_p = pset - fset

    folder_counts = Counter(v["folder"] for v in frozen_names.values())
    only_f_folders = Counter(frozen_names[b]["folder"] for b in only_f)

    # duplicates: a frozen picture already covered by the earlier annotation
    dup_rows = [{"basename": b,
                 "frozen_folder": frozen_names[b]["folder"],
                 "frozen_job": frozen_names[b]["job"],
                 "prev_files": ";".join(sorted(set(prev_names[b]["files"]))),
                 "frozen_labels": ";".join(sorted(set(frozen_names[b]["labels"]))),
                 "prev_labels": ";".join(sorted(set(prev_names[b]["labels"])))}
                for b in sorted(both)]
    dup_rows_same = sum(1 for r in dup_rows if r["frozen_labels"] == r["prev_labels"])

    add_rows = [{"basename": b,
                 "prev_files": ";".join(sorted(set(prev_names[b]["files"]))),
                 "prev_labels": ";".join(sorted(set(prev_names[b]["labels"]))),
                 "in_manifest": b in manifest_names,
                 "in_picture_table": b in table_names}
                for b in sorted(only_p)]

    empty_rows = [{"basename": b, "job": frozen_names[b]["job"],
                   "folder": frozen_names[b]["folder"]}
                  for b in sorted(frozen_names) if not frozen_names[b]["labels"]]

    known = Counter()
    for b, v in frozen_names.items():
        if v["folder"] == "PRODUCTION-20260925":
            known["old_in_manifest" if b in manifest_names else "old_not_in_manifest"] += 1
        else:
            known["new_in_manifest" if b in manifest_names else "new_not_in_manifest"] += 1

    summary = {
        "frozen_pictures": len(fset),
        "frozen_pictures_by_source_folder": dict(folder_counts),
        "frozen_only_pictures": len(only_f),
        "frozen_only_pictures_by_source_folder": dict(only_f_folders),
        "duplicate_pictures_covered_before": len(both),
        "duplicates_with_identical_label_set": dup_rows_same,
        "duplicates_with_changed_label_set": len(both) - dup_rows_same,
        "previous_only_pictures": len(only_p),
        "previous_only_by_source_file": dict(Counter(
            r["prev_files"] for r in add_rows)),
        "previous_only_in_manifest": sum(1 for r in add_rows if r["in_manifest"]),
        "previous_only_in_picture_table": sum(1 for r in add_rows if r["in_picture_table"]),
        "previous_pictures": len(pset),
        "frozen_empty_images": len(empty_rows),
        "knownness": dict(known),
    }

    def dump(name, rows):
        if not rows:
            (OUT / name).write_text("", encoding="utf-8")
            return
        with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    dump("duplicates_vs_previous.csv", dup_rows)
    dump("pictures_previous_only.csv", add_rows)
    dump("frozen_empty_images.csv", empty_rows)
    (OUT / "coverage.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
