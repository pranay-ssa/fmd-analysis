---
title: "Ticket 044: Experiment 3.1 workbook and verifier"
date: 2026-11-16
type: protocol
status: active
where: docs/wayfinder/tickets/044-exp3-1-workbook.md
---
Type: build, AFK. Map: [Experiment 3.1](../exp3_1_size_gate_20261116.md).

## Question

Can the pilot be handed over as one workbook that a lead can read without our internal names, and
that a verifier can recompute cell by cell?

## Spec

Sheets, in this order:

1. **Summary**: one plain line saying what the pilot asked, then the headline table: per arm, per
   class, AUROC with supports, false-fire on all and on decisive pictures, recall. HEMA carries
   `not measurable` in the value cell with the reason in the same row.
2. **Size read**: one row per gated class, size-flagged counted as fail, unflagged as pass, Bubble
   and Clear as pass, every other class as fail. Supports, recall, false fire, AUROC.
3. **Pass/fail**: the usual caught / clear passed / bubble-only passed / overall counts, plus the
   column that drove each fail, on the 99 decisive pictures, and the object-side-only read on the
   full test population under a header that says so.
4. **Per picture**: truth, verdict, columns fired, gate status, decisive flag, largest box in px
   and microns. Filterable, no formulas that hide the source value.

Rules: client-safe (no paths, no script or run-folder names, no ticket ids, no version tags),
every count names its population, no em dashes, definitions sheet or a definitions block for
decisive, gate, AUROC and false-fire. The workbook is internal for now but may go to the lead, so
write it to the reader-facing standard.

Builder `experiments/multilabel_ooi/build_exp3_1_workbook.py`, verifier
`verify_exp3_1_workbook.py`, sharing no code. The verifier recomputes every numeric cell from
`per_class.csv`, `per_picture.csv` and `picture_detail.csv`, checks the sheet list and headings,
and sweeps for paths, script names, ticket ids and em dashes.

## Done when

Verifier exits 0 on the workbook as written, and at least three tamper proofs each exit 1 naming
the cell. Report the workbook path and the verifier output.
