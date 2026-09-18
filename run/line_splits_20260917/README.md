# Per-line split assignments, 2026-09-17

One folder per production line. `split.csv` is the assignment: one row per picture with its
content hash, its source file on the VM, its class, its line and whether it sits in the train
or the test half. `split_report.json` holds the per-class counts, the class list and the rule.

The rule is exact-count stratified: inside each class inside each line the pictures are shuffled
with seed 42 and exactly round-half-up(pictures x 0.30) become the test half. It reproduces the
published table in `run/line_eda/20260917/all_lines_class_split_70_30_and_80_20.csv` cell for cell.

Classes with no test picture on a line are dropped from that line entirely, both halves: 7
cells at 70:30. The run therefore covers 8402 pictures, 5875 train and 2527 test.
- dropped: L24 Bubble Scatter (1 picture)
- dropped: L24 Bubble On 123 (1 picture)
- dropped: L25 HEMA Fragment (1 picture)
- dropped: L25 Bubble Irregular (1 picture)
- dropped: L26 Bubble On Edge (1 picture)
- dropped: L26 Bubble Scatter (1 picture)
- dropped: L27 Bubble On Edge (1 picture)
