#!/usr/bin/env python3
"""Build the multi-hot label matrix for the 5 lens-presentation (LP) tags.

Reads the CVAT export data/Updated Annotations 20260922.xml, extracts per-image
membership in {P1_COC, P1_FL, P1_ML, P1_MPP, P1_NL}, de-duplicates repeated
identical tags on the same image (125 images carry P1_MPP twice), joins the
content md5 from run/line_eda/20260916/image_md5_records.csv (that file has no
header: folder, class, filename, md5, bytes) and writes labels.csv.

Columns written:
  image_path, P1_COC, P1_FL, P1_ML, P1_MPP, P1_NL, md5, md5_source,
  task_id, task_name, n_tags, has_any_tag, negatives_reliable

negatives_reliable is True only when the image carries at least one tag (any
task, so a human looked at it) or it belongs to a fully finished task folder
(every image in that task carries at least one annotation). The Low Dose task is
76/1952 done, so untagged Low Dose images are unreliable negatives.

Usage (from anywhere inside the repo):
    python experiments/multilabel_resnet50/build_labels.py [--out PATH]
"""
import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_XML = REPO / "data" / "Updated Annotations 20260922.xml"
DEFAULT_MD5 = REPO / "run" / "line_eda" / "20260916" / "image_md5_records.csv"
DEFAULT_OUT = Path(__file__).resolve().parent / "labels.csv"

LP_TAGS = ["P1_COC", "P1_FL", "P1_ML", "P1_MPP", "P1_NL"]

# Cross-check targets from run/annotations_audit_20260923/multi_label_lp_analysis.json
EXPECTED = {
    "images_total": 6097,
    "images_with_any_LP": 3377,
    "untagged": 2145,
    "P1_COC": 183,
    "P1_FL": 178,
    "P1_ML": 1442,
    "P1_MPP": 1427,
    "P1_NL": 325,
    "dup_P1_MPP_images": 125,
}


def is_md5(value):
    return len(value) == 32 and all(c in "0123456789abcdefABCDEF" for c in value)


def load_md5(path):
    """Return (by_full_path, by_folder_filename, conflicting_keys).

    Keys are the same relative paths the XML uses: folder/class/filename.
    """
    by_full = {}
    by_folder_file = defaultdict(list)
    conflicts = 0
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.reader(fh):
            if len(row) < 4:
                continue
            folder, cls, fname, md5 = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            if not is_md5(md5):
                continue  # skips a header row if one ever appears
            key = "%s/%s/%s" % (folder, cls, fname)
            if key in by_full and by_full[key] != md5:
                conflicts += 1
            by_full[key] = md5
            by_folder_file["%s/%s" % (folder, fname)].append((cls, md5))
    return by_full, by_folder_file, conflicts


