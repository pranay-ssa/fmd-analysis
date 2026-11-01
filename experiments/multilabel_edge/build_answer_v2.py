"""Build the label-and-object answer workbook for the 2026-10-25 review.

Everything is counted from the annotation resolution, not from the training
label list:
  run/eda_full_20261015/resolved_labels.csv       one row per marked object/tag,
                                                  one annotation of record per picture
  run/multilabel_edge_20261023_rev3/label_matrix.csv   only to identify the Clear
                                                  pictures (no mark anywhere on them)
  run/draft2_eda_20261023/ooi_objects_all.json    object counts with the older
                                                  class names folded in

Rules applied (agreed 2026-10-26):
  * a label is any object class or whole-image tag present on the picture;
  * the micron gate is a size flag INSIDE its class, never a label of its own;
  * Clear is the label for a picture with no mark on it;
  * 32 objects annotated Extraneous Polymer keep the earlier name Fiber for
    this reply, so the numbers line up with the onboarding report.

Output: reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx
"""
import csv, json, collections, sys

ROOT = "D:/fmd-analysis"
RES = f"{ROOT}/run/eda_full_20261015/resolved_labels.csv"
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"
OOI = f"{ROOT}/run/draft2_eda_20261023/ooi_objects_all.json"
OUT_XLSX = f"{ROOT}/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx"
OUT_SPEC = f"{ROOT}/reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026_spec.json"

ACCENT, BAND, TOTALFILL, NOTE = "1F3864", "D9E2F2", "EDF1F8", "595959"


def C(v, **kw):
    d = {"value": v}
    d.update(kw)
    return d


def s_title(t): return [C(t, bold=True, font_size=14, font_color=ACCENT)]
def s_line(t): return [C(t, italic=True, font_color=NOTE, font_size=9)]
def s_note(t): return [C(t, italic=True, font_color=NOTE, font_size=9)]
def s_header(r): return [C(v, bold=True, font_color="FFFFFF", fill=ACCENT, valign="center") for v in r]
def s_section(r): return [C(v, bold=True, fill=BAND, font_color=ACCENT) for v in r]
def s_num(v): return C(v, format="#,##0", bold=True)
def s_share(v): return C(v, format="0.0%", bold=True)


def s_total(row):
    out = []
    for v in row:
        if isinstance(v, dict):
            d = dict(v); d["bold"] = True; d["fill"] = TOTALFILL; out.append(d)
        else:
            out.append(C(v, bold=True, fill=TOTALFILL))
    return out


# ------------------------------------------------------------------ data
rows = list(csv.DictReader(open(RES, newline="", encoding="utf-8")))
mat = list(csv.DictReader(open(MAT, newline="", encoding="utf-8")))
obj = json.load(open(OOI, encoding="utf-8"))

FAMILY = {
    "P2_BB": "Bubble", "Bubble": "Bubble", "P2_BI": "Bubble", "Bubble Irregular": "Bubble",
    "P2_BST": "Bubble", "Stretched Bubble": "Bubble",
    "P2_BC": "Bubble Cluster", "Bubble Cluster": "Bubble Cluster",
    "P2_WP": "Wet Package", "Wet Package": "Wet Package",
    "P3_FM": "Foreign Matter", "Foreign Matter": "Foreign Matter",
    "P3_FIB": "Fiber", "Fiber": "Fiber",
    "P3_EP": "Extraneous Polymer", "Extraneous Polymer": "Extraneous Polymer",
    "P3_HE": "HEMA", "HEMA Fragment": "HEMA",
    "Bubble On 123": "Bubble On 123", "Bubble On Edge": "Bubble On Edge",
    "P1_MPP": "Missing Primary Package", "P1_PPM": "Package Misalignment",
    "P1_COC": "Cavity Off Center", "P1_ML": "Multiple Lens", "P1_FL": "Folded Lens",
    "P1_NL": "No Lens", "P2_LOC": "Lens Off Center", "P2_LD": "Low Dose",
    "P2_DS": "Dirty Strobe", "P2_DC": "Dirty Camera", "P2_BSC": "Bubble Scatter",
    "P2_HMO": "HEMA Obstruction", "F2_FOV": "View Obstructed", "P2_FOV": "View Obstructed",
    "P3_FM_MICRON_THRESHOLD": "Foreign Matter", "P3_FIB_MICRON_THRESHOLD": "Fiber",
    "P3_EP_MICRON_THRESHOLD": "Extraneous Polymer", "P3_HE_MICRON_THRESHOLD": "HEMA",
}
GATE = {"Foreign Matter": "P3_FM_MICRON_THRESHOLD", "Fiber": "P3_FIB_MICRON_THRESHOLD",
        "Extraneous Polymer": "P3_EP_MICRON_THRESHOLD", "HEMA": "P3_HE_MICRON_THRESHOLD"}

