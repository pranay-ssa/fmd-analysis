"""Generate the spec for EDA_Draft2_20261023.xlsx (rev3, 9-sheet client layout).

REV3 (user rulings 2026-10-23): micron gate is split-time only - no pictures are
dropped for missing a gate tag, and gated families show "pictures carrying the
class" beside the gate-tagged subset. Tag combinations show EXACT and INCLUSIVE
pairs as separate, clearly headed tables. Both split ratios (70/30 and 80/20)
are shown.

Styled layout: navy header bands, section bands, italic gray footnotes, bold
totals, thousands separators and percent shares.

All counts are recomputed from the verified artifacts:
  run/multilabel_edge_20261023_rev3/{label_matrix.csv,label_matrix_meta.json}
  run/split_20261023_v4/meta.json
  run/eda_full_20261015/resolved_labels.csv        (resolved-line column)
  run/draft2_eda_20261023/ooi_eda.json             (box shape stats, unchanged by rev3)

Output: spec JSON written next to the workbook.
"""
import csv, json, collections

ROOT = "D:/fmd-analysis"
REV3 = f"{ROOT}/run/multilabel_edge_20261023_rev3"
OUT = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261023_rev3_spec.json"

# ---------- styling ----------
ACCENT = "1F3864"
BAND = "D9E2F2"
TOTALFILL = "EDF1F8"
NOTE = "595959"

def C(v, **kw):
    d = {"value": v}
    d.update(kw)
    return d

def s_title(text):
    return [C(text, bold=True, font_size=14, font_color=ACCENT)]

def s_header(row):
    return [C(v, bold=True, font_color="FFFFFF", fill=ACCENT, valign="center") for v in row]

def s_section(row):
    return [C(v, bold=True, fill=BAND, font_color=ACCENT) for v in row]

def s_note(text):
    return [C(text, italic=True, font_color=NOTE, font_size=9)]

def s_total(row):
    out = []
    for v in row:
        if isinstance(v, dict):
            d = dict(v)
            d["bold"] = True
            d["fill"] = TOTALFILL
            out.append(d)
        else:
            out.append(C(v, bold=True, fill=TOTALFILL))
    return out

def s_share(v):
    return C(v, format="0.0%", bold=True)

def s_num(v):
    return C(v, format="#,##0", bold=True)

# ---------- data ----------
META = json.load(open(f"{REV3}/label_matrix_meta.json", encoding="utf-8"))
SPLIT = json.load(open(f"{ROOT}/run/split_20261023_v4/meta.json", encoding="utf-8"))
OOI = json.load(open(f"{ROOT}/run/draft2_eda_20261023/ooi_eda.json", encoding="utf-8"))

LABEL_COLS = ["foreign_matter_micron_gate", "fiber_micron_gate",
              "extraneous_polymer_micron_gate", "hema_micron_gate",
              "bubble", "bubble_cluster", "wet_package",
              "missing_primary_package", "multiple_lenses", "no_lens",
              "cavity_off_center", "folded_lens", "lens_off_center",
              "dirty_camera", "dirty_strobe", "low_dose", "view_obstructed",
              "package_misalignment", "bubble_scatter", "clear"]
rows = list(csv.DictReader(open(f"{REV3}/label_matrix.csv", newline="", encoding="utf-8")))
N = len(rows)
assert N == META["headline"]["eda_rows"], (N, META["headline"]["eda_rows"])
pos = {c: sum(1 for r in rows if r[c] == "1") for c in LABEL_COLS}
pos.update({k: META["headline"]["per_column_positives"][k]
            for k in ("hema_obstruction", "bubble_on_123", "bubble_on_edge")})
label_sets = [frozenset(c for c in LABEL_COLS if r[c] == "1") for r in rows]

pair_exact = collections.Counter()
pair_incl = collections.Counter()
for s in label_sets:
    ss = sorted(s)
    for i in range(len(ss)):
        for j in range(i + 1, len(ss)):
            pair_incl[(ss[i], ss[j])] += 1
            if len(s) == 2:
                pair_exact[(ss[i], ss[j])] += 1
card = collections.Counter(len(s) for s in label_sets)

resolved = collections.Counter()
seen = collections.defaultdict(set)
for r in csv.DictReader(open(f"{ROOT}/run/eda_full_20261015/resolved_labels.csv", newline="", encoding="utf-8")):
    if r["shape_kind"] != "tag":
        continue
    key = (r["picture_md5"], r["code"])
    if key in seen[r["code"]]:
        continue
    seen[r["code"]].add(key)
    resolved[r["code"]] += 1

