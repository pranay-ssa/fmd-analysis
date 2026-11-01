"""Total EDA statistics after the 24-file export.

Rules (as stated by the user):
  * EDA: a picture that shows a class belongs to that class. The micron-gate tag is a subset
    of the class and is reported as "of which size-flagged", never as its own class.
  * Split: the four gated classes are positive on the size flag only (frozen rule); legacy
    classes are not split labels.

Writes the frozen CSVs the total-EDA workbook formats:
  population.csv, lp.csv, ooi.csv, combos_exact.csv, combos_inclusive.csv, label_counts.csv,
  outside_split.csv, splits.csv, reconciliation.csv
"""
import csv
import json
import os
import statistics
from collections import Counter, defaultdict

ROOT = "D:/fmd-analysis"
RUN = f"{ROOT}/run/eda_full_24files_20261028"
REC = f"{ROOT}/run/eda_batch24_20261028/record_before_after.csv"
OUT = f"{ROOT}/run/eda_total_20261028"
os.makedirs(OUT, exist_ok=True)

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
OOI = [("P2_BB", "Bubble"), ("P2_BC", "Bubble Cluster"), ("P2_WP", "Wet Package"),
       ("P1_SG", "Surface Groove"), ("P3_FIB", "Fiber"), ("P3_EP", "Extraneous Polymer"),
       ("P3_HE", "HEMA"), ("P3_FM", "Foreign Matter")]
LEGACY = [("P2_HMO", "HEMA Obstruction"), ("", "Bubble On 123"), ("", "Bubble On Edge")]
GATES = {"foreign_matter_micron_gate": ("P3_FM_MICRON_THRESHOLD", "Foreign Matter"),
         "fiber_micron_gate": ("P3_FIB_MICRON_THRESHOLD", "Fiber"),
         "extraneous_polymer_micron_gate": ("P3_EP_MICRON_THRESHOLD", "Extraneous Polymer"),
         "hema_micron_gate": ("P3_HE_MICRON_THRESHOLD", "HEMA")}
OOI_CANON = {"bubble": "Bubble", "bubble_irregular": "Bubble", "stretched_bubble": "Bubble",
             "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
             "foreign_matter": "Foreign Matter", "fiber": "Fiber",
             "extraneous_polymer": "Extraneous Polymer", "hema_obstruction": "HEMA",
             "hema_fragment": "HEMA"}
LP_CANON = {cid: name for _, name, cid, _ in LP if cid}
# EDA label space: every guide class, gates excluded.
CLASS_CODES = {"P2_BB", "Bubble", "P2_BI", "Bubble Irregular", "P2_BST", "Stretched Bubble",
               "P2_BC", "Bubble Cluster", "P2_WP", "Wet Package",
               "P3_FM", "Foreign Matter", "P3_FIB", "Fiber", "P3_EP", "Extraneous Polymer",
               "P3_HE", "HEMA Fragment",
               "P1_MPP", "P1_PPM", "P1_COC", "P2_FOV", "F2_FOV", "P1_NL", "P1_ML", "P1_FL",
               "P2_LOC", "P2_LD", "P2_DS", "P2_DC", "P2_BSC"}
PLAIN = {"P3_FM": "Foreign Matter", "Foreign Matter": "Foreign Matter",
         "P3_FIB": "Fiber", "Fiber": "Fiber", "P3_EP": "Extraneous Polymer",
         "Extraneous Polymer": "Extraneous Polymer", "P3_HE": "HEMA", "HEMA Fragment": "HEMA"}
LEGACY_CODES = {"P2_HMO", "Bubble On 123", "Bubble On Edge"}


def rows(path):
    return list(csv.DictReader(open(path, newline="", encoding="utf-8")))


