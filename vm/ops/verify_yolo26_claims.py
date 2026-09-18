#!/usr/bin/env python3
"""Read-only verification of YOLO26 fork claims on the VM (no training, no writes).

Checks, in order:
  1. Where the feat_concat yamls actually live + md5 (repo root vs experiments/ vs experiments/yolo26/).
  2. The VM copies of those yamls, verbatim, so they can be diffed against the local repo.
  3. Every yolo26/crop-repro run's args.yaml: model source, optimizer, lr0, lrf, single_cls.
  4. The actual lr column from crop_repro results.csv, first and last epoch.
  5. Trained checkpoints: param count + detection-head config (reg_max / end2end / one2one branch).
  6. Log lines proving what optimizer the trainer really used.

Run: python3 -u /home/pranayp/yolo_ooi/verify_yolo26_claims.py
"""
import hashlib
from pathlib import Path

PRJ = Path("/home/pranayp/yolo_ooi")
RUNS_ARCH = PRJ / "runs" / "yolo26_arch"
RUNS_REPRO = PRJ / "runs" / "crop_repro"
RUNS_MC = PRJ / "runs" / "yolo26_multiclass"


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def banner(txt):
    print()
    print("=" * 72)
    print(txt)
    print("=" * 72)


banner("1. YAML INVENTORY")
cands = (list(PRJ.glob("*.yaml"))
         + list(PRJ.glob("experiments/*.yaml"))
         + list(PRJ.glob("experiments/yolo26/*.yaml")))
for p in sorted(set(cands)):
    print(f"  md5={md5(p)}  size={p.stat().st_size:6d}  {p}")

banner("2. VM COPIES OF THE FEAT CONCAT YAMLS (verbatim)")
for name in ["experiments/yolo26_feat_concat.yaml",
             "experiments/yolo26_feat_concat_v2.yaml",
             "experiments/yolo26/yolo26_feat_concat.yaml",
             "experiments/yolo26/yolo26_feat_concat_v2.yaml"]:
    p = PRJ / name
    print(f"--- {name}   exists={p.exists()}")
    if p.exists():
        for i, line in enumerate(p.read_text().splitlines(), 1):
            print(f"{i:3d}| {line}")
    print()

banner("3. RUN ARGS (what each run actually used)")
KEYS = {"model", "data", "optimizer", "lr0", "lrf", "momentum", "batch", "imgsz",
        "epochs", "patience", "seed", "single_cls", "cos_lr", "warmup_epochs",
        "task", "name", "end2end", "reg_max"}
for d in sorted(RUNS_ARCH.glob("*/args.yaml")) + sorted(RUNS_REPRO.glob("*/args.yaml")) + sorted(RUNS_MC.glob("*/args.yaml")):
    print(f"--- {d.parent.name}")
    for line in d.read_text().splitlines():
        if line.split(":")[0].strip() in KEYS:
            print(f"    {line.strip()}")
    print()

banner("4. ACTUAL LR COLUMN, crop_repro results.csv (first + last epoch)")
for d in sorted(RUNS_REPRO.glob("*/results.csv")):
    lines = d.read_text().splitlines()
    if not lines:
        continue
    hdr = [h.strip() for h in lines[0].split(",")]
    idx = {h: i for i, h in enumerate(hdr)}
    cols = [c for c in ("epoch", "lr/pg0", "lr/pg1", "lr/pg2", "metrics/mAP50(B)", "metrics/mAP50-95(B)") if c in idx]
    print(f"--- {d.parent.name}  epochs={len(lines) - 1}  cols={cols}")
    for row in (lines[1], lines[-1]):
        parts = row.split(",")
        print("    " + "  ".join(f"{c}={parts[idx[c]]}" for c in cols if idx[c] < len(parts)))
    print()

banner("5. TRAINED MODELS: params + head config")
targets = [("baseline(b8)", RUNS_ARCH / "yolo26n_baseline"),
           ("feat_concat_V1", RUNS_ARCH / "yolo26n_feat_concat"),
           ("feat_concat_V2", RUNS_ARCH / "yolo26n_feat_concat_v2"),
           ("mc_baseline", RUNS_MC / "yolo26n_mc_baseline")]
from ultralytics import YOLO  # noqa: E402  (import after banners so failures are obvious)

for label, d in targets:
    w = d / "weights" / "best.pt"
    print(f"--- {label}: {w}   exists={w.exists()}")
    if not w.exists():
        continue
    m = YOLO(str(w))
    net = m.model
    head = net.model[-1]
    print(f"    params_sum={sum(p.numel() for p in net.parameters())}")
    print(f"    yaml: nc={net.yaml.get('nc')} reg_max={net.yaml.get('reg_max')} end2end={net.yaml.get('end2end')}")
    print(f"    head={type(head).__name__} nc={getattr(head, 'nc', None)} reg_max={getattr(head, 'reg_max', None)} "
          f"end2end={getattr(head, 'end2end', None)} legacy={getattr(head, 'legacy', None)} nl={getattr(head, 'nl', None)}")
    print(f"    head_children={sorted(dict(head.named_children()))}")
    print("    layers=" + ",".join(type(x).__name__ for x in net.model))
    print()

banner("6. LOG LINES: the real optimizer choice")
for logname in ["yolo26_v2.log", "yolo26_feat_concat.log", "yolo26_mc.log", "crop_repro.log"]:
    p = PRJ / logname
    if not p.exists():
        hits = list(PRJ.glob(logname.replace(".log", "*")))
        print(f"--- {logname}: MISSING (near matches: {[x.name for x in hits]})")
        continue
    text = p.read_text(errors="replace").splitlines()
    keys = ("ignoring 'lr0", "optimizer:", "AdamW", "MuSGD", "Overriding class names", "single class")
    hits = [ln.strip() for ln in text if any(k.lower() in ln.lower() for k in keys)]
    print(f"--- {logname}: {len(text)} lines, {len(hits)} matching")
    for ln in hits[:10]:
        print("   ", ln)
    print()

banner("DONE")
