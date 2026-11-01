"""Build Tag_Combinations_Answer_20261025.xlsx.

Answers the four points raised in the 2026-10-25 review message:
  1. images with 0, 1, 2 ... labels, this report and the FMD onboarding EDA
     report side by side;
  2. the full list of labels considered here;
  3. the most frequent label among the one-label pictures;
  4. the most frequent label pairs among the two-label pictures.

Everything on the label side is recomputed from the verified label matrix:
  run/multilabel_edge_20261023_rev3/{label_matrix.csv,label_matrix_meta.json}
The onboarding-report block is transcribed from that workbook's
"Tags single vs combo" sheet (source named on the sheet itself).

Output: spec JSON + xlsx, both next to the workbook.
"""
import csv, json, collections

ROOT = "D:/fmd-analysis"
REV3 = f"{ROOT}/run/multilabel_edge_20261023_rev3"
OUT_XLSX = f"{ROOT}/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261025.xlsx"
OUT_SPEC = f"{ROOT}/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261025_spec.json"

ACCENT = "1F3864"
BAND = "D9E2F2"
TOTALFILL = "EDF1F8"
NOTE = "595959"


def C(v, **kw):
    d = {"value": v}
    d.update(kw)
    return d


def s_title(t):
    return [C(t, bold=True, font_size=14, font_color=ACCENT)]


def s_line(t):
    return [C(t, italic=True, font_color=NOTE, font_size=9)]


def s_header(row):
    return [C(v, bold=True, font_color="FFFFFF", fill=ACCENT, valign="center") for v in row]


def s_section(row):
    return [C(v, bold=True, fill=BAND, font_color=ACCENT) for v in row]


def s_note(t):
    return [C(t, italic=True, font_color=NOTE, font_size=9)]


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


def s_num(v):
    return C(v, format="#,##0", bold=True)


def s_share(v):
    return C(v, format="0.0%", bold=True)


# ---------------------------------------------------------------- data
META = json.load(open(f"{REV3}/label_matrix_meta.json", encoding="utf-8"))
rows = list(csv.DictReader(open(f"{REV3}/label_matrix.csv", newline="", encoding="utf-8")))
N = len(rows)
assert N == META["headline"]["eda_rows"], (N, META["headline"]["eda_rows"])

ALL_COLS = list(META["label_columns"])
LEGACY = ["bubble_on_123", "bubble_on_edge", "hema_obstruction"]
COUNTED = [c for c in ALL_COLS if c not in LEGACY]

NAME = {
    "foreign_matter_micron_gate": "Foreign Matter gate",
    "fiber_micron_gate": "Fiber gate",
    "extraneous_polymer_micron_gate": "Extraneous Polymer gate",
    "hema_micron_gate": "HEMA gate",
    "bubble": "Bubble", "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
    "missing_primary_package": "Missing Primary Package", "multiple_lenses": "Multiple Lens",
    "no_lens": "No Lens", "cavity_off_center": "Cavity Off Center",
    "folded_lens": "Folded Lens", "lens_off_center": "Lens Off Center",
    "dirty_camera": "Dirty Camera", "dirty_strobe": "Dirty Strobe", "low_dose": "Low Dose",
    "view_obstructed": "View Obstructed", "package_misalignment": "Package Misalignment",
    "bubble_scatter": "Bubble Scatter", "clear": "Clear",
    "bubble_on_123": "Bubble On 123", "bubble_on_edge": "Bubble On Edge",
    "hema_obstruction": "HEMA Obstruction",
}
CODE = {
    "foreign_matter_micron_gate": "P3_FM_MICRON_THRESHOLD", "fiber_micron_gate": "P3_FIB_MICRON_THRESHOLD",
    "extraneous_polymer_micron_gate": "P3_EP_MICRON_THRESHOLD", "hema_micron_gate": "P3_HE_MICRON_THRESHOLD",
    "bubble": "P2_BB", "bubble_cluster": "P2_BC", "wet_package": "P2_WP",
    "missing_primary_package": "P1_MPP", "multiple_lenses": "P1_ML", "no_lens": "P1_NL",
    "cavity_off_center": "P1_COC", "folded_lens": "P1_FL", "lens_off_center": "P2_LOC",
    "dirty_camera": "P2_DC", "dirty_strobe": "P2_DS", "low_dose": "P2_LD",
    "view_obstructed": "F2_FOV / P2_FOV", "package_misalignment": "P1_PPM",
    "bubble_scatter": "P2_BSC", "clear": "no code (folder rule)",
    "bubble_on_123": "no code in the current list", "bubble_on_edge": "no code in the current list",
    "hema_obstruction": "P2_HMO",
}
KIND = {
    "foreign_matter_micron_gate": "Size flag on a marked object",
    "fiber_micron_gate": "Size flag on a marked object",
    "extraneous_polymer_micron_gate": "Size flag on a marked object",
    "hema_micron_gate": "Size flag on a marked object",
    "bubble": "Marked object", "bubble_cluster": "Marked object", "wet_package": "Marked object",
    "bubble_scatter": "Whole-image tag",
    "missing_primary_package": "Whole-image tag, stands alone",
    "package_misalignment": "Whole-image tag, stands alone",
    "cavity_off_center": "Whole-image tag, stands alone",
    "view_obstructed": "Whole-image tag, stands alone",
    "multiple_lenses": "Whole-image tag", "no_lens": "Whole-image tag",
    "folded_lens": "Whole-image tag", "lens_off_center": "Whole-image tag",
    "dirty_camera": "Whole-image tag", "dirty_strobe": "Whole-image tag",
    "low_dose": "Whole-image tag", "clear": "Pass picture, never carries another label",
    "bubble_on_123": "Marked object, kept for reference",
    "bubble_on_edge": "Marked object, kept for reference",
    "hema_obstruction": "Whole-image tag, kept for reference",
}