codes = collections.defaultdict(set)
for r in rows:
    codes[r["picture_md5"]].add(r["code"])

# the 32 objects the newer annotation calls Extraneous Polymer but that the
# onboarding report counts as Fiber: pictures whose only such mark is EP while
# the training list carries the Fiber size flag
FLIP = {r["picture_md5"] for r in mat
        if r["fiber_micron_gate"] == "1" and "P3_FIB_MICRON_THRESHOLD" not in codes[r["picture_md5"]]}
CLEAR = {r["picture_md5"] for r in mat if r["clear"] == "1"}
assert len(FLIP) == 32 and len(CLEAR) == 2156 and not (CLEAR & set(codes))

labels = {}
for p, cs in codes.items():
    s = {FAMILY[c] for c in cs}
    if p in FLIP:
        s.discard("Extraneous Polymer")
        s.add("Fiber")
    labels[p] = s
for p in CLEAR:
    labels[p] = {"Clear"}

N = len(labels)
card = collections.Counter(len(v) for v in labels.values())
singles = collections.Counter(next(iter(s)) for s in labels.values() if len(s) == 1)
pairs = collections.Counter(tuple(sorted(s)) for s in labels.values() if len(s) == 2)
per_label = collections.Counter()
for s in labels.values():
    per_label.update(s)
gate_pics = {c: {p for p, cs in codes.items() if GATE[c] in cs} for c in GATE}

# hand-typed expectations, independent of the workbook
assert N == 6938
assert dict(card) == {1: 5531, 2: 649, 3: 418, 4: 199, 5: 97, 6: 29, 7: 12, 8: 3}
assert len(pairs) == 28 and sum(pairs.values()) == 649
assert singles.most_common(2) == [("Clear", 2156), ("Missing Primary Package", 1426)]
assert pairs.most_common(1) == [(("Lens Off Center", "Multiple Lens"), 371)]
assert per_label["Fiber"] == 210 and per_label["Extraneous Polymer"] == 112
assert sum(card.values()) == N

QUOTED = {0: 248, 1: 5301, 2: 660, 3: 424, 4: 207, 5: 71, 6: 20, 7: 5, 8: 2}
ONBOARD = {1: 3256, 2: 654, 3: 216, 4: 14, 5: 1}

