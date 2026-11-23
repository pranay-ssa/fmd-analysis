---
title: How we present results to the lead - proposal for discussion
date: 2026-11-17
type: protocol
status: active
where: docs/data_presentation_proposal_20261117.md
---

# How we present results to the lead

**Draft for discussion. Not in effect.** No existing artifact changes, and no new artifact follows
these rules, until the discussion with the lead closes and this doc is replaced by a decision.

## What prompted this

Two points came back from the lead on 2026-11-17.

1. We answer a question and then add material she did not ask for. When she asked for the gate
   analysis results, the workbook also carried defect size numbers. Size was never part of the
   question.
2. Our Excel tables lead with percentages. She wants counts, because she does her own arithmetic on
   the numbers and a percentage hides the base.

## What we do now

| Practice today | Example in the last gate workbook | Effect on the reader |
|---|---|---|
| Share columns as the headline | `Share of fail caught (%)`, `False-fail rate (%)` | She cannot recover the count without the base |
| Extra analysis included because it is interesting | Mean score by defect size in pixels, seven size bins | She has to work out which table answers her question |
| Method and result in the same table | Threshold, AUROC, recall, precision in one row | Hard to tell the asked number from the supporting number |

## Proposed rules

**R1. One deliverable answers one question.** The question goes at the top in one line. Everything
that does not answer it is left out, or goes to a separate note that names itself as extra.

**R2. Counts are the primary number.** Every count names its population in the header, for example
"pictures examined", "boxes marked", "tags".

**R3. A percentage appears only when it was asked for, and never alone.** If a share is shown, the two
counts that produced it sit in the same row. A share of a small base is marked as such.

**R4. No derived metric that was not asked for.** AUROC, precision, recall, F1, means and distributions
are supporting measures. They are supplied on request, or in a clearly separate sheet, not beside the
asked number.

**R5. Result first, method last.** The asked number is the first table. How it was obtained is one
plain sentence, plus a method sheet if needed.

**R6. Units do not mix.** Pictures, boxes and tags are three different counts. One table never adds
them, and every column says which it is.

## Worked example: the gate analysis

| | What she asked | What we sent | What R1 to R6 would send |
|---|---|---|---|
| Headline | Gate analysis results | AUROC, recall, false-fail rate, mean score by size bin | Fail, caught, missed and wrongly failed counts, per model, no share column unless she asks |
| Extra | Nothing | Defect size in native pixels, seven bins | Not in this workbook. Offered as a separate note |
| Base | Not stated | Percentage columns with counts in some rows | Counts on the stated population in every row |

The size work itself is not wasted. It is a separate finding and can be offered as its own note if
she wants it.

## Open questions for the discussion

1. **Percentages.** None at all, or counts with one share column when the population is small enough
   that a count alone misleads?
2. **Scope.** Does this cover every workbook, or only the ones she reads? Our internal tables still
   need shares to compare runs.
3. **Unit.** When the question says "images", do we report pictures with at least one mark, or every
   picture in the set? The two differ (13,635 against 13,682 in the frozen set).
4. **Extra findings.** Second sheet, separate note, or not sent until asked?
5. **Format.** Workbook only, or decks and messages too?
6. **Old artifacts.** Do the earlier percentage workbooks stay as they are, or get marked superseded
   when this rule lands?

## What changes when this is agreed

- A short presentation standard under `docs/reference/`, one page, linked from `AGENTS.md` beside the
  reader-facing rules.
- The workbook builder gains a switch: counts only, by default, with an explicit flag for shares.
- A check in the workbook verifier that every table states its population and its unit.

Until then nothing changes. The next deliverable follows the current practice unless the lead asks
otherwise in writing.
