"""Multi-label LP classifier: one file, two variants (A and B).

WHAT THIS FILE DOES, IN PLAIN WORDS
------------------------------------
We ask one neural network a set of yes/no questions about each lens picture:

    "Does this picture show Multiple Lens?  Folded Lens?  Low Dose? ..."

Twelve questions, one per LP (lens presentation) tag. The answers are independent, so a
picture can answer yes to several at once. That is what "multi-label" means here.

A picture with nothing wrong answers no to all twelve. That is the Clear case, and it is
what makes the model able to say "pass" later. There is no separate Clear output: Clear is
simply the row where every answer is no.

Two variants, same code:

    A  pure LP      rows = pictures with an LP tag + Clear pictures
                    columns = the 12 LP questions
                    Use this to measure how well the network sees the LP conditions.

    B  LP + object  the same rows, plus pictures that carry an object but no LP tag
                    columns = the 12 LP questions + one "object present" question
                    Use this to check whether a single coarse object flag fires, which is
                    what the routing block will need later. The object column is never
                    averaged into the LP scores; it is read as fire rates only.

HOW TO RUN IT
-------------
Step 1, no GPU and no torch needed, just to build and check the labels:

    python experiments/multilabel_lp_full/train_lp.py --variant a --labels-only
    python experiments/multilabel_lp_full/train_lp.py --variant b --labels-only

Step 2, a two-step shape check on random tensors (needs torch, no images):

    python experiments/multilabel_lp_full/train_lp.py --variant a --smoke

Step 3, the real run on the VM (needs torch, torchvision and the image folder):

    python experiments/multilabel_lp_full/train_lp.py --variant a \
        --image-root /home/amd100-user/FMD_Data_26082026/fmd_temp_images \
        --out run/multilabel_lp_full_20261027/a

The client works in PyTorch, and so does this file: torchvision ResNet50, BCEWithLogitsLoss,
one sigmoid score per question. The older single-label arena used TensorFlow; this line has
always been PyTorch, so nothing needs porting.

WHERE THE LABELS COME FROM
--------------------------
`run/eda_full_20261015/resolved_labels.csv` is the annotation of record: one annotation per
picture, newest file wins, duplicate copies of a picture collapsed. A picture is a row only
if it carries a label, or if it is Clear. Empty entries in unfinished annotation tasks are
neither, so they never become rows and can never be trained as negatives.

Clear pictures carry no annotation entry at all, so their identity comes from the matrix's
`clear` column, which was checked to be exactly the set of pictures with an empty entry.

The train/test assignment is the frozen v5 split, so this experiment cannot invent its own
split and cannot leak a picture across both sides.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- paths and label space

# The repo root is two levels up from experiments/multilabel_lp_full/train_lp.py
ROOT = Path(__file__).resolve().parents[2]
# Inputs can be pointed at a newer annotation run without editing this file, so an older
# run stays reproducible:
#   LP_RESOLVED=run/eda_full_20261028/resolved_labels.csv LP_SPLIT=run/split_20261028_v6/split_80_20.csv
RESOLVED = ROOT / os.environ.get("LP_RESOLVED", "run/eda_full_20261028/resolved_labels.csv")
MATRIX = ROOT / os.environ.get("LP_MATRIX", "run/multilabel_edge_20261029_rev4/label_matrix.csv")
SPLIT = ROOT / os.environ.get("LP_SPLIT", "run/split_20261028_v6/split_80_20.csv")

# The twelve LP tags that have pictures, in a fixed order. The order is the column order of
# every target vector, every metric row and every checkpoint. Never reorder this list.
# Three guide tags are absent on purpose because no picture carries them:
# Edge Bottle-Capped (P1_EBC), Torn Lens (P1_TL), Lens Rupture (P1_LR).
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

# Codes that mean "an object is marked on this picture". All seven object classes collapse
# into the single object column of variant B, because the routing block only needs to know
# whether something is there, not what it is. Typing the object is the YOLO's job.
OBJECT_CODES = {
    "P2_BB", "Bubble", "P2_BI", "Bubble Irregular", "P2_BST", "Stretched Bubble",
    "P2_BC", "Bubble Cluster", "P2_WP", "Wet Package",
    "P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
    "P3_HE", "HEMA Fragment",
}

# Some LP columns accept two codes, because the same condition was written two ways in
# different annotation files. View Obstructed is P2_FOV in one file and F2_FOV in another.
LP_ALIASES = {"P2_FOV": {"P2_FOV", "F2_FOV"}}

# Expected row counts and positives, frozen in the spec. If the data ever changes, the run
# stops here instead of silently training on a different dataset.
# 2026-10-29: re-frozen on the 24-file annotation and split v7. The previous run's numbers
# (a 6219 rows, b 6659, and the older positives) are kept in git history and in
# run/multilabel_lp_full_20261028/.
EXPECTED = {
    "a": {"rows": 6747, "positives": {"P1_MPP": 1428, "P1_ML": 1426, "P2_LOC": 1201,
                                      "P2_DC": 573, "P1_NL": 326, "P1_FL": 333,
                                      "P2_LD": 677, "P1_COC": 185, "P2_DS": 33,
                                      "P2_FOV": 63, "P2_BSC": 5, "P1_PPM": 33}},
    "b": {"rows": 7470, "positives": {"P1_MPP": 1428, "P1_ML": 1426, "P2_LOC": 1201,
                                      "P2_DC": 573, "P1_NL": 326, "P1_FL": 333,
                                      "P2_LD": 677, "P1_COC": 185, "P2_DS": 33,
                                      "P2_FOV": 63, "P2_BSC": 5, "P1_PPM": 33}},
}


# ---------------------------------------------------------------- part 1: labels
# This part is pure Python. It runs on any machine, with or without torch, so the label
# matrix can be checked before anyone books a GPU.

def read_annotation():
    """Return {md5: {"codes": set, "path": str}} from the annotation of record."""
    pictures = {}
    with open(RESOLVED, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            md5 = row["picture_md5"]
            entry = pictures.setdefault(md5, {"codes": set(), "path": row["winning_path"]})
            entry["codes"].add(row["code"])
    return pictures


def read_clear():
    """Return the set of md5s that are Clear: no annotation entry, nothing marked."""
    clear = set()
    with open(MATRIX, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["clear"] == "1":
                clear.add(row["picture_md5"])
    return clear


def read_split():
    """Return {md5: "train"|"test"} from the frozen v5 split."""
    with open(SPLIT, newline="", encoding="utf-8") as fh:
        return {row["picture_md5"]: row["split"] for row in csv.DictReader(fh)}


def lp_flags(codes):
    """Which LP questions are yes for this picture, as a dict code -> 0/1."""
    flags = {}
    for code in LP_COLUMNS:
        wanted = LP_ALIASES.get(code, {code})
        flags[code] = 1 if (codes & wanted) else 0
    return flags


def build_rows(variant, verbose=True):
    """Build the rows for one variant.

    A row is one picture the model may see. Each row carries:
        md5, image_path, split, target (list of 0/1 in LP_TAGS order, plus object for B),
        has_lp, has_object, is_clear  (the last three drive the subset reporting).
    """
    pictures = read_annotation()
    clear = read_clear()
    split = read_split()

    rows = []
    for md5, entry in pictures.items():
        flags = lp_flags(entry["codes"])
        has_lp = any(flags.values())
        has_object = bool(entry["codes"] & OBJECT_CODES)

        # Variant A keeps pictures with an LP tag and nothing else. A picture that also has
        # an object stays in A: it is still an LP question, and dropping it would bias the
        # measurement towards easy pictures.
        if variant == "a":
            keep = has_lp
        else:
            # Variant B adds object-only pictures. They answer no to every LP question and
            # yes to the object question, which is exactly what the routing block tests.
            keep = has_lp or has_object
        if not keep:
            continue
        rows.append({
            "md5": md5, "image_path": entry["path"], "split": split.get(md5),
            "flags": flags, "has_lp": has_lp, "has_object": has_object, "is_clear": False,
        })

    # Clear pictures have no annotation entry, so they are added from the clear set. They
    # answer no to every question, and they are the only pictures that can teach the model
    # what a pass looks like.
    for md5 in clear:
        rows.append({
            "md5": md5, "image_path": None, "split": split.get(md5),
            "flags": {c: 0 for c in LP_COLUMNS}, "has_lp": False, "has_object": False,
            "is_clear": True,
        })

    # Clear pictures have no path in the annotation file, so take it from the matrix row.
    if any(r["image_path"] is None for r in rows):
        with open(MATRIX, newline="", encoding="utf-8") as fh:
            path_of = {row["picture_md5"]: row["winning_path"] for row in csv.DictReader(fh)}
        for row in rows:
            if row["image_path"] is None:
                row["image_path"] = path_of[row["md5"]]

    # Keep only pictures the frozen split actually assigns. Anything outside the split is
    # not part of this experiment, by design.
    rows = [r for r in rows if r["split"] in ("train", "test")]

    # Build the target vector once, so training and evaluation cannot disagree on order.
    for row in rows:
        target = [row["flags"][c] for c in LP_COLUMNS]
        if variant == "b":
            target.append(1 if row["has_object"] else 0)
        row["target"] = target

    rows.sort(key=lambda r: r["md5"])

    # Stop loudly if the data is not the data the spec was written against.
    expected = EXPECTED[variant]
    if len(rows) != expected["rows"]:
        raise SystemExit(f"variant {variant}: {len(rows)} rows, expected {expected['rows']}")
    for code, want in expected["positives"].items():
        got = sum(r["flags"][code] for r in rows)
        if got != want:
            raise SystemExit(f"variant {variant}: {code} has {got} positives, expected {want}")

    if verbose:
        n_train = sum(1 for r in rows if r["split"] == "train")
        print(f"variant {variant}: {len(rows)} rows, {n_train} train / {len(rows) - n_train} test")
        for code, name in LP_TAGS:
            print(f"  {code:8s} {name:26s} {sum(r['flags'][code] for r in rows):5d}")
        if variant == "b":
            print(f"  {'object':8s} {'any object present':26s} {sum(r['target'][-1] for r in rows):5d}")
        print(f"  {'clear':8s} {'all-zero rows':26s} {sum(r['is_clear'] for r in rows):5d}")
    return rows


def write_labels(rows, variant, out_path):
    """Write the label matrix as CSV, one row per picture. Useful for review and for reuse."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["md5", "image_path", "split"] + LP_COLUMNS
    if variant == "b":
        columns.append("object_present")
    columns += ["has_lp", "has_object", "is_clear"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row["md5"], row["image_path"], row["split"]] + row["target"] +
                            [int(row["has_lp"]), int(row["has_object"]), int(row["is_clear"])])
    print(f"labels written: {out_path}")


