# Next experiments, the six highlighted classes, and the line comparison panels (2026-09-17)

Record for the three things the lead asked for on 2026-09-17, as she wrote them:

1. "Run the MultiLevel MultiScale on this also. the 1st architecture"
2. "I have highlighted some classes from each of the line. Once train on them as well. Only for
   ResNet50 for now"
3. "Ok. Then on the highlighted classes only ResNet50. And on the complete set ResNet50 and
   MultiScaleMultiLevel (Arch 1)"
4. "And i will need some sample images of classes from each Line. Lets say Fiber image from each
   line. for 2 or 3 classes. Just to show the client that visually they look same in each line."

ResNet50 on the complete per-line split already ran on 2026-09-17, so the two new training jobs are:

| # | Experiment | Classes | Architecture | Split |
|---|---|---|---|---|
| A | Highlighted classes | the six she marked | ResNet50 | `run/class_subset_6_20260917/` |
| B | Complete set | all classes of each line | ResNet50-Inception MultiLevel MultiScale (her Arch 1) | `run/line_splits_20260917/` |

The six highlighted classes: Missing Primary Package, Multiple Lenses, Foreign Matter,
Lens Off Center, Missing Lens, HEMA Obstruction. All six are present on all five lines, so every
line trains and scores all six.

## A. The six-class split

Built by `src/build_class_subset_splits.py` from the existing full per-line assignment. A picture
keeps the train or test side it already had, so this run and the full run score the same pictures
on the same side and the two tables are comparable.

| Line | Pictures | Train | Test |
|---|---|---|---|
| L24 | 2,298 | 1,608 | 690 |
| L25 | 578 | 404 | 174 |
| L26 | 856 | 599 | 257 |
| L27 | 725 | 507 | 218 |
| L31 | 438 | 306 | 132 |
| **All five** | **4,895** | **3,424** | **1,471** |

For comparison, the full split holds 8,402 pictures (5,875 train, 2,527 test). The subset is 58
per cent of the training volume, so experiment A should take about 30 minutes against the 54
minutes the full ResNet50 run took.

## B. Both architectures, prepared and validated without the GPU

`experiments/cnn/train_line_model.py` now takes `--arch`. The builders are imported from
`experiments/cnn/model_training.py` instead of being copied, so there is one definition of each
architecture and no chance of the two drifting apart. `ARCH_LABELS` gives each one its
reader-facing name, and every run records both the key and the label in `metrics.json`, so a
results file says which architecture it is in the words the tables use.

Validated on the CPU (the GPU stays free for the teammate):

| Check | Result |
|---|---|
| Both architectures build | ResNet50 25,700,230 parameters; ResNet50-Inception MultiLevel MultiScale 58,530,694 |
| End to end on a 34-picture split, one epoch, CPU | passed: split read, frames decoded, model built, trained, evaluated; metrics, history, confusion matrix and weights all written; 34 s |

Runner scripts, all syntax-checked on the box:

| Script | Does |
|---|---|
| `experiments/cnn/run_subset6_resnet50.sh` | experiment A, five lines, ResNet50 on the six-class split |
| `experiments/cnn/run_multiscale_full.sh` | experiment B, five lines, multi-scale on the complete split |
| `experiments/cnn/run_next_experiments.sh` | runs A then B in order, for one launch |
| `vm/ops/check_gpu_free.sh` | says whether the A100 is free; exit 0 only when nothing holds it |

Neither experiment starts on its own. The GPU is shared with srikantht and swetap, so the launch
waits for a person to say the box is free.

Estimated GPU time, from the measured ResNet50 run and the recorded architecture costs: A about 30
minutes, B about 75 minutes (the multi-scale architecture cost 495 s against ResNet50's 345 s on
the earlier combined run, about 1.4 times per picture). About 1 hour 45 minutes in total.

