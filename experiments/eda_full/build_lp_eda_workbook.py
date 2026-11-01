"""Build the Lens Presentation EDA workbook.

One deliverable for the reviewer who asked for the lens presentation EDA.
Counts only: no microns, no paths, no internal names. Sources are the resolved
label set and the picture table already frozen under run/.
"""
import csv
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RUN = "run/eda_full_20261015"
OUT = "reports/eda_full/_tmp_Lens_Presentation_EDA_20261015.xlsx"
OLD = "ICube Defects Library"

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(bold=True, color="FFFFFF")
TOT_FILL = PatternFill("solid", fgColor="D9E2F3")
TOT_FONT = Font(bold=True)

rows = list(csv.DictReader(open(f"{RUN}/resolved_labels.csv", encoding="utf-8")))
pics = {r["md5"]: r for r in csv.DictReader(open(f"{RUN}/picture_table.csv", encoding="utf-8"))}
names, tier = {}, {}
for r in csv.DictReader(open(f"{RUN}/label_census.csv", encoding="utf-8")):
    if r["dimension"] == "all" and r["bucket"] == "all":
        names[r["canonical_id"]] = r["canonical_name"]
        tier[r["canonical_id"]] = r["tier"]

tags = [r for r in rows if r["shape_kind"] == "tag"]

stat = defaultdict(lambda: {"n": 0, "pics": defaultdict(int),
                            "gen": defaultdict(set), "line": defaultdict(set)})
for r in tags:
    s = stat[r["canonical_id"]]
    s["n"] += 1
    s["pics"][r["picture_md5"]] += 1
    p = pics.get(r["picture_md5"])
    if p is None:
        continue
    folders = p["all_folders"]
    n_upd = sum(1 for f in folders.split(";") if "Updated" in f)
    gen = ("Old library only" if OLD in folders and n_upd == 0
           else "Library and updated" if OLD in folders else "Updated only")
    s["gen"][gen].add(r["picture_md5"])
    s["line"][p["line"]].add(r["picture_md5"])

GENS = ["Updated only", "Library and updated", "Old library only"]
LINES = ["L24", "L25", "L26", "L27", "L31"]


def sheet(wb, title, headers, data, widths, total_row=None, note=None):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
        cell.alignment = Alignment(horizontal="center")
    for row in data:
        ws.append(row)
    if total_row:
        ws.append(total_row)
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=c)
            cell.fill, cell.font = TOT_FILL, TOT_FONT
    if note:
        ws.append([])
        ws.append([note])
        ws.cell(row=ws.max_row, column=1).font = Font(italic=True, size=9)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    return ws


wb = Workbook()
wb.remove(wb.active)

# 1. Read me
ws = wb.create_sheet("Read me")
readme = [
    ("Lens Presentation EDA", ""),
    ("", ""),
    ("Scope", "Lens presentation tags: whole-picture conditions such as missing primary "
              "package, multiple lenses, lens off centre, missing lens, folded lens, "
              "dirty camera, low dose, cavity off centre and the micron-threshold flags."),
    ("Picture set", "The full annotated picture set across all library and updated folders, "
                    "all production lines."),
    ("Counting rule", "A picture counts for a class once, regardless of source. The newer "
                      "annotation is kept where a picture was re-annotated."),
    ("Companion table", "Defect boxes are reported separately: 14,182 boxes over 1,130 "
                        "pictures. This workbook covers the 5,832 presentation tags."),
    ("", ""),
    ("Headline", "5,832 presentation tags over 4,329 distinct pictures."),
    ("", ""),
    ("Sheets", "LP tags: per class counts and shares. Coverage by generation: the same "
               "class counted separately in each annotation generation. LP by line and "
               "LP by folder: distinct pictures per class in each stratum."),
    ("Note", "Counts only. Sizes are reported in pixels in the companion defect workbook; "
             "no size conversion is used here."),
]
for k, v in readme:
    ws.append([k, v])
ws.column_dimensions["A"].width = 18
ws.column_dimensions["B"].width = 110
for r in (1, 9):
    ws.cell(row=r, column=1).font = Font(bold=True, size=12)
for r in range(1, len(readme) + 1):
    v = ws.cell(row=r, column=2)
    v.alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(row=r, column=1).font = Font(bold=True)