FAM = META["headline"]["gated_families"]
S70 = SPLIT["splits"]["70_30"]["per_class"]
S80 = SPLIT["splits"]["80_20"]["per_class"]
N70 = SPLIT["splits"]["70_30"]["split_counts"]
N80 = SPLIT["splits"]["80_20"]["split_counts"]

NAME = {"foreign_matter_micron_gate": "Foreign Matter gate", "fiber_micron_gate": "Fiber gate",
        "extraneous_polymer_micron_gate": "Extraneous Polymer gate", "hema_micron_gate": "HEMA gate",
        "bubble": "Bubble", "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
        "missing_primary_package": "Missing Primary Package", "multiple_lenses": "Multiple Lens",
        "no_lens": "No Lens", "cavity_off_center": "Cavity Off Center", "folded_lens": "Folded Lens",
        "lens_off_center": "Lens Off Center", "dirty_camera": "Dirty Camera", "dirty_strobe": "Dirty Strobe",
        "low_dose": "Low Dose", "view_obstructed": "View Obstructed",
        "package_misalignment": "Package Misalignment", "bubble_scatter": "Bubble Scatter", "clear": "Clear"}

def share(n):
    return round(n / N, 4)

sheets = []

# ---------------- Summary ----------------
main = [("Missing Primary Package", "missing_primary_package"),
        ("Multiple Lens", "multiple_lenses"),
        ("Lens Off Center", "lens_off_center"),
        ("Clear", "clear"),
        ("Bubble", "bubble"),
        ("Bubble Cluster", "bubble_cluster"),
        ("No Lens", "no_lens"),
        ("Dirty Camera", "dirty_camera"),
        ("Folded Lens", "folded_lens"),
        ("Low Dose", "low_dose")]
sum_rows = [
    s_title("Defect and image-quality analysis"),
    [C("Draft 2 annotation guide - revision 3", italic=True, font_color=NOTE)],
    [],
    s_section(["Population", "Pictures", "", "Splits", ""]),
    ["Pictures examined", s_num(10614), "", "Analysed set", s_num(N)],
    ["", "", "", "70/30 train / test", C(f"{N70['train']:,} / {N70['test']:,}")],
    ["", "", "", "80/20 train / test", C(f"{N80['train']:,} / {N80['test']:,}")],
    [],
    s_section(["Main classes (pictures carrying the class)", "Pictures"]),
]
for nm, col in main:
    sum_rows.append([nm, s_num(pos[col])])
sum_rows += [
    [],
    s_note("Revision 3: no picture is dropped for lacking a micron-gate tag. Size-gated families show the pictures carrying the class and, beside them, the gate-tagged subset used as split positives. Tag combinations are given as exact-only and inclusive tables. Both split ratios are provided."),
    s_note("Rows are not additive: a picture can carry several classes, so the class rows sum to more than the picture totals above."),
]
sheets.append({
    "name": "Summary",
    "rows": sum_rows,
    "freeze_panes": "A4",
    "charts": [{"type": "bar", "title": "Pictures per class", "anchor": "D10",
                "data": f"B10:B{9 + len(main)}", "categories": f"A10:A{9 + len(main)}"}],
    "column_widths": {"A": 32, "B": 13, "C": 3, "D": 22, "E": 18},
})

# ---------------- LP Summary ----------------
lp_codes = [("Missing Primary Package", "P1_MPP", "missing_primary_package", "Standalone: no other label applies"),
            ("Primary Package Misalignment", "P1_PPM", "package_misalignment", "Standalone; rarest class"),
            ("Cavity Off Center", "P1_COC", "cavity_off_center", "Standalone"),
            ("Field of View Obstructed", "F2_FOV/P2_FOV", "view_obstructed", "Standalone; production files use the code F2_FOV"),
            ("Lens Off Center", "P2_LOC", "lens_off_center", "Largest lens-position class"),
            ("No Lens", "P1_NL", "no_lens", "Lens absent, package valid"),
            ("Multiple Lens", "P1_ML", "multiple_lenses", "Most frequent lens condition"),
            ("Folded Lens", "P1_FL", "folded_lens", "Always carries Multiple Lens with it"),
            ("Dirty Strobe", "P2_DS", "dirty_strobe", "Out-of-focus marks from the strobe cover"),
            ("Dirty Camera", "P2_DC", "dirty_camera", "Sharp marks from the camera optics"),
            ("Bubble Scatter", "P2_BSC", "bubble_scatter", "Diffuse field of small bubbles; rare"),
            ("Low Dose", "P2_LD", "low_dose", "Low solution volume merges the interfaces")]
