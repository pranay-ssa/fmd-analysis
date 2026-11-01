"""Verify the two 24-file EDA workbooks against the annotation itself.

Recomputes every table from the annotation files and the resolved label sets, reads the
workbook by header name, and compares. Ends with a tampered-cell proof: a copy with one
cell changed must fail the same check.

Usage: python verify_eda_24files.py
Exit code 0 when both workbooks pass untampered and both tamper checks fail.
"""
import csv
import glob
import os
import shutil
import statistics
import tempfile
from collections import Counter, defaultdict

import openpyxl

# defusedxml first: the annotation XML is client-supplied, so the hardened parser is used
# whenever it is installed and the stdlib parser only as a fallback for a bare environment.
try:
    import defusedxml.ElementTree as ET
except ModuleNotFoundError:  # pragma: no cover
    import xml.etree.ElementTree as ET

ROOT = "D:/fmd-analysis"
XML = f"{ROOT}/data/PRODUCTION_20260925_300"
OLD = f"{ROOT}/run/eda_full_20261028/resolved_labels.csv"
MERGED = f"{ROOT}/run/eda_full_24files_20261028/resolved_labels.csv"
PT = f"{ROOT}/run/eda_full_24files_20261028/picture_table.csv"
WB1 = f"{ROOT}/reports/eda_24files_20261028/FMD_EDA_24Files_20261028.xlsx"
WB2 = f"{ROOT}/reports/eda_24files_20261028/FMD_EDA_Record_20261028.xlsx"

GROUPS = ["7 revised", "17 new", "24 total"]
LP_GUIDE = ["Missing Primary Package", "Package Misalignment", "Cavity Off Center", "View Obstructed",
            "Lens Off Center", "No Lens", "Multiple Lens", "Folded Lens", "Edge Bottle-Capped",
            "Torn Lens", "Lens Rupture", "Dirty Strobe", "Dirty Camera", "Bubble Scatter", "Low Dose"]
OOI_GUIDE = ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
             "Extraneous Polymer", "HEMA", "Foreign Matter"]
LEGACY = ["HEMA Obstruction", "Bubble On 123", "Bubble On Edge"]
LP_IDS = {"missing_primary_package": "Missing Primary Package", "package_misalignment": "Package Misalignment",
          "cavity_off_center": "Cavity Off Center", "view_obstructed": "View Obstructed",
          "lens_off_center": "Lens Off Center", "missing_lens": "No Lens",
          "multiple_lenses": "Multiple Lens", "folded_lens": "Folded Lens",
          "dirty_strobe": "Dirty Strobe", "dirty_camera": "Dirty Camera",
          "bubble_scatter": "Bubble Scatter", "low_dose": "Low Dose"}
OOI_IDS = {"bubble": "Bubble", "bubble_irregular": "Bubble", "stretched_bubble": "Bubble",
           "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
           "foreign_matter": "Foreign Matter", "fiber": "Fiber",
           "extraneous_polymer": "Extraneous Polymer",
           "hema_obstruction": "HEMA", "hema_fragment": "HEMA"}
GATE_BASE = {"foreign_matter": "Foreign Matter", "fiber": "Fiber",
             "extraneous_polymer": "Extraneous Polymer", "hema": "HEMA"}


def rows_of(path):
    return list(csv.DictReader(open(path, newline="", encoding="utf-8")))


def num(v):
    return -1 if v is None else int(v)


def group_of(job):
    return "7 revised" if job <= 4521946 else "17 new"


# ---------- workbook readers ----------
def table(ws):
    """Header row (the first row holding 'Code') -> (headers, data rows after it)."""
    headers, out, started = None, [], False
    for row in ws.iter_rows(values_only=True):
        vals = list(row)
        if not started:
            text = [str(v).strip() if v is not None else "" for v in vals]
            if "Code" in text:
                headers = {h: i for i, h in enumerate(text) if h}
                started = True
            continue
        out.append(vals)
    return headers or {}, out


def find(rows, headers, name):
    col = headers.get("Class", headers.get("Label", 1))
    for r in rows:
        if len(r) > col and r[col] is not None and str(r[col]).strip() == name:
            return r
    return None


def cell(row, headers, header):
    i = headers.get(header)
    if i is None or len(row) <= i:
        return None
    return row[i]


def num_row(ws, label):
    for row in ws.iter_rows(values_only=True):
        if row and row[0] is not None and str(row[0]).strip() == label:
            return row
    return None


