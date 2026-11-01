"""Build the reader-facing notebook for the multi-label LP experiment.

Written for a reader who will not run it: design first, code second, and the label cells carry
the real output so the numbers are visible without executing anything. No internal paths,
folder names, version tags or ticket references.

Regenerate after any change so the notebook cannot drift by hand-editing.
"""
import contextlib
import io
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROOT = HERE.parents[1]
OUT = ROOT / "notebooks/FMD_MultiLabel_LP_AllTags.ipynb"

nb = nbf.v4.new_notebook()
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(text, output=None):
    cell = nbf.v4.new_code_cell(text.strip("\n"))
    if output is not None:
        cell["outputs"] = [nbf.v4.new_output("stream", name="stdout", text=output)]
        cell["execution_count"] = 1
    cells.append(cell)


def real_outputs():
    """Run the label builder on the current data and capture what the two cells print."""
    import train_lp

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rows = train_lp.build_rows("a")
    n_train = sum(1 for r in rows if r["split"] == "train")
    build_text = f"variant a: {len(rows)} pictures, {n_train} train / {len(rows) - n_train} test\n"

    lines = [f"{'code':8s} {'condition':26s} {'pictures':>9s}"]
    for code_, name in train_lp.LP_TAGS:
        lines.append(f"{code_:8s} {name:26s} {sum(r['flags'][code_] for r in rows):9d}")
    lines.append(f"{'clear':8s} {'nothing marked':26s} {sum(r['is_clear'] for r in rows):9d}")
    return build_text, "\n".join(lines) + "\n"


build_out, check_out = real_outputs()

md("""
# Multi-label lens inspection: predicting every lens-presentation condition

This notebook is a design walkthrough of one experiment: can a single image classifier report
every lens-presentation (LP) condition visible in a lens picture, when one picture can carry
several conditions at once?

It is written to be read, not run. The code is the code we train with; the numbers printed
under the label cells are the real counts on the current annotation.

**Scope.** This experiment answers one question: are the conditions learnable from a whole
picture, and does the model keep seeing them when an object is also present. Pass or fail
decisions and object detection are separate pieces of work, described at the end.
""")

md("""
## 1. The question

A lens picture can show several conditions at once: Multiple Lens together with a Folded Lens,
or Dirty Camera together with an off-centre lens. A single-choice classifier must pick one and
discard the rest, so the model answers twelve independent yes/no questions instead.

A picture with nothing wrong answers **no to all twelve**. That is the Clear case, and it is
what allows the model to say "nothing here" later.

Two variants are measured with the same code and the same pictures:

| Variant | Predicts | Purpose |
|---|---|---|
| **A, conditions only** | the twelve conditions | clean measurement of how well each condition is seen |
| **B, conditions plus object** | the twelve conditions and one coarse "an object is present" flag | checks whether a single object flag fires, which the routing step needs |

The object flag in B covers all seven object classes as one answer. It is a routing signal,
not a detection result, and its score is never averaged with the condition scores.
""")

md("""
## 2. Architecture at a glance

```
  picture, resized to 224 x 224
              |
      ResNet50 trunk, pretrained on ImageNet
              |
      one score per condition, independent of the others
              |
      threshold each score, 0.5 by default
              |
      12 answers per picture (plus 1 object flag in variant B)
              |
      later stage: rules layer  <---  object detector
```

Three properties of this design are deliberate:

- **Independent scores, not a single choice.** The final layer has no softmax, so two
  conditions can both be true. Softmax would force them to compete.
- **The whole picture at 224 px.** Conditions such as lens presentation or dirt on the camera
  are properties of the frame, so a downscaled whole frame carries the evidence. Small objects
  do not survive that downscale, which is exactly why objects are left to the detector.
- **Clear is the all-zero row.** The model sees pictures where every answer is no, so "nothing
  here" is something it has learned rather than something inferred.
""")

md("""
## 3. The pictures

Counts come from the annotation of record: one annotation per picture, newest file wins, and
copies of the same picture counted once. A picture is used only if it carries a label or if it
is Clear. Entries left empty in an unfinished annotation task are neither, so they are not used
and can never be trained as negatives.

| Group | Pictures |
|---|---|
| Pictures with an annotation | 6,938 |
| Carrying at least one LP condition | 4,063 |
| Clear, nothing marked | 2,156 |
| Carrying an object | 1,103 |

Clear pictures are 31 percent of the set. Without them the model would only ever see pictures
that have a condition and could never learn what a pass looks like.
""")