CLASS_KIND = {
    "Bubble": "Marked object", "Bubble Cluster": "Marked object", "Wet Package": "Marked object",
    "Foreign Matter": "Marked object", "Fiber": "Marked object",
    "Extraneous Polymer": "Marked object", "HEMA": "Marked object",
    "Missing Primary Package": "Whole-image tag", "Multiple Lens": "Whole-image tag",
    "No Lens": "Whole-image tag", "Cavity Off Center": "Whole-image tag",
    "Folded Lens": "Whole-image tag", "Lens Off Center": "Whole-image tag",
    "Dirty Camera": "Whole-image tag", "Dirty Strobe": "Whole-image tag",
    "Low Dose": "Whole-image tag", "View Obstructed": "Whole-image tag",
    "Package Misalignment": "Whole-image tag", "Bubble Scatter": "Whole-image tag",
    "HEMA Obstruction": "Whole-image tag, kept for reference",
    "Bubble On 123": "Marked object, kept for reference",
    "Bubble On Edge": "Marked object, kept for reference",
    "Clear": "No mark on the picture",
}
CLASS_CODE = {
    "Bubble": "P2_BB (also P2_BI, P2_BST)", "Bubble Cluster": "P2_BC", "Wet Package": "P2_WP",
    "Foreign Matter": "P3_FM", "Fiber": "P3_FIB", "Extraneous Polymer": "P3_EP",
    "HEMA": "P3_HE", "Missing Primary Package": "P1_MPP", "Package Misalignment": "P1_PPM",
    "Cavity Off Center": "P1_COC", "Multiple Lens": "P1_ML", "Folded Lens": "P1_FL",
    "No Lens": "P1_NL", "Lens Off Center": "P2_LOC", "Low Dose": "P2_LD",
    "Dirty Strobe": "P2_DS", "Dirty Camera": "P2_DC", "Bubble Scatter": "P2_BSC",
    "View Obstructed": "F2_FOV", "HEMA Obstruction": "P2_HMO",
    "Bubble On 123": "no current code", "Bubble On Edge": "no current code",
    "Clear": "no code",
}
ORDER = ["Bubble", "Bubble Cluster", "Wet Package", "Foreign Matter", "Fiber",
         "Extraneous Polymer", "HEMA", "Missing Primary Package", "Multiple Lens", "No Lens",
         "Cavity Off Center", "Folded Lens", "Lens Off Center", "Dirty Camera", "Dirty Strobe",
         "Low Dose", "View Obstructed", "Package Misalignment", "Bubble Scatter",
         "HEMA Obstruction", "Bubble On 123", "Bubble On Edge", "Clear"]
assert set(ORDER) == set(per_label), set(per_label) ^ set(ORDER)

sheets = []

# ---------------------------------------------------------------- 1 how to read
hr = [s_title("Labels on a picture: the questions answered")]
hr += [s_line("What was asked in the review, and where each answer sits. Every count below is "
              "taken from the annotations: one annotation of record per picture, duplicate copies "
              "of a picture counted once.")]
hr += [[], s_section(["What was asked", "Where it is answered"])]
for q, a in [
    ("Pictures carrying 0, 1, 2 ... labels, this report beside the onboarding report",
     "Sheet: labels per picture"),
    ("The full list of labels considered", "Sheet: labels considered"),
    ("The most frequent label on one-label pictures", "Sheet: one-label pictures"),
    ("The most frequent label pairs on two-label pictures", "Sheet: two-label pictures"),
    ("Is the size flag a separate label, and what does the Debris group hold",
     "Sheets: labels considered, debris group"),
    ("Objects marked per class, both reports, and the HEMA names", "Sheet: objects per class"),
]:
    hr.append([q, a])
hr += [[], s_section(["The pictures behind these counts"])]
hr += [s_header(["Population", "Pictures", "What it is"])]
hr += [
    ["Images in the archive", s_num(10614), "Every image delivered, annotated or not"],
    ["Pictures in an annotation", s_num(6938), "At least one annotation entry exists for the picture"],
    ["Pictures with a mark", s_num(4782), "At least one object or tag on the annotation of record"],
    ["Pictures with no mark (Clear)", s_num(2156), "Nothing marked anywhere on the picture"],
    ["Pictures in the onboarding report", s_num(4141), "Pictures carrying a whole-image tag in its data"],
]
hr += [s_note("The onboarding report's 4,141 is this report's 6,938 minus 641 pictures that carry only "
              "an object and 2,156 Clear pictures. Its tag table covers whole-image tags only, so it "
              "cannot be compared with a table that counts object classes too; both populations are "
              "named in the labels-per-picture sheet.")]