# ---------- recompute: batch ----------
def recompute_batch():
    manifest = {os.path.basename(r["path"]).lower(): r["md5"]
                for r in rows_of(f"{ROOT}/run/eda_full_24files_20261028/file_manifest.csv")}
    pop = defaultdict(lambda: {"entries": 0, "zero": 0, "pics": set(), "marked": set()})
    for f in sorted(glob.glob(f"{XML}/annotations_45219*.xml")):
        job = int(os.path.basename(f).split("_")[1].split(".")[0])
        g = group_of(job)
        for im in ET.parse(f).getroot().findall("image"):
            md5 = manifest[os.path.basename(im.get("name") or "").lower()]
            shapes = im.findall("box") + im.findall("tag")
            for grp in (g, "24 total"):
                p = pop[grp]
                p["entries"] += 1; p["pics"].add(md5)
                if shapes:
                    p["marked"].add(md5)
                else:
                    p["zero"] += 1
    lp = defaultdict(lambda: defaultdict(set))
    ooi = defaultdict(lambda: defaultdict(lambda: {"pics": set(), "tags": 0}))
    flags = defaultdict(lambda: defaultdict(set))
    per_pic = defaultdict(Counter)
    per_class_pic = defaultdict(Counter)
    for r in rows_of(MERGED):
        if r["source_group"] != "production_20260925":
            continue
        g = group_of(int(r["source_file"].split("_")[1].split(".")[0]))
        cid = r["canonical_id"]
        if cid.endswith("_micron_gate"):
            base = GATE_BASE[cid[:-len("_micron_gate")]]
            for grp in (g, "24 total"):
                flags[grp][base].add(r["picture_md5"])
            continue
        if r["shape_kind"] == "box" and cid in OOI_IDS:
            name = OOI_IDS[cid]
            for grp in (g, "24 total"):
                ooi[grp][name]["pics"].add(r["picture_md5"])
                ooi[grp][name]["tags"] += 1
                per_pic[grp][r["picture_md5"]] += 1
            per_class_pic[name][r["picture_md5"]] += 1
        elif r["shape_kind"] == "tag" and cid in LP_IDS:
            for grp in (g, "24 total"):
                lp[grp][LP_IDS[cid]].add(r["picture_md5"])
    return pop, lp, ooi, flags, per_pic, per_class_pic


# ---------- recompute: record ----------
def recompute_record():
    pt = rows_of(PT)
    clearf = {p["md5"] for p in pt if p["winning_path"].split("/")[1:2] == ["Clear"]}
    out = {}
    for scope, path in (("old", OLD), ("new", MERGED)):
        rows = rows_of(path)
        marked = {r["picture_md5"] for r in rows}
        table_ = defaultdict(lambda: {"pics": set(), "tags": 0})
        flags = defaultdict(set)
        for r in rows:
            cid, kind = r["canonical_id"], r["shape_kind"]
            if cid.endswith("_micron_gate"):
                flags[GATE_BASE[cid[:-len("_micron_gate")]]].add(r["picture_md5"])
                continue
            if kind == "tag" and cid == "hema_obstruction":
                name = "HEMA Obstruction"
            elif kind == "box" and cid in ("hema_obstruction", "hema_fragment"):
                name = "HEMA"
            elif kind == "box" and cid in OOI_IDS:
                name = OOI_IDS[cid]
            elif kind == "tag" and cid in LP_IDS:
                name = LP_IDS[cid]
            elif cid in ("bubble_on_123", "bubble_on_edge"):
                name = "Bubble On 123" if cid == "bubble_on_123" else "Bubble On Edge"
            else:
                continue
            table_[name]["pics"].add(r["picture_md5"])
            table_[name]["tags"] += 1
        out[scope] = {"marked": len(marked), "clear": len(clearf - marked),
                      "analysed": len(marked) + len(clearf - marked), "table": table_, "flags": flags}
    return out


