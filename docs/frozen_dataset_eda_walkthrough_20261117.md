---
title: Frozen dataset EDA - what was asked, what the numbers mean, how to read them
date: 2026-11-17
type: method
status: active
where: docs/frozen_dataset_eda_walkthrough_20261117.md
---

# Frozen dataset EDA: the study guide

This is the document to read before you send anything to the lead. It explains the question behind
each number, the exact definition used, why the number is that size, and where it could move. It is
internal. The shorter result doc is `docs/frozen_dataset_eda_20261117.md`; the raw evidence is
`run/frozen_eda_20261117/`; the images now live in the verified store described in section 6.4.

The counts in this guide are the 17 November all-record pass. The current workbook cut, with the
duplicate-pair sensitivity and the size-untagged PASS analysis, is
`docs/frozen_eda_workbook_20261118.md`.

Read order if you have ten minutes: sections 1, 4 and 10. If you have an hour: everything. Section 9 is
the part that changed most after the lead's clarification.

---

## 1. What an EDA is for here

The EDA is a census of the annotation, not a model result. It answers three questions before any
training starts:

1. **How many pictures do we have, and how many of them are new?** This sets the denominator for every
   future result. A model scored on 6,942 pictures and a model scored on 13,682 pictures cannot be
   compared by their raw numbers.
2. **What does each picture carry?** Presentation tags, object boxes, size flags, nothing. This sets
   the label space: which columns exist, which are rare, which co-occur so often that a model cannot
   separate them.
3. **Where is the data inconsistent?** Names that disagree with codes, pictures with no marks, classes
   that appear in one export and not another. These become questions for the lead, not silent fixes.

An EDA number is only meaningful with two things attached: the **unit** (picture, box, or tag) and the
**population** (which pictures were counted). Every number below carries both.

---

## 2. What the lead asked, item by item

Her message, in full:

> Check the overall images covered in the Frozen set. Verify how many are duplicates (i.e., images
> covered by previous annotation). For duplicate images, the Frozen annotation should have the final
> say. If any images not covered in Frozen but present in previous annotation files, we can add them to
> the final frozen set. I will send a mail to Bryce that this is what we are following.
>
> Count of LP presentation tags
> Count of OOI tags images and boxes and size gates
> Count of single-tagged and multi-tagged images.
> Count of single-tagged images, tag-wise
> Count of two-tagged images, tag-wise
> Count of three-tagged images, tag-wise
> Count of clear lens images

That is eight deliverables. One clarification came later and changes the answer to items 6 and 7:
**single means one class in total, whether that class is an LP presentation tag or an OOI object class.**
The tables in section 9 follow that definition.

| # | Her wording | What it means in our data | Answer |
|---|---|---|---|
| 1 | Overall images covered in the Frozen set | Distinct picture names in the 92 annotation files | 13,682 pictures, 13,635 with a mark |
| 2 | How many are duplicates | Frozen pictures that also appear in the previous annotation | 6,771 by name, 6,794 by content |
| 3 | Images in previous but not in Frozen, to add | Previous-annotation pictures whose content is not in the frozen set | 198 by name, 174 genuine after resolving one duplicate |
| 4 | Count of LP presentation tags | Tag statements from the 15 lens-presentation codes | 12,252 instances on 9,252 pictures |
| 5 | OOI tags, images, boxes and size gates | The 8 object classes: pictures, boxes, and the 4 size flags | 10,032 pictures, 119,292 boxes, 4,060 gate tags on 3,742 pictures |
| 6 | Single-tagged and multi-tagged images | Pictures carrying exactly one class, or more than one, LP or OOI | 4,111 single, 9,524 multi, plus 47 with no class |
| 7 | Single / two / three-tagged, tag-wise | Which class, and the LP/OOI composition of each group | Section 9, four tables |
| 8 | Count of clear lens images | Clear-folder pictures with no mark, per the project rule | 42, after 2,291 left Clear for a class bucket |

Status of the add-backs: 147 are held pending client confirmation, and 27 legacy reference pictures are
discarded. The working count stays 13,682. The decision is recorded in
`docs/decisions/2026-11-17-addback-scope.md`.

---

## 3. The data: what arrived and how it is built

### 3.1 The files

99 files in the frozen folder:

| Kind | Count | What it is |
|---|---|---|
| CVAT annotation XML | 92 | The annotation itself, one file per job |
| Client's converted table | 1 | Every shape flattened to a row, with their pass/fail flags |
| Client's model output | 1 | One row per picture: predicted class and confidence |
| Client's per-job counts | 1 | Their own `annotations` and `images` count per class per job |
| Client's totals | 2 | Two summary versions of the same count |
| Client's workbook | 1 | A wide version of the counts |
| Client's notebook | 1 | The code that produced the tables above |

The 92 XML files are 70 jobs numbered 4521940 to 4522009 and 22 jobs numbered 4686372 to 4686393.
Each job holds about 150 pictures; the last job of each run is shorter.

### 3.2 The annotation format

Each XML is a CVAT export:

```
annotations
  meta/job/id, size, created, updated, owner
  image name="FMD_PROD/PRODUCTION-20260925/20241101_105743_L24_C15_9265.bmp" width=2448 height=2048
    tag  label="P2_LD"
    box  label="P2_BB" xtl=.. ytl=.. xbr=.. ybr=.. rotation=..
```

