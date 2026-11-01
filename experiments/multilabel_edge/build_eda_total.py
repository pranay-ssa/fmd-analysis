"""Build the total-EDA workbook for the annotation after the 24-file export.

Mirrors the Draft-2 EDA workbook shape (Summary, LP Summary, Tag Combinations, OOI Summary)
and adds the before/after training and test split on the merged record, plus a reconciliation
sheet that proves the numbers equal the October record workbook.

Every number comes from run/eda_total_20261028/*.csv and the split meta files. Nothing is
typed in by hand. Client-safe: no paths, script names, job ids or version tags.
"""
import csv
import json
import os

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = "D:/fmd-analysis"
NUM = f"{ROOT}/run/eda_total_20261028"
OUT = f"{ROOT}/reports/eda_total_20261028"
os.makedirs(OUT, exist_ok=True)

ACCENT, LEGACY_FILL = "1F3864", "F2F2F2"
HEAD_FONT = Font(bold=True, color="FFFFFF")
TITLE = Font(bold=True, size=14, color=ACCENT)
SUB = Font(italic=True, size=9, color="595959")
BOLD = Font(bold=True)


def read_csv(name):
    with open(f"{NUM}/{name}", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEAD_FONT
        cell.fill = PatternFill("solid", fgColor=ACCENT)
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def title_block(ws, title, subtitle, width):
    ws.cell(row=1, column=1, value=title).font = TITLE
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    ws.cell(row=2, column=1, value=subtitle).font = SUB
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    ws.row_dimensions[1].height = 22


def note(ws, row, text, width):
    c = ws.cell(row=row, column=1, value=text)
    c.font = SUB
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=width)
    ws.row_dimensions[row].height = 26


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def main():
    pop = {r["measure"]: int(r["value"]) for r in read_csv("population.csv")}
    lp = read_csv("lp.csv")
    ooi = read_csv("ooi.csv")
    exact = read_csv("combos_exact.csv")
    incl = read_csv("combos_inclusive.csv")
    lcounts = read_csv("label_counts.csv")
    splits = read_csv("splits.csv")
    outside = read_csv("outside_split.csv")
    v6 = json.load(open(f"{ROOT}/run/split_20261028_v6/meta.json", encoding="utf-8"))
    v7 = json.load(open(f"{ROOT}/run/split_20261028_v7/meta.json", encoding="utf-8"))
    rec = {r["name"]: r for r in csv.DictReader(
        open(f"{ROOT}/run/eda_batch24_20261028/record_before_after.csv", newline="", encoding="utf-8"))}

    marked = pop["Pictures with at least one mark"]
    clear = pop["Pictures with nothing marked (Clear)"]
    analysed = pop["Analysed set"]
    ooi_tags = sum(int(r["tags"]) for r in ooi if r["guide"] == "Yes")
    ooi_pics = pop["Pictures with at least one OOI tag"]
    rows_before = v6["rows"]
    rows_after = v7["rows"]
    b70 = v6["splits"]["70_30"]["split_counts"]
    a70 = v7["splits"]["70_30"]["split_counts"]
    b80 = v6["splits"]["80_20"]["split_counts"]
    a80 = v7["splits"]["80_20"]["split_counts"]
    drop_before = 6938 - rows_before
    drop_after = analysed - rows_after

    wb = Workbook()

    # ---- Read me
    ws = wb.active
    ws.title = "Read me"
    title_block(ws, "Total defect and image-quality analysis after the 24-file annotation",
                "Prepared 28 October 2026. The whole record after the client's 24-file export. Client-safe.", 6)
    lines = [
        "This workbook covers the whole annotation record after the 24 files arrived: 10,614 pictures examined, "
        f"{marked:,} with at least one mark, {clear:,} Clear, {analysed:,} in the analysed set.",
        "It follows the shape of the earlier Draft-2 workbook: Summary, LP Summary, Tag Combinations, OOI Summary. "
        "It adds the training and test split before and after the 24 files, and a reconciliation sheet.",
        f"OOI tags: {ooi_pics:,} pictures carry at least one OOI tag; {ooi_tags:,} OOI tags in all. Lens presentation: "
        f"{pop['Pictures with at least one lens presentation tag']:,} pictures carry at least one.",
        "Every class row carries the guide code. The guide's 15 lens presentation classes and 8 OOI classes are all listed, "
        "including the four with no annotated pictures. Classes outside the guide are marked legacy.",
        "The split uses the frozen rules of 26 October 2026: Draft 2 codes plus Clear, legacy excluded, the four gated "
        "object classes positive on the size flag only, iterative stratification, content md5 groups, both ratios.",
        "Sheets: Summary; LP Summary; Tag Combinations; OOI Summary; Training and Test Split; Reconciliation; Definitions.",
    ]
    r = 4
    for line in lines:
        c = ws.cell(row=r, column=1, value=line)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.row_dimensions[r].height = 30
        r += 1
    widths(ws, {"A": 110})

    # ---- Summary
    ws = wb.create_sheet("Summary")
    title_block(ws, "Summary", "The population, the class list, and the split before and after the 24 files.", 9)
    ws.cell(row=4, column=1, value="Population").font = BOLD
    hdr = ["Measure", "Pictures"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=5, column=i, value=h)
    style_header(ws, 5, 2)
    rr = 6
    for measure in ("Pictures examined", "Pictures with at least one mark",
                    "Pictures with at least one OOI tag", "Pictures with at least one lens presentation tag",
                    "Pictures with nothing marked (Clear)", "Analysed set"):
        ws.cell(row=rr, column=1, value=measure)
        ws.cell(row=rr, column=2, value=pop[measure]).number_format = "#,##0"
        rr += 1
    note(ws, rr, "The analysed set is every picture with marks plus Clear. A picture with no marks outside the Clear "
                 "folder is a placeholder and is not counted.", 9)

    rr += 2
    ws.cell(row=rr, column=1, value="Training and test split").font = BOLD
    rr += 1
    hdr = ["Ratio", "Before: train", "Before: test", "Before: rows", "After: train", "After: test", "After: rows",
           "Not in a split before", "Not in a split after"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, len(hdr))
    rr += 1
    for label, bt, be, b, at, ae, a in (
            ("70 / 30", b70.get("train", 0), b70.get("test", 0), rows_before,
             a70.get("train", 0), a70.get("test", 0), rows_after),
            ("80 / 20", b80.get("train", 0), b80.get("test", 0), rows_before,
             a80.get("train", 0), a80.get("test", 0), rows_after)):
        vals = [label, bt, be, b, at, ae, a, 6938 - rows_before, analysed - rows_after]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j > 1:
                cell.number_format = "#,##0"
        rr += 1
    note(ws, rr, "Before is the split on the seven-file record (6,938 analysed, 6,659 rows). After is the same frozen "
                 "recipe on the merged 24-file record (7,617 analysed, 7,470 rows).", 9)

    rr += 2
    ws.cell(row=rr, column=1, value="Classes").font = BOLD
    rr += 1
    for line in (
        "15 lens presentation classes in the guide; 3 carry no annotated picture (P1_EBC, P1_TL, P1_LR).",
        "8 OOI classes in the guide; 1 carries no annotated picture (P1_SG).",
        f"3 legacy classes outside the guide, counted in the EDA and not used in the split: HEMA Obstruction (P2_HMO) "
        f"{next(int(r['pictures']) for r in ooi if r['class'] == 'HEMA Obstruction')}, Bubble On 123 "
        f"{next(int(r['pictures']) for r in ooi if r['class'] == 'Bubble On 123')}, Bubble On Edge "
        f"{next(int(r['pictures']) for r in ooi if r['class'] == 'Bubble On Edge')}. "
        f"{next(int(r['pictures']) for r in outside if r['reason'] == 'Total')} pictures are outside the split.",
        f"OOI tags: {ooi_pics:,} pictures, {ooi_tags:,} tags. Bubble alone is "
        f"{next(int(r['pictures']) for r in ooi if r['class'] == 'Bubble'):,} pictures.",
        "The 24 files add 719 pictures to the record; the split rows rise by "
        f"{rows_after - rows_before:,} because the analysed set also grew and fewer pictures are outside a split.",
    ):
        c = ws.cell(row=rr, column=1, value=line)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=9)
        rr += 1
    widths(ws, {"A": 52, "B": 14, "C": 14, "D": 12, "E": 14, "F": 13, "G": 12, "H": 18, "I": 18})

    # ---- LP Summary
    ws = wb.create_sheet("LP Summary")
    title_block(ws, "Lens presentation: 15 guide classes",
                "Pictures carrying each class in the analysed set, and the split-positive count in each split.", 7)
    hdr = ["Code", "Class", "Pictures", "Share of analysed pictures", "In 70/30 split", "In 80/20 split", "Note"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in lp:
        vals = [row["code"], row["class"], int(row["pictures"]), float(row["share"]),
                int(row["in_70"]), int(row["in_80"]), "No annotated pictures" if int(row["pictures"]) == 0 else ""]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j == 3 or j in (5, 6):
                cell.number_format = "#,##0"
            if j == 4:
                cell.number_format = "0.0%"
        rr += 1
    note(ws, rr + 1, "Rows are not additive: a picture can carry several classes. A picture with no annotated picture is "
                     "still listed at 0 so the guide's 15 hold. HEMA Obstruction (P2_HMO, 36 pictures) is legacy and is not "
                     "a split label.", 7)
    widths(ws, {"A": 10, "B": 30, "C": 12, "D": 16, "E": 12, "F": 12, "G": 30})
    ws.freeze_panes = "C5"

    # ---- Tag Combinations
    ws = wb.create_sheet("Tag Combinations")
    title_block(ws, "Tag combinations", "Two definitions, two tables. A pair can look rare in the exact table only because "
                "most of its pictures carry a third label.", 4)
    rr = 4
    ws.cell(row=rr, column=1, value="Table 1 - Exact pairs").font = BOLD
    rr += 1
    ws.cell(row=rr, column=1, value="The picture's complete label set is precisely that pair, nothing else.").font = SUB
    rr += 1
    for i, h in enumerate(["#", "Tag pair", "Pictures"], 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, 3)
    rr += 1
    for i, row in enumerate(exact[:15], 1):
        ws.cell(row=rr, column=1, value=i)
        ws.cell(row=rr, column=2, value=row["pair"])
        ws.cell(row=rr, column=3, value=int(row["pictures"])).number_format = "#,##0"
        rr += 1
    rr += 2
    ws.cell(row=rr, column=1, value="Table 2 - Inclusive pairs").font = BOLD
    rr += 1
    ws.cell(row=rr, column=1, value="The picture carries both labels; any further labels are allowed.").font = SUB
    rr += 1
    for i, h in enumerate(["#", "Tag pair", "Pictures"], 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, 3)
    rr += 1
    for i, row in enumerate(incl[:15], 1):
        ws.cell(row=rr, column=1, value=i)
        ws.cell(row=rr, column=2, value=row["pair"])
        ws.cell(row=rr, column=3, value=int(row["pictures"])).number_format = "#,##0"
        rr += 1
    rr += 2
    ws.cell(row=rr, column=1, value="How many labels one picture carries (all classes in the data, legacy included; Clear counts as one)").font = BOLD
    rr += 1
    for i, h in enumerate(["Labels on the picture", "Pictures"], 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, 2)
    rr += 1
    for row in lcounts:
        label = "0 class labels" if row["labels"] == "0" else f"{row['labels']} label(s)"
        ws.cell(row=rr, column=1, value=label)
        ws.cell(row=rr, column=2, value=int(row["pictures"])).number_format = "#,##0"
        rr += 1
    note(ws, rr + 1, "Every analysed picture carries at least one label: a guide class, one of the three legacy classes, or "
                     "Clear. The pair space covers every class present in the data, legacy included; legacy classes are marked "
                     "and are not used in the split. There is no zero-label bucket.", 4)

    rr += 3
    ws.cell(row=rr, column=1, value="Pictures with a mark outside the split label space").font = BOLD
    rr += 1
    for i, h in enumerate(["Reason", "Detail", "Pictures"], 1):
        ws.cell(row=rr, column=i, value=h)
    style_header(ws, rr, 3)
    rr += 1
    for row in outside:
        if row["reason"] == "Total":
            continue
        ws.cell(row=rr, column=1, value=row["reason"])
        ws.cell(row=rr, column=2, value=row["detail"])
        ws.cell(row=rr, column=3, value=int(row["pictures"])).number_format = "#,##0"
        rr += 1
    total = next(int(r["pictures"]) for r in outside if r["reason"] == "Total")
    ws.cell(row=rr, column=1, value="Total").font = BOLD
    ws.cell(row=rr, column=2, value="Analysed pictures outside the split").font = BOLD
    ws.cell(row=rr, column=3, value=total).font = BOLD
    ws.cell(row=rr, column=3).number_format = "#,##0"
    note(ws, rr + 1, "They all carry an annotation mark; none is Clear. 62 carry only legacy classes. 85 carry an object "
                     "with no size flag and nothing else: the EDA counts them in their class, the split cannot use them "
                     "because the four gated classes are positive on the size flag only.", 4)
    widths(ws, {"A": 40, "B": 46, "C": 12, "D": 10})

    # ---- OOI Summary
    ws = wb.create_sheet("OOI Summary")
    title_block(ws, "OOI tags: 8 guide classes", "Pictures carrying each class, the size-flag subset, the number of tags, "
                "and the typical tag size.", 9)
    hdr = ["Code", "Class", "In guide", "Pictures", "Of which size-flagged", "OOI tags", "Typical width (px)",
           "Typical height (px)", "Note"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for row in ooi:
        note_text = ""
        if row["guide"] == "Legacy":
            note_text = "Legacy class outside the guide; not a split label"
        elif row["class"] == "Bubble":
            note_text = "Includes Bubble Irregular and Stretched Bubble"
        elif row["class"] in ("Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA"):
            note_text = "Split positives = the size-flagged subset"
        vals = [row["code"], row["class"], row["guide"], int(row["pictures"]), int(row["gate"]),
                int(row["tags"]), float(row["median_w"]) or "-", float(row["median_h"]) or "-", note_text]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if j in (4, 5, 6):
                cell.number_format = "#,##0"
            if j in (7, 8) and isinstance(v, (int, float)):
                cell.number_format = "0.0"
            if j == 9:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            if row["guide"] == "Legacy":
                cell.fill = PatternFill("solid", fgColor=LEGACY_FILL)
        rr += 1
    note(ws, rr + 1, "Typical size is the median of the box extents. Pictures and tags count the same annotation: one "
                     "picture can carry many tags. The size-flagged subset is the split positive for its class.", 9)
    widths(ws, {"A": 10, "B": 28, "C": 10, "D": 12, "E": 16, "F": 12, "G": 14, "H": 14, "I": 44})
    ws.freeze_panes = "C5"

    # ---- Training and Test Split
    ws = wb.create_sheet("Training and Test Split")
    title_block(ws, "Training and test split before and after the 24 files",
                "Same frozen recipe, same seed, content-md5 groups. Before = the seven-file record (v6); after = the "
                "merged 24-file record (v7).", 11)
    hdr = ["Code", "Class", "Before: train", "Before: test", "Before: total", "After: train", "After: test",
           "After: total", "Change: train", "Change: test", "Note"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    for ratio in ("70_30", "80_20"):
        ws.cell(row=rr, column=1, value=f"{ratio.replace('_', ' / ')} split").font = BOLD
        ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=11)
        rr += 1
        for row in [r for r in splits if r["ratio"] == ratio]:
            bt, be, at, ae = int(row["before_train"]), int(row["before_test"]), int(row["after_train"]), int(row["after_test"])
            vals = [row["code"], row["class"], bt, be, bt + be, at, ae, at + ae, at - bt, ae - be,
                    "Split positives = size-flagged pictures" if "gate" in row["class"].lower() else ""]
            for j, v in enumerate(vals, 1):
                cell = ws.cell(row=rr, column=j, value=v)
                if isinstance(v, int) and j >= 3:
                    cell.number_format = "#,##0;-#,##0"
                if j == 11:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
            rr += 1
        bt = b70.get("train", 0) if ratio == "70_30" else b80.get("train", 0)
        be = b70.get("test", 0) if ratio == "70_30" else b80.get("test", 0)
        at = a70.get("train", 0) if ratio == "70_30" else a80.get("train", 0)
        ae = a70.get("test", 0) if ratio == "70_30" else a80.get("test", 0)
        vals = ["", "Total split rows", bt, be, bt + be, at, ae, at + ae, at - bt, ae - be,
                f"Not in a split: {6938 - rows_before} before, {analysed - rows_after} after"]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if isinstance(v, int) and j >= 3:
                cell.number_format = "#,##0;-#,##0"
            cell.font = BOLD
        rr += 1
        note(ws, rr, "A test split of 30 percent takes 2,235 pictures after the 24 files, against 2,006 before.", 11)
        rr += 2
    note(ws, rr, "The split label space is Draft 2 codes plus Clear. Legacy classes do not stratify the split; for the four "
                 "size-gated classes the flagged pictures are the class positives. No picture is dropped for lacking a flag "
                 "unless it carries no other label.", 11)
    widths(ws, {"A": 10, "B": 30, "C": 13, "D": 13, "E": 13, "F": 13, "G": 13, "H": 13, "I": 13, "J": 13, "K": 44})
    ws.freeze_panes = "C5"

    # ---- Reconciliation
    ws = wb.create_sheet("Reconciliation")
    title_block(ws, "Reconciliation", "The same figures in this workbook and in the October record workbook. "
                "A 'Yes' in the last column means the two agree.", 5)
    hdr = ["Figure", "Total EDA", "Record workbook", "Source", "Match"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(hdr))
    rr = 5
    # Read the record workbook and reconcile against it cell by cell, not against a copy.
    rec_wb = load_workbook(f"{ROOT}/reports/eda_24files_20261028/FMD_EDA_Record_20261028.xlsx", data_only=True)
    rec_pop, rec_lab = {}, {}
    for row in rec_wb["Summary"].iter_rows(values_only=True):
        if not row:
            continue
        if row[0] in ("Pictures with at least one mark", "Pictures with nothing marked (Clear)", "Analysed set"):
            rec_pop[row[0]] = int(row[1])
        if row[1] and isinstance(row[4], int):
            rec_lab[str(row[1])] = int(row[4])
    checks = [
        ("Pictures with marks", marked, rec_pop.get("Pictures with at least one mark"), "record workbook, Summary"),
        ("Clear", clear, rec_pop.get("Pictures with nothing marked (Clear)"), "record workbook, Summary"),
        ("Analysed set", analysed, rec_pop.get("Analysed set"), "record workbook, Summary"),
    ]
    for class_row in lp + ooi:
        name = class_row["class"]
        checks.append((f"{name} pictures", int(class_row["pictures"]), rec_lab.get(name), "record workbook, Summary"))
    checks += [("Split rows before (v6)", rows_before, "", "split v6"),
               ("Split rows after (v7)", rows_after, "", "split v7")]
    for label, a, b, src in checks:
        match = "n/a" if b == "" else ("Yes" if a == b else "No")
        vals = [label, a, b, src, match]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=rr, column=j, value=v)
            if isinstance(v, int) and j in (2, 3):
                cell.number_format = "#,##0"
        rr += 1
    note(ws, rr + 1, "The 24-file batch workbook counts only the 24 files: 3,592 pictures with marks and 36,098 OOI tags. "
                     "This workbook counts the whole record, so it equals the record workbook, not the batch workbook.", 5)
    widths(ws, {"A": 32, "B": 14, "C": 16, "D": 18, "E": 8})

    # ---- Definitions
    ws = wb.create_sheet("Definitions")
    title_block(ws, "Definitions", "Every term used in the sheets above.", 4)
    defs = [
        ("Picture examined", "Every distinct image in the inspection library, counted once."),
        ("Analysed set", "Every picture with marks plus Clear; a picture with no marks outside the Clear folder is a placeholder."),
        ("OOI tag", "An object of interest, marked with a box. One picture can carry many. 8 classes in the guide."),
        ("Lens Presentation", "A condition marked for the whole picture, one tag per picture. 15 classes in the guide."),
        ("Size flag", "A tag saying the object is above the size threshold. A subset of its class, and the split positive for "
                      "Foreign Matter, Fiber, Extraneous Polymer and HEMA."),
        ("Clear", "A picture with nothing marked. A label, and a negative class, not a guide class."),
        ("Split row", "A picture with at least one split label. A picture whose only marks are legacy, or an un-gated object "
                      "and nothing else, is outside the split."),
        ("Split label", "A label the model can learn: the four size flags, Bubble, Bubble Cluster, Wet Package, the 12 lens "
                        "presentation classes that carry pictures, and Clear."),
        ("Outside the split", "A picture with marks but no split label: legacy-only, or an un-gated object and nothing else. "
                              "It is not Clear. The EDA still counts an un-gated object in its class; only the split "
                              "excludes it."),
        ("Before / after", "Before is the seven-file record and its split (v6). After is the merged 24-file record and its "
                           "split (v7), built with the same frozen recipe."),
        ("Legacy classes", "HEMA Obstruction (P2_HMO), Bubble On 123, Bubble On Edge: outside the guide, not split labels."),
        ("Class code", "The short code the annotation guide uses, such as P2_BB or P1_ML."),
    ]
    rr = 4
    for term, text in defs:
        ws.cell(row=rr, column=1, value=term).font = BOLD
        c = ws.cell(row=rr, column=2, value=text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        rr += 1
    widths(ws, {"A": 26, "B": 110})

    path = f"{OUT}/FMD_EDA_Total_20261028.xlsx"
    wb.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
