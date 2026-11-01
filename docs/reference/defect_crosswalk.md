---
title: The canonical defect crosswalk across the three annotation vocabularies
date: 2026-10-15
type: reference
status: active
where: docs/reference/defect_crosswalk.md
---

# The canonical defect crosswalk

One row per defect, mapping every annotation code and every plain library name
across the three vocabularies onto a single entry. Built and checked by ticket
009 (`experiments/eda_full/build_crosswalk.py` and
`experiments/eda_full/verify_crosswalk.py`). The table itself is
`data/crosswalk.csv`; the per-file code inventory it was built from is
`run/eda_full_20261015/crosswalk_evidence.json`.

## The three vocabularies

| Source | CVAT target | Shape | Codes used | Plain names |
|---|---|---|---|---|
| `data/annotations.xml` | project 2, old ICube Defects Library | 2,020 boxes, 0 tags over 435 images | 0 | 10 |
| `data/Updated Annotations 20260922.xml` | project 3, "ICube Data 20260915" | 183 boxes, 4,930 tags over 6,097 images | 20 used of 22 defined | 0 |
| `data/annotations_4521940.xml` ... `4521946.xml` | 7 production jobs | 12,793 boxes, 1,487 tags over 1,047 images | 24 used of 25 defined | 0 |

The labels are the CVAT 1.1 detection-export form: `label="CODE"` is an
attribute on each `<box>` or `<tag>` element.

## The map

28 canonical defects: 12 boxes, 12 tags, 4 gates.

| id | name | kind | project 2 | Sep-22 | production |
|---|---|---|---|---|---|
| bubble | Bubble | box | Bubble | P2_BB | P2_BB |
| bubble_cluster | Bubble Cluster | box | Bubble Cluster | P2_BC | P2_BC |
| bubble_irregular | Bubble Irregular | box | Bubble Irregular | P2_BI | P2_BI |
| stretched_bubble | Stretched Bubble | box | | P2_BST | P2_BST |
| extraneous_polymer | Extraneous Polymer | box | Extraneous Polymer | P3_EP | P3_EP |
| fiber | Fiber | box | Fiber | P3_FIB | P3_FIB |
| foreign_matter | Foreign Matter | box | Foreign Matter | P3_FM | P3_FM |
| hema_fragment | HEMA Fragment | box | HEMA Fragment | P3_HE | |
| hema_obstruction | HEMA Obstruction | box\|tag | | P2_HMO | P3_HE |
| wet_package | Wet Package | box | Wet Package | P2_WP | P2_WP |
| bubble_on_123 | Bubble On 123 | box | Bubble On 123 | | |
| bubble_on_edge | Bubble On Edge | box | Bubble On Edge | | |
| missing_primary_package | Missing Primary Package | tag | | P1_MPP | P1_MPP |
| multiple_lenses | Multiple Lenses | tag | | P1_ML | P1_ML |
| lens_off_center | Lens Off Center | tag | | P2_LOC | P2_LOC |
| missing_lens | Missing Lens | tag | | P1_NL | P1_NL |
| cavity_off_center | Cavity Off Center | tag | | P1_COC | P1_COC |
| folded_lens | Folded Lens | tag | | P1_FL | P1_FL |
| dirty_camera | Dirty Camera | tag | | P2_DC | P2_DC |
| low_dose | Low Dose | tag | | P2_LD | P2_LD |
| dirty_strobe | Dirty Strobe | tag | | P2_DS | P2_DS |
| bubble_scatter | Bubble Scatter | tag | | P2_BSC | P2_BSC |
| package_misalignment | Package Misalignment | tag | | P1_PPM | P1_PPM |
| view_obstructed | View Obstructed | tag | | P2_FOV | F2_FOV |
| foreign_matter_micron_gate | Foreign Matter micron gate | gate | | | P3_FM_MICRON_THRESHOLD |
| fiber_micron_gate | Fiber micron gate | gate | | | P3_FIB_MICRON_THRESHOLD |
| extraneous_polymer_micron_gate | Extraneous Polymer micron gate | gate | | | P3_EP_MICRON_THRESHOLD |
| hema_micron_gate | HEMA micron gate | gate | | | P3_HE_MICRON_THRESHOLD |

Empty cells mean the row has no code in that vocabulary at all. `library_folder_name`
and `is_size_gate` in `data/crosswalk.csv` carry the rest.

## The shape kind is per source, not one value per defect

`kind` is the union of the kinds the sources actually carry, so a defect that is a
whole-image tag in one project and a box in another says so instead of picking a
winner. `data/crosswalk.csv` also carries the kind per source, which is the column
to read when the box and tag tiers are counted separately:

| Column | Values |
|---|---|
| `kind_project2` | box, tag, box\|tag, `defined_only`, `not_present`, or empty where the row has no code in that vocabulary |
| `kind_updated_20260922` | as above |
| `kind_production_20260925` | as above |
| `used_*` | `yes` when a shape carries the code in that source, `no` otherwise, empty when there is no code |

`defined_only` means the vocabulary defines the code but no shape carries it, so it
must never be counted as an instance. Three cells are in that state: `P2_BSC` in the
production files, and `P1_PPM` and `P2_FOV` in the Sep-22 project.

One canonical defect is source dependent: **HEMA Obstruction** is a whole-image tag
(`P2_HMO`) in the Sep-22 project and a box code (`P3_HE`) in the production files, so
its `kind` reads `box|tag` and its `kind_conflict` reads `yes`. It is the only such
row. Every other defect carries one kind consistently.

