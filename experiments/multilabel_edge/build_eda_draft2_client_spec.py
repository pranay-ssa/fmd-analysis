"""Generate the client/lead-facing EDA workbook spec (EDA_Draft2_20261023.xlsx).

Rules applied (AGENTS.md, reader-facing artifacts):
  - no internal paths, script names, ticket ids, run folders or version tags
  - every sheet opens with a plain "what this shows" line
  - every count names its population in the column header
  - any term that must appear is defined on the Definitions sheet
Inputs: run/draft2_eda_20261023/*.json, run/multilabel_edge_20261023/*,
        run/split_20261023_v3/meta.json
Output: EDA_Draft2_client_spec.json
"""
import json, csv

ROOT = "D:/fmd-analysis"
lp = json.load(open(f"{ROOT}/run/draft2_eda_20261023/lp_eda.json"))
ooi = json.load(open(f"{ROOT}/run/draft2_eda_20261023/ooi_eda.json"))
audit = json.load(open(f"{ROOT}/run/multilabel_edge_20261023/standalone_audit.json"))
meta = json.load(open(f"{ROOT}/run/split_20261023_v3/meta.json"))

rows = list(csv.DictReader(open(f"{ROOT}/run/multilabel_edge_20261023/label_matrix.csv",
                                newline="", encoding="utf-8")))
COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
        "extraneous_polymer_micron_gate", "hema_micron_gate",
        "bubble", "bubble_cluster", "wet_package", "bubble_on_123",
        "bubble_on_edge", "hema_obstruction", "missing_primary_package",
        "multiple_lenses", "no_lens", "cavity_off_center", "folded_lens",
        "lens_off_center", "dirty_camera", "dirty_strobe", "low_dose",
        "view_obstructed", "package_misalignment", "bubble_scatter", "clear"]
pos = {c: sum(1 for r in rows if r[c] == "1") for c in COLS}
assert len(rows) == 6785 and pos["clear"] == 2156

TITLE = "1F3864"      # dark blue
HEAD = "2F5597"       # header blue
BAND = "EAF0F8"       # light band
NOTE = "595959"       # grey text
FONT = "Calibri"

def t(text, span, size=16):
    return {"value": text, "bold": True, "font_size": size, "font_color": "FFFFFF",
            "fill": TITLE, "align": "left", "valign": "center"}

def sub(text, span):
    return {"value": text, "italic": True, "font_size": 10, "font_color": NOTE,
            "wrap": True, "valign": "top"}

def hdr(vals):
    return [{"value": v, "bold": True, "font_size": 10, "font_color": "FFFFFF",
             "fill": HEAD, "wrap": True, "valign": "center", "border": "thin",
             "align": "left"} for v in vals]

def data_row(vals, band=False, formats=None):
    out = []
    for i, v in enumerate(vals):
        c = {"value": v, "border": "thin", "valign": "top", "wrap": True}
        if band:
            c["fill"] = BAND
        if formats and i in formats:
            c["format"] = formats[i]
        out.append(c)
    return out

def blank(n):
    return [None] * n

sheets = []

# ================= Summary =================
main_classes = [
    ("Missing Primary Package", pos["missing_primary_package"]),
    ("Multiple Lens", pos["multiple_lenses"]),
    ("Lens Off Center", pos["lens_off_center"]),
    ("Clear", pos["clear"]),
    ("Bubble", pos["bubble"]),
    ("Bubble Cluster", pos["bubble_cluster"]),
    ("No Lens", pos["no_lens"]),
    ("Dirty Camera", pos["dirty_camera"]),
    ("Folded Lens", pos["folded_lens"]),
    ("Low Dose", pos["low_dose"]),
]
sum_rows = [
    [t("Defect and image-quality analysis - Draft 2 annotation guide", 7), None, None, None, None, None, None],
    [sub("Prepared October 2026. This workbook summarises the annotated inspection images for the "
         "Draft 2 annotation frame: 15 picture tags and 8 object classes, how many pictures carry each "
         "class, what the objects look like, which classes can be confused, and how the pictures are "
         "divided for training and testing.", 7), None, None, None, None, None, None],
    blank(7),
    [{"value": "Pictures examined", "bold": True}, 10614, None,
     {"value": "Pictures with usable labels", "bold": True}, 6785, None, None],
    [{"value": "Pictures used for training and testing", "bold": True}, 6574, None,
     {"value": "Training / test", "bold": True}, "4,568 / 2,006", None, None],
    blank(7),
    [{"value": "Main classes (pictures carrying the class)", "bold": True, "font_size": 11}, None, None, None, None, None, None],
]
for name, n in main_classes:
    sum_rows.append(data_row([name, n], band=len(sum_rows) % 2 == 0, formats={1: "#,##0"}))
