"""Build the Experiment 3.1 derived split and the 4-column size-gate label table.

Ticket: docs/wayfinder/tickets/037-exp3-1-split-label-table.md
Map:    docs/wayfinder/exp3_1_size_gate_20261116.md

Reads the frozen annotation export and split v8, and writes, under
run/split_exp3_1_20261116/:

    split.csv          picture_md5,group_id,split
    labels.csv         picture_md5,image_path,split,fm_gated,fiber_gated,ep_gated,hema_gated
    picture_detail.csv presence, gate, decisive and largest-box columns
    meta.json          rule, input md5s, counts

Split v8 is read only. Nothing in Experiment 1 or 2 is touched.

Counting rules
--------------
Identity is picture_md5 (the export is already one annotation per picture with
the newest file winning, so a picture appears once per annotation element).

A picture *carries* a class when it has a shape_kind == box row with that
class's canonical id. HEMA is any of hema, hema_obstruction, hema_fragment.

A picture is *size-flagged* for a class when it carries that class's gate code
as a tag row. Unflagged = class box present and that class's gate code absent.
The gate is a subset of its class and is never a label of its own.

Move rule (union over the four classes, because one model is scored on one
split): a picture leaves train or validation for test when it carries a box of
any of the four classes without that class's gate tag. A picture gated in every
gated class it carries keeps its v8 assignment. A picture outside v8 that is
unflagged for any of the four classes is added as a test row. The move rule does
not depend on the decisive columns.

Decisive, for a class: the picture carries that class unflagged, and carries no
other fail label, where an other fail label is any of the 12 lens canonical ids
in a box row or a tag row, wet_package, bubble_cluster, surface_groove, or
another of the four classes present and gated.

See CORRECTION_NOTE for the superseded decisive totals and for the missing_lens
alias, which is recorded rather than silently resolved.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LABELS_CSV = REPO / "run/eda_full_20261029/resolved_labels.csv"
PICTURE_TABLE = REPO / "run/eda_full_20261029/picture_table.csv"
V8_SPLIT = REPO / "run/split_20261103_v8/split_70_15_15.csv"
OUT_DIR = REPO / "run/split_exp3_1_20261116"

MD5_LABELS = "f61ea0b90df095ebe52d1332f8bfdb8a"
MD5_PICTURES = "a03ddeead53bae370c17bd8ea15c0df0"
MD5_V8 = "1a71d66d2de384cf47a3fcf7d9115baa"

VERSION = "exp3_1_v1"
DATE = "2026-11-16"

# class key -> canonical box id that proves presence
CLASS_BOX = {
    "fm": "foreign_matter",
    "fiber": "fiber",
    "ep": "extraneous_polymer",
}
HEMA_BOX = {"hema", "hema_obstruction", "hema_fragment"}

# class key -> the tag row code that proves the size gate fired
CLASS_GATE_CODE = {
    "fm": "P3_FM_MICRON_THRESHOLD",
    "fiber": "P3_FIB_MICRON_THRESHOLD",
    "ep": "P3_EP_MICRON_THRESHOLD",
    "hema": "P3_HE_MICRON_THRESHOLD",
}

KEYS = ["fm", "fiber", "ep", "hema"]

# The 12 canonical lens ids, exactly as the ticket names them, applied to box
# rows and tag rows alike (in this export they only ever occur as tag rows).
#
# "no_lens" is named but never occurs in the export; the export spells it
# "missing_lens" (code P1_NL, 326 pictures). Counting that alias is deliberately
# NOT done: it moves foreign matter decisive from 51 to 42 and extraneous
# polymer from 34 to 33, against the totals asserted for this build. The alias
# arithmetic is exposed per row so the choice stays auditable.
LENS_IDS = {
    "missing_primary_package",
    "multiple_lenses",
    "lens_off_center",
    "dirty_camera",
    "no_lens",
    "folded_lens",
    "low_dose",
    "cavity_off_center",
    "dirty_strobe",
    "view_obstructed",
    "bubble_scatter",
    "package_misalignment",
}
NO_LENS_ALIAS = "missing_lens"

# Non-class fail labels that disqualify a picture from a decisive call.
OTHER_BOX_FAIL = {"wet_package", "bubble_cluster", "surface_groove"}

CORRECTION_NOTE = (
    "The map and the ticket print decisive totals of foreign matter 105, fiber "
    "18, polymer 37, HEMA 6 (160 pictures). Those came from a tag-blind scratch "
    "calculation and are superseded on 2026-11-16: decisive counts lens "
    "canonical ids carried as tag rows, not only lens boxes. The totals this "
    "build asserts are foreign matter 51 (36 outside v8), fiber 14 (13), "
    "polymer 34 (33), HEMA 3 (3), i.e. 102 decisive pictures, with 329 / 29 / 6 "
    "/ 3 unflagged pictures failing on another fail label. Separately, the "
    "export has no canonical_id 'no_lens'; it uses 'missing_lens' (P1_NL). "
    "Counting that alias as a lens id gives 42 / 14 / 33 / 3, so it is not "
    "counted, and picture_detail.csv carries trailing columns showing the "
    "arithmetic under both readings."
)

# Every asserted count. Asserted, never adjusted.
EXPECT_ROWS = 7555
EXPECT_SPLIT = {"train": 4964, "val": 1058, "test": 1533}
EXPECT_MOVED = 327
EXPECT_ADDED = 85
EXPECT_ALREADY_TEST_UNFLAGGED = 41

EXPECT_PRESENT = {"fm": 834, "fiber": 405, "ep": 175, "hema": 157}
EXPECT_UNFLAGGED = {"fm": 380, "fiber": 43, "ep": 40, "hema": 6}
# class -> (train gated, val gated, test gated, test unflagged)
EXPECT_BY_SPLIT = {
    "fm": (315, 60, 79, 380),
    "fiber": (195, 43, 124, 43),
    "ep": (81, 14, 40, 40),
    "hema": (79, 20, 52, 6),
}
# class -> (decisive total, decisive outside v8), corrected 16 November
EXPECT_DECISIVE = {"fm": (51, 36), "fiber": (14, 13), "ep": (34, 33), "hema": (3, 3)}
# class -> unflagged pictures that fail on another fail label
EXPECT_OTHER_FAIL = {"fm": 329, "fiber": 29, "ep": 6, "hema": 3}


class CountMismatch(RuntimeError):
    """An asserted count did not reproduce. Never continues past this."""


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_inputs() -> dict[str, str]:
    triples = [
        (LABELS_CSV, MD5_LABELS),
        (PICTURE_TABLE, MD5_PICTURES),
        (V8_SPLIT, MD5_V8),
    ]
    for path, want in triples:
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        got = md5_of(path)
        if got != want:
            raise SystemExit(f"md5 mismatch on {path}: want {want}, got {got}")
    return {
        str(p.relative_to(REPO)).replace("\\", "/"): want for p, want in triples
    }


def read_annotations():
    """Return per-picture presence, gate, lens, other fail, alias lens, largest box."""
    present: dict[str, set[str]] = {}
    gated: dict[str, set[str]] = {}
    lens: dict[str, set[str]] = {}
    other: dict[str, set[str]] = {}
    alias_lens: dict[str, set[str]] = {}
    largest: dict[tuple[str, str], float] = {}

    code_to_key = {v: k for k, v in CLASS_GATE_CODE.items()}

    with LABELS_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            md5 = row["picture_md5"].strip()
            if not md5:
                continue
            cid = (row["canonical_id"] or "").strip()
            kind = (row["shape_kind"] or "").strip()

            # lens ids and non-class fail labels disqualify on box or tag rows
            if cid in LENS_IDS:
                lens.setdefault(md5, set()).add(cid)
            if cid == NO_LENS_ALIAS:
                alias_lens.setdefault(md5, set()).add(cid)
            if cid in OTHER_BOX_FAIL:
                other.setdefault(md5, set()).add(cid)

            if kind == "box":
                key = None
                for k, box_id in CLASS_BOX.items():
                    if cid == box_id:
                        key = k
                        break
                if key is None and cid in HEMA_BOX:
                    key = "hema"
                if key is not None:
                    present.setdefault(md5, set()).add(key)
                    side = max(
                        abs(float(row["xbr"]) - float(row["xtl"])),
                        abs(float(row["ybr"]) - float(row["ytl"])),
                    )
                    prev = largest.get((md5, key))
                    if prev is None or side > prev:
                        largest[(md5, key)] = side

            elif kind == "tag":
                key = code_to_key.get((row["code"] or "").strip())
                if key is not None:
                    gated.setdefault(md5, set()).add(key)

    return present, gated, lens, other, alias_lens, largest


def read_v8() -> dict[str, str]:
    out: dict[str, str] = {}
    with V8_SPLIT.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[row["picture_md5"].strip()] = row["split"].strip()
    return out


def read_paths() -> dict[str, str]:
    out: dict[str, str] = {}
    with PICTURE_TABLE.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[row["md5"].strip()] = row["winning_path"]
    return out


def unflagged(classes: set[str], gates: set[str]) -> set[str]:
    return {c for c in classes if c not in gates}


def is_decisive(
    key: str, classes: set[str], gates: set[str], lens: set[str], other: set[str]
) -> bool:
    """Decisive for `key`: that class unflagged and no other fail label present."""
    if key not in classes or key in gates:
        return False
    if lens or other:
        return False
    return not any(c != key and c in gates for c in classes)


def build() -> int:
    inputs = check_inputs()
    present, gated, lens, other, alias_lens, largest = read_annotations()
    v8 = read_v8()
    paths = read_paths()

    classes_of = lambda m: present.get(m, set())
    gates_of = lambda m: gated.get(m, set())
    lens_of = lambda m: lens.get(m, set())
    other_of = lambda m: other.get(m, set())
    alias_of = lambda m: alias_lens.get(m, set())

    # ---- split rule -------------------------------------------------------
    assignment: dict[str, str] = {}
    moved: list[str] = []
    already_test_unflagged: list[str] = []
    for md5, split in v8.items():
        if unflagged(classes_of(md5), gates_of(md5)):
            if split == "test":
                already_test_unflagged.append(md5)
            else:
                moved.append(md5)
            assignment[md5] = "test"
        else:
            assignment[md5] = split

    added: list[str] = []
    for md5 in present:
        if md5 not in v8 and unflagged(classes_of(md5), gates_of(md5)):
            assignment[md5] = "test"
            added.append(md5)

    # ---- counts -----------------------------------------------------------
    by_split = {
        s: sum(1 for v in assignment.values() if v == s) for s in ("train", "val", "test")
    }

    by_split_per_class: dict[str, tuple[int, int, int, int]] = {}
    for k in KEYS:
        row = [
            sum(
                1
                for m, sp in assignment.items()
                if sp == s and k in classes_of(m) and k in gates_of(m)
            )
            for s in ("train", "val", "test")
        ]
        row.append(
            sum(
                1
                for m, sp in assignment.items()
                if sp == "test" and k in classes_of(m) and k not in gates_of(m)
            )
        )
        by_split_per_class[k] = (row[0], row[1], row[2], row[3])

    decisive = {
        k: (
            sum(
                1
                for m in present
                if is_decisive(k, classes_of(m), gates_of(m), lens_of(m), other_of(m))
            ),
            sum(
                1
                for m in present
                if m not in v8
                and is_decisive(k, classes_of(m), gates_of(m), lens_of(m), other_of(m))
            ),
        )
        for k in KEYS
    }
    # Same rule with the missing_lens alias counted as a lens id. Diagnostic only.
    decisive_alias = {
        k: sum(
            1
            for m in present
            if is_decisive(
                k, classes_of(m), gates_of(m), lens_of(m).union(alias_of(m)), other_of(m)
            )
        )
        for k in KEYS
    }

    present_counts = {k: sum(1 for m in present if k in classes_of(m)) for k in KEYS}
    unflagged_counts = {
        k: sum(1 for m in present if k in classes_of(m) and k not in gates_of(m)) for k in KEYS
    }
    other_fail_counts = {k: unflagged_counts[k] - decisive[k][0] for k in KEYS}

    # ---- assertions -------------------------------------------------------
    problems: list[str] = []

    def eq(label: str, got, want):
        if got != want:
            problems.append(f"{label}: got {got}, asserted {want}")

    eq("rows", len(assignment), EXPECT_ROWS)
    for s in ("train", "val", "test"):
        eq(f"{s} rows", by_split[s], EXPECT_SPLIT[s])
    eq("moved out of train/val", len(moved), EXPECT_MOVED)
    eq("added from outside v8", len(added), EXPECT_ADDED)
    eq("unflagged already in v8 test", len(already_test_unflagged), EXPECT_ALREADY_TEST_UNFLAGGED)
    # 1,121 v8 test + 412 entering = 1,533; the 41 already in v8 test are inside the 1,121
    eq("moved + added entering test", len(moved) + len(added), 412)
    eq("rows with no winning_path", sum(1 for m in assignment if not paths.get(m, "").strip()), 0)
    for k in KEYS:
        eq(f"{k} present", present_counts[k], EXPECT_PRESENT[k])
        eq(f"{k} unflagged", unflagged_counts[k], EXPECT_UNFLAGGED[k])
        eq(
            f"{k} gated",
            present_counts[k] - unflagged_counts[k],
            EXPECT_PRESENT[k] - EXPECT_UNFLAGGED[k],
        )
        eq(f"{k} train/val/test gated + test unflagged", by_split_per_class[k], EXPECT_BY_SPLIT[k])
        eq(f"{k} decisive total/outside v8", decisive[k], EXPECT_DECISIVE[k])
        eq(f"{k} unflagged failing another label", other_fail_counts[k], EXPECT_OTHER_FAIL[k])

    # The premise of the experiment.
    leak = [
        m
        for m, s in assignment.items()
        if s in ("train", "val") and unflagged(classes_of(m), gates_of(m))
    ]
    eq("unflagged pictures left in train or val", len(leak), 0)

    if problems:
        raise CountMismatch("asserted counts did not reproduce:\n  " + "\n  ".join(problems))

    # ---- writes -----------------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    split_rows = sorted(assignment.items())
    with (OUT_DIR / "split.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["picture_md5", "group_id", "split"])
        for md5, split in split_rows:
            w.writerow([md5, md5, split])

    def bit(flag: bool) -> int:
        return 1 if flag else 0

    with (OUT_DIR / "labels.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "picture_md5",
                "image_path",
                "split",
                "fm_gated",
                "fiber_gated",
                "ep_gated",
                "hema_gated",
            ]
        )
        for md5, split in split_rows:
            p, g = classes_of(md5), gates_of(md5)
            w.writerow(
                [
                    md5,
                    paths[md5],
                    split,
                    bit("fm" in p and "fm" in g),
                    bit("fiber" in p and "fiber" in g),
                    bit("ep" in p and "ep" in g),
                    bit("hema" in p and "hema" in g),
                ]
            )

    detail_cols = [
        "picture_md5", "split", "image_path",
        "fm_present", "fm_gated",
        "fiber_present", "fiber_gated",
        "ep_present", "ep_gated",
        "hema_present", "hema_gated",
        "decisive_fm", "decisive_fiber", "decisive_ep", "decisive_hema",
        "largest_fm_px", "largest_fiber_px", "largest_ep_px", "largest_hema_px",
        "other_fail_labels",
        # appended diagnostics, outside the ticket's column list
        "missing_lens_present",
        "decisive_fm_alias_counted", "decisive_fiber_alias_counted",
        "decisive_ep_alias_counted", "decisive_hema_alias_counted",
    ]
    with (OUT_DIR / "picture_detail.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(detail_cols)
        for md5, split in split_rows:
            p, g, l, o = classes_of(md5), gates_of(md5), lens_of(md5), other_of(md5)
            a = alias_of(md5)
            row = [md5, split, paths[md5]]
            for k in KEYS:
                row += [bit(k in p), bit(k in p and k in g)]
            for k in KEYS:
                row.append(bit(is_decisive(k, p, g, l, o)))
            for k in KEYS:
                side = largest.get((md5, k))
                row.append(f"{side:.2f}" if side is not None else "")
            row.append(";".join(sorted(l.union(o))))
            row.append(bit(bool(a)))
            for k in KEYS:
                row.append(bit(is_decisive(k, p, g, l.union(a), o)))
            w.writerow(row)

    meta = {
        "version": VERSION,
        "date": DATE,
        "ticket": "docs/wayfinder/tickets/037-exp3-1-split-label-table.md",
        "map": "docs/wayfinder/exp3_1_size_gate_20261116.md",
        "derived_from": "run/split_20261103_v8/split_70_15_15.csv (read only, unmodified)",
        "rule": {
            "identity": "picture_md5, one annotation per picture, newest file wins",
            "class_present": (
                "shape_kind == box with canonical id foreign_matter / fiber / "
                "extraneous_polymer; HEMA is any of hema, hema_obstruction, hema_fragment"
            ),
            "size_flagged": (
                "that class's gate code present as a tag row: P3_FM_MICRON_THRESHOLD, "
                "P3_FIB_MICRON_THRESHOLD, P3_EP_MICRON_THRESHOLD, P3_HE_MICRON_THRESHOLD"
            ),
            "unflagged": "class box present and that class's gate code absent",
            "gate_is_subset": "the gate is a subset of its class, never a label of its own",
            "move": (
                "a picture leaves train or validation for test when it carries a box of any "
                "of the four classes without that class's gate tag; a picture gated in every "
                "gated class it carries keeps its v8 assignment; a picture outside v8 that is "
                "unflagged for any of the four classes is added as a test row"
            ),
            "union_reason": "one model is scored on one split",
            "decisive": (
                "carries that class unflagged and carries no other fail label, where other fail "
                "labels are any of the 12 lens canonical ids in a box or tag row, wet_package, "
                "bubble_cluster, surface_groove, or another of the four classes present and gated"
            ),
            "lens_ids": sorted(LENS_IDS),
            "correction_note": CORRECTION_NOTE,
        },
        "inputs": [{"path": p, "md5": m} for p, m in inputs.items()],
        "outputs": {
            "split.csv": "picture_md5,group_id,split, same schema as v8",
            "labels.csv": "picture_md5,image_path,split,fm_gated,fiber_gated,ep_gated,hema_gated",
            "picture_detail.csv": (
                "presence, gate, decisive and largest-box columns; largest_*_px is "
                "max(xbr-xtl, ybr-ytl) of the largest box of that class in native pixels; "
                "other_fail_labels is a semicolon list of the lens and non-class fail labels "
                "present; the trailing *_alias_counted columns add the missing_lens alias"
            ),
        },
        "counts": {
            "rows": len(assignment),
            "train": by_split["train"],
            "val": by_split["val"],
            "test": by_split["test"],
            "moved_out_of_train_or_val": len(moved),
            "added_from_outside_v8": len(added),
            "unflagged_already_in_v8_test": len(already_test_unflagged),
            "entering_test": len(moved) + len(added),
            "unflagged_left_in_train_or_val": len(leak),
            "v8_rows": len(v8),
            "v8_train": sum(1 for v in v8.values() if v == "train"),
            "v8_val": sum(1 for v in v8.values() if v == "val"),
            "v8_test": sum(1 for v in v8.values() if v == "test"),
        },
        "by_class": {
            k: {
                "present": present_counts[k],
                "gated": present_counts[k] - unflagged_counts[k],
                "unflagged": unflagged_counts[k],
                "train_gated": by_split_per_class[k][0],
                "val_gated": by_split_per_class[k][1],
                "test_gated": by_split_per_class[k][2],
                "test_unflagged": by_split_per_class[k][3],
                "decisive_total": decisive[k][0],
                "decisive_outside_v8": decisive[k][1],
                "unflagged_failing_another_label": other_fail_counts[k],
            }
            for k in KEYS
        },
        "decisive_with_missing_lens_alias": decisive_alias,
        "class_weights_train": {
            "n_train": by_split["train"],
            **{
                k: round(
                    (by_split["train"] - by_split_per_class[k][0]) / by_split_per_class[k][0], 1
                )
                for k in KEYS
            },
        },
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # ---- console ----------------------------------------------------------
    print(f"wrote {OUT_DIR}")
    print(
        f"  rows {len(assignment)}  train {by_split['train']}  "
        f"val {by_split['val']}  test {by_split['test']}"
    )
    print(
        f"  moved {len(moved)}  added {len(added)}  already test {len(already_test_unflagged)}"
    )
    for k in KEYS:
        d = meta["by_class"][k]
        print(
            f"  {k:6s} present {d['present']:4d} gated {d['gated']:4d} "
            f"unflagged {d['unflagged']:3d} | train/val/test gated "
            f"{d['train_gated']}/{d['val_gated']}/{d['test_gated']} "
            f"test unflagged {d['test_unflagged']:3d} | decisive {d['decisive_total']} "
            f"({d['decisive_outside_v8']} outside v8) | other-fail "
            f"{d['unflagged_failing_another_label']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(build())
