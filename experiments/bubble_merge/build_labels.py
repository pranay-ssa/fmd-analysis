#!/usr/bin/env python3
"""Build the Task 1 (bubble merge) single-label dataset locally.

WHAT THIS DOES
    Reads the frozen folder record run/line_eda/20260916/image_md5_records.csv
    and writes one row per distinct picture (content hash) with:

      * class_separate  - one tag per image under the rules below (the 22
                          defect/tag classes exactly as the line models saw
                          them), plus Clear for pictures that carry no tag.
      * class_merged    - the same row with the four bubble classes of the
                          client email folded into one Bubble class
                          (Bubble, Bubble On 123, Bubble On Edge,
                          Bubble Irregular). Bubble Cluster, Bubble Scatter
                          and every other class are untouched.
      * tag_family      - LP tag, OOI tag, or Clear.
      * line            - production line parsed from the file name.
      * split           - train / test, 70:30, md5-grouped, seed 42,
                          stratified on class_separate so the merged and the
                          separate variants see identical pictures on both
                          sides.

RULES (decisions taken with the user 2026-10-06, order updated 2026-10-07,
on top of the frozen 2026-09-17 pool rules R1-R6 of src/make_line_splits.py)
    N1  Clear is now a class: a picture whose only label anywhere is Clear
        becomes class "Clear". A picture that carries any other tag keeps the
        tag (the 128 Clear-plus-defect pictures stay under their defect).
    N2  One tag per picture, decided by folder priority. CHANGED 2026-10-07
        on client confirmation: the UPDATED folders outrank the old library,
        and between the updated folders the historical order stands: Updated
        ICube Objects, then Updated ICube Categorical Classes, then the old
        ICube Defects Library. Every run before 2026-10-07 used the reverse
        (old library first); the 20261006 outputs are that record. No tag is
        ever deducted from another column.
    N3  Merge scope: only the four classes named in the email merge. Bubble
        Cluster (36 pictures) and Bubble Scatter (7) stay separate.
    N4  Fiber-to-Extraneous-Polymer consequence of N2, spelled out because
        the client named it: the 33 pictures the old library calls Fiber and
        the updated folders call Extraneous Polymer are Extraneous Polymer.

OUTPUT (run/bubble_merge/20261007/)
    labels.csv              one row per picture, both variants, split column
    count_table.csv         class, tag_family, tag-presence, dataset count,
                            train, test (separate variant, merged variant)
    split_70_30_seed42.csv  md5, split (the file trainers read)
    summary.json            totals for the verifier and the report
"""
from __future__ import annotations

import csv
import json
import os
import random
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
OUT = os.path.join(REPO, "run", "bubble_merge", "20261007")
SEED = 42
TEST_FRACTION = 0.30

F_OBJ = "Updated ICube Objects 20260915"
F_CAT = "Updated ICube Categorical Classes 20260915"
F_OLD = "ICube Defects Library"
# N2 as confirmed by the client 2026-10-07: updated folders outrank the old
# library; between the updated folders the historical order stands.
PRIORITY = {F_OBJ: 0, F_CAT: 1, F_OLD: 2}

# R3 name equivalences plus R2 HEMA (identical to src/make_line_splits.py)
ALIAS = {
    "HEMA": "HEMA Fragment",
    "Low Dose": "Low Dose Obstructing Region of Interest",
    "Multiple Lens": "Multiple Lenses",
    "Primary Package Misalignment": "Package Misalignment",
    "Field Of View Obstructed": "View Obstructed",
}
NON_CLASS = {"duplicates"}          # R6, excluded outright
CLEAR = "Clear"                     # N1, lowest possible priority

# N3: only the four classes named in the email merge.
MERGE = {
    "Bubble": "Bubble",
    "Bubble On 123": "Bubble",
    "Bubble On Edge": "Bubble",
    "Bubble Irregular": "Bubble",
}

LP_TAGS = [
    "Bubble Scatter", "Cavity Off Center", "Dirty Camera", "Dirty Strobe",
    "HEMA Obstruction", "Lens Off Center",
    "Low Dose Obstructing Region of Interest", "Missing Lens",
    "Missing Primary Package", "Multiple Lenses", "Package Misalignment",
    "View Obstructed",
]
OOI_TAGS = [
    "Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123",
    "Bubble On Edge", "Extraneous Polymer", "Fiber", "Foreign Matter",
    "HEMA Fragment", "Stretched Bubble", "Wet Package",
]


def family(cls: str) -> str:
    if cls == CLEAR:
        return "Clear"
    if cls in LP_TAGS:
        return "LP tag"
    if cls in OOI_TAGS:
        return "OOI tag"
    raise KeyError("class with no tag family: %s" % cls)


def norm(cls: str) -> str:
    return ALIAS.get(cls, cls)


def line_of(name: str) -> str:
    for part in name.split("_"):
        if len(part) >= 3 and part[0] == "L" and part[1:].isdigit():
            return part
    return "NO-LINE"