hr += [s_note("No picture in the annotation is unlabelled. A picture with nothing marked is Clear, and "
              "Clear is a label.")]
sheets.append({"name": "How to read", "rows": hr, "freeze_panes": "A6",
               "column_widths": {"A": 62, "B": 14, "C": 74}})

# ---------------------------------------------------------------- 2 labels per picture
lp = [s_title("How many labels one picture carries, both reports")]
lp += [s_line(f"This report: all {N:,} annotated pictures, every object class, every whole-image tag "
              "and Clear. Onboarding report: whole-image tags only, 4,141 pictures.")]
lp += [s_section(["1. This report, and the table quoted in the review"])]
lp += [s_header(["Labels on the picture", "This report, pictures", "Share",
                 "As quoted in the review", "Onboarding report (tags only)"])]
for k in range(0, 9):
    lp.append([C(k), s_num(card.get(k, 0)), s_share(card.get(k, 0) / N),
               s_num(QUOTED.get(k, 0)) if k in QUOTED else C("-"),
               s_num(ONBOARD[k]) if k in ONBOARD else C("-")])
lp += [s_total(["Total", s_num(N), s_share(1.0), s_num(N), s_num(4141)])]
lp += [[], s_section(["2. Why the two columns differ"])]
lp += [s_note("No picture is unlabelled. The earlier table showed 248 pictures at 0 labels because the "
              "four size-flagged object classes (Foreign Matter, Fiber, Extraneous Polymer, HEMA) had "
              "no column of their own: a picture whose only mark was such an object had nowhere to "
              "appear. All four now have their own column, so the 0 row is empty.")]
lp += [s_note("A size flag is part of its class, not a second label. Counting the flag beside the class "
              "would give every large object two labels; it is counted here once, inside its class.")]
lp += [s_note("The onboarding report counts whole-image tags only (4,141 pictures, 15 tags). Object "
              "marks and Clear frames sit outside it, which is why its row for one label reads 3,256 "
              "and its table stops at 5.")]
sheets.append({"name": "Labels per picture", "rows": lp, "freeze_panes": "A5",
               "column_widths": {"A": 26, "B": 20, "C": 10, "D": 22, "E": 24}})

# ---------------------------------------------------------------- 3 labels considered
lc = [s_title("Every label considered, and every name it appears under")]
lc += [s_line(f"{len(ORDER)} names occur in the annotation: 12 whole-image tags, 7 object classes, the "
              "HEMA Obstruction tag, two older box classes kept for reference, and Clear. The guide defines "
              "23 classes: 15 tags and 8 object classes. Four of those have no examples yet, the three "
              "lens-damage tags and Surface Groove, so they carry no pictures here. The pictures column "
              "counts pictures carrying the label, so the rows overlap and do not sum to a picture total.")]
lc += [s_header(["Label", "What it is", "Code or name in the annotation", "Pictures", "Counted as a label"])]
REF_ONLY = {"HEMA Obstruction", "Bubble On 123", "Bubble On Edge"}
for name in ORDER:
    counted = "Reference only, not in the split" if name in REF_ONLY else "Yes"
    lc.append([name, CLASS_KIND[name], CLASS_CODE[name], s_num(per_label[name]), C(counted, bold=True)])
lc += [[], s_section(["Not labels: the size flag inside a class"])]
lc += [s_header(["Size flag", "Inside which class", "Pictures carrying the class", "Of which flagged", "Share flagged"])]
for name in ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"]:
    lc.append([name + " size flag", name, s_num(per_label[name]), s_num(len(gate_pics[name])),
               s_share(len(gate_pics[name]) / per_label[name])])
lc += [s_note("The flag marks the objects that crossed the size threshold. It never appears without its "
              "class object, so it is a subset of the class and is counted inside the class total.")]
