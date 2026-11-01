"""Build the multi-label Edge label matrix (ticket 019).

Frame: docs/decisions/2026-10-21-multilabel-edge-frame.md.
Inputs (read-only):
  run/eda_full_20261015/picture_table.csv      universe, one row per distinct picture (content md5)
  run/eda_full_20261015/resolved_labels.csv    winner-takes-all shapes
  run/eda_full_20261015/file_manifest.csv      basename -> md5 map (name-keyed mention route)
  data/*.xml                                   the 9 annotation exports (mention parse)
  run/multilabel_edge_20261021/fiber_ep_flip_list.csv  the verified 33-picture Fiber/EP flip set
Outputs:
  run/multilabel_edge_20261021/label_matrix.csv
  run/multilabel_edge_20261021/label_matrix_meta.json
"""
import csv, json, hashlib, collections, glob, os
import xml.etree.ElementTree as ET

ROOT = "D:/fmd-analysis"
EDA = f"{ROOT}/run/eda_full_20261015"
OUT = f"{ROOT}/run/multilabel_edge_20261021"

GATE_CODES = {
    "P3_FM_MICRON_THRESHOLD": "foreign_matter_micron_gate",
    "P3_FIB_MICRON_THRESHOLD": "fiber_micron_gate",
    "P3_EP_MICRON_THRESHOLD": "extraneous_polymer_micron_gate",
    "P3_HE_MICRON_THRESHOLD": "hema_micron_gate",
}
PLAIN = {"foreign_matter", "fiber", "extraneous_polymer", "hema_fragment"}
BUBBLE_ABSORB = {"bubble_irregular", "stretched_bubble"}  # fold into bubble per Draft 2
DEFECT_COLS = ["bubble", "bubble_cluster", "bubble_on_123", "bubble_on_edge",
               "wet_package", "bubble_scatter", "hema_obstruction"]
GATE_COLS = list(GATE_CODES.values())
LP_COLS = ["missing_primary_package", "multiple_lenses", "no_lens", "cavity_off_center",
           "folded_lens", "lens_off_center", "dirty_camera", "dirty_strobe", "low_dose",
           "view_obstructed", "package_misalignment"]
LABEL_COLS = GATE_COLS + DEFECT_COLS + LP_COLS + ["clear"]
CANON_TO_COL = {
    "bubble": "bubble", "bubble_irregular": "bubble", "stretched_bubble": "bubble",
    "bubble_cluster": "bubble_cluster", "bubble_on_123": "bubble_on_123",
    "bubble_on_edge": "bubble_on_edge", "wet_package": "wet_package",
    "bubble_scatter": "bubble_scatter", "hema_obstruction": "hema_obstruction",
    "missing_primary_package": "missing_primary_package", "multiple_lenses": "multiple_lenses",
    "missing_lens": "no_lens", "cavity_off_center": "cavity_off_center",
    "folded_lens": "folded_lens", "lens_off_center": "lens_off_center",
    "dirty_camera": "dirty_camera", "dirty_strobe": "dirty_strobe",
    "low_dose": "low_dose", "view_obstructed": "view_obstructed",
    "package_misalignment": "package_misalignment",
}

def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ---- universe ----
with open(f"{EDA}/picture_table.csv", newline="", encoding="utf-8") as f:
    universe = {r["md5"]: r for r in csv.DictReader(f)}
assert len(universe) == 10614, len(universe)