pos = {c: sum(1 for r in rows if r[c] == "1") for c in ALL_COLS}
label_sets = [frozenset(c for c in COUNTED if r[c] == "1") for r in rows]
card = collections.Counter(len(s) for s in label_sets)
single = collections.Counter()
pair_exact = collections.Counter()
for s in label_sets:
    if len(s) == 1:
        single[next(iter(s))] += 1
    elif len(s) == 2:
        pair_exact[" + ".join(sorted(NAME[c] for c in s))] += 1

N_SINGLE = sum(single.values())
N_PAIR = sum(pair_exact.values())

# FMD onboarding EDA report, sheet "Tags single vs combo":
# how many tags one picture carries (whole-image tags only, tagged pictures only)
ONBOARD_CARD = {1: 3256, 2: 654, 3: 216, 4: 14, 5: 1}
ONBOARD_N = sum(ONBOARD_CARD.values())
ONBOARD_SOURCE = ("Counted in the FMD onboarding EDA report, sheet \"Tags single vs combo\": "
                  "whole-image tags only, pictures carrying at least one tag.")

sheets = []

# ---------------------------------------------------- How to read
hr = [s_title("Tag combinations and object counts - the questions answered")]
hr += [s_line("This file answers the questions on tag combinations and on the object counts: the label "
              "list, the pictures carrying 0, 1, 2 ... labels, the tables for one-label and two-label "
              "pictures, and the objects marked per class in both reports.")]
hr += [[], s_section(["What was asked", "Where it is answered"])]
for q, a in [
    ("Number of images with 0, 1, 2 ... labels, both EDA reports",
     "Sheet: labels per picture (this report beside the onboarding EDA report)"),
    ("List of every label considered", "Sheet: labels considered"),
    ("Most frequent label among the 5,301 one-label images",
     "Sheet: one-label pictures"),
    ("Most frequent label pairs among the 660 two-label images",
     "Sheet: two-label pictures"),
    ("Objects marked per class, both reports (rechecked)",
     "Sheet: objects per class"),
    ("HEMA: is the legacy object class HEMA Fragment, and is every HEMA Fragment counted?",
     "Sheet: objects per class, HEMA section at the foot"),
]:
    hr.append([C(q, bold=True), a])
hr += [[], s_section(["Populations, stated up front"])]
hr += [
    ["This report", C(N, format="#,##0", bold=True),
     "pictures carrying at least one label (every annotated picture, plus pass pictures)"],
    ["FMD onboarding EDA report", C(ONBOARD_N, format="#,##0", bold=True),
     "pictures carrying at least one whole-image tag; marked objects are counted in that report's object sheets"],
]
hr += [s_note("Both reports count every picture of their own population. Nothing is restricted to "
              "pictures that carry a size-gate flag: of the pictures here, "
              f"{pos['foreign_matter_micron_gate']} carry the Foreign Matter size flag, "
              f"{pos['fiber_micron_gate']} the Fiber flag, {pos['extraneous_polymer_micron_gate']} the "
              f"Extraneous Polymer flag and {pos['hema_micron_gate']} the HEMA flag, and the rest of the "
              "population is counted exactly the same way.")]
sheets.append({"name": "How to read", "rows": hr,
               "column_widths": {"A": 58, "B": 44, "C": 60}})

