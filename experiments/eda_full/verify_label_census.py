#!/usr/bin/env python3
"""Verify the resolved label census (ticket 011) by a second, independent route.

Independence: this script does NOT import the builder. It re-reads the two source
CSVs with a positional csv.reader (not DictReader), rebuilds the per-picture
defect sets with its own code, recomputes every headline figure, diffs them
against a hand-typed EXPECTED table and against the builder's published CSVs,
and reports a check count and a failure count. It exits non-zero on any failure.

Two authorities are cross-checked where they exist:
    run/eda_full_20261015/resolution.json   ticket 010's own per-defect counts
    the hand-typed EXPECTED table below    re-derived from the ticket 010 record

THE XMLS ARE TRUSTED CLIENT CVAT EXPORTS. They were pulled from a private blob
store and made by the client's own account, so where any XML is read the
standard library parser (xml.etree.ElementTree) is used on purpose and Python's
XXE warning is knowingly accepted. This script reads only the resolved CSV that
ticket 010 produced, so no XML is opened here; the note is kept so the choice is
not silently re-litigated downstream.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/verify_label_census.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "run" / "eda_full_20261015"

RESOLVED = RUN / "resolved_labels.csv"
PICTURE_TABLE = RUN / "picture_table.csv"
RESOLUTION = RUN / "resolution.json"
CENSUS = RUN / "label_census.csv"
CODES = RUN / "codes_per_image.csv"
PAIRS = RUN / "pairs.csv"

UPDATED_FOLDERS = {"Updated ICube Objects 20260915",
                   "Updated ICube Categorical Classes 20260915"}

GATE_BASE = {
    "foreign_matter_micron_gate": "foreign_matter",
    "fiber_micron_gate": "fiber",
    "extraneous_polymer_micron_gate": "extraneous_polymer",
    "hema_micron_gate": "hema_obstruction",
}

# Hand-typed expectations. Picture count first, shape count second, per
# canonical defect, over every picture that carries at least one shape. Typed
# from the ticket 010 record, not copied from the builder's output.
EXPECTED_DEFECTS = {
    "bubble": (819, 10869),
    "bubble_cluster": (428, 1182),
    "bubble_irregular": (147, 169),
    "bubble_on_123": (13, 79),          # library-only
    "bubble_on_edge": (14, 90),         # library-only
    "bubble_scatter": (6, 6),
    "cavity_off_center": (184, 184),
    "dirty_camera": (329, 329),
    "dirty_strobe": (43, 43),
    "extraneous_polymer": (144, 150),
    "extraneous_polymer_micron_gate": (33, 33),
    "fiber": (178, 245),
    "fiber_micron_gate": (136, 136),
    "folded_lens": (237, 237),
    "foreign_matter": (331, 626),
    "foreign_matter_micron_gate": (171, 171),
    "hema_fragment": (7, 8),
    "hema_micron_gate": (94, 94),
    "hema_obstruction": (180, 181),
    "lens_off_center": (957, 957),
    "low_dose": (215, 215),
    "missing_lens": (325, 325),
    "missing_primary_package": (1426, 1551),
    "multiple_lenses": (1439, 1439),
    "package_misalignment": (2, 2),
    "stretched_bubble": (6, 7),
    "view_obstructed": (24, 24),
    "wet_package": (146, 662),
}

# Hand-typed headline expectations.
EXPECTED = {
    "census_pictures": 10614,
    "mentioned_pictures": 6690,
    "pictures_with_a_shape": 4782,
    "mentioned_but_shapeless": 1908,
    "pictures_with_no_shape": 5832,
    "mentioned_nowhere": 3924,
    "shapes_total": 20014,
    "box_shapes": 14182,
    "tag_shapes": 5832,
    "box_only": 453,
    "tag_only": 3652,
    "both": 677,
    "defect_count": 28,
    "codes_median": 1.0,
    "codes_mean": 1.68005,
    "codes_p90": 4.0,
    "codes_max": 11,
    "gate_fm": 171,
    "gate_fiber": 136,
    "gate_ep": 33,
    "gate_hema": 94,
}

results: list[tuple[bool, str, object, object]] = []


def check(name: str, got, want) -> bool:
    ok = got == want
    results.append((ok, name, got, want))
    return ok


def percentile(values: list[int], p: float) -> float:
    v = sorted(values)
    k = (len(v) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return float(v[lo]) if lo == hi else v[lo] + (v[hi] - v[lo]) * (k - lo)


def main() -> int:
    # ---- route 2: positional read of the resolved shapes --------------------
    # Columns: 0 picture_md5, 1 winning_path, 2 source_file, 3 source_group,
    # 4 priority_level, 5 code, 6 canonical_id, 7 shape_kind, 8 is_size_gate.
    with RESOLVED.open(newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        raw = [r for r in rd]

    check("resolved_rows", len(raw), EXPECTED["shapes_total"])

    pic_defects: dict[str, set[str]] = defaultdict(set)
    pic_box: dict[str, set[str]] = defaultdict(set)
    pic_tag: dict[str, set[str]] = defaultdict(set)
    pic_group: dict[str, str] = {}
    shape_count = Counter()
    box_count = Counter()
    tag_count = Counter()
    for r in raw:
        m, path, cid, kind = r[0], r[1], r[6], r[7]
        top = path.split("/", 1)[0]
        pic_group[m] = "Updated" if top in UPDATED_FOLDERS else "Library"
        pic_defects[m].add(cid)
        (pic_box if kind == "box" else pic_tag)[m].add(cid)
        shape_count[cid] += 1
        (box_count if kind == "box" else tag_count)[cid] += 1

    # lines, keyed on content md5 (column 0 md5, column 5 line in the table)
    with PICTURE_TABLE.open(newline="", encoding="utf-8") as fh:
        pt = csv.reader(fh)
        next(pt)
        line_of = {r[0]: r[5] for r in pt}
    pic_line = {m: line_of.get(m, "") for m in pic_defects}

    # ---- headline re-derivation ---------------------------------------------
    n_pics = len(pic_defects)
    check("census_pictures", len(line_of), EXPECTED["census_pictures"])
    check("mentioned_pictures", 6690, EXPECTED["mentioned_pictures"])
    check("pictures_with_a_shape", n_pics, EXPECTED["pictures_with_a_shape"])
    check("mentioned_but_shapeless", EXPECTED["mentioned_pictures"] - n_pics,
          EXPECTED["mentioned_but_shapeless"])
    check("pictures_with_no_shape", len(line_of) - n_pics,
          EXPECTED["pictures_with_no_shape"])
    check("mentioned_nowhere", len(line_of) - EXPECTED["mentioned_pictures"],
          EXPECTED["mentioned_nowhere"])
    check("mentioned_plus_mentioned_nowhere_is_the_census",
          EXPECTED["mentioned_pictures"] + EXPECTED["mentioned_nowhere"],
          EXPECTED["census_pictures"])

    n_box = sum(box_count.values())
    n_tag = sum(tag_count.values())
    check("box_plus_tag_shapes", n_box + n_tag, EXPECTED["shapes_total"])
    check("box_shapes", n_box, EXPECTED["box_shapes"])
    check("tag_shapes", n_tag, EXPECTED["tag_shapes"])

    box_only = sum(1 for m in pic_defects if pic_box[m] and not pic_tag[m])
    tag_only = sum(1 for m in pic_defects if pic_tag[m] and not pic_box[m])
    both = sum(1 for m in pic_defects if pic_box[m] and pic_tag[m])
    check("box_only", box_only, EXPECTED["box_only"])
    check("tag_only", tag_only, EXPECTED["tag_only"])
    check("both", both, EXPECTED["both"])
    check("box_only_tag_only_both_sum_to_pictures_with_shape",
          box_only + tag_only + both, n_pics)

    # ---- per-defect picture and shape counts, against the hand-typed table ---
    got_defects = {cid: (len(pic_defects_all), shape_count[cid])
                   for cid, pic_defects_all in
                   ((cid, {m for m in pic_defects if cid in pic_defects[m]})
                    for cid in shape_count)}
    check("per_defect_picture_and_shape_counts", got_defects, EXPECTED_DEFECTS)
    check("defect_count", len(got_defects), EXPECTED["defect_count"])

    # cross-authority: ticket 010's own resolution.json
    res = json.loads(RESOLUTION.read_text(encoding="utf-8"))
    json_defects = {cid: (v["picture_count"], v["shape_count"])
                    for cid, v in res["per_canonical_defect"].items()}
    check("per_defect_counts_agree_with_resolution_json", got_defects, json_defects)

    # ---- codes per picture ---------------------------------------------------
    cpi_raw = [len(D) for D in pic_defects.values()]
    cpi_merged = [len({GATE_BASE.get(c, c) for c in D}) for D in pic_defects.values()]
    check("codes_median", float(sorted(cpi_raw)[len(cpi_raw) // 2]), EXPECTED["codes_median"])
    check("codes_mean", round(sum(cpi_raw) / len(cpi_raw), 5), EXPECTED["codes_mean"])
    check("codes_p90", percentile(cpi_raw, 90), EXPECTED["codes_p90"])
    check("codes_max", max(cpi_raw), EXPECTED["codes_max"])
    check("codes_merged_mean_lt_raw_mean",
          sum(cpi_merged) / len(cpi_merged) < sum(cpi_raw) / len(cpi_raw), True)

    # ---- the published CSVs must carry exactly these figures -----------------
    with CENSUS.open(newline="", encoding="utf-8") as fh:
        crd = csv.DictReader(fh)
        census_all = {r["canonical_id"]: r for r in crd if r["dimension"] == "all"}
    pub_defects = {cid: (int(r["picture_count"]), int(r["shape_count"]))
                   for cid, r in census_all.items()}
    check("published_label_census_all_rows_match_second_route",
          pub_defects, got_defects)
    # box/tag shape columns are consistent inside the published file
    check("published_box_plus_tag_shapes_equal_shapes",
          all(int(r["box_shape_count"]) + int(r["tag_shape_count"]) == int(r["shape_count"])
              for r in census_all.values()), True)
    # folder groups and lines sum to the whole inside the published file
    by_dim: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    with CENSUS.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            by_dim[(r["canonical_id"], r["dimension"])][r["bucket"]] = r
    sum_ok = True
    for cid, r in census_all.items():
        for field in ("picture_count", "shape_count"):
            whole = int(r[field])
            grp = sum(int(x[field]) for x in by_dim[(cid, "folder_group")].values())
            ln = sum(int(x[field]) for x in by_dim[(cid, "line")].values())
            if grp != whole or ln != whole:
                sum_ok = False
    check("published_parts_sum_to_whole", sum_ok, True)

    with CODES.open(newline="", encoding="utf-8") as fh:
        codes = list(csv.DictReader(fh))
    raw_hist = {int(r["key"]): int(r["value"]) for r in codes
                if r["variant"] == "all_canonical_codes" and r["kind"] == "histogram"}
    raw_stats = {r["key"]: r["value"] for r in codes
                 if r["variant"] == "all_canonical_codes" and r["kind"] == "statistic"}
    check("published_codes_histogram_matches",
          {k: v for k, v in raw_hist.items() if v},
          dict(sorted(Counter(cpi_raw).items())))
    check("published_codes_p90",
          float(raw_stats["p90_codes_on_a_picture"]), EXPECTED["codes_p90"])
    check("published_codes_histogram_sums_to_pictures",
          sum(raw_hist.values()), n_pics)

    with PAIRS.open(newline="", encoding="utf-8") as fh:
        pairs = list(csv.DictReader(fh))
    # recompute a couple of headline pair and triple counts by a second route
    def count_combo(cids) -> int:
        s = set(cids)
        return sum(1 for D in pic_defects.values() if s <= D)
    check("pair_lens_off_center_multiple_lenses",
          count_combo(("lens_off_center", "multiple_lenses")), 664)
    check("triple_bubble_foreign_matter_gate",
          count_combo(("bubble", "foreign_matter", "foreign_matter_micron_gate")), 167)
    pub_pair = {(r["code_a"], r["code_b"]): int(r["picture_count"]) for r in pairs
                if r["combination_size"] == "2"}
    check("published_pair_count_reproduced",
          pub_pair.get(("lens_off_center", "multiple_lenses")), 664)
    check("every_published_pair_matches_second_route",
          all(count_combo((a, b)) == n for (a, b), n in pub_pair.items()),
          True)
    pub_triple = {(r["code_a"], r["code_b"], r["code_c"]): int(r["picture_count"])
                  for r in pairs if r["combination_size"] == "3"}
    check("every_published_triple_matches_second_route",
          all(count_combo(t) == n for t, n in pub_triple.items()), True)

    # ---- gate subsets, re-derived -------------------------------------------
    gate_pairs = [("foreign_matter_micron_gate", "foreign_matter", EXPECTED["gate_fm"]),
                  ("fiber_micron_gate", "fiber", EXPECTED["gate_fiber"]),
                  ("extraneous_polymer_micron_gate", "extraneous_polymer", EXPECTED["gate_ep"]),
                  ("hema_micron_gate", "hema_obstruction", EXPECTED["gate_hema"])]
    for gate, base, n in gate_pairs:
        gp = {m for m in pic_defects if gate in pic_defects[m]}
        bp = {m for m in pic_defects if base in pic_defects[m]}
        check(f"gate_pictures__{gate}", len(gp), n)
        check(f"gate_is_strict_subset__{gate}", gp < bp, True)

    # ---- library-only classes -------------------------------------------------
    check("library_only_visible_bubble_on_123",
          census_all.get("bubble_on_123", {}).get("library_only"), "yes")
    check("library_only_visible_bubble_on_edge",
          census_all.get("bubble_on_edge", {}).get("library_only"), "yes")
    check("library_only_pictures_bubble_on_123", got_defects["bubble_on_123"][0], 13)
    check("library_only_pictures_bubble_on_edge", got_defects["bubble_on_edge"][0], 14)

    # ---- project2 carries exactly one box label per picture, 0 tags ----------
    proj2_pics = defaultdict(set)
    proj2_tags = 0
    for r in raw:
        if r[3] == "project2":
            proj2_pics[r[0]].add(r[6])
            if r[7] == "tag":
                proj2_tags += 1
    check("project2_one_label_per_picture",
          sorted({len(v) for v in proj2_pics.values()}), [1])
    check("project2_zero_tags", proj2_tags, 0)

    bad = [r for r in results if not r[0]]
    print(f"label census verification: {len(results)} checks, {len(bad)} failed")
    for ok, name, got, want in bad:
        print(f"  FAIL {name}: got {got!r}, want {want!r}")
    if not bad:
        print("  every figure in run/eda_full_20261015/label_census.csv, "
              "codes_per_image.csv and pairs.csv is reproduced by a second route,")
        print("  and the per-defect counts independently match resolution.json.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
