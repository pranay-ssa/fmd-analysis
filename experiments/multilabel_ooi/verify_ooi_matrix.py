"""Verify the OOI label table independently of the builder (ticket 027).

Nothing here is read from build_ooi_matrix.py or taken on trust from it. The verifier

  * pins the frozen split file by md5 and the table's row count and key set,
  * rebuilds every class and gate column from the annotation of record using its OWN
    map, written against the raw annotation codes rather than the builder's canonical
    ids, and compares the result cell by cell,
  * asserts every count the ticket names: class 2,171 / 1,132 / 798 / 392 / 314 / 154 /
    142 / 0, gate 454 / 362 / 135 / 151, and the val/test split per class,
  * asserts gate is a subset of class on every row,
  * asserts the twelve lens columns and clear are row-for-row equal to labels_b.csv,
  * pins the HEMA exclusion: the one obstruction tag-only picture in the split is not a
    HEMA picture, and counting it would read 155 instead of 154,
  * proves the legacy bubble tags and the Surface Groove absence are real, non-vacuous
    rules,
  * then edits one cell of a copy per proof and fails unless the failure names that cell.

Run:
    .venv/Scripts/python.exe experiments/multilabel_ooi/verify_ooi_matrix.py
Exit 0 = every asserted count held, the subset rule held, the lens columns were verbatim,
and each tampered copy was caught naming the cell that was changed.
"""
import csv
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOLVED = ROOT / "run" / "eda_full_20261029" / "resolved_labels.csv"
SPLIT = ROOT / "run" / "split_20261103_v8" / "split_70_15_15.csv"
LABELS_B = ROOT / "run" / "multilabel_lp_v8_20261103" / "labels_b.csv"
OUTDIR = ROOT / "run" / "ooi_matrix_20261104"
TABLE = OUTDIR / "ooi_labels.csv"
COUNTS = OUTDIR / "counts.json"

LENS_COLUMNS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD",
                "P1_COC", "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]
CLASS_COLUMNS = ["class_bubble", "class_bubble_cluster", "class_foreign_matter",
                 "class_fiber", "class_wet_package", "class_hema",
                 "class_extraneous_polymer", "class_surface_groove"]
GATE_COLUMNS = ["gate_foreign_matter", "gate_fiber", "gate_extraneous_polymer", "gate_hema"]
GATE_OWNER = {"gate_foreign_matter": "class_foreign_matter",
              "gate_fiber": "class_fiber",
              "gate_extraneous_polymer": "class_extraneous_polymer",
              "gate_hema": "class_hema"}
HEADER = ["picture_md5", "split"] + CLASS_COLUMNS + GATE_COLUMNS + LENS_COLUMNS + ["clear"]

# The verifier's own class map, over raw annotation codes. P2_HMO, the legacy whole-image
# HEMA obstruction tag, is deliberately in no map, and the two library-only bubble tags are
# in none either: that is the ticket's exclusion, expressed here rather than inherited.
CLASS_FROM_CODE = {
    "class_bubble": frozenset({"P2_BB", "Bubble", "P2_BI", "Bubble Irregular",
                               "P2_BST", "Stretched Bubble"}),
    "class_bubble_cluster": frozenset({"P2_BC", "Bubble Cluster"}),
    "class_foreign_matter": frozenset({"P3_FM", "Foreign Matter", "P3_FM_MICRON_THRESHOLD"}),
    "class_fiber": frozenset({"P3_FIB", "Fiber", "P3_FIB_MICRON_THRESHOLD"}),
    "class_wet_package": frozenset({"P2_WP", "Wet Package"}),
    "class_hema": frozenset({"P3_HE", "HEMA Fragment", "P3_HE_MICRON_THRESHOLD"}),
    "class_extraneous_polymer": frozenset({"P3_EP", "Extraneous Polymer",
                                           "P3_EP_MICRON_THRESHOLD"}),
    "class_surface_groove": frozenset(),
}
GATE_FROM_CODE = {"gate_foreign_matter": "P3_FM_MICRON_THRESHOLD",
                  "gate_fiber": "P3_FIB_MICRON_THRESHOLD",
                  "gate_extraneous_polymer": "P3_EP_MICRON_THRESHOLD",
                  "gate_hema": "P3_HE_MICRON_THRESHOLD"}