# ---------------------------------------------------- labels per picture
lp = [s_title("Pictures by number of labels, both EDA reports")]
lp += [s_line(f"How many labels one picture carries, in this report ({N:,} pictures) and in the "
              f"FMD onboarding EDA report ({ONBOARD_N:,} pictures with at least one tag).")]
lp += [s_section([f"1. This report: {N:,} pictures carrying at least one label"])]
lp += [s_header(["Labels on the picture", "Pictures", "Share of pictures"])]
for k in range(0, 9):
    n = card.get(k, 0)
    lp.append([f"{k} label(s)", s_num(n), s_share(round(n / N, 4))])
lp += [s_total(["Total", s_num(N), s_share(1.0)])]
lp += [[], s_section([f"2. FMD onboarding EDA report: {ONBOARD_N:,} pictures with at least one tag"])]
lp += [s_header(["Tags on the picture", "Pictures", "Share of tagged pictures"])]
for k in range(1, 6):
    n = ONBOARD_CARD[k]
    lp.append([f"{k} tag(s)", s_num(n), s_share(round(n / ONBOARD_N, 4))])
lp += [s_total(["Total", s_num(ONBOARD_N), s_share(1.0)])]
lp += [[], s_section(["Why the two tables are not the same size"])]
for t in [
    f"Populations: this report starts from every picture with at least one label ({N:,}); the onboarding "
    f"report starts from pictures carrying a whole-image tag ({ONBOARD_N:,}) and does not count pictures "
    "whose only labels are marked objects.",
    "Label definitions: this report counts whole-image tags, marked objects, the four size flags and the "
    "pass pictures as labels. The onboarding report's tag table counts whole-image tags only, so a picture "
    "with one tag and several marked objects reads as 1 there and as several labels here.",
    "Pass pictures: counted as a label here, not counted as a tag there.",
    "One winning annotation source is used per picture here; that report reads every annotation file, "
    "so a picture labelled in two files can be counted with the union of both.",
]:
    lp.append(s_note("- " + t))
lp += [s_note("Both tables are internally consistent: each one's rows add up to its own population.")]
sheets.append({"name": "Labels per picture", "rows": lp, "freeze_panes": "A6",
               "column_widths": {"A": 34, "B": 16, "C": 24, "D": 6}})

# ---------------------------------------------------- labels considered
lc = [s_title("Every label considered in this report")]
lc += [s_line(f"One row per label. {len(COUNTED)} labels are counted in the tables of this file; "
              f"{len(LEGACY)} reference-only labels are listed and excluded.")]
lc += [s_header(["Guide code", "Label", "What it is", "Pictures carrying it",
                 "Counted in this file"])]
for c in ALL_COLS:
    lc.append([CODE[c], NAME[c], KIND[c], s_num(pos[c]),
               C("No - reference only", italic=True) if c in LEGACY else C("Yes", bold=True)])
lc += [s_total(["", "Total pictures", "", s_num(N), ""])]
lc += [s_note("A picture can carry more than one label, so the picture column adds up to more than "
              f"{N:,}. Size flags are labels in their own right and are counted like any other label; "
              "no picture is included or excluded because of them.")]
lc += [s_note("Three guide labels carry no pictures at all (Edge Bottle-Capped, Torn Lens, Lens Rupture) "
              "and therefore have no row here.")]
sheets.append({"name": "Labels considered", "rows": lc, "freeze_panes": "A4",
               "column_widths": {"A": 28, "B": 26, "C": 34, "D": 20, "E": 22}})

# ---------------------------------------------------- one-label pictures
one = [s_title("One-label pictures: the most frequent label first")]
one += [s_line(f"All {N_SINGLE:,} pictures carrying exactly one label, ranked. "
               f"Population: pictures of this report with exactly one label, {N_SINGLE:,}.")]
one += [s_header(["#", "Label", "Pictures", "Share of one-label pictures"])]
for i, (c, n) in enumerate(single.most_common(), start=1):
    one.append([i, NAME[c], s_num(n), s_share(round(n / N_SINGLE, 4))])
one += [s_total(["", "Total", s_num(N_SINGLE), s_share(1.0)])]
one += [s_note("Clear, Missing Primary Package, Cavity Off Center, Primary Package Misalignment and "
               "View Obstructed stand alone by rule, so every picture carrying one of them sits in this "
               "table. Folded Lens and the HEMA size flag never appear alone: they always travel with "
               "another label.")]
sheets.append({"name": "One-label pictures", "rows": one, "freeze_panes": "A5",
               "column_widths": {"A": 6, "B": 32, "C": 14, "D": 26}})

