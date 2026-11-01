---
title: The 300 micron gate
date: 2026-10-15
type: result
status: active
where: reports/eda_full/micron_gate_20261015.md
---

# The 300 micron gate

Ticket 014 of the full-coverage EDA map. What the four production
`*_MICRON_THRESHOLD` tags gate on, whether the data supports the client's 300
micron statement, and the client's own gate inverted into an independent
microns-per-pixel estimate.

The four gate codes are the CLIENT'S AUTHORITY. Everything derived here is
reported BESIDE them, never instead of them.

## The headline

**The gate flips on the LONGER SIDE of the annotation box, `max(w, h)`, not on
the diagonal.** At that proxy it is a clean size cut: zero images sit on the
wrong side of the boundary in any class that has both a flagged and an unflagged
group, in both the 2026-10-13 and the 2026-10-15 files. The diagonal does not
work: it misclassifies 39 of 282 Foreign Matter images (22 flagged below the
largest unflagged diagonal, 17 unflagged at or above the smallest flagged one)
and 4 of 154 Fiber images. The longer side is exactly the "diameter or length,
that is the LARGEST DIMENSION" the URS section 5.2 describes.

**The cut moved, and it moved by exactly the ratio the client stated.** The
boundary between flagged and unflagged images sat at roughly 42 px on the
2026-10-13 files and at roughly 19.5 px on the 2026-10-15 files. The ratio of
the two boundaries brackets 647 / 300 = 2.157. So the older cut was the 647
micron foreign-matter threshold and the newer one is the 300 micron cut the
client announced on 2026-10-13. The data agrees the threshold moved.

**But the data does NOT support 300 microns at our scale.** The same boundary
read at our own scales gives a cut of about 352 to 358 microns, not 300. Say it
plainly: at 18.1165 the Foreign Matter boundary is 351.6 to 355.3 microns, at
18.25 it is 354.2 to 357.9 microns. The observed jump is about 18 percent larger
than a 300 micron cut would put it at our scale.

**The inversion gives about 15.3 microns per pixel, which agrees with NEITHER
18.1165 nor 18.25.** If the boundary sits at B pixels and the client's cut is
300 microns, the client's scale is 300 / B. That is 15.30 to 15.46 from the new
cut alone and 15.12 to 15.38 from the old 647 cut, intersecting to 15.30 to
15.38, midpoint 15.34. This is 15 percent below both candidates. The inversion
does not resolve the 18.1165 against 18.25 question; it is inconsistent with
both of them.

## What is measured, and in which scope

The gate tags exist only in the production files, so an image is in scope for a
base code only when it carries a production annotation box of that code
(priority level 1). An image's size for a base code is the size of its LARGEST
base-code box, measured two ways:

- `diag` = `sqrt(w^2 + h^2)`, the rectangle diagonal;
- `side` = `max(w, h)`, the longer side of the rectangle.

`w` and `h` are the annotation rectangle side lengths (`abs(xbr - xtl)` and
`abs(ybr - ytl)`), the same geometry ticket 012 publishes in `box_sizes.csv`.
All joins are keyed on content md5, never on a path. Microns appear at both
candidate scales in every table, with the scale named.

The four base codes are `P3_FM` (Foreign Matter), `P3_FIB` (Fiber), `P3_EP`
(Extraneous Polymer) and `P3_HE` (HEMA Obstruction). `P3_HE` also carries the
library-only HEMA Fragment class in the Sep-22 project; that class has no
production code, so it does not enter the production scope.

## The boundary, new and old, at both scales

Boundary means the open-closed interval `(largest unflagged side, smallest
flagged side]`, in pixels, over the production scope. `mid` is its midpoint. The
micron columns read the midpoint at each scale.

| Base code | Cut (client) | Files | Unflagged max (px) | Flagged min (px) | Mid (px) | Mid um @18.1165 | Mid um @18.25 |
|---|---|---|---|---|---|---|---|
| P3_FM | 300 | 2026-10-15 | 19.250 | 19.610 | 19.430 | 352.00 | 354.60 |
| P3_FIB | 300 | 2026-10-15 | 19.410 | 19.900 | 19.655 | 356.08 | 358.70 |
| P3_EP | 300 | 2026-10-15 | 15.800 | 25.190 | 20.495 | 371.30 | 374.03 |
| P3_HE | 300 | 2026-10-15 | none | 296.520 | none | none | none |
| P3_FM | 647 | 2026-10-13 | 41.780 | 42.790 | 42.285 | 766.06 | 771.70 |
| P3_FIB | 647 | 2026-10-13 | 42.080 | 44.170 | 43.125 | 781.27 | 787.03 |
| P3_EP | 647 | 2026-10-13 | 25.190 | 42.740 | 33.965 | 615.33 | 619.86 |
| P3_HE | 647 | 2026-10-13 | none | 296.520 | none | none | none |

The P3_EP interval is wide because only two production Extraneous Polymer images
are unflagged, so the lower edge is thin; P3_FM (111 unflagged) and P3_FIB (18
unflagged) set the tight boundary. The ratio test uses only P3_FM and P3_FIB.

