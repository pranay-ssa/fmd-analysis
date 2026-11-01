#!/usr/bin/env python3
"""Independent verifier for ticket 015 coverage.

Second route. Every headline count is re-derived here from the inputs with a
different parser and a different join than the builder, then compared with both
hand-typed expected values and the builder's own coverage.csv. Disagreement is a
failure, not a warning.

Differences from the builder's route:
- the XML files are parsed with iterparse, not ElementTree.parse;
- the mention set is built basename -> md5 from the manifest in one pass;
- the per-folder, per-group and per-line numbers are recomputed from scratch and
  diffed against coverage.csv row by row;
- the folder-label disagreement is re-derived three ways, by content and by name,
  over the whole library and over the production batch, and all three are typed.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/verify_coverage.py
"""

from __future__ import annotations

import csv
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
COVERAGE_CSV = RUN / "coverage.csv"
FOLDER_DISAGREEMENT_CSV = RUN / "folder_disagreement.csv"

XML_FILES = [f"annotations_45219{n}.xml" for n in range(40, 47)] + [
    "Updated Annotations 20260922.xml", "annotations.xml",
]

LIBRARY_FOLDERS = (
    "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
    "ICube Defects Library",
)
GROUP_OF = {
    "Updated ICube Objects 20260915": "Updated",
    "Updated ICube Categorical Classes 20260915": "Updated",
    "ICube Defects Library": "Library",
}
PROD_FOLDER = "PRODUCTION_20260925/images"
NOT_A_CLASS = {"duplicates"}

# Hand-typed expected values, written from the ticket and the map, not read back.
EXPECTED = {
    "census": 10614,
    "mentioned": 6690,
    "shape": 4782,
    "mentioned_nowhere": 3924,
    "no_shape": 5832,
    "folder_objects": 4230,
    "folder_categorical": 6207,
    "folder_library": 177,
    "group_updated": 10437,
    "group_library": 177,
    "line_L24": 4348,
    "line_L25": 972,
    "line_L26": 1503,
    "line_L27": 1637,
    "line_L31": 2154,
    "library_only_total": 177,
    "production_files": 1047,
    "production_distinct_contents": 1046,
    "blob_folder_total": 10438,
    "disagreement_content_all": 279,
    "disagreement_content_batch": 129,
    "disagreement_name_batch": 114,
    "disagreement_published": 113,
}

# Hand-typed library-only class breakdown, from the census record and ticket 007.
EXPECTED_LIB_ONLY_CLASS = {
    "Bubble": 72, "Bubble Irregular": 26, "Wet Package": 27, "Bubble On 123": 14,
    "Bubble Cluster": 21, "Bubble On Edge": 14, "Dirty Strobe": 1, "Fiber": 1,
    "Bubble Scatter": 1,
}

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str = "") -> None:
    checks.append((name, ok, note))


