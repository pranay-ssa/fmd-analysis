#!/usr/bin/env python3
"""Build the canonical crosswalk across the three annotation vocabularies.

Ticket 009 of the full-coverage EDA map.

The crosswalk is one row per canonical defect. It maps every code and every
plain library name onto a single entry, keeps the collisions visible instead of
merging them, and records the evidence for every library name that is mapped
onto a code.

The XML files are trusted CVAT exports made by the client's own account
(bbarrine@its.jnj.com), pulled from a private blob store on 2026-10-13. They are
not attacker supplied, so the standard library parser is used on purpose and
Python's XXE warning is knowingly accepted here.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/build_crosswalk.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RUN = REPO / "run" / "eda_full_20261015"

# The three vocabularies. The production group is the 7 CVAT jobs.
GROUPS = {
    "project2": ["annotations.xml"],
    "updated_20260922": ["Updated Annotations 20260922.xml"],
    "production_20260925": [f"annotations_45219{n}.xml" for n in range(40, 47)],
}

# Column order of data/crosswalk.csv.
COLUMNS = [
    "canonical_id",
    "canonical_name",
    "kind",
    "kind_conflict",
    "code_in_project2",
    "code_in_updated_20260922",
    "code_in_production_20260925",
    "kind_project2",
    "kind_updated_20260922",
    "kind_production_20260925",
    "used_project2",
    "used_updated_20260922",
    "used_production_20260925",
    "library_folder_name",
    "is_size_gate",
    "gate_base_code",
    "collision_flag",
    "mapping_evidence",
    "open_question",
]

# One row per canonical defect, in a fixed order (boxes, then tags, then gates).
# kind is box | tag | gate.
# evidence for every library name that maps onto a code is stated in
# mapping_evidence, per acceptance check 5.
CANONICAL = [
    # ---- localised defects (boxes) -----------------------------------------
    dict(
        canonical_id="bubble", canonical_name="Bubble", kind="box",
        code_in_project2="Bubble", code_in_updated_20260922="P2_BB",
        code_in_production_20260925="P2_BB", library_folder_name="Bubble",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P2_BB is pinned by the acronym list "
                         "(docs/annotations_update_20260923.md section 2.2); the library folder is named Bubble.",
        open_question="",
    ),
    dict(
        canonical_id="bubble_cluster", canonical_name="Bubble Cluster", kind="box",
        code_in_project2="Bubble Cluster", code_in_updated_20260922="P2_BC",
        code_in_production_20260925="P2_BC", library_folder_name="Bubble Cluster",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P2_BC is pinned by the acronym list; the library folder is named Bubble Cluster.",
        open_question="",
    ),
    dict(
        canonical_id="bubble_irregular", canonical_name="Bubble Irregular", kind="box",
        code_in_project2="Bubble Irregular", code_in_updated_20260922="P2_BI",
        code_in_production_20260925="P2_BI", library_folder_name="Bubble Irregular",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P2_BI is pinned by the acronym list; the library folder is named Bubble Irregular.",
        open_question="",
    ),
    dict(
        canonical_id="stretched_bubble", canonical_name="Stretched Bubble", kind="box",
        code_in_project2="", code_in_updated_20260922="P2_BST",
        code_in_production_20260925="P2_BST", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="",
        open_question="Confirm P2_BST = Stretched Bubble. This is the only mapping pinned by elimination, not by a CVAT task name or an acronym: after the task-name and acronym pins, P2_BST is the only box code left and Stretched Bubble the only ontology box name that matches B-ST.",
    ),
    dict(
        canonical_id="extraneous_polymer", canonical_name="Extraneous Polymer", kind="box",
        code_in_project2="Extraneous Polymer", code_in_updated_20260922="P3_EP",
        code_in_production_20260925="P3_EP", library_folder_name="Extraneous Polymer",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P3_EP is pinned by the CVAT task name P3_EP sitting on the blob folder Extraneous Polymer; the library folder is named Extraneous Polymer.",
        open_question="",
    ),
    dict(
        canonical_id="fiber", canonical_name="Fiber", kind="box",
        code_in_project2="Fiber", code_in_updated_20260922="P3_FIB",
        code_in_production_20260925="P3_FIB", library_folder_name="Fiber",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P3_FIB is pinned by the acronym list; the library folder is named Fiber.",
        open_question="",
    ),
    dict(
        canonical_id="foreign_matter", canonical_name="Foreign Matter", kind="box",
        code_in_project2="Foreign Matter", code_in_updated_20260922="P3_FM",
        code_in_production_20260925="P3_FM", library_folder_name="Foreign Matter",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P3_FM is pinned by the acronym list; the library folder is named Foreign Matter.",
        open_question="",
    ),
    dict(
        canonical_id="hema_fragment", canonical_name="HEMA Fragment", kind="box",
        code_in_project2="HEMA Fragment", code_in_updated_20260922="P3_HE",
        code_in_production_20260925="", library_folder_name="HEMA Fragment",
        is_size_gate="no", gate_base_code="", collision_flag="P3_HE_shared_code",
        mapping_evidence="Project 3 code P3_HE is pinned by the acronym list as HEMA Fragment; the library folder is named HEMA Fragment.",
        open_question="COLLISION: P3_HE means HEMA Fragment here but HEMA Obstruction in the 7 production files. One code, two meanings. Confirm which reading applies to the production boxes.",
    ),
    dict(
        canonical_id="hema_obstruction", canonical_name="HEMA Obstruction", kind="box|tag",
        code_in_project2="", code_in_updated_20260922="P2_HMO",
        code_in_production_20260925="P3_HE", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="P3_HE_shared_code",
        mapping_evidence="Project 3 code P2_HMO is pinned by the CVAT task name P2_HMO on the blob folder HEMA Obstruction (tag). The production files label HEMA Obstruction boxes P3_HE (docs/cvat_production_20260925_pull.md).",
        open_question="COLLISION: P3_HE means HEMA Obstruction here but HEMA Fragment in the Sep-22 project. The shape kind also differs: HEMA Obstruction is a tag (P2_HMO) in the Sep-22 project and a box (P3_HE) in the production files. Confirm the intended code and shape kind.",
    ),
    dict(
        canonical_id="wet_package", canonical_name="Wet Package", kind="box",
        code_in_project2="Wet Package", code_in_updated_20260922="P2_WP",
        code_in_production_20260925="P2_WP", library_folder_name="Wet Package",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="Project 3 code P2_WP is pinned by the acronym list; the library folder is named Wet Package.",
        open_question="",
    ),
    dict(
        canonical_id="bubble_on_123", canonical_name="Bubble On 123", kind="box",
        code_in_project2="Bubble On 123", code_in_updated_20260922="",
        code_in_production_20260925="", library_folder_name="Bubble On 123",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="",
        open_question="Library-only class, left unmapped: neither newer project defines a code for it. The ontology keeps Bubble Over 123 Mark. Confirm whether it is retained as its own class or consolidated.",
    ),
    dict(
        canonical_id="bubble_on_edge", canonical_name="Bubble On Edge", kind="box",
        code_in_project2="Bubble On Edge", code_in_updated_20260922="",
        code_in_production_20260925="", library_folder_name="Bubble On Edge",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="",
        open_question="Library-only class, left unmapped: neither newer project defines a code for it. The ontology keeps Bubble On Edge. Confirm whether it is retained as its own class or consolidated.",
    ),
    # ---- whole-image flags (tags) ------------------------------------------
    dict(
        canonical_id="missing_primary_package", canonical_name="Missing Primary Package", kind="tag",
        code_in_project2="", code_in_updated_20260922="P1_MPP",
        code_in_production_20260925="P1_MPP", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="multiple_lenses", canonical_name="Multiple Lenses", kind="tag",
        code_in_project2="", code_in_updated_20260922="P1_ML",
        code_in_production_20260925="P1_ML", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="lens_off_center", canonical_name="Lens Off Center", kind="tag",
        code_in_project2="", code_in_updated_20260922="P2_LOC",
        code_in_production_20260925="P2_LOC", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="missing_lens", canonical_name="Missing Lens", kind="tag",
        code_in_project2="", code_in_updated_20260922="P1_NL",
        code_in_production_20260925="P1_NL", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="cavity_off_center", canonical_name="Cavity Off Center", kind="tag",
        code_in_project2="", code_in_updated_20260922="P1_COC",
        code_in_production_20260925="P1_COC", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="folded_lens", canonical_name="Folded Lens", kind="tag",
        code_in_project2="", code_in_updated_20260922="P1_FL",
        code_in_production_20260925="P1_FL", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="dirty_camera", canonical_name="Dirty Camera", kind="tag",
        code_in_project2="", code_in_updated_20260922="P2_DC",
        code_in_production_20260925="P2_DC", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="low_dose", canonical_name="Low Dose", kind="tag",
        code_in_project2="", code_in_updated_20260922="P2_LD",
        code_in_production_20260925="P2_LD", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="",
        open_question="The Sep-22 Low Dose task is annotated for 3.9 percent of its folder (only its last job was worked). Confirm the task is finished before the tag is counted as complete.",
    ),
    dict(
        canonical_id="dirty_strobe", canonical_name="Dirty Strobe", kind="tag",
        code_in_project2="", code_in_updated_20260922="P2_DS",
        code_in_production_20260925="P2_DS", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="", open_question="",
    ),
    dict(
        canonical_id="bubble_scatter", canonical_name="Bubble Scatter", kind="tag",
        code_in_project2="", code_in_updated_20260922="P2_BSC",
        code_in_production_20260925="P2_BSC", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="",
        open_question="Defined in both newer projects. Used only by the Sep-22 project; the production files define P2_BSC but carry no shape with it.",
    ),
    dict(
        canonical_id="package_misalignment", canonical_name="Package Misalignment", kind="tag",
        code_in_project2="", code_in_updated_20260922="P1_PPM",
        code_in_production_20260925="P1_PPM", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="",
        mapping_evidence="",
        open_question="Defined in the Sep-22 project with no annotation there; used only by the production files (2 images). Confirm the class is live.",
    ),
    dict(
        canonical_id="view_obstructed", canonical_name="View Obstructed", kind="tag",
        code_in_project2="", code_in_updated_20260922="P2_FOV",
        code_in_production_20260925="F2_FOV", library_folder_name="",
        is_size_gate="no", gate_base_code="", collision_flag="F2_FOV_naming_anomaly",
        mapping_evidence="The Sep-22 project defines P2_FOV = View Obstructed (no shape in that file); the production files label the same class F2_FOV (docs/cvat_production_20260925_pull.md).",
        open_question="NAMING ANOMALY: the usual scheme is P1_ / P2_ / P3_, so F2_ is anomalous where the Sep-22 project defines P2_FOV for View Obstructed. Confirm the intended code and whether the two are the same class.",
    ),
    # ---- size gates --------------------------------------------------------
    dict(
        canonical_id="foreign_matter_micron_gate", canonical_name="Foreign Matter micron gate", kind="gate",
        code_in_project2="", code_in_updated_20260922="",
        code_in_production_20260925="P3_FM_MICRON_THRESHOLD", library_folder_name="",
        is_size_gate="yes", gate_base_code="P3_FM", collision_flag="",
        mapping_evidence="",
        open_question="Production-only tag and a strict subset of P3_FM, so it is a size flag on Foreign Matter, not a separate defect. Confirm the gate cut (300 microns per the client).",
    ),
    dict(
        canonical_id="fiber_micron_gate", canonical_name="Fiber micron gate", kind="gate",
        code_in_project2="", code_in_updated_20260922="",
        code_in_production_20260925="P3_FIB_MICRON_THRESHOLD", library_folder_name="",
        is_size_gate="yes", gate_base_code="P3_FIB", collision_flag="",
        mapping_evidence="",
        open_question="Production-only tag and a strict subset of P3_FIB, so it is a size flag on Fiber, not a separate defect. Confirm the gate cut (300 microns per the client).",
    ),
    dict(
        canonical_id="extraneous_polymer_micron_gate", canonical_name="Extraneous Polymer micron gate", kind="gate",
        code_in_project2="", code_in_updated_20260922="",
        code_in_production_20260925="P3_EP_MICRON_THRESHOLD", library_folder_name="",
        is_size_gate="yes", gate_base_code="P3_EP", collision_flag="",
        mapping_evidence="",
        open_question="Production-only tag and a strict subset of P3_EP, so it is a size flag on Extraneous Polymer, not a separate defect. Confirm the gate cut (300 microns per the client).",
    ),
    dict(
        canonical_id="hema_micron_gate", canonical_name="HEMA micron gate", kind="gate",
        code_in_project2="", code_in_updated_20260922="",
        code_in_production_20260925="P3_HE_MICRON_THRESHOLD", library_folder_name="",
        is_size_gate="yes", gate_base_code="P3_HE", collision_flag="",
        mapping_evidence="",
        open_question="Production-only tag and a strict subset of P3_HE, the production HEMA Obstruction code. In the production files every P3_HE image also carries this tag, so HEMA Obstruction is unconditional and not size gated. Confirm the gate cut and that reading.",
    ),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def label_defs(root: ET.Element) -> list[tuple[str, str]]:
    """Defined labels with their CVAT type, from project (project files) or job (production files)."""
    meta = root.find("meta")
    container = meta.find("project")
    if container is None:
        container = meta.find("job")
    labels = container.find("labels")
    out: list[tuple[str, str]] = []
    if labels is not None:
        for lab in labels.findall("label"):
            out.append((lab.findtext("name"), lab.findtext("type")))
    return out


def inventory_file(path: Path, group: str) -> dict:
    """Per-file code inventory, from label attributes on each shape."""
    root = ET.parse(path).getroot()  # trusted client export, XXE accepted
    box_codes: dict[str, int] = {}
    tag_codes: dict[str, int] = {}
    for image in root.findall("image"):
        for box in image.findall("box"):
            box_codes[box.get("label")] = box_codes.get(box.get("label"), 0) + 1
        for tag in image.findall("tag"):
            tag_codes[tag.get("label")] = tag_codes.get(tag.get("label"), 0) + 1
    return {
        "group": group,
        "file": path.name,
        "sha256": sha256(path),
        "images": len(root.findall("image")),
        "box_shapes": sum(box_codes.values()),
        "tag_shapes": sum(tag_codes.values()),
        "box_codes": dict(sorted(box_codes.items())),
        "tag_codes": dict(sorted(tag_codes.items())),
        "defined_labels": [{"name": n, "type": t} for n, t in label_defs(root)],
    }


def used_codes_by_group(inventories: list[dict]) -> dict[str, set[str]]:
    used: dict[str, set[str]] = {g: set() for g in GROUPS}
    for inv in inventories:
        used[inv["group"]].update(inv["box_codes"])
        used[inv["group"]].update(inv["tag_codes"])
    return used


def crosswalk_codes(rows: list[dict], column: str) -> set[str]:
    return {r[column] for r in rows if r[column]}


def check_gate_subset(inventories: list[dict], gate_base: dict[str, str]) -> dict:
    """For each gate code: every shape carrying it also carries its base code in the same image, same file.

    Returns per-gate counts plus a failure count.
    """
    result: dict[str, dict] = {}
    failures = 0
    for gate, base in gate_base.items():
        gate_shapes = 0
        base_shapes = 0
        for inv in inventories:
            path = DATA / inv["file"]
            root = ET.parse(path).getroot()
            for image in root.findall("image"):
                has_gate = any(
                    shape.get("label") == gate
                    for kind in ("box", "tag")
                    for shape in image.findall(kind)
                )
                if not has_gate:
                    continue
                gate_shapes += 1
                has_base = any(
                    shape.get("label") == base
                    for kind in ("box", "tag")
                    for shape in image.findall(kind)
                )
                if has_base:
                    base_shapes += 1
        ok = gate_shapes == base_shapes
        if not ok:
            failures += 1
        result[gate] = {
            "base_code": base,
            "images_with_gate": gate_shapes,
            "images_with_gate_and_base": base_shapes,
            "ok": ok,
        }
    return {"gates": result, "failures": failures}


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    inventories: list[dict] = []
    for group, files in GROUPS.items():
        for name in files:
            inventories.append(inventory_file(DATA / name, group))

    used = used_codes_by_group(inventories)

    # Shape kind per source, DERIVED from the exports rather than authored, so no
    # cell can claim a kind the file contradicts. A code carried by a shape is
    # "box" or "tag" (a code that is both anywhere in one group is written as
    # "box|tag"); a code the vocabulary defines but no shape carries is
    # "defined_only"; a code the vocabulary does not define at all is left empty.
    # The canonical "kind" is the union over the sources that carry the code, so a
    # defect that is a tag in one project and a box in another says so.
    kinds_by_group: dict[str, dict[str, set[str]]] = {g: {} for g in GROUPS}
    defined_by_group: dict[str, set[str]] = {g: set() for g in GROUPS}
    for inv in inventories:
        g = inv["group"]
        for code in inv["box_codes"]:
            kinds_by_group[g].setdefault(code, set()).add("box")
        for code in inv["tag_codes"]:
            kinds_by_group[g].setdefault(code, set()).add("tag")
        for lab in inv["defined_labels"]:
            defined_by_group[g].add(lab["name"])

    KIND_COLUMNS = {
        "project2": ("code_in_project2", "kind_project2", "used_project2"),
        "updated_20260922": ("code_in_updated_20260922", "kind_updated_20260922",
                             "used_updated_20260922"),
        "production_20260925": ("code_in_production_20260925", "kind_production_20260925",
                                "used_production_20260925"),
    }
    derived: dict[str, dict] = {}
    for row in CANONICAL:
        cells = {
            "kind_project2": "", "kind_updated_20260922": "", "kind_production_20260925": "",
            "used_project2": "", "used_updated_20260922": "", "used_production_20260925": "",
            "kind_conflict": "no",
        }
        seen: set[str] = set()
        for group, (code_col, kind_col, used_col) in KIND_COLUMNS.items():
            code = row[code_col]
            if not code:
                continue
            kinds = kinds_by_group[group].get(code, set())
            if kinds:
                cells[kind_col] = "|".join(sorted(kinds))
                cells[used_col] = "yes"
                seen |= kinds
            elif code in defined_by_group[group]:
                cells[kind_col] = "defined_only"
                cells[used_col] = "no"
            else:
                cells[kind_col] = "not_present"
                cells[used_col] = "no"
        if row["is_size_gate"] == "yes":
            cells["kind"] = "gate"
        else:
            cells["kind"] = "|".join(sorted(seen)) if seen else row["kind"]
        cells["kind_conflict"] = "yes" if len(seen) > 1 else "no"
        derived[row["canonical_id"]] = cells

    # Acceptance 1: every code used on a shape is present in its crosswalk column.
    col_by_group = {
        "project2": "code_in_project2",
        "updated_20260922": "code_in_updated_20260922",
        "production_20260925": "code_in_production_20260925",
    }
    coverage_failures = []
    coverage_detail = {}
    for group, column in col_by_group.items():
        listed = crosswalk_codes(CANONICAL, column)
        missing = sorted(used[group] - listed)
        coverage_detail[group] = {
            "used_on_shapes": sorted(used[group]),
            "used_count": len(used[group]),
            "listed_in_crosswalk": sorted(listed),
            "missing_from_crosswalk": missing,
        }
        if missing:
            coverage_failures.append((group, missing))

    # Acceptance 4: gate subset property.
    gate_base = {r["code_in_production_20260925"]: r["gate_base_code"]
                 for r in CANONICAL if r["is_size_gate"] == "yes"}
    gate_check = check_gate_subset(
        [inv for inv in inventories if inv["group"] == "production_20260925"],
        gate_base,
    )

    # Self-checks on the authored table.
    checks = []
    checks.append(("every_used_code_in_crosswalk", not coverage_failures,
                   f"missing: {coverage_failures}" if coverage_failures else "all 9 files covered"))
    checks.append(("gate_subset_holds", gate_check["failures"] == 0,
                   f"{gate_check['failures']} gate(s) failed"))
    collisions = [r for r in CANONICAL if r["collision_flag"]]
    collision_names = {r["collision_flag"] for r in collisions}
    checks.append(("collisions_flagged_and_answered",
                   all(r["open_question"] for r in collisions) and len(collision_names) >= 2,
                   f"collision flags: {sorted(collision_names)}"))
    unmapped = [r for r in CANONICAL if r["library_folder_name"] and not r["code_in_updated_20260922"]]
    checks.append(("unmapped_library_names_carry_a_question",
                   all(r["open_question"] for r in unmapped),
                   f"unmapped library names: {[r['canonical_name'] for r in unmapped]}"))
    mapped_lib = [r for r in CANONICAL
                  if r["library_folder_name"] and r["code_in_updated_20260922"]]
    checks.append(("mapped_library_names_carry_evidence",
                   all(r["mapping_evidence"] for r in mapped_lib),
                   f"mapped library names: {len(mapped_lib)}"))
    kinds_ok = all(tok in ("box", "tag", "gate")
                   for r in CANONICAL for tok in str(r["kind"]).split("|") if tok)
    checks.append(("kinds_valid", kinds_ok, "box|tag|gate, pipe-joined where sources disagree"))
    ids_unique = len({r["canonical_id"] for r in CANONICAL}) == len(CANONICAL)
    checks.append(("canonical_ids_unique", ids_unique, f"{len(CANONICAL)} rows"))
    kind_mismatches = [
        (r["canonical_id"], r["kind"], derived[r["canonical_id"]]["kind"])
        for r in CANONICAL
        if set(str(r["kind"]).split("|")) != set(str(derived[r["canonical_id"]]["kind"]).split("|"))
    ]
    checks.append(("authored_kind_matches_the_files", not kind_mismatches,
                   f"mismatches: {kind_mismatches}" if kind_mismatches
                   else "every authored kind matches the shape kinds in the exports"))
    conflict_rows = [r for r in CANONICAL if derived[r["canonical_id"]]["kind_conflict"] == "yes"]
    checks.append(("source_dependent_kind_is_flagged_and_questioned",
                   all(r["open_question"].strip() for r in conflict_rows),
                   f"source-dependent kinds: {[r['canonical_id'] for r in conflict_rows]}"))
    defined_only_rows = [
        (r["canonical_id"], g)
        for r in CANONICAL
        for g in GROUPS
        if derived[r["canonical_id"]][KIND_COLUMNS[g][1]] == "defined_only"
    ]
    checks.append(("defined_only_cells_are_not_counted_as_shapes",
                   all(derived[cid][KIND_COLUMNS[g][2]] == "no"
                       for cid, g in defined_only_rows),
                   f"{len(defined_only_rows)} defined-only cells: {defined_only_rows}"))

    failed = sum(1 for _, ok, _ in checks if not ok)

    # Write the crosswalk.
    csv_path = DATA / "crosswalk.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in CANONICAL:
            writer.writerow({**row, **derived[row["canonical_id"]]})
    crosswalk_md5 = hashlib.md5(csv_path.read_bytes()).hexdigest()
    crosswalk_sha256 = sha256(csv_path)

    evidence = {
        "ticket": "009-canonical-crosswalk",
        "date": "2026-10-15",
        "files": inventories,
        "used_codes_by_group": {g: sorted(s) for g, s in used.items()},
        "coverage": coverage_detail,
        "gate_subset_check": gate_check,
        "source_kinds": {row["canonical_id"]: derived[row["canonical_id"]] for row in CANONICAL},
        "kind_conflict_rows": [r["canonical_id"] for r in CANONICAL
                               if derived[r["canonical_id"]]["kind_conflict"] == "yes"],
        "crosswalk": {
            "path": "data/crosswalk.csv",
            "rows": len(CANONICAL),
            "md5": crosswalk_md5,
            "sha256": crosswalk_sha256,
            "columns": COLUMNS,
        },
        "collision_flags": {
            "P3_HE_shared_code": "P3_HE is HEMA Fragment (box) in the Sep-22 project and HEMA Obstruction (box) in the 7 production files.",
            "F2_FOV_naming_anomaly": "View Obstructed is P2_FOV in the Sep-22 project and F2_FOV in the production files.",
        },
        "checks": [{"name": n, "ok": ok, "note": note} for n, ok, note in checks],
        "check_count": len(checks),
        "failed_count": failed,
    }
    ev_path = RUN / "crosswalk_evidence.json"
    ev_path.write_text(json.dumps(evidence, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"crosswalk rows: {len(CANONICAL)}")
    print(f"used codes: project2 {len(used['project2'])}, "
          f"updated {len(used['updated_20260922'])}, "
          f"production {len(used['production_20260925'])}")
    print(f"coverage failures: {len(coverage_failures)}")
    print(f"gate subset failures: {gate_check['failures']}")
    for name, ok, note in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {note}")
    print(f"crosswalk.csv md5: {crosswalk_md5}")
    print(f"crosswalk.csv sha256: {crosswalk_sha256}")
    print(f"evidence: {ev_path.relative_to(REPO)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
