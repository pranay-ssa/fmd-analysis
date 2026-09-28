---
title: run/ep_fiber_check/20260922 - the evidence sheets for the two-name pictures
date: 2026-09-22
type: result
status: active
where: run/ep_fiber_check/20260922/README.md
---

# The two-name pictures, as pictures

Four sheets that let a reader see the Fiber against Extraneous Polymer question and the nine
cross-folder frames for themselves. Built 2026-09-22 from the crops and frames already taken on the
box. Method and the blind read: `experiments/ep_fiber_check/README.md`. The measurement itself:
`run/ep_fiber_check/20260921/README.md`.

## Sheet 1, the three groups

`ep_fiber_evidence_1_groups.png`. Six objects from each group, largest box first, keeping the form
the read put in the majority for that group: 17 objects both folders call Extraneous Polymer, 17 both
call Fiber, and the 34 contested objects. The two agreed groups separate by eye and the contested
objects follow the Fiber group.

**Checked independently after building, without telling the reader which row was which:** the top row
read as thick irregular masses and shreds, the middle and bottom rows as thin strands of near constant
width, and the middle and bottom rows read as alike. That is the same verdict the blind read reached
on the number counts.

## Sheet 2, detail

`ep_fiber_evidence_2_closeup.png`. Three objects from each group at larger size, chosen on form. Same
independent check: the top row thicker and more irregular, the other two rows thin filaments.

The first version of this sheet picked cells by box area, and the top row then held two filaments. The
selection was changed to the recorded form and the caption now says the selection is on form, because
an evidence sheet that shows the wrong half of a group argues against itself.

## Sheet 3, every object in the check

`ep_fiber_evidence_3_all_objects.png`. All 68 objects: the 17 the folders agree are Extraneous
Polymer, the 17 they agree are Fiber, and all 34 contested. The form filter that chooses the cells on
sheets 1 and 2 is switched off here, so the cell count equals the object count and the objects that
read against their group are on the sheet instead of being dropped. A reader who does not trust the
selection on sheets 1 and 2 can work from this one.

## Two faults in the first build, and the fixes

- **The row labels were clipped.** Text was wrapped by character count, so a row label ran wider than
  its column and the image panels were pasted over it. Every block of text is now measured with its
  own font and wrapped to the column it sits in, and each sheet is read back whole before it ships.
- **The completeness sheet was filtering.** It still applied the form filter, so it showed 56 of the
  68 objects while its caption said nothing was filtered. The filter is off on that sheet, and the
  build now prints the cells it drew per group: 17, 17 and 34.

## Sheet 4, the nine frames the two folders name differently

`ep_fiber_evidence_4_cross_folder_frames.png`, with one file per frame beside it. Nine pictures where
the older library and the newer folder give different **box** classes, so it is not one object under
two names but two different claims about the same frame:

| Frame | Older library says | Newer folder says | Boxes drawn |
|---|---|---|---|
| 20241106_092943 on line 24 | Bubble Irregular | Foreign Matter | 1 |
| 20241106_185031 on line 24 | Bubble | Foreign Matter | 25 |
| 20241107_035652 on line 24 | Bubble | Fiber | 17 |
| 20241108_021953 on line 24 | Wet Package | Foreign Matter | 7 |
| 20241109_083707 on line 24 | Bubble | Fiber | 17 |
| 20241109_213824 on line 24 | Bubble | Extraneous Polymer | 3 |
| 20260810_203017 on line 24 | Extraneous Polymer | Foreign Matter | 1 |
| 20241102_140219 on line 27 | Bubble Irregular | Foreign Matter | 2 |
| 20260805_140220 on line 31 | Foreign Matter | Fiber | 1 |

The annotation file carries the older library's class only, so no box exists for the second name.
Read on the frames, at the resolution of the sheet, **the second name is not visible as a separate
object in eight of the nine**. One frame, 20241107_035652, holds a dark particle away from its boxes,
which would fit the Foreign Matter family. The frame 20260810_203017 holds a faint thin scratch and
some faint specks outside its single box; a scratch is not the same claim as a boxed defect.

## What this changes

The 55 two-label pictures are **one disagreement between two folder trees, not 55 multi-defect
frames**. Every one of the 55 sits in the older library and in the newer folder. Not one of them has
two labels inside the older library alone, and not one of them has two classes in its box file. So:

- The text of a claim like "55 pictures hold two defects" is wrong on the evidence. The count 55 is
  right; the reading is not.
- The second-box request to the client changes shape. It is not "box the second object on nine
  pictures", because the second object does not appear to be there. It is "confirm which tree's
  naming is right, and confirm whether these nine were meant to record a second defect at all".
- The multi-object case has **no confirmed example** in this data. That is the number to carry to the
  lead: 0 of the 434 annotated pictures carry two classes in the box file, and the 55 are a folder
  naming difference rather than evidence of co-occurring defects.

## Verified while building

| Check | Result |
|---|---|
| Crops read | 68 crops from 67 distinct pictures, 0 missing |
| Frames pulled for sheet 4 | 9 of 9 resolved on the box, by name and then by date, time and line |
| Frame hashes, box against local copy | **9 of 9 match** |
| Boxes drawn | 1, 25, 17, 7, 17, 3, 1, 2, 1, matching the counts in the split file |
| The blind read of sheets 1 and 2 by a second reader | agrees with the recorded verdicts |

## What this does not settle

- **The read of sheet 4 is a first pass on a downscaled sheet.** One reader, one pass. The originals
  sit beside the sheet as `frame_01` to `frame_09`, so a challenge can be answered at full resolution.
- **The 217 Extraneous Polymer pictures that exist only in the newer folder are still unchecked.**
  This work is about the pictures both trees hold.
- **2 of the 34 contested objects read as a thick mass**, not a filament. The older library's name is
  the better fit for the group, not a perfect fit for every frame.

## Files

| File | What it holds |
|---|---|
| `ep_fiber_evidence_1_groups.png` | the three groups, six objects each |
| `ep_fiber_evidence_2_closeup.png` | three objects from each group, larger |
| `ep_fiber_evidence_3_all_objects.png` | every object in the check, all 68 |
| `ep_fiber_evidence_4_cross_folder_frames.png` | the nine cross-folder frames with their boxes |
| `frame_01` to `frame_09` | one PNG per frame, half size, for a closer look |
| `pictures_to_pull.csv` | the nine pictures with their boxes and both folder paths |
| `pull_report.csv` | the same, with the name the annotation file uses |

Scripts: `experiments/ep_fiber_check/build_evidence_sheets.py` (sheets 1 to 3, from the crops),
`experiments/ep_fiber_check/compose_cross_folder_sheet.py` (sheet 4, from the frames). The crops and
the frames are rebuilt from the box by `crop_source_bmp.py` and by the resolve step recorded in the
scripts.

No local path appears in any sheet caption. The sheets are safe to forward as they stand.
