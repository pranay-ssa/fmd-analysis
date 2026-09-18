#!/usr/bin/env python3
"""Local pre-push diff: fork yaml vs the pinned stock yolo26.yaml, row by row.

Same intent as vm/ops/preflight_fork.py but runs on the workstation with no ultralytics
install, so a copy-paste mistake in a fork is caught before it is pushed to the VM.

Usage: python local_fork_diff.py <fork.yaml> [--stock <stock.yaml>]
"""
import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML needed: pip install pyyaml")

TOP_KEYS = ("nc", "end2end", "reg_max", "scales")


def rows(cfg):
    return [tuple(r) for r in list(cfg.get("backbone", [])) + list(cfg.get("head", []))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fork")
    ap.add_argument("--stock", default="yolo26_stock_8.4.142.yaml")
    args = ap.parse_args()

    stock = yaml.safe_load(Path(args.stock).read_text())
    fork = yaml.safe_load(Path(args.fork).read_text())

    print("=" * 72)
    print(f"LOCAL DIFF  fork={args.fork}")
    print(f"            stock={args.stock}")
    print("=" * 72)

    print("\n[1] top-level keys")
    bad = 0
    for k in TOP_KEYS:
        s, f = stock.get(k), fork.get(k)
        ok = f == s
        bad += 0 if ok else 1
        print(f"    {k:<10} stock={s!r:<32} fork={f!r:<32} {'OK' if ok else 'FAIL'}")
    extra = set(fork) - set(stock)
    missing = set(stock) - set(fork)
    print(f"    extra keys in fork: {sorted(extra) or 'none'}")
    print(f"    keys missing from fork: {sorted(missing) or 'none'}")
    bad += len(extra) + len(missing)

    print("\n[2] SPPF row arg form")
    s_sppf = [r for r in rows(stock) if len(r) > 2 and r[2] == "SPPF"]
    f_sppf = [r for r in rows(fork) if len(r) > 2 and r[2] == "SPPF"]
    print(f"    stock={s_sppf}")
    print(f"    fork ={f_sppf}  {'OK' if s_sppf == f_sppf else 'FAIL'}")
    bad += 0 if s_sppf == f_sppf else 1

    print("\n[3] row-level diff (row index = backbone rows then head rows)")
    S, F = rows(stock), rows(fork)
    ndiff = 0
    for i in range(max(len(S), len(F))):
        s = S[i] if i < len(S) else None
        f = F[i] if i < len(F) else None
        if s != f:
            ndiff += 1
            print(f"    row {i:>2}  stock={s}")
            print(f"    {'':>6}  fork ={f}")
    print(f"\n    differing rows: {ndiff}   (stock {len(S)} rows -> fork {len(F)} rows)")

    print("\n[4] every reference target exists")
    refs_bad = []
    for i, r in enumerate(F):
        src = r[0]
        targets = src if isinstance(src, (list, tuple)) else [src]
        for t in targets:
            if isinstance(t, int) and not (-1 <= t < len(F)):
                refs_bad.append((i, t))
    if refs_bad:
        bad += 1
        for i, t in refs_bad:
            print(f"    FAIL row {i} references {t}, outside 0..{len(F) - 1}")
    else:
        print(f"    all {len(F)} rows reference valid rows (or -1)")

    print("\n[5] module names present in both")
    mods_s = {r[2] for r in S if len(r) > 2}
    mods_f = {r[2] for r in F if len(r) > 2}
    new_mods = mods_f - mods_s
    print(f"    modules in fork but not stock: {sorted(new_mods) or 'none'}")
    print(f"    modules in stock but not fork: {sorted(mods_s - mods_f) or 'none'}")

    print("=" * 72)
    print(f"VERDICT: {'FAIL' if bad else 'PASS'}  (failures: {bad})")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
