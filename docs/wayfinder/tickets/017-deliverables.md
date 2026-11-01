---
title: "Ticket 017: the deliverables"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/017-deliverables.md
---

# 017: The deliverables

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 016.

## Resolution (2026-10-15)

Done. The set is in `reports/eda_full/`:

| Artifact | What it holds |
|---|---|
| `FMD_Full_EDA_20261015.xlsx` | 10 sheets: Read me, Census, Labels, Distributions, Box geometry, Blind scale, Micron gate, Coverage, Crosswalk, Checks. 34 to 80 rows each, all populated |
| `full_eda_report.html` | the navigable report, 53 KB |
| `distributions_widget.html` | the distributions widget, 12,669 bytes, one self-contained file |
| `findings_20261015.md` | the findings page |
| `full_numbers.json` | every headline in one file, the source the others read |

The October scripts were generalised into `experiments/eda_full/` rather than
rewritten: `eda_numbers.py`, `build_workbook.py`, `build_report_html.py`,
`make_distribution_widget.py`, `verify_deliverables.py`.

**Verified.** `verify_deliverables.py` exits 0 on 106 checks, 0 failed. I re-checked
the gates myself:

- Em dashes across the report, the widget, the findings page and every workbook text
  cell: **0**.
- Drive paths, home paths, internal folder names, file-name extensions and internal
  ticket tokens across the report, the workbook and the widget: **0**.
- Cross-section references of the form "see section": **0**, so every claim stands on
  its own.
- The widget carries no `http` reference at all, no script tag and no link tag, so it
  is genuinely self-contained.
- The workbook reads back with all 10 sheets populated.

**The inversion is reported prominently and not as resolved.** The report says the
client's own gate inverts to about 15.34 microns per pixel across an interval of
15.298 to 15.376, from a 300 micron boundary at 19.41 to 19.61 px and a 647 micron
boundary at 42.08 to 42.79 px, and that this agrees with neither 18.1165 nor 18.25.

One subtlety the findings page handles correctly: the 5,832 no-shape picture count
and the 5,832 tag-shape count are the same number arrived at twice, so every table
names which one it means.

## Question

What does the lead actually receive, in what form, and does it answer the
question that was asked without sending the reader anywhere else?

## The set, fixed in the grill

Mirror the 2026-10-13 production batch set, at full coverage:

1. a workbook, one sheet per question
2. an HTML report
3. a distributions widget
4. a findings doc
5. a coverage sheet
6. a crosswalk sheet

The 2026-10-13 scripts in `experiments/production_20260925/` are generalised
rather than rewritten.

## Rules that apply to everything produced here

- No em dashes. Use a hyphen, a comma, a colon or parentheses.
- No local file paths or file names in anything client-facing: defect-class names
  and generic toolchain terms only.
- Every claim states its evidence in the same sentence or bullet. No cross-section
  references of the form "see section 7".
- Every micron figure names its scale in the same table.
- The Oct-13 numbers appear only in a clearly labelled superseded section, with
  the delta stated.

## Acceptance

1. Every figure in the workbook is re-derived by the verifier's route, not typed.
2. The report reads standalone: no required second document for a headline claim.
3. The superseded 2026-10-13 record is labelled superseded, and the delta section
   names what moved and why.
4. Nothing client-facing carries a path, a file name or an internal ticket number.
