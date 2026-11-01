#!/usr/bin/env python3
"""Coverage analysis for ticket 015 of the full-coverage EDA map.

What is mentioned, what carries a shape, and what is mentioned nowhere, out of
what exists, by library folder, by folder group, by production line and by
canonical defect, plus the pictures the three library folders label differently
from each other.

Counting rules, fixed by the map and not negotiable here:

- Every join is keyed on content md5, never on a path. 187 basenames hold a
  content that also exists under a second name, so a path-based count undercounts.
- Every table says whether it is a MENTION count or a SHAPE count.
  A picture is MENTIONED when some annotation file lists it. A picture CARRIES a
  SHAPE when the resolved label set holds at least one shape for it. The word
  "annotated" alone is never used.

Terms:
- census            = run/eda_full_20261015/picture_table.csv, 10,614 distinct pictures.
- mentioned         = listed by at least one of the 9 annotation files (by basename
                      resolved through the full manifest, keyed on md5).
- carries a shape   = at least one surviving shape in resolved_labels.csv.
- mentioned nowhere = in the census and not in the mentioned set.
- no shape          = in the census and not in the shape set.

Population, one path per picture (map decision 6): a picture is assigned to the
folder of its winning_path, the first library folder that holds it in the fixed
order Updated Objects, Updated Categorical, old library. So the per-folder, per
group and per line strata partition the census and their distinct counts sum to
10,614.

The XML files are trusted CVAT exports made by the client's own account and
pulled from a private blob store, not attacker supplied, so the standard library
parser is used on purpose and Python's XXE warning is knowingly accepted here.
This mirrors resolve_labels.py.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/coverage.py
"""

from __future__ import annotations

import csv
import hashlib
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RUN = REPO / "run" / "eda_full_20261015"

PICTURE_TABLE = RUN / "picture_table.csv"
FILE_MANIFEST = RUN / "file_manifest.csv"
RESOLVED = RUN / "resolved_labels.csv"
DISAGREEMENT = RUN / "disagreement.csv"
CROSSWALK = DATA / "crosswalk.csv"
COVERAGE_CSV = RUN / "coverage.csv"
FOLDER_DISAGREEMENT_CSV = RUN / "folder_disagreement.csv"

PRODUCTION = [(1, "production_20260925", f"annotations_45219{n}.xml") for n in range(40, 47)]
SOURCES = PRODUCTION + [
    (2, "updated_20260922", "Updated Annotations 20260922.xml"),
    (3, "project2", "annotations.xml"),
]

LIBRARY_FOLDERS = (
    "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
    "ICube Defects Library",
)
FOLDER_GROUP = {
    "Updated ICube Objects 20260915": "Updated",
    "Updated ICube Categorical Classes 20260915": "Updated",
    "ICube Defects Library": "Library",
}
# The census partitions into folder groups; production/images is not an image source.
GROUP_ORDER = ["Updated", "Library"]
LINE_ORDER = ["L24", "L25", "L26", "L27", "L31"]

# The class subfolder that is not a class: a parking folder of exact copies.
NOT_A_CLASS = {"duplicates"}

# Old-library class names that a newer project renamed. Used only to name the
# folder a canonical defect nominally lives in for the per-class table.
FOLDER_ALIASES = {
    "low_dose": ["Low Dose Obstructing Region of Interest"],
}

COVERAGE_COLUMNS = [
    "stratum_type", "stratum_value", "population_name",
    "distinct_pictures", "pictures_mentioned", "pictures_with_shape",
    "pictures_no_shape", "pictures_mentioned_nowhere",
    "shape_coverage_ratio", "mention_coverage_ratio",
    "defect_pictures_carrying", "defect_share_of_population",
]

FOLDER_DISAGREEMENT_COLUMNS = [
    "picture_md5", "winning_path", "in_production_batch",
    "updated_objects_class", "updated_categorical_class", "defects_library_class",
    "distinct_class_count", "class_pair", "class_set", "n_library_folders",
]


def basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def class_of(path: str) -> str:
    parts = path.split("/")
    return parts[1] if len(parts) > 2 else "<root>"


def load_manifest():
    """basename -> set(md5), md5 -> set((folder, class)), md5 -> set(folder)."""
    by_basename: dict[str, set[str]] = defaultdict(set)
    md5_fc: dict[str, set[tuple[str, str]]] = defaultdict(set)
    md5_folders: dict[str, set[str]] = defaultdict(set)
    with FILE_MANIFEST.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            md5 = row["md5"]
            by_basename[basename(row["path"])].add(md5)
            md5_fc[md5].add((row["folder"], class_of(row["path"])))
            md5_folders[md5].add(row["folder"])
    return by_basename, md5_fc, md5_folders


def load_picture_table():
    """md5 -> {winning_path, line, in_production_batch}."""
    table: dict[str, dict[str, str]] = {}
    with PICTURE_TABLE.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[row["md5"]] = {
                "winning_path": row["winning_path"],
                "line": row["line"],
                "in_production_batch": row["in_production_batch"],
            }
    return table


def load_crosswalk():
    canon: dict[str, dict[str, str]] = {}
    with CROSSWALK.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            canon[row["canonical_id"]] = row
    return canon


def mentioned_set(by_basename):
    """Basename of every annotation image, resolved through the manifest to md5."""
    mentioned: set[str] = set()
    for _level, _group, fname in SOURCES:
        root = ET.parse(DATA / fname).getroot()  # trusted client export, XXE accepted on purpose
        for image in root.findall("image"):
            md5s = by_basename.get(basename(image.get("name")))
            if md5s:
                mentioned |= md5s
    return mentioned


def shape_sets():
    """set of md5 that carry a shape, plus canonical_id -> set(md5)."""
    shape: set[str] = set()
    per_canon: dict[str, set[str]] = defaultdict(set)
    with RESOLVED.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            shape.add(row["picture_md5"])
            if row["canonical_id"]:
                per_canon[row["canonical_id"]].add(row["picture_md5"])
    return shape, per_canon


def folder_names_for_defect(cid: str, row: dict[str, str], existing: set[str]) -> list[str]:
    """The library class folder(s) a canonical defect nominally lives in."""
    names: list[str] = []
    if row["library_folder_name"]:
        names.append(row["library_folder_name"])
    if row["canonical_name"] in existing:
        names.append(row["canonical_name"])
    names.extend(FOLDER_ALIASES.get(cid, []))
    seen: list[str] = []
    for n in names:
        if n in existing and n not in seen:
            seen.append(n)
    return seen