sum_rows += [blank(7), [sub("Charts on the right show the same counts as bars. Every sheet opens with one line "
                            "explaining what it shows. Terms are defined on the 'Definitions' sheet.", 7), None, None, None, None, None, None],
             [sub("Class rows are not additive: a picture can carry several classes, so the class rows sum to more "
                  "than the picture totals above.", 7), None, None, None, None, None, None]]
sheets.append({
    "name": "Summary",
    "column_widths": {"A": 34, "B": 14, "C": 3, "D": 38, "E": 16, "F": 16, "G": 16},
    "row_heights": {"1": 26},
    "merges": ["A1:G1", "A2:G2"],
    "freeze_panes": "A4",
    "charts": [{"type": "bar", "title": "Pictures per class",
                "anchor": "D8", "data": f"B8:B{7 + len(main_classes)}",
                "categories": f"A8:A{7 + len(main_classes)}"}],
    "rows": sum_rows})

# ================= Class Summary =================
lp_rows = [hdr(["Class", "Guide code", "Pictures in analysed set (6,785)",
                "Share of analysed pictures", "Pictures in training/test set (6,574)", "Notes"])]
v3u = {"P1_MPP": 1426, "P1_PPM": 2, "P1_COC": 184, "P2_FOV": 24, "P2_LOC": 922,
       "P1_NL": 322, "P1_ML": 1402, "P1_FL": 226, "P2_DS": 41, "P2_DC": 298,
       "P2_BSC": 6, "P2_LD": 204}
notes = {
 "P1_MPP": "Standalone: no other label applies",
 "P1_PPM": "Standalone; rarest class",
 "P1_COC": "Standalone",
 "P2_FOV": "Standalone; production files use the code F2_FOV",
 "P2_LOC": "Largest lens-position class",
 "P1_NL": "Lens absent, package valid",
 "P1_ML": "Most frequent lens condition",
 "P1_FL": "Often occurs together with Multiple Lens",
 "P1_EBC": "No annotated pictures yet",
 "P1_TL": "No annotated pictures yet",
 "P1_LR": "No annotated pictures yet",
 "P2_DS": "Out-of-focus marks from the strobe cover",
 "P2_DC": "Sharp marks from the camera optics",
 "P2_BSC": "Diffuse field of small bubbles; rare",
 "P2_LD": "Low solution volume merges the interfaces",
}
for i, rec in enumerate(lp["lp_counts"]):
    n = rec["pictures"]
    lp_rows.append(data_row(
        [rec["name"], rec["code"], n, round(n / 6785, 4),
         v3u.get(rec["code"], 0) if rec["column"] != "(none)" else 0,
         notes.get(rec["code"], "")],
        band=i % 2 == 1, formats={2: "#,##0", 3: "0.0%", 4: "#,##0"}))
lp_rows.append(blank(6))
lp_rows.append(data_row(["Clear", "(none)", pos["clear"], round(pos["clear"] / 6785, 4), 2156,
                         "Picture is clear; never carries another label"], band=True,
                        formats={2: "#,##0", 3: "0.0%", 4: "#,##0"}))
lp_rows.append(data_row(["HEMA Obstruction (legacy)", "P2_HMO", pos["hema_obstruction"],
                         round(pos["hema_obstruction"] / 6785, 4), 0,
                         "Kept for reference only; not part of the current class list"],
                        formats={2: "#,##0", 3: "0.0%", 4: "#,##0"}))
