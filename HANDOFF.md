---
title: Handoff (state of the work)
date: 2026-10-28
type: state
status: active
where: HANDOFF.md
---

# fmd-analysis - Handoff

**Resume here:** the re-export is fully absorbed and measured. The merged annotation of
record over all 24 files is `run/eda_full_24files_20261028/` (5,500 marked + 2,117 Clear =
7,617 pictures), and two review workbooks are built and verified in
`reports/eda_24files_20261028/` - the 24-file batch EDA and the cumulative record. They await
the user's review on 2026-10-29. The splits (`run/split_20261028_v6/`) and the LP label tables
still sit on the pre-merge seven-file record (6,659 rows); whether the 24-file population joins
the experiment is the open decision. Both LP variants are trained; metrics are local in
`run/multilabel_lp_full_20261028/`. Read `session_shakehand.md` for the working context and the
traps; this file keeps the repository state.

The split rules are frozen and v6 is the current split for the trained models. The reply
workbook still shows the pre-merge annotation and needs rebuilding on the merged record. Open
items: the Fiber/Extraneous Polymer naming, the P3_HE name collision (client ruling), the three
duplicate picture entries in the 24-file export, and ticket 022's remaining legs (picture-by-
picture checks of the parked items: Fiber gate, Folded Lens 237-vs-178, the 84-picture rescue
set).

**State**

