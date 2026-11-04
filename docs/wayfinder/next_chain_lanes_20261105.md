---
title: Next round, atomised across three lanes (proposal, awaiting review)
date: 2026-11-04
type: protocol
status: active
where: docs/wayfinder/next_chain_lanes_20261105.md
---

# Next round, atomised across three lanes

Status: **proposal, not dispatched.** Parked on 2026-11-04 at the user's request so the walkthrough and
the point-4 workbook can be read first. No cards exist yet. Approval creates the cards; a second go
releases the first dispatch.

Lane key: W = worker card (dispatched), S = subagent card (parked, orchestrator runs it), O = operator
card (session work).

## A. Bubble-only specificity (the known weakness)

| # | Lane | Card | Output | Runs during |
|---|---|---|---|---|
| A1 | W | Build hard negatives from bubble-only training pictures | exclusion list, ~196 pictures | - |
| A2 | W | Train combined arm with hard negatives | run record, ~25 min GPU | A3 |
| A3 | S | Error analysis: which fail columns fire on bubble-only pictures, before and after | table of column and count | A2 |
| A4 | W | Verify A2 independently | verifier exit 0, tamper proof | - |
| A5 | O | Update decision doc and workbook | revised doc + sheet | - |

Acceptance: catch rate and clear false fails must not worsen by more than one picture, or the old model
stays. The bubble-only pass count is the number the block exists to move.

## B. Threshold grid to 0.99 (no GPU)

| # | Lane | Card | Output |
|---|---|---|---|
| B1 | S | Rescore saved predictions over the 0.05 to 0.99 grid | new thresholds table |
| B2 | S | Compare catch and false-fail at old and new cuts | one table |
| B3 | O | Fold into the workbook if the cuts move | revised sheet |

## C. Second seed (error bars)

| # | Lane | Card | Output | Runs during |
|---|---|---|---|---|
| C1 | W | Rerun weighted object arm, seed 7 | run record, ~25 min | C3 |
| C2 | W | Rerun combined arm, seed 7 | run record, ~25 min | C3 |
| C3 | S | Delta analysis: which differences survive the seed change | table with ranges | C1, C2 |
| C4 | W | Verify C1 and C2 | verifier exit 0 | - |
| C5 | O | Update docs with error bars | doc | - |

## D. Gate plus weight (closes the original question)

| # | Lane | Card | Output | Runs during |
|---|---|---|---|---|
| D1 | W | Train gate arm with weights | run record, ~25 min | D3 |
| D2 | W | Verify D1 and compare with class plus weight | verdict | - |
| D3 | S | Error analysis on the gate arm: where the cost sits now | table | D1 |
| D4 | O | Amend the decision record | doc | - |

## E. Close-out (operator lane, about 10 minutes each)

| # | Card |
|---|---|
| E1 | Decision and session docs |
| E2 | HANDOFF, INDEX, registry rows for the new runs |
| E3 | Notion staging lines, draft state |
| E4 | Orphan sweep of parked cards |

## Counts and timing

18 cards: 9 worker, 5 subagent, 4 operator. Four GPU runs at about 25 minutes each plus verification.
Serial estimate 3 h 15 min; with the analyses inside the GPU windows, about 2 h 15 min.

## Rules applied

- Every worker card carries lane, inputs, output artifact, done test, files it may touch, sandbox needs.
- Verifiers stay whole, one card per run, never split per class.
- Subagent cards are parked in `scheduled` so the dispatcher cannot claim them; the orchestrator closes them.
- The close-out is operator lane, because it is synthesis over context the session already holds.
- Registry rows for new runs are their own card, because `experiments/update_registry.py` only refreshes
  rows that already exist.
