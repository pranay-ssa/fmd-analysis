#!/usr/bin/env python3
"""Independent verifier for the canonical crosswalk (ticket 009).

This is a second parsing route, not a re-run of the builder. The builder reads
each export with ElementTree.parse and findall; this verifier reads each export
with iterparse over ("end",) events and walks the finished <image> elements. The
round-trip of the label attributes is therefore produced by different code, and
the two are diffed.

The file list, the crosswalk columns and the hand-typed EXPECTED numbers below
are the arbiter. Exit code is non-zero on any failed check.

The XML files are trusted CVAT exports made by the client's own account
(bbarrine@its.jnj.com) from a private blob store. They are not attacker
supplied, so the standard library parser is used on purpose and Python's XXE
warning is knowingly accepted here.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/verify_crosswalk.py
"""

from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RUN = REPO / "run" / "eda_full_20261015"
CROSSWALK = DATA / "crosswalk.csv"
EVIDENCE = RUN / "crosswalk_evidence.json"

GROUPS = {
    "project2": ["annotations.xml"],
    "updated_20260922": ["Updated Annotations 20260922.xml"],
    "production_20260925": [f"annotations_45219{n}.xml" for n in range(40, 47)],
}
COL_BY_GROUP = {
    "project2": "code_in_project2",
    "updated_20260922": "code_in_updated_20260922",
    "production_20260925": "code_in_production_20260925",
}

# Hand-typed expected values, read off the files by eye before this script ran.
EXPECTED = {
    "crosswalk_rows": 28,
    "group_used_counts": {"project2": 10, "updated_20260922": 20, "production_20260925": 24},
    "file_image_counts": {
        "annotations.xml": 435,
        "Updated Annotations 20260922.xml": 6097,
        "annotations_4521940.xml": 150,
        "annotations_4521941.xml": 150,
        "annotations_4521942.xml": 147,
        "annotations_4521943.xml": 150,
        "annotations_4521944.xml": 150,
        "annotations_4521945.xml": 150,
        "annotations_4521946.xml": 150,
    },
    "file_shape_counts": {
        "annotations.xml": (2020, 0),
        "Updated Annotations 20260922.xml": (183, 4930),
        "annotations_4521940.xml": (1695, 149),
        "annotations_4521941.xml": (1973, 201),
        "annotations_4521942.xml": (1943, 261),
        "annotations_4521943.xml": (2431, 237),
        "annotations_4521944.xml": (1816, 224),
        "annotations_4521945.xml": (1296, 186),
        "annotations_4521946.xml": (1639, 229),
    },
    # gate code -> base code, for the production files.
    "gate_base": {
        "P3_FM_MICRON_THRESHOLD": "P3_FM",
        "P3_FIB_MICRON_THRESHOLD": "P3_FIB",
        "P3_EP_MICRON_THRESHOLD": "P3_EP",
        "P3_HE_MICRON_THRESHOLD": "P3_HE",
    },
    "gate_ok_images": {
        "P3_FM_MICRON_THRESHOLD": 171,
        "P3_FIB_MICRON_THRESHOLD": 136,
        "P3_EP_MICRON_THRESHOLD": 33,
        "P3_HE_MICRON_THRESHOLD": 95,
    },
    "collision_flags": {"P3_HE_shared_code", "F2_FOV_naming_anomaly"},
    "source_dependent_kinds": {"hema_obstruction"},
}


def read_images(path: Path) -> list[tuple[str, dict[str, list[str]]]]:
    """Second route: iterparse end events, collect finished <image> children.

    Returns one entry per image: (name, {"box": [...], "tag": [...]}).
    """
    # Trusted client export; the standard library parser is accepted here.
    context = ET.iterparse(path, events=("end",))
    out: list[tuple[str, dict[str, list[str]]]] = []
    for event, elem in context:
        if elem.tag != "image":
            continue
        labels = {"box": [], "tag": []}
        for box in elem.findall("box"):
            labels["box"].append(box.get("label"))
        for tag in elem.findall("tag"):
            labels["tag"].append(tag.get("label"))
        out.append((elem.get("name"), labels))
        elem.clear()
    return out


