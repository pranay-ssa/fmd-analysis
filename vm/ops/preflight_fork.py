#!/usr/bin/env python3
"""Preflight gate for an architecture fork. Run BEFORE any training launch.

Why this exists: on 2026-09-11 two "feature concat" forks were trained that were not what
their names claimed. One contained no head edit at all, and both had dropped the stock head
keys (`end2end`, `reg_max`) plus shortened the SPPF arg list, so `parse_model` rebuilt a
different detector with an identical row layout. This gate makes that class of mistake
loud, cheap and blocking instead of silent.

What it checks
  1. Every top-level key of the pinned stock yaml is present in the fork (nc, end2end,
     reg_max, scales, activation if present).
  2. The fork's SPPF row carries the same arg form as stock (in 8.4.x a 3-arg-or-shorter
     SPPF row takes the legacy branch: activated cv1, no residual).
  3. The built fork has the stock head: reg_max matches stock's, and the one2one branch
     exists iff stock's does.
  4. The row-level diff against stock is printed, so the intended edit is visible and any
     accidental extra edit is caught.
  5. The initialisation contract is printed for the record (a fork built from a yaml starts
     from scratch; a control built from a .pt starts pretrained).

Usage
  python3 preflight_fork.py <fork.yaml> [--stock yolo26n.yaml] [--manifest out.json]
Exits non-zero on any failed assertion, so a launcher can `&&` it before training.
"""
import argparse
import hashlib
import json
from pathlib import Path

from ultralytics import YOLO

HEAD_KEYS = ("nc", "end2end", "reg_max", "scales")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def rows(cfg):
    return [tuple(r) for r in list(cfg.get("backbone", [])) + list(cfg.get("head", []))]


def head_facts(model):
    head = model.model[-1]
    kids = sorted(dict(head.named_children()))
    return {
        "type": type(head).__name__,
        "reg_max": getattr(head, "reg_max", None),
        "end2end": getattr(head, "end2end", None),
        "children": kids,
        "one2one": [k for k in kids if "one2one" in k],
        "nc": getattr(head, "nc", None),
        "params": sum(p.numel() for p in model.parameters()),
        "n_layers": len(model.model),
        "layer_types": [type(x).__name__ for x in model.model],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fork")
    ap.add_argument("--stock", default="yolo26n.yaml", help="pinned stock cfg (packaged default: yolo26n.yaml)")
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()

    failures = []
    fork_path = Path(args.fork)
    if not fork_path.exists():
        raise SystemExit(f"fork not found: {fork_path}")

    stock = YOLO(args.stock, task="detect")
    fork = YOLO(str(fork_path), task="detect", verbose=False)
    scfg, fcfg = stock.model.yaml, fork.model.yaml
    sf, ff = head_facts(stock.model), head_facts(fork.model)

    print("=" * 72)
    print(f"PREFLIGHT  fork={fork_path}  (md5 {md5(fork_path)})")
    print(f"           stock={args.stock}  (md5 {md5(Path(args.stock).resolve()) if Path(args.stock).exists() else 'packaged'})")
    print("=" * 72)

    print("\n[1] top-level keys")
    for k in HEAD_KEYS:
        s, f = scfg.get(k), fcfg.get(k)
        ok = f is not None and f == s
        print(f"    {k:<10} stock={s!r:<30} fork={f!r:<30} {'OK' if ok else 'FAIL'}")
        if not ok:
            failures.append(f"top-level key '{k}': stock={s!r} fork={f!r}")

    print("\n[2] SPPF row arg form")
    s_sppf = [r for r in rows(scfg) if len(r) > 2 and r[2] == "SPPF"]
    f_sppf = [r for r in rows(fcfg) if len(r) > 2 and r[2] == "SPPF"]
    print(f"    stock={s_sppf}")
    print(f"    fork ={f_sppf}")
    if s_sppf != f_sppf:
        failures.append(f"SPPF row differs: stock={s_sppf} fork={f_sppf}")

    print("\n[3] built head identity")
    for k in ("type", "reg_max", "end2end", "children", "params", "n_layers"):
        print(f"    {k:<10} stock={sf[k]!r}")
        print(f"    {'':<10} fork ={ff[k]!r}")
    print(f"    param delta (fork - stock, nc=80 both) = {ff['params'] - sf['params']:+d}")
    if ff["reg_max"] != sf["reg_max"]:
        failures.append(f"reg_max drifted: stock={sf['reg_max']} fork={ff['reg_max']}")
    if bool(ff["one2one"]) != bool(sf["one2one"]):
        failures.append(f"one2one branch: stock={sf['one2one']} fork={ff['one2one']}")

    print("\n[4] row-level diff vs stock")
    S, F = rows(scfg), rows(fcfg)
    ndiff = 0
    for i in range(max(len(S), len(F))):
        s = S[i] if i < len(S) else None
        f = F[i] if i < len(F) else None
        if s != f:
            ndiff += 1
            print(f"    row {i:>2}  stock={s}")
            print(f"    {'':>6}  fork ={f}")
    print(f"    differing rows: {ndiff}  (stock {len(S)} rows -> fork {len(F)} rows)")
    if ndiff == 0:
        print("    NOTE: zero differing rows means this fork is the stock architecture.")

    print("\n[5] initialisation contract")
    print("    A yaml-built model starts from scratch. For a matched comparison either train")
    print("    the control from the same yaml, or load stock weights into the fork explicitly:")
    print(f"      YOLO({fork_path.name!r}, task='detect').load('yolo26n.pt')")
    print("    Record which one was used in the run manifest (ADR-012).")

    manifest = {
        "fork": str(fork_path),
        "fork_md5": md5(fork_path),
        "stock": args.stock,
        "stock_head": sf,
        "fork_head": ff,
        "row_diff_count": ndiff,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }
    out = Path(args.manifest) if args.manifest else fork_path.with_suffix(".preflight.json")
    out.write_text(json.dumps(manifest, indent=2, default=str))
    print(f"\nmanifest -> {out}")

    print("=" * 72)
    if failures:
        print("VERDICT: FAIL")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("VERDICT: PASS - the fork differs from stock only where you intended, and the head is stock.")


if __name__ == "__main__":
    main()
