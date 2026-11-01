---
title: "Ticket 019 - Label matrix and the previous-name change table"
date: 2026-10-21
type: task
status: done
where: docs/wayfinder/tickets/019-label-matrix-change-table.md
---

# Ticket 019: Label matrix and the previous-name change table

Build `run/multilabel_edge_<date>/label_matrix.csv`: one row per picture
(content md5, winning_path, source_group, reliability flags), one 0/1 column
per class in the frozen frame (23 columns), labels de-duplicated to set
membership per picture.

Steps:

1. Apply the drop rule: exclude pictures carrying plain FM/Fiber/EP/HEMA
   Fragment with no gate tag. Re-derive the 345 figure independently; report
   the 75 that also carry another defect class as a flagged list.
2. Apply the Fiber/EP flip from the verified picture-by-picture list
   (fact-finder output), never from the count-33 coincidence. The flip list,
   its derivation and its md5s are saved beside the matrix.
3. Column derivation: gate columns from the four `P3_*_MICRON_THRESHOLD`
   tags; Bubble absorbs bubble_irregular and stretched_bubble; Bubble On 123,
   Bubble On Edge, HEMA Obstruction stay their own columns per decision;
   Clear = no defect-class label (LP tags do not block Clear); Low Dose
   carries an unreliability flag, not a removal.
4. Change table: previous name and code against Draft 2 code and name, one
   row per class, with what changed (source: Draft 2 changelog section 1).
5. Legend sheet from `data/crosswalk.csv` codes; every later artifact reuses it.

Done when: row count reconciles against the 10,614 census minus the drop set,
every column total is derived twice (builder and independent verifier), and
the flip set is checked picture by picture against the disagreement table.
