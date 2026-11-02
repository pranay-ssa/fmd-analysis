---
title: "Ticket 016: verification gate"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/tickets/016-verification-gate.md
---

# 016: Verification gate

Type: task, AFK. Map:
[full-coverage EDA](../eda_full_coverage_map.md). Blocked by: 011, 012, 014, 015.

## Resolution (2026-10-15)

Done. Record: `docs/reference/eda_full_verification.md`.

**157 assertions, 0 failures, the gate exits 0.**

- **Gate 1, independent re-derivation:** 142 figures recomputed through a third
  implementation that reads only the 9 raw annotation XMLs, `file_manifest.csv` and
  the frozen crosswalk. It never calls a per-ticket verifier. All 142 agree.
- **Gate 2, byte-identical rerun:** all 24 artifacts identical, 0 not identical.
  19 were genuinely regenerated from scratch in dependency order into a separate
  output tree. The 5 raw VM inputs (the 65 GB hash outputs and the two measurement
  transcripts) were reused read-only with unchanged md5s rather than re-reading
  10,000 images. No builder writes a timestamp, so no artifact was legitimately
  allowed to differ.
- **Gate 3, the verifiers bite:** five verifiers were shown to exit non-zero on a
  corrupted copy, and 0 on the clean file: crosswalk, resolution, label census,
  coverage and micron gate, all `clean=0 corrupted=1`.
- **The 15.34 inversion was reproduced independently** from the 9 production XMLs
  plus the 7 read-only 2026-10-13 XMLs, keyed on content md5, using the longer side
  of the largest base-code box, and explicitly NOT from `box_sizes.csv`. New cut
  19.410 to 19.610 px gives 15.2983 to 15.4560; old cut 42.080 to 42.790 px gives
  15.1204 to 15.3755; combined 15.2983 to 15.3755. The interval contains neither
  18.1165 nor 18.25, so the claim stands.
- **Cross-artifact consistency, 15 checks, all holding:** 14,182 boxes plus 5,832
  tags equals 20,014 shapes identically in three separate files; the five coverage
  figures 10,614, 6,690, 4,782, 5,832 and 3,924 agree across three files and are
  mutually consistent; the four gate codes are strict subsets at 171, 136, 33 and
  94; the 170-picture delta reconciles per base code; and no picture carries two
  sources.
- **Named as not independently reachable, with reasons:** the VM cavity and rim
  measurements, the coverage per-defect share table, the full pairs table, and
  ticket 008's documentary finding. Nothing was quietly skipped.

## Question

Does every headline number survive three independent checks before it reaches a
document, a workbook or the client?

## The three gates, fixed in the grill

1. **A verifier with hand-typed expected values.** Expected values are typed by
   hand into the verifier, not read from the artifact under test, and the verifier
   exits non-zero on any mismatch. The 2026-09-17 client EDA verifier ran 139
   checks and the annotations audit ran 33; this one carries the same shape.
2. **A byte-identical rerun.** The whole pipeline is deterministic. Sorting uses
   an explicit tiebreaker, and a rerun at a different `PYTHONHASHSEED` produces
   the same bytes.
3. **An independent second derivation of every headline.** Each headline number
   is recomputed by a different route: a second parser, a second reading of the
   XMLs, or a figure that can be reached two ways and must agree.

Plus md5 pairs on every artifact that crosses a machine boundary.

## Deliverable

- `experiments/eda_full/verify_eda_full.py`, the verifier, with its check
  count. (The script itself is no longer in the repository.)
- `run/eda_full_20261015/verification.json`: checks, failures, the rerun's md5
  pairs, and the second derivations.
- `docs/reference/eda_full_verification.md`.

## Acceptance

1. Zero failures. A failure is fixed or documented as a known limit; it is never
   waived.
2. The check count and the failure count are both stated, and the verifier's exit
   code is the gate.
3. Cross-machine artifacts carry md5 pairs from both sides.
4. The independent derivations are named, not just counted.
5. A deliberately broken input makes the verifier fail, which proves the verifier
   bites.
