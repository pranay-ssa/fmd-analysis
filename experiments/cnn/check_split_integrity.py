#!/usr/bin/env python3
"""Split-integrity check for the combined 22-class CNN set.

Answers two questions that a 2 to 3 point cross-split accuracy difference can hide behind:
  1. Do crops from the same SOURCE image sit on both sides of the split (near-duplicate
     leakage)? Crops of one defect/frame are visually near-identical, so leakage inflates
     accuracy, and it inflates most the classes that have many crops per source.
  2. How many crops come from each source, per class, per side? This is the weight that
     leakage would carry.

Reads split.csv (columns: source,class,split,single_crop) from the dataset root.
Usage: python3 check_split_integrity.py [dataset_root]
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1
            else "/home/pranayp/combined_dataset_single_20260908")
CSV = ROOT / "split.csv"

rows = list(csv.DictReader(CSV.open()))
print(f"split.csv: {len(rows)} rows | columns: {list(rows[0])}")

side = Counter(r["split"] for r in rows)
print(f"rows per side: {dict(side)}")

# crops per source image
per_source = defaultdict(set)
for r in rows:
    per_source[r["source"]].add(r["split"])
multi = {s: v for s, v in per_source.items() if len(v) > 1}
print(f"distinct source images: {len(per_source)}")
print(f"sources present on BOTH sides: {len(multi)}")

# crops per source, split by whether the source is single-sided
crops_per_source = defaultdict(int)
for r in rows:
    crops_per_source[r["source"]] += 1
leaked_crops = sum(crops_per_source[s] for s in multi)
print(f"crops belonging to leaked sources: {leaked_crops} "
      f"({100.0 * leaked_crops / len(rows):.1f} percent of all crops)")

if multi:
    print("\nleaked sources, with how they are distributed:")
    for s in sorted(multi)[:15]:
        parts = Counter(r["split"] for r in rows if r["source"] == s)
        cls = {r["class"] for r in rows if r["source"] == s}
        print(f"  {s:<34} {dict(parts)}  class={sorted(cls)}")

# per-class view: the weight leakage would carry if it existed
print("\nper class: crops, sources, mean crops per source (train / test)")
by_class = defaultdict(lambda: {"train": 0, "test": 0, "src_train": set(), "src_test": set()})
for r in rows:
    b = by_class[r["class"]]
    b[r["split"]] += 1
    b[f"src_{r['split']}"].add(r["source"])
print(f"{'class':<44}{'train':>7}{'test':>7}{'crops/src train':>17}{'crops/src test':>16}")
tot_t = tot_e = 0
for cls in sorted(by_class, key=lambda c: -(by_class[c]['train'] + by_class[c]['test'])):
    b = by_class[cls]
    tot_t += b["train"]; tot_e += b["test"]
    cpt = b["train"] / len(b["src_train"]) if b["src_train"] else 0
    cpe = b["test"] / len(b["src_test"]) if b["src_test"] else 0
    print(f"{cls:<44}{b['train']:>7}{b['test']:>7}{cpt:>17.2f}{cpe:>16.2f}")
print(f"{'TOTAL':<44}{tot_t:>7}{tot_e:>7}")

# exact duplicate filenames across sides (a second, cruder leakage signal)
names = defaultdict(set)
for r in rows:
    names[Path(r["single_crop"]).name].add(r["split"])
dupes = [n for n, v in names.items() if len(v) > 1]
print(f"\nidentical crop filenames on both sides: {len(dupes)}")
for n in dupes[:10]:
    print("  ", n)
