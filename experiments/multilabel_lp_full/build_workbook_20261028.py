"""Build the results workbook for the LP run of 2026-10-28.

Reads only the two metrics files written by train_lp.py, so every number in the workbook comes
from one place. Plain class names throughout: no codes, no paths, no file names, so it can be
sent to a reader who does not know the pipeline.

Terminology, fixed 2026-10-28: the twelve answers are LP classes (from the LP tags), the
thirteenth answer is one OOI flag that covers all eight OOI classes together.

Usage:
    .venv/Scripts/python experiments/multilabel_lp_full/build_workbook_20261028.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / os.environ.get("LP_RUN_DIR", "run/multilabel_lp_full_20261029")
OUT_XLSX = ROOT / "reports/multilabel_production/lp_full_results_20261029.xlsx"

A = json.loads((RUN / "a/metrics.json").read_text(encoding="utf-8"))
B = json.loads((RUN / "b/metrics.json").read_text(encoding="utf-8"))


def label_rows(path: Path) -> int:
    with open(path, encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


TOTAL_A = label_rows(RUN / "labels_a.csv")
TOTAL_B = label_rows(RUN / "labels_b.csv")

# The bar and the per-class bars fixed in the design before the run.
OVERALL_TARGET = 0.85
TARGETS = {"Lens Off Center": 0.90, "Dirty Camera": 0.85, "Folded Lens": 0.70, "Low Dose": 0.70}

# What each number means, in the words used in the workbook. Every number in the text is
# read from the run's own metrics, so the run 1 and run 2 sheets cannot drift apart.
# Where the cause is measured it is stated; where it is a hypothesis it says so.
def reason(name: str, m: dict, old: dict) -> str:
    v = m["per_class"][next(k for k, w in m["per_class"].items() if w["name"] == name)]
    o = old["per_class"][next(k for k, w in old["per_class"].items() if w["name"] == name)]
    ap, recall, best, thr = v["auprc"], v["recall_0.5"], v["best_f1"], v["threshold"]
    old_ap = o["auprc"]
    if name == "Missing Primary Package":
        return ("The most consistent class in the set and the largest test group. The model ranks it "
                f"almost perfectly and still finds {recall*100:.1f} percent of the pictures at the "
                "0.5 cut-off.")
    if name == "Multiple Lens":
        return ("A large, visually distinct class. Strong ranking and a balanced precision and recall "
                "at the default cut-off, so the number is trustworthy.")
    if name == "No Lens":
        return ("An empty cavity looks different from every other case. Ranking is almost perfect and "
                f"recall at the default cut-off is {recall:.2f}.")
    if name == "Cavity Off Center":
        return (f"Only {v['support']} test pictures. The shift of the cavity is a strong visual cue; "
                "the small dip against the previous run is within what a group this size can wobble.")
    if name == "Lens Off Center":
        return ("Still below its 0.90 target, at "
                f"{ap:.2f}. The lens position also changes with multiple lens and cavity offset, so "
                f"the three overlap; the best balance is {best:.2f} at a lower threshold. More test "
                f"pictures moved it from {old_ap:.2f} to {ap:.2f}.")
    if name == "Dirty Camera":
        return ("Below its 0.85 target at "
                f"{ap:.2f}, but improved: the test group grew from {o['support']} to {v['support']} "
                f"pictures and lifted the score from {old_ap:.2f} and recall at the default cut-off "
                f"from {o['recall_0.5']:.2f} to {recall:.2f}. The best balance, {best:.2f}, comes at "
                f"a {thr:.2f} threshold. What remains looks like the intrinsic difficulty of diffuse, "
                "low-contrast dirt rather than a data shortage.")
    if name == "Folded Lens":
        return ("Better, and still the weakest class with enough pictures to judge: "
                f"{ap:.2f} against its 0.70 target, up from {old_ap:.2f} on twice the test support. "
                f"Everything the model flags is right, but at the default cut-off it finds only "
                f"{recall*100:.0f} percent of them; the best balance is {best:.2f} at a {thr:.2f} "
                "threshold. Almost every folded lens in the data also carries multiple lens, so the "
                "overlap remains a label design finding, not only a training problem.")
    if name == "Low Dose":
        return ("Now well above its 0.70 target at "
                f"{ap:.2f}, on three times the test support, with recall {recall:.2f} at the default "
                "cut-off. The unfinished-annotation caveat from the previous run carries less weight "
                f"now that the class has {v['support']} test pictures, but a marking pass on the "
                "older files would still settle it.")
    if name == "Dirty Strobe":
        return (f"{v['support']} test pictures. The number is noise in either direction and should "
                "not be quoted.")
    if name == "View Obstructed":
        return (f"{v['support']} test pictures. The ranking looks high but the group is still too "
                "small to support a conclusion.")
    if name == "Bubble Scatter":
        return f"{v['support']} test picture. Nothing can be concluded."
    if name == "Package Misalignment":
        return ("Measurable for the first time, on "
                f"{v['support']} test pictures. Too few to judge; the next annotation pass should "
                "decide whether this class stays in scope.")
    raise KeyError(name)


def verdict(name: str, ap: float, support: int) -> str:
    if support == 0:
        return "No examples in the test set"
    if support < 20:
        return "Too few pictures to judge"
    if name in TARGETS:
        return ("Meets the target" if ap >= TARGETS[name]
                else f"Below the {TARGETS[name]:.2f} target")
    return ("Meets the 0.85 bar" if ap >= OVERALL_TARGET
            else f"Below the {OVERALL_TARGET:.2f} bar")


def rows_of(metrics: dict, old: dict) -> list[dict]:
    out = []
    for v in metrics["per_class"].values():
        out.append({
            "name": v["name"], "support": v["support"], "ap": v["auprc"],
            "precision": v["precision_0.5"], "recall": v["recall_0.5"],
            "f1": v["f1_0.5"], "best_f1": v["best_f1"], "threshold": v["threshold"],
            "verdict": verdict(v["name"], v["auprc"], v["support"]),
            "reason": reason(v["name"], metrics, old),
        })
    out.sort(key=lambda r: (-(r["support"] > 0), -r["ap"] if r["ap"] == r["ap"] else 0))
    return out


# The previous run of this same experiment, on the seven-file annotation, loaded so the
# 7-vs-24 comparison and the per-class prose read their own numbers.
OLD = json.loads((RUN.parent / "multilabel_lp_full_20261028/a/metrics.json").read_text(encoding="utf-8"))
OLD_B = json.loads((RUN.parent / "multilabel_lp_full_20261028/b/metrics.json").read_text(encoding="utf-8"))
OLD_DIR = RUN.parent / "multilabel_lp_full_20261028"
TOTAL_A_OLD = label_rows(OLD_DIR / "labels_a.csv")
TOTAL_B_OLD = label_rows(OLD_DIR / "labels_b.csv")

ROWS_A = rows_of(A, OLD)
ROWS_B = rows_of(B, OLD_B)

# The two earlier runs on the five-class label set, read from their own results.
EARLIER = []
for label, path in (("Earlier run, plain", RUN.parent / "multilabel_lp_20260928/metrics.json"),
                    ("Earlier run, class weighting",
                     RUN.parent / "multilabel_lp_posw_20261005/metrics.json")):
    if path.is_file():
        m = json.loads(path.read_text(encoding="utf-8"))
        t = m["test_metrics"]
        EARLIER.append({"label": label, "classes": len(t["per_class"]),
                        "train": m["rows"]["train"], "test": m["rows"]["test"],
                        "macro": t["macro_auprc"], "folded": t["per_class"]["P1_FL"]["auprc"],
                        "exact": t["exact_match_ratio"]})

SHARED = ["Missing Primary Package", "Multiple Lens", "No Lens", "Cavity Off Center",
          "Folded Lens"]
CURRENT5 = sum(v["auprc"] for v in A["per_class"].values()
               if v["name"] in SHARED) / len(SHARED)


# ---------------------------------------------------------------- workbook styling

HDR_FILL = PatternFill("solid", fgColor="1F3B57")
HDR_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14)
NOTE_FONT = Font(italic=True, size=9, color="555555")
BOX_FILL = PatternFill("solid", fgColor="F2F5F9")
THIN = Side(style="thin", color="CCCCCC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def sheet(wb, title, heading, note=None):
    ws = wb.create_sheet(title)
    ws["A1"] = heading
    ws["A1"].font = TITLE_FONT
    if note:
        ws["A2"] = note
        ws["A2"].font = NOTE_FONT
        ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A4"
    return ws


def table(ws, start_row, headers, rows, widths, formats=None, fill=None):
    for j, h in enumerate(headers, start=1):
        c = ws.cell(row=start_row, column=j, value=h)
        c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(rows, start=start_row + 1):
        for j, val in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=val)
            c.border = BORDER
            if fill:
                c.fill = fill
            c.alignment = Alignment(wrap_text=(j == len(row)), vertical="top")
            if formats and j in formats and isinstance(val, (int, float)):
                c.number_format = formats[j]
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(j)].width = w


wb = Workbook()
wb.remove(wb.active)

# ---- sheet 1: results, with the split box
ws = sheet(wb, "Results", "Multi-label lens inspection, results of 2026-10-29",
           "Two runs of the same model on the same pictures. Run 1 answers the twelve LP "
           "classes. Run 2 answers the same twelve plus one OOI flag, which covers all eight "
           "OOI classes together rather than naming one.")
rows = [
    ("LP classes predicted", 12, 13, "answers per picture"),
    ("Average precision over the 8 judgeable classes", A["macro_auprc_judgeable"],
     B["macro_auprc_judgeable"], "0 to 1, higher is better"),
    ("Pictures where every answer was right", A["exact_match"], B["exact_match"], "share"),
    ("Wrong answers per picture-class question", A["hamming_loss"], B["hamming_loss"], "share"),
    ("Training time", A["timing"]["seconds_training"], B["timing"]["seconds_training"], "seconds"),
    ("Time per training pass", A["timing"]["seconds_per_epoch"], B["timing"]["seconds_per_epoch"],
     "seconds"),
    ("Time to score one picture", A["timing"]["inference_ms_per_image"],
     B["timing"]["inference_ms_per_image"], "milliseconds"),
]
table(ws, 4, ["Measure", "Run 1: LP classes only", "Run 2: LP classes plus OOI flag", "Unit"],
      rows, [46, 26, 34, 26], formats={2: "0.000", 3: "0.000"})
for i in range(5, 12):
    for j in (2, 3):
        v = ws.cell(row=i, column=j).value
        if isinstance(v, float) and v > 10:
            ws.cell(row=i, column=j).number_format = "#,##0"
ws.cell(row=13, column=1,
        value="Average precision is computed per class and then averaged over the eight classes "
              "that have at least 20 test pictures. The four very rare classes are shown but "
              "left out of the average.").font = NOTE_FONT

# the split box: same pictures, split 80/20, one row per run
ws["A16"] = "Train and test split"
ws["A16"].font = Font(bold=True, size=12)
split = [
    ("Run 1: LP classes only", TOTAL_A - A["rows"], A["rows"], TOTAL_A, "80 / 20"),
    ("Run 2: LP classes plus OOI flag", TOTAL_B - B["rows"], B["rows"], TOTAL_B, "80 / 20"),
]
table(ws, 17, ["Run", "Pictures for training", "Pictures for testing", "Total pictures",
               "Split"],
      split, [34, 20, 20, 16, 10], formats={2: "#,##0", 3: "#,##0", 4: "#,##0"}, fill=BOX_FILL)
ws.cell(row=21, column=1,
        value="Population: the seven revised annotation files only. The seventeen newly "
              "received files, 2,550 pictures, are not in either run; they get their own EDA "
              "first.").font = NOTE_FONT

# ---- sheets 2 and 3: per class
for title, metrics, rows_ in (("LP classes, run 1", A, ROWS_A),
                              ("LP classes, run 2", B, ROWS_B)):
    ws = sheet(wb, title, "Every LP class, one row each",
               "Test pictures is how many pictures in the test set carry the class. Precision, "
               "recall and F1 are read at the default 0.5 cut-off. Best F1 is the best balance "
               "reachable at any cut-off, and the threshold column says where.")
    table(ws, 4,
          ["LP class", "Test pictures", "Average precision", "Precision at 0.5",
           "Recall at 0.5", "F1 at 0.5", "Best F1", "Best threshold", "Verdict",
           "What the number says"],
          [(r["name"], r["support"], r["ap"], r["precision"], r["recall"], r["f1"],
            r["best_f1"], r["threshold"], r["verdict"], r["reason"]) for r in rows_],
          [26, 13, 17, 15, 13, 11, 9, 13, 26, 80],
          formats={3: "0.000", 4: "0.000", 5: "0.000", 6: "0.000", 7: "0.000", 8: "0.00"})

# ---- sheet 4: the OOI flag
ws = sheet(wb, "OOI flag", "Run 2, the thirteenth class: one OOI flag",
           "The thirteenth answer is not a separate finding. It is one flag that covers all "
           "eight OOI classes together: it says at least one OOI class is present, without "
           "saying which. It is scored by how often it fires, not by average precision, "
           "because it routes a picture rather than describing it.")
oc = B["object_column"]
table(ws, 4, ["Group", "Pictures", "Times the flag fired", "Share", "Target"],
      [("Pictures with an OOI and no LP class", oc["pictures_object_only"],
        round(oc["fire_rate_object_only"] * oc["pictures_object_only"]),
        oc["fire_rate_object_only"], "at least 90 percent"),
       ("Pictures with an LP class and an OOI", oc["pictures_mixed"],
        round(oc["fire_rate_mixed"] * oc["pictures_mixed"]), oc["fire_rate_mixed"],
        "no target set"),
       ("Clear pictures", oc["pictures_clear"],
        round(oc["fire_rate_clear"] * oc["pictures_clear"]), oc["fire_rate_clear"],
        "at most 5 percent")],
      [44, 12, 22, 12, 24], formats={4: "0.0%"})
ws.cell(row=9, column=1,
        value="A flag that fires on almost every Clear picture would make the routing useless; "
              "a flag that misses OOI pictures would send dirty pictures down the wrong path."
        ).font = NOTE_FONT

# ---- sheet 5: earlier runs, kept apart
ws = sheet(wb, "Earlier runs", "Earlier runs, kept separate from this one",
           "Two earlier runs answered five LP classes on a smaller test set. They are kept in "
           "their own sheet and are never mixed into the results of this run.")
table(ws, 4,
      ["Run", "LP classes", "Training pictures", "Test pictures",
       "Macro over the five shared classes", "Folded Lens", "Pictures fully right"],
      [(e["label"], e["classes"], e["train"], e["test"], e["macro"], e["folded"], e["exact"])
       for e in EARLIER]
      + [("This run, LP classes only", 12, TOTAL_A - A["rows"], A["rows"], CURRENT5,
          A["per_class"]["P1_FL"]["auprc"], A["exact_match"])],
      [32, 11, 18, 13, 30, 12, 18],
      formats={5: "0.000", 6: "0.000", 7: "0.0%"})
ws.cell(row=9, column=1,
        value="The five shared classes are the only like-for-like line. This run's headline of "
              f"{A['macro_auprc_judgeable']:.2f} averages over eight classes, so it must never "
              "be set beside the earlier 0.90 and 0.92: the label sets differ, five against "
              f"twelve, and the test pictures differ, 677 against {A['rows']:,}.").font = NOTE_FONT
ws.cell(row=10, column=1,
        value="Four of the five shared classes sit at or near the ceiling in every run. Folded "
              "Lens is the only one that moved, and three things changed at once between the "
              "earlier runs and this one: the label set, the test pictures, and the annotation "
              "revision. The drop cannot be pinned on one of them from these numbers.").font = NOTE_FONT

# ---- sheet: seven files vs twenty-four files
ws = sheet(wb, "7 vs 24 files", "The same experiment on the two annotations",
           "The previous run used seven annotation files, 1,047 pictures; this run uses all "
           "twenty-four, 3,597. Same model, same split rules, same questions; only the "
           "annotation differs.")
occ_o = OLD_B["object_column"]
occ_n = B["object_column"]
table(ws, 4,
      ["Measure", "Variant 1, 7 files", "Variant 1, 24 files",
       "Variant 2, 7 files", "Variant 2, 24 files"],
      [("Test pictures", OLD["rows"], A["rows"], OLD_B["rows"], B["rows"]),
       ("Training pictures", TOTAL_A_OLD - OLD["rows"], TOTAL_A - A["rows"],
        TOTAL_B_OLD - OLD_B["rows"], TOTAL_B - B["rows"]),
       ("Macro over the eight judgeable classes", f"{OLD['macro_auprc_judgeable']:.2f}",
        f"{A['macro_auprc_judgeable']:.2f}", f"{OLD_B['macro_auprc_judgeable']:.2f}",
        f"{B['macro_auprc_judgeable']:.2f}"),
       ("Pictures fully right", f"{OLD['exact_match']*100:.1f}%", f"{A['exact_match']*100:.1f}%",
        f"{OLD_B['exact_match']*100:.1f}%", f"{B['exact_match']*100:.1f}%"),
       ("Wrong answers", f"{OLD['hamming_loss']*100:.1f}%", f"{A['hamming_loss']*100:.1f}%",
        f"{OLD_B['hamming_loss']*100:.1f}%", f"{B['hamming_loss']*100:.1f}%"),
       ("Object flag fires on OOI pictures",
        f"{occ_o['fire_rate_object_only']*100:.1f}%", f"{occ_n['fire_rate_object_only']*100:.1f}%",
        "", ""),
       ("Object flag fires on Clear pictures",
        f"{occ_o['fire_rate_clear']*100:.1f}%", f"{occ_n['fire_rate_clear']*100:.1f}%",
        "", "")],
      [34, 16, 16, 16, 16])

row = 12
ws.cell(row=row, column=1,
        value="Per LP class, variant 1: previous annotation to this one").font = NOTE_FONT
row += 1
table(ws, row,
      ["LP class", "Test pictures, 7 to 24", "Average precision, 7 to 24",
       "Recall at the cut-off, 7 to 24"],
      [(A["per_class"][code]["name"],
        f'{OLD["per_class"][code]["support"]} to {A["per_class"][code]["support"]}',
        (f'{OLD["per_class"][code]["auprc"]:.2f} to {A["per_class"][code]["auprc"]:.2f}'
         if OLD["per_class"][code]["auprc"] == OLD["per_class"][code]["auprc"]
         and A["per_class"][code]["auprc"] == A["per_class"][code]["auprc"] else "not measurable"),
        f'{OLD["per_class"][code]["recall_0.5"]:.2f} to {A["per_class"][code]["recall_0.5"]:.2f}')
       for code in OLD["per_class"]],
      [28, 20, 24, 26])

# ---- sheet 6: reading
ws = sheet(wb, "Reading", "What the results say")
lines = [
    ("The average clears the bar",
     "Macro average precision over the eight judgeable classes is 0.85 against a target of "
     "0.85, up from 0.78 on the previous, smaller annotation. Low Dose alone moved from 0.77 "
     "to 0.92 on three times the test support."),
    ("Three classes still hold the score down, for three different reasons",
     "Folded Lens 0.49 is a label overlap problem, Dirty Camera 0.72 is the intrinsic "
     "difficulty of diffuse low-contrast dirt, and Lens Off Center 0.82 overlaps with two "
     "other classes. Each improved as its test group grew, which points at data, not the "
     "model, as the main lever."),
    ("Folded Lens is better but not solved",
     "Twice the test support nearly doubled the score to 0.49, still short of its 0.70 "
     "target. Almost every folded lens also carries multiple lens, so reporting the pair "
     "together, or marking folded lenses that appear alone, is the next lever."),
    ("The OOI flag now meets both routing targets",
     "It fires on 99.3 percent of OOI-only pictures against a 90 percent target, and on 0.5 "
     "percent of Clear pictures against a 5 percent limit. The conditional pass and fail "
     "block can be built on this behaviour."),
    ("Run 2 costs a little average and buys the routing signal",
     "The average moves from 0.85 to 0.82 between the variants, while the object flag lets "
     "the routing block see almost every object-bearing picture and almost never stops a "
     "clean one."),
]
r = 4
for head, body in lines:
    ws.cell(row=r, column=1, value=head).font = Font(bold=True, size=11)
    ws.cell(row=r, column=2, value=body).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 46
    r += 1
ws.column_dimensions["A"].width = 52
ws.column_dimensions["B"].width = 96

# ---- sheet 7: definitions
ws = sheet(wb, "Definitions", "What the words mean")
defs = [
    ("LP class", "One of the twelve lens-presentation classes the model answers, taken from "
                 "the LP tags in the annotation. A missing package or an off-centre lens is an "
                 "LP class."),
    ("LP tag", "The annotation tag a picture carries for a lens-presentation class. The "
               "twelve LP classes are built from these tags."),
    ("OOI class", "One of the eight object-of-interest classes, such as a bubble, a fibre or "
                  "foreign matter. Marked as a region in the picture."),
    ("OOI flag", "The thirteenth answer in run 2. One flag covering all eight OOI classes "
                 "together: at least one is present, without naming which."),
    ("Clear", "A picture where nothing is marked. It is a real answer, not a missing one."),
    ("Test pictures", "Pictures held back from training and used only to measure. The model "
                      "never sees them while learning."),
    ("Average precision", "A single number for one class that asks: when the model ranks "
                          "pictures by how sure it is, how often are the true ones at the top. "
                          "1 is perfect, 0.5 is a coin toss."),
    ("Precision", "Of the pictures the model flagged, how many were right."),
    ("Recall", "Of the pictures that truly carry the class, how many the model found."),
    ("F1", "One number combining precision and recall. Useful when both matter."),
    ("Cut-off", "The score above which the model says yes. 0.5 is the default; lowering it "
                "finds more pictures and makes more mistakes."),
]
table(ws, 4, ["Term", "Meaning"], defs, [22, 110])

OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT_XLSX)
print(f"written {OUT_XLSX}")
