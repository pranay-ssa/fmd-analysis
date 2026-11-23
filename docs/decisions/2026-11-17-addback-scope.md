---
title: Frozen add-back scope - 147 held, 27 discarded
date: 2026-11-17
type: decision
status: active
where: docs/decisions/2026-11-17-addback-scope.md
---

# Frozen add-back scope

## Decision

- **27 pictures are discarded.** They carry the two legacy reference classes, Bubble On Edge 14 and
  Bubble On 123 13. They will not be added to the frozen set.
- **147 pictures are held** pending client confirmation. They are not in the store and do not count
  towards the working total.
- **The working count stays 13,682** until that confirmation arrives.

## Why

The 147 map to current classes: 121 directly, and 26 Bubble Irregular through the existing fold into
Bubble. They are usable, but adding them changes the dataset size, so the client confirms first.

The 27 have no class in the current guide, no experiment uses them, and no fold rule covers them.

## Resolved on the way

One picture appeared under two names with two labels, Multiple Lens from the 22 September file and
Wet Package from the older file. The priority rule gives the newer file the label, so Multiple Lens
stands and the Wet Package entry is dropped. That is why the candidate count is 174 and not 175.

## Consequences

- `addback_candidates.csv` carries a `decision` column: 147 `pending_client`, 27 `discarded`.
- `images/` stays at 13,682 pictures.
- The 147 source files stay in the library tree. They are not in the 13,270-file duplicate set, so
  deleting that set later does not remove them.
- If the 147 are approved, the set becomes 13,829 pictures and they are appended to the manifest, never
  edited into it.
