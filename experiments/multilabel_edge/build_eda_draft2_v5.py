"""Rebuild the Draft 2 EDA from the annotation (2026-10-26).

Rules (agreed 2026-10-26):
  * every count comes from the annotation: one annotation of record per picture,
    duplicate copies of a picture counted once;
  * a label is any object class or whole-image tag on the picture, plus Clear
    for a picture with nothing marked;
  * the micron size flag is a subset of its class, never a label;
  * 32 objects the newer annotation calls Extraneous Polymer keep the earlier
    Fiber name, so the object table agrees with the onboarding report;
  * the split is untouched: its sheet reproduces the frozen split and says so.

Inputs (read-only):
  run/eda_full_20261015/{resolved_labels.csv,box_sizes.csv,label_census.csv,
                         picture_table.csv}
  run/multilabel_edge_20261023_rev3/label_matrix.csv   (Clear rows, split-eligible flag)
  run/split_20261023_v4/meta.json
  data/*.xml                                          (union census only)

Output: reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx
"""
import csv, json, glob, os, re, collections, statistics

ROOT = "D:/fmd-analysis"
RES = f"{ROOT}/run/eda_full_20261015/resolved_labels.csv"
BOX = f"{ROOT}/run/eda_full_20261015/box_sizes.csv"
PT = f"{ROOT}/run/eda_full_20261015/picture_table.csv"
MAT = f"{ROOT}/run/multilabel_edge_20261023_rev3/label_matrix.csv"
SPLIT = f"{ROOT}/run/split_20261023_v4/meta.json"
OUT = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx"
SPEC = f"{ROOT}/reports/draft2_eda_20261023/EDA_Draft2_20261026_spec.json"

ACCENT, BAND, TOTALFILL, NOTE = "1F3864", "D9E2F2", "EDF1F8", "595959"


def C(v, **kw):
    d = {"value": v}
    d.update(kw)
    return d


def s_title(t): return [C(t, bold=True, font_size=14, font_color=ACCENT)]
def s_sub(t): return [C(t, italic=True, font_color=NOTE, font_size=9)]
def s_note(t): return [C(t, italic=True, font_color=NOTE, font_size=9)]
def s_header(r): return [C(v, bold=True, font_color="FFFFFF", fill=ACCENT, valign="center") for v in r]
def s_section(r): return [C(v, bold=True, fill=BAND, font_color=ACCENT) for v in r]
def s_num(v): return C(v, format="#,##0", bold=True)
def s_share(v): return C(v, format="0.0%", bold=True)
def s_dec(v): return C(v, format="0.0", bold=True)


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
split_meta = json.load(open(SPLIT, encoding="utf-8"))

