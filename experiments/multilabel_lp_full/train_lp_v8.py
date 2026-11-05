"""Multi-label LP classifier, v8: three-way split, thresholds chosen on validation.

WHAT CHANGED FROM train_lp.py (the 2026-10-29 run)
--------------------------------------------------
1. The split is three-way, 70/15/15 (run/split_20261103_v8/split_70_15_15.csv):
       train  the model trains here
       val    used for ONE thing: choosing the decision threshold of each class
       test   read once, at the end, and never used to choose anything
2. Every class gets its own threshold, picked by a grid search on the validation split
   (0.05 to 0.95 in 0.05 steps, maximum F1). The old file computed the same grid on the
   TEST split, which is the leak this version removes.
3. The test read reports every class twice: at the fixed 0.5 cut and at its chosen
   threshold, so the gain (or the loss) is visible and attributable.
4. A class with fewer than 10 validation positives is not tuned. It keeps 0.5 and is
   labelled "default" rather than given a threshold that is really noise.
5. With --all-rows, variant a also keeps the 723 object-only pictures, so a and b
   read the same 7,470 rows and differ only in the thirteenth answer.

Everything else is the 2026-10-29 protocol, unchanged on purpose: ResNet-50, 224 px,
batch 8, 50 epochs fixed with no early stopping, SGD lr 1e-4 momentum 0.9, seed 42,
BCEWithLogitsLoss, no augmentation, pos_weight off. The last epoch is the model of
record. That way the only two differences from the October run are the split shape and
where the threshold comes from.

HOW TO RUN IT
-------------
Labels only, no GPU and no torch:

    python experiments/multilabel_lp_full/train_lp_v8.py --variant b --labels-only

Shape check on random tensors (needs torch, no images):

    python experiments/multilabel_lp_full/train_lp_v8.py --variant b --smoke

The real run on the VM:

    python experiments/multilabel_lp_full/train_lp_v8.py --variant b \
        --image-root /data/FMD_Data_26082026/fmd_temp_images \
        --out run/multilabel_lp_v8_20261103/b
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- paths and label space

ROOT = Path(__file__).resolve().parents[2]
RESOLVED = ROOT / os.environ.get("LP_RESOLVED", "run/eda_full_20261029/resolved_labels.csv")
MATRIX = ROOT / os.environ.get("LP_MATRIX", "run/multilabel_edge_20261029_rev4/label_matrix.csv")
SPLIT = ROOT / os.environ.get("LP_SPLIT", "run/split_20261103_v8/split_70_15_15.csv")

# The twelve LP tags that have pictures, in a fixed order. Never reorder: it is the
# column order of every target vector, metric row and checkpoint.
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

OBJECT_CODES = {
    "P2_BB", "Bubble", "P2_BI", "Bubble Irregular", "P2_BST", "Stretched Bubble",
    "P2_BC", "Bubble Cluster", "P2_WP", "Wet Package",
    "P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
    "P3_HE", "HEMA Fragment",
}
LP_ALIASES = {"P2_FOV": {"P2_FOV", "F2_FOV"}}

# Row counts and positives frozen against the 24-file annotation. The three-way split
# moves pictures between sides; it does not change the population, so these still hold.
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
SPLITS = ("train", "val", "test")


# ---------------------------------------------------------------- part 1: labels

def read_annotation():
    pictures = {}
    with open(RESOLVED, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            md5 = row["picture_md5"]
            entry = pictures.setdefault(md5, {"codes": set(), "path": row["winning_path"]})
            entry["codes"].add(row["code"])
    return pictures


def read_clear():
    clear = set()
    with open(MATRIX, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["clear"] == "1":
                clear.add(row["picture_md5"])
    return clear


def read_split():
    """Return {md5: "train"|"val"|"test"} from the frozen v8 split."""
    with open(SPLIT, newline="", encoding="utf-8") as fh:
        return {row["picture_md5"]: row["split"] for row in csv.DictReader(fh)}


def lp_flags(codes):
    flags = {}
    for code in LP_COLUMNS:
        wanted = LP_ALIASES.get(code, {code})
        flags[code] = 1 if (codes & wanted) else 0
    return flags


def build_rows(variant, verbose=True, all_rows=False):
    """Build the rows for one variant, carrying the three-way split assignment."""
    pictures = read_annotation()
    clear = read_clear()
    split = read_split()

    rows = []
    for md5, entry in pictures.items():
        flags = lp_flags(entry["codes"])
        has_lp = any(flags.values())
        has_object = bool(entry["codes"] & OBJECT_CODES)
        keep = has_lp or (has_object and (variant == "b" or all_rows))
        if not keep:
            continue
        rows.append({"md5": md5, "image_path": entry["path"], "split": split.get(md5),
                     "flags": flags, "has_lp": has_lp, "has_object": has_object,
                     "is_clear": False})

    for md5 in clear:
        rows.append({"md5": md5, "image_path": None, "split": split.get(md5),
                     "flags": {c: 0 for c in LP_COLUMNS}, "has_lp": False,
                     "has_object": False, "is_clear": True})

    if any(r["image_path"] is None for r in rows):
        with open(MATRIX, newline="", encoding="utf-8") as fh:
            path_of = {row["picture_md5"]: row["winning_path"] for row in csv.DictReader(fh)}
        for row in rows:
            if row["image_path"] is None:
                row["image_path"] = path_of[row["md5"]]

    rows = [r for r in rows if r["split"] in SPLITS]

    for row in rows:
        target = [row["flags"][c] for c in LP_COLUMNS]
        if variant == "b":
            target.append(1 if row["has_object"] else 0)
        row["target"] = target

    rows.sort(key=lambda r: r["md5"])

    expected = EXPECTED["b"] if (variant == "b" or all_rows) else EXPECTED["a"]
    if len(rows) != expected["rows"]:
        raise SystemExit(f"variant {variant}: {len(rows)} rows, expected {expected['rows']}")
    for code, want in expected["positives"].items():
        got = sum(r["flags"][code] for r in rows)
        if got != want:
            raise SystemExit(f"variant {variant}: {code} has {got} positives, expected {want}")
    missing = [r["md5"] for r in rows if r["split"] is None]
    if missing:
        raise SystemExit(f"{len(missing)} rows are not assigned by {SPLIT.name}")

    if verbose:
        counts = {s: sum(1 for r in rows if r["split"] == s) for s in SPLITS}
        print(f"variant {variant}: {len(rows)} rows, "
              f"{counts['train']} train / {counts['val']} val / {counts['test']} test")
        print(f"  {'class':8s} {'name':26s} {'total':>6s} {'train':>6s} {'val':>5s} {'test':>5s}")
        for code, name in LP_TAGS:
            print(f"  {code:8s} {name:26s} "
                  f"{sum(r['flags'][code] for r in rows):6d} "
                  + " ".join(f"{sum(1 for r in rows if r['flags'][code] and r['split'] == s):6d}"
                             for s in SPLITS))
        if variant == "b":
            print(f"  {'object':8s} {'any object present':26s} "
                  f"{sum(r['target'][-1] for r in rows):6d} "
                  + " ".join(f"{sum(1 for r in rows if r['target'][-1] and r['split'] == s):6d}"
                             for s in SPLITS))
        print(f"  {'clear':8s} {'all-zero rows':26s} "
              f"{sum(r['is_clear'] for r in rows):6d} "
              + " ".join(f"{sum(1 for r in rows if r['is_clear'] and r['split'] == s):6d}"
                         for s in SPLITS))
    return rows


def write_labels(rows, variant, out_path):
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

def average_precision(y_true, y_score):
    y_true = np.asarray(y_true, dtype=np.float64)
    y_score = np.asarray(y_score, dtype=np.float64)
    n_pos = y_true.sum()
    if n_pos == 0:
        return float("nan")
    order = np.argsort(-y_score, kind="stable")
    hits = y_true[order]
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(hits) + 1)
    recall = tp / n_pos
    delta = np.diff(np.concatenate([[0.0], recall]))
    return float((delta * precision).sum())


def macro_ap(y_true, y_score, columns):
    values = {}
    for j, name in enumerate(columns):
        ap = average_precision(y_true[:, j], y_score[:, j])
        if not np.isnan(ap):
            values[name] = ap
    macro = float(np.mean(list(values.values()))) if values else float("nan")
    return macro, values


def precision_recall_f1(y_true, y_score, threshold, columns):
    """Precision, recall and F1 at one fixed threshold, per column."""
    pred = (y_score >= threshold).astype(np.float64)
    out = {}
    for j, name in enumerate(columns):
        tp = float(((pred[:, j] == 1) & (y_true[:, j] == 1)).sum())
        fp = float(((pred[:, j] == 1) & (y_true[:, j] == 0)).sum())
        fn = float(((pred[:, j] == 0) & (y_true[:, j] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[name] = {"precision": precision, "recall": recall, "f1": f1,
                     "support": int(y_true[:, j].sum())}
    return out


THRESHOLD_GRID = [round(float(t), 2) for t in np.arange(0.05, 1.0, 0.05)]
DEFAULT_THRESHOLD = 0.5
MIN_VAL_POSITIVES = 10


def choose_thresholds(val_true, val_score, columns, min_positives=MIN_VAL_POSITIVES):
    """Pick one threshold per class by maximum F1 on the validation split.

    Returns {column: {...}} with the chosen threshold, where it came from, the full
    validation curve, and the 0.5 numbers for comparison. A class with fewer than
    `min_positives` validation positives is not tuned: the F1 curve at that support is
    noise, so it keeps 0.5 and says so.
    """
    chosen = {}
    for j, name in enumerate(columns):
        support = int(val_true[:, j].sum())
        curve = []
        for t in THRESHOLD_GRID:
            m = precision_recall_f1(val_true[:, j:j + 1], val_score[:, j:j + 1], t, [name])[name]
            curve.append({"threshold": t, "precision": round(m["precision"], 6),
                          "recall": round(m["recall"], 6), "f1": round(m["f1"], 6)})
        at_half = next(c for c in curve if c["threshold"] == DEFAULT_THRESHOLD)
        if support < min_positives:
            best = max(curve, key=lambda c: (c["f1"], c["threshold"]))
            chosen[name] = {"threshold": DEFAULT_THRESHOLD, "source": "default",
                            "reason": f"val positives {support} < {min_positives}",
                            "val_support": support, "val_f1_at_threshold": at_half["f1"],
                            "val_f1_at_0.5": at_half["f1"],
                            "val_best_f1_seen": best["f1"],
                            "val_best_threshold_seen": best["threshold"],
                            "curve": curve}
            continue
        # Tie-break towards the higher threshold: at equal F1 the stricter cut is the
        # safer operating point, and it keeps the choice off the very low scores.
        best = max(curve, key=lambda c: (c["f1"], c["threshold"]))
        chosen[name] = {"threshold": best["threshold"], "source": "val",
                        "reason": "max F1 on val", "val_support": support,
                        "val_f1_at_threshold": best["f1"],
                        "val_f1_at_0.5": at_half["f1"],
                        "val_best_f1_seen": best["f1"],
                        "val_best_threshold_seen": best["threshold"],
                        "curve": curve}
    return chosen


def evaluate_test(y_true, y_score, rows, variant, thresholds):
    """Every number the test read reports, at 0.5 and at the chosen thresholds."""
    columns = LP_COLUMNS + (["object_present"] if variant == "b" else [])
    macro, per_class = macro_ap(y_true, y_score, LP_COLUMNS)
    at_half = precision_recall_f1(y_true, y_score, DEFAULT_THRESHOLD, columns)

    cut = np.array([thresholds[c]["threshold"] for c in columns])
    pred_at_cut = (y_score >= cut).astype(int)
    truth = y_true.astype(int)
    pred_at_half = (y_score >= DEFAULT_THRESHOLD).astype(int)

    judgeable = {c: v for c, v in per_class.items() if at_half[c]["support"] >= 20}
    macro_judgeable = float(np.mean(list(judgeable.values()))) if judgeable else float("nan")

    lp_slice = slice(0, len(LP_COLUMNS))
    exact_half = float((pred_at_half[:, lp_slice] == truth[:, lp_slice]).all(axis=1).mean())
    exact_cut = float((pred_at_cut[:, lp_slice] == truth[:, lp_slice]).all(axis=1).mean())
    ham_half = float((pred_at_half[:, lp_slice] != truth[:, lp_slice]).mean())
    ham_cut = float((pred_at_cut[:, lp_slice] != truth[:, lp_slice]).mean())

    macro_f1_half = float(np.mean([at_half[c]["f1"] for c in judgeable])) if judgeable else float("nan")
    per_class_f1_cut = {}
    for j, c in enumerate(LP_COLUMNS):
        tp = float(((pred_at_cut[:, j] == 1) & (truth[:, j] == 1)).sum())
        fp = float(((pred_at_cut[:, j] == 1) & (truth[:, j] == 0)).sum())
        fn = float(((pred_at_cut[:, j] == 0) & (truth[:, j] == 1)).sum())
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        per_class_f1_cut[c] = {"precision": p, "recall": r,
                               "f1": 2 * p * r / (p + r) if (p + r) else 0.0}
    macro_f1_cut = float(np.mean([per_class_f1_cut[c]["f1"] for c in judgeable])) if judgeable else float("nan")

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
        "rows": len(rows),
        "macro_auprc_all": macro,
        "macro_auprc_judgeable": macro_judgeable,
        "judgeable_classes": sorted(judgeable),
        "macro_f1_0.5": macro_f1_half,
        "macro_f1_val_thr": macro_f1_cut,
        "exact_match": exact_half,
        "exact_match_val_thr": exact_cut,
        "hamming_loss": ham_half,
        "hamming_loss_val_thr": ham_cut,
        "per_class": {},
        "subsets": subsets,
    }
    for code, name in LP_TAGS:
        result["per_class"][code] = {
            "name": name,
            "support": at_half[code]["support"],
            "auprc": per_class.get(code, float("nan")),
            "threshold": thresholds[code]["threshold"],
            "threshold_source": thresholds[code]["source"],
            "precision_0.5": at_half[code]["precision"],
            "recall_0.5": at_half[code]["recall"],
            "f1_0.5": at_half[code]["f1"],
            "precision_val_thr": per_class_f1_cut[code]["precision"],
            "recall_val_thr": per_class_f1_cut[code]["recall"],
            "f1_val_thr": per_class_f1_cut[code]["f1"],
        }

    if variant == "b":
        j = len(LP_COLUMNS)
        object_scores = y_score[:, j]
        object_only = np.array([r["has_object"] and not r["has_lp"] for r in rows])
        mixed = np.array([r["has_object"] and r["has_lp"] for r in rows])
        clear = np.array([r["is_clear"] for r in rows])
        obj_cut = thresholds["object_present"]["threshold"]
        result["object_column"] = {
            "note": "fire rates only; not comparable with the LP AUPRC values",
            "threshold": obj_cut,
            "threshold_source": thresholds["object_present"]["source"],
            "fire_rate_object_only": float((object_scores >= obj_cut)[object_only].mean()) if object_only.any() else None,
            "fire_rate_mixed": float((object_scores >= obj_cut)[mixed].mean()) if mixed.any() else None,
            "fire_rate_clear": float((object_scores >= obj_cut)[clear].mean()) if clear.any() else None,
            "fire_rate_object_only_0.5": float((object_scores >= 0.5)[object_only].mean()) if object_only.any() else None,
            "fire_rate_mixed_0.5": float((object_scores >= 0.5)[mixed].mean()) if mixed.any() else None,
            "fire_rate_clear_0.5": float((object_scores >= 0.5)[clear].mean()) if clear.any() else None,
            "pictures_object_only": int(object_only.sum()),
            "pictures_mixed": int(mixed.sum()),
            "pictures_clear": int(clear.sum()),
        }
    return result


# ---------------------------------------------------------------- part 3: torch

def build_model(n_outputs, arch="resnet50"):
    import torch.nn as nn
    from torchvision import models

    if arch != "resnet50":
        raise SystemExit(f"arch {arch} not implemented in this file; start with resnet50")
    weights = models.ResNet50_Weights.IMAGENET1K_V2
    model = models.resnet50(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, n_outputs)
    return model


class LensDataset:
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
    import torch
    counts = np.zeros(n_cols, dtype=np.float64)
    for row in rows:
        counts += np.array(row["target"], dtype=np.float64)
    negatives = len(rows) - counts
    weights = np.where(counts > 0, negatives / np.maximum(counts, 1), 1.0)
    return torch.tensor(weights, dtype=torch.float32)


def predict(model, loader, device):
    import torch
    model.eval()
    scores, truths = [], []
    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
            scores.append(torch.sigmoid(logits).float().cpu().numpy())
            truths.append(targets.numpy())
    return np.concatenate(truths, axis=0), np.concatenate(scores, axis=0)


def run_training(rows, variant, args):
    """Train on train, choose thresholds on val, read the test split once."""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    columns = LP_COLUMNS + (["object_present"] if variant == "b" else [])
    n_cols = len(columns)

    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    test_rows = [r for r in rows if r["split"] == "test"]
    if not train_rows or not val_rows or not test_rows:
        raise SystemExit(f"empty split: {len(train_rows)} train / {len(val_rows)} val / "
                         f"{len(test_rows)} test")

    loaders = {}
    for name, part in (("train", train_rows), ("val", val_rows), ("test", test_rows)):
        loaders[name] = DataLoader(
            LensDataset(part, args.image_root, args.imgsz), batch_size=args.batch,
            shuffle=(name == "train"), num_workers=args.workers,
            pin_memory=(device.type == "cuda"))

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
        for images, targets in loaders["train"]:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
                loss = criterion(logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach()) * images.size(0)
        mean_loss = total_loss / len(train_rows)
        history.append({"epoch": epoch, "train_loss": mean_loss})
        print(f"epoch {epoch:02d}/{args.epochs}  train loss {mean_loss:.4f}", flush=True)
    train_seconds = time.time() - train_started

    # The validation read. This is the only place a threshold is chosen, and it happens
    # before the test split is touched.
    val_started = time.time()
    val_true, val_score = predict(model, loaders["val"], device)
    thresholds = choose_thresholds(val_true, val_score, columns, args.min_val_positives)
    val_seconds = time.time() - val_started
    tuned = [c for c in columns if thresholds[c]["source"] == "val"]
    print(f"thresholds chosen on {len(val_rows)} val pictures: "
          f"{len(tuned)} tuned, {len(columns) - len(tuned)} default", flush=True)
    for c in columns:
        t = thresholds[c]
        print(f"  {c:16s} {t['threshold']:.2f}  ({t['source']}, "
              f"val F1 {t['val_f1_at_threshold']:.3f} vs {t['val_f1_at_0.5']:.3f} at 0.5)")

    # The test read, once.
    test_started = time.time()
    test_true, test_score = predict(model, loaders["test"], device)
    test_seconds = time.time() - test_started

    metrics = evaluate_test(test_true, test_score, test_rows, variant, thresholds)
    metrics["variant"] = variant
    metrics["thresholds"] = {
        "objective": "maximum F1 per class on the validation split",
        "grid": THRESHOLD_GRID,
        "default_threshold": DEFAULT_THRESHOLD,
        "min_val_positives": args.min_val_positives,
        "per_class": thresholds,
        "tuned": tuned,
        "default": [c for c in columns if thresholds[c]["source"] != "val"],
    }
    metrics["split"] = {
        "path": str(SPLIT), "md5": hashlib.md5(open(SPLIT, "rb").read()).hexdigest(),
        "counts": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
    }
    metrics["config"] = {
        "variant": variant, "arch": args.arch, "imgsz": args.imgsz, "batch": args.batch,
        "epochs": args.epochs, "lr": args.lr, "pos_weight": bool(args.pos_weight),
        "seed": args.seed, "device": str(device), "columns": columns,
        "split_shape": "70/15/15", "threshold_source": "val",
    }
    metrics["timing"] = {
        "seconds_total": round(time.time() - started, 1),
        "seconds_training": round(train_seconds, 1),
        "seconds_per_epoch": round(train_seconds / args.epochs, 1),
        "seconds_validation": round(val_seconds, 1),
        "seconds_inference": round(test_seconds, 1),
        "inference_images": len(test_rows),
        "inference_ms_per_image": round(1000.0 * test_seconds / max(len(test_rows), 1), 2),
    }
    metrics["history"] = history

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Save the raw scores as well as the summary. With these, any threshold can be re-read
    # on a laptop without the GPU, and a threshold chosen on val can be applied to the test
    # scores later without another training run.
    np.savez_compressed(
        out_dir / "predictions.npz",
        val_md5=np.array([r["md5"] for r in val_rows]),
        val_true=val_true, val_score=val_score,
        test_md5=np.array([r["md5"] for r in test_rows]),
        test_true=test_true, test_score=test_score,
        columns=np.array(columns),
    )
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    with open(out_dir / "thresholds.json", "w", encoding="utf-8") as fh:
        json.dump({"variant": variant, "split": metrics["split"],
                   "objective": metrics["thresholds"]["objective"],
                   "grid": THRESHOLD_GRID, "per_class": thresholds}, fh, indent=2)
    torch.save(model.state_dict(), out_dir / "final.pt")
    print(f"metrics written: {out_dir / 'metrics.json'}")
    print(f"thresholds written: {out_dir / 'thresholds.json'}")
    t = metrics["timing"]
    print(f"timing: train {t['seconds_training']}s ({t['seconds_per_epoch']}s/epoch), "
          f"val {t['seconds_validation']}s, test {t['seconds_inference']}s = "
          f"{t['inference_ms_per_image']} ms/image on {t['inference_images']} test pictures")
    return metrics


def dump_predictions(rows, variant, args):
    """Re-run inference from a saved checkpoint and write predictions.npz. No training."""
    import torch
    from torch.utils.data import DataLoader

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    columns = LP_COLUMNS + (["object_present"] if variant == "b" else [])
    out_dir = Path(args.out)
    ckpt = out_dir / "final.pt"
    if not ckpt.is_file():
        raise SystemExit(f"no checkpoint at {ckpt}")
    model = build_model(len(columns), args.arch).to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
    arrays = {}
    for name in ("val", "test"):
        part = [r for r in rows if r["split"] == name]
        loader = DataLoader(LensDataset(part, args.image_root, args.imgsz),
                            batch_size=args.batch, shuffle=False, num_workers=args.workers)
        truth, score = predict(model, loader, device)
        arrays[name] = (truth, score, [r["md5"] for r in part])
        print(f"{name}: {len(part)} pictures scored")
    np.savez_compressed(
        out_dir / "predictions.npz",
        val_md5=np.array(arrays["val"][2]), val_true=arrays["val"][0], val_score=arrays["val"][1],
        test_md5=np.array(arrays["test"][2]), test_true=arrays["test"][0], test_score=arrays["test"][1],
        columns=np.array(columns),
    )
    print(f"predictions written: {out_dir / 'predictions.npz'}")


def run_smoke(variant, args):
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
        print(f"smoke step {step + 1}: loss {float(loss.detach()):.4f}, "
              f"output {tuple(model(images).shape)}")
    # Prove the threshold chooser runs on a known array as well as the model.
    y_true = np.array([[1], [1], [0], [0], [1], [0]], dtype=float)
    y_score = np.array([[0.9], [0.2], [0.8], [0.1], [0.3], [0.4]])
    chosen = choose_thresholds(y_true, y_score, ["toy"])
    print(f"threshold chooser ok: {chosen['toy']['threshold']} "
          f"(val F1 {chosen['toy']['val_f1_at_threshold']:.3f})")
    print(f"smoke ok: variant {variant}, {n_cols} outputs")


# ---------------------------------------------------------------- command line

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=["a", "b"], required=True)
    parser.add_argument("--labels-only", action="store_true")
    parser.add_argument("--all-rows", action="store_true",
                        help="variant a also keeps object-only pictures, so both variants read 7,470 rows")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--dump-predictions", action="store_true",
                        help="score val and test from --out/final.pt and write predictions.npz")
    parser.add_argument("--image-root", default=os.environ.get("FMD_IMAGE_ROOT", ""))
    parser.add_argument("--out", default="")
    parser.add_argument("--arch", default="resnet50")
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pos-weight", action="store_true")
    parser.add_argument("--min-val-positives", type=int, default=MIN_VAL_POSITIVES,
                        help="a class below this many val positives keeps 0.5")
    args = parser.parse_args()

    rows = build_rows(args.variant, all_rows=args.all_rows)

    if args.labels_only:
        out = Path(args.out) if args.out else \
            ROOT / f"run/multilabel_lp_v8_20261103/labels_{args.variant}.csv"
        write_labels(rows, args.variant, out)
        return

    if args.smoke:
        run_smoke(args.variant, args)
        return

    if not args.image_root:
        raise SystemExit("set --image-root or FMD_IMAGE_ROOT before training")

    root = Path(args.image_root)
    step = max(1, len(rows) // 40)
    sample = rows[::step][:40]
    missing = [r["image_path"] for r in sample if not (root / r["image_path"]).is_file()]
    if missing:
        raise SystemExit(
            f"{len(missing)} of {len(sample)} sampled pictures are not under {root}\n"
            f"  expected layout: <root>/<top folder>/<class folder>/<file>\n"
            f"  first missing: {missing[0]}\n"
            f"  the root must hold all three top folders, not one of them")
    print(f"image root ok: {len(sample)} sampled pictures found under {root}")
    if not args.out:
        args.out = str(ROOT / f"run/multilabel_lp_v8_20261103/{args.variant}")
    if args.dump_predictions:
        dump_predictions(rows, args.variant, args)
        return
    run_training(rows, args.variant, args)


if __name__ == "__main__":
    main()
