#!/usr/bin/env python3
"""Verify the label resolution by an independent second route.

Ticket 010 of the full-coverage EDA map.

The builder reads the 9 XMLs with ElementTree.parse and walks image children.
This verifier reads the same 9 XMLs with iterparse over ("end",) events, resolves
pictures from the census, recomputes the winner-takes-all resolution and the
disagreement counts from scratch, and diffs every headline against

  * the recorded outputs (run/eda_full_20261015/resolution.json, resolved_labels.csv,
    disagreement.csv), and
  * a hand-typed EXPECTED table below.

It also re-derives the 2026-10-13 to 2026-10-15 production delta, if a local copy
of the 2026-10-13 files is available (see OLD_PROD_DIR). That spot check compares
each production picture's shape multiset between the two versions and reports
every changed picture and every added or removed shape label.

The XML files are trusted CVAT exports made by the client's own account and
pulled from a private blob store, so the standard library parser is used on
purpose and Python's XXE warning is knowingly accepted here.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/verify_resolution.py
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
RUN = REPO / "run" / "eda_full_20261015"

PRODUCTION = [(1, "production_20260925", f"annotations_45219{n}.xml")
              for n in range(40, 47)]
SOURCES = (PRODUCTION
           + [(2, "updated_20260922", "Updated Annotations 20260922.xml")]
           + [(3, "project2", "annotations.xml")])

# The 2026-10-13 production exports, pulled read-only from the shared VM into a
# local scratch directory. Override with the OLD_PROD_DIR environment variable.
OLD_PROD_DIR = Path(os.environ.get(
    "OLD_PROD_DIR",
    "C:/Users/Abcom/AppData/Local/hermes/cache/scratch/old_prod"))

# --- hand-typed expected values --------------------------------------------
EXPECTED = {
    "census_pictures": 10614,
    "resolved_pictures": 6690,
    "resolved_shapes": 20014,
    "unannotated_pictures": 3924,
    "wins_by_level": {1: 1046, 2: 5387, 3: 257},
    "wins_by_file": {
        "annotations_4521940.xml": 149,
        "annotations_4521941.xml": 150,
        "annotations_4521942.xml": 147,
        "annotations_4521943.xml": 150,
        "annotations_4521944.xml": 150,
        "annotations_4521945.xml": 150,
        "annotations_4521946.xml": 150,
        "Updated Annotations 20260922.xml": 5387,
        "annotations.xml": 257,
    },
    "disagreement_rows": 886,
    "sep22_mentions": 709,
    "sep22_with_labels": 594,
    "old_mentions": 177,
    "old_with_labels": 177,
    # basename-based estimates from the map, kept for the comparison of record.
    "basename_estimate_sep22": 708,
    "basename_estimate_old": 116,
    "basename_only_sep22_lost_by_hash": 1,   # 709 - 708
    "basename_only_old_lost_to_prod": 15,   # 131 - 116
    "old_lost_to_prod": 131,
    "old_lost_to_sep22": 46,
    "unresolved_annotation_images": 0,
    "renamed_alias_basenames": 187,
    "delta_changed_pictures": 170,
    "delta_added_tags": {"P3_FM_MICRON_THRESHOLD": 118,
                         "P3_FIB_MICRON_THRESHOLD": 51,
                         "P3_EP_MICRON_THRESHOLD": 1},
    "delta_removed_tags": {"P1_ML": 1},
    "per_canonical": {
        "bubble": (819, 10869), "bubble_cluster": (428, 1182),
        "bubble_irregular": (147, 169), "bubble_on_123": (13, 79),
        "bubble_on_edge": (14, 90), "bubble_scatter": (6, 6),
        "cavity_off_center": (184, 184), "dirty_camera": (329, 329),
        "dirty_strobe": (43, 43), "extraneous_polymer": (144, 150),
        "extraneous_polymer_micron_gate": (33, 33), "fiber": (178, 245),
        "fiber_micron_gate": (136, 136), "folded_lens": (237, 237),
        "foreign_matter": (331, 626), "foreign_matter_micron_gate": (171, 171),
        "hema_fragment": (7, 8), "hema_micron_gate": (94, 94),
        "hema_obstruction": (180, 181), "lens_off_center": (957, 957),
        "low_dose": (215, 215), "missing_lens": (325, 325),
        "missing_primary_package": (1426, 1551), "multiple_lenses": (1439, 1439),
        "package_misalignment": (2, 2), "stretched_bubble": (6, 7),
        "view_obstructed": (24, 24), "wet_package": (146, 662),
    },
}


def basename(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def iter_images(path: Path):
    """Second route: iterparse end events, so an <image> is fully built before read."""
    for _event, elem in ET.iterparse(path, events=("end",)):  # trusted client export
        if elem.tag != "image":
            continue
        shapes: list[tuple[str, str]] = []
        for tag in elem.findall("tag"):
            shapes.append(("tag", tag.get("label")))
        for box in elem.findall("box"):
            shapes.append(("box", box.get("label")))
        yield elem.get("name"), shapes
        elem.clear()


def shapes_by_image(path: Path) -> dict[str, Counter]:
    return {basename(n): Counter(s) for n, s in iter_images(path)}


def boxes_by_image(path: Path) -> dict[str, list[tuple]]:
    """Geometry per image, from iterparse end events, so it is the second route too."""
    out: dict[str, list[tuple]] = {}
    for _event, elem in ET.iterparse(path, events=("end",)):  # trusted client export
        if elem.tag != "image":
            continue
        boxes = sorted((b.get("xtl"), b.get("ytl"), b.get("xbr"), b.get("ybr"),
                        b.get("rotation")) for b in elem.findall("box"))
        out[basename(elem.get("name"))] = boxes
        elem.clear()
    return out


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, note: str = "") -> None:
        checks.append((name, bool(ok), note))

    # --- census from the manifest --------------------------------------------
    by_basename: dict[str, set[str]] = defaultdict(set)
    manifest_md5: set[str] = set()
    with (RUN / "file_manifest.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_basename[basename(row["path"])].add(row["md5"])
            manifest_md5.add(row["md5"])
    winning_path: dict[str, str] = {}
    with (RUN / "picture_table.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            winning_path[row["md5"]] = row["winning_path"]
    census = set(winning_path)
    check("census_size", len(census) == EXPECTED["census_pictures"],
          f"{len(census)}")
    check("manifest_matches_census", manifest_md5 == census,
          f"symdiff {len(manifest_md5 ^ census)}")

    # --- code -> canonical ----------------------------------------------------
    code_by_group: dict[str, dict[str, str]] = {g: {} for _, g, _ in SOURCES}
    with (DATA / "crosswalk.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for _lvl, group, _f in SOURCES:
                code = row["code_in_production_20260925" if group == "production_20260925"
                           else "code_in_updated_20260922" if group == "updated_20260922"
                           else "code_in_project2"]
                if code:
                    code_by_group[group][code] = row["canonical_id"]

    # --- second-route re-derivation ------------------------------------------
    picture_mentions: dict[str, list[dict]] = defaultdict(list)
    per_file_pictures: dict[str, set[str]] = {}
    unresolved: dict[str, int] = defaultdict(int)
    file_images: dict[str, int] = {}
    for level, group, fname in SOURCES:
        pics: set[str] = set()
        n_images = 0
        for name, shapes in iter_images(DATA / fname):
            n_images += 1
            b = basename(name)
            md5s = by_basename.get(b)
            if not md5s:
                unresolved[fname] += 1
                continue
            for m in md5s:
                pics.add(m)
                picture_mentions[m].append({"level": level, "group": group,
                                            "file": fname, "shapes": shapes})
        per_file_pictures[fname] = pics
        file_images[fname] = n_images

    resolved: dict[str, dict] = {}
    for m, mentions in picture_mentions.items():
        wl = min(mt["level"] for mt in mentions)
        winner = [mt for mt in mentions if mt["level"] == wl][0]
        resolved[m] = {"winner": winner, "mentions": mentions}

    win_by_level = Counter()
    win_by_file = Counter()
    resolved_shapes = 0
    two_source = 0
    canon_pics: dict[str, set[str]] = defaultdict(set)
    canon_shapes = Counter()
    for m, r in resolved.items():
        win_by_level[r["winner"]["level"]] += 1
        win_by_file[r["winner"]["file"]] += 1
        resolved_shapes += len(r["winner"]["shapes"])
        if len({mt["file"] for mt in r["mentions"] if mt["level"] == r["winner"]["level"]}) != 1:
            two_source += 1
        for kind, code in r["winner"]["shapes"]:
            cid = code_by_group[r["winner"]["group"]].get(code)
            if cid:
                canon_shapes[cid] += 1
                canon_pics[cid].add(m)

    dis_by_lower = defaultdict(lambda: {"mentions": 0, "with_labels": 0})
    dis_rows = 0
    for m, r in resolved.items():
        for mt in r["mentions"]:
            if mt["level"] <= r["winner"]["level"]:
                continue
            dis_rows += 1
            d = dis_by_lower[mt["file"]]
            d["mentions"] += 1
            if mt["shapes"]:
                d["with_labels"] += 1

    # --- compare to EXPECTED --------------------------------------------------
    check("resolved_pictures", len(resolved) == EXPECTED["resolved_pictures"],
          f"{len(resolved)}")
    check("resolved_shapes", resolved_shapes == EXPECTED["resolved_shapes"],
          f"{resolved_shapes}")
    check("unannotated_pictures",
          len(census - set(resolved)) == EXPECTED["unannotated_pictures"],
          f"{len(census - set(resolved))}")
    check("wins_by_level", dict(win_by_level) == EXPECTED["wins_by_level"],
          f"{dict(win_by_level)}")
    check("wins_by_file", dict(win_by_file) == EXPECTED["wins_by_file"],
          f"{dict(win_by_file)}")
    check("no_picture_two_winning_files", two_source == 0, f"{two_source}")
    check("disagreement_rows", dis_rows == EXPECTED["disagreement_rows"],
          f"{dis_rows}")
    check("sep22_mentions",
          dis_by_lower["Updated Annotations 20260922.xml"]["mentions"] == EXPECTED["sep22_mentions"],
          f"{dis_by_lower['Updated Annotations 20260922.xml']['mentions']}")
    check("sep22_with_labels",
          dis_by_lower["Updated Annotations 20260922.xml"]["with_labels"] == EXPECTED["sep22_with_labels"],
          f"{dis_by_lower['Updated Annotations 20260922.xml']['with_labels']}")
    check("old_mentions",
          dis_by_lower["annotations.xml"]["mentions"] == EXPECTED["old_mentions"],
          f"{dis_by_lower['annotations.xml']['mentions']}")
    check("old_with_labels",
          dis_by_lower["annotations.xml"]["with_labels"] == EXPECTED["old_with_labels"],
          f"{dis_by_lower['annotations.xml']['with_labels']}")
    check("unresolved_annotation_images",
          sum(unresolved.values()) == EXPECTED["unresolved_annotation_images"],
          f"{dict(unresolved)}")

    # basename-estimate reconciliation, second route.
    prod_pics = set().union(*[per_file_pictures[f] for _l, _g, f in PRODUCTION])
    sep_lost = {m for m in per_file_pictures["Updated Annotations 20260922.xml"]
                if m in prod_pics}
    old_pics = per_file_pictures["annotations.xml"]
    old_lost_prod = {m for m in old_pics if m in prod_pics}
    old_lost_sep = {m for m in old_pics
                    if m in per_file_pictures["Updated Annotations 20260922.xml"]
                    and m not in prod_pics}
    check("old_lost_to_prod", len(old_lost_prod) == EXPECTED["old_lost_to_prod"],
          f"{len(old_lost_prod)}")
    check("old_lost_to_sep22", len(old_lost_sep) == EXPECTED["old_lost_to_sep22"],
          f"{len(old_lost_sep)}")
    check("basename_estimate_gap_sep22",
          len(sep_lost) - EXPECTED["basename_estimate_sep22"] == EXPECTED["basename_only_sep22_lost_by_hash"],
          f"{len(sep_lost)} vs {EXPECTED['basename_estimate_sep22']}")
    check("basename_estimate_gap_old",
          len(old_lost_prod) - EXPECTED["basename_estimate_old"] == EXPECTED["basename_only_old_lost_to_prod"],
          f"{len(old_lost_prod)} vs {EXPECTED['basename_estimate_old']}")

    # per-canonical picture and shape counts.
    canon_mismatch = {
        cid: (len(canon_pics.get(cid, ())), canon_shapes.get(cid, 0),
              EXPECTED["per_canonical"].get(cid))
        for cid in set(canon_pics) | set(EXPECTED["per_canonical"])
        if (len(canon_pics.get(cid, ())), canon_shapes.get(cid, 0))
        != EXPECTED["per_canonical"].get(cid)
    }
    check("per_canonical_picture_and_shape_counts", not canon_mismatch,
          f"{canon_mismatch}")

    # --- diff against the recording ------------------------------------------
    recorded = json.loads((RUN / "resolution.json").read_text(encoding="utf-8"))
    check("json_resolved_total",
          recorded["win_counts"]["resolved_pictures_total"] == len(resolved),
          f"{recorded['win_counts']['resolved_pictures_total']}")
    check("json_resolved_shapes",
          recorded["resolved_shape_count"] == resolved_shapes,
          f"{recorded['resolved_shape_count']}")
    check("json_disagreement_rows",
          recorded["disagreement"]["rows"] == dis_rows,
          f"{recorded['disagreement']['rows']}")
    check("json_win_by_file",
          {k: v for k, v in recorded["win_counts"]["by_source_file"].items()} == dict(win_by_file),
          "")
    check("json_file_images",
          all(recorded["files"][f]["images"] == file_images[f] for _l, _g, f in SOURCES),
          "")
    check("json_no_unresolved",
          recorded.get("unresolved_annotation_images", {}) == {},
          "")
    check("json_renamed_aliases",
          recorded["renamed_aliases"]["basenames_only_visible_via_the_manifest"]
          == EXPECTED["renamed_alias_basenames"],
          f"{recorded['renamed_aliases']['basenames_only_visible_via_the_manifest']}")

    # output files: byte identity against the md5 the builder recorded.
    check("resolved_labels_csv_md5",
          md5(RUN / "resolved_labels.csv") == recorded["outputs"]["resolved_labels.csv"]["md5"],
          md5(RUN / "resolved_labels.csv"))
    check("disagreement_csv_md5",
          md5(RUN / "disagreement.csv") == recorded["outputs"]["disagreement.csv"]["md5"],
          md5(RUN / "disagreement.csv"))

    # resolved_labels.csv read back: every picture on one source only.
    csv_sources: dict[str, set[str]] = defaultdict(set)
    csv_pictures: set[str] = set()
    with (RUN / "resolved_labels.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            csv_pictures.add(row["picture_md5"])
            csv_sources[row["picture_md5"]].add(row["source_file"])
    check("csv_single_source_per_picture",
          all(len(s) == 1 for s in csv_sources.values()),
          f"{sum(1 for s in csv_sources.values() if len(s) > 1)} multi-source")
    check("csv_pictures_subset_of_resolved",
          csv_pictures <= set(resolved),
          f"{len(csv_pictures - set(resolved))} stray")

    # --- delta: 2026-10-13 vs 2026-10-15 production files --------------------
    skip_count = 0
    if OLD_PROD_DIR.is_dir():
        adds = Counter()
        dels = Counter()
        added_kinds: set[str] = set()
        removed_kinds: set[str] = set()
        changed = 0
        geom_changed = 0
        for _lvl, _grp, fname in PRODUCTION:
            new = shapes_by_image(DATA / fname)
            old = shapes_by_image(OLD_PROD_DIR / fname)
            new_geom = boxes_by_image(DATA / fname)
            old_geom = boxes_by_image(OLD_PROD_DIR / fname)
            for key in set(new) | set(old):
                ns, os_ = new.get(key, Counter()), old.get(key, Counter())
                if ns != os_:
                    changed += 1
                    for lab, c in (ns - os_).items():
                        adds[lab[1]] += c
                        added_kinds.add(lab[0])
                    for lab, c in (os_ - ns).items():
                        dels[lab[1]] += c
                        removed_kinds.add(lab[0])
                if new_geom.get(key, []) != old_geom.get(key, []):
                    geom_changed += 1
        check("delta_changed_pictures",
              changed == EXPECTED["delta_changed_pictures"], f"{changed}")
        check("delta_added_tags", dict(adds) == EXPECTED["delta_added_tags"],
              f"{dict(adds)}")
        check("delta_removed_tags", dict(dels) == EXPECTED["delta_removed_tags"],
              f"{dict(dels)}")
        check("delta_only_tags_changed",
              added_kinds <= {"tag"} and removed_kinds <= {"tag"},
              f"added {added_kinds}, removed {removed_kinds}")
        check("delta_geometry_untouched", geom_changed == 0, f"{geom_changed}")
    else:
        skip_count += 1
        print(f"note: OLD_PROD_DIR not found ({OLD_PROD_DIR}); delta checks skipped")

    failed = sum(1 for _n, ok, _note in checks if not ok)
    print(f"verifier checks: {len(checks)}, failed: {failed}, skipped: {skip_count}")
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