# ---- resolved shapes ----
labels = {m: collections.Counter() for m in universe}   # column -> 1
plain_present = {m: False for m in universe}
gate_present = {m: False for m in universe}
has_shape = {m: False for m in universe}
with open(f"{EDA}/resolved_labels.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        m = r["picture_md5"]
        if m not in universe:
            continue
        has_shape[m] = True
        cid, code = r["canonical_id"], r["code"]
        if code in GATE_CODES:
            labels[m][GATE_CODES[code]] = 1
            gate_present[m] = True
        elif cid == "hema_obstruction":
            # decision 13 / P3_HE collision: the column carries only the legacy
            # Sep-22 P2_HMO tags; production P3_HE boxes belong to the gate column
            if r["shape_kind"] == "tag":
                labels[m]["hema_obstruction"] = 1
        elif cid in CANON_TO_COL:
            labels[m][CANON_TO_COL[cid]] = 1
        elif cid in PLAIN:
            plain_present[m] = True

# ---- mentions (name-keyed route, per census convention) ----
name_to_md5s = collections.defaultdict(set)
with open(f"{EDA}/file_manifest.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        name_to_md5s[os.path.basename(r["path"])].add(r["md5"])
mentioned = {m: False for m in universe}
unmapped_names = set()
for xml_path in [f"{ROOT}/data/annotations.xml",
                 f"{ROOT}/data/Updated Annotations 20260922.xml"] + \
                sorted(glob.glob(f"{ROOT}/data/annotations_45219[0-4][0-9].xml")):
    for _, el in ET.iterparse(xml_path, events=("end",)):
        if el.tag == "image":
            base = os.path.basename(el.get("name", ""))
            hits = name_to_md5s.get(base)
            if not hits:
                unmapped_names.add(base)
            else:
                for m in hits:
                    if m in mentioned:
                        mentioned[m] = True
            el.clear()
print(f"mention parse: unmapped image names: {len(unmapped_names)}")

# ---- flip set ----
with open(f"{OUT}/fiber_ep_flip_list.csv", newline="", encoding="utf-8") as f:
    flip = [r["picture_md5"] for r in csv.DictReader(f)]
assert len(flip) == 33 and len(set(flip)) == 33, len(flip)
for m in flip:
    assert m in universe, m
    labels[m]["fiber_micron_gate"] = 1   # decision 12: flip stays as Fiber in the EDA reading

# ---- Clear folder rule (frame decision 14, 2026-10-21) ----
# Clear = winning path sits in a Clear folder of the two Updated libraries.
# Older (losing) annotation files may rescue a folder picture into its defect
# class; plain-family carriers in the folder still go through the gate rules.
clear_folder = {m for m, u in universe.items()
                if u["winning_path"].split("/")[1] == "Clear"}
PLAIN_NAME_TO_CANON = {
    "Bubble": "bubble", "Bubble Cluster": "bubble_cluster",
    "Bubble Irregular": "bubble_irregular", "Stretched Bubble": "stretched_bubble",
    "Wet Package": "wet_package", "Fiber": "fiber", "Foreign Matter": "foreign_matter",
    "Extraneous Polymer": "extraneous_polymer", "HEMA Fragment": "hema_fragment",
    "Bubble On 123": "bubble_on_123", "Bubble On Edge": "bubble_on_edge"}
rescue = collections.defaultdict(set)
with open(f"{EDA}/disagreement.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        m = r["picture_md5"]
        if m not in clear_folder:
            continue
        for tok in r["lower_labels"].split(";"):
            cid = PLAIN_NAME_TO_CANON.get(tok.split(":")[0].strip())
            if cid:
                rescue[m].add(cid)
n_rescued = 0
for m, cids in rescue.items():
    for cid in cids:
        if cid in CANON_TO_COL:
            if labels[m][CANON_TO_COL[cid]] == 0:
                n_rescued += 1
            labels[m][CANON_TO_COL[cid]] = 1
        elif cid in PLAIN:
            plain_present[m] = True

# ---- build rows ----
rows, drop_only_plain, dropped_unlabeled = [], [], []
for m, u in universe.items():
    defect_pos = any(labels[m][c] for c in GATE_COLS + DEFECT_COLS)
    only_plain = plain_present[m] and not defect_pos
    if only_plain:
        drop_only_plain.append(m)
        continue
    row = {
        "picture_md5": m,
        "winning_path": u["winning_path"],
        "folder_group": u["all_folders"].split(";")[0].strip(),
        "line": u["line"],
        "mention_status": "shape" if has_shape[m] else ("mentioned" if mentioned[m] else "unmentioned"),
        "negatives_reliable": int(has_shape[m] or m in clear_folder),
        "plain_family_present": int(plain_present[m]),
        "flip_exception": int(m in flip and labels[m]["fiber_micron_gate"] == 1
                              and not gate_present[m]),
        "split_eligible": int(not (plain_present[m] and not gate_present[m])),
    }
    for c in GATE_COLS + DEFECT_COLS + LP_COLS:
        row[c] = labels[m][c]
    row["clear"] = int(not defect_pos and not plain_present[m] and m in clear_folder)
    non_clear = [c for c in LABEL_COLS if c != "clear"]
    if row["clear"]:
        row["row_status"] = "clear_folder"
    elif any(row[c] for c in non_clear):
        row["row_status"] = "labeled"
    else:
        # decision 15, resolved 2026-10-21: unannotated rows (0 tags = no tags)
        # are not required for the experiment - dropped from the matrix
        dropped_unlabeled.append(m)
        continue
    rows.append(row)

out_cols = ["picture_md5", "winning_path", "folder_group", "line", "mention_status",
            "negatives_reliable", "plain_family_present", "flip_exception",
            "split_eligible", "row_status"] + LABEL_COLS
with open(f"{OUT}/label_matrix.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_cols)
    w.writeheader()
    w.writerows(rows)

# ---- headlines ----
pos = {c: sum(r[c] for r in rows) for c in LABEL_COLS}
card = collections.Counter(sum(r[c] for c in LABEL_COLS) for r in rows)
vectors = collections.Counter(tuple(r[c] for c in LABEL_COLS) for r in rows)
elig = [r for r in rows if r["split_eligible"] == 1]
headline = {
    "universe": len(universe),
    "dropped_only_plain": len(drop_only_plain),
    "dropped_unannotated": len(dropped_unlabeled),
    "unannotated_composition": dict(collections.Counter(
        "mentioned" if mentioned[m] else "unmentioned" for m in dropped_unlabeled)),
    "eda_rows": len(rows),
    "split_eligible_rows": len(elig),
    "flip_rows_in_matrix": sum(r["flip_exception"] for r in rows),
    "clear_rows": pos["clear"],
    "clear_rows_negative_unreliable": sum(1 for r in rows if r["clear"] == 1 and r["negatives_reliable"] == 0),
    "clear_folder_pictures": len(clear_folder),
    "rescued_defect_rows": n_rescued,
    "row_status_counts": dict(collections.Counter(r["row_status"] for r in rows)),
    "per_column_positives": pos,
    "cardinality_distribution": dict(sorted(card.items())),
    "distinct_label_vectors": len(vectors),
    "unmapped_mention_names": len(unmapped_names),
}
with open(f"{OUT}/label_matrix_meta.json", "w", encoding="utf-8") as f:
    json.dump({
        "ticket": "019", "date": "2026-10-21",
        "frame": "docs/decisions/2026-10-21-multilabel-edge-frame.md",
        "inputs": {
            "picture_table": f"{EDA}/picture_table.csv",
            "resolved_labels": f"{EDA}/resolved_labels.csv",
            "flip_list": f"{OUT}/fiber_ep_flip_list.csv",
            "flip_list_md5": md5_of(f"{OUT}/fiber_ep_flip_list.csv"),
        },
        "label_columns": LABEL_COLS,
        "headline": headline,
    }, f, indent=2)
print(json.dumps(headline, indent=2))
