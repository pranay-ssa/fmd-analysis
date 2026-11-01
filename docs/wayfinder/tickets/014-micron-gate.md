---
title: "Ticket 014: the 300 micron gate"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/014-micron-gate.md
---

# 014: The 300 micron gate

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 010, 012, 013.

## Resolution (2026-10-15)

Done, and this ticket broke a published number. Record:
`reports/eda_full/micron_gate_20261015.md`.

**The gate is a clean size cut, on the LONGER SIDE, not the diagonal.** With the
longer side `max(w, h)` as the size proxy there are 0 misclassifications in every
testable class; the diagonal leaves 39 on Foreign Matter and 4 on Fiber. The October
analysis used the diagonal and therefore concluded the gate was not a size cut at
all. That conclusion is superseded.

**The client's 647-to-300 change is confirmed from the data.** The boundary moved
from 42.08 to 42.79 px on the old files to 19.41 to 19.61 px on the new ones. The
ratio interval (2.131, 2.276] brackets 647 divided by 300, which is 2.157.

**The inversion, and what it says.** Inverting each boundary gives a scale that does
not depend on our own 14,200 micron reference:

| Cut | Boundary px | Implied microns per pixel |
|---|---|---|
| 300 (new) | 19.41 to 19.61 | 15.298 to 15.456 |
| 647 (old) | 42.08 to 42.79 | 15.120 to 15.376 |
| Combined | | **15.298 to 15.376, midpoint 15.337** |

**That agrees with neither 18.1165 nor 18.25.** Two independent boundaries, taken
five weeks apart on two different annotation passes, land in the same place, so this
is not a single-measurement fluke. Read at our scale the declared cut would be 353 to
358 microns, about 18 percent above the 300 the client states. Equivalently, our
published 18.1165 is about 18 percent too large, or the 14,200 micron lens diameter
it rests on is about 12,024 microns, not 14,200.

**Assumptions the inversion rests on**, all stated: the gate is applied to the
largest base-code box on the image; the box edges delimit the debris with no
systematic margin; the declared cut is exact; and the fitting proxy is the longer
side. The weakest is the second, because a box drawn with a margin would push the
implied scale down.

**Verified independently.** I recomputed the boundaries myself from
`box_sizes.csv` and `resolved_labels.csv`: Foreign Matter maximum unflagged side 19.25
px against minimum flagged 19.61 px, Fiber 19.41 against 19.90 px. Same result.

**Also settled.** HEMA Obstruction is unconditional: 94 flagged and 0 unflagged on
both file dates, so there is no boundary to invert. Extraneous Polymer has only 2
unflagged images and cannot set a boundary on its own.

**The delta.** 170 changed pictures: 169 carry an added gate tag (118 Foreign Matter,
51 Fiber, 1 Extraneous Polymer, one picture gaining both an FM and a Fiber tag) and 1
lost a Multiple Lenses tag and gained no gate tag. Geometry untouched, 0 pictures.
Per base: Foreign Matter 53 to 171, Fiber 85 to 136, Extraneous Polymer 32 to 33, HEMA
94 to 94.

Verifier 39 checks, 0 failures, on a route that re-parses the production XML directly
rather than reading `box_sizes.csv`. Byte-identical rebuild.

## Question

What do the four `*_MICRON_THRESHOLD` tags gate on, what cut in microns do they
imply at each candidate scale, and does the data agree with the client's
statement that the cut moved from 647 to 300 microns?

## What is already known

- The four gate codes are strict subsets of their base codes.
- On the 2026-10-13 files, the flagged-versus-unflagged gap sat far above 300,
  500 and 647 microns, so the gate did not look like a 300 micron cut then.
- The newer files add 118 Foreign Matter, 51 Fiber and 1 Extraneous Polymer gate
  tags and change no geometry at all, which is what a loosened cut would look
  like.
- HEMA Obstruction is flagged on every picture that carries it, so it is not
  size gated: there is no unflagged comparison group.

## Deliverable

- `run/eda_full_20261015/gate_analysis.csv`: per base code, the flagged and
  unflagged largest-box distributions, the gap in pixels and in microns at each
  candidate scale.
- `reports/eda_full/micron_gate_20261015.md`, stating plainly whether the data
  supports a 300 micron cut, and if not, what cut it does imply.

## Acceptance

1. The gate tags are read as the client's authority. Our derived cut is reported
   beside them and never instead of them.
2. The implied cut is computed at both candidate scales, so the ticket does not
   silently depend on the answer to 013.
3. The before-and-after comparison against the 2026-10-13 files is reported as a
   delta table, and the 170 changed pictures are reconciled picture by picture.
4. HEMA Obstruction is reported as unconditional, with the reason stated.
5. Any class whose gate cannot be tested for lack of an unflagged group says so.