**Measured, once they ran:** A took 32 minutes and B took 63 minutes, so 95 minutes for both against
the 105 estimated. The 1.4x ratio from the screening run did not hold on this data: the multi-scale
model ran at 45 ms per step against ResNet50's 44.5 ms on the identical 1,993-picture L24 train set,
so it costs about a tenth more per epoch, not four tenths. The live measurement is the one to quote.

## C. Disk: found full, fixed, and made harmless

The box root filesystem was at 100 per cent (605 MB free) before these runs. The teammate's own
74 GB under `/home/srikantht` accounts for most of it and is not ours to touch, and neither
`/data` (367 GB free) nor `/mnt` (60 GB free) accepts our login. Two fixes:

- Cleared our own pip wheel cache, 3.5 GB, taking free space to 4.1 GB.
- A failed weight write is now a warning, not a failure. Metrics, history and the confusion
  matrix are written before the weights, so a full disk can no longer cost a training run.

Runs need about 0.2 GB of weights per ResNet50 line and 0.5 GB per multi-scale line, so about 3.3
GB for both experiments. That fits, but only just, so the master runner prints the free space
before it starts.

**Resolved the same day.** The owner confirmed his 57 GB duplicate copy could go, and it was removed
after all 12,081 of its files were matched by name and size against the /data copy that our training
reads, with 51 checksums matching as well. Free space went from 3.1 GB to 60 GB, taking the root
filesystem from 98 per cent used to about 50 per cent. The full record, including the comparison
behind the deletion and the safeguard used, is in `reports/ops/disk_breakdown_20260917.md`.

## D. Line comparison panels

Built by `src/make_line_comparison_panels.py`, one figure per class, five columns, one column per
line, two pictures per line.

**How the pictures are chosen.** For a class on a line, take that class's pictures from the line's
test half, sort by content hash and take evenly spaced samples. Nothing is chosen for how it looks,
so the panel cannot be read as a selection of flattering examples. The chosen pictures and their
statistics are in `samples.csv`, so anyone can re-derive the selection or ask for a different
stride.

Drawn for seven classes, so the two or three the lead wants are a subset of what exists: Fiber
(her example), Foreign Matter, Missing Primary Package, Multiple Lenses, Lens Off Center, Missing
Lens, HEMA Obstruction.

**Second figure per class: is that class the same on every line, measured.** The panel shows two
pictures per line; a box plot of frame brightness over every test picture of the class says
whether those two are representative. 1,579 pictures measured in total.

What the measurement says, for the 1,579 pictures across seven classes:

- **Frame geometry is identical everywhere.** Every picture is 2448x2048 and every one has the
  same byte size, 5,014,582 bytes. One distinct frame size and one distinct file size across all
  thirty-five class-line combinations. The capture format does not vary by line.
