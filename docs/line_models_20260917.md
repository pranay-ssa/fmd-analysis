# Per-line ResNet50 models: five lines, 70:30, batch 4, 50 epochs (2026-09-17)

Step 4 of the lead's sequence. One ResNet50 per production line, each trained on its own line's train
half and scored on held-out pictures from the same line. This is the run the line analysis of
2026-09-16 was built for.

Workbook: `reports/cnn/FMD_Line_ResNet50_Results_20260917.xlsx`
Notebook for the lead: `notebooks/FMD_Line_Models_20260917.ipynb`
Verifier: `experiments/cnn/verify_line_results.py` (910 checks, 0 failed)

## What was run

| Item | Value |
|---|---|
| Model | ResNet50, ImageNet weights, base fully trainable, GAP + batch norm + dense 1024 + dropout 0.3 + softmax |
| Optimizer / loss | SGD lr 1e-4, momentum 0.9, Nesterov / sparse categorical crossentropy |
| Epochs, batch, seed | 50, 4, 42 |
| Input | the raw 2448x2048 frame resized to 224x224, no crop |
| Data | 8,402 pictures: 5,875 train, 2,527 test, 87 class-line cells |
| Split | exact-count stratified inside each class inside each line, seed 42, test = round-half-up(n x 0.30) |
| Hardware | one A100 80GB, 24 cores. 06:14:44Z to 07:09:08Z, 54.4 minutes for all five, every run exit 0 |

