---
title: experiments/eda_full/ - the canonical crosswalk across the three annotation vocabularies
date: 2026-10-15
type: protocol
status: active
where: experiments/eda_full/README.md
---

# Canonical crosswalk (ticket 009)

The three annotation sources label the same defects with three different
vocabularies:

| Source | CVAT target | Codes | Plain names |
|---|---|---|---|
| `data/annotations.xml` | project 2, "Sweta Annotations Defect Library" (old ICube Defects Library) | 0 | 10 |
| `data/Updated Annotations 20260922.xml` | project 3, "ICube Data 20260915" | 22 | 0 |
| `data/annotations_4521940.xml` ... `4521946.xml` | 7 production jobs | 24 | 0 |

The crosswalk is one row per canonical defect. It maps every code and every
plain name onto a single entry, and it keeps the collisions visible instead of
merging them. The output is `data/crosswalk.csv`.

## What is here

- `build_crosswalk.py` - reads the 9 XMLs with `ElementTree.parse`, writes
  `data/crosswalk.csv` and `run/eda_full_20261015/crosswalk_evidence.json`, and
  checks its own numbers (28 rows, coverage, gate subset, collisions). Exits
  non-zero on a failed check.
- `verify_crosswalk.py` - a second parsing route that reads the 9 XMLs with
  `iterparse` over `("end",)` events, re-derives the code inventory, diffs it
  against the crosswalk and the evidence file, and diffs every headline against
  a hand-typed `EXPECTED` table. Reports a check count and a failure count.
  Exits non-zero on any failure.

```bash
./.venv/Scripts/python.exe experiments/eda_full/build_crosswalk.py
./.venv/Scripts/python.exe experiments/eda_full/verify_crosswalk.py
```

Current state: 28 canonical rows, 10 builder self-checks and 32 verifier checks, 0 failed.

## Columns

`canonical_id, canonical_name, kind, kind_conflict, code_in_project2,
code_in_updated_20260922, code_in_production_20260925, kind_project2,
kind_updated_20260922, kind_production_20260925, used_project2,
used_updated_20260922, used_production_20260925, library_folder_name,
is_size_gate, gate_base_code, collision_flag, mapping_evidence, open_question`

- `kind` is `box` (a localised defect), `tag` (a whole-image flag) or `gate`
  (a size flag on another defect). It is the union over the sources that carry
  the code, so a defect the two projects annotate differently reads
  `box|tag` and sets `kind_conflict` to `yes`. HEMA Obstruction is the one such
  row.
- `kind_<source>` is the shape kind that source actually carries, and is the
  column to read when the box and tag tiers are counted separately. Its values
  are `box`, `tag`, `box|tag`, `defined_only` (the vocabulary defines the code
  but no shape carries it), `not_present`, or empty when the row has no code in
  that vocabulary. `used_<source>` is `yes` only when a shape carries the code.
  Never count a `defined_only` cell as an instance. Three cells are in that
  state: `P2_BSC` in the production files, `P1_PPM` and `P2_FOV` in the Sep-22
  project.
- `kind_<source>` and `used_<source>` are DERIVED from the exports by both the
  builder and the verifier, not authored, so a cell cannot claim a kind the file
  contradicts. The authored `kind` is diffed against the derived value by a
  check.
- `code_in_project2` is the old library's label, which is a plain name, so it
  repeats `library_folder_name` for the 10 library classes.
- Empty cells mean the row has no code in that vocabulary at all. A cell that is
  `defined_only` means the vocabulary defines the code but no shape carries it.

## The collisions, kept visible

| Collision | Detail | Client question |
|---|---|---|
| `P3_HE_shared_code` | `P3_HE` is HEMA Fragment (box) in the Sep-22 project and HEMA Obstruction (box) in the 7 production files. One code, two meanings, so it is carried on two rows and never merged. | Which reading applies to the production boxes. |
| `F2_FOV_naming_anomaly` | View Obstructed is `P2_FOV` in the Sep-22 project and `F2_FOV` in the production files. | The scheme is `P1_`/`P2_`/`P3_`; confirm the intended code and whether the two are one class. |

