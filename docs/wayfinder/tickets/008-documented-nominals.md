---
title: "Ticket 008: documented nominals for a blind scale reference"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/008-documented-nominals.md
---

# 008: Documented nominals for a blind scale reference

Type: research, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: nothing.

## Resolution (2026-10-15)

Done, and the answer is a blocker. Record:
`docs/reference/received_docs_nominals.md`.

**Zero usable blind nominals, and 18.25 is written nowhere.**

- Every physical dimension in the received documents is a threshold (647, 500,
  300 microns), a fraction (20 percent of the visible lens), a pixels-only rule
  (a 5 x 5 bubble), annotation statistics in pixels with no unit, or a hardware
  parameter (megapixels, focal lengths, backlight wavelengths, 200 ms). None is
  the fixed real size of a feature that can be picked out and measured in the
  image.
- The one obvious candidate, the lens rim, has its nominal diameter (14,200
  microns) written only in our own artifacts. Measuring the rim against our own
  figure is circular, so it is not blind.
- 18.25 microns per pixel appears in no received document. It exists only in our
  own wayfinder notes recording that the lead said it. The client has put a
  cutoff in writing, never a scale.
- One client document is cited in our records and is **not present on this
  machine**: the "FMD Annotation Guide - FM vs FM-Exclusion Classes
  (2026-08-21)", referenced from `reports/urs_dilemmas_meeting.md` at an
  old-machine path. It is the most likely place a lens or package diameter would
  be written. The old machine's document folder is not on this laptop.

**Consequence for ticket 013.** The absolute blind test as planned cannot run.
Ticket 013 is re-scoped into a variation test (which needs no client nominal) and
a blocked absolute test. Ticket 018 carries the request for a written nominal.

## Question

Which physical dimensions in the documents the client has given us can serve as
a blind reference for microns-per-pixel, and where exactly does 18.25 appear?

## Why it blocks

Ticket 013 measures a feature in pixels and compares it to a nominal in microns.
If the nominal comes from our own `scale_estimate.json`, the test is not blind.
It has to come from the received documents.

## Sources to read

- `docs/FM3 Edge Algorithm URS Final Draft .pdf`
- `docs/Manufacturing Condition Ontology V1.docx`
- the accepted-email record in `experiments/production_20260925/annotator_email_20261013.json`
- `scale_estimate.json` and `measure_scale.py` on the VM (for method only, not
  as the nominal)
- any pass/fail criteria document that names the 647 micron and 300 micron cuts

## Deliverable

`docs/reference/received_docs_nominals.md`: every physical dimension found, with
its source document and where in it, and a plain statement of which of them can
carry a blind measurement. Plus where 18.25 is written, if it is written
anywhere at all.

## Acceptance

1. Each nominal carries a citation to the document and page or section.
2. The document states which nominals are usable and which are not, with the
   reason.
3. If only one usable nominal exists, that is stated explicitly, because it
   removes the second independent reference and weakens ticket 013.
