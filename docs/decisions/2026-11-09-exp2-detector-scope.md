---
title: Experiment 2 scope - YOLO26n detector, seven classes, Bubble and Cluster separate
date: 2026-11-09
type: decision
status: active
where: docs/decisions/2026-11-09-exp2-detector-scope.md
---

# Experiment 2 scope

## Decision

Experiment 2 keeps the twelve trained lens tags in the Experiment 1 nineteen-column head and moves
the seven object classes to a YOLO26n detector. The detector predicts Bubble, Bubble Cluster, Wet
Package, Fiber, Extraneous Polymer, HEMA and Foreign Matter, with Bubble and Bubble Cluster separate.
The pass/fail block is unchanged and reads the detector's class list as its object source.

The lens source is the Experiment 1 head's lens columns; its object columns are ignored, so the lens
side is identical to Experiment 1 and the only changed variable is the object source. The detector
trains on all 5,239 training pictures, with empty label files for the 3,676 that carry no object.
Its confidence is chosen per class on validation, with the Experiment 1 guard: fewer than 10
validation positives keeps a default cut. Test is read once.

The detector dataset is built and verified on the frozen split. Both training arms ran on 10 November:
all pictures (primary) and boxed pictures only (comparison).

## Why

- The lead's 5 November message hands the object classes to a detector in the second experiment, and
  the user asked on 9 November to keep Bubble and Bubble Cluster separate, as in Experiment 1.
- Holding the lens source fixed makes the phase 1 and phase 2 pass/fail numbers comparable. A new
  lens head would change two variables at once.
- The pass rule passes a picture carrying only bubbles and fails contamination, so the detector
  cannot be reduced to a coarse object tag. It must carry the seven classes.
- All training pictures, including object-free backgrounds, match the line's real picture mix and
  give the detector negatives; the bubble-only false fails in Experiment 1 were a specificity
  problem, not a coverage problem.
- YOLO26n is the family already used in the September arena and the crop comparison; the current
  split and annotation are new, so the September numbers are not a baseline.

## Consequences

- Dataset: `/data/FMD_Data_26082026/fmd_detector_20261110`, 7,470 image symlinks and labels, 41 MB;
  verifier exits 0.
- Record: `run/detector_20261110/`; spec: `docs/wayfinder/exp2_yolo_detector_20261109.md`.
- Driver: `vm/drivers/run_yolo26_fmd_detector.py`; both arms complete on 10 November.
- The all-pictures arm stays primary: test mAP50-95 0.1707 against 0.1475 for the boxed-only arm, and
  1 Clear false fail against 47 at the chosen Bubble-and-Cluster cuts. The boxed arm catches slightly
  more fails but is less specific; the background pictures earn their place.
- The detector result is reported through the same block, both pass rules, with the Bubble/Cluster
  confusion beside the per-class AP. No test picture chooses a cut or a model.
