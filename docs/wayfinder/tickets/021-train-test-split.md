---
title: "Ticket 021 - Train/test split, 70/30"
date: 2026-10-21
type: task
status: done
where: docs/wayfinder/tickets/021-train-test-split.md
---

# Ticket 021: Train/test split, 70/30

Blocked by tickets 023, 024, 025 and 026 (the 2026-10-22 meeting items). The
split is decided on their outputs. All four are done; see the map.

## Resolution (2026-10-23)

Built per the frozen recipe: iterative stratification (Sechidis 2011),
two-way 70/30, seed 42, content-md5 groups, no validation split. Builder
`experiments/multilabel_edge/build_split.py`; artifacts
`run/split_20261023/split.csv` + `meta.json`.

- 6,679 eligible rows: 4,645 train / 2,034 test (69.55 / 30.45).
- Zero group crossings; every eligible row exactly once.
- Rare columns, exact: PPM 1/1, Bubble Scatter 4/2, On 123 9/4, On Edge
  10/4, FOV 17/7. Their test metrics carry one-digit confidence.
- Largest drift from the 70/30 expectation: fiber gate 89/48 (expect
  95.9/41.1) and folded lens 167/59 (expect 158.2/67.8); both remain
  monotone-safe for training.
- Triple-checked under ticket 022's split legs: byte-identical rerun
  (md5 match), independent second derivation, hand-typed expected values,
  corrupted-input proof (5 moved rows caught, exit 1).

## REVISION - v2 supersedes the above (user decision 2026-10-23)

The user narrowed the label space: Draft 2 guide codes plus Clear ONLY.
On 123, On Edge and HEMA Obstruction are excluded as classes; gate tags
mark the four gated classes (already true in the matrix). Universe:
6,679 to 6,574 (105 rows carried only excluded labels). Split v2:
4,572 train / 2,002 test, same recipe, artifacts run/split_20261023_v2/,
builder build_split_v2.py, verifier verify_split_v2.py (all triple-check
legs pass, corrupted-input proof included). Decision record:
docs/decisions/2026-10-23-split-label-space.md. v1 artifacts stay on disk,
superseded.

## v3 (2026-10-23, later same day)

Option A applied: Clear exclusive. Matrix rev2 (Clear 2,156; the 10 dual
rows are Dirty Camera-only), split rebuilt on it: run/split_20261023_v3/,
4,568 train / 2,006 test, zero crossings, full triple check passes
(verify_split_v3.py). v2 and v1 stay on disk, superseded. The active split
is v3.

Iterative stratification (Sechidis et al.) over the 23-column multi-hot
matrix, two-way 70/30, seed 42, group-aware assignment keyed on content md5,
saved as `split.csv` (content hash, group id, split) with a `meta.json`
carrying the recipe, seed, input md5s and per-class split counts.

Checks at build time: per-class train/test drift inside a stated tolerance,
zero groups crossing splits, byte-identical rerun, rare classes (Bubble On
123: 13, Bubble On Edge: 14, Package Misalignment: 2, and any column under
about 30 positives) reported with their exact test counts and a note that
their test metrics carry wide confidence intervals.

No validation split exists; the record states the trainer must use a fixed
schedule and never select on the test set.