Three things follow from this, and most counting mistakes on this project come from missing one:

- **A tag is a whole-picture statement.** It has no geometry. "Low Dose" is the picture, not a region.
- **A box is one region.** The same picture can hold 126 bubble boxes. Boxes are the object side, and
  they are what a detector trains on.
- **A picture is one `image` element, identified by its file name.** The counts below are pictures
  unless a column says boxes.

### 3.3 Two batches, one export

The frozen set is not one photo campaign. It is two image folders:

| Folder in storage | Pictures in storage | In the export | Capture dates |
|---|---|---|---|
| `PRODUCTION-20260925` | 10,438 | 10,435 | 2024-11 to 2026-09 |
| `PRODUCTION-20261031` | 3,247 | 3,247 | 2026-07 to 2026-10 |
| `PRODUCTION_20261106` | 3,500 | 0 | 2026-08 to 2026-10 |
| `PRODUCTION_20261113` | 4,064 | 0 | 2026-07 to 2026-10 |

Two points matter here.

- **The old batch is the library re-annotated.** Its pictures are the ones we have been working with
  since September. They come from folders such as `Updated ICube Objects 20260915/Foreign Matter` and
  `Updated ICube Objects 20260915/Clear`, and each picture was filed under exactly one defect class.
  The frozen annotation re-annotates them from scratch.
- **The new batch is line output.** `PRODUCTION-20261031` is 3,247 pictures straight from the line,
  filed by date and cavity, with no library class folder. The annotation is the only description those
  pictures have.

The two November folders (`20261106`, `20261113`) are the same kind of line output but were not
annotated in this export. That is the single biggest open scope question.

### 3.4 What "covered" means

A picture is covered if its name appears inside an `<image>` element in the export. Two wrinkles:

- **Name is not identity.** The library saved some pictures under a longer name as well, and the same
  content can appear once under each. We therefore check both name and content hash (section 5).
- **An image element can be empty.** A job that is not finished lists pictures with no tag and no box.
  47 pictures are in that state. They are entries, not annotated pictures, and they are counted
  separately.

### 3.5 Codes and names: one rule

The code in the annotation file is the identity. The readable name is a convenience, and it has changed
between documents. From here on this document uses the Draft 2 names, with the code always available:

| Code | Draft 2 name | Do not use |
|---|---|---|
| P1_NL | No Lens | Missing Lens |
| P1_ML | Multiple Lens | Multiple Lenses, or "ML" |
| P1_PPM | Primary Package Misalignment | Package Misalignment |
| F2_FOV | Field of View Obstructed | View Obstructed |
| P1_MPP | Missing Primary Package | MPP as a name |

Two warnings.

- **Never write "ML" on its own.** In older material it has stood for both Missing Lens and Multiple
  Lens. The code removes the ambiguity, and the code is what the files carry.
- **A name change is not a class change.** Missing Lens became No Lens; the code P1_NL and its 721
  pictures did not move. Any old table that says Missing Lens is the same class.

---

## 4. Counting conventions: the part that decides the numbers

This is the most important section. "How many tags does this picture have" has three legitimate
answers, and the lead's clarification picks one of them.

Take one real picture, `20241101_105743_L24_C15_9265.bmp` from job 4521940. It carries no tag, and 15
boxes: 10 Bubble and 5 Bubble Cluster.

| Reading | What you count | This picture | Where it is used |
|---|---|---|---|
| **Instances** | Every `<tag>` and `<box>` element | 0 tags, 15 boxes | Class inventories (sections 7 and 8) |
| **LP tags only** | Distinct presentation codes | 0 | The earlier LP-only table, kept for comparison |
| **Classes on the picture** | Distinct LP codes plus distinct object classes, size flags folded | 2 (Bubble, Bubble Cluster) | Single, two and three-class (section 9) |

Rules that apply to the third reading:

- **A size flag does not add a class.** The four `_MICRON_THRESHOLD` tags always sit on a picture that
  already has that class box, so folding them changes nothing in the class count. We checked: zero
  gates without their class.
- **Many boxes of one class are one class.** Five Bubble boxes are one OOI class.
- **Clear is reported separately.** Clear is a folder label, not a tag. A Clear picture has no class,
  so it is not counted as single-tagged.
- **Legacy classes keep their row** if they appear. None appear in the frozen export; the 27 add-back
  pictures that carry them are outside the set.

How the three readings differ on this export:

| Reading | 0 | 1 | 2 | 3 | 4 | 5 | 6+ | Total |
|---|---|---|---|---|---|---|---|---|
| LP tags only | 4,383 | 7,237 | 1,244 | 580 | 174 | 17 | 0 | 13,635 |
| Every tag in the file (flags included) | 2,302 | 8,112 | 1,957 | 859 | 333 | 62 | 10 | 13,635 |
| **Classes, LP and OOI together** | **5** | **4,111** | **4,236** | **2,756** | **1,263** | **716** | **553** | **13,640** |

The third row is the operative one. It excludes the 42 Clear pictures, which are added in section 9.
The last column groups 6, 7, 8 and 9 classes: 361 + 155 + 33 + 4 = 553.

The middle row is there only to show why "single-tagged" varies so much between reports. A picture with
one presentation tag and three size flags is single under the first row and four under the second. The
size flags are the difference, and they are size statements, not classes.

