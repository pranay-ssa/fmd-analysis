"""Experiment 3.2 workbook: the redo of Experiment 1 under the size correction.

Two models, one verdict, two rule orders. Reader-facing: no internal paths, script names, ticket
ids or version tags. Every count names its population. No em dashes.

    .venv/Scripts/python.exe experiments/multilabel_ooi/build_exp3_2_workbook.py \
        --scores run/exp3_2_scores_20261116 \
        --size-scores run/exp3_1_scores_20261117 \
        --labels run/split_exp3_2_20261116/labels_19.csv \
        --gate-meta run/split_exp3_1_20261116/meta.json \
        --out reports/multilabel_production/size_gate_redo_20261116.xlsx
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

COND_LABEL = {
    "P1_MPP": "Missing Primary Package", "P1_ML": "Multiple Lens",
    "P2_LOC": "Lens Off Center", "P2_DC": "Dirty Camera", "P1_NL": "No Lens",
    "P1_FL": "Folded Lens", "P2_LD": "Low Dose", "P1_COC": "Cavity Off Center",
    "P2_DS": "Dirty Strobe", "P2_FOV": "View Obstructed", "P2_BSC": "Bubble Scatter",
    "P1_PPM": "Package Misalignment", "class_bubble": "Bubble",
    "class_bubble_cluster": "Bubble Cluster", "class_wet_package": "Wet Package",
}
SIZE_LABEL = {"foreign_matter": "Foreign Matter", "fiber": "Fiber",
              "extraneous_polymer": "Extraneous Polymer", "hema": "HEMA"}
ARM_LABEL = {"stage0": "Baseline, object-class model",
             "gate4_224": "Size-trained", "gate4_448": "Size-trained, double resolution"}
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=13)


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def header(ws, title: str, line: str, width: int = 8) -> int:
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A2"] = line
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    ws.row_dimensions[2].height = 30
    return 4


def table(ws, start: int, headers: list[str], body: list[list]) -> int:
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=start, column=j, value=h)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for i, r in enumerate(body, start + 1):
        for j, v in enumerate(r, 1):
            ws.cell(row=i, column=j, value=v)
    for j, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(j)].width = max(12, min(40, len(h) + 4))
    return start + len(body) + 2


def pct(v):
    if v in ("", None):
        return ""
    return round(float(v) * 100, 1)


RULE_ROWS = [
    ["Clear only", "pass", "pass"],
    ["Bubble only", "pass", "pass"],
    ["Bubble Cluster", "fail", "pass"],
    ["Any of the twelve lens conditions", "fail", "fail"],
    ["Wet Package", "fail", "fail"],
    ["A size-flagged class below the cut (untagged)", "pass", "pass"],
    ["A size-flagged class above the cut", "fail", "fail"],
]


def what_we_did(wb) -> None:
    ws = wb.create_sheet("What we did", 1)
    r = header(ws, "What we did, step by step",
               "How the redo of Experiment 1 was built and scored. Same pictures as Experiment 1, "
               "two models, one verdict.", 2)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 104
    r = table(ws, r, ["Step", "Detail"], [
        ["The question",
         "Experiment 1 asked whether one model can hold the twelve lens conditions and the seven "
         "object classes at once, and applied one pass/fail rule. The redo asks the same question "
         "with the corrected rule order, and treats the size of the four flagged classes as a "
         "separate question rather than a property of the object."],
        ["Why two models",
         "A picture cannot be both a training example for its lens condition and an unseen "
         "example for its size class. Splitting the work keeps the lens results on exactly the "
         "same pictures as Experiment 1, and keeps the size question on pictures the size model "
         "has never seen."],
        ["Model one, the conditions",
         "Reads the twelve lens conditions plus Bubble, Bubble Cluster and Wet Package. Fifteen "
         "outputs. Trained on the frozen picture assignment: 5,239 training and 1,110 validation "
         "pictures, the same pictures Experiment 1 used."],
        ["Model two, the size",
         "Reads the four size-flagged classes: Foreign Matter, Fiber, Extraneous Polymer and "
         "HEMA. Four outputs. Trained only on pictures that carry the size flag, meaning the "
         "defect is above the cut. Validation holds flagged pictures only as well."],
        ["The test set",
         "The condition model is scored on the same 1,121 test pictures as Experiment 1. The "
         "size model is scored on all 1,533 test pictures, which include untagged pictures of "
         "each class: 380 Foreign Matter, 43 Fiber, 40 Extraneous Polymer and 6 HEMA. Untagged "
         "means below the cut. The tagged test pictures are the guard: without them, a model "
         "that never fires would look perfect."],
        ["Training settings",
         "Resolution 224 pixels, 50 epochs, batch 8, learning rate 0.0001, seed 42, class "
         "weighting on. The same recipe the earlier size experiment used, so the two are "
         "comparable."],
        ["Choosing the threshold",
         "One threshold per class, chosen on validation pictures only, at the value that "
         "maximises F1. Test pictures play no part in choosing it."],
        ["Forming the verdict",
         "A picture fails if either model fires a failing label. It passes only when neither "
         "does. A picture carrying several labels takes the strictest outcome: one failing label "
         "is enough."],
        ["What changed against Experiment 1",
         "Two things. Bubble Cluster moved to the fail side, which is the new order from the "
         "client and lead. The four size-flagged classes are judged by the size flag, not by the "
         "object being present, so a below-cut picture passes. The models, the training pictures "
         "and the test pictures are unchanged."],
    ])
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=2, max_col=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    r = table(ws, r, ["Label present in truth", "Primary rule", "Secondary rule"], RULE_ROWS)
    ws.cell(row=r, column=1,
            value="The two rules differ in one row only: Bubble Cluster. Everything else is "
                  "identical, which is why the two results sit close together.")
    ws.cell(row=r + 1, column=1,
            value="Not shown here: a comparison across repeat runs with different seeds, and any "
                  "confirmation of the pass set by the client. Both are open.")


def all_classes_sheet(wb, cond_path: Path, size_path: Path) -> None:
    ws = wb.create_sheet("All classes table", 4)
    r = header(ws, "Every class, one table",
               "Threshold, AUROC, precision, recall and F1 for the fifteen condition classes and "
               "the four size classes. Every threshold is chosen on validation pictures only.", 8)
    body = []
    for x in rows(cond_path):
        body.append([COND_LABEL.get(x["class"], x["class"]), "Condition model",
                     int(x["support"]), round(float(x["threshold"]), 2),
                     round(float(x["auroc"]), 3), round(float(x["precision"]), 3),
                     round(float(x["recall"]), 3), round(float(x["f1"]), 3)])
    for x in rows(size_path):
        body.append([x["class"], x["read_by"], int(x["population"]), float(x["threshold"]),
                     float(x["auroc"]), float(x["precision"]), float(x["recall"]),
                     float(x["f1"])])
    r = table(ws, r, ["Class", "Read by", "Test pictures carrying it", "Threshold", "AUROC",
                      "Precision", "Recall", "F1"], body)
    ws.cell(row=r, column=1,
            value="The condition rows are measured on the same 1,121 test pictures as Experiment "
                  "1. The size rows are measured on every test picture that carries the class, "
                  "flagged and untagged together, so the Foreign Matter row rests on 459 pictures "
                  "and the HEMA row on 58.")
    ws.cell(row=r + 1, column=1,
            value="Bubble Scatter has one test picture, so its precision, recall and F1 are "
                  "noise. HEMA has 6 untagged test pictures out of 58, so its high scores rest "
                  "mostly on pictures like those it trained on.")


def pictures_per_class(wb, labels_path: Path, gate_meta: Path) -> None:
    ws = wb.create_sheet("Pictures per class")
    r = header(ws, "Pictures per class, by split",
               "The condition model sees every picture under the frozen assignment. The size "
               "model sees flagged pictures only in training and validation, and both flagged "
               "and untagged pictures at test.", 6)

    cond = rows(labels_path)
    body = []
    for key, label in COND_LABEL.items():
        if key not in cond[0]:
            continue
        d = {s: sum(1 for x in cond if x["split"] == s and x[key] == "1")
             for s in ("train", "val", "test")}
        group = "Lens condition" if key.startswith("P") else "Object class"
        body.append([label, group, d["train"], d["val"], d["test"],
                     d["train"] + d["val"] + d["test"]])
    r = table(ws, r, ["Class", "Group", "Train", "Validation", "Test", "All pictures"], body)
    ws.cell(row=r, column=1,
            value="A picture can carry several classes, so the columns do not add to the split "
                  "size. The split itself is 5,239 train, 1,110 validation and 1,121 test.")

    meta = json.loads(Path(gate_meta).read_text(encoding="utf-8"))
    body = []
    for key, label in SIZE_LABEL.items():
        c = meta["by_class"][{"foreign_matter": "fm", "fiber": "fiber",
                              "extraneous_polymer": "ep", "hema": "hema"}[key]]
        body.append([label, c["train_gated"], c["val_gated"], c["test_gated"],
                     c["test_unflagged"], c["test_gated"] + c["test_unflagged"]])
    r = table(ws, r, ["Class", "Train, flagged", "Validation, flagged", "Test, flagged",
                      "Test, untagged", "Test, all carrying the class"], body)
    ws.cell(row=r, column=1,
            value="Flagged means the defect is above the size cut and the picture fails on that "
                  "class. Untagged means below the cut and the picture passes on that class. "
                  "Training and validation hold flagged pictures only, zero untagged.")
    ws.cell(row=r + 1, column=1,
            value="The size model's split is 4,964 training, 1,058 validation and 1,533 test. "
                  "The condition model's split is 5,239 training, 1,110 validation and 1,121 "
                  "test. They differ because 412 pictures moved into test so that no untagged "
                  "picture of a flagged class sits in training or validation.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True)
    ap.add_argument("--size-scores", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels", required=True,
                    help="labels_19.csv: per-split counts for the fifteen condition classes")
    ap.add_argument("--gate-meta", required=True,
                    help="meta.json of the size split: flagged and untagged counts per class")
    ap.add_argument("--size-classes", required=True,
                    help="CSV of threshold, AUROC, precision, recall and F1 for the size classes")
    args = ap.parse_args()
    src = Path(args.scores)
    pf = rows(src / "pass_fail.csv")
    cond = rows(src / "conditions.csv")
    per_pic = rows(src / "per_picture.csv")
    summary = json.loads((src / "summary.json").read_text(encoding="utf-8"))
    size_rows = rows(Path(args.size_scores) / "per_class.csv")

    wb = Workbook()

    # ---------------------------------------------------------------- summary
    ws = wb.active
    ws.title = "Summary"
    r = header(ws, "Pass and fail after the size correction, with the new rule order",
               "Same 1,121 test pictures as Experiment 1. Two models: one reads the twelve lens "
               "conditions and the three other object classes, one reads the four size-flagged "
               "classes. A picture passes only when neither model fires a failing label.")
    r = table(ws, r, ["Point", "Plain reading"], [
        ["Two things changed", "Bubble Cluster moved to the fail side, which is the new order "
                               "from the client and lead. The four size-flagged classes are now "
                               "judged by the size flag, not by whether the object is present, "
                               "so a below-cut picture passes."],
        ["What did not change", "The training pictures, the test pictures and the pass set for "
                                "everything else."],
        ["The size correction", "Two pictures that used to fail because the object was present "
                                "now pass because it is below the cut. Measured with the same two "
                                "models, fail pictures went from 768 to 766, so the difference is "
                                "arithmetic only, not a different model."],
        ["The rule order", "Bubble Cluster now fails, which adds 18 pictures. Fail pictures "
                           "went from 766 to 784."],
        ["Checked against Experiment 1", "Applying the earlier reading, where the object being "
                                         "present is enough to fail, to the same two models "
                                         "gives 768 fail and 353 pass. That is exactly the "
                                         "Experiment 1 number, so the two changes above are "
                                         "measured from a known starting point."],
        ["The headline", "99.2% of failing pictures are caught. 92.3% of passing pictures pass. "
                         "The rates barely move because the verdict is still driven by the lens "
                         "conditions, not by size."],
    ])
    r = table(ws, r, ["Rule", "Fail pictures", "Caught", "Missed", "Pass pictures", "Passed",
                      "Wrongly failed"], [
        ["Primary, Bubble Cluster fails", int(pf[0]["fail_pictures"]), int(pf[0]["caught"]),
         int(pf[0]["missed"]), int(pf[0]["passed_ok"]) + int(pf[0]["wrongly_failed"]),
         int(pf[0]["passed_ok"]), int(pf[0]["wrongly_failed"])],
        ["Secondary, Bubble Cluster passes", int(pf[1]["fail_pictures"]), int(pf[1]["caught"]),
         int(pf[1]["missed"]), int(pf[1]["passed_ok"]) + int(pf[1]["wrongly_failed"]),
         int(pf[1]["passed_ok"]), int(pf[1]["wrongly_failed"])],
    ])
    ws.cell(row=r, column=1,
            value="Under the primary rule the Bubble Cluster column fires on 18 of the 26 wrong "
                  "fails, on its own in 7 of them. Under the secondary rule that job moves to the "
                  "Foreign Matter size call, which fires on 19 of 30, on its own in 14.")

    what_we_did(wb)

    # --------------------------------------------------------------- pass/fail
    ws = wb.create_sheet("Pass-fail")
    r = header(ws, "Pass and fail, both rules",
               "Population: the 1,121 test pictures that neither model saw in training. A fail "
               "picture carries at least one failing label in truth; a pass picture carries none.",
               9)
    body = []
    for x in pf:
        pop = int(x["population"])
        body.append([x["rule"], pop, int(x["fail_pictures"]), int(x["caught"]),
                     pct(x["share_fail_caught"]), int(x["missed"]),
                     int(x["passed_ok"]) + int(x["wrongly_failed"]),
                     pct(x["share_pass_passed"]), int(x["wrongly_failed"])])
    table(ws, r, ["Rule", "Pictures", "Fail pictures", "Caught", "Share of fail caught (%)",
                  "Missed", "Pass pictures", "Share of pass passed (%)", "Wrongly failed"], body)

    # -------------------------------------------------------------- conditions
    ws = wb.create_sheet("Conditions")
    r = header(ws, "The fifteen condition classes",
               "Population: the 1,121 test pictures. Threshold chosen on validation pictures "
               "only. Bubble Cluster is on the fail side under the primary rule and on the pass "
               "side under the secondary rule.", 8)
    body = [[COND_LABEL.get(x["class"], x["class"]), int(x["support"]), round(float(x["auroc"]), 3),
             round(float(x["threshold"]), 2), round(float(x["precision"]), 3),
             round(float(x["recall"]), 3), round(float(x["f1"]), 3)]
            for x in cond]
    r = table(ws, r, ["Class", "Test pictures carrying it", "AUROC", "Threshold",
                      "Precision", "Recall", "F1"], body)
    ws.cell(row=r, column=1,
            value="Bubble Scatter has one test picture, so its F1 is noise and is not a result.")

    all_classes_sheet(wb, src / "conditions.csv", Path(args.size_classes))

    pictures_per_class(wb, Path(args.labels), Path(args.gate_meta))

    # ---------------------------------------------------------------- size read
    ws = wb.create_sheet("Size read")
    r = header(ws, "The four size-flagged classes",
               "Read from the size specialist. Population: the 1,533 test pictures of the size "
               "split, restricted to those carrying the class. Flagged pictures should fail, "
               "untagged pictures should pass.", 10)
    body = []
    for arm in ("stage0", "gate4_224", "gate4_448"):
        for c, label in SIZE_LABEL.items():
            m = [x for x in size_rows if x["set"] == arm and x["class"] == c]
            if not m:
                continue
            m = m[0]
            body.append([ARM_LABEL[arm], label, round(float(m["cut"]), 2),
                         round(float(m["auroc"]), 3), int(m["gated_n"]), int(m["unflagged_n"]),
                         pct(m["recall_at_cut"]), pct(m["false_fire_all"]),
                         pct(m["false_fire_decisive"])])
    r = table(ws, r, ["Model", "Class", "Threshold", "AUROC", "Flagged pictures",
                      "Untagged pictures", "Recall (%)", "False-fail rate, all untagged (%)",
                      "False-fail rate, size call decides (%)"], body)
    ws.cell(row=r, column=1,
            value="HEMA is not judgeable: every production HEMA picture carries the size flag.")

    # -------------------------------------------------------------- per picture
    ws = wb.create_sheet("Per picture")
    r = header(ws, "Every test picture under both rules",
               "One row per picture per rule. Truth is the annotation; predicted is what the two "
               "models said together.", 6)
    body = [[x["rule"], x["md5"], x["truth"], x["predicted"], x["truth_labels"], x["fired"]]
            for x in per_pic]
    table(ws, r, ["Rule", "Picture", "Truth", "Predicted", "Failing labels in truth",
                  "Failing labels fired"], body)

    # -------------------------------------------------------------- definitions
    ws = wb.create_sheet("Definitions")
    r = header(ws, "Terms used in this workbook",
               "One line each, so the tables can be read without the internal notes.", 2)
    r = table(ws, r, ["Term", "Meaning"], [
        ["Pass picture", "A picture with no failing label: clear, or Bubble only, or a "
                         "size-flagged class that is below the cut, and nothing else."],
        ["Fail picture", "A picture carrying at least one failing label: a lens condition, Wet "
                         "Package, a size-flagged defect above the cut, and Bubble Cluster "
                         "under the primary rule."],
        ["Size flag", "A mark saying a defect of that class is above the size cut. One flag per "
                      "picture, set by the largest defect of that class."],
        ["Untagged picture", "A picture of a gated class with no size flag, meaning below the "
                             "cut. It passes on that class and only that class."],
        ["AUROC", "Chance that a failing picture scores above a passing one. 0.5 is a coin "
                  "flip, 1.0 is a perfect ordering."],
        ["Threshold", "The score above which a label is called present. Chosen on validation "
                      "pictures only."],
        ["Recall", "Of the pictures truly carrying a label, the share the model fires on."],
        ["False-fail rate", "Of the pictures not carrying a label, the share the model fires on."],
        ["Bubble Cluster", "A cluster of bubbles. It fails under the primary rule and passes "
                           "under the secondary rule."],
    ])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"wrote {out} with {len(wb.sheetnames)} sheets: {wb.sheetnames}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