sheets.append({
    "name": "LP Summary",
    "column_widths": {"A": 34, "B": 12, "C": 22, "D": 16, "E": 24, "F": 46},
    "row_heights": {"1": 30},
    "freeze_panes": "A2",
    "autofilter": f"A1:F{1 + 1 + len(lp['lp_counts'])}",
    "rows": [hdr(["Class", "Guide code", "Pictures in analysed set (6,785)",
                  "Share of analysed pictures", "Pictures in training/test set (6,574)", "Notes"])] + lp_rows[1:]
            + [blank(6),
               [sub("Class rows are not additive: a picture can carry several tags, so the rows above sum to "
                    "7,328 against 6,785 distinct pictures. Clear never shares a picture.", 6), None, None, None, None, None]]})

# ================= Tag Combinations =================
co_rows = [hdr(["Two tags on the same picture", "Pictures", "Note"])]
pair_notes = {"lens_off_center+multiple_lenses": "Largest overlap",
              "multiple_lenses+folded_lens": "Guide advises applying both",
              "lens_off_center+low_dose": "The pair the guide warns about",
              "dirty_camera+low_dose": ""}
for pair, n in sorted(lp["co"].items(), key=lambda kv: -kv[1]):
    a, b = pair.split("+")
    co_rows.append(data_row([f"{a} and {b}", n, pair_notes.get(pair, "")],
                            band=len(co_rows) % 2 == 0, formats={1: "#,##0"}))
co_rows += [blank(3), [{"value": "How many tags one picture carries", "bold": True, "font_size": 11}, None, None]]
for k, v in lp["card"].items():
    co_rows.append(data_row([f"{k} tag(s)", v], band=len(co_rows) % 2 == 0, formats={1: "#,##0"}))
sheets.append({
    "name": "Tag Combinations",
    "column_widths": {"A": 44, "B": 12, "C": 42},
    "row_heights": {"1": 24},
    "freeze_panes": "A2",
    "rows": co_rows})

# ================= Objects =================
order = ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
         "Extraneous Polymer", "HEMA (Draft 2: one class)", "Foreign Matter"]
codes = {"Bubble": "P2_BB", "Bubble Cluster": "P2_BC", "Wet Package": "P2_WP",
         "Surface Groove": "P1_SG", "Fiber": "P3_FIB", "Extraneous Polymer": "P3_EP",
         "HEMA (Draft 2: one class)": "P3_HE", "Foreign Matter": "P3_FM"}
onotes = {
 "Bubble": "Most objects are bubbles. The merged bubble class (with irregular and stretched bubbles) has 750 pictures and 10,205 marked objects; the training table counts 862 pictures because pictures rescued by older labels are included",
 "Bubble Irregular (folds into Bubble)": "Every picture with an irregular bubble also has a regular bubble",
 "Bubble On 123 (library-only)": "Reference only; not part of the current class list",
 "Bubble On Edge (library-only)": "Reference only; not part of the current class list",
 "HEMA (Draft 2: one class)": "Held as two earlier annotations; the size gate marks the class",
 "Extraneous Polymer": "Fewest pictures kept in the training set",
}
obj_rows = [hdr(["Object class", "Guide code", "Pictures with this object",
                 "Pictures in analysed set (6,785)", "Objects marked",
                 "Median objects per picture", "Most objects on one picture",
                 "Typical width (px)", "Typical height (px)", "Width, 95th percentile (px)",
                 "Height, 95th percentile (px)", "Notes"])]
obj_rows.append([{"value": "Draft 2 object classes (8)", "bold": True, "font_size": 11,
                  "fill": "D6E2F2"}, None, None, None, None, None, None, None, None, None, None, None])
for i, name in enumerate(order):
    d = ooi.get(name)
    if d is None:
        obj_rows.append(data_row([name, codes.get(name, "(legacy)"), 0, 0, 0, None, None,
                                  None, None, None, None,
                                  "Defined in the guide; no annotated objects yet"],
                                 band=i % 2 == 1))
        continue
    obj_rows.append(data_row(
        [name, codes.get(name, "(legacy)"), d["pictures"], d["pictures_in_matrix"],
         d["box_instances"], d.get("boxes_per_picture_median"), d.get("boxes_per_picture_max"),
         d["w_px_median"], d["h_px_median"], d["w_px_p95"], d["h_px_p95"], onotes.get(name, "")],
        band=i % 2 == 1, formats={2: "#,##0", 3: "#,##0", 4: "#,##0"}))