MAP = {
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
CANON = {
    "bubble": "Bubble", "bubble_irregular": "Bubble", "stretched_bubble": "Bubble",
    "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
    "foreign_matter": "Foreign Matter", "fiber": "Fiber",
    "extraneous_polymer": "Extraneous Polymer", "hema_fragment": "HEMA",
    "hema_obstruction": "HEMA Obstruction", "bubble_on_123": "Bubble On 123",
    "bubble_on_edge": "Bubble On Edge", "missing_primary_package": "Missing Primary Package",
    "package_misalignment": "Package Misalignment", "cavity_off_center": "Cavity Off Center",
    "multiple_lenses": "Multiple Lens", "folded_lens": "Folded Lens", "missing_lens": "No Lens",
    "lens_off_center": "Lens Off Center", "low_dose": "Low Dose", "dirty_strobe": "Dirty Strobe",
    "dirty_camera": "Dirty Camera", "bubble_scatter": "Bubble Scatter",
    "view_obstructed": "View Obstructed",
    "foreign_matter_micron_gate": "Foreign Matter", "fiber_micron_gate": "Fiber",
    "extraneous_polymer_micron_gate": "Extraneous Polymer", "hema_micron_gate": "HEMA",
}
GATE = {"Foreign Matter": "P3_FM_MICRON_THRESHOLD", "Fiber": "P3_FIB_MICRON_THRESHOLD",
        "Extraneous Polymer": "P3_EP_MICRON_THRESHOLD", "HEMA": "P3_HE_MICRON_THRESHOLD"}

codes = collections.defaultdict(set)
for r in rows:
    codes[r["picture_md5"]].add(r["code"])

FLIP = {r["picture_md5"] for r in mat
        if r["fiber_micron_gate"] == "1" and "P3_FIB_MICRON_THRESHOLD" not in codes[r["picture_md5"]]}
CLEAR = {r["picture_md5"] for r in mat if r["clear"] == "1"}
ELIGIBLE = {r["picture_md5"] for r in mat if r["split_eligible"] == "1"}
assert len(FLIP) == 32 and len(CLEAR) == 2156 and len(ELIGIBLE) == 6679
assert not (CLEAR & set(codes))

labels = {}
for p, cs in codes.items():
    s = {MAP[c] for c in cs}
    if p in FLIP:
        s -= {"Extraneous Polymer"}
        s |= {"Fiber"}
    labels[p] = s
for p in CLEAR:
    labels[p] = {"Clear"}

N = len(labels)
card = collections.Counter(len(v) for v in labels.values())
singles = collections.Counter(next(iter(s)) for s in labels.values() if len(s) == 1)
pairs = collections.Counter(tuple(sorted(s)) for s in labels.values() if len(s) == 2)
incl = collections.Counter()
for s in labels.values():
    if len(s) > 1:
        ss = sorted(s)
        for i, a in enumerate(ss):
            for b in ss[i + 1:]:
                incl[(a, b)] += 1
per = collections.Counter()
for s in labels.values():
    per.update(s)

# objects and sizes
objects = collections.Counter()
pics_obj = collections.defaultdict(set)
gate_pics = {c: set() for c in GATE}
for r in rows:
    if r["shape_kind"] != "box":
        continue
    cls = MAP[r["code"]]
    if r["picture_md5"] in FLIP and cls == "Extraneous Polymer":
        cls = "Fiber"
    objects[cls] += 1
    pics_obj[cls].add(r["picture_md5"])
for c, g in GATE.items():
    gate_pics[c] = {p for p, cs in codes.items() if g in cs}

W = collections.defaultdict(list)
H = collections.defaultdict(list)
for r in rows:
    if r["shape_kind"] != "box":
        continue
    cls = MAP[r["code"]]
    if r["picture_md5"] in FLIP and cls == "Extraneous Polymer":
        cls = "Fiber"
    W[cls].append(float(r["xbr"]) - float(r["xtl"]))
    H[cls].append(float(r["ybr"]) - float(r["ytl"]))


def med(xs):
    return round(statistics.median(xs), 1) if xs else "-"


# union census per class, all files, duplicates removed by picture content
name2md5 = {}
for r in csv.DictReader(open(PT, newline="", encoding="utf-8")):
    name2md5[os.path.basename(r["winning_path"])] = r["md5"]


def norm(n):
    return re.sub(r"_\d+\.\d+(?=\.bmp$)", "", n, flags=re.I)


norm2 = {}
for k, v in name2md5.items():
    norm2.setdefault(norm(k), v)

union_sets = collections.defaultdict(set)
unmatched = 0
for f in sorted(glob.glob(f"{ROOT}/data/*.xml")):
    txt = open(f, encoding="utf-8", errors="replace").read()
    for blk in txt.split("<image ")[1:]:
        n = os.path.basename(re.search(r'name="([^"]+)"', blk).group(1))
        body = blk.split("</image>")[0]
        md5 = name2md5.get(n) or norm2.get(norm(n))
        if md5 is None:
            unmatched += 1
            continue
        found = set()
        for code in re.findall(r'<(?:box|polygon)\b[^>]*\blabel="([^"]+)"', body) + \
                    re.findall(r'<tag\b[^>]*\blabel="([^"]+)"', body):
            if code in MAP:
                found.add(MAP[code])
        for cls in found:
            union_sets[cls].add(md5)

# split per class, from the frozen split
split70 = split_meta["splits"]["70_30"]
split80 = split_meta["splits"]["80_20"]
SPLIT_COLS = {
    "foreign_matter_micron_gate": "Foreign Matter size flag",
    "fiber_micron_gate": "Fiber size flag",
    "extraneous_polymer_micron_gate": "Extraneous Polymer size flag",
    "hema_micron_gate": "HEMA size flag",
    "bubble": "Bubble", "bubble_cluster": "Bubble Cluster", "wet_package": "Wet Package",
    "missing_primary_package": "Missing Primary Package", "multiple_lenses": "Multiple Lens",
    "no_lens": "No Lens", "cavity_off_center": "Cavity Off Center", "folded_lens": "Folded Lens",
    "lens_off_center": "Lens Off Center", "dirty_camera": "Dirty Camera",
    "dirty_strobe": "Dirty Strobe", "low_dose": "Low Dose", "view_obstructed": "View Obstructed",
    "package_misalignment": "Package Misalignment", "bubble_scatter": "Bubble Scatter",
    "clear": "Clear",
}

ORDER = ["Bubble", "Bubble Cluster", "Wet Package", "Foreign Matter", "Fiber",
         "Extraneous Polymer", "HEMA", "Missing Primary Package", "Multiple Lens", "No Lens",
         "Cavity Off Center", "Folded Lens", "Lens Off Center", "Dirty Camera", "Dirty Strobe",
         "Low Dose", "View Obstructed", "Package Misalignment", "Bubble Scatter",
         "HEMA Obstruction", "Bubble On 123", "Bubble On Edge", "Clear",
         "Edge Bottle-Capped", "Torn Lens", "Lens Rupture", "Surface Groove"]
EMPTY_TAGS = {"Edge Bottle-Capped", "Torn Lens", "Lens Rupture"}
EMPTY_BOX = {"Surface Groove"}

DEB = ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"]
deb_union = {p for p, s in labels.items() if s & set(DEB)}
deb_multi = sum(1 for p in deb_union if len(labels[p] & set(DEB)) > 1)
deb_gate = sum(1 for p in deb_union if any(GATE[c] in codes[p] for c in DEB))

S_MPP = "Missing Primary Package"
standalone = []
for tag in ["Missing Primary Package", "Package Misalignment", "Cavity Off Center", "View Obstructed"]:
    n = per[tag]
    extra = sum(1 for s in labels.values() if tag in s and len(s) > 1)
    standalone.append((tag, n, extra))

# hand checks
assert N == 6938 and dict(card) == {1: 5531, 2: 649, 3: 418, 4: 199, 5: 97, 6: 29, 7: 12, 8: 3}
assert len(pairs) == 28 and sum(pairs.values()) == 649
assert len(incl) == 83
assert per["Fiber"] == 210 and per["Extraneous Polymer"] == 112 and per["Clear"] == 2156
assert per["Bubble Cluster"] == 428
assert objects["Bubble"] == 11045 and objects["HEMA"] == 103 and objects["Fiber"] == 277
assert len(standalone) == 4 and all(x[2] == 0 for x in standalone)

sheets = []

# ------------------------------------------------------------------ summary
s = [s_title("Defect and image-quality analysis")]
s += [s_sub("Draft 2 annotation guide. Rebuilt from the annotations on 2026-10-26; supersedes the "
            "23 October workbook.")]
s += [[], s_section(["Population", "Pictures"])]
s += [["Pictures examined", s_num(10614)], ["Pictures in an annotation (the analysed set)", s_num(N)],
      ["  of which carry a mark", s_num(len(codes))],
      ["  of which have nothing marked (Clear)", s_num(len(CLEAR))]]
s += [[], s_section(["Training and test split", "Train / test pictures"])]
c70, c80 = split70["split_counts"], split80["split_counts"]
s += [["70 / 30", f"{c70.get('train', 0):,} / {c70.get('test', 0):,}"],
      ["80 / 20", f"{c80.get('train', 0):,} / {c80.get('test', 0):,}"]]
s += [[], s_section(["Label", "Kind", "Pictures carrying it", "Share of the analysed set"])]
for name in sorted(ORDER, key=lambda x: -per[x]):
    if name == "Clear":
        kind = "Clear"
    elif name in EMPTY_TAGS:
        kind = "Whole-image tag, no examples yet"
    elif name in EMPTY_BOX:
        kind = "Object class, no examples yet"
    elif name in ("Bubble On 123", "Bubble On Edge"):
        kind = "Object class, reference only"
    elif name == "HEMA Obstruction":
        kind = "Whole-image tag, reference only"
    elif name in DEB or name in ("Bubble", "Bubble Cluster", "Wet Package"):
        kind = "Object class"
    else:
        kind = "Whole-image tag"
    s.append([name, kind, s_num(per[name]), s_share(per[name] / N)])
s += [s_note("Rows are not additive: a picture can carry several labels.")]
s += [s_note("No picture is unlabelled. A picture with nothing marked is Clear, and Clear is a label; "
             "the 2,156 Clear pictures are 31 percent of the analysed set.")]
s += [s_note("Four classes in the guide have no examples yet, so they show zero above: Edge Bottle-Capped, "
             "Torn Lens and Lens Rupture are tags, Surface Groove is an object class. They are listed so the "
             "guide's full class list is visible.")]
s += [s_note("A size flag is a subset of its class, not a label: a picture with a large object still "
             "carries one class label for it.")]
sheets.append({"name": "Summary", "rows": s, "freeze_panes": "A4",
               "column_widths": {"A": 56, "B": 30, "C": 14, "D": 22}})

# ------------------------------------------------------------------ LP summary
lp = [s_title("Whole-image tags")]
lp += [s_sub("Pictures carrying each tag, its share of the analysed set, and how many of those pictures "
             "can enter the split.")]
lp += [s_header(["Tag", "Guide code", "Pictures carrying it", "Share of the analysed set",
                 "In the split set (70/30)", "In the split set (80/20)", "Notes"])]
TAGS = ["Missing Primary Package", "Package Misalignment", "Cavity Off Center", "View Obstructed",
        "No Lens", "Multiple Lens", "Folded Lens", "Lens Off Center", "Low Dose", "Dirty Strobe",
        "Dirty Camera", "Bubble Scatter", "HEMA Obstruction",
        "Edge Bottle-Capped", "Torn Lens", "Lens Rupture"]
TCODE = {"Missing Primary Package": "P1_MPP", "Package Misalignment": "P1_PPM",
         "Cavity Off Center": "P1_COC", "View Obstructed": "F2_FOV", "No Lens": "P1_NL",
         "Multiple Lens": "P1_ML", "Folded Lens": "P1_FL", "Lens Off Center": "P2_LOC",
         "Low Dose": "P2_LD", "Dirty Strobe": "P2_DS", "Dirty Camera": "P2_DC",
         "Bubble Scatter": "P2_BSC", "Edge Bottle-Capped": "P1_EBC", "Torn Lens": "P1_TL",
         "Lens Rupture": "P1_LR", "HEMA Obstruction": "P2_HMO"}
TNOTE = {
    "Missing Primary Package": "Standalone: no other label applies",
    "Package Misalignment": "Standalone; rarest class",
    "Cavity Off Center": "Standalone",
    "View Obstructed": "Standalone",
    "No Lens": "Mostly alone; 4 with Dirty Camera",
    "Multiple Lens": "Mostly combined",
    "Folded Lens": "Never alone; carries Multiple Lens",
    "Lens Off Center": "Mostly combined",
    "Low Dose": "Mostly alone",
    "Dirty Strobe": "Mostly alone; 2 combined",
    "Dirty Camera": "Mostly combined",
    "Bubble Scatter": "5 alone, 1 with Lens Off Center",
    "HEMA Obstruction": "Kept for reference, not in the current class list",
    "Edge Bottle-Capped": "No examples yet; the class is defined in the guide",
    "Torn Lens": "No examples yet; the class is defined in the guide",
    "Lens Rupture": "No examples yet; the class is defined in the guide",
}
for t in TAGS:
    lp.append([t, TCODE[t], s_num(per[t]), s_share(per[t] / N),
               s_num(sum(1 for p in ELIGIBLE if t in labels[p])),
               s_num(sum(1 for p in ELIGIBLE if t in labels[p])), TNOTE[t]])
lp += [s_total(["Total tag pictures (a picture can carry several tags)", "",
                s_num(sum(per[t] for t in TAGS)), s_share(sum(per[t] for t in TAGS) / N), "", "", ""])]
lp += [s_note("The split set holds the pictures that can enter the split; the same 6,679 pictures are "
              "available to both ratios, which is why the two columns agree.")]
sheets.append({"name": "LP Summary", "rows": lp, "freeze_panes": "A4",
               "column_widths": {"A": 30, "B": 12, "C": 18, "D": 20, "E": 20, "F": 20, "G": 40}})

# ------------------------------------------------------------------ tag combinations
tc = [s_title("Labels on a picture and their combinations")]
tc += [s_sub("Counted from the annotation. A label is an object class, a whole-image tag, or Clear. A "
             "size flag is not a label; it is a subset of its class.")]
tc += [[], s_section(["Table 1 - Exact pairs"]), ]
tc += [s_sub("The picture's complete label set is exactly that pair, nothing else.")]
tc += [s_header(["#", "Label pair", "Pictures", "Share of two-label pictures"])]
for i, (pr, n) in enumerate(pairs.most_common(), start=1):
    tc.append([C(i), " + ".join(pr), s_num(n), s_share(n / sum(pairs.values()))])
tc += [s_total(["", "Total two-label pictures", s_num(sum(pairs.values())), s_share(1.0)])]
tc += [[], s_section(["Table 2 - Inclusive pairs"])]
tc += [s_sub("The picture carries both labels; any further labels in addition are allowed.")]
tc += [s_header(["#", "Label pair", "Pictures", "Share of the smaller class"])]
for i, (pr, n) in enumerate(incl.most_common(), start=1):
    smaller = min(per[pr[0]], per[pr[1]])
    tc.append([C(i), " + ".join(pr), s_num(n), s_share(n / smaller)])
tc += [s_note(f"{len(incl)} distinct pairs occur at least once. A pair of rare labels can look common in "
              "this table because the rest of the picture is free; read it beside Table 1.")]
tc += [[], s_section(["How many labels one picture carries"])]
tc += [s_header(["Labels on the picture", "Pictures", "Share of the analysed set"])]
for k in range(1, 9):
    tc.append([s_num(k), s_num(card.get(k, 0)), s_share(card.get(k, 0) / N)])
tc += [s_total(["Total", s_num(N), s_share(1.0)])]
tc += [s_note("No picture carries zero labels: the four object classes have their own column here, and a "
              "picture whose only mark is such an object carries that class as its label.")]
tc += [s_note("2 or more labels on 1,407 pictures means the tag model must be multi-label.")]
sheets.append({"name": "Tag Combinations", "rows": tc, "freeze_panes": "A4",
               "column_widths": {"A": 7, "B": 56, "C": 12, "D": 26}})

# ------------------------------------------------------------------ OOI summary
oo = [s_title("Object classes")]
oo += [s_sub("Pictures carrying each object class, the share over the size threshold, the objects marked, "
             "and the typical object size in pixels. Sizes are the median over every object of the class, "
             "including the objects that carry an older plain class name.")]
oo += [s_header(["Object class", "Guide code", "Pictures carrying the class",
                 "Of which over the size threshold", "Objects marked", "Typical width (px)",
                 "Typical height (px)", "Notes"])]
for cls, code in [("Bubble", "P2_BB"), ("Bubble Cluster", "P2_BC"), ("Wet Package", "P2_WP"),
                  ("Foreign Matter", "P3_FM"), ("Fiber", "P3_FIB"),
                  ("Extraneous Polymer", "P3_EP"), ("HEMA", "P3_HE"),
                  ("Surface Groove", "P1_SG")]:
    g = len(gate_pics.get(cls, ())) if cls in GATE else None
    oo.append([cls, code, s_num(per[cls]), s_num(g) if g is not None else C("-"),
               s_num(objects[cls]), s_dec(med(W[cls])), s_dec(med(H[cls])),
               "32 objects the newer annotation calls Extraneous Polymer keep the earlier Fiber name here"
               if cls == "Fiber" else
               ("The same 32 objects sit under Fiber above" if cls == "Extraneous Polymer" else
                ("No examples yet; the class is defined in the guide" if cls == "Surface Groove" else ""))])
oo += [s_total(["Total objects, the eight object classes", "",
                s_num(len(set().union(*pics_obj.values()))), "",
                s_num(sum(objects[c] for c in ["Bubble", "Bubble Cluster", "Wet Package", "Foreign Matter",
                                               "Fiber", "Extraneous Polymer", "HEMA"])), "", "", ""])]
oo += [[], s_section(["Older names kept for reference (not in the current class list)"])]
oo += [s_header(["Name", "Code", "Pictures", "Objects marked", "Typical width (px)", "Typical height (px)",
                 "Note", ""])]
for name, code, note in [("Bubble On 123", "", "Library only, no current code"),
                         ("Bubble On Edge", "", "Library only, no current code"),
                         ("HEMA Obstruction", "P2_HMO", "Whole-image tag, not an object class")]:
    if name == "HEMA Obstruction":
        oo.append([name, code, s_num(per[name]), C("-"), C("-"), C("-"), note, ""])
    else:
        oo.append([name, code, s_num(per[name]), s_num(objects[name]),
                   s_dec(med(W[name])), s_dec(med(H[name])), note, ""])
oo += [s_note("Bubble is one class: Bubble Irregular and Stretched Bubble fold into it, and the older "
              "library's plain Bubble name folds in too. Every such picture also carries the Bubble mark.")]
oo += [s_note("HEMA is 103 objects on 101 pictures: 95 production objects, 4 objects in one later file and "
              "4 in the older library under the HEMA Fragment name.")]
sheets.append({"name": "OOI Summary", "rows": oo, "freeze_panes": "A4",
               "column_widths": {"A": 26, "B": 10, "C": 22, "D": 24, "E": 14, "F": 16, "G": 16, "H": 62}})

# ------------------------------------------------------------------ standalone
st = [s_title("Standalone tags")]
st += [s_sub("Tags the guide says cannot share a picture with anything else. Checked against every label, "
             "object classes included.")]
st += [s_header(["Standalone tag", "Pictures tagged", "Pictures carrying any other label", "Status"])]
for tag, n, extra in standalone:
    st.append([tag, s_num(n), s_num(extra),
               "Follows the guide: no other label on these pictures" if extra == 0
               else "VIOLATION: see note"])
st += [s_note("Checked on the annotation, so an object class counts as an extra label. All four tags keep "
              "zero violations.")]
sheets.append({"name": "Standalone Tags", "rows": st, "freeze_panes": "A4",
               "column_widths": {"A": 34, "B": 16, "C": 30, "D": 54}})

# ------------------------------------------------------------------ confusion
def both(a, b):
    return sum(1 for s in labels.values() if a in s and b in s)


cr = [s_title("Confusion risks")]
cr += [s_sub("Class pairs that look alike, how to tell them apart, and how many pictures carry both.")]
cr += [s_header(["Class", "Can look like", "How to tell them apart", "Guide section", "Pictures with both"])]
cr += [
    ["Cavity Off Center", f"Package Misalignment ({per['Package Misalignment']})",
     "Off-centre image with the package correctly seated = Cavity Off Center", "4.3",
     s_num(both("Cavity Off Center", "Package Misalignment"))],
    [f"Lens Off Center ({per['Lens Off Center']})", f"Low Dose ({per['Low Dose']})",
     "If the cause is too little solution it is Low Dose; a real shift in a full cavity is Lens Off Center",
     "4.5, 4.15", s_num(both("Lens Off Center", "Low Dose"))],
    [f"Wet Package ({per['Wet Package']})", f"Bubble ({per['Bubble']})",
     "Wet package marks look like bubbles but are liquid: gradual brightness, no sharp rim", "5.2",
     s_num(both("Wet Package", "Bubble"))],
    ["Extraneous Polymer", "Fiber",
     "Mixed shapes (a strand with a clump) are recorded as Fiber; Extraneous Polymer is for a confident "
     "polymer sheet or fragment. 32 objects were renamed between the two, and keep the earlier Fiber name "
     "in this workbook", "5.4B", s_num(both("Extraneous Polymer", "Fiber"))],
    [f"Bubble Scatter ({per['Bubble Scatter']})", "Bubble / Bubble Cluster",
     "Scatter is a whole-picture tag for many small bubbles spread widely; single bubbles are boxed",
     "4.14, 5.1B", s_num(both("Bubble Scatter", "Bubble"))],
    [f"Dirty Strobe ({per['Dirty Strobe']})", f"Dirty Camera ({per['Dirty Camera']})",
     "Strobe marks are soft and blurred; camera marks are sharp spots", "4.12, 4.13",
     s_num(both("Dirty Strobe", "Dirty Camera"))],
    [f"No Lens ({per['No Lens']})", "any lens condition",
     "No Lens needs a valid package and confidence that no lens is present", "4.6",
     s_num(both("No Lens", "Multiple Lens"))],
    [f"Multiple Lens ({per['Multiple Lens']})", f"Folded Lens ({per['Folded Lens']})",
     "Not a conflict: a folded lens in a multi-lens picture carries both tags", "4.7, 4.8",
     s_num(both("Multiple Lens", "Folded Lens"))],
]
cr += [[], s_section(["Features that look like defects but are not annotated"])]
cr += [["Package marks (fiber-like marks that repeat in the same place)", "Fiber, Foreign Matter",
        "Not annotated. A model will still see them, so they limit achievable precision.", "3.1", ""],
       ["Crater-like bubble artifacts (rings from collapsed bubbles)", "Wet Package, Fiber, Extraneous Polymer, Foreign Matter",
        "Not annotated. They resemble wet-package and debris marks.", "3.2", ""]]
cr += [s_note("The number in brackets after a class is how many pictures carry that class, from the "
              "Summary sheet. The last column counts the pictures carrying both classes; a zero means "
              "the two never appear on the same picture.")]
sheets.append({"name": "Confusion Risks", "rows": cr, "freeze_panes": "A4",
               "column_widths": {"A": 30, "B": 30, "C": 76, "D": 14, "E": 16}})

# ------------------------------------------------------------------ earlier vs current
ec = [s_title("The same label counted at each stage")]
ec += [s_sub("Union census counts a picture once if any annotation file marks it, duplicate copies removed. "
             "Resolved keeps one annotation of record per picture. The analysed set is that resolution over "
             "every picture in an annotation. The split set is the part that can enter the split.")]
ec += [s_header(["Label", "Union census", "Resolved", "Analysed set", "In split set (split positive)"])]
for name in sorted(ORDER, key=lambda x: -per[x]):
    ec.append([name, s_num(len(union_sets.get(name, ()))) if name != "Clear" else C("-"),
               s_num(per[name]) if name != "Clear" else C("-"), s_num(per[name]),
               s_num(sum(1 for p in ELIGIBLE if name in labels[p]))])
ec += [[], s_section(["Size flags (inside their class, not labels)"])]
ec += [s_header(["Flag", "Union census", "Resolved", "Analysed set", "Split set"])]
for cls in ["Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"]:
    ec.append([cls + " size flag",
               s_num(len(union_sets.get(cls, ()))) if False else C("-"),
               s_num(len(gate_pics[cls])), s_num(len(gate_pics[cls])),
               s_num(sum(1 for p in ELIGIBLE if GATE[cls] in codes[p]))])
ec += [s_note("26 annotation entries, all in the older library file, could not be matched to a picture "
              "row, so the union column can read one or two below the resolved column. The resolved and "
              "analysed columns are the counts of record.")]
ec += [s_note("The split set for the four object classes holds the pictures carrying the size flag, because "
              "the split treats the flag as the positive for those classes. The training label list carries "
              "32 pictures in the Fiber flag that the annotation records as Extraneous Polymer.")]
sheets.append({"name": "Earlier vs Current", "rows": ec, "freeze_panes": "A4",
               "column_widths": {"A": 34, "B": 16, "C": 14, "D": 16, "E": 14}})

# ------------------------------------------------------------------ split
sp = [s_title("Training and test split - both ratios, same recipe and seed")]
sp += [s_sub("This sheet reproduces the frozen split. Rows for the four object classes count pictures "
             "carrying the size flag, which is the positive the split uses for those classes.")]
for label, meta in [("70% training / 30% test", split70), ("80% training / 20% test", split80)]:
    sp += [[], s_section([label])]
    sp += [s_header(["Class", "Training pictures", "Test pictures", "Total", "Note"])]
    counts = meta["split_counts"]
    for col, pretty in SPLIT_COLS.items():
        pc = meta["per_class"].get(col)
        if pc is None:
            continue
        tr, te = pc.get("train", 0), pc.get("test", 0)
        note = "Split positives = pictures carrying the size flag" if col.endswith("micron_gate") else ""
        sp.append([pretty, s_num(tr), s_num(te), s_num(tr + te), note])
    sp += [s_total(["Total pictures", s_num(counts.get("train", 0)), s_num(counts.get("test", 0)),
                    s_num(counts.get("train", 0) + counts.get("test", 0)),
                    "Content groups never cross the split"])]
sp += [s_note("Only the Draft 2 codes and Clear are positives. 105 pictures whose only marks are HEMA "
              "Obstruction, Bubble On 123 or Bubble On Edge are left out, so the split covers 6,574 pictures "
              "out of the 6,679 that can otherwise enter.")]
sheets.append({"name": "Training and Test Split", "rows": sp, "freeze_panes": "A4",
               "column_widths": {"A": 32, "B": 18, "C": 16, "D": 12, "E": 48}})

# ------------------------------------------------------------------ definitions
df = [s_title("Definitions")]
df += [s_header(["Term", "Meaning"])]
for t, m in [
    ("Picture examined", "Every distinct image in the library, counted once."),
    ("Analysed set", "The 6,938 pictures that carry an annotation entry."),
    ("Label", "One class present on a picture: an object class, a whole-image tag, or Clear."),
    ("Object class", "The class of a marked object: Bubble, Bubble Cluster, Wet Package, Foreign Matter, "
                     "Fiber, Extraneous Polymer, HEMA."),
    ("Whole-image tag", "One tag on the picture, not on an object."),
    ("Size flag", "The micron threshold tag on an object. It marks an object over the size threshold and "
                  "sits inside its class; it is not a label."),
    ("Clear", "A picture with nothing marked. It counts as one label."),
    ("Debris group", "The four object classes together: Foreign Matter, Fiber, Extraneous Polymer, HEMA. "
                     "A group, not a class in the guide."),
    ("Union census", "A picture counted once if any annotation file marks it, duplicate copies removed."),
    ("Resolved", "One annotation of record per picture; older annotations of the same picture ignored."),
    ("Split set", "The pictures that enter the training and test split."),
    ("Exact pair", "The picture's complete label set is exactly those two labels."),
    ("Inclusive pair", "The picture carries both labels and may carry others."),
]:
    df.append([t, m])
sheets.append({"name": "Definitions", "rows": df, "freeze_panes": "A4",
               "column_widths": {"A": 26, "B": 100}})


# ------------------------------------------------------------------ render
def render(spec, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    wb.remove(wb.active)
    for sh in spec:
        ws = wb.create_sheet(sh["name"])
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
        for col, w in sh.get("column_widths", {}).items():
            ws.column_dimensions[col].width = w
        if sh.get("freeze_panes"):
            ws.freeze_panes = sh["freeze_panes"]
        ws.sheet_view.showGridLines = False
    wb.save(path)


if __name__ == "__main__":
    with open(SPEC, "w", encoding="utf-8") as f:
        json.dump(sheets, f, indent=1)
    render(sheets, OUT)
    print("written:", OUT)
    print("sheets:", [x["name"] for x in sheets])
    print("labels per picture:", dict(sorted(card.items())))
    print("exact pairs", len(pairs), sum(pairs.values()), "| inclusive pairs", len(incl))
    print("objects:", dict(objects))
    print("debris", len(deb_union), "multi", deb_multi, "gated", deb_gate)
    print("unmatched census names:", unmatched)
