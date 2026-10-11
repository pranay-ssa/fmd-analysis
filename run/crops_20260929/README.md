# FMD Crops - Single-Size Fixed Crop Library

Source of truth for everything under `fmd_temp_images/crops/`. Point people here.
Last updated: 2026-09-29. Full run: 11,936 crops, all parity checks OK.

---

## What this folder is

Single-size fixed crops of the FMD inspection BMPs. Every source image in the
three defect folders has exactly one crop here, produced by the production
Fixed-Crop algorithm (same detection and placement as the verified 2026-09-03
pipeline). The crops are derived data: the original defect folders are the
source of truth for the images themselves, and this folder never modifies them.

## Directory structure

```
fmd_temp_images/crops/
├── README.md                        <- this file
├── eda/                             <- size EDA scripts + results
│   ├── eda_size_analysis.py/.json/.md     BMP header dimension scan (all frames 2448x2048)
│   └── eda_usability.py/.json/.md         content-vs-canonical usability EDA
└── single_size/
    ├── manifest_ALL.csv                   combined manifest, all 12,079 crops
    ├── manifest_categorical.csv           per-root combined manifests
    ├── manifest_objects.csv
    ├── manifest_old_library.csv
    ├── Updated ICube Categorical Classes 20260915_crop/   12 class folders, 6,384 crops
    ├── Updated ICube Objects 20260915_crop/                5 class folders, 4,230 crops
    ├── ICube Defects Library_crop/                        22 class folders, 1,465 crops
    └── scripts/
        ├── crop_single_size.py        the crop script (see "How to run")
        ├── build_combined_manifest.py rebuilds the combined CSVs
        └── full_run_log.txt           log of the 2026-09-29 full run
```

Inside each `<root>_crop/` folder there is one folder per class, named
`<Class>_single_crop/`. Example:

```
single_size/Updated ICube Objects 20260915_crop/Fiber_single_crop/
├── 20241101_234032_L24_C13_9988_crop.bmp
├── 20241101_..._crop.bmp
├── ...                              (one crop per source image)
└── manifest.csv                     (one row per source image)
```

## Naming rules

- Crop files keep the source stem and end with `_crop.bmp`:
  `<source_stem>_crop.bmp`. A source image and its crop share the stem, so
  joins are a plain string match.
- Class folders are `<Class>_single_crop/`, where `<Class>` is exactly the
  source folder name (so `Low Dose` and `HEMA` keep their short names from the
  updated roots; the old library keeps its long names). Folder names are never
  mixed across roots.
- `duplicates_single_crop/` (143 crops) is from the smoke test only. The
  `duplicates` folder was deliberately excluded from the full run.

## Counts (verified 2026-09-29, parity: inputs = crops = manifest rows)

| Source root | Classes | Images | Crops |
|---|---|---|---|
| Updated ICube Categorical Classes 20260915 | 12 (duplicates excluded) | 6,384 | 6,384 |
| Updated ICube Objects 20260915 | 5 | 4,230 | 4,230 |
| ICube Defects Library | 22 | 1,465 | 1,465 |
| duplicates (smoke test only) | 1 | 143 | 143 |
| **Total** | | **12,222** | **12,222** |

The old ICube Library numbers reproduce the verified 2026-09-02 production run
exactly (View Obstructed 6 lit / 16 blank, Cavity Off Center 5 blank, Missing
Primary Package 1 expanded), which is the cross-check that this run matches
historical pipeline behavior.

## The manifest - how to map annotations into a crop

### Combined manifests (easiest way to join)

At the top of `single_size/` there are four combined CSVs built from the
per-class manifests:

| file | rows | contents |
|---|---|---|
| `manifest_ALL.csv` | 12,079 | every crop in the library, all roots |
| `manifest_categorical.csv` | 6,384 | Updated ICube Categorical Classes 20260915 |
| `manifest_objects.csv` | 4,230 | Updated ICube Objects 20260915 |
| `manifest_old_library.csv` | 1,465 | ICube Defects Library |

They carry two extra columns on top of the per-class manifest columns:

- `source_root` - `categorical` / `objects` / `old_library`. Always filter or
  group on this: the same class name exists in more than one root (e.g. Fiber
  in `objects` and in `old_library`), and the same image can appear in two
  roots by design (old images repeated in the updated folders get separate
  crops in both).
