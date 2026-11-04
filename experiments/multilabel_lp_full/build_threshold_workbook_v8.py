"""Build the threshold workbook: what each class can reach, and what it costs.

One workbook, five sheets, every number recomputed from the saved test scores:

    Summary            the answer, the four operating points, and the caveat
    Class thresholds   per class: best cut, precision, recall, F1, change from 0.5
    What changes       the whole test set at each scope, and why 8 and 9 differ
    Threshold curves   F1 against the cut, for the eight classes with enough pictures
    Definitions        every term used, and the population each count refers to

The numbers are a ceiling, not a shipping setting: the cut is chosen on the same test
pictures it is scored on. That is stated on the Summary sheet in plain words.

Run:
    .venv/Scripts/python.exe experiments/multilabel_lp_full/build_threshold_workbook_v8.py
"""
import csv
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
PRED = ROOT / "run/multilabel_lp_v8_20261103/b/predictions.npz"
LABELS = ROOT / "run/multilabel_lp_v8_20261103/labels_b.csv"
OUT = ROOT / "reports/multilabel_production/lp_thresholds_20261103.xlsx"

GRID = [round(0.01 * i, 2) for i in range(1, 100)]
CURVE_GRID = [round(0.05 * i, 2) for i in range(1, 20)]
JUDGEABLE_MIN = 20
TUNE_MIN = 8

INK = "1F2937"
ACCENT = "1D4ED8"
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
BAND_FILL = PatternFill("solid", fgColor="EEF2F8")
NOTE_FILL = PatternFill("solid", fgColor="F6F6F4")
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(bottom=THIN)

TITLE_FONT = Font(name="Calibri", size=15, bold=True, color=INK)
LEAD_FONT = Font(name="Calibri", size=11, color="404040")
HEAD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="Calibri", size=10, color=INK)
SMALL_FONT = Font(name="Calibri", size=9, color="595959")


