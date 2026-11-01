#!/usr/bin/env python3
"""Pull the 2026-09-25 production batch onto the VM: 7 CVAT annotation XMLs
plus the 1,047 images those XMLs reference, into an annotations/ + images/
layout that mirrors the blob containers.

Lives in the repo (vm/ops/), NOT on the VM: that box is shared, so we leave no
script behind. Run it by piping it over ssh, which writes only the data:

    ssh amd-a100-vm 'python3 - --dest <path>' < vm/ops/pull_20260925_batch.py

A plain run on the VM defaults to the standard destination.

SAFE BY DEFAULT
  * every file lands as <name>.part, is verified against the size and the
    content_md5 the service reports, then renamed atomically. A failed or
    truncated transfer is deleted so a re-run retries it instead of skipping it.
  * a prefix that matches zero blobs is a hard failure (exit 2), never success.
  * free space is checked against the destination itself (resolved, not its
    parent) before any byte moves.
  * existing files are skipped, not overwritten, so a re-run is a real retry.

EXIT CODES
  0 ok   2 no match   3 not enough space   4 config/auth error
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_CONN_FILE = os.path.expanduser("~/armor_blob_conn")
DEFAULT_ACCOUNT = "stjnjmakearmor"
ANN_CONTAINER = "fmd-cvat-annotations"
IMG_CONTAINER = "fmd-cvat-images"
ANN_PREFIX = "PRODUCTION_20260925/"
IMG_PREFIX = "FMD_PROD/PRODUCTION-20260925/"
DEST_ROOT = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images/PRODUCTION_20260925"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

EXIT_NOMATCH = 2
EXIT_NOSPACE = 3
EXIT_CONFIG = 4


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return "{0:.1f} {1}".format(n, unit)
        n /= 1024.0
    return "{0:.1f} PB".format(n)


def load_connection_string(conn_file, account):
    path = os.path.expanduser(conn_file)
    if not os.path.exists(path):
        sys.stderr.write("No credential file at {0}\n".format(path))
        sys.exit(EXIT_CONFIG)
    text = open(path, "r", encoding="utf-8").read().strip()
    if not text:
        sys.stderr.write("Credential file {0} is empty.\n".format(path))
        sys.exit(EXIT_CONFIG)
    if "AccountName=" in text:
        return text, path
    return ("DefaultEndpointsProtocol=https;AccountName={0};AccountKey={1};"
            "EndpointSuffix=core.windows.net".format(account, text)), path + " (bare key)"


def download_one(container, blob_name, dest_path, expected_size, expected_md5, args):
    """Download one blob atomically, verifying size and MD5 before the rename."""
    part_path = dest_path + ".part"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    last = None
    for attempt in range(1, args.attempts + 1):
        try:
            with open(part_path, "wb") as handle:
                container.download_blob(
                    blob_name,
                    max_concurrency=args.max_concurrency,
                    connection_timeout=args.connection_timeout,
                    read_timeout=args.read_timeout,
                ).readinto(handle)

            got = os.path.getsize(part_path)
            if expected_size is not None and got != expected_size:
                raise IOError("size mismatch: got {0}, service said {1}".format(got, expected_size))

            if expected_md5:
                digest = hashlib.md5()
                with open(part_path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected_md5:
                    raise IOError("md5 mismatch: got {0}, service said {1}".format(
                        digest.hexdigest(), expected_md5))

            os.replace(part_path, dest_path)
            return got
        except Exception as exc:
            last = exc
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
            if attempt < args.attempts:
                time.sleep(min(2 ** attempt, 15))
    raise last


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Pull the 2026-09-25 production batch (annotations + its 1047 images).")
    p.add_argument("--conn-file", default=DEFAULT_CONN_FILE)
    p.add_argument("--account", default=DEFAULT_ACCOUNT)
    p.add_argument("--dest", default=DEST_ROOT)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--max-concurrency", type=int, default=4)
    p.add_argument("--attempts", type=int, default=3)
    p.add_argument("--connection-timeout", type=int, default=60)
    p.add_argument("--read-timeout", type=int, default=600)
    p.add_argument("--limit", type=int, default=None, help="download at most N files (smoke test)")
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    ann_dest = os.path.join(args.dest, "annotations")
    img_dest = os.path.join(args.dest, "images")

    from azure.storage.blob import BlobServiceClient

    conn_str, source = load_connection_string(args.conn_file, args.account)
    print("credentials : {0}".format(source))
    print("dest root   : {0}".format(args.dest))
    print("  annotations -> {0}".format(ann_dest))
    print("  images      -> {0}".format(img_dest))

    service = BlobServiceClient.from_connection_string(conn_str)
    ann = service.get_container_client(ANN_CONTAINER)
    img = service.get_container_client(IMG_CONTAINER)

    # ---- pass 1: annotation XMLs, and the image names they reference -------
    plan = []          # (blob_name, dest_path, size, etag, md5, kind)
    referenced = set()
    n_ann = 0
    for blob in ann.list_blobs(name_starts_with=ANN_PREFIX):
        name = blob.name
        if name.endswith("/"):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext != ".xml":
            print("NOTE: non-xml file in the annotations folder, pulled anyway: {0}".format(name))
        md5 = None
        try:
            md5 = blob.content_settings.content_md5
            md5 = md5.hex() if md5 else None
        except Exception:
            md5 = None
        dest = os.path.join(ann_dest, os.path.basename(name))
        plan.append((name, dest, blob.size, blob.etag, md5, "annotation"))
        n_ann += 1

    print("\n--- annotations ({0}) ---".format(ANN_CONTAINER))
    print("files matched : {0}".format(n_ann))
    if n_ann == 0:
        sys.stderr.write("ZERO MATCH on {0!r} in {1}. Refusing to continue.\n".format(ANN_PREFIX, ANN_CONTAINER))
        return EXIT_NOMATCH

    # the image names come from the XML we are about to download; fetch them
    # from the service directly so a dry run does not write anything.
    # NOTE on parser safety: stdlib ElementTree is XXE/billion-laughs sensitive,
    # but this input is our own team's CVAT export from our own storage account,
    # not untrusted web content, so no external entities or network fetches are
    # reachable here. If this ever parses a vendor-supplied file, switch to
    # defusedxml.
    import xml.etree.ElementTree as ET
    for blob_name, _, _, _, _, kind in list(plan):
        if kind != "annotation":
            continue
        raw = ann.download_blob(blob_name).readall()
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            sys.stderr.write("could not parse {0}: {1}\n".format(blob_name, exc))
            return EXIT_CONFIG
        for im in root.iter("image"):
            nm = im.get("name")
            if nm:
                referenced.add(nm)
    print("images referenced by the annotations: {0}".format(len(referenced)))

    # ---- pass 2: the referenced images ------------------------------------
    print("\n--- images ({0}) ---".format(IMG_CONTAINER))
    n_img = 0
    img_bytes = 0
    missing = []
    for blob in img.list_blobs(name_starts_with=IMG_PREFIX):
        name = blob.name
        if name in referenced:
            md5 = None
            try:
                md5 = blob.content_settings.content_md5
                md5 = md5.hex() if md5 else None
            except Exception:
                md5 = None
            dest = os.path.join(img_dest, os.path.basename(name))
            plan.append((name, dest, blob.size, blob.etag, md5, "image"))
            n_img += 1
            img_bytes += blob.size or 0

    found = {b for b, d, s, e, m, k in plan if k == "image"}
    missing = sorted(referenced - found)
    print("referenced images found in blob : {0}".format(n_img))
    print("referenced images MISSING       : {0}".format(len(missing)))
    for n in missing[:10]:
        print("    {0}".format(n))
    print("image bytes                     : {0} ({1})".format(human(img_bytes), img_bytes))
    if n_img == 0:
        sys.stderr.write("ZERO MATCH for the referenced images in {0}. Refusing to continue.\n".format(IMG_CONTAINER))
        return EXIT_NOMATCH

    # ---- what is already on disk ------------------------------------------
    todo = []
    skipped_existing = 0
    for blob_name, dest, size, etag, md5, kind in plan:
        if not args.overwrite and os.path.exists(dest):
            skipped_existing += 1
            continue
        todo.append((blob_name, dest, size, etag, md5, kind))

    if args.limit is not None:
        todo = todo[:args.limit]

    need = sum(t[2] or 0 for t in todo)
    print("\nmatched files   : {0} ({1} annotation xml + {2} images)".format(len(plan), n_ann, n_img))
    print("already on disk : {0}".format(skipped_existing))
    print("to transfer     : {0} ({1})".format(len(todo), human(need)))

    if args.dry_run:
        print("\nDRY RUN: nothing written.")
        return 0

    # ---- free space, resolved at the destination itself -------------------
    probe = args.dest
    while probe and not os.path.isdir(probe):
        probe = os.path.dirname(probe)
    if not probe:
        probe = os.path.abspath(os.sep)
    free = shutil.disk_usage(probe).free
    print("\nfree space at {0}: {1}".format(probe, human(free)))
    if need > free * 0.95 and not args.force:
        sys.stderr.write("Not enough free space: need {0}, free {1}. Use --force to override.\n".format(
            human(need), human(free)))
        return EXIT_NOSPACE

    # ---- download ---------------------------------------------------------
    os.makedirs(ann_dest, exist_ok=True)
    os.makedirs(img_dest, exist_ok=True)
    manifest_path = os.path.join(args.dest, "manifest.csv")
    started = time.time()
    done = failed = written = 0
    rows = []

    print("downloading {0} file(s) with {1} worker(s)\n".format(len(todo), args.jobs))
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {}
        for blob_name, dest, size, etag, md5, kind in todo:
            fut = pool.submit(download_one, img if kind == "image" else ann,
                              blob_name, dest, size, md5, args)
            futures[fut] = (blob_name, dest, size, etag, md5, kind)

        for i, fut in enumerate(as_completed(futures), 1):
            blob_name, dest, size, etag, md5, kind = futures[fut]
            try:
                got = fut.result()
                done += 1
                written += got
                rows.append([kind, blob_name, dest, size, etag, md5, "downloaded", ""])
            except Exception as exc:
                failed += 1
                rows.append([kind, blob_name, dest, size, etag, md5, "failed", str(exc)])
            if i % 50 == 0 or i == len(todo):
                el = time.time() - started
                rate = written / el / 1024.0 / 1024.0 if el > 0 else 0
                print("  {0}/{1}  ok={2} fail={3}  {4}  {5:.1f} MB/s".format(
                    i, len(todo), done, failed, human(written), rate))

    with open(manifest_path, "w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle)
        w.writerow(["kind", "blob_name", "local_path", "bytes", "etag", "content_md5", "status", "error"])
        w.writerows(rows)
    failed_rows = [r for r in rows if r[6] != "downloaded"]
    fail_path = os.path.join(args.dest, "failures.csv")
    if failed_rows:
        with open(fail_path, "w", newline="", encoding="utf-8") as handle:
            w = csv.writer(handle)
            w.writerow(["kind", "blob_name", "local_path", "bytes", "etag", "content_md5", "status", "error"])
            w.writerows(failed_rows)

    print("\n--- summary ---")
    print("downloaded : {0}".format(done))
    print("failed     : {0}".format(failed))
    print("bytes      : {0} ({1})".format(human(written), written))
    print("elapsed    : {0:.0f}s".format(time.time() - started))
    print("manifest   : {0}".format(manifest_path))
    if failed_rows:
        print("failures   : {0}".format(fail_path))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
