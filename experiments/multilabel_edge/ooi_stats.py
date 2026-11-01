"""OOI tag analysis for the 24-file export.

Per guide object class and file group: pictures, OOI tags (boxes), the size-flag subset, and
the tags-per-picture median and maximum. Plus the distribution of OOI tags per picture.

Reads the resolved annotation of record (production rows only) and writes two frozen CSVs the
workbook builder formats:

  run/eda_batch24_20261028/ooi_table.csv        group, code, class, pictures, tags, flagged, mean, median, max
  run/eda_batch24_20261028/ooi_distribution.csv group, bucket, pictures

Checks, printed and enforced: the per-class picture and tag counts match class_table.csv, and
the distribution sums to the number of pictures carrying at least one OOI tag.
"""
import csv
import os
import statistics
from collections import Counter, defaultdict

import defusedxml.ElementTree as ET  # noqa: F401  (kept for parity with the other scripts)

ROOT = "D:/fmd-analysis"
SRC = f"{ROOT}/run/eda_full_24files_20261028/resolved_labels.csv"
CT = f"{ROOT}/run/eda_batch24_20261028/class_table.csv"
OUT = f"{ROOT}/run/eda_batch24_20261028"

FOLD = {"bubble_irregular", "stretched_bubble"}
CODES = {"Bubble": "P2_BB", "Bubble Cluster": "P2_BC", "Wet Package": "P2_WP",
         "Surface Groove": "P1_SG", "Fiber": "P3_FIB", "Extraneous Polymer": "P3_EP",
         "HEMA": "P3_HE", "Foreign Matter": "P3_FM"}
ORDER = ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
         "Extraneous Polymer", "HEMA", "Foreign Matter"]
GATE = {"foreign_matter": "Foreign Matter", "fiber": "Fiber",
        "extraneous_polymer": "Extraneous Polymer", "hema": "HEMA"}
GROUPS = ["7 revised", "17 new", "24 total"]
BUCKETS = [("1 tag", 1, 1), ("2 to 3 tags", 2, 3), ("4 to 9 tags", 4, 9),
           ("10 to 19 tags", 10, 19), ("20 or more tags", 20, 10**9)]


def rows(path):
    return list(csv.DictReader(open(path, newline="", encoding="utf-8")))


def group_of(job):
    return "7 revised" if job <= 4521946 else "17 new"


def main():
    boxes = defaultdict(Counter)      # (group, class) -> picture md5 count
    per_pic = defaultdict(Counter)    # group -> picture md5 -> OOI tags
    flags = defaultdict(set)          # (group, class) -> picture md5
    for r in rows(SRC):
        if r["source_group"] != "production_20260925":
            continue
        g = group_of(int(r["source_file"].split("_")[1].split(".")[0]))
        cid = r["canonical_id"]
        if cid.endswith("_micron_gate"):
            for grp in (g, "24 total"):
                flags[(grp, GATE[cid[:-len("_micron_gate")]])].add(r["picture_md5"])
            continue
        if r["shape_kind"] != "box":
            continue
        name = "Bubble" if cid in FOLD else {"bubble": "Bubble", "bubble_cluster": "Bubble Cluster",
                                             "wet_package": "Wet Package", "foreign_matter": "Foreign Matter",
                                             "fiber": "Fiber", "extraneous_polymer": "Extraneous Polymer",
                                             "hema_obstruction": "HEMA", "hema_fragment": "HEMA"}.get(cid)
        if name is None:
            continue
        for grp in (g, "24 total"):
            boxes[(grp, name)][r["picture_md5"]] += 1
            per_pic[grp][r["picture_md5"]] += 1

    out = []
    for grp in GROUPS:
        for name in ORDER:
            per = boxes.get((grp, name), {})
            n = len(per)
            tags = sum(per.values())
            med = statistics.median(per.values()) if per else 0
            out.append({"group": grp, "code": CODES[name], "class": name, "pictures": n,
                        "tags": tags, "flagged": len(flags.get((grp, name), set())),
                        "mean": round(tags / n, 2) if n else 0,
                        "median": med, "max": max(per.values()) if per else 0})
    with open(f"{OUT}/ooi_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "code", "class", "pictures", "tags", "flagged", "mean", "median", "max"])
        w.writeheader()
        w.writerows(out)

    dist = []
    for grp in GROUPS:
        counts = Counter()
        for c in per_pic[grp].values():
            for label, lo, hi in BUCKETS:
                if lo <= c <= hi:
                    counts[label] += 1
                    break
        total = sum(counts.values())
        for label, _, _ in BUCKETS:
            dist.append({"group": grp, "bucket": label, "pictures": counts[label]})
        dist.append({"group": grp, "bucket": "Pictures with at least one OOI tag", "pictures": total})
    with open(f"{OUT}/ooi_distribution.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["group", "bucket", "pictures"])
        w.writeheader()
        w.writerows(dist)

    # checks against class_table.csv
    ct = {(r["class"], r["group"]): r for r in rows(CT)}
    bad = 0
    for r in out:
        key = ("bubble (folded)" if r["class"] == "Bubble" else
               {"Bubble Cluster": "bubble_cluster", "Wet Package": "wet_package",
                "Foreign Matter": "foreign_matter", "Fiber": "fiber",
                "Extraneous Polymer": "extraneous_polymer", "HEMA": "hema_obstruction"}.get(r["class"]), r["group"])
        row = ct.get(key)
        if row is None:
            continue
        if int(row["pictures"]) != r["pictures"] or int(row["shapes"]) != r["tags"]:
            bad += 1
            print(f"MISMATCH {r['group']} {r['class']}: ooi {r['pictures']}/{r['tags']} vs class_table {row['pictures']}/{row['shapes']}")
    for grp in GROUPS:
        n = len(per_pic[grp])
        tags = sum(per_pic[grp].values())
        total = [d for d in dist if d["group"] == grp and d["bucket"].startswith("Pictures with")][0]["pictures"]
        print(f"{grp}: {n} distinct pictures carry OOI tags, {tags} tags, distribution covers {total}")
        if total != n:
            bad += 1
            print(f"  DISTRIBUTION MISMATCH: {total} vs {n}")
    print("checks:", "PASS" if bad == 0 else f"{bad} FAILED")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
