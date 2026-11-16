---
title: "Ticket 039: add the gate4 column mode to the multilabel trainer"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/039-exp3-1-trainer-mode.md
---
Type: build, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

Can the Experiment 1 trainer train four gate columns from the new label table without changing
any behaviour the Experiment 1 or 2 records depend on?

## Spec

- Add `--columns gate4`: output columns, in this order, `fm_gated`, `fiber_gated`, `ep_gated`,
  `hema_gated`. Truth is the column value in `run/split_exp3_1_20261116/labels.csv`.
- The table is passed the same way the existing one is; do not hardcode the v8 table. Add a
  `--table` argument if the trainer does not already take one, defaulting to the current path so
  existing commands are unchanged.
- `--gated-target` is irrelevant for gate4 and must be ignored, not silently applied.
- Inverse-frequency weight on the training split only: `(N - n) / n`, N = 4,964. Expected weights
  14.8, 24.5, 60.3, 61.8. Record the vector in the run record.
- Thresholds: validation only, grid 0.05 to 0.95, highest F1, ties to the higher cut, extended to
  0.99 if the maximum lands at 0.95.
- Do not modify `predict_picture.py`, `pass_fail_block.py` or `run_arm.py` beyond what is strictly
  required to accept a four-column checkpoint.
- Regression proof: `--labels-only` for `--columns ooi` and `--columns combined` on the v8 table
  must reproduce the recorded per-split counts and positive counts, and the trainer's diff must
  touch only the new mode. Record both outputs in the card.
- `--labels-only --columns gate4` on the new table must print 4,964 / 1,058 / 1,533 and training
  positives 315 / 195 / 81 / 79.
- A synthetic smoke run on 40 rows, 1 epoch, all four columns, must complete and write predictions.

## Done when

Both regression runs match the recorded counts, the gate4 labels-only counts match, the smoke run
completes, and the diff is limited to the new mode. Report the diffstat and the four outputs.

## What changed

One file: `experiments/multilabel_ooi/train_multilabel.py`, **363 insertions, 40 deletions**
(`git diff --numstat`). No other tracked file is touched: `predict_picture.py`,
`pass_fail_block.py`, `run_arm.py`, split v8 and every Experiment 1 and 2 artifact are unchanged.

The new mode is additive. `--columns gate4` is a third choice, `read_gate4_table` is a separate
reader that opens no v8 file, `evaluate_test_gate4` is a separate test read, and the shared
functions it hooks (`output_columns`, `build_rows`, `labels_report`, `choose_thresholds`,
`run_training`) branch on the mode with the ooi and combined paths left as they were. Proof 1 is a
byte-for-byte comparison against the committed trainer, not a reading of the code.

Decisions worth naming:

- `--table` defaults per mode: the v8 table for `ooi`/`combined`, the Experiment 3.1 table for
  `gate4`. An existing command is unchanged because it never reaches the new default.
- The gate4 table carries its own `split` column and its own `image_path`, so the mode reads no v8
  path table and no v8 split file. It cross-checks the table against the sibling `split.csv` when
  that file is present: 7,555 pictures, zero disagreements.
- `--pos-weight` defaults to `on` for gate4 only; `ooi` and `combined` still default to `off`.
- The 0.99 extension is a parameter, not a wider shared grid: `choose_thresholds(extend_ceiling=
  False)` keeps the 19-point 0.05 to 0.95 grid for ooi and combined, and the four extra points are
  evaluated only when gate4's maximum F1 lands on 0.95. `grid_extended` is recorded per class.
- The run record carries the weight vector, the table md5, the frozen counts and the ceiling rule,
  so the arm is readable without the table.
- `--expect-counts off` exists only so a synthetic table can be exercised. It prints "frozen counts
  NOT asserted" and records `counts_asserted: false`. Real runs assert 4,964 / 1,058 / 1,533 and the
  twelve per-split gate positives.

## Proofs, run locally on 16 November

Environment: laptop venv, no torch by design (`Python 3.12.14`). `--labels-only` needs numpy and csv
only, so proofs 1 and 2 run here.

### 1. Regression: ooi and combined on the v8 table

Both modes were run against the committed trainer (`git show HEAD:...`) and the two outputs diffed.
Zero differing lines in either mode.