md("""
## 4. The twelve conditions

| Code | Condition | Pictures |
|---|---|---|
| P1_MPP | Missing Primary Package | 1,426 |
| P1_ML | Multiple Lens | 1,439 |
| P2_LOC | Lens Off Center | 957 |
| P2_DC | Dirty Camera | 329 |
| P1_NL | No Lens | 325 |
| P1_FL | Folded Lens | 237 |
| P2_LD | Low Dose | 215 |
| P1_COC | Cavity Off Center | 184 |
| P2_DS | Dirty Strobe | 43 |
| P2_FOV | View Obstructed | 24 |
| P2_BSC | Bubble Scatter | 6 |
| P1_PPM | Package Misalignment | 2 |

Three further conditions in the annotation guide have no examples at all and are therefore not
predicted: Edge Bottle-Capped, Torn Lens, Lens Rupture. They remain in the guide and are listed
at zero until pictures exist.

The last four rows are too rare to judge. They are reported but excluded from the headline
average.
""")

md("""
## 5. Why multi-label, in numbers

| Conditions on one picture | Pictures |
|---|---|
| one | 3,186 |
| two | 646 |
| three | 216 |
| four | 14 |
| five | 1 |

So 877 pictures, one in five of the annotated set, carry more than one condition. A
single-choice classifier would throw that away.
""")

md("""
## 6. Design decisions and why

| Decision | Why | Alternative rejected |
|---|---|---|
| Twelve independent binary outputs | 877 pictures carry more than one condition | one softmax over twelve classes |
| Whole picture at 224 x 224 | conditions are properties of the frame | full-resolution input, which costs memory for no gain on conditions |
| Clear as an all-zero row | the model must see a pass picture | training on condition pictures only, which cannot produce a pass |
| One object flag, not seven object classes | routing only needs to know something is present; typing is the detector's job | seven object heads at 224 px, where a small particle is a pixel or two |
| Average precision per condition | severe imbalance, 2 pictures against 1,439 | accuracy, which a model that always says no would win |
| Fixed 50 epochs, no augmentation | comparability with the earlier five-condition runs | early stopping and augmentation, which change two things at once |
| No class weighting on the first run | same comparability; weights are a second run if rare classes collapse | class weights from the start |
| Split by picture content | near-duplicate pictures must not straddle train and test | a random row split, which leaks duplicates |
""")

md("""
## 7. How the model is measured

**Average precision (AUPRC) per condition is the metric of record.** Accuracy would mislead: a
model that always answers "no" scores 99 percent on Package Misalignment, which has two
pictures. Average precision measures whether positive pictures rank above negative ones.

Also reported:

- precision, recall and F1 at a fixed 0.5 cut-off, plus the best achievable F1 per condition;
- exact match, the share of pictures where all twelve answers are right;
- Hamming loss, the share of wrong answers across all picture-question pairs;
- the same average precision on three subsets: conditions only, conditions plus an object, and
  Clear. A drop on the mixed subset means the model learned a shortcut;
- for variant B, the object flag as fire rates: on object pictures, on Clear pictures (the
  false-fire number), and on mixed pictures.
""")

md("""
## 8. Setup

The three input tables and the image folder are configured here. The three tables are the
annotation of record, the Clear list, and the frozen train/test assignment.

Running the training cells needs PyTorch, torchvision, Pillow and numpy, and a GPU for a
practical run. The label cells need nothing beyond the standard library.
""")

code("""
import csv
from pathlib import Path

import numpy as np

# ---- settings -------------------------------------------------------------------------
VARIANT = "a"                 # "a" = conditions only, "b" = conditions + one object flag
ANNOTATION_CSV = Path("annotation_of_record.csv")   # columns: picture id, path, code
CLEAR_CSV = Path("clear_pictures.csv")              # columns: picture id, path, clear
SPLIT_CSV = Path("train_test_assignment.csv")       # columns: picture id, split
IMAGE_ROOT = Path("")                               # folder holding the image files

# ---- the twelve conditions, in a fixed order ------------------------------------------
# This order is the column order of every target vector and every metric. Never reorder it.
LP_TAGS = [
    ("P1_MPP", "Missing Primary Package"),
    ("P1_ML", "Multiple Lens"),
    ("P2_LOC", "Lens Off Center"),
    ("P2_DC", "Dirty Camera"),
    ("P1_NL", "No Lens"),
    ("P1_FL", "Folded Lens"),
    ("P2_LD", "Low Dose"),
    ("P1_COC", "Cavity Off Center"),
    ("P2_DS", "Dirty Strobe"),
    ("P2_FOV", "View Obstructed"),
    ("P2_BSC", "Bubble Scatter"),
    ("P1_PPM", "Package Misalignment"),
]
LP_COLUMNS = [code for code, _ in LP_TAGS]

# One condition is written two ways in different annotation files.
LP_ALIASES = {"P2_FOV": {"P2_FOV", "F2_FOV"}}

# Every object class collapses into one flag. Typing the object is a detection job.
OBJECT_CODES = {
    "P2_BB", "Bubble", "P2_BI", "Bubble Irregular", "P2_BST", "Stretched Bubble",
    "P2_BC", "Bubble Cluster", "P2_WP", "Wet Package",
    "P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
    "P3_HE", "HEMA Fragment",
}
""")

