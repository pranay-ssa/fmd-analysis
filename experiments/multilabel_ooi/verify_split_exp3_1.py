"""Independent verifier for the Experiment 3.1 split and gate label table.

Ticket: docs/wayfinder/tickets/037-exp3-1-split-label-table.md

Imports nothing from build_split_exp3_1.py and shares no constants or helpers
with it: every count below is recomputed from run/eda_full_20261029/ and the
frozen split v8, then compared against the written artifacts. The asserted
counts are typed here as literals on purpose, so a bug in the builder's
expectations cannot hide behind a shared definition.

Checks
------
 1. input md5s
 2. split.csv: schema, 7,555 unique rows, recomputed assignment, split counts
 3. the experiment premise: zero unflagged gated-class pictures in train or val
 4. labels.csv: md5 set, split agreement, image_path == picture_table.winning_path,
    four gate cells against a fresh recomputation
 5. picture_detail.csv: presence, gate, decisive, largest box and other-fail list
 6. meta.json counts against the same recomputation
 7. tamper proofs: one moved row and one flipped gate cell are both rejected

Exit 0 only if every check passes and both tamper proofs catch their tamper.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

ANN = REPO / "run/eda_full_20261029/resolved_labels.csv"
PICTURES = REPO / "run/eda_full_20261029/picture_table.csv"
FROZEN = REPO / "run/split_20261103_v8/split_70_15_15.csv"
OUT = REPO / "run/split_exp3_1_20261116"

WANT_MD5 = {
    str(ANN.relative_to(REPO)).replace("\\", "/"): "f61ea0b90df095ebe52d1332f8bfdb8a",
    str(PICTURES.relative_to(REPO)).replace("\\", "/"): "a03ddeead53bae370c17bd8ea15c0df0",
    str(FROZEN.relative_to(REPO)).replace("\\", "/"): "1a71d66d2de384cf47a3fcf7d9115baa",
}

# Written out again, independently of the builder.
GATE_CODE_BY_CLASS = {
    "fm": "P3_FM_MICRON_THRESHOLD",
    "fiber": "P3_FIB_MICRON_THRESHOLD",
    "ep": "P3_EP_MICRON_THRESHOLD",
    "hema": "P3_HE_MICRON_THRESHOLD",
}
BOX_CLASS = {"foreign_matter": "fm", "fiber": "fiber", "extraneous_polymer": "ep"}
HEMA_ANY = ("hema", "hema_obstruction", "hema_fragment")
LENS = (
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
)
ALIAS_NO_LENS = "missing_lens"
NON_CLASS_FAIL = ("wet_package", "bubble_cluster", "surface_groove")
CLASSES = ("fm", "fiber", "ep", "hema")

# asserted counts, typed independently
WANT_ROWS = 7555
WANT_SPLIT = {"train": 4964, "val": 1058, "test": 1533}
WANT_ENTERING = 412
WANT_MOVED = 327
WANT_ADDED = 85
WANT_ALREADY_TEST = 41
WANT_PRESENT = {"fm": 834, "fiber": 405, "ep": 175, "hema": 157}
WANT_UNFLAGGED = {"fm": 380, "fiber": 43, "ep": 40, "hema": 6}
WANT_SPLIT_CLASS = {
    "fm": {"train": 315, "val": 60, "test": 79, "test_unflagged": 380},
    "fiber": {"train": 195, "val": 43, "test": 124, "test_unflagged": 43},
    "ep": {"train": 81, "val": 14, "test": 40, "test_unflagged": 40},
    "hema": {"train": 79, "val": 20, "test": 52, "test_unflagged": 6},
}
WANT_DECISIVE = {"fm": 51, "fiber": 14, "ep": 34, "hema": 3}
WANT_DECISIVE_OUTSIDE = {"fm": 36, "fiber": 13, "ep": 33, "hema": 3}
WANT_OTHER_FAIL = {"fm": 329, "fiber": 29, "ep": 6, "hema": 3}
WANT_ENTRY_COLUMNS = ["picture_md5", "group_id", "split"]
WANT_LABEL_COLUMNS = [
    "picture_md5", "image_path", "split", "fm_gated", "fiber_gated", "ep_gated", "hema_gated"
]
WANT_DETAIL_COLUMNS = [
    "picture_md5", "split", "image_path",
    "fm_present", "fm_gated", "fiber_present", "fiber_gated", "ep_present", "ep_gated",
    "hema_present", "hema_gated",
    "decisive_fm", "decisive_fiber", "decisive_ep", "decisive_hema",
    "largest_fm_px", "largest_fiber_px", "largest_ep_px", "largest_hema_px",
    "other_fail_labels",
]


def digest(path: Path) -> str:
    m = hashlib.md5()
    m.update(path.read_bytes())
    return m.hexdigest()


def load_annotation():
    """Rebuild presence / gate / lens / other-fail / largest side per picture.

    Parsed positionally from the header line, so a renamed column is a loud
    failure rather than a silently empty set.
    """
    with ANN.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
        idx = {name: header.index(name) for name in
               ("picture_md5", "code", "canonical_id", "shape_kind", "xtl", "ytl", "xbr", "ybr")}
        carries: dict[str, set[str]] = {}
        flags: dict[str, set[str]] = {}
        lens_on: dict[str, set[str]] = {}
        fails_on: dict[str, set[str]] = {}
        longest: dict[str, dict[str, float]] = {}

        for raw in csv.reader(fh):
            if not raw:
                continue
            picture = raw[idx["picture_md5"]].strip()
            if not picture:
                continue
            cid = raw[idx["canonical_id"]].strip()
            kind = raw[idx["shape_kind"]].strip()
            code = raw[idx["code"]].strip()

            if cid in LENS or cid == ALIAS_NO_LENS:
                bucket = lens_on if cid in LENS else None
                if bucket is not None:
                    bucket.setdefault(picture, set()).add(cid)
            if cid in NON_CLASS_FAIL:
                fails_on.setdefault(picture, set()).add(cid)

            if kind == "box":
                which = BOX_CLASS.get(cid)
                if which is None and cid in HEMA_ANY:
                    which = "hema"
                if which is not None:
                    carries.setdefault(picture, set()).add(which)
                    dx = float(raw[idx["xbr"]]) - float(raw[idx["xtl"]])
                    dy = float(raw[idx["ybr"]]) - float(raw[idx["ytl"]])
                    side = abs(dx) if abs(dx) >= abs(dy) else abs(dy)
                    per = longest.setdefault(picture, {})
                    if which not in per or side > per[which]:
                        per[which] = side

            if kind == "tag" and code in GATE_CODE_BY_CLASS.values():
                for name, wanted_code in GATE_CODE_BY_CLASS.items():
                    if code == wanted_code:
                        flags.setdefault(picture, set()).add(name)

    alias: dict[str, set[str]] = {}
    with ANN.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
        idx = {name: header.index(name) for name in ("picture_md5", "canonical_id")}
        for raw in csv.reader(fh):
            if not raw:
                continue
            if raw[idx["canonical_id"]].strip() == ALIAS_NO_LENS:
                alias.setdefault(raw[idx["picture_md5"]].strip(), set()).add(ALIAS_NO_LENS)

    return carries, flags, lens_on, fails_on, longest, alias


def load_picture_paths() -> dict[str, str]:
    with PICTURES.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return {row["md5"].strip(): row["winning_path"] for row in reader}


def load_frozen() -> dict[str, str]:
    with FROZEN.open(newline="", encoding="utf-8") as fh:
        return {
            row["picture_md5"].strip(): row["split"].strip() for row in csv.DictReader(fh)
        }


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        return header, list(reader)


def compute(carries, flags, frozen):
    """Recompute the assignment and the uncalled guard from the annotation."""
    unflagged_of = lambda p: set(carries.get(p, set())) - set(flags.get(p, set()))
    assign: dict[str, str] = {}
    moved, already = [], []
    for picture, was in frozen.items():
        if unflagged_of(picture):
            assign[picture] = "test"
            (already if was == "test" else moved).append(picture)
        else:
            assign[picture] = was
    added = []
    for picture in carries:
        if picture not in frozen and unflagged_of(picture):
            assign[picture] = "test"
            added.append(picture)
    return assign, moved, added, already, unflagged_of


def audit(split_header, split_rows, label_header, label_rows, detail_header, detail_rows,
          meta, ctx, expect_frozen_inputs=True):
    """Pure check. Returns a list of failure strings; empty means clean."""
    carries, flags, lens_on, fails_on, longest, alias, paths, frozen = ctx
    bad: list[str] = []
    assign, moved, added, already, unflagged_of = compute(carries, flags, frozen)

    # -- split.csv ------------------------------------------------------
    if split_header != WANT_ENTRY_COLUMNS:
        bad.append(f"split.csv header {split_header}")
    if len(split_rows) != WANT_ROWS:
        bad.append(f"split.csv rows {len(split_rows)} != {WANT_ROWS}")
    keys = [r["picture_md5"].strip() for r in split_rows]
    if len(set(keys)) != len(keys):
        bad.append("split.csv has duplicate picture_md5")
    got_assign = {r["picture_md5"].strip(): r["split"].strip() for r in split_rows}
    if set(got_assign) != set(assign):
        only_file = sorted(set(got_assign) - set(assign))[:3]
        only_calc = sorted(set(assign) - set(got_assign))[:3]
        bad.append(f"split.csv population differs; extra {only_file} missing {only_calc}")
    wrong = [p for p in got_assign if p in assign and got_assign[p] != assign[p]]
    if wrong:
        bad.append(
            f"split.csv disagrees with the move rule on {len(wrong)} rows, e.g. "
            f"{[(p, got_assign[p], assign[p]) for p in wrong[:3]]}"
        )
    for row in split_rows:
        if row["group_id"].strip() != row["picture_md5"].strip():
            bad.append(f"group_id != picture_md5 for {row['picture_md5']}")
            break
        if row["split"].strip() not in ("train", "val", "test"):
            bad.append(f"bad split value {row['split']}")
            break

    counts = {s: sum(1 for r in split_rows if r["split"].strip() == s) for s in ("train", "val", "test")}
    for s, want in WANT_SPLIT.items():
        if counts[s] != want:
            bad.append(f"split.csv {s} {counts[s]} != {want}")

    # -- premise ------------------------------------------------------
    leaking = [
        r["picture_md5"] for r in split_rows
        if r["split"].strip() in ("train", "val") and unflagged_of(r["picture_md5"].strip())
    ]
    if leaking:
        bad.append(f"{len(leaking)} unflagged gated-class pictures left in train/val, e.g. {leaking[:3]}")

    # -- labels.csv ---------------------------------------------------
    if label_header[:7] != WANT_LABEL_COLUMNS:
        bad.append(f"labels.csv header {label_header[:7]}")
    if len(label_rows) != WANT_ROWS:
        bad.append(f"labels.csv rows {len(label_rows)} != {WANT_ROWS}")
    if {r["picture_md5"].strip() for r in label_rows} != set(got_assign):
        bad.append("labels.csv population differs from split.csv")

    gate_bad, path_bad = [], []
    for row in label_rows:
        picture = row["picture_md5"].strip()
        if row["split"].strip() != got_assign.get(picture):
            gate_bad.append((picture, "split"))
        if row["image_path"] != paths.get(picture, "\0"):
            path_bad.append(picture)
        present = carries.get(picture, set())
        gated = flags.get(picture, set())
        for name in CLASSES:
            want = "1" if (name in present and name in gated) else "0"
            if row[f"{name}_gated"].strip() != want:
                gate_bad.append((picture, f"{name}_gated"))
    if gate_bad:
        bad.append(f"labels.csv wrong gate cells: {len(gate_bad)}, e.g. {gate_bad[:3]}")
    if path_bad:
        bad.append(f"labels.csv image_path != winning_path on {len(path_bad)}, e.g. {path_bad[:3]}")

    # -- picture_detail.csv -------------------------------------------
    if detail_header[:20] != WANT_DETAIL_COLUMNS:
        bad.append(f"picture_detail.csv header {detail_header[:20]}")
    if len(detail_rows) != WANT_ROWS:
        bad.append(f"picture_detail.csv rows {len(detail_rows)} != {WANT_ROWS}")
    if {r["picture_md5"].strip() for r in detail_rows} != set(got_assign):
        bad.append("picture_detail.csv population differs from split.csv")

    def decisive(name, picture):
        present = set(carries.get(picture, set()))
        gated = set(flags.get(picture, set()))
        if name not in present or name in gated:
            return False
        if lens_on.get(picture) or fails_on.get(picture):
            return False
        return not any(c != name and c in gated for c in present)

    detail_bad = []
    for row in detail_rows:
        picture = row["picture_md5"].strip()
        if row["split"].strip() != got_assign.get(picture):
            detail_bad.append((picture, "split"))
        present = carries.get(picture, set())
        gated = flags.get(picture, set())
        for name in CLASSES:
            if row[f"{name}_present"].strip() != ("1" if name in present else "0"):
                detail_bad.append((picture, f"{name}_present"))
            if row[f"{name}_gated"].strip() != (
                "1" if (name in present and name in gated) else "0"
            ):
                detail_bad.append((picture, f"{name}_gated"))
            if row[f"decisive_{name}"].strip() != ("1" if decisive(name, picture) else "0"):
                detail_bad.append((picture, f"decisive_{name}"))
            want_side = longest.get(picture, {}).get(name)
            cell = row[f"largest_{name}_px"].strip()
            if want_side is None:
                if cell != "":
                    detail_bad.append((picture, f"largest_{name}_px"))
            else:
                try:
                    ok = abs(float(cell) - want_side) <= 0.0051
                except ValueError:
                    ok = False
                if not ok:
                    detail_bad.append((picture, f"largest_{name}_px"))
        want_other = ";".join(
            sorted(set(lens_on.get(picture, set())).union(fails_on.get(picture, set())))
        )
        if row["other_fail_labels"] != want_other:
            detail_bad.append((picture, "other_fail_labels"))
    if detail_bad:
        bad.append(f"picture_detail.csv wrong cells: {len(detail_bad)}, e.g. {detail_bad[:3]}")

    # -- recomputed aggregate tables -----------------------------------
    for name in CLASSES:
        present_n = sum(1 for p in carries if name in carries[p])
        gated_n = sum(1 for p in carries if name in carries[p] and name in flags.get(p, set()))
        if present_n != WANT_PRESENT[name]:
            bad.append(f"{name} present {present_n} != {WANT_PRESENT[name]}")
        if present_n - gated_n != WANT_UNFLAGGED[name]:
            bad.append(f"{name} unflagged {present_n - gated_n} != {WANT_UNFLAGGED[name]}")
        for s, want in WANT_SPLIT_CLASS[name].items():
            if s == "test_unflagged":
                got = sum(
                    1 for p, sp in got_assign.items()
                    if sp == "test" and name in carries.get(p, set())
                    and name not in flags.get(p, set())
                )
            else:
                got = sum(
                    1 for p, sp in got_assign.items()
                    if sp == s and name in carries.get(p, set()) and name in flags.get(p, set())
                )
            if got != want:
                bad.append(f"{name} {s} {got} != {want}")
        dec_n = sum(1 for p in carries if decisive(name, p))
        dec_out = sum(1 for p in carries if p not in frozen and decisive(name, p))
        if dec_n != WANT_DECISIVE[name]:
            bad.append(f"{name} decisive {dec_n} != {WANT_DECISIVE[name]}")
        if dec_out != WANT_DECISIVE_OUTSIDE[name]:
            bad.append(f"{name} decisive outside v8 {dec_out} != {WANT_DECISIVE_OUTSIDE[name]}")
        other_n = WANT_UNFLAGGED[name] - dec_n
        if other_n != WANT_OTHER_FAIL[name]:
            bad.append(f"{name} other-fail {other_n} != {WANT_OTHER_FAIL[name]}")

    if len(moved) != WANT_MOVED:
        bad.append(f"moved {len(moved)} != {WANT_MOVED}")
    if len(added) != WANT_ADDED:
        bad.append(f"added {len(added)} != {WANT_ADDED}")
    if len(already) != WANT_ALREADY_TEST:
        bad.append(f"already in v8 test {len(already)} != {WANT_ALREADY_TEST}")
    if len(moved) + len(added) != WANT_ENTERING:
        bad.append(f"entering test {len(moved) + len(added)} != {WANT_ENTERING}")

    # -- meta.json -----------------------------------------------------
    want_meta = {
        "rows": WANT_ROWS, "train": WANT_SPLIT["train"], "val": WANT_SPLIT["val"],
        "test": WANT_SPLIT["test"], "moved_out_of_train_or_val": WANT_MOVED,
        "added_from_outside_v8": WANT_ADDED,
        "unflagged_already_in_v8_test": WANT_ALREADY_TEST,
        "unflagged_left_in_train_or_val": 0,
    }
    for key, want in want_meta.items():
        if meta.get("counts", {}).get(key) != want:
            bad.append(f"meta counts.{key} {meta.get('counts', {}).get(key)} != {want}")
    if meta.get("version") != "exp3_1_v1":
        bad.append(f"meta version {meta.get('version')}")
    for name in CLASSES:
        row = meta.get("by_class", {}).get(name, {})
        checks = {
            "present": WANT_PRESENT[name],
            "unflagged": WANT_UNFLAGGED[name],
            "train_gated": WANT_SPLIT_CLASS[name]["train"],
            "val_gated": WANT_SPLIT_CLASS[name]["val"],
            "test_gated": WANT_SPLIT_CLASS[name]["test"],
            "test_unflagged": WANT_SPLIT_CLASS[name]["test_unflagged"],
            "decisive_total": WANT_DECISIVE[name],
            "decisive_outside_v8": WANT_DECISIVE_OUTSIDE[name],
            "unflagged_failing_another_label": WANT_OTHER_FAIL[name],
        }
        for key, want in checks.items():
            if row.get(key) != want:
                bad.append(f"meta by_class.{name}.{key} {row.get(key)} != {want}")

    if expect_frozen_inputs:
        got_inputs = {d["path"]: d["md5"] for d in meta.get("inputs", [])}
        if got_inputs != WANT_MD5:
            bad.append(f"meta inputs {got_inputs} != {WANT_MD5}")

    return bad


def main() -> int:
    failures: list[str] = []

    for rel, want in WANT_MD5.items():
        path = REPO / rel
        got = digest(path)
        if got != want:
            failures.append(f"input md5 {rel}: {got} != {want}")

    if failures:
        for f in failures:
            print(f"FAIL {f}")
        return 1

    ctx_data = load_annotation()
    ctx = ctx_data + (load_picture_paths(), load_frozen())
    carries, flags = ctx[0], ctx[1]

    split_header, split_rows = read_csv(OUT / "split.csv")
    label_header, label_rows = read_csv(OUT / "labels.csv")
    detail_header, detail_rows = read_csv(OUT / "picture_detail.csv")
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))

    failures = audit(
        split_header, split_rows, label_header, label_rows, detail_header, detail_rows, meta, ctx
    )

    # ---- tamper proof 1: one moved row ---------------------------------
    moved_target = None
    for picture, was in load_frozen().items():
        if was in ("train", "val") and picture in set(carries) and (
            set(carries[picture]) - set(flags.get(picture, set()))
        ):
            moved_target = (picture, was)
            break
    if moved_target is None:
        failures.append("tamper proof 1: no moved row available to tamper with")
    else:
        picture, was = moved_target
        t_split = copy.deepcopy(split_rows)
        t_label = copy.deepcopy(label_rows)
        t_detail = copy.deepcopy(detail_rows)
        for rows in (t_split, t_label, t_detail):
            for row in rows:
                if row["picture_md5"].strip() == picture:
                    row["split"] = was
        found = audit(
            split_header, t_split, label_header, t_label, detail_header, t_detail, meta, ctx
        )
        hits = [f for f in found if "move rule" in f or "left in train/val" in f]
        if not hits:
            failures.append(f"tamper proof 1 not caught: moved row {picture} put back to {was}")
        else:
            print(f"tamper 1 caught: moved row {picture} restored to {was} -> {hits[0][:110]}")

    # ---- tamper proof 2: one flipped gate cell -------------------------
    flip_target = None
    for row in label_rows:
        if row["fm_gated"].strip() == "1":
            flip_target = row["picture_md5"].strip()
            break
    if flip_target is None:
        failures.append("tamper proof 2: no fm_gated=1 cell available to flip")
    else:
        t_label = copy.deepcopy(label_rows)
        for row in t_label:
            if row["picture_md5"].strip() == flip_target:
                row["fm_gated"] = "0"
        t_detail = copy.deepcopy(detail_rows)
        for row in t_detail:
            if row["picture_md5"].strip() == flip_target:
                row["fm_gated"] = "0"
        found = audit(
            split_header, copy.deepcopy(split_rows), label_header, t_label,
            detail_header, t_detail, meta, ctx,
        )
        hits = [f for f in found if "gate cells" in f or "fm train" in f or "fm " in f and "!=" in f]
        if not hits:
            failures.append(f"tamper proof 2 not caught: fm_gated flipped on {flip_target}")
        else:
            print(f"tamper 2 caught: fm_gated flipped on {flip_target} -> {hits[0][:110]}")

    # a clean re-audit must still pass, proving the tamper copies were local
    if audit(
        split_header, split_rows, label_header, label_rows, detail_header, detail_rows, meta, ctx
    ):
        failures.append("clean re-audit failed after tamper tests")

    if failures:
        for f in failures:
            print(f"FAIL {f}")
        print(f"\n{len(failures)} failure(s)")
        return 1

    print("PASS every count reproduced from the annotation")
    print(f"  rows {WANT_ROWS}  train {WANT_SPLIT['train']}  val {WANT_SPLIT['val']}  test {WANT_SPLIT['test']}")
    print(f"  moved {WANT_MOVED}  added {WANT_ADDED}  already in v8 test {WANT_ALREADY_TEST}")
    for name in CLASSES:
        print(
            f"  {name:6s} present {WANT_PRESENT[name]:4d} unflagged {WANT_UNFLAGGED[name]:3d} "
            f"train/val/test gated {WANT_SPLIT_CLASS[name]['train']}/"
            f"{WANT_SPLIT_CLASS[name]['val']}/{WANT_SPLIT_CLASS[name]['test']} "
            f"test unflagged {WANT_SPLIT_CLASS[name]['test_unflagged']:3d} "
            f"decisive {WANT_DECISIVE[name]} ({WANT_DECISIVE_OUTSIDE[name]} outside v8) "
            f"other-fail {WANT_OTHER_FAIL[name]}"
        )
    print("  zero unflagged gated-class pictures in train or val")
    return 0


if __name__ == "__main__":
    sys.exit(main())