LEGACY_BUBBLE_CODES = {"Bubble On 123": 13, "Bubble On Edge": 14}
LEGACY_HEMA_TAG_CODE = "P2_HMO"
SURFACE_GROOVE_CODES = {"P1_SG", "Surface Groove"}

# Hand-typed from docs/wayfinder/tickets/027-ooi-label-table.md and the OOI point 4 map,
# never copied out of counts.json or any run output.
EXPECTED_ROWS = 7470
EXPECTED_SPLIT_MD5 = "1a71d66d2de384cf47a3fcf7d9115baa"
EXPECTED_SPLIT_TOTALS = {"train": 5239, "val": 1110, "test": 1121}
EXPECTED_CLASS = {"class_bubble": 2171, "class_bubble_cluster": 1132,
                  "class_foreign_matter": 798, "class_fiber": 392,
                  "class_wet_package": 314, "class_hema": 154,
                  "class_extraneous_polymer": 142, "class_surface_groove": 0}
EXPECTED_GATE = {"gate_foreign_matter": 454, "gate_fiber": 362,
                 "gate_extraneous_polymer": 135, "gate_hema": 151}
# val / test per class, in the ticket's order.
EXPECTED_VAL_TEST = {"class_bubble": (326, 325), "class_bubble_cluster": (170, 170),
                     "class_foreign_matter": (110, 112), "class_fiber": (60, 58),
                     "class_wet_package": (47, 47), "class_hema": (25, 27),
                     "class_extraneous_polymer": (19, 17),
                     "class_surface_groove": (0, 0)}
# Ticket 029 states the gated test positives directly: FM 72, Fiber 56, EP 17, HEMA 27.
EXPECTED_GATE_TEST = {"gate_foreign_matter": 72, "gate_fiber": 56,
                      "gate_extraneous_polymer": 17, "gate_hema": 27}
# The single hema_obstruction tag-only picture in the frozen split (val side).
EXPECTED_TAG_ONLY_MD5 = "d50402e0b6d5817615e343aecb3447df"
EXPECTED_HEMA_WITH_TAG = 155