Ratio of the old boundary to the new one, over the FM and Fiber intervals:

```
old FM lower  / new Fiber upper = 41.780 / 19.900 = 2.100
old Fiber upper / new FM lower  = 44.170 / 19.250 = 2.295
                                    the interval (2.131, 2.276] brackets 2.157
```

2.157 is 647 / 300. The boundary ratio lands on it, which is the evidence that
the old cut was 647 and the new cut is 300, and that the proxy is unchanged.

## Size distributions, flagged against unflagged

Production scope, side proxy, both scales. p25 / p50 / p75, never a bare mean.
These are the numbers in `gate_analysis.csv`; the diagonal rows are there too.

| Base code | Gate state | n images | p25 px | p50 px | p75 px | p50 um @18.1165 | p50 um @18.25 |
|---|---|---|---|---|---|---|---|
| P3_FM | flagged | 171 | 27.06 | 33.16 | 45.45 | 600.74 | 605.17 |
| P3_FM | unflagged | 111 | 8.97 | 12.21 | 16.55 | 221.20 | 222.83 |
| P3_FIB | flagged | 136 | 34.55 | 52.61 | 86.39 | 953.02 | 960.04 |
| P3_FIB | unflagged | 18 | 14.63 | 16.12 | 17.63 | 292.03 | 294.19 |
| P3_EP | flagged | 33 | 66.16 | 133.48 | 227.05 | 2,418.19 | 2,436.01 |
| P3_EP | unflagged | 2 | 15.77 | 15.78 | 15.79 | 285.88 | 287.99 |
| P3_HE | flagged | 94 | 999.73 | 1,055.81 | 1,090.78 | 19,127.58 | 19,268.53 |
| P3_HE | unflagged | 0 | - | - | - | - | - |

The gap between flagged and unflagged is the boundary above, not a distribution
statistic: no flagged image has a largest side below the smallest flagged one,
and no unflagged image reaches it.

## Which proxy fits, and by how much

Misclassification count per base code, new 300 cut, production scope: an image
is misclassified when a flagged image's size is below the largest unflagged
size, or an unflagged image's size reaches the smallest flagged size.

| Base code | diag misclassifications | side misclassifications |
|---|---|---|
| P3_FM | 39 | 0 |
| P3_FIB | 4 | 0 |
| P3_EP | 0 | 0 |
| P3_HE | not testable | not testable |

The longer side fits exactly; the diagonal does not. This matters because for a
wide box the two numbers differ: a 3 to 1 box has a longest side well under its
diagonal. The client's cut tracks the longest side, which is what section 5.2 of
the URS specifies.

## Does the data support a 300 micron cut?

At our two candidate scales, no. The boundary is a fixed length in pixels,
19.4 to 19.6 px. Read at 18.1165 it is a 351.6 to 355.3 micron cut; read at
18.25 it is 354.2 to 357.9 microns. Both are about 18 percent above 300.

The data supports a 300 micron cut only if the client's own scale is about 15.3
microns per pixel. If the client's scale is 18.1165 or 18.25, then the cut they
applied reads as about 353 to 358 microns at that scale, and there is a real
tension to resolve: either the declared cut is a nominal, or the annotation box
overshoots the debris, or our scale is about 18 percent too high.

## The independent scale route

If the gate is applied to the largest base-code box on the image, and the box
edges delimit the debris, then the boundary is a client-anchored length and the
client's scale is `cut_um / boundary_px`, independent of our 14,200 micron
reference.

| Source of the boundary | Boundary interval (px) | Implied scale (um/px) | Midpoint |
|---|---|---|---|
| New 300 cut, FM and Fiber intersected | (19.410, 19.610] | 15.298 to 15.456 | 15.377 |
| Old 647 cut, FM and Fiber intersected | (42.080, 42.790] | 15.120 to 15.376 | 15.247 |
| Combined (new and old intersected) | - | 15.298 to 15.376 | 15.337 |

Agreement: **neither 18.1165 nor 18.25.** The combined interval 15.30 to 15.38
does not contain 18.1165 and does not contain 18.25. So this route does not
resolve the two candidate scales; it is inconsistent with both, which is a third
answer and is stated as such.

Assumptions it rests on, each of which can break it:

1. the gate is applied to the LARGEST base-code box on the image (not to some
   other object, and not to the debris the algorithm would segment itself);
2. the annotation box edges delimit the debris, with no systematic margin;
3. the client's declared cut is exact, 300 now and 647 before;
4. the fitting proxy is the longer side `max(w, h)`, which the data supports but
   which is our inference, not the client's written rule.

The boundary is not too soft to invert: it is the sharpest part of this ticket,
with zero images on the wrong side of it. The uncertainty reported is therefore
the width of the boundary interval plus the assumption risk, not sampling noise.

## The before-and-after delta, 2026-10-13 against 2026-10-15

The 2026-10-13 production files were pulled read-only from the shared VM into a
local scratch directory and compared shape by shape with the current files,
keyed on content md5. `gate_delta.csv` is one row per changed picture, all 170.