def bn(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def cls(path: str) -> str:
    parts = path.split("/")
    return parts[1] if len(parts) > 2 else "<root>"


def main() -> int:
    # --- route A: manifest, one pass -----------------------------------------
    md5s: set[str] = set()
    by_basename: dict[str, set[str]] = defaultdict(set)
    md5_fc: dict[str, set[tuple[str, str]]] = defaultdict(set)
    md5_folders: dict[str, set[str]] = defaultdict(set)
    prod_md5: set[str] = set()
    prod_files = 0
    with FILE_MANIFEST.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            md5 = row["md5"]
            md5s.add(md5)
            by_basename[bn(row["path"])].add(md5)
            md5_fc[md5].add((row["folder"], cls(row["path"])))
            md5_folders[md5].add(row["folder"])
            if row["folder"] == PROD_FOLDER:
                prod_files += 1
                prod_md5.add(md5)

    check("census_matches_expected", len(md5s) == EXPECTED["census"],
          f"{len(md5s)} vs {EXPECTED['census']}")

    # --- route A: picture table ----------------------------------------------
    table: dict[str, dict[str, str]] = {}
    with PICTURE_TABLE.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[row["md5"]] = {"winning_path": row["winning_path"], "line": row["line"],
                                 "in_production_batch": row["in_production_batch"]}
    check("picture_table_keys_equal_manifest", set(table) == md5s,
          f"symdiff {len(set(table) ^ md5s)}")

    # --- route A: mentions by iterparse --------------------------------------
    mentioned: set[str] = set()
    for fname in XML_FILES:
        for event, elem in ET.iterparse(DATA / fname, events=("end",)):
            if elem.tag == "image":
                ids = by_basename.get(bn(elem.get("name") or ""))
                if ids:
                    mentioned |= ids
                elem.clear()
    check("mentioned_matches_expected", len(mentioned) == EXPECTED["mentioned"],
          f"{len(mentioned)} vs {EXPECTED['mentioned']}")

    # --- route A: shape set from resolved labels ------------------------------
    shape: set[str] = set()
    with RESOLVED.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            shape.add(row["picture_md5"])
    check("shape_matches_expected", len(shape) == EXPECTED["shape"],
          f"{len(shape)} vs {EXPECTED['shape']}")
    check("mentioned_nowhere_matches_expected",
          len(md5s - mentioned) == EXPECTED["mentioned_nowhere"],
          f"{len(md5s - mentioned)} vs {EXPECTED['mentioned_nowhere']}")
    check("no_shape_matches_expected", len(md5s - shape) == EXPECTED["no_shape"],
          f"{len(md5s - shape)} vs {EXPECTED['no_shape']}")
    check("shape_subset_of_mentioned", shape <= mentioned,
          f"{len(shape - mentioned)} shape not mentioned")

    # --- route A: strata recomputed ------------------------------------------
    folder_pop: dict[str, set[str]] = defaultdict(set)
    group_pop: dict[str, set[str]] = defaultdict(set)
    line_pop: dict[str, set[str]] = defaultdict(set)
    for m in md5s:
        f = table[m]["winning_path"].split("/")[0]
        folder_pop[f].add(m)
        group_pop[GROUP_OF[f]].add(m)
        line_pop[table[m]["line"]].add(m)

    check("folder_objects", len(folder_pop["Updated ICube Objects 20260915"]) == EXPECTED["folder_objects"],
          f"{len(folder_pop['Updated ICube Objects 20260915'])}")
    check("folder_categorical",
          len(folder_pop["Updated ICube Categorical Classes 20260915"]) == EXPECTED["folder_categorical"],
          f"{len(folder_pop['Updated ICube Categorical Classes 20260915'])}")
    check("folder_library", len(folder_pop["ICube Defects Library"]) == EXPECTED["folder_library"],
          f"{len(folder_pop['ICube Defects Library'])}")
    check("group_updated", len(group_pop["Updated"]) == EXPECTED["group_updated"],
          f"{len(group_pop['Updated'])}")
    check("group_library", len(group_pop["Library"]) == EXPECTED["group_library"],
          f"{len(group_pop['Library'])}")
    for ln, want in (("L24", EXPECTED["line_L24"]), ("L25", EXPECTED["line_L25"]),
                     ("L26", EXPECTED["line_L26"]), ("L27", EXPECTED["line_L27"]),
                     ("L31", EXPECTED["line_L31"])):
        check(f"line_{ln}", len(line_pop[ln]) == want, f"{len(line_pop[ln])} vs {want}")

    folder_sum = sum(len(v) for v in folder_pop.values())
    group_sum = sum(len(v) for v in group_pop.values())
    line_sum = sum(len(v) for v in line_pop.values())
    check("folders_sum_to_census", folder_sum == EXPECTED["census"], f"{folder_sum}")
    check("groups_sum_to_census", group_sum == EXPECTED["census"], f"{group_sum}")
    check("lines_sum_to_census", line_sum == EXPECTED["census"], f"{line_sum}")

    # --- route B: diff against coverage.csv ----------------------------------
    cov: dict[tuple[str, str], dict[str, str]] = {}
    with COVERAGE_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cov[(row["stratum_type"], row["stratum_value"])] = row

    def recompute(pop: set[str]):
        return {"distinct_pictures": len(pop), "pictures_mentioned": len(pop & mentioned),
                "pictures_with_shape": len(pop & shape)}

    cov_ok = True
    detail = []
    for f in LIBRARY_FOLDERS:
        want = recompute(folder_pop[f])
        got = cov.get(("folder", f), {})
        if not got or int(got["distinct_pictures"]) != want["distinct_pictures"] \
                or int(got["pictures_mentioned"]) != want["pictures_mentioned"] \
                or int(got["pictures_with_shape"]) != want["pictures_with_shape"]:
            cov_ok = False
            detail.append(f"folder {f}")
    for g in ("Updated", "Library"):
        want = recompute(group_pop[g])
        got = cov.get(("folder_group", g), {})
        if not got or int(got["distinct_pictures"]) != want["distinct_pictures"] \
                or int(got["pictures_with_shape"]) != want["pictures_with_shape"]:
            cov_ok = False
            detail.append(f"group {g}")
    for ln in ("L24", "L25", "L26", "L27", "L31"):
        want = recompute(line_pop[ln])
        got = cov.get(("production_line", ln), {})
        if not got or int(got["distinct_pictures"]) != want["distinct_pictures"] \
                or int(got["pictures_with_shape"]) != want["pictures_with_shape"]:
            cov_ok = False
            detail.append(f"line {ln}")
    check("coverage_csv_matches_second_route", cov_ok, "; ".join(detail) or "all folder/group/line rows agree")

    # ratio sanity: shape_coverage_ratio equals with_shape / distinct for the
    # partitioning rows.
    ratio_ok = True
    for (stype, _val), row in cov.items():
        if stype == "canonical_defect":
            continue
        d = int(row["distinct_pictures"])
        s = int(row["pictures_with_shape"])
        if d and abs(float(row["shape_coverage_ratio"]) - s / d) > 1e-6:
            ratio_ok = False
    check("coverage_ratios_recompute", ratio_ok, "folder/group/line ratios agree")

    # --- library-only pictures ------------------------------------------------
    library_only = {m for m in md5s if md5_folders[m] == {"ICube Defects Library"}}
    check("library_only_total", len(library_only) == EXPECTED["library_only_total"],
          f"{len(library_only)} vs {EXPECTED['library_only_total']}")
    lib_class = Counter()
    for m in library_only:
        for f, c in md5_fc[m]:
            if f == "ICube Defects Library":
                lib_class[c] += 1
    check("library_only_class_breakdown_typed", dict(lib_class) == EXPECTED_LIB_ONLY_CLASS,
          f"{dict(sorted(lib_class.items()))}")
    check("library_only_class_sums", sum(lib_class.values()) == len(library_only), "ok")

    # --- production overlap (ticket 007, restated) ----------------------------
    check("production_files", prod_files == EXPECTED["production_files"], f"{prod_files}")
    check("production_distinct_contents",
          len(prod_md5) == EXPECTED["production_distinct_contents"], f"{len(prod_md5)}")
    check("production_contents_all_in_library", prod_md5 <= md5s,
          f"{len(prod_md5 - md5s)} not in library")

    # --- blob coverage line, quoted, no pull ----------------------------------
    ratio = EXPECTED["production_files"] / EXPECTED["blob_folder_total"]
    check("blob_coverage_10_0_percent", abs(round(ratio * 100, 1) - 10.0) < 0.05,
          f"{ratio * 100:.4f} percent, quoted 10.0")

    # --- folder-label disagreement, three routes ------------------------------
    # route 1: content md5, whole library, duplicates folder dropped.
    dis_all: set[str] = set()
    for m, fcs in md5_fc.items():
        classes = {c for f, c in fcs if f in LIBRARY_FOLDERS and c not in NOT_A_CLASS}
        if len(classes) > 1:
            dis_all.add(m)
    check("disagreement_content_all", len(dis_all) == EXPECTED["disagreement_content_all"],
          f"{len(dis_all)} vs {EXPECTED['disagreement_content_all']}")
    # agreement with the builder's folder_disagreement.csv row count.
    with FOLDER_DISAGREEMENT_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    check("folder_disagreement_csv_row_count", len(rows) == len(dis_all),
          f"{len(rows)} vs {len(dis_all)}")
    check("folder_disagreement_csv_all_multi_class",
          all(int(r["distinct_class_count"]) > 1 for r in rows), "ok")

    # route 2: content md5, production batch only.
    batch = {m for m in md5s if table[m]["in_production_batch"] == "true"}
    dis_batch = {m for m in dis_all if m in batch}
    check("disagreement_content_batch", len(dis_batch) == EXPECTED["disagreement_content_batch"],
          f"{len(dis_batch)} vs {EXPECTED['disagreement_content_batch']}")

    # route 3: basename based, production batch only (the published method).
    # build basename -> classes directly from the manifest
    bn_cls: dict[str, set[str]] = defaultdict(set)
    bn_batch: dict[str, bool] = {}
    with FILE_MANIFEST.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["folder"] not in LIBRARY_FOLDERS:
                continue
            if cls(row["path"]) in NOT_A_CLASS:
                continue
            name = bn(row["path"])
            bn_cls[name].add(cls(row["path"]))
            bn_batch[name] = bn_batch.get(name, False) or (
                table.get(row["md5"], {}).get("in_production_batch") == "true")
    dis_name_batch = {n for n, cs in bn_cls.items() if len(cs) > 1 and bn_batch.get(n)}
    check("disagreement_name_batch", len(dis_name_batch) == EXPECTED["disagreement_name_batch"],
          f"{len(dis_name_batch)} vs {EXPECTED['disagreement_name_batch']}")

    # The published 113 differs from every route here; record the gap explicitly.
    check("disagreement_published_113_differs_from_rederived",
          EXPECTED["disagreement_published"] != len(dis_name_batch)
          and EXPECTED["disagreement_published"] != len(dis_batch)
          and EXPECTED["disagreement_published"] != len(dis_all),
          f"published 113; redriven content-all {len(dis_all)}, content-batch {len(dis_batch)}, "
          f"name-batch {len(dis_name_batch)}")

    # --- report ---------------------------------------------------------------
    failed = sum(1 for _n, ok, _note in checks if not ok)
    print(f"checks: {len(checks)}, failed: {failed}")
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    print(f"redriven disagreement: content-all {len(dis_all)}, content-batch {len(dis_batch)}, "
          f"name-batch {len(dis_name_batch)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