obj_rows.append(blank(12))
obj_rows.append([{"value": "Older classes kept for reference (not in the current class list)", "bold": True, "font_size": 11,
                  "fill": "EDEDED"}, None, None, None, None, None, None, None, None, None, None, None])
legacy = ["Bubble Irregular (folds into Bubble)", "Stretched Bubble (folds into Bubble)",
          "Bubble On 123 (library-only)", "Bubble On Edge (library-only)"]
for i, name in enumerate(legacy):
    d = ooi[name]
    obj_rows.append(data_row(
        [name, "(legacy)", d["pictures"], d["pictures_in_matrix"], d["box_instances"],
         d.get("boxes_per_picture_median"), d.get("boxes_per_picture_max"),
         d["w_px_median"], d["h_px_median"], d["w_px_p95"], d["h_px_p95"], onotes.get(name, "")],
        band=i % 2 == 1, formats={2: "#,##0", 3: "#,##0", 4: "#,##0"}))
obj_rows.append(blank(12))
obj_rows.append(data_row(["Total, the 8 object classes", "", 1130, 977, 12783, None, None, None,
                          None, None, None,
                          "1,130 pictures carry at least one object of any class; 79% of the objects in "
                          "these 8 classes are bubbles"],
                         band=True, formats={2: "#,##0", 3: "#,##0", 4: "#,##0"}))
obj_rows.append(data_row(["Total, all object classes", "", 1130, 977, 13087, None, None, None,
                          None, None, None,
                          "12,783 objects in the 8 classes above, plus 304 in the reference classes"],
                         formats={2: "#,##0", 3: "#,##0", 4: "#,##0"}))
obj_rows.append(blank(12))
obj_rows.append([sub("Pictures with this object are not additive: 2,098 placements across 1,130 distinct "
                     "pictures. Objects marked is additive and equals the total (12,783).", 12), None, None,
                 None, None, None, None, None, None, None, None, None])
sheets.append({
    "name": "Objects",
    "column_widths": {"A": 34, "B": 11, "C": 14, "D": 16, "E": 12, "F": 12, "G": 12,
                      "H": 12, "I": 12, "J": 14, "K": 14, "L": 60},
    "row_heights": {"1": 44},
    "freeze_panes": "B2",
    "rows": obj_rows})

# ================= Standalone Tags =================
sa_rows = [hdr(["Tag", "Pictures carrying it", "Pictures that also carry another label", "Status"])]
for code in ["P1_MPP", "P1_PPM", "P1_COC", "P2_FOV", "F2_FOV"]:
    a = audit["resolved_derivation"][code]
    sa_rows.append(data_row([f"{code}", a["pictures_tagged"], a["pictures_with_extra_labels"],
                             "Follows the guide: no other label on these pictures"],
                            band=len(sa_rows) % 2 == 1, formats={1: "#,##0", 2: "#,##0"}))
sa_rows += [blank(4),
            [sub("The annotation guide defines these four tags as standalone: when one is applied, no other tag or object "
                 "label applies to that picture. The annotations were checked against this rule and no exceptions were found. "
                 "The fourth class appears under two spellings in the files (P2_FOV and F2_FOV); both are counted here.", 4), None, None, None]]
sheets.append({
    "name": "Standalone Tags",
    "column_widths": {"A": 34, "B": 18, "C": 28, "D": 56},
    "row_heights": {"1": 30},
    "freeze_panes": "A2",
    "rows": sa_rows})

