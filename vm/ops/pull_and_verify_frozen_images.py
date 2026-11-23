#!/usr/bin/env python3
"""Verify every frozen image against the blob, and stage the missing new batch.

Phase old: for every blob in PRODUCTION-20260925, find a local file with the same basename,
           hash it, and compare with the blob's stored Content-MD5. No downloads. The three
           alias blobs (long names whose content is annotated under a short name) are expected
           to have no name match and are reported, not fixed.

Phase new: make PRODUCTION-20261031 complete in the staging folder. For each blob:
             - already in staging with the right hash  -> skip
             - a local copy elsewhere matches the hash -> copy it in
             - otherwise                                -> download to .part, verify, rename
           A failed or truncated download is deleted, so a re-run retries it.

Reads the credential at ~/armor_blob_conn. Writes only the staging folder and its report.
Nothing outside the staging folder is touched.

Run on the VM (no script is left behind if piped):
    ssh amd-a100-vm 'python3 - --limit 3' < vm/ops/pull_and_verify_frozen_images.py
    ssh amd-a100-vm 'nohup python3 /tmp/pv.py > /tmp/pv.log 2>&1 & echo $!' < ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from azure.storage.blob import BlobServiceClient

CONN = os.path.expanduser("~/armor_blob_conn")
ACCOUNT = "stjnjmakearmor"
CONTAINER = "fmd-cvat-images"
ROOT = Path("/data/FMD_Data_26082026")
STAGE = ROOT / "PRODUCTION-20261031"
PREFIX_OLD = "FMD_PROD/PRODUCTION-20260925/"
PREFIX_NEW = "FMD_PROD/PRODUCTION-20261031/"
IMG_EXTS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def connect() -> BlobServiceClient:
    if not os.path.exists(CONN):
        sys.exit("no credential at %s" % CONN)
    text = Path(CONN).read_text(encoding="utf-8").strip()
    if "AccountName=" not in text:
        text = ("DefaultEndpointsProtocol=https;AccountName=%s;AccountKey=%s;"
                "EndpointSuffix=core.windows.net" % (ACCOUNT, text))
    return BlobServiceClient.from_connection_string(text)


def local_index(root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    skip = STAGE.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if here.resolve() == skip:
            dirnames[:] = []
            continue
        for name in filenames:
            if Path(name).suffix.lower() in IMG_EXTS:
                index.setdefault(name, []).append(here / name)
    return index


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most this many blobs per phase (smoke test)")
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    svc = connect()
    cc = svc.get_container_client(CONTAINER)
    STAGE.mkdir(parents=True, exist_ok=True)

    print("building the local basename index under %s" % ROOT, flush=True)
    index = local_index(ROOT)
    print("indexed %d distinct basenames" % len(index), flush=True)

    hash_cache: dict[Path, str] = {}

    def cached_md5(path: Path) -> str | None:
        if path in hash_cache:
            return hash_cache[path]
        try:
            digest = md5_file(path)
        except OSError:
            return None
        hash_cache[path] = digest
        return digest

    rows: list[dict] = []
    started = time.time()

    # ---------- phase old: verify only ----------
    old_blobs = []
    for b in cc.list_blobs(name_starts_with=PREFIX_OLD):
        if args.limit and len(old_blobs) >= args.limit:
            break
        old_blobs.append(b)
    print("old batch: %d blobs to verify" % len(old_blobs), flush=True)

    old_ok = old_missing = old_mismatch = 0
    for i, b in enumerate(old_blobs, 1):
        base = b.name.rsplit("/", 1)[-1]
        blob_md5 = b.content_settings.content_md5
        blob_hex = bytes(blob_md5).hex() if blob_md5 else ""
        candidates = index.get(base, [])
        status = "no_local_copy"
        local_path = ""
        local_hex = ""
        for cand in candidates:
            got = cached_md5(cand)
            if got is None:
                continue
            local_hex = got
            local_path = str(cand)
            if blob_hex and got == blob_hex:
                status = "ok"
                break
            status = "hash_mismatch"
        if status == "ok":
            old_ok += 1
        elif status == "hash_mismatch":
            old_mismatch += 1
        else:
            old_missing += 1
        rows.append({"phase": "old", "name": b.name.rsplit("/", 1)[-1],
                     "size": b.size, "blob_md5": blob_hex, "local_path": local_path,
                     "local_md5": local_hex, "status": status})
        if i % 1000 == 0:
            print("  old %d/%d  ok=%d missing=%d mismatch=%d"
                  % (i, len(old_blobs), old_ok, old_missing, old_mismatch), flush=True)

    print("old batch done: ok=%d missing=%d mismatch=%d in %.1f min"
          % (old_ok, old_missing, old_mismatch, (time.time() - started) / 60), flush=True)

    # ---------- phase new: complete the staging folder ----------
    new_blobs = [b for b in cc.list_blobs(name_starts_with=PREFIX_NEW)]
    if args.limit:
        new_blobs = new_blobs[: args.limit]
    print("new batch: %d blobs, staging folder %s" % (len(new_blobs), STAGE), flush=True)

    def ensure(blob) -> dict:
        base = blob.name.rsplit("/", 1)[-1]
        dest = STAGE / base
        blob_md5 = blob.content_settings.content_md5
        blob_hex = bytes(blob_md5).hex() if blob_md5 else ""
        if dest.exists():
            got = cached_md5(dest)
            if blob_hex and got == blob_hex:
                return {"phase": "new", "name": base, "size": blob.size,
                        "blob_md5": blob_hex, "local_path": str(dest),
                        "local_md5": got, "status": "already_staged"}
        for cand in index.get(base, []):
            got = cached_md5(cand)
            if got and blob_hex and got == blob_hex:
                try:
                    if not dest.exists():
                        os.link(cand, dest)
                    return {"phase": "new", "name": base, "size": blob.size,
                            "blob_md5": blob_hex, "local_path": str(cand),
                            "local_md5": got, "status": "copied_from_local"}
                except OSError:
                    break
        if args.no_download:
            return {"phase": "new", "name": base, "size": blob.size, "blob_md5": blob_hex,
                    "local_path": "", "local_md5": "", "status": "needs_download"}
        part = dest.with_suffix(dest.suffix + ".part")
        try:
            data = cc.download_blob(blob.name).readall()
            got = hashlib.md5(data).hexdigest()
            if blob_hex and got != blob_hex:
                part.unlink(missing_ok=True)
                return {"phase": "new", "name": base, "size": blob.size, "blob_md5": blob_hex,
                        "local_path": "", "local_md5": got, "status": "download_hash_mismatch"}
            part.write_bytes(data)
            os.replace(part, dest)
            return {"phase": "new", "name": base, "size": blob.size, "blob_md5": blob_hex,
                    "local_path": str(dest), "local_md5": got, "status": "downloaded"}
        except Exception as exc:  # noqa: BLE001 - report, never abort the batch
            part.unlink(missing_ok=True)
            return {"phase": "new", "name": base, "size": blob.size, "blob_md5": blob_hex,
                    "local_path": "", "local_md5": "", "status": "error: %s" % exc}

    done = 0
    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ensure, b): b for b in new_blobs}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1
            done += 1
            if done % 250 == 0:
                print("  new %d/%d  %s" % (done, len(new_blobs), counts), flush=True)

    report = {
        "old": {"blobs": len(old_blobs), "ok": old_ok, "no_local_copy": old_missing,
                "hash_mismatch": old_mismatch},
        "new": {"blobs": len(new_blobs), "status_counts": counts},
        "staged_files": len(list(STAGE.glob("*.bmp"))),
        "minutes": round((time.time() - started) / 60, 1),
    }
    (STAGE / "_verification_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    import csv as _csv
    with (STAGE / "_verification.csv").open("w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(report, indent=1), flush=True)


if __name__ == "__main__":
    main()