def build():
    """Return {md5: dict} resolved to exactly one class per picture."""
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))

    candidates = defaultdict(list)      # md5 -> [(priority, class)]
    sources = defaultdict(list)         # md5 -> [folder/class/file, ...]
    line_of_md5, name_of, seen = {}, {}, set()
    n_rows = 0
    for folder, cls, name, md5, _bytes in rows:
        n_rows += 1
        line_of_md5.setdefault(md5, line_of(name))
        name_of.setdefault(md5, name)
        seen.add(md5)
        rel = "%s/%s/%s" % (folder, cls, name)   # path exactly as stored on disk
        if rel not in sources[md5]:
            sources[md5].append(rel)
        cls = norm(cls)
        if cls in NON_CLASS:
            continue
        if cls == CLEAR:
            continue                    # N1: Clear only if nothing else
        candidates[md5].append((PRIORITY[folder], cls))
    # second pass: Clear rows were skipped above, so re-read them for the
    # pictures that ended up with no candidate at all.
    clear_pictures = set()
    for folder, cls, name, md5, _bytes in rows:
        if norm(cls) == CLEAR:
            clear_pictures.add(md5)

    pool = {}
    for md5 in seen:
        cand = candidates.get(md5, [])
        if cand:
            cls = sorted(cand, key=lambda c: c[0])[0][1]
        elif md5 in clear_pictures:
            cls = CLEAR                 # N1
        else:
            continue                    # no label anywhere: not in the dataset
        ordered = sorted(sources[md5],
                         key=lambda p: PRIORITY.get(p.split("/", 1)[0], 9))
        pool[md5] = {
            "class_separate": cls,
            "class_merged": MERGE.get(cls, cls),
            "tag_family": family(cls),
            "line": line_of_md5[md5],
            "filename": name_of[md5],
            "sources": ordered,         # every on-disk copy, priority order
        }

    # tag presence: every distinct picture carrying the tag in ANY folder,
    # reported beside the one-tag assignment so both readings are on record.
    presence = defaultdict(set)
    for folder, cls, name, md5, _bytes in rows:
        cls = norm(cls)
        if cls in NON_CLASS:
            continue
        presence[cls].add(md5)
    return pool, presence, n_rows, len(seen)


def split(pool, seed=SEED, frac=TEST_FRACTION):
    """Stratified 70:30 on class_separate, deterministic, one row per md5."""
    by_class = defaultdict(list)
    for md5, rec in pool.items():
        by_class[rec["class_separate"]].append(md5)
    out = {}
    for cls in sorted(by_class):
        members = sorted(by_class[cls])
        rnd = random.Random("%s|%s" % (seed, cls))
        rnd.shuffle(members)
        n_test = int(len(members) * frac + 0.5)     # round half up
        for i, md5 in enumerate(members):
            out[md5] = "test" if i < n_test else "train"
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    pool, presence, n_rows, n_distinct = build()
    split_col = split(pool)

    # ---- labels.csv -------------------------------------------------------
    label_path = os.path.join(OUT, "labels.csv")
    with open(label_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["md5", "filename", "line", "class_separate", "class_merged",
                    "tag_family", "split", "sources"])
        for md5 in sorted(pool):
            r = pool[md5]
            w.writerow([md5, r["filename"], r["line"], r["class_separate"],
                        r["class_merged"], r["tag_family"], split_col[md5],
                        "|".join(r["sources"])])

    # ---- split file (trainer input) --------------------------------------
    with open(os.path.join(OUT, "split_70_30_seed42.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["md5", "split"])
        for md5 in sorted(pool):
            w.writerow([md5, split_col[md5]])

    # ---- count tables -----------------------------------------------------
    fam_of = {c: family(c) for c in LP_TAGS + OOI_TAGS + [CLEAR]}
    tables = {}
    for key, name in (("class_separate", "separate"), ("class_merged", "merged")):
        tab = defaultdict(lambda: {"train": 0, "test": 0, "total": 0})
        for md5, rec in pool.items():
            c = rec[key]
            tab[c]["total"] += 1
            tab[c]["train" if split_col[md5] == "train" else "test"] += 1
        tables[name] = dict(tab)

    for name, tab in tables.items():
        # tag presence for the merged view: a class that absorbs others counts
        # the pictures of every member tag, not just the namesake tag.
        pres = {}
        for cls in tab:
            members = [m for m, dst in MERGE.items() if dst == cls]
            folded = members and all(m == cls or m not in tab for m in members)
            if folded:                    # merged view: members are not classes
                union = set()
                for m in members:
                    union |= presence.get(m, set())
                pres[cls] = len(union)
            else:                         # separate view: the tag as it stands
                pres[cls] = len(presence.get(cls, ()))
        with open(os.path.join(OUT, "count_table_%s.csv" % name), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["class", "tag_family", "tag_presence_pictures",
                        "dataset_pictures", "train", "test"])
            for cls in sorted(tab, key=lambda c: (fam_of[c], c)):
                w.writerow([cls, fam_of[cls], pres[cls],
                            tab[cls]["total"], tab[cls]["train"],
                            tab[cls]["test"]])

    summary = {
        "source_rows": n_rows,
        "distinct_pictures": n_distinct,
        "dataset_pictures": len(pool),
        "tagged_pictures": sum(1 for r in pool.values()
                               if r["class_separate"] != CLEAR),
        "clear_pictures": sum(1 for r in pool.values()
                              if r["class_separate"] == CLEAR),
        "classes_separate": len(tables["separate"]),
        "classes_merged": len(tables["merged"]),
        "train": sum(1 for s in split_col.values() if s == "train"),
        "test": sum(1 for s in split_col.values() if s == "test"),
        "seed": SEED,
        "test_fraction": TEST_FRACTION,
        "merge_map": MERGE,
        "counts_separate": {k: v["total"] for k, v in tables["separate"].items()},
        "counts_merged": {k: v["total"] for k, v in tables["merged"].items()},
        "tag_presence": {k: len(v) for k, v in sorted(presence.items())},
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)

    print("rows %d | distinct %d | dataset %d | tagged %d | Clear %d"
          % (n_rows, n_distinct, summary["dataset_pictures"],
             summary["tagged_pictures"], summary["clear_pictures"]))
    print("classes: separate %d -> merged %d | train %d test %d"
          % (summary["classes_separate"], summary["classes_merged"],
             summary["train"], summary["test"]))
    print("outputs in %s" % OUT)


if __name__ == "__main__":
    main()
