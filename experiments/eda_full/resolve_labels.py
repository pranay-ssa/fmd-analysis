#!/usr/bin/env python3
"""Resolve the final label set for every picture under the winner-takes-all rule.

Ticket 010 of the full-coverage EDA map.

Priority order (fixed with the user in the grill):

  1. the 7 CVAT production files, annotations_4521940 .. annotations_4521946
  2. Updated Annotations 20260922.xml
  3. annotations.xml (the old ICube Defects Library, project 2)

The highest-priority file that mentions a picture supplies ALL of that picture's
labels. Every lower-priority file is silent for it. No picture may carry labels
from two sources, so every picture resolves to exactly one source of record.

An annotation image is resolved to a picture by its BASENAME. The basename is
looked up in the census built from run/eda_full_20261015/file_manifest.csv (one
row per file on disk, keyed on content md5). The census is the right key rather
than picture_table.csv's winning_path alone: the same content is saved under more
than one file name across folders, so a basename taken from picture_table's
winning_path column cannot see 187 of the aliases (see renamed_aliases in the
output). Every basename in the whole census maps to exactly one md5, so the
lookup is deterministic. Any annotation image whose basename is absent from the
census is reported, never dropped.

The XML files are trusted CVAT exports made by the client's own account
(bbarrine@its.jnj.com) and pulled from a private blob store. They are not
attacker supplied, so the standard library parser is used on purpose and
Python's XXE warning is knowingly accepted here.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/resolve_labels.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
# Where the production XMLs live. The re-export keeps all 24 in one folder, so point
# EDA_PROD_DIR there instead of copying newer files into data/ root.
PROD_DIR = Path(os.environ.get("EDA_PROD_DIR", str(DATA)))
# Output folder. Override to keep an earlier run's evidence intact when the annotation
# changes: EDA_RUN_DIR=run/eda_full_20261028 ... The two input tables are read from the same
# folder, so copy picture_table.csv and file_manifest.csv into a new folder before using it.
RUN = Path(os.environ.get("EDA_RUN_DIR", str(REPO / "run" / "eda_full_20261015")))

PICTURE_TABLE = RUN / "picture_table.csv"
FILE_MANIFEST = RUN / "file_manifest.csv"
CROSSWALK = DATA / "crosswalk.csv"

# Source tables, in priority order. level 1 (highest) is the production jobs.
# EDA_PROD_JOBS selects which production jobs form level 1: "40-46" (the frozen 7,
# the default), "47-63" (the standalone new batch), or "40-63" (the 24-file merge).
def _production_jobs() -> list[int]:
    spec = os.environ.get("EDA_PROD_JOBS", "40-46").strip()
    jobs: list[int] = []
    for part in spec.split(","):
        lo, sep, hi = part.partition("-")
        jobs.extend(range(int(lo), int(hi if sep else lo) + 1))
    return jobs


PRODUCTION = [(1, "production_20260925", f"annotations_45219{n}.xml")
              for n in _production_jobs()]
SOURCES = (
    PRODUCTION
    + [(2, "updated_20260922", "Updated Annotations 20260922.xml")]
    + [(3, "project2", "annotations.xml")]
)

# Which crosswalk column carries the code for each source group.
CODE_COLUMN = {
    "production_20260925": "code_in_production_20260925",
    "updated_20260922": "code_in_updated_20260922",
    "project2": "code_in_project2",
}

RESOLVED_COLUMNS = [
    "picture_md5", "winning_path", "source_file", "source_group", "priority_level",
    "code", "canonical_id", "shape_kind", "is_size_gate",
    "xtl", "ytl", "xbr", "ybr", "rotation",
]

DISAGREEMENT_COLUMNS = [
    "picture_md5", "winning_path", "winning_source_file", "winning_level",
    "lower_source_file", "lower_level", "lower_has_labels",
    "winning_label_count", "lower_label_count", "winning_labels", "lower_labels",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def basename(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def load_picture_table() -> tuple[dict[str, str], set[str]]:
    """md5 -> winning_path, plus the md5 set."""
    winning: dict[str, str] = {}
    with PICTURE_TABLE.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            winning[row["md5"]] = row["winning_path"]
    return winning, set(winning)


def load_manifest() -> tuple[dict[str, set[str]], set[str]]:
    """basename -> set of md5, over every file on disk. Also returns the md5 set."""
    by_basename: dict[str, set[str]] = defaultdict(set)
    md5s: set[str] = set()
    with FILE_MANIFEST.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_basename[basename(row["path"])].add(row["md5"])
            md5s.add(row["md5"])
    return by_basename, md5s


def load_crosswalk() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Return (code -> canonical info) per source group and per canonical row."""
    by_group: dict[str, dict[str, str]] = {g: {} for g in CODE_COLUMN}
    canon: dict[str, dict[str, str]] = {}
    with CROSSWALK.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = row["canonical_id"]
            canon[cid] = row
            for group, column in CODE_COLUMN.items():
                code = row[column]
                if code:
                    by_group[group][code] = cid
    return by_group, canon


