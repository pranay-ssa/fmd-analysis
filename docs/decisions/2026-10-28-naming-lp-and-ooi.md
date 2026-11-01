---
title: Naming for the LP and OOI classes
date: 2026-10-28
type: decision
status: active
where: docs/decisions/2026-10-28-naming-lp-and-ooi.md
---

# Naming for the LP and OOI classes

## Decision

The word "condition" is dropped from results artefacts and documents. The two families are
named by their annotation families:

- **LP class** for one of the twelve lens-presentation answers, built from the LP tags. "LP tag"
  is used only when the annotation tag itself is meant.
- **OOI class** for one of the eight object-of-interest classes, marked as a region.
- **OOI flag** for the thirteenth answer in run 2. It is not a separate finding and does not
  name an OOI class: it says at least one OOI class is present.

"Object" alone is no longer used as a class word, because it reads as a shape rather than a
family and hides that the flag aggregates eight classes.

## Why

The results artefacts and the annotation guide were using three words for two things:
"condition", "class" and "tag" for the LP side, and "object" and "OOI" for the other. A reader
who has the guide in hand had to translate. Naming them by the annotation families makes the
mapping direct and makes the thirteenth answer's role obvious.

## Where it applies

The results workbook, the client report, and any document that quotes them. Older documents
keep their wording; they describe earlier runs and are not rewritten.

## Consequence for the thirteenth answer

Because the flag covers all eight OOI classes together, it is scored by fire rate on three
groups (OOI-only, mixed, Clear), never by average precision. Quoting an average precision for
it would imply it distinguishes among the eight, which it does not.
