"""One multi-label trainer for the object head and the combined head.

WHAT THIS IS (ticket 028)
--------------------------
A generalisation of experiments/multilabel_lp_full/train_lp_v8.py. One script
serves every round of OOI point 4. Rounds differ by flags, never by a forked
script. The threshold chooser, the evaluation maths and the prediction dump are
reused from train_lp_v8.py unchanged in behaviour: grid 0.05 to 0.95 step 0.05
on validation, highest F1 per class, ties to the higher cut, guard of 10
validation positives (below it the class keeps 0.5 and says "default").

Label source: run/ooi_matrix_20261104/ooi_labels.csv, the ticket-027 table
(7,470 rows, 27 columns, md5 7fd1106e355464deac72da73aa6b2c4b). The trainer
asserts every ticket-frozen count on each run and stops on a mismatch. Image
paths come from run/eda_full_20261029/resolved_labels.csv (winning_path) with
run/multilabel_edge_20261029_rev4/label_matrix.csv as the fallback for clear
rows, exactly as train_lp_v8.py derives them.

Column groups and switches:
  --columns ooi        the 7 supported object columns (class_*). Surface Groove
                       is never a model output: its column stays all-zero and
                       appears only in the --labels-only report.
  --columns combined   the 12 lens columns plus the same 7 object columns
                       (19 outputs, 20 minus Surface Groove).
  --columns gate4      Experiment 3.1's four gate columns: fm_gated,
                       fiber_gated, ep_gated, hema_gated, read from their own
                       table, run/split_exp3_1_20261116/labels.csv. Truth is the
                       column itself, so a picture carrying the class unflagged
                       is a negative, never masked; that is what makes the
                       false-fire rate measurable. The table carries its own
                       split and image path, so no v8 artifact is read.
                       --gated-target is ignored in this mode, --pos-weight
                       defaults to on, and the threshold grid extends to 0.99
                       when the maximum lands on 0.95.
  --table PATH         label table to read. Defaults per mode to the v8 table
                       for ooi/combined and the Exp 3.1 table for gate4, so an
                       existing command is unchanged.
  --gated-target class the four gated classes (foreign_matter, fiber,
                       extraneous_polymer, hema) train on their class_* column.
  --gated-target gate  those four train on their gate_* column. No model ever
                       trains on both column groups for the same class.
  --pos-weight on      per-class (N - n) / n computed on the train split only,
                       from this arm's training targets. off (default) is plain
                       BCEWithLogitsLoss.

Evaluation truth never follows the switch. Thresholds and every reported metric
use class-level truth for the object columns whatever the arm trained on, so
both round-1 arms are graded on the same truth (ticket 030: an arm is never
graded on its own target).

Outputs per arm under run/multilabel_ooi_20261104/<arm>/: metrics.json (macro AP
over the 7 supported classes with the frozen prevalence floors beside them, F1
at 0.5 and at the chosen cuts, the Bubble/Cluster confusion, recall-by-flag for
the 4 gated classes, and for combined runs the lens block), thresholds.json,
predictions.npz (val and test truth and scores plus the gate flags), final.pt.
run.json is written by the runner, never by this script.

HOW TO RUN IT
-------------
Counts only (no torch, no images, runs anywhere):
    .venv/Scripts/python.exe experiments/multilabel_ooi/train_multilabel.py --labels-only

Smoke, two-batch step (torch lives on the VM only):
    .venv/bin/python experiments/multilabel_ooi/train_multilabel.py \
        --columns ooi --gated-target class --pos-weight off --smoke

A real arm (VM):
    .venv/bin/python experiments/multilabel_ooi/train_multilabel.py \
        --columns ooi --gated-target class --pos-weight off \
        --image-root /data/FMD_Data_26082026/fmd_temp_images \
        --out run/multilabel_ooi_20261104/class

Experiment 3.1 (VM), four gate columns from their own table:
    .venv/bin/python experiments/multilabel_ooi/train_multilabel.py \
        --columns gate4 --image-root /data/FMD_Data_26082026/fmd_temp_images \
        --out run/gate4_exp3_1_20261116/gate4_224

Counts for the gate4 table, no torch needed:
    ... --columns gate4 --labels-only

--out defaults to run/multilabel_ooi_20261104/<gated-target> for ooi with
pos-weight off, adds _posw when it is on, and prefixes combined_ in combined
mode. The runner passes --out explicitly.

Re-score from a checkpoint:
    ... --dump-predictions --out run/multilabel_ooi_20261104/class
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- paths and label space

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / os.environ.get("OOI_TABLE", "run/ooi_matrix_20261104/ooi_labels.csv")
GATE4_TABLE = ROOT / os.environ.get(
    "OOI_TABLE_GATE4", "run/split_exp3_1_20261116/labels.csv")
GATE4_SPLIT = ROOT / os.environ.get(
    "OOI_SPLIT_GATE4", "run/split_exp3_1_20261116/split.csv")
RESOLVED = ROOT / os.environ.get("OOI_RESOLVED", "run/eda_full_20261029/resolved_labels.csv")
MATRIX = ROOT / os.environ.get("OOI_MATRIX", "run/multilabel_edge_20261029_rev4/label_matrix.csv")
SPLIT = ROOT / os.environ.get("OOI_SPLIT", "run/split_20261103_v8/split_70_15_15.csv")

TABLE_MD5 = "7fd1106e355464deac72da73aa6b2c4b"
SPLIT_MD5 = "1a71d66d2de384cf47a3fcf7d9115baa"

# The twelve LP tags, in table order. Never reorder: it is the column order of
# every target vector, metric row and checkpoint.
LP_TAGS = [
    ("P1_MPP", "Missing Primary Package"),
    ("P1_ML", "Multiple Lens"),
    ("P2_LOC", "Lens Off Center"),
    ("P2_DC", "Dirty Camera"),
    ("P1_NL", "No Lens"),
    ("P1_FL", "Folded Lens"),
    ("P2_LD", "Low Dose"),
    ("P1_COC", "Cavity Off Center"),
    ("P2_DS", "Dirty Strobe"),
    ("P2_FOV", "View Obstructed"),
    ("P2_BSC", "Bubble Scatter"),
    ("P1_PPM", "Package Misalignment"),
]
LENS_COLUMNS = [code for code, _ in LP_TAGS]

# The seven supported object classes in table order. Surface Groove is missing
# on purpose: it is an all-zero column, never a model output.
OBJECT_TAGS = [
    ("class_bubble", "Bubble"),
    ("class_bubble_cluster", "Bubble Cluster"),
    ("class_foreign_matter", "Foreign Matter"),
    ("class_fiber", "Fiber"),
    ("class_wet_package", "Wet Package"),
    ("class_hema", "HEMA"),
    ("class_extraneous_polymer", "Extraneous Polymer"),
]
OBJECT_COLUMNS = [code for code, _ in OBJECT_TAGS]
SURFACE_GROOVE = "class_surface_groove"
ALL_CLASS_COLUMNS = OBJECT_COLUMNS + [SURFACE_GROOVE]

# The four gated classes: class column -> gate column. --gated-target gate swaps
# the training target of exactly these four; the evaluation truth never moves.
GATED_COLUMNS = {
    "class_foreign_matter": "gate_foreign_matter",
    "class_fiber": "gate_fiber",
    "class_extraneous_polymer": "gate_extraneous_polymer",
    "class_hema": "gate_hema",
}
GATE_ORDER = ["gate_foreign_matter", "gate_fiber", "gate_extraneous_polymer", "gate_hema"]

# ---------------------------------------------- Experiment 3.1, --columns gate4
# A second, self-contained label space: four gate columns, their own table and
# their own split (ticket 037). Nothing here is read by the ooi or combined
# modes, and no v8 artifact is read by this one.
GATE4_COLUMNS = ["fm_gated", "fiber_gated", "ep_gated", "hema_gated"]
GATE4_TAGS = [
    ("fm_gated", "Foreign Matter"),
    ("fiber_gated", "Fiber"),
    ("ep_gated", "Extraneous Polymer"),
    ("hema_gated", "HEMA"),
]
GATE4_TABLE_COLUMNS = ["picture_md5", "image_path", "split"] + GATE4_COLUMNS

# ------------------------------------- Experiment 3.2, --columns cond15
# The condition specialist: the twelve lens columns plus the three non-gated
# object classes. The four gated classes are a separate model, so no size
# question enters this one and no picture is moved out of training.
COND15_COLUMNS = list(LENS_COLUMNS) + ["class_bubble", "class_bubble_cluster",
                                      "class_wet_package"]
COND15_TABLE = ROOT / "run/split_exp3_2_20261116/labels_conditions.csv"
COND15_EXPECTED_SPLIT = {"train": 5239, "val": 1110, "test": 1121}
# Frozen from the Experiment 3.1 split table; asserted on every run of the mode.
GATE4_EXPECTED_SPLIT = {"train": 4964, "val": 1058, "test": 1533}
GATE4_EXPECTED_POSITIVES = {
    "fm_gated": {"train": 315, "val": 60, "test": 79},
    "fiber_gated": {"train": 195, "val": 43, "test": 124},
    "ep_gated": {"train": 81, "val": 14, "test": 40},
    "hema_gated": {"train": 79, "val": 20, "test": 52},
}

# ------------------------------------- Frozen dataset, --columns frozen17
# The frozen 70/15/15 split. Seventeen class columns: ten lens conditions and
# the seven object classes. Clear and the six classes below 200 pictures are
# excluded. The four gate flags are auxiliary only; they are saved with the
# predictions so the flagged and unflagged reads need no second pass.
FROZEN17_COLUMNS = [
    "P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD", "P1_COC",
    "P2_FOV", "P1_PPM",
    "class_bubble", "class_bubble_cluster", "class_foreign_matter", "class_fiber",
    "class_wet_package", "class_hema", "class_extraneous_polymer",
]
FROZEN17_TABLE = ROOT / "experiments/frozen_data_experiments/splits/frozen_70_15_15_20261119/labels_17.csv"
FROZEN17_SPLIT = FROZEN17_TABLE.parent / "split.csv"
FROZEN17_GATES = FROZEN17_TABLE.parent / "gates_4.csv"
FROZEN17_EXPECTED_SPLIT = {"train": 9537, "val": 2049, "test": 2045}
FROZEN17_EXPECTED_TOTAL = {
    "P1_MPP": 1427, "P1_ML": 1511, "P2_LOC": 1570, "P2_DC": 1991,
    "P1_NL": 721, "P1_FL": 586, "P2_LD": 2124, "P1_COC": 816,
    "P2_FOV": 222, "P1_PPM": 1055,
    "class_bubble": 9771, "class_bubble_cluster": 4989,
    "class_foreign_matter": 2366, "class_fiber": 1394,
    "class_wet_package": 813, "class_hema": 337,
    "class_extraneous_polymer": 1017,
}
FROZEN17_GATE_TOTAL = {
    "gate_foreign_matter": 1400, "gate_fiber": 1304,
    "gate_extraneous_polymer": 1013, "gate_hema": 337,
}

# AP floor for a constant score is prevalence, frozen in the OOI point 4 map.
# Each value is asserted against the table total at read time.
PREVALENCE_FLOORS = {
    "class_bubble": 0.291,
    "class_bubble_cluster": 0.152,
    "class_foreign_matter": 0.107,
    "class_fiber": 0.052,
    "class_wet_package": 0.042,
    "class_hema": 0.021,
    "class_extraneous_polymer": 0.019,
}

NUMERIC_COLUMNS = ALL_CLASS_COLUMNS + GATE_ORDER + LENS_COLUMNS + ["clear"]

SPLITS = ("train", "val", "test")

# Frozen counts, taken from tickets 027, 028 and 029 and the OOI point 4 map.
EXPECTED_SPLIT = {"train": 5239, "val": 1110, "test": 1121}
EXPECTED_CLASS_TOTAL = {
    "class_bubble": 2171, "class_bubble_cluster": 1132, "class_foreign_matter": 798,
    "class_fiber": 392, "class_wet_package": 314, "class_hema": 154,
    "class_extraneous_polymer": 142, "class_surface_groove": 0,
}
EXPECTED_CLASS_VAL_TEST = {
    "class_bubble": (326, 325), "class_bubble_cluster": (170, 170),
    "class_foreign_matter": (110, 112), "class_fiber": (60, 58),
    "class_wet_package": (47, 47), "class_hema": (25, 27),
    "class_extraneous_polymer": (19, 17),
}
EXPECTED_GATE_TOTAL = {
    "gate_foreign_matter": 454, "gate_fiber": 362,
    "gate_extraneous_polymer": 135, "gate_hema": 151,
}
EXPECTED_GATE_TEST = {
    "gate_foreign_matter": 72, "gate_fiber": 56,
    "gate_extraneous_polymer": 17, "gate_hema": 27,
}
EXPECTED_LENS_TOTAL = {
    "P1_MPP": 1428, "P1_ML": 1426, "P2_LOC": 1201, "P2_DC": 573,
    "P1_NL": 326, "P1_FL": 333, "P2_LD": 677, "P1_COC": 185,
    "P2_DS": 33, "P2_FOV": 63, "P2_BSC": 5, "P1_PPM": 33,
}
EXPECTED_CLEAR = 2117


# ---------------------------------------------------------------- part 1: labels

def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _expect(label, got, want, where=None):
    if got != want:
        raise SystemExit(f"{(where or TABLE).name}: {label} is {got}, expected {want}")


def read_table(columns_mode="ooi", table=None, expect_counts=True):
    """Read the ticket-027 label table and assert every frozen count.

    Returns the rows as dicts: picture_md5, split, and all 25 numeric columns
    as ints. This is the only place labels enter the trainer. In gate4 mode the
    Experiment 3.1 table is read instead, by read_gate4_table.
    """
    if columns_mode == "gate4":
        return read_gate4_table(Path(table) if table else GATE4_TABLE, expect_counts)
    if columns_mode == "cond15":
        return read_cond15_table(Path(table) if table else COND15_TABLE, expect_counts)
    if columns_mode == "frozen17":
        return read_frozen17_table(Path(table) if table else FROZEN17_TABLE, expect_counts)

    table = Path(table) if table else TABLE
    table_md5 = md5_of(table)
    if table_md5 != TABLE_MD5:
        raise SystemExit(f"{table} md5 {table_md5}, expected {TABLE_MD5}")
    split_md5 = md5_of(SPLIT)
    if split_md5 != SPLIT_MD5:
        raise SystemExit(f"{SPLIT} md5 {split_md5}, expected {SPLIT_MD5}")

    with open(table, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    rows = []
    for record in raw:
        row = {"picture_md5": record["picture_md5"], "split": record["split"]}
        for column in NUMERIC_COLUMNS:
            row[column] = int(record[column])
        rows.append(row)

    _expect("rows", len(rows), 7470)

    # The split file and the table must carry the same pictures on the same side.
    with open(SPLIT, newline="", encoding="utf-8") as fh:
        split_of = {record["picture_md5"]: record["split"] for record in csv.DictReader(fh)}
    _expect("split rows", len(split_of), 7470)
    _expect("picture set", {r["picture_md5"] for r in rows}, set(split_of))
    disagreed = [r["picture_md5"] for r in rows if split_of.get(r["picture_md5"]) != r["split"]]
    if disagreed:
        raise SystemExit(f"{len(disagreed)} rows disagree with {SPLIT.name}, "
                         f"first {disagreed[0]}")

    split_totals = Counter(r["split"] for r in rows)
    for side, want in EXPECTED_SPLIT.items():
        _expect(f"{side} rows", split_totals[side], want)

    for column, want in EXPECTED_CLASS_TOTAL.items():
        _expect(f"{column} total", sum(r[column] for r in rows), want)
    for column, (want_val, want_test) in EXPECTED_CLASS_VAL_TEST.items():
        _expect(f"{column} val", sum(r[column] for r in rows if r["split"] == "val"), want_val)
        _expect(f"{column} test", sum(r[column] for r in rows if r["split"] == "test"), want_test)
    for column, want in EXPECTED_GATE_TOTAL.items():
        _expect(f"{column} total", sum(r[column] for r in rows), want)
    for column, want in EXPECTED_GATE_TEST.items():
        _expect(f"{column} test", sum(r[column] for r in rows if r["split"] == "test"), want)
    for column, want in EXPECTED_LENS_TOTAL.items():
        _expect(f"{column} total", sum(r[column] for r in rows), want)
    _expect("clear total", sum(r["clear"] for r in rows), EXPECTED_CLEAR)

    # Gate is a subset of class on every row.
    violations = 0
    for row in rows:
        for class_column, gate_column in GATED_COLUMNS.items():
            if row[gate_column] > row[class_column]:
                violations += 1
    _expect("gate subset violations", violations, 0)

    # The frozen floors are the population prevalence of their class.
    for column, floor in PREVALENCE_FLOORS.items():
        _expect(f"floor {column}", round(EXPECTED_CLASS_TOTAL[column] / 7470, 3), floor)

    return rows


def read_gate4_table(table, expect_counts=True):
    """Read the Experiment 3.1 four-column table (ticket 037).

    Schema: picture_md5, image_path, split, fm_gated, fiber_gated, ep_gated,
    hema_gated. The table carries its own split and its own image path, so no
    v8 artifact is opened in this mode. The four frozen per-split counts are
    asserted on every real run; --expect-counts off is for a synthetic table
    only, and says so loudly.
    """
    if not table.is_file():
        raise SystemExit(f"gate4 label table not found: {table}")
    table_md5 = md5_of(table)
    with open(table, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        present = list(reader.fieldnames or [])
        missing = [c for c in GATE4_TABLE_COLUMNS if c not in present]
        if missing:
            raise SystemExit(f"{table.name}: missing columns {missing}")
        raw = list(reader)

    rows = []
    for record in raw:
        row = {"picture_md5": record["picture_md5"], "split": record["split"],
               "image_path": record["image_path"]}
        for column in GATE4_COLUMNS:
            row[column] = int(record[column])
        rows.append(row)

    totals = Counter(r["split"] for r in rows)
    print(f"table: {table} md5 {table_md5}")
    print(f"rows: {len(rows)}: {totals['train']} train / {totals['val']} val / "
          f"{totals['test']} test")

    # The split of record beside the table must agree picture for picture with
    # the split column this run trains on. Skipped for a synthetic table.
    split_path = GATE4_SPLIT if table.parent == GATE4_TABLE.parent \
        else table.parent / "split.csv"
    if expect_counts and split_path.is_file():
        with open(split_path, newline="", encoding="utf-8") as fh:
            split_of = {r["picture_md5"]: r["split"] for r in csv.DictReader(fh)}
        _expect("picture set", {r["picture_md5"] for r in rows}, set(split_of), table)
        disagreed = [r["picture_md5"] for r in rows
                     if split_of.get(r["picture_md5"]) != r["split"]]
        _expect(f"rows disagreeing with {split_path.name}", len(disagreed), 0, table)
        print(f"split cross-check: {split_path.name} agrees on all {len(split_of)} pictures")

    if expect_counts:
        for side, want in GATE4_EXPECTED_SPLIT.items():
            _expect(f"{side} rows", totals[side], want, table)
        for column, per in GATE4_EXPECTED_POSITIVES.items():
            for side in SPLITS:
                got = sum(r[column] for r in rows if r["split"] == side)
                _expect(f"{column} {side} positives", got, per[side], table)
    else:
        print("frozen counts NOT asserted: --expect-counts off, synthetic table only")
    return rows


def read_paths():
    """winning_path per md5: resolved labels first, label matrix as fallback.

    This is train_lp_v8.py's derivation, unchanged.
    """
    path_of = {}
    with open(RESOLVED, newline="", encoding="utf-8") as fh:
        for record in csv.DictReader(fh):
            path_of.setdefault(record["picture_md5"], record["winning_path"])
    with open(MATRIX, newline="", encoding="utf-8") as fh:
        for record in csv.DictReader(fh):
            path_of.setdefault(record["picture_md5"], record["winning_path"])
    return path_of


def read_cond15_table(table, expect_counts=True):
    """Read the condition specialist's 15-column table (Experiment 3.2).

    The table is self-contained: it carries image_path and split, so no v8
    artifact is opened. Counts are asserted against the frozen assignment.
    """
    table = Path(table)
    if not table.is_file():
        raise SystemExit(f"cond15 label table not found: {table}")
    with open(table, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    if not raw:
        raise SystemExit(f"empty cond15 table: {table}")
    required = ["picture_md5", "image_path", "split"] + COND15_COLUMNS
    missing = [c for c in required if c not in raw[0]]
    if missing:
        raise SystemExit(f"cond15 table missing columns: {missing}")
    rows = []
    for record in raw:
        row = {"picture_md5": record["picture_md5"], "split": record["split"],
               "image_path": record["image_path"]}
        for column in COND15_COLUMNS:
            row[column] = int(record[column])
        rows.append(row)
    counts = Counter(r["split"] for r in rows)
    print(f"cond15 table: {table} md5 {md5_of(table)}")
    print(f"rows: {len(rows)}: " + " / ".join(f"{counts[s]} {s}" for s in ("train", "val", "test")))
    if expect_counts:
        _expect("cond15 rows", len(rows), sum(COND15_EXPECTED_SPLIT.values()))
        for side, want in COND15_EXPECTED_SPLIT.items():
            _expect(f"cond15 {side} rows", counts[side], want)
        positives = {c: sum(r[c] for r in rows if r["split"] == "train")
                     for c in COND15_COLUMNS}
        print("cond15 train positives: "
              + ", ".join(f"{c}={n}" for c, n in positives.items()))
    return rows


def read_frozen17_table(table, expect_counts=True):
    """Read the frozen 17-column table and its four gate flags.

    Schema: md5, image_path, split, then the 17 columns. gates_4.csv sits beside
    it and carries md5, image_path and the four gate flags. The gate flags are
    attached to each row as a four-value list in GATE_ORDER, so the run can save
    them with the predictions and the results can split flagged from unflagged
    without another pass over the store.
    """
    table = Path(table)
    if not table.is_file():
        raise SystemExit(f"frozen17 label table not found: {table}")
    with open(table, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    if not raw:
        raise SystemExit(f"empty frozen17 table: {table}")
    required = ["md5", "image_path", "split"] + FROZEN17_COLUMNS
    missing = [c for c in required if c not in raw[0]]
    if missing:
        raise SystemExit(f"frozen17 table missing columns: {missing}")

    gate_of = {}
    gates_path = table.parent / "gates_4.csv"
    if gates_path.is_file():
        with open(gates_path, newline="", encoding="utf-8") as fh:
            for record in csv.DictReader(fh):
                gate_of[(record["md5"], record["image_path"])] = [
                    int(record[c]) for c in GATE_ORDER]
    elif expect_counts:
        raise SystemExit(f"frozen17 gate table not found: {gates_path}")
    else:
        print(f"gate table not found: {gates_path}; gate flags read as zero")

    rows = []
    for record in raw:
        key = (record["md5"], record["image_path"])
        row = {"picture_md5": record["md5"], "split": record["split"],
               "image_path": record["image_path"],
               "gate": gate_of.get(key, [0, 0, 0, 0])}
        for column in FROZEN17_COLUMNS:
            row[column] = int(record[column])
        rows.append(row)

    counts = Counter(r["split"] for r in rows)
    print(f"frozen17 table: {table} md5 {md5_of(table)}")
    print(f"rows: {len(rows)}: " + " / ".join(f"{counts[s]} {s}" for s in ("train", "val", "test")))
    if expect_counts:
        _expect("frozen17 rows", len(rows), sum(FROZEN17_EXPECTED_SPLIT.values()))
        for side, want in FROZEN17_EXPECTED_SPLIT.items():
            _expect(f"frozen17 {side} rows", counts[side], want)
        for column, want in FROZEN17_EXPECTED_TOTAL.items():
            _expect(f"frozen17 {column} total", sum(r[column] for r in rows), want)
        for column, want in FROZEN17_GATE_TOTAL.items():
            j = GATE_ORDER.index(column)
            _expect(f"frozen17 {column} total", sum(r["gate"][j] for r in rows), want)
        split_path = table.parent / "split.csv"
        if split_path.is_file():
            with open(split_path, newline="", encoding="utf-8") as fh:
                split_of = {r["md5"]: r["split"] for r in csv.DictReader(fh)}
            _expect("frozen17 split rows", len(split_of), len(rows))
            disagreed = [r["picture_md5"] for r in rows
                         if split_of.get(r["picture_md5"]) != r["split"]]
            _expect("rows disagreeing with split.csv", len(disagreed), 0)
        print("frozen17 train positives: "
              + ", ".join(f"{c}={sum(r[c] for r in rows if r['split'] == 'train')}"
                          for c in FROZEN17_COLUMNS))
    return rows


def output_columns(columns_mode):
    """The model's output columns, in fixed order, for one column group."""
    if columns_mode == "ooi":
        return list(OBJECT_COLUMNS)
    if columns_mode == "combined":
        return list(LENS_COLUMNS) + list(OBJECT_COLUMNS)
    if columns_mode == "gate4":
        return list(GATE4_COLUMNS)
    if columns_mode == "cond15":
        return list(COND15_COLUMNS)
    if columns_mode == "frozen17":
        return list(FROZEN17_COLUMNS)
    raise SystemExit(f"unknown columns mode {columns_mode}")