The model, optimizer, loss, metric set and seed are the same code as the 2026-09-15 six-architecture run;
the architecture function was diffed against `model_training.py` and differs only in its docstring. Three
differences are deliberate and they mean the two runs' numbers must not be compared: batch 4 instead of 8
(the lead's instruction for this step), the raw frame instead of the per-class fixed-size crop, and one
model per line instead of one pooled model.

## The split, as an assignment

`src/build_line_split_assignments.py` turned the published count table into a per-picture assignment:
8,402 rows across five `split.csv` files, each carrying the content hash, the image path, the class and the
train or test side. Classes with no test picture on a line are dropped from that line entirely, which
removed 7 single-picture cells (L24 Bubble Scatter and Bubble On 123; L25 HEMA Fragment and Bubble
Irregular; L26 Bubble On Edge and Bubble Scatter; L27 Bubble On Edge).

The pool was not redistributed to produce these numbers: the assignment reproduces the published table of
`docs/line_split_revision_20260917.md` cell for cell, and the line splits were verified against it before
anything was trained.

Images were never copied. The library stays on the library account's volume and every run reads it by
absolute path.

## Results

| Line | Train | Test | Classes | Accuracy | Macro F1 | Weighted F1 | Training minutes |
|---|---|---|---|---|---|---|---|
| L24 | 1,993 | 858 | 19 | 87.30% | 56.64% | 86.76% | 18.5 |
| L25 | 663 | 287 | 17 | 91.29% | 59.08% | 90.51% | 5.9 |
| L26 | 853 | 365 | 17 | 84.38% | 60.10% | 84.30% | 7.6 |
| L27 | 955 | 409 | 15 | 84.60% | 62.87% | 84.59% | 8.3 |
| L31 | 1,411 | 608 | 19 | 90.95% | 48.34% | 90.28% | 12.2 |
| **All five** | **5,875** | **2,527** | **87 cells** | **87.77%** | 57.41% (mean of the five) | **87.33%** | **52.5** |

Accuracy and weighted F1 are pooled over the 2,527 test pictures. Macro F1 is the plain mean of the five
per-line macro figures, because the five models carry different class lists and there is no single macro
quantity across them.

## What the numbers say

**1. The score tracks how many test pictures a cell holds, not which line it came from.** Across all 87
class-line cells:

| Test pictures in the cell | Cells | Mean F1 | Median F1 | Lowest | Highest | Cells at zero F1 |
|---|---|---|---|---|---|---|
| 1 to 4 | 35 | 32.54% | 0.00% | 0.00% | 100.00% | 20 |
| 5 to 24 | 28 | 65.02% | 80.12% | 0.00% | 100.00% | 2 |
| 25 or more | 24 | 83.52% | 87.30% | 41.18% | 100.00% | 0 |

A cell with four or fewer test pictures has a median F1 of zero and includes two cells at 100 percent. No
cell with 25 or more pictures scores zero. This is the 35 thin cells the 2026-09-16 analysis predicted, now
visible in results, and it is why no difference between the five lines should be read as a finding about the
lines.

**2. The same class produces unrelated scores on different lines, and the swing follows the cell size.**
Lens Off Center: 87 percent on 59 test pictures (L24), 100 percent on 2 (L26), 14 percent on 8 (L27), 0
percent on 2 (L25). View Obstructed: 0, 91, 33, 100, 95 percent on cells of 6, 5, 10, 3 and 11. Multiple
Lenses stays at 89 to 100 percent on cells of 16 to 202. Missing Primary Package is 80 to 100 percent.

**3. Most errors sit inside one family.** 309 of the 2,527 test pictures are misclassified, 12.2 percent.
The largest directions: Foreign Matter to Fiber 66, Fiber to Foreign Matter 21, Extraneous Polymer to Fiber
20, Extraneous Polymer to Foreign Matter 17, Lens Off Center to Low Dose Obstructing Region of Interest 14,
Foreign Matter to Extraneous Polymer 10, Fiber to Extraneous Polymer 8, View Obstructed to Bubble 8. The
three debris classes account for 142 of the 309 errors, 46 percent, and the dataset does not separate them
cleanly: 33 pictures carry both Extraneous Polymer and Fiber as labels and the pooling rule gives each one
label. The client's naming document states that Lens Off Center is commonly confused with Low Dose, and 14
errors land in exactly that direction.

**4. The classes that hold up are structural; the classes that fail are small objects.** Missing Primary
Package, Cavity Off Center, Package Misalignment and Multiple Lenses score 80 to 100 percent almost
everywhere. Fiber (24 to 67 percent), Extraneous Polymer (0 to 67), Bubble Cluster, Bubble Irregular and the
single-picture classes fail. This is what a 2448-wide frame squeezed to 224x224 does to a defect a few tens
of pixels across, and it is the measurable cost of dropping the crop step.

## How the numbers were checked

`experiments/cnn/verify_line_results.py` takes the confusion matrices as the raw evidence and rebuilds
everything from the counts: per-class precision, recall and F1, the macro and weighted aggregates, accuracy
from the diagonal, then compares each result against `metrics.json`, against every cell of the workbook
(summary, each per-class table, the confusion table on each line sheet, the band table, the cell count) and
against `run/line_results_20260917/summary.json`. 910 checks, 0 failed.

The split was verified separately before training: every one of the 8,402 image paths was confirmed to exist
and be readable by the account that ran the training, and the per-class counts in the materialised
assignment were diffed against the published table.

## Artifacts

| Item | Where |
|---|---|
| Trainer | `experiments/cnn/train_line_model.py` |
| Run script | `experiments/cnn/run_line_models.sh` |
| Split builder | `src/build_line_split_assignments.py` |
| Split assignments | `run/line_splits_20260917/line_<line>/split.csv` and `split_report.json` |
| Deliverable builder | `src/make_line_results.py` |
| Workbook | `reports/cnn/FMD_Line_ResNet50_Results_20260917.xlsx` - Summary, one sheet per line, Cells by support, and Line summary (CNN format) |
| Inference re-measure | `experiments/cnn/measure_line_inference.py`, results in `runs/cnn/lines/inference_warm.json` |
| Notebook | `notebooks/FMD_Line_Models_20260917.ipynb` |
| Verifier | `experiments/cnn/verify_line_results.py` |
| Local mirror of the runs | `runs/cnn/lines/<line>/epochs_50/` (metrics, history, confusion matrix PNG and CSV, log) |
| Trained weights | on the VM only: `~/line_experiment_20260917/runs/<line>/epochs_50/weights.weights.h5` (about 200 MB per line) |

## Open items

1. **Batch 4 costs about four times the wall clock of batch 8.** The earlier 22-class run trained 1,172
   pictures for 50 epochs in 345 s; this run needed 52.5 minutes for 5,875. If a future run does not need
   batch 4 specifically, batch 8 is roughly an order of magnitude cheaper per picture.
2. **These five numbers are not comparable with the six-architecture run**, because the input differs by the
   crop step. A single control run on one line, crops against raw frames and nothing else changed, would say
   how much the crop step is worth.
3. **Inference per image is quoted as the run recorded it, without a warmup pass**, per the instruction for
   this step: 3.842 to 9.843 ms per image across the five lines, against 1.28 ms for the crop-based ResNet50
   on a warm protocol. That figure carries the one-time XLA graph trace and cuDNN autotune cost, so it reads
   high and is not like-for-like with the six-architecture table's warm column. The weights are saved, and
   `experiments/cnn/measure_line_inference.py` will produce a warm figure (1.694 to 2.018 ms per image) if
   that comparison is ever wanted.
4. **The pooled single-model baseline has not been run.** The point of the line analysis was to compare five
   line models against one pooled model; this run supplies only the first half of that comparison.
5. **Nothing here is a claim about the lines.** Every per-line difference in the tables above sits on a thin
   cell. The comparable quantities, per-class recall on classes with a thick test cell on three or more
   lines, are what any line-versus-pooled statement should rest on.
