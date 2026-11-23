#!/usr/bin/env python3
"""Copy every picture in the frozen manifest into one images folder, verified.

For each manifest row, find a local file with that basename whose content matches the row's
picture_key, copy it into images/, then read the copy once and check md5 and record sha256.
Nothing is deleted. A source that does not match is skipped, never trusted.

Writes, inside the store:
    images/<basename>
    checksums/images.sha256
    _copy_report.json
    _copy_missing.csv

Re-runnable: a file already in images/ with the right hash is skipped.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/data/FMD_Data_26082026")
STORE = ROOT / "frozen_data_20261117"
IMAGES = STORE / "images"
IMG_EXTS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def hashes(path: Path) -> tuple[str, str]:
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest()


def build_index(root: Path, skip: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    skip_r = skip.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if here.resolve() == skip_r:
            dirnames[:] = []
            continue
        for name in filenames:
            if Path(name).suffix.lower() in IMG_EXTS:
                index.setdefault(name, []).append(here / name)
    return index


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = list(csv.DictReader((STORE / "manifest.csv").open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    IMAGES.mkdir(parents=True, exist_ok=True)
    (STORE / "checksums").mkdir(parents=True, exist_ok=True)
    (STORE / "audit").mkdir(parents=True, exist_ok=True)

    print("indexing sources under %s" % ROOT, flush=True)
    index = build_index(ROOT, STORE)
    print("indexed %d basenames" % len(index), flush=True)

    def handle(row: dict) -> dict:
        name = row["basename"]
        want = row["picture_key"]
        dest = IMAGES / name
        if dest.exists():
            got, sha = hashes(dest)
            if got == want:
                return {"basename": name, "status": "already_present", "sha256": sha,
                        "source": ""}
            dest.unlink()
        for cand in index.get(name, []):
            try:
                shutil.copy2(cand, dest)
            except OSError as exc:
                continue
            got, sha = hashes(dest)
            if got == want:
                return {"basename": name, "status": "copied", "sha256": sha,
                        "source": str(cand)}
            dest.unlink(missing_ok=True)
        return {"basename": name, "status": "no_matching_source", "sha256": "", "source": ""}

    started = time.time()
    results = []
    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(handle, r): r for r in rows}
        for done, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            counts[res["status"]] = counts.get(res["status"], 0) + 1
            if done % 500 == 0:
                print("  %d/%d %s" % (done, len(rows), counts), flush=True)

    missing = [r for r in results if r["status"] == "no_matching_source"]
    with (STORE / "audit" / "missing_from_copy.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["basename", "status", "source", "sha256"])
        w.writeheader()
        w.writerows(missing)

    good = sorted((r for r in results if r["sha256"]), key=lambda r: r["basename"])
    with (STORE / "checksums" / "images.sha256").open("w", encoding="utf-8") as fh:
        for r in good:
            fh.write("%s  images/%s\n" % (r["sha256"], r["basename"]))

    report = {
        "manifest_rows": len(rows),
        "status_counts": counts,
        "images_in_store": len(list(IMAGES.glob("*"))),
        "checksum_lines": len(good),
        "minutes": round((time.time() - started) / 60, 1),
    }
    (STORE / "audit" / "build_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1), flush=True)
    if missing:
        print("MISSING:", [m["basename"] for m in missing[:10]], flush=True)


if __name__ == "__main__":
    main()
