#!/usr/bin/env python3
"""Label-space tables for the frozen set, on unique images.

Base: the 92 frozen annotation files, de-duplicated to one record per image content.
The four content-duplicate pairs keep the more complete annotation, tie-break base name.
The five unmarked pictures outside the Clear folder are unannotated and are excluded from
label statistics; Clear is a label, so there is no zero-label row.

Writes JSON and CSVs under run/frozen_eda_20261118/.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STORE = REPO / "run/frozen_eda_20261117/store"
OUT = REPO / "run/frozen_eda_20261118"
OUT.mkdir(parents=True, exist_ok=True)

# Records dropped from each duplicate pair: keep the more complete annotation,
# tie-break the base name (pair 1 is a 7/7 tie, base name kept).
DROP = {
    "20241102_004906_L24_C5_9471_0.6629.bmp",
    "20241109_174228_L24_C4_9649_0.9824.bmp",
    "20241110_024940_L24_C13_9997.bmp",
    "20260816_093047_L26_PalletGHF0816135159_Cavity12_B01BJQ6_Fail7_Score(0.989757).bmp",
}

LP = {
    "P1_COC": "Cavity Off Center",
    "P1_EBC": "Edge Bottle-Capped",
    "P1_FL": "Folded Lens",
    "P1_LR": "Lens Rupture",
    "P1_ML": "Multiple Lens",
    "P1_MPP": "Missing Primary Package",
    "P1_NL": "No Lens",
    "P1_PPM": "Primary Package Misalignment",
    "P1_TL": "Torn Lens",
    "P2_BSC": "Bubble Scatter",
    "P2_DC": "Dirty Camera",
    "P2_DS": "Dirty Strobe",
    "P2_LD": "Low Dose",
    "P2_LOC": "Lens Off Center",
    "F2_FOV": "Field of View Obstructed",
}
OOI = {
    "P2_BB": "Bubble",
    "P2_BC": "Bubble Cluster",
    "P2_WP": "Wet Package",
    "P1_SG": "Surface Groove",
    "P3_FM": "Foreign Matter",
    "P3_FIB": "Fiber",
    "P3_EP": "Extraneous Polymer",
    "P3_HE": "HEMA",
}
DEBRIS = ["P3_FM", "P3_FIB", "P3_EP", "P3_HE"]

def main() -> None:
    manifest = list(csv.DictReader(open(STORE / "manifest.csv", encoding="utf-8-sig")))
    keep = [r for r in manifest if r["basename"] not in DROP]
    keys = {r["basename"] for r in keep}
    tags = [t for t in csv.DictReader(open(STORE / "labels/tags.csv", encoding="utf-8-sig"))
            if t["basename"] in keys]
    boxes = [b for b in csv.DictReader(open(STORE / "labels/boxes.csv", encoding="utf-8-sig"))
             if b["basename"] in keys]

    pic = defaultdict(lambda: {"lp": set(), "gate": set(), "box": set()})
    lp_inst = Counter()
    gate_inst = Counter()
    box_count = Counter()
    for t in tags:
        if t["kind"] == "gate":
            pic[t["basename"]]["gate"].add(t["code"])
            gate_inst[t["code"]] += int(t["instances"])
        else:
            pic[t["basename"]]["lp"].add(t["code"])
            lp_inst[t["code"]] += int(t["instances"])
    for b in boxes:
        pic[b["basename"]]["box"].add(b["code"])
        box_count[b["code"]] += 1

    marked = {n for n, v in pic.items() if v["lp"] or v["box"]}
    def truth(v):
        return str(v).lower() in ("1", "true", "yes")
    clear_source = {r["basename"] for r in keep if truth(r.get("is_clear_source"))}
    clear = {n for n in clear_source if n not in marked}
    unannotated = keys - marked - clear
    labelled = marked | clear  # Clear is a label
    classes = {n: pic[n]["lp"] | pic[n]["box"] for n in labelled}
    dist = Counter(len(classes[n]) for n in labelled)
    # Clear contributes one label (Clear), no classes.
    label_totals = {"Clear": len(clear)}
    for k in range(1, 10):
        label_totals[str(k)] = dist.get(k, 0)

    lp_pics = {n for n in labelled if pic[n]["lp"]}
    ooi_pics = {n for n in labelled if pic[n]["box"]}
    both = lp_pics & ooi_pics
    single_lp = {n for n in labelled if len(classes[n]) == 1 and pic[n]["lp"]}
    single_ooi = {n for n in labelled if len(classes[n]) == 1 and pic[n]["box"]}
    single_counts = Counter()
    for n in labelled:
        if len(classes[n]) == 1:
            single_counts[next(iter(classes[n]))] += 1
    single_rows = [{"code": k, "class": LP.get(k, OOI.get(k, k)), "pictures": v}
                   for k, v in single_counts.most_common()]

    lp_rows = []
    for code, name in LP.items():
        pics = sum(1 for n in labelled if code in pic[n]["lp"])
        lp_rows.append({"code": code, "class": name, "pictures": pics,
                        "tags": lp_inst.get(code, 0),
                        "share_of_labelled": pics / len(labelled)})

    ooi_rows = []
    for code, name in OOI.items():
        pics = sum(1 for n in labelled if code in pic[n]["box"])
        gate = gate_inst.get(code + "_MICRON_THRESHOLD", 0)
        ooi_rows.append({"code": code, "class": name, "pictures": pics,
                         "boxes": box_count.get(code, 0), "size_flagged": gate,
                         "share_of_labelled": pics / len(labelled)})

    def composition(k: int):
        comp = Counter()
        tops = Counter()
        for n in labelled:
            c = classes[n]
            if len(c) != k:
                continue
            a = len(pic[n]["lp"] & c)
            b = len(pic[n]["box"] & c)
            comp[f"{a} LP + {b} OOI"] += 1
            tops[tuple(sorted(c))] += 1
        return (
            [{"composition": x, "pictures": y} for x, y in
             sorted(comp.items(), key=lambda kv: -kv[1])],
            [{"labels": list(t), "pictures": y} for t, y in tops.most_common(15)],
        )

    comp1, top1 = composition(1)
    comp2, top2 = composition(2)
    comp3, top3 = composition(3)
    comp4, top4 = composition(4)

    # Inclusive pairs: the picture carries both labels, any further labels allowed.
    pair_counts = Counter()
    for n in labelled:
        cs = sorted(classes[n])
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                pair_counts[(cs[i], cs[j])] += 1
    top_inclusive = [{"labels": list(t), "pictures": y} for t, y in pair_counts.most_common(15)]

    def pass_report():
        out = {}
        allowed_strict = {"P2_BB", *DEBRIS}
        allowed_ext = allowed_strict | {"P2_BC", "P2_WP"}
        for code in DEBRIS + ["UNION"]:
            if code == "UNION":
                unt = [n for n in labelled
                       if any(c in pic[n]["box"] for c in DEBRIS)
                       and not any((c + "_MICRON_THRESHOLD") in pic[n]["gate"] for c in DEBRIS)]
                pics = len({n for n in labelled if any(c in pic[n]["box"] for c in DEBRIS)})
                flagged = len({n for n in labelled
                               if any((c + "_MICRON_THRESHOLD") in pic[n]["gate"] for c in DEBRIS)})
            else:
                unt = [n for n in labelled
                       if code in pic[n]["box"] and (code + "_MICRON_THRESHOLD") not in pic[n]["gate"]]
                pics = sum(1 for n in labelled if code in pic[n]["box"])
                flagged = sum(1 for n in labelled if (code + "_MICRON_THRESHOLD") in pic[n]["gate"])
            def ok(n, allowed):
                return not pic[n]["lp"] and not pic[n]["gate"] and pic[n]["box"] <= allowed
            strict = sum(1 for n in unt if ok(n, allowed_strict))
            ext = sum(1 for n in unt if ok(n, allowed_ext))
            reasons = Counter()
            for n in unt:
                if pic[n]["lp"]:
                    reasons["LP tag present"] += 1
                if pic[n]["gate"]:
                    reasons["Another size flag present"] += 1
                if "P2_BC" in pic[n]["box"]:
                    reasons["Bubble Cluster"] += 1
                if "P2_WP" in pic[n]["box"]:
                    reasons["Wet Package"] += 1
                if "P1_SG" in pic[n]["box"]:
                    reasons["Surface Groove"] += 1
            out[code] = {"pictures": pics, "flagged": flagged, "untagged": len(unt),
                         "pass_strict": strict, "pass_extended": ext,
                         "reasons": dict(reasons)}
        return out

    pass_rows = pass_report()

    summary = {
        "annotation_records": len(manifest),
        "unique_images": len(keep),
        "duplicate_records_removed": len(manifest) - len(keep),
        "labelled_population": len(labelled),
        "clear": len(clear),
        "unannotated": len(unannotated),
        "marked": len(marked),
        "lp_pictures": len(lp_pics),
        "ooi_pictures": len(ooi_pics),
        "lp_and_ooi": len(both),
        "single_lp": len(single_lp),
        "single_ooi": len(single_ooi),
        "single_total": len(single_lp) + len(single_ooi),
        "multi_total": len(marked) - len(single_lp) - len(single_ooi),
        "labels": label_totals,
    }

    data = {"summary": summary, "lp": lp_rows, "ooi": ooi_rows, "single_labels": single_rows,
            "composition1": comp1, "top1": top1,
            "composition2": comp2, "top2": top2, "top_inclusive": top_inclusive,
            "composition3": comp3, "top3": top3,
            "composition4": comp4, "top4": top4,
            "size_untagged": pass_rows}
    (OUT / "label_space.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def write_csv(name, rows, fields):
        with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    write_csv("lp_labels.csv", lp_rows, ["code", "class", "pictures", "tags", "share_of_labelled"])
    write_csv("ooi_labels.csv", ooi_rows, ["code", "class", "pictures", "boxes", "size_flagged", "share_of_labelled"])
    write_csv("composition3.csv", comp3, ["composition", "pictures"])
    write_csv("composition4.csv", comp4, ["composition", "pictures"])
    print(json.dumps(summary, indent=2))
    print(json.dumps(pass_rows, indent=2))

if __name__ == "__main__":
    main()