def parse_export(xml_path):
    """Parse the CVAT export into per-image records plus the task id to name map."""
    root = ET.parse(xml_path).getroot()

    task_names = {}
    meta = root.find("meta")
    if meta is not None:
        for task in meta.iter("task"):
            task_names[task.findtext("id") or ""] = task.findtext("name") or ""

    records = []
    for img in root.findall("image"):
        name = img.get("name") or ""
        task_id = img.get("task_id") or ""
        raw_tags = [child.get("label") for child in img if child.tag == "tag"]
        raw_tags = [t for t in raw_tags if t]
        tag_set = set(raw_tags)
        records.append({
            "image_path": name,
            "task_id": task_id,
            "task_name": task_names.get(task_id, ""),
            "raw_tags": raw_tags,
            "tag_set": tag_set,
            "n_annotations": len(img),  # any child: tag or box
        })
    return records, task_names


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml", default=str(DEFAULT_XML), help="CVAT export XML")
    ap.add_argument("--md5", default=str(DEFAULT_MD5), help="image md5 record csv (no header)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output labels.csv")
    args = ap.parse_args()

    records, _ = parse_export(Path(args.xml))
    by_full, by_folder_file, conflicts = load_md5(Path(args.md5))

    # A task folder is fully finished when every image in it carries at least one
    # annotation. Low Dose (76/1952 done) and Extraneous Polymer fall out as unfinished.
    per_task = defaultdict(lambda: [0, 0])
    for rec in records:
        slot = per_task[rec["task_id"]]
        slot[0] += 1
        if rec["n_annotations"] > 0:
            slot[1] += 1
    finished_tasks = {tid for tid, (n, done) in per_task.items() if n > 0 and done == n}

    md5_hits = md5_fallback = md5_miss = 0
    rows = []
    dup_lp = Counter()
    for rec in records:
        key = rec["image_path"]
        md5 = by_full.get(key)
        source = "record"
        if md5 is None:
            # fallback: same folder + filename, unique class in the record file
            folder, _, fname = key.partition("/")
            cands = by_folder_file.get("%s/%s" % (folder, fname), [])
            if len(cands) == 1:
                md5 = cands[0][1]
                source = "record_folder_filename"
                md5_fallback += 1
            else:
                md5 = ""
                source = "missing"
                md5_miss += 1
        if md5:
            md5_hits += 1

        raw = rec["raw_tags"]
        for tag in set(raw):
            if raw.count(tag) > 1:
                dup_lp[tag] += raw.count(tag) - 1

        labels = [1 if t in rec["tag_set"] else 0 for t in LP_TAGS]
        has_any_tag = len(rec["tag_set"]) > 0
        reliable = bool(has_any_tag or rec["task_id"] in finished_tasks)
        rows.append([
            rec["image_path"], *labels, md5, source,
            rec["task_id"], rec["task_name"], len(rec["tag_set"]),
            int(has_any_tag), int(reliable),
        ])

    header = ["image_path"] + LP_TAGS + [
        "md5", "md5_source", "task_id", "task_name", "n_tags",
        "has_any_tag", "negatives_reliable",
    ]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)

    # ---- report and cross-check -------------------------------------------------
    n = len(rows)
    per_class = {t: sum(r[1 + i] for r in rows) for i, t in enumerate(LP_TAGS)}
    any_lp = sum(1 for r in rows if any(r[1:1 + len(LP_TAGS)]))
    untagged = sum(1 for r in rows if r[header.index("n_tags")] == 0)
    unreliable = sum(1 for r in rows if r[header.index("negatives_reliable")] == 0)
    groups = Counter(r[header.index("md5")] for r in rows if r[header.index("md5")])
    multi_groups = sum(1 for _, c in groups.items() if c > 1)

    checks = [
        ("images_total", n, EXPECTED["images_total"]),
        ("images_with_any_LP", any_lp, EXPECTED["images_with_any_LP"]),
        ("untagged", untagged, EXPECTED["untagged"]),
        ("dup_P1_MPP_images", dup_lp.get("P1_MPP", 0), EXPECTED["dup_P1_MPP_images"]),
    ] + [(t, per_class[t], EXPECTED[t]) for t in LP_TAGS]

    print("wrote %s (%d rows)" % (out_path, n))
    print("per-class positive images: " + ", ".join("%s=%d" % (t, per_class[t]) for t in LP_TAGS))
    print("images with any LP tag: %d | untagged: %d | unreliable negatives: %d" % (any_lp, untagged, unreliable))
    print("duplicate tag instances removed: %s" % (dict(dup_lp) or "none"))
    print("md5 join: %d exact, %d fallback(folder+filename), %d missing | %d conflicting keys"
          % (md5_hits, md5_fallback, md5_miss, conflicts))
    print("md5 groups: %d unique, %d holding more than one image (leakage risk if split by path)"
          % (len(groups), multi_groups))
    print("unfinished task folders: %s"
          % ", ".join(sorted({r[header.index("task_name")] or r[header.index("task_id")]
                              for r in rows if r[header.index("negatives_reliable")] == 0
                              and r[header.index("n_tags")] == 0})))

    failures = [(name, got, want) for name, got, want in checks if got != want]
    if failures:
        for name, got, want in failures:
            print("MISMATCH %s: got %s want %s" % (name, got, want))
        return 1
    print("cross-check: %d/%d expectations matched" % (len(checks), len(checks)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