Both the builder and the verifier now derive the per-source kind from the exports and
diff it against the table, so a cell can no longer claim a kind the file contradicts.

## The collisions

| Flag | Rows | What collides | Client question |
|---|---|---|---|
| `P3_HE_shared_code` | hema_fragment, hema_obstruction | `P3_HE` is HEMA Fragment in the Sep-22 project and HEMA Obstruction in the production files. HEMA Obstruction is also a tag (`P2_HMO`) in Sep-22 and a box (`P3_HE`) in production. | Which reading applies to the production boxes, and which shape kind is intended. |
| `F2_FOV_naming_anomaly` | view_obstructed | View Obstructed is `P2_FOV` in Sep-22 and `F2_FOV` in production. The scheme is `P1_`/`P2_`/`P3_`, so `F2_` is anomalous. | Confirm the intended code and whether the two are one class. |

Neither collision is merged. `P3_HE` stays on two rows and is never written as a
single canonical defect.

## The size gates

The four `*_MICRON_THRESHOLD` codes are production-only tags and each one is a
strict subset of a base box code. For every gate, every image that carries it
also carries its base code in the same file. This is checked, not assumed, by
both the builder and the verifier.

| Gate | Base | Images with the gate | Also carry the base |
|---|---|---|---|
| `P3_FM_MICRON_THRESHOLD` | `P3_FM` | 171 | 171 |
| `P3_FIB_MICRON_THRESHOLD` | `P3_FIB` | 136 | 136 |
| `P3_EP_MICRON_THRESHOLD` | `P3_EP` | 33 | 33 |
| `P3_HE_MICRON_THRESHOLD` | `P3_HE` | 95 | 95 |

Because every `P3_HE` image also carries the gate, HEMA Obstruction is
unconditional and is not size gated.

## Library names, and the evidence for each mapping

The old library is the only source that uses plain names. Eight of its ten names
map onto a code; the mapping and its evidence are in the `mapping_evidence`
column:

- `Extraneous Polymer` is pinned by the CVAT task name `P3_EP` on the blob
  folder of the same name.
- `Bubble`, `Bubble Cluster`, `Bubble Irregular`, `Fiber`, `Foreign Matter`,
  `HEMA Fragment` and `Wet Package` are pinned by the acronym list in
  `docs/annotations_update_20260923.md` section 2.2.
- `Bubble On 123` and `Bubble On Edge` are **left unmapped**. Neither newer
  project defines a code for them, so there is nothing to map onto. They stay in
  scope as their own classes.

One code, `P2_BST`, is pinned by elimination rather than by a task name or an
acronym. The `open_question` column says so for that row.

## Open questions for the client

1. The `P3_HE` collision. Is it HEMA Fragment or HEMA Obstruction, and is it a
   box or a tag.
2. `F2_FOV`. Confirm the intended code for View Obstructed.
3. `P2_BST` = Stretched Bubble. Pinned by elimination.
4. `Bubble On 123` and `Bubble On Edge`. Both lost their labels in the newer
   projects; confirm whether they are retained or consolidated.
5. `Package Misalignment` (`P1_PPM`). Defined in Sep-22 with no annotation
   there; used only by the production files (2 images).
6. `Bubble Scatter` (`P2_BSC`). Defined in both newer projects, used only by the
   Sep-22 project.
7. Low Dose. The Sep-22 Low Dose task carries the tag on 3.9 percent of its
   folder; confirm the task is finished.
8. The gate cut. Confirm the four gates apply at 300 microns.

## Notes and caveats

- The production files hold 1,487 `<tag>` shapes across the 7 jobs, not the
  1,318 recorded in `docs/cvat_production_20260925_pull.md`. The box count
  agrees at 12,793. The crosswalk uses the file count and flags the difference.
- Three codes are defined but carry no shape anywhere: `P1_PPM` and `P2_FOV` in
  the Sep-22 project, `P2_BSC` in the production files. They are carried in the
  crosswalk as vocabulary, not as annotated instances.
- This table is frozen before any counting ticket reads it. The client questions
  above are carried out by ticket 018.

## Evidence

| What | Where |
|---|---|
| Builder, 10 self-checks | `experiments/eda_full/build_crosswalk.py` |
| Verifier, 32 checks, 0 failed | `experiments/eda_full/verify_crosswalk.py` |
| Protocol and pitfalls | `experiments/eda_full/README.md` |
| Per-file code inventory and checks | `run/eda_full_20261015/crosswalk_evidence.json` |
| The crosswalk | `data/crosswalk.csv` (md5 `a33b1d96d6fc1ac0021a8d1372f4d875`) |
| The arrival notes for the Sep-22 project | `docs/annotations_update_20260923.md` |
| The production pull and its code legend | `docs/cvat_production_20260925_pull.md` |

## Correction log

| When | What | Why |
|---|---|---|
| 2026-10-15, before freeze | `hema_obstruction.kind` corrected from `box` to `box|tag` | The first build stated one kind for a defect that the two projects annotate differently. `P2_HMO` is a whole-image tag with 174 instances in the Sep-22 project, and `P3_HE` is a box with 95 instances in the production files. A single `box` would have put tag instances into the box tier in every later count. |
| 2026-10-15, before freeze | Per-source kind, `used_*` and `defined_only` columns added | The first build could not distinguish a source that carries a code from one that merely defines it, which is what hid the error above. Three cells are defined but unused. |
| 2026-10-15, before freeze | Two derived checks added to the builder, three to the verifier | So the same class of error fails a check instead of reaching a workbook. |
