#!/usr/bin/env python3
"""Download the two Armor (Azure Blob) ICube folders into the VM data directory.

Runs on the VM (stdlib + azure-storage-blob only; the VM python3 has no pandas).

SAFE BY DEFAULT
---------------
  ./download_armor_blobs.py --dry-run
      Lists what would be downloaded. Writes nothing. Reports per-prefix image
      counts, total bytes, non-image files that the extension filter drops,
      sample names, and free space at the destination. Exits non-zero if a
      prefix matches zero blobs (a silent zero-match looks like success and is
      the most likely failure mode).

  ./download_armor_blobs.py --dest /home/amd100-user/FMD_Data_26082026/fmd_temp_images
      Downloads. Every file lands as <name>.part, is verified against the size and
      MD5 reported by the service, then renamed atomically. A failed or truncated
      transfer is deleted, so a later re-run retries it instead of skipping it.
      Writes manifest.csv (provenance) next to the images.

CREDENTIALS
-----------
Read from $ARMOR_BLOB_CONNECTION_STRING, else from --conn-file (default
~/.fmd/armor_blob_conn, chmod 600). The file may hold either the full
connection string or the bare account key. Nothing is hard-coded.

EXIT CODES
----------
  0 ok   2 a prefix matched no blobs   3 not enough disk space   4 config/auth error
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import get_close_matches

DEFAULT_CONN_FILE = "~/.fmd/armor_blob_conn"
DEFAULT_ACCOUNT = "stjnjmakearmor"
DEFAULT_CONTAINER = "fmd-temp"
DEFAULT_PREFIXES = [
    "Updated ICube Objects 20260915/",
    "Updated ICube Categorical Classes 20260915/",
]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

EXIT_NOMATCH = 2
EXIT_NOSPACE = 3
EXIT_CONFIG = 4


# ---------------------------------------------------------------------------
# credentials
# ---------------------------------------------------------------------------

def load_connection_string(conn_file, account):
    """Full connection string from the environment, else from a file.

    Accepts either a complete connection string or a bare account key in the file.
    """
    env = os.environ.get("ARMOR_BLOB_CONNECTION_STRING", "").strip()
    if env:
        return env, "environment variable ARMOR_BLOB_CONNECTION_STRING"

    path = os.path.expanduser(conn_file)
    if not os.path.exists(path):
        sys.stderr.write(
            "No credential found.\n"
            "  Set ARMOR_BLOB_CONNECTION_STRING, or write the connection string to\n"
            "  {0} (chmod 600).\n".format(path)
        )
        sys.exit(EXIT_CONFIG)

    text = open(path, "r", encoding="utf-8").read().strip()
    if not text:
        sys.stderr.write("Credential file {0} is empty.\n".format(path))
        sys.exit(EXIT_CONFIG)

    if "AccountName=" in text:
        return text, path
    # bare account key
    conn = (
        "DefaultEndpointsProtocol=https;"
        "AccountName={0};"
        "AccountKey={1};"
        "EndpointSuffix=core.windows.net".format(account, text)
    )
    return conn, path + " (bare key)"


# ---------------------------------------------------------------------------
# listing
# ---------------------------------------------------------------------------

def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return "{0:.1f} {1}".format(n, unit)
        n /= 1024.0
    return "{0:.1f} PB".format(n)


def scan_prefix(container, prefix, exts):
    """Return (images, skipped) for one prefix.

    images: list of dicts {name, size, etag, md5, rel}
    skipped: list of non-image blob names dropped by the extension filter
    """
    images = []
    skipped = []
    for blob in container.list_blobs(name_starts_with=prefix):
        name = blob.name
        if name.endswith("/"):
            continue
        ext = os.path.splitext(name)[1].lower()
        if exts and ext not in exts:
            skipped.append(name)
            continue
        md5 = None
        try:
            md5 = blob.content_settings.content_md5
            md5 = md5.hex() if md5 is not None else None
        except Exception:
            md5 = None
        images.append({
            "name": name,
            "size": blob.size,
            "etag": blob.etag,
            "md5": md5,
            "rel": name[len(prefix):] if name.startswith(prefix) else name,
        })
    return images, skipped


def top_level_folders(container, cap=250000):
    """Distinct first path segments in the container, for zero-match diagnosis."""
    found = set()
    seen = 0
    for blob in container.list_blobs():
        seen += 1
        head = blob.name.split("/")[0]
        found.add(head)
        if seen >= cap:
            break
    return sorted(found), seen >= cap


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

def download_one(container, blob_name, dest_path, expected_size, expected_md5, args):
    """Download one blob atomically, verifying size and MD5 before the rename."""
    part_path = dest_path + ".part"
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    last_error = None

    for attempt in range(1, args.attempts + 1):
        try:
            with open(part_path, "wb") as handle:
                stream = container.download_blob(
                    blob_name,
                    max_concurrency=args.max_concurrency,
                    connection_timeout=args.connection_timeout,
                    read_timeout=args.read_timeout,
                )
                stream.readinto(handle)

            got = os.path.getsize(part_path)
            if expected_size is not None and got != expected_size:
                raise IOError(
                    "size mismatch: got {0} bytes, service reported {1}".format(
                        got, expected_size
                    )
                )

            if args.verify_md5 and expected_md5:
                digest = hashlib.md5()
                with open(part_path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected_md5:
                    raise IOError(
                        "md5 mismatch: got {0}, service reported {1}".format(
                            digest.hexdigest(), expected_md5
                        )
                    )

            os.replace(part_path, dest_path)  # atomic within the same filesystem
            return got

        except Exception as exc:  # transient network errors, mismatch, disk full
            last_error = exc
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
            if attempt < args.attempts:
                time.sleep(min(2 ** attempt, 15))

    raise last_error


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Download selected Armor blob folders into the VM data directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dest", default=None,
                        help="destination directory (default: the VM fmd_temp_images path)")
    parser.add_argument("--prefix", action="append", default=None,
                        help="blob prefix to download; repeatable (default: the two ICube 20260915 folders)")
    parser.add_argument("--conn-file", default=DEFAULT_CONN_FILE,
                        help="file holding the connection string or bare account key")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT, help="storage account name")
    parser.add_argument("--container", default=DEFAULT_CONTAINER, help="container name")
    parser.add_argument("--dry-run", action="store_true",
                        help="list only; write nothing")
    parser.add_argument("--overwrite", action="store_true",
                        help="re-download files that already exist (default: skip them)")
    parser.add_argument("--strip-prefix", action="store_true",
                        help="drop the blob folder name from the local path (merges both folders)")
    parser.add_argument("--jobs", type=int, default=8, help="parallel blob downloads")
    parser.add_argument("--max-concurrency", type=int, default=4,
                        help="parallel chunk streams inside one blob")
    parser.add_argument("--attempts", type=int, default=3, help="attempts per blob")
    parser.add_argument("--no-md5", dest="verify_md5", action="store_false",
                        help="skip the MD5 check (size is still checked)")
    parser.set_defaults(verify_md5=True)
    parser.add_argument("--connection-timeout", type=int, default=60)
    parser.add_argument("--read-timeout", type=int, default=600)
    parser.add_argument("--limit", type=int, default=None,
                        help="download at most N blobs (smoke test)")
    parser.add_argument("--dump-names", default=None,
                        help="write every matched blob name and size to this CSV, then stop")
    parser.add_argument("--force", action="store_true",
                        help="proceed even if free space looks insufficient")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.dest is None:
        args.dest = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
    prefixes = args.prefix if args.prefix else list(DEFAULT_PREFIXES)

    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import AzureError

    conn_str, source = load_connection_string(args.conn_file, args.account)
    print("credentials : {0}".format(source))
    print("container   : {0}".format(args.container))
    print("destination : {0}".format(args.dest))
    print("prefixes    : {0}".format(len(prefixes)))

    try:
        service = BlobServiceClient.from_connection_string(conn_str)
        container = service.get_container_client(args.container)
    except Exception as exc:
        sys.stderr.write("Could not build the client: {0}\n".format(exc))
        return EXIT_CONFIG

    # ---- list ------------------------------------------------------------
    total_bytes = 0
    total_images = 0
    total_skipped = 0
    plan = []

    for prefix in prefixes:
        print("\nlisting prefix: {0!r}".format(prefix))
        try:
            images, skipped = scan_prefix(container, prefix, IMAGE_EXTS)
        except AzureError as exc:
            sys.stderr.write("  listing failed: {0}\n".format(exc))
            return EXIT_CONFIG

        size = sum(img["size"] for img in images)
        total_bytes += size
        total_images += len(images)
        total_skipped += len(skipped)

        print("  images              : {0}".format(len(images)))
        print("  bytes               : {0} ({1} bytes)".format(human(size), size))
        print("  non-image files     : {0} (dropped by the extension filter)".format(len(skipped)))

        if images:
            names = sorted(img["name"] for img in images)
            print("  first name          : {0}".format(names[0]))
            print("  last name           : {0}".format(names[-1]))
            classes = sorted({img["rel"].split("/")[0] for img in images if "/" in img["rel"]})
            print("  subfolders          : {0}".format(len(classes)))
            if classes:
                preview = ", ".join(classes[:8])
                print("  subfolder names     : {0}{1}".format(
                    preview, " ..." if len(classes) > 8 else ""))
            exts = {}
            for img in images:
                ext = os.path.splitext(img["name"])[1].lower()
                exts[ext] = exts.get(ext, 0) + 1
            print("  extensions          : {0}".format(
                ", ".join("{0}={1}".format(k, v) for k, v in sorted(exts.items()))))
        else:
            print("\n  ZERO MATCH for {0!r}".format(prefix))
            try:
                folders, truncated = top_level_folders(container)
            except AzureError as exc:
                sys.stderr.write("  could not list the container: {0}\n".format(exc))
                folders, truncated = [], False
            print("  top level folders in the container: {0}".format(len(folders)))
            for folder in folders[:40]:
                print("    {0!r}".format(folder))
            if truncated:
                print("    (listing truncated; more folders may exist)")
            guess = get_close_matches(prefix.rstrip("/"), folders, n=3, cutoff=0.5)
            if guess:
                print("  closest matches: {0}".format(", ".join(repr(g) for g in guess)))
            print("  refusing to continue: fix the prefix and re-run")
            return EXIT_NOMATCH

        for img in images:
            plan.append((prefix, img))

    print("\n{0} image(s) matched across {1} prefix(es); {2} total; {3} non-image file(s) dropped".format(
        total_images, len(prefixes), human(total_bytes), total_skipped))

    if args.dump_names:
        with open(args.dump_names, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["prefix", "blob_name", "bytes", "etag", "content_md5"])
            for prefix, img in plan:
                writer.writerow([prefix, img["name"], img["size"], img["etag"], img["md5"]])
        print("wrote {0}".format(args.dump_names))

    if total_images == 0:
        print("nothing to download")
        return EXIT_NOMATCH

    # ---- dedupe and decide what is missing -------------------------------
    seen = set()
    todo = []
    skipped_existing = 0
    for prefix, img in plan:
        if img["name"] in seen:            # overlapping prefixes must not race
            continue
        seen.add(img["name"])
        rel = img["rel"] if args.strip_prefix else img["name"]
        dest_path = os.path.join(args.dest, rel)
        if not args.overwrite and os.path.exists(dest_path):
            skipped_existing += 1
            continue
        todo.append((img, dest_path))

    if args.limit is not None:
        todo = todo[:args.limit]

    need = sum(img["size"] for img, _ in todo)
    print("\nmissing on disk     : {0}".format(len(todo)))
    print("already on disk     : {0}".format(skipped_existing))
    print("bytes to transfer   : {0} ({1} bytes)".format(human(need), need))

    if args.dry_run:
        print("\nDRY RUN: nothing written.")
        return 0

    # ---- space check -----------------------------------------------------
    probe = args.dest
    while probe and not os.path.isdir(probe):
        probe = os.path.dirname(probe)
    if not probe:
        probe = os.path.abspath(os.sep)
    free = shutil.disk_usage(probe).free
    print("free space at {0}: {1}".format(probe, human(free)))
    if need > free * 0.95 and not args.force:
        sys.stderr.write(
            "Not enough free space: need {0}, free {1}. Use --force to override.\n".format(
                human(need), human(free))
        )
        return EXIT_NOSPACE

    # ---- download --------------------------------------------------------
    os.makedirs(args.dest, exist_ok=True)
    manifest_path = os.path.join(args.dest, "manifest.csv")
    started = time.time()
    done = 0
    failed = 0
    written_bytes = 0
    failures = []
    rows = []

    print("\ndownloading {0} file(s) with {1} worker(s)".format(len(todo), args.jobs))
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {}
        for img, dest_path in todo:
            future = pool.submit(download_one, container, img["name"], dest_path,
                                 img["size"], img["md5"], args)
            futures[future] = (img, dest_path)

        for index, future in enumerate(as_completed(futures), 1):
            img, dest_path = futures[future]
            try:
                size = future.result()
                done += 1
                written_bytes += size
                rows.append([img["name"], dest_path, img["size"], img["etag"],
                             img["md5"], "downloaded", ""])
            except Exception as exc:
                failed += 1
                failures.append((img["name"], str(exc)))
                rows.append([img["name"], dest_path, img["size"], img["etag"],
                             img["md5"], "failed", str(exc)])
            if index % 25 == 0 or index == len(futures):
                elapsed = time.time() - started
                rate = written_bytes / elapsed / 1024 / 1024 if elapsed > 0 else 0
                print("  {0}/{1}  downloaded={2} failed={3}  {4}  {5:.1f} MB/s".format(
                    index, len(futures), done, failed, human(written_bytes), rate))

    with open(manifest_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["blob_name", "local_path", "bytes", "etag", "content_md5",
                         "status", "error"])
        writer.writerows(sorted(rows))

    failure_path = manifest_path.replace(".csv", "_failures.csv")
    if failures:
        with open(failure_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["blob_name", "error"])
            writer.writerows(failures)

    print("\ndownloaded          : {0}".format(done))
    print("failed              : {0}".format(failed))
    print("already on disk     : {0}".format(skipped_existing))
    print("bytes transferred   : {0}".format(human(written_bytes)))
    print("manifest            : {0}".format(manifest_path))
    if failures:
        print("failures            : {0}".format(failure_path))
        for name, error in failures[:10]:
            print("  FAILED {0}: {1}".format(name, error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
