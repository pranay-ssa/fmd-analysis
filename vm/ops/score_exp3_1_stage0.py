"""Experiment 3.1 Stage 0: score the Experiment 1 combined checkpoint on the new test population.

Inference only. No training, no threshold choice, no pass/fail verdict.

    python3.12 vm/ops/score_exp3_1_stage0.py \
        --table run/split_exp3_1_20261116/labels.csv \
        --detail run/split_exp3_1_20261116/picture_detail.csv \
        --image-root /data/FMD_Data_26082026/fmd_temp_images \
        --ckpt run/multilabel_ooi_20261104/combined/final.pt \
        --exp1-run run/multilabel_ooi_20261104/combined/run.json \
        --out run/exp3_1_stage0_20261117

The transform is copied from LensDataset in experiments/multilabel_ooi/train_multilabel.py
(Resize((imgsz, imgsz)), ToTensor, ImageNet normalise) so the scores are on the same footing as
the Experiment 1 predictions. If that function changes, this must change with it.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

CLASS_COLUMNS = ["class_foreign_matter", "class_fiber",
                 "class_extraneous_polymer", "class_hema"]
GATE_FOR = {"class_foreign_matter": "fm_gated", "class_fiber": "fiber_gated",
            "class_extraneous_polymer": "ep_gated", "class_hema": "hema_gated"}


def read_table(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty table: {path}")
    return rows


def auroc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--detail", required=True,
                    help="picture_detail.csv, for the *_present flags")
    ap.add_argument("--image-root", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--exp1-run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    import numpy as np
    import torch
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments" / "multilabel_ooi"))
    from train_multilabel import build_model  # noqa: E402

    run_meta = json.loads(Path(args.exp1_run).read_text(encoding="utf-8"))
    all_columns = list(run_meta["config"]["output_columns"])
    missing = [c for c in CLASS_COLUMNS if c not in all_columns]
    if missing:
        raise SystemExit(f"checkpoint run.json lacks {missing}")

    rows = [r for r in read_table(Path(args.table)) if r["split"] == "test"]
    if not rows:
        raise SystemExit("no test rows in the table")
    detail = {r["picture_md5"]: r for r in read_table(Path(args.detail))}
    root = Path(args.image_root)

    class TestSet(Dataset):
        def __init__(self, rows):
            self.rows = rows
            self.tf = transforms.Compose([
                transforms.Resize((args.imgsz, args.imgsz)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225]),
            ])

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, i):
            r = self.rows[i]
            path = root / r["image_path"]
            if not path.is_file():
                raise SystemExit(f"image not found: {path}")
            with Image.open(path) as img:
                x = self.tf(img.convert("RGB"))
            return x, i

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(len(all_columns)).to(device)
    state = torch.load(args.ckpt, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.eval()

    loader = DataLoader(TestSet(rows), batch_size=args.batch, shuffle=False,
                        num_workers=args.workers)
    scores = np.zeros((len(rows), len(all_columns)), dtype=np.float32)
    with torch.no_grad():
        for images, idx in loader:
            images = images.to(device)
            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                logits = model(images)
            scores[idx.numpy()] = torch.sigmoid(logits).float().cpu().numpy()

    keep = [all_columns.index(c) for c in CLASS_COLUMNS]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_dir / "predictions.npz",
        md5=np.array([r["picture_md5"] for r in rows]),
        split=np.array(["test"] * len(rows)),
        score=scores[:, keep],
        columns=np.array(CLASS_COLUMNS),
        image_path=np.array([r["image_path"] for r in rows]),
    )

    per_class = {}
    present_key = {"class_foreign_matter": "fm_present", "class_fiber": "fiber_present",
                   "class_extraneous_polymer": "ep_present", "class_hema": "hema_present"}
    for col in CLASS_COLUMNS:
        gate_col = GATE_FOR[col]
        j = keep[CLASS_COLUMNS.index(col)]  # index into the 19-column array, not the 4 kept
        carrying = [i for i, r in enumerate(rows)
                    if detail[r["picture_md5"]][present_key[col]] == "1"]
        pos = [float(scores[i, j]) for i in carrying if rows[i][gate_col] == "1"]
        neg = [float(scores[i, j]) for i in carrying if rows[i][gate_col] == "0"]
        per_class[col] = {"auroc": auroc(pos, neg), "gated_n": len(pos),
                          "unflagged_n": len(neg)}

    primary = per_class["class_foreign_matter"]["auroc"]
    run = {
        "schema_version": 1,
        "run_id": f"score__exp1_combined__{args.imgsz}__stage0",
        "family": "score",
        "arm": "stage0_exp1_combined",
        "status": "ok",
        "host": "vm",
        "data": {"table": args.table, "split": "test", "n_test": len(rows),
                 "classes": 4, "image_root": args.image_root},
        "config": {"imgsz": args.imgsz, "batch": args.batch, "ckpt": args.ckpt},
        "metrics": {"primary": {"name": "fm_auroc_test", "value": primary},
                    "per_class": per_class},
        "artifacts": {"predictions": str(out_dir / "predictions.npz")},
        "notes": ("Stage 0 baseline. 327 of the 1,533 test pictures were in this "
                  "checkpoint's training set, so their scores are contaminated; the 85 "
                  "out-of-split and 41 already-in-test pictures are clean."),
    }
    (out_dir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(per_class, indent=2))
    print(f"wrote {out_dir / 'predictions.npz'} and run.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
