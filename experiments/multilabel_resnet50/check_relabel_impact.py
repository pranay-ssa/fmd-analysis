#!/usr/bin/env python3
"""Does the Fiber -> Extraneous Polymer relabel touch our lens-presentation rows?

The annotator ruled that 33 contested pictures are Extraneous Polymer, not Fiber.
Fiber and Extraneous Polymer are out-of-inclusion tags. The lens-presentation
matrix holds five different tags. This script checks the overlap directly: how
many of the 33 sit in the 3,377 lens-presentation rows, and what those rows
carry. It also checks the two Clear-tag pictures named in the clear-tag analysis
that carry a lens-presentation tag in the new drop.
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_splits as ms                       # noqa: E402
from make_split_variants import load_lp_rows, LP_TAGS  # noqa: E402

REPO = HERE.parents[1]
BOXES = REPO / "run" / "ep_fiber_check" / "20260921" / "ep_fiber_boxes.csv"
CLEAR_HASHES = ["9beaab56a1cb25cae4d0fa9c45961491",
                "e02d87833be94d9721cb73f91339e6c7"]

_SCORE_TAIL = re.compile(r"^(.*)_\d+\.\d+$")


def _descore(name):
    """name_0.9995_0.7391.bmp -> name.bmp. Annotation score suffixes only."""
    stem = name.rsplit(".", 1)[0]
    while True:
        m = _SCORE_TAIL.match(stem)
        if not m or not m.group(1):
            return stem + ".bmp"
        stem = m.group(1)


def main():
    lp = load_lp_rows(ms.DEFAULT_LABELS)
    by_path = {r["image_path"]: r for r in lp}
    by_base = {Path(r["image_path"]).name: r for r in lp}
    by_md5 = {r.get("md5", ""): r for r in lp if r.get("md5")}
    lp_set = set(by_path)

    print("lens-presentation rows: %d" % len(lp))

    # ---- the 33 contested pictures -----------------------------------------
    if not BOXES.exists():
        print("box list not found: %s" % BOXES)
        return 1
    with open(BOXES, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    print("box list: %d rows, columns: %s" % (len(rows), list(rows[0]) if rows else []))

    labels_all = ms.load_rows(ms.DEFAULT_LABELS)
    by_all_base = {}
    for r in labels_all:
        by_all_base.setdefault(_descore(Path(r["image_path"]).name), r["image_path"])

    pics = {}          # label image_path -> box group
    unmatched = set()
    for r in rows:
        v = (r.get("file_name") or "").strip()
        if not v:
            continue
        grp = (r.get("group") or "?").split("_")[0]        # A_conflict -> A
        hit = by_all_base.get(_descore(Path(v).name))
        if hit:
            pics[hit] = grp
        else:
            unmatched.add(Path(v).name)
    print("distinct pictures in the box list: %d matched to the label matrix, %d not found"
          % (len(pics), len(unmatched)))
    for grp in ("A", "B", "C"):
        g = [p for p, k in pics.items() if k == grp]
        hit = [p for p in g if p in lp_set]
        print("  group %s: %d pictures, %d of them in the 3,377 lens rows"
              % (grp, len(g), len(hit)))

    in_lp = [by_path[p] for p in sorted(pics) if p in lp_set]
    print("of all box-list pictures, in the 3,377 lens rows: %d" % len(in_lp))
    if in_lp:
        per_tag = {t: sum(int(r[t]) for r in in_lp) for t in LP_TAGS}
        print("  what they carry: %s" % per_tag)
        for r in in_lp[:10]:
            tags = [t for t in LP_TAGS if int(r[t]) == 1]
            print("    %s -> %s" % (Path(r["image_path"]).name, tags or "(no lens tag)"))

    # ---- the two Clear-tag pictures named in the clear-tag analysis ---------
    print("Clear-tag pictures carrying a lens tag in the new drop:")
    labels_all = ms.load_rows(ms.DEFAULT_LABELS)
    for h in CLEAR_HASHES:
        hit = [r for r in labels_all if r.get("md5") == h]
        if not hit:
            print("  %s... not in the label matrix" % h[:12])
            continue
        r = hit[0]
        lp_tags = [t for t in LP_TAGS if int(r.get(t) or 0) == 1]
        in_set = r["image_path"] in lp_set
        others = [k for k, v in r.items()
                  if v == "1" and k not in LP_TAGS
                  and k not in ("negatives_reliable", "split", "split_named")]
        print("  %s... in lens set: %s | lens tags: %s | task: %s | other tags: %s"
              % (h[:12], in_set, lp_tags or "none", r.get("task_name", "?"),
                 others or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
