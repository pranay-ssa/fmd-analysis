---
title: experiments/ep_fiber_check/ - is Fiber against Extraneous Polymer a naming choice or a misfile
date: 2026-09-21
type: experiment
status: active
where: experiments/ep_fiber_check/README.md
---

# Fiber against Extraneous Polymer, judged on the frames

## The question

33 pictures sit in two folders under two names. The older library calls them `Fiber`. The newer
folder calls them `Extraneous Polymer`. Both folders agree on every other picture in those two
classes.

The claim in the strategy doc was that this is one object under two names, so the client picks the
taxonomy and the pipeline pools the labels under one class. That claim was an inference from the
folder record, not a measurement. This experiment measures it. The answer decides two things: which
name the pipeline should keep, and whether the classifier's Fiber against Extraneous Polymer error
is a naming problem or a recognition problem.

## The method

The object is cropped out of each frame and judged on its form, blind to which folder named it.

1. `box_list.py` writes every box from the two classes to a list, in three groups. Group A is the 34
   boxes on the 33 contested pictures. Group B is the 17 boxes both folders call Extraneous Polymer.
   Group C is 17 of the boxes both folders call Fiber.
2. `crop_source_bmp.py` runs on the VM. It crops the box plus 35 per cent padding out of the source
   frame and writes the crop as a small bitmap. The VM has no Python imaging library, so it reads
   and writes the 8 bit paletted BMP by hand with the standard library only.
3. `build_sheets.py` builds two sheets. Every crop is fitted into a cell of the same size, so a thin
   filament and a fat lump are shown at a comparable apparent size, which is the property being
   judged. The only label on a sheet is a number, and the cell to group map goes to a separate file.
4. The verdicts are recorded per number before the map is opened. `join_verdicts.py` then joins them
   and prints the counts per group.

## The result

Form verdict per group, 68 objects:

| Group | Thin filament | Thick mass | Unclear | Thin share |
|---|---|---|---|---|
| A, contested: older library says Fiber, newer folder says Extraneous Polymer | 29 | 2 | 3 | 94 per cent |
| B, both folders say Extraneous Polymer | 2 | 14 | 1 | 12 per cent |
| C, both folders say Fiber | 13 | 3 | 1 | 81 per cent |

Three readings follow.

1. The two classes are visually separate when a folder agrees with itself. The agreed Extraneous
   Polymer objects are a thick mass in 14 of 17 cases. The agreed Fiber objects are a thin filament
   in 13 of 17 cases. They are not two words for one thing.
2. The contested 33 read as fibers, not as polymer: 29 of 34 objects are thin filaments. That is
   closer to group C at 81 per cent than to group B at 12 per cent.
3. So the older library's `Fiber` name matches the frames and the newer folder's name is the odd
   one. The right question for the client is whether those pictures were misfiled in the newer
   folder, not which of two vocabularies should win.

The pipeline rule that takes the older library's class for a picture with two classes is therefore
supported here, on the frames, not only on seniority.

## What this does not settle

217 of the 267 pictures the newer folder calls Extraneous Polymer are not in the older library at
all, so no second source has ever checked their name. If the newer folder applies the Extraneous
Polymer name loosely, those 217 are at risk and they are most of the class.

Do not expect the same method to work on them unchanged. The box that made this check clean comes
from `annotations.xml`, and that file covers the older library only: it names the folder
`ICube Defects Library` on all 435 of its images and no updated folder on any of them. So the 217
have no object box anywhere, and there is nothing to crop to. Checking them means judging whole
frames or proposing a region, and the verdict will be weaker than this one. Ask the client whether
object-level annotation exists for the updated folders before spending effort here.

A second, smaller warning sits in group B. One of its objects reads as a ribbed or segmented strand,
and the client's ontology says the ribbed pattern is what distinguishes a HEMA Fragment from
extraneous polymer. The Extraneous Polymer class may hold a few HEMA Fragments. This is a flag, not
a finding, and one object cannot carry it.

## How to re-run

```
python experiments/ep_fiber_check/box_list.py          # writes the box list for the three groups
scp run/ep_fiber_check/20260921/ep_fiber_boxes.csv experiments/ep_fiber_check/crop_source_bmp.py \
    amd-a100-vm:/tmp/
ssh amd-a100-vm 'cd /tmp && python3 /tmp/crop_source_bmp.py > /tmp/epfiber_manifest.csv'
scp -r amd-a100-vm:/tmp/epfiber_crops <local>          # 68 small bitmaps, about 17 MB
python experiments/ep_fiber_check/build_sheets.py      # the two sheets and the cell to group key
# read the sheets, write the verdicts, then:
python experiments/ep_fiber_check/join_verdicts.py
```

The VM work is read only. `amd-a100-vm` needs the Windows ssh-agent service, which holds the key.

## Pitfalls found while doing this

- **A nested dictionary comprehension silently attached the wrong value.** The first version of
  `box_list.py` built the picture hash lookup as a nested comprehension over the folder record. It
  returned the folder name instead of the file hash for all 1,465 older library rows, so every
  contested picture fell through to the control group and the contested group came out empty. The
  count looked plausible, which is what made it dangerous. It is a plain loop now, with a comment.
  Check a lookup against a second, simpler build before trusting a table that came out of it.
- **Fitting the crop into a fixed cell is the right normalisation for reading form, and the wrong
  one for reading size.** Cell fitting made the thick masses and the thin filaments comparable. A
  question about size must use the box numbers in `sheet_key.csv` instead.
- **Do not let this check read unfitted crops at one scale.** The contested boxes are long and
  sprawling (median 407 px wide against 84 px for the rest of the class), so a raw crop shrunk into
  a cell would have made every thick object look thin.
