---
title: run/ep_fiber_check/20260921 - the Fiber against Extraneous Polymer read
date: 2026-09-21
type: result
status: active
where: run/ep_fiber_check/20260921/README.md
---

# The two-name pictures, read on the frames

Answer to the question in `reports/multilabel/MULTILABEL_STRATEGY_20260921.md` section 3.4, and the
measurement that replaced the earlier inference there. Method and caveats:
`experiments/ep_fiber_check/README.md`.

## Result

68 objects judged blind on form. Groups A and B and C are not marked on the sheets.

| Group | Thin filament | Thick mass | Unclear |
|---|---|---|---|
| A, contested 33 pictures, 34 boxes | 29 | 2 | 3 |
| B, both folders say Extraneous Polymer, 17 boxes | 2 | 14 | 1 |
| C, both folders say Fiber, 17 boxes | 13 | 3 | 1 |

The contested pictures read as fibers, and the two classes separate cleanly where the folders agree
with each other. The older library's `Fiber` name is the one that matches the frames.

## Files

| File | What it holds |
|---|---|
| `sheet_1.png`, `sheet_2.png` | the 68 objects, fitted into equal cells, numbered only |
| `sheet_key.csv` | cell number to group, file name and box size. Opened after the verdicts |
| `sheet_verdicts.csv` | the verdict per cell with its group joined on |
| `ep_fiber_boxes.csv` | the 68 boxes sent to the VM, with the group they belong to |
| `source_file_hashes.csv` | one row per crop: source file, hash, byte size, frame size, crop size |

The crops themselves are not kept. They are about 17 MB and `crop_source_bmp.py` rebuilds them.

## Checks run before any verdict

- **Hashes.** Every source picture pulled from the VM was hashed there and compared against
  `run/line_eda/20260916/image_md5_records.csv`: 67 distinct pictures, 0 mismatched. The frames read
  are the frames the pipeline holds.
- **Boxes inside the frame.** 0 of 68 boxes fall outside its picture.
- **Frame geometry as reported by the VM.** 2448 by 2048, 8 bit, for every file. This is the same
  geometry the annotation file records, and it settles the transposed `2048 x 2448` written in the
  2026-09-15 data record.
- **Folder counts, read on the VM.** ICube Defects Library: Fiber 61, Extraneous Polymer 17.
  Updated ICube Objects: Fiber 328, Extraneous Polymer 267. These match the local folder record.
