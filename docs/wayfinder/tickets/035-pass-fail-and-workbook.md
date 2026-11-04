---
title: "Ticket 035: pass/fail read and the point-4 workbook"
date: 2026-11-04
type: protocol
status: done
where: docs/wayfinder/tickets/035-pass-fail-and-workbook.md
---
Type: build, AFK. Map: Map: [OOI point 4](../ooi_point4_map.md)..

## Question

What does the agreed pass/fail rule do on the winning arm's test predictions, and can the
whole point-4 result be handed over in one verified workbook?

## Spec

- Rule, agreed 2026-11-04: a picture passes only if it is clear or carries nothing but
  bubble classes (Bubble, Bubble Cluster); everything else fails, including all twelve
  lens tags, Wet Package, Foreign Matter, Fiber, Extraneous Polymer, HEMA, Surface Groove
  and Bubble Scatter. Truth: 2,117 clear + 196 bubble-only pass, 5,157 fail (test 768/353).
  A picture fails if any fail-class column fires at its cut; the OR is the rule, not a
  second model.
- Report caught, clear passed, clear wrongly failed at 0.5 and at the chosen cuts, against
  the November reference (86.1 percent caught, 12 clear wrongly failed at 0.5).
- Workbook via a builder and an independent verifier that recomputes from the saved
  predictions and catches a tampered cell. Sheets: summary, object class table with the
  prevalence floors, thresholds with the guard, curves for the supported classes, the
  pass/fail table, definitions. Client-safe: no paths, no script names, no internal ids;
  every count names its population.
- Also report the recall-by-flag diagnostic (gated versus un-gated) for the four gated
  classes in the workbook's method notes.

## Done when

Verifier exits 0 with the tamper proof caught; the workbook is written under
`reports/multilabel_production/` beside the November one.

## Resolution (2026-11-04, ticket 035)

### The rule on the winning arm (combined head; test split 768 fail / 353 pass = 317 clear + 36 bubble-only)

| Operating point | Fail pictures caught | Clear pictures passed | Clear wrongly failed | Pass pictures predicted pass |
|---|---|---|---|---|
| At 0.5 | 760 of 768 (99.0 percent) | 316 of 317 (99.7 percent) | 1 of 317 | 324 of 353 (91.8 percent) |
| At chosen cuts | 759 of 768 (98.8 percent) | 316 of 317 (99.7 percent) | 1 of 317 | 325 of 353 (92.1 percent) |

November model read under the same rule, same populations: 710 of 768 (92.4 percent)
at 0.5 and 730 of 768 (95.1 percent) at its own chosen cuts, with 3 of the 317 clear
test pictures wrongly failed at both points. The 1 clear and 28 bubble-only test
pictures the winning arm fails at 0.5 fail on lens tags and object classes firing,
never on the bubble columns.

### The November reference reproduces, and it is lens scoped

86.1 percent caught = 589 of the 684 lens-tagged test pictures at 0.5; 12 clear
wrongly failed and 97.3 percent clear passed = 425 of the 437 test pictures without a
lens tag. The recorded reference therefore counts only the twelve lens tags as the
defect and only pictures without a lens tag as clear, so it does not sit on the
rule's 768 / 317 population. The like-for-like row is the November model under the
rule (92.4 percent at 0.5), which the workbook reports beside it.

### Workbook and verifier

- `reports/multilabel_production/ooi_point4_workbook_20261104.xlsx`, seven sheets:
  Summary; Object classes with prevalence floors and the Bubble/Cluster confusion;
  Thresholds with the guard; F1 against the cut for the seven supported object
  classes; Pass-fail with block A on the rule's populations and block B on the
  reference's lens scope; Method notes carrying the recall-by-flag diagnostic
  (Foreign Matter 72/40, Fiber 56/2, Extraneous Polymer 17/0, HEMA 27/0, gated then
  un-gated test pictures, recall at 0.5 and at the chosen cut); Definitions.
- Builder `experiments/multilabel_ooi/build_point4_workbook.py`, verifier
  `experiments/multilabel_ooi/verify_point4_workbook.py`. The verifier shares no
  code with the builder: it recomputes 465 cells from the saved scores and the label
  table, checks the sheet list, the required headings, the definition terms and the
  client-safe sweep (no paths, no script names, no internal column ids, no em
  dashes), and fails naming the cell.
- Verifier exits 0 on the workbook as written. Tamper proofs, each exit 1 naming its
  cell: caught count 760 to 761 names `Pass-fail!B5`; Bubble average precision
  0.9473770597 to 0.997377 names `Object classes!F4`; row label Foreign Matter to
  Foreign-Matter names `Method notes!A17`; a cell rewritten to name a path, a script
  and a predictions file names `Summary!A2`.
- Cross-checks inside the builder: split truth 5,157 fail / 2,313 pass with 2,117
  clear and 196 bubble-only, test truth 768 / 353 with 317 clear and 36 bubble-only;
  macro average precision 0.6380419266 over the seven supported object classes and
  0.8815123493 over the eight judgeable lens classes both equal the recorded
  metrics; November's 0.8182347079 re-derives from its own scores; both Bubble and
  Cluster confusion tables and all 24 recall-by-flag cells equal the recorded
  metrics; every cut equals the recorded cut and every guarded class has fewer than
  10 validation pictures.

### Scope and hygiene

HEAD unchanged at 5ab3467ff31b93870f6f50fde92f8eee67d9102c. New files: the two
scripts under `experiments/multilabel_ooi/` and the workbook under
`reports/multilabel_production/`. This resolution plus the deterministic
`tools/index_docs.py --check` regeneration of `docs/INDEX.md` are the only edits to
tracked files; nothing was committed. Client-safe sweep of the finished workbook:
0 breaches.
