#!/usr/bin/env python3
"""Independent re-derivation of the Clear analysis and the pooled dataset, from the files on the VM.

Reads the three delivered folders, hashes every image itself, rebuilds the pool with the three
rules, and diffs the result against the numbers we published. Stdlib only.
"""
import csv
import hashlib
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

BASE = "/home/amd100-user/FMD_Data_26082026/fmd_temp_images"
LIB = "ICube Defects Library"
CAT = "Updated ICube Categorical Classes 20260915"
OBJ = "Updated ICube Objects 20260915"
FOLDERS = [LIB, CAT, OBJ]
IMG_EXT = (".bmp", ".png", ".jpg", ".jpeg", ".tif", ".tiff")
MANIFEST = os.path.join(BASE, "manifest.csv")

NAME_MAP = {"Low Dose": "Low Dose Obstructing Region of Interest"}
NOT_A_CLASS = {"Clear", "HEMA", "duplicates"}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return path, h.hexdigest()


def main():
    recs = []          # (folder, class, basename, path, size)
    skipped = []
    for folder in FOLDERS:
        root = os.path.join(BASE, folder)
        for cls in sorted(os.listdir(root)):
            cdir = os.path.join(root, cls)
            if not os.path.isdir(cdir):
                skipped.append(os.path.join(folder, cls))
                continue
            for name in sorted(os.listdir(cdir)):
                p = os.path.join(cdir, name)
                if not os.path.isfile(p):
                    continue
                if not name.lower().endswith(IMG_EXT):
                    skipped.append(os.path.join(folder, cls, name))
                    continue
                recs.append((folder, cls, name, p, os.path.getsize(p)))

    print("image files found: {:,}".format(len(recs)))
    for folder in FOLDERS:
        print("   {:<48} {:,}".format(folder, sum(1 for r in recs if r[0] == folder)))
    print("non-image entries skipped: {}".format(skipped))

    with Pool(16) as pool:
        hashes = dict(pool.map(md5, [r[3] for r in recs], chunksize=16))
    print("hashed {:,} files".format(len(hashes)))

    # cross-check against the Azure listing stored at download time
    manifest = {}
    with open(MANIFEST, newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            if row.get("local_path"):
                manifest[row["local_path"]] = row.get("content_md5", "").strip().lower()
    mismatch, missing = [], []
    for folder, cls, name, path, size in recs:
        want = manifest.get(path)
        if want is None:
            missing.append(path)
        elif want and want != hashes[path]:
            mismatch.append((path, want, hashes[path]))
    print("\nagainst manifest.csv (Azure content hashes):")
    print("   files not in the manifest : {}".format(len(missing)))
    print("   hash mismatches           : {}".format(len(mismatch)))
    for m in mismatch[:5]:
        print("      ", m)

    # ------------------------------------------------------------ the pool, same rules as the report
    lib_classes = {r[1] for r in recs if r[0] == LIB}
    defect_classes = {NAME_MAP.get(c, c) for c in lib_classes}

    def mapped(c):
        return NAME_MAP.get(c, c)

    def is_defect(folder, cls):
        return mapped(cls) in defect_classes and cls not in NOT_A_CLASS

    pic = defaultdict(lambda: {"labels": set(), "lib": set(), "lines": set(), "folders": set()})
    bad_name = []
    for folder, cls, name, path, size in recs:
        key = hashes[path]
        parts = name.split("_")
        line = parts[2] if len(parts) > 2 else ""
        if not (len(line) == 3 and line.startswith("L") and line[1:].isdigit()):
            bad_name.append(name)
        pic[key]["folders"].add(folder)
        if line:
            pic[key]["lines"].add(line)
        if is_defect(folder, cls):
            pic[key]["labels"].add(mapped(cls))
            if folder == LIB:
                pic[key]["lib"].add(mapped(cls))

    pool = Counter()
    for key, e in pic.items():
        if e["labels"]:
            cls = sorted(e["lib"])[0] if e["lib"] else sorted(e["labels"])[0]
            for ln in e["lines"]:
                pool[(cls, ln)] += 1

    LINES = sorted({ln for (c, ln) in pool}, key=lambda s: int(s[1:]))
    total_files = len(recs)
    unique = len(pic)
    pool_total = sum(pool.values())
    excluded = sum(1 for e in pic.values() if not e["labels"])
    two_labels = sum(1 for e in pic.values() if len(e["labels"]) > 1)
    multi_folder = sum(1 for e in pic.values() if len(e["folders"]) > 1)
    line_clash = sum(1 for e in pic.values() if len(e["lines"]) > 1)

    # ------------------------------------------------------------ the Clear analysis
    clear_keys = sorted({hashes[r[3]] for r in recs if r[0] == OBJ and r[1] == "Clear"})
    clear_shared, clear_only, breakdown = [], [], Counter()
    for key in clear_keys:
        labs = pic[key]["labels"]
        if labs:
            clear_shared.append(key)
            for lab in labs:
                breakdown[lab] += 1
        else:
            clear_only.append(key)
    clear_only_by_line = Counter()
    for key in clear_only:
        for ln in pic[key]["lines"]:
            clear_only_by_line[ln] += 1
    clear_shared_by_line = Counter()
    for key in clear_shared:
        for ln in pic[key]["lines"]:
            clear_shared_by_line[ln] += 1

    # ------------------------------------------------------------ expected numbers
    EXPECT = {
        "files_total_folders": (total_files, 12079),
        "unique_pictures": (unique, 10614),
        "pool_total": (pool_total, 8401),
        "excluded_no_defect_label": (excluded, 2213),
        "two_defect_labels": (two_labels, 51),
        "pictures_in_two_folders": (multi_folder, 1278),
        "line_clashes": (line_clash, 0),
        "clear_total": (len(clear_keys), 2333),
        "clear_shared": (len(clear_shared), 128),
        "clear_leftover": (len(clear_only), 2205),
    }
    for ln, want in (("L24", 2853), ("L25", 951), ("L26", 1220), ("L27", 1365), ("L31", 2012)):
        EXPECT["pool_" + ln] = (sum(v for (c, l), v in pool.items() if l == ln), want)
    for ln, want in (("L24", 1495), ("L25", 20), ("L26", 283), ("L27", 272), ("L31", 135)):
        EXPECT["clear_only_" + ln] = (clear_only_by_line[ln], want)
    for cls, want in (("Bubble", 37), ("Wet Package", 34), ("Dirty Strobe", 16),
                      ("Bubble Irregular", 16), ("Bubble Cluster", 15), ("Dirty Camera", 10)):
        EXPECT["clear_label_" + cls] = (breakdown[cls], want)
    MATRIX = {
        ("Missing Primary Package", "L24"): 1147, ("Multiple Lenses", "L26"): 674,
        ("Foreign Matter", "L27"): 549, ("Fiber", "L31"): 120,
        ("Dirty Camera", "L24"): 25, ("Bubble On 123", "L31"): 13,
        ("Wet Package", "L26"): 52, ("Bubble Irregular", "L27"): 21,
        ("Dirty Strobe", "L26"): 31, ("View Obstructed", "L31"): 38,
        ("HEMA Obstruction", "L24"): 151, ("Extraneous Polymer", "L26"): 134,
        ("Cavity Off Center", "L24"): 93, ("Package Misalignment", "L25"): 176,
        ("Lens Off Center", "L24"): 195, ("Missing Lens", "L24"): 183,
        ("Bubble", "L24"): 82, ("Bubble Cluster", "L24"): 18,
        ("Bubble On Edge", "L31"): 6, ("HEMA Fragment", "L24"): 5,
        ("Bubble Scatter", "L27"): 3,
        ("Low Dose Obstructing Region of Interest", "L31"): 1307,
    }
    for k, v in MATRIX.items():
        EXPECT["cell_" + k[0] + "_" + k[1]] = (pool.get(k, 0), v)

    print("\n================ results ================")
    print("files in the three folders : {:,}".format(total_files))
    print("unique pictures            : {:,}".format(unique))
    print("pooled dataset             : {:,} pictures across {} classes".format(pool_total, len(defect_classes)))
    print("no defect label            : {:,}".format(excluded))
    print("pictures in two folders    : {:,}".format(multi_folder))
    print("pictures with two labels   : {}".format(two_labels))
    print("line clashes               : {}".format(line_clash))
    print("basenames without a line   : {}".format(len(bad_name)))
    print("\nCLEAR")
    print("  total Clear pictures     : {:,}".format(len(clear_keys)))
    print("  also carrying a class    : {:,}".format(len(clear_shared)))
    print("  Clear only               : {:,}".format(len(clear_only)))
    print("  distinct classes the Clear pictures also carry: {}".format(len(breakdown)))
    for c, v in breakdown.most_common():
        print("      {:<40} {}".format(c, v))
    print("  Clear-only per line:")
    for ln in LINES:
        print("      {:<6} {:,}".format(ln, clear_only_by_line[ln]))
    print("  Clear-shared per line:")
    for ln in LINES:
        print("      {:<6} {}".format(ln, clear_shared_by_line[ln]))

    print("\n================ diff against the published numbers ================")
    fails = 0
    for k, (got, want) in EXPECT.items():
        ok = got == want
        fails += 0 if ok else 1
        print("  {:<44} {:>8}  expected {:>8}  {}".format(
            k, got, want, "ok" if ok else "MISMATCH"))
    print("\n{}".format("all {} checks matched".format(len(EXPECT)) if not fails
                        else "{} MISMATCHES".format(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
