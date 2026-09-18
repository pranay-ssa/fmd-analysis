#!/usr/bin/env python3
"""Follow-up: LR trajectories + which log holds the fixed-LR runs. Read-only."""
from pathlib import Path

PRJ = Path("/home/pranayp/yolo_ooi")
RUNS_REPRO = PRJ / "runs" / "crop_repro"


def banner(txt):
    print()
    print("=" * 72)
    print(txt)
    print("=" * 72)


banner("A. ALL LOGS IN PROJECT ROOT")
for p in sorted(PRJ.glob("*.log")):
    print(f"  {p.stat().st_size:9d}  {p.name}")

banner("B. WHICH LOG SAYS what about lr0 (every 'ignoring lr0' + optimizer line)")
for p in sorted(PRJ.glob("*.log")):
    hits = []
    for ln in p.read_text(errors="replace").splitlines():
        s = ln.strip()
        if "ignoring 'lr0" in s or s.startswith("optimizer: AdamW") or s.startswith("optimizer: MuSGD"):
            hits.append(s[:150])
    if hits:
        print(f"--- {p.name}")
        for h in hits:
            print("   ", h)

banner("C. LR TRAJECTORY (every 10th epoch) + best epoch, per crop_repro run")
for d in sorted(RUNS_REPRO.glob("*/results.csv")):
    lines = d.read_text().splitlines()
    hdr = [h.strip() for h in lines[0].split(",")]
    idx = {h: i for i, h in enumerate(hdr)}
    rows = [r.split(",") for r in lines[1:]]
    lr_key = "lr/pg0" if "lr/pg0" in idx else None
    map_key = next((k for k in idx if k.startswith("metrics/mAP50(B")), None)
    print(f"--- {d.parent.name}: {len(rows)} epochs")
    if lr_key and map_key:
        lrs = [float(r[idx[lr_key]]) for r in rows]
        maps = [float(r[idx[map_key]]) for r in rows]
        print(f"    lr  first={lrs[0]:.9f}  max={max(lrs):.9f}  last={lrs[-1]:.9f}")
        print("    lr traj@epochs1,20,40,60,80,100: " + "  ".join(f"{lrs[i]:.6f}" for i in (0, 19, 39, 59, 79, 99) if i < len(lrs)))
        best = max(range(len(maps)), key=lambda i: maps[i])
        print(f"    mAP50 best={maps[best]:.5f} at epoch {best + 1}   final={maps[-1]:.5f}")
    print()

banner("D. VM SUMMARY JSONS (compare against the local mirrors)")
for name in ["crop_repro_summary.json", "crop_repro_summary_fixedlr.json", "crop_repro_summary_all.json",
             "yolo26_feat_concat_summary.json", "yolo26_feat_concat_v2_summary.json", "yolo26_mc_summary.json"]:
    p = PRJ / name
    print(f"--- {name}: exists={p.exists()}")
    if p.exists():
        print(p.read_text().strip()[:1200])
    print()

banner("E. BUILD PARAM COUNTS FROM THE VM YAMLS (what the fork yaml alone builds to, nc=80 default)")
from ultralytics import YOLO  # noqa: E402

for label, path in [("stock yolo26n.yaml (packaged)", "yolo26n.yaml"),
                    ("VM experiments/yolo26_feat_concat.yaml", str(PRJ / "experiments/yolo26_feat_concat.yaml")),
                    ("VM yolo26_feat_concat_v2.yaml (root)", str(PRJ / "yolo26_feat_concat_v2.yaml"))]:
    try:
        m = YOLO(path, task="detect")
        head = m.model.model[-1]
        print(f"--- {label}")
        print(f"    params={sum(p.numel() for p in m.model.parameters())}  nc={m.model.yaml.get('nc')} "
              f"reg_max={m.model.yaml.get('reg_max')} end2end={m.model.yaml.get('end2end')}")
        print(f"    head reg_max={getattr(head, 'reg_max', None)} children={sorted(dict(head.named_children()))}")
        print(f"    layers={len(m.model.model)}  types=" + ",".join(type(x).__name__ for x in m.model.model))
    except Exception as e:  # noqa: BLE001
        print(f"--- {label}: FAILED {type(e).__name__}: {e}")
    print()

banner("DONE")