def read_definitions(path: Path) -> set[str]:
    """Codes the vocabulary DEFINES, from the meta label block, via iterparse.

    In a CVAT 1.1 detection export the only <label> ELEMENTS are the definitions
    inside <meta><labels>; shapes carry label as an attribute. So collecting every
    <label> element yields exactly the defined set.
    """
    defined: set[str] = set()
    context = ET.iterparse(path, events=("end",))
    for _event, elem in context:
        if elem.tag == "label":
            name = elem.findtext("name")
            if name:
                defined.add(name)
            elem.clear()
    return defined


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, note: str = "") -> None:
        checks.append((name, bool(ok), note))

    if not CROSSWALK.exists():
        print(f"missing {CROSSWALK}; run build_crosswalk.py first")
        return 2
    if not EVIDENCE.exists():
        print(f"missing {EVIDENCE}; run build_crosswalk.py first")
        return 2

    with CROSSWALK.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    with EVIDENCE.open(encoding="utf-8") as fh:
        evidence = json.load(fh)

    # --- row and id checks -------------------------------------------------
    add("crosswalk_row_count", len(rows) == EXPECTED["crosswalk_rows"],
        f"{len(rows)} rows, expected {EXPECTED['crosswalk_rows']}")
    ids = [r["canonical_id"] for r in rows]
    add("canonical_ids_unique", len(set(ids)) == len(ids), f"{len(ids)} ids")
    add("kinds_valid",
        all(tok in ("box", "tag", "gate") for r in rows for tok in str(r["kind"]).split("|") if tok),
        "box|tag|gate, pipe-joined where sources disagree")
    add("kind_conflict_flagged_and_questioned",
        all(r["open_question"].strip() for r in rows if r["kind_conflict"] == "yes"),
        f"{sum(1 for r in rows if r['kind_conflict'] == 'yes')} source-dependent rows")

    # --- independent inventory, from iterparse ----------------------------
    used: dict[str, set[str]] = {g: set() for g in GROUPS}
    kinds_group: dict[str, dict[str, set[str]]] = {g: {} for g in GROUPS}
    defined_group: dict[str, set[str]] = {g: set() for g in GROUPS}
    shapes_by_file: dict[str, tuple[int, int]] = {}
    images_by_file: dict[str, int] = {}
    prod_images: list[tuple[str, str, dict[str, list[str]]]] = []
    for group, files in GROUPS.items():
        for name in files:
            path = DATA / name
            imgs = read_images(path)
            images_by_file[name] = len(imgs)
            boxes = sum(len(labels["box"]) for _, labels in imgs)
            tags = sum(len(labels["tag"]) for _, labels in imgs)
            shapes_by_file[name] = (boxes, tags)
            for _, labels in imgs:
                used[group].update(labels["box"])
                used[group].update(labels["tag"])
                for code in labels["box"]:
                    kinds_group[group].setdefault(code, set()).add("box")
                for code in labels["tag"]:
                    kinds_group[group].setdefault(code, set()).add("tag")
                if group == "production_20260925":
                    prod_images.append((name, _, labels))
            defined_group[group] |= read_definitions(path)

    add("image_counts_match_expected",
        images_by_file == EXPECTED["file_image_counts"],
        f"got {images_by_file}")
    add("shape_counts_match_expected",
        shapes_by_file == EXPECTED["file_shape_counts"],
        f"got {shapes_by_file}")

    # --- acceptance 1: every used code is in its crosswalk column ----------
    for group, column in COL_BY_GROUP.items():
        listed = {r[column] for r in rows if r[column]}
        missing = sorted(used[group] - listed)
        add(f"used_codes_in_crosswalk__{group}", not missing,
            f"{len(used[group])} used, missing {missing}" if missing
            else f"{len(used[group])} used, all present")
    for group, count in EXPECTED["group_used_counts"].items():
        add(f"used_count__{group}", len(used[group]) == count,
            f"{len(used[group])} vs expected {count}")

    # --- per-source shape kind, re-derived from the iterparse inventory ------
    kind_col_by_group = {
        "project2": ("code_in_project2", "kind_project2", "used_project2"),
        "updated_20260922": ("code_in_updated_20260922", "kind_updated_20260922",
                             "used_updated_20260922"),
        "production_20260925": ("code_in_production_20260925", "kind_production_20260925",
                                "used_production_20260925"),
    }
    kind_mismatches: list[tuple[str, str, str, str]] = []
    conflict_ids: set[str] = set()
    for r in rows:
        seen: set[str] = set()
        for group, (code_col, kind_col, used_col) in kind_col_by_group.items():
            code = r[code_col]
            if not code:
                if r[kind_col] or r[used_col]:
                    kind_mismatches.append((r["canonical_id"], group, "no code",
                                            f"{r[kind_col] or '-'}/{r[used_col] or '-'}"))
                continue
            kinds = kinds_group[group].get(code, set())
            if kinds:
                want_kind, want_used = "|".join(sorted(kinds)), "yes"
                seen |= kinds
            elif code in defined_group[group]:
                want_kind, want_used = "defined_only", "no"
            else:
                want_kind, want_used = "not_present", "no"
            if (r[kind_col], r[used_col]) != (want_kind, want_used):
                kind_mismatches.append((r["canonical_id"], group,
                                        f"{r[kind_col]}/{r[used_col]}",
                                        f"{want_kind}/{want_used}"))
        if len(seen) > 1:
            conflict_ids.add(r["canonical_id"])
    add("per_source_kind_consistent_with_the_files", not kind_mismatches,
        f"{len(kind_mismatches)} mismatches: {kind_mismatches[:5]}" if kind_mismatches
        else "every kind cell matches the shape kinds the exports carry")
    add("source_dependent_kinds_match_expected", conflict_ids == EXPECTED["source_dependent_kinds"],
        f"{sorted(conflict_ids)} vs expected {sorted(EXPECTED['source_dependent_kinds'])}")
    add("source_dependent_kinds_are_pipe_joined",
        all("|" in r["kind"] for r in rows if r["canonical_id"] in conflict_ids),
        "the canonical kind is the union over the sources that carry the code")

    # --- acceptance 4: gate subset, independent window ---------------------
    for gate, base in EXPECTED["gate_base"].items():
        with_gate = 0
        with_base = 0
        for _name, _img, labels in prod_images:
            all_labels = set(labels["box"]) | set(labels["tag"])
            if gate in all_labels:
                with_gate += 1
                if base in all_labels:
                    with_base += 1
        add(f"gate_subset__{gate}", with_gate == with_base and with_gate > 0,
            f"{with_base} of {with_gate} gate images also carry {base}")
        add(f"gate_count__{gate}", with_gate == EXPECTED["gate_ok_images"][gate],
            f"{with_gate} gate images, expected {EXPECTED['gate_ok_images'][gate]}")

    # --- collisions flagged and answered -----------------------------------
    collision_rows = [r for r in rows if r["collision_flag"]]
    flags = {r["collision_flag"] for r in collision_rows}
    add("collision_flags_match", flags == EXPECTED["collision_flags"],
        f"flags {sorted(flags)}")
    add("collisions_have_questions",
        all(r["open_question"].strip() for r in collision_rows),
        f"{len(collision_rows)} collision rows")
    hema_rows = [r for r in rows if r["collision_flag"] == "P3_HE_shared_code"]
    add("p3_he_not_merged", len(hema_rows) == 2,
        f"{len(hema_rows)} rows carry the P3_HE collision")
    add("p3_he_two_meanings_kept",
        {r["canonical_name"] for r in hema_rows} == {"HEMA Fragment", "HEMA Obstruction"},
        "HEMA Fragment and HEMA Obstruction stay distinct")

    # --- acceptance 5: library names mapped with evidence, unmapped stated -
    mapped_lib = [r for r in rows
                  if r["library_folder_name"] and r["code_in_updated_20260922"]]
    unmapped_lib = [r for r in rows
                    if r["library_folder_name"] and not r["code_in_updated_20260922"]]
    add("mapped_library_names_have_evidence",
        all(r["mapping_evidence"].strip() for r in mapped_lib),
        f"{len(mapped_lib)} mapped library names")
    add("unmapped_library_names_have_question",
        all(r["open_question"].strip() for r in unmapped_lib),
        f"{len(unmapped_lib)} unmapped: {[r['canonical_name'] for r in unmapped_lib]}")

    # --- evidence file agreement -------------------------------------------
    add("evidence_rows_match", evidence["crosswalk"]["rows"] == len(rows),
        f"{evidence['crosswalk']['rows']} vs {len(rows)}")
    ev_used = evidence["used_codes_by_group"]
    add("evidence_used_codes_match",
        all(set(ev_used[g]) == used[g] for g in GROUPS),
        "independent sets equal to evidence sets")
    add("evidence_has_no_coverage_failures",
        all(not d["missing_from_crosswalk"] for d in evidence["coverage"].values()),
        "no code missing from the crosswalk")

    # --- report -------------------------------------------------------------
    failed = [c for c in checks if not c[1]]
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    print(f"checks: {len(checks)}")
    print(f"failed: {len(failed)}")
    if failed:
        print("FAILURES:", [c[0] for c in failed])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
