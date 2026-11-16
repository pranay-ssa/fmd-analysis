"""Build the Experiment 3.1 pilot workbook.

Reader-facing. No paths, script names, run-folder names, ticket ids or version tags. Every count
names its population. No em dashes.

    .venv/Scripts/python.exe experiments/multilabel_ooi/build_exp3_1_workbook.py \
        --scores run/exp3_1_scores_20261117 \
        --out reports/multilabel_production/size_gate_pilot_20261116.xlsx
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CLASS_LABEL = {
    "foreign_matter": "Foreign Matter",
    "fiber": "Fiber",
    "extraneous_polymer": "Extraneous Polymer",
    "hema": "HEMA",
}
ARM_LABEL = {
    "stage0": "Baseline, object-class model",
    "gate4_224": "Size-trained, 224 px",
    "gate4_448": "Size-trained, 448 px",
}
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=13)


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def header(ws, title: str, line: str) -> int:
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A2"] = line
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=8)
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
        width = max(12, min(38, len(h) + 4))
        ws.column_dimensions[get_column_letter(j)].width = width
    return start + len(body) + 2


def pct(v):
    if v in ("", None):
        return "not measured"
    return round(float(v) * 100, 1)


def fmt(v, places=3):
    if v in ("", None):
        return "not measured"
    return round(float(v), places)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    src = Path(args.scores)
    per_class = rows(src / "per_class.csv")
    size_bins = rows(src / "size_bins.csv")
    per_picture = rows(src / "per_picture.csv")
    summary = json.loads((src / "summary.json").read_text(encoding="utf-8"))

    arms = [a for a in ("stage0", "gate4_224", "gate4_448")
            if any(r["set"] == a for r in per_class)]
    wb = Workbook()

    # ---------------------------------------------------------------- summary
    ws = wb.active
    ws.title = "Summary"
    r = header(ws, "Can the model tell a defect above the size cut from one below it?",
               "Four defect classes that carry a size flag. Flagged means above the cut, "
               "unflagged means below it. Every column uses the same test pictures.")
    r = table(ws, r, ["What was done", "Plain reading"], [
        ["The production rule", "A defect only fails a picture when it is above the size cut. "
                                "The record marks that with one size flag per picture, set by the "
                                "largest defect of that class."],
        ["The question", "Does a model learn the size of the defect, or only that the object is "
                         "present? A model that only sees the object will fail good pictures."],
        ["How it was tested", "The four size-flagged classes only, one output each. Training and "
                              "validation contain only pictures that carry the size flag. The test "
                              "set adds pictures of the same classes without the flag, which the "
                              "model never sees in training."],
        ["What a good result looks like", "Unflagged pictures score low and are passed; flagged "
                                          "pictures score high and are failed."],
    ])
    for arm in arms:
        head = [r_ for r_ in per_class if r_["set"] == arm and r_["class"] == "foreign_matter"][0]
        line = (f"{int(head['gated_n'])} flagged and {int(head['unflagged_n'])} unflagged Foreign "
                f"Matter pictures. AUROC {fmt(head['auroc'])}. Catches "
                f"{pct(head['recall_at_cut'])}% of flagged. {pct(head['false_fire_all'])}% of "
                f"unflagged fail, and {pct(head['false_fire_decisive'])}% of the "
                f"{int(head['decisive_n'])} where the size call decides.")
        ws.cell(row=r, column=1, value=ARM_LABEL[arm])
        ws.cell(row=r, column=2, value=line)
        r += 1
    r += 1
    ws.cell(row=r, column=1,
            value="AUROC: pick one flagged and one unflagged picture at random; it is the chance the "
                  "flagged one scores higher. 0.5 is a coin flip, 1.0 is a perfect ordering. It "
                  "does not depend on the threshold.")
    ws.cell(row=r + 1, column=1,
            value="HEMA is reported but not judged: every production HEMA picture carries the "
                  "size flag, and the few that do not are unassessed fragments, so there is no "
                  "below-cut population to test against.")

    # ------------------------------------------------- why the test has both
    ws = wb.create_sheet("Why the test has both", 1)
    r = header(ws, "Why the test set has both kinds of picture",
               "The size question is answered on untagged pictures only. A small tagged set is "
               "held back as a guard and never used to judge size.")
    r = table(ws, r, ["Point", "Plain reading"], [
        ["What was asked", "Training and validation contain size-tagged pictures only. The test "
                           "shows the model pictures without the tag."],
        ["What we did", "Exactly that, plus a small set of tagged pictures held back from "
                        "training and never used in the size tables."],
        ["Why the guard is needed", "On untagged pictures alone, a model that never flags "
                                    "anything scores 100%. The guard is the only way to see "
                                    "whether real above-cut defects are still caught."],
        ["How the numbers are read", "Size is read from the untagged column: false-fail rate and "
                                     "AUROC. The tagged column is recall, read on its own. The "
                                     "two are never added together."],
        ["No leakage", "The tagged guard pictures were not in training or validation for any "
                       "model in this workbook."],
        ["Fair comparison", "Every model is scored on the same untagged pictures, so the columns "
                            "compare like with like."],
    ])
    ws.cell(row=r, column=1,
            value="Counts for Foreign Matter: 380 untagged pictures for the size read, 79 tagged "
                  "pictures in the guard.")

    # --------------------------------------------------------------- size read
    ws = wb.create_sheet("Size read")
    r = header(ws, "The size read, one row per class and model",
               "Flagged is counted as fail, unflagged as pass, Bubble and Clear as pass, every "
               "other class as fail. Test pictures only, carrying the class.")
    body = []
    for arm in arms:
        for c in CLASS_LABEL:
            m = [x for x in per_class if x["set"] == arm and x["class"] == c]
            if not m:
                continue
            m = m[0]
            body.append([
                ARM_LABEL[arm], CLASS_LABEL[c], fmt(m["cut"], 2), fmt(m["auroc"]),
                int(m["gated_n"]), int(m["unflagged_n"]), int(m["decisive_n"]),
                pct(m["recall_at_cut"]), pct(m["false_fire_all"]),
                pct(m["false_fire_decisive"]),
                "yes" if m["measurable"] == "yes" else m["measurable"],
            ])
    r = table(ws, r, ["Model", "Class", "Threshold", "AUROC",
                      "Flagged pictures", "Unflagged pictures", "Unflagged, size call decides",
                      "Recall, flagged caught (%)", "False-fail rate, all unflagged (%)",
                      "False-fail rate, size call decides (%)",
                      "Judgeable"], body)
    ws.cell(row=r, column=1,
            value="Unflagged pictures that carry another failing label are counted in 'Unflagged "
                  "failed' but not in the last column: they fail whatever the size call was.")

    # ------------------------------------------------------------ score and size
    ws = wb.create_sheet("Score and size")
    r = header(ws, "How the score moves with defect size",
               "Mean score by the longest side of the largest defect of that class, in native "
               "pixels, test pictures only. The size cut sits at about 19.5 px on production "
               "pictures.")
    body = []
    for arm in arms:
        for c in ("foreign_matter", "fiber", "extraneous_polymer"):
            part = [x for x in size_bins if x["set"] == arm and x["class"] == c]
            if not part:
                continue
            row = [ARM_LABEL[arm], CLASS_LABEL[c]]
            for b in ["0-8", "8-12", "12-18", "18-24", "24-36", "36-64", "64-max"]:
                cell = [x for x in part if x["bin_px"] == b]
                row.append(fmt(cell[0]["mean_score"]) if cell else "")
            body.append(row)
    table(ws, r, ["Model", "Class", "0-8 px", "8-12 px", "12-18 px", "18-24 px",
                  "24-36 px", "36-64 px", "64 px and up"], body)

    # ---------------------------------------------------------------- pass/fail
    ws = wb.create_sheet("Pass-fail")
    r = header(ws, "Pass and fail on the pictures where the size call alone decides",
               "These pictures carry one of the four classes without its size flag and no other "
               "failing label. The verdict is therefore exact on them. The wider test population "
               "is scored on the object classes only and is not a production verdict.")
    body = []
    for arm in arms:
        p = summary["sets"][arm]["pass_fail_decisive"]
        body.append([ARM_LABEL[arm], p["population"], p["failed"], p["passed"],
                     pct(p["failed"] / p["population"]) if p["population"] else "",
                     pct(p["passed"] / p["population"]) if p["population"] else ""])
    r = table(ws, r, ["Model", "Pictures where the size call decides", "Failed", "Passed",
                      "Share failed (%)", "Share passed (%)"], body)
    ws.cell(row=r, column=1,
            value="The full test population has 1,533 pictures. A verdict on all of them would "
                  "need every failing class, which this pilot does not model.")

    # -------------------------------------------------------------- per picture
    ws = wb.create_sheet("Per picture")
    r = header(ws, "Every test picture, its scores and its verdict",
               "One row per test picture that carries any of the four classes. Scores are the "
               "model's own, 0 to 1. 'Size call decides' marks the pictures where no other "
               "failing label is present.")
    heads = ["Model", "Picture", "Foreign Matter", "Fiber", "Extraneous Polymer", "HEMA",
             "Columns that fired", "Verdict", "Size call decides"]
    body = [[ARM_LABEL[x["set"]], x["md5"], x.get("foreign_matter", ""), x.get("fiber", ""),
             x.get("extraneous_polymer", ""), x.get("hema", ""), x["fired"], x["verdict"],
             "yes" if x["decisive"] == "1" else ""] for x in per_picture]
    table(ws, r, heads, body)

    # -------------------------------------------------------------- definitions
    ws = wb.create_sheet("Definitions")
    r = header(ws, "Terms used in this workbook",
               "One line each, so the tables can be read without the internal notes.")
    r = table(ws, r, ["Term", "Meaning"], [
        ["Size flag", "A mark on a picture saying that a defect of that class is above the size "
                      "cut. One flag per picture, set by the largest defect of that class."],
        ["Flagged picture", "A picture of one of the four classes that carries the size flag."],
        ["Unflagged picture", "A picture of the same class with no size flag. On production "
                              "pictures this means the defect is below the cut."],
        ["Size call decides", "The picture carries no other failing label, so passing or failing "
                              "it depends only on whether the size call is right."],
        ["AUROC", "Chance that a flagged picture scores higher than an unflagged one, taken over "
                 "every flagged and unflagged pair. 0.5 is a coin flip, 1.0 is a perfect "
                 "ordering. It does not depend on the threshold."],
        ["Threshold", "The score above which a picture is called flagged. Chosen on validation "
                    "pictures only, never on test."],
        ["Decisive", "See 'Size call decides'."],
        ["Guard set", "Tagged pictures held back from training and scored separately, to check "
                      "that real above-cut defects are still caught. They are never used to "
                      "judge size."],
    ])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"wrote {out} with {len(wb.sheetnames)} sheets: {wb.sheetnames}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