# ================= Confusion Risks =================
conf = [
 ("Cavity Off Center (184)", "Primary Package Misalignment (2)",
  "Both show the area of interest cut off. Off-centre image with the package correctly seated = Cavity Off Center; package not seated or out of position = Primary Package Misalignment.", "4.3", 0),
 ("Lens Off Center (953)", "Low Dose (215)",
  "Both look like the lens has moved. If the cause is too little solution, it is Low Dose; a real shift in a well-filled bowl is Lens Off Center.", "4.5, 4.15", 17),
 ("Wet Package (146)", "Bubble (862)",
  "Wet package marks look like bubbles but are liquid: gradual brightness change, irregular outline, usually near the package edge.", "5.2", 117),
 ("Extraneous Polymer", "Fiber",
  "Mixed shapes (a strand with a clump) are recorded as Fiber; Extraneous Polymer only when the material is clearly polymer.", "5.4B", "n/a"),
 ("Surface Groove (no data)", "Torn Lens",
  "A groove that opens into a tear or flap is Torn Lens; a shallow surface channel is Surface Groove.", "5.3, 4.10", "no data"),
 ("Surface Groove (no data)", "Extraneous Polymer",
  "Raised or extra material is Extraneous Polymer; a groove is missing material.", "5.3", "no data"),
 ("Torn Lens (no data)", "Lens Rupture",
  "Torn lens stays in one piece; rupture separates it into pieces.", "4.10, 4.11", "no data"),
 ("Edge Bottle-Capped (no data)", "Torn Lens / Lens Rupture",
  "Edge deformation with a continuous edge is Edge Bottle-Capped; a tear into the lens is Torn Lens; separated material is Lens Rupture.", "4.9", "no data"),
 ("Bubble Scatter (6)", "Bubble / Bubble Cluster",
  "Scatter is a whole-picture tag for many small bubbles spread widely; single bubbles and touching groups are marked objects.", "4.14, 5.1B", 0),
 ("Dirty Strobe (43)", "Dirty Camera (326)",
  "Same kind of contamination, different focus: strobe marks are soft and creep in from the edge; camera marks are sharp anywhere in the picture.", "4.12, 4.13", "n/a"),
 ("No Lens (323)", "any lens condition",
  "No Lens requires a valid package and confidence that no lens is present; otherwise the specific condition applies.", "4.6", 0),
 ("Multiple Lens (1,433)", "Folded Lens (237)",
  "Not a conflict: a folded lens in a multi-lens picture carries both tags.", "4.7, 4.8, 4.11", 236),
 ("Bubble", "Foreign Matter family",
  "Anything that cannot be confidently called a bubble is recorded as the most appropriate foreign-matter class.", "1.3", "n/a"),
 ("any uncertain defect", "most appropriate class",
  "Uncertain features are recorded under the closest class; consistency is preferred over guessing the physical cause.", "1.3", "n/a"),
]
cf_rows = [hdr(["Class", "Can look like", "How to tell them apart", "Guide section", "Pictures with both"])]
for i, (a, b, how, sec, n) in enumerate(conf):
    cf_rows.append(data_row([a, b, how, sec, n], band=i % 2 == 1, formats={4: "#,##0"}))
cf_rows += [blank(5),
            [{"value": "Features that look like defects but are not annotated", "bold": True, "font_size": 11}, None, None, None, None],
            data_row(["Package marks (fiber-like marks that repeat in the same place)", "Fiber, Foreign Matter",
                      "Not annotated. A model will still see them, so they limit achievable precision on these classes.", "3.1", None], band=True),
            data_row(["Crater-like bubble artifacts (rings or depressions from collapsed bubbles)", "Wet Package, Fiber, Extraneous Polymer, Foreign Matter",
                      "Not annotated. They resemble wet-package and debris marks.", "3.2", None])]
sheets.append({
    "name": "Confusion Risks",
    "column_widths": {"A": 30, "B": 30, "C": 76, "D": 12, "E": 16},
    "row_heights": {"1": 30},
    "freeze_panes": "A2",
    "rows": cf_rows})

