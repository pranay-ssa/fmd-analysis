---
title: experiments/annotations/ - reading a CVAT annotation export
date: 2026-09-23
type: protocol
status: active
where: experiments/annotations/README.md
---

# Annotation exports (the CVAT XMLs in `data/`)

Two annotation exports live in `data/`. They are the label source for every detection
number and every classifier class folder we hold, so treat a new one as a data drop, not
as a file: read it, count it, and write down what it does and does not cover before
anything trains on it.

| File | Project | Images | Boxes | Tags | Labels |
|---|---|---|---|---|---|
| `data/annotations.xml` | id 2, "Sweta Annotations Defect Library" | 435 | 2,020 | 0 | 10 |
| `data/Updated Annotations 20260922.xml` | id 3, "ICube Data 20260915" | 6,097 | 183 | 4,930 | 22 |

The two files are **different projects**, not two revisions of one project: they share no
label name and no task name, and their label sets differ (see
`docs/annotations_update_20260923.md`).

## What is here

- `audit_updated_annotations.py` - reads both XMLs, writes the audit tables to
  `run/annotations_audit_20260923/`, and checks its own numbers against the `EXPECTED`
  table at the top of the file. Exits non-zero on a failed check.
- `verify_annotation_audit.py` - re-derives every published figure through a second code
  path and diffs it against a hand-typed `EXPECTED` table plus `summary.json`. Run this
  after any change to either XML or to the builder.

```bash
./.venv/Scripts/python.exe experiments/annotations/audit_updated_annotations.py
./.venv/Scripts/python.exe experiments/annotations/verify_annotation_audit.py
```

Outputs in `run/annotations_audit_20260923/`:

| File | What it holds |
|---|---|
| `summary.json` | every headline figure, the source SHA-256, and the check list |
| `tasks.csv` | one row per CVAT task: size, images in the export, jobs, coverage of the class its folder is named for |
| `jobs.csv` | one row per CVAT job (segment): frames, images, how many carry a tag or a box |
| `labels.csv` | one row per label code: class name, ontology wording, kind, instances, pictures, folders |
| `folder_x_tags.csv`, `folder_x_boxes.csv` | folder against label cross tabs |
| `drop_coverage.csv` | every subfolder of the 2026-09-16 blob drop against its image count in this export |
| `shared_with_older_library.csv` | the pictures both XMLs annotate, with both files' labels |
| `reannotation_iou.csv` | one row per matched box pair across the two files: label, IoU, identical-geometry flag |
| `tag_pairs.csv` | label co-occurrence counts |

## The reverse EDA, coverage of the whole drop

The audit above counts what the file holds. The reverse EDA asks the opposite question: of
every picture in the September drop, which ones carry no annotation at all, and are those
the ones the older library already covers. It joins three records on picture content:

| Record | Path |
|---|---|
| image inventory with content hashes | `run/line_eda/20260916/image_md5_records.csv` |
| the new export | `data/Updated Annotations 20260922.xml` |
| the older library export | `data/annotations.xml` |
| the client EDA of 2026-09-17, cross-checked against | `run/client_eda/20260917/` |

```bash
./.venv/Scripts/python.exe experiments/annotations/reverse_eda_annotation_coverage.py
./.venv/Scripts/python.exe experiments/annotations/verify_reverse_eda.py
```

Outputs in `run/annotations_reverse_eda_20260923/`:

| File | What it holds |
|---|---|
| `summary.json` | every headline figure and the check list |
| `picture_coverage.csv` | one row per distinct picture: where it sits, what each file says about it |
| `folder_x_coverage.csv` | one row per drop class folder: pictures, new annotation, older-file only, nothing |
| `gap_by_folder.csv` | the pictures with nothing anywhere, one row per folder, each picture counted once |
| `library_coverage.csv` | one row per older library class: files, pictures, and how the drop covers them |
| `library_pictures_in_drop.csv` | older library class against the drop folder its pictures sit in |
| `duplication_axis.csv` | pictures with a copy in the older library against pictures without |
| `library_same_picture_different_name.csv` | the 38 library files whose drop copy carries a score suffix |
| `verification.json` | the 93 independent checks |

Findings and the questions they raise are in `docs/reverse_eda_annotation_coverage_20260923.md`.

## How the label codes were read

The new project labels everything with a code (`P1_MPP`, `P2_BB`, `P3_EP`) and the code
legend is not in the repository. The mapping in `audit_updated_annotations.py` is derived,
and the derivation is recorded in `docs/annotations_update_20260923.md` section 2:

- 11 codes are pinned by a CVAT task name that sits on a blob folder of that name;
- the acronyms pin the rest (`P3_FIB` Fiber, `P3_FM` Foreign Matter, `P2_BB` Bubble, ...);
- `P2_BST` is pinned by elimination: it is the only unassigned box code and Stretched
  Bubble is the only unassigned ontology box name that matches.

Two ontology box names have no code at all in this project: **Bubble On Edge** and
**Bubble Over 123 Mark**. That is a finding, not a gap in the derivation. Confirm the
legend with the client before a dataset is built from this file.

## Pitfalls

- **`iterparse` start events expose a partially built element.** Reading an `<image>`'s
  children at its start event on the 2026-09-22 file silently counts 4,910 of the 4,930
  tags. Read children at the **end** event (the builder uses `ElementTree.parse`, the
  verifier uses `iterparse` with `events=("end",)`).
- **A task name is not the label it applies.** Tasks `P1_DC` and `P1_DS` apply the labels
  `P2_DC` and `P2_DS`. Measure a task's coverage against the class its blob folder is
  named for (`FOLDER_TO_CODE`), never against the task's own name.
- **A CVAT task `size` is the frame count, not the image count.** A task whose image was
  deleted after the task was created keeps its frame span and reports fewer images in the
  export (tasks 15, 19, 20, 23 and 27 here). Compare `size` with the images present
  before treating a folder as fully covered.
- **An unannotated image inside a task is not evidence that a class is rare.** Check where
  the tag sits inside the task's jobs: a contiguous block of empty jobs is an unfinished
  task, and a class tag applied to almost every image of one job is the folder name being
  copied, not a judgement (section 4 of the doc).
- **`<labels>` is not under `<meta>`.** It sits inside `<project>`, after `<tasks>`, so
  `meta.find("labels")` returns `None` and the label list silently reads as empty. Read
  `root.find("meta").find("project").find("labels")`.
- **Join the files to the images on content, never on file name.** A picture that sits in
  two folders can carry two names: the drop copy of a library picture often has a score
  suffix appended (`..._9354.bmp` in the library, `..._9354_0.9821_0.5907.bmp` in the
  Updated folder). 38 of the older library's 1,465 files are the same picture as a drop
  file under a different name, and a name join misses every one of them.
- **An image element in the export is not an annotation.** The 2026-09-22 file carries
  6,097 image elements of which 2,021 hold nothing, so images and annotated pictures are
  two different numbers (6,097 against 4,076). Count the tags and boxes before calling a
  picture annotated.
- **A task `size` above the images present means frames are absent from the export.** The
  older library file names 462 frames across its ten tasks and carries 435 image elements
  (Wet Package short 23). Treat its own coverage as a floor, not a ceiling.