# ---------------------------------------------------------------- part 2: metrics
# AUPRC is the metric of record because the classes are very uneven (Multiple Lens 1,439
# pictures, Package Misalignment 2). Accuracy would be meaningless: a model that always
# says no scores 99% on the rarest class. Average precision does not let it get away with
# that. These functions are numpy only, so they behave the same everywhere.

def average_precision(y_true, y_score):
    """Average precision for one class, same definition as sklearn's average_precision_score."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_score = np.asarray(y_score, dtype=np.float64)
    n_pos = y_true.sum()
    if n_pos == 0:
        return float("nan")          # class absent here, excluded from the macro average
    order = np.argsort(-y_score, kind="stable")
    hits = y_true[order]
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(hits) + 1)
    recall = tp / n_pos
    delta = np.diff(np.concatenate([[0.0], recall]))
    return float((delta * precision).sum())


def macro_ap(y_true, y_score, columns):
    """Mean AP over the columns that have at least one positive in this subset."""
    values = {}
    for j, name in enumerate(columns):
        ap = average_precision(y_true[:, j], y_score[:, j])
        if not np.isnan(ap):
            values[name] = ap
    macro = float(np.mean(list(values.values()))) if values else float("nan")
    return macro, values


def precision_recall_f1(y_true, y_score, threshold):
    """Plain precision, recall and F1 at one fixed threshold, per column."""
    pred = (y_score >= threshold).astype(np.float64)
    out = {}
    for j, name in enumerate(LP_COLUMNS):
        tp = float(((pred[:, j] == 1) & (y_true[:, j] == 1)).sum())
        fp = float(((pred[:, j] == 1) & (y_true[:, j] == 0)).sum())
        fn = float(((pred[:, j] == 0) & (y_true[:, j] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[name] = {"precision": precision, "recall": recall, "f1": f1,
                     "support": int(y_true[:, j].sum())}
    return out


def best_f1_threshold(y_true, y_score, name):
    """The threshold in 0.05 steps that gives the best F1 for one class.

    Reported next to the 0.5 numbers so a threshold effect is visible: a class can look
    dead at 0.5 and fine at 0.2, and that difference is information, not a bug.
    """
    j = LP_COLUMNS.index(name)
    best = (-1.0, 0.5)
    for threshold in np.arange(0.05, 1.0, 0.05):
        f1 = precision_recall_f1(y_true, y_score, float(threshold))[name]["f1"]
        if f1 > best[0]:
            best = (f1, float(threshold))
    return {"best_f1": best[0], "threshold": best[1]}


def evaluate(y_true, y_score, rows, variant):
    """Every number this experiment reports, from one place.

    y_true / y_score are arrays of shape (n_pictures, n_columns). `rows` is the same list
    used to build them, so the subset masks line up by position.
    """
    n = len(rows)
    n_cols = y_true.shape[1]

    macro, per_class = macro_ap(y_true, y_score, LP_COLUMNS)
    at_half = precision_recall_f1(y_true, y_score, 0.5)

    # Judgeable = the class has enough test pictures to mean anything. The spec fixed 20.
    judgeable = {c: v for c, v in per_class.items() if at_half[c]["support"] >= 20}
    macro_judgeable = float(np.mean(list(judgeable.values()))) if judgeable else float("nan")

    # Exact match and Hamming are over the LP columns only, never the object column.
    pred = (y_score[:, :len(LP_COLUMNS)] >= 0.5).astype(int)
    truth = y_true[:, :len(LP_COLUMNS)].astype(int)
    exact = float((pred == truth).all(axis=1).mean())
    hamming = float((pred != truth).mean())

    # The same LP average precision, computed separately on three kinds of picture. If the
    # model only works on LP-only pictures and collapses on mixed ones, it has learned the
    # shortcut "object present means no LP tag" and the routing design must change.
    def subset_mask(predicate):
        return np.array([predicate(r) for r in rows])

    subsets = {}
    for label, predicate in [
        ("lp_only", lambda r: r["has_lp"] and not r["has_object"]),
        ("mixed", lambda r: r["has_lp"] and r["has_object"]),
        ("clear", lambda r: r["is_clear"]),
    ]:
        mask = subset_mask(predicate)
        if mask.sum() == 0:
            continue
        m, values = macro_ap(y_true[mask][:, :len(LP_COLUMNS)],
                             y_score[mask][:, :len(LP_COLUMNS)], LP_COLUMNS)
        subsets[label] = {"pictures": int(mask.sum()), "macro_ap": m, "per_class": values}

    result = {
        "rows": n,
        "macro_auprc_all": macro,
        "macro_auprc_judgeable": macro_judgeable,
        "judgeable_classes": sorted(judgeable),
        "per_class": {},
        "exact_match": exact,
        "hamming_loss": hamming,
        "subsets": subsets,
    }
    for code, name in LP_TAGS:
        result["per_class"][code] = {
            "name": name,
            "support": at_half[code]["support"],
            "auprc": per_class.get(code, float("nan")),
            "precision_0.5": at_half[code]["precision"],
            "recall_0.5": at_half[code]["recall"],
            "f1_0.5": at_half[code]["f1"],
            **best_f1_threshold(y_true, y_score, code),
        }

    # The object column is read as fire rates, never as a class score. AUPRC on a bucket of
    # seven unrelated classes would flatter the model and mean nothing.
    if variant == "b":
        object_scores = y_score[:, -1]
        fires = object_scores >= 0.5
        object_only = np.array([r["has_object"] and not r["has_lp"] for r in rows])
        mixed = np.array([r["has_object"] and r["has_lp"] for r in rows])
        clear = np.array([r["is_clear"] for r in rows])
        result["object_column"] = {
            "note": "fire rates only; not comparable with the LP AUPRC values",
            "fire_rate_object_only": float(fires[object_only].mean()) if object_only.any() else None,
            "fire_rate_mixed": float(fires[mixed].mean()) if mixed.any() else None,
            "fire_rate_clear": float(fires[clear].mean()) if clear.any() else None,
            "pictures_object_only": int(object_only.sum()),
            "pictures_mixed": int(mixed.sum()),
            "pictures_clear": int(clear.sum()),
        }
    return result


# ---------------------------------------------------------------- part 3: torch
# Everything below needs torch. The import is inside the functions so that --labels-only
# works on a laptop with no torch installed.

def build_model(n_outputs, arch="resnet50"):
    """ResNet50 trunk with a fresh head: one score per question.

    The head has no softmax on purpose. Softmax forces the answers to compete, which is
    wrong here: a picture can genuinely have Multiple Lens and Folded Lens at once.
    """
    import torch.nn as nn
    from torchvision import models

    if arch != "resnet50":
        raise SystemExit(f"arch {arch} not implemented in this file; start with resnet50")
    weights = models.ResNet50_Weights.IMAGENET1K_V2
    model = models.resnet50(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, n_outputs)
    return model


class LensDataset:
    """One item = one picture tensor + one target vector.

    Images are resized straight to 224 x 224 with no augmentation. That matches the earlier
    multi-label runs, so a difference between runs is the labels and not the preprocessing.
    """

    def __init__(self, rows, image_root, imgsz=224):
        self.rows = rows
        self.image_root = Path(image_root) if image_root else None
        self.imgsz = imgsz

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        import torch
        from PIL import Image
        from torchvision import transforms

        row = self.rows[index]
        if self.image_root is None:
            raise SystemExit("image root not set: pass --image-root or set FMD_IMAGE_ROOT")
        path = self.image_root / row["image_path"]
        if not path.is_file():
            raise SystemExit(f"image not found: {path}")
        transform = transforms.Compose([
            transforms.Resize((self.imgsz, self.imgsz)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        with Image.open(path) as img:
            tensor = transform(img.convert("RGB"))
        target = torch.tensor(row["target"], dtype=torch.float32)
        return tensor, target


def pos_weight_from(rows, n_cols):
    """Weight each positive by how rare it is: negatives / positives.

    Off by default, exactly as in the first October run. When switched on it is global, one
    weight per column, and it mainly helps the rare classes (Folded Lens, Low Dose).
    """
    import torch
    counts = np.zeros(n_cols, dtype=np.float64)
    for row in rows:
        counts += np.array(row["target"], dtype=np.float64)
    negatives = len(rows) - counts
    weights = np.where(counts > 0, negatives / np.maximum(counts, 1), 1.0)
    return torch.tensor(weights, dtype=torch.float32)


def run_training(rows, variant, args):
    """Train the model, evaluate once on the test split, write metrics.json."""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_cols = len(LP_COLUMNS) + (1 if variant == "b" else 0)

    train_rows = [r for r in rows if r["split"] == "train"]
    test_rows = [r for r in rows if r["split"] == "test"]
    train_ds = LensDataset(train_rows, args.image_root, args.imgsz)
    test_ds = LensDataset(test_rows, args.image_root, args.imgsz)
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                              num_workers=args.workers, pin_memory=(device.type == "cuda"))
    test_loader = DataLoader(test_ds, batch_size=args.batch, shuffle=False,
                             num_workers=args.workers, pin_memory=(device.type == "cuda"))

    model = build_model(n_cols, args.arch).to(device)
    weight = pos_weight_from(train_rows, n_cols).to(device) if args.pos_weight else None
    criterion = nn.BCEWithLogitsLoss(pos_weight=weight)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9,
                                nesterov=True, weight_decay=1e-4)
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda"))

    history = []
    started = time.time()
    train_started = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for images, targets in train_loader:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
                loss = criterion(logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach()) * images.size(0)
        mean_loss = total_loss / len(train_ds)
        history.append({"epoch": epoch, "train_loss": mean_loss})
        print(f"epoch {epoch:02d}/{args.epochs}  train loss {mean_loss:.4f}", flush=True)

    # Fixed schedule, no early stopping: the last epoch is the model of record, matching the
    # October protocol. Evaluating once at the end keeps the number honest and the run short.
    train_seconds = time.time() - train_started

    # Inference timing: the whole test pass, timed as a unit. The GPU is already warm from
    # training on the same shapes, so the per-image figure is steady state, not cold start.
    model.eval()
    scores, truths = [], []
    infer_started = time.time()
    with torch.no_grad():
        for images, targets in test_loader:
            images = images.to(device)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
            scores.append(torch.sigmoid(logits).float().cpu().numpy())
            truths.append(targets.numpy())
    y_score = np.concatenate(scores, axis=0)
    y_true = np.concatenate(truths, axis=0)
    infer_seconds = time.time() - infer_started

    metrics = evaluate(y_true, y_score, test_rows, variant)
    metrics["config"] = {
        "variant": variant, "arch": args.arch, "imgsz": args.imgsz, "batch": args.batch,
        "epochs": args.epochs, "lr": args.lr, "pos_weight": bool(args.pos_weight),
        "seed": args.seed, "device": str(device), "columns": LP_COLUMNS +
        (["object_present"] if variant == "b" else []),
    }
    metrics["timing"] = {
        "seconds_total": round(time.time() - started, 1),
        "seconds_training": round(train_seconds, 1),
        "seconds_per_epoch": round(train_seconds / args.epochs, 1),
        "seconds_inference": round(infer_seconds, 1),
        "inference_images": len(test_rows),
        "inference_ms_per_image": round(1000.0 * infer_seconds / max(len(test_rows), 1), 2),
    }
    metrics["history"] = history

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    torch.save(model.state_dict(), out_dir / "final.pt")
    print(f"metrics written: {out_dir / 'metrics.json'}")
    t = metrics["timing"]
    print(f"timing: train {t['seconds_training']}s ({t['seconds_per_epoch']}s/epoch), "
          f"inference {t['seconds_inference']}s = {t['inference_ms_per_image']} ms/image "
          f"on {t['inference_images']} test pictures")
    return metrics


def run_smoke(variant, args):
    """Two optimizer steps on random tensors: proves shapes, loss and AMP without images."""
    import torch
    import torch.nn as nn

    n_cols = len(LP_COLUMNS) + (1 if variant == "b" else 0)
    model = build_model(n_cols, args.arch)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, nesterov=True)
    images = torch.randn(2, 3, args.imgsz, args.imgsz)
    targets = torch.randint(0, 2, (2, n_cols)).float()
    for step in range(2):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(images), targets)
        loss.backward()
        optimizer.step()
        print(f"smoke step {step + 1}: loss {float(loss.detach()):.4f}, output {tuple(model(images).shape)}")
    print(f"smoke ok: variant {variant}, {n_cols} outputs")


# ---------------------------------------------------------------- command line

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=["a", "b"], required=True,
                        help="a = LP + Clear, b = LP + Clear + one object column")
    parser.add_argument("--labels-only", action="store_true",
                        help="build and check the label matrix, then stop (no torch needed)")
    parser.add_argument("--smoke", action="store_true",
                        help="two steps on random tensors, no images needed")
    parser.add_argument("--image-root", default=os.environ.get("FMD_IMAGE_ROOT", ""),
                        help="folder that holds the image files")
    parser.add_argument("--out", default="", help="output folder for metrics and checkpoint")
    parser.add_argument("--arch", default="resnet50")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pos-weight", action="store_true",
                        help="off by default; the first run never uses it")
    args = parser.parse_args()

    rows = build_rows(args.variant)

    if args.labels_only:
        out = Path(args.out) if args.out else ROOT / f"run/multilabel_lp_full_20261027/labels_{args.variant}.csv"
        write_labels(rows, args.variant, out)
        return

    if args.smoke:
        run_smoke(args.variant, args)
        return

    if not args.image_root:
        raise SystemExit("set --image-root or FMD_IMAGE_ROOT before training")

    # The label table stores each picture's path relative to the data root, and those paths
    # start with three different top folders. Pointing --image-root at one of them instead of
    # the parent would fail on the first batch, after the model is built. Check a spread of
    # sample paths here so a wrong root stops the run before it starts.
    root = Path(args.image_root)
    step = max(1, len(rows) // 40)
    sample = rows[::step][:40]
    missing = [r["image_path"] for r in sample if not (root / r["image_path"]).is_file()]
    if missing:
        raise SystemExit(
            f"{len(missing)} of {len(sample)} sampled pictures are not under {root}\n"
            f"  expected layout: <root>/<top folder>/<class folder>/<file>\n"
            f"  first missing: {missing[0]}\n"
            f"  the root must hold all three top folders, not one of them"
        )
    print(f"image root ok: {len(sample)} sampled pictures found under {root}")
    if not args.out:
        args.out = str(ROOT / f"run/multilabel_lp_full_20261027/{args.variant}")
    run_training(rows, args.variant, args)


if __name__ == "__main__":
    main()
