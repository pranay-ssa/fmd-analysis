#!/usr/bin/env python3
"""Detail tables behind the frozen-dataset walkthrough.

Every table names its population. Three counting conventions are emitted side by side,
because they answer different questions and must never be mixed:

  instances   one <tag> or <box> element
  codes       one distinct code on a picture (gates counted separately)
  labels      one class on a picture, gate folded into its class, Clear counted as one
              (this is the convention the client's own label table uses)

Run:
    ./.venv/Scripts/python.exe experiments/annotations/frozen_eda_detail.py
"""

from __future__ import annotations

import csv
import json
import statistics
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "data/Frozen Annotation Dataset/Frozen Annotation Dataset"
RUN = REPO / "run/eda_full_20261029"
OUT = REPO / "run/frozen_eda_20261117/detail"

GATES = {
    "P3_FM_MICRON_THRESHOLD": "P3_FM",
    "P3_FIB_MICRON_THRESHOLD": "P3_FIB",
    "P3_EP_MICRON_THRESHOLD": "P3_EP",
    "P3_HE_MICRON_THRESHOLD": "P3_HE",
}
LP = {"P1_MPP", "P1_PPM", "P1_COC", "F2_FOV", "P2_LOC", "P1_NL", "P1_ML", "P1_FL",
      "P1_EBC", "P1_TL", "P1_LR", "P2_DS", "P2_DC", "P2_BSC", "P2_LD"}
OOI = {"P2_BB", "P2_BC", "P2_WP", "P1_SG", "P3_FIB", "P3_EP", "P3_HE", "P3_FM"}
NAMES = {
    "P1_MPP": "Missing Primary Package", "P1_PPM": "Package Misalignment",
    "P1_COC": "Cavity Off Center", "F2_FOV": "View Obstructed",
    "P2_LOC": "Lens Off Center", "P1_NL": "Missing Lens",
    "P1_ML": "Multiple Lenses", "P1_FL": "Folded Lens",
    "P1_EBC": "Edge Bottle-Capped", "P1_TL": "Torn Lens",
    "P1_LR": "Lens Rupture", "P2_DS": "Dirty Strobe",
    "P2_DC": "Dirty Camera", "P2_BSC": "Bubble Scatter", "P2_LD": "Low Dose",
    "P2_BB": "Bubble", "P2_BC": "Bubble Cluster", "P2_WP": "Wet Package",
    "P1_SG": "Surface Groove", "P3_FIB": "Fiber", "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA", "P3_FM": "Foreign Matter",
}


