---
title: Decision - Multi-label Edge experiment label frame
date: 2026-10-21
type: decision
status: active
where: docs/decisions/2026-10-21-multilabel-edge-frame.md
---

# Decision: Multi-label Edge experiment label frame

Settled in the grill on 2026-10-21 against the FMC Annotation Guide Draft 2
(`D:/FMD-KB/Annotation Guides/`), which is authoritative for class names and codes.

## Settled decisions

1. **"Edge" means the client's edge algorithm**: the four micron gates decide
   pass/fail, so for Foreign Matter, Fiber, Extraneous Polymer and HEMA the
   gate IS the class. One column per family, named as the gate tag
   (`P3_FM/FIB/EP/HE_MICRON_THRESHOLD`). No plain FM/Fiber/EP/HEMA-Fragment
   column exists in this experiment.
2. **Drop rule**: a picture carrying a plain FM/Fiber/EP/HEMA-Fragment code
   with no gate tag is excluded from the dataset entirely. Corrected census
   (grill round 5): 259 pictures carry a plain family with no gate; the EDA
   drops the 153 whose only defects are plain-family and not saved by the
   flip; it keeps the 75 mixed pictures carrying their other labels. The
   split reading additionally excludes every gate-less plain carrier in the
   matrix irrespective of other tags: 106 pictures (the 75 mixed plus 31 of
   the 33 flipped). An earlier figure of 345/270/75 mixed up the production
   `P3_HE` boxes with the plain-HEMA set; superseded by this census.
3. **Bubble frame**: Bubble Irregular and Stretched Bubble fold into Bubble
   (Draft 2 consolidates them into P2_BB). Bubble On 123 and Bubble On Edge
   stay their own classes - a deliberate departure from Draft 2, which
   deprecates both; the discrepancy is carried in the workbook.
4. **HEMA Obstruction stays as a legacy class** (86 pictures, Sep-22
   `P2_HMO`), although Draft 2 retires the tag with no successor. The
   discrepancy is carried in the workbook.
5. **Universe**: all 10,614 distinct pictures of the three libraries, labels
   from winner-takes-all resolution (7 production files, then Sep-22, then old
   library). Clear = 1 only when the picture carries no defect-class label;
   LP tags do not block Clear.
6. **Column scope**: every tag class with at least one shape (5 previous LP
   classes plus Dirty Camera, Dirty Strobe, Low Dose, View Obstructed,
   Primary Package Misalignment, Bubble Scatter), the defect boxes (Bubble,
   Bubble Cluster, Bubble On 123, Bubble On Edge, Wet Package), HEMA
   Obstruction, the 4 gates, and Clear: 23 columns. New Draft 2 classes with
   zero data (P1_EBC, P1_TL, P1_LR, P1_SG) are skipped.
7. **Fiber/EP flip**: pictures annotated Fiber in an older vintage and EP in
   the winning vintage count as Fiber (Draft 2 section 5.4B makes
   uncertainty-defaults-to-Fiber the rule). Applied from a verified
   picture-by-picture list, never from a count coincidence.
8. **Split**: 70/30 two-way, iterative stratification (Sechidis), seed 42,
   grouped on content md5, saved split file plus meta JSON. No validation
   split; the trainer must fall back to a fixed schedule and never select on
   the test set.
9. **Codes and legend**: every report and workbook names classes by Draft 2
   code and name (No Lens P1_NL, Multiple Lens P1_ML, Primary Package
   Misalignment P1_PPM, HEMA P3_HE, and so on) and carries the legend sheet.
10. **Outputs land in new dated directories**; nothing from the 2026-10-15
    EDA is overwritten.

11. **Two readings, one artifact** (grill round 4, 2026-10-21): the EDA
    reading keeps the 33 flipped pictures as Fiber positives and keeps the
    75 mixed plain-family pictures carrying their other labels (drop set is
    the 153 pictures whose only defects are plain-family and that the flip
    does not save). The split
    reading additionally excludes, irrespective of other tags, every
    picture in the matrix that carries a plain FM/Fiber/EP/HEMA code with no
    gate tag: 106 pictures (the 75 mixed plus the 31 gate-less flipped). The split is built on the
    split reading; `split_eligible` carries it per picture.
12. **Fiber/EP flip set verified**: the 33 are exactly the Fiber-to-EP
    disagreement set (1:1 with the ep_fiber_check group-A contested list,
    md5-keyed). The `P3_EP_MICRON_THRESHOLD` gate set is also 33 but
    overlaps it by only 2 md5s; the coincidence is documented, never used.
    Flip list: `run/multilabel_edge_20261021/fiber_ep_flip_list.csv`
    (md5 `b14215ca1637fe103c1bd1bd8e06ee47`).
13. **Bubble Cluster facts** (census, 2026-10-21): it is never a tag in any
    source (0 instances). The library Bubble Cluster folder holds 21
    pictures whose 111 shapes are all boxes named Bubble Cluster. The 6
    bubble-family tags that exist are P2_BSC Bubble Scatter (Sep-22). 14
    old-library BC pictures duplicated into newer folders lost their labels
    to winner-takes-all and read as Clear in the resolved labels; flagged
    in the workbook.

14. **Clear is a folder-derived class** (grill round 6, 2026-10-21): Clear =
    the winning path sits in a Clear class folder of the two Updated
    libraries (2,333 pictures); defect annotations from any older (losing)
    file rescue a folder picture into its defect class; plain-family
    carriers in the folder still go through the gate drop rules. Clear class
    after the rule: 2,166, all reliable by folder membership. This replaces
    the earlier computed-absence definition (which had inflated Clear to
    9,392 with 5,832 unreliable negatives).
15. **Unannotated pictures dropped** (resolved 2026-10-21): the 3,676
    matrix-less pictures - 1,907 name-listed empty by the Sep-22 export and
    1,769 never listed in any annotation file - are not required for the
    experiment (0 tags = no tags). Final usable set: 6,785 pictures (4,619
    labeled + 2,166 Clear); split universe 6,679 after the 106 gate-less
    plain carriers. VM hash sweep the same day verified all 12,079 library
    bitmaps byte-identical (10,614 distinct contents).

## Consequences accepted

- The four gate classes exist only where the production files annotate, so
  those classes are production-vintage only.
- Old-library and Sep-22 plain FM/Fiber/EP/HEMA pictures leave the dataset;
  per-class comparability with earlier experiments breaks for those families.
- Multi-label metrics, not accuracy: mean per-class average precision against
  prevalence, sigmoid-plus-threshold inference, float multi-hot targets.
