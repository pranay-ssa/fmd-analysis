#!/usr/bin/env python3
"""Build the frozen store manifest and label tables from the annotation and the inventory.

One row per picture in the frozen export (13,682). The manifest is the join key for everything
downstream; paths are never built from class names.

Outputs, under run/frozen_eda_20261117/store/:
    manifest.csv, labels/tags.csv, labels/boxes.csv, addback_candidates.csv
"""

from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
RUN = REPO / "run/eda_full_20261029"
EDA = REPO / "run/frozen_eda_20261117"
OUT = EDA / "store"

GATES = {"P3_FM_MICRON_THRESHOLD", "P3_FIB_MICRON_THRESHOLD",
         "P3_EP_MICRON_THRESHOLD", "P3_HE_MICRON_THRESHOLD"}


def base(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def main() -> None:
    (OUT / "labels").mkdir(parents=True, exist_ok=True)

    # inventory of the old batch
    md5_of = {}
    for row in csv.DictReader((RUN / "file_manifest.csv").open(encoding="utf-8")):
        md5_of.setdefault(base(row["path"]), row["md5"])
    info = {}
    for row in csv.DictReader((RUN / "picture_table.csv").open(encoding="utf-8")):
        info[row["md5"]] = row

    # new batch hashes, verified against the blob during the pull
    new = {}
    with (EDA / "new_batch_md5.csv").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            name, size, md5 = line.strip().split(",")
            new[name] = (md5, int(size))

    duplicates = {r["basename"] for r in
                  csv.DictReader((EDA / "duplicates_vs_previous.csv").open(encoding="utf-8"))}

    manifest = []
    tags_rows = []
    box_rows = []
    for path in sorted(FROZEN.glob("annotations_*.xml")):
        root = ET.parse(path).getroot()
        job = root.findtext("meta/job/id") or ""
        for im in root.findall("image"):
            name = im.get("name", "")
            b = base(name)
            batch = name.split("/")[1] if "/" in name else ""
            tags = [t.get("label", "") for t in im.findall("tag")]
            boxes = im.findall("box")
            joined = md5_of.get(b)
            if batch.startswith("PRODUCTION-20260925") and joined:
                row_info = info.get(joined, {})
                winning = row_info.get("winning_path", "")
                folder = winning.split("/")[1] if "/" in winning else ""
                size = int(row_info.get("bytes") or 0)
                capture = row_info.get("capture_date", "")
                status = "duplicate" if b in duplicates else "new_old_batch"
                key = joined
            else:
                key, size = new.get(b, ("", 0))
                folder = "PRODUCTION-20261031"
                capture = b[:8] if b[:8].isdigit() else ""
                status = "new_upload"

            manifest.append({
                "picture_key": key,
                "basename": b,
                "bytes": size,
                "source_batch": batch,
                "source_folder": folder,
                "capture_date": capture,
                "job_id": job,
                "has_marks": "yes" if (tags or boxes) else "no",
                "n_tags": len(tags),
                "tag_codes": ";".join(sorted(set(t for t in tags if t not in GATES))),
                "n_boxes": len(boxes),
                "box_codes": ";".join(sorted({x.get("label", "") for x in boxes})),
                "gate_codes": ";".join(sorted(t for t in tags if t in GATES)),
                "is_clear_source": "yes" if folder == "Clear" else "no",
                "prev_annotation_status": status,
                "in_previous_annotation": "yes" if status == "duplicate" else "no",
            })
            for code, n in Counter(tags).items():
                tags_rows.append({"picture_key": key, "basename": b, "code": code,
                                  "kind": "gate" if code in GATES else "tag",
                                  "instances": n})
            for x in boxes:
                box_rows.append({
                    "picture_key": key, "basename": b, "code": x.get("label", ""),
                    "xtl": x.get("xtl"), "ytl": x.get("ytl"),
                    "xbr": x.get("xbr"), "ybr": x.get("ybr"),
                    "rotation": x.get("rotation", "0"),
                })

    def write(name, rows):
        with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    # content duplicates inside the frozen export: same picture, two names, both annotated
    seen = {}
    for row in manifest:
        key = row["picture_key"]
        if key and key in seen:
            row["content_duplicate"] = "yes"
            row["duplicate_of"] = seen[key]
            for other in manifest:
                if other["basename"] == seen[key]:
                    other["content_duplicate"] = "yes"
                    other["duplicate_of"] = other["basename"]
        elif key:
            seen[key] = row["basename"]
            row["content_duplicate"] = "no"
            row["duplicate_of"] = ""

    write("manifest.csv", manifest)
    write("labels/tags.csv", tags_rows)
    write("labels/boxes.csv", box_rows)

    # add-backs stay out of the store until the lead confirms
    addbacks = list(csv.DictReader((EDA / "previous_only_by_content.csv").open(encoding="utf-8")))
    addbacks = [r for r in addbacks if r["md5_present_in_frozen"] == "no"]
    # The two previous files that can supply a label are ranked by the project rule:
    # Updated Annotations 20260922.xml (level 2) outranks annotations.xml (level 3).
    # When one picture carries two labels from the two files, the newer file wins.
    priority = {"Updated Annotations 20260922.xml": 2, "annotations.xml": 3}
    by_md5: dict[str, list[dict]] = {}
    for r in addbacks:
        by_md5.setdefault(r["md5_known"], []).append(r)
    keep = []
    dropped = []
    for md5, group in by_md5.items():
        if len(group) == 1:
            keep.append(group[0])
            continue
        group = sorted(group, key=lambda r: priority.get(r["prev_files"], 9))
        winner = group[0]
        for loser in group[1:]:
            dropped.append({**loser, "superseded_by": winner["basename"]})
        keep.append(winner)

    fold = {"Bubble Irregular"}          # settled: folds into Bubble
    hold = {"Bubble On Edge", "Bubble On 123"}  # reference classes, no rule yet
    with (OUT / "addback_candidates.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["basename", "prev_files", "prev_labels", "md5",
                                           "manifest_path", "status", "decision", "note"])
        w.writeheader()
        for r in sorted(keep, key=lambda x: (x["prev_labels"], x["basename"])):
            if r["prev_labels"] in fold:
                status = "fold_into_bubble"
            elif r["prev_labels"] in hold:
                status = "hold_reference_class"
            else:
                status = "ready"
            note = ""
            if len(by_md5[r["md5_known"]]) > 1:
                note = ("same picture also labelled %s in %s; newer file wins"
                        % (", ".join(x["prev_labels"] for x in by_md5[r["md5_known"]]
                                     if x is not r),
                           ", ".join(sorted({x["prev_files"] for x in by_md5[r["md5_known"]]
                                             if x is not r}))))
            # The decision of 2026-11-17: the 27 reference-class pictures are discarded;
            # the other 147 wait on client confirmation. Neither group is in the store.
            decision = "discarded" if status == "hold_reference_class" else "pending_client"
            w.writerow({"basename": r["basename"], "prev_files": r["prev_files"],
                        "prev_labels": r["prev_labels"], "md5": r["md5_known"],
                        "manifest_path": r["manifest_path"], "status": status,
                        "decision": decision, "note": note})

    with (OUT / "addback_dropped.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["basename", "prev_files", "prev_labels", "md5",
                                           "superseded_by"])
        w.writeheader()
        for r in dropped:
            w.writerow({"basename": r["basename"], "prev_files": r["prev_files"],
                        "prev_labels": r["prev_labels"], "md5": r["md5_known"],
                        "superseded_by": r["superseded_by"]})

    summary = {
        "rows": len(manifest),
        "with_marks": sum(1 for r in manifest if r["has_marks"] == "yes"),
        "no_marks": sum(1 for r in manifest if r["has_marks"] == "no"),
        "status": dict(Counter(r["prev_annotation_status"] for r in manifest)),
        "clear_source": sum(1 for r in manifest if r["is_clear_source"] == "yes"),
        "tag_rows": len(tags_rows),
        "box_rows": len(box_rows),
        "addback_candidates_by_name": len(addbacks),
        "addback_final_rows": len(keep),
        "addback_ready": sum(1 for r in keep if r["prev_labels"] not in fold | hold),
        "addback_fold_into_bubble": sum(1 for r in keep if r["prev_labels"] in fold),
        "addback_hold_reference": sum(1 for r in keep if r["prev_labels"] in hold),
        "addback_pending_client": sum(1 for r in keep if r["prev_labels"] not in hold),
        "addback_discarded": sum(1 for r in keep if r["prev_labels"] in hold),
        "addback_dropped": len(dropped),
        "missing_picture_key": sum(1 for r in manifest if not r["picture_key"]),
        "duplicate_picture_keys": len(manifest) - len({r["picture_key"] for r in manifest}),
        "content_duplicate_rows": sum(1 for r in manifest if r.get("content_duplicate") == "yes"),
    }
    print(summary)
    (OUT / "manifest_summary.json").write_text(__import__("json").dumps(summary, indent=1),
                                               encoding="utf-8")


if __name__ == "__main__":
    main()