def main():
    codes_all = defaultdict(set)
    pics = defaultdict(lambda: {"box": set(), "tag": set(), "legacy": set(), "gate": set(), "geo": defaultdict(list)})
    for r in rows(f"{RUN}/resolved_labels.csv"):
        cid = r["canonical_id"]
        codes_all[r["picture_md5"]].add(r["code"])
        p = pics[r["picture_md5"]]
        if r["shape_kind"] == "box" and cid in ("bubble_on_123", "bubble_on_edge"):
            p["legacy"].add("Bubble On 123" if cid == "bubble_on_123" else "Bubble On Edge")
        elif r["shape_kind"] == "box":
            name = OOI_CANON.get(cid)
            if name:
                p["box"].add(name)
                p["geo"][name].append((float(r["xbr"]) - float(r["xtl"]), float(r["ybr"]) - float(r["ytl"])))
        elif r["shape_kind"] == "tag":
            if cid in LP_CANON:
                p["tag"].add(LP_CANON[cid])
            elif cid == "hema_obstruction":
                p["tag"].add("HEMA Obstruction")
        if cid.endswith("_micron_gate"):
            p["gate"].add(GATES[cid][1])

    clear_md5 = {x["md5"] for x in rows(f"{RUN}/picture_table.csv")
                 if x["winning_path"].split("/")[1:2] == ["Clear"] and x["md5"] not in pics}
    marked = len(pics)
    analysed = marked + len(clear_md5)

    rec = {r["name"]: r for r in rows(REC)}
    problems = []
    for code, name in OOI:
        want = int(rec[name]["merged_pictures"]) if name in rec else 0
        got = sum(1 for p in pics.values() if name in p["box"])
        if got != want:
            problems.append(f"OOI {name}: {got} vs record {want}")
    for code, name, cid, _ in LP:
        want = int(rec[name]["merged_pictures"]) if name in rec else 0
        got = sum(1 for p in pics.values() if name in p["tag"])
        if got != want:
            problems.append(f"LP {name}: {got} vs record {want}")

    any_box = sum(1 for p in pics.values() if p["box"])
    any_lp = sum(1 for p in pics.values() if p["tag"] - {"HEMA Obstruction"})
    pop = [("Pictures examined", 10614), ("Pictures with at least one mark", marked),
           ("Pictures with at least one OOI tag", any_box),
           ("Pictures with at least one lens presentation tag", any_lp),
           ("Pictures with nothing marked (Clear)", len(clear_md5)), ("Analysed set", analysed)]
    with open(f"{OUT}/population.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["measure", "value"]); w.writerows(pop)

    # ---------- pictures outside the split (the split uses the gate as positive) ----------
    split_label_codes = ({v[0] for v in GATES.values()} | {"P2_BB", "Bubble", "P2_BI", "Bubble Irregular",
                          "P2_BST", "Stretched Bubble", "P2_BC", "Bubble Cluster",
                          "P2_WP", "Wet Package", "P1_MPP", "P1_PPM", "P1_COC", "P2_FOV", "F2_FOV",
                          "P1_NL", "P1_ML", "P1_FL", "P2_LOC", "P2_LD", "P2_DS", "P2_DC", "P2_BSC"})
    legacy_detail = {"P2_HMO": "HEMA Obstruction (P2_HMO)", "Bubble On 123": "Bubble On 123",
                     "Bubble On Edge": "Bubble On Edge"}
    outside = []
    for m, cs in codes_all.items():
        if cs & split_label_codes:
            continue
        fams = sorted({PLAIN[c] for c in cs if c in PLAIN})
        if fams:
            outside.append(["Object only, no size flag", " + ".join(fams), m])
        else:
            outside.append(["Legacy class only", " + ".join(sorted({legacy_detail.get(c, c) for c in cs & LEGACY_CODES})), m])
    agg = Counter((r, d) for r, d, _ in outside)
    with open(f"{OUT}/outside_split.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["reason", "detail", "pictures"])
        for (reason, detail), n in sorted(agg.items(), key=lambda x: (x[0][0], -x[1])):
            w.writerow([reason, detail, n])
        w.writerow(["Total", "Pictures outside the split", sum(agg.values())])

    before = json.load(open(f"{ROOT}/run/split_20261028_v6/meta.json", encoding="utf-8"))
    after = json.load(open(f"{ROOT}/run/split_20261028_v7/meta.json", encoding="utf-8"))

    # ---------- LP ----------
    lp_rows = []
    for code, name, cid, key in LP:
        n = sum(1 for p in pics.values() if name in p["tag"])
        in70 = (after["splits"]["70_30"]["per_class"][key]["train"] + after["splits"]["70_30"]["per_class"][key]["test"]) if key else 0
        in80 = (after["splits"]["80_20"]["per_class"][key]["train"] + after["splits"]["80_20"]["per_class"][key]["test"]) if key else 0
        lp_rows.append([code, name, n, round(n / analysed, 6), in70, in80])
    with open(f"{OUT}/lp.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "class", "pictures", "share", "in_70", "in_80"])
        w.writerows(lp_rows)

    # ---------- OOI (all class pictures; gate is the subset) ----------
    ooi_rows = []
    for code, name in OOI:
        pset = [m for m, p in pics.items() if name in p["box"]]
        gate = sum(1 for m in pset if name in pics[m]["gate"])
        tags = sum(len(p["geo"][name]) for p in pics.values())
        geos = [g for p in pics.values() for g in p["geo"][name]]
        mw = round(statistics.median(g[0] for g in geos), 1) if geos else 0
        mh = round(statistics.median(g[1] for g in geos), 1) if geos else 0
        ooi_rows.append([code, name, "Yes", len(pset), gate, tags, mw, mh])
    for code, name in LEGACY:
        if name == "HEMA Obstruction":
            pset = [m for m, p in pics.items() if "HEMA Obstruction" in p["tag"]]
            ooi_rows.append([code, name, "Legacy", len(pset), 0, len(pset), 0, 0])
        else:
            cid = "bubble_on_123" if name == "Bubble On 123" else "bubble_on_edge"
            pset = {r["picture_md5"] for r in rows(f"{RUN}/resolved_labels.csv") if r["canonical_id"] == cid}
            tags = sum(1 for r in rows(f"{RUN}/resolved_labels.csv") if r["canonical_id"] == cid)
            ooi_rows.append([code, name, "Legacy", len(pset), 0, tags, 0, 0])
    with open(f"{OUT}/ooi.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "class", "guide", "pictures", "gate", "tags", "median_w", "median_h"])
        w.writerows(ooi_rows)

    # ---------- pairs and label counts over classes (EDA reading) ----------
    sets = {}
    for m, p in pics.items():
        s = set(p["tag"]) | p["box"] | p["legacy"]
        if s:
            sets[m] = s
    pair_all, pair_exact = Counter(), Counter()
    for s in sets.values():
        items = sorted(s)
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                pair_all[(items[i], items[j])] += 1
                if len(items) == 2:
                    pair_exact[(items[i], items[j])] += 1
    for name, counter in (("combos_exact", pair_exact), ("combos_inclusive", pair_all)):
        with open(f"{OUT}/{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["pair", "pictures"])
            for (a, b), n in sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:30]:
                w.writerow([f"{a} + {b}", n])
    dist = Counter()
    for m in pics:
        dist[len(sets.get(m, set()))] += 1
    for m in clear_md5:
        dist[1] += 1
    with open(f"{OUT}/label_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["labels", "pictures"])
        for n in sorted(dist):
            w.writerow([n, dist[n]])

    # ---------- splits before / after (gate positives, unchanged) ----------
    split_map = [("foreign_matter_micron_gate", "P3_FM_MICRON_THRESHOLD", "Foreign Matter gate"),
                 ("fiber_micron_gate", "P3_FIB_MICRON_THRESHOLD", "Fiber gate"),
                 ("extraneous_polymer_micron_gate", "P3_EP_MICRON_THRESHOLD", "Extraneous Polymer gate"),
                 ("hema_micron_gate", "P3_HE_MICRON_THRESHOLD", "HEMA gate"),
                 ("bubble", "P2_BB", "Bubble"),
                 ("bubble_cluster", "P2_BC", "Bubble Cluster"),
                 ("wet_package", "P2_WP", "Wet Package"),
                 ("missing_primary_package", "P1_MPP", "Missing Primary Package"),
                 ("package_misalignment", "P1_PPM", "Package Misalignment"),
                 ("cavity_off_center", "P1_COC", "Cavity Off Center"),
                 ("view_obstructed", "P2_FOV", "View Obstructed"),
                 ("lens_off_center", "P2_LOC", "Lens Off Center"),
                 ("no_lens", "P1_NL", "No Lens"),
                 ("multiple_lenses", "P1_ML", "Multiple Lens"),
                 ("folded_lens", "P1_FL", "Folded Lens"),
                 ("dirty_strobe", "P2_DS", "Dirty Strobe"),
                 ("dirty_camera", "P2_DC", "Dirty Camera"),
                 ("bubble_scatter", "P2_BSC", "Bubble Scatter"),
                 ("low_dose", "P2_LD", "Low Dose"),
                 ("clear", "", "Clear")]
    split_rows = []
    for ratio in ("70_30", "80_20"):
        for key, code, name in split_map:
            b = before["splits"][ratio]["per_class"].get(key, {"train": 0, "test": 0})
            a = after["splits"][ratio]["per_class"].get(key, {"train": 0, "test": 0})
            split_rows.append([ratio, code, name, b["train"], b["test"], a["train"], a["test"]])
    with open(f"{OUT}/splits.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ratio", "code", "class", "before_train", "before_test", "after_train", "after_test"])
        w.writerows(split_rows)

    with open(f"{OUT}/reconciliation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["figure", "total_eda", "record_workbook", "source", "note"])
        w.writerows([
            ["Pictures with marks", marked, marked, "resolved labels", ""],
            ["Clear", len(clear_md5), len(clear_md5), "picture table minus marks", ""],
            ["Analysed set", analysed, analysed, "marks + Clear", ""],
            ["Split rows before (v6)", before["rows"], before["rows"], "split v6", ""],
            ["Split rows after (v7)", after["rows"], after["rows"], "split v7", ""],
        ])

    print(f"marked {marked}, clear {len(clear_md5)}, analysed {analysed}, outside split {sum(agg.values())}")
    print(f"split rows before {before['rows']}, after {after['rows']}")
    print("class checks:", "PASS" if not problems else f"{len(problems)} FAILED")
    for p in problems:
        print("  ", p)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
