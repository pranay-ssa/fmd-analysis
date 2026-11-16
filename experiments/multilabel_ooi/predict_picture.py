"""One picture in, one verdict out, on the line's clock.

WHAT THIS IS
------------
The deployed path. A picture is read, the multi-label head scores its nineteen
columns, and the pass/fail block turns those scores into a verdict:

    image -> resnet50 -> 19 scores -> rule -> PASS or FAIL (+ the class that did it)

Two files ship, both small: this one (torch) and pass_fail_block.py (no torch, so
the rule can be reviewed, tested and re-derived without the model).

THE NPZ IS NOT PART OF THIS PATH
--------------------------------
predictions.npz, metrics.json and thresholds.json are the audit record: they let a
reviewer recompute every number we report, months later, without a GPU. Nothing on a
line picture passes through them. They are the reason the numbers can be checked;
they are not the way the model runs.

WHY IT MUST BE A RESIDENT PROCESS
---------------------------------
Loading the checkpoint plus importing torch costs seconds, once. Paying that per
picture would blow any latency budget, so the line keeps this process warm and calls
it. Two shapes:

  resident service   import score_picture() in the camera loop, call it per frame
  one shot           this file's CLI, for a single picture or a replay of a folder

HOW TO RUN IT
-------------
One picture (JSON on stdout):
    .venv/bin/python experiments/multilabel_ooi/predict_picture.py \
        --image /data/.../picture.png --cuts run/multilabel_ooi_20261104/combined/thresholds.json

Latency, the real-time question, single picture at a time:
    .venv/bin/python experiments/multilabel_ooi/predict_picture.py \
        --checkpoint run/multilabel_ooi_20261104/combined/final.pt \
        --cuts run/multilabel_ooi_20261104/combined/thresholds.json \
        --bench 120 --device cuda

The bench reports decode, forward and total separately, because on a line the image
arrives as pixels and the decode is part of the budget, not free.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pass_fail_block as block  # noqa: E402

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
IMGSZ = 224
COLUMNS = ["P1_MPP", "P1_ML", "P2_LOC", "P2_DC", "P1_NL", "P1_FL", "P2_LD", "P1_COC",
           "P2_DS", "P2_FOV", "P2_BSC", "P1_PPM",
           "class_bubble", "class_bubble_cluster", "class_foreign_matter", "class_fiber",
           "class_wet_package", "class_hema", "class_extraneous_polymer"]


def build_model(n_outputs=len(COLUMNS), arch="resnet50"):
    """The same head the trainer builds: resnet50 with a plain linear output."""
    import torch.nn as nn
    from torchvision import models

    if arch != "resnet50":
        raise SystemExit(f"arch {arch} not implemented; the trained checkpoints are resnet50")
    model = models.resnet50(weights=None)
    model.fc = nn.Linear(model.fc.in_features, n_outputs)
    return model


class Reader:
    """Loads the head once and turns a picture into a verdict."""

    def __init__(self, checkpoint: str, cuts: dict, device: str = "cpu", amp: bool = True):
        import torch

        self.torch = torch
        self.device = torch.device(device)
        self.amp = bool(amp) and self.device.type == "cuda"
        self.cuts = cuts
        self.model = build_model()
        state = torch.load(checkpoint, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()

    def _tensor(self, image_path: str):
        from PIL import Image
        from torchvision import transforms

        transform = transforms.Compose([
            transforms.Resize((IMGSZ, IMGSZ)),
            transforms.ToTensor(),
            transforms.Normalize(mean=list(IMAGENET_MEAN), std=list(IMAGENET_STD)),
        ])
        with Image.open(image_path) as img:
            return transform(img.convert("RGB"))

    def scores(self, tensor) -> np.ndarray:
        torch = self.torch
        with torch.no_grad():
            with torch.amp.autocast("cuda", enabled=self.amp):
                logits = self.model(tensor.unsqueeze(0).to(self.device))
            return torch.sigmoid(logits).float().cpu().numpy()[0]

    def verdict(self, image_path: str) -> dict:
        """The production call: picture path in, verdict out."""
        t0 = time.perf_counter()
        tensor = self._tensor(image_path)
        t1 = time.perf_counter()
        values = self.scores(tensor)
        t2 = time.perf_counter()
        result = block.decide({c: float(values[i]) for i, c in enumerate(COLUMNS)}, cuts=self.cuts)
        t3 = time.perf_counter()
        result["ms"] = {"decode": round((t1 - t0) * 1e3, 2),
                        "forward": round((t2 - t1) * 1e3, 2),
                        "decide": round((t3 - t2) * 1e3, 3),
                        "total": round((t3 - t0) * 1e3, 2)}
        return result


def load_cuts(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {c: float(v["threshold"]) for c, v in data["per_class"].items()}


def bench(reader: Reader, image_paths: list[str], warmup: int) -> dict:
    if reader.device.type == "cuda":
        reader.torch.cuda.synchronize()
    for path in image_paths[:warmup]:
        reader.verdict(path)
    if reader.device.type == "cuda":
        reader.torch.cuda.synchronize()

    rows = [reader.verdict(p) for p in image_paths[warmup:]]
    def stats(key):
        values = np.array([r["ms"][key] for r in rows], dtype=float)
        return {"p50": round(float(np.percentile(values, 50)), 2),
                "p95": round(float(np.percentile(values, 95)), 2),
                "max": round(float(values.max()), 2)}
    verdicts = [r["verdict"] for r in rows]
    return {
        "pictures": len(rows),
        "warmup": warmup,
        "device": str(reader.device),
        "amp": reader.amp,
        "ms": {k: stats(k) for k in ("decode", "forward", "decide", "total")},
        "pass": verdicts.count("pass"),
        "fail": verdicts.count("fail"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="")
    ap.add_argument("--checkpoint", default="run/multilabel_ooi_20261104/combined/final.pt")
    ap.add_argument("--cuts", default="run/multilabel_ooi_20261104/combined/thresholds.json")
    ap.add_argument("--device", default="cuda" if _cuda_available() else "cpu")
    ap.add_argument("--no-amp", action="store_true")
    ap.add_argument("--bench", type=int, default=0, help="time this many test pictures")
    ap.add_argument("--image-root", default="/data/FMD_Data_26082026/fmd_temp_images")
    args = ap.parse_args()

    if not (args.image or args.bench):
        ap.error("give --image, or --bench N for the timing run")

    reader = Reader(args.checkpoint, load_cuts(args.cuts), args.device, amp=not args.no_amp)
    if args.image:
        print(json.dumps(reader.verdict(args.image), indent=2))
        return 0

    import csv
    root = Path(args.image_root)
    resolved = Path("run/eda_full_20261029/resolved_labels.csv")
    with open(resolved, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    paths = []
    seen = set()
    for row in rows:
        if row["picture_md5"] in seen:
            continue
        seen.add(row["picture_md5"])
        paths.append(str(root / row["winning_path"]))
    step = max(len(paths) // (args.bench + 12), 1)
    sample = [paths[i] for i in range(0, len(paths), step)][: args.bench + 12]
    print(json.dumps(bench(reader, sample, warmup=min(12, len(sample) // 2)), indent=2))
    return 0


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
