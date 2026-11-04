"""Build the OOI label table: eight class columns plus four gate columns on the frozen split.

Ticket 027 (docs/wayfinder/tickets/027-ooi-label-table.md). One row per picture of the
frozen v8 split, carrying:

  picture_md5, split,
  eight class columns   class_bubble .. class_surface_groove (presence of the object, any size),
  four gate columns     gate_foreign_matter .. gate_hema (the micron flag), a subset of class,
  twelve lens columns   P1_MPP .. P1_PPM, copied verbatim from labels_b.csv,
  clear                 copied verbatim from labels_b.csv.

Evidence comes from the annotation of record (run/eda_full_20261029/resolved_labels.csv),
joined to the frozen split on picture_md5. HEMA reads the production boxes and the fragments
and the gate rows; the legacy whole-image obstruction tag is not evidence (the one tag-only
picture in the split therefore stays out of the class). bubble_on_123 and bubble_on_edge are
library-only and are never read as evidence for any column.

This script writes the table and its counts and checks its own structure (row count, key
set, gate subset of class). It asserts no class or gate total: the numbers are the business
of experiments/multilabel_ooi/verify_ooi_matrix.py, which rebuilds every column from the
annotation with its own code map and takes nothing on trust from here.

Run:
    .venv/Scripts/python.exe experiments/multilabel_ooi/build_ooi_matrix.py
Exit 0 = run/ooi_matrix_20261104/ooi_labels.csv and counts.json written.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOLVED = ROOT / "run" / "eda_full_20261029" / "resolved_labels.csv"
SPLIT = ROOT / "run" / "split_20261103_v8" / "split_70_15_15.csv"
LABELS_B = ROOT / "run" / "multilabel_lp_v8_20261103" / "labels_b.csv"
OUTDIR = ROOT / "run" / "ooi_matrix_20261104"
TABLE = OUTDIR / "ooi_labels.csv"
COUNTS = OUTDIR / "counts.json"

SPLIT_MD5 = "1a71d66d2de384cf47a3fcf7d9115baa"
ROWS = 7470
SPLITS = ("train", "val", "test")

LENS_COLUMNS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD",
                "P1_COC", "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM"]

# Class columns in the ticket's count order. Each entry: column, canonical ids that set it,
# and the shape each id must show (empty dict = any shape). Surface Groove has no pictures.
CLASS_COLUMNS = [
    ("class_bubble", ("bubble", "bubble_irregular", "stretched_bubble"), {}),
    ("class_bubble_cluster", ("bubble_cluster",), {}),
    ("class_foreign_matter", ("foreign_matter", "foreign_matter_micron_gate"), {}),
    ("class_fiber", ("fiber", "fiber_micron_gate"), {}),
    ("class_wet_package", ("wet_package",), {}),
    ("class_hema", ("hema_fragment", "hema_obstruction", "hema_micron_gate"),
     {"hema_obstruction": "box"}),
    ("class_extraneous_polymer", ("extraneous_polymer", "extraneous_polymer_micron_gate"), {}),
    ("class_surface_groove", (), {}),
]

# Gate columns: gate column, the class column it must be a subset of, canonical id of the
# gate row. The gate row is class evidence for its class and nothing else.
GATE_COLUMNS = [
    ("gate_foreign_matter", "class_foreign_matter", "foreign_matter_micron_gate"),
    ("gate_fiber", "class_fiber", "fiber_micron_gate"),
    ("gate_extraneous_polymer", "class_extraneous_polymer", "extraneous_polymer_micron_gate"),
    ("gate_hema", "class_hema", "hema_micron_gate"),
]

# Library-only legacy classes: read out of the record so they are never mistaken for
# evidence, and never named in any class or gate map.
EXCLUDED_CLASSES = ("bubble_on_123", "bubble_on_edge")

HEADER = (["picture_md5", "split"]
          + [c for c, _, _ in CLASS_COLUMNS]
          + [g for g, _, _ in GATE_COLUMNS]
          + LENS_COLUMNS + ["clear"])


def md5_of(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def read_split():
    """[(picture_md5, split)] in file order, checked against the frozen split."""
    if md5_of(SPLIT) != SPLIT_MD5:
        raise SystemExit(f"FAIL: split file md5 {md5_of(SPLIT)} != frozen {SPLIT_MD5}")
    with open(SPLIT, newline="", encoding="utf-8-sig") as fh:
        rows = [(r["picture_md5"], r["split"]) for r in csv.DictReader(fh)]
    if len(rows) != ROWS:
        raise SystemExit(f"FAIL: split has {len(rows)} rows, expected {ROWS}")
    if len({m for m, _ in rows}) != len(rows):
        raise SystemExit("FAIL: duplicate picture_md5 in the split")
    bad = [m for m, s in rows if s not in SPLITS]
    if bad:
        raise SystemExit(f"FAIL: {len(bad)} split rows carry a name outside train/val/test")
    return rows


def read_labels_b():
    """{md5: {column: value}} for the twelve lens columns and clear, verbatim."""
    with open(LABELS_B, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != ROWS:
        raise SystemExit(f"FAIL: labels_b.csv has {len(rows)} rows, expected {ROWS}")
    carry = {r["md5"]: {c: r[c] for c in LENS_COLUMNS + ["is_clear"]} for r in rows}
    if len(carry) != len(rows):
        raise SystemExit("FAIL: duplicate md5 in labels_b.csv")
    return carry


def read_evidence():
    """{md5: {canonical_id: {shape_kind}}} from the annotation of record."""
    evidence = {}
    with open(RESOLVED, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            shapes = evidence.setdefault(row["picture_md5"], {}).setdefault(
                row["canonical_id"], set())
            shapes.add(row["shape_kind"])
    return evidence


def flag(shapes, sources, shape_filter):
    """1 when any source id is present with the shape its filter demands."""
    for cid in sources:
        if cid not in shapes:
            continue
        wanted = shape_filter.get(cid)
        if wanted is None or wanted in shapes[cid]:
            return 1
    return 0


def main():
    split_rows = read_split()
    labels_b = read_labels_b()
    evidence = read_evidence()

    split_map = dict(split_rows)
    if set(labels_b) != set(split_map):
        raise SystemExit("FAIL: labels_b.csv and the split do not cover the same pictures")

    rows = []
    for md5, split_name in sorted(split_rows):
        shapes = evidence.get(md5, {})
        record = {"picture_md5": md5, "split": split_name}
        for column, sources, shape_filter in CLASS_COLUMNS:
            record[column] = flag(shapes, sources, shape_filter)
        for column, _owner, gate_id in GATE_COLUMNS:
            record[column] = 1 if gate_id in shapes else 0
        for column in LENS_COLUMNS:
            record[column] = labels_b[md5][column]
        record["clear"] = labels_b[md5]["is_clear"]
        rows.append(record)

    # Structural self-checks. The class and gate totals belong to the verifier.
    broken = [r["picture_md5"] for r in rows
              if any(r[gate] and not r[owner] for gate, owner, _ in GATE_COLUMNS)]
    if broken:
        raise SystemExit(f"FAIL: gate is not a subset of class on {len(broken)} rows")
    if len(rows) != ROWS:
        raise SystemExit(f"FAIL: built {len(rows)} rows, expected {ROWS}")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(TABLE, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)

    class_totals = {c: sum(r[c] for r in rows) for c, _, _ in CLASS_COLUMNS}
    gate_totals = {g: sum(r[g] for r in rows) for g, _, _ in GATE_COLUMNS}
    per_split = {
        column: {s: sum(r[column] for r in rows if r["split"] == s) for s in SPLITS}
        for column in [c for c, _, _ in CLASS_COLUMNS] + [g for g, _, _ in GATE_COLUMNS]
    }
    counts = {
        "table": "run/ooi_matrix_20261104/ooi_labels.csv",
        "rows": len(rows),
        "split_md5": md5_of(SPLIT),
        "inputs": {
            "resolved_labels.csv": {"path": str(RESOLVED.relative_to(ROOT)).replace("\\", "/"),
                                    "md5": md5_of(RESOLVED)},
            "split_70_15_15.csv": {"path": str(SPLIT.relative_to(ROOT)).replace("\\", "/"),
                                   "md5": md5_of(SPLIT)},
            "labels_b.csv": {"path": str(LABELS_B.relative_to(ROOT)).replace("\\", "/"),
                             "md5": md5_of(LABELS_B)},
        },
        "split_totals": {s: sum(1 for r in rows if r["split"] == s) for s in SPLITS},
        "class_totals": class_totals,
        "gate_totals": gate_totals,
        "per_split": per_split,
        "notes": {
            "class_columns": "presence of the object at any size; the micron gate is folded "
                             "into its class",
            "gate_columns": "the micron-gate rows for Foreign Matter, Fiber, Extraneous "
                            "Polymer and HEMA, a subset of the class on every row",
            "hema": "production boxes (hema_obstruction, shape_kind box) plus hema_fragment "
                    "plus the gate rows; the legacy whole-image obstruction tag is not "
                    "evidence, so the one tag-only picture in the split is excluded",
            "excluded": list(EXCLUDED_CLASSES) + ["hema_obstruction tag rows"],
            "clear_and_lens": "verbatim from run/multilabel_lp_v8_20261103/labels_b.csv",
        },
    }
    with open(COUNTS, "w", encoding="utf-8") as fh:
        json.dump(counts, fh, indent=2, sort_keys=False)
        fh.write("\n")

    print(f"table  {TABLE}")
    print(f"rows   {len(rows)}   splits " +
          " / ".join(f"{counts['split_totals'][s]}" for s in SPLITS))
    width = max(len(c) for c in class_totals)
    print("class")
    for column, _, _ in CLASS_COLUMNS:
        total = class_totals[column]
        where = " ".join(f"{per_split[column][s]:5d}" for s in SPLITS)
        print(f"  {column:<{width}} {total:5d}   {where}")
    print("gate")
    for column, _, _ in GATE_COLUMNS:
        total = gate_totals[column]
        where = " ".join(f"{per_split[column][s]:5d}" for s in SPLITS)
        print(f"  {column:<{width}} {total:5d}   {where}")
    print(f"counts {COUNTS}")
    print("BUILD OK (structure checked here; the totals are asserted by verify_ooi_matrix.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