# ---------- checks ----------
def check_batch(wb_path):
    failures = []
    pop, lp, ooi, flags, per_pic, per_class_pic = recompute_batch()
    marked = len(pop["24 total"]["marked"])
    wb = openpyxl.load_workbook(wb_path, data_only=True)

    ws = wb["Summary"]
    for g in GROUPS:
        row = num_row(ws, g)
        want = [pop[g]["entries"], len(pop[g]["pics"]), len(pop[g]["marked"]), pop[g]["zero"]]
        got = list(row[1:5]) if row else [None] * 4
        for i, (w, gv) in enumerate(zip(want, got)):
            if num(gv) != w:
                failures.append(f"Summary {g} col {i+2}: workbook {gv}, recomputed {w}")

    ws = wb["Lens Presentation 7-17-24"]
    headers, rows = table(ws)
    if len([r for r in rows if r and r[headers.get('Class', 1)] in LP_GUIDE]) != 15:
        failures.append("Lens Presentation: expected 15 guide rows")
    for name in LP_GUIDE:
        row = find(rows, headers, name)
        if row is None:
            failures.append(f"Lens Presentation: row missing for {name}")
            continue
        for g in GROUPS:
            got = cell(row, headers, g)
            if num(got) != len(lp[g][name]):
                failures.append(f"Lens Presentation {name} / {g}: workbook {got}, recomputed {len(lp[g][name])}")
        if name in ("Edge Bottle-Capped", "Torn Lens", "Lens Rupture"):
            for g in GROUPS:
                if num(cell(row, headers, g)) != 0:
                    failures.append(f"Lens Presentation {name} / {g}: should be 0")
        share = cell(row, headers, "Share of pictures with marks (24)")
        want_share = len(lp["24 total"][name]) / marked
        if share is None or abs(float(share) - want_share) > 1e-9:
            failures.append(f"Lens Presentation {name} share: workbook {share}, recomputed {want_share:.6f}")

    ws = wb["OOI tags, 7 vs 17 vs 24"]
    headers, rows = table(ws)
    if len([r for r in rows if r and r[headers.get('Class', 1)] in OOI_GUIDE]) != 8:
        failures.append("OOI: expected 8 guide rows")
    for name in OOI_GUIDE:
        row = find(rows, headers, name)
        if row is None:
            failures.append(f"OOI: row missing for {name}")
            continue
        for g in GROUPS:
            for header, want in ((f"{g}: pictures", len(ooi[g][name]["pics"])),
                                 (f"{g}: tags", ooi[g][name]["tags"]),
                                 (f"{g}: of which flagged", len(flags[g][name]))):
                got = cell(row, headers, header)
                if num(got) != want:
                    failures.append(f"OOI {name} / {header}: workbook {got}, recomputed {want}")
        if name == "Surface Groove":
            for g in GROUPS:
                if num(cell(row, headers, f"{g}: pictures")) != 0:
                    failures.append(f"OOI Surface Groove / {g}: should be 0")
            continue
        vals = list(per_class_pic[name].values())
        want = [round(sum(vals) / len(vals), 2) if vals else 0,
                statistics.median(vals) if vals else 0, max(vals) if vals else 0]
        got = [cell(row, headers, "Tags per picture (24)"), cell(row, headers, "Median tags per picture (24)"),
               cell(row, headers, "Most tags on one picture (24)")]
        if got[0] is None or abs(float(got[0]) - want[0]) > 1e-9:
            failures.append(f"OOI {name} mean: workbook {got[0]}, recomputed {want[0]}")
        for i in (1, 2):
            if got[i] is None or float(got[i]) != float(want[i]):
                failures.append(f"OOI {name} {'median' if i == 1 else 'max'}: workbook {got[i]}, recomputed {want[i]}")

    hdr_row = None
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row and str(row[0]).strip() == "Tags on one picture":
            hdr_row = i
            break
    if hdr_row is None:
        failures.append("OOI: distribution header missing")
    else:
        buckets = {}
        for row in ws.iter_rows(min_row=hdr_row + 1, max_row=hdr_row + 6, values_only=True):
            buckets[str(row[0]).strip()] = row[1:4]
        def bucket_of(c):
            return ("1 tag" if c == 1 else "2 to 3 tags" if c <= 3 else "4 to 9 tags" if c <= 9
                    else "10 to 19 tags" if c <= 19 else "20 or more tags")
        for bucket in ("1 tag", "2 to 3 tags", "4 to 9 tags", "10 to 19 tags", "20 or more tags"):
            if bucket not in buckets:
                failures.append(f"OOI distribution: bucket missing {bucket}")
                continue
            for i, g in enumerate(GROUPS):
                want = sum(1 for c in per_pic[g].values() if bucket_of(c) == bucket)
                if num(buckets[bucket][i]) != want:
                    failures.append(f"OOI distribution {bucket} / {g}: workbook {buckets[bucket][i]}, "
                                    f"recomputed {want}")
        total = buckets.get("Pictures with at least one OOI tag")
        if total is None:
            failures.append("OOI distribution: total row missing")
        else:
            for i, g in enumerate(GROUPS):
                if num(total[i]) != len(per_pic[g]):
                    failures.append(f"OOI distribution total / {g}: workbook {total[i]}, recomputed {len(per_pic[g])}")

    for sheet, n in (("Changes, 7 revised files", 133), ("Changes, 17 new files", 71)):
        ws = wb[sheet]
        count = sum(1 for row in ws.iter_rows(min_row=5, values_only=True) if row[0])
        if count != n:
            failures.append(f"{sheet}: {count} rows, expected {n}")
    return failures