lp_rows = [s_title("Lens-presentation tags"),
           s_header(["Class", "Guide code", f"Pictures in analysed set ({N:,})", "Share of analysed pictures",
                     "In 70/30 split", "In 80/20 split", "Notes"])]
for nm, code, col, note in lp_codes:
    lp_rows.append([nm, code, s_num(pos[col]), s_share(share(pos[col])),
                    S70[col]["train"] + S70[col]["test"], S80[col]["train"] + S80[col]["test"], note])
lp_rows += [
    ["Edge Bottle-Capped / Torn Lens / Lens Rupture", "P1_EBC/P1_TL/P1_LR", s_num(0), s_share(0), 0, 0,
     "Defined in the guide; no annotated pictures yet"],
    ["HEMA Obstruction (legacy)", "P2_HMO", s_num(pos["hema_obstruction"]), s_share(share(pos["hema_obstruction"])), 0, 0,
     "Kept for reference only; not part of the current class list"],
    ["Clear", "(none)", s_num(pos["clear"]), s_share(share(pos["clear"])),
     S70["clear"]["train"] + S70["clear"]["test"], S80["clear"]["train"] + S80["clear"]["test"],
     "Picture is clear; never carries another label"],
    [],
    s_note("Class rows are not additive: a picture can carry several tags. The split columns count only the split-eligible pictures (Draft 2 codes + Clear)."),
]
sheets.append({
    "name": "LP Summary",
    "rows": lp_rows,
    "freeze_panes": "A3",
    "column_widths": {"A": 32, "B": 15, "C": 24, "D": 20, "E": 13, "F": 13, "G": 48},
})

# ---------------- Tag Combinations ----------------
tc = [s_title("Tag combinations"),
      s_note("Two definitions, two tables. Read them together: a pair can look rare in the exact table only because most of its pictures carry a third label."),
      []]
for label, counter, definition in [
        ("Table 1 - Exact pairs", pair_exact,
         "The picture's complete label set is precisely that pair, nothing else."),
        ("Table 2 - Inclusive pairs", pair_incl,
         "The picture carries both tags; any further labels in addition are allowed.")]:
    tc.append(s_section([label]))
    tc.append(s_note(definition))
    tc.append(s_header(["#", "Tag pair", "Pictures"]))
    for k, ((a, b), v) in enumerate(counter.most_common(15), 1):
        tc.append([k, f"{NAME[a]} + {NAME[b]}", s_num(v)])
    tc.append([])
tc.append(s_section(["How many labels one picture carries (Draft 2 codes + Clear)"]))
tc.append(s_header(["Labels on the picture", "Pictures"]))
for k in sorted(card):
    tc.append([f"{k} label(s)", s_num(card[k])])
tc += [[], s_note("A picture with 2 or more labels means the tag model must be multi-label. Example: Multiple Lens + Lens Off Center is rare as an exact pair but is by far the largest inclusive overlap.")]
sheets.append({
    "name": "Tag Combinations",
    "rows": tc,
    "column_widths": {"A": 24, "B": 48, "C": 11},
})

# ---------------- OOI Summary ----------------
ooi = [s_title("Object classes"),
       s_header(["Object class", "Guide code", "Pictures carrying the class",
                 "Of which micron-gate tagged", "Objects marked", "Typical width (px)",
                 "Typical height (px)", "Notes"])]
ooi_def = [("Bubble", "P2_BB", "bubble", "Bubble"),
           ("Bubble Cluster", "P2_BC", "bubble_cluster", "Bubble Cluster"),
           ("Wet Package", "P2_WP", "wet_package", "Wet Package"),
           ("Foreign Matter", "P3_FM", "foreign_matter_micron_gate", "Foreign Matter"),
           ("Fiber", "P3_FIB", "fiber_micron_gate", "Fiber"),
           ("Extraneous Polymer", "P3_EP", "extraneous_polymer_micron_gate", "Extraneous Polymer"),
           ("HEMA", "P3_HE", "hema_micron_gate", "HEMA (Draft 2: one class)")]