- `crop_relpath` - path of the crop relative to `single_size/`, ready to use:
  `os.path.join("<crops>/single_size", row.crop_relpath)`.

To rebuild them after any crop run (as amd100-user):

```bash
cd .../crops/single_size/scripts
python3 build_combined_manifest.py
```

The builder ends with its own integrity check (`crops on disk == manifest
rows -> OK`) and exits non-zero on a mismatch. It reads only the per-class
manifests and writes the four CSVs; it never touches crops or sources.

### Per-class manifests

Every class folder also has its own `manifest.csv`, one row per source image:

| column | meaning |
|---|---|
| file | source image file name (crop = same stem + `_crop.bmp`) |
| class | class folder name |
| status | `ok` (canonical window), `expanded` (no-loss guard, see below), `blank` (dark frame, frame-centered window), `error` (none in the current run) |
| recovered_tier | `tier1` (normal detection), `tier2` (dim-content recovery, mean >= 13), empty for blank |
| canonical | the class canonical window, `WxH` |
| width, height | actual crop size in pixels |
| left, top | top-left corner of the crop window inside the original 2448x2048 frame |
| right, bottom | bottom-right corner (inclusive) |
| orig_width, orig_height | source frame size (always 2448x2048 today) |

**Annotation remapping rule:** a bounding box in the original frame maps into
the crop by subtracting the window offset:

```
x_crop = x_original - left
y_crop = y_original - top
```

Nothing else is needed. The crop is a pure translation: pixel values are
unchanged, only the (left, top) window was cut.

## Reading the manifest with care (cautions)

1. **`expanded` rows have a larger crop than canonical.** When the lit content
   plus a 45 px margin does not fit the canonical window, the no-loss guard
   expands that one image to `content + 45 px` so nothing is clipped. For those
   rows `width/height` differ from `canonical`, and `left/top` are still exact.
   Do not assume a fixed size per class; read `width/height` from the manifest.
   96 images across the run are expanded (worst case Missing Lens updated:
   55 of 324).
2. **`blank` rows are frame-centered canonical windows on dark frames.** The
   detection found no lit content meeting the pipeline gates (these are mostly
   View Obstructed and Cavity Off Center frames where the obstruction hides the
   object). The crop is still written, centered on the frame, so the count of
   images stays 1:1. An annotation remap is still valid; whether the defect is
   visible is a data question, not a crop defect.
3. **`tier2` rows were recovered at a lower brightness floor** (mean >= 13
   instead of 15). This is the standing three-tier recovery policy from
   2026-09-02, unchanged.
4. **A warning is not a clip.** `expanded` means the window grew to keep all
   content. No crop in this run lost content: every expanded row contains the
   full content bbox plus the 45 px margin by construction.

## Canonical single-size windows (W x H)

The window sizes embed a 120 px border around the lens content. They are the
2026-09-03 canonical set, revalidated against the updated folders by the
usability EDA on 2026-09-29 (see `crops/eda/eda_usability.md`).

| Class | W x H | Class | W x H |
|---|---|---|---|
| Bubble | 1560x1532 | Lens Off Center | 1580x1560 |
| Bubble Cluster | 1596x1584 | Low Dose Obstructing Region of Interest | 1548x1528 |
| Bubble Irregular | 1556x1524 | Missing Lens | 1544x1524 |
| Bubble On 123 | 1540x1540 | Missing Primary Package | 1520x1516 |
| Bubble On Edge | 1564x1564 | Multiple Lenses | 1592x1592 |
| Bubble Scatter | 1548x1516 | Package Misalignment | 2020x2048 |
| Cavity Off Center | 1704x1564 | View Obstructed | 1496x1296 |
| Dirty Camera | 1876x1716 | Wet Package | 1552x1540 |
| Dirty Strobe | 1572x1788 | Clear (assigned 2026-09-29) | 1680x1644 |
| Extraneous Polymer | 1576x1524 | HEMA (updated root, = HEMA Fragment) | 1544x1520 |
| Fiber | 1560x1528 | duplicates (smoke only) | 1560x1532 |
| Foreign Matter | 1556x1784 | fallback (unknown class) | 1560x1532 |
| HEMA Fragment | 1544x1520 | | |
| HEMA Obstruction | 1584x1532 | | |

