"""End-to-end check of the pipeline seam: picture -> CNN -> scores -> pass/fail.

WHAT THIS PROVES
----------------
The trained combined head plus the pass/fail block reproduce, on real pictures,
the scores and verdicts that were saved during training. Run it on the VM (torch
lives there), scoring a spread of test pictures from disk:

    .venv/bin/python - < vm/ops/score_pipeline_check.py   (piped, nothing left behind)

For each picture it prints the maximum absolute difference between the score this
run computes and the score in predictions.npz, and whether the block's verdict
agrees. A match means the deployed path (open image, resize 224, normalise,
forward, sigmoid, decide) is the same path the reported numbers came from.

Exit code 0 only when every picture matches within tolerance and every verdict agrees.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path("/home/pranayp/fmd-analysis")
ARM = ROOT / "run" / "multilabel_ooi_20261104" / "combined"
IMAGE_ROOT = "/data/FMD_Data_26082026/fmd_temp_images"
sys.path.insert(0, str(ROOT / "experiments" / "multilabel_ooi"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import pass_fail_block as block  # noqa: E402
import train_multilabel as T  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--tolerance", type=float, default=1e-3)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--image-root", default=IMAGE_ROOT)
    ap.add_argument("--amp", action="store_true", default=True,
                    help="match the trainer's fp16 autocast (default on)")
    ap.add_argument("--batch", type=int, default=8,
                    help="match the trainer's scoring batch size (default 8)")
    args = ap.parse_args()

    raw = T.read_table()
    rows, columns = T.build_rows(raw, "combined", "class")
    test_rows = [r for r in rows if r["split"] == "test"]
    if len(test_rows) != 1121:
        raise SystemExit(f"test rows {len(test_rows)}, expected 1121")

    step = max(len(test_rows) // args.n, 1)
    picked = [test_rows[i] for i in range(0, len(test_rows), step)][: args.n]

    saved = np.load(ARM / "predictions.npz")
    saved_md5 = [str(m) for m in saved["test_md5"]]
    saved_index = {m: i for i, m in enumerate(saved_md5)}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = T.build_model(len(columns))
    model.load_state_dict(torch.load(ARM / "final.pt", map_location=device, weights_only=True))
    model.to(device).eval()

    dataset = T.LensDataset(picked, args.image_root, imgsz=args.imgsz)
    worst, bad, verdict_bad = 0.0, 0, 0
    print(f"{'md5':<10} {'max|diff|':>9} {'saved':>6} {'live':>6}  driver")
    amp = args.amp and device.type == "cuda"
    # Same batch size the trainer scored with: batch composition changes which
    # cudnn kernels run, and at fp16 that moves the last digits.
    with torch.no_grad():
        for start in range(0, len(picked), args.batch):
            chunk = picked[start:start + args.batch]
            tensors = torch.stack([dataset[start + k][0] for k in range(len(chunk))]).to(device)
            with torch.amp.autocast("cuda", enabled=amp):
                logits = model(tensors)
            lives = torch.sigmoid(logits).float().cpu().numpy()
            for k, row in enumerate(chunk):
                live = lives[k]

                j = saved_index[row["md5"]]
                ref = saved["test_score"][j]
                diff = float(np.max(np.abs(live - ref)))
                worst = max(worst, diff)

                live_scores = {c: float(live[ci]) for ci, c in enumerate(columns)}
                ref_scores = {c: float(ref[ci]) for ci, c in enumerate(columns)}
                live_v = block.decide(live_scores)["verdict"]
                ref_v = block.decide(ref_scores)["verdict"]
                agree = live_v == ref_v
                verdict_bad += 0 if agree else 1
                bad += 0 if diff <= args.tolerance else 1

                driver = block.decide(live_scores)["driver"] or "-"
                print(f"{row['md5'][:8]:<10} {diff:>9.2e} {ref_v:>6} {live_v:>6}  {driver}"
                      + ("" if agree else "   VERDICT MISMATCH"))

    summary = {
        "pictures": len(picked),
        "device": str(device),
        "max_abs_score_diff": worst,
        "tolerance": args.tolerance,
        "pictures_out_of_tolerance": bad,
        "verdict_mismatches": verdict_bad,
        "columns": columns,
    }
    print(json.dumps(summary, indent=2))
    return 0 if (bad == 0 and verdict_bad == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