def check_record(wb_path):
    failures = []
    rec = recompute_record()
    wb = openpyxl.load_workbook(wb_path, data_only=True)

    ws = wb["Summary"]
    want = {"Pictures with at least one mark": rec["new"]["marked"],
            "Pictures with nothing marked (Clear)": rec["new"]["clear"],
            "Analysed set": rec["new"]["analysed"]}
    for label, w in want.items():
        row = num_row(ws, label)
        if row is None:
            failures.append(f"Summary: row missing for {label}")
        elif num(row[1]) != w:
            failures.append(f"Summary {label}: workbook {row[1]}, recomputed {w}")

    ws = wb["Before and after"]
    headers, rows = table(ws)
    for name in LP_GUIDE + OOI_GUIDE + LEGACY:
        row = find(rows, headers, name)
        if row is None:
            failures.append(f"Before/after: row missing for {name}")
            continue
        old = rec["old"]["table"].get(name, {"pics": set(), "tags": 0})
        new = rec["new"]["table"].get(name, {"pics": set(), "tags": 0})
        for header, w in zip(("Pictures before", "Pictures after", "Change"),
                             (len(old["pics"]), len(new["pics"]), len(new["pics"]) - len(old["pics"]))):
            got = cell(row, headers, header)
            if num(got) != w:
                failures.append(f"Before/after {name} / {header}: workbook {got}, recomputed {w}")
        for header, w in (("of which flagged before", len(rec["old"]["flags"].get(name, set()))),
                          ("of which flagged after", len(rec["new"]["flags"].get(name, set())))):
            got = cell(row, headers, header)
            if num(got) != w:
                failures.append(f"Before/after {name} / {header}: workbook {got}, recomputed {w}")
        if name in OOI_GUIDE:
            for header, w in (("OOI tags before", old["tags"]), ("OOI tags after", new["tags"])):
                got = cell(row, headers, header)
                if num(got) != w:
                    failures.append(f"Before/after {name} / {header}: workbook {got}, recomputed {w}")
    row = find(rows, headers, "Clear")
    if row is None:
        failures.append("Before/after: Clear row missing")
    else:
        for header, w in (("Pictures before", rec["old"]["clear"]), ("Pictures after", rec["new"]["clear"]),
                          ("Change", rec["new"]["clear"] - rec["old"]["clear"])):
            if num(cell(row, headers, header)) != w:
                failures.append(f"Before/after Clear / {header}: workbook {cell(row, headers, header)}, recomputed {w}")

    ws = wb["Lens Presentation"]
    headers, rows = table(ws)
    if len([r for r in rows if r and r[headers.get('Class', 1)] in LP_GUIDE]) != 15:
        failures.append("Record Lens Presentation: expected 15 rows")
    for name in ("Edge Bottle-Capped", "Torn Lens", "Lens Rupture"):
        row = find(rows, headers, name)
        if row is None or num(cell(row, headers, "Before")) != 0 or num(cell(row, headers, "After")) != 0:
            failures.append(f"Record Lens Presentation: {name} should be 0/0")

    ws = wb["OOI tags"]
    headers, rows = table(ws)
    if len([r for r in rows if r and r[headers.get('Class', 1)] in OOI_GUIDE + LEGACY]) != 11:
        failures.append("Record OOI: expected 8 guide + 3 legacy rows")
    for name in LEGACY:
        row = find(rows, headers, name)
        if row is None:
            failures.append(f"Record OOI: legacy row missing for {name}")
        elif str(cell(row, headers, "In guide")).strip() != "Legacy":
            failures.append(f"Record OOI: {name} not marked legacy")
    return failures


def main():
    f1 = check_batch(WB1)
    f2 = check_record(WB2)
    print("workbook 1:", "OK" if not f1 else f"{len(f1)} failures")
    for f in f1[:25]:
        print("   ", f)
    print("workbook 2:", "OK" if not f2 else f"{len(f2)} failures")
    for f in f2[:25]:
        print("   ", f)

    tmp = tempfile.mkdtemp()
    p1 = os.path.join(tmp, "wb1.xlsx")
    shutil.copy(WB1, p1)
    wb = openpyxl.load_workbook(p1)
    ws = wb["OOI tags, 7 vs 17 vs 24"]
    headers, _ = table(ws)
    target = None
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row and str(row[1]).strip() == "Bubble":
            target = (i, headers["24 total: pictures"] + 1)
            break
    ws.cell(row=target[0], column=target[1]).value += 1
    wb.save(p1)
    t1 = check_batch(p1)

    p2 = os.path.join(tmp, "wb2.xlsx")
    shutil.copy(WB2, p2)
    wb = openpyxl.load_workbook(p2)
    ws = wb["Before and after"]
    headers, _ = table(ws)
    target = None
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row and str(row[1]).strip() == "Bubble":
            target = (i, headers["Pictures after"] + 1)
            break
    ws.cell(row=target[0], column=target[1]).value += 1
    wb.save(p2)
    t2 = check_record(p2)
    print("tamper workbook 1:", "CAUGHT" if t1 else "MISSED")
    print("tamper workbook 2:", "CAUGHT" if t2 else "MISSED")
    ok = not f1 and not f2 and t1 and t2
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
