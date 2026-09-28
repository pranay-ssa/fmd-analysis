#!/usr/bin/env python3
"""Join the blind verdicts to the group key and report the confusion.

Verdicts were recorded from the two sheets before the key was opened. Cell numbers are the
printed numbers on the sheets.
"""
import csv
import os
from collections import Counter, defaultdict

SCR = r"C:\Users\Abcom\AppData\Local\hermes\cache\scratch"

VERDICT = {
    1: "THIN", 2: "MASS", 3: "THIN", 4: "MASS", 5: "THIN", 6: "THIN", 7: "THIN", 8: "THIN",
    9: "MASS", 10: "THIN", 11: "THIN", 12: "THIN", 13: "THIN", 14: "THIN", 15: "THIN",
    16: "THIN", 17: "MASS", 18: "THIN", 19: "THIN", 20: "THIN", 21: "THIN", 22: "MASS",
    23: "THIN", 24: "THIN", 25: "THIN", 26: "THIN", 27: "THIN", 28: "THIN", 29: "MASS",
    30: "THIN", 31: "MASS", 32: "THIN", 33: "MASS", 34: "THIN", 35: "THIN", 36: "THIN",
    37: "MASS", 38: "MASS", 39: "MASS", 40: "THIN", 41: "THIN", 42: "MASS", 43: "THIN",
    44: "MASS", 45: "MASS", 46: "THIN", 47: "THIN", 48: "MASS", 49: "THIN", 50: "THIN",
    51: "THIN", 52: "THIN", 53: "UNCLEAR", 54: "MASS", 55: "THIN", 56: "THIN", 57: "UNCLEAR",
    58: "THIN", 59: "UNCLEAR", 60: "MASS", 61: "THIN", 62: "MASS", 63: "THIN", 64: "THIN",
    65: "UNCLEAR", 66: "UNCLEAR", 67: "THIN", 68: "MASS",
}

key = {int(r["cell"]): r for r in csv.DictReader(open(os.path.join(SCR, "sheet_key.csv"),
                                                     newline="", encoding="utf-8"))}
label = {
    "A_conflict": "A  older library says Fiber, newer folder says Extraneous Polymer",
    "B_ref_extraneous_polymer": "B  both folders say Extraneous Polymer",
    "C_ref_fiber": "C  both folders say Fiber",
}
tally = defaultdict(Counter)
for cell, verdict in VERDICT.items():
    tally[key[cell]["group"]][verdict] += 1

print("=" * 96)
print("BLIND VERDICT BY GROUP, 68 objects, judged on form only")
print("=" * 96)
print("%-62s %6s %6s %8s %10s" % ("group", "THIN", "MASS", "UNCLEAR", "THIN share"))
for g in ["A_conflict", "B_ref_extraneous_polymer", "C_ref_fiber"]:
    t = tally[g]
    n = sum(t.values())
    decided = t["THIN"] + t["MASS"]
    share = 100.0 * t["THIN"] / decided if decided else 0
    print("%-62s %6d %6d %8d %9.0f%%" % (label[g], t["THIN"], t["MASS"], t["UNCLEAR"], share))

print()
print("verdict rows written for the record:")
with open(os.path.join(SCR, "sheet_verdicts.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["cell", "group", "verdict", "file_name", "box_w", "box_h"])
    for cell in sorted(VERDICT):
        r = key[cell]
        w.writerow([cell, r["group"], VERDICT[cell], r["file_name"], r["box_w"], r["box_h"]])
print("   sheet_verdicts.csv")

# the pictures that carry both names, one line each, so a human can re-check the doubtful ones
print()
print("=" * 96)
print("THE 33 TWO-NAME PICTURES, one line each")
print("=" * 96)
seen = set()
for cell in sorted(VERDICT):
    r = key[cell]
    if r["group"] != "A_conflict" or r["file_name"] in seen:
        continue
    seen.add(r["file_name"])
    print("   %-6s box %5s x %-5s  %s" % (VERDICT[cell], r["box_w"], r["box_h"], r["file_name"]))
print("   %d pictures" % len(seen))