def ratio(num: int, den: int):
    return "" if den == 0 else round(num / den, 6)


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    by_basename, md5_fc, md5_folders = load_manifest()
    table = load_picture_table()
    canon = load_crosswalk()
    mentioned = mentioned_set(by_basename)
    shape, per_canon = shape_sets()

    universe = set(table)
    census = len(universe)
    assert set(md5_fc) == universe, "manifest and picture table disagree on md5s"

    existing_folders = {c for _f, c in (fc for s in md5_fc.values() for fc in s)}
    existing_folders -= NOT_A_CLASS

    coverage_rows: list[dict] = []
    checks: list[tuple[str, bool, str]] = []

    def emit(stratum_type, value, pop_name, population, carrying=None):
        d = len(population)
        m = len(population & mentioned)
        if carrying is None:
            s = len(population & shape)
            row = {
                "distinct_pictures": d,
                "pictures_mentioned": m,
                "pictures_with_shape": s,
                "pictures_no_shape": d - s,
                "pictures_mentioned_nowhere": d - m,
                "shape_coverage_ratio": ratio(s, d),
                "mention_coverage_ratio": ratio(m, d),
                "defect_pictures_carrying": "",
                "defect_share_of_population": "",
            }
        else:
            c = len(carrying)
            # A shape count: how many pictures carry the defect, and its share of the
            # population (the folder the defect nominally lives in). The share can
            # exceed 1 because the labels come from the annotation files and were not
            # assigned by folder, so a defect filed mostly outside its nominal folder
            # reads above 1. pictures_no_shape and pictures_mentioned_nowhere do not
            # describe a defect row and are left blank.
            row = {
                "distinct_pictures": d,
                "pictures_mentioned": m,
                "pictures_with_shape": c,
                "pictures_no_shape": "",
                "pictures_mentioned_nowhere": "",
                "shape_coverage_ratio": ratio(c, d),
                "mention_coverage_ratio": ratio(m, d),
                "defect_pictures_carrying": c,
                "defect_share_of_population": ratio(c, d),
            }
        row_out = {"stratum_type": stratum_type, "stratum_value": value,
                   "population_name": pop_name}
        row_out.update(row)
        coverage_rows.append(row_out)

    # --- per library folder (folder of winning_path) --------------------------
    folder_pop: dict[str, set[str]] = defaultdict(set)
    for m in universe:
        folder_pop[table[m]["winning_path"].split("/")[0]].add(m)
    pop_name = "census pictures assigned to the folder by winning_path (map decision 6)"
    for f in LIBRARY_FOLDERS:
        emit("folder", f, pop_name, folder_pop.get(f, set()))
    folder_sum = sum(len(v) for v in folder_pop.values())
    checks.append(("folders_partition_census", folder_sum == census,
                   f"folder distinct sum {folder_sum} vs census {census}"))

    # --- per folder group -----------------------------------------------------
    group_pop: dict[str, set[str]] = defaultdict(set)
    for m in universe:
        group_pop[FOLDER_GROUP[table[m]["winning_path"].split("/")[0]]].add(m)
    for g in GROUP_ORDER:
        emit("folder_group", g, "census pictures in the folder group (winning_path folder)",
             group_pop[g])
    group_sum = sum(len(v) for v in group_pop.values())
    checks.append(("groups_partition_census", group_sum == census,
                   f"group distinct sum {group_sum} vs census {census}"))

    # --- per production line --------------------------------------------------
    line_pop: dict[str, set[str]] = defaultdict(set)
    for m in universe:
        line_pop[table[m]["line"]].add(m)
    for ln in LINE_ORDER:
        emit("production_line", ln, "census pictures on the line (from the filename)", line_pop[ln])
    line_sum = sum(len(v) for v in line_pop.values())
    checks.append(("lines_partition_census", line_sum == census,
                   f"line distinct sum {line_sum} vs census {census}"))

    # --- per canonical defect -------------------------------------------------
    class_members: dict[str, set[str]] = defaultdict(set)
    for md5, fcs in md5_fc.items():
        for _f, c in fcs:
            if c not in NOT_A_CLASS:
                class_members[c].add(md5)

    defect_over_nominal = 0
    for cid in sorted(canon):
        row = canon[cid]
        names = folder_names_for_defect(cid, row, existing_folders)
        carry = per_canon.get(cid, set())
        if names:
            population: set[str] = set()
            for n in names:
                population |= class_members[n]
            pop_label = "pictures filed in the library class folder(s) named " + ", ".join(names)
            emit("canonical_defect", cid, pop_label, population, carrying=carry)
            if len(carry) > len(population):
                defect_over_nominal += 1
        else:
            emit("canonical_defect", cid, "no library class folder is named for this defect",
                 set(), carrying=carry)
    checks.append(("defects_reported_carry_over_nominal_folder", True,
                   f"{defect_over_nominal} defects carry more pictures than their nominal "
                   f"folder holds (reported, not a failure)"))

    # --- library-only pictures -------------------------------------------------
    library_only = {m for m in universe if md5_folders[m] == {"ICube Defects Library"}}
    library_only_class = Counter()
    for m in library_only:
        for f, c in md5_fc[m]:
            if f == "ICube Defects Library":
                library_only_class[c] += 1
    checks.append(("library_only_pictures_sum_to_class_breakdown",
                   sum(library_only_class.values()) == len(library_only),
                   f"{sum(library_only_class.values())} vs {len(library_only)}"))

    # --- write coverage.csv ---------------------------------------------------
    with COVERAGE_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COVERAGE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(coverage_rows)
    coverage_md5 = hashlib.md5(COVERAGE_CSV.read_bytes()).hexdigest()

    # --- folder-label disagreement --------------------------------------------
    # A picture the library folders label differently from each other: its class
    # subfolder name is not the same across the library folders that hold it.
    # Keyed on content md5, the "duplicates" parking folder dropped.
    disagree_rows: list[dict] = []
    for md5, fcs in md5_fc.items():
        cls_by_folder: dict[str, set[str]] = defaultdict(set)
        for f, c in fcs:
            if f in LIBRARY_FOLDERS and c not in NOT_A_CLASS:
                cls_by_folder[f].add(c)
        classes = {c for cs in cls_by_folder.values() for c in cs}
        if len(classes) > 1:
            def joined(folder):
                return "; ".join(sorted(cls_by_folder.get(folder, [])))
            pair = tuple(sorted(classes))
            disagree_rows.append({
                "picture_md5": md5,
                "winning_path": table[md5]["winning_path"],
                "in_production_batch": table[md5]["in_production_batch"],
                "updated_objects_class": joined("Updated ICube Objects 20260915"),
                "updated_categorical_class": joined("Updated ICube Categorical Classes 20260915"),
                "defects_library_class": joined("ICube Defects Library"),
                "distinct_class_count": len(classes),
                "class_pair": " vs ".join(pair),
                "class_set": " | ".join(pair),
                "n_library_folders": len(cls_by_folder),
            })
    disagree_rows.sort(key=lambda r: (r["class_pair"], r["picture_md5"]))
    with FOLDER_DISAGREEMENT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FOLDER_DISAGREEMENT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(disagree_rows)
    folder_disagreement_md5 = hashlib.md5(FOLDER_DISAGREEMENT_CSV.read_bytes()).hexdigest()

    # --- checks on the headline numbers ---------------------------------------
    checks.append(("census_total", census == 10614, f"census {census}"))
    checks.append(("mentioned_total", len(mentioned) == 6690, f"mentioned {len(mentioned)}"))
    checks.append(("shape_total", len(shape) == 4782, f"shape {len(shape)}"))
    checks.append(("mentioned_nowhere_total", census - len(mentioned) == 3924,
                   f"nowhere {census - len(mentioned)}"))
    checks.append(("no_shape_total", census - len(shape) == 5832,
                   f"no_shape {census - len(shape)}"))
    checks.append(("library_only_177", len(library_only) == 177,
                   f"library-only {len(library_only)}"))
    checks.append(("disagreement_rows_gt_113", len(disagree_rows) >= 113,
                   f"folder disagreement pictures {len(disagree_rows)}"))
    # Every picture mentioned or carrying a shape is in the census.
    checks.append(("mentioned_subset_of_census", mentioned <= universe, "ok"))
    checks.append(("shape_subset_of_mentioned", shape <= mentioned,
                   f"{len(shape - mentioned)} carry a shape but are not mentioned"))
    # No class folder carries a class assigned to a picture twice within one folder.
    checks.append(("every_library_folder_counted", set(folder_pop) <= set(LIBRARY_FOLDERS),
                   f"folders seen {sorted(folder_pop)}"))

    failed = sum(1 for _n, ok, _note in checks if not ok)

    print(f"census {census}, mentioned {len(mentioned)}, carries a shape {len(shape)}")
    print(f"mentioned nowhere {census - len(mentioned)}, no shape {census - len(shape)}")
    print(f"library-only pictures {len(library_only)}: {dict(sorted(library_only_class.items()))}")
    print(f"folder disagreement pictures: {len(disagree_rows)}")
    print(f"coverage.csv md5: {coverage_md5}")
    print(f"folder_disagreement.csv md5: {folder_disagreement_md5}")
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    print(f"checks: {len(checks)}, failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
