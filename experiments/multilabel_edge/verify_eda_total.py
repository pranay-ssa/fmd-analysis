"""Verify the total-EDA workbook against the annotation, the splits and the record workbook.

Recomputes the population, the LP and OOI tables, the tag combinations, the label-count
distribution and both splits from the source files, then compares the workbook cell by cell
by header name. Ends with a tampered-cell proof.

Usage: python verify_eda_total.py
Exit code 0 when the workbook agrees untampered and the tamper is caught.
"""
import csv
import json
import os
import statistics
from collections import Counter, defaultdict

import openpyxl

ROOT = "D:/fmd-analysis"
RUN = f"{ROOT}/run/eda_full_24files_20261028"
REC = f"{ROOT}/run/eda_batch24_20261028/record_before_after.csv"
WB = f"{ROOT}/reports/eda_total_20261028/FMD_EDA_Total_20261028.xlsx"

LP = [("P1_MPP", "Missing Primary Package", "missing_primary_package", "missing_primary_package"),
      ("P1_PPM", "Package Misalignment", "package_misalignment", "package_misalignment"),
      ("P1_COC", "Cavity Off Center", "cavity_off_center", "cavity_off_center"),
      ("P2_FOV", "View Obstructed", "view_obstructed", "view_obstructed"),
      ("P2_LOC", "Lens Off Center", "lens_off_center", "lens_off_center"),
      ("P1_NL", "No Lens", "missing_lens", "no_lens"),
      ("P1_ML", "Multiple Lens", "multiple_lenses", "multiple_lenses"),
      ("P1_FL", "Folded Lens", "folded_lens", "folded_lens"),
      ("P1_EBC", "Edge Bottle-Capped", None, None),
      ("P1_TL", "Torn Lens", None, None),
      ("P1_LR", "Lens Rupture", None, None),
      ("P2_DS", "Dirty Strobe", "dirty_strobe", "dirty_strobe"),
      ("P2_DC", "Dirty Camera", "dirty_camera", "dirty_camera"),
      ("P2_BSC", "Bubble Scatter", "bubble_scatter", "bubble_scatter"),
      ("P2_LD", "Low Dose", "low_dose", "low_dose")]
OOI = ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
       "Extraneous Polymer", "HEMA", "Foreign Matter"]
LEGACY = ["HEMA Obstruction", "Bubble On 123", "Bubble On Edge"]
GATE_OF = {"Foreign Matter": "foreign_matter_micron_gate", "Fiber": "fiber_micron_gate",
           "Extraneous Polymer": "extraneous_polymer_micron_gate", "HEMA": "hema_micron_gate"}
GATE_NAME = {"foreign_matter_micron_gate": "Foreign Matter gate", "fiber_micron_gate": "Fiber gate",
             "extraneous_polymer_micron_gate": "Extraneous Polymer gate", "hema_micron_gate": "HEMA gate"}
OOI_CANON = {"bubble": "Bubble", "bubble_irregular": "Bubble", "stretched_bubble": "Bubble",
             "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
             "foreign_matter": "Foreign Matter", "fiber": "Fiber",
             "extraneous_polymer": "Extraneous Polymer", "hema_obstruction": "HEMA", "hema_fragment": "HEMA"}
LP_CANON = {cid: name for _, name, cid, _ in LP if cid}
SPLIT_DISPLAY = {k: n for _, n, _, k in LP if k}
SPLIT_DISPLAY.update({"bubble": "Bubble", "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
                      "clear": "Clear"})
SPLIT_DISPLAY.update({k: v for k, v in GATE_NAME.items()})


def rows(path):
    return list(csv.DictReader(open(path, newline="", encoding="utf-8")))


def num(v):
    return -1 if v is None else int(v)


def table(ws):
    headers, out, started = None, [], False
    for row in ws.iter_rows(values_only=True):
        vals = list(row)
        if not started:
            text = [str(v).strip() if v is not None else "" for v in vals]
            if "Code" in text and ("Class" in text or "Label" in text):
                headers = {h: i for i, h in enumerate(text) if h}
                started = True
            continue
        out.append(vals)
    return headers or {}, out