def md5_of(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def read_split():
    with open(SPLIT, newline="", encoding="utf-8-sig") as fh:
        return {r["picture_md5"]: r["split"] for r in csv.DictReader(fh)}


def read_labels_b():
    with open(LABELS_B, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {r["md5"]: r for r in rows}, len(rows)


def read_codes():
    """{md5: set of raw annotation codes}. The verifier's own view of the record."""
    codes = {}
    with open(RESOLVED, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            codes.setdefault(row["picture_md5"], set()).add(row["code"])
    return codes


def as_int(text):
    """0 or 1 from a cell, or None when the cell is anything else."""
    if text in ("0", "1"):
        return int(text)
    return None


def rebuild(codes, md5):
    """Expected class and gate values for one picture, from the verifier's own maps."""
    seen = codes.get(md5, set())
    want = {col: int(bool(seen & allowed)) for col, allowed in CLASS_FROM_CODE.items()}
    for gate, code in GATE_FROM_CODE.items():
        want[gate] = int(code in seen)
    return want


def check(table_path):
    """Every failure this verifier can name. Empty list = the table holds."""
    bad = []

    digest = md5_of(SPLIT)
    if digest != EXPECTED_SPLIT_MD5:
        bad.append(f"split file md5 {digest} != frozen {EXPECTED_SPLIT_MD5}")
    split_map = read_split()
    labels_b, labels_b_rows = read_labels_b()
    codes = read_codes()

    with open(table_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames
        rows = list(reader)
    if header != HEADER:
        bad.append(f"header {header} != expected {HEADER}")
        return bad

    # Keys: one row per split picture, no duplicates, nothing extra.
    if len(rows) != EXPECTED_ROWS:
        bad.append(f"rows {len(rows)} != {EXPECTED_ROWS}")
    table = {r["picture_md5"]: r for r in rows}
    if len(table) != len(rows):
        bad.append(f"{len(rows) - len(table)} duplicate picture_md5 rows")
    if set(table) != set(split_map):
        missing = len(set(split_map) - set(table))
        extra = len(set(table) - set(split_map))
        bad.append(f"key set differs from the split: {missing} missing, {extra} extra")

    if labels_b_rows != EXPECTED_ROWS:
        bad.append(f"labels_b.csv has {labels_b_rows} rows != {EXPECTED_ROWS}")

    # Cell by cell against the verifier's rebuild, then the split and the carried columns.
    splits_seen = {}
    for md5 in sorted(set(table) & set(split_map)):
        row = table[md5]
        want = rebuild(codes, md5)
        for column in CLASS_COLUMNS + GATE_COLUMNS:
            got = as_int(row[column])
            if got is None:
                bad.append(f"cell {md5} {column}: table value {row[column]!r} is not 0/1")
            elif got != want[column]:
                bad.append(f"cell {md5} {column}: table {got}, annotation {want[column]}")
        if row["split"] != split_map[md5]:
            bad.append(f"cell {md5} split: table {row['split']!r}, "
                       f"split file {split_map[md5]!r}")
        splits_seen[md5] = row["split"]
        carried = labels_b.get(md5)
        if carried is None:
            bad.append(f"cell {md5}: picture missing from labels_b.csv")
            continue
        for column in LENS_COLUMNS:
            if row[column] != carried[column]:
                bad.append(f"cell {md5} {column}: table {row[column]!r}, "
                           f"labels_b {carried[column]!r}")
        if row["clear"] != carried["is_clear"]:
            bad.append(f"cell {md5} clear: table {row['clear']!r}, "
                       f"labels_b {carried['is_clear']!r}")
        if row["split"] != carried["split"]:
            bad.append(f"cell {md5} split: table {row['split']!r}, "
                       f"labels_b {carried['split']!r}")

    # Gate is a subset of class on every row.
    for md5, row in sorted(table.items()):
        for gate, owner in GATE_OWNER.items():
            if as_int(row[gate]) == 1 and as_int(row[owner]) != 1:
                bad.append(f"subset violation: {md5} {gate}=1 while {owner}=0")

    # Every count the ticket names, read off the table itself.
    totals = {col: sum(as_int(r[col]) or 0 for r in rows) for col in CLASS_COLUMNS + GATE_COLUMNS}
    for column, expected in EXPECTED_CLASS.items():
        if totals[column] != expected:
            bad.append(f"count {column}: table {totals[column]} != {expected}")
    for column, expected in EXPECTED_GATE.items():
        if totals[column] != expected:
            bad.append(f"count {column}: table {totals[column]} != {expected}")

    split_totals = {s: sum(1 for r in rows if r["split"] == s)
                    for s in ("train", "val", "test")}
    for side, expected in EXPECTED_SPLIT_TOTALS.items():
        if split_totals[side] != expected:
            bad.append(f"split {side}: table {split_totals[side]} != {expected}")

    for column, (val_want, test_want) in EXPECTED_VAL_TEST.items():
        got = (sum(1 for r in rows if r["split"] == "val" and as_int(r[column]) == 1),
               sum(1 for r in rows if r["split"] == "test" and as_int(r[column]) == 1))
        if got != (val_want, test_want):
            bad.append(f"val/test {column}: table {got[0]}-{got[1]} != {val_want}-{test_want}")
    for column, expected in EXPECTED_GATE_TEST.items():
        got = sum(1 for r in rows if r["split"] == "test" and as_int(r[column]) == 1)
        if got != expected:
            bad.append(f"test gate {column}: table {got} != {expected}")

    # Surface Groove: no pictures exist, so the column and its split counts must be zero.
    if totals["class_surface_groove"] != 0:
        bad.append(f"count class_surface_groove: table "
                   f"{totals['class_surface_groove']} != 0 (the class has no pictures)")
    sg_pics = sorted(m for m, cs in codes.items() if cs & SURFACE_GROOVE_CODES)
    if sg_pics:
        bad.append(f"the record carries {len(sg_pics)} Surface Groove pictures, "
                   "so the all-zero column is wrong")

    # HEMA: the one obstruction tag-only picture in the split is excluded, and the ticket's
    # 154 depends on it: with the legacy tag counted the class would read 155.
    tag_only = sorted(m for m in split_map
                      if LEGACY_HEMA_TAG_CODE in codes.get(m, set())
                      and not (codes.get(m, set()) & CLASS_FROM_CODE["class_hema"]))
    if tag_only != [EXPECTED_TAG_ONLY_MD5]:
        bad.append(f"obstruction tag-only pictures in the split {tag_only} != "
                   f"[{EXPECTED_TAG_ONLY_MD5}]")
    for md5 in tag_only:
        row = table.get(md5)
        if row is None:
            bad.append(f"cell {md5}: the tag-only picture is missing from the table")
        else:
            if as_int(row["class_hema"]) != 0:
                bad.append(f"cell {md5} class_hema: table {row['class_hema']} but the "
                           "legacy obstruction tag is not evidence")
            if row["split"] != split_map.get(md5):
                bad.append(f"cell {md5} split: table {row['split']!r} != "
                           f"split file {split_map.get(md5)!r}")
    with_tag = sum(1 for m in split_map
                   if (codes.get(m, set()) & CLASS_FROM_CODE["class_hema"])
                   or LEGACY_HEMA_TAG_CODE in codes.get(m, set()))
    if with_tag != EXPECTED_HEMA_WITH_TAG:
        bad.append(f"HEMA with the obstruction tag counted reads {with_tag} != "
                   f"{EXPECTED_HEMA_WITH_TAG}, so the exclusion is not the one pinned here")

    # The two legacy bubble tags: they exist in the record, they are out of the split, and
    # no picture gains class_bubble from them.
    for code, expected in LEGACY_BUBBLE_CODES.items():
        pics = sorted(m for m, cs in codes.items() if code in cs)
        if len(pics) != expected:
            bad.append(f"record holds {len(pics)} {code} pictures != {expected}")
        in_split = [m for m in pics if m in split_map]
        if in_split:
            bad.append(f"{len(in_split)} {code} pictures sit in the frozen split, "
                       "where the ticket excludes them")
    legacy_only = [m for m in split_map
                   if codes.get(m, set()) & set(LEGACY_BUBBLE_CODES)
                   and not (codes.get(m, set()) & CLASS_FROM_CODE["class_bubble"])]
    for md5 in legacy_only:
        row = table.get(md5)
        if row is not None and as_int(row["class_bubble"]) == 1:
            bad.append(f"cell {md5} class_bubble: table 1 but its only bubble evidence is "
                       "a legacy library tag")

    return bad


def tamper(table_path, column, pick, flip):
    """Copy the table, set `column` of the picked row to `flip`, return (md5, copy path)."""
    with open(table_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    target = None
    for row in rows:
        if pick(row):
            target = row
            break
    if target is None:
        raise SystemExit(f"FAIL: no row found to tamper in {column}")
    target[column] = flip
    directory = tempfile.mkdtemp(prefix="ooi_tamper_")
    copy = Path(directory) / "ooi_labels.csv"
    with open(copy, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
    return target["picture_md5"], copy


def prove(table_path, label, column, pick, flip):
    """One tamper proof: the copy must fail, and the failure must name the cell."""
    md5, copy = tamper(table_path, column, pick, flip)
    try:
        bad = check(copy)
    finally:
        shutil.rmtree(copy.parent, ignore_errors=True)
    named = [line for line in bad if md5 in line and column in line]
    if not named:
        print(f"FAIL: {label} tamper was not caught naming the cell")
        for line in bad[:10]:
            print("  ", line)
        return False
    print(f"tamper proof {label}: caught -> {named[0]}")
    return True


def main():
    for path in (RESOLVED, SPLIT, LABELS_B, TABLE, COUNTS):
        if not path.exists():
            print(f"FAIL: missing {path}")
            return 1

    print(f"inputs  resolved md5 {md5_of(RESOLVED)}")
    print(f"        split    md5 {md5_of(SPLIT)} (frozen {EXPECTED_SPLIT_MD5})")
    print(f"        labels_b md5 {md5_of(LABELS_B)}")

    bad = check(TABLE)
    if bad:
        print(f"FAIL: {len(bad)} problems")
        for line in bad[:40]:
            print("  ", line)
        if len(bad) > 40:
            print(f"   ... {len(bad) - 40} more")
        return 1

    # counts.json is the builder's own summary: agree with it, but never source from it.
    counts = json.loads(COUNTS.read_text(encoding="utf-8"))
    with open(TABLE, newline="", encoding="utf-8-sig") as fh:
        table_rows = list(csv.DictReader(fh))
    table_totals = {c: sum(int(r[c]) for r in table_rows)
                    for c in CLASS_COLUMNS + GATE_COLUMNS}
    mismatched = []
    for column, total in table_totals.items():
        written = counts.get("class_totals", {}).get(column)
        if written is None:
            written = counts.get("gate_totals", {}).get(column)
        if written != total:
            mismatched.append(f"{column} {written} != {total}")
    if counts.get("rows") != EXPECTED_ROWS:
        mismatched.append(f"rows={counts.get('rows')}")
    for name, path in (("resolved_labels.csv", RESOLVED), ("split_70_15_15.csv", SPLIT),
                       ("labels_b.csv", LABELS_B)):
        if counts.get("inputs", {}).get(name, {}).get("md5") != md5_of(path):
            mismatched.append(f"input md5 {name}")
    if mismatched:
        print(f"FAIL: counts.json disagrees with the table on {mismatched}")
        return 1

    print(f"rows    {EXPECTED_ROWS}   splits " +
          " / ".join(str(EXPECTED_SPLIT_TOTALS[s]) for s in ("train", "val", "test")))
    print("class   " + "  ".join(f"{c.replace('class_', '')} {EXPECTED_CLASS[c]}"
                                  for c in CLASS_COLUMNS))
    print("gate    " + "  ".join(f"{g.replace('gate_', '')} {EXPECTED_GATE[g]}"
                                  for g in GATE_COLUMNS))
    print("val/test " + "  ".join(
        f"{c.replace('class_', '')} {EXPECTED_VAL_TEST[c][0]}-{EXPECTED_VAL_TEST[c][1]}"
        for c in CLASS_COLUMNS if c in EXPECTED_VAL_TEST))
    print(f"lens + clear: {len(LENS_COLUMNS) + 1} columns x {EXPECTED_ROWS} rows "
          "verbatim from labels_b.csv")
    print(f"HEMA: {EXPECTED_CLASS['class_hema']} with the obstruction tag-only picture "
          f"excluded ({EXPECTED_TAG_ONLY_MD5}); {EXPECTED_HEMA_WITH_TAG} with it counted")
    print(f"subset: gate inside class on all {EXPECTED_ROWS} rows x {len(GATE_COLUMNS)} gates")

    proofs = [
        prove(TABLE, "class", "class_bubble",
              lambda r: r["class_bubble"] == "1", "0"),
        prove(TABLE, "gate", "gate_foreign_matter",
              lambda r: r["class_foreign_matter"] == "0" and r["gate_foreign_matter"] == "0",
              "1"),
        prove(TABLE, "lens", "P1_MPP", lambda r: r["P1_MPP"] == "1", "0"),
    ]
    if not all(proofs):
        return 1

    print(f"PASS: {TABLE.name} matches the annotation under ticket 027 rules; "
          "every count asserted, tamper proofs caught naming their cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
