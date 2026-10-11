---
title: Pos-weight architecture sweep: all four notebook architectures rerun with the class weight
date: 2026-10-06
type: result
status: active
where: reports/multilabel/ml_posw_arch_sweep_20261006.md
---

# Pos-weight architecture sweep, 2026-10-06

The four notebook architectures were rerun with the Folded Lens class weight on. Each run
kept the recipe of the 2026-10-05 weighted baseline (same labels, same 80/20 split of
2,700 train and 677 test, SGD, batch 8, 50 epochs, seed 42, pos weights 17.49 / 18.01 /
1.34 / 1.37 / 9.38) and changed only the architecture. All four runs exited 0 on the A100.

## Plain vs weighted, all five architectures (677 test pictures, cut 0.5)

| Architecture | FL recall, plain | FL recall, weighted | FL F1, weighted | FL AUPRC, weighted | Macro F1, weighted | Exact match, weighted |
|---|---|---|---|---|---|---|
| ResNet 50 (standard) | 5.6% | 47.2% | 0.507 | 0.622 | 0.892 | 0.945 |
| MultiScale | 0% | 58.3% | 0.525 | 0.582 | 0.898 | 0.938 |
| Attention SE | 0% | 77.8% | 0.500 | 0.675 | 0.896 | 0.913 |
| Inception + attention | 0% | 58.3% | 0.462 | 0.600 | 0.890 | 0.925 |
| Inception + refined decode | 0% | 61.1% | 0.571 | 0.617 | 0.914 | 0.951 |

## What the table says

- The class weight lifts Folded Lens on every architecture, including the four whose
  Folded Lens scores were all negative without it. The patch is architecture-independent.
- The best combined row is Inception + refined decode: Folded Lens F1 0.571 at recall
  61.1%, every other tag at precision 1.0 and recall 1.0, exact match 0.951, the highest
  of any run on this line.
- Caveat: these are single runs. The line's repeat-run band is 0.037 macro F1. The
  Folded Lens recall moves (0 to 58 to 78%) sit far outside the band, so they are real.
  The precision differences between rows sit inside it, so they are not claimed.

## Comparability note

The four architecture runs print the same tap warning as the 2026-09-29 plain sweep
(the residual-add hook misses and the taps fall back to the post-ReLU stage outputs).
Same behaviour on both sides of the comparison, so the plain vs weighted rows are
readable against each other.

## Status

The artifacts are mirrored under the run folder (metrics, histories, logs), md5-checked
against the VM. The user is holding this data out of the weekly deck until after the
daily meeting; the deck is unchanged.
