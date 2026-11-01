---
title: "Ticket 013: blind scale determination per folder group and line"
date: 2026-10-15
type: protocol
status: active
where: docs/wayfinder/tickets/013-blind-scale.md
---

# 013: Blind scale determination per folder group and line

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 007, 008.

## Resolution (2026-10-15)

013a is done. Record: `reports/eda_full/blind_scale_20261015.md`. 013b remains
blocked on the client and no microns figure from this ticket is blind.

**The answer: no, the lines and the two folder groups do not differ beyond noise.**
Raw rim p50 spans 688 to 763 px, a between-stratum range of 75 px (10.2 percent),
while the within-stratum relative spread is 10.0 to 25.7 percent. Restricted to
pictures where the rim finder locked on cleanly, the ten strata agree within 52 px
(6.8 percent) and the clean within-stratum standard deviation is 32.8 to 51.7 px,
which is the same size as the difference. So no line and no folder group stands out.

**The finding that matters for the scale question.** The within-stratum spread,
10 to 26 percent, dwarfs the 0.7 percent gap between 18.1165 and 18.25. That gap is
not resolvable by this measurement or by the published one, and saying so is the
result. The scale cannot be tightened by sampling more images at this precision.

**Caveat carried forward.** The rim routine reused from the 2026-10-13 run misfires
on a stratum-dependent slice of pictures, from 11.5 percent to 41.8 percent, and the
raw medians move with that contamination rate. The clean-band figures are the
trustworthy ones, but the band is a fixed 640 to 900 px window chosen from the pooled
histogram, which can itself hide a real per-stratum difference by truncation.

**Sample sizes, corrected.** The ticket text said Library L25 161 and Library L26
254, taken from basename membership; the real universes from `picture_table.csv` are
Library L24 788, L25 155, L26 205, L27 115, L31 139, and Updated L24 4,272, L25 948,
L26 1,475, L27 1,610, L31 2,132. Achieved: 200 everywhere except the capped Library
L25 (155), L27 (115) and L31 (139). Ticket 007's 177 library-only pictures and this
ticket's Library strata are different things and must not be conflated: 1,225 of the
1,402 library pictures also sit in an Updated folder.

Checked three ways: the sample reproduces from its seed, the aggregation is
byte-identical across two runs, and the verifier re-derives every per-stratum median
by a second route plus re-reads 30 pictures from the VM through an independently
written rim routine with 0 disagreements.

## Re-scoped (2026-10-15, after 008)

Ticket 008 found zero usable blind nominals, so the absolute blind test as
written cannot run. Split into two:

**013a, the variation test (runs now).** Measure the lens rim and the cavity in
PIXELS per folder group x line, 200 per stratum with the cap reported, from ticket
007's picture table. Report the pixel distributions per stratum and the spread.
This answers the question that was actually asked, "does the line give a different
answer", and it needs no client nominal: the lens is the same physical part on
every line, so any pixel difference between strata is a scale difference. State
plainly that the implied microns-per-pixel it also prints is computed at our own
single reference (14,200 microns) and is therefore not an independent check of
that reference.

**013b, the absolute test (blocked).** Inverting a client-written threshold is the
only remaining route to a scale that does not depend on our own number, and it
belongs to ticket 014: the client applies the 300 micron gate on their own scale,
so the boundary between flagged and unflagged debris boxes is a client-anchored
length. Ticket 014 computes that boundary anyway. If it lands cleanly, 014 supplies
the independent scale; if not, 013b waits on a written lens diameter from the
client, which ticket 018 asks for.

Do not report any microns-per-pixel figure from 013a as though it were blind.

## Question

Is 18.25 microns per pixel right, is our 18.1165 right, or is the difference
inside the measurement noise? And does the answer change by folder group or by
production line, which is the part nobody has checked?

## Sampling, fixed in the grill

200 pictures per folder group x line, capped where a group has fewer, with the
cap reported. The two groups are the Updated folders together, and the ICube
Defects Library. Per-line availability in the old library is thin: L27 tops out
at 115, L31 at 139, L25 at 161, so those strata will report a cap.

## Method, blind by construction

1. Take the nominal from ticket 008's documented value, not from
   `scale_estimate.json`.
2. Measure the chosen physical feature in pixels on each sampled picture, with a
   fixed, written-down procedure, and a per-image measure that a second reader can
   reproduce.
3. Convert and report microns per pixel per stratum with p25, p50, p75 and the
   relative spread.
4. Only then compare with 18.1165 and with 18.25.

## Deliverable

- `run/eda_full_20261015/scale_samples.csv`, one row per measured picture.
- `run/eda_full_20261015/scale_by_stratum.json`.
- `reports/eda_full/blind_scale_20261015.md`.

## Acceptance

1. The nominal is cited to its source document, and no number from
   `scale_estimate.json` is used as an input to the measurement.
2. The measurement procedure is written down before the numbers are read, and the
   procedure is reproducible by a second reader on the same pictures.
3. Every stratum reports its achieved sample size and its cap, if any.
4. The reported spread is compared against the gap between the two candidate
   scales, so the answer states whether the gap is resolvable at all. Our own
   earlier spread was 5.3 percent against a 0.7 percent gap, which is a finding
   in itself.
5. Per-line variation, if any, is shown as a table and not only described in prose.