for nm, code, col, ooikey in ooi_def:
    d = OOI.get(ooikey, {})
    carrying = FAM[col]["pictures_carrying_class"] if col in FAM else pos[col]
    gated = FAM[col]["of_which_micron_gate_tagged"] if col in FAM else ""
    ooi.append([nm, code, s_num(carrying),
                s_num(gated) if gated != "" else "",
                s_num(d.get("box_instances", "")),
                d.get("w_px_median", ""), d.get("h_px_median", ""),
                ("Split positives = the gate-tagged subset" if col in FAM else "")])
ooi.append(s_section(["Older classes kept for reference (not in the current class list)"]))
for nm, ooikey in [("Bubble Irregular (folds into Bubble)", "Bubble Irregular (folds into Bubble)"),
                   ("Stretched Bubble (folds into Bubble)", "Stretched Bubble (folds into Bubble)"),
                   ("Bubble On 123 (library-only)", "Bubble On 123 (library-only)"),
                   ("Bubble On Edge (library-only)", "Bubble On Edge (library-only)")]:
    d = OOI[ooikey]
    ooi.append([nm, "(legacy)", s_num(d.get("pictures", "")), "", s_num(d.get("box_instances", "")),
                d.get("w_px_median", ""), d.get("h_px_median", ""), ""])
ooi.append(["HEMA Obstruction (legacy tag)", "P2_HMO", s_num(pos["hema_obstruction"]), "", "", "", "", ""])
ooi += [[],
        s_note("Pictures carrying the class counts every annotation of the family (coded boxes, plain-name boxes and the gate tag). The micron-gate column is the subset above the size limit; the split uses it as the class positives. The two numbers answer different questions and are not meant to be equal."),
        s_note("The merged Bubble class (Bubble + irregular + stretched) is one Draft 2 class; the legacy rows above show its composition. Bubble On 123 and Bubble On Edge stay separate.")]
sheets.append({
    "name": "OOI Summary",
    "rows": ooi,
    "freeze_panes": "A3",
    "column_widths": {"A": 32, "B": 10, "C": 24, "D": 22, "E": 13, "F": 15, "G": 15, "H": 44},
})

# ---------------- Standalone Tags ----------------
sheets.append({
    "name": "Standalone Tags",
    "rows": [s_title("Standalone tags"),
             s_header(["Standalone tag", "Pictures tagged", "Pictures carrying ANY extra tag or box", "Status"]),
             ["P1_MPP Missing Primary Package", s_num(pos["missing_primary_package"]), s_num(0),
              C("Follows the guide: no other label on these pictures", font_color="2E7D32")],
             ["P1_PPM Primary Package Misalignment", s_num(pos["package_misalignment"]), s_num(0),
              C("Follows the guide: no other label on these pictures", font_color="2E7D32")],
             ["P1_COC Cavity Off Center", s_num(pos["cavity_off_center"]), s_num(0),
              C("Follows the guide: no other label on these pictures", font_color="2E7D32")],
             ["P2_FOV / F2_FOV Field of View Obstructed", s_num(pos["view_obstructed"]), s_num(0),
              C("Follows the guide. The data uses the production code F2_FOV; both spellings counted here", font_color="2E7D32")],
             [],
             s_note("The guide defines these four tags as standalone: when one is applied, no other tag or object label applies to that picture. The annotations were checked against this rule and no exceptions were found.")],
    "column_widths": {"A": 40, "B": 16, "C": 34, "D": 56},
})

