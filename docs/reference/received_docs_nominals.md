---
title: Received documents, documented physical dimensions and the blind scale reference
date: 2026-10-15
type: reference
status: active
where: docs/reference/received_docs_nominals.md
---

# Received documents, documented physical dimensions and the blind scale reference

Ticket 008. Every physical dimension the client has given us, where it is written,
and which of them can carry a blind microns-per-pixel measurement for ticket 013.

Ticket 013 measures a feature in pixels and compares it to a nominal size in
microns. The nominal has to come from a document the client gave us, otherwise the
test just re-measures our own assumption. This doc records what actually exists.

## 1. What the received set is

Three documents the client gave us are present in this repository:

- `docs/FM3 Edge Algorithm URS Final Draft .pdf`, titled "FM3 Requirement
  Specifications: Edge Algorithm", Revision DRAFT, dated 28 August 2026, 34 pages.
- `docs/Manufacturing Condition Ontology V1.docx`, by Bryce Barrineau, V1.0.
- The annotator handover email of 2026-10-13, from Bryce Barrineau, recorded
  verbatim at `experiments/production_20260925/annotator_email_20261013.json`.

One further client document is cited in our records but is not present here, so it
could not be checked: the "FMD Annotation Guide - FM vs FM-Exclusion Classes
(2026-08-21)" at `D:/02-SSA/JnJ-Docs/FMD Official docs/`, named as a source in
`reports/urs_dilemmas_meeting.md`. It is the most likely place a lens or package
diameter would be written, so ticket 013 should ask for it rather than assume it is
absent from the client's world.

The JnJ production line specs in `docs/reference/jnj_production_line_specs.md` are
what the JnJ team shared with us on 2026-10-12, recorded by us. They are hardware
parameters, not a dimension of anything in the image, and they are listed below so
that the search is complete.

## 2. Every physical dimension found, with its source

| Dimension | Value | Unit | Source document | Where in it | Blind usable |
|---|---|---|---|---|---|
| Foreign matter detection threshold (largest dimension of non-lens material in contact with packing solution) | 647 | microns (0.647 mm) | FM3 Edge Algorithm URS Final Draft (received) | Section 1.1.1, p3, which names QP-0050; restated as Requirement 1 in Section 4.1, p7; restated in Section 6.2, p28 | No, a pass/fail threshold, not the size of an object we can measure |
| Debris size grouping bands, a nice-to-have | under 300; 300 to 500; 500 to 647 | microns | same URS | Section 4.2 Nice to Haves, item 1 (a, b, c), p7 | No, thresholds only |
| HEMA to lens overlap that reclassifies a defect as HEMA Obstruction | more than 20 | percent of the visible lens, dimensionless | same URS | Section 5.2.1, p22, itself flagged "pending EDA" | No, a fraction, carries no length |
| Minimum bubble annotation size | 5 x 5 | pixels | Manufacturing Condition Ontology V1.0 (received) | Bubble Conditions, the Bubble subsection | No, pixels only, no micron value |
| Per-class object size statistics (width, height, area) | e.g. Bubble width mean 23 px and max 394.3 px, Fiber width max 1228.8 px, HEMA Fragment height max 644.3 px | pixels, unit not stated | same Ontology | Annotation Specification, the Object Sizes tables | No, annotation statistics in pixels, no micron value and no fixed nominal |
| Foreign-matter-over-threshold tag rule | debris exceeds 647 | microns | Annotator handover email, Bryce Barrineau, 2026-10-13 (received) | `annotator_email_20261013.json`, fields `stated_rule` and `threshold_um` | No, restates the 647 threshold |
| Edge algorithm pass/fail latency | 200 | milliseconds | same URS | Section 6.1 | No, a time, not a length |
| Debris measurement convention | diameter or length, largest dimension | none | same URS | Section 5.2 introduction | No, a method, carries no value |
| Camera sensor resolution | 8 MP, 12 MP, 5 MP | megapixels | JnJ line vision specs, shared 2026-10-12, recorded at `docs/reference/jnj_production_line_specs.md` | "The three line setups", Camera model row | No, no object-space nominal and no pixel pitch |
| Optics focal length | 12 mm, 75 mm, 6 mm, 25 mm | millimetres, focal length | same | "The three line setups", Optics row | No, a lens parameter, not a dimension in the scene |
| Backlight wavelength | 625 nm, 660 nm | nanometres | same | "The three line setups", Backlight row | No |
| Image frame geometry | 2448 x 2048 | pixels | Our own file measurement, `docs/cvat_production_20260925_pull.md` and `docs/reference/production_20260925_batch_analysis.md` | Verification table, and the EDA sheet | No, the image size, not a dimension of anything pictured, and it is our measurement of the files rather than a client nominal |