def base(name: str) -> str:
    return name.rsplit("/", 1)[-1]


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

    pics = {}
    for path in sorted(FROZEN.glob("annotations_*.xml")):
        root = ET.parse(path).getroot()
        job = root.findtext("meta/job/id") or ""
        for im in root.findall("image"):
            b = base(im.get("name", ""))
            pics[b] = {
                "job": job,
                "folder": im.get("name", "").split("/")[1],
                "tags": [t.get("label", "") for t in im.findall("tag")],
                "boxes": [x.get("label", "") for x in im.findall("box")],
            }

    # basename -> md5 -> winning_path, from the previous record's inventory
    name_md5 = {}
    with (RUN / "file_manifest.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name_md5.setdefault(base(row["path"]), row["md5"])
    md5_path = {}
    md5_folders = {}
    with (RUN / "picture_table.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            md5_path[row["md5"]] = row["winning_path"]
            md5_folders[row["md5"]] = row["all_folders"]

    def winning_folder(b: str) -> str:
        md5 = name_md5.get(b)
        if not md5 or md5 not in md5_path:
            return ""
        parts = md5_path[md5].split("/")
        return parts[1] if len(parts) > 1 else ""

    def is_clear_folder(b: str) -> bool:
        return winning_folder(b) == "Clear"

    annotated = {b: v for b, v in pics.items() if v["tags"] or v["boxes"]}
    empty = [b for b in pics if b not in annotated]

    # ---------- A. Clear ----------
    clear_pics = [b for b in pics if is_clear_folder(b)]
    clear_empty = [b for b in clear_pics if b not in annotated]
    clear_rows = []
    for b in clear_pics:
        v = pics[b]
        lp = {t for t in v["tags"] if t not in GATES}
        gate = {t for t in v["tags"] if t in GATES}
        boxcls = set(v["boxes"])
        if b not in annotated:
            state = "no mark at all"
        elif not lp and not v["boxes"]:
            state = "size gate only"
        elif not lp and boxcls <= {"P2_BB", "P2_BC"}:
            state = "bubbles only"
        elif not lp:
            state = "other box only"
        else:
            state = "presentation tag present"
        clear_rows.append({"basename": b, "job": v["job"], "state": state,
                           "tags": ";".join(sorted(set(v["tags"]))),
                           "boxes": ";".join(sorted(boxcls))})
    clear_state = Counter(r["state"] for r in clear_rows)

    # ---------- C. labels per picture, client convention ----------
    label_dist = Counter()
    label_sets = Counter()
    for b, v in annotated.items():
        labels = set()
        for t in v["tags"]:
            labels.add(GATES.get(t, t))
        for x in v["boxes"]:
            labels.add(x)
        label_dist[len(labels)] += 1
        for lab in labels:
            label_sets[lab] += 1
    for b in clear_empty:
        label_dist[1] += 1
        label_sets["Clear"] += 1

    # ---------- H. population split ----------
    lp_pics = {b for b, v in annotated.items() if any(t in LP for t in v["tags"])}
    box_pics = {b for b, v in annotated.items() if v["boxes"]}
    overlap = {
        "lp tag only": len(lp_pics - box_pics),
        "ooi box only": len(box_pics - lp_pics),
        "both": len(lp_pics & box_pics),
        "clear, no mark": len(clear_empty),
        "no mark, not a clear picture": len([b for b in empty if b not in clear_empty]),
    }

    # ---------- D. co-occurrence ----------
    pairs = Counter()
    for b, v in annotated.items():
        lp = sorted({t for t in v["tags"] if t not in GATES})
        for i in range(len(lp)):
            for j in range(i + 1, len(lp)):
                pairs[(lp[i], lp[j])] += 1
    pair_rows = [{"tag_a": a, "tag_b": b, "pictures": n}
                 for (a, b), n in pairs.most_common(25)]

    # ---------- E. boxes per picture ----------
    per_class_boxes = defaultdict(list)
    for b, v in annotated.items():
        c = Counter(v["boxes"])
        for code, n in c.items():
            per_class_boxes[code].append(n)
    box_rows = []
    for code in sorted(per_class_boxes, key=lambda k: -len(per_class_boxes[k])):
        vals = per_class_boxes[code]
        box_rows.append({
            "code": code, "class": NAMES.get(code, ""), "pictures": len(vals),
            "boxes": sum(vals), "boxes_per_picture_mean": round(sum(vals) / len(vals), 2),
            "median": statistics.median(vals), "max": max(vals),
        })

    # ---------- F. gate coverage ----------
    gate_rows = []
    for gate, cls in GATES.items():
        cls_pics = {b for b, v in annotated.items() if cls in v["boxes"]}
        gated = {b for b, v in annotated.items() if gate in v["tags"]}
        gate_rows.append({
            "class": NAMES[cls], "code": cls,
            "pictures_with_class": len(cls_pics),
            "pictures_with_gate": len(gated),
            "pictures_with_gate_and_class": len(gated & cls_pics),
            "gate_without_class": len(gated - cls_pics),
            "below_cut": len(cls_pics - gated),
            "share_flagging": round(100 * len(gated) / len(cls_pics), 1) if cls_pics else 0,
        })

    # ---------- G. year mix ----------
    years = Counter()
    for b in pics:
        years[b[:4]] += 1

    # ---------- I. per job ----------
    per_job = []
    for job in sorted({v["job"] for v in pics.values()}, key=int):
        members = {b: v for b, v in pics.items() if v["job"] == job}
        per_job.append({
            "job_id": job,
            "source_folder": next(iter(members.values()))["folder"],
            "pictures": len(members),
            "with_mark": sum(1 for v in members.values() if v["tags"] or v["boxes"]),
            "lp_pictures": sum(1 for v in members.values()
                               if any(t in LP for t in v["tags"])),
            "box_pictures": sum(1 for v in members.values() if v["boxes"]),
            "lp_tag_instances": sum(1 for v in members.values()
                                    for t in v["tags"] if t in LP),
            "boxes": sum(len(v["boxes"]) for v in members.values()),
            "gate_tags": sum(1 for v in members.values()
                             for t in v["tags"] if t in GATES),
        })

    # ---------- J. legacy pictures from the previous record ----------
    legacy_prev = defaultdict(set)
    for row in csv.DictReader((RUN / "resolved_labels.csv").open(encoding="utf-8")):
        if row["canonical_id"] in ("bubble_on_123", "bubble_on_edge") or (
                row["canonical_id"] == "hema_obstruction" and row["shape_kind"] == "tag"):
            legacy_prev[row["canonical_id"]].add(base(row["winning_path"]))
    legacy_rows = []
    for cid, names in legacy_prev.items():
        in_frozen = [b for b in names if b in pics]
        now = Counter()
        for b in in_frozen:
            v = pics[b]
            if b in clear_empty:
                now["no mark"] += 1
            for t in set(v["tags"]):
                now[("tag", t)] += 1
            for x in set(v["boxes"]):
                now[("box", x)] += 1
        legacy_rows.append({
            "legacy_class": cid,
            "pictures_in_previous_record": len(names),
            "pictures_in_frozen": len(in_frozen),
            "not_in_frozen": len(names) - len(in_frozen),
            "carrying_now": "; ".join(f"{k[1] if isinstance(k, tuple) else k} {v}"
                                      for k, v in now.most_common(6)),
        })

    # ---------- K. duplicate tags ----------
    dup_tags = [{"basename": b, "tags": ";".join(v["tags"])}
                for b, v in annotated.items() if len(v["tags"]) != len(set(v["tags"]))]

    write("clear_pictures.csv", clear_rows)
    write("pairs_lp.csv", pair_rows)
    write("boxes_per_picture.csv", box_rows)
    write("gate_coverage.csv", gate_rows)
    write("per_job_detail.csv", per_job)
    write("legacy_pictures.csv", legacy_rows)
    write("duplicate_tags.csv", dup_tags)
    write("labels_per_picture.csv",
          [{"labels_on_picture": k, "pictures": v} for k, v in sorted(label_dist.items())])

    summary = {
        "clear_folder_pictures_in_frozen": len(clear_pics),
        "clear_state": dict(clear_state),
        "clear_definition_count": len(clear_empty),
        "empty_pictures": len(empty),
        "empty_not_clear": [b for b in empty if b not in clear_empty],
        "population_split": overlap,
        "labels_per_picture_client_convention": dict(sorted(label_dist.items())),
        "pictures_with_at_least_one_label": sum(label_dist.values()),
        "year_mix": dict(sorted(years.items())),
        "label_top": label_sets.most_common(30),
        "gate_coverage": gate_rows,
        "legacy": legacy_rows,
        "duplicate_tag_pictures": len(dup_tags),
    }
    (OUT / "detail_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "label_top"}, indent=1))
    print("\ntop labels:", label_sets.most_common(15))


if __name__ == "__main__":
    main()
