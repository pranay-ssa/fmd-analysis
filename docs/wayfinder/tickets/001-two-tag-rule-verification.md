---
title: "Ticket 001: did any earlier run count the 178 Folded Lens pictures against Multiple Lenses"
date: 2026-10-06
type: result
status: done
where: docs/wayfinder/tickets/001-two-tag-rule-verification.md
---

# 001: Two-tag rule verification

Type: research, AFK. Map: [Task 1 bubble merge](../task1_bubble_merge_map.md).

## Question

The lead was told that images with two tags were handled by taking the
primary class, specifically that all 178 Folded Lens images were counted as
Folded Lens and deducted from Multiple Lenses. Is that what any previous run
or split actually did? Checked independently here, while Srikanth checks in
parallel.

## Resolution (2026-10-06)

No. Nothing in this repository counts the 178 as Folded Lens in a single-label
dataset or deducts from Multiple Lenses:

- The pooled one-tag dataset every published split used has no Folded Lens
  class at all (label-space inventory: 0 pictures), and Multiple Lenses keeps
  1,436 of its 1,439 tagging pictures; the 3 it loses go to other tags.
- The 22-class CNN set is built from the older library's 22 folders, which
  contain no Folded Lens folder.
- The multi-label line is multi-label by design: 1,442 and 178 both keep all
  their pictures, and 1,442 minus 178 equals 1,264 was published as "Multiple
  Lenses pictures without Folded Lens", which is tag presence.
- The export inventory records Folded Lens with 0 pictures in a folder named
  for it, all 178 sitting in the Multiple Lenses folder.

So a folder-based single-label reading puts the 178 in Multiple Lenses, the
opposite of the claim. If a reduced Multiple Lenses count was shown to the
client it came from outside this repo (teammate workbook or meeting
arithmetic), which is where the parallel check should look.

Full evidence: `docs/two_tag_rule_verification_20261006.md`.

## Consequences for the map

Nothing in the data changes. The destination absorbs one obligation: the
written result must state the one-tag rule as it actually stands, so the
conversation with the client is corrected with evidence rather than memory.