def build_rows(raw, columns_mode, gated_target, with_paths=True):
    """Attach image path, training target and evaluation truth to each row.

    target is what this arm trains on: the gate column replaces the class
    column for the four gated classes when --gated-target gate. truth is what
    every metric is computed on: always the class column, never the gate.
    """
    columns = output_columns(columns_mode)
    if columns_mode == "cond15":
        rows = []
        for record in raw:
            values = [record[c] for c in COND15_COLUMNS]
            row = {"md5": record["picture_md5"], "split": record["split"],
                   "truth": list(values), "target": list(values), "gate": [0, 0, 0, 0]}
            if with_paths:
                row["image_path"] = record.get("image_path")
            rows.append(row)
        if with_paths:
            missing = [r["md5"] for r in rows if not r["image_path"]]
            if missing:
                raise SystemExit(f"{len(missing)} rows have no image path, first {missing[0]}")
        return rows, columns
    if columns_mode == "frozen17":
        rows = []
        for record in raw:
            values = [record[c] for c in FROZEN17_COLUMNS]
            row = {"md5": record["picture_md5"], "split": record["split"],
                   "truth": list(values), "target": list(values),
                   "gate": list(record.get("gate", [0, 0, 0, 0]))}
            if with_paths:
                row["image_path"] = record.get("image_path")
            rows.append(row)
        if with_paths:
            missing = [r["md5"] for r in rows if not r["image_path"]]
            if missing:
                raise SystemExit(f"{len(missing)} rows have no image path, first {missing[0]}")
        return rows, columns
    if columns_mode == "gate4":
        # gate4 trains on the gate columns themselves, so target and truth are
        # the same vector, and --gated-target has nothing to swap. The table
        # carries the image path, so the v8 path tables are not opened.
        rows = []
        for record in raw:
            values = [record[c] for c in GATE4_COLUMNS]
            row = {"md5": record["picture_md5"], "split": record["split"],
                   "truth": list(values), "target": list(values), "gate": list(values)}
            if with_paths:
                row["image_path"] = record.get("image_path")
            rows.append(row)
        if with_paths:
            missing = [r["md5"] for r in rows if not r["image_path"]]
            if missing:
                raise SystemExit(f"{len(missing)} rows have no image path, first {missing[0]}")
        return rows, columns

    path_of = read_paths() if with_paths else {}
    rows = []
    for record in raw:
        truth = [record[c] for c in columns]
        target = list(truth)
        if gated_target == "gate":
            for j, column in enumerate(columns):
                gate_column = GATED_COLUMNS.get(column)
                if gate_column is not None:
                    target[j] = record[gate_column]
        row = {"md5": record["picture_md5"], "split": record["split"],
               "truth": truth, "target": target,
               "gate": [record[g] for g in GATE_ORDER]}
        if with_paths:
            row["image_path"] = path_of.get(record["picture_md5"])
        rows.append(row)

    if with_paths:
        missing = [r["md5"] for r in rows if not r["image_path"]]
        if missing:
            raise SystemExit(f"{len(missing)} rows have no image path, first {missing[0]}")
    return rows, columns