| Base code | Old flagged (2026-10-13) | New flagged (2026-10-15) | Added | Side range of the newly flagged (px) |
|---|---|---|---|---|
| P3_FM | 53 | 171 | 118 | 19.610 to 41.780 |
| P3_FIB | 85 | 136 | 51 | 19.900 to 42.080 |
| P3_EP | 32 | 33 | 1 | 25.190 |
| P3_HE | 94 | 94 | 0 | - |

Reconciliation of the 170 pictures, picture by picture:

- 169 pictures carry an added gate tag: 117 Foreign Matter only, 50 Fiber only,
  1 Extraneous Polymer only, and 1 picture that gained both a Foreign Matter and
  a Fiber tag. That is 118 Foreign Matter adds, 51 Fiber adds and 1 Extraneous
  Polymer add, which equals the count of tags added.
- 1 further picture lost one `P1_ML` tag (its tag count fell from 4 to 3). It
  gained no gate tag, so it is a distinct picture.
- 169 with adds plus 1 removal-only equals 170 changed pictures. No picture both
  gained and lost a tag.
- Every newly flagged picture's largest side sits between the old boundary and
  the new boundary, which is exactly the band a loosened cut newly admits.
- Geometry is untouched: 0 pictures changed any box. Only tags differ, which
  matches the ticket 010 result and the earlier independent check.

## Classes whose gate cannot be tested

- **HEMA Obstruction (`P3_HE`) is unconditional and is not size gated.** All 94
  production HEMA images carry both the base box and the gate tag, so there is
  no unflagged group and no boundary to measure. The gate tag adds nothing to a
  picture that already carries the class. This holds on both the 2026-10-13 and
  the 2026-10-15 files (94 flagged, 0 unflagged, both times), so the HEMA flag
  did not move with the 647 to 300 change either.
- **Extraneous Polymer** has only two unflagged production images, so its
  boundary lower edge is thin; it is reported but the FM and Fiber boundaries
  set the inversion. Its flagged-versus-unflagged split is still clean.
- The `P3_HE` boxes are region annotations rather than defect spots (carried
  from ticket 012), so even a boundary on them would not be a debris size.

## Files and how to run

| Artifact | What it is |
|---|---|
| `run/eda_full_20261015/gate_analysis.csv` | per base code, per proxy, per scope, per gate state: distributions in px and in microns at both scales, plus the boundary |
| `run/eda_full_20261015/gate_delta.csv` | one row per changed picture, 170 rows |
| `run/eda_full_20261015/gate_scale_estimate.json` | the inverted scale, its interval, its assumptions, the agreement |
| `experiments/eda_full/micron_gate.py` | the builder |
| `experiments/eda_full/verify_micron_gate.py` | the verifier |

```bash
./.venv/Scripts/python.exe experiments/eda_full/micron_gate.py
./.venv/Scripts/python.exe experiments/eda_full/verify_micron_gate.py
```

The verifier reads the 2026-10-13 production files from `OLD_PROD_DIR` (default a
local scratch path, never the repo). When that directory is absent the delta
checks are skipped, not faked.

## Verification

1. **Both proxies reported and compared.** `gate_analysis.csv` carries `diag`
   and `side` rows for every base code, scope and gate state, and the proxy
   table above gives the misclassification counts. The longer side fits (0
   misclassifications in every testable class) and the diagonal does not (39 on
   Foreign Matter, 4 on Fiber).
2. **Both scales in every micron table.** Every table names 18.1165 and 18.25,
   and the verifier checks that `p50_um_18_25 / p50_um_18_1165` equals
   18.25 / 18.1165 (ratio 1.007369), proven on a spot row and structurally by
   the four micron columns present in the header.
3. **The gate is the client's authority.** Every number here is the boundary the
   client's own tags draw; our cut in microns is reported beside it at both
   scales, never in place of it.
4. **The 170-picture delta is reconciled picture by picture.** 169 with adds
   (118 FM, 51 Fiber, 1 EP) plus 1 `P1_ML` removal-only equals 170. The verifier
   re-derives the changed count, the added tags, the removed tags and the zero
   geometry change straight from the XML as a second route, and it reconciles
   the 118 FM adds against the 171 new flagged minus 53 old flagged.
5. **HEMA Obstruction reported unconditional**, with the reason (no unflagged
   group) and with the verification that it is 94 flagged and 0 unflagged on
   both file dates.
6. **The inverted scale states its uncertainty and assumptions** and says
   plainly that it agrees with neither candidate scale (combined 15.30 to 15.38,
   midpoint 15.337, against 18.1165 and 18.25).
7. **Byte-identical rebuild, md5 both times.**

```
gate_analysis.csv          c04bca2505f3fb38b64a600877fa6a7d
gate_delta.csv             5b59485051c8c58b55228c8506a2a990
gate_scale_estimate.json   62d60c00428dee32f9f3ae20bcc2823a
```

The verifier re-derives every headline gap by a second route (parsing the
production XML directly instead of reading `box_sizes.csv`, and computing
percentiles with `statistics.quantiles` inclusive): **39 checks, 0 failures.**

Nothing was written to the shared VM. The 2026-10-13 files were read only and
copied to a local scratch directory outside the repo.
