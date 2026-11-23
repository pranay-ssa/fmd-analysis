#!/usr/bin/env python3
"""Frozen-dataset EDA: counts for the questions asked, each with its population named.

Every table counts pictures from the annotation, never from a training matrix.
Mentions (shape instances) and pictures (distinct image basenames) are separate columns.

Definitions used here, stated so the numbers can be re-read:

  tag            a <tag> element: one whole-picture statement
  box            a <box> element: one region
  LP tag         one of the 15 lens-presentation codes (P1_*, P2_* presentation, F2_FOV)
  size gate      one of the 4 P3_*_MICRON_THRESHOLD tags; a size flag inside its class
  OOI class      one of the 8 object classes; counted as pictures carrying a box of it
  multi-tagged   the picture carries 2 or more tags of any class

Run:
    ./.venv/Scripts/python.exe experiments/annotations/frozen_eda.py
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
OUT = REPO / "run/frozen_eda_20261117"
CLIENT_TOTALS = FROZEN / "defect_counts_totals - 2626666.csv"

LP = {
    "P1_MPP": "Missing Primary Package",
    "P1_PPM": "Package Misalignment",
    "P1_COC": "Cavity Off Center",
    "P2_FOV": "View Obstructed",
    "F2_FOV": "View Obstructed",
    "P2_LOC": "Lens Off Center",
    "P1_NL": "Missing Lens",
    "P1_ML": "Multiple Lenses",
    "P1_FL": "Folded Lens",
    "P1_EBC": "Edge Bottle-Capped",
    "P1_TL": "Torn Lens",
    "P1_LR": "Lens Rupture",
    "P2_DS": "Dirty Strobe",
    "P2_DC": "Dirty Camera",
    "P2_BSC": "Bubble Scatter",
    "P2_LD": "Low Dose",
}
OOI = {
    "P2_BB": "Bubble",
    "P2_BC": "Bubble Cluster",
    "P2_WP": "Wet Package",
    "P1_SG": "Surface Groove",
    "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA",
    "P3_FM": "Foreign Matter",
}
GATE = {
    "P3_FM_MICRON_THRESHOLD": "Foreign Matter size gate",
    "P3_FIB_MICRON_THRESHOLD": "Fiber size gate",
    "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer size gate",
    "P3_HE_MICRON_THRESHOLD": "HEMA size gate",
}


def basename(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def load() -> dict[str, dict]:
    pics: dict[str, dict] = {}
    for path in sorted(FROZEN.glob("annotations_*.xml")):
        root = ET.parse(path).getroot()
        job = root.findtext("meta/job/id") or ""
        for img in root.findall("image"):
            b = basename(img.get("name", ""))
            tags = [t.get("label", "") for t in img.findall("tag")]
            boxes = [b2.get("label", "") for b2 in img.findall("box")]
            pics[b] = {
                "name": img.get("name", ""),
                "job": job,
                "folder": img.get("name", "").split("/")[1] if "/" in img.get("name", "") else "",
                "tags": tags,
                "boxes": boxes,
            }
    return pics


def write(name: str, rows: list[dict]) -> None:
    if not rows:
        (OUT / name).write_text("", encoding="utf-8")
        return
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pics = load()

    annotated = {b: v for b, v in pics.items() if v["tags"] or v["boxes"]}
    empty = sorted(set(pics) - set(annotated))

    # ---------- LP tags ----------
    lp_mentions = Counter()
    lp_pics: dict[str, set] = defaultdict(set)
    gate_mentions = Counter()
    gate_pics: dict[str, set] = defaultdict(set)
    box_mentions = Counter()
    box_pics: dict[str, set] = defaultdict(set)
    for b, v in annotated.items():
        for code in v["tags"]:
            if code in GATE:
                gate_mentions[code] += 1
                gate_pics[code].add(b)
            else:
                lp_mentions[code] += 1
                lp_pics[code].add(b)
        for code in v["boxes"]:
            box_mentions[code] += 1
            box_pics[code].add(b)

    lp_rows = []
    for code in sorted(lp_mentions):
        lp_rows.append({
            "code": code,
            "class": LP.get(code, "UNMAPPED"),
            "tag_instances": lp_mentions.get(code, 0),
            "pictures": len(lp_pics.get(code, ())),
        })
    write("lp_tags.csv", lp_rows)

    ooi_rows = []
    for code in sorted(set(OOI) | set(box_mentions)):
        ooi_rows.append({
            "code": code,
            "class": OOI.get(code, "UNMAPPED"),
            "pictures_with_boxes": len(box_pics.get(code, ())),
            "boxes": box_mentions.get(code, 0),
        })
    write("ooi_classes.csv", ooi_rows)

    gate_rows = []
    for code in GATE:
        gate_rows.append({
            "code": code,
            "class": GATE[code],
            "gate_tags": gate_mentions.get(code, 0),
            "pictures_with_gate": len(gate_pics.get(code, ())),
        })
    write("size_gates.csv", gate_rows)

    # ---------- tag distribution ----------
    # A picture states a tag once; a repeated identical tag is an annotation artefact, so
    # picture-level tables count distinct tags. Instance counts stay as the file has them.
    d_all = Counter()
    d_lp = Counter()
    for v in annotated.values():
        d_all[len(set(v["tags"]))] += 1
        d_lp[len({t for t in v["tags"] if t not in GATE})] += 1

    dist_rows = []
    for n in range(0, max(max(d_all), max(d_lp)) + 1):
        dist_rows.append({"tags_per_picture": n,
                          "pictures_all_tags": d_all.get(n, 0),
                          "pictures_lp_tags_only": d_lp.get(n, 0)})
    write("tag_distribution.csv", dist_rows)

    # ---------- tag-wise, by exact tag count ----------
    # Primary tables count LP presentation tags only. The size-gate flags are tags in the
    # file, but they are size statements inside a class, so their own set is emitted too
    # rather than mixed into the primary tables.
    by_n_lp: dict[int, Counter] = defaultdict(Counter)
    by_n_all: dict[int, Counter] = defaultdict(Counter)
    for v in annotated.values():
        lp_only = sorted({t for t in v["tags"] if t not in GATE})
        all_tags = sorted(set(v["tags"]))
        if lp_only:
            by_n_lp[len(lp_only)].update(lp_only)
        if all_tags:
            by_n_all[len(all_tags)].update(all_tags)

    def tag_rows(counter: Counter) -> list[dict]:
        return [{"tag": code,
                 "class": LP.get(code) or OOI.get(code) or GATE.get(code, ""),
                 "pictures": k}
                for code, k in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]

    for n, fname in ((1, "single_tagged.csv"), (2, "two_tagged.csv"), (3, "three_tagged.csv")):
        write(fname, tag_rows(by_n_lp.get(n, Counter())))
        write(fname.replace(".csv", "_incl_size_gates.csv"),
              tag_rows(by_n_all.get(n, Counter())))

    # ---------- clear ----------
    folder_of = {}
    with (REPO / "run/eda_full_20261029/file_manifest.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            folder_of.setdefault(basename(row["path"]), row["folder"])
    clear_rows = []
    clear_folder = [b for b in pics if folder_of.get(b, "").split("/")[-1].lower() == "clear"]
    for b in sorted(clear_folder):
        clear_rows.append({"basename": b, "job": pics[b]["job"],
                           "labels": ";".join(sorted(set(pics[b]["tags"] + pics[b]["boxes"])))})
    write("clear_folder_pictures.csv", clear_rows)

    clear_unlabelled = [b for b in clear_folder if b not in annotated]
    no_label_any = empty
    no_tag_but_box = [b for b, v in annotated.items() if not v["tags"]]

    # ---------- candidate readings of "clear lens" ----------
    # The Clear folder of the source library is not part of the production batch, so a
    # folder join gives zero. Record the candidate readings with their counts, so the
    # definition is a decision and not a guess.
    no_lp = [b for b, v in annotated.items() if not any(t in LP for t in v["tags"])]
    no_ooi = [b for b, v in annotated.items() if not v["boxes"]]
    neither = [b for b, v in annotated.items()
               if not any(t in LP for t in v["tags"]) and not v["boxes"]]
    clear_candidates = [
        {"reading": "no LP presentation tag", "pictures": len(no_lp),
         "of_annotated": len(annotated)},
        {"reading": "no OOI box", "pictures": len(no_ooi), "of_annotated": len(annotated)},
        {"reading": "no LP tag and no OOI box", "pictures": len(neither),
         "of_annotated": len(annotated)},
        {"reading": "no shape at all (unannotated placeholder)", "pictures": len(empty),
         "of_annotated": len(pics)},
    ]
    write("clear_candidates.csv", clear_candidates)

    # ---------- per job ----------
    per_job = []
    for job in sorted({v["job"] for v in pics.values()}, key=int):
        members = [v for v in pics.values() if v["job"] == job]
        per_job.append({
            "job_id": job,
            "pictures": len(members),
            "pictures_with_shape": sum(1 for v in members if v["tags"] or v["boxes"]),
            "lp_tag_instances": sum(1 for v in members for t in v["tags"] if t not in GATE),
            "size_gate_tags": sum(1 for v in members for t in v["tags"] if t in GATE),
            "boxes": sum(len(v["boxes"]) for v in members),
            "source_folder": members[0]["folder"] if members else "",
        })
    write("per_job.csv", per_job)

    # ---------- reconciliation against the client's own totals (shared jobs only) ----------
    shared = {j for j in {v["job"] for v in pics.values()} if int(j) <= 4522009}
    ours = Counter()
    ours_pics: dict[str, set] = defaultdict(set)
    for b, v in annotated.items():
        if v["job"] not in shared:
            continue
        for code in v["tags"]:
            ours[code] += 1
            ours_pics[code].add(b)
        for code in v["boxes"]:
            ours[code] += 1
            ours_pics[code].add(b)
    recon = []
    if CLIENT_TOTALS.exists():
        with CLIENT_TOTALS.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                code = row["defect"]
                recon.append({
                    "code": code,
                    "client_annotations": int(row["annotations"]),
                    "client_images": int(row["images"]),
                    "ours_mentions_70_jobs": ours.get(code, 0),
                    "ours_pictures_70_jobs": len(ours_pics.get(code, ())),
                    "mentions_match": ours.get(code, 0) == int(row["annotations"]),
                    "pictures_match": len(ours_pics.get(code, ())) == int(row["images"]),
                })
    write("client_reconciliation.csv", recon)

    summary = {
        "image_entries": len(pics),
        "annotated_pictures": len(annotated),
        "pictures_with_no_shape": len(empty),
        "pictures_without_any_tag": len(no_tag_but_box),
        "pictures_by_source_folder": dict(Counter(v["folder"] for v in pics.values())),
        "lp_tag_codes_with_data": sum(1 for r in lp_rows if r["tag_instances"]),
        "lp_tag_instances": sum(lp_mentions.values()),
        "lp_tag_instances_distinct_per_picture": sum(
            len({t for t in v["tags"] if t not in GATE}) for v in annotated.values()),
        "pictures_with_repeated_identical_tag": sum(
            1 for v in annotated.values() if len(v["tags"]) != len(set(v["tags"]))),
        "pictures_with_lp_tag": len({b for s in lp_pics.values() for b in s}),
        "ooi_codes_with_data": sum(1 for r in ooi_rows if r["boxes"]),
        "pictures_with_ooi_box": len({b for s in box_pics.values() for b in s}),
        "ooi_boxes": sum(box_mentions.values()),
        "size_gate_tags": sum(gate_mentions.values()),
        "pictures_with_size_gate": len({b for s in gate_pics.values() for b in s}),
        "pictures_by_tag_count_all_tags": {str(k): v for k, v in sorted(d_all.items())},
        "pictures_by_tag_count_lp_only": {str(k): v for k, v in sorted(d_lp.items())},
        "clear_folder_pictures_in_frozen": len(clear_folder),
        "clear_folder_pictures_with_no_shape": len(clear_unlabelled),
        "unmapped_tag_codes": sorted({c for c in lp_mentions if c not in LP and c not in GATE}),
        "unmapped_box_codes": sorted({c for c in box_mentions if c not in OOI}),
        "client_reconciliation_rows": len(recon),
        "client_reconciliation_all_match": all(
            r["mentions_match"] and r["pictures_match"] for r in recon) if recon else None,
    }
    (OUT / "eda_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