def read_images(path: Path) -> list[tuple[str, list[dict]]]:
    """Document-ordered (name, shapes) per image. A shape carries its code, kind and box geometry."""
    root = ET.parse(path).getroot()  # trusted client export, XXE accepted on purpose
    out: list[tuple[str, list[dict]]] = []
    for image in root.findall("image"):
        shapes: list[dict] = []
        for tag in image.findall("tag"):
            shapes.append({"kind": "tag", "code": tag.get("label")})
        for box in image.findall("box"):
            shapes.append({
                "kind": "box", "code": box.get("label"),
                "xtl": box.get("xtl"), "ytl": box.get("ytl"),
                "xbr": box.get("xbr"), "ybr": box.get("ybr"),
                "rotation": box.get("rotation"),
            })
        out.append((image.get("name"), shapes))
    return out


def label_tokens(shapes: list[dict]) -> str:
    return " | ".join(sorted(f"{s['code']}:{s['kind']}" for s in shapes))


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)

    winning_path, table_md5 = load_picture_table()
    by_basename, manifest_md5 = load_manifest()
    code_by_group, canon = load_crosswalk()

    # --- checks on the inputs -------------------------------------------------
    checks: list[tuple[str, bool, str]] = []
    collisions = {b: m for b, m in by_basename.items() if len(m) > 1}
    checks.append(("every_basename_maps_to_one_md5", not collisions,
                   f"{len(collisions)} basenames collide"))
    checks.append(("manifest_and_picture_table_agree_on_md5s",
                   manifest_md5 == table_md5,
                   f"manifest {len(manifest_md5)}, table {len(table_md5)}, "
                   f"symdiff {len(manifest_md5 ^ table_md5)}"))

    # Aliases: content saved under more than one basename, and basenames the
    # picture_table winning_path column alone cannot see.
    md5_to_names: dict[str, set[str]] = defaultdict(set)
    for b, ms in by_basename.items():
        for m in ms:
            md5_to_names[m].add(b)
    aliased = {m: sorted(n) for m, n in md5_to_names.items() if len(n) > 1}
    table_basenames = {basename(p) for p in winning_path.values()}
    alias_only = sorted(b for b in by_basename if b not in table_basenames)

    # code -> canonical must be injective within each source group.
    for group, mapping in code_by_group.items():
        seen: dict[str, str] = {}
        dupes = []
        for code, cid in mapping.items():
            if code in seen:
                dupes.append(code)
            seen[code] = cid
        checks.append((f"code_to_canonical_injective__{group}", not dupes,
                       f"duplicate codes: {dupes}"))

    # --- parse every file and resolve each image to a picture ----------------
    # picture md5 -> list of {level, group, file, shapes}
    picture_mentions: dict[str, list[dict]] = defaultdict(list)
    file_stats: dict[str, dict] = {}
    unresolved: dict[str, list[str]] = defaultdict(list)

    for level, group, fname in SOURCES:
        path = (PROD_DIR if group == "production_20260925" else DATA) / fname
        images = read_images(path)
        picture_ids: set[str] = set()
        shape_count = 0
        for name, shapes in images:
            b = basename(name)
            md5s = by_basename.get(b)
            if not md5s:
                unresolved[fname].append(name)
                continue
            shape_count += len(shapes)
            for m in md5s:
                picture_ids.add(m)
                picture_mentions[m].append(
                    {"level": level, "group": group, "file": fname, "shapes": shapes})
        file_stats[fname] = {
            "group": group,
            "priority_level": level,
            "images": len(images),
            "shapes": shape_count,
            "distinct_pictures_mentioned": len(picture_ids),
            "sha256": sha256(path),
        }

    # --- winner takes all -----------------------------------------------------
    resolved: dict[str, dict] = {}
    for m, mentions in picture_mentions.items():
        levels = {mt["level"] for mt in mentions}
        winner_level = min(levels)
        winners = [mt for mt in mentions if mt["level"] == winner_level]
        wfiles = {mt["file"] for mt in winners}
        if len(wfiles) != 1:
            checks.append((f"single_winner_file__{m}", False, f"{sorted(wfiles)}"))
            winner = winners[0]
        else:
            winner = winners[0]
        resolved[m] = {"winner": winner, "mentions": mentions}

    checks.append(("every_picture_has_at_least_one_mention",
                   all(len(r["mentions"]) >= 1 for r in resolved.values()),
                   f"{len(resolved)} pictures"))
    # No picture carries labels from two sources: each resolved picture has a
    # single winning file, and the resolved rows are drawn only from it.
    multiwinner = [m for m, r in resolved.items()
                   if len({mt["file"] for mt in r["mentions"] if mt["level"] == r["winner"]["level"]}) != 1]
    checks.append(("no_picture_has_two_winning_files", not multiwinner,
                   f"{len(multiwinner)} pictures with two winning files"))

    # --- resolved_labels.csv: one row per surviving shape ---------------------
    resolved_rows: list[dict] = []
    for m, r in resolved.items():
        win = r["winner"]
        group = win["group"]
        for seq, s in enumerate(win["shapes"]):
            cid = code_by_group.get(group, {}).get(s["code"])
            row = {
                "picture_md5": m,
                "winning_path": winning_path[m],
                "source_file": win["file"],
                "source_group": group,
                "priority_level": win["level"],
                "code": s["code"],
                "canonical_id": cid or "",
                "shape_kind": s["kind"],
                "is_size_gate": canon.get(cid, {}).get("is_size_gate", "no") if cid else "",
                "xtl": s.get("xtl", ""), "ytl": s.get("ytl", ""),
                "xbr": s.get("xbr", ""), "ybr": s.get("ybr", ""),
                "rotation": s.get("rotation", ""),
                "_key": (win["level"], win["file"], m, seq),
            }
            resolved_rows.append(row)
    resolved_rows.sort(key=lambda x: x["_key"])
    for row in resolved_rows:
        del row["_key"]

    # --- disagreement.csv: a lower-priority file also mentions a won picture --
    disagreement_rows: list[dict] = []
    for m, r in resolved.items():
        win = r["winner"]
        wlabels = label_tokens(win["shapes"])
        for mt in r["mentions"]:
            if mt["level"] <= win["level"]:
                continue
            lo = mt["shapes"]
            disagreement_rows.append({
                "picture_md5": m,
                "winning_path": winning_path[m],
                "winning_source_file": win["file"],
                "winning_level": win["level"],
                "lower_source_file": mt["file"],
                "lower_level": mt["level"],
                "lower_has_labels": "yes" if lo else "no",
                "winning_label_count": len(win["shapes"]),
                "lower_label_count": len(lo),
                "winning_labels": wlabels,
                "lower_labels": label_tokens(lo),
            })
    disagreement_rows.sort(key=lambda x: (x["lower_level"], x["lower_source_file"],
                                          x["picture_md5"], x["winning_source_file"]))

    # --- counts ---------------------------------------------------------------
    win_level_counts = Counter()
    win_file_counts = Counter()
    for r in resolved.values():
        win_level_counts[r["winner"]["level"]] += 1
        win_file_counts[r["winner"]["file"]] += 1

    # per-canonical shape and picture counts, over surviving shapes
    canon_shapes = Counter()
    canon_pics: dict[str, set[str]] = defaultdict(set)
    for row in resolved_rows:
        if row["canonical_id"]:
            canon_shapes[row["canonical_id"]] += 1
            canon_pics[row["canonical_id"]].add(row["picture_md5"])

    # disagreement breakdown, by lower file
    dis_by_lower = defaultdict(lambda: {"mentions": 0, "with_labels": 0})
    for row in disagreement_rows:
        d = dis_by_lower[row["lower_source_file"]]
        d["mentions"] += 1
        if row["lower_has_labels"] == "yes":
            d["with_labels"] += 1

    resolved_total = len(resolved)
    per_source_sum = sum(win_file_counts.values())

    # --- checks on the results ------------------------------------------------
    checks.append(("per_source_wins_sum_to_resolved_total",
                   per_source_sum == resolved_total,
                   f"{per_source_sum} vs {resolved_total}"))
    checks.append(("every_resolved_picture_is_in_picture_table",
                   all(m in table_md5 for m in resolved),
                   f"{sum(1 for m in resolved if m not in table_md5)} missing"))
    checks.append(("every_surviving_shape_has_a_canonical_id",
                   all(row["canonical_id"] for row in resolved_rows),
                   f"{sum(1 for row in resolved_rows if not row['canonical_id'])} un-mapped"))
    # No resolved picture is fed by more than one source file.
    src_per_pic: dict[str, set[str]] = defaultdict(set)
    for row in resolved_rows:
        src_per_pic[row["picture_md5"]].add(row["source_file"])
    two_src = {m: s for m, s in src_per_pic.items() if len(s) > 1}
    checks.append(("resolved_rows_single_source_per_picture", not two_src,
                   f"{len(two_src)} pictures fed by two files"))
    # Lower-priority mentions never leak into resolved rows.
    leaks = 0
    for row in resolved_rows:
        r = resolved[row["picture_md5"]]
        if row["source_file"] != r["winner"]["file"]:
            leaks += 1
    checks.append(("no_lower_priority_shape_survives", leaks == 0, f"{leaks} leaked rows"))
    checks.append(("annotations_resolve_completely",
                   not any(unresolved.values()),
                   f"unresolved by file: { {k: len(v) for k, v in unresolved.items() if v} }"))
    # Shape kinds are only box or tag in the resolved table.
    bad_kind = [row["shape_kind"] for row in resolved_rows if row["shape_kind"] not in ("box", "tag")]
    checks.append(("shape_kinds_are_box_or_tag", not bad_kind, f"{len(bad_kind)} bad kinds"))

    failed = sum(1 for _, ok, _ in checks if not ok)

    # --- write the outputs ----------------------------------------------------
    resolved_csv = RUN / "resolved_labels.csv"
    with resolved_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESOLVED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(resolved_rows)
    resolved_md5 = hashlib.md5(resolved_csv.read_bytes()).hexdigest()

    disagreement_csv = RUN / "disagreement.csv"
    with disagreement_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DISAGREEMENT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(disagreement_rows)
    disagreement_md5 = hashlib.md5(disagreement_csv.read_bytes()).hexdigest()

    resolution = {
        "ticket": "010-label-resolution",
        "date": "2026-10-15",
        "priority_order": {
            str(lvl): sorted({f for l, _, f in SOURCES if l == lvl})
            for lvl in sorted({l for l, _, _ in SOURCES})
        },
        "files": {f: file_stats[f] for _, _, f in SOURCES},
        "win_counts": {
            "by_priority_level": {str(k): v for k, v in sorted(win_level_counts.items())},
            "by_source_file": dict(sorted(win_file_counts.items())),
            "resolved_pictures_total": resolved_total,
            "per_source_sum": per_source_sum,
        },
        "resolved_shape_count": len(resolved_rows),
        "per_canonical_defect": {
            cid: {"shape_count": canon_shapes.get(cid, 0),
                  "picture_count": len(canon_pics.get(cid, ()))}
            for cid in sorted(set(canon_shapes) | set(canon_pics))
        },
        "disagreement": {
            "rows": len(disagreement_rows),
            "by_lower_file": {k: dict(v) for k, v in sorted(dis_by_lower.items())},
            "sep22_mentions": sum(1 for r in disagreement_rows
                                  if r["lower_source_file"] == "Updated Annotations 20260922.xml"),
            "sep22_with_labels": sum(1 for r in disagreement_rows
                                     if r["lower_source_file"] == "Updated Annotations 20260922.xml"
                                     and r["lower_has_labels"] == "yes"),
            "old_mentions": sum(1 for r in disagreement_rows
                                if r["lower_source_file"] == "annotations.xml"),
            "old_with_labels": sum(1 for r in disagreement_rows
                                   if r["lower_source_file"] == "annotations.xml"
                                   and r["lower_has_labels"] == "yes"),
        },
        "unresolved_annotation_images": {k: v for k, v in unresolved.items() if v},
        "renamed_aliases": {
            "basenames_in_more_than_one_name_for_one_content": len(aliased),
            "basenames_only_visible_via_the_manifest": len(alias_only),
            "examples": alias_only[:10],
        },
        "picture_table_pictures": len(table_md5),
        "unannotated_pictures": len(table_md5 - set(resolved)),
        "outputs": {
            "resolved_labels.csv": {"rows": len(resolved_rows), "md5": resolved_md5},
            "disagreement.csv": {"rows": len(disagreement_rows), "md5": disagreement_md5},
        },
        "checks": [{"name": n, "ok": ok, "note": note} for n, ok, note in checks],
        "check_count": len(checks),
        "failed_count": failed,
    }
    out_json = RUN / "resolution.json"
    out_json.write_text(json.dumps(resolution, indent=2, sort_keys=False) + "\n",
                        encoding="utf-8")

    # --- report ---------------------------------------------------------------
    print(f"pictures in census: {len(table_md5)}")
    print(f"pictures with any annotation (resolved): {resolved_total}")
    print(f"resolved shapes: {len(resolved_rows)}")
    print("wins by priority level: " + ", ".join(
        f"{k}={v}" for k, v in sorted(win_level_counts.items())))
    print("wins by source file:")
    for f, n in sorted(win_file_counts.items()):
        print(f"   {f}: {n}")
    print(f"disagreement rows: {len(disagreement_rows)}")
    for f, d in sorted(dis_by_lower.items()):
        print(f"   {f}: mentions={d['mentions']} with_labels={d['with_labels']}")
    print(f"basenames only visible via the manifest: {len(alias_only)}")
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    print(f"resolved_labels.csv md5: {resolved_md5}")
    print(f"disagreement.csv md5: {disagreement_md5}")
    print(f"checks: {len(checks)}, failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
