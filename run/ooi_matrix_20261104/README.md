# OOI label table, 2026-11-04 (ticket 027)

`ooi_labels.csv` is the object label table over the frozen split: one row for each of the
7,470 pictures of `run/split_20261103_v8/split_70_15_15.csv`, carrying both column groups,
the eight class columns and the four gate columns, beside the twelve lens columns and
clear.

## Files

| file | what | md5 |
| --- | --- | --- |
| `ooi_labels.csv` | the table, 7,470 rows, 27 columns, sorted by `picture_md5` | `7fd1106e355464deac72da73aa6b2c4b` |
| `counts.json` | the builder's own count summary and input provenance | `d9eb9a0eccf67b674476e08d1ef17f1d` |
| `verify_ooi_matrix.log` | the verifier run that gates this table (exit 0) | see log |

Built and verified with `D:/fmd-analysis/.venv/Scripts/python.exe`:

```
python experiments/multilabel_ooi/build_ooi_matrix.py     # writes the table and counts.json
python experiments/multilabel_ooi/verify_ooi_matrix.py    # exit 0 = every count asserted
```

A rebuild is byte-identical: two consecutive builds produced md5
`7fd1106e355464deac72da73aa6b2c4b`.

## Inputs, pinned

| input | md5 |
| --- | --- |
| `run/eda_full_20261029/resolved_labels.csv` | `f61ea0b90df095ebe52d1332f8bfdb8a` |
| `run/split_20261103_v8/split_70_15_15.csv` | `1a71d66d2de384cf47a3fcf7d9115baa` (the frozen split) |
| `run/multilabel_lp_v8_20261103/labels_b.csv` | `764a412597aad359f644eb1414d31cda` |

No split is built or changed by this ticket: the join to the annotation is on `picture_md5`
and the split membership, 5,239 train / 1,110 val / 1,121 test, comes from the frozen file.

## Columns, 27 in order

1. `picture_md5`, `split`.
2. Eight class columns, presence of the object at any size:
   `class_bubble`, `class_bubble_cluster`, `class_foreign_matter`, `class_fiber`,
   `class_wet_package`, `class_hema`, `class_extraneous_polymer`, `class_surface_groove`.
3. Four gate columns, the micron flag for the four gated classes:
   `gate_foreign_matter`, `gate_fiber`, `gate_extraneous_polymer`, `gate_hema`.
4. Twelve lens columns copied verbatim from `labels_b.csv`: `P1_MPP`, `P1_ML`, `P2_LOC`,
   `P2_DC`, `P1_NL`, `P1_FL`, `P2_LD`, `P1_COC`, `P2_DS`, `P2_FOV`, `P2_BSC`, `P1_PPM`.
5. `clear`, copied verbatim from `labels_b.csv` (`is_clear`).

## How each class is read

| column | evidence in the annotation of record | pictures | val | test |
| --- | --- | --- | --- | --- |
| `class_bubble` | `bubble` + `bubble_irregular` + `stretched_bubble` | 2,171 | 326 | 325 |
| `class_bubble_cluster` | `bubble_cluster` | 1,132 | 170 | 170 |
| `class_foreign_matter` | `foreign_matter` + its micron gate | 798 | 110 | 112 |
| `class_fiber` | `fiber` + its micron gate | 392 | 60 | 58 |
| `class_wet_package` | `wet_package` | 314 | 47 | 47 |
| `class_hema` | `hema_fragment` + `hema_obstruction` with `shape_kind` box + its micron gate | 154 | 25 | 27 |
| `class_extraneous_polymer` | `extraneous_polymer` + its micron gate | 142 | 19 | 17 |
| `class_surface_groove` | no pictures anywhere, all-zero column | 0 | 0 | 0 |

| gate column | evidence | gate pictures | of which un-gated |
| --- | --- | --- | --- |
| `gate_foreign_matter` | `foreign_matter_micron_gate` rows | 454 | 344 |
| `gate_fiber` | `fiber_micron_gate` rows | 362 | 30 |
| `gate_extraneous_polymer` | `extraneous_polymer_micron_gate` rows | 135 | 7 |
| `gate_hema` | `hema_micron_gate` rows | 151 | 3 |

The gate row is class evidence for its own class and nothing else, so every gate cell sits
inside its class cell: 7,470 rows x 4 gates, zero violations.

## Exclusions

- `bubble_on_123` (13 pictures) and `bubble_on_edge` (14 pictures) are library-only: they
  are in no map, so they can set no column. None of the 27 sits in the frozen split.
- The legacy whole-image `hema_obstruction` tag (`P2_HMO`) is not evidence. Exactly one
  picture in the split carries it and nothing else, `d50402e0b6d5817615e343aecb3447df`
  on the val side, and it is not a HEMA picture: the class reads 154 with it excluded and
  155 if the tag were counted.

## What the verifier does

`verify_ooi_matrix.py` takes nothing from the builder. It pins the frozen split by md5,
rebuilds every class and gate cell from the annotation with its own map written over the
raw annotation codes (the builder reads canonical ids), then asserts: row count and key
set, all eight class counts, all four gate counts, val/test per class, the split totals,
the gate-inside-class rule on every row, the twelve lens columns and clear row for row
against `labels_b.csv`, the HEMA exclusion with its 155 counterfactual, the two legacy
bubble tags and the Surface Groove absence as real non-vacuous rules, and that
`counts.json` agrees with the table. It then edits one cell of a copy, once for a class,
once for a gate and once for a lens column, and fails unless the failure names that cell.

Extra adversarial coverage (9 mutations: dropped row, swapped class cells, split change,
clear change, HEMA on the tag-only picture, forced subset break, non-binary cell, lens
change, rewritten key) were all caught, and an untouched copy produced zero failures.