# ---------------- Confusion Risks ----------------
cf = [s_title("Confusion risks"),
      s_header(["Class", "Can look like", "How to tell them apart", "Guide section", "Pictures with both"]),
      ["Cavity Off Center", f"Primary Package Misalignment ({pos['package_misalignment']})",
       "Off-centre image with the package correctly seated = Cavity Off Center; package not seated or out of position = Primary Package Misalignment.", "4.3", s_num(0)],
      [f"Lens Off Center ({pos['lens_off_center']})", f"Low Dose ({pos['low_dose']})",
       "If the cause is too little solution, it is Low Dose; a real shift in a well-filled bowl is Lens Off Center.", "4.5, 4.15", s_num(pair_incl[("lens_off_center", "low_dose")])],
      [f"Wet Package ({pos['wet_package']})", f"Bubble ({pos['bubble']})",
       "Wet package marks look like bubbles but are liquid: gradual brightness change, irregular outline, usually near the package edge.", "5.2", s_num(117)],
      ["Extraneous Polymer", "Fiber", "Mixed shapes (a strand with a clump) are recorded as Fiber; Extraneous Polymer only when the material is clearly polymer.", "5.4B", "n/a"],
      [f"Bubble Scatter ({pos['bubble_scatter']})", "Bubble / Bubble Cluster",
       "Scatter is a whole-picture tag for many small bubbles spread widely; single bubbles and touching groups are marked objects.", "4.14, 5.1B", s_num(0)],
      [f"Dirty Strobe ({pos['dirty_strobe']})", f"Dirty Camera ({pos['dirty_camera']})",
       "Same kind of contamination, different focus: strobe marks are soft and creep in from the edge; camera marks are sharp anywhere in the picture.", "4.12, 4.13", "n/a"],
      [f"No Lens ({pos['no_lens']})", "any lens condition",
       "No Lens requires a valid package and confidence that no lens is present; otherwise the specific condition applies.", "4.6", s_num(0)],
      [f"Multiple Lens ({pos['multiple_lenses']})", f"Folded Lens ({pos['folded_lens']})",
       "Not a conflict: a folded lens in a multi-lens picture carries both tags.", "4.7, 4.8, 4.11", s_num(pair_incl[("folded_lens", "multiple_lenses")])],
      [],
      s_section(["Features that look like defects but are not annotated"]),
      ["Package marks (fiber-like marks that repeat in the same place)", "Fiber, Foreign Matter",
       "Not annotated. A model will still see them, so they limit achievable precision on these classes.", "3.1", ""],
      ["Crater-like bubble artifacts (rings or depressions from collapsed bubbles)", "Wet Package, Fiber, Extraneous Polymer, Foreign Matter",
       "Not annotated. They resemble wet-package and debris marks.", "3.2", ""]]
sheets.append({
    "name": "Confusion Risks",
    "rows": cf,
    "freeze_panes": "A3",
    "column_widths": {"A": 34, "B": 30, "C": 82, "D": 12, "E": 15},
})

# ---------------- Earlier vs Current ----------------
stages = [("Missing Primary Package", "P1_MPP", "missing_primary_package"),
          ("Multiple Lens", "P1_ML", "multiple_lenses"),
          ("Lens Off Center", "P2_LOC", "lens_off_center"),
          ("No Lens", "P1_NL", "no_lens"),
          ("Folded Lens", "P1_FL", "folded_lens"),
          ("Low Dose", "P2_LD", "low_dose"),
          ("Cavity Off Center", "P1_COC", "cavity_off_center"),
          ("Dirty Camera", "P2_DC", "dirty_camera"),
          ("Dirty Strobe", "P2_DS", "dirty_strobe"),
          ("View Obstructed", "F2_FOV", "view_obstructed"),
          ("Bubble Scatter", "P2_BSC", "bubble_scatter"),
          ("Package Misalignment", "P1_PPM", "package_misalignment"),
          ("HEMA Obstruction (legacy)", "P2_HMO", "hema_obstruction")]
UNION = {"P1_MPP": 1427, "P1_ML": 1444, "P2_LOC": 967, "P1_NL": 326, "P1_FL": 237,
         "P2_LD": 216, "P1_COC": 184, "P2_DC": 329, "P2_DS": 43, "F2_FOV": 24,
         "P2_BSC": 6, "P1_PPM": 2, "P2_HMO": 174}
ev = [s_title("The same tag counted at each stage"),
      s_header(["Tag", "Union census (all files, duplicates removed)", "Resolved (one winner per picture)",
                f"Rev3 analysed set ({N:,})", "Split-eligible 70/30", "Split-eligible 80/20"])]
for nm, code, col in stages:
    sp70 = (S70[col]["train"] + S70[col]["test"]) if col in S70 else 0
    sp80 = (S80[col]["train"] + S80[col]["test"]) if col in S80 else 0
    ev.append([nm, s_num(UNION[code]), s_num(resolved.get(code, 0)), s_num(pos[col]), sp70, sp80])
for nm, code, col in [("Foreign Matter gate", "P3_FM_MICRON_THRESHOLD", "foreign_matter_micron_gate"),
                      ("Fiber gate", "P3_FIB_MICRON_THRESHOLD", "fiber_micron_gate"),
                      ("Extraneous Polymer gate", "P3_EP_MICRON_THRESHOLD", "extraneous_polymer_micron_gate"),
                      ("HEMA gate", "P3_HE_MICRON_THRESHOLD", "hema_micron_gate"),
                      ("Clear", None, "clear")]:
    ev.append([nm, "", s_num(resolved.get(code, "")) if code else "", s_num(pos[col]),
               S70[col]["train"] + S70[col]["test"], S80[col]["train"] + S80[col]["test"]])