---

## 5. How we know the numbers are right

Four independent checks, all reproducible.

**5.1 The export matches storage.** We downloaded all 99 files again from the account and compared
content hashes with the local copies: 99 of 99 identical, 0 differences. The folder we received is the
folder the client holds.

**5.2 Every named picture exists.** For each frozen picture we looked for its name in the storage
folder it claims. Result: 10,435 of 10,435 in the old folder (0 missing), 3,247 of 3,247 in the new one
(0 missing). The old folder holds 10,438 files; the 3 extra are the same picture content saved under a
longer name, not unannotated pictures. We proved that by content hash: each of the 3 matches an
annotated picture under its short name.

**5.3 The counts survive a second method.** A plain text count of `<tag label="...">` and
`<box label="...">` across the 92 files gives exactly the parser's totals, code by code: 16,312 tags
and 119,292 boxes. Two methods, same answer.

**5.4 Our numbers reconcile with the client's own table.** Their per-defect table covers 71 jobs,
including job 4522010, which is not in the export. For the 70 shared jobs, our counts plus their own
4522010 row reproduce their totals exactly for Bubble, Bubble Cluster, Foreign Matter, Fiber,
Extraneous Polymer, HEMA, Field of View Obstructed and all four size gates. Five classes differ by a
handful (Cavity Off Center 1, Folded Lens 10, Multiple Lens 2, Missing Primary Package 1, Dirty Camera
10), which is what a later re-export looks like. If our parser were wrong, this agreement would not
happen.

The verification scripts are `experiments/annotations/verify_frozen_eda.py`, which recomputes 30
headline figures, and `verify_frozen_detail.py`, which recomputes the structure numbers in section 9.

---

## 6. Coverage, duplicates and the store (her items 1 to 3)

### 6.1 The denominator

| Measure | Count |
|---|---|
| Pictures in the frozen export | 13,682 |
| With at least one mark | 13,635 |
| With no mark at all | 47 |
| Old batch (`PRODUCTION-20260925`) | 10,435 |
| New batch (`PRODUCTION-20261031`) | 3,247 |
| Capture year 2024 | 3,671 |
| Capture year 2026 | 10,011 |

The 47 empty pictures break down as 42 Clear-folder pictures and 5 others. The 5 are three `Fail`-named
pictures from 2026 and two from 2024. They look like unfinished rows rather than clean pictures.

Why the two-batch split matters: the old batch is a **re-annotation of a set we already know**, the new
batch is **data we have never had**. Mixing them into one number hides that. Every table below can be
cut by batch.

### 6.2 Duplicates

Her definition is the right one for her purpose: a duplicate is a picture the previous annotation
already covered. We measured it two ways, because file names on this project are not stable.

| Measure | Count | Meaning |
|---|---|---|
| Frozen pictures also named in the previous annotation | 6,771 | Direct name match |
| Same content under a different name | 23 | Name differs, hash matches |
| Distinct pictures already annotated before | 6,794 | 6,771 + 23 |
| Frozen pictures never annotated before (by content) | 6,888 | 13,682 − 6,794 |
| - by name alone | 6,911 | 13,682 − 6,771; the 23 aliases below are counted here |
| - of which new upload | 3,247 | The 2026 line batch |
| - of which old batch, on disk but never annotated | 3,641 | 3,664 by name, less the 23 aliases |

The rule she set is: **for duplicates, the frozen annotation wins.** We checked what that changes:

| Comparison of the two annotations on the 6,771 shared pictures | Count |
|---|---|
| Same label set in both | 3,269 |
| Different label set | 3,502 |

So 3,502 pictures, just over half the old batch, changed label between the previous annotation and the
frozen one. That is the number to quote when someone asks whether earlier results still stand: for
those pictures, the earlier label matrix no longer describes the picture. It does not automatically
invalidate a model that was trained on them, but it does mean any new evaluation must use the frozen
labels, and a like-for-like comparison with an older run has to say which label set it used.

### 6.3 Pictures to add back

Her rule: if a picture is in a previous annotation but not in the frozen set, it can be added.

| Step | Count |
|---|---|
| Previous-annotation pictures not named in the frozen export | 198 |
| - same content already in the frozen set under another name | 23 |
| - genuinely absent | 175 |
| - one picture counted twice, two names, two labels | 1 |
| **Distinct candidates** | **174** |
| - held pending client confirmation | 147 |
| - discarded (legacy reference classes) | 27 |

The 174 by class, with the decision:

| Class | Pictures | Decision |
|---|---|---|
| Bubble | 72 | Pending client |
| Wet Package | 24 | Pending client |
| Bubble Cluster | 21 | Pending client |
| Multiple Lens (`P1_ML`) | 3 | Pending client |
| Fiber | 1 | Pending client |
| Bubble Irregular | 26 | Pending client, folds into Bubble |
| Bubble On Edge | 14 | Discarded |
| Bubble On 123 | 13 | Discarded |
| **Total** | **174** | |

Three points to understand:

- **The 175 became 174 because one picture carried two labels.** `20241114_001422_L25_C5_9744.bmp` is
  Multiple Lens in the 22 September file and Wet Package in the older file. The priority rule gives the
  newer file the label, so Multiple Lens stands and the Wet Package row is dropped. That is also why Wet
  Package is 24 and not 25.