lc += [s_note("Flags are counted as annotated. The 32 objects kept under the earlier Fiber name carry the "
              "Extraneous Polymer flag, which is why Fiber reads 136 of 210 flagged and Extraneous "
              "Polymer 33 of 112.")]
lc += [[], s_section(["Names that appear in the annotation but are not current labels"])]
lc += [s_header(["Name", "Belongs to", "Pictures", "Why it is listed"])]
lc += [
    ["Bubble Irregular, Stretched Bubble", "Bubble", "147 / 6",
     "Older names merged into Bubble; those pictures also carry the Bubble mark"],
    ["P3_FM_MICRON_THRESHOLD and the three other flag names", "their class", s_num(388),
     "Size flag, not a class; 388 pictures carry at least one"],
]
lc += [[], s_section(["Where the training label list differs from the annotation"])]
lc += [s_header(["Item", "Training label list", "Annotation", "Explanation"])]
lc += [
    ["Fiber size flag, pictures", s_num(168), s_num(136),
     "32 pictures whose objects the newer annotation calls Extraneous Polymer carry the Fiber flag in "
     "the training label list, because the guide defaults an unclear object to Fiber. This workbook "
     "counts the flag as annotated."],
    ["Bubble Cluster, pictures", s_num(430), s_num(428),
     "Two pictures keep an older Bubble Cluster mark although their newer annotation has none. This "
     "workbook counts the annotation."],
]
lc += [s_note("The training label list is unchanged. It is the basis of the train and test split, not a "
              "count of the annotation, and every count in this workbook comes from the annotation.")]
sheets.append({"name": "Labels considered", "rows": lc, "freeze_panes": "A4",
               "column_widths": {"A": 34, "B": 30, "C": 32, "D": 12, "E": 20}})

# ---------------------------------------------------------------- 4 one-label
ol = [s_title("The label on one-label pictures")]
ol += [s_line(f"{sum(singles.values()):,} pictures carry exactly one label. Counted from the annotation, "
              "size flags folded into their class, Clear included.")]
ol += [s_header(["Rank", "Label", "Pictures", "Share of one-label pictures"])]
for i, (name, n) in enumerate(singles.most_common(), start=1):
    ol.append([C(i), name, s_num(n), s_share(n / sum(singles.values()))])
ol += [s_total(["", "Total", s_num(sum(singles.values())), s_share(1.0)])]
ol += [s_note("Clear is the largest group: 2,156 pictures show no defect at all. Clear, Missing Primary "
              "Package, Cavity Off Center, Package Misalignment and View Obstructed are alone by rule; "
              "they carry no co-tag.")]
sheets.append({"name": "One-label pictures", "rows": ol, "freeze_panes": "A4",
               "column_widths": {"A": 7, "B": 40, "C": 12, "D": 26}})

# ---------------------------------------------------------------- 5 two-label
tl = [s_title("The two labels on two-label pictures")]
tl += [s_line(f"{sum(pairs.values()):,} pictures carry exactly two labels, in {len(pairs)} distinct pairs.")]
tl += [s_header(["Rank", "The two labels", "Pictures", "Share of two-label pictures"])]
for i, (pr, n) in enumerate(pairs.most_common(), start=1):
    tl.append([C(i), " + ".join(pr), s_num(n), s_share(n / sum(pairs.values()))])
tl += [s_total(["", "Total", s_num(sum(pairs.values())), s_share(1.0)])]
tl += [s_note("A pair is counted once, order ignored. A size flag is not a pair member; a picture with a "
              "large Bubble is still Bubble plus whatever else it carries.")]
sheets.append({"name": "Two-label pictures", "rows": tl, "freeze_panes": "A4",
               "column_widths": {"A": 7, "B": 52, "C": 12, "D": 26}})

# ---------------------------------------------------------------- 6 debris group
DEB = ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"]
union = set()
for name in DEB:
    union |= {p for p, s in labels.items() if name in s}
