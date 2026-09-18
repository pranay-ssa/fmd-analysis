#!/usr/bin/env python3
"""
Client EDA numbers, v2 - the five questions in the 2026-09-17 client note.

Source of truth: run/line_eda/20260916/image_md5_records.csv
    folder, class, basename, md5, bytes   (12,079 rows, one per file)

Rules, in the order the client note states them:
  R1  The two Updated folders are the dataset. The old ICube Defects Library is
      used only for pictures that are not in the updated folders.
  R2  Clear is ignored as a class/tag.
  R2b Exception stated in the same note: pictures that sit in Clear AND carry a
      defect label are kept, under the defect label.
  R3  HEMA (Updated Objects) reads as HEMA Fragment.
  R4  Name equivalences: Low Dose == Low Dose Obstructing Region of Interest,
      Multiple Lenses == Multiple Lens, Package Misalignment ==
      Primary Package Misalignment, View Obstructed == Field Of View Obstructed.
  R5  "Unique image" == distinct content (md5), never distinct file name.
  R6  duplicates is not a class; its pictures already sit in a class folder.

Output: run/client_eda/20260917/*.csv + a printed numbers report.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
OUT = os.path.join(REPO, "run", "client_eda", "20260917")

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
F_OLD = "ICube Defects Library"
UPDATED = (F_OBJ, F_CAT)

ALIAS = {
    "HEMA": "HEMA Fragment",
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "Multiple Lens": "Multiple Lenses",
    "Primary Package Misalignment": "Package Misalignment",
    "Field Of View Obstructed": "View Obstructed",
}
NON_TAGS = {"Clear", "duplicates"}

# the 12 image-level tags (ontology "Image Level Labels (TAG)") carried by the
# Updated Categorical Classes folder
LP_TAGS = [
    "Bubble Scatter", "Cavity Off Center", "Dirty Camera", "Dirty Strobe",
    "HEMA Obstruction", "Lens Off Center", "Low Dose Obstructing Region of Interest",
    "Missing Lens", "Missing Primary Package", "Multiple Lenses",
    "Package Misalignment", "View Obstructed",
]
# the object types carried by the Updated Objects folder (Clear excluded)
OOI_TAGS = ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA Fragment"]


def norm(c: str) -> str:
    return ALIAS.get(c, c)


def line_of(name: str) -> str:
    for part in name.split("_"):
        if len(part) >= 3 and part[0] == "L" and part[1:].isdigit():
            return part
    return "NO-LINE"


def load():
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    recs = [{"folder": r[0], "cls": r[1], "raw": r[1], "name": r[2], "md5": r[3],
             "line": line_of(r[2]), "tag": norm(r[1])} for r in rows]
    return recs


def table(rows, headers):
    rows = [[str(c) for c in r] for r in rows]
    rows = [[str(c) for c in headers]] + rows
    w = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for i, r in enumerate(rows):
        out.append("  ".join(c.ljust(w[j]) for j, c in enumerate(r)).rstrip())
        if i == 0:
            out.append("  ".join("-" * x for x in w))
    print("\n".join("  " + x for x in out))


def write_csv(name, headers, rows):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        w.writerows(rows)
    return p


def main():
    recs = load()
    written = []
    by_folder = defaultdict(list)
    for r in recs:
        by_folder[r["folder"]].append(r)
    md5_folder = {f: {r["md5"] for r in rs} for f, rs in by_folder.items()}
    md5_updated = md5_folder[F_OBJ] | md5_folder[F_CAT]
    md5_all = {r["md5"] for r in recs}
    lines = sorted({r["line"] for r in recs})

    # -------- 1. old library coverage ------------------------------------
    old = by_folder[F_OLD]
    old_unc_rows = [r for r in old if r["md5"] not in md5_updated]
    old_unc_md5 = {r["md5"] for r in old_unc_rows}
    new_names = {r["name"] for r in recs if r["folder"] in UPDATED}

    print("=" * 92)
    print("Q1  IS EVERY OLD-LIBRARY PICTURE ALSO IN THE UPDATED FOLDERS?")
    print("=" * 92)
    table(
        [
            ["Old library, files", len(old)],
            ["Old library, unique pictures", len(md5_folder[F_OLD])],
            ["Old files whose content IS in an updated folder", len(old) - len(old_unc_rows)],
            ["Old files whose content is in NO updated folder", len(old_unc_rows)],
            ["  -> distinct pictures they hold (added to the dataset)", len(old_unc_md5)],
            ["Old files whose NAME is in an updated folder (looser test)", sum(1 for r in old if r["name"] in new_names)],
        ],
        ["Measure", "Count"],
    )
    cov_rows = []
    for cls in sorted({r["cls"] for r in old}):
        rs = [r for r in old if r["cls"] == cls]
        cov = len({r["md5"] for r in rs if r["md5"] in md5_updated})
        unc = len({r["md5"] for r in rs if r["md5"] not in md5_updated})
        cov_rows.append([cls, len(rs), len({r["md5"] for r in rs}), cov, unc])
    cov_rows.append(["TOTAL", len(old), len(md5_folder[F_OLD]),
                     len(md5_folder[F_OLD]) - len(old_unc_md5), len(old_unc_md5)])
    table(cov_rows, ["Old class", "Files", "Unique", "Already covered", "NOT covered"])
    written.append(write_csv("1_old_library_coverage.csv",
                             ["old_class", "files", "unique_images", "already_covered", "not_covered"],
                             cov_rows))

    # -------- dataset build ----------------------------------------------
    # tag set per picture, from every source, Clear/duplicates dropped (R2, R2b, R6)
    tags_of = defaultdict(set)
    folders_of = defaultdict(set)
    name_of = {}
    line_of_md5 = {}
    for r in recs:
        folders_of[r["md5"]].add(r["folder"])
        name_of.setdefault(r["md5"], r["name"])
        line_of_md5.setdefault(r["md5"], r["line"])
        if r["cls"] not in NON_TAGS:
            tags_of[r["md5"]].add(r["tag"])
    # a picture is in the dataset when it is in an updated folder OR only in the old library
    dataset = sorted(m for m in md5_all if (m in md5_updated or m in old_unc_md5) and tags_of.get(m))
    clear_md5 = {r["md5"] for r in by_folder[F_OBJ] if r["cls"] == "Clear"}
    kept_clear = sorted(clear_md5 & set(dataset))
    dropped_clear = len(clear_md5) - len(kept_clear)

    print()
    print("=" * 92)
    print("Q2A  TOTALS PER FOLDER, UNIQUE PICTURES, PRODUCTION LINES")
    print("=" * 92)
    a_rows = []
    for f in (F_OBJ, F_CAT, F_OLD):
        a_rows.append([f, len(by_folder[f]), len(md5_folder[f])])
    a_rows.append(["TOTAL, three folders", len(recs), len(md5_all)])
    table(a_rows, ["Folder", "Files", "Unique pictures"])
    print(f"\n  Pictures in the two Updated folders together: {len(md5_updated)}")
    print(f"  Production lines found in the file names: {len(lines)}  ({', '.join(lines)})")
    print(f"  Files with no line marker: {sum(1 for r in recs if r['line'] == 'NO-LINE')}")
    written.append(write_csv("2a_folder_totals.csv",
                             ["folder", "files", "unique_pictures"],
                             a_rows + [["Updated folders together", len(by_folder[F_OBJ]) + len(by_folder[F_CAT]), len(md5_updated)],
                                       ["Production lines", 5, 5]]))

    print()
    print("=" * 92)
    print("Q2A  THE DATASET THE CLIENT ASKS FOR (R1, R2, R2b)")
    print("=" * 92)
    table(
        [
            ["Pictures in the two Updated folders", len(md5_updated)],
            ["Pictures the old library adds (in no updated folder)", len(old_unc_md5)],
            ["Unique pictures under the two Updated folders + old-library remainder", len(md5_updated) + len(old_unc_md5)],
            ["Clear pictures set aside (no defect label anywhere)", dropped_clear],
            ["Clear pictures kept under their defect label", len(kept_clear)],
            ["FINAL dataset, unique pictures", len(dataset)],
        ],
        ["Step", "Pictures"],
    )
    print("\n  Source of the Clear pictures that are kept:")
    src = defaultdict(int)
    for m in kept_clear:
        for r in recs:
            if r["md5"] == m and r["cls"] != "Clear" and r["cls"] != "duplicates":
                src[f"{r['folder'].replace(' 20260915','')} / {r['tag']}"] += 1
    for k in sorted(src):
        print(f"    {k:60s} {src[k]}")
    print(f"    {'TOTAL entries':60s} {sum(src.values())}   ({len(kept_clear)} distinct pictures)")

    # -------- B. per line -------------------------------------------------
    print()
    print("=" * 92)
    print("Q2B  UNIQUE PICTURES PER PRODUCTION LINE")
    print("=" * 92)
    b_rows = []
    for ln in lines:
        obj = sum(1 for m in md5_folder[F_OBJ] if line_of_md5[m] == ln)
        cat = sum(1 for m in md5_folder[F_CAT] if line_of_md5[m] == ln)
        oldk = sum(1 for m in old_unc_md5 if line_of_md5[m] == ln)
        tot = sum(1 for m in dataset if line_of_md5[m] == ln)
        clr = sum(1 for m in clear_md5 if line_of_md5[m] == ln)
        b_rows.append([ln, obj, cat, oldk, clr, tot])
    b_rows.append(["TOTAL", len(md5_folder[F_OBJ]), len(md5_folder[F_CAT]),
                   len(old_unc_md5), len(clear_md5), len(dataset)])
    table(b_rows, ["Line", "Updated Objects", "Updated Categorical", "Old library (kept)",
                   "Clear (set aside)", "DATASET total"])
    written.append(write_csv("2b_unique_per_line.csv",
                             ["production_line", "updated_objects", "updated_categorical",
                              "old_library_kept", "clear_set_aside", "dataset_total"], b_rows))

    # -------- C. Lens Presentation tags -----------------------------------
    print()
    print("=" * 92)
    print("Q2C  UNIQUE PICTURES PER LENS PRESENTATION TAG")
    print("=" * 92)
    c_rows, c_tot_new, c_tot_all = [], 0, 0
    for tag in LP_TAGS:
        new = {m for m in md5_updated if tag in tags_of.get(m, ())}
        allm = {m for m in dataset if tag in tags_of.get(m, ())}
        extra = len(allm - new)
        clr = len(allm & clear_md5)
        c_rows.append([tag, len(new), extra, len(allm), clr])
        c_tot_new += len(new)
        c_tot_all += len(allm)
    c_rows.append(["TOTAL (pictures carrying at least one LP tag)",
                   len({m for m in md5_updated if tags_of.get(m, set()) & set(LP_TAGS)}),
                   len({m for m in dataset if tags_of.get(m, set()) & set(LP_TAGS)}),
                   len({m for m in dataset if tags_of.get(m, set()) & set(LP_TAGS)}),
                   len({m for m in dataset if tags_of.get(m, set()) & set(LP_TAGS)} & clear_md5)])
    table(c_rows, ["Lens Presentation tag", "Updated folders", "Added by old library",
                   "DATASET total", "of which were in Clear"])
    rows_out = [r for r in c_rows if not str(r[0]).startswith("TOTAL")]
    written.append(write_csv("2c_lens_presentation_tags.csv",
                             ["tag", "updated_folders", "added_from_old_library",
                              "dataset_total", "of_which_in_clear"], rows_out))

    # -------- D. OOI tags -------------------------------------------------
    print()
    print("=" * 92)
    print("Q2D  UNIQUE PICTURES PER OOI TAG  (Updated Objects folder)")
    print("=" * 92)
    d_rows = []
    for tag in OOI_TAGS:
        new = {m for m in md5_folder[F_OBJ] if tag in tags_of.get(m, ())}
        allm = {m for m in dataset if tag in tags_of.get(m, ())}
        clr = len(allm & clear_md5)
        d_rows.append([tag, len(new), len(allm) - len(new), len(allm), clr])
    table(d_rows, ["OOI tag", "Updated Objects", "Added by old library",
                   "DATASET total", "of which were in Clear"])
    d_rows_out = [["HEMA Fragment (folder name: HEMA)"] + d_rows[3][1:]] + d_rows[:3]
    written.append(write_csv("2d_ooi_tags.csv",
                             ["tag", "updated_objects", "added_from_old_library",
                              "dataset_total", "of_which_in_clear"], d_rows_out))

    print("\n  Same table over the full object-level (bounding-box) tag list of the ontology:")
    box = ["Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123", "Bubble On Edge",
           "Bubble Scatter", "Wet Package", "Fiber", "Extraneous Polymer", "Foreign Matter",
           "HEMA Fragment"]
    d2 = []
    for tag in box:
        inupd = len({m for m in md5_updated if tag in tags_of.get(m, ())})
        tot = len({m for m in dataset if tag in tags_of.get(m, ())})
        d2.append([tag, inupd, tot - inupd, tot])
    table(d2, ["Object-level tag", "In an updated folder", "Only in old library", "DATASET total"])
    written.append(write_csv("2d_alt_object_level_tags.csv",
                             ["tag", "in_updated_folders", "only_in_old_library", "dataset_total"], d2))

    # -------- E. multi-tag -------------------------------------------------
    print()
    print("=" * 92)
    print("Q2E  IS ONE PICTURE EVER ANNOTATED WITH MORE THAN ONE TAG?  (Clear ignored)")
    print("=" * 92)
    multi = {m: t for m, t in tags_of.items() if m in set(dataset) and len(t) > 1}
    table(
        [
            ["Pictures in the dataset", len(dataset)],
            ["Pictures carrying exactly one tag", len(dataset) - len(multi)],
            ["Pictures carrying more than one tag", len(multi)],
            ["  two tags", sum(1 for t in multi.values() if len(t) == 2)],
            ["  three tags", sum(1 for t in multi.values() if len(t) == 3)],
        ],
        ["Measure", "Count"],
    )
    pairs = defaultdict(int)
    for t in multi.values():
        ts = sorted(t)
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                pairs[(ts[i], ts[j])] += 1
    print("\n  Tag pairs that share a picture:")
    pr = [[a, b, n] for (a, b), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))]
    table(pr + [["TOTAL pictures with more than one tag", "", len(multi)]],
          ["Tag A", "Tag B", "Pictures"])
    written.append(write_csv("2e_multi_tag_pairs.csv", ["tag_a", "tag_b", "pictures"], pr))

    det = []
    for m, t in sorted(multi.items(), key=lambda kv: (-len(kv[1]), sorted(kv[1]))):
        where = "; ".join(sorted({f"{r['folder'].replace(' 20260915','')}/{r['raw']}"
                                 for r in recs if r["md5"] == m}))
        det.append(["|".join(sorted(t)), len(t), line_of_md5[m], where, name_of[m]])
    written.append(write_csv("2e_multi_tag_detail.csv",
                             ["tags", "tag_count", "production_line", "where", "file_name"], det))

    # -------- done ---------------------------------------------------------
    meta = {
        "source": "run/line_eda/20260916/image_md5_records.csv",
        "files_total": len(recs),
        "pictures_total": len(md5_all),
        "pictures_two_updated_folders": len(md5_updated),
        "old_library_files": len(old),
        "old_library_only_pictures": len(old_unc_md5),
        "clear_set_aside": dropped_clear,
        "clear_kept_under_defect_label": len(kept_clear),
        "dataset_unique_pictures": len(dataset),
        "lines": lines,
        "multi_tag_pictures": len(multi),
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print("\nwritten to run/client_eda/20260917/:")
    for p in written:
        print("  " + os.path.basename(p))


if __name__ == "__main__":
    main()
