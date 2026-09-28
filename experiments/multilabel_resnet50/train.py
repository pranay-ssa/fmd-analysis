#!/usr/bin/env python3
"""Multi-label ResNet50 trainer for the 5 lens-presentation tags.

Code complete, not yet run for real. Recipe (see DESIGN.md):
  base      torchvision resnet50, ImageNet weights, head -> Linear(2048, 5)
  loss      BCEWithLogitsLoss (optional --pos-weight from the train split)
  input     224 x 224, resize + random hflip on train
  early stop on macro AUPRC (mean per-class average precision) with --patience
  outputs   <out>/best.pt, <out>/history.csv, <out>/metrics.json

Data: labels.csv plus splits/seed42.csv from this folder, joined on image_path.
Image pixels are not in the repo: pass --image-root or set FMD_IMAGE_ROOT to the
drop folder root; image paths inside labels.csv are relative to that root.
negatives_reliable rows can be excluded with --reliable-only.

Usage:
    python experiments/multilabel_resnet50/train.py --help
    python experiments/multilabel_resnet50/train.py --image-root <root> --epochs 30 --batch 32
    python experiments/multilabel_resnet50/train.py --smoke            # 2 steps, real images
    python experiments/multilabel_resnet50/train.py --smoke-synthetic   # 2 steps, random tensors
"""
import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_LABELS = HERE / "labels.csv"
DEFAULT_SPLIT = HERE / "splits" / "seed42.csv"
DEFAULT_OUT = HERE / "runs"
LP_TAGS = ["P1_COC", "P1_FL", "P1_ML", "P1_MPP", "P1_NL"]
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
SMOKE_STEPS = 2
SMOKE_IMAGES = 8