- **The 27 discarded pictures are legacy reference classes.** They have no class in the current guide,
  no experiment uses them, and no fold rule covers them. They stay out.
- **Bubble Irregular is not an open question.** The existing rule folds it into Bubble. It is grouped
  with the 147 only because those 147 as a whole are waiting on the client, not because the mapping is
  unclear.

Every candidate is single-label, and every source file exists on disk. The list, with hashes and the
decision column, is `run/frozen_eda_20261117/store/addback_candidates.csv` and is copied into the store.

### 6.4 Where the pictures now live

The annotation images are consolidated in one verified store on the VM:

`/data/FMD_Data_26082026/frozen_data_20261117/`

| Item | Count |
|---|---|
| `images/` | 13,682 files, original names, 64 GB |
| `annotations/xml/` | 92 files |
| `annotations/client_supplied/` | 7 files |
| `manifest.csv` | 13,682 rows, one per picture |
| `labels/tags.csv` | 16,306 rows |
| `labels/boxes.csv` | 119,292 rows |
| `checksums/` | sha256 of every image and of the manifest |

Every image was checked against its manifest md5 after copying: 13,682 of 13,682, 0 missing, 0 extra.
The old folders are kept for now because earlier scripts still read those paths; they are deleted only
after training reads the store and one full run passes from it. The 147 held add-backs are not in that
duplicate set, so they remain available if approved.

---

## 7. LP presentation tags (her item 4)

An LP tag is a whole-picture statement from the lens-presentation family. There are 15 codes in the
guide and **all 15 now carry pictures**, which is new: three of them had none until this export.

| Code | Class | Tag instances | Pictures |
|---|---|---|---|
| P2_LD | Low Dose | 2,124 | 2,124 |
| P2_DC | Dirty Camera | 1,992 | 1,992 |
| P2_LOC | Lens Off Center | 1,571 | 1,570 |
| P1_ML | Multiple Lens | 1,514 | 1,511 |
| P1_MPP | Missing Primary Package | 1,427 | 1,427 |
| P1_PPM | Primary Package Misalignment | 1,055 | 1,055 |
| P1_COC | Cavity Off Center | 817 | 816 |
| P1_NL | No Lens | 721 | 721 |
| P1_FL | Folded Lens | 586 | 586 |
| F2_FOV | Field of View Obstructed | 223 | 222 |
| P1_TL | Torn Lens | 117 | 117 |
| P1_LR | Lens Rupture | 36 | 36 |
| P2_DS | Dirty Strobe | 33 | 33 |
| P1_EBC | Edge Bottle-Capped | 24 | 24 |
| P2_BSC | Bubble Scatter | 12 | 12 |
| **Total** | | **12,252** | **9,252** |

How to read it:

- **Instances against pictures.** Where the two differ, one picture carries the same tag twice. Four
  pictures do this: one carries Multiple Lens twice and Lens Off Center twice, one carries Multiple Lens
  three times, one carries Field of View Obstructed twice, and one carries Cavity Off Center twice. The
  distinct statement count is 12,246. This is an annotation artefact, not a class of picture.
- **The distribution is top-heavy.** Low Dose and Dirty Camera alone are 4,116 of the 12,252 instances.
  Torn Lens, Lens Rupture, Dirty Strobe, Edge Bottle-Capped and Bubble Scatter together are 222, under
  2%. Any per-class metric on those five will be noisy, and the earlier F1 warning about Bubble Scatter
  (one test picture) still applies.
- **Folded Lens is not independent.** 571 of its 586 pictures also carry Multiple Lens. That is the
  guide's own co-tag rule, and it is why Folded Lens recall has been hard to move: a picture with both
  can be right for Multiple Lens and wrong for Folded Lens at the same time.

### The most common LP pairs

| Pair | Pictures |
|---|---|
| Multiple Lens + Lens Off Center | 1,220 |
| Folded Lens + Multiple Lens | 571 |
| Folded Lens + Lens Off Center | 459 |
| Multiple Lens + Dirty Camera | 384 |
| Dirty Camera + Lens Off Center | 384 |
| Dirty Camera + Low Dose | 268 |
| Folded Lens + Dirty Camera | 156 |
| Multiple Lens + Torn Lens | 99 |
| No Lens + Dirty Camera | 95 |
| Primary Package Misalignment + Dirty Camera | 90 |
| Torn Lens + Lens Off Center | 74 |

The first pair is worth remembering: 1,220 pictures carry both, 78% of all Lens Off Center pictures. But
section 9 shows something more important: not one of those 1,220 is a two-class picture. Every one also
carries bubbles. The lens pair never stands alone.

---

## 8. OOI boxes and size gates (her item 5)

Her sentence asks for three different things, so here are three tables.

### 8.1 Pictures and boxes per class

| Code | Class | Pictures with a box | Boxes | Boxes per picture (mean / median / max) |
|---|---|---|---|---|
| P2_BB | Bubble | 9,775 | 92,223 | 9.4 / 7 / 126 |
| P2_BC | Bubble Cluster | 4,991 | 14,700 | 3.0 / 2 / 38 |
| P3_FM | Foreign Matter | 2,367 | 4,813 | 2.0 / 1 / 147 |
| P3_FIB | Fiber | 1,396 | 2,830 | 2.0 / 1 / 35 |
| P3_EP | Extraneous Polymer | 1,018 | 1,084 | 1.1 / 1 / 5 |
| P2_WP | Wet Package | 813 | 3,159 | 3.9 / 2 / 91 |
| P3_HE | HEMA | 340 | 351 | 1.0 / 1 / 4 |
| P1_SG | Surface Groove | 88 | 132 | 1.5 / 1 / 5 |
| **Total** | | **10,032** | **119,292** | |

