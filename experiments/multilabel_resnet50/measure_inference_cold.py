#!/usr/bin/env python3
"""Fresh-process, no-warmup inference measurement for a finished run.

The timing inside train.py measures a cold pass in the training process, where the
CUDA context is already up. This script starts a new process, loads the checkpoint,
and times a first pass over the test loader with no warmup at all, so it also
carries the process and CUDA initialisation costs. It is the "no warmup" number in
the strict sense, and it doubles as a checkpoint check: the architecture recorded in
the checkpoint's own args is rebuilt and the state dict must load with no missing
and no unexpected keys.

Usage (from a folder holding labels.csv, splits/ and train.py):
    python3 measure_inference_cold.py --run <dir with best.pt> [--arch <name>] [--batch 8]
"""
import argparse
import json
import sys
import time
from pathlib import Path

PROCESS_T0 = time.perf_counter()

import numpy as np  # noqa: E402


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="directory holding best.pt")
    ap.add_argument("--arch", default="", help="override the architecture in the checkpoint")
    ap.add_argument("--labels", default="labels.csv")
    ap.add_argument("--split", default="splits/variant_80_20_two_way.csv")
    ap.add_argument("--split-column", default="split_named")
    ap.add_argument("--image-root", required=True)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--repeats", type=int, default=3, help="steady repeats after the cold pass")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    import torch
    import torchvision
    import train as T

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_path = Path(args.run) / "best.pt"
    # weights_only=False is deliberate: this file is written by train.py in this same
    # folder by our own run, and holds only tensors plus plain scalars, strings and
    # dicts (no callables), so there is nothing to unpickle beyond the state dict.
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    arch = args.arch or ckpt.get("args", {}).get("arch", T.ARCH_RESNET50)
    t_loaded = time.perf_counter()

    model = T.build_model(torch, torchvision, ckpt["weights"], len(T.LP_TAGS), arch)
    missing, unexpected = model.load_state_dict(ckpt["model"], strict=False)
    if missing or unexpected:
        print("CHECKPOINT MISMATCH: missing=%s unexpected=%s" % (list(missing)[:5], list(unexpected)[:5]))
        return 1
    model = model.to(device).eval()
    t_ready = time.perf_counter()

    rows = T.load_dataset_rows(args.labels, args.split, "test", False, args.split_column)
    tf = T.build_transforms(torch, torchvision, args.imgsz, train=False)
    loader = torch.utils.data.DataLoader(
        T.LensDataset(rows, args.image_root, args.imgsz, False, torch, tf),
        batch_size=args.batch, shuffle=False, num_workers=args.workers)
    t_data = time.perf_counter()

    cold = T.inference_pass(model, loader, device, torch, device.type == "cuda", collect=False)
    t_cold = time.perf_counter()
    steady = [T.inference_pass(model, loader, device, torch, device.type == "cuda", collect=False)
              for _ in range(args.repeats)]
    steady_ms = [s["ms_per_image"] for s in steady]

    out = {
        "run": str(args.run),
        "arch": arch,
        "arch_label": T.ARCH_LABELS[arch],
        "params_total": T.count_params(model),
        "device": T.device_label(torch, device),
        "batch": args.batch,
        "test_images": cold["images"],
        "warmup_used": False,
        "fresh_process": True,
        "checkpoint_state_dict": "loaded clean (no missing, no unexpected keys)",
        "cold_inference_ms_per_image": round(cold["ms_per_image"], 3),
        "cold_inference_total_seconds": round(cold["seconds"], 4),
        "cold_first_batch_ms": round(cold["first_batch_ms"], 3),
        "steady_inference_ms_per_image_median": round(float(np.median(steady_ms)), 3),
        "steady_inference_ms_per_image_repeats": [round(v, 3) for v in steady_ms],
        "process_start_to_checkpoint_loaded_s": round(t_loaded - PROCESS_T0, 3),
        "process_start_to_model_on_gpu_s": round(t_ready - PROCESS_T0, 3),
        "process_start_to_first_batch_s": round(t_data - PROCESS_T0, 3),
        "process_start_to_cold_pass_done_s": round(t_cold - PROCESS_T0, 3),
    }
    print(json.dumps(out, indent=1))
    (Path(args.run) / "inference_cold.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