def labels_report(raw, args):
    """Print the per-split counts of every column group and confirm the frozen numbers."""
    if args.columns == "cond15":
        counts = Counter(r["split"] for r in raw)
        print(f"cond15 rows: {len(raw)}: {counts['train']} train / {counts['val']} val / "
              f"{counts['test']} test")
        print("  column                      total  train   val  test")
        for column in COND15_COLUMNS:
            total = sum(int(r[column]) for r in raw)
            tr = sum(int(r[column]) for r in raw if r["split"] == "train")
            va = sum(int(r[column]) for r in raw if r["split"] == "val")
            te = sum(int(r[column]) for r in raw if r["split"] == "test")
            print(f"  {column:24s} {total:6d} {tr:6d} {va:5d} {te:5d}")
        print(f"model outputs ({len(COND15_COLUMNS)}): {', '.join(COND15_COLUMNS)}")
        return
    if args.columns == "frozen17":
        counts = Counter(r["split"] for r in raw)
        print(f"frozen17 rows: {len(raw)}: {counts['train']} train / "
              f"{counts['val']} val / {counts['test']} test")
        print("  column                      total  train   val  test")
        for column in FROZEN17_COLUMNS:
            total = sum(int(r[column]) for r in raw)
            tr = sum(int(r[column]) for r in raw if r["split"] == "train")
            va = sum(int(r[column]) for r in raw if r["split"] == "val")
            te = sum(int(r[column]) for r in raw if r["split"] == "test")
            print(f"  {column:24s} {total:6d} {tr:6d} {va:5d} {te:5d}")
        print("  gate flags (auxiliary, not model outputs)")
        for j, gate in enumerate(GATE_ORDER):
            total = sum(int(r["gate"][j]) for r in raw)
            tr = sum(int(r["gate"][j]) for r in raw if r["split"] == "train")
            va = sum(int(r["gate"][j]) for r in raw if r["split"] == "val")
            te = sum(int(r["gate"][j]) for r in raw if r["split"] == "test")
            print(f"  {gate:24s} {total:6d} {tr:6d} {va:5d} {te:5d}")
        print(f"model outputs ({len(FROZEN17_COLUMNS)}): {', '.join(FROZEN17_COLUMNS)}")
        return
    if args.columns == "gate4":
        gate4_labels_report(raw, args)
        return
    split_totals = Counter(r["split"] for r in raw)

    def counts(column):
        total = sum(r[column] for r in raw)
        per = {s: sum(r[column] for r in raw if r["split"] == s) for s in SPLITS}
        return total, per

    print(f"table: {TABLE.relative_to(ROOT).as_posix()} md5 {TABLE_MD5}")
    print(f"split: {SPLIT.relative_to(ROOT).as_posix()} md5 {SPLIT_MD5}")
    print(f"rows: {len(raw)}: {split_totals['train']} train / {split_totals['val']} val / "
          f"{split_totals['test']} test")
    header = f"  {'column':26s} {'total':>6s} {'train':>6s} {'val':>5s} {'test':>5s}"
    print(header)

    def line(column, note=""):
        total, per = counts(column)
        print(f"  {column:26s} {total:6d} {per['train']:6d} {per['val']:5d} {per['test']:5d}{note}")

    print("class columns (object truth, --columns ooi):")
    for column in ALL_CLASS_COLUMNS:
        note = "   (never a model output)" if column == SURFACE_GROOVE else ""
        line(column, note)
    print("gate columns (gate-arm targets, --gated-target gate):")
    for column in GATE_ORDER:
        line(column)
    print("lens columns (--columns combined):")
    for column in LENS_COLUMNS:
        line(column)
    line("clear", "   (all-zero rows)")

    print("all frozen counts match ticket 027: class "
          + "/".join(str(EXPECTED_CLASS_TOTAL[c]) for c in ALL_CLASS_COLUMNS)
          + ", gate " + "/".join(str(EXPECTED_GATE_TOTAL[c]) for c in GATE_ORDER)
          + ", split " + "/".join(str(EXPECTED_SPLIT[s]) for s in SPLITS))
    columns = output_columns(args.columns)
    print(f"flags: --columns {args.columns} --gated-target {args.gated_target} "
          f"--pos-weight {args.pos_weight}")
    print(f"model outputs ({len(columns)}): {', '.join(columns)}")