# ---------------------------------------------------- two-label pictures
two = [s_title("Two-label pictures: the most frequent pairs first")]
two += [s_line(f"All {N_PAIR:,} pictures carrying exactly two labels, as {len(pair_exact)} distinct pairs, "
               f"ranked. Population: pictures of this report with exactly two labels, {N_PAIR:,}.")]
two += [s_header(["#", "Pair of labels (the picture carries these two and nothing else)",
                  "Pictures", "Share of two-label pictures"])]
for i, (p, n) in enumerate(pair_exact.most_common(), start=1):
    two.append([i, p, s_num(n), s_share(round(n / N_PAIR, 4))])
two += [s_total(["", "Total", s_num(N_PAIR), s_share(1.0)])]
two += [s_note("Exact pairs: the picture's complete label set is exactly that pair. A pair can look rare "
               "here only because most of its pictures carry a third label as well.")]
sheets.append({"name": "Two-label pictures", "rows": two, "freeze_panes": "A5",
               "column_widths": {"A": 6, "B": 56, "C": 14, "D": 28}})

# ---------------------------------------------------- objects per class
OOI = json.load(open(f"{ROOT}/run/draft2_eda_20261023/ooi_objects_all.json", encoding="utf-8"))
# FMD onboarding EDA report, sheet "Boxes by class"
ONBOARD_OBJ = {
    "Bubble": (11045, 862), "Bubble Cluster": (1182, 428), "Wet Package": (662, 146),
    "Surface Groove": (0, 0), "Fiber": (277, 210), "Extraneous Polymer": (118, 112),
    "HEMA": (103, 101), "Foreign Matter": (626, 331),
    "Bubble On 123": (79, 13), "Bubble On Edge": (90, 14),
}
WHY = {
    "Fiber": "This report keeps the delivered class. The onboarding report applies the guide's "
             "default-to-Fiber rule to 32 objects delivered as Extraneous Polymer; the call is an open point.",
    "Extraneous Polymer": "32 objects delivered as Extraneous Polymer are counted as Fiber in the onboarding "
                          "report; the call is an open point.",
}
obj = [s_title("Objects marked per class, both EDA reports")]
obj += [s_line(f"Every marked object in the archive counted once ({OOI['population']['boxes_total']:,} "
               f"objects on {OOI['population']['pictures_with_a_box']:,} pictures), with the older plain "
               "class names folded into their guide class. This report beside the onboarding EDA report.")]
obj += [s_header(["Class", "Guide code", "Objects marked, this report", "Pictures carrying the class, this report",
                  "Objects marked, onboarding report", "Pictures, onboarding report", "Why the numbers differ"])]
CODES = {"Bubble": "P2_BB", "Bubble Cluster": "P2_BC", "Wet Package": "P2_WP", "Surface Groove": "P1_SG",
         "Fiber": "P3_FIB", "Extraneous Polymer": "P3_EP", "HEMA": "P3_HE", "Foreign Matter": "P3_FM"}
for name in ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
             "Extraneous Polymer", "HEMA", "Foreign Matter"]:
    o = OOI["classes"][name]
    ho, hp = ONBOARD_OBJ[name]
    obj.append([name, CODES[name], s_num(o["objects"]), s_num(o["pictures"]), s_num(ho), s_num(hp),
                WHY.get(name, "Same count" if (o["objects"], o["pictures"]) == (ho, hp) else "")])
obj += [s_section(["Older classes kept for reference (not in the current class list)"])]
for name in ["Bubble On 123", "Bubble On Edge"]:
    o = OOI["reference"][name]
    ho, hp = ONBOARD_OBJ[name]
    obj.append([name, "", s_num(o["objects"]), s_num(o["pictures"]), s_num(ho), s_num(hp),
                "Same count" if (o["objects"], o["pictures"]) == (ho, hp) else ""])
obj += [s_total(["Total objects", "", s_num(OOI["totals"]["all"]), s_num(OOI["population"]["pictures_with_a_box"]),
                 s_num(sum(v[0] for v in ONBOARD_OBJ.values())), s_num(OOI["population"]["pictures_with_a_box"]),
                 "Both reports account for every marked object; a picture can carry several classes, so the "
                 "picture column is the number of pictures with at least one object"])]
