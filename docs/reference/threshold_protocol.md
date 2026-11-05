---
title: Threshold selection protocol
date: 2026-11-04
type: method
status: active
where: docs/reference/threshold_protocol.md
---

# Threshold selection protocol

The rule for turning model scores into per-class decisions. Written after comparing our LP threshold
workbook against a teammate's independent grid search, where the two used the same predictions and reached
opposite conclusions about how well the thresholds work. Run this whenever a model is retrained on new or
larger data. The cuts never carry over between datasets; the rule does.

## The rule

1. **Choose on validation, score on test once.** Every cut comes from validation pictures only. Freeze all
   cuts before the test set is read. No test-driven adjustment, not even by one grid step.
2. **Grid 0.01 to 0.99, step 0.01, hard floor 0.05.** The floor matters: a cut of 0.0 reports every picture
   as carrying the class, and on a class with one positive that is the F1 optimum. Never allow it.
3. **Maximise F1 subject to a validation precision floor of 0.5.** Report the 0.6 variant as a sensitivity
   row. The floor is what stops a weak class from buying recall with false alarms.
4. **If no cut clears the floor, the class predicts nothing.** Record it as "not predictable at this data
   volume". Never default it to 0.5, which silently answers "present" on half the score range, and never
   let it select 0.0.
5. **Prefer the plateau centre to the peak.** Among cuts within 0.02 F1 of the maximum, take the middle.
   Record both the peak and the chosen cut. This is what keeps a one-step grid change from moving the
   quoted number.
6. **Require cut stability across seeds.** Train two seeds. A cut that moves more than 0.05 between them is
   a property of the seed, not of the class, and is quoted as a range rather than a number.
7. **Report per class:** cut, validation precision and recall, test precision and recall, test false
   positives, support, and that class's share of the Hamming loss.
8. **Two picture-level operating points:** balanced and precision-first. A pass/fail reader cares about
   wrongly failed clear pictures far more than about macro F1.
9. **Never carry a cut across datasets.** Re-derive everything when the pictures change. A cut is a
   property of the score distribution, and the distribution moves with the data.

## Why each rule exists, with the measurements

Same model, same split, same saved scores. The only difference between the rows is the selection rule.

| Rule | Hamming val | Hamming test | View Obstructed test F1 | Dirty Strobe and Bubble Scatter |
|---|---|---|---|---|
| Grid 0.0 to 1.0, step 0.1, no constraint | 0.1904 | 0.1910 | 0.889 | predict every picture |
| Count guard, minimum 10 validation pictures, default 0.5 | 0.0243 | 0.0250 | 0.000 | silent |
| Count guard, minimum 8, default 0.5 | 0.0243 | 0.0248 | 0.889 | Dirty Strobe tuned to 0.05, 5 false positives, no test gain |
| Precision floor 0.6 | 0.0219 | 0.0225 | 0.889 | predict nothing |
| Fixed 0.5, no tuning | 0.0253 | 0.0242 | 0.000 | n/a |

The unconstrained grid search made 2,570 wrong tag decisions on 13,452 test cells, 7.9 times the error of
a fixed 0.5 and 2.7 times the error of predicting nothing. Two classes at a cut of 0.0 produced 2,211 of
the 2,536 validation errors on their own. A precision floor removes that whole failure mode and also
recovers the class the count guard suppressed.

The count guard's cost is real and was already visible in our workbook: View Obstructed has 9 validation
pictures and 10 test pictures, reaches validation F1 1.000 with no false positives, and scores 0.889 on
test at a cut of 0.2. Under a guard of 10 it keeps 0.5 and reports 0.000. A minimum picture count is a
proxy for "can this class support a cut", and precision answers that question directly.

## What the workbook must contain

| Sheet | Content |
|---|---|
| Summary | the recommendation in three lines, the two operating points, the picture-level table |
| Selected thresholds | one row per class: cut, validation P/R/F1, test P/R/F1, test false positives, support |
| Threshold curves | F1 against cut per class, from the same grid, so the plateau is visible |
| Error audit | per-class false positives and their share of Hamming loss |
| Method | the rule, the grid, the floor, the guard, the seed count, stated plainly |
| Definitions | cut, support, precision, recall, F1, Hamming, exact match, operating point |

The selected thresholds sheet is not optional. A workbook whose only per-class table is the test-optimal
ceiling cannot be applied by its reader, and a ceiling is easy to mistake for a setting.

## Distinguish the two questions

A **ceiling** table answers "how much signal is in these scores". It chooses each cut on the same pictures
it scores and must be labelled as a ceiling on every sheet that carries it. A **selected thresholds**
table answers "what do we ship". It chooses on validation and scores once on test. Both are useful; mixing
them in one table, or omitting the second, is how a reader applies an unreachable number.

## Failure modes this protocol is built against

- **The degenerate cut.** A rare class maximises F1 by firing on everything. Rule 2 and rule 3 both block it.
- **The coarse grid.** Dirty Strobe's best cut is 0.05, which a 0.1 grid never tests; at 0.0 it looks like a
  threshold when it is not one. Rule 2.
- **The count guard.** Excludes classes with clean signal because they are rare. Rule 3.
- **The default cut.** A class left untuned at 0.5 is still making decisions. Say "predicts nothing"
  explicitly if that is the intent. Rule 4.
- **The single peak.** A cut chosen on one step of one seed moves when either changes. Rules 5 and 6.
- **The aggregate that hides its cause.** Hamming and exact match are dominated by the worst class; always
  publish the per-class false positive count beside them. Rule 7.
- **The carried-over cut.** The 2026 thresholds describe a 1,121-picture test set; a full-data model has a
  different score distribution. Rule 9.

## Checklist before quoting any threshold number

1. Was the cut chosen on validation pictures, and were the test pictures read once?
2. Is the class above the precision floor, or is it recorded as not predictable?
3. Is the quoted F1 from the plateau centre or from a single step?
4. How many seeds, and did the cut agree between them?
5. Is the table a ceiling or a selected threshold, and does the sheet say which?
6. Is the per-class false positive count visible next to any aggregate?