md("""
## 9. Build the label table

Each row is one picture. The target is twelve 0/1 answers, plus the object flag in variant B.
Clear pictures are added from their own list because they carry no annotation entry at all.
""")

code("""
def build_rows(variant, annotation_csv, clear_csv, split_csv):
    \"\"\"Return one dict per picture: path, split, target vector and three flags.\"\"\"
    pictures = {}
    with open(annotation_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            entry = pictures.setdefault(row["picture_md5"],
                                        {"codes": set(), "path": row["winning_path"]})
            entry["codes"].add(row["code"])

    clear = {}
    with open(clear_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["clear"] == "1":
                clear[row["picture_md5"]] = row["winning_path"]

    with open(split_csv, newline="", encoding="utf-8") as fh:
        split = {row["picture_md5"]: row["split"] for row in csv.DictReader(fh)}

    rows = []

    # Pictures that carry a condition. In variant B, pictures that carry only an object are
    # added too: they answer no to every condition and yes to the object flag.
    for md5, entry in pictures.items():
        flags = {c: int(bool(entry["codes"] & LP_ALIASES.get(c, {c}))) for c in LP_COLUMNS}
        has_lp = any(flags.values())
        has_object = bool(entry["codes"] & OBJECT_CODES)
        if not (has_lp or (variant == "b" and has_object)):
            continue
        if split.get(md5) not in ("train", "test"):
            continue
        rows.append({"md5": md5, "path": entry["path"], "split": split[md5], "flags": flags,
                     "has_lp": has_lp, "has_object": has_object, "is_clear": False})

    # Clear pictures: no marks at all, so every answer is no.
    for md5, path in clear.items():
        if split.get(md5) not in ("train", "test"):
            continue
        rows.append({"md5": md5, "path": path, "split": split[md5],
                     "flags": {c: 0 for c in LP_COLUMNS},
                     "has_lp": False, "has_object": False, "is_clear": True})

    for row in rows:
        target = [row["flags"][c] for c in LP_COLUMNS]
        if variant == "b":
            target.append(int(row["has_object"]))
        row["target"] = target
    rows.sort(key=lambda r: r["md5"])
    return rows


rows = build_rows(VARIANT, ANNOTATION_CSV, CLEAR_CSV, SPLIT_CSV)
train_n = sum(1 for r in rows if r["split"] == "train")
print(f"variant {VARIANT}: {len(rows)} pictures, {train_n} train / {len(rows) - train_n} test")
""", output=build_out)

md("""
## 10. Check the table before training

The counts below should match section 4. If one does not, stop: a wrong label table produces a
wrong model, and the metrics will look plausible either way.
""")

code("""
print(f"{'code':8s} {'condition':26s} {'pictures':>9s}")
for code_, name in LP_TAGS:
    print(f"{code_:8s} {name:26s} {sum(r['flags'][code_] for r in rows):9d}")
if VARIANT == "b":
    print(f"{'object':8s} {'any object present':26s} {sum(r['target'][-1] for r in rows):9d}")
print(f"{'clear':8s} {'nothing marked':26s} {sum(r['is_clear'] for r in rows):9d}")
""", output=check_out)

md("""
## 11. The model

A standard image network, ResNet50 pretrained on ImageNet, with the last layer replaced by one
score per question. No softmax, because the questions are independent. The loss is binary
cross-entropy averaged over the twelve questions, so the model is pushed to get all of them
right, not just the common ones.
""")

code("""
def build_model(n_outputs):
    import torch.nn as nn
    from torchvision import models
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    model.fc = nn.Linear(model.fc.in_features, n_outputs)
    return model
""")

md("""
## 12. The image pipeline

Images are resized straight to 224 by 224 with no augmentation, so a difference between two
runs is the labels and not the preprocessing. Normalisation uses the standard ImageNet
statistics the pretrained network expects.
""")

code("""
class LensDataset:
    def __init__(self, rows, image_root, imgsz=224):
        self.rows, self.image_root, self.imgsz = rows, Path(image_root), imgsz

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        import torch
        from PIL import Image
        from torchvision import transforms
        row = self.rows[index]
        transform = transforms.Compose([
            transforms.Resize((self.imgsz, self.imgsz)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        with Image.open(self.image_root / row["path"]) as img:
            tensor = transform(img.convert("RGB"))
        return tensor, torch.tensor(row["target"], dtype=torch.float32)
""")

md("""
## 13. Training

Fifty epochs, fixed schedule, no early stopping: the last epoch is the model of record. That
matches the earlier five-condition runs, so the numbers are comparable. No class weighting on
the first run, for the same reason.
""")