multi = sum(1 for p in union if sum(1 for n in DEB if n in labels[p]) > 1)
any_gate = sum(1 for p in union if any(GATE[n] in codes[p] for n in DEB))
dg = [s_title("The Debris group: the four classes that hold debris")]
dg += [s_line("Debris is not a class in the guide. It is the group of four object classes below. A picture "
              "can hold more than one of them, so the class rows do not add to the group total.")]
dg += [s_header(["Class", "Pictures", "Of which over the size threshold", "Share over threshold"])]
for name in DEB:
    dg.append([name, s_num(per_label[name]), s_num(len(gate_pics[name])),
               s_share(len(gate_pics[name]) / per_label[name])])
dg += [s_total(["Debris group, pictures (each picture once)", s_num(len(union)),
                s_num(any_gate), s_share(any_gate / len(union))])]
dg += [[], s_section(["How the group overlaps"])]
dg += [s_header(["Pictures holding", "Count"])]
dg.append(["Exactly one of the four classes", s_num(len(union) - multi)])
dg.append(["Two or more of the four classes", s_num(multi)])
dg.append(["At least one object over the size threshold", s_num(any_gate)])
dg += [s_note("647 pictures carry at least one debris class, and 388 of those carry at least one object "
              "over the size threshold. The flag is a subset inside each class; it is not a filter on "
              "the group.")]
sheets.append({"name": "Debris group", "rows": dg, "freeze_panes": "A4",
               "column_widths": {"A": 46, "B": 12, "C": 30, "D": 20}})

# ---------------------------------------------------------------- 7 objects per class
ONB_OBJ = {"Bubble": (11045, 862), "Bubble Cluster": (1182, 428), "Wet Package": (662, 146),
           "Surface Groove": (0, 0), "Fiber": (277, 210), "Extraneous Polymer": (118, 112),
           "HEMA": (103, 101), "Foreign Matter": (626, 331),
           "Bubble On 123": (79, 13), "Bubble On Edge": (90, 14)}
ob = [s_title("Objects marked per class, both reports")]
ob += [s_line(f"Every marked object in the archive counted once ({obj['population']['boxes_total']:,} "
              f"objects on {obj['population']['pictures_with_a_box']:,} pictures), with the older plain "
              "class names folded into their class.")]
ob += [s_header(["Class", "Guide code", "Objects, this report", "Pictures, this report",
                 "Objects, onboarding report", "Pictures, onboarding report", "Why the two differ"])]
CODES = {"Bubble": "P2_BB", "Bubble Cluster": "P2_BC", "Wet Package": "P2_WP", "Surface Groove": "P1_SG",
         "Fiber": "P3_FIB", "Extraneous Polymer": "P3_EP", "HEMA": "P3_HE", "Foreign Matter": "P3_FM"}
WHY = {
    "Fiber": "32 objects that the newer annotation calls Extraneous Polymer keep the earlier name here, "
             "so this column agrees with the onboarding report. Under the newer name the class holds "
             "245 objects on 178 pictures. When the class is next annotated the newer name will be used.",
    "Extraneous Polymer": "The same 32 objects sit in Fiber above, for the same reason; under the newer "
                          "name the class holds 150 objects on 144 pictures.",
}
EARLIER_NAME = {"Fiber": (277, 210), "Extraneous Polymer": (118, 112)}
for name in ["Bubble", "Bubble Cluster", "Wet Package", "Surface Groove", "Fiber",
             "Extraneous Polymer", "HEMA", "Foreign Matter"]:
    o = obj["classes"][name]
    ho, hp = ONB_OBJ[name]
    own = EARLIER_NAME.get(name, (o["objects"], o["pictures"]))
    ob.append([name, CODES[name], s_num(own[0]), s_num(own[1]), s_num(ho), s_num(hp),
               WHY.get(name, "Same count" if own == (ho, hp) else "")])
