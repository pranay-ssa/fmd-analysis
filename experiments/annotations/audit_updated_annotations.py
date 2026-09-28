"""Audit the 2026-09-22 annotation export against the older library and the drop manifest.

Reads the two CVAT XMLs and writes the audit tables to run/annotations_audit_20260923/,
then checks its own numbers against an EXPECTED table embedded here.

Stdlib only, so it runs on any interpreter with no venv, and the verifier can re-derive
every figure without importing this file.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

OLD_XML = "data/annotations.xml"
NEW_XML = "data/Updated Annotations 20260922.xml"
OUT_DIR = "run/annotations_audit_20260923"

# ---------------------------------------------------------------- label codes
# Derived in the doc (docs/annotations_update_20260923.md, section 2). Eleven codes are
# pinned by the task name sitting on a folder of that name; the rest by acronym, and
# P2_BST by elimination: it is the only unassigned box code and Stretched Bubble the only
# ontology box name that matches. Bubble On Edge and Bubble Over 123 Mark have no code.
CODE_TO_CLASS = {
    "P1_MPP": "Missing Primary Package",
    "P1_PPM": "Package Misalignment",
    "P1_COC": "Cavity Off Center",
    "P2_FOV": "View Obstructed",
    "P2_LOC": "Lens Off Center",
    "P1_NL": "Missing Lens",
    "P1_ML": "Multiple Lenses",
    "P1_FL": "Folded Lens",
    "P2_DS": "Dirty Strobe",
    "P2_DC": "Dirty Camera",
    "P2_BSC": "Bubble Scatter",
    "P2_LD": "Low Dose Obstructing Region of Interest",
    "P2_HMO": "HEMA Obstruction",
    "P2_BB": "Bubble",
    "P2_BC": "Bubble Cluster",
    "P2_BI": "Bubble Irregular",
    "P2_BST": "Stretched Bubble",
    "P2_WP": "Wet Package",
    "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA Fragment",
    "P3_FM": "Foreign Matter",
}

# The same class under the ontology document's own wording, where it differs from the name
# the dataset already uses (run/line_eda/20260917/all_lines_class_split_70_30.csv).
ONTOLOGY_NAME = {
    "P1_PPM": "Primary Package Misalignment",
    "P2_FOV": "Field Of View Obstructed",
    "P1_ML": "Multiple Lens",
    "P2_BI": "Irregular Bubble",
    "P2_LD": "Low Dose Obstructing ROI",
}

# The 22 classes the pooled split is built on.
REPO_22 = [
    "Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123", "Bubble On Edge",
    "Bubble Scatter", "Cavity Off Center", "Dirty Camera", "Dirty Strobe",
    "Extraneous Polymer", "Fiber", "Foreign Matter", "HEMA Fragment", "HEMA Obstruction",
    "Lens Off Center", "Low Dose Obstructing Region of Interest", "Missing Lens",
    "Missing Primary Package", "Multiple Lenses", "Package Misalignment",
    "View Obstructed", "Wet Package",
]

# The blob folder a task was built from, where it is not the class name.
FOLDER_NAME = {"P2_LD": "Low Dose"}

# The class a blob folder is named for, so a task's coverage is measured against the label
# its own folder stands for rather than against the task's internal name.
FOLDER_TO_CODE = {
    "Missing Primary Package": "P1_MPP", "Package Misalignment": "P1_PPM",
    "Cavity Off Center": "P1_COC", "View Obstructed": "P2_FOV",
    "Lens Off Center": "P2_LOC", "Missing Lens": "P1_NL", "Multiple Lenses": "P1_ML",
    "Folded Lens": "P1_FL", "Dirty Strobe": "P2_DS", "Dirty Camera": "P2_DC",
    "Bubble Scatter": "P2_BSC", "Low Dose": "P2_LD", "HEMA Obstruction": "P2_HMO",
    "Bubble": "P2_BB", "Bubble Cluster": "P2_BC", "Bubble Irregular": "P2_BI",
    "Stretched Bubble": "P2_BST", "Wet Package": "P2_WP", "Fiber": "P3_FIB",
    "Extraneous Polymer": "P3_EP", "HEMA Fragment": "P3_HE", "Foreign Matter": "P3_FM",
}

# The ontology document's two annotation lists (docs/Manufacturing Condition Ontology V1.docx).
ONTOLOGY_TAGS = [
    "Missing Lens", "Multiple Lens", "Missing Primary Package",
    "Primary Package Misalignment", "Cavity Off Center", "Field Of View Obstructed",
    "HEMA Obstruction", "Low Dose Obstructing ROI", "Folded Lens", "Lens Off Center",
    "Dirty Camera", "Dirty Strobe", "Bubble Scatter",
]
ONTOLOGY_BOXES = [
    "Fiber", "Extraneous Polymer", "Foreign Matter", "HEMA Fragment", "Bubble",
    "Stretched Bubble", "Irregular Bubble", "Bubble Cluster", "Bubble On Edge",
    "Bubble Over 123 Mark", "Wet Package",
]

# Subfolder counts of the 2026-09-16 blob drop, from docs/armor_blob_transfer_20260916.md.
DROP = {
    "Updated ICube Objects 20260915": {
        "Clear": 2333, "Foreign Matter": 1282, "Fiber": 328,
        "Extraneous Polymer": 267, "HEMA": 20,
    },
    "Updated ICube Categorical Classes 20260915": {
        "Low Dose": 1952, "Multiple Lenses": 1439, "Missing Primary Package": 1427,
        "Missing Lens": 324, "Package Misalignment": 293, "Lens Off Center": 258,
        "Cavity Off Center": 183, "HEMA Obstruction": 175, "duplicates": 143,
        "View Obstructed": 117, "Dirty Strobe": 42, "Dirty Camera": 25,
        "Bubble Scatter": 6,
    },
}

EXPECTED = {
    "new_images": 6097,
    "new_tags": 4930,
    "new_boxes": 183,
    "new_labels": 22,
    "new_tasks": 11,
    "new_images_with_a_tag": 3952,
    "new_images_with_a_box": 137,
    "new_images_with_tag_and_box": 13,
    "new_images_with_no_annotation": 2021,
    "new_images_with_no_tag": 2145,
    "new_labels_never_used": 2,
    "old_images": 435,
    "old_boxes": 2020,
    "old_rotated_boxes": 2015,
    "shared_basenames": 46,
    "shared_with_boxes_in_both": 45,
    "shared_boxes_identical_geometry": 0,
    "drop_images": 10614,
    "drop_images_in_this_export": 6097,
    "reannotation_pictures": 45,
    "reannotation_pairs": 46,
}


# ---------------------------------------------------------------- geometry
def rot_box_polygon(b):
    """(xtl, ytl, xbr, ybr, rotation) -> the four corners of the rotated rectangle."""
    import math
    x0, y0, x1, y1, rot = b
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    w, h = x1 - x0, y1 - y0
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return pts


def _clip(poly, a, b):
    """Sutherland-Hodgman clip of a convex polygon by the half plane left of a->b."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        sq = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        if sp >= 0:
            out.append(p)
        if (sp > 0 and sq < 0) or (sp < 0 and sq > 0):
            t = sp / (sp - sq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def area(poly):
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def poly_iou(p, q):
    inter = p
    for i in range(len(q)):
        inter = _clip(inter, q[i], q[(i + 1) % len(q)])
        if len(inter) < 3:
            return 0.0
    ai = area(inter)
    u = area(p) + area(q) - ai
    return ai / u if u > 0 else 0.0


# ---------------------------------------------------------------- parsing
def parse(path):
    root = ET.parse(path).getroot()
    proj = root.find("meta").find("project")
    tasks = {}
    for t in proj.find("tasks"):
        tasks[int(t.findtext("id"))] = dict(
            name=t.findtext("name"), size=int(t.findtext("size")),
            created=t.findtext("created"), updated=t.findtext("updated"),
            jobs=[(int(s.findtext("id")), int(s.findtext("start")), int(s.findtext("stop")))
                  for s in t.find("segments")])
    labels = [(l.findtext("name"), l.findtext("type"))
              for l in proj.find("labels")]
    images = []
    for im in root.findall("image"):
        nm = im.get("name")
        parts = nm.split("/")
        boxes = [dict(label=b.get("label"), xtl=float(b.get("xtl")), ytl=float(b.get("ytl")),
                      xbr=float(b.get("xbr")), ybr=float(b.get("ybr")),
                      rot=float(b.get("rotation") or 0.0), source=b.get("source"))
                 for b in im.findall("box")]
        images.append(dict(name=nm, base=nm.rsplit("/", 1)[-1],
                           parent=parts[0] if len(parts) > 2 else "",
                           folder=parts[1] if len(parts) > 2 else parts[0],
                           task=int(im.get("task_id")),
                           width=int(im.get("width")), height=int(im.get("height")),
                           tags=[t.get("label") for t in im.findall("tag")],
                           tag_src=[t.get("source") for t in im.findall("tag")],
                           boxes=boxes))
    return dict(project=proj.findtext("name"), project_id=proj.findtext("id"),
                created=proj.findtext("created"), updated=proj.findtext("updated"),
                dumped=root.find("meta").findtext("dumped"),
                tasks=tasks, labels=labels, images=images)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    old, new = parse(OLD_XML), parse(NEW_XML)
    n_imgs = new["images"]
    checks = []

    def check(name, got, want):
        checks.append(dict(check=name, got=got, expected=want, ok=got == want))

    # -- headline
    tag_inst = Counter(t for r in n_imgs for t in r["tags"])
    tag_pics = Counter()
    for r in n_imgs:
        for lab in set(r["tags"]):
            tag_pics[lab] += 1
    box_inst = Counter(b["label"] for r in n_imgs for b in r["boxes"])
    box_pics = Counter()
    for r in n_imgs:
        for lab in set(b["label"] for b in r["boxes"]):
            box_pics[lab] += 1
    n_tagged = sum(1 for r in n_imgs if r["tags"])
    n_boxed = sum(1 for r in n_imgs if r["boxes"])
    n_both = sum(1 for r in n_imgs if r["tags"] and r["boxes"])
    n_empty = sum(1 for r in n_imgs if not r["tags"] and not r["boxes"])
    used = set(tag_inst) | set(box_inst)
    never = [c for c, _ in new["labels"] if c not in used]

    old_imgs = old["images"]
    old_rot = sum(1 for r in old_imgs for b in r["boxes"] if b["rot"] != 0.0)
    oldbase = {r["base"]: r for r in old_imgs}
    newbase = {r["base"]: r for r in n_imgs}
    shared = sorted(set(oldbase) & set(newbase))

    # -- re-annotation IoU on the pictures both files annotate with at least one box
    pairs = []
    for bname in shared:
        ob, nb = oldbase[bname]["boxes"], newbase[bname]["boxes"]
        if not ob or not nb:
            continue
        for i, o in enumerate(ob):
            op = rot_box_polygon((o["xtl"], o["ytl"], o["xbr"], o["ybr"], o["rot"]))
            best, bestj = -1.0, -1
            for j, n in enumerate(nb):
                np_ = rot_box_polygon((n["xtl"], n["ytl"], n["xbr"], n["ybr"], n["rot"]))
                v = poly_iou(op, np_)
                if v > best:
                    best, bestj = v, j
            pairs.append(dict(image=bname,
                              old_folder=oldbase[bname]["folder"],
                              new_folder=newbase[bname]["folder"],
                              old_label=o["label"], new_label=nb[bestj]["label"],
                              old_box_index=i, new_box_index=bestj,
                              iou=round(best, 6),
                              identical=bool(op == rot_box_polygon(
                                  (nb[bestj]["xtl"], nb[bestj]["ytl"], nb[bestj]["xbr"],
                                   nb[bestj]["ybr"], nb[bestj]["rot"])))))
    ious = sorted(p["iou"] for p in pairs)

    def pct(sorted_vals, q):
        if not sorted_vals:
            return None
        k = (len(sorted_vals) - 1) * q
        lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
        return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo), 6)

    tag_totals = Counter()
    label_rows = []
    for code, kind in new["labels"]:
        cls = CODE_TO_CLASS.get(code, "")
        own_folder = FOLDER_NAME.get(code, cls)
        rows = [r for r in n_imgs if code in r["tags"] or code in [b["label"] for b in r["boxes"]]]
        folders = Counter(r["folder"] for r in rows)
        label_rows.append(dict(
            code=code, class_name=cls, ontology_name=ONTOLOGY_NAME.get(code, cls), kind=kind,
            instances=tag_inst.get(code, 0) + box_inst.get(code, 0),
            pictures=len(rows),
            pictures_in_the_folder_named_for_it=folders.get(own_folder, 0),
            folders=";".join(sorted(folders))))
        tag_totals[code] = len(rows)

    with open(f"{OUT_DIR}/labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(label_rows[0].keys()))
        w.writeheader()
        w.writerows(label_rows)

    # -- per task
    task_rows = []
    for tid in sorted(new["tasks"]):
        t = new["tasks"][tid]
        rs = [r for r in n_imgs if r["task"] == tid]
        folder = rs[0]["folder"] if rs else ""
        code = FOLDER_TO_CODE.get(folder, t["name"])
        cls = CODE_TO_CLASS.get(code, t["name"])
        cov = sum(1 for r in rs
                  if code in r["tags"] or code in [b["label"] for b in r["boxes"]])
        task_rows.append(dict(
            task_id=tid, task_name=t["name"], folder=folder,
            parent=rs[0]["parent"] if rs else "",
            class_of_the_folder=cls, code_of_the_folder=code,
            task_size=t["size"], images_in_export=len(rs), jobs=len(t["jobs"]),
            images_carrying_the_class_of_the_folder=cov,
            coverage_pct=round(100.0 * cov / len(rs), 2) if rs else 0.0,
            images_with_a_tag=sum(1 for r in rs if r["tags"]),
            images_with_a_box=sum(1 for r in rs if r["boxes"]),
            images_with_no_annotation=sum(1 for r in rs if not r["tags"] and not r["boxes"]),
            created=t["created"][:19], updated=t["updated"][:19]))
    with open(f"{OUT_DIR}/tasks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(task_rows[0].keys()))
        w.writeheader()
        w.writerows(task_rows)

    # -- per job: where the annotation stops inside a task
    job_rows = []
    for tid in sorted(new["tasks"]):
        t = new["tasks"][tid]
        rs = [r for r in n_imgs if r["task"] == tid]
        for jid, sa, st in t["jobs"]:
            chunk = rs[sa:st + 1] if st < len(rs) else rs[sa:]
            job_rows.append(dict(
                task_id=tid, task_name=t["name"], job_id=jid, start_frame=sa, stop_frame=st,
                images=len(chunk),
                images_with_a_tag=sum(1 for r in chunk if r["tags"]),
                images_with_a_box=sum(1 for r in chunk if r["boxes"]),
                images_with_no_annotation=sum(1 for r in chunk if not r["tags"] and not r["boxes"]),
                labels=";".join(f"{k}={v}" for k, v in
                                Counter(t for r in chunk for t in r["tags"]).most_common()) or
                       ";".join(f"{k}={v}" for k, v in
                                Counter(b["label"] for r in chunk for b in r["boxes"]).most_common())))
    with open(f"{OUT_DIR}/jobs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(job_rows[0].keys()))
        w.writeheader()
        w.writerows(job_rows)

    # -- folder cross tabs
    for kind, key in (("tags", "tags"), ("boxes", "boxes")):
        if kind == "tags":
            codes = sorted({t for r in n_imgs for t in r["tags"]})
        else:
            codes = sorted({b["label"] for r in n_imgs for b in r["boxes"]})
        rows = []
        for (parent, folder) in sorted({(r["parent"], r["folder"]) for r in n_imgs}):
            rs = [r for r in n_imgs if (r["parent"], r["folder"]) == (parent, folder)]
            row = dict(parent=parent, folder=folder,
                       images=len(rs),
                       images_annotated=sum(1 for r in rs if r["tags"] or r["boxes"]),
                       images_empty=sum(1 for r in rs if not r["tags"] and not r["boxes"]))
            for c in codes:
                if kind == "tags":
                    row[c] = sum(1 for r in rs if c in r["tags"])
                else:
                    row[c] = sum(1 for r in rs for b in r["boxes"] if b["label"] == c)
            rows.append(row)
        with open(f"{OUT_DIR}/folder_x_{kind}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    # -- coverage of the 2026-09-16 drop
    drop_rows = []
    for parent, subs in DROP.items():
        for folder, n in subs.items():
            inxml = sum(1 for r in n_imgs if r["parent"] == parent and r["folder"] == folder)
            drop_rows.append(dict(parent=parent, folder=folder, drop_images=n,
                                  images_in_this_export=inxml,
                                  not_in_this_export=n - inxml,
                                  covered_pct=round(100.0 * inxml / n, 1)))
    with open(f"{OUT_DIR}/drop_coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(drop_rows[0].keys()))
        w.writeheader()
        w.writerows(drop_rows)

    # -- the pictures both files annotate
    shared_rows = []
    for bname in shared:
        o, n = oldbase[bname], newbase[bname]
        oc = Counter(b["label"] for b in o["boxes"])
        nc = Counter(b["label"] for b in n["boxes"])
        shared_rows.append(dict(
            image=bname, old_folder=o["folder"], old_tags=";".join(o["tags"]),
            old_boxes=";".join(f"{k}x{v}" for k, v in oc.items()),
            new_folder=n["folder"], new_tasks=n["task"],
            new_tags=";".join(n["tags"]),
            new_boxes=";".join(f"{k}x{v}" for k, v in nc.items())))
    with open(f"{OUT_DIR}/shared_with_older_library.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(shared_rows[0].keys()))
        w.writeheader()
        w.writerows(shared_rows)

    with open(f"{OUT_DIR}/reannotation_iou.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
        w.writeheader()
        w.writerows(pairs)

    # -- tag co-occurrence
    co = Counter()
    for r in n_imgs:
        ts = sorted(set(r["tags"]))
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                co[(ts[i], ts[j])] += 1
    with open(f"{OUT_DIR}/tag_pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label_a", "class_a", "label_b", "class_b", "pictures"])
        for (a, b), v in co.most_common():
            w.writerow([a, CODE_TO_CLASS.get(a, ""), b, CODE_TO_CLASS.get(b, ""), v])

    # -- checks
    check("new_images", len(n_imgs), EXPECTED["new_images"])
    check("new_tags", sum(tag_inst.values()), EXPECTED["new_tags"])
    check("new_boxes", sum(box_inst.values()), EXPECTED["new_boxes"])
    check("new_labels", len(new["labels"]), EXPECTED["new_labels"])
    check("new_tasks", len(new["tasks"]), EXPECTED["new_tasks"])
    check("images_with_a_tag", n_tagged, EXPECTED["new_images_with_a_tag"])
    check("images_with_a_box", n_boxed, EXPECTED["new_images_with_a_box"])
    check("images_with_tag_and_box", n_both, EXPECTED["new_images_with_tag_and_box"])
    check("images_with_no_annotation", n_empty, EXPECTED["new_images_with_no_annotation"])
    check("images_with_no_tag", len(n_imgs) - n_tagged, EXPECTED["new_images_with_no_tag"])
    check("labels_defined_never_used", len(never), EXPECTED["new_labels_never_used"])
    check("old_images", len(old_imgs), EXPECTED["old_images"])
    check("old_boxes", sum(len(r["boxes"]) for r in old_imgs), EXPECTED["old_boxes"])
    check("old_rotated_boxes", old_rot, EXPECTED["old_rotated_boxes"])
    check("shared_basenames", len(shared), EXPECTED["shared_basenames"])
    check("shared_pictures_carrying_boxes_in_both",
          len({p["image"] for p in pairs}), EXPECTED["shared_with_boxes_in_both"])
    check("reannotation_pictures", len({p["image"] for p in pairs}),
          EXPECTED["reannotation_pictures"])
    check("reannotation_pairs", len(pairs), EXPECTED["reannotation_pairs"])
    check("reannotation_pairs_with_identical_geometry",
          sum(1 for p in pairs if p["identical"]), EXPECTED["shared_boxes_identical_geometry"])
    check("drop_images", sum(n for s in DROP.values() for n in s.values()), EXPECTED["drop_images"])
    check("drop_images_in_this_export", len(n_imgs), EXPECTED["drop_images_in_this_export"])
    check("every_new_image_is_2448x2048",
          sorted({(r["width"], r["height"]) for r in n_imgs}), [(2448, 2048)])
    check("every_old_image_is_2448x2048",
          sorted({(r["width"], r["height"]) for r in old_imgs}), [(2448, 2048)])
    check("every_tag_is_marked_manual",
          sorted({s for r in n_imgs for s in r["tag_src"]}), ["manual"])
    check("no_annotation_is_interpolated_or_tracked",
          sorted({b["source"] for r in n_imgs for b in r["boxes"]}), ["manual"])

    # label mapping must cover the ontology exactly, with the two known gaps
    codes = {c for c, _ in new["labels"]}
    check("codes_without_a_class_name", sorted(codes - set(CODE_TO_CLASS)), [])
    check("codes_without_an_ontology_name", sorted(codes - set(ONTOLOGY_NAME) - set(CODE_TO_CLASS)), [])
    check("every_ontology_tag_name_has_a_code",
          sorted({ONTOLOGY_NAME.get(c, CODE_TO_CLASS[c]) for c, k in new["labels"] if k == "tag"}),
          sorted(ONTOLOGY_TAGS))
    check("ontology_box_names_with_no_code",
          sorted(set(ONTOLOGY_BOXES)
                 - {ONTOLOGY_NAME.get(c, CODE_TO_CLASS[c]) for c, k in new["labels"]
                    if k == "rectangle"}),
          ["Bubble On Edge", "Bubble Over 123 Mark"])
    check("label_set_is_the_repo_22_less_2_plus_2",
          sorted({CODE_TO_CLASS[c] for c, _ in new["labels"]}),
          sorted(set(REPO_22) - {"Bubble On 123", "Bubble On Edge"}
                 | {"Folded Lens", "Stretched Bubble"}))
    check("tags_are_never_on_a_box_class",
          sorted(set(tag_inst) & {"P2_BB", "P2_BC", "P2_BI", "P2_BST", "P2_WP",
                                  "P3_FIB", "P3_EP", "P3_HE", "P3_FM"}), [])
    check("boxes_are_never_on_a_tag_class",
          sorted(set(box_inst) & {c for c, k in new["labels"] if k == "tag"}), [])

    summary = dict(
        source_file=NEW_XML, sha256=sha256(NEW_XML),
        bytes=os.path.getsize(NEW_XML),
        project=new["project"], project_id=new["project_id"],
        project_created=new["created"], project_updated=new["updated"], dumped=new["dumped"],
        images=len(n_imgs), tasks=len(new["tasks"]), labels_defined=len(new["labels"]),
        tag_instances=sum(tag_inst.values()), box_instances=sum(box_inst.values()),
        images_with_a_tag=n_tagged, images_with_a_box=n_boxed, images_with_tag_and_box=n_both,
        images_with_no_annotation=n_empty,
        images_with_no_tag=len(n_imgs) - n_tagged,
        labels_never_used=never,
        tag_instances_by_label=dict(tag_inst.most_common()),
        box_instances_by_label=dict(box_inst.most_common()),
        picture_counts_by_label=dict(tag_totals.most_common()),
        older_library=dict(file=OLD_XML, sha256=sha256(OLD_XML), images=len(old_imgs),
                           boxes=sum(len(r["boxes"]) for r in old_imgs),
                           rotated_boxes=old_rot),
        shared_basenames=len(shared),
        reannotation=dict(pairs=len(pairs),
                          pictures=len({p["image"] for p in pairs}),
                          identical_geometry=sum(1 for p in pairs if p["identical"]),
                          min=ious[0] if ious else None, p25=pct(ious, .25),
                          median=pct(ious, .5), mean=round(sum(ious) / len(ious), 6) if ious else None,
                          p75=pct(ious, .75), max=ious[-1] if ious else None,
                          pairs_the_new_file_calls_extraneous_polymer=
                              sum(1 for p in pairs if p["new_label"] == "P3_EP"),
                          pairs_identical_geometry=sum(1 for p in pairs if p["identical"])),
        drop=dict(parents={k: sum(v.values()) for k, v in DROP.items()},
                  total=sum(n for s in DROP.values() for n in s.values()),
                  in_this_export=len(n_imgs),
                  not_in_this_export=sum(n for s in DROP.values() for n in s.values()) - len(n_imgs)),
        checks=checks, checks_failed=sum(1 for c in checks if not c["ok"]))
    with open(f"{OUT_DIR}/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    for c in checks:
        if not c["ok"]:
            print(f"  FAIL {c['check']}: got {c['got']} expected {c['expected']}")
    print(f"wrote {OUT_DIR}: {len(checks)} checks, {summary['checks_failed']} failed")
    print(f"  new: {len(n_imgs)} images, {sum(tag_inst.values())} tags, "
          f"{sum(box_inst.values())} boxes, {len(new['labels'])} labels, {len(new['tasks'])} tasks")
    print(f"  re-annotation: {len(pairs)} box pairs on {len({p['image'] for p in pairs})} "
          f"shared pictures, {sum(1 for p in pairs if p['identical'])} with identical geometry, "
          f"median IoU {pct(ious, .5)}")
    return summary


if __name__ == "__main__":
    main()