code("""
def train(rows, epochs=50, batch=8, lr=1e-4, seed=42, image_root=IMAGE_ROOT):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_rows = [r for r in rows if r["split"] == "train"]
    loader = DataLoader(LensDataset(train_rows, image_root), batch_size=batch, shuffle=True,
                        num_workers=4, pin_memory=(device.type == "cuda"))
    model = build_model(len(rows[0]["target"])).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9, nesterov=True,
                                weight_decay=1e-4)
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda"))

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        for images, targets in loader:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                loss = criterion(model(images), targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running += float(loss.detach()) * images.size(0)
        print(f"epoch {epoch:02d}/{epochs}  train loss {running / len(train_rows):.4f}")
    return model
""")

md("""
## 14. Measuring

Average precision is computed per condition from the ranking of the scores. A condition with
no positive pictures in the test set is reported as blank and left out of the average.
""")

code("""
def average_precision(y_true, y_score):
    \"\"\"Average precision for one condition, the same definition as scikit-learn.\"\"\"
    y_true = np.asarray(y_true, dtype=float)
    y_score = np.asarray(y_score, dtype=float)
    if y_true.sum() == 0:
        return float("nan")
    order = np.argsort(-y_score, kind="stable")
    hits = y_true[order]
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(hits) + 1)
    recall = tp / y_true.sum()
    return float((np.diff(np.concatenate([[0.0], recall])) * precision).sum())


def report(y_true, y_score, columns):
    print(f"{'condition':28s} {'pictures':>9s} {'AUPRC':>7s} {'F1@0.5':>7s}")
    values = []
    for j, name in enumerate(columns):
        ap = average_precision(y_true[:, j], y_score[:, j])
        pred = y_score[:, j] >= 0.5
        tp = float((pred & (y_true[:, j] == 1)).sum())
        fp = float((pred & (y_true[:, j] == 0)).sum())
        fn = float((~pred & (y_true[:, j] == 1)).sum())
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
        support = int(y_true[:, j].sum())
        print(f"{name:28s} {support:9d} {ap:7.3f} {f1:7.3f}")
        if support >= 20:
            values.append(ap)
    if values:
        print(f"\\naverage over conditions with at least 20 test pictures: {np.mean(values):.3f}")
    else:
        print("\\nno condition has 20 or more test pictures in this subset")
""")

md("""
## 15. Reading the results

What to look at, in order:

1. **The average over the eight conditions with at least 20 test pictures.** That is the
   headline. Dirty Strobe, View Obstructed, Bubble Scatter and Package Misalignment have too
   few pictures to judge; they are printed and excluded from the average.
2. **Folded Lens on its own.** It appears with Multiple Lens in almost every picture, so a model
   can score Multiple Lens perfectly and still miss Folded Lens. A low Folded Lens score beside
   a high Multiple Lens score means the model learned the pairing, not the appearance. That is
   a label-design finding, not a training bug.
3. **The same average on mixed pictures.** In variant B, compare conditions-only pictures with
   pictures that carry a condition and an object. A large drop means the object flag has become
   a shortcut: the model has learned "object present, so no condition", which would be wrong on
   exactly the pictures that matter.
4. **The object fire rate on Clear pictures.** This is the false-fire number and it should be
   low, while the fire rate on object pictures should be high. No AUPRC is quoted for this flag.

Two caveats to keep in view when quoting a number:

- **Low Dose has an unfinished annotation task behind it.** Most pictures in its folder carry no
  tag, which may mean "not low dose" or may mean "not yet looked at". Its score is the least
  trustworthy of the eight and should not be quoted alone.
- **Rare conditions are noise.** One or two test pictures cannot support a conclusion in either
  direction.
""")

md("""
## 16. What success looks like

| Measure | Target |
|---|---|
| Average over the eight judgeable conditions | at least 0.85 |
| Folded Lens | at least 0.70 |
| Lens Off Center | at least 0.90 |
| Dirty Camera | at least 0.85 |
| Low Dose | at least 0.70 |
| Object flag fires on object pictures (variant B) | at least 90 percent |
| Object flag fires on Clear pictures (variant B) | at most 5 percent |
| Conditions-plus-object pictures, variant B | within 0.05 of the conditions-only pictures |

If variant A clears its targets and variant B's flag fires as above, the routing step is worth
building. If the mixed-picture score collapses in B, the routing design changes before any rules
are written.
""")

md("""
## 17. Out of scope

Turning these twelve answers into a pass or fail decision, and identifying which object is
present. Those are the next two pieces of work and they are separate on purpose: the classifier
answers questions about the lens, the detector finds objects, and a rules layer combines the
two.
""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.10"},
}
nbf.validate(nb)
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print(f"written {OUT} with {len(cells)} cells")