Four things this tells you:

- **Bubbles dominate the box count.** 92,223 of 119,292 boxes are Bubble, 77%. A detector's loss is
  mostly a bubble loss whether you want it or not.
- **A picture can carry 147 Foreign Matter boxes.** The median is 1. This is the long tail that makes
  per-object metrics unstable and per-picture metrics the safer read.
- **The classes are not separable by presence.** Bubble Cluster appears on 4,991 pictures, and virtually
  all of them also carry Bubble. Counting "pictures with Cluster" is fine; treating the two as
  independent classes is not.
- **Surface Groove exists now.** 88 pictures, 132 boxes. It was at zero in every previous export, and
  the project rule says a zero class must still be listed. It no longer needs that note.

### 8.2 Size gates

The four `_MICRON_THRESHOLD` tags are not classes. Each one is a single whole-picture statement: *at
least one box of this class is larger than the micron cut*. The tag does not say which box crossed.

| Class | Pictures with the class | Pictures with the gate | Share flagged | Pictures below the cut |
|---|---|---|---|---|
| Foreign Matter | 2,367 | 1,400 | 59.1% | 967 |
| Fiber | 1,396 | 1,306 | 93.6% | 90 |
| Extraneous Polymer | 1,018 | 1,014 | 99.6% | 4 |
| HEMA | 340 | 340 | 100% | 0 |
| **Row sum** | **5,121** | **4,060** | | **1,061** |

- **The total row is a sum of the four class rows.** A picture can carry two gated classes, so it is
  not a distinct-picture count; the per-class rows are the ones to quote.
- **No gate sits on a picture without its class.** We checked: 0 in all four. So a gate is always a
  subset of its class, never a stray label.
- **HEMA and Extraneous Polymer carry no useful size split.** Every HEMA picture is flagged; almost
  every EP picture is. A size experiment on those two has no negative group, which is why the previous
  size work reported HEMA as not measurable.
- **Foreign Matter is the only class with a meaningful below-cut group**: 967 pictures, 41% of its
  pictures. That is where a size decision can actually be tested.
- **What the cut is, in pixels.** The boundary sits at about 19.5 pixels on the longer side, which is
  about 299 microns at the client's 15.34 microns per pixel, or about 353 microns at 18.1. Quote the
  pixel boundary and both scales. A bare "300 micron" hides a real disagreement about scale.

A worked example: `20241101_160136_L27_C11_9030_0.6928.bmp` carries `P2_DC` and
`P3_FM_MICRON_THRESHOLD`, with one Foreign Matter box 23.2 pixels on its longer side. At 15.34 microns
per pixel that is 356 microns, above the cut, so the flag is consistent. A second picture with a 41.2
pixel box, 632 microns, is also flagged. Below 19.5 pixels, no flag.

---

## 9. Single, two and three classes (her items 6 to 8)

### 9.1 What kind of picture each one is

| Kind of picture | Pictures | What it means |
|---|---|---|
| LP tag only, no box | 3,603 | A presentation answer and nothing marked |
| OOI box only, no tag | 4,383 | Objects marked, no presentation statement |
| Both | 5,649 | The common case |
| Clear, no mark | 42 | Clear-folder picture with nothing marked |
| No mark, not Clear | 5 | Placeholder rows, not usable |
| **Total** | **13,682** | |

The overlap is the headline: 41% of marked pictures carry both a presentation tag and at least one box.
A model that only reads tags ignores 4,383 pictures' worth of object information, and a detector that
only reads boxes ignores 3,603 presentation-only pictures.

### 9.2 Classes per picture

Distinct classes, LP and OOI together, size flags folded. The 42 Clear pictures and the 5 empty rows are
excluded, so the population is 13,640.

| Classes on the picture | Pictures | Share |
|---|---|---|
| 0 | 5 | 0.04% |
| 1 | 4,111 | 30.1% |
| 2 | 4,236 | 31.0% |
| 3 | 2,756 | 20.2% |
| 4 | 1,263 | 9.3% |
| 5 | 716 | 5.2% |
| 6 | 361 | 2.6% |
| 7 | 155 | 1.1% |
| 8 | 33 | 0.2% |
| 9 | 4 | 0.03% |
| **Total** | **13,640** | |

So: **4,111 single, 9,524 multi**, and 47 pictures with no class at all (42 Clear, 5 empty). The 9,524
split as 4,236 with two classes, 2,756 with three, and 2,532 with four or more.

### 9.3 Single-tagged pictures, and what they are

| Kind | Pictures |
|---|---|
| One LP tag | 3,439 |
| One OOI class | 672 |
| **Total single** | **4,111** |

The 672 OOI-only pictures are mostly bubble pictures: 576 carry Bubble alone. The rest are single-object
pictures of Foreign Matter (39), Fiber (32), Bubble Cluster (10), Extraneous Polymer (9), Wet Package
(3) and HEMA (3).

