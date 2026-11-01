#!/usr/bin/env python3
"""Census and content identity for the ICube library folders (ticket 007).

Read only over the shared VM. Stdlib only. Chunked 1 MiB reads keep memory
flat. Output is deterministic: every collection is written in an explicit
sort order, so a rerun under a different PYTHONHASHSEED is byte-identical.

Modes
  hash       walk the source folders, md5 every .bmp, print file_manifest.csv
  aggregate  read file_manifest.csv, write picture_table.csv and census.json

The aggregation step reads ONLY file_manifest.csv, so the distinct picture
count is reproducible from the manifest alone.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys

CHUNK = 1024 * 1024  # 1 MiB

# The three library folders plus the production image folder, relative to root.
LIBRARY_FOLDERS = [
    "Updated ICube Objects 20260915",
    "Updated ICube Categorical Classes 20260915",
    "ICube Defects Library",
]
PRODUCTION_FOLDER = "PRODUCTION_20260925/images"
ALL_FOLDERS_ORDER = LIBRARY_FOLDERS + [PRODUCTION_FOLDER]

FOLDER_GROUP = {
    "ICube Defects Library": "Library",
    "Updated ICube Objects 20260915": "Updated",
    "Updated ICube Categorical Classes 20260915": "Updated",
    "PRODUCTION_20260925/images": "Production",
}

MANIFEST_COLUMNS = ["path", "folder", "folder_group", "bytes", "md5"]
PICTURE_COLUMNS = [
    "md5", "bytes", "winning_path", "all_folders", "n_copies",
    "line", "capture_date", "in_production_batch",
]

LINE_RE = re.compile(r"_(L\d{2})_")
DATE_RE = re.compile(r"^(\d{8})_")


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def parse_line(basename):
    m = LINE_RE.search(basename)
    return m.group(1) if m else ""


def parse_date(basename):
    m = DATE_RE.match(basename)
    return m.group(1) if m else ""


def basename_of(relpath):
    return relpath.rsplit("/", 1)[-1]


def subfolder_of(relpath, folder):
    """Return the second path segment (class folder) or '' for a flat folder."""
    parts = relpath.split("/")
    # parts[0] is the source folder for the three library trees; the production
    # tree carries two segments (PRODUCTION_20260925/images).
    if folder == PRODUCTION_FOLDER:
        rest = parts[2:]
    else:
        rest = parts[1:]
    return rest[0] if len(rest) > 1 else ""


def walk_manifest(root):
    rows = []
    for folder in ALL_FOLDERS_ORDER:
        base = os.path.join(root, folder)
        group = FOLDER_GROUP[folder]
        for dirpath, dirnames, filenames in os.walk(base):
            for name in filenames:
                if not name.lower().endswith(".bmp"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                rows.append({
                    "path": rel,
                    "folder": folder,
                    "folder_group": group,
                    "bytes": str(os.path.getsize(full)),
                })
    # Deterministic order regardless of filesystem walk order.
    rows.sort(key=lambda r: (ALL_FOLDERS_ORDER.index(r["folder"]), r["path"]))
    total = len(rows)
    for i, r in enumerate(rows, 1):
        r["md5"] = md5_file(os.path.join(root, r["path"]))
        if i % 500 == 0 or i == total:
            sys.stderr.write("hashed %d/%d\n" % (i, total))
            sys.stderr.flush()
    return rows


def write_manifest(rows, stream):
    w = csv.DictWriter(stream, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)


def read_manifest(path):
    rows = []
    with open(path, "r", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "path": r["path"],
                "folder": r["folder"],
                "folder_group": r["folder_group"],
                "bytes": int(r["bytes"]),
                "md5": r["md5"],
            })
    return rows


def folder_sort_key(folder):
    return ALL_FOLDERS_ORDER.index(folder) if folder in ALL_FOLDERS_ORDER else len(ALL_FOLDERS_ORDER)


def build_picture_rows(rows):
    by_hash = {}
    for r in rows:
        by_hash.setdefault(r["md5"], []).append(r)

    pictures = []
    for md5 in sorted(by_hash):
        group = by_hash[md5]
        library = [r for r in group if r["folder_group"] != "Production"]
        production = [r for r in group if r["folder_group"] == "Production"]

        if library:
            library_sorted = sorted(
                library, key=lambda r: (LIBRARY_FOLDERS.index(r["folder"]), r["path"]))
            winner = library_sorted[0]
        else:
            # Production only picture: it has no library home.
            winner = sorted(production, key=lambda r: r["path"])[0]

        folders = sorted({r["folder"] for r in group}, key=folder_sort_key)
        name = basename_of(winner["path"])
        pictures.append({
            "md5": md5,
            "bytes": winner["bytes"],
            "winning_path": winner["path"],
            "all_folders": ";".join(folders),
            "n_copies": len(group),
            "line": parse_line(name),
            "capture_date": parse_date(name),
            "in_production_batch": "true" if production else "false",
        })
    return pictures, by_hash


def write_pictures(pictures, path):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PICTURE_COLUMNS, lineterminator="\n")
        w.writeheader()
        for p in pictures:
            w.writerow(p)


def build_census(rows, pictures, by_hash):
    # Per folder and per folder group file and byte counts.
    per_folder = {}
    for r in rows:
        e = per_folder.setdefault(r["folder"], {"files": 0, "bytes": 0})
        e["files"] += 1
        e["bytes"] += r["bytes"]
    per_folder = {k: per_folder[k] for k in sorted(per_folder, key=folder_sort_key)}

    per_group = {}
    for r in rows:
        e = per_group.setdefault(r["folder_group"], {"files": 0, "bytes": 0})
        e["files"] += 1
        e["bytes"] += r["bytes"]
    per_group = {k: per_group[k] for k in sorted(per_group)}

    # Per line, over files and over distinct pictures.
    per_line_files = {}
    for r in rows:
        line = parse_line(basename_of(r["path"]))
        per_line_files[line] = per_line_files.get(line, 0) + 1
    per_line_pictures = {}
    for p in pictures:
        per_line_pictures[p["line"]] = per_line_pictures.get(p["line"], 0) + 1

    def line_block(line):
        return {
            "files": per_line_files.get(line, 0),
            "distinct_pictures": per_line_pictures.get(line, 0),
        }

    named_lines = sorted(l for l in set(per_line_pictures) | set(per_line_files) if l)
    per_line = {l: line_block(l) for l in named_lines}
    no_line = {
        "files": per_line_files.get("", 0),
        "distinct_pictures": per_line_pictures.get("", 0),
    }

    # No date tag.
    no_date_files = sum(1 for r in rows if not parse_date(basename_of(r["path"])))
    no_date_pictures = sum(1 for p in pictures if not p["capture_date"])

    # Duplicates subfolder.
    dup_rows = [r for r in rows
                if subfolder_of(r["path"], r["folder"]) == "duplicates"]
    dup_hashes = {r["md5"] for r in dup_rows}
    lib_hashes = {r["md5"] for r in rows if r["folder_group"] != "Production"}
    dup_repeat = sorted(h for h in dup_hashes if h in lib_hashes)
    dup_unique = sorted(h for h in dup_hashes if h not in lib_hashes)

    # Cross-folder duplicates: one content in more than one source folder.
    folders_per_hash = {}
    for r in rows:
        folders_per_hash.setdefault(r["md5"], set()).add(r["folder"])
    cross_folder = sorted(h for h, fs in folders_per_hash.items() if len(fs) > 1)

    # Repeated content anywhere (n_copies > 1).
    repeated = sorted(h for h, g in by_hash.items() if len(g) > 1)

    # Production match against the library.
    prod_rows = [r for r in rows if r["folder_group"] == "Production"]
    lib_names = {basename_of(r["path"]) for r in rows if r["folder_group"] != "Production"}
    prod_matched_hash = 0
    prod_basename_only = 0
    prod_new = []
    for r in prod_rows:
        name = basename_of(r["path"])
        hash_in_lib = r["md5"] in lib_hashes
        name_in_lib = name in lib_names
        if hash_in_lib:
            prod_matched_hash += 1
        elif name_in_lib:
            prod_basename_only += 1
        else:
            prod_new.append(r["path"])

    prod_distinct = len({r["md5"] for r in prod_rows})
    prod_distinct_matched = len({r["md5"] for r in prod_rows} & lib_hashes)

    census = {
        "universe": "three library folders plus the production image folder",
        "distinct_pictures_total": len(pictures),
        "distinct_pictures_in_library": len(
            [p for p in pictures if "Production" not in p["all_folders"]]),
        "totals": {
            "files_on_disk": len(rows),
            "bytes_on_disk": sum(r["bytes"] for r in rows),
            "library_files": sum(1 for r in rows if r["folder_group"] != "Production"),
            "library_bytes": sum(r["bytes"] for r in rows if r["folder_group"] != "Production"),
            "production_files": len(prod_rows),
            "production_bytes": sum(r["bytes"] for r in prod_rows),
            "distinct_pictures": len(pictures),
            "repeated_content_hashes": len(repeated),
        },
        "per_folder": per_folder,
        "per_folder_group": per_group,
        "per_line": per_line,
        "line_missing_tag": no_line,
        "date_missing_tag": {
            "files": no_date_files,
            "distinct_pictures": no_date_pictures,
        },
        "duplicates_subfolder": {
            "folder": "Updated ICube Categorical Classes 20260915/duplicates",
            "files": len(dup_rows),
            "distinct_hashes": len(dup_hashes),
            "repeat_library_pictures": len(dup_repeat),
            "unique_to_duplicates": len(dup_unique),
        },
        "content_identity": {
            "hashes_with_more_than_one_copy": len(repeated),
            "hashes_in_more_than_one_folder": len(cross_folder),
            "copy_count_distribution": copy_distribution(by_hash),
        },
        "production_match": {
            "production_files": len(prod_rows),
            "production_distinct_pictures": prod_distinct,
            "matched_by_hash_files": prod_matched_hash,
            "matched_by_hash_distinct_pictures": prod_distinct_matched,
            "matched_by_basename_only_files": prod_basename_only,
            "not_in_library_files": len(prod_new),
            "adds_new_picture": len(prod_new) > 0,
            "not_in_library_paths": prod_new,
        },
    }
    return census


def copy_distribution(by_hash):
    dist = {}
    for group in by_hash.values():
        dist[len(group)] = dist.get(len(group), 0) + 1
    return {str(k): dist[k] for k in sorted(dist)}


def mode_hash(args):
    rows = walk_manifest(args.root)
    write_manifest(rows, sys.stdout)


def mode_aggregate(args):
    rows = read_manifest(args.manifest)
    pictures, by_hash = build_picture_rows(rows)
    os.makedirs(args.outdir, exist_ok=True)
    write_pictures(pictures, os.path.join(args.outdir, "picture_table.csv"))
    census = build_census(rows, pictures, by_hash)
    with open(os.path.join(args.outdir, "census.json"), "w", newline="") as fh:
        fh.write(json.dumps(census, indent=2, sort_keys=True))
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)

    h = sub.add_parser("hash", help="md5 every .bmp and print file_manifest.csv")
    h.add_argument("--root", required=True)
    h.set_defaults(func=mode_hash)

    a = sub.add_parser("aggregate", help="build picture_table.csv and census.json")
    a.add_argument("--manifest", required=True)
    a.add_argument("--outdir", required=True)
    a.set_defaults(func=mode_aggregate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
