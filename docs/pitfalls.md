---
title: Pitfalls and their fixes, multi-label edge experiment
date: 2026-10-21
type: reference
status: active
where: docs/pitfalls.md
---

# Pitfalls and their fixes

One line per problem, then the fix. Append as we hit them; never delete entries.

| When | Problem | Fix |
|---|---|---|
| 2026-10-21 | Quoted heredocs fail in Windows git-bash (unmatched-quote EOF) | Write a `.py` file, then run it |
| 2026-10-21 | MSYS path translation is off for native tools; `/c/...` paths fail for git, python | Pass `C:/...` forward-slash native paths to native programs; `/c/...` only for bash builtins |
| 2026-10-21 | The name "wayfinder" cannot be loaded as a skill (duplicate name/path collision with another skill in the same tier) | Follow the wayfinder convention directly: map + tickets in `docs/wayfinder/`, five-line headers, `tools/index_docs.py` after doc changes |
| 2026-10-21 | The Sep-22 CVAT export lists thousands of image names with zero shapes; a name-mention is not an annotation (1,907 such pictures surfaced as fake negatives until ruled out) | Count annotations by shapes carried, never by names listed; 0 tags = no tags |
| 2026-10-21 | xlsx rebuild fails with Permission denied while the workbook is open in Excel | Ask the user to close the file, or write to a versioned filename and swap |
| 2026-10-23 | A count read from one population looks like the matrix column: Fiber gate is 137 in the split-eligible set but 168 in the full matrix (the 31-row Fiber/EP flip sits only in the matrix), and Bubble is 746 strict-code / 750 merged / 862 matrix | Name the population beside every count (census, matrix, split universe) and have the workbook verifier recompute each cell from its source; a hand-typed column hides the mismatch |
| 2026-10-23 | A class measured as a union can hide containment: Bubble Irregular looked additive (+108) but every BI picture also carries P2_BB, so the merge added 4 pictures, not 112 | Compute the overlap before stating a merged total; report the union, not the sum |
| 2026-10-23 | A total row that sits under a mixed table is read as the sum of every row: the object total (12,783) covered only the eight guide classes while four reference classes sat above it with 304 more boxes | Put a subtotal where its group ends, label it with the group ("Total, the 8 object classes"), and add a separate all-rows total (13,087); have the verifier check both sums |
| 2026-10-23 | Multi-label columns never add up to picture totals: the split class rows sum to 6,268/2,675 against 4,568/2,006 pictures, and tag rows sum to 7,328 against 6,785 | State the population in every header and print a "sum of the class rows" line beside the picture total, with one sentence saying a picture can carry several classes |
| 2026-10-23 | A zero-box class silently disappears from a stats dict and then from the workbook: Surface Groove (P1_SG) vanished from the Objects sheet, leaving 7 of the guide's 8 classes | Build every class sheet from the guide's class list, emit explicit zero rows, and have the verifier assert that all guide classes are present, not only that present values match |
