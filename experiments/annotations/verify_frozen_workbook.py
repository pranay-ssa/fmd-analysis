#!/usr/bin/env python3
"""Verify the frozen EDA workbook by numbers, not by rendering.

Recomputes the label tables from the store with a separate code path and compares
them with the cells in the workbook. No images, no vision.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]
STORE = REPO / "run/frozen_eda_20261117/store"
XLSX = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "reports/frozen_eda_20261118/FMD_Frozen_EDA_draft_20261118.xlsx"

DROP = {
    "20241102_004906_L24_C5_9471_0.6629.bmp",
    "20241109_174228_L24_C4_9649_0.9824.bmp",
    "20241110_024940_L24_C13_9997.bmp",
    "20260816_093047_L26_PalletGHF0816135159_Cavity12_B01BJQ6_Fail7_Score(0.989757).bmp",
}
DEBRIS = ["P3_FM", "P3_FIB", "P3_EP", "P3_HE"]

fails: list[str] = []
checks = 0

def eq(label, got, want):
    global checks
    checks += 1
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")

def close(label, got, want):
    global checks
    checks += 1
    if not isinstance(got, (int, float)) or abs(got - want) > 1e-9:
        fails.append(f"{label}: got {got!r}, want {want!r}")

# ---- independent recount ----
manifest = [r for r in csv.DictReader(open(STORE / "manifest.csv", encoding="utf-8-sig"))
            if r["basename"] not in DROP]
keys = {r["basename"] for r in manifest}
pic = defaultdict(lambda: {"lp": set(), "gate": set(), "box": set()})
for t in csv.DictReader(open(STORE / "labels/tags.csv", encoding="utf-8-sig")):
    if t["basename"] in keys:
        if t["kind"] == "gate":
            pic[t["basename"]]["gate"].add(t["code"])
        else:
            pic[t["basename"]]["lp"].add(t["code"])
box_total = 0
for b in csv.DictReader(open(STORE / "labels/boxes.csv", encoding="utf-8-sig")):
    if b["basename"] in keys:
        pic[b["basename"]]["box"].add(b["code"])
        box_total += 1

marked = {n for n, v in pic.items() if v["lp"] or v["box"]}
clear = {r["basename"] for r in manifest if str(r.get("is_clear_source")).lower() in ("1", "true", "yes")} - marked
labelled = marked | clear
classes = {n: pic[n]["lp"] | pic[n]["box"] for n in labelled}
dist = Counter(len(classes[n]) for n in labelled)
lp_pics = {n for n in labelled if pic[n]["lp"]}
ooi_pics = {n for n in labelled if pic[n]["box"]}
single_lp = {n for n in labelled if len(classes[n]) == 1 and pic[n]["lp"]}
single_ooi = {n for n in labelled if len(classes[n]) == 1 and pic[n]["box"]}
single_counts = Counter(next(iter(classes[n])) for n in labelled if len(classes[n]) == 1)
pairs_exact = Counter(tuple(sorted(classes[n])) for n in labelled if len(classes[n]) == 2)
pair_incl = Counter()
for n in labelled:
    cs = sorted(classes[n])
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            pair_incl[(cs[i], cs[j])] += 1

def comp(k):
    c = Counter()
    for n in labelled:
        if len(classes[n]) == k:
            c[(len(pic[n]["lp"] & classes[n]), len(pic[n]["box"] & classes[n]))] += 1
    if k >= 3:
        c[(k, 0)] += 0  # the empty split is a real zero
    return c

def passed(n, extended):
    if pic[n]["lp"] or pic[n]["gate"]:
        return False
    allowed = {"P2_BB", *DEBRIS}
    if extended:
        allowed |= {"P2_BC", "P2_WP"}
    return pic[n]["box"] <= allowed

# ---- workbook ----
wb = openpyxl.load_workbook(XLSX, data_only=True)
eq("sheet names", wb.sheetnames, ["Read me", "Summary", "Duplicate sensitivity", "LP labels",
                                  "OOI labels", "Label combinations", "Size untagged PASS",
                                  "Duplicates and Clear", "Definitions"])
ws = wb["Summary"]
cells = {ws.cell(row=r, column=1).value: ws.cell(row=r, column=2).value for r in range(1, ws.max_row + 1)}
eq("records", cells["Annotation records, all retained"], len(manifest) + 4)
eq("second records", cells["Second records of four pairs, retained"], 4)
eq("distinct", cells["Distinct pictures"], len(manifest))
eq("marked", cells["Pictures with at least one mark"], len(marked))
eq("clear", cells["Clear"], len(clear))
eq("unannotated", cells["Unannotated, excluded from labels"], len(keys - labelled))
eq("labelled", cells["Labelled pictures"], len(labelled))
eq("lp pictures", cells["At least one LP tag"], len(lp_pics))
eq("ooi pictures", cells["At least one OOI box"], len(ooi_pics))
eq("both", cells["LP tag and OOI box"], len(lp_pics & ooi_pics))
eq("single lp", cells["Single label, LP"], len(single_lp))
eq("single ooi", cells["Single label, OOI"], len(single_ooi))
for k in (2, 3, 4):
    eq(f"{k} labels", cells[f"Exactly {'two' if k == 2 else 'three' if k == 3 else 'four'} labels"], dist[k])

ws = wb["Duplicate sensitivity"]
row_of = {ws.cell(row=r, column=1).value: r for r in range(1, ws.max_row + 1)}
eq("sens records", [ws.cell(row=row_of["Annotation records"], column=c).value for c in (2, 3, 4)],
   [13682, 13678, 13674])
eq("sens labelled", [ws.cell(row=row_of["Labelled pictures"], column=c).value for c in (2, 3, 4)],
   [13677, 13673, 13669])
eq("sens lp", [ws.cell(row=row_of["Pictures with an LP tag"], column=c).value for c in (2, 3, 4)],
   [9252, 9251, 9250])
eq("sens ooi", [ws.cell(row=row_of["Pictures with an OOI box"], column=c).value for c in (2, 3, 4)],
   [10032, 10028, 10024])
eq("sens both", [ws.cell(row=row_of["Pictures with both"], column=c).value for c in (2, 3, 4)],
   [5649, 5648, 5647])
eq("sens single", [ws.cell(row=row_of["Single label"], column=c).value for c in (2, 3, 4)],
   [4111, 4111, 4111])
eq("sens three", [ws.cell(row=row_of["Three labels"], column=c).value for c in (2, 3, 4)],
   [2756, 2754, 2752])
eq("sens BC", [ws.cell(row=row_of["P2_BC"], column=c).value for c in (3, 4, 5)],
   [4991, 4989, 4986])
eq("sens BB change", [ws.cell(row=row_of["P2_BB"], column=c).value for c in (6, 7)], [-4, -8])

ws = wb["LP labels"]
eq("LP headers", [ws.cell(row=4, column=c).value for c in range(1, 5)],
   ["Code", "Class", "Pictures", "Share of labelled pictures"])
eq("LP total label", ws.cell(row=20, column=1).value, "Any LP tag")
eq("LP total pictures", ws.cell(row=20, column=3).value, len(lp_pics))
lp_note = ws.cell(row=22, column=1).value
eq("LP note states tag entries", "12,250" in lp_note and "six" in lp_note, True)

ws = wb["OOI labels"]
eq("OOI headers", [ws.cell(row=4, column=c).value for c in range(1, 7)],
   ["Code", "Class", "Pictures", "Boxes", "Of which size-flagged", "Share of labelled pictures"])
eq("OOI total label", ws.cell(row=13, column=1).value, "Any OOI box")
eq("OOI total pictures", ws.cell(row=13, column=3).value, len(ooi_pics))
eq("OOI total boxes", ws.cell(row=13, column=4).value, box_total)

ws = wb["Label combinations"]
vals = [(ws.cell(row=r, column=1).value, ws.cell(row=r, column=2).value)
        for r in range(1, ws.max_row + 1)]
labels_tbl = dict(vals[5:16])
for k in range(1, 10):
    eq(f"count table {k}", labels_tbl[f"{k} label" + ("" if k == 1 else "s")], dist[k])
eq("count clear", labels_tbl["Clear"], len(clear))
eq("count total", labels_tbl["Total"], len(labelled))
eq("labels sum", sum(dist[k] for k in range(1, 10)) + len(clear), len(labelled))

rows_1 = [(a, b) for a, b in vals if isinstance(a, str) and a in
          {f"{c}" for c in ("Missing Primary Package", "Primary Package Misalignment",
                            "Cavity Off Center", "Bubble", "Field of View Obstructed",
                            "No Lens", "Foreign Matter", "Fiber", "Low Dose", "Bubble Cluster",
                            "Extraneous Polymer", "Lens Off Center", "Wet Package", "HEMA",
                            "Dirty Camera")}]
eq("one-label table rows", len(rows_1), 15)
eq("one-label table sum", sum(b for _, b in rows_1), sum(single_counts.values()))
eq("one-label total row", [b for a, b in vals if a == "Total"][-1], sum(single_counts.values()))

comp1 = comp(1)
eq("comp1 lp", comp1[(1, 0)], len(single_lp))
eq("comp1 ooi", comp1[(0, 1)], len(single_ooi))
comp2 = comp(2)
eq("comp2 2ooi", comp2[(0, 2)], 2565)
eq("comp2 1+1", comp2[(1, 1)], 1507)
eq("comp2 2lp", comp2[(2, 0)], 164)

# exact and inclusive tables: count rows between their headers and the next blank/header
def block_rows(header):
    start = next(r for r, (a, _) in enumerate(vals, 1) if a == header)
    out = []
    for a, b in vals[start:]:
        if a is None or a in ("Exact pair (the complete label set)",
                              "Inclusive pair (both labels, further labels allowed)",
                              "Composition", "Exact label set"):
            break
        out.append((a, b))
    return out

exact2 = block_rows("Exact pair (the complete label set)")
incl2 = block_rows("Inclusive pair (both labels, further labels allowed)")
eq("exact2 rows", len(exact2), 15)
eq("incl2 rows", len(incl2), 15)
eq("exact2 top", exact2[0][1], pairs_exact.most_common(1)[0][1])
eq("incl2 top", incl2[0][1], pair_incl.most_common(1)[0][1])
eq("exact2 descending", all(exact2[i][1] >= exact2[i + 1][1] for i in range(len(exact2) - 1)), True)
eq("incl2 descending", all(incl2[i][1] >= incl2[i + 1][1] for i in range(len(incl2) - 1)), True)

comp3 = comp(3)
eq("comp3 lp2ooi", comp3[(1, 2)], 1529)
eq("comp3 3ooi", comp3[(0, 3)], 1018)
eq("comp3 2lp1ooi", comp3[(2, 1)], 207)
eq("comp3 three LP", comp3[(3, 0)], 0)
eq("zero-split note present", "non-zero splits only" in (ws.cell(row=2, column=1).value or ""), True)
comp4 = comp(4)
for k, rows_k, total_k in ((1, comp1, 4111), (2, comp2, 4236), (3, comp3, 2754), (4, comp4, 1262)):
    eq(f"composition {k} sums to its bucket", sum(rows_k.values()), total_k)
eq("comp4 1lp3ooi", comp4[(1, 3)], 627)
eq("comp4 2lp2ooi", comp4[(2, 2)], 438)
eq("comp4 4ooi", comp4[(0, 4)], 112)
eq("comp4 3lp1ooi", comp4[(3, 1)], 85)
eq("comp4 four LP", comp4[(4, 0)], 0)

ws = wb["Size untagged PASS"]
pass_rows = {}
for r in range(5, 10):
    name = ws.cell(row=r, column=1).value
    pass_rows[name] = [ws.cell(row=r, column=c).value for c in range(2, 9)]
for code, name in [("P3_FM", "Foreign Matter"), ("P3_FIB", "Fiber"),
                   ("P3_EP", "Extraneous Polymer"), ("P3_HE", "HEMA")]:
    pics = sum(1 for n in labelled if code in pic[n]["box"])
    flagged = sum(1 for n in labelled if (code + "_MICRON_THRESHOLD") in pic[n]["gate"])
    unt = [n for n in labelled if code in pic[n]["box"] and (code + "_MICRON_THRESHOLD") not in pic[n]["gate"]]
    eq(f"{code} pics", pass_rows[name][0], pics)
    eq(f"{code} flagged", pass_rows[name][1], flagged)
    eq(f"{code} untagged", pass_rows[name][2], len(unt))
    eq(f"{code} strict", pass_rows[name][3], sum(1 for n in unt if passed(n, False)))
    eq(f"{code} extended", pass_rows[name][5], sum(1 for n in unt if passed(n, True)))
unt_u = [n for n in labelled
         if any(c in pic[n]["box"] for c in DEBRIS)
         and not any((c + "_MICRON_THRESHOLD") in pic[n]["gate"] for c in DEBRIS)]
eq("union no flag", pass_rows["Any of the four (no size flag at all)"][2], len(unt_u))
eq("union strict", pass_rows["Any of the four (no size flag at all)"][3], sum(1 for n in unt_u if passed(n, False)))
eq("union extended", pass_rows["Any of the four (no size flag at all)"][5], sum(1 for n in unt_u if passed(n, True)))

ws = wb["Duplicates and Clear"]
iou = [ws.cell(row=r, column=5).value for r in range(7, 11)]
eq("iou values", iou, [0.95, 0.88, 1.0, 0.84])
clear_row = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == "Still Clear")
eq("clear still", ws.cell(row=clear_row, column=4).value, len(clear))


# ---- every share against its own denominator, every total against its parts ----
lab = len(labelled)
ws = wb["LP labels"]
for r in range(5, 20):
    close(f"LP share row {r}", ws.cell(row=r, column=4).value,
          ws.cell(row=r, column=3).value / lab)
close("LP total share", ws.cell(row=20, column=4).value, ws.cell(row=20, column=3).value / lab)

ws = wb["OOI labels"]
for r in range(5, 13):
    close(f"OOI share row {r}", ws.cell(row=r, column=6).value,
          ws.cell(row=r, column=3).value / lab)
close("OOI total share", ws.cell(row=13, column=6).value, ws.cell(row=13, column=3).value / lab)

ws = wb["Size untagged PASS"]
for r in range(5, 10):
    pics, flagged, unt, strict, sh, ext, eh = [ws.cell(row=r, column=c).value for c in range(2, 9)]
    eq(f"PASS row {r} adds", flagged + unt, pics)
    eq(f"PASS row {r} strict <= untagged", strict <= unt, True)
    eq(f"PASS row {r} extended >= strict", ext >= strict, True)
    eq(f"PASS row {r} extended <= untagged", ext <= unt, True)
    if unt == 0:
        eq(f"PASS row {r} strict share blank", sh, "-")
        eq(f"PASS row {r} extended share blank", eh, "-")
    else:
        close(f"PASS row {r} strict share", sh, strict / unt)
        close(f"PASS row {r} extended share", eh, ext / unt)

# Summary population and group algebra
eq("summary population adds",
   cells["Pictures with at least one mark"] + cells["Clear"] + cells["Unannotated, excluded from labels"],
   cells["Distinct pictures"])
eq("summary labelled adds", cells["Pictures with at least one mark"] + cells["Clear"], cells["Labelled pictures"])
eq("summary lp/ooi/both",
   cells["At least one LP tag"] + cells["At least one OOI box"] - cells["LP tag and OOI box"],
   cells["Pictures with at least one mark"])

# Label-count table sums to the labelled total
eq("label counts add", sum(labels_tbl[f"{k} label" + ("" if k == 1 else "s")] for k in range(1, 10))
   + labels_tbl["Clear"], labels_tbl["Total"])

# Duplicate sensitivity: each base reconciles, each delta is a subtraction
ws = wb["Duplicate sensitivity"]
row_of = {ws.cell(row=r, column=1).value: r for r in range(1, ws.max_row + 1)}
for col, base in ((2, "all"), (3, "one"), (4, "exclude")):
    records = ws.cell(row=row_of["Annotation records"], column=col).value
    labelled_b = ws.cell(row=row_of["Labelled pictures"], column=col).value
    clear_b = ws.cell(row=row_of["Clear"], column=col).value
    unann_b = ws.cell(row=row_of["Unannotated"], column=col).value
    lp_b = ws.cell(row=row_of["Pictures with an LP tag"], column=col).value
    ooi_b = ws.cell(row=row_of["Pictures with an OOI box"], column=col).value
    both_b = ws.cell(row=row_of["Pictures with both"], column=col).value
    eq(f"sens {base} labelled+unannotated", labelled_b + unann_b, records)
    eq(f"sens {base} lp+ooi-both", lp_b + ooi_b - both_b, labelled_b - clear_b)
    bucket_names = ["Single label"] + [f"{w} labels" for w in
                                      ("Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine")]
    eq(f"sens {base} buckets+clear",
       sum(ws.cell(row=row_of[n], column=col).value for n in bucket_names) + clear_b, labelled_b)

for code in ("P2_BB", "P2_BC", "P3_FIB", "P3_HE", "P3_FM", "P3_EP", "P1_LR", "P2_DC"):
    a, o, e = [ws.cell(row=row_of[code], column=c).value for c in (3, 4, 5)]
    eq(f"sens {code} one delta", ws.cell(row=row_of[code], column=6).value, o - a)
    eq(f"sens {code} both delta", ws.cell(row=row_of[code], column=7).value, e - a)

# Clear block adds
ws = wb["Duplicates and Clear"]
clear_vals = {ws.cell(row=r, column=1).value: ws.cell(row=r, column=4).value for r in range(1, ws.max_row + 1)}
eq("clear reannotated adds", clear_vals["- bubble boxes only"] + clear_vals["- another object box only"]
   + clear_vals["- presentation tag present"], clear_vals["Re-annotated with a class"])
eq("clear folder adds", clear_vals["Re-annotated with a class"] + clear_vals["Still Clear"],
   clear_vals["Clear-folder images in the frozen set"])

# No percentage outside 0..1
for sh in wb.worksheets:
    for row in sh.iter_rows():
        for cell in row:
            if isinstance(cell.value, (int, float)) and "%" in (cell.number_format or ""):
                if not 0 <= cell.value <= 1:
                    fails.append(f"share out of range {sh.title}!{cell.coordinate}: {cell.value}")

# no zero-label phrasing anywhere
bad = []
for sh in wb.worksheets:
    for row in sh.iter_rows(values_only=True):
        for v in row:
            if isinstance(v, str) and "0 label" in v.lower():
                bad.append((sh.title, v))
eq("no zero-label string", bad, [])

print(f"checks: {checks}, failures: {len(fails)}")
for f in fails:
    print("FAIL", f)
sys.exit(1 if fails else 0)