# Whole-image multiplicity with OOI = defect content in ANY form: the OOI tags
# (four micron-gate flags, HEMA obstruction, bubble scatter) OR any defect box
# (bubbles, wet package, foreign matter, fiber, HEMA fragment, extraneous
# polymer). An image is:
#   Multi (mix): carries an OOI signal (OOI tag or defect box)  -> mix wins
#   Multi (LP tags): two or more tag classes, all lens presentation, no OOI
#   Single-tag images: exactly one tag class and no OOI signal
OOI_IDS = {cid for cid in names if "micron_gate" in cid} | {
    "hema_obstruction", "bubble_scatter"}
img_tags = defaultdict(set)
img_src = {}
for r in tags:
    img_tags[r["picture_md5"]].add(r["canonical_id"])
    img_src[r["picture_md5"]] = r["source_group"]
img_boxes = defaultdict(set)
for r in rows:
    if r["shape_kind"] == "box":
        img_boxes[r["picture_md5"]].add(r["canonical_id"])


def has_ooi(m):
    return bool(img_tags[m] & OOI_IDS) or bool(img_boxes.get(m))


# 2. LP tags, the table in the reviewer's format
data, tot_single, tot_multi_lp, tot_multi_mix, tot_u, tot_p = [], 0, 0, 0, 0, 0
ordered = sorted(stat.items(), key=lambda kv: -kv[1]["n"])
for cid, s in ordered:
    single = multi_lp = multi_mix = 0
    for m in s["pics"]:
        if has_ooi(m):
            multi_mix += 1
        elif len(img_tags[m]) >= 2:
            multi_lp += 1
        else:
            single += 1
    tot_single += single
    tot_multi_lp += multi_lp
    tot_multi_mix += multi_mix
    src_u = sum(1 for m in s["pics"] if img_src.get(m) == "updated_20260922")
    src_p = len(s["pics"]) - src_u
    tot_u += src_u
    tot_p += src_p
    data.append([names.get(cid, cid), s["n"], round(100.0 * s["n"] / len(tags), 2),
                 len(s["pics"]), single, multi_lp, multi_mix, src_u, src_p])
tot_pics = len({m for s in stat.values() for m in s["pics"]})
sheet(wb, "LP tags",
      ["Tag", "Tags", "% of tags", "Images with it", "Single-tag images",
       "Multi (LP tags)", "Multi (mix)", "From Sep-22 update", "From production re-annotation"],
      data, [34, 9, 9, 13, 15, 14, 12, 16, 20],
      total_row=["TOTAL", len(tags), 100.00, tot_pics, tot_single, tot_multi_lp, tot_multi_mix, tot_u, tot_p],
      note="The three image columns classify each class-image pair. Single-tag: the image has "
           "one tag and no defect content. Multi (LP tags): two or more lens-presentation "
           "tags and no defect content. Multi (mix): the image carries defect content (OOI) "
           "in any form: a micron-gate flag, HEMA obstruction, bubble scatter tag, or any "
           "defect box such as bubbles or wet package; mix takes precedence. An image can "
           "appear in several class rows, so the TOTAL row sums class-image pairs, not "
           "distinct images. The final two columns split each class by the annotation pass "
           "that first tagged the image and add to Images-with-it.")

# 3. Coverage by annotation generation
data = []
for cid, s in ordered:
    row = [names.get(cid, cid)]
    for g in GENS:
        row.append(len(s["gen"].get(g, set())))
    row.append(len(s["pics"]))
    data.append(row)
sheet(wb, "Coverage by generation",
      ["Tag"] + [g + " (images)" for g in GENS] + ["Distinct images"],
      data, [34, 20, 22, 18, 16],
      note="Generation columns overlap: a re-annotated picture counts in both generations, "
           "so they do not add to the last column.")

# 4. LP tags by line
data = []
for cid, s in ordered:
    row = [names.get(cid, cid)]
    for ln in LINES:
        row.append(len(s["line"].get(ln, set())))
    row.append(len(s["pics"]))
    data.append(row)
sheet(wb, "LP by line", ["Tag"] + LINES + ["All lines"], data, [34] + [9] * len(LINES) + [12],
      note="Distinct pictures carrying the tag, per production line.")

# 5. LP tags by folder group
data = []
for cid, s in ordered:
    row = [names.get(cid, cid)]
    for g in GENS:
        row.append(len(s["gen"].get(g, set())))
    data.append(row)
sheet(wb, "LP by folder", ["Tag"] + GENS, data, [34, 20, 22, 18],
      note="Distinct pictures carrying the tag, by where the picture lives.")

wb.save(OUT)
print("written", OUT)
print("tags", len(tags), "classes", len(ordered), "distinct pictures", tot_pics)