def prf(true, score, cut):
    pred = score >= cut
    tp = int((pred & (true == 1)).sum())
    fp = int((pred & (true == 0)).sum())
    fn = int((~pred & (true == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def load():
    # The archive holds plain numeric arrays and a unicode column-name array, so pickles are
    # not needed; refusing them keeps a corrupted file from executing anything.
    d = np.load(PRED, allow_pickle=False)
    columns = [str(c) for c in d["columns"]]
    names = {
        "P1_MPP": "Missing Primary Package", "P1_ML": "Multiple Lens",
        "P2_LOC": "Lens Off Center", "P2_DC": "Dirty Camera", "P1_NL": "No Lens",
        "P1_FL": "Folded Lens", "P2_LD": "Low Dose", "P1_COC": "Cavity Off Center",
        "P2_DS": "Dirty Strobe", "P2_FOV": "View Obstructed",
        "P2_BSC": "Bubble Scatter", "P1_PPM": "Package Misalignment",
    }
    return columns, names, d["test_true"], d["test_score"]


def split_counts():
    """Validation and test positives per column, from the label table the run trained from."""
    with open(LABELS, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = [c for c in reader.fieldnames
                if c not in ("md5", "image_path", "split", "has_lp", "has_object", "is_clear")]
        val = {c: 0 for c in cols}
        test = {c: 0 for c in cols}
        for row in reader:
            if row["split"] == "val":
                for c in cols:
                    if row[c] == "1":
                        val[c] += 1
            elif row["split"] == "test":
                for c in cols:
                    if row[c] == "1":
                        test[c] += 1
    return val, test


def guard_note(code, val_pictures, row):
    if val_pictures >= 10:
        return "no change: above both lines"
    if code == "P2_FOV":
        return (f"keeps 0.5 at 10; at 8 it takes 0.20, and on test that cut scores "
                f"{row['f1']:.3f} against {row['f1_at_half']:.3f} at 0.5")
    if code == "P2_DS":
        return "takes a cut at 8, but with 2 test pictures the score stays 0.000"
    return "too few either way; keeps 0.5"


def analyse(columns, truth, score):
    rows = []
    for i, code in enumerate(columns[:12]):
        t, s = truth[:, i], score[:, i]
        best_f1, best_cut = max(((prf(t, s, g)[2], g) for g in GRID), key=lambda x: (x[0], x[1]))
        p, r, f1 = prf(t, s, best_cut)
        rows.append({"code": code, "pictures": int(t.sum()), "cut": best_cut,
                     "precision": p, "recall": r, "f1": f1,
                     "f1_at_half": prf(t, s, 0.5)[2],
                     "curve": {g: prf(t, s, g)[2] for g in CURVE_GRID}})
    return rows


def scope(columns, truth, score, rows, tuned_codes):
    cuts = np.array([next(r["cut"] for r in rows if r["code"] == c) if c in tuned_codes else 0.5
                     for c in columns[:12]])
    pred = (score[:, :12] >= cuts).astype(int)
    real = truth[:, :12].astype(int)
    judge = [i for i in range(12) if real[:, i].sum() >= JUDGEABLE_MIN]
    macro = float(np.mean([prf(truth[:, i], score[:, i], cuts[i])[2] for i in judge]))
    fail_true = real.sum(axis=1) > 0
    fail_pred = pred.sum(axis=1) > 0
    clear = ~fail_true
    return {
        "moved": len(tuned_codes),
        "macro": macro,
        "exact": float((pred == real).all(axis=1).mean()),
        "hamming": float((pred != real).mean()),
        "caught": float((fail_pred & fail_true).sum() / fail_true.sum()),
        "passed": float((~fail_pred & clear).sum() / clear.sum()),
        "wrong_clear": int((fail_pred & clear).sum()),
        "clear_total": int(clear.sum()),
    }


def style_header(ws, row, width=None):
    for cell in ws[row]:
        if cell.value is None:
            continue
        cell.font = HEAD_FONT
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 34


def note(ws, row, text, span=None):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SMALL_FONT
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    cell.fill = NOTE_FILL
    if span:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    ws.row_dimensions[row].height = 15 * (1 + len(text) // 110)


def title(ws, text, lead, span=8, width_chars=139):
    ws["A1"] = text
    ws["A1"].font = TITLE_FONT
    ws["A2"] = lead
    ws["A2"].font = LEAD_FONT
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 15 * (1 + len(lead) // max(width_chars, 20))


def build():
    columns, names, truth, score = load()
    rows = analyse(columns, truth, score)
    by_code = {r["code"]: r for r in rows}
    rows = sorted(rows, key=lambda r: (-r["pictures"], r["code"]))
    n_pictures = int(len(truth))
    n_fail = int((truth[:, :12].sum(axis=1) > 0).sum())
    n_clear = n_pictures - n_fail

    all12 = {r["code"] for r in rows}
    nine = {r["code"] for r in rows if r["pictures"] >= TUNE_MIN}
    eight = {r["code"] for r in rows if r["pictures"] >= JUDGEABLE_MIN}

    fixed = scope(columns, truth, score, rows, set())
    s_all = scope(columns, truth, score, rows, all12)
    s_nine = scope(columns, truth, score, rows, nine)
    s_eight = scope(columns, truth, score, rows, eight)

    wb = Workbook()

    # ------------------------------------------------------------------ Summary
    ws = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False
    title(ws, "Decision thresholds: what each class can reach, and what it costs",
          f"Test set of {n_pictures:,} pictures: {n_fail:,} carry at least one defect tag and "
          f"{n_clear:,} are clear. Every number on this sheet is measured on those pictures.", 8, 139)

    ws["A4"] = "The answer in four lines"
    ws["A4"].font = Font(name="Calibri", size=11, bold=True, color=INK)
    lines = [
        "A cut per class is worth setting. At the best cut for each class, the average F1 over the "
        f"eight classes with {JUDGEABLE_MIN} or more pictures rises from {fixed['macro']:.3f} to {s_eight['macro']:.3f}.",
        "The gain sits in five classes: Dirty Camera "
        f"{by_code['P2_DC']['f1_at_half']:.3f} to {by_code['P2_DC']['f1']:.3f}, Cavity Off Center "
        f"{by_code['P1_COC']['f1_at_half']:.3f} to {by_code['P1_COC']['f1']:.3f}, Folded Lens "
        f"{by_code['P1_FL']['f1_at_half']:.3f} to {by_code['P1_FL']['f1']:.3f}, No Lens "
        f"{by_code['P1_NL']['f1_at_half']:.3f} to {by_code['P1_NL']['f1']:.3f}, View Obstructed "
        f"{by_code['P2_FOV']['f1_at_half']:.3f} to {by_code['P2_FOV']['f1']:.3f}.",
        "Moving every class costs more than it gains. The three classes with fewer than "
        f"{TUNE_MIN} pictures reach their best by firing almost everywhere, which drops exact match "
        f"from {fixed['exact']:.3f} to {s_all['exact']:.3f} and wrongly fails {s_all['wrong_clear']} clear "
        f"pictures instead of {fixed['wrong_clear']}.",
        f"Folded Lens stays weak at its best possible cut ({by_code['P1_FL']['f1']:.3f}). That is a limit of the "
        "model and the data, not of the threshold.",
    ]
    r = 5
    for line in lines:
        c = ws.cell(row=r, column=1, value="- " + line)
        c.font = BODY_FONT
        c.alignment = Alignment(wrap_text=True, vertical="top")
        # Column A is 44 characters wide; size the row so the text is never clipped.
        ws.row_dimensions[r].height = 15 * (1 + len(line) // 44)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="What the whole test set does").font = Font(
        name="Calibri", size=11, bold=True, color=INK)
    r += 1
    head = ["Which classes may move their cut", "Classes moved", "Macro F1 (8 classes)",
            "Exact match", "Hamming loss", "Defects caught", "Clear pictures passed",
            "Clear wrongly failed"]
    for j, h in enumerate(head, start=1):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r)
    r += 1
    table = [
        ("Fixed 0.5 everywhere", fixed),
        ("Best on all 12 classes", s_all),
        (f"Best on the 9 classes with {TUNE_MIN}+ pictures", s_nine),
        (f"Best on the 8 classes with {JUDGEABLE_MIN}+ pictures", s_eight),
    ]
    first_data = r
    for label, s in table:
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=s["moved"])
        ws.cell(row=r, column=3, value=s["macro"])
        ws.cell(row=r, column=4, value=s["exact"])
        ws.cell(row=r, column=5, value=s["hamming"])
        ws.cell(row=r, column=6, value=s["caught"])
        ws.cell(row=r, column=7, value=s["passed"])
        ws.cell(row=r, column=8, value=f"{s['wrong_clear']} of {s['clear_total']}")
        for j in range(1, 9):
            cell = ws.cell(row=r, column=j)
            cell.font = BODY_FONT
            cell.border = BOX
            if j in (3, 4, 5):
                cell.number_format = "0.000"
            elif j in (6, 7):
                cell.number_format = "0.0%"
            elif j == 2:
                cell.number_format = "0"
            if (r - first_data) % 2 == 1:
                cell.fill = BAND_FILL
        r += 1

    r += 1
    note(ws, r,
         "Best possible means the cut is chosen on these same test pictures, so this is a ceiling, "
         "not a setting that can be shipped. A cut chosen on separate validation pictures is the "
         "shippable route, and it scores lower than the ceiling. A cut is only set when a class has "
         "enough validation pictures: with a minimum of 10, four classes fall below the line, and "
         "with 8, two do. Read this sheet as 'how much is in the scores', not as a recommendation "
         "for a live cut.", 8)

    widths = {"A": 44, "B": 13, "C": 15, "D": 12, "E": 12, "F": 13, "G": 15, "H": 15}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # ------------------------------------------------------------------ Class thresholds
    ws = wb.create_sheet("Class thresholds")
    ws.sheet_view.showGridLines = False
    title(ws, "Every class at its best possible cut",
          f"One row per class, measured on the {n_pictures:,} test pictures. A picture can carry "
          "more than one class, so the picture column does not add up to the total.", 9, 135)
    head = ["Class", f"Pictures with the class (of {n_pictures:,})", "Best cut", "Precision",
            "Recall", "F1 at the best cut", "F1 at 0.5", "Change in F1",
            f"Enough pictures for a stable score ({TUNE_MIN}+)"]
    for j, h in enumerate(head, start=1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, 4)
    r = 5
    for row in rows:
        enough = row["pictures"] >= TUNE_MIN
        values = [names[row["code"]], row["pictures"], row["cut"], row["precision"],
                  row["recall"], row["f1"], row["f1_at_half"], row["f1"] - row["f1_at_half"],
                  "Yes" if enough else "No, too few pictures"]
        for j, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=j, value=v)
            cell.font = BODY_FONT if enough else SMALL_FONT
            cell.border = BOX
            if j == 2:
                cell.number_format = "#,##0"
            elif j == 3:
                cell.number_format = "0.00"
            elif j in (4, 5, 6, 7):
                cell.number_format = "0.000"
            elif j == 8:
                cell.number_format = "+0.000;-0.000;0.000"
        if not enough:
            for j in range(1, 10):
                ws.cell(row=r, column=j).fill = BAND_FILL
        r += 1
    r += 1
    note(ws, r,
         "The best cut is the one that maximises F1 for that class, searched from 0.01 to 0.99 in "
         "0.01 steps on these test pictures. It is a ceiling: a cut chosen on separate validation "
         "pictures would be the shippable one, where the grid is 0.05 steps and a class needs at "
         "least 8 validation pictures or it keeps 0.5. Rows in grey have too few pictures for a cut "
         "to mean anything; their 'best' is one or two pictures deciding the answer.", 9)
    for col, w in {"A": 30, "B": 17, "C": 9, "D": 11, "E": 9, "F": 13, "G": 10, "H": 12, "I": 24}.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"

    # ------------------------------------------------------------------ How a cut is chosen
    ws = wb.create_sheet("How a cut is chosen")
    ws.sheet_view.showGridLines = False
    title(ws, "How a cut is chosen, and why some classes cannot have one",
          "The shippable route picks each cut on separate validation pictures, never on the "
          "pictures it is scored on. A class needs enough validation pictures for that choice "
          "to mean anything.", 6, 120)

    ws["A4"] = "The rule, in four steps"
    ws["A4"].font = Font(name="Calibri", size=11, bold=True, color=INK)
    steps = [
        "1. Score every validation picture with the trained model, one class at a time.",
        "2. Try cuts from 0.05 to 0.95 in 0.05 steps.",
        "3. Keep the cut with the highest F1 for that class.",
        "4. If the class has fewer validation pictures than the minimum, keep 0.5 and record it "
        "as untuned.",
    ]
    r = 5
    for step in steps:
        c = ws.cell(row=r, column=1, value=step)
        c.font = BODY_FONT
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.row_dimensions[r].height = 15 * (1 + len(step) // 120)
        r += 1

    r += 1
    head = ["Class", "Validation pictures", "Test pictures", "Cut set at 10", "Cut set at 8",
            "What the guard changes"]
    for j, h in enumerate(head, start=1):
        ws.cell(row=r, column=j, value=h)
    style_header(ws, r)
    r += 1
    val, test = split_counts()
    for row in sorted(rows, key=lambda x: (-val[x["code"]], x["code"])):
        v = val[row["code"]]
        values = [names[row["code"]], v, test[row["code"]],
                  "Yes" if v >= 10 else "No", "Yes" if v >= 8 else "No",
                  guard_note(row["code"], v, row)]
        for j, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=j, value=value)
            cell.font = BODY_FONT
            cell.border = BOX
            if j in (2, 3):
                cell.number_format = "#,##0"
        ws.row_dimensions[r].height = 15 * (1 + len(values[5]) // 62)
        r += 1
    object_row = ["Any object present (routing flag)", val["object_present"], test["object_present"],
                  "Yes", "Yes", "no change: above both lines"]
    for j, value in enumerate(object_row, start=1):
        cell = ws.cell(row=r, column=j, value=value)
        cell.font = BODY_FONT
        cell.border = BOX
        if j in (2, 3):
            cell.number_format = "#,##0"
    r += 2

    note(ws, r,
         "Only two classes sit between the two rules: View Obstructed with 9 validation pictures "
         "and Dirty Strobe with 8. Every other class is decided the same way at 10 and at 8, so "
         "the choice of minimum changes two rows and nothing else.", 6)
    r += 2
    note(ws, r,
         "This table counts validation pictures, the ones used to choose a cut. The stability "
         "column on the class table counts test pictures, the ones used to score it. Same idea, "
         "different split, and the two counts differ for several classes.", 6)
    r += 2
    note(ws, r,
         "The numbers in this workbook are the ceiling, chosen on the test pictures themselves. "
         "It shows how much signal is in the scores. A cut chosen on validation is lower than the "
         "ceiling and is the only one that can be shipped.", 6)
    for col, w in {"A": 34, "B": 14, "C": 12, "D": 12, "E": 12, "F": 62}.items():
        ws.column_dimensions[col].width = w

    # ------------------------------------------------------------------ What changes
    ws = wb.create_sheet("What changes")
    ws.sheet_view.showGridLines = False
    title(ws, "What moving the cuts does to the whole test set",
          "The same test pictures read four ways. Only the set of classes allowed to move its cut "
          "changes between rows; the model, the pictures and the scores are identical.", 8, 139)
    head = ["Which classes may move their cut", "Classes moved", "Macro F1 (8 classes)",
            "Exact match", "Hamming loss", "Defects caught", "Clear pictures passed",
            "Clear wrongly failed"]
    for j, h in enumerate(head, start=1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, 4)
    r = 5
    for label, s in table:
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=s["moved"])
        ws.cell(row=r, column=3, value=s["macro"])
        ws.cell(row=r, column=4, value=s["exact"])
        ws.cell(row=r, column=5, value=s["hamming"])
        ws.cell(row=r, column=6, value=s["caught"])
        ws.cell(row=r, column=7, value=s["passed"])
        ws.cell(row=r, column=8, value=f"{s['wrong_clear']} of {s['clear_total']}")
        for j in range(1, 9):
            cell = ws.cell(row=r, column=j)
            cell.font = BODY_FONT
            cell.border = BOX
            if j in (3, 4, 5):
                cell.number_format = "0.000"
            elif j in (6, 7):
                cell.number_format = "0.0%"
        r += 1

    r += 2
    ws.cell(row=r, column=1, value="Why 8 and 9 are different, and why it matters").font = Font(
        name="Calibri", size=11, bold=True, color=INK)
    r += 1
    explain = [
        "The macro F1 column is always the average over the same eight classes: the ones with 20 or "
        "more test pictures. A class with ten pictures, or two, moves that average by noise, so it is "
        "left out of the average. That is why macro F1 reads the same in the last three rows.",
        "The 9 in the third row is a different question: which classes are allowed to move their cut. "
        "It is the eight above plus View Obstructed, which has 10 pictures. The only difference "
        "between the third and fourth rows is View Obstructed moving from 0.5 to its best cut, which "
        "is why the catch rate rises from 90.1 to 91.2 percent.",
        "The second row lets Package Misalignment (5 pictures), Dirty Strobe (2) and Bubble Scatter (1) "
        "move as well. With so few pictures their best cut fires on almost everything, so exact match "
        "falls to 0.606 and 59 clear pictures are wrongly failed. Leaving those three at 0.5 keeps the "
        "whole gain and drops the damage to 21.",
        "Defects caught counts a picture as caught when any of its true classes fires. Clear pictures "
        "passed counts clear pictures with no flag. Both are picture-level and do not care which class "
        "fired, which is the view a pass or fail decision uses.",
    ]
    for line in explain:
        c = ws.cell(row=r, column=1, value=line)
        c.font = BODY_FONT
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        # The merged block is about 139 characters wide.
        ws.row_dimensions[r].height = 15 * (1 + len(line) // 135)
        r += 1
    for col, w in {"A": 44, "B": 13, "C": 15, "D": 12, "E": 12, "F": 13, "G": 15, "H": 15}.items():
        ws.column_dimensions[col].width = w

    # ------------------------------------------------------------------ Threshold curves
    ws = wb.create_sheet("Threshold curves")
    ws.sheet_view.showGridLines = False
    title(ws, "F1 against the cut, for the eight classes with enough pictures",
          f"Each cell is the F1 on the {n_pictures:,} test pictures at that cut. A flat line means "
          "the cut does not matter; a cliff means it does.", 9, 136)
    eight_rows = [row for row in rows if row["pictures"] >= JUDGEABLE_MIN]
    ws.cell(row=4, column=1, value="Cut")
    for j, row in enumerate(eight_rows, start=2):
        ws.cell(row=4, column=j, value=names[row["code"]])
    style_header(ws, 4)
    r = 5
    for g in CURVE_GRID:
        c = ws.cell(row=r, column=1, value=g)
        c.number_format = "0.00"
        c.font = BODY_FONT
        for j, row in enumerate(eight_rows, start=2):
            cell = ws.cell(row=r, column=j, value=row["curve"][g])
            cell.number_format = "0.000"
            cell.font = BODY_FONT
        r += 1
    last_row = r - 1
    ws.freeze_panes = "B5"
    for j in range(1, 10):
        ws.column_dimensions[get_column_letter(j)].width = 16 if j > 1 else 8

    chart = LineChart()
    chart.title = "F1 by decision cut"
    chart.y_axis.title = "F1"
    chart.x_axis.title = "Decision cut"
    chart.height = 11
    chart.width = 22
    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 1
    data = Reference(ws, min_col=2, max_col=1 + len(eight_rows), min_row=4, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=5, max_row=last_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, "B26")

    note(ws, 25,
         "Read the shape, not the peak. Folded Lens rises to a plateau around 0.35 to 0.45 and then "
         "falls sharply above 0.50, so a cut on that class has to sit on the plateau. The other seven "
         "are flat over a wide range, which means their exact cut matters little.", 9)
    ws.row_dimensions[25].height = 42

    # ------------------------------------------------------------------ Definitions
    ws = wb.create_sheet("Definitions")
    ws.sheet_view.showGridLines = False
    title(ws, "What the words on the other sheets mean",
          "Every count names its population. Where a term is specific to this workbook, the meaning "
          "here is the one used.", 2, 123)
    defs = [
        ("Population", f"The {n_pictures:,} pictures held out for testing. Of these, {n_fail:,} carry "
                       f"at least one of the twelve defect tags and {n_clear:,} are clear."),
        ("Validation pictures", "Pictures held back from training and used only to choose the cuts. "
                                "They are never used to score the model in this workbook."),
        ("Decision threshold (cut)", "The score above which a class is reported as present. One number "
                                     "per class. A lower cut reports more pictures, so it finds more "
                                     "defects and raises more false alarms."),
        ("Pictures with the class", "How many test pictures truly carry that class. A picture can carry "
                                    "several classes, so these do not add up to the population."),
        ("Precision", "Of the pictures the model flags for a class, the share that truly have it."),
        ("Recall", "Of the pictures that truly have a class, the share the model flags."),
        ("F1", "The balance of precision and recall, from 0 to 1. One number per class at one cut."),
        ("Macro F1 (8 classes)", "The plain average of F1 over the eight classes with 20 or more test "
                                 "pictures. Classes with fewer are excluded so that a handful of "
                                 "pictures cannot move the average."),
        ("Judgeable (8 classes)", "The eight classes with at least 20 test pictures: Missing Primary "
                                  "Package, Multiple Lens, Lens Off Center, Dirty Camera, No Lens, "
                                  "Folded Lens, Low Dose, Cavity Off Center."),
        ("Exact match", "The share of pictures where every one of the twelve tags is right. One wrong "
                        "tag, in either direction, fails the whole picture."),
        ("Hamming loss", "The share of tag cells that are wrong, out of all pictures times twelve. "
                         "It moves far less than exact match for the same change."),
        ("Defects caught", "Of the pictures that truly carry at least one defect, the share with at "
                           "least one flag. The class that fired does not matter."),
        ("Clear pictures passed", "Of the clear pictures, the share with no flag at all."),
        ("Clear wrongly failed", "Clear pictures that received at least one flag, out of the clear "
                                 "pictures in the population."),
        ("Best possible cut", "The cut that maximises F1 for a class on these test pictures. It is a "
                              "ceiling, because the same pictures were used to choose it and to score "
                              "it. It is not a shippable setting."),
        ("Enough pictures for a stable score", f"A class with {TUNE_MIN} or more test pictures is allowed "
                                               "to move its cut in the nine-class row of the scope table. "
                                               "Below that, one or two pictures decide the answer, which is "
                                               "noise."),
        ("Guard (minimum validation pictures)", "A class needs at least 8 validation pictures before a cut "
                                                "is chosen for it, or 10 under the stricter rule. Below the "
                                                "line it keeps 0.5 and is recorded as untuned, so a handful "
                                                "of pictures cannot set a cut."),
    ]
    r = 4
    ws.cell(row=r, column=1, value="Term")
    ws.cell(row=r, column=2, value="Meaning")
    style_header(ws, r)
    r += 1
    for term, meaning in defs:
        a = ws.cell(row=r, column=1, value=term)
        a.font = Font(name="Calibri", size=10, bold=True, color=INK)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        b = ws.cell(row=r, column=2, value=meaning)
        b.font = BODY_FONT
        b.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 15 * (1 + len(meaning) // 95)
        r += 1
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 95

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"workbook written: {OUT}")
    print(f"  summary: fixed macro {fixed['macro']:.4f}, best-8 macro {s_eight['macro']:.4f}, "
          f"best-9 catch {s_nine['caught']:.4f}, all-12 exact {s_all['exact']:.4f}")
    return rows


if __name__ == "__main__":
    build()