```
$ train_multilabel.py --labels-only --columns ooi
table: run/ooi_matrix_20261104/ooi_labels.csv md5 7fd1106e355464deac72da73aa6b2c4b
split: run/split_20261103_v8/split_70_15_15.csv md5 1a71d66d2de384cf47a3fcf7d9115baa
rows: 7470: 5239 train / 1110 val / 1121 test
  column                      total  train   val  test
class columns (object truth, --columns ooi):
  class_bubble                 2171   1520   326   325
  class_bubble_cluster         1132    792   170   170
  class_foreign_matter          798    576   110   112
  class_fiber                   392    274    60    58
  class_wet_package             314    220    47    47
  class_hema                    154    102    25    27
  class_extraneous_polymer      142    106    19    17
  class_surface_groove            0      0     0     0   (never a model output)
gate columns (gate-arm targets, --gated-target gate):
  gate_foreign_matter           454    320    62    72
  gate_fiber                    362    251    55    56
  gate_extraneous_polymer       135    102    16    17
  gate_hema                     151     99    25    27
all frozen counts match ticket 027: class 2171/1132/798/392/314/154/142/0,
  gate 454/362/135/151, split 5239/1110/1121
flags: --columns ooi --gated-target class --pos-weight off
model outputs (7): class_bubble, class_bubble_cluster, class_foreign_matter, class_fiber,
  class_wet_package, class_hema, class_extraneous_polymer

$ train_multilabel.py --labels-only --columns combined
  (same table, split and frozen-count lines)
all frozen counts match ticket 027: class 2171/1132/798/392/314/154/142/0,
  gate 454/362/135/151, split 5239/1110/1121
flags: --columns combined --gated-target class --pos-weight off
model outputs (19): P1_MPP, P1_ML, P2_LOC, P2_DC, P1_NL, P1_FL, P2_LD, P1_COC, P2_DS, P2_FOV,
  P2_BSC, P1_PPM, class_bubble, class_bubble_cluster, class_foreign_matter, class_fiber,
  class_wet_package, class_hema, class_extraneous_polymer
```

### 2. gate4 on the Experiment 3.1 table

```
$ train_multilabel.py --labels-only --columns gate4
table: run/split_exp3_1_20261116/labels.csv md5 222c873f17a9f101d32b0b36e210e5e3
rows: 7555: 4964 train / 1058 val / 1533 test
split cross-check: split.csv agrees on all 7555 pictures
  column          total  train   val  test
  fm_gated          454    315    60    79   (Foreign Matter)
  fiber_gated       362    195    43   124   (Fiber)
  ep_gated          135     81    14    40   (Extraneous Polymer)
  hema_gated        151     79    20    52   (HEMA)
training positives: 315 / 195 / 81 / 79
inverse-frequency pos_weight on train only, N = 4964: 14.8 / 24.5 / 60.3 / 61.8
frozen counts match ticket 037: split 4964/1058/1533, train positives 315/195/81/79
flags: --columns gate4 --gated-target class (ignored) --pos-weight on
model outputs (4): fm_gated, fiber_gated, ep_gated, hema_gated
```

Every number the spec asks for is present and matches the ticket-037 tables, and the weights land on
the expected 14.8 / 24.5 / 60.3 / 61.8.

### 3. Four-column smoke run

Moved by the 16 November instruction: the laptop venv carries no torch by design, and the 40-row
1-epoch run happens on the VM in the training card (tickets 041 and 042). Run here instead, to prove
the four-column path without torch:

- a 40-row synthetic table (24 train / 8 val / 8 test) through `--labels-only --columns gate4
  --expect-counts off`: four outputs in the required order, the weight vector, and a line stating
  the frozen counts were not asserted;
- `build_rows` on that table: four outputs in order, `truth == target == gate`, and
  `--gated-target gate` produces identical targets, so the ignored switch cannot leak;
- `choose_thresholds`: 19 points and no `grid_extended` key on the default grid; 23 points with
  `grid_extended: true` when the maximum F1 lands on 0.95; 19 points with `grid_extended: false`
  when it does not;
- `evaluate_test_gate4` on the synthetic test split: the six top-level keys and 15 per-class keys
  the run record writes.

## Not done here

The 40-row 1-epoch training run on the VM, and therefore a real gate4 `predictions.npz`. That is
ticket 041's smoke step and the first place a gate4 checkpoint exists.

