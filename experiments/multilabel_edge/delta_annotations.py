"""Compare two sets of annotation XML files and report the delta.

Written for the case where revised versions of annotation files arrive and we must know
exactly what changed before rebuilding anything: which pictures appeared or disappeared,
which codes were added or removed, how many boxes moved, and how the class totals shifted.

The comparison is keyed on the image name inside the XML, because that is the identity the
annotation itself uses. Box geometry is compared at two decimals, so a rounding difference in
the writer does not show up as a change.

Usage:
    python delta_annotations.py --old data --new <folder with the revised files> \
        --out run/delta_20261028/delta.json

The tool only reads. It never writes into either folder.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

# Annotation files are local exports written by the labelling tool, read only, and never
# fetched over a network. defusedxml is used when present because it refuses entity tricks
# outright; the stdlib parser is the fallback so the tool still runs on a bare interpreter.
try:
    import defusedxml.ElementTree as ET
except ModuleNotFoundError:  # pragma: no cover - environment without defusedxml
    import xml.etree.ElementTree as ET


def read_xml(path: Path) -> dict:
    """Return {image name: {"boxes": [...], "tags": [...]}} for one annotation file."""
    out = {}
    root = ET.parse(path).getroot()
    for img in root.iter("image"):
        name = img.get("name") or ""
        entry = out.setdefault(name, {"boxes": [], "tags": []})
        for box in img.iter("box"):
            label = box.get("label") or ""
            geom = tuple(round(float(box.get(k, 0) or 0), 2)
                         for k in ("xtl", "ytl", "xbr", "ybr"))
            entry["boxes"].append((label, geom))
        for tag in img.iter("tag"):
            entry["tags"].append(tag.get("label") or "")
    return out


def read_folder(folder: Path) -> tuple[dict, dict]:
    """Return (images by name, per-file image counts). Later files win on a duplicate name."""
    images, files = {}, {}
    for path in sorted(folder.glob("*.xml")):
        found = read_xml(path)
        files[path.name] = len(found)
        for name, entry in found.items():
            images[name] = {**entry, "source_file": path.name}
    return images, files


def moved_boxes(old_boxes: list, new_boxes: list, label: str) -> int:
    """Count boxes of one label whose coordinates changed, pairing nearest centres first.

    Pairing by nearest centre matters: a plain sorted comparison shifts every box after an
    insertion or deletion and reports movement that did not happen.
    """
    ga = [g for lbl, g in old_boxes if lbl == label]
    gb = [g for lbl, g in new_boxes if lbl == label]
    if not ga or not gb:
        return 0
    pairs = []
    for i, x in enumerate(ga):
        cx, cy = (x[0] + x[2]) / 2, (x[1] + x[3]) / 2
        for j, y in enumerate(gb):
            dx, dy = (y[0] + y[2]) / 2, (y[1] + y[3]) / 2
            pairs.append((abs(cx - dx) + abs(cy - dy), i, j))
    pairs.sort()
    used_a, used_b, moved = set(), set(), 0
    for _, i, j in pairs:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        if ga[i] != gb[j]:
            moved += 1
    return moved


def compare(old: dict, new: dict) -> dict:
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = []
    for name in sorted(set(old) & set(new)):
        a, b = old[name], new[name]
        a_codes = Counter(lbl for lbl, _ in a["boxes"])
        b_codes = Counter(lbl for lbl, _ in b["boxes"])
        a_tags, b_tags = Counter(a["tags"]), Counter(b["tags"])
        codes_added = {k: v for k, v in (b_codes - a_codes).items()}
        codes_removed = {k: v for k, v in (a_codes - b_codes).items()}
        # A box whose label survives but whose coordinates moved.
        moved = sum(moved_boxes(a["boxes"], b["boxes"], label)
                    for label in set(a_codes) & set(b_codes))
        tags_added = {k: v for k, v in (b_tags - a_tags).items()}
        tags_removed = {k: v for k, v in (a_tags - b_tags).items()}
        if codes_added or codes_removed or moved or tags_added or tags_removed:
            changed.append({
                "image": name,
                "old_file": a["source_file"], "new_file": b["source_file"],
                "codes_added": codes_added, "codes_removed": codes_removed,
                "boxes_moved": moved,
                "tags_added": tags_added, "tags_removed": tags_removed,
            })

    def totals(images: dict) -> dict:
        out = defaultdict(int)
        for entry in images.values():
            for label, _ in entry["boxes"]:
                out[label] += 1
            for label in entry["tags"]:
                out["tag:" + label] += 1
        return dict(sorted(out.items()))

    t_old, t_new = totals(old), totals(new)
    class_delta = {k: t_new.get(k, 0) - t_old.get(k, 0)
                   for k in sorted(set(t_old) | set(t_new))
                   if t_new.get(k, 0) != t_old.get(k, 0)}
    return {
        "pictures": {"old": len(old), "new": len(new),
                     "added": added, "removed": removed,
                     "changed": changed},
        "class_totals": {"old": t_old, "new": t_new, "delta": class_delta},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True, help="folder holding the current annotation files")
    ap.add_argument("--new", required=True, help="folder holding the revised files")
    ap.add_argument("--out", required=True, help="where to write the delta json")
    args = ap.parse_args()

    old_images, old_files = read_folder(Path(args.old))
    new_images, new_files = read_folder(Path(args.new))
    result = compare(old_images, new_images)
    result["files"] = {"old": old_files, "new": new_files}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=False), encoding="utf-8")

    p = result["pictures"]
    print(f"pictures: {p['old']} -> {p['new']}  "
          f"added {len(p['added'])}, removed {len(p['removed'])}, changed {len(p['changed'])}")
    if result["class_totals"]["delta"]:
        print("class totals that moved:")
        for code, diff in result["class_totals"]["delta"].items():
            print(f"  {code:28s} {diff:+d}")
    else:
        print("class totals identical")
    for item in p["changed"][:10]:
        bits = []
        if item["codes_added"]:
            bits.append(f"+{item['codes_added']}")
        if item["codes_removed"]:
            bits.append(f"-{item['codes_removed']}")
        if item["boxes_moved"]:
            bits.append(f"{item['boxes_moved']} moved")
        print(f"  {item['image'][:70]:70s} {' '.join(bits)}")
    print(f"written {out}")


if __name__ == "__main__":
    main()