- 2026-10-28 (re-export absorbed, merged record, 24-file EDA workbooks):
  - Twenty-four files arrived from the client under `PRODUCTION_20260925_300/`, 3,597
    entries / 3,594 pictures; the seven we held were revised, seventeen are new. The
    previous seven are archived in `data/incoming/20261026_previous/`.
  - The 7-file revision changed 133 of the 1,047 old pictures. Box-level diff: 118 folded
    into Bubble, 11 debris moves, 2 other relabels, 2 box moves. (The earlier 114 / 13 / 4 / 2
    split was approximate; the workbook's per-picture sheet is the record.)
  - Merged record over all 24 files: `run/eda_full_24files_20261028/`, 14/14 checks,
    5,500 marked + 2,117 Clear = 7,617 pictures. The 17 files add 719 pictures and 2,403 class
    labels and remove 70 label instances (21 naming/fold artifacts, 49 real relabels).
  - Total EDA workbook `reports/eda_total_20261028/` (Summary, LP Summary, Tag Combinations,
    OOI Summary, split before and after, Reconciliation) and the v7 split in
    `run/split_20261028_v7/`: 7,470 rows (70/30 5,235 / 2,235; 80/20 5,989 / 1,481) against
    6,659 (4,653 / 2,006; 5,327 / 1,332) before. 279 pictures were outside a split before,
    147 after (62 legacy-only, 85 un-gated object-only). The EDA counts every picture of a
    class with the gate as "of which size-flagged"; only the split uses the gate positives.
    The workbook reconciles with the record workbook on every row.
  - Two workbooks, client-safe and verified (tamper proof): `reports/eda_24files_20261028/`
    `FMD_EDA_24Files_20261028.xlsx` (7 | 17 | 24 per tier, OOI tag analysis and distribution,
    one row per changed picture with a reason) and `FMD_EDA_Record_20261028.xlsx`
    (before/after per class). After the review the tiers are named OOI tags (boxes) and
    Lens Presentation (whole-image tags), every row carries the guide code, all 15 LP and 8 OOI
    guide classes are listed including the four zeros, and the three legacy classes are grey
    and marked. OOI: 2,089 pictures, 36,098 tags. Numbers as CSVs in
    `run/eda_batch24_20261028/`; builders `ooi_stats.py`, `build_eda_24files.py`,
    `verify_eda_24files.py`.
  - The pre-merge seven-file record stays current for the experiment: `run/eda_full_20261028/`,
    `run/split_20261028_v6/` (6,659 rows), `run/multilabel_lp_full_20261028/` (A 6,219 at
    4,971 / 1,248; B 6,659 at 5,327 / 1,332).
  - VM staging complete under `/home/pranayp/fmd-analysis` (md5 manifests matched, 24 files);
    labels-only and smoke green; GPU fixed (7.0 kernel + NVIDIA modules, torch 2.14.1+cu126);
    both variants trained on the A100 (A 1,451 s training, 24.2 s inference; B 1,479.9 s,
    7.7 s). Metrics pulled local.
  - Data quirks: three pictures are listed twice in the export (one identical pair, two
    differing by 1 and 7 marks); one picture is listed with no marks and loses its only label
    under precedence. Both are in the workbook change sheets.
  - `experiments/multilabel_edge/delta_annotations.py` compares two sets of annotation
    files: pictures added or removed, codes added or removed per picture, boxes moved
    (paired by nearest centre), tags added or removed, and the class totals that shift.
    Tested both ways: identical input reports zero, and a copy with one box removed and
    one moved reports one changed picture, P2_BB -1, one moved.
- 2026-10-27 (multi-label LP experiment, one file, two variants):
  - `experiments/multilabel_lp_full/train_lp.py` builds labels from the
    annotation, trains ResNet50 with 12 independent condition outputs plus Clear,
    and in variant B one coarse object-present output. Labels are written and
    checked without torch: variant A 6,219 rows (4,971 / 1,248), variant B 6,659
    (5,326 / 1,333), 440 object-only.
  - Reader-facing notebook `notebooks/FMD_MultiLabel_LP_AllTags.ipynb` (17
    sections, real counts embedded, no internal names), regenerated by
    `make_notebook.py`.
  - Rule 13 added to the split decision: a legacy mention does not disqualify a
    picture that carries a Draft 2 code. The eight HEMA-Obstruction-tagged
    pictures that also carry a condition stay rows, contribute only that
    condition, and read 0 on the object flag.
  - VM readiness: data root `/data/FMD_Data_26082026/fmd_temp_images` holds all
    three top folders; torch is not installed; the GPU driver needs the pending
    reboot before `nvidia-smi` works; the staged tree needs `run/` (not `runs/`)
    beside `experiments/` so the input paths resolve.
- 2026-10-26 (split considerations frozen after the lead asked that the approved
  EDA distribution be kept):
  - Decision `docs/decisions/2026-10-26-split-considerations.md`: annotation
    population, Draft-2 codes plus Clear, legacy classes excluded (105 pictures),
    gated object classes positive on the micron gate only (FM 171, Fiber 136,
    EP 33, HEMA 94); the gate rule applies to those four classes only, so a
    picture is dropped only when it has no positive at all (174 debris-only
    pictures, plus 105 legacy-only).
  - New splits `run/split_20261026_v5/` (70/30 4,653 / 2,006; 80/20
    5,326 / 1,333; 6,659 rows), builder `build_split_v5.py`, verifier
    `verify_split_v5.py` (PASS, tamper proof). Every non-gated class now equals
    its EDA count (Bubble 862, Bubble Cluster 428, Multiple Lens 1,439); Fiber
    gate is 136.
  - `run/split_20261023_v4/` stays as the record for the models already trained.
- 2026-10-25 (review message on tag combinations and object counts):
  - OOI correction: the object table counted only guide-coded shapes while its
    picture column came from the matrix, so 1,095 older-library plain-name
    objects on 229 pictures were never attributed and HEMA read 99 instead of
    103. Corrected counts in `docs/reference/draft2_eda_ooi_20261023.md`
    (Bubble 11,045/862, Cluster 1,182/428, WP 662/146, Fiber 245/178,
    EP 150/144, HEMA 103/101, FM 626/331, all 14,182 on 1,130 pictures).
    Artifact `run/draft2_eda_20261023/ooi_objects_all.json`, builder
    `experiments/multilabel_edge/correct_ooi_object_counts.py`.
  - HEMA check: the legacy object class is HEMA Fragment, not HEMA
    Obstruction (P2_HMO is a whole-image tag, 86 pictures, kept separate). All
    8 HEMA Fragment pictures count as HEMA: 4 also carry a newer production
    annotation, the other 4 are folded in by the correction.
  - Reply workbook, second version 2026-10-26:
    `reports/draft2_eda_20261023/Tag_Combinations_Answer_20261026.xlsx` (8
    sheets), builder `experiments/multilabel_edge/build_answer_v2.py`,
    verifier `verify_answer_v2.py` (recomputes from the annotation, compares by
    row label, tamper proof). The 25 October draft was deleted; this is the only
    reply workbook.
  - Label space corrected 2026-10-26: labels are counted from the annotation
    (one annotation of record per picture), size flags sit INSIDE their class
    (never a label), Clear is a label, and the 3 legacy names are counted as
    labels. Labels per picture: 0 -> 0, 1 -> 5,531, 2 -> 649, 3 -> 418,
    4 -> 199, 5 -> 97, 6 -> 29, 7 -> 12, 8 -> 3 (6,938 total). 28 distinct
    pairs. The old 248 / 5,301 / 660 / 424 / 207 / 71 / 20 / 5 / 2 came from
    the training label list: 143 pictures marked only with an OOI object had no
    class column, and 105 carried only a legacy name.
  - Population reconciles with the onboarding report: 6,938 = 4,782 with a mark
    + 2,156 Clear; the onboarding table covers 4,141 (whole-image tags only) =
    6,938 - 641 box-only - 2,156 Clear.
  - Debris group (FM + Fiber + EP + HEMA): 647 pictures, 96 holding more than
    one class, 388 with at least one object over the size threshold.
  - Audited every training-list column against the annotation: only two drift.
    `fiber_micron_gate` 168 vs 136 (the 32 EP objects recoded as Fiber by the
    guide default, 31 flagged), and `bubble_cluster` 430 vs 428 (two pictures
    keep an older library Bubble Cluster label while their newer annotation has
    none). Noted in the workbook; the list stays frozen for the split.
  - Draft 2 EDA rebuilt 2026-10-26 on the same rules:
    `reports/draft2_eda_20261023/EDA_Draft2_20261026.xlsx` (9 sheets, builder
    `experiments/multilabel_edge/build_eda_draft2_v5.py`, verifier
    `verify_eda_v5.py`). It supersedes `EDA_Draft2_20261023.xlsx`. Changes:
    labels per picture 0/5,531/649/418/199/97/29/12/3; exact pairs 28 (649
    pictures), inclusive pairs 83; objects 11,045 / 1,182 / 662 / 626 / 277 /
    118 / 103; Bubble Cluster 428; sizes recomputed over every object including
    the older names; Summary gains the object classes and the Debris group; the
    split sheet reproduces the frozen split and says it counts split positives.
  - Reply convention for Fiber / Extraneous Polymer: the 32 objects keep the
    earlier Fiber name so the columns agree with the onboarding report (Fiber
    277/210, EP 118/112); the annotation reading is 245/178 and 150/144 and is
    stated in a note on the sheet. Next annotation uses the newer name.

- Ticket 023 (standalone-tag audit) done 2026-10-23: zero violations. All
  pictures carrying P1_MPP (1,426), P1_PPM (2), P1_COC (184) or F2_FOV (24)
  carry only that label. P2_FOV exists in the Sep-22 project but tags zero
  pictures. Two derivations agree (resolved line + raw parse of all eight
  newer files); artifacts in `run/multilabel_edge_20261023/`, script
  `experiments/multilabel_edge/standalone_audit.py`.
- Ticket 024 (guide confusion table) done 2026-10-23: 14 rules from Draft 2
  in `docs/reference/guide_confusion_table_20261023.md`, with matrix counts
  and pair co-occurrence. WP-Bubble 117 co-occur, LOC-LD 17, ML-FL 236
  (co-tag rule). EBC, TL, LR, SG and HEMA-as-P3_HE have no data yet.
- Ticket 026 done 2026-10-23 with ONE USER QUESTION OUT: 10 Clear-folder
  pictures carry only a Dirty Camera tag and are labeled Clear AND Dirty
  Camera (builder never checks LP columns before granting Clear). Under the
  strict meeting reading they would be Dirty Camera only. Asked by Telegram
  2026-10-23; 10 rows = 0.15 percent, nothing blocks on it.
- Ticket 025 done 2026-10-23: Draft-2 EDA in two parts, plus the approved
  9-sheet consolidated workbook `reports/draft2_eda_20261023/EDA_Draft2_20261023.xlsx`
  (Overview, LP Tags, LP Co-occurrence, OOI Boxes, Standalone Audit, Guide
  Summary, Class Summary, Tag Combinations, Objects, Standalone Tags,
  Confusion Risks, Earlier vs Current, Training and Test Split, Definitions;
  verifier `verify_eda_draft2_workbook.py` recomputes every headline,
  0 failures, corrupted-cell proof catches a tampered cell). Spec builder
  `experiments/multilabel_edge/build_eda_draft2_client_spec.py`. The
  workbook is READER-FACING per the new AGENTS.md rule: no internal paths,
  script names, ticket ids or version tags; plain headers that name their
  population; definitions sheet; styled headers, frozen panes and a chart.
  LP: 11 live tags (ML 1,433, MPP 1,426, LOC 953 lead; PPM 2, BSC 6, FOV 24
  trail), EBC/TL/LR empty. OOI shape line: 1,130 pictures, 12,783 boxes,
  79 percent Bubble (10,070 boxes, median 11 per picture, 6.6 x 6.4 px).
  Docs: `docs/reference/draft2_eda_lp_20261023.md` and
  `draft2_eda_ooi_20261023.md`; workbook
  `reports/draft2_eda_20261023/draft2_eda_20261023.xlsx` (verified against
  run/draft2_eda_20261023/*.json, 0 mismatches).
- Ticket 021 done 2026-10-23, REVISED same day (user decision): split label
  space = Draft 2 codes plus Clear only. On 123, On Edge, HEMA Obstruction
  excluded as classes; gate tags mark the four gated families. Universe
  6,679 to 6,574 (105 rows carried only excluded labels: 78 HEMA-only,
  13 On-123-only, 14 On-Edge-only). THEN v3 (Option A,
  Clear exclusive, user decision same day): matrix rev2
  `run/multilabel_edge_20261023/` (builder `build_label_matrix_rev2.py`),
  Clear 2,156; the 10 Clear+Dirty Camera rows are Dirty Camera-only.
  ACTIVE SPLIT: v3, `run/split_20261023_v3/split.csv` + `meta.json`,
  builder `experiments/multilabel_edge/build_split_v3.py`, verifier
  `verify_split_v3.py` (all triple-check legs pass). 4,568 train / 2,006
  test. v1 and v2 stay on disk, superseded.
  Rare columns now: PPM 1/1, BSC 4/2, FOV 17/7, EP gate 25/8.
  Decision record: `docs/decisions/2026-10-23-split-label-space.md`.
  v1 (6,679 rows, included the legacy classes) stays on disk, superseded.
  Merged-Bubble measurement: BI 100 percent contained in P2_BB; merged
  Bubble = 750 shape-line / 862 matrix (789 in the v2 universe).
- Draft 2 guide confirmed as 15 LP tags + 8 OOI box classes; the standalone
  rules sit in guide sections 4.1 to 4.4. F2_FOV vs P2_FOV is with the lead;
  working assumption: P2_FOV is the guide code (ticket 018 open question).
- The pre-meeting state stands: label matrix + EDA user-accepted
  2026-10-21 (6,785 usable, 6,679 split-eligible), VM hash verification done.

**Next, in order**

1. User reviews the two EDA workbooks (2026-10-29) and raises questions; answer from the
   number CSVs and the annotation.
2. Decide whether the 24-file population joins the experiment. The v7 split measures what
   joining would look like (7,470 rows); if yes, rebuild the LP label tables on it and retrain.
   The trained A/B models stay as the pre-merge measurement until then.
3. Rebuild the reply workbook on the merged record (the old one answers with pre-merge counts).
4. Client rulings: P3_HE, Fiber/Extraneous Polymer; annotation owner: the duplicate entries
   and the picture listed with no marks.

**Decisions that are settled and must not be relitigated**

- Gate IS the class for FM/Fiber/EP/HEMA; plain-family carriers without a
  gate drop (153) or lose split eligibility (106).
- Clear = winning path in a Clear folder of the two Updated libraries
  (2,166); the 2026-10-22 meeting confirms Clear as the third namespace.
- Standalone tags carry no co-tags (ticket 023, measured, not assumed).
- Unannotated pictures (3,676) are out: 0 tags = no tags.
- BI and BST fold into Bubble; Bubble On 123, Bubble On Edge and HEMA
  Obstruction stay as classes despite Draft 2 (workbook discrepancy notes).
- 70/30 two-way split, seed 42, content-md5 groups; no validation split.
- Draft 2 codes and the legend in every artifact.

**Rules in force**

All compute local; the amd-a100 VM read-only (hash/census proofs), scripts
piped over ssh, nothing written to the shared VM tree. Triple check means a
verifier with hand-typed expected values, a byte-identical rerun, and an
independent second derivation. Numbers go to the user the moment they are
read. Pitfalls log at `docs/pitfalls.md`. Five-line headers on every doc;
`docs/INDEX.md` regenerated after doc changes.

**Open questions carried forward**

- Where training will run when the experiment starts: the image pixels sit
  on the VM (about 34 GB for the usable set); local work so far is labels
  and split only.
- The client questions still out (ticket 018): P3_HE collision, F2_FOV,
  P2_BST, the 300 micron gate cut, Low Dose task completeness.
- Whether the rare columns (PPM 2, Bubble Scatter 6, On 123 13, On Edge 14)
  are modeled or parked; whether Clear is downweighted at training time.
- The 70/30 two-way split has no validation set: the trainer must use a
  fixed schedule and never select on the test set.