Size EDA verdict: all 2026-09-03 sizes remain usable for the updated folders.
Per decision on 2026-09-29: Missing Lens keeps its canonical size and oversized
images expand via the no-loss guard (option a); Clear was assigned
1680x1644 from its observed max content extent (option 2); duplicates were
excluded from the full run (option 3).

## The algorithm (one paragraph)

For each image: load grayscale, mask = pixel > 3 (fixed threshold, never
Otsu), connected components, keep blobs with size >= 500 px AND mean
intensity >= 15 (rejects noise specks and faint streaks), take the union
bounding box of all kept blobs (survives fragmentation), retry that image at
mean >= 13 if nothing passed (tier 2), else declare the frame blank (tier 3).
Place the canonical WxH window centered on the content box, clamped to the
frame; if no content, center on the frame. If the content box plus a 45 px
margin does not fit the window, expand that image to content + 45 px (the
no-loss guard, status `expanded`). Save `<stem>_crop.bmp` and append a
manifest row. Pixel values are never altered: the crop is a pure translation.

## How to run the scripts

All commands run on the A100 box (vm-amd-a100-westus2), as `amd100-user`
(the output folder belongs to that account; `pranayp` can read but not write
there). Python 3 with numpy, pillow, scipy (installed with
`pip3 install --user --break-system-packages numpy pillow scipy`).

```bash
cd /home/amd100-user/FMD_Data_26082026/fmd_temp_images/crops/single_size/scripts

# Smoke test (one class, ~2 s):
python3 crop_single_size.py --classes duplicates

# Full run (all three roots, ~6 min at 16 workers, excludes duplicates):
python3 crop_single_size.py --all

# Optional flags:
#   --classes <name> [<name> ...]   only these class folders
#   --workers N                     parallel workers (default 16)
```

The script ends with a parity check per class: queued images = crop files on
disk = manifest rows. It prints `ALL CLASS COUNTS PARITY OK` and exits 0 only
when every class matches; any mismatch prints `PARITY FAILURE` and exits 1.

Re-running is safe for a class folder: crops are overwritten with identical
output (the algorithm is deterministic; no randomness anywhere), and the
manifest is rewritten in full. A re-run after new images are added to a source
folder will crop the new images too; check the parity line.

The EDA scripts in `crops/eda/` are read-only scans over the source folders
(header-only dimension scan, and the detection pass with no crops written).
Run them the same way: `python3 eda_usability.py --out <path>.json`.

## Safeguards (how this folder is maintained)

1. **Sources are read-only, always.** The script opens source images in read
   mode only; it never writes, moves, renames or deletes anything under
   `Updated ICube ...`, `ICube Defects Library`, or any other source folder.
   Verified: the write test against a source folder fails with permission
   denied, and source counts were re-checked after the full run.
2. **One crop per image, no exceptions.** Duplicates in the data are kept as
   separate files and get separate crops: the number of source images in a
   folder always equals the number of crops in its `_single_crop` folder.
3. **Parity check on every run.** The crop script asserts counts per class at
   the end, and `build_combined_manifest.py` re-asserts
   `crops on disk == combined rows` every time it runs. Never trust a run
   whose log does not end with `ALL CLASS COUNTS PARITY OK` (crop script) or
   `-> OK` (manifest builder).
4. **No crops are ever edited in place by hand.** Regenerate with the script
   instead. Hand-edited crops would silently break the pixel-exact guarantee.
5. **Do not rename class folders.** Downstream joins key on
   `<Class>_single_crop/` and on stems ending in `_crop.bmp`.
6. **New vendor batch = new source folders, new EDA, then crop.** Run the two
   EDA scripts first (they are read-only), compare against the canonical table
   above, and only then crop. If a class shows systematic `expanded` rows well
   above a few percent, raise the question before accepting the run.

## Verification evidence (2026-09-29)

- Smoke test on `duplicates`: 143 in = 143 out; 5/5 random rows pixel-checked,
  crop == exact window of source at the manifest offset (ok, expanded and
  blank statuses all verified bit-exact).
- Full run: 11,936 queued, 337 s at 16 workers, all 39 classes parity OK,
  exit 0. Log: `single_size/scripts/full_run_log.txt`.
- Old-library cross-check: per-class status counts match the verified
  2026-09-02 production run.
- Sources untouched: counts re-checked after the run; write attempts to the
  source tree fail as expected.