def gate4_labels_report(raw, args):
    """The Experiment 3.1 read: four gate columns, per-split counts, weights.

    There is no class/gate/lens split to report here: the table holds the four
    gate columns only, one per gated class, positive on the size flag.
    """
    totals = Counter(r["split"] for r in raw)

    def per(column):
        return {s: sum(r[column] for r in raw if r["split"] == s) for s in SPLITS}

    print(f"  {'column':14s} {'total':>6s} {'train':>6s} {'val':>5s} {'test':>5s}")
    counts = {}
    for column, name in GATE4_TAGS:
        counts[column] = per(column)
        print(f"  {column:14s} {sum(counts[column].values()):6d} {counts[column]['train']:6d} "
              f"{counts[column]['val']:5d} {counts[column]['test']:5d}   ({name})")

    train_rows = totals["train"]
    weights = []
    for column, _name in GATE4_TAGS:
        n = counts[column]["train"]
        weights.append((train_rows - n) / n if n else float("inf"))
    print("training positives: " + " / ".join(str(counts[c]["train"]) for c, _ in GATE4_TAGS))
    print(f"inverse-frequency pos_weight on train only, N = {train_rows}: "
          + " / ".join(f"{w:.1f}" for w in weights))
    if args.expect_counts == "on":
        print("frozen counts match ticket 037: split "
              + "/".join(str(GATE4_EXPECTED_SPLIT[s]) for s in SPLITS)
              + ", train positives "
              + "/".join(str(GATE4_EXPECTED_POSITIVES[c]["train"]) for c, _ in GATE4_TAGS))
    columns = output_columns(args.columns)
    print(f"flags: --columns {args.columns} --gated-target {args.gated_target} (ignored) "
          f"--pos-weight {args.pos_weight}")
    print(f"model outputs ({len(columns)}): {', '.join(columns)}")


# ---------------------------------------------------------------- part 2: metrics

def average_precision(y_true, y_score):
    y_true = np.asarray(y_true, dtype=np.float64)
    y_score = np.asarray(y_score, dtype=np.float64)
    n_pos = y_true.sum()
    if n_pos == 0:
        return float("nan")
    order = np.argsort(-y_score, kind="stable")
    hits = y_true[order]
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(hits) + 1)
    recall = tp / n_pos
    delta = np.diff(np.concatenate([[0.0], recall]))
    return float((delta * precision).sum())


def macro_ap(y_true, y_score, columns):
    values = {}
    for j, name in enumerate(columns):
        ap = average_precision(y_true[:, j], y_score[:, j])
        if not np.isnan(ap):
            values[name] = ap
    macro = float(np.mean(list(values.values()))) if values else float("nan")
    return macro, values


