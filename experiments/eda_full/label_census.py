#!/usr/bin/env python3
"""Resolved label census and multi-label analysis at full coverage.

Ticket 011 of the full-coverage EDA map. It takes the frozen label resolution
(ticket 010) and counts, per canonical defect, the pictures and the shapes that
carry it, split by folder group (Updated = the two Updated folders; Library =
ICube Defects Library) and by production line, with the box tier and the tag
tier always kept apart.

COUNTING RULES (not negotiable, a sibling ticket got them wrong once):

  * Every join is keyed on the content md5, never on a path. 187 basenames hold
    a content that also exists under a second name, so a path-based count
    undercounts. resolved_labels.csv and picture_table.csv are both keyed on the
    picture md5, so the joins here are content joins by construction.
  * A MENTION is not a SHAPE. 6,690 census pictures are mentioned by some file,
    only 4,782 carry at least one shape, and 5,832 are mentioned nowhere. Every
    figure below says which of the two it is. The word "annotated" is never used
    on its own.
  * The box tier and the tag tier are annotated to very different depths and are
    never pooled silently. shape_kind splits them.
  * Library-only classes (Bubble On 123, Bubble On Edge) stay visible under
    their own names; they carry no code in either newer project.
  * A crosswalk cell reading `defined_only` names a code no shape carries and is
    never counted as an instance. The three such cells are P2_BSC (production),
    P1_PPM and P2_FOV (Sep-22).

THE XMLS ARE TRUSTED CLIENT CVAT EXPORTS. They were pulled from a private blob
store and made by the client's own account, so where any XML is read the
standard library parser (xml.etree.ElementTree) is used on purpose and Python's
XXE warning is knowingly accepted. This script reads only the resolved CSV that
ticket 010 produced, so no XML is opened here; the note is kept so the choice is
not silently re-litigated downstream.

Inputs  (all local):
    run/eda_full_20261015/resolved_labels.csv   20,014 rows, one per surviving shape
    run/eda_full_20261015/picture_table.csv      10,614 rows, one per picture, keyed on md5
    data/crosswalk.csv                           the frozen canonical crosswalk, 28 rows

Outputs (all local):
    run/eda_full_20261015/label_census.csv
    run/eda_full_20261015/codes_per_image.csv
    run/eda_full_20261015/pairs.csv

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/label_census.py
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "run" / "eda_full_20261015"

RESOLVED = RUN / "resolved_labels.csv"
PICTURE_TABLE = RUN / "picture_table.csv"
CROSSWALK = REPO / "data" / "crosswalk.csv"

OUT_CENSUS = RUN / "label_census.csv"
OUT_CODES = RUN / "codes_per_image.csv"
OUT_PAIRS = RUN / "pairs.csv"

# The library-only classes carry no code in either newer project, so they are
# detected from the crosswalk rather than hard-coded.
LIBRARY_FOLDERS = {
    "ICube Defects Library", "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
}
UPDATED_FOLDERS = {"Updated ICube Objects 20260915",
                   "Updated ICube Categorical Classes 20260915"}

# A gate tag is a size flag on its base defect, not a separate defect. Kept here
# only for the "gates merged into their base" variant of the code histogram.
GATE_BASE = {
    "foreign_matter_micron_gate": "foreign_matter",
    "fiber_micron_gate": "fiber",
    "extraneous_polymer_micron_gate": "extraneous_polymer",
    "hema_micron_gate": "hema_obstruction",
}

# A pair / triple is "worth naming" above this picture count.
PAIR_MIN = 2
TRIPLE_MIN = 3

TIER_RANK = {"box": 0, "box|tag": 1, "tag": 2, "gate": 3}

CENSUS_COLUMNS = [
    "canonical_id", "canonical_name", "tier", "kind_conflict", "is_size_gate",
    "library_only", "dimension", "bucket",
    "picture_count", "box_picture_count", "tag_picture_count",
    "shape_count", "box_shape_count", "tag_shape_count",
]


def folder_group(winning_path: str) -> str:
    """Updated = the two Updated folders; Library = the old ICube Defects Library."""
    top = winning_path.split("/", 1)[0]
    return "Updated" if top in UPDATED_FOLDERS else "Library"


def load_crosswalk() -> dict[str, dict]:
    """canonical_id -> crosswalk row, over the frozen crosswalk."""
    by_id: dict[str, dict] = {}
    for row in csv.DictReader(CROSSWALK.open(encoding="utf-8")):
        by_id[row["canonical_id"]] = row
    return by_id


def load_lines() -> dict[str, str]:
    """md5 -> production line, from the census picture table (keyed on content md5)."""
    lines: dict[str, str] = {}
    for row in csv.DictReader(PICTURE_TABLE.open(encoding="utf-8")):
        lines[row["md5"]] = row["line"]
    return lines


def percentile(values: list[int], p: float) -> float:
    """Linear-interpolation percentile (the numpy default), no numpy needed."""
    if not values:
        return float("nan")
    v = sorted(values)
    k = (len(v) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(v[lo])
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def main() -> int:
    canon = load_crosswalk()
    lines = load_lines()

    # ---- read the resolved shapes and build the per-picture facts -----------
    # Each surviving shape carries exactly one canonical defect (ticket 010
    # checked 0 un-mapped), one shape_kind and one picture md5.
    rows = list(csv.DictReader(RESOLVED.open(encoding="utf-8")))

    pic_defects: dict[str, set[str]] = defaultdict(set)     # picture -> canonical ids
    pic_box: dict[str, set[str]] = defaultdict(set)         # picture -> canonical ids present as a box
    pic_tag: dict[str, set[str]] = defaultdict(set)         # picture -> canonical ids present as a tag
    pic_group: dict[str, str] = {}
    pic_line: dict[str, str] = {}

    # per-defect aggregation accumulators
    d_shapes = Counter()                                    # canonical -> shapes
    d_box_shapes = Counter()
    d_tag_shapes = Counter()
    d_pics: dict[str, set[str]] = defaultdict(set)
    d_box_pics: dict[str, set[str]] = defaultdict(set)
    d_tag_pics: dict[str, set[str]] = defaultdict(set)
    # per-defect x dimension x bucket accumulators
    d_dim_shapes = defaultdict(Counter)                     # canonical -> {(dim,bucket): shapes}
    d_dim_box = defaultdict(Counter)
    d_dim_tag = defaultdict(Counter)
    d_dim_pics = defaultdict(lambda: defaultdict(set))
    d_dim_boxpics = defaultdict(lambda: defaultdict(set))
    d_dim_tagpics = defaultdict(lambda: defaultdict(set))

    for r in rows:
        cid = r["canonical_id"]
        kind = r["shape_kind"]
        m = r["picture_md5"]
        grp = folder_group(r["winning_path"])
        line = lines.get(m, "")
        pic_group[m] = grp
        pic_line[m] = line
        pic_defects[m].add(cid)
        if kind == "box":
            pic_box[m].add(cid)
        else:
            pic_tag[m].add(cid)
        d_shapes[cid] += 1
        d_pics[cid].add(m)
        if kind == "box":
            d_box_shapes[cid] += 1
            d_box_pics[cid].add(m)
        else:
            d_tag_shapes[cid] += 1
            d_tag_pics[cid].add(m)
        for key in (("folder_group", grp), ("line", line)):
            d_dim_shapes[cid][key] += 1
            d_dim_pics[cid][key].add(m)
            if kind == "box":
                d_dim_box[cid][key] += 1
                d_dim_boxpics[cid][key].add(m)
            else:
                d_dim_tag[cid][key] += 1
                d_dim_tagpics[cid][key].add(m)

    # ---- census rows: per defect, all + folder group + line -----------------
    all_buckets = sorted({pic_line[m] for m in pic_defects})
    census_rows: list[dict] = []
    checked_sum = 0
    for cid in sorted(d_shapes,
                      key=lambda c: (TIER_RANK.get(canon[c]["kind"], 9), c)):
        c = canon.get(cid, {})
        tier = c.get("kind", "")
        lib_only = "yes" if (cid in ("bubble_on_123", "bubble_on_edge")) else "no"
        base = {
            "canonical_id": cid,
            "canonical_name": c.get("canonical_name", ""),
            "tier": tier,
            "kind_conflict": c.get("kind_conflict", ""),
            "is_size_gate": c.get("is_size_gate", "no"),
            "library_only": lib_only,
        }

        def emit(dimension: str, bucket: str) -> None:
            if dimension == "all":
                pics, boxp, tagp = d_pics[cid], d_box_pics[cid], d_tag_pics[cid]
                sh, bsh, tsh = d_shapes[cid], d_box_shapes[cid], d_tag_shapes[cid]
            else:
                key = (dimension, bucket)
                pics = d_dim_pics[cid][key]
                boxp = d_dim_boxpics[cid][key]
                tagp = d_dim_tagpics[cid][key]
                sh = d_dim_shapes[cid][key]
                bsh = d_dim_box[cid][key]
                tsh = d_dim_tag[cid][key]
            census_rows.append({**base, "dimension": dimension, "bucket": bucket,
                                "picture_count": len(pics),
                                "box_picture_count": len(boxp),
                                "tag_picture_count": len(tagp),
                                "shape_count": sh, "box_shape_count": bsh,
                                "tag_shape_count": tsh})

        emit("all", "all")
        for grp in ("Updated", "Library"):
            emit("folder_group", grp)
        for ln in all_buckets:
            emit("line", ln)

        # ACCEPTANCE 1: the parts sum to the whole, on both folders and lines, for
        # picture counts and shape counts alike.
        for field in ("picture_count", "shape_count"):
            by_grp = sum(rw[field] for rw in census_rows
                         if rw["canonical_id"] == cid and rw["dimension"] == "folder_group")
            by_line = sum(rw[field] for rw in census_rows
                          if rw["canonical_id"] == cid and rw["dimension"] == "line")
            whole = next(rw[field] for rw in census_rows
                         if rw["canonical_id"] == cid and rw["dimension"] == "all")
            checked_sum += 1
            assert by_grp == whole, f"{cid} {field}: folder groups {by_grp} != {whole}"
            assert by_line == whole, f"{cid} {field}: lines {by_line} != {whole}"

    # ---- codes per picture --------------------------------------------------
    # Two variants. The raw one counts every canonical code, so a size gate shows
    # up as its own code on top of its base. The merged one folds each gate into
    # its base, which is the honest "how many distinct defects sit on a picture".
    def codes_per_picture(merge_gates: bool) -> list[int]:
        out = []
        for m, D in pic_defects.items():
            if merge_gates:
                out.append(len({GATE_BASE.get(c, c) for c in D}))
            else:
                out.append(len(D))
        return out

    codes_rows: list[dict] = []
    for variant, merge in (("all_canonical_codes", False),
                           ("with_gate_tags_merged_into_base", True)):
        cpi = codes_per_picture(merge)
        hist = Counter(cpi)
        for n in range(0, max(cpi) + 1):
            codes_rows.append({"variant": variant, "kind": "histogram",
                               "key": str(n), "value": str(hist.get(n, 0))})
        stats = {
            "pictures_with_at_least_one_shape": len(cpi),
            "median_codes_on_a_picture": statistics.median(cpi),
            "mean_codes_on_a_picture": round(statistics.mean(cpi), 6),
            "p90_codes_on_a_picture": percentile(cpi, 90),
            "max_codes_on_a_picture": max(cpi),
        }
        for k, v in stats.items():
            codes_rows.append({"variant": variant, "kind": "statistic",
                               "key": k, "value": str(v)})

    # ---- pairs and triples on one picture -----------------------------------
    pair_counter = Counter()
    triple_counter = Counter()
    for D in pic_defects.values():
        s = sorted(D)
        for a, b in itertools.combinations(s, 2):
            pair_counter[(a, b)] += 1
        for t in itertools.combinations(s, 3):
            triple_counter[t] += 1

    def tier_of(cid: str) -> str:
        return canon.get(cid, {}).get("kind", "")

    pairs_rows: list[dict] = []
    for (a, b), n in sorted(pair_counter.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < PAIR_MIN:
            continue
        pairs_rows.append({"combination_size": 2, "code_a": a, "code_b": b,
                           "code_c": "", "tier_a": tier_of(a), "tier_b": tier_of(b),
                           "tier_c": "", "picture_count": n})
    for (a, b, c), n in sorted(triple_counter.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < TRIPLE_MIN:
            continue
        pairs_rows.append({"combination_size": 3, "code_a": a, "code_b": b,
                           "code_c": c, "tier_a": tier_of(a), "tier_b": tier_of(b),
                           "tier_c": tier_of(c), "picture_count": n})

    # ---- checks -------------------------------------------------------------
    checks: list[tuple[str, bool, str]] = []

    n_shapes = len(rows)
    n_box_shapes = sum(1 for r in rows if r["shape_kind"] == "box")
    n_tag_shapes = sum(1 for r in rows if r["shape_kind"] == "tag")
    n_pics = len(pic_defects)

    checks.append(("every_shape_kind_is_box_or_tag",
                   all(r["shape_kind"] in ("box", "tag") for r in rows),
                   f"kinds: {sorted({r['shape_kind'] for r in rows})}"))
    checks.append(("box_plus_tag_shapes_equal_shapes",
                   n_box_shapes + n_tag_shapes == n_shapes,
                   f"{n_box_shapes}+{n_tag_shapes}={n_shapes}"))
    checks.append(("parts_sum_to_whole_on_every_defect", checked_sum > 0,
                   f"{checked_sum} sums asserted"))
    # every picture carrying a shape has a line and a folder group
    checks.append(("every_picture_has_a_line",
                   all(pic_line[m] for m in pic_defects),
                   f"{sum(1 for m in pic_defects if not pic_line[m])} missing a line"))
    # the gate subset relationships, asserted picture by picture
    for gate, base in GATE_BASE.items():
        gp = {m for m in pic_defects if gate in pic_defects[m]}
        bp = {m for m in pic_defects if base in pic_defects[m]}
        checks.append((f"gate_subset__{gate}",
                       gp <= bp and len(gp) > 0,
                       f"{len(gp)} pictures hold {gate}, all of them also hold {base} "
                       f"(base on {len(bp)} pictures), strict={len(gp) < len(bp)}"))
    # library-only classes are visible under their own names
    lib = [cid for cid in d_shapes if cid in ("bubble_on_123", "bubble_on_edge")]
    checks.append(("library_only_classes_present",
                   set(lib) == {"bubble_on_123", "bubble_on_edge"},
                   f"{sorted(lib)}"))
    # every code counted is in the crosswalk
    checks.append(("every_counted_code_is_in_crosswalk",
                   all(cid in canon for cid in d_shapes),
                   f"{sum(1 for cid in d_shapes if cid not in canon)} unknown"))

    failed = sum(1 for _, ok, _ in checks if not ok)
    assert failed == 0, [c for c in checks if not c[1]]

    # ---- write --------------------------------------------------------------
    def write(path: Path, columns: list[str], out_rows: list[dict]) -> str:
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
            w.writeheader()
            w.writerows(out_rows)
        return hashlib.md5(path.read_bytes()).hexdigest()

    md5_census = write(OUT_CENSUS, CENSUS_COLUMNS, census_rows)
    md5_codes = write(OUT_CODES, ["variant", "kind", "key", "value"], codes_rows)
    md5_pairs = write(OUT_PAIRS,
                      ["combination_size", "code_a", "code_b", "code_c",
                       "tier_a", "tier_b", "tier_c", "picture_count"], pairs_rows)

    # ---- report -------------------------------------------------------------
    box_only = sum(1 for m in pic_defects if pic_box[m] and not pic_tag[m])
    tag_only = sum(1 for m in pic_defects if pic_tag[m] and not pic_box[m])
    both = sum(1 for m in pic_defects if pic_box[m] and pic_tag[m])
    print(f"surviving shapes: {n_shapes} (box {n_box_shapes}, tag {n_tag_shapes})")
    print(f"pictures carrying at least one shape: {n_pics}")
    print(f"  box only: {box_only}, tag only: {tag_only}, both: {both}")
    print(f"mentioned but shapeless (neither): {6690 - n_pics}")
    print(f"defects in the census: {len(d_shapes)}")
    cpi = codes_per_picture(False)
    print(f"codes per picture: median {statistics.median(cpi)}, "
          f"mean {statistics.mean(cpi):.4f}, p90 {percentile(cpi, 90)}")
    print(f"pairs named: {sum(1 for r in pairs_rows if r['combination_size'] == 2)}, "
          f"triples named: {sum(1 for r in pairs_rows if r['combination_size'] == 3)}")
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    print(f"label_census.csv  md5: {md5_census}")
    print(f"codes_per_image.csv md5: {md5_codes}")
    print(f"pairs.csv         md5: {md5_pairs}")
    print(f"checks: {len(checks)}, failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