Tag-wise, for all 4,111 single-class pictures:

| Code | Class | Kind | Pictures |
|---|---|---|---|
| P1_MPP | Missing Primary Package | LP | 1,376 |
| P1_PPM | Primary Package Misalignment | LP | 958 |
| P1_COC | Cavity Off Center | LP | 805 |
| P2_BB | Bubble | OOI | 576 |
| F2_FOV | Field of View Obstructed | LP | 221 |
| P1_NL | No Lens | LP | 45 |
| P3_FM | Foreign Matter | OOI | 39 |
| P3_FIB | Fiber | OOI | 32 |
| P2_LD | Low Dose | LP | 29 |
| P2_BC | Bubble Cluster | OOI | 10 |
| P3_EP | Extraneous Polymer | OOI | 9 |
| P2_WP | Wet Package | OOI | 3 |
| P2_LOC | Lens Off Center | LP | 3 |
| P3_HE | HEMA | OOI | 3 |
| P2_DC | Dirty Camera | LP | 2 |
| **Total** | | | **4,111** |

What changed from the LP-only table is the point of this section. Low Dose was 1,778 single-tag pictures
under the LP-only reading and is 29 here, because almost every Low Dose picture also carries bubbles.
The same is true of No Lens (625 to 45) and Dirty Camera (1,030 to 2). Single-class pictures are
genuinely simple pictures: mostly cavity and package conditions, or a picture with bubbles and nothing
else.

### 9.4 Two-class pictures: composition

4,236 pictures carry exactly two classes.

| Composition | Pictures |
|---|---|
| OOI + OOI | 2,565 |
| LP + OOI | 1,507 |
| LP + LP | 164 |
| **Total** | **4,236** |

The most common exact pairs:

| Pair | Composition | Pictures |
|---|---|---|
| Bubble + Bubble Cluster | OOI + OOI | 1,212 |
| Bubble + Low Dose | OOI + LP | 848 |
| Bubble + Foreign Matter | OOI + OOI | 677 |
| No Lens + Bubble | LP + OOI | 283 |
| Bubble + Fiber | OOI + OOI | 272 |
| Bubble + Extraneous Polymer | OOI + OOI | 246 |
| Bubble + Dirty Camera | OOI + LP | 190 |
| Primary Package Misalignment + Dirty Camera | LP + LP | 88 |
| Bubble + HEMA | OOI + OOI | 87 |
| Bubble + Lens Off Center | OOI + LP | 68 |
| Bubble + Wet Package | OOI + OOI | 59 |

Two observations:

- **A bubble is in almost every two-class picture.** Every pair in the top ten except one contains
  Bubble. The two-class population is not a lens-defect population; it is a bubble population with one
  other thing attached.
- **LP + LP is rare.** 164 pictures, and 88 of them are Primary Package Misalignment plus Dirty Camera.
  Only 11 pairs of two presentation tags exist at all, and the largest is 88.

### 9.5 Three-class pictures: composition

2,756 pictures carry exactly three classes.

| Composition | Pictures |
|---|---|
| 1 LP + 2 OOI | 1,529 |
| 3 OOI | 1,019 |
| 2 LP + 1 OOI | 208 |
| 3 LP | 0 |
| **Total** | **2,756** |

The most common exact triples:

| Triple | Pictures |
|---|---|
| Bubble + Bubble Cluster + Low Dose | 572 |
| Bubble + Bubble Cluster + Foreign Matter | 388 |
| Bubble + Bubble Cluster + Extraneous Polymer | 223 |
| Bubble + Bubble Cluster + Dirty Camera | 205 |
| Bubble + Bubble Cluster + Fiber | 166 |
| Bubble + Bubble Cluster + Lens Off Center | 104 |
| Bubble + Dirty Camera + Extraneous Polymer | 101 |
| Bubble + Dirty Camera + Foreign Matter | 80 |
| Bubble + Bubble Cluster + HEMA | 77 |

There is no three-LP picture at all. The busiest triples are Bubble plus Bubble Cluster plus one more
class, which again says the object side drives the multi-class population.

### 9.6 What co-occurs most

Across every picture with two or more classes, 152 distinct class pairs appear. The top fifteen:

| Pair | Composition | Pictures |
|---|---|---|
| Bubble + Bubble Cluster | OOI + OOI | 4,943 |
| Bubble + Foreign Matter | OOI + OOI | 2,278 |
| Bubble + Low Dose | OOI + LP | 2,073 |
| Bubble + Dirty Camera | OOI + LP | 1,786 |
| Bubble + Lens Off Center | OOI + LP | 1,555 |
| Multiple Lens + Bubble | LP + OOI | 1,505 |
| Bubble + Fiber | OOI + OOI | 1,300 |
| Multiple Lens + Lens Off Center | LP + LP | 1,220 |
| Bubble Cluster + Foreign Matter | OOI + OOI | 1,078 |
| Bubble Cluster + Dirty Camera | OOI + LP | 1,028 |
| Multiple Lens + Bubble Cluster | LP + OOI | 1,006 |
| Bubble + Extraneous Polymer | OOI + OOI | 993 |
| Bubble Cluster + Lens Off Center | OOI + LP | 989 |
| Bubble Cluster + Low Dose | OOI + LP | 914 |
| Bubble + Wet Package | OOI + OOI | 750 |

