# Data Ingestion

This folder holds raw defect-library drops from the VM. The pipeline and EDA
read from here. Keep the layout below so the scripts keep working.

## Layout

```
data/
├── annotations.xml        # source-of-truth labels (CVAT). READ-ONLY to code.
└── incoming/
    ├── Bubble/            # one folder per defect class
    ├── HEMA Fragment/
    ├── HEMA Obstruction/
    └── <New Class>/      # add a new folder when you download a new class
```

## Where the VM library comes from

New library drops arrive from the Armor Azure Blob Storage account. The downloader is
`vm/ops/download_armor_blobs.py`. The 2026-09-16 drop (10,614 images, 49.6 GB) is recorded in
`docs/armor_blob_transfer_20260916.md`, with the source folders, the destination on the VM, the
verification and the re-run commands. `data/incoming/` holds the subset that the local pipeline uses.

## How to add a new class

1. On the VM, find the class folder under `iCube Defects Library/`.
2. Copy it into `data/incoming/<Exact Class Name>/`.
   The class name MUST match the `label` in `annotations.xml` exactly
   (e.g. "Bubble", "HEMA Fragment", "Bubble Cluster").
3. Make sure `annotations.xml` (the full VM one) is the current copy in
   `data/annotations.xml`. If the VM library grew, re-download it and
   overwrite this file.
4. Run the pipeline on that class:
   ```
   uv run src/preprocess.py --input data/incoming/<Class> \
       --output run/crops/<Class>_<YYYYMMDD>
   ```
5. Run the before/after EDA:
   ```
   uv run src/eda_before_after.py --class "<Class>" \
       --annot data/annotations.xml \
       --crops run/crops/<Class>_<YYYYMMDD> \
       --out   run/eda/<Class>_<YYYYMMDD> \
       --orig-images data/incoming/<Class>
   ```
6. Two sheets are produced in `run/eda/<Class>_<YYYYMMDD>/`:
   - `eda_full_<Class>.csv`: internal, detailed (offset, remap, invariance checks).
   - `eda_report_<Class>.csv`: client-facing, 10 columns: original metrics
     (n_boxes, image_w, image_h, total_defect_area_px, largest_box_area_px)
     then the same for the cropped image (suffix `_c`). The defect metrics
     should match exactly; image size changes (border removed).

## Verification, and where recorded answers live

- **Identity is content hash, never file name.** Check name against content in BOTH directions and publish the
  pair of counts: content found under a different name (a name-based diff misses these) and names that appear in
  two folders over different content (must be zero, and that zero is what licenses quoting name overlap at all).
  A stakeholder re-checking by filename finds fewer matches than we quote, so give both numbers with the
  mechanism beside them.
- **Every published number comes from a script over the data.** Diff a hand-written figure against the source
  table after editing prose; a transposed number is usually another correct total from the same page, so it
  survives a "does this number appear" check.
- **Re-derive the published numbers on the source machine.** `vm/ops/*.py` holds a checked-in harness that
  re-walks the data on the VM, re-hashes it against `manifest.csv`, rebuilds the derived tables and diffs every
  published figure as PASS/FAIL. Run it before numbers go to the client. It validates the analysis, not just the
  bytes, and it catches prose errors the page cannot see.
- **Recorded answers to client questions live in `docs/`, not in chat.** See
  `docs/clear_tag_analysis_20260916.md` (the Clear tag: numbers, method, verification, superseded numbers and the
  open decision). Each such doc carries a **superseded numbers** table so retired figures are not reused.

## Rules

- Never edit `annotations.xml` by hand. It is the ground truth.
- Each run gets its own dated folder under `run/`. We never overwrite a
  previous run's crops or EDA.
- Images are git-ignored (heavy, from VM). Only code, docs, and the small
  `samples/` set are committed.
- Presentation-tag images (no bbox) are held out from the EDA: only
  object-of-interest classes with boxes are checked.
