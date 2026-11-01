---
title: "Map: full-coverage EDA across the three ICube libraries"
date: 2026-10-15
type: protocol
status: done
where: docs/wayfinder/eda_full_coverage_map.md
---

# Map: full-coverage EDA across the three ICube libraries

## Destination

One triple-checked EDA that covers every picture in the three library folders
(Updated ICube Objects 20260915, Updated ICube Categorical Classes 20260915,
ICube Defects Library), with every label resolved under the new priority rule
(the 7 CVAT production files first, then `Updated Annotations 20260922.xml`,
then `annotations.xml`), a frozen canonical crosswalk across the three
annotation vocabularies, the 300 micron debris gate applied to Foreign Matter,
Fiber and Extraneous Polymer, a blind micron-per-pixel determination split by
folder group and by production line, and the 2026-10-13 artifact set (workbook,
HTML report, distributions widget, findings doc) regenerated at full scale plus
a coverage sheet and a crosswalk sheet.

## Notes

- Domain: FMD lens inspection. The three library folders hold 12,079 files
  (1,465 + 4,230 + 6,384) on the shared VM at
  `/home/amd100-user/FMD_Data_26082026/fmd_temp_images/`. `PRODUCTION_20260925`
  sits beside them and holds the 7 newer annotation files plus a second copy of
  1,047 pictures that all already exist in the library folders.
- Skills every session should consult: `fmd-preprocess` for image and crop
  conventions, `xlsx` for the workbook, `simple-english` for generated prose,
  `grilling` when a decision is the blocker.
- **This map carries execution, not only decisions.** The user asked for the
  work divided into subtasks and appended as we go, so the one-ticket-per-session
  rule is relaxed here: tickets may be worked in batches, in dependency order.
- Tracker: local markdown. Tickets live in `docs/wayfinder/tickets/`, blocking
  is written in the ticket body and in the ticket index below, and the frontier
  is the tickets marked open with no unfinished blocker.
- Every doc carries the five-line header and `docs/INDEX.md` is regenerated with
  `tools/index_docs.py` after docs change.
- Numbers go to the user the moment they are read; verification runs in parallel
  and an explicit correction follows if it disagrees.
- Nothing is written to the shared VM tree except the artifact a run is meant to
  write. Scripts live in the repo and are piped over ssh.
- **Count the right thing.** 6,690 pictures are MENTIONED by some file, only 4,782
  carry at least one shape, 5,832 carry no shape, and 3,924 are mentioned nowhere.
  Every table says whether it is a mention count or a shape count. The two
  "unannotated" figures are different numbers and must never be swapped.
- **Key on content md5, never on the path.** 187 basenames hold a content that also
  exists under a second name, so a path-based count undercounts.
- **One production picture is annotated twice.** `20241102_004906_L24_C5_9471.bmp`
  and `20241102_004906_L24_C5_9471_0.6629.bmp` are byte-identical and both carry the
  same eight shapes including `P3_HE` and its gate flag. So 95 label records in the
  production files collapse to 94 pictures, and the "1,047 distinct images" claim
  holds by name but not by content.

## Decisions already taken (grill, 2026-10-15)

1. `PRODUCTION_20260925` stays on the VM as the home of the 7 newer annotation
   files, but it is not an image source: all 1,047 of its pictures already exist
   in the library folders, so the EDA does not report it as a separate folder.
2. Other VM folders (`20260826_T24_Production_Sample`, `Package Find Test`,
   `Ripple Obstruction`, `YOLO26_ICube_Defects`, `crops`, `Utils`) are out,
   unless a defect class turns out to need them.
3. Compute runs on the VM, scripts piped over ssh, only artifacts copied back,
   with md5 pairs on both machines.
4. Label precedence is winner-takes-all per image: the highest-priority file that
   mentions a picture supplies all of that picture's labels, and lower-priority
   files are silent for it. The full disagreement table is published.
5. The consequence of rule 4 is accepted: 708 of the 1,047 production pictures
   lose their Sep-22 tags and 116 lose their old-library boxes, all recorded in
   the disagreement table.
6. One path per picture in the counts: the first library folder that holds it, in
   the fixed order Updated Objects, Updated Categorical, old library.
7. `F2_FOV` against `P2_FOV`, and the `P3_HE` collision (HEMA Fragment in the
   Sep-22 project, HEMA Obstruction in the production files), are kept as
   distinct flagged crosswalk rows. Counting proceeds; the question goes to the
   client in parallel.
8. Bubble On Edge and Bubble Over 123 Mark stay in scope as their own classes,
   tagged library-only, because they have not been consolidated yet.
9. The blind scale test is sampled at 200 per folder group x line, capped where a
   group has fewer, and the cap is reported. The sample is drawn from the full
   universe, not from the 1,047 batch.
10. The 300 micron rule gates Foreign Matter, Fiber and Extraneous Polymer. The
    four `*_MICRON_THRESHOLD` tags in the annotations are the client's authority;
    our own derived cut in microns is reported beside them, not instead of them.
11. Per-line analysis recomputes every headline per line, plus per-line
    microns-per-pixel.
12. Deliverables mirror the 2026-10-13 set plus a coverage sheet and a crosswalk
    sheet.
13. Triple check means a verifier with hand-typed expected values, a
    byte-identical rerun, and an independent second derivation of every headline.
14. The 2026-10-13 EDA of the 1,047 is marked superseded and keeps a delta
    section; it is not silently overwritten.
15. HEMA Obstruction is reported as flagged on every image that carries it, so it
    is not size gated.
16. The 9,391 unannotated blob images get a coverage line only, no pull.
17. This EDA is analysis only. The pooled one-tag-per-image dataset rebuild stays
    its own effort.

## Decisions so far