Two further numbers are in circulation and are our own, so they are recorded here to
be clear about what they are not:

- 18.1165 microns per pixel. Our `scale_estimate.json` on the shared VM, quoted in
  `docs/reference/production_20260925_batch_analysis.md` and in the 2026-10-13
  workbook and report. It is a measured result, not a client nominal.
- 14,200 microns, the lens diameter used as the numerator in that estimate, together
  with the 783.8 px lens rim trimmed mean over 200 images and the 5.3 percent
  relative spread. These live only in our own artifacts: `scale_estimate.json` on the
  VM, `vm/ops/analyze_20260925.py`, and the 2026-10-13 docs and workbook. The number
  14,200 is written in no received document that is present in this repository.

## 3. Which nominals can carry a blind measurement, and why

A blind measurement needs a feature that is visible in the images, that has a fixed
real size, and whose real size is written in a client document. Measuring that
feature in pixels and dividing the documented size by the pixel count gives microns
per pixel independently of our own estimate.

By that test, no dimension in the received documents qualifies.

- The 647 microns, the 300 and 500 microns, and the 20 percent overlap are all
  thresholds or fractions. They say when a defect becomes a reject. They are not the
  size of a pictured object, so there is nothing fixed to measure against them.
- The 5 x 5 pixel bubble rule is given only in pixels. It carries no micron value, so
  it cannot yield microns per pixel.
- The Object Sizes tables are statistics of annotation boxes, in pixels, with no unit
  stated. They describe what the annotators drew, not a physical nominal.
- The 200 ms latency, the camera megapixels, the focal lengths and the backlight
  wavelengths are not dimensions of anything in the scene. The camera and optics
  entries carry no sensor pixel pitch and no working distance, so they cannot be
  turned into a scale either.
- The only feature in these images with an obvious fixed real size is the lens rim,
  and the lens diameter is written in no received document present here. The 14,200
  microns we use for it is our own figure. Measuring the rim against 14,200 would
  divide a number we computed in terms of that value by itself, which is exactly the
  circularity ticket 008 exists to catch.

So the usable count is zero, not one. There is no received-document nominal that
ticket 013 can measure against, and the second and only remaining candidate (the lens
diameter) is our own assumption. That is stated plainly because it weakens ticket 013
more than a single usable nominal would: a single independent reference is thin, and
zero means there is no blind reference at all until the client supplies one.

The 300, 500 and 647 micron cuts cannot stand in for a nominal either. They are
applied by the annotator's script on the client's own images, at the client's own
scale, to produce the `*_MICRON_THRESHOLD` flags, and the 2026-10-13 analysis showed
that no reading of a box's size at 647 microns reproduces all four flags. They are a
threshold, not a fixed-length object, so they cannot be inverted into microns per
pixel.

## 4. Where 18.25 is written

Nowhere in a received document. The figure 18.25 microns per pixel appears only in
our own wayfinder files:

- `docs/wayfinder/task1_bubble_merge_map.md`, line 55, "defect size across five
  production lines at 18.25 um/pixel".
- `docs/wayfinder/tickets/013-blind-scale.md`, in the question and in step 4.
- `docs/wayfinder/tickets/008-documented-nominals.md`, in the question and the
  deliverable.

In every one of those it is our own note that the lead said it, not a quotation from
a client file. So 18.25 is spoken, not written. The URS, the Ontology and the
annotator email do not contain it, and neither does any workbook, report or script.
The only scale the client has put in writing is the 647 micron cut, and that is a
size threshold, not a scale.

## 5. What ticket 013 can and cannot test as a result

Ticket 013 cannot run its planned blind test on the nominal it intended. It planned
to measure the lens rim in pixels and divide by a documented lens diameter, but no
received document states that diameter. The 14,200 microns is ours, so that
measurement would only reproduce our own estimate and would not be blind. The other
documented dimensions are thresholds, fractions, pixel counts or hardware parameters,
none of which is a fixed physical size of a feature we can pick out and measure. As
things stand, ticket 013 can compare our 18.1165 against the lead's spoken 18.25, and
it can report the per-stratum spread, but it cannot produce an independent microns per
pixel from the documents. To make the test blind, the client must supply a written
lens diameter in microns, or the FMD Annotation Guide, or another document naming the
real size of a feature that appears in the images, for example the package bowl or a
fiducial mark. Until then, the honest reading is that the blind test is blocked on a
missing nominal, not merely weakened by having only one.