- **Brightness does vary a little by line.** L26 is the darkest for Fiber, Foreign Matter, Multiple
  Lenses and HEMA Obstruction (Foreign Matter 11.1 against L24's 16.6 on a 0 to 255 scale), and
  L24 and L31 are the brightest. Spread inside a line is 1 to 3 intensity units, so the gap
  between lines is real, though the distributions overlap.
- **Some lines carry too few pictures to compare.** Missing Primary Package has 2 test pictures on
  L26 and 4 on L27; Missing Lens has 1 on L26. Their numbers are shown with the count beside them
  and should not be read as a line difference.

So the honest sentence for the client is: the frames are the same size and format on every line
and the same class looks the same, with a small exposure difference that shows up as L26 being
slightly darker.

## E. Results side, also prepared

The table builder serves all three experiments now, so the two new runs land in the same format
the lead already approved.

| Script | Does |
|---|---|
| `src/make_line_results.py` | reads a run folder and writes the workbook and the notebook |

It takes the run folder, the output paths, a label for the run, and an optional second run to
compare against, all from the environment, so nothing has to be edited between experiments:

| Setting | Meaning |
|---|---|
| `LINE_RESULTS_RUNS` | the run folder to read, default the ResNet50 run |
| `LINE_RESULTS_LABEL` | the name printed for that run, for example `ResNet50` |
| `LINE_RESULTS_COMPARE_RUNS` | a second run to compare against, optional |
| `LINE_RESULTS_COMPARE_LABEL` | the name printed for the second run |
| `LINE_RESULTS_XLSX`, `LINE_RESULTS_NB`, `LINE_RESULTS_JSON` | where the three outputs go |

With a second run given, the workbook gains a sheet with one row per line: accuracy, macro recall
and macro F1 for both runs, the change between them, and a pooled row for each. Because both runs
score the same pictures on the same side, a difference on that sheet is the architecture and
nothing else.

Checked: rebuilding the existing ResNet50 workbook with this builder reproduces it and passes the
same 1,088 checks, and the comparison sheet was exercised by comparing a run against itself,
where every change must be exactly zero. It is.

## F. State: both experiments have now run

Both ran on 2026-09-17, A from 09:54Z for 32 minutes and B from 10:46Z for 63 minutes, all five
lines exit 0 on each, GPU released afterwards. Metrics, history and confusion matrices were pulled
off the box; the weights stayed there, per instruction.

**A, the six highlighted classes on ResNet50.** Pooled accuracy over the 1,471 test pictures of the
six classes: **96.26 per cent**, against 90.34 per cent when the full ResNet50 model is restricted
to the same six classes and scored on the same pictures. The six-class models are better on four of
the five lines, most of all where data is thinnest (L31 +17.4 points on 132 test pictures, L27 +12.8
on 218), and level on L26. Restricting the classes also raises macro recall by 6.8 points.
`reports/cnn/FMD_Line_SixClasses_ResNet50_20260917.xlsx`,
`reports/cnn/FMD_SixClasses_vs_FullModel_20260917.xlsx`,
`run/line_results_subset6_20260917/subset_vs_full.json`.

**B, the complete set on ResNet50-Inception MultiLevel MultiScale.** Pooled accuracy over the 2,527
test pictures: **89.47 per cent** against **87.77 per cent** for ResNet50 on the identical pictures,
so **+1.70 points**, while mean macro recall falls **2.67 points** (59.26 to 56.60). The gain is not
uniform: it comes from a few classes with many pictures (Foreign Matter +24 correct answers, +0.95
points; View Obstructed +13, +0.51; Extraneous Polymer +12, +0.47), and it is paid for on more
classes than it helps overall (26 class-line cells recalled less, 20 more, 41 unchanged). The
per-class decomposition in `run/line_results_multiscale_20260917/arch_vs_base.json` adds up to the
pooled change exactly, which the comparison script asserts.

Read together, the two results say the same thing from different directions: what helps most on
this data is narrowing what the model has to decide (A), and the architecture change that widens
capacity helps the common classes while costing the rare ones (B).

Artifacts: `reports/cnn/FMD_Line_MultiScale_ResNet50_20260917.xlsx` (the five-line workbook, 31
verification checks against the run's own metrics),
`reports/cnn/FMD_Architecture_Comparison_20260917.xlsx` (the comparison, per line and per class),
`notebooks/FMD_Line_MultiScale_20260917.ipynb` and
`notebooks/FMD_Architecture_Comparison_20260917.ipynb` for the lead,
`experiments/cnn/compare_architectures.py` and `experiments/cnn/verify_multiscale_workbook.py` so
both can be re-run.

Open questions now:

1. Which two or three classes should go to the client? Seven are drawn; Fiber is the lead's example.
2. Should the multi-scale architecture go forward? It wins on pooled accuracy and loses on macro
   recall, so the decision is which of the two the client's problem rewards. A seed-spread
   measurement would say whether the 1.7-point gain is above run-to-run variation; it has not been
   measured on this data.
3. The full-run weights and the multi-scale weights are still on the box (about 3.3 GB total). Free
   space is 60 GB, so there is no longer any pressure to remove them.
4. The batch-4 against batch-8 cost question, and one pooled model on the same split.