def precision_recall_f1(y_true, y_score, threshold, columns):
    """Precision, recall and F1 at one fixed threshold, per column."""
    pred = (y_score >= threshold).astype(np.float64)
    out = {}
    for j, name in enumerate(columns):
        tp = float(((pred[:, j] == 1) & (y_true[:, j] == 1)).sum())
        fp = float(((pred[:, j] == 1) & (y_true[:, j] == 0)).sum())
        fn = float(((pred[:, j] == 0) & (y_true[:, j] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[name] = {"precision": precision, "recall": recall, "f1": f1,
                     "support": int(y_true[:, j].sum())}
    return out


THRESHOLD_GRID = [round(float(t), 2) for t in np.arange(0.05, 1.0, 0.05)]
# Extended only when gate4's maximum F1 lands on the top of the grid.
CEILING_GRID = [0.96, 0.97, 0.98, 0.99]
DEFAULT_THRESHOLD = 0.5
MIN_VAL_POSITIVES = 10


def choose_thresholds(val_true, val_score, columns, min_positives=MIN_VAL_POSITIVES,
                      extend_ceiling=False):
    """Pick one threshold per class by maximum F1 on the validation split.

    Returns {column: {...}} with the chosen threshold, where it came from, the full
    validation curve, and the 0.5 numbers for comparison. A class with fewer than
    `min_positives` validation positives is not tuned: the F1 curve at that support is
    noise, so it keeps 0.5 and says so.

    With extend_ceiling, a class whose best cut is the top of the grid (0.95) is
    re-picked over 0.96 to 0.99, so a saturated class is not cut short by the
    grid. Off by default: the ooi and combined grids are unchanged.
    """
    chosen = {}
    for j, name in enumerate(columns):
        support = int(val_true[:, j].sum())
        curve = []
        for t in THRESHOLD_GRID:
            m = precision_recall_f1(val_true[:, j:j + 1], val_score[:, j:j + 1], t, [name])[name]
            curve.append({"threshold": t, "precision": round(m["precision"], 6),
                          "recall": round(m["recall"], 6), "f1": round(m["f1"], 6)})
        at_half = next(c for c in curve if c["threshold"] == DEFAULT_THRESHOLD)
        extended = False
        if support < min_positives:
            best = max(curve, key=lambda c: (c["f1"], c["threshold"]))
            chosen[name] = {"threshold": DEFAULT_THRESHOLD, "source": "default",
                            "reason": f"val positives {support} < {min_positives}",
                            "val_support": support, "val_f1_at_threshold": at_half["f1"],
                            "val_f1_at_0.5": at_half["f1"],
                            "val_best_f1_seen": best["f1"],
                            "val_best_threshold_seen": best["threshold"],
                            "curve": curve}
            if extend_ceiling:
                chosen[name]["grid_extended"] = False
            continue
        # Tie-break towards the higher threshold: at equal F1 the stricter cut is the
        # safer operating point, and it keeps the choice off the very low scores.
        best = max(curve, key=lambda c: (c["f1"], c["threshold"]))
        if extend_ceiling and best["threshold"] == THRESHOLD_GRID[-1]:
            for t in CEILING_GRID:
                m = precision_recall_f1(val_true[:, j:j + 1], val_score[:, j:j + 1], t,
                                        [name])[name]
                curve.append({"threshold": t, "precision": round(m["precision"], 6),
                              "recall": round(m["recall"], 6), "f1": round(m["f1"], 6)})
            best = max(curve, key=lambda c: (c["f1"], c["threshold"]))
            extended = True
        chosen[name] = {"threshold": best["threshold"], "source": "val",
                        "reason": "max F1 on val", "val_support": support,
                        "val_f1_at_threshold": best["f1"], "val_f1_at_0.5": at_half["f1"],
                        "val_best_f1_seen": best["f1"],
                        "val_best_threshold_seen": best["threshold"],
                        "curve": curve}
        if extend_ceiling:
            chosen[name]["grid_extended"] = extended
    return chosen


JOINT_ORDER = ["both", "bubble_only", "cluster_only", "neither"]


def joint_label(bubble, cluster):
    if bubble and cluster:
        return "both"
    if bubble:
        return "bubble_only"
    if cluster:
        return "cluster_only"
    return "neither"


def bubble_cluster_confusion(truth, pred):
    """4x4 joint confusion: rows are the truth pair, columns the predicted pair.

    truth and pred are (n, 2) arrays in [class_bubble, class_bubble_cluster] order.
    """
    matrix = {t: {p: 0 for p in JOINT_ORDER} for t in JOINT_ORDER}
    for i in range(len(truth)):
        t = joint_label(int(truth[i, 0]), int(truth[i, 1]))
        p = joint_label(int(pred[i, 0]), int(pred[i, 1]))
        matrix[t][p] += 1
    return matrix


def recall_by_flag(test_rows, truth, pred_half, pred_cut):
    """Recall of each gated class on class-level test truth, split by the gate flag.

    The gate flag is the picture's own flag; it says nothing about which target
    the arm trained on. n is the class-positive test pictures in that group.
    """
    out = {}
    for gate_column in GATE_ORDER:
        class_column = next(c for c, g in GATED_COLUMNS.items() if g == gate_column)
        j = OBJECT_COLUMNS.index(class_column)
        g = GATE_ORDER.index(gate_column)
        positives = [i for i in range(len(test_rows)) if truth[i, j]]
        gated = [i for i in positives if test_rows[i]["gate"][g]]
        ungated = [i for i in positives if not test_rows[i]["gate"][g]]

        def rate(group, pred):
            if not group:
                return None
            hits = sum(1 for i in group if pred[i])
            return round(hits / len(group), 6)

        out[class_column] = {
            "gated": {"n": len(gated),
                      "recall_0.5": rate(gated, pred_half[:, j] == 1),
                      "recall_chosen": rate(gated, pred_cut[:, j] == 1)},
            "ungated": {"n": len(ungated),
                        "recall_0.5": rate(ungated, pred_half[:, j] == 1),
                        "recall_chosen": rate(ungated, pred_cut[:, j] == 1)},
        }
    return out


def evaluate_test(y_true, y_score, test_rows, thresholds, columns):
    """Every number the test read reports, at 0.5 and at the chosen thresholds."""
    obj_idx = [j for j, c in enumerate(columns) if c in OBJECT_COLUMNS]
    y_obj_true = y_true[:, obj_idx]
    y_obj_score = y_score[:, obj_idx]

    macro_obj, ap_obj = macro_ap(y_obj_true, y_obj_score, OBJECT_COLUMNS)
    at_half = precision_recall_f1(y_obj_true, y_obj_score, DEFAULT_THRESHOLD, OBJECT_COLUMNS)
    cut_obj = np.array([thresholds[c]["threshold"] for c in OBJECT_COLUMNS])
    pred_half = (y_obj_score >= DEFAULT_THRESHOLD).astype(int)
    pred_cut = (y_obj_score >= cut_obj).astype(int)
    truth_obj = y_obj_true.astype(int)

    per_class = {}
    f1_half, f1_cut = [], []
    for j, column in enumerate(OBJECT_COLUMNS):
        tp = float(((pred_cut[:, j] == 1) & (truth_obj[:, j] == 1)).sum())
        fp = float(((pred_cut[:, j] == 1) & (truth_obj[:, j] == 0)).sum())
        fn = float(((pred_cut[:, j] == 0) & (truth_obj[:, j] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[column] = {
            "name": dict(OBJECT_TAGS)[column],
            "support": int(truth_obj[:, j].sum()),
            "prevalence_floor": PREVALENCE_FLOORS[column],
            "test_prevalence": round(float(truth_obj[:, j].mean()), 6),
            "auprc": ap_obj.get(column, float("nan")),
            "threshold": thresholds[column]["threshold"],
            "threshold_source": thresholds[column]["source"],
            "precision_0.5": at_half[column]["precision"],
            "recall_0.5": at_half[column]["recall"],
            "f1_0.5": at_half[column]["f1"],
            "precision_chosen": precision,
            "recall_chosen": recall,
            "f1_chosen": f1,
        }
        f1_half.append(at_half[column]["f1"])
        f1_cut.append(f1)

    bubble_j = OBJECT_COLUMNS.index("class_bubble")
    cluster_j = OBJECT_COLUMNS.index("class_bubble_cluster")
    pair_idx = [bubble_j, cluster_j]

    result = {
        "rows": len(test_rows),
        "macro_ap_supported": macro_obj,
        "per_class": per_class,
        "macro_f1_0.5": float(np.mean(f1_half)),
        "macro_f1_chosen": float(np.mean(f1_cut)),
        "bubble_cluster_confusion": {
            "note": ("test split, truth pair vs predicted pair, order "
                     + " / ".join(JOINT_ORDER)),
            "at_0.5": bubble_cluster_confusion(truth_obj[:, pair_idx], pred_half[:, pair_idx]),
            "at_chosen": bubble_cluster_confusion(truth_obj[:, pair_idx], pred_cut[:, pair_idx]),
        },
        "recall_by_flag": recall_by_flag(test_rows, truth_obj, pred_half, pred_cut),
    }

    lens_idx = [j for j, c in enumerate(columns) if c in LENS_COLUMNS]
    if lens_idx:
        y_len_true = y_true[:, lens_idx]
        y_len_score = y_score[:, lens_idx]
        macro_len, ap_len = macro_ap(y_len_true, y_len_score, LENS_COLUMNS)
        at_half_len = precision_recall_f1(y_len_true, y_len_score, DEFAULT_THRESHOLD, LENS_COLUMNS)
        cut_len = np.array([thresholds[c]["threshold"] for c in LENS_COLUMNS])
        pred_len_half = (y_len_score >= DEFAULT_THRESHOLD).astype(int)
        pred_len_cut = (y_len_score >= cut_len).astype(int)
        truth_len = y_len_true.astype(int)
        judgeable = {c: v for c, v in ap_len.items() if at_half_len[c]["support"] >= 20}

        per_lens = {}
        for j, column in enumerate(LENS_COLUMNS):
            tp = float(((pred_len_cut[:, j] == 1) & (truth_len[:, j] == 1)).sum())
            fp = float(((pred_len_cut[:, j] == 1) & (truth_len[:, j] == 0)).sum())
            fn = float(((pred_len_cut[:, j] == 0) & (truth_len[:, j] == 1)).sum())
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            per_lens[column] = {
                "name": dict(LP_TAGS)[column],
                "support": at_half_len[column]["support"],
                "auprc": ap_len.get(column, float("nan")),
                "threshold": thresholds[column]["threshold"],
                "threshold_source": thresholds[column]["source"],
                "precision_0.5": at_half_len[column]["precision"],
                "recall_0.5": at_half_len[column]["recall"],
                "f1_0.5": at_half_len[column]["f1"],
                "precision_chosen": precision,
                "recall_chosen": recall,
                "f1_chosen": f1,
            }
        macro_f1_half = float(np.mean([at_half_len[c]["f1"] for c in judgeable])) \
            if judgeable else float("nan")
        macro_f1_cut = float(np.mean([per_lens[c]["f1_chosen"] for c in judgeable])) \
            if judgeable else float("nan")
        result["lens"] = {
            "macro_auprc": macro_len,
            "macro_auprc_judgeable": float(np.mean(list(judgeable.values())))
            if judgeable else float("nan"),
            "judgeable_classes": sorted(judgeable),
            "macro_f1_0.5": macro_f1_half,
            "macro_f1_chosen": macro_f1_cut,
            "exact_match_0.5": float((pred_len_half == truth_len).all(axis=1).mean()),
            "exact_match_chosen": float((pred_len_cut == truth_len).all(axis=1).mean()),
            "hamming_0.5": float((pred_len_half != truth_len).mean()),
            "hamming_chosen": float((pred_len_cut != truth_len).mean()),
            "per_class": per_lens,
        }
    return result


def evaluate_test_cond15(y_true, y_score, columns):
    """AUPRC and F1 for the fifteen condition columns. No object/gate split."""
    macro, ap = macro_ap(y_true, y_score, columns)
    at_half = precision_recall_f1(y_true, y_score, DEFAULT_THRESHOLD, columns)
    return {"rows": int(y_true.shape[0]), "macro_ap_cond15": macro,
            "per_class": at_half, "ap": ap}


def evaluate_test_frozen17(y_true, y_score, test_rows, thresholds, columns):
    """The frozen read: all 17 columns, at 0.5 and at the validation cuts.

    Every column gets support, prevalence, AUPRC, its chosen threshold, and
    precision, recall and F1 at both cuts. The seven object columns also get the
    Bubble/Cluster joint confusion and recall split by the size flag. The gate
    flags are auxiliary; they never enter a metric as truth.
    """
    truth = y_true.astype(int)
    at_half = precision_recall_f1(y_true, y_score, DEFAULT_THRESHOLD, columns)
    macro, ap = macro_ap(y_true, y_score, columns)
    cut = np.array([thresholds[c]["threshold"] for c in columns])
    pred_half = (y_score >= DEFAULT_THRESHOLD).astype(int)
    pred_cut = (y_score >= cut).astype(int)
    name_of = dict(LP_TAGS + OBJECT_TAGS)

    per_class = {}
    f1_half, f1_cut = [], []
    n_rows = truth.shape[0]
    for j, column in enumerate(columns):
        tp = float(((pred_cut[:, j] == 1) & (truth[:, j] == 1)).sum())
        fp = float(((pred_cut[:, j] == 1) & (truth[:, j] == 0)).sum())
        fn = float(((pred_cut[:, j] == 0) & (truth[:, j] == 1)).sum())
        tp_05 = int(((pred_half[:, j] == 1) & (truth[:, j] == 1)).sum())
        fp_05 = int(((pred_half[:, j] == 1) & (truth[:, j] == 0)).sum())
        fn_05 = int(((pred_half[:, j] == 0) & (truth[:, j] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[column] = {
            "name": name_of.get(column, column),
            "support": int(truth[:, j].sum()),
            "prevalence": round(float(truth[:, j].mean()), 6),
            "auprc": ap.get(column, float("nan")),
            "threshold": thresholds[column]["threshold"],
            "threshold_source": thresholds[column]["source"],
            "precision_0.5": at_half[column]["precision"],
            "recall_0.5": at_half[column]["recall"],
            "f1_0.5": at_half[column]["f1"],
            "fired_0.5": int((pred_half[:, j] == 1).sum()),
            "tp_0.5": tp_05, "fp_0.5": fp_05, "fn_0.5": fn_05,
            "tn_0.5": int(n_rows - tp_05 - fp_05 - fn_05),
            "precision_chosen": precision,
            "recall_chosen": recall,
            "f1_chosen": f1,
            "fired_chosen": int((pred_cut[:, j] == 1).sum()),
            "tp_chosen": int(tp), "fp_chosen": int(fp), "fn_chosen": int(fn),
            "tn_chosen": int(n_rows - tp - fp - fn),
        }
        f1_half.append(at_half[column]["f1"])
        f1_cut.append(f1)

    obj_idx = [j for j, c in enumerate(columns) if c in OBJECT_COLUMNS]
    truth_obj = truth[:, obj_idx]
    pred_obj_half = pred_half[:, obj_idx]
    pred_obj_cut = pred_cut[:, obj_idx]
    pair_idx = [OBJECT_COLUMNS.index("class_bubble"),
                OBJECT_COLUMNS.index("class_bubble_cluster")]

    return {
        "rows": len(test_rows),
        "macro_auprc": macro,
        "macro_f1_0.5": float(np.mean(f1_half)),
        "macro_f1_chosen": float(np.mean(f1_cut)),
        "per_class": per_class,
        "bubble_cluster_confusion": {
            "note": ("test split, truth pair vs predicted pair, order "
                     + " / ".join(JOINT_ORDER)),
            "at_0.5": bubble_cluster_confusion(truth_obj[:, pair_idx],
                                               pred_obj_half[:, pair_idx]),
            "at_chosen": bubble_cluster_confusion(truth_obj[:, pair_idx],
                                                  pred_obj_cut[:, pair_idx]),
        },
        "recall_by_flag": recall_by_flag(test_rows, truth_obj,
                                         pred_obj_half, pred_obj_cut),
    }


def evaluate_test_gate4(y_true, y_score, test_rows, thresholds, columns):
    """The test read for the four gate columns.

    Truth is the gate column itself, so one column answers one question: gated
    against unflagged. Every metric here is read on that truth, at 0.5 and at
    the validation-chosen cut; there is no class/gate split to reconcile and no
    Bubble/Cluster or lens block in this label space.
    """
    truth = y_true.astype(int)
    cut = np.array([thresholds[c]["threshold"] for c in columns])
    pred_half = (y_score >= DEFAULT_THRESHOLD).astype(int)
    pred_cut = (y_score >= cut).astype(int)

    per_class = {}
    auprc = {}
    f1_half, f1_cut = [], []
    for j, column in enumerate(columns):
        ap = average_precision(truth[:, j], y_score[:, j])
        auprc[column] = ap
        at_half = precision_recall_f1(truth[:, j:j + 1], y_score[:, j:j + 1],
                                      DEFAULT_THRESHOLD, [column])[column]

        def read(pred):
            tp = float(((pred[:, j] == 1) & (truth[:, j] == 1)).sum())
            fp = float(((pred[:, j] == 1) & (truth[:, j] == 0)).sum())
            fn = float(((pred[:, j] == 0) & (truth[:, j] == 1)).sum())
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            return precision, recall, f1, int((pred[:, j] == 1).sum())

        precision, recall, f1, fired = read(pred_cut)
        per_class[column] = {
            "name": dict(GATE4_TAGS)[column],
            "support": int(truth[:, j].sum()),
            "negatives": int(len(truth) - truth[:, j].sum()),
            "test_prevalence": round(float(truth[:, j].mean()), 6),
            "auprc": ap,
            "threshold": thresholds[column]["threshold"],
            "threshold_source": thresholds[column]["source"],
            "precision_0.5": at_half["precision"],
            "recall_0.5": at_half["recall"],
            "f1_0.5": at_half["f1"],
            "fired_0.5": int((pred_half[:, j] == 1).sum()),
            "precision_chosen": precision,
            "recall_chosen": recall,
            "f1_chosen": f1,
            "fired_chosen": fired,
        }
        f1_half.append(at_half["f1"])
        f1_cut.append(f1)

    judged = [c for c in columns if not np.isnan(auprc[c])]
    return {
        "rows": len(test_rows),
        "note": ("gate4: truth is the gate column, one column per gated class, "
                 "gated against unflagged"),
        "macro_auprc": float(np.mean([auprc[c] for c in judged])) if judged else float("nan"),
        "per_class": per_class,
        "macro_f1_0.5": float(np.mean(f1_half)),
        "macro_f1_chosen": float(np.mean(f1_cut)),
    }


# ---------------------------------------------------------------- part 3: torch

def build_model(n_outputs, arch="resnet50"):
    import torch.nn as nn
    from torchvision import models

    if arch != "resnet50":
        raise SystemExit(f"arch {arch} not implemented in this file; start with resnet50")
    weights = models.ResNet50_Weights.IMAGENET1K_V2
    model = models.resnet50(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, n_outputs)
    return model


class LensDataset:
    """Yields (image, training target, evaluation truth).

    target and truth differ only in the four gated slots of a gate arm; every
    metric reads truth, only the loss reads target.
    """

    def __init__(self, rows, image_root, imgsz=224):
        self.rows = rows
        self.image_root = Path(image_root) if image_root else None
        self.imgsz = imgsz

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        import torch
        from PIL import Image
        from torchvision import transforms

        row = self.rows[index]
        if self.image_root is None:
            raise SystemExit("image root not set: pass --image-root or set FMD_IMAGE_ROOT")
        path = self.image_root / row["image_path"]
        if not path.is_file():
            raise SystemExit(f"image not found: {path}")
        transform = transforms.Compose([
            transforms.Resize((self.imgsz, self.imgsz)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        with Image.open(path) as img:
            tensor = transform(img.convert("RGB"))
        target = torch.tensor(row["target"], dtype=torch.float32)
        truth = torch.tensor(row["truth"], dtype=torch.float32)
        return tensor, target, truth


def pos_weight_from(rows, n_cols):
    """Per-class (N - n) / n on the training targets of these rows."""
    import torch
    counts = np.zeros(n_cols, dtype=np.float64)
    for row in rows:
        counts += np.array(row["target"], dtype=np.float64)
    negatives = len(rows) - counts
    weights = np.where(counts > 0, negatives / np.maximum(counts, 1), 1.0)
    return torch.tensor(weights, dtype=torch.float32)


def predict(model, loader, device):
    import torch
    model.eval()
    scores, truths = [], []
    with torch.no_grad():
        for images, _target, truth in loader:
            images = images.to(device)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
            scores.append(torch.sigmoid(logits).float().cpu().numpy())
            truths.append(truth.numpy())
    return np.concatenate(truths, axis=0), np.concatenate(scores, axis=0)


def run_training(rows, columns, args):
    """Train on train, choose thresholds on val, read the test split once."""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_cols = len(columns)
    gate4 = args.columns == "gate4"
    cond15 = args.columns == "cond15"
    frozen17 = args.columns == "frozen17"
    table_path = table_of(args)
    table_md5 = md5_of(table_path)

    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    test_rows = [r for r in rows if r["split"] == "test"]
    if not train_rows or not val_rows or not test_rows:
        raise SystemExit(f"empty split: {len(train_rows)} train / {len(val_rows)} val / "
                         f"{len(test_rows)} test")

    loaders = {}
    for name, part in (("train", train_rows), ("val", val_rows), ("test", test_rows)):
        loaders[name] = DataLoader(
            LensDataset(part, args.image_root, args.imgsz), batch_size=args.batch,
            shuffle=(name == "train"), num_workers=args.workers,
            pin_memory=(device.type == "cuda"))

    model = build_model(n_cols, args.arch).to(device)
    weight = pos_weight_from(train_rows, n_cols).to(device) if args.pos_weight == "on" else None
    criterion = nn.BCEWithLogitsLoss(pos_weight=weight)
    pos_weight_vector = None
    if gate4:
        # The Experiment 3.1 arm is weighted by inverse frequency on the train
        # split only: (N - n) / n per gate column, N = train rows. Recorded in
        # the run record so the weighting is readable without the table.
        base = pos_weight_from(train_rows, n_cols)
        pos_weight_vector = {c: round(float(v), 3) for c, v in zip(columns, base)}
        print("pos_weight on train only: "
              + ", ".join(f"{c} {v:.1f}" for c, v in pos_weight_vector.items()),
              flush=True)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9,
                                nesterov=True, weight_decay=1e-4)
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda"))

    history = []
    started = time.time()
    train_started = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for images, targets, _truth in loaders["train"]:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
                loss = criterion(logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach()) * images.size(0)
        mean_loss = total_loss / len(train_rows)
        history.append({"epoch": epoch, "train_loss": mean_loss})
        print(f"epoch {epoch:02d}/{args.epochs}  train loss {mean_loss:.4f}", flush=True)
    train_seconds = time.time() - train_started

    # The validation read. This is the only place a threshold is chosen, and it
    # happens before the test split is touched. val truth is class-level for the
    # object columns whatever this arm trained on.
    val_started = time.time()
    val_true, val_score = predict(model, loaders["val"], device)
    thresholds = choose_thresholds(val_true, val_score, columns, args.min_val_positives,
                                  extend_ceiling=gate4)
    val_seconds = time.time() - val_started
    tuned = [c for c in columns if thresholds[c]["source"] == "val"]
    print(f"thresholds chosen on {len(val_rows)} val pictures: "
          f"{len(tuned)} tuned, {len(columns) - len(tuned)} default", flush=True)
    for c in columns:
        t = thresholds[c]
        print(f"  {c:24s} {t['threshold']:.2f}  ({t['source']}, "
              f"val F1 {t['val_f1_at_threshold']:.3f} vs {t['val_f1_at_0.5']:.3f} at 0.5)")

    # The test read, once.
    test_started = time.time()
    test_true, test_score = predict(model, loaders["test"], device)
    test_seconds = time.time() - test_started

    if gate4:
        metrics = evaluate_test_gate4(test_true, test_score, test_rows, thresholds, columns)
        metrics["primary"] = {"name": "macro_auprc_four_gates",
                              "value": metrics["macro_auprc"]}
    elif cond15:
        metrics = evaluate_test_cond15(test_true, test_score, columns)
        metrics["primary"] = {"name": "macro_ap_cond15",
                              "value": metrics["macro_ap_cond15"]}
    elif frozen17:
        metrics = evaluate_test_frozen17(test_true, test_score, test_rows,
                                         thresholds, columns)
        metrics["primary"] = {"name": "macro_auprc_17",
                              "value": metrics["macro_auprc"]}
    else:
        metrics = evaluate_test(test_true, test_score, test_rows, thresholds, columns)
        metrics["primary"] = {"name": "macro_ap_supported",
                              "value": metrics["macro_ap_supported"]}
    metrics["columns_mode"] = args.columns
    metrics["gated_target"] = "ignored" if (gate4 or cond15 or frozen17) else args.gated_target
    metrics["thresholds"] = {
        "objective": "maximum F1 per class on the validation split",
        "grid": THRESHOLD_GRID,
        "default_threshold": DEFAULT_THRESHOLD,
        "min_val_positives": args.min_val_positives,
        "per_class": thresholds,
        "tuned": tuned,
        "default": [c for c in columns if thresholds[c]["source"] != "val"],
    }
    if gate4 or cond15:
        if gate4:
            metrics["thresholds"]["ceiling_extension"] = CEILING_GRID
        metrics["thresholds"]["ceiling_rule"] = (
            "the grid runs 0.05 to 0.95 and extends to 0.99 only when the maximum F1 "
            "lands on 0.95; ties go to the higher cut")
        metrics["split"] = {
            "path": table_path.relative_to(ROOT).as_posix() if table_path.is_relative_to(ROOT)
            else str(table_path),
            "md5": table_md5,
            "source": ("split column of the gate4 label table" if gate4
                       else "split column of the cond15 label table"),
            "counts": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
            "frozen": GATE4_EXPECTED_SPLIT if gate4 else COND15_EXPECTED_SPLIT,
        }
    elif frozen17:
        split_path = table_path.parent / "split.csv"
        gates_path = table_path.parent / "gates_4.csv"
        metrics["split"] = {
            "path": table_path.relative_to(ROOT).as_posix()
            if table_path.is_relative_to(ROOT) else str(table_path),
            "md5": table_md5,
            "source": "split column of the frozen17 label table",
            "counts": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
            "frozen": FROZEN17_EXPECTED_SPLIT,
            "split_file": split_path.relative_to(ROOT).as_posix()
            if split_path.is_relative_to(ROOT) else str(split_path),
            "split_file_md5": md5_of(split_path) if split_path.is_file() else None,
            "gates_file": gates_path.relative_to(ROOT).as_posix()
            if gates_path.is_relative_to(ROOT) else str(gates_path),
            "gates_file_md5": md5_of(gates_path) if gates_path.is_file() else None,
        }
    else:
        metrics["split"] = {
            "path": str(SPLIT), "md5": md5_of(SPLIT),
            "counts": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
        }
    metrics["config"] = {
        "columns": args.columns,
        "gated_target": "ignored" if (gate4 or frozen17) else args.gated_target,
        "pos_weight": args.pos_weight,
        "output_columns": columns,
        "arch": args.arch, "imgsz": args.imgsz, "batch": args.batch,
        "epochs": args.epochs, "lr": args.lr, "seed": args.seed,
        "device": str(device), "split_shape": "70/15/15",
        "threshold_source": "val",
        "recipe": ("resnet50, 224, batch 8, 50 epochs, no early stopping, "
                   "SGD lr 1e-4 momentum 0.9 (nesterov, weight decay 1e-4), "
                   "seed 42, BCEWithLogitsLoss"),
        "table": table_path.relative_to(ROOT).as_posix()
        if table_path.is_relative_to(ROOT) else str(table_path),
        "table_md5": table_md5,
        "split_md5": (table_md5 if gate4 else
                      md5_of(table_path.parent / "split.csv") if frozen17 else SPLIT_MD5),
        "truth": ("the gate column itself: gated against unflagged"
                  if gate4 else
                  "class-level for all 17 columns; no gate swap"
                  if frozen17 else
                  "class-level for the object columns whatever the arm trained on"),
    }
    if gate4:
        metrics["config"]["pos_weight_vector"] = pos_weight_vector
        metrics["config"]["pos_weight_rule"] = "(N - n) / n on the train split only"
        metrics["config"]["counts_asserted"] = args.expect_counts == "on"
    metrics["predictions_keys"] = ["val_md5", "val_image_path", "val_true", "val_score", "val_gate",
                                   "test_md5", "test_image_path", "test_true", "test_score", "test_gate",
                                   "columns", "gated_columns"]
    metrics["timing"] = {
        "seconds_total": round(time.time() - started, 1),
        "seconds_training": round(train_seconds, 1),
        "seconds_per_epoch": round(train_seconds / args.epochs, 1),
        "seconds_validation": round(val_seconds, 1),
        "seconds_inference": round(test_seconds, 1),
        "inference_images": len(test_rows),
        "inference_ms_per_image": round(1000.0 * test_seconds / max(len(test_rows), 1), 2),
    }
    metrics["history"] = history

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Save the raw scores as well as the summary. With these, any threshold can be
    # re-read on a laptop without the GPU, and a threshold chosen on val can be
    # applied to the test scores later without another training run. The gate
    # flags ride along so recall-by-flag can be recomputed from this file alone.
    np.savez_compressed(
        out_dir / "predictions.npz",
        val_md5=np.array([r["md5"] for r in val_rows]),
        val_image_path=np.array([r["image_path"] for r in val_rows]),
        val_true=val_true, val_score=val_score,
        val_gate=np.array([r["gate"] for r in val_rows], dtype=np.int64),
        test_md5=np.array([r["md5"] for r in test_rows]),
        test_image_path=np.array([r["image_path"] for r in test_rows]),
        test_true=test_true, test_score=test_score,
        test_gate=np.array([r["gate"] for r in test_rows], dtype=np.int64),
        columns=np.array(columns),
        gated_columns=np.array(columns if gate4 else GATE_ORDER),
    )
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    with open(out_dir / "thresholds.json", "w", encoding="utf-8") as fh:
        record = {"columns": args.columns,
                  "gated_target": "ignored" if (gate4 or frozen17) else args.gated_target,
                  "split": metrics["split"],
                  "objective": metrics["thresholds"]["objective"],
                  "grid": THRESHOLD_GRID, "per_class": thresholds}
        if gate4:
            record["ceiling_extension"] = CEILING_GRID
            record["ceiling_rule"] = metrics["thresholds"]["ceiling_rule"]
        json.dump(record, fh, indent=2)
    torch.save(model.state_dict(), out_dir / "final.pt")
    print(f"metrics written: {out_dir / 'metrics.json'}")
    print(f"thresholds written: {out_dir / 'thresholds.json'}")
    t = metrics["timing"]
    print(f"timing: train {t['seconds_training']}s ({t['seconds_per_epoch']}s/epoch), "
          f"val {t['seconds_validation']}s, test {t['seconds_inference']}s = "
          f"{t['inference_ms_per_image']} ms/image on {t['inference_images']} test pictures")
    if gate4:
        print(f"primary: {metrics['primary']['name']} = {metrics['primary']['value']:.4f}")
    else:
        if "macro_ap_supported" in metrics:
            print(f"primary: macro AP over the seven supported classes = "
                  f"{metrics['macro_ap_supported']:.4f}")
        else:
            print(f"primary: {metrics['primary']['name']} = "
                  f"{metrics['primary']['value']:.4f}")
    return metrics


def dump_predictions(rows, columns, args):
    """Re-run inference from a saved checkpoint and write predictions.npz. No training."""
    import torch
    from torch.utils.data import DataLoader

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out)
    ckpt = out_dir / "final.pt"
    if not ckpt.is_file():
        raise SystemExit(f"no checkpoint at {ckpt}")
    model = build_model(len(columns), args.arch).to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
    arrays = {}
    for name in ("val", "test"):
        part = [r for r in rows if r["split"] == name]
        loader = DataLoader(LensDataset(part, args.image_root, args.imgsz),
                            batch_size=args.batch, shuffle=False, num_workers=args.workers)
        truth, score = predict(model, loader, device)
        arrays[name] = (truth, score, [r["md5"] for r in part],
                        [r["image_path"] for r in part],
                        np.array([r["gate"] for r in part], dtype=np.int64))
        print(f"{name}: {len(part)} pictures scored")
    np.savez_compressed(
        out_dir / "predictions.npz",
        val_md5=np.array(arrays["val"][2]),
        val_image_path=np.array(arrays["val"][3]),
        val_true=arrays["val"][0], val_score=arrays["val"][1],
        val_gate=arrays["val"][4],
        test_md5=np.array(arrays["test"][2]),
        test_image_path=np.array(arrays["test"][3]),
        test_true=arrays["test"][0],
        test_score=arrays["test"][1], test_gate=arrays["test"][4],
        columns=np.array(columns),
        gated_columns=np.array(columns if args.columns == "gate4" else GATE_ORDER),
    )
    print(f"predictions written: {out_dir / 'predictions.npz'}")


def run_smoke(rows, columns, args):
    """Two optimizer steps on random tensors, plus the label-side proofs."""
    import torch
    import torch.nn as nn

    n_cols = len(columns)
    model = build_model(n_cols, args.arch)
    train_rows = [r for r in rows if r["split"] == "train"]
    weight = pos_weight_from(train_rows, n_cols) if args.pos_weight == "on" else None
    criterion = nn.BCEWithLogitsLoss(pos_weight=weight)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, nesterov=True)
    images = torch.randn(2, 3, args.imgsz, args.imgsz)
    targets = torch.randint(0, 2, (2, n_cols)).float()
    for step in range(2):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(images), targets)
        loss.backward()
        optimizer.step()
        print(f"smoke step {step + 1}: loss {float(loss.detach()):.4f}, "
              f"output {tuple(model(images).shape)}")
    # Prove the threshold chooser runs on a known array as well as the model.
    y_true = np.array([[1], [1], [0], [0], [1], [0]], dtype=float)
    y_score = np.array([[0.9], [0.2], [0.8], [0.1], [0.3], [0.4]])
    chosen = choose_thresholds(y_true, y_score, ["toy"])
    print(f"threshold chooser ok: {chosen['toy']['threshold']} "
          f"(val F1 {chosen['toy']['val_f1_at_threshold']:.3f})")
    # Prove the gated-target switch changed the training targets, using the
    # real train rows this run would have trained on. gate4 has no switch: its
    # four outputs are the gate columns themselves.
    gated_columns = list(GATE4_COLUMNS) if args.columns == "gate4" else list(GATED_COLUMNS)
    gated_positives = {}
    for class_column in gated_columns:
        j = columns.index(class_column)
        gated_positives[class_column] = int(sum(r["target"][j] for r in train_rows))
    print(f"train target positives under --gated-target {args.gated_target}: "
          + ", ".join(f"{c}={n}" for c, n in gated_positives.items()))
    if weight is not None:
        print(f"pos_weight on: min {float(weight.min()):.2f} max {float(weight.max()):.2f}, "
              f"first three { [round(float(v), 2) for v in weight[:3]] }")
    else:
        print("pos_weight off: plain BCEWithLogitsLoss")
    print(f"smoke ok: columns {args.columns}, gated target {args.gated_target}, "
          f"pos-weight {args.pos_weight}, {n_cols} outputs")


# ---------------------------------------------------------------- command line

def table_of(args):
    """The label table this run reads: gate4 defaults to its own, else the v8 table."""
    if args.table:
        return Path(args.table)
    if args.columns == "gate4":
        return GATE4_TABLE
    if args.columns == "cond15":
        return COND15_TABLE
    if args.columns == "frozen17":
        return FROZEN17_TABLE
    return TABLE


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--columns", choices=["ooi", "combined", "gate4", "cond15", "frozen17"],
                        default="ooi",
                        help="ooi = 7 object columns, combined = 12 lens + 7 object, "
                             "gate4 = the four Experiment 3.1 gate columns, "
                             "cond15 = the twelve lens columns plus the three non-gated "
                             "object classes (Experiment 3.2), "
                             "frozen17 = the frozen split, 10 lens + 7 object")
    parser.add_argument("--gated-target", choices=["class", "gate"], default="class",
                        help="which column group feeds the four gated classes "
                             "(ignored by --columns gate4 and frozen17)")
    parser.add_argument("--pos-weight", choices=["on", "off"], default=None,
                        help="per-class (N - n) / n on the train split only; default "
                             "on for gate4, cond15 and frozen17, off otherwise")
    parser.add_argument("--table", default="",
                        help="label table path; default is the v8 table, the "
                             "Experiment 3.1 table for gate4, the Experiment 3.2 "
                             "table for cond15, or the frozen table for frozen17")
    parser.add_argument("--expect-counts", choices=["on", "off"], default="on",
                        help="off skips the frozen count assertions; synthetic tables only")
    parser.add_argument("--labels-only", action="store_true",
                        help="print the per-split counts and stop")
    parser.add_argument("--smoke", action="store_true",
                        help="two-batch step on random tensors, needs torch")
    parser.add_argument("--dump-predictions", action="store_true",
                        help="score val and test from --out/final.pt and write predictions.npz")
    parser.add_argument("--image-root", default=os.environ.get("FMD_IMAGE_ROOT", ""))
    parser.add_argument("--out", default="")
    parser.add_argument("--arch", default="resnet50")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-val-positives", type=int, default=MIN_VAL_POSITIVES,
                        help="a class below this many val positives keeps 0.5")
    args = parser.parse_args()

    if args.pos_weight is None:
        args.pos_weight = "on" if args.columns in ("gate4", "cond15", "frozen17") else "off"

    raw = read_table(args.columns, table_of(args), expect_counts=args.expect_counts == "on")

    if args.labels_only:
        labels_report(raw, args)
        return

    rows, columns = build_rows(raw, args.columns, args.gated_target, with_paths=True)

    if args.smoke:
        run_smoke(rows, columns, args)
        return

    if not args.image_root:
        raise SystemExit("set --image-root or FMD_IMAGE_ROOT before training")

    root = Path(args.image_root)
    step = max(1, len(rows) // 40)
    sample = rows[::step][:40]
    missing = [r["image_path"] for r in sample if not (root / r["image_path"]).is_file()]
    if missing:
        raise SystemExit(
            f"{len(missing)} of {len(sample)} sampled pictures are not under {root}\n"
            f"  expected layout: <root>/<top folder>/<class folder>/<file>\n"
            f"  first missing: {missing[0]}\n"
            f"  the root must hold all three top folders, not one of them")
    print(f"image root ok: {len(sample)} sampled pictures found under {root}")
    if not args.out:
        if args.columns == "frozen17":
            raise SystemExit("pass --out for frozen17: the run folder in the experiment tree")
        if args.columns == "gate4":
            arm = "gate4"
        else:
            arm = args.gated_target if args.columns == "ooi" else f"combined_{args.gated_target}"
        if args.pos_weight == "on" and args.columns not in ("gate4", "cond15"):
            arm = f"{arm}_posw"
        args.out = str(ROOT / f"run/multilabel_ooi_20261104/{arm}")
    if args.dump_predictions:
        dump_predictions(rows, columns, args)
        return
    run_training(rows, columns, args)


if __name__ == "__main__":
    main()