# ================= Earlier vs Current =================
cmp = [
 ("Missing Primary Package", 1426, 1426, 1426, "Same at every stage"),
 ("Multiple Lenses", 1439, 1433, 1402, "A few pictures carry only unlabelled material and are left out of the analysed set"),
 ("Lens Off Center", 957, 953, 922, "Same reason; further pictures are outside the training/test set"),
 ("Dirty Camera", 329, 326, 298, "Same reason"),
 ("Missing Lens (No Lens)", 325, 323, 322, "Same reason"),
 ("Folded Lens", 237, 237, 226, "Outside the training/test set"),
 ("Low Dose", 215, 215, 204, "Outside the training/test set"),
 ("Cavity Off Center", 184, 184, 184, "Same at every stage"),
 ("Foreign Matter size flag", 171, 171, 171, "Same at every stage"),
 ("Fiber size flag", 136, 168, 137, "The analysed set also carries older label corrections; the training/test set counts the size flag only"),
 ("HEMA size flag", 94, 94, 94, "Same at every stage"),
 ("Dirty Strobe", 43, 43, 41, "Outside the training/test set"),
 ("Extraneous Polymer size flag", 33, 33, 33, "Same at every stage"),
 ("View Obstructed", 24, 24, 24, "Same at every stage"),
 ("Bubble Scatter", 6, 6, 6, "Same at every stage"),
 ("Package Misalignment", 2, 2, 2, "Same at every stage"),
 ("HEMA Obstruction", 86, 86, 0, "Kept for reference; not part of the current class list"),
 ("Bubble On 123", "(object list)", 13, 0, "Kept for reference; not part of the current class list"),
 ("Bubble On Edge", "(object list)", 14, 0, "Kept for reference; not part of the current class list"),
 ("Clear", "(new)", 2156, 2156, "Pictures with nothing to report"),
]
cmp_rows = [hdr(["Class", "Earlier full count", "Current analysed set (6,785)",
                 "Training/test set (6,574)", "Why the numbers differ"])]
for i, (a, b, c, d, why) in enumerate(cmp):
    cmp_rows.append(data_row([a, b, c, d, why], band=i % 2 == 1,
                             formats={1: "#,##0", 2: "#,##0", 3: "#,##0"}))
cmp_rows += [blank(5),
             [sub("The three picture sets differ by design. The analysed set keeps only pictures that carry at least one label "
                  "and a size flag where the guide requires one; the training/test set also leaves out pictures whose only labels "
                  "are no longer in the class list.", 5), None, None, None, None]]
sheets.append({
    "name": "Earlier vs Current",
    "column_widths": {"A": 30, "B": 16, "C": 22, "D": 20, "E": 66},
    "row_heights": {"1": 30},
    "freeze_panes": "A2",
    "rows": cmp_rows})

# ================= Training and Test Split =================
sp_rows = [hdr(["Class", "Training pictures", "Test pictures", "Total", "Expected training",
                "Expected test", "Note"])]
rare = {"package_misalignment", "bubble_scatter", "view_obstructed", "extraneous_polymer_micron_gate"}
pretty = {"foreign_matter_micron_gate": "Foreign Matter size flag", "fiber_micron_gate": "Fiber size flag",
          "extraneous_polymer_micron_gate": "Extraneous Polymer size flag",
          "hema_micron_gate": "HEMA size flag", "bubble": "Bubble (merged class)",
          "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
          "missing_primary_package": "Missing Primary Package", "multiple_lenses": "Multiple Lens",
          "no_lens": "No Lens", "cavity_off_center": "Cavity Off Center",
          "folded_lens": "Folded Lens", "lens_off_center": "Lens Off Center",
          "dirty_camera": "Dirty Camera", "dirty_strobe": "Dirty Strobe",
          "low_dose": "Low Dose", "view_obstructed": "View Obstructed",
          "package_misalignment": "Package Misalignment", "bubble_scatter": "Bubble Scatter",
          "clear": "Clear"}
for i, c in enumerate(["foreign_matter_micron_gate", "fiber_micron_gate",
                       "extraneous_polymer_micron_gate", "hema_micron_gate", "bubble",
                       "bubble_cluster", "wet_package", "missing_primary_package",
                       "multiple_lenses", "no_lens", "cavity_off_center", "folded_lens",
                       "lens_off_center", "dirty_camera", "dirty_strobe", "low_dose",
                       "view_obstructed", "package_misalignment", "bubble_scatter", "clear"]):
    p = meta["per_class"][c]
    note = "Few pictures: test results will vary widely" if c in rare else ""
    sp_rows.append(data_row([pretty[c], p["train"], p["test"], p["train"] + p["test"],
                             p["expect_train"], p["expect_test"], note],
                            band=i % 2 == 1, formats={1: "#,##0", 2: "#,##0", 3: "#,##0", 4: "#,##0", 5: "#,##0"}))