HEMA Obstruction also changes shape kind across sources: a tag (`P2_HMO`) in the
Sep-22 project, a box (`P3_HE`) in the production files. That is recorded in the
row's `open_question`.

## The four gate codes

`P3_FM_MICRON_THRESHOLD`, `P3_FIB_MICRON_THRESHOLD`,
`P3_EP_MICRON_THRESHOLD` and `P3_HE_MICRON_THRESHOLD` are production-only tags.
Each one is a strict subset of its base box code. For each gate, every image
that carries the gate also carries its base code in the same file, which is what
makes the case that they are a size gate on a defect and not a separate defect.
Counts in `run/eda_full_20261015/crosswalk_evidence.json`:

| Gate | Base | Images with the gate | Also carry the base |
|---|---|---|---|
| `P3_FM_MICRON_THRESHOLD` | `P3_FM` | 171 | 171 |
| `P3_FIB_MICRON_THRESHOLD` | `P3_FIB` | 136 | 136 |
| `P3_EP_MICRON_THRESHOLD` | `P3_EP` | 33 | 33 |
| `P3_HE_MICRON_THRESHOLD` | `P3_HE` | 95 | 95 |

## Map of the ticket's acceptance checks

| Acceptance | Where it is proved |
|---|---|
| 1. every code on a shape is in the crosswalk | builder self-check `every_used_code_in_crosswalk`; verifier `used_codes_in_crosswalk__*` |
| 2. independent second derivation | `verify_crosswalk.py` (iterparse route) reports check and failure counts |
| 3. collisions flagged, never merged, each with a client question | rows with `collision_flag`; verifier `p3_he_not_merged`, `collisions_have_questions` |
| 4. gate subset asserted and checked | builder `check_gate_subset`; verifier `gate_subset__*` |
| 5. no code dropped, library names mapped only with evidence | `mapping_evidence` column; verifier `mapped_library_names_have_evidence`, `unmapped_library_names_have_question` |
| 6. byte-identical rebuild | `md5 data/crosswalk.csv` = `b6c1c027f2ede3d0a7af97da49f48a03` on a rerun |

## Pitfalls

- **The label code is an attribute, not a child element.** Each shape is
  `<box label="CODE" ...>` or `<tag label="CODE" ...>`. A `label` lookup that
  reads child elements returns nothing.
- **Project 2 uses plain names, not codes.** `code_in_project2` holds the plain
  label, which is also the library folder name. Do not expect a `Pn_xx` code
  there.
- **`iterparse` start events expose a partially built `<image>`.** Count children
  at the `end` event. The builder uses `ElementTree.parse`, the verifier uses
  `iterparse(events=("end",))`, so a regression in either route shows up as a
  diff between them.
- **A defined label is not a used code.** The Sep-22 project defines `P1_PPM`
  and `P2_FOV` with no shape; the production files define `P2_BSC` with no
  shape. They are carried in the crosswalk anyway (they are still part of the
  vocabulary), but they must not be counted as annotated instances.
- **The production tag total does not match the pull doc.** The files in
  `data/` hold 1,487 `<tag>` shapes across the 7 production jobs, not the 1,318
  recorded in `docs/cvat_production_20260925_pull.md`. The box count agrees
  (12,793). The crosswalk uses the file count. The discrepancy is flagged for
  whoever revisits that doc.
- **The XMLs are trusted client exports.** They were pulled from a private blob
  store on 2026-10-13 and made by the client's own account, so the standard
  library parser is used on purpose and the XXE warning is knowingly accepted.
  This is a deliberate choice on a trusted input, not an oversight.
- **The crosswalk is frozen before counting.** Per the acceptance rule, no
  counting ticket reads this table until the user freezes it. Ticket 018 carries
  the client questions out.