- [007 Picture census and content identity](tickets/007-picture-census.md): 10,614 distinct pictures; the old library contributes 177 the Updated folders do not hold; all 1,047 production pictures match by content hash and add nothing; the production batch is 1,046 distinct contents, not 1,047.
- [008 Documented nominals for a blind scale reference](tickets/008-documented-nominals.md): zero usable blind nominals and 18.25 is written nowhere, so the absolute blind test is blocked and ticket 013 is split into a variation test that runs and an absolute test that waits on the client.
- [016 Verification gate](tickets/016-verification-gate.md): 157 assertions and 0 failures, 142 figures re-derived through a third implementation, 24 artifacts byte-identical on a from-scratch rerun, five verifiers proven to fail on corrupted input, and the 15.34 inversion reproduced independently from the raw export.
- [014 The 300 micron gate](tickets/014-micron-gate.md): the gate is a clean size cut on the longer side, and inverting the client's own 300 and 647 micron boundaries both give about 15.34 microns per pixel, which agrees with neither 18.1165 nor 18.25.
- [011 Resolved label census and multi-label analysis](tickets/011-label-census-multilabel.md): 20,014 shapes split cleanly into 14,182 boxes and 5,832 tags, codes per picture median 1 and mean 1.68, and the library-only classes stay visible.
- [015 Coverage analysis](tickets/015-coverage.md): the 177 library-only pictures reproduce exactly, but the published 113 figure is a name-based count and on content identity the overlap is larger; and this ticket corrected the map's no-mention figure.
- [013 Blind scale](tickets/013-blind-scale.md): no production line and no folder group differs from another beyond the measurement noise, and the within-stratum spread of 10 to 26 percent dwarfs the 0.7 percent gap between 18.1165 and 18.25, so that gap is not resolvable at all. The absolute blind test stays blocked on the client.
- [010 Label resolution and the disagreement table](tickets/010-label-resolution.md): every listed picture resolves to exactly one source, no picture carries two sources, and 6,690 is a mention count against 4,782 that carry a shape.
- [009 Canonical crosswalk](tickets/009-canonical-crosswalk.md): 28 canonical defects with both collisions kept unmerged; one cell corrected before freeze (HEMA Obstruction is a tag in one project and a box in the other), and per-source kind columns added so the class of error fails a check.

## Not yet specified

- Whether the 9,391 unannotated production images come back as explicit
  negatives, which needs a blob pull and a reason.
- The per-class numeric threshold rule, if the client's 300 micron statement turns
  out to apply to one class only or at a different cut per class.
- Whether Bubble On Edge and Bubble Over 123 Mark are later consolidated, which
  changes every count that carries them.
- Whether the resolved label table becomes the base for a new pooled one-tag
  dataset, once the client answers the questions in ticket 018.
- **What the true scale is.** The client's own gate inverts to about 15.34 microns
  per pixel and agrees with neither figure in circulation, so either the declared
  cut is not exactly 300 microns or our published 18.1165 is wrong by about 18
  percent. Nothing on this map can settle it: it needs a written nominal or the
  client's answer, and until then every micron figure we publish carries that
  question mark. Pixel figures are unaffected.

## Out of scope

- The pooled one-tag-per-image dataset rebuild and every model run on it.
- Task 1 (bubble merge) which has its own map, Task 2 (HEMA Fragment on clear
  images), and the detection and classifier lines generally.
- Pulling the 60 GB image set to this laptop.
- Re-annotating anything, or changing any source annotation file.

## Ticket index

| Ticket | Type | Status | Blocked by |
|---|---|---|---|
| [007 Picture census and content identity](tickets/007-picture-census.md) | task | done | - |
| [008 Documented nominals for a blind scale reference](tickets/008-documented-nominals.md) | research | done | - |
| [009 Canonical crosswalk](tickets/009-canonical-crosswalk.md) | task | done, awaiting the freeze | - |
| [010 Label resolution and the disagreement table](tickets/010-label-resolution.md) | task | done | - |
| [011 Resolved label census and multi-label analysis](tickets/011-label-census-multilabel.md) | task | done | - |
| [012 Box geometry and micron distributions](tickets/012-box-geometry-micron.md) | task | done | - |
| [013 Blind scale: variation test done, absolute test blocked](tickets/013-blind-scale.md) | task | done (013a); 013b on the client | - |
| [014 The 300 micron gate](tickets/014-micron-gate.md) | task | done | - |
| [015 Coverage analysis](tickets/015-coverage.md) | task | done | - |
| [016 Verification gate](tickets/016-verification-gate.md) | task | done | - |
| [017 The deliverables](tickets/017-deliverables.md) | task | done | - |
| [018 Client questions out](tickets/018-client-questions.md) | task | done, awaiting the user to send | - |

All twelve tickets are closed. Two things sit outside the destination and are
follow-ups rather than tickets on this map:

1. **013b, the absolute scale test**, needs a written nominal from the client.
2. **The 18 percent question reaches past this map.** Every defect-size figure quoted
   in microns before 2026-10-15 rests on the same 14,200 micron lens diameter. If the
   client's answer shows that figure is wrong, a separate sweep through the published
   material is owed, and it wants its own map.

## Post-map change, 2026-10-15

The user asked for the microns-per-pixel metric to go into the workbook. The
`Box geometry` sheet was reworked in place: it now names the scale every micron
column uses, carries the true derivation of 18.1165 including that its sample was 200
passing frames from a separate production-sample drop rather than this dataset and
that the 14,200 micron nominal is our own figure, and reports the per-folder and
per-line measurement attempt with the 25.4 percent window failure that makes it not
quotable. Record: `reports/eda_full/scale_derivation_20261015.md`. The October batch
record was marked superseded the same day, and the wording that described its scale as
coming from "200 production images" was corrected.