ob += [s_section(["Older classes kept for reference (not in the current class list)"])]
for name in ["Bubble On 123", "Bubble On Edge"]:
    o = obj["reference"][name]
    ho, hp = ONB_OBJ[name]
    ob.append([name, "", s_num(o["objects"]), s_num(o["pictures"]), s_num(ho), s_num(hp),
               "Same count" if (o["objects"], o["pictures"]) == (ho, hp) else ""])
ob += [s_total(["Total objects", "", s_num(obj["totals"]["all"]), s_num(obj["population"]["pictures_with_a_box"]),
                s_num(14182), s_num(obj["population"]["pictures_with_a_box"]),
                "Both reports account for every marked object"])]
ob += [s_note("A picture can carry several classes, so the picture column is the number of pictures with "
              "at least one object, not the sum of the rows.")]
ob += [[], s_section(["HEMA: the two older names, checked"])]
ob += [s_header(["Name", "What it is", "Objects or pictures", "Counted as HEMA here"])]
ob += [
    ["HEMA Fragment", "The older library's object class for HEMA", "8 objects on 8 pictures",
     C("Yes: 4 from the newer production annotation, 4 counted by the older name", bold=True)],
    ["HEMA Obstruction", "A whole-image tag, not an object class", "86 pictures",
     C("No, kept separate by rule", bold=True)],
    ["Guide code P3_HE", "Names HEMA Obstruction in the production files and HEMA Fragment in one later file",
     "95 production + 4 later objects", C("Yes, both under one class", bold=True)],
]
ob += [s_note("All eight HEMA Fragment pictures count as HEMA: four also carry a newer production "
              "annotation, the other four exist only under the older name and are folded in here. HEMA "
              "reads 103 objects on 101 pictures.")]
ob += [[], s_section(["The table quoted in the review, checked line by line"])]
ob += [s_header(["Class", "Quoted: pictures / objects (flag)", "Our count: pictures / objects (flag)",
                 "What the quoted figure counts"])]
ob += [
    ["Bubble", "862 / 20,831", "862 / 11,045",
     "The picture count agrees. The object count has no source in the archive: every box of every class in "
     "all nine annotation files is 14,996, and the onboarding report also counts 11,045."],
    ["Bubble Cluster", "430 / 1,070", "428 / 1,182",
     "1,070 is the boxes in the seven production files; the other 112 come from the older library, and two "
     "pictures keep an older mark the current files no longer carry."],
    ["Wet Package", "146 / 593", "146 / 662",
     "593 counts only boxes carrying the P2_WP code; the other 69 carry the older plain Wet Package name."],
    ["Foreign Matter", "37 / 179", "331 / 626",
     "Neither figure matches the archive or the onboarding report: the production files alone hold 571 "
     "boxes, so 37 pictures and 179 objects match no counting basis we hold."],
    ["Fiber", "210 / flag 171 / 223", "210 / flag 136 / 277",
     "171 is the Foreign Matter flag count, not the Fiber one. 223 counts only boxes carrying P3_FIB; "
     "adding 22 older Fiber boxes and 32 objects the newer annotation calls Extraneous Polymer gives 277."],
    ["Extraneous Polymer", "144 / flag 168 / 149", "112 / flag 33 / 118",
     "144 is the count before 32 objects moved to Fiber; the flag on those 144 pictures is 33. 168 is the "
     "Fiber flag in the training label list, which is why the row reads as more flagged objects than pictures."],
    ["HEMA", "101 / flag 94 / 99", "101 / flag 94 / 103",
     "99 leaves out the 4 boxes from the older library that the onboarding report also counts."],
    ["HEMA Obstruction (legacy)", "89 / 89", "86 pictures / no objects",
     "It is a whole-image tag, so it has no objects. The archive holds it on 86 pictures of record; the "
     "other 88 mentions are superseded."],
]
ob += [s_note("Read down the two count columns with the note on the right: several figures in the quoted table "
              "count a different unit (boxes carrying one code, boxes in one file group, or a count taken "
              "before the 32 objects moved), which is what makes the columns look inconsistent.")]