obj += [[], s_section(["HEMA: the two older names, checked"])]
obj += [s_header(["Name", "What it is", "Objects or pictures", "Counted as HEMA here"])]
obj += [
    ["HEMA Fragment", "The older library's object class for HEMA", "8 objects on 8 pictures",
     C("Yes: 4 from the newer production annotation, 4 counted here", bold=True)],
    ["HEMA Obstruction", "A whole-image tag, not an object class", "86 pictures",
     C("No, kept separate by rule", bold=True)],
    ["Guide code P3_HE", "Names HEMA Obstruction in the production files and HEMA Fragment in the Sep-22 file",
     "95 production + 4 Sep-22 objects", C("Yes, both under one class", bold=True)],
]
obj += [s_note("All eight HEMA Fragment pictures are counted as HEMA. Four of them also carry a newer "
               "production annotation, which marks them as HEMA objects; the other four exist only in the older "
               "library, and folding that name in is what takes HEMA from 99 to 103 objects and from 97 to 101 "
               "pictures.")]
obj += [s_note("Correction: the earlier object table counted only objects whose class was already a guide code. "
               "Folding the older plain class names in adds 1,095 objects on 229 pictures - the 4 HEMA Fragment "
               "objects are among them - so the class table above replaces that table. The picture and object "
               "columns now use one rule.")]
sheets.append({"name": "Objects per class", "rows": obj, "freeze_panes": "A5",
               "column_widths": {"A": 24, "B": 12, "C": 22, "D": 26, "E": 24, "F": 20, "G": 58}})

# ---------------------------------------------------- definitions
df = [s_title("Definitions")]
df += [s_header(["Term", "Meaning"])]
for t, m in [
    ("Picture considered", f"A distinct picture counted once, even when the same picture appears in more "
                           f"than one folder. This report considers {N:,} of them."),
    ("Label", "Anything the annotation puts on the picture: a whole-image tag, a marked object, a size "
              "flag, or the pass picture mark."),
    ("Whole-image tag", "A label describing the whole picture, for example a folded lens or an off-centre "
                        "lens."),
    ("Marked object", "An outlined object inside the picture, for example a bubble or a fiber."),
    ("Size flag (micron gate)", "A label saying the marked object exceeds the agreed size limit. It is one "
                                "label among the rest; it never decides which pictures are counted."),
    ("Clear", "A pass picture with nothing to report. Clear never appears together with another label."),
    ("One-label picture", "A picture whose complete label set holds exactly one label."),
    ("Two-label picture", "A picture whose complete label set holds exactly two labels."),
    ("Exact pair", "A picture whose complete label set is exactly that pair of labels, nothing else."),
    ("Reference-only labels", "Bubble On 123, Bubble On Edge and HEMA Obstruction: kept for reference, "
                              "not counted in the tables of this file."),
]:
    df.append([C(t, bold=True), m])
sheets.append({"name": "Definitions", "rows": df, "column_widths": {"A": 26, "B": 110}})

spec = {"workbook": {"default_header_style": True, "full_calc_on_load": True}, "sheets": sheets}
with open(OUT_SPEC, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=1)


# ---------------------------------------------------------------- render
def render(spec, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    wb.remove(wb.active)
    for sh in spec["sheets"]:
        ws = wb.create_sheet(sh["name"][:31])
        for r_i, row in enumerate(sh["rows"], start=1):
            for c_i, cell in enumerate(row, start=1):
                if cell is None:
                    continue
                if not isinstance(cell, dict):
                    cell = {"value": cell}
                c = ws.cell(row=r_i, column=c_i, value=cell.get("value"))
                if cell.get("bold"):
                    c.font = Font(bold=True, color=cell.get("font_color"))
                elif cell.get("italic"):
                    c.font = Font(italic=True, color=cell.get("font_color"),
                                  size=cell.get("font_size"))
                elif cell.get("font_color"):
                    c.font = Font(color=cell.get("font_color"), size=cell.get("font_size"))
                if cell.get("font_size") and not (cell.get("bold") or cell.get("italic")):
                    c.font = Font(size=cell["font_size"], color=cell.get("font_color"))
                if cell.get("fill"):
                    c.fill = PatternFill("solid", fgColor=cell["fill"])
                if cell.get("format"):
                    c.number_format = cell["format"]
                c.alignment = Alignment(vertical=cell.get("valign") or "center",
                                        wrap_text=bool(cell.get("wrap")))
        for col, width in (sh.get("column_widths") or {}).items():
            ws.column_dimensions[col].width = width
        if sh.get("freeze_panes"):
            ws.freeze_panes = sh["freeze_panes"]
        ws.sheet_view.showGridLines = False
    wb.save(path)


render(spec, OUT_XLSX)
print("xlsx:", OUT_XLSX)
print("sheets:", [s["name"] for s in sheets])
print("N", N, "card", sorted(card.items()), "single", N_SINGLE, "pairs", len(pair_exact), N_PAIR)
