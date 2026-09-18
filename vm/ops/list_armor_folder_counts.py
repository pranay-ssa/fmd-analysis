#!/usr/bin/env python3
"""Read-only: count the images in each class folder of the two Updated ICube
20260915 folders as they stand in the Armor blob container right now.

Purpose: the client's two bar charts disagree with our hash-verified file counts
in four cells (Dirty Strobe 43 vs 42, Lens Off Center 259 vs 258, Extraneous
Polymer 269 vs 267, Foreign Matter 1280 vs 1282). This tells us whether the
source folder itself has changed since the 2026-09-16 transfer, or whether the
charts were built by a different counting method.

Writes nothing and downloads nothing.

    python3 list_armor_folder_counts.py [--conn-file ~/.fmd/armor_blob_conn]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

from azure.storage.blob import BlobServiceClient

DEFAULT_CONN_FILE = "~/.fmd/armor_blob_conn"
DEFAULT_ACCOUNT = "stjnjmakearmor"
DEFAULT_CONTAINER = "fmd-temp"
PREFIXES = [
    "Updated ICube Objects 20260915/",
    "Updated ICube Categorical Classes 20260915/",
]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def load_connection_string(conn_file, account):
    env = os.environ.get("ARMOR_BLOB_CONNECTION_STRING", "").strip()
    if env:
        return env
    path = os.path.expanduser(conn_file)
    if not os.path.exists(path):
        sys.stderr.write("No credential at {0} and no ARMOR_BLOB_CONNECTION_STRING.\n".format(path))
        sys.exit(4)
    text = open(path, "r", encoding="utf-8").read().strip()
    if "AccountName=" in text:
        return text
    return ("DefaultEndpointsProtocol=https;AccountName={0};AccountKey={1};"
            "EndpointSuffix=core.windows.net".format(account, text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conn-file", default=DEFAULT_CONN_FILE)
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    ap.add_argument("--account", default=DEFAULT_ACCOUNT)
    ap.add_argument("--prefix", action="append", default=None,
                    help="restrict the per-class table to these prefixes (repeatable)")
    ap.add_argument("--no-container-totals", action="store_true")
    args = ap.parse_args()

    prefixes = args.prefix if args.prefix else list(PREFIXES)

    conn = load_connection_string(args.conn_file, args.account)
    svc = BlobServiceClient.from_connection_string(conn)
    container = svc.get_container_client(args.container)

    for prefix in prefixes:
        counts = Counter()
        sizes = Counter()
        other = Counter()
        total = 0
        for blob in container.list_blobs(name_starts_with=prefix):
            rest = blob.name[len(prefix):]
            parts = rest.split("/")
            ext = os.path.splitext(blob.name)[1].lower()
            if ext not in IMAGE_EXTS:
                other[rest] += 1
                continue
            sub = "/".join(parts[:-1]) if len(parts) > 1 else "(root)"
            counts[sub] += 1
            sizes[sub] += blob.size
            total += 1
        print("\n" + prefix)
        print("  image blobs: {0}".format(total))
        for cls in sorted(counts, key=lambda c: -counts[c]):
            print("    {0:45s} {1:6d}  {2:.1f} MB".format(cls, counts[cls], sizes[cls] / 1e6))
        for name, n in sorted(other.items()):
            print("    NON-IMAGE: {0}".format(name))

    if args.no_container_totals:
        return
    print("\ncontainer totals by top-level folder:")
    tops = Counter()
    for blob in container.list_blobs():
        top = blob.name.split("/")[0]
        tops[top] += 1
    for t in sorted(tops, key=lambda c: -tops[c])[:30]:
        print("    {0:50s} {1}".format(t, tops[t]))


if __name__ == "__main__":
    main()