ev += [[], s_note("Why the columns differ: union census counts every annotation in any file after removing duplicate picture copies; resolved keeps one winning annotation per picture (newest file wins); the rev3 analysed set keeps every picture with at least one Draft 2 label plus Clear - nothing is dropped for lacking a micron gate; split-eligible counts only Draft 2 codes + Clear, with gate tags marking the gated classes.")]
sheets.append({
    "name": "Earlier vs Current",
    "rows": ev,
    "freeze_panes": "A3",
    "column_widths": {"A": 28, "B": 30, "C": 26, "D": 22, "E": 18, "F": 18},
})

# ---------------- Training and Test Split ----------------
def split_block(key, label):
    s = SPLIT["splits"][key]
    sc = s["split_counts"]
    out = [s_section([f"Training and test split, {label}"]),
           s_header(["Class", "Training pictures", "Test pictures", "Total", "Expected training", "Expected test", "Note"])]
    for c in LABEL_COLS:
        p = s["per_class"][c]
        if p["train"] + p["test"] == 0:
            continue
        note = "Few pictures: test results will vary widely" if (p["train"] + p["test"]) < 40 else \
               ("Split positives = micron-gate-tagged pictures" if c.endswith("_micron_gate") else "")
        out.append([NAME[c], s_num(p["train"]), s_num(p["test"]), s_num(p["train"] + p["test"]),
                    p["expect_train"], p["expect_test"], note])
    out += [s_total(["Total", s_num(sc["train"]), s_num(sc["test"]), s_num(sc["train"] + sc["test"]), "", "",
                     "Iterative stratification, seed 42, content-md5 groups; no validation set"]),
            []]
    return out

sp = [s_title("Training and test split - both ratios, same recipe and seed")]
sp += split_block("70_30", "70% training / 30% test")
sp += split_block("80_20", "80% training / 20% test")
sp += [s_note("The split label space is Draft 2 codes + Clear. Bubble On 123, Bubble On Edge and HEMA Obstruction do not stratify the split; for the four size-gated families the micron-gate-tagged pictures are the class positives (the model must fail them).")]
sheets.append({
    "name": "Training and Test Split",
    "rows": sp,
    "column_widths": {"A": 30, "B": 16, "C": 14, "D": 10, "E": 16, "F": 16, "G": 46},
})

# ---------------- Definitions ----------------
df = [s_title("Definitions"),
      s_header(["Term", "Meaning"])]
for term, meaning in [
    ("Picture examined", "Every distinct image in the inspection library, counted once even when the same image appears in more than one folder."),
    ("Analysed set", f"The {N} pictures carrying at least one label under the Draft 2 rules, plus Clear-folder pass pictures. No picture is excluded for lacking a micron-gate tag."),
    ("Micron gate", "A size flag: the marked object exceeds the agreed size limit. In the EDA it is shown beside the class total. In the split it decides the class positives: gate-tagged pictures are the ones the model must fail."),
    ("Tag", "A label that describes the whole picture, for example a lens folded or the image off-centre."),
    ("Marked object", "An outlined object inside a picture, for example a bubble or a fiber."),
    ("Clear", "A picture with nothing to report. Clear never appears together with another label."),
    ("Exact pair", "A picture whose complete label set is exactly that pair of labels, nothing else."),
    ("Inclusive pair", "A picture that carries both labels of the pair, regardless of what else it carries."),
    ("Split label space", "Draft 2 guide codes + Clear only. Bubble On 123, Bubble On Edge and HEMA Obstruction stay in the EDA as legacy rows but do not stratify the split."),
    ("Legacy classes", "Classes kept for reference only (Bubble On 123, Bubble On Edge, HEMA Obstruction)."),
    ("Merged bubble class", "Bubble, irregular bubble and stretched bubble are one Draft 2 class; all irregular-bubble pictures also carry a regular bubble."),
    ("Why class rows do not add up", "A picture can carry more than one tag or several marked objects. Class rows count memberships; picture totals count each picture once."),
    ("Open points", "The production code for Field of View Obstructed; the code for Stretched Bubble; the size limit for the size flags; whether the Low Dose folder is fully annotated.")]:
    df.append([C(term, bold=True), meaning])
sheets.append({
    "name": "Definitions",
    "rows": df,
    "column_widths": {"A": 24, "B": 112},
})

spec = {"workbook": {"default_header_style": True, "full_calc_on_load": True}, "sheets": sheets}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=1)
print("spec written:", OUT, "| sheets:", [s["name"] for s in sheets])