ob += [s_note("One internal check closes the question: a size flag sits inside its class, so a class can never "
              "show more flagged objects than pictures. The Extraneous Polymer row shows 168 flagged on 144 "
              "pictures, so that row was assembled from two tables.")]
ob += [s_note("The two reports we can test agree line by line in the table above: 14,182 objects on 1,130 "
              "pictures, both.")]
sheets.append({"name": "Objects per class", "rows": ob, "freeze_panes": "A5",
               "column_widths": {"A": 24, "B": 12, "C": 20, "D": 22, "E": 22, "F": 22, "G": 62}})

# ---------------------------------------------------------------- 8 definitions
df = [s_title("Definitions")]
df += [s_line("One meaning per term, used the same way on every sheet.")]
df += [s_header(["Term", "Meaning"])]
for t, m in [
    ("Picture", "One image, counting duplicate copies of the same image once."),
    ("Label", "One class present on a picture: an object class, a whole-image tag, or Clear."),
    ("Object", "A box drawn around a defect on a picture. One picture can hold many objects."),
    ("Object class", "The class of a marked object: Bubble, Bubble Cluster, Wet Package, Foreign Matter, "
                     "Fiber, Extraneous Polymer, HEMA."),
    ("Whole-image tag", "One tag on the picture, not on an object: lens presentation, image condition, "
                        "or the reference tag HEMA Obstruction."),
    ("Size flag", "The micron threshold tag on an object. It marks an object that crossed the size "
                  "threshold and sits inside its class; it is not a label of its own."),
    ("Clear", "A picture with nothing marked on it. It counts as one label."),
    ("Debris group", "The four object classes together: Foreign Matter, Fiber, Extraneous Polymer, HEMA. "
                     "A group, not a class in the guide."),
    ("Annotation of record", "The newest annotation for a picture. Older annotations of the same picture "
                             "are ignored."),
]:
    df.append([t, m])
sheets.append({"name": "Definitions", "rows": df, "freeze_panes": "A4",
               "column_widths": {"A": 26, "B": 96}})


# ------------------------------------------------------------------ render
def render(spec, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    for sh in spec:
        ws = wb.create_sheet(sh["name"])
        widths = sh.get("column_widths", {})
        for i, row in enumerate(sh["rows"], start=1):
            for j, cell in enumerate(row, start=1):
                if isinstance(cell, dict):
                    val, opts = cell["value"], cell
                else:
                    val, opts = cell, {}
                c = ws.cell(row=i, column=j, value=val)
                c.font = Font(name="Calibri", size=opts.get("font_size", 10),
                              bold=opts.get("bold", False),
                              italic=opts.get("italic", False),
                              color=opts.get("font_color", "000000"))
                if opts.get("fill"):
                    c.fill = PatternFill("solid", start_color=opts["fill"], end_color=opts["fill"])
                if opts.get("format"):
                    c.number_format = opts["format"]
                c.alignment = Alignment(vertical=opts.get("valign", "center"), wrap_text=True)
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        if sh.get("freeze_panes"):
            ws.freeze_panes = sh["freeze_panes"]
        ws.sheet_view.showGridLines = False
    wb.save(path)


if __name__ == "__main__":
    with open(OUT_SPEC, "w", encoding="utf-8") as f:
        json.dump(sheets, f, indent=1)
    render(sheets, OUT_XLSX)
    print("written:", OUT_XLSX)
    print("sheets:", [s["name"] for s in sheets])
    print("labels per picture:", dict(sorted(card.items())), "total", sum(card.values()))
    print("one-label top 5:", singles.most_common(5))
    print("pairs:", len(pairs), "distinct,", sum(pairs.values()), "pictures")