def find(rows_, headers, name):
    col = headers.get("Class", headers.get("Label", 1))
    for r in rows_:
        if len(r) > col and r[col] is not None and str(r[col]).strip() == name:
            return r
    return None


def cell(row, headers, header):
    i = headers.get(header)
    return row[i] if i is not None and len(row) > i else None


def recompute():
    codes_all = defaultdict(set)
    pics = defaultdict(lambda: {"box": set(), "tag": set(), "legacy": set(), "gate": set(), "geo": defaultdict(list)})
    for r in rows(f"{RUN}/resolved_labels.csv"):
        codes_all[r["picture_md5"]].add(r["code"])
        p = pics[r["picture_md5"]]
        cid, kind = r["canonical_id"], r["shape_kind"]
        if kind == "box" and cid in ("bubble_on_123", "bubble_on_edge"):
            p["legacy"].add("Bubble On 123" if cid == "bubble_on_123" else "Bubble On Edge")
        elif kind == "box":
            name = OOI_CANON.get(cid)
            if name:
                p["box"].add(name)
                p["geo"][name].append((float(r["xbr"]) - float(r["xtl"]), float(r["ybr"]) - float(r["ytl"])))
        elif kind == "tag":
            if cid in LP_CANON:
                p["tag"].add(LP_CANON[cid])
            elif cid == "hema_obstruction":
                p["tag"].add("HEMA Obstruction")
        if cid.endswith("_micron_gate"):
            p["gate"].add(GATE_NAME[cid])
    clear = {x["md5"] for x in rows(f"{RUN}/picture_table.csv")
             if x["winning_path"].split("/")[1:2] == ["Clear"] and x["md5"] not in pics}
    labels = ([GATE_NAME[k] for k in GATE_NAME] + ["Bubble", "Bubble Cluster", "Wet Package"]
              + [n for _, n, c, _ in LP if c])
    sets = {}
    for m, p in pics.items():
        s = set(p["tag"]) | p["box"] | p["legacy"]
        if s:
            sets[m] = s
    return pics, clear, labels, sets, codes_all


