#!/usr/bin/env python3
"""Verify run/bubble_merge/20261007 against every published figure it
depends on.

Independent routes, not a re-run of the builder's own arithmetic:

  A. totals against the frozen source record (row count, distinct pictures)
  B. per-class-per-line pool counts against
     run/line_eda/20260917/all_lines_class_split_70_30.csv, EXACTLY as
     changed by the client-confirmed folder-order flip of 2026-10-07
     (updated folders outrank the old library; the 20261006 labels are the
     old-order record this diff is taken against)
  C. one-tag assignment against src/make_line_splits.py::build_pool,
     imported and compared picture by picture: every difference must be one
     of the contested two-library pictures, flipped old -> updated
  D. tag-presence counts against the client EDA figures of
     docs/client_eda_numbers_20260917.md (items C and D)
  E. Clear arithmetic: 2,333 Clear-tagged = 128 also tagged + 2,205 Clear-only
  F. merge arithmetic: merged Bubble = sum of the four member classes, every
     other class unchanged, 23 classes -> 20
  G. split: one row per picture, per-class test = round-half-up(0.3 * n),
     train + test = total, no picture in both sides
  H. determinism: the builder re-run in memory reproduces the written files
  N. the order flip itself: exactly 52 pictures change class, exactly 33 of
     them Fiber -> Extraneous Polymer, every changed picture is genuinely
     contested (tags in two libraries), and no picture keeps an old-library
     tag that an updated folder contradicts

Run:  python experiments/bubble_merge/verify_labels.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "run", "bubble_merge", "20261007")
OLD_LABELS = os.path.join(REPO, "run", "bubble_merge", "20261006", "labels.csv")
SRC = os.path.join(REPO, "run", "line_eda", "20260916", "image_md5_records.csv")
LINE_SPLIT = os.path.join(REPO, "run", "line_eda", "20260917",
                          "all_lines_class_split_70_30.csv")

CHECKS = []


def check(name, got, want):
    ok = got == want
    CHECKS.append((ok, name, got, want))
    return ok


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    builder = load_module(os.path.join(REPO, "experiments", "bubble_merge",
                                       "build_labels.py"), "build_labels")

    # ---- A. totals against the source record -----------------------------
    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    check("A1 source rows", len(rows), 12079)
    check("A2 distinct pictures in source", len({r[3] for r in rows}), 10614)

    with open(os.path.join(OUT, "summary.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    with open(os.path.join(OUT, "labels.csv"), newline="", encoding="utf-8") as fh:
        labels = list(csv.DictReader(fh))

    check("A3 dataset pictures", len(labels), 10614)
    check("A4 one row per picture", len({r["md5"] for r in labels}), 10614)
    check("A5 tagged pictures", s["tagged_pictures"], 8409)
    check("A6 Clear pictures", s["clear_pictures"], 2205)
    check("A7 tagged + Clear = dataset",
          s["tagged_pictures"] + s["clear_pictures"], s["dataset_pictures"])
    check("A8 classes separate", s["classes_separate"], 23)
    check("A9 classes merged", s["classes_merged"], 20)

    # ---- B. pool counts against the published line split, as flipped -----
    published = defaultdict(int)          # (line, class) -> pictures
    with open(LINE_SPLIT, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["class"] == "TOTAL":      # per-line total rows, not classes
                continue
            published[(r["line"], r["class"])] = int(r["pictures"])
    # the 52 client-confirmed order flips, keyed by md5, old class -> new
    with open(OLD_LABELS, newline="", encoding="utf-8") as fh:
        old_cls = {r["md5"]: r["class_separate"] for r in csv.DictReader(fh)}
    flips = {m: (old_cls[m], r["class_separate"])
             for m, r in ((r["md5"], r) for r in labels)
             if r["class_separate"] != old_cls[m]}
    want = defaultdict(int)
    for (line, cls), v in published.items():
        want[(line, cls)] = v
    for m, (o, nw) in flips.items():
        r = next(x for x in labels if x["md5"] == m)
        want[(r["line"], o)] -= 1
        want[(r["line"], nw)] += 1
    mine = defaultdict(int)
    line_total = defaultdict(int)
    for r in labels:
        if r["class_separate"] == "Clear":
            continue
        mine[(r["line"], r["class_separate"])] += 1
        line_total[r["line"]] += 1
    diff = {k: (mine.get(k, 0), want.get(k, 0))
            for k in set(mine) | set(want) if mine.get(k, 0) != want.get(k, 0)}
    check("B1 every class-line cell = published split + the 52 flips", diff, {})
    check("B2 line L24 tagged pictures", line_total["L24"], 2853)
    check("B3 line L25 tagged pictures", line_total["L25"], 952)
    check("B4 line L26 tagged pictures", line_total["L26"], 1220)
    check("B5 line L27 tagged pictures", line_total["L27"], 1365)
    check("B6 line L31 tagged pictures", line_total["L31"], 2019)
    check("B7 no picture without a line", line_total.get("NO-LINE", 0), 0)

    # ---- C. one-tag assignment vs make_line_splits, flip-aware -----------
    splits_mod = load_module(os.path.join(REPO, "src", "make_line_splits.py"),
                             "make_line_splits")
    their_pool = splits_mod.build_pool()          # md5 -> (class, line, name)
    their_class = {m: v[0] for m, v in their_pool.items()}
    my_class = {r["md5"]: r["class_separate"] for r in labels
                if r["class_separate"] != "Clear"}
    check("C1 same pictures carry a tag", sorted(their_class), sorted(my_class))
    # the frozen rule is old-first, ours is updated-first: every difference
    # must be a contested picture whose updated-folder tag differs
    mism_old_first = {m: (their_class[m], my_class[m]) for m in their_class
                      if my_class[m] != their_class[m]}
    check("C2 differences vs the frozen old-first rule = the 52 flips",
          mism_old_first, flips)
    clear_rows = {r["md5"] for r in labels if r["class_separate"] == "Clear"}
    check("C3 Clear pictures carry no other label anywhere",
          sorted(clear_rows),
          sorted(set(labels_md5(labels)) - set(their_class)))

    # ---- D. tag presence against the client EDA figures ------------------
    presence = s["tag_presence"]
    EDA_LP = {"Low Dose Obstructing Region of Interest": 1952,
              "Multiple Lenses": 1439, "Missing Primary Package": 1427,
              "Missing Lens": 324, "Package Misalignment": 293,
              "Lens Off Center": 258, "Cavity Off Center": 183,
              "HEMA Obstruction": 175, "View Obstructed": 117,
              "Dirty Strobe": 43, "Dirty Camera": 25, "Bubble Scatter": 7}
    EDA_OOI = {"Foreign Matter": 1283, "Fiber": 362,
               "Extraneous Polymer": 268, "HEMA Fragment": 20,
               "Bubble": 113, "Wet Package": 67, "Bubble Irregular": 44,
               "Bubble Cluster": 36, "Bubble On 123": 14,
               "Bubble On Edge": 14, "Stretched Bubble": 0}
    for cls, want in list(EDA_LP.items()) + list(EDA_OOI.items()):
        check("D1 tag presence %s" % cls, presence.get(cls, 0), want)
    check("D2 Folded Lens carries no picture in the folder pool",
          presence.get("Folded Lens", 0), 0)

    # ---- E. Clear arithmetic --------------------------------------------
    check("E1 Clear-tagged pictures", presence.get("Clear", 0), 2333)
    clear_md5s = clear_tagged(rows)
    clear_with_defect = sum(1 for r in labels
                            if r["class_separate"] != "Clear"
                            and r["md5"] in clear_md5s)
    check("E2 pictures tagged Clear and a defect keep the defect",
          clear_with_defect, 128)
    check("E3 2,333 - 128 = 2,205", 2333 - 128, 2205)

    # ---- F. merge arithmetic --------------------------------------------
    FOUR = ["Bubble", "Bubble On 123", "Bubble On Edge", "Bubble Irregular"]
    sep, mrg = s["counts_separate"], s["counts_merged"]
    check("F1 merged Bubble = sum of the four classes",
          mrg["Bubble"], sum(sep[c] for c in FOUR))
    others = [c for c in sep if c not in FOUR]
    check("F2 every other class keeps its count",
          {c: mrg[c] for c in others}, {c: sep[c] for c in others})
    check("F3 23 - 3 = 20 classes", len(sep) - 3, len(mrg))
    check("F4 Cluster and Scatter are NOT merged",
          ("Bubble Cluster" in mrg, "Bubble Scatter" in mrg), (True, True))
    check("F5 the three other members are gone from the merged variant",
          [c for c in FOUR if c != "Bubble" and c in mrg], [])

    # ---- G. split --------------------------------------------------------
    per_cls = defaultdict(lambda: [0, 0])       # class -> [train, test]
    side = defaultdict(set)
    for r in labels:
        per_cls[r["class_separate"]][0 if r["split"] == "train" else 1] += 1
        side[r["md5"]].add(r["split"])
    check("G1 no picture on both sides",
          [m for m, v in side.items() if len(v) > 1], [])
    check("G2 split file covers every picture",
          len(read_split(os.path.join(OUT, "split_70_30_seed42.csv"))),
          10614)
    bad = {}
    for cls, (tr, te) in per_cls.items():
        n = tr + te
        want_te = int(n * 0.30 + 0.5)
        if te != want_te or tr != n - te:
            bad[cls] = (n, tr, te, want_te)
    check("G3 per-class test = round-half-up(0.3 n), train = rest", bad, {})
    check("G4 totals", (sum(tr for tr, _ in per_cls.values()),
                        sum(te for _, te in per_cls.values())),
          (s["train"], s["test"]))

    # ---- H. determinism: rebuild in memory and compare to the files ------
    pool, presence2, _n_rows, _n_dist = builder.build()
    split2 = builder.split(pool)
    check("H1 rebuild reproduces every label row",
          [(m, pool[m]["class_separate"], pool[m]["class_merged"],
            split2[m]) for m in sorted(pool)],
          [(r["md5"], r["class_separate"], r["class_merged"], r["split"])
           for r in sorted(labels, key=lambda r: r["md5"])])
    check("H2 rebuild reproduces tag presence",
          {k: len(v) for k, v in sorted(presence2.items())}, presence)

    # ---- F-extra: the merged table's tag presence, as a union of members --
    with open(os.path.join(OUT, "count_table_merged.csv"), newline="",
              encoding="utf-8") as fh:
        mrg_pres = {r["class"]: int(r["tag_presence_pictures"])
                    for r in csv.DictReader(fh)}
    member_union = set()
    for c in FOUR:
        member_union |= presence2.get(c, set())
    assigned_four = {m for m, r in pool.items() if r["class_separate"] in FOUR}
    # flip-aware: pictures carrying a member tag may now legitimately sit in
    # a non-member class when an updated folder outranks the member tag
    expected_diverted = {m for m, (o, nw) in flips.items()
                         if o in FOUR and nw not in FOUR}
    check("F6 member-tag pictures outside the member classes = exactly the "
          "priority-diverted ones", sorted(member_union - assigned_four),
          sorted(expected_diverted))
    check("F7 every member-assigned picture carries a member tag",
          sorted(assigned_four - member_union), [])
    check("F8 merged Bubble tag presence = union of the four member tags",
          mrg_pres["Bubble"], len(member_union))
    with open(os.path.join(OUT, "count_table_separate.csv"), newline="",
              encoding="utf-8") as fh:
        sep_pres = {r["class"]: int(r["tag_presence_pictures"])
                    for r in csv.DictReader(fh)}
    check("F9 separate Bubble tag presence stays the namesake tag only",
          sep_pres["Bubble"], presence["Bubble"])
    with open(os.path.join(OUT, "count_table_separate.csv"), newline="",
              encoding="utf-8") as fh:
        sep_rows = list(csv.DictReader(fh))
    gap = sum(int(r["tag_presence_pictures"]) - int(r["dataset_pictures"])
              for r in sep_rows if r["tag_family"] != "Clear")
    # every counted-once picture appears in one more tag column than it has
    # dataset rows, so the gap IS the number of two-tag pictures: the client
    # EDA of 2026-09-17 published that number as 55.
    check("F10 separate table gap = the 55 two-tag pictures", gap, 55)

    # ---- N. the order flip itself ----------------------------------------
    # N1: exactly 52 pictures change class, exactly as the probe predicted
    check("N1 exactly 52 pictures change class", len(flips), 52)
    # N2: exactly 33 of them are Fiber -> Extraneous Polymer (client-named)
    fib_ep = {m: t for m, t in flips.items() if t == ("Fiber",
                                                      "Extraneous Polymer")}
    check("N2 exactly 33 flips are Fiber -> Extraneous Polymer",
          len(fib_ep), 33)
    # N3: every flipped picture is genuinely contested (its updated-folder
    # tag set includes the new class, its old-library set the old class)
    upd_tags, old_tags = defaultdict(set), defaultdict(set)
    for folder, cls, name, md5, _b in rows:
        c = builder.norm(cls)           # same alias map the builder uses
        if c in ("Clear", "duplicates"):
            continue
        tagset = upd_tags if folder != "ICube Defects Library" else old_tags
        tagset[md5].add(c)
    bogus = {m for m, (o, nw) in flips.items()
             if nw not in upd_tags[m] or o not in old_tags[m]}
    check("N3 every flip is backed by an updated-folder tag for the new "
          "class and an old-library tag for the old", sorted(bogus), [])
    # N4: nothing unflipped keeps an old-library tag that an updated folder
    # contradicts (the priority reversal is applied everywhere, not just
    # where it matched the probe)
    leftovers = []
    for r in labels:
        m = r["md5"]
        if m in flips:
            continue
        old_side = old_tags.get(m, set())
        upd_side = upd_tags.get(m, set())
        # contradiction = the picture HAS an updated tag, keeps an old-library
        # tag, and that tag is not also present in the updated folders
        if (upd_side and r["class_separate"] in old_side
                and r["class_separate"] not in upd_side):
            leftovers.append(m)
    check("N4 no unflipped picture keeps a contradicted old-library tag",
          sorted(leftovers), [])
    # N5: the split reshuffle touches only classes that lost/gained pictures
    old_split = {r["md5"]: r["split"] for r in csv.DictReader(
        open(OLD_LABELS, newline="", encoding="utf-8"))}
    moved_classes = {t[0] for t in flips.values()} | {t[1] for t in flips.values()}
    wrong_side = [m for m, r in ((r["md5"], r) for r in labels)
                  if r["split"] != old_split[m]
                  and r["class_separate"] not in moved_classes]
    check("N5 split flips happen only inside classes that changed membership",
          sorted(wrong_side), [])

    # ---- report ----------------------------------------------------------
    failed = [c for c in CHECKS if not c[0]]
    print("checks: %d, failed: %d" % (len(CHECKS), len(failed)))
    for ok, name, got, want in failed:
        print("  FAIL %s\n    got  %r\n    want %r" % (name, got, want))
    if not failed:
        print("PASS")
    sys.exit(1 if failed else 0)


def labels_md5(labels):
    return [r["md5"] for r in labels]


def clear_tagged(rows):
    return {r[3] for r in rows if r[1] == "Clear"}


def read_split(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


if __name__ == "__main__":
    main()