The important row is Multiple Lens + Lens Off Center at 1,220. It has no two-class pictures at all: every
one of those 1,220 sits on a picture that also has bubbles, so it is a three-class or larger
combination. A model that learns "off centre" from this data is learning it in the presence of bubbles,
never alone.

### 9.7 Clear lens pictures

"Clear" is not a code in the annotation. It is a folder label, and the project rule is:

> Clear is a picture whose winning library path is the Clear folder and which carries no mark. A
> picture with no mark that is not from the Clear folder is an unfinished row, not Clear.

That rule reproduces the previous record exactly: 2,333 Clear-folder pictures, 2,117 with no marks at
that time.

On the frozen annotation:

| State of the 2,333 Clear-folder pictures | Pictures |
|---|---|
| No mark at all, still Clear | **42** |
| Bubble or Bubble Cluster boxes only | 1,712 |
| Another object box only (Foreign Matter, Wet Package, Fiber) | 255 |
| A presentation tag, often with boxes | 324 |
| **Total** | **2,333** |

So the folder did not lose its pictures. **2,291 moved into a class bucket** and 42 stayed Clear. That is
the right way to say it: not "Clear collapsed", but "the re-annotation gave 2,291 of those pictures a
class".

Three consequences:

- **The pass population did not disappear, it changed shape.** 1,798 pictures carry nothing but Bubble
  or Bubble Cluster boxes. The pass rule already says "Clear or bubble only", so most of the former
  Clear set is still a pass set under a different name.
- **579 Clear-folder pictures carry something other than bubbles**: 255 an object box (Foreign Matter,
  Wet Package or Fiber), 324 a presentation tag. Under the pass rule the presentation tags fail, and the
  object boxes fail unless they sit below the size cut. These are the ones worth a spot check with the
  client.
- **Clear cannot be computed for the new batch at all.** Clear is a folder in the old library; the
  3,247 new pictures have no library folder. If clear pictures matter for the new batch, the annotation
  needs a Clear code or a folder convention.

---

## 10. The one-page story

If you have to explain this in two minutes:

> The frozen export is complete and matches the client's storage exactly. It covers 13,682 pictures:
> 10,435 from the batch we already knew, re-annotated, and 3,247 new line pictures. Of the old batch,
> 6,771 pictures were annotated before and the frozen labels replace them; 3,502 of those changed label.
> All 23 guide classes now have data. The counts are 12,252 presentation tags on 9,252 pictures, 119,292
> object boxes on 10,032 pictures, and 4,060 size flags on 3,742 pictures.
>
> On the lead's definition, a class is either an LP tag or an OOI object class. That gives 4,111 pictures
> with exactly one class, 4,236 with two, 2,756 with three and 2,532 with four or more. The multi-class
> population is driven by bubbles: every common pair except one contains Bubble, and there is no
> three-LP picture at all. The lens pair Multiple Lens plus Lens Off Center appears on 1,220 pictures,
> but never on a picture without bubbles.
>
> Clear is a folder label. 2,291 of its 2,333 pictures received a class in the re-annotation, so 42
> remain Clear. That is a re-labelling, not a loss.
>
> Three questions are open: two further uploads in storage, 7,564 pictures, carry no annotation; one job
> in the client's own table is missing from the export; and 147 add-back pictures wait on client
> confirmation. The 27 legacy reference pictures are discarded.

The sentence that will surprise her is about Clear. Say it with the reason in the same breath: 2,291 of
the folder's pictures were given a class, so 42 remain Clear.

---

## 11. The traps in this dataset

Each one is real, each one changes a number if missed.

1. **Name is not content.** 23 frozen pictures are the same picture as a previous-annotation entry under
   another name. Counting names would report 23 false "missing" pictures. Always join on hash when the
   question is coverage.
2. **Five name forms.** A picture can be `..._9265.bmp`, `..._9265_0.5637.bmp`, or
   `..._Score(0.98)_0.43_0.93.bmp`. The library folder records add trailing score fields the file on
   disk does not carry. Strip the extension before matching, and prefer the hash.
3. **Tag is not box.** Bubble is a box, Low Dose is a tag. A picture can carry 126 bubble boxes; that is
   one class and one class count.
4. **Gate is not a class.** The four size flags are a subset of their class. Counting them beside the
   class double counts; counting them as their own class creates a phantom fifth class.
5. **Gate is one per picture.** It marks that at least one box crossed, not which one. A picture with
   one large and five small Foreign Matter boxes has one flag, and the flag cannot train a per-object
   size head.
6. **No flag can mean two things.** On production pictures, no flag means below the cut. On the
   September project files, no flag means the picture was never assessed. Say which reading applies.
7. **Empty image is not Clear.** 47 pictures have no mark. Only 42 are Clear-folder pictures; 5 are
   unfinished rows.
8. **Clear is a folder, not a zero.** The same picture can be Clear in the library and marked in the new
   annotation. Clear is the folder plus no marks, never "no boxes in this file".
9. **Legacy classes vanish silently.** HEMA Obstruction (36 pictures) was a tag in the previous record;
   in the frozen export all 36 are HEMA boxes. Bubble On 123 (13) and Bubble On Edge (14) are not in the
   export at all, and are discarded from the add-backs.
10. **Duplicate tags exist.** 4 pictures carry the same tag twice. Instance counts include them;
    picture counts must not.