# ---------------------------------------------------------------- metrics (numpy only)
def average_precision(y_true, y_score):
    """AP for one class, sklearn average_precision_score semantics."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_score = np.asarray(y_score, dtype=np.float64)
    n_pos = y_true.sum()
    if n_pos == 0:
        return float("nan")  # class absent from this subset, excluded from macro
    order = np.argsort(-y_score, kind="stable")
    hits = y_true[order]
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(hits) + 1)
    recall = tp / n_pos
    delta = np.diff(np.concatenate([[0.0], recall]))
    return float((delta * precision).sum())


def macro_auprc(y_true, y_score):
    """Returns (macro value or nan, per-class list)."""
    per_class = [average_precision(y_true[:, j], y_score[:, j]) for j in range(y_true.shape[1])]
    finite = [v for v in per_class if not np.isnan(v)]
    macro = float(np.mean(finite)) if finite else float("nan")
    return macro, per_class


# ---------------------------------------------------------------- data loading
def load_dataset_rows(labels_path, split_path, split_name, reliable_only, split_column="split"):
    """Return list of dicts with path + target for one split."""
    with open(labels_path, newline="", encoding="utf-8") as fh:
        labels = {r["image_path"]: r for r in csv.DictReader(fh)}
    with open(split_path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r[split_column] == split_name]

    out = []
    missing_label_rows = 0
    for row in rows:
        lab = labels.get(row["image_path"])
        if lab is None:
            missing_label_rows += 1
            continue
        if reliable_only and lab.get("negatives_reliable", "1") not in ("1", "True", "true"):
            continue
        out.append({
            "image_path": row["image_path"],
            "target": [int(lab[t]) for t in LP_TAGS],
            "negatives_reliable": lab.get("negatives_reliable", "1") in ("1", "True", "true"),
        })
    if missing_label_rows:
        print("warning: %d split rows missing from labels.csv" % missing_label_rows)
    return out


def resolve_image(image_root, image_path):
    if not image_root:
        raise SystemExit(
            "image root not set: pass --image-root <dir> or set FMD_IMAGE_ROOT. "
            "Image pixels are not stored in the repo (see README).")
    p = Path(image_root) / image_path
    if not p.is_file():
        raise SystemExit("image not found: %s" % p)
    return p


class LensDataset:
    """Map-style dataset (plain class, no torch base class needed)."""

    def __init__(self, rows, image_root, imgsz, train, torch, transforms):
        self.rows = rows
        self.image_root = image_root
        self.imgsz = imgsz
        self.train = train
        self.torch = torch
        self.transforms = transforms

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        from PIL import Image
        row = self.rows[i]
        path = resolve_image(self.image_root, row["image_path"])
        with Image.open(path) as img:
            tensor = self.transforms(img.convert("RGB"))
        target = self.torch.tensor(row["target"], dtype=self.torch.float32)
        return tensor, target


def build_transforms(torch, torchvision, imgsz, train):
    ops = []
    if train:
        ops.append(torchvision.transforms.RandomHorizontalFlip(p=0.5))
    ops += [
        torchvision.transforms.Resize((imgsz, imgsz)),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize(IMAGENET_MEAN.tolist(), IMAGENET_STD.tolist()),
    ]
    return torchvision.transforms.Compose(ops)


# ---------------------------------------------------------------- training
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=str(DEFAULT_LABELS))
    ap.add_argument("--split", default=str(DEFAULT_SPLIT))
    ap.add_argument("--image-root", default=os.environ.get("FMD_IMAGE_ROOT", ""),
                    help="root directory the image_path column is relative to "
                         "(default: $FMD_IMAGE_ROOT)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--split-column", default="split",
                    help="column name in the split file holding train/test/val "
                         "(use split_named for the two-way 80/20 dataframe)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--optimizer", choices=("sgd", "adamw"), default="sgd",
                    help="sgd = SGD(lr, momentum=--momentum, nesterov=True), the "
                         "recipe shared with the lead's notebook builds")
    ap.add_argument("--momentum", type=float, default=0.9)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--patience", type=int, default=5, help="early stop patience on macro AUPRC")
    ap.add_argument("--weights", default="IMAGENET1K_V2",
                    help="torchvision weights name, or 'none' for random init")
    ap.add_argument("--reliable-only", action="store_true",
                    help="drop rows with negatives_reliable = False from every split")
    ap.add_argument("--pos-weight", action="store_true",
                    help="set per-class BCE pos_weight from the train split")
    ap.add_argument("--no-amp", action="store_true", help="disable mixed precision")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="", help="cuda|cpu|mps, default: auto")
    ap.add_argument("--smoke", action="store_true",
                    help="run %d optimizer steps on up to %d real train images and exit"
                         % (SMOKE_STEPS, SMOKE_IMAGES))
    ap.add_argument("--smoke-synthetic", action="store_true",
                    help="run %d optimizer steps on random tensors (no image files needed)"
                         % SMOKE_STEPS)
    return ap.parse_args(argv)


def import_torch():
    try:
        import torch
        import torchvision
    except ImportError as exc:
        raise SystemExit(
            "torch/torchvision are required for training (%s).\n"
            "Install them first, e.g. `uv pip install torch torchvision`." % exc)
    return torch, torchvision


def pick_device(torch, requested):
    if requested:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(torch, seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_model(torch, torchvision, weights_name, n_classes):
    """ResNet50 with the classifier head replaced. weights_name is a
    torchvision ResNet50_Weights member (e.g. IMAGENET1K_V2) or none/random."""
    enum = torchvision.models.ResNet50_Weights
    name = weights_name.strip()
    if name.lower() in ("none", "random", ""):
        weights = None
    else:
        try:
            weights = enum[name] if name.upper() == "DEFAULT" else enum[name.upper()]
        except KeyError:
            raise SystemExit("unknown --weights %r, choose one of %s or none"
                             % (weights_name, ", ".join(enum.__members__)))
    model = torchvision.models.resnet50(weights=weights)
    model.fc = torch.nn.Linear(model.fc.in_features, n_classes)
    return model


def amp_scaler(torch, enabled):
    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=enabled)


def amp_autocast(torch, enabled):
    try:
        return torch.amp.autocast("cuda", enabled=enabled)
    except (AttributeError, TypeError):
        return torch.cuda.amp.autocast(enabled=enabled)


def run_smoke(args, torch, torchvision, device):
    """2 optimizer steps, either on real train images or on random tensors."""
    set_seed(torch, args.seed)
    model = build_model(torch, torchvision, args.weights, len(LP_TAGS)).to(device)
    criterion = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    if args.smoke_synthetic:
        def batch():
            x = torch.randn(min(SMOKE_IMAGES, args.batch), 3, args.imgsz, args.imgsz, device=device)
            y = (torch.rand(x.shape[0], len(LP_TAGS), device=device) < 0.4).float()
            return x, y
        print("smoke: synthetic random tensors (no image files touched)")
    else:
        rows = load_dataset_rows(args.labels, args.split, "train", args.reliable_only,
                                 args.split_column)
        if not rows:
            raise SystemExit("no train rows found, run build_labels.py and make_splits.py first")
        rows = rows[:SMOKE_IMAGES]
        tf = build_transforms(torch, torchvision, args.imgsz, train=True)
        dataset = LensDataset(rows, args.image_root, args.imgsz, True, torch, tf)
        loader = torch.utils.data.DataLoader(dataset, batch_size=min(SMOKE_IMAGES, len(rows)),
                                             shuffle=False, num_workers=0)
        iterator = iter(loader)
        def batch():
            try:
                return next(iterator)
            except StopIteration:
                return next(iter(loader))
        print("smoke: %d real train images from %s" % (len(rows), args.image_root))

    model.train()
    for step in range(1, SMOKE_STEPS + 1):
        x, y = batch()
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        print("  step %d/%d loss=%.4f logits_shape=%s"
              % (step, SMOKE_STEPS, float(loss.detach()), tuple(logits.shape)))
    print("smoke: OK, %d optimizer steps executed on %s" % (SMOKE_STEPS, device))
    return 0


def build_optimizer(torch, args, params):
    if args.optimizer == "sgd":
        return torch.optim.SGD(params, lr=args.lr, momentum=args.momentum,
                               nesterov=True, weight_decay=args.weight_decay)
    return torch.optim.AdamW(params, lr=args.lr, weight_decay=args.weight_decay)


def collect_predictions(model, loader, device, torch, amp_enabled):
    """Run inference over a loader, return (y_true, y_score) numpy arrays."""
    model.eval()
    scores, truths = [], []
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            with amp_autocast(torch, amp_enabled):
                logits = model(x)
            scores.append(logits.float().cpu().numpy())
            truths.append(y.cpu().numpy())
    y_score = np.concatenate(scores) if scores else np.zeros((0, len(LP_TAGS)), dtype=np.float32)
    y_true = np.concatenate(truths) if truths else np.zeros((0, len(LP_TAGS)), dtype=np.int64)
    return y_true, y_score


def full_metrics(y_true, y_score, threshold=0.5):
    """Threshold metrics + AUPRC per class and macro. Returns a dict; raw
    predictions are dumped separately so any metric can be recomputed later."""
    eps = 1e-12
    y_pred = (y_score >= threshold).astype(np.int64)
    out = {"threshold": threshold}
    per_class = {}
    f1s, aps = [], []
    for j, tag in enumerate(LP_TAGS):
        t, p = y_true[:, j], y_pred[:, j]
        tp = int(((t == 1) & (p == 1)).sum())
        fp = int(((t == 0) & (p == 1)).sum())
        fn = int(((t == 1) & (p == 0)).sum())
        tn = int(((t == 0) & (p == 0)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        ap = average_precision(y_true[:, j], y_score[:, j])
        support = int(t.sum())
        per_class[tag] = {
            "support": support,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(prec, 5),
            "recall": round(rec, 5),
            "f1": round(f1, 5),
            "auprc": None if np.isnan(ap) else round(ap, 5),
        }
        if support:
            f1s.append(f1)
        if not np.isnan(ap):
            aps.append(ap)
    n, k = y_true.shape
    out["per_class"] = per_class
    out["macro_f1"] = round(float(np.mean(f1s)), 5) if f1s else None
    out["macro_auprc"] = round(float(np.mean(aps)), 5) if aps else None
    out["micro_precision"] = round(sum(pc["tp"] for pc in per_class.values()) /
                                   max(sum(pc["tp"] + pc["fp"] for pc in per_class.values()), eps), 5)
    out["micro_recall"] = round(sum(pc["tp"] for pc in per_class.values()) /
                                max(sum(pc["tp"] + pc["fn"] for pc in per_class.values()), eps), 5)
    out["hamming_loss"] = round(float((y_true != y_pred).sum()) / (n * k), 5)
    out["exact_match_ratio"] = round(float((y_true == y_pred).all(axis=1).mean()), 5)
    return out


def run_training(args, torch, torchvision, device):
    set_seed(torch, args.seed)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_rows = load_dataset_rows(args.labels, args.split, "train", args.reliable_only,
                                   args.split_column)
    # val is optional: the frozen 80/20 decision is a fixed-epoch two-way run
    val_rows = load_dataset_rows(args.labels, args.split, "val", args.reliable_only,
                                 args.split_column)
    test_rows = load_dataset_rows(args.labels, args.split, "test", args.reliable_only,
                                  args.split_column)
    if not train_rows:
        raise SystemExit("empty train split, check the split file and --split-column")
    print("rows: train=%d val=%d test=%d (reliable_only=%s, split_column=%s)"
          % (len(train_rows), len(val_rows), len(test_rows), args.reliable_only,
             args.split_column))

    y_train = np.array([r["target"] for r in train_rows], dtype=np.int64)
    pos_weight = None
    if args.pos_weight:
        n = len(y_train)
        pos = y_train.sum(axis=0)
        pos_weight = torch.tensor((n - pos) / np.maximum(pos, 1), dtype=torch.float32)
        print("pos_weight: %s" % np.round(pos_weight.numpy(), 2).tolist())
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device) if pos_weight is not None else None)

    model = build_model(torch, torchvision, args.weights, len(LP_TAGS)).to(device)
    optimizer = build_optimizer(torch, args, model.parameters())
    use_amp = (device.type == "cuda") and not args.no_amp
    scaler = amp_scaler(torch, use_amp)

    train_tf = build_transforms(torch, torchvision, args.imgsz, train=True)
    eval_tf = build_transforms(torch, torchvision, args.imgsz, train=False)
    train_loader = torch.utils.data.DataLoader(
        LensDataset(train_rows, args.image_root, args.imgsz, True, torch, train_tf),
        batch_size=args.batch, shuffle=True, num_workers=args.workers, drop_last=False)
    val_loader = None
    if val_rows:
        val_loader = torch.utils.data.DataLoader(
            LensDataset(val_rows, args.image_root, args.imgsz, False, torch, eval_tf),
            batch_size=args.batch, shuffle=False, num_workers=args.workers)

    history = []
    best_macro, best_epoch, bad_epochs = -1.0, -1, 0
    best_state = None
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        running, seen = 0.0, 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad(set_to_none=True)
            with amp_autocast(torch, use_amp):
                logits = model(x)
                loss = criterion(logits, y)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running += float(loss.detach()) * x.shape[0]
            seen += x.shape[0]
        row = {
            "epoch": epoch,
            "train_loss": running / max(seen, 1),
            "val_macro_auprc": None,
            "seconds": round(time.time() - t0, 1),
        }
        if val_loader is not None:
            v_true, v_score = collect_predictions(model, val_loader, device, torch, use_amp)
            val_macro, val_per_class = macro_auprc(v_true, v_score)
            row["val_macro_auprc"] = None if np.isnan(val_macro) else round(val_macro, 5)
            for j, tag in enumerate(LP_TAGS):
                row["val_auprc_" + tag] = None if np.isnan(val_per_class[j]) else round(val_per_class[j], 5)
        history.append(row)
        print("epoch %2d loss=%.4f val_macro_auprc=%s (%.1fs)"
              % (epoch, row["train_loss"], row["val_macro_auprc"], row["seconds"]))

        if val_loader is not None:
            if not np.isnan(val_macro) and val_macro > best_macro + 1e-6:
                best_macro, best_epoch, bad_epochs = float(val_macro), epoch, 0
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                torch.save({"model": best_state, "epoch": epoch, "macro_auprc": best_macro,
                            "classes": LP_TAGS, "imgsz": args.imgsz,
                            "weights": args.weights, "args": vars(args)},
                           out_dir / "best.pt")
            else:
                bad_epochs += 1
                if bad_epochs >= args.patience:
                    print("early stop at epoch %d (best epoch %d, macro AUPRC %.5f)"
                          % (epoch, best_epoch, best_macro))
                    break

    if not history:
        print("no epochs ran, check --epochs")
        return 1
    with open(out_dir / "history.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)

    # checkpoint: best-on-val when a val set exists, otherwise final epoch
    if best_state is None:
        best_epoch = history[-1]["epoch"]
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        torch.save({"model": best_state, "epoch": best_epoch, "macro_auprc": None,
                    "classes": LP_TAGS, "imgsz": args.imgsz,
                    "weights": args.weights, "args": vars(args)},
                   out_dir / "best.pt")
    model.load_state_dict(best_state)

    result = {
        "best_epoch": best_epoch,
        "checkpoint": "best_on_val" if val_rows else "final_epoch_fixed_schedule",
        "rows": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
        "reliable_only": args.reliable_only,
        "pos_weight": bool(args.pos_weight),
        "optimizer": args.optimizer,
        "config": {k: v for k, v in vars(args).items()},
    }
    if val_rows:
        v_true, v_score = collect_predictions(model, val_loader, device, torch, use_amp)
        result["val_metrics"] = full_metrics(v_true, v_score)
    for name, rows in (("test", test_rows),):
        if not rows:
            continue
        loader = torch.utils.data.DataLoader(
            LensDataset(rows, args.image_root, args.imgsz, False, torch, eval_tf),
            batch_size=args.batch, shuffle=False, num_workers=args.workers)
        t_true, t_score = collect_predictions(model, loader, device, torch, use_amp)
        result[name + "_metrics"] = full_metrics(t_true, t_score)
        # raw predictions: any metric she asks for later is recomputable without a re-run
        np.savez_compressed(out_dir / ("test_predictions.npz"),
                            y_true=t_true.astype(np.int8), y_score=t_score.astype(np.float32),
                            paths=np.array([r["image_path"] for r in rows]),
                            classes=np.array(LP_TAGS))
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("wrote %s, %s, %s" % (out_dir / "best.pt", out_dir / "history.csv", out_dir / "metrics.json"))
    return 0


def main(argv=None):
    args = parse_args(argv)
    torch, torchvision = import_torch()
    device = pick_device(torch, args.device)
    print("device: %s (cuda available: %s)" % (device, torch.cuda.is_available()))
    if args.smoke or args.smoke_synthetic:
        return run_smoke(args, torch, torchvision, device)
    return run_training(args, torch, torchvision, device)


if __name__ == "__main__":
    sys.exit(main())