def main_checks():
    pics, clear, labels, sets, codes_all = recompute()
    marked = len(pics)
    analysed = marked + len(clear)
    v6 = json.load(open(f"{ROOT}/run/split_20261028_v6/meta.json", encoding="utf-8"))
    v7 = json.load(open(f"{ROOT}/run/split_20261028_v7/meta.json", encoding="utf-8"))
    rec = {r["name"]: r for r in rows(REC)}

    wb = openpyxl.load_workbook(WB, data_only=True)
    f = []

    ws = wb["Summary"]
    want_pop = {"Pictures examined": 10614, "Pictures with at least one mark": marked,
                "Pictures with at least one OOI tag": sum(1 for p in pics.values() if p["box"]),
                "Pictures with at least one lens presentation tag": sum(1 for p in pics.values() if p["tag"] - {"HEMA Obstruction"}),
                "Pictures with nothing marked (Clear)": len(clear), "Analysed set": analysed}
    for k, v in want_pop.items():
        row = next((r for r in ws.iter_rows(values_only=True) if r[0] == k), None)
        if row is None:
            f.append(f"Summary: row missing {k}")
        elif num(row[1]) != v:
            f.append(f"Summary {k}: {row[1]} vs {v}")
    for i, (label, ratio) in enumerate((("70 / 30", "70_30"), ("80 / 20", "80_20"))):
        row = next((r for r in ws.iter_rows(values_only=True) if r[0] == label), None)
        if row is None:
            f.append(f"Summary: split row missing {label}")
            continue
        b = v6["splits"][ratio]["split_counts"]; a = v7["splits"][ratio]["split_counts"]
        want = [b.get("train", 0), b.get("test", 0), v6["rows"], a.get("train", 0), a.get("test", 0), v7["rows"],
                6938 - v6["rows"], analysed - v7["rows"]]
        for j, w in enumerate(want):
            if num(row[1 + j]) != w:
                f.append(f"Summary {label} col {j+2}: {row[1+j]} vs {w}")

    ws = wb["LP Summary"]
    headers, rws = table(ws)
    if len([r for r in rws if r and r[headers.get('Class', 1)] in [x[1] for x in LP]]) != 15:
        f.append("LP Summary: expected 15 guide rows")
    for code, name, cid, key in LP:
        row = find(rws, headers, name)
        if row is None:
            f.append(f"LP: row missing {name}")
            continue
        n = sum(1 for p in pics.values() if name in p["tag"])
        if num(cell(row, headers, "Pictures")) != n:
            f.append(f"LP {name}: {cell(row, headers, 'Pictures')} vs {n}")
        share = cell(row, headers, "Share of analysed pictures")
        if share is None or abs(float(share) - n / analysed) > 1e-6:
            f.append(f"LP {name} share: {share} vs {n/analysed:.6f}")
        if key:
            for h, ratio in (("In 70/30 split", "70_30"), ("In 80/20 split", "80_20")):
                w = v7["splits"][ratio]["per_class"][key]["train"] + v7["splits"][ratio]["per_class"][key]["test"]
                if num(cell(row, headers, h)) != w:
                    f.append(f"LP {name} / {h}: {cell(row, headers, h)} vs {w}")

    # Tag combinations
    exact, incl = Counter(), Counter()
    for s in sets.values():
        items = sorted(s)
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                incl[(items[i], items[j])] += 1
                if len(items) == 2:
                    exact[(items[i], items[j])] += 1
    ws = wb["Tag Combinations"]
    all_rows = list(ws.iter_rows(values_only=True))
    texts = [str(r[0]).strip() if r[0] is not None else "" for r in all_rows]
    try:
        t1 = texts.index("Table 1 - Exact pairs")
        t2 = texts.index("Table 2 - Inclusive pairs")
        t3 = next(i for i, t in enumerate(texts) if "How many" in t and "label" in t.lower())
    except StopIteration:
        f.append("Tag Combinations: section headers missing")
        t1 = t2 = t3 = 0
    for table_rows, counter, title in ((all_rows[t1:t2], exact, "exact"), (all_rows[t2:t3], incl, "inclusive")):
        pairs = []
        for r in table_rows:
            if r[0] is not None and r[1] is not None and str(r[0]).strip().isdigit():
                pairs.append((str(r[1]).strip(), int(r[2])))
        want = [(f"{a} + {b}", n) for (a, b), n in sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:15]]
        if pairs != want:
            f.append(f"Tag Combinations {title}: rows differ from recomputation")
            for got, exp in zip(pairs, want):
                if got != exp:
                    f.append(f"   {title}: {got} vs {exp}")
                    break
    # label counts
    dist = Counter()
    for m in pics:
        dist[len(sets.get(m, set()))] += 1
    dist[1] += len(clear)
    got = {}
    for r in all_rows[t3:]:
        if r[0] and "label" in str(r[0]).lower() and str(r[0]).strip()[0].isdigit() and isinstance(r[1], (int, float)):
            got[int(str(r[0]).split()[0])] = int(r[1])
    for n, c in sorted(dist.items()):
        if got.get(n) != c:
            f.append(f"Label count {n}: {got.get(n)} vs {c}")
    if 0 in got:
        f.append(f"Label counts: a zero-label bucket is present ({got[0]}), but every analysed picture has a label")
    if sum(got.values()) != analysed:
        f.append(f"Label counts: rows sum to {sum(got.values())}, expected {analysed}")

    # OOI
    ws = wb["OOI Summary"]
    headers, rws = table(ws)
    if len([r for r in rws if r and r[headers.get('Class', 1)] in OOI]) != 8:
        f.append("OOI: expected 8 guide rows")
    for name in OOI:
        row = find(rws, headers, name)
        if row is None:
            f.append(f"OOI: row missing {name}")
            continue
        pset = [m for m, p in pics.items() if name in p["box"]]
        gate = sum(1 for m in pset if GATE_OF.get(name) and GATE_NAME[GATE_OF[name]] in pics[m]["gate"]) if name in GATE_OF else 0
        tags = sum(len(p["geo"][name]) for p in pics.values())
        for h, w in (("Pictures", len(pset)), ("Of which size-flagged", gate), ("OOI tags", tags)):
            if num(cell(row, headers, h)) != w:
                f.append(f"OOI {name} / {h}: {cell(row, headers, h)} vs {w}")
        geos = [g for p in pics.values() for g in p["geo"][name]]
        if geos:
            for h, w in (("Typical width (px)", statistics.median(g[0] for g in geos)),
                         ("Typical height (px)", statistics.median(g[1] for g in geos))):
                v = cell(row, headers, h)
                if v is None or abs(float(v) - w) > 0.06:
                    f.append(f"OOI {name} / {h}: {v} vs {w:.1f}")
    for name in OOI:
        row = find(rws, headers, name)
        if row is not None and str(cell(row, headers, "In guide")).strip() != "Yes":
            f.append(f"OOI: {name} not marked as a guide class")
    for name in LEGACY:
        row = find(rws, headers, name)
        if row is None:
            f.append(f"OOI: legacy row missing {name}")
            continue
        if str(cell(row, headers, "In guide")).strip() != "Legacy":
            f.append(f"OOI: {name} not marked legacy")
        if name == "HEMA Obstruction":
            n = sum(1 for p in pics.values() if "HEMA Obstruction" in p["tag"])
            tags = n
        else:
            cid = "bubble_on_123" if name == "Bubble On 123" else "bubble_on_edge"
            n = len({r["picture_md5"] for r in rows(f"{RUN}/resolved_labels.csv") if r["canonical_id"] == cid})
            tags = sum(1 for r in rows(f"{RUN}/resolved_labels.csv") if r["canonical_id"] == cid)
        for h, w in (("Pictures", n), ("OOI tags", tags)):
            if num(cell(row, headers, h)) != w:
                f.append(f"OOI legacy {name} / {h}: {cell(row, headers, h)} vs {w}")

    # outside-split block
    ws = wb["Tag Combinations"]
    all_rows = list(ws.iter_rows(values_only=True))
    hdr_i = next((i for i, r in enumerate(all_rows) if r[0] == "Reason" and r[1] == "Detail"), None)
    if hdr_i is None:
        f.append("Outside-split block: header missing")
    else:
        got_rows, total = {}, None
        for r in all_rows[hdr_i + 1:]:
            if r[0] == "Total":
                total = int(r[2])
                break
            if r[0] and r[1]:
                got_rows[(str(r[0]), str(r[1]))] = int(r[2])
        SPLIT_CODES = ({"P3_FM_MICRON_THRESHOLD", "P3_FIB_MICRON_THRESHOLD", "P3_EP_MICRON_THRESHOLD",
                        "P3_HE_MICRON_THRESHOLD", "P2_BB", "Bubble", "P2_BI", "Bubble Irregular",
                        "P2_BST", "Stretched Bubble", "P2_BC", "Bubble Cluster", "P2_WP", "Wet Package",
                        "F2_FOV"}
                       | {code for code, _, _, _ in LP if code})
        PLAIN_MAP = {"P3_FM": "Foreign Matter", "Foreign Matter": "Foreign Matter",
                     "P3_FIB": "Fiber", "Fiber": "Fiber", "P3_EP": "Extraneous Polymer",
                     "Extraneous Polymer": "Extraneous Polymer", "P3_HE": "HEMA", "HEMA Fragment": "HEMA"}
        LEG_DETAIL = {"P2_HMO": "HEMA Obstruction (P2_HMO)", "Bubble On 123": "Bubble On 123",
                      "Bubble On Edge": "Bubble On Edge"}
        want_rows = Counter()
        for m, cs in codes_all.items():
            if cs & SPLIT_CODES:
                continue
            fams = sorted({PLAIN_MAP[c] for c in cs if c in PLAIN_MAP})
            if fams:
                want_rows[("Object only, no size flag", " + ".join(fams))] += 1
            else:
                want_rows[("Legacy class only", " + ".join(sorted({LEG_DETAIL.get(c, c) for c in cs & set(LEG_DETAIL)})))] += 1
        if got_rows != dict(want_rows):
            f.append(f"Outside-split block: {got_rows} vs {dict(want_rows)}")
        if total != sum(want_rows.values()):
            f.append(f"Outside-split total: {total} vs {sum(want_rows.values())}")

    # Split sheet
    ws = wb["Training and Test Split"]
    ratio = None
    seen = set()
    for r in ws.iter_rows(values_only=True):
        a = str(r[0]).strip() if r[0] is not None else ""
        if a.endswith("split") and "/" in a:
            ratio = "70_30" if a.startswith("70") else "80_20"
            continue
        if ratio and r[1] and str(r[1]).strip() in SPLIT_DISPLAY.values():
            name = str(r[1]).strip()
            key = next((k for k, v in SPLIT_DISPLAY.items() if v == name), None)
            b = v6["splits"][ratio]["per_class"].get(key, {"train": 0, "test": 0})
            aa = v7["splits"][ratio]["per_class"].get(key, {"train": 0, "test": 0})
            want = [b["train"], b["test"], b["train"] + b["test"], aa["train"], aa["test"], aa["train"] + aa["test"],
                    aa["train"] - b["train"], aa["test"] - b["test"]]
            got = [num(v) for v in r[2:10]]
            if got != want:
                f.append(f"Split {ratio} {name}: {got} vs {want}")
            seen.add((ratio, name))
        if ratio and r[1] == "Total split rows":
            b = v6["splits"][ratio]["split_counts"]; aa = v7["splits"][ratio]["split_counts"]
            want = [b["train"], b["test"], v6["rows"], aa["train"], aa["test"], v7["rows"],
                    aa["train"] - b["train"], aa["test"] - b["test"]]
            if [num(v) for v in r[2:10]] != want:
                f.append(f"Split {ratio} totals: {[num(v) for v in r[2:10]]} vs {want}")
    for ratio_ in ("70_30", "80_20"):
        if len([1 for (rt, _) in seen if rt == ratio_]) != 20:
            f.append(f"Split {ratio_}: expected 20 class rows")

    # Reconciliation against the record workbook itself
    ws = wb["Reconciliation"]
    rec_wb = openpyxl.load_workbook(f"{ROOT}/reports/eda_24files_20261028/FMD_EDA_Record_20261028.xlsx", data_only=True)
    rec_pop, rec_lab = {}, {}
    for row in rec_wb["Summary"].iter_rows(values_only=True):
        if not row:
            continue
        if row[0] in ("Pictures with at least one mark", "Pictures with nothing marked (Clear)", "Analysed set"):
            rec_pop[row[0]] = int(row[1])
        if row[1] and isinstance(row[4], int):
            rec_lab[str(row[1])] = int(row[4])
    for r in ws.iter_rows(min_row=5, values_only=True):
        label = r[0]
        if not label or str(r[4]).strip() not in ("Yes", "No", "n/a"):
            continue
        if label.startswith("Split rows"):
            continue
        if label == "Pictures with marks":
            want = rec_pop.get("Pictures with at least one mark")
        elif label == "Clear":
            want = rec_pop.get("Pictures with nothing marked (Clear)")
        elif label == "Analysed set":
            want = rec_pop.get("Analysed set")
        else:
            want = rec_lab.get(str(label).replace(" pictures", ""))
        if want is None:
            f.append(f"Reconciliation {label}: not found in the record workbook")
            continue
        if num(r[1]) != want or num(r[2]) != want:
            f.append(f"Reconciliation {label}: total {r[1]}, record column {r[2]}, record workbook {want}")
        if str(r[4]).strip() != "Yes":
            f.append(f"Reconciliation {label}: Match column reads {r[4]}")
    return f


def tamper_check():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "t.xlsx")
    shutil.copy(WB, p)
    wb = openpyxl.load_workbook(p)
    ws = wb["Training and Test Split"]
    for row in ws.iter_rows():
        if row[1].value == "Bubble":
            row[5].value = int(row[5].value) + 1
            break
    wb.save(p)
    original = WB
    globals()["WB"] = p
    failures = main_checks()
    globals()["WB"] = original
    return failures


def main():
    f = main_checks()
    print("workbook:", "OK" if not f else f"{len(f)} failures")
    for x in f[:30]:
        print("   ", x)
    t = tamper_check()
    print("tamper:", "CAUGHT" if t else "MISSED")
    ok = not f and t
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