11. **The client's own totals cover 71 jobs, not 70.** Job 4522010 is in their per-defect table and not
    in the export. Their totals therefore cannot be compared with ours without removing that row, or
    adding it to ours.
12. **Folder naming is inconsistent.** `PRODUCTION-20260925` and `PRODUCTION-20261031` use a hyphen;
    `PRODUCTION_20261106` and `PRODUCTION_20261113` use an underscore. Do not read that as a different
    kind of batch without evidence.
13. **"ML" is not a name.** It has meant both Missing Lens and Multiple Lens. Use `P1_NL` and `P1_ML`,
    and use the Draft 2 names, No Lens and Multiple Lens.
14. **"Single-tagged" has three meanings.** LP-only, every tag in the file, and one class across LP and
    OOI give 7,237, 8,112 and 4,111. State which one is meant, as the lead did.
15. **A two-class lens pair does not exist.** Multiple Lens plus Lens Off Center is 1,220 pictures
    overall and 0 at exactly two classes, because bubbles are always present. Quoting the 1,220 as if
    it were a two-tag group is wrong.

---

## 12. What moves the numbers, and by how much

| Item | Effect |
|---|---|
| The two November uploads are in scope | +7,564 pictures, whole EDA recomputed |
| Job 4522010 belongs to the export | +1 job, about 150 pictures and 1,299 shapes |
| The 147 held add-backs are approved | 13,829 pictures |
| The 147 are refused | 13,682 stays |
| The 27 reference pictures (discarded) | no change; they stay out |
| The 47 empty pictures are annotated | picture count unchanged, marks increase |
| Clear were read as "no presentation tag" | 4,383 instead of 42; not the project rule |

The two that can move most are the November uploads (+7,564, more than half the current set) and the
scope of the two batches. Neither is a detail.

---

## 13. What is not done, and what it means

- **No label mapping for the four newly populated classes.** Edge Bottle-Capped, Torn Lens, Lens
  Rupture and Surface Groove have pictures but no row in our crosswalk. Until they are mapped they
  cannot enter a matrix, and their pictures would silently drop out of a split.
- **No picture-level matrix, no split.** The existing frozen split v8 is built on the previous
  annotation and is stale for 3,502 pictures. Do not reuse it for a frozen-dataset result.
- **No content deduplication inside the new batch.** The 3,247 new pictures have not been hashed against
  the old batch. Names do not collide, but names are not identity (trap 1). Four duplicate pairs were
  found inside the frozen set itself and are flagged in the manifest.
- **No pass/fail measurement on the frozen set.** Not asked for. The pieces are here (Clear 42,
  bubble-only 1,798, gates 4,060), but a pass/fail number has to be computed through the block.
- **The add-back decision is half closed.** 27 are discarded, 147 wait on client confirmation. The store
  and every number above describe 13,682 until that closes.

---

## 14. Appendix: where each number lives

| Table | File |
|---|---|
| File inventory, per-file stats | `run/frozen_eda_20261117/frozen_files.csv`, `inventory.json` |
| Coverage, duplicates, add-backs | `run/frozen_eda_20261117/coverage.json`, `duplicates_vs_previous.csv`, `pictures_previous_only.csv`, `previous_only_by_content.csv` |
| LP tags | `run/frozen_eda_20261117/lp_tags.csv` |
| OOI classes and boxes | `run/frozen_eda_20261117/ooi_classes.csv` |
| Size gates | `run/frozen_eda_20261117/size_gates.csv` |
| Classes per picture, composition | `run/frozen_eda_20261117/detail/composition_summary.json` |
| Single by class | `run/frozen_eda_20261117/detail/single_by_class.csv` |
| Two-class compositions and pairs | `run/frozen_eda_20261117/detail/two_compositions.csv`, `two_pairs.csv` |
| Three-class compositions and triples | `run/frozen_eda_20261117/detail/three_compositions.csv`, `three_triples.csv` |
| All class pairs | `run/frozen_eda_20261117/detail/pairs_all.csv` |
| LP-only tables, kept for comparison | `run/frozen_eda_20261117/{single,two,three}_tagged.csv` |
| Clear | `run/frozen_eda_20261117/detail/clear_pictures.csv` |
| Boxes per picture, per class | `run/frozen_eda_20261117/detail/boxes_per_picture.csv` |
| Gate coverage | `run/frozen_eda_20261117/detail/gate_coverage.csv` |
| Per-job counts | `run/frozen_eda_20261117/detail/per_job_detail.csv`, `per_job.csv` |
| Legacy class mapping | `run/frozen_eda_20261117/detail/legacy_pictures.csv` |
| Duplicate tags | `run/frozen_eda_20261117/detail/duplicate_tags.csv` |
| Add-back candidates and decisions | `run/frozen_eda_20261117/store/addback_candidates.csv`, `addback_dropped.csv` |
| Store manifest and checksums | VM store `manifest.csv`, `checksums/images.sha256` |

Scripts: `experiments/annotations/frozen_inventory.py`, `frozen_coverage.py`,
`frozen_by_content.py`, `frozen_eda.py`, `frozen_eda_detail.py`, `frozen_eda_by_composition.py`,
`build_blob_check.py`, `verify_frozen_eda.py`, `verify_frozen_detail.py`.
