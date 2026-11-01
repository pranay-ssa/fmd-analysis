"""Standalone inference for the lens-presentation defect classifier.

Runs one image through the trained model and prints a score (0 to 1) for each
class. A class is flagged when its score passes the threshold set in
config.json.

Usage:
    python predict.py                 (uses config.json as-is)
    python predict.py --config my_config.json

Requires: torch, torchvision, pillow (see requirements.txt).
"""
import argparse
import json
import sys
from pathlib import Path

import torch
import torchvision
from PIL import Image
from torchvision import transforms


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for key in ("checkpoint", "image_path", "classes"):
        if key not in cfg:
            sys.exit("config is missing the '%s' entry" % key)
    return cfg


def build_model(n_classes):
    model = torchvision.models.resnet50()
    model.fc = torch.nn.Linear(model.fc.in_features, n_classes)
    return model


def main():
    ap = argparse.ArgumentParser(description="Score one image for lens-presentation defects.")
    ap.add_argument("--config", default="config.json", help="path to the config file")
    args = ap.parse_args()

    cfg = load_config(args.config)
    ckpt = Path(cfg["checkpoint"])
    image_path = Path(cfg["image_path"])
    if not ckpt.exists():
        sys.exit("checkpoint not found: %s (set 'checkpoint' in the config file)" % ckpt)
    if not image_path.exists():
        sys.exit("image not found: %s (set 'image_path' in the config file)" % image_path)

    classes = cfg["classes"]
    model = build_model(len(classes))
    state = torch.load(ckpt, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    tfm = transforms.Compose([
        transforms.Resize((int(cfg.get("input_size", 224)),) * 2),
        transforms.ToTensor(),
        transforms.Normalize(cfg.get("mean", [0.485, 0.456, 0.406]),
                             cfg.get("std", [0.229, 0.224, 0.225])),
    ])
    x = tfm(Image.open(image_path).convert("RGB")).unsqueeze(0)

    with torch.no_grad():
        scores = torch.sigmoid(model(x))[0].tolist()

    print("image: %s" % image_path)
    print("checkpoint: %s" % ckpt)
    print("")
    print("%-24s %-28s %8s  %s" % ("code", "class", "score", "flag"))
    for cls, s in zip(classes, scores):
        thr = float(cls.get("threshold", 0.5))
        flag = "FLAGGED" if s >= thr else "-"
        print("%-24s %-28s %8.4f  %s" % (cls["code"], cls["name"], s, flag))


if __name__ == "__main__":
    main()
