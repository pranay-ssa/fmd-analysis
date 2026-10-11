---
title: Did any earlier run count the 178 Folded Lens images against Multiple Lenses
date: 2026-10-06
type: result
status: active
where: docs/two_tag_rule_verification_20261006.md
---

# Two-tag images: what rule earlier runs actually followed

**The claim being verified.** In conversation with the client it was said that
images carrying two tags were handled by taking the primary class, and
specifically that all 178 Folded Lens images were counted as Folded Lens and
deducted from Multiple Lenses. That claim may be wrong, and the question asked
was: did any previous run or split follow this rule?

**Answer: no.** No dataset, split or run in this repository counts the 178
images as Folded Lens, and no run deducts anything from Multiple Lenses.
Folded Lens is not a class in any single-label dataset here at all. Checked
2026-10-06 on this machine; the shared VM and teammate artifacts were not
touched, as agreed.

## What was checked, and what it showed

1. **The one-tag dataset that every line model and every published split used
   (rule R5 of the line-split builder: the older library decides, then the
   Updated Objects folder, then the Updated Categorical folder).** Folded Lens
   is not one of its classes: the label-space inventory of 2026-09-21 records
   Folded Lens with 0 pictures, because no folder in the data carries that
   name. Multiple Lenses is carried by 1,439 pictures as a tag and is assigned
   1,436 of them; the 3 pictures that go elsewhere go to other tags, none to
   Folded Lens. Every one of the 8,409 assigned pictures was compared against
   the frozen builder's own output, picture by picture, with zero
   differences (2026-10-06, 62 checks, 0 failed).

2. **The 22-class CNN set (1,465 pictures).** Its 22 classes are the older
   library's 22 class folders, and that list contains no Folded Lens folder,
   so a Folded Lens class cannot exist in that set and Multiple Lenses cannot
   have been reduced by it.

3. **The multi-label line on the annotation export (3,377 rows).** This line
   is deliberately multi-label: Multiple Lenses is 1,442 and Folded Lens is
   178, and all 178 pictures sit in both columns, so nothing is deducted from
   anything. The decomposition 1,442 = 178 + 1,264 was quoted to the lead on
   2026-09-29, in exactly the words "1,264 Multiple Lenses pictures without
   Folded Lens", which is tag presence, not a single-label assignment.

4. **The annotation export inventory of 2026-09-23.** Its row for Folded Lens
   records 178 pictures and **0 pictures in the folder named for it**, with
   the folder listed as Multiple Lenses. A folder-based single-label reading
   therefore puts all 178 into Multiple Lenses, which is the opposite of the
   claim.

5. **A repository-wide search for the rule itself.** No script, split file or
   report contains a single-label Folded Lens assignment, a deduction from
   Multiple Lenses, or any count of 1,264 as a dataset figure.

## What this means

- The data does not need correcting: in every single-label dataset here,
  Multiple Lenses keeps all of its pictures and Folded Lens does not exist as
  a class; in the multi-label line both columns keep the 178.
- The statement as remembered matches no artifact in this repository. The
  closest real number is 1,442 minus 178 equals 1,264, published as the
  number of Multiple Lenses pictures that do not also carry Folded Lens.
- If a Multiple Lenses count reduced by 178 was shown to the client, it came
  from outside this repository (a teammate workbook or meeting arithmetic),
  and that is where an independent check should look. This is recorded as an
  open item for Srikanth's parallel verification.

## Independent check on the VM (2026-10-07)

The same question was put to the VM's own artifacts, read-only, while the
Task 1 training ran. All 11 previous split files on the VM were scanned, plus
the class directories of every dataset root and every library folder under
the image root:

- **No split has a Folded Lens class.** The five pooled line splits, the
  22-class CNN set, both lens-presentation sets, the OoI sets, the YOLO split
  and the smoke subset all list their classes, and none contains a "fold"
  class of any spelling.
- **The pooled line splits give Multiple Lenses = 1,436** (L24 335, L25 276,
  L26 674, L27 54, L31 97), which is exactly the undeducted pool figure: tag
  presence 1,439 with 3 pictures taken by other tags. A 178 deduction would
  read 1,258, 1,261 or 1,264; none of those numbers appears anywhere.
- **No Folded Lens folder exists** in any dataset root's train or test tree,
  and none in any library folder under
  `/data/FMD_Data_26082026/fmd_temp_images`.

So the VM side says the same thing the repository side says: earlier splits
counted the 178 Folded Lens pictures inside Multiple Lenses, never as a
Folded Lens class, and never deducted them. Script and captured output:
`experiments/bubble_merge/q5_vm_check.py` and
`run/bubble_merge/20261006/q5_vm_check_output.txt`.

## Scope and caveats

Repository scripts, split files, label inventories and reports were checked
locally on 2026-10-06; the VM's own split files, dataset roots and image
library were checked read-only on 2026-10-07 (above). The trained-model
workbooks and the teammate's own tables have still not been read: that part
of the parallel check remains with Srikanth. One local comparison could not
be run (a scratch probe of the two-tag pair breakdown) because it did not get
execution consent; the number it would have produced, the count of two-tag
pictures, was instead reproduced by the main verifier as 55, matching the
figure published to the client on 2026-09-17.

---

*Internal record. Evidence: `run/multilabel_eda/20260921/1_label_space.csv`,
`run/annotations_audit_20260923/labels.csv`,
`run/annotations_audit_20260923/multi_label_lp_analysis.json`,
`src/make_line_splits.py`, `experiments/bubble_merge/verify_labels.py`,
`reports/multilabel/teams_message_baseline_vs_multiscale_20260929.md`.*