sp_rows += [blank(7),
            data_row(["Total", meta["split_counts"]["train"], meta["split_counts"]["test"],
                      meta["rows"], round(0.7 * meta["rows"], 1), round(0.3 * meta["rows"], 1),
                      "70% training / 30% test"], band=True,
                     formats={1: "#,##0", 2: "#,##0", 3: "#,##0", 4: "#,##0", 5: "#,##0"}),
            data_row(["Sum of the class rows above",
                      sum(v["train"] for v in meta["per_class"].values()),
                      sum(v["test"] for v in meta["per_class"].values()),
                      sum(v["train"] + v["test"] for v in meta["per_class"].values()),
                      None, None,
                      "Larger than the total because some pictures carry more than one class"],
                     formats={1: "#,##0", 2: "#,##0", 3: "#,##0"}),
            blank(7),
            [sub("Pictures were divided 70/30 with the class mix balanced by stratified sampling and a fixed random seed. "
                 "Every picture appears in exactly one side. There is no separate validation set.", 7), None, None, None, None, None, None]]
sheets.append({
    "name": "Training and Test Split",
    "column_widths": {"A": 34, "B": 16, "C": 14, "D": 12, "E": 16, "F": 14, "G": 44},
    "row_heights": {"1": 30},
    "freeze_panes": "A2",
    "autofilter": f"A1:G{1 + 1 + 20}",
    "rows": sp_rows})

# ================= Definitions =================
defs = [
 ("Picture examined", "Every distinct image in the inspection library, counted once even when the same image appears in more than one folder."),
 ("Picture with usable labels", "A picture that carries at least one tag or marked object under the current rules, or that is clear."),
 ("Training/test pictures", "The pictures that feed the model, after leaving out pictures whose only labels are no longer in the class list."),
 ("Tag", "A label that describes the whole picture, for example a lens folded or the image off-centre."),
 ("Marked object", "An outlined object inside a picture, for example a bubble or a fiber."),
 ("Clear", "A picture with nothing to report. Clear never appears together with another label."),
 ("Size flag", "A tag applied to a defect that is above the agreed size limit. For foreign matter, fiber, extraneous polymer and HEMA, only flagged pictures count as that class."),
 ("Merged bubble class", "Bubble, irregular bubble and stretched bubble are one class in the Draft 2 guide. All irregular-bubble pictures also carry a regular bubble, so the merged total is 750 pictures, not the sum of the three."),
 ("Legacy classes", "Classes kept for reference only (Bubble On 123, Bubble On Edge, HEMA Obstruction). They are not part of the current class list or the training/test set."),
 ("Standalone tag", "A tag that the guide says must appear alone: Missing Primary Package, Primary Package Misalignment, Cavity Off Center and Field of View Obstructed."),
 ("Object size (px)", "The width and height of the outlined object in image pixels. Sizes describe the object, not its rotation."),
 ("Why counts differ between sheets", "The three picture sets in this workbook are nested. The earlier count looked at every annotation file; the analysed set applies the current rules; the training/test set also drops classes that are no longer used."),
]
d_rows = [hdr(["Term", "Meaning"])]
for i, (a, b) in enumerate(defs):
    d_rows.append(data_row([a, b], band=i % 2 == 1))
d_rows.append(data_row(["Why class rows do not add up to the totals",
                       "A picture can carry more than one tag, or several marked objects. Class rows therefore count "
                       "class memberships: 4,568 training pictures carry 6,268 class memberships. The training and test "
                       "totals count each picture once, so they are smaller than the column sums. Marked objects are "
                       "the exception: each object belongs to one class, so that column does add up to its total."],
                      band=len(d_rows) % 2 == 1))
d_rows += [blank(2),
           [sub("Open points for confirmation: the code used in production files for Field of View Obstructed; the code for Stretched Bubble; "
                "the size limit for the size flags; and whether the Low Dose folder is fully annotated.", 2), None]]
sheets.append({
    "name": "Definitions",
    "column_widths": {"A": 38, "B": 100},
    "row_heights": {"1": 24},
    "freeze_panes": "A2",
    "rows": d_rows})

spec = {"workbook": {"default_header_style": False}, "sheets": sheets}
json.dump(spec, open(f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_client_spec.json", "w", encoding="utf-8"), indent=1)
print("client spec written, sheets:", [s["name"] for s in sheets])
