---
title: Clear excluded from the frozen experiment splits
date: 2026-11-19
type: decision
status: active
where: docs/decisions/2026-11-19-clear-excluded-frozen.md
---

# Clear excluded from the frozen experiment splits

The lead confirmed on 19 November 2026 that the 42 Clear pictures are excluded from the frozen experiment population.

- Clear is not a model column. It is the all-zero row, and it is now removed.
- The six classes below 200 pictures stay excluded as columns: Edge Bottle-Capped 24, Lens Rupture 35, Torn Lens 117, Bubble Scatter 12, Dirty Strobe 33, Surface Groove 88.
- The class cut removes no pictures. No picture carries only an excluded class. The 281 pictures that carry an excluded class also carry a kept class and stay in the split.
- Split population: 13,673 labelled minus 42 Clear = 13,631 pictures.

Consequence for the rule: pass is no longer "Clear or bubble or untagged size". With no Clear rows, a picture passes only when it carries no lens tag, no size tag, no Wet Package, and every object is Bubble, Bubble Cluster under the secondary order, or an untagged object of the four size-flagged classes. The six excluded classes cannot fail a picture because the model cannot see them.
