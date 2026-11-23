#!/usr/bin/env python3
"""Inventory a CVAT annotation export and compare its picture coverage with earlier exports.

Read-only. The only writes are the CSV/JSON evidence files under --out.

Counts are produced in three separate spaces, never mixed:

  mentions   one <tag> or <box> element
  pictures   one distinct image basename carrying at least one shape of that code
  images     one distinct <image> element, whether or not it carries a shape

Run:
    ./.venv/Scripts/python.exe experiments/annotations/frozen_inventory.py \
        --frozen "data/Frozen Annotation Dataset/Frozen Annotation Dataset" \
        --out run/frozen_eda_20261117
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

PROD = "data/PRODUCTION_20260925_300"
LEGACY = ["data/Updated Annotations 20260922.xml", "data/annotations.xml"]


def basename(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_export(path: Path) -> dict:
    """Parse one CVAT job export into flat records.

    The files are CVAT exports pulled from the client's own account, not
    attacker-supplied input, so the standard library parser is used on purpose
    (same stance as experiments/eda_full/resolve_labels.py).
    """
    tree = ET.parse(path)
    root = tree.getroot()
    meta = root.find("meta/job")
    job = {
        "file": path.name,
        "job_id": meta.findtext("id") if meta is not None else "",
        "size": meta.findtext("size") if meta is not None else "",
        "created": meta.findtext("created") if meta is not None else "",
        "updated": meta.findtext("updated") if meta is not None else "",
        "owner": (meta.findtext("owner/username") if meta is not None else "") or "",
    }
    images = []
    for img in root.findall("image"):
        name = img.get("name", "")
        shapes = []
        for tag in img.findall("tag"):
            shapes.append((tag.get("label", ""), "tag"))
        for box in img.findall("box"):
            shapes.append((box.get("label", ""), "box"))
        images.append({"name": name, "base": basename(name), "shapes": shapes})
    return {"job": job, "images": images, "sha256": sha256(path)}


def collect(paths: list[Path]) -> dict:
    files = []
    all_images: dict[str, list] = {}
    name_to_files: dict[str, set] = defaultdict(set)
    for p in paths:
        rec = parse_export(p)
        files.append(
            {
                **rec["job"],
                "sha256": rec["sha256"],
                "images": len(rec["images"]),
                "images_with_shape": sum(1 for i in rec["images"] if i["shapes"]),
                "tag_mentions": sum(1 for i in rec["images"] for s in i["shapes"] if s[1] == "tag"),
                "box_mentions": sum(1 for i in rec["images"] for s in i["shapes"] if s[1] == "box"),
            }
        )
        for img in rec["images"]:
            name_to_files[img["base"]].add(p.name)
            all_images.setdefault(img["base"], []).append((p.name, img["shapes"]))
    return {"files": files, "images": all_images, "name_to_files": name_to_files}


def label_table(images: dict) -> list[dict]:
    """Per code and shape kind: mentions and distinct pictures."""
    mentions = Counter()
    pics: dict[tuple[str, str], set] = defaultdict(set)
    for base, rows in images.items():
        for _f, shapes in rows:
            for code, kind in shapes:
                mentions[(code, kind)] += 1
                pics[(code, kind)].add(base)
    out = []
    for (code, kind), n in sorted(mentions.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append({"code": code, "shape_kind": kind, "mentions": n, "pictures": len(pics[(code, kind)])})
    return out


def per_file_labels(recs: list[dict]) -> list[dict]:
    rows = []
    for rec in recs:
        jid = rec["job"]["job_id"]
        c = Counter()
        p = defaultdict(set)
        for img in rec["images"]:
            for code, kind in img["shapes"]:
                c[(code, kind)] += 1
                p[(code, kind)].add(img["base"])
        for (code, kind), n in c.items():
            rows.append({"job_id": jid, "file": rec["job"]["file"], "code": code,
                         "shape_kind": kind, "mentions": n, "pictures": len(p[(code, kind)])})
    return rows


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = columns or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    out = (repo / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    frozen_dir = repo / args.frozen
    frozen_paths = sorted(frozen_dir.glob("annotations_*.xml"))

    prev_prod = sorted((repo / PROD).glob("annotations_*.xml"))
    prev_paths = prev_prod + [repo / p for p in LEGACY if (repo / p).exists()]

    frozen = collect(frozen_paths)
    prev = collect(prev_paths)

    # job-level overlap
    f_jobs = {int(f["job_id"]) for f in frozen["files"] if f["job_id"]}
    p_jobs = {int(f["job_id"]) for f in prev["files"] if f["job_id"]}

    f_names = set(frozen["images"])
    p_names = set(prev["images"])

    summary = {
        "frozen_files": len(frozen_paths),
        "prev_files": len(prev_paths),
        "frozen_jobs": len(f_jobs),
        "prev_jobs": len(p_jobs),
        "jobs_shared": len(f_jobs & p_jobs),
        "jobs_frozen_only": len(f_jobs - p_jobs),
        "jobs_prev_only": len(p_jobs - f_jobs),
        "frozen_images": len(f_names),
        "frozen_image_elements": sum(f["images"] for f in frozen["files"]),
        "frozen_images_with_shape": sum(1 for b, rows in frozen["images"].items()
                                        if any(sh for _f, sh in rows)),
        "prev_images": len(p_names),
        "pictures_in_both": len(f_names & p_names),
        "pictures_frozen_only": len(f_names - p_names),
        "pictures_prev_only": len(p_names - f_names),
        "basenames_mapping_to_two_files_within_frozen": sum(
            1 for b, fs in frozen["name_to_files"].items() if len(fs) > 1),
        "basenames_mapping_to_two_files_within_prev": sum(
            1 for b, fs in prev["name_to_files"].items() if len(fs) > 1),
        "frozen_total_tag_mentions": sum(f["tag_mentions"] for f in frozen["files"]),
        "frozen_total_box_mentions": sum(f["box_mentions"] for f in frozen["files"]),
        "frozen_job_ids": sorted(f_jobs),
    }

    write_csv(out / "frozen_files.csv", frozen["files"])
    write_csv(out / "prev_files.csv", prev["files"])
    write_csv(out / "frozen_labels.csv", label_table(frozen["images"]))
    write_csv(out / "prev_labels.csv", label_table(prev["images"]))
    write_csv(out / "frozen_labels_by_job.csv", per_file_labels(
        [parse_export(p) for p in frozen_paths]))

    only_prev = sorted(p_names - f_names)
    only_frozen = sorted(f_names - p_names)
    write_csv(out / "pictures_prev_only.csv", [{"basename": b} for b in only_prev])
    write_csv(out / "pictures_frozen_only.csv", [{"basename": b} for b in only_frozen])

    (out / "inventory.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("\nTop frozen labels (mentions):")
    for row in label_table(frozen["images"])[:40]:
        print(f"  {row['code']:<32} {row['shape_kind']:<4} {row['mentions']:>6}  on {row['pictures']:>5} pictures")
    print("\nPrev-only sample:", only_prev[:10])
    print("Frozen-only sample:", only_frozen[:10])


if __name__ == "__main__":
    main()
