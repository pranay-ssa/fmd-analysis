---
title: Split considerations, frozen 2026-10-26
date: 2026-10-26
type: decision
status: active
where: docs/decisions/2026-10-26-split-considerations.md
---

# Split considerations, frozen 2026-10-26

The lead asked that the approved EDA distribution be maintained for future splits. These are
the rules that were agreed and frozen, and the splits built on them.

## Rules

1. Population is the annotation: one annotation of record per picture, newest file wins,
   duplicate copies of a picture counted once. 6,938 pictures, including 2,156 Clear.
2. Clear is a label. Every annotated picture carries something, so there is no 0-label row.
3. Label space is Draft 2 codes plus Clear: 15 image tags and 8 object classes in the guide,
   of which 12 tags and 7 object classes carry pictures. The four classes with no examples
   (Edge Bottle-Capped, Torn Lens, Lens Rupture, Surface Groove) are listed at zero and are
   never split positives.
4. Legacy classes are excluded: HEMA Obstruction, Bubble On 123, Bubble On Edge. Their 105
   pictures carry no Draft 2 code and are not split rows.
5. The four gated object classes are positive on the micron gate only: Foreign Matter 171,
   Fiber 136, Extraneous Polymer 33, HEMA 94.
6. The gate rule applies to the four gated classes only. A picture that carries a debris object
   without a gate tag and nothing else has no positive to train on, so it is not a split row
   (174 pictures). A picture that carries any other label stays a row and contributes that
   label; its un-gated debris object simply adds no positive.
7. The flag is never a label of its own: in the split it is the positive for its class, in
   the EDA it is the "of which flagged" column.
8. The 32 objects renamed between Fiber and Extraneous Polymer stay under Fiber in the EDA,
   but only the gate tag makes a split positive, so Fiber is 136, not 168 and not 137.
9. Bubble Cluster is 428 in the EDA and 378 among split rows. The two labels rescued from the
   older library are dropped, because the annotation of record calls those objects Bubble.
10. Bubble is one class: Bubble Irregular, Stretched Bubble and the older plain Bubble names
    fold in.
11. A lower annotation file never overrides a class the annotation of record already assigns;
    it only fills a picture the record leaves empty.
12. Split rows are 6,659. Both ratios are produced: 70/30 at 4,653 / 2,006 and 80/20 at
    5,326 / 1,333. Stratification is iterative (Sechidis 2011), two-way, content md5 groups
    on one side, no validation split.
13. A legacy mention does not disqualify a picture that carries a Draft 2 code. Eight pictures
    carry the HEMA Obstruction tag and also a condition (Lens Off Center 2, Multiple Lens 2,
    Low Dose 4; four in train, four in test). They stay rows and contribute only their
    condition. The obstruction tag is not a column, so nothing about it is trained or scored,
    and the object flag reads 0 for them because obstruction is not one of the seven object
    classes. The 78 pictures whose only mark is obstruction remain excluded under rule 4.

## Split positives, v5

| Column | Positives |
|---|---|
| Foreign Matter gate | 171 |
| Fiber gate | 136 |
| Extraneous Polymer gate | 33 |
| HEMA gate | 94 |
| Bubble | 862 |
| Bubble Cluster | 428 |
| Wet Package | 146 |
| Missing Primary Package | 1,426 |
| Multiple Lens | 1,439 |
| No Lens | 325 |
| Cavity Off Center | 184 |
| Folded Lens | 237 |
| Lens Off Center | 957 |
| Dirty Camera | 329 |
| Dirty Strobe | 43 |
| Low Dose | 215 |
| View Obstructed | 24 |
| Package Misalignment | 2 |
| Bubble Scatter | 6 |
| Clear | 2,156 |

## What changed against v4

- Rows 6,574 to 6,659: pictures that carry a non-gated label are no longer dropped for also
  carrying an un-gated debris object.
- Every non-gated class rises to its EDA count: Bubble 789 to 862, Bubble Cluster 380 to 428,
  Wet Package 126 to 146, Multiple Lens 1,402 to 1,439, Lens Off Center 922 to 957.
- Fiber gate positives 137 to 136: the one rule-flipped picture carries no gate tag.
- Bubble Cluster is 428, matching the EDA, after the two rescued labels are dropped.
- Totals: 70/30 4,568 / 2,006 to 4,653 / 2,006; 80/20 5,269 / 1,305 to 5,326 / 1,333.
- The gate classes are rare, so their test shares still vary by a few pictures against the exact
  ratio (Foreign Matter 129 / 42 at 70/30).

## Amendment, 2026-10-28: revised production annotation

The seven production annotation files were re-exported on 2026-10-26 and replaced in `data/`.
The rules above are unchanged; three inputs moved.

- 133 of the 1,047 pictures were relabelled, almost all of them folding Bubble Irregular and
  Stretched Bubble into Bubble at source, plus a scatter of debris moves between Foreign Matter,
  Fiber, Extraneous Polymer, Wet Package and Bubble Cluster. Four boxes moved, two pictures.
- Class pictures after the revision: Foreign Matter 326 with a gate of 166, Fiber 179 with a gate
  of 137, Extraneous Polymer gate 34, HEMA gate 94, Bubble Cluster 427, Bubble 862 unchanged,
  Wet Package 146 unchanged.
- Splits `run/split_20261028_v6/` supersede v5 for the experiment: same 6,659 rows, the same
  drops, and seven pictures that change side at 80/20 (5,327 / 1,332). Variant A of the
  experiment is untouched, because the seven are object-only rows; variant B moves by one.

## Artifacts

- `run/split_20261026_v5/split_70_30.csv`, `split_80_20.csv`, `meta.json`
- Builder `experiments/multilabel_edge/build_split_v5.py`
- Verifier `experiments/multilabel_edge/verify_split_v5.py` (recomputes from the annotation,
  checks every per-class count against the files, proves a moved row is caught)

`run/split_20261023_v4/` stays on disk as the record of what earlier runs used. Models
trained on it are not comparable with models trained on v5.

## Amendment, 2026-10-29: EDA and split read the size flag differently

The rule was restated by the user and is now explicit:

- **EDA**: a picture that shows a class belongs to that class. The micron-gate tag is the
  subset of that class and is reported as "of which size-flagged". An un-gated object-only
  picture is still counted in its class in every EDA table.
- **Split**: the four gated classes are positive on the size flag only, as frozen in rule 5.
  An un-gated object-only picture has no split positive and is outside the split, even though
  the EDA counts it in its class.

The two readings answer different questions: "how many pictures show this class" and "which
pictures can the model learn to fail". Never present the gate-only split count as the class
count, or the class count as the split positives.
