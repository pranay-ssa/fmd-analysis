#!/usr/bin/env python3
"""Multi-label ResNet50 trainer for the 5 lens-presentation tags.

Recipe (see DESIGN.md) and the architecture set live here:
  base      torchvision resnet50, ImageNet weights, head -> Linear(2048, 5)
  --arch    resnet50 (that baseline) or one of the four architectures of
            notebooks/FMD_ResNet50Architectures.ipynb, ported to PyTorch:
              resnet50_inception           notebook Arch 1, MultiLevel MultiScale
              resnet50_se                  notebook Arch 2, MultiLevel Attention (SE)
              resnet50_inception_attention notebook Arch 3, Inception + branch attention
              resnet50_inception_refine    notebook Arch 4, Inception + refined decode
            The multi-label task keeps every architecture's connectivity, filter
            counts, taps and head except the last layer: Linear(*, 5) with no
            softmax, because the loss is BCEWithLogitsLoss over 5 independent tags.
  loss      BCEWithLogitsLoss (optional --pos-weight from the train split)
  input     224 x 224, resize + random hflip on train
  early stop on macro AUPRC (mean per-class average precision) with --patience
  outputs   <out>/best.pt, <out>/history.csv, <out>/metrics.json
            metrics.json carries an inference/training timing block. The
            inference headline is a COLD pass: the first pass over the test
            loader with no warmup of any kind, exactly the no-warmup convention
            this project uses. A steady-state median is reported next to it for
            context and is labelled as such.

Data: labels.csv plus splits/seed42.csv from this folder, joined on image_path.
Image pixels are not in the repo: pass --image-root or set FMD_IMAGE_ROOT to the
drop folder root; image paths inside labels.csv are relative to that root.
negatives_reliable rows can be excluded with --reliable-only.

Usage:
    python experiments/multilabel_resnet50/train.py --help
    python experiments/multilabel_resnet50/train.py --image-root <root> --epochs 30 --batch 32
    python experiments/multilabel_resnet50/train.py --arch resnet50_inception --image-root <root>
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

# ---------------------------------------------------------------- architecture set
# Ports of the four architectures in notebooks/FMD_ResNet50Architectures.ipynb, plus
# the plain ResNet50 baseline they are measured against. Connectivity, filter counts,
# taps, fusion widths and the fully connected head are the notebook's; only the final
# layer differs (Linear(., 5), no softmax) because this task is multi-label.
ARCH_RESNET50 = "resnet50"
ARCH_MULTISCALE = "resnet50_inception"                   # notebook Arch 1, MultiLevel MultiScale
ARCH_MULTILVL_ATTENTION = "resnet50_se"                  # notebook Arch 2, MultiLevel Attention
ARCH_INCEPTION_ATTENTION = "resnet50_inception_attention"  # notebook Arch 3
ARCH_INCEPTION_REFINE = "resnet50_inception_refine"        # notebook Arch 4
ARCHS = (ARCH_RESNET50, ARCH_MULTISCALE, ARCH_MULTILVL_ATTENTION,
         ARCH_INCEPTION_ATTENTION, ARCH_INCEPTION_REFINE)
ARCH_LABELS = {
    ARCH_RESNET50: "ResNet50 (baseline)",
    ARCH_MULTISCALE: "ResNet50 MultiLevel MultiScale (notebook Architecture 1)",
    ARCH_MULTILVL_ATTENTION: "ResNet50 MultiLevel Attention SE (notebook Architecture 2)",
    ARCH_INCEPTION_ATTENTION: "ResNet50 Inception + branch attention (notebook Architecture 3)",
    ARCH_INCEPTION_REFINE: "ResNet50 Inception + refined decode (notebook Architecture 4)",
}

# Inception branch filter counts, per tap (the notebook's l3 / l4 / l5 dictionaries).
INC_FILTERS = {
    "l3": {"branch1": 64, "branch2_reduce": 96, "branch2_out": 104,
           "branch3_reduce": 32, "branch3_out": 172, "branch4_out": 172},
    "l4": {"branch1": 128, "branch2_reduce": 192, "branch2_out": 208,
           "branch3_reduce": 64, "branch3_out": 344, "branch4_out": 344},
    "l5": {"branch1": 256, "branch2_reduce": 384, "branch2_out": 416,
           "branch3_reduce": 128, "branch3_out": 688, "branch4_out": 688},
}
TAP_CHANNELS = {"l3": 512, "l4": 1024, "l5": 2048}   # conv3_block4_add, conv4_block6_add, conv5_block3_add
FUSION_CHANNELS = 512 + 1024 + 2048
TAP_NAMES = "conv3_block4_add+conv4_block6_add+conv5_block3_add"


def _arch_modules(torch):
    """Build the module classes the notebook architectures need.

    Defined in a factory so torch stays a lazy import: everything above this point
    runs without torch installed.
    """
    nn = torch.nn

    def conv(c_in, c_out, kernel, pad):
        """Keras Conv2D(k, padding='same', activation='relu') at stride 1, with bias."""
        return nn.Sequential(nn.Conv2d(c_in, c_out, kernel, padding=pad), nn.ReLU(inplace=True))

    class SEBlock(nn.Module):
        """Squeeze-and-Excitation: GAP -> FC(ch//16, relu) -> FC(ch, sigmoid) -> scale."""

        def __init__(self, channels, reduction=16):
            super().__init__()
            self.fc1 = nn.Linear(channels, channels // reduction)
            self.fc2 = nn.Linear(channels // reduction, channels)

        def forward(self, x):
            w = x.mean(dim=(2, 3))
            w = torch.sigmoid(self.fc2(torch.relu(self.fc1(w))))
            return x * w.unsqueeze(-1).unsqueeze(-1)

    class InceptionBlock(nn.Module):
        """GoogLeNet-style Inception block: 1x1 | 1x1-3x3 | 1x1-5x5 | pool-1x1.

        Spatial size is preserved. attention=True adds SE attention after every
        branch (notebook Architecture 3).
        """

        def __init__(self, c_in, filters, attention=False):
            super().__init__()
            self.branch1 = conv(c_in, filters["branch1"], 1, 0)
            self.branch2 = nn.Sequential(conv(c_in, filters["branch2_reduce"], 1, 0),
                                         conv(filters["branch2_reduce"], filters["branch2_out"], 3, 1))
            self.branch3 = nn.Sequential(conv(c_in, filters["branch3_reduce"], 1, 0),
                                         conv(filters["branch3_reduce"], filters["branch3_out"], 5, 2))
            self.branch4 = nn.Sequential(nn.MaxPool2d(3, stride=1, padding=1),
                                         conv(c_in, filters["branch4_out"], 1, 0))
            self.attention = attention
            if attention:
                self.se1 = SEBlock(filters["branch1"])
                self.se2 = SEBlock(filters["branch2_out"])
                self.se3 = SEBlock(filters["branch3_out"])
                self.se4 = SEBlock(filters["branch4_out"])
            self.out_channels = (filters["branch1"] + filters["branch2_out"] +
                                 filters["branch3_out"] + filters["branch4_out"])

        def forward(self, x):
            branches = [self.branch1(x), self.branch2(x), self.branch3(x), self.branch4(x)]
            if self.attention:
                branches = [self.se1(branches[0]), self.se2(branches[1]),
                            self.se3(branches[2]), self.se4(branches[3])]
            return torch.cat(branches, dim=1)

    class Head(nn.Module):
        """GAP -> BN -> 2048 (dropout 0.3) -> 1024 (dropout 0.3) -> n_classes."""

        def __init__(self, c_in, n_classes, dropout=0.3):
            super().__init__()
            self.bn = nn.BatchNorm1d(c_in)
            self.fc1 = nn.Linear(c_in, 2048)
            self.do1 = nn.Dropout(dropout)
            self.fc2 = nn.Linear(2048, 1024)
            self.do2 = nn.Dropout(dropout)
            self.out = nn.Linear(1024, n_classes)

        def forward(self, x):
            x = x.mean(dim=(2, 3))
            x = self.bn(x)
            x = self.do1(torch.relu(self.fc1(x)))
            x = self.do2(torch.relu(self.fc2(x)))
            return self.out(x)

    class ResNetTaps(nn.Module):
        """torchvision ResNet50 split at the notebook's three taps.

        The notebook reads conv3_block4_add / conv4_block6_add / conv5_block3_add,
        which in Keras are the residual Add layers, so their tensors sit BEFORE the
        block's final ReLU. torchvision applies that ReLU inside the block, so a
        pre-hook on the last block's relu module captures the same tensor.
        `used_hooks` records whether that worked; if torchvision ever changes its
        block forwards the fallback is the post-ReLU stage output, and a smoke test
        reports the mode so a silent change is visible.
        """

        def __init__(self, resnet):
            super().__init__()
            self.stem = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu, resnet.maxpool)
            self.layer1 = resnet.layer1
            self.layer2 = resnet.layer2   # conv3_block4_add, 28x28x512
            self.layer3 = resnet.layer3   # conv4_block6_add, 14x14x1024
            self.layer4 = resnet.layer4   # conv5_block3_add, 7x7x2048
            self._tap = {}
            self.used_hooks = False
            for key, stage in (("l3", self.layer2), ("l4", self.layer3), ("l5", self.layer4)):
                stage[-1].relu.register_forward_pre_hook(self._probe(key))

        def _probe(self, key):
            def hook(_module, inputs):
                self._tap[key] = inputs[0]
            return hook

        def forward(self, x):
            self._tap = {}
            x = self.layer1(self.stem(x))
            out3 = self.layer2(x)
            out4 = self.layer3(out3)
            out5 = self.layer4(out4)
            self.used_hooks = len(self._tap) == 3
            return (self._tap.get("l3", out3), self._tap.get("l4", out4), self._tap.get("l5", out5))

    class MultiScaleNet(nn.Module):
        """Notebook Architecture 1: Inception blocks on all three taps, the 28x28 and
        7x7 paths brought to 14x14, fused by concatenation (3584 channels)."""

        def __init__(self, resnet, n_classes):
            super().__init__()
            self.taps = ResNetTaps(resnet)
            self.i3 = InceptionBlock(TAP_CHANNELS["l3"], INC_FILTERS["l3"])
            self.i4 = InceptionBlock(TAP_CHANNELS["l4"], INC_FILTERS["l4"])
            self.i5 = InceptionBlock(TAP_CHANNELS["l5"], INC_FILTERS["l5"])
            self.down3 = nn.Sequential(nn.LeakyReLU(0.1, inplace=True), nn.MaxPool2d(2))
            self.up5 = nn.Sequential(nn.LeakyReLU(0.1, inplace=True),
                                     nn.ConvTranspose2d(2048, 2048, 2, stride=2),
                                     nn.BatchNorm2d(2048),
                                     nn.LeakyReLU(0.1, inplace=True))
            self.head = Head(FUSION_CHANNELS, n_classes)

        def forward(self, x):
            l3, l4, l5 = self.taps(x)
            x3 = self.down3(self.i3(l3))
            x4 = self.i4(l4)
            x5 = self.up5(self.i5(l5))
            return self.head(torch.cat([x3, x4, x5], dim=1))

    class MultiLevelAttentionNet(nn.Module):
        """Notebook Architecture 2: SE attention on each tap (no Inception), same
        resize, fusion and head as Architecture 1."""

        def __init__(self, resnet, n_classes):
            super().__init__()
            self.taps = ResNetTaps(resnet)
            self.se3 = SEBlock(TAP_CHANNELS["l3"])
            self.se4 = SEBlock(TAP_CHANNELS["l4"])
            self.se5 = SEBlock(TAP_CHANNELS["l5"])
            self.down3 = nn.Sequential(nn.LeakyReLU(0.1, inplace=True), nn.MaxPool2d(2))
            self.up5 = nn.Sequential(nn.LeakyReLU(0.1, inplace=True),
                                     nn.ConvTranspose2d(2048, 2048, 2, stride=2),
                                     nn.BatchNorm2d(2048),
                                     nn.LeakyReLU(0.1, inplace=True))
            self.head = Head(FUSION_CHANNELS, n_classes)

        def forward(self, x):
            l3, l4, l5 = self.taps(x)
            x3 = self.down3(self.se3(l3))
            x4 = self.se4(l4)
            x5 = self.up5(self.se5(l5))
            return self.head(torch.cat([x3, x4, x5], dim=1))

    class InceptionAttentionNet(MultiScaleNet):
        """Notebook Architecture 3: Architecture 1 with SE attention inside every
        Inception branch."""

        def __init__(self, resnet, n_classes):
            super().__init__(resnet, n_classes)
            self.i3 = InceptionBlock(TAP_CHANNELS["l3"], INC_FILTERS["l3"], attention=True)
            self.i4 = InceptionBlock(TAP_CHANNELS["l4"], INC_FILTERS["l4"], attention=True)
            self.i5 = InceptionBlock(TAP_CHANNELS["l5"], INC_FILTERS["l5"], attention=True)

    class InceptionRefineNet(MultiScaleNet):
        """Notebook Architecture 4: Architecture 1 with the L5 path decoded by bicubic
        upsampling, a depthwise 3x3 refinement and a 1x1 channel mixer (no transposed
        convolution)."""

        def __init__(self, resnet, n_classes):
            super().__init__(resnet, n_classes)
            self.up5 = nn.Sequential(nn.LeakyReLU(0.1, inplace=True),
                                     nn.Upsample(scale_factor=2, mode="bicubic", align_corners=False),
                                     nn.Conv2d(2048, 2048, 3, padding=1, groups=2048, bias=False),
                                     nn.BatchNorm2d(2048),
                                     nn.LeakyReLU(0.1, inplace=True),
                                     nn.Conv2d(2048, 2048, 1, bias=False),
                                     nn.BatchNorm2d(2048),
                                     nn.LeakyReLU(0.1, inplace=True))

    return {
        ARCH_MULTISCALE: MultiScaleNet,
        ARCH_MULTILVL_ATTENTION: MultiLevelAttentionNet,
        ARCH_INCEPTION_ATTENTION: InceptionAttentionNet,
        ARCH_INCEPTION_REFINE: InceptionRefineNet,
    }


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
    ap.add_argument("--arch", default=ARCH_RESNET50, choices=list(ARCHS),
                    help="model architecture; %s is the plain baseline every other "
                         "row is measured against (default: %s)" % (ARCH_RESNET50, ARCH_RESNET50))
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


def resolve_weights(torchvision, weights_name):
    """--weights name -> a torchvision ResNet50_Weights member, or None for random."""
    enum = torchvision.models.ResNet50_Weights
    name = weights_name.strip()
    if name.lower() in ("none", "random", ""):
        return None
    try:
        return enum[name] if name.upper() == "DEFAULT" else enum[name.upper()]
    except KeyError:
        raise SystemExit("unknown --weights %r, choose one of %s or none"
                         % (weights_name, ", ".join(enum.__members__)))


def count_params(model):
    return sum(p.numel() for p in model.parameters())


def build_model(torch, torchvision, weights_name, n_classes, arch=ARCH_RESNET50):
    """Build one of ARCHS. weights_name is a torchvision ResNet50_Weights member
    (e.g. IMAGENET1K_V2) or none/random.

    The plain baseline is exactly the model the 2026-09-28 run used. The four
    notebook architectures share its ImageNet-initialised ResNet50 trunk, so a
    difference between two of them is the architecture and not the initialisation.
    """
    if arch not in ARCHS:
        raise SystemExit("unknown --arch %r, choose one of %s" % (arch, ", ".join(ARCHS)))
    weights = resolve_weights(torchvision, weights_name)
    resnet = torchvision.models.resnet50(weights=weights)
    if arch == ARCH_RESNET50:
        resnet.fc = torch.nn.Linear(resnet.fc.in_features, n_classes)
        model = resnet
    else:
        model = _arch_modules(torch)[arch](resnet, n_classes)
    model.arch = arch
    return model


def taps_mode(model):
    """Which tensor the notebook taps resolved to: the residual Add output (the
    notebook's conv*_add layers) or, if torchvision's block forward changed, the
    post-ReLU stage output."""
    taps = getattr(model, "taps", None)
    if taps is None:
        return "n/a (baseline has no taps)"
    return "pre-activation residual add" if taps.used_hooks else "POST-RELU STAGE OUTPUT (hook missed)"


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
    model = build_model(torch, torchvision, args.weights, len(LP_TAGS), args.arch).to(device)
    print("arch: %s (%s) params=%d"
          % (args.arch, ARCH_LABELS[args.arch], count_params(model)))
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
    # taps_mode can only be read after a forward pass: it reports whether the
    # residual-add pre-hook on each stage's last block actually captured the tap
    print("taps after %d forward passes: %s" % (SMOKE_STEPS, taps_mode(model)))
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


def sync_device(torch, device):
    if device.type == "cuda":
        torch.cuda.synchronize()


def inference_pass(model, loader, device, torch, amp_enabled, collect=True):
    """One pass over a loader, timed from the first batch with NO warmup of any kind.

    This is the project's no-warmup convention: whatever the first pass costs is
    inside the number. `collect` also returns the predictions, so the timed cold
    pass is the same pass the metrics come from and no extra pass is invented.
    """
    model.eval()
    scores, truths = [], []
    images = 0
    first_batch_ms = None
    sync_device(torch, device)
    t0 = time.perf_counter()
    with torch.no_grad():
        for i, (x, y) in enumerate(loader):
            t_batch = time.perf_counter()
            x = x.to(device)
            with amp_autocast(torch, amp_enabled):
                logits = model(x)
            if i == 0:
                sync_device(torch, device)
                first_batch_ms = (time.perf_counter() - t_batch) * 1000.0
            if collect:
                scores.append(logits.float().cpu().numpy())
                truths.append(y.numpy())
            images += x.shape[0]
    sync_device(torch, device)
    elapsed = time.perf_counter() - t0
    out = {
        "seconds": elapsed,
        "images": images,
        "ms_per_image": elapsed * 1000.0 / max(images, 1),
        "first_batch_ms": first_batch_ms,
    }
    if collect:
        out["y_score"] = np.concatenate(scores) if scores else np.zeros((0, len(LP_TAGS)), dtype=np.float32)
        out["y_true"] = np.concatenate(truths) if truths else np.zeros((0, len(LP_TAGS)), dtype=np.int64)
    return out


def model_only_ms(model, batch, device, torch, amp_enabled, warm_repeats=10, timed_repeats=10):
    """Per-image milliseconds of the forward call alone, on one batch held in GPU
    memory, after `warm_repeats` warmup passes. Reported for context only: the
    headline inference numbers above are the no-warmup ones."""
    x = batch.to(device)
    model.eval()
    with torch.no_grad():
        for _ in range(warm_repeats):
            with amp_autocast(torch, amp_enabled):
                model(x)
    sync_device(torch, device)
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(timed_repeats):
            with amp_autocast(torch, amp_enabled):
                model(x)
    sync_device(torch, device)
    return (time.perf_counter() - t0) * 1000.0 / (timed_repeats * x.shape[0])


def device_label(torch, device):
    if device.type == "cuda":
        try:
            return torch.cuda.get_device_name(device)
        except Exception:
            return "cuda"
    return str(device)


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

    model = build_model(torch, torchvision, args.weights, len(LP_TAGS), args.arch).to(device)
    print("arch: %s (%s)" % (args.arch, ARCH_LABELS[args.arch]))
    print("params: %d, taps: %s" % (count_params(model), taps_mode(model)))
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

    if args.arch != ARCH_RESNET50 and not getattr(model, "taps", None).used_hooks:
        print("WARNING: the residual-add tap pre-hook did not fire, so the taps are the "
              "post-ReLU stage outputs and are NOT what the notebook reads. Do not trust "
              "this row's architecture claim.")
    result = {
        "best_epoch": best_epoch,
        "checkpoint": "best_on_val" if val_rows else "final_epoch_fixed_schedule",
        "arch": args.arch,
        "arch_label": ARCH_LABELS[args.arch],
        "params_total": count_params(model),
        "taps": taps_mode(model),
        "rows": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
        "reliable_only": args.reliable_only,
        "pos_weight": bool(args.pos_weight),
        "optimizer": args.optimizer,
        "config": {k: v for k, v in vars(args).items()},
    }
    if val_rows:
        v_true, v_score = collect_predictions(model, val_loader, device, torch, use_amp)
        result["val_metrics"] = full_metrics(v_true, v_score)
    train_seconds = sum(h["seconds"] for h in history)
    timing = {
        "device": device_label(torch, device),
        "batch": args.batch,
        "amp": bool(use_amp),
        "warmup_used": False,
        "eval_pass": "test" if test_rows else "val",
        "images": 0,
        "train_seconds_total": round(train_seconds, 1),
        "train_seconds_per_epoch_mean": round(train_seconds / max(len(history), 1), 3),
        "note": ("the cold numbers are the first pass over the test loader after the best "
                 "checkpoint was restored: no warmup of any kind, so one-time costs are "
                 "inside them. The steady numbers are repeats of the same pass afterwards."),
    }
    if test_rows:
        test_loader = torch.utils.data.DataLoader(
            LensDataset(test_rows, args.image_root, args.imgsz, False, torch, eval_tf),
            batch_size=args.batch, shuffle=False, num_workers=args.workers)
        # timed cold pass, no warmup: its predictions are the ones scored below
        cold = inference_pass(model, test_loader, device, torch, use_amp, collect=True)
        t_true, t_score = cold["y_true"], cold["y_score"]
        steady = [inference_pass(model, test_loader, device, torch, use_amp, collect=False)
                  for _ in range(3)]
        steady_ms = [s["ms_per_image"] for s in steady]
        try:
            probe_batch = next(iter(test_loader))[0]
            m_only = model_only_ms(model, probe_batch, device, torch, use_amp)
        except StopIteration:
            m_only = None
        timing.update({
            "images": cold["images"],
            "inference_ms_per_image_cold": round(cold["ms_per_image"], 3),
            "inference_total_seconds_cold": round(cold["seconds"], 4),
            "inference_first_batch_ms_cold": round(cold["first_batch_ms"], 3),
            "inference_ms_per_image_steady_median": round(float(np.median(steady_ms)), 3),
            "inference_ms_per_image_steady_repeats": [round(v, 3) for v in steady_ms],
            "model_only_ms_per_image_warm": None if m_only is None else round(m_only, 3),
        })
        result["test_metrics"] = full_metrics(t_true, t_score)
        # raw predictions: any metric she asks for later is recomputable without a re-run
        np.savez_compressed(out_dir / ("test_predictions.npz"),
                            y_true=t_true.astype(np.int8), y_score=t_score.astype(np.float32),
                            paths=np.array([r["image_path"] for r in test_rows]),
                            classes=np.array(LP_TAGS))
    result["timing"] = timing
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("timing: cold %.3f ms/img (first pass, no warmup), steady %.3f ms/img, train %.1f s total"
          % (timing.get("inference_ms_per_image_cold", float("nan")),
             timing.get("inference_ms_per_image_steady_median", float("nan")),
             timing["train_seconds_total"]))
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
