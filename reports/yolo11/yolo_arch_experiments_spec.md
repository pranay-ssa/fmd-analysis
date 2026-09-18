# YOLO Architecture Experiments on OoI Tags — Spec

**Created:** 2026-09-07T09:49:21+05:30
**Last updated:** 2026-09-11 (Entry 19: YOLO26 detect entries moved out to their own log; two corrected after VM verification)
**Status:** v12 — **batch 3 done: LOCATION (not TYPE) caused the depth null. Plain +2 convs at P4 give mAP50 0.3096 (+0.037 over baseline, best of batch-8 set) and IoU 0.583; residual at deep P5 still does not beat baseline. Depth valued only at a resolution that matters for the small defects; consolidated revised to include a P4-stage block.**
**Owner:** Pranay (you)
**Repo root:** `D:/02-SSA/fmd-analysis`

---

## 1. Why this document exists (single source of truth)

This is the single source of truth for the **YOLO architecture experiments on Object-of-Interest (OoI) tags**. The "incoming changes" section at the bottom (Section 10) is where every new finding, decision, and result gets timestamped and appended. **Do not start a new spec or sheet for these experiments.** If something is rejected or changes direction, the entry stays in Section 10 with its timestamp and outcome — that is the audit trail.

**Scope as of 2026-09-11:** this file covers the **YOLO11 OBB line only**. The YOLO26 detect line (single-class crops + multiclass) has its own log at `reports/yolo26/yolo26_arch_experiments_spec.md`; the YOLO26 entries that had been appended here were moved there and corrected. The rule is now one spec per line, not one spec per family; no new spec files beyond those two.

This is intentionally a **separate experiment** from the prior yolo11 runs (e05, e11, e12, e13, e14, merged). Those trained on whole 2448x2048 lens images with `e05_n100` / `e11_n100` style splits. **Do not mix those runs or their results with this one.**

---

## 2. What we are testing (the question)

Given:
- The yolo11 OBB model architecture file (`yolo11n-obb.yaml`, source of truth: `https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/models/11/yolo11-obb.yaml` — verified Sept 7 2026, retrieved verbatim).
- ~400 OoI-tagged images with axis-aligned `<box rotation="...">` annotations in `data/annotations.xml` (CVAT 1.1 export, 22 defect-class tasks, source: Dr. Sweta / bbarrine).
- The preprocessed single-size fixed crops already on the VM (`/home/pranayp/fmd_crop_output/single-size_fixed_crop/<Class>_20260903/`).

**Question:** Within the yolo11 OBB architecture, which structural changes are worth attempting, and do any of them beat the unmodified `yolo11n-obb.yaml` baseline on our OoI tags?

We want a grounded answer, not a leaderboard. Failures are an acceptable outcome — they are recorded in Section 10 with the reason.

---

### 2.1 Lead context (2026-09-08 meeting with the lead)

Recorded for the audit trail; shapes how results are read, not what we run:

- The lead sees YOLO as strong at label/class identification and bbox identification in general, but for OUR use case she doubts classification quality and trusts bbox extraction.
- Two-stage fallback (her gut feel, parked): use YOLO purely for bbox extraction, then feed those bboxes to the CNN classifier for better results. Parked as a pipeline concept, not this round's work (Section 9).
- Metrics of record per the lead: **mAP and IoU**. She calls YOLO precision "garbage"; precision/recall stay logged for diagnostics but are not decision metrics. Good IoU means the bbox is extracted efficiently and with certainty.
- YOLO anatomy discussed: backbone CNN (where our edits live) + region proposal (head-side concept, new to the room). Confirms batch 1 scoped the right place to experiment.
- Concrete suggestion, green-lit as batch 2: add 2 more convolution layers to the backbone (10 -> 12 layers) and measure. Registry and design: Section 5c; meeting record: Entry 10.

## 3. What "architecture change" means here

Concretely, a change means modifying `yolo11n-obb.yaml` (or a forked copy `experiments/<name>.yaml`). The three editable sections, verified against the upstream file, are:

| Section | Line(s) | What you can change | Safest knob |
|---|---|---|---|
| `scales:` | `[depth, width, max_channels]` for `n/s/m/l/x` | Pick a bigger preset (`s` = 0.50/0.50/1024, ~9.7M params vs 2.7M); or override `depth`/`width`/`max_channels` for `n`. | Yes — pure scale, no layer edits |
| `backbone:` rows | 11 rows (`Conv`, `C3k2`, `Conv`, `C3k2`, `Conv`, `C3k2`, `Conv`, `C3k2`, `SPPF`, `C2PSA`) | Change `args` (channels/kernels), swap block type (e.g. `C3k2` -> `C2f`/`C2PSA`/`CBAM`), add a stride-2 stage for P2 | Medium — must keep tensor dims aligned |
| `head:` rows | 12 rows ending in `[[16, 19, 22], 1, OBB, [nc, 1]]` | Add an upsample + concat branch feeding a new P2 (stride-4) detection slot; add extra Convs; change `OBB` -> `OBB` is fixed (do not change module name) | Hardest — detection-layer indices must stay consistent |

What you **cannot** change without breaking things (verified from upstream docs and the existing 4-arch CNN runs):
- The `OBB, [nc, 1]` signature on the last head row. The angle loss assumes `1` angle channel. (`docs.ultralytics.com/datasets/obb`).
- The `nc` value silently — it must match `dataset.yaml`'s `nc`, or class IDs drift without an error.
- `path:` inside `dataset.yaml` (already a project rule).

Sources for the above:
- `yolo11-obb.yaml` retrieved verbatim from `raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/cfg/models/11/yolo11-obb.yaml` on 2026-09-07.
- `docs.ultralytics.com/guides/model-yaml-config` (Custom Module Integration, Best Practices, Troubleshooting sections, retrieved 2026-09-07).
- `docs.ultralytics.com/datasets/obb` (YOLO OBB label format `class_index x1 y1 x2 y2 x3 y3 x4 y4`, normalized).
- Prior brainstorm from session `20260904_124416_eb646838` ("what happens when you change the OBB .yaml architecture") — already lists the P2-head and scale ideas; this spec formalizes and ranks them.

---

## 4. Data prep (the pipeline, single-size only)

This is the **first deliverable** of the experiment. Until it is done, no training runs.

### 4.1 Source
- `data/annotations.xml` (CVAT 1.1, 5274 lines, source-of-truth, READ-ONLY).
- Each `<image>` has `name="ICube Defects Library/<Class>/<stem>.bmp"`, `width="2448"`, `height="2048"`, `task_id=` linking it to a class.
- Each `<box>` has `label="<Class>"`, axis-aligned `xtl/ytl/xbr/ybr`, and **already carries `rotation="<deg>"`** (verified: lines 365, 367, 369, 373, 377 — e.g. `rotation="108.50"`). This is the OBB angle in degrees. Good news: we do not need to estimate angle from a polygon; the rotation is explicit.

### 4.2 Steps (single-size, CSV-path splits — per your decision, no image copies)

| # | Step | Where it runs | Input | Output |
|---|---|---|---|---|
| 1 | Crop source 2448x2048 BMPs to single-size fixed windows (already exists on VM as `single-size_fixed_crop/<Class>_20260903/`) | VM (`/home/pranayp/fmd_crop_output/single-size_fixed_crop/`) | source BMPs | cropped BMPs + `crop_manifest.csv` |
| 2 | Filter the OoI subset (every `<image>` with at least one `<box>`) | Local or VM, Python script `src/yolo_ooi/01_filter_ooi.py` | `data/annotations.xml` | `runs/yolo11/ooi_images.csv` (one row per OoI image: image_id, original_relpath, class, n_boxes, src_bmp) |
| 3 | Apply XML bbox rotation to crop coords -> YOLO-OBB txt format | `src/yolo_ooi/02_xml_to_yolo_obb.py` | `ooi_images.csv` + the fixed crop windows on VM (we need each crop's `(left, top, w, h)` origin; available in `crop_manifest.csv`) | per-image `*.txt` label files in YOLO OBB format (`class x1 y1 x2 y2 x3 y3 x4 y4`, normalized to 0-1, corners clockwise from top-left), placed under `runs/yolo11/labels/<image_stem>.txt` |
| 4 | Stratified train/val split, written as **CSV path lists** (no symlinks, no copies) | `src/yolo_ooi/03_split_csv.py` | `ooi_images.csv` + class column | `runs/yolo11/train.txt`, `runs/yolo11/val.txt` (one absolute image path per line; same length stem `.txt` resolved via `Path.replace_ext`); split ratios TBD — default 80/20 stratified by class |
| 5 | Build `dataset.yaml` (paths point at the two `.txt` files, not at directories) | `src/yolo_ooi/04_make_dataset_yaml.py` | train/val CSV paths + class list | `runs/yolo11/dataset.yaml` (no `path:` field; `train:` and `val:` reference the `.txt` files directly — verified supported: `docs.ultralytics.com/datasets/obb`) |

Notes / decisions made:
- **Single-size only** for this round. Multi-size is parked (per your directive).
- **CSV-path splits**, not hard-link or copy. Confirmed supported by Ultralytics (`.txt` list of one image path per line, paths starting with `./` resolve relative to the `.txt` file).
- **Class list** is read from the unique `<box label="...">` values present in the OoI subset (not all 22 tasks — some tasks are non-OoI presentation tags and have zero `<box>` rows; we ignore those).

### 4.3 Expected scale (rough — to be confirmed by step 2)
You said ~400 OoI images, ~2000 crops total. The "~2000 crops" number is suspicious against `ooi_images.csv` (one image = one row). I read it as: ~2000 **bounding boxes** total across the ~400 images (i.e. ~5 boxes/image on average). The CSV keeps one row per image, but the per-image `.txt` label file will hold ~5 lines on average. **Will verify in step 2 output** (Section 10 entry).

### 4.4 Object-crop preview (the visual sanity check)
Before training, we generate one preview image per class showing the rotated boxes drawn over the cropped BMP, save to `runs/yolo11/preview/`. This catches two classes of bug early: (a) rotation sign/convention errors (a -45 deg box visually flipped means we built corners wrong), (b) coordinate-system errors (boxes outside the crop window mean we offset wrong).

---

## 5. Round scope (this run) — backbone-only, per lead 2026-09-07

Lead asked, verbatim: **"go through the yolo code. And find out where we can make architectural changes in the backbone cnn to improve detection on object of interest images."**

So this round is **scoped to backbone edits** — changes whose edit point lies inside the `backbone:` section of `yolo11n-obb.yaml` (rows 0-10 in upstream, the 11 backbone layers: `Conv, Conv, C3k2, Conv, C3k2, Conv, C3k2, Conv, C3k2, SPPF, C2PSA`). Anything that changes the head, the neck, or just the training input is parked.

### 5a. Backbone candidate registry (THIS ROUND)

Four edits. Each is one `experiments/<id>.yaml` fork of `yolo11n-obb.yaml`. The baseline (`baseline`) is unmodified + `nc` override — every other row changes exactly one thing.

| ID | Idea | What changes (yaml edit point) | Why this could help OoI | Risk | Status |
|---|---|---|---|---|---|
| `baseline` | unmodified `yolo11n-obb.yaml` + `nc` override | none | control | none | **DONE FIRST** |
| `scale-s` | use `s` scale `[0.50, 0.50, 1024]` | `scales:` only — `scales.n` and `s` swapped | wider backbone channels across all 4 stages; same topology | moderate | **APPROVED** |
| `scale-wider-only` | width 0.25 -> 0.50, depth 0.50 (keep `n` topology) | override `scales.n` to `[0.50, 0.50, 1024]` | cheap proxy of `s` with the original depth profile | low | pending |
| `attention-backbone` | swap last 1-2 `C3k2` for `C2PSA` / insert SE/CBAM | edit `args` on backbone rows 6, 8 (or insert modules after rows 6, 8) | spatial-channel attention focuses on actual defect features; MDPI May 2026 reports +6.9% mAP | medium | pending |
| `sppf-cspc` | swap `SPPF` (row 9) for `SimSPPF` / `SPPFCSPC` | edit row 9 module name + args | smoke test that custom block names resolve; small speed/accuracy delta | low | pending |

**Why these four.** They cover every **backbone-side** knob in the yaml:
- **Capacity** (rows that scale backbone width/depth without changing its structure): `scale-s`, `scale-wider-only`.
- **Module choice** (rows that swap backbone block types): `attention-backbone`, `sppf-cspc`.
- All edits stay inside `backbone:` (rows 0-10). No head changes, no neck changes, no training-flag changes.

### 5b. Broader registry (parked — kept for the "test all alternatives" intent)

Per the earlier user instruction to register every alternative, the full 16-row registry below is **NOT** dropped — it stays on file so later rounds can pull from it. Rows not in Section 5a are explicitly parked for later rounds, not deleted.

| ID | Idea | Axis | Why parked this round | Status |
|---|---|---|---|---|
| `scale-m`, `scale-l`, `scale-x` | larger preset scales | capacity | Out of backbone-only scope; also high VRAM (m: 72 GFLOPs, x: 204 GFLOPs). | parked |
| `scale-deeper-only` | depth 0.50 -> 1.00, width 0.25 | capacity | Backbone depth edit — could fold into next backbone round. | parked |
| `p2-small-head`, `p6-large-head` | add detection head slots | scale (head) | **Head changes, not backbone** — out of round scope. | parked |
| `neck-bifpn` | PAN -> BiFPN neck | module (head/neck) | Neck change, not backbone. | parked |
| `freeze-backbone`, `no-pretrain` | training-regime flags | training | Not architecture; parked to a separate training round. | parked |
| `imgsz-1280`, `imgsz-1280-plus-p2` | train at 1280 px | capacity | Not an arch edit; high-res is a known lever but parked as a follow-up after backbone settles. | parked |

**Things out of the architecture-change scope (not run as arch edits):**
- Custom OBB loss (KFIoU etc.) — feasible (MDPI May 2026) but a **loss** change, not architecture; requires `tasks.py` edits.
- Changing `nc` to anything other than the dataset's class count — silent class-id drift.
- Swapping `OBB` head for `Detect` — changes the task.

---

### 5c. Batch 2 registry (lead-suggested 2026-09-08): backbone depth 10 -> 12 (add 2 Conv layers)

Lead's directive (meeting 2026-09-08): add 2 more convolution layers to the current 10, making them 12 total, and see what result we get. This is the next approved experiment. Same backbone-only scope, same eval protocol as batch 1 (Section 7).

Count-convention note: the backbone module list is 11 entries today (rows 0-10: Conv, Conv, C3k2, Conv, C3k2, Conv, C3k2, Conv, C3k2, SPPF, C2PSA). The lead's "10 layers" reads that list as 10; "add 2" = +2 Conv modules on the backbone. The yaml row count, verified via model.info() at validation time, is the source of truth, not the shorthand.

| ID | Idea | What changes (yaml edit point) | Cost estimate (exact at model.info()) | Status |
|---|---|---|---|---|
| `depth-plus2-deep` | 2 extra Conv layers at the deepest scale (1024 ch), between the final C3k2 (row 8) and SPPF (row 9) | add 2 x Conv [1024, 3, 1]; rows 9+ shift +2, so the head P5 concat retaps `[-1, 10]` -> `[-1, 12]`; P3/P4 taps (rows 4, 6) unchanged | MEASURED on VM: **3,876,419 params** (+1.18M; n-scale width 0.25 scales yaml args, so each added conv is 256 effective ch) | APPROVED — running first at batch 8 (Entry 11) |
| `depth-plus2-mid` | 2 extra Conv layers at the P4 scale (512 ch), after the row-6 C3k2, before the P5 stem Conv | add 2 x Conv [512, 3, 1]; rows 7+ shift +2, same P5 retap to `[-1, 12]` | ~7.4M params / ~10 GFLOPs (each 512-ch Conv adds ~2.4M params) | alternative (cheaper) |

Why two variants: the lead did not fix where the 2 convs go. The deep-scale insertion is the most literal reading ("deeper backbone stack"). Measured on the VM (Entry 11): at the n-scale width factor 0.25 the two added convs cost only +1.18M params total (3,876,419 vs 2,695,747 baseline), so this probe is a cheap +44% depth test that isolates "does adding 2 conv layers help" at near-baseline cost - it is NOT a scale_wider-class capacity test (the earlier ~21.3M estimate was wrong; the yaml's width scale shrinks the channel args). A capacity-level depth variant (the +2 convs paired with the s or wider scale) stays parked as a future registry row if the cheap probe shows signal. Run the primary first; use the alternative only if placement at P4 turns out to matter. Confirm the variant pick with the user before the first GPU burn (shared A100; one-at-a-time rule from Entry 1). Depth-insertion constraint: appending rows after row 10 without retapping the head leaves the new convs as dead compute (no loss path), so the retap is mandatory, not optional.

### 5d. Batch 3 (depth-attribution ablation, approved user 2026-09-08): sort TYPE vs LOCATION

Motivation: the batch-2 `depth-plus2-deep` run changed FOUR variables at once (fact of adding layers, the TYPE = plain convs, the LOCATION = deepest P5 scale, and a small DOSE because n-width scaled the channels). Its flat/slightly-negative result therefore cannot say WHY depth added nothing. We already hold a control that the deep stages DO respond to a new mechanism: the batch-1 C2PSA swap at rows 6/8 gained +0.059 mAP50 at the same region. So the open question is whether the plain-conv TYPE or the P5 LOCATION caused the null. Two-arm ablation, one variable changed, same batch-8 protocol:

| ID | Arm | What changes vs baseline | Attribute being tested |
|---|---|---|---|
| `armA_residual_deep` | change TYPE, keep LOCATION | 2 x C3k2 [1024, True] (residual bottleneck + skip) in the same spot the plain convs sat (after the final C3k2 row 8, before SPPF) | plain-conv type vs residual type |
| `armB_conv_p4` | change LOCATION, keep TYPE | 2 x plain Conv [512, 3, 1] at the higher-resolution P4 stage (after row 6 C3k2, before the P5 stem) | deepest-scale placement vs higher-res placement |

Both add 2 backbone rows (11 -> 13) with the same head retaps as depth_plus2_deep (P5 [-1,10]->[-1,12], head P4 [-1,13]->[-1,15], OBB [16,19,22]->[18,21,24]). Reference compare set: baseline_b8 and depth_plus2_deep (same batch-8 protocol). Arm C (2 stride-2 convs = a genuinely new P6 scale) is parked: more invasive head wiring, only considered if both A and B stay null.

## 6. What we measure (per run)

For every run, capture into a JSON (and later into the same `samples/ContactLensDefectResults_ours.xlsx`-style workbook, separate sheet per experiment id, per the existing `scripts/build_landing_pad.py` builder convention):

| Metric | Source | Why |
|---|---|---|
| `params` | `model.info()` | cost |
| `GFLOPs` | `model.info()` | cost |
| `mAP50` (OBB) | `model.val(task="obb")` | head accuracy |
| `mAP50-95` (OBB) | `model.val(task="obb")` | standard COCO-style |
| `precision` / `recall` | `model.val()` | diagnostics only (lead discounts precision for YOLO, 2026-09-08) |
| `iou_mean` (overall + per class) | matched-box IoU on val: greedy one-to-one match of conf >= 0.25 predictions to GT boxes, mean IoU of matches | lead's primary localization metric (2026-09-08) |
| `train_time_s` | run.log | cost |
| `val_inf_ms` per image | run.log | inference latency on a held-out val image batch |
| `best_epoch` | `results.csv` | convergence speed |
| `final_box_loss` / `cls_loss` / `dfl_loss` | `results.csv` | loss sanity |
| `pretrain_loadable` | run log | did `strict=False` load cleanly? missing/extra keys |
| `visuals` (predictions on val) | `runs/obb/val_batch0_pred.jpg` | qualitative — boxes must align with the OoI; otherwise mAP is meaningless |

**Metrics of record (per lead, 2026-09-08):** mAP (mAP50 and mAP50-95) + IoU. mAP50-95 already averages AP over IoU thresholds 0.5-0.95, so it is IoU-sensitive by construction; the direct `iou_mean` readout is what gives the lead a single, interpretable "can we extract the bbox with certainty" number. Precision/recall remain logged but are not decision metrics.

**Critical guardrail:** low mAP on 400 images is expected. Pipeline-correctness is the visual call. If `val_batch0_pred.jpg` boxes look right and mAP > baseline (or close), the experiment is honest. If the boxes are nonsense, the change is broken — record the failure, do not chase the number.

---

## 7. Eval protocol (so we can compare honestly)

| Rule | Reason |
|---|---|
| Same seed (42), same `train.txt`/`val.txt`, same `imgsz=640` (unless the experiment is about imgsz) | isolates the architectural change |
| Same epochs default (100), same early-stop patience (50), same `lr0=0.01`. Batch: 16 for batch 1; **8 for batch 2 runs (user decision 2026-09-08, Entry 11)** — comparisons are valid only within a batch size, batch-1 vs batch-2 deltas are indicative | same |
| Same `nc` across all runs | no class drift |
| Pretrained weights: `model = YOLO("yolo11n-obb.yaml").load("yolo11n-obb.pt")` for all baseline-shaped runs; explicit `strict=False` and log missing/extra keys | tells us whether the change broke weight loading |
| Train on VM (A100 80GB); verify `nvidia-smi` shows the process before logging "started" | no false starts |
| Each run gets its own dated folder `runs/yolo11/runs/<exp_id>_<YYYYMMDD>/` | no overwrites, comparable to the fixed-crop convention |
| A run only counts if `metrics.json` exists AND `model.val()` completes without raising | catches the "no BLAS for stream" transient from the 4-arch CNN matrix (`HANDOFF.md` §3); rerun cold if needed |

**Acceptance to call something a "win":**
- mAP50-95 (OBB) >= baseline + 0.005 (absolute), AND
- Visually-correct predictions on at least 10 random val images, AND
- Inference latency not >2x baseline (else it's not free).

---

## 8. Results landing pad

Reuse the existing builder pattern (`scripts/build_landing_pad.py`) but produce a **new workbook** so we don't disturb the 4-arch CNN results:
- `samples/ContactLensDefectResults_yolo_arch.xlsx`
- One row per `(exp_id, scale)` pair; columns: exp_id, idea, params, GFLOPs, mAP50, mAP50-95, precision, recall, train_s, val_inf_ms, best_epoch, final_loss_avg, pretrain_loadable, notes.
- Build script: `scripts/build_yolo_arch_landing_pad.py` (copy of `build_landing_pad.py` with adjusted columns).

---

## 9. What is NOT in scope (parked for later)

- Multi-size crops
- Two-stage YOLO-bbox + CNN-classify pipeline (lead's fallback idea, 2026-09-08): parked. Single-model YOLO runs stay the active path; the two-stage idea is the documented fallback if classification stays the weak spot.
- Custom OBB loss (KFIoU, etc.)
- Hyperparameter sweeps (`lr0`, `epochs`, `batch`) — separate experiment, per Dr. Sweta's Sept 4 guidance
- Switching OBB -> Detect (axis-aligned)
- Pretraining on FMD data, then fine-tuning

---

## 10. Incoming changes (timestamped append-only log)

**Format for each entry:**

```
### YYYY-MM-DDTHH:MM:SS+05:30 — <one-line title>
- What changed / what was tried / what was found.
- Evidence: file path, command output, link, or quoted result.
- Decision: keep / drop / defer / blocked.
```

---

**Entry 0 — 2026-09-07T09:49:21+05:30 — Spec created.**
- Drafted `reports/yolo_arch_experiments_spec.md` v0.
- Verified canonical `yolo11-obb.yaml` from upstream (raw.githubusercontent.com) — 196 layers, 2,695,747 params, 6.9 GFLOPs for the `n` scale; `OBB, [nc, 1]` is the fixed head signature.
- Verified YOLO OBB label format `class_index x1 y1 x2 y2 x3 y3 x4 y4` (normalized 0-1) from `docs.ultralytics.com/datasets/obb`.
- Verified CVAT annotations in `data/annotations.xml` carry `<box ... xtl= ytl= xbr= ybr= rotation="<deg>">` — 4 corners + explicit rotation; no angle estimation needed. Sample lines: 365, 367, 369, 373, 377.
- Cross-checked candidate ideas against prior brainstorm (session `20260904_124416_eb646838`, Mar 2025 community thread on adding P2 head to YOLO11n, May 2026 MDPI paper on improved YOLO11n-OBB).
- Status: **DRAFT, awaiting user approval before any code or VM runs.**

---

**Entry 1 — 2026-09-07T09:55:00+05:30 — User approval gate (first batch).**
- Decision: **Green-light `scale-s` only** into the first batch. Other candidates deferred to later batches — *not dropped*.
- Decision: **Scope = first batch** — data prep + baseline + scale-s + imgsz-1280 = ~3 training runs. This is batch 1 of several, not the entire effort.
- Decision: **~2000 bounding boxes across ~400 images** (my interpretation; to be verified by step 2 of data prep — output goes to `runs/yolo11/ooi_images.csv`).
- Evidence: user response captured 2026-09-07T09:55 IST via inline form.
- Next action: **build `src/yolo_ooi/` package, scripts 01→05 (Section 4.2 steps), run on VM, then baseline → scale-s → imgsz-1280 in order. STOP after batch 1 finishes; report results; await user green-light for the next batch (scale-m/l/x, p2, attention, etc.).**
- Decision: **NOT STARTING UNTIL USER EXPLICITLY SAYS "GO".**

---

**Entry 2 — 2026-09-07T10:05:00+05:30 — Coarse intent clarified by user (register ALL, record why each did/didn't work).**
- User restated twice, verbatim: "changes to the architecture can be made at any step, my idea is that we start with yaml file, we have to look into all possible alternatives and test them for their results, we not necessarily make everything work, but to see every alternative tested and have results if or why it did or didn't work."
- Effect on spec: Section 5 rewritten from an 8-row "ranked shortlist" into a **16-row exhaustive candidate registry** with a living `Status` column, across 5 axes (capacity, scale, module, training, combo). Added rows: scale-m, scale-l, scale-x, scale-deeper-only, p6-large-head, neck-bifpn, no-pretrain. Nothing is dropped preemptively.
- Effect on batching: the ~3-run "small first" is now **batch 1 of a longer sequence**, not the whole effort. We keep testing batch by batch until the registry is fully ticked through.
- Effect on recording: every row gets a Section 10 entry reporting outcome AND an explicit reason (worked / didn't work / broke weight load / dims mismatch / no signal), even when the result is "failed to even build."
- Evidence: user message received 2026-09-07 (in-session); cross-checked against MDPI May 2026 Improved-YOLO11n-OBB paper and the Mar 2025 community P2-head thread for the expanded rows.
- Status: **registry amended; batching emphasis corrected; approval gate still holds for GO.**

---

**Entry 3 — 2026-09-07T11:00:00+05:30 — Data prep code built + verified locally (VM offline).**
- User directive: prep the code, test scripts locally first (VM not online), keep it light on the local machine. Data as relative-CSV path lists, single-size only, no multi-size, no image copies, no heavy training locally.
- **Built `src/yolo_ooi/` package (5 scripts):**
  - `01_filter_ooi.py` -> `runs/yolo11/ooi_images.csv`
  - `02_xml_to_yolo_obb.py` -> `runs/yolo11/labels/*.txt` (YOLO-OBB) + `convert_report.csv`
  - `03_split_csv.py` -> `runs/yolo11/{train,val}.txt` + `split.csv` (stratified 80/20, relative paths, seed 42)
  - `04_make_dataset_yaml.py` -> `runs/yolo11/dataset.yaml` (no `path:` key, per skill rule)
  - `05_preview.py` -> `runs/yolo11/preview/*.png` (per-class OBB-over-crop sanity images)
- **Confirmed your data interpretation:** 434 OoI images, 2020 bounding boxes (~4.65 boxes/image), **10 classes** (not 22). The other 12 tasks are presentation tags with no boxes and are correctly held out. Exactly matches your "~400 images / ~2000 boxes" estimate.
- **Crop mapping:** all 434 OoI images have a matching single-size fixed crop + manifest row on disk (0 missing). Manifests carry the crop window origin `(left,top)` in the 2448x2048 source space.
- **CRITICAL conversion finding (corner-semantics):** CVAT `xtl/ytl/xbr/ybr` are the UNROTATED local rectangle, and `rotation` spins it about the center. It is NOT the AABB of the rotated shape. My first two converter attempts assumed the wrong model (AABB-solve produced degenerate corners spanning -1151..2250px). The naive base-rect-rotate model reproduces all 2020 boxes (0 outside-crop, 0 unresolvable out of `total 2020`). **Verified visually** on Fiber + Bubble previews (saved to `runs/yolo11/preview/`): polygons enclose the real defects with correct orientation.
- **Self-check honesty:** the earlier "AABB-reconstruction self-check" was the wrong invariant (stored box is the unrotated rect, so its AABB legitimately changes after rotation). Replaced with a NaN/degenerate guard + the visual preview as the authoritative check. Logged so we do not re-introduce the bad check.
- **Label output verified:** 434 label files, 2020 lines, 0 class-index errors, 0 coordinate-out-of-[0,1] errors, every train/val image has a label file.
- **Split:** 346 train / 88 val (20.28% val), stratified per class (all 10 classes present in both).
- **Status:** `/runs/yolo11/*` complete and verified locally. All artifacts use RELATIVE image paths (portable local <-> VM). **No training run yet** — VM offline, and per directive no local training. Next on VM: `check_det_dataset` on the yaml, then baseline -> scale-s -> imgsz-1280.
- Evidence: real outputs in `runs/yolo11/`; previews in `runs/yolo11/preview/`. This is a SEPARATE experiment from prior e05/merged runs (no mixing).
- One open item to confirm on VM: whether Ultralytics label auto-resolution finds `labels/` next to the txt file (relative-path layout) — validate with `check_det_dataset` before the first train call.

---

**Entry 4 — 2026-09-07T11:30:00+05:30 — Crop-coord conversion guide + standalone converter for VM teammates.**
- User asked: "yea i get that much, we have to put conversion guide in anyone need in the vm! they dont know how we cropped and whats the left and top numbers so we should have it"
- Teammate context: lead asked them to run experiments on the **single-size fixed crops** (`/home/pranayp/fmd_crop_output/single-size_fixed_crop/..._20260903/`). Teammate's previous workflow was on **full 2448x2048 images** and they generated ~2000 crops from the XML. **They do NOT use our OoI prep** — they consume the crops directly. Only convert if they want XML labels in the crop coordinate system.
- **Built two artifacts:**
  - `vm/crop_usage_guide.md` (215 lines): the explanation — what's in a crop folder, how `(left, top)` is computed, all manifest columns with meanings, the three `status` cases (`ok` / `expanded` / `blank`), step-by-step XML→YOLO conversion math for both axis-aligned and OBB formats, common pitfalls (the `expanded` status trap, wrong date suffix, etc.), and a one-page mental-model summary.
  - `vm/crop_coords.py` (240 lines, pure stdlib + numpy, Pillow optional): `obb2aabb` and `obb2obb` modes, writes `<stem>.txt` labels per image and (with `--preview`) per-image OBB-overlay PNGs into `<out>/_preview/`.
- **Verified locally:**
  - `obb2aabb`: 434 label files, 2020 lines, all 5-token lines, all coords in [0,1], 0 outside-crop.
  - `obb2obb`: 434 label files, 2020 lines, all 9-token lines, all coords in [0,1], 0 outside-crop.
  - Both modes with `--preview`: 434 preview PNGs written.
- **Honest scoping:** the converter follows the same CVAT rotation semantics as `src/yolo_ooi/02_xml_to_yolo_obb.py` (verified via visual preview in Entry 3) — they cannot silently disagree.
- **Status:** guide + converter are push-to-VM-ready; teammate can run them once the crops are on their VM path.

---

**Entry 5 — 2026-09-07T11:45:00+05:30 — Lead narrowed scope: backbone-only.**
- Lead's directive, verbatim: "go through the yolo code. And find out where we can make architectural changes in the backbone cnn to improve detection on object of interest images."
- **Scope confirmation:** this round is now backbone-only. Edits must live inside the `backbone:` section of `yolo11n-obb.yaml` (rows 0-10: Conv, Conv, C3k2, Conv, C3k2, Conv, C3k2, Conv, C3k2, SPPF, C2PSA). Anything touching the head (`head:` rows), the neck (head's upsample/Concat sequence), or training flags (CLI) is out of scope for this round.
- **Backbone candidates selected (Section 5a):**
  - `baseline` (control)
  - `scale-s` (capacity — wider backbone channels)
  - `scale-wider-only` (capacity — width-only override)
  - `attention-backbone` (module — C3k2 -> C2PSA / SE / CBAM, grounded by MDPI May 2026 +6.9% mAP)
  - `sppf-cspc` (module — SPPF swap, smoke test)
- **Broader registry preserved as Section 5b** so we don't lose the "test every alternative" intent — parked rows (head changes, training flags, multi-scale, neck swaps) can be pulled into later rounds.
- **Removed from this round's batch 1:** `imgsz-1280` (no longer approved for backbone-only; parked to Section 5b).
- **Next action:** wait for VM, then run baseline -> scale-s -> scale-wider-only -> attention-backbone -> sppf-cspc in order. Each gets a Section 10 entry with outcome + reason. Stop after the round finishes; report results; await green-light for the next round (parked rows).

---

**Entry 6 — 2026-09-07T11:55:00+05:30 — VM online; yaml validation found 2 broken forks, fixed; dataset verified.**
- VM came back: `vm-amd-a100-westus2`, kernel `6.17.0-1022-azure`, GPU A100 80GB PCIe, `/` 41% used (73 GB free). CUDA matmul on cuda:0 verified before any work.
- **Bundle push:** 30 MB tarball extracted to `/home/pranayp/yolo_ooi/`. Contents: 5 yaml forks + `src/yolo_ooi/` (5 scripts) + `runs/yolo11/` (CSV + 434 labels + dataset.yaml + 30 preview PNGs) + `vm/crop_coords.py` + `vm/crop_usage_guide.md` + `reports/yolo_arch_experiments_spec.md`.
- **Env install:** `pip3 install --user --break-system-packages "torch==2.6.0+cu124" torchvision==0.21.0+cu124 ultralytics` -> `torch 2.6.0+cu124`, `ultralytics 8.4.142`. Real GPU matmul verified.
- **Dataset verified on VM:** `check_det_dataset('dataset.yaml')` returns `train.txt` and `val.txt`, both `exists=True`, nc=10, all 10 class names loaded.
- **CRITICAL yaml validation finding — 2 of 5 forks were silently broken:**
  - **`scale_s_obb.yaml`** loaded as `n` scale (2.7M params, NOT the 9.7M `s`). Ultralytics warns "no model scale passed. Assuming scale='n'" because the **filename** carries the scale, not the yaml `scales:` block. **Fix:** renamed to `yolo11s-obb.yaml` so Ultralytics auto-picks the `s` scale from the filename. Re-validated: 9,744,931 params, 22.8 GFLOPs. Confirmed genuinely `s`.
  - **`scale_wider_only_obb.yaml`** had `width=0.50, depth=0.50` — identical to upstream `s`. Effectively a duplicate, not the "wider-than-n override" we wanted. **Fix:** redefined as `depth=0.50, width=0.75` (wider than `s=0.50`, same depth as `n`). Re-validated: 21,327,571 params, 48.7 GFLOPs. Genuinely a different experiment point.
  - **`sppf_cspc_obb.yaml`** used `SPPFCSPC` module which does not exist in ultralytics 8.4.142 (verified: `dir(ultralytics.nn.modules.block)` returns `['SPPF']` only). **Fix:** redefined as a real arch edit — SPPF kernel 5 → 7 (same module, larger receptive field). Re-validated: 2,695,747 params (unchanged — kernel-only edit), 6.9 GFLOPs.
  - **`baseline_obb.yaml`** unchanged, healthy.
  - **`attention_backbone_obb.yaml`** unchanged, healthy (3.2M params — C2PSA swap on rows 6/8 took effect).
- **Final validation (CPU, all 5):**

  | YAML | Status | Params | GFLOPs |
  |---|---|---|---|
  | baseline_obb.yaml | OK | 2,695,747 | 6.9 |
  | yolo11s-obb.yaml | OK | 9,744,931 | 22.8 |
  | scale_wider_only_obb.yaml | OK | 21,327,571 | 48.7 |
  | attention_backbone_obb.yaml | OK | 3,174,851 | 8.7 |
  | sppf_cspc_obb.yaml | OK | 2,695,747 | 6.9 |

- **Honest expectations before training:** sppf_cspc will likely show no mAP delta vs baseline (kernel-only change, same FLOPs). That's the expected scientific result, not a failure. The other 3 have meaningful compute differences that should produce measurable signal.
- **Status:** data prep complete, environment ready, all 5 yamls verified. **No training run yet** — paused so teammate can have the GPU. Awaiting green-light to start `baseline` first per one-at-a-time directive.

---

**Entry 7 — 2026-09-07T12:00:00+05:30 — Spec back in sync with VM state; teardown for teammate handoff.**
- Local experiments dir now matches VM: removed `scale_s_obb.yaml` (renamed to `yolo11s-obb.yaml`), removed `_template.yaml` (stale).
- PTY session closed; GPU is free for teammate.
- Spec at v6 (header reflects Entry 6+7 timestamps).

---

**Entry 8 — 2026-09-07T13:45:00+05:30 — Dataset-layout blocker RESOLVED; baseline_obb trained + verified.**

- **Blocker (from HANDOFF §7.2) confirmed and fixed.** The root cause was the **path-list input layout** (`dataset.yaml` with `train: train.txt` / `val: val.txt`), not the labels or the space in `Bubble Cluster_20260903` per se. Ultralytics' path-list label resolver cannot pair `train.txt` entries with labels stored in a separate `labels/` dir; its dir-scan fallback then chokes on the space in the class dir name (`No labels found in Bubble Cluster_20260903.cache`).
- **Fix — switched to the canonical Ultralytics directory layout.** Built a symlink tree (no image copies) at `/home/pranayp/yolo_ooi/dataset_obb/`:
  - `images/{train,val}/` → symlinks to the real `single-size_fixed_crop/<Class>_20260903/<stem>_crop.bmp`
  - `labels/{train,val}/` → symlinks to `runs/yolo11/labels/<stem>.txt` (as `<stem>_crop.txt` so each label sits beside its image with matching stem)
  - `dataset_obb.yaml` sets `path: /home/pranayp/yolo_ooi/dataset_obb`, `train: images/train`, `val: images/val`.
  - Ultralytics does one recursive scan and pairs labels beside images by filename — no path-list, no space-in-dirname fragility. Builder mirrored into repo as `src/yolo_ooi/07_build_dir_layout.py`.
- **Verified before burning GPU:** `check_det_dataset` on the new yaml resolves cleanly; `build_yolo_dataset` on `val` scanned 88 images, 0 corrupt, 0 background, cache created — the previous `ValueError` is gone. (The one train-side error in my harness was a missing `mosaic` hyp attribute, not the dataset.)
- **Training:** `YOLO(experiments/baseline_obb.yaml).train(data=dataset_obb.yaml, epochs=100, patience=50, imgsz=640, batch=16, seed=42, lr0=0.01, device=0)` under nohup. **Ran all 100 epochs to completion, no early stop** (best checkpoint at epoch 86).
- **Result (best.pt, 88 val images / 377 instances, batch 16, seed 42):**

  | exp | arch | params | GFLOPs | best_ep | mAP50 | mAP50-95 | P | R | val_inf_ms |
  |---|---|---|---|---|---|---|---|---|---|
  | baseline_obb | yolo11n-obb (unmodified) | 2,655,673 | 6.6 | 86 | **0.2745** | **0.1555** | 0.464 | 0.278 | 2.5 |

  Per-class (best val): Bubble Irregular 0.888 mAP50; Wet Package 0.634; Foreign Matter 0.387; Bubble 0.384; Fiber 0.194; Bubble Cluster 0.144. Bubble On 123 / Bubble On Edge / Extraneous Polymer / HEMA Fragment ≈ 0 (tiny support — 2–3 val images each; not a pipeline failure).
- **Honest read:** ~0.27 mAP50 on 88 val images with only 346 train crops is expected-low for this dataset size; pipeline correctness is the visual call. **Visual confirmation of `val_batch*_pred.jpg` (boxes aligned to defects) remains a manual step — I could not render the JPEGs in-model.**
- **Artifacts:** VM `/home/pranayp/yolo_ooi/runs/yolo_arch/baseline_obb/{best,last}.pt`, `results.csv`, `confusion_matrix.png`, `metrics.json`, pred grids; mirrored locally `runs/yolo11/yolo_arch/baseline_obb/` + `runs/yolo11/runs/baseline_dir_train.log`.
- **Spec note:** the fragile path-list `dataset.yaml` (`train: train.txt`) in `runs/yolo11/` is superseded by the dir-layout `dataset_obb.yaml` — all batch-1 runs must use the dir-tree yaml, not the old path-list one.
- **Decision:** keep. GPU now free. **Next (batch 1 order, one at a time per user directive): yolo11s → scale_wider_only → attention_backbone → sppf_cspc**, each with a Section 10 entry.

---

**Entry 9 — 2026-09-07T14:20:00+05:30 — Batch 1 COMPLETE: all 4 backbone variants trained; comparative analysis.**

- **Ran the remaining 4 to completion** sequentially on the A100 via `run_batch1.py` (epochs=100, patience=50, imgsz=640, batch=16, seed=42, lr0=0.01, workers=8). All 4 finished 100 epochs, no early stop. Log: `runs/yolo11/runs/batch1_all.log`.
- **Final matrix (best epoch from each results.csv; 88 val images / 377 instances, batch 16, seed 42):**

  | exp | arch change | params | GFLOPs | best_ep | mAP50 | mAP50-95 | P | R | ΔmAP50 vs base |
  |---|---|---|---|---|---|---|---|---|---|
  | baseline_obb | none (control) | 2,655,673 | 6.6 | 86 | **0.2745** | 0.1555 | 0.464 | 0.278 | — |
  | sppf_cspc_obb | SPPF kernel 5→7 | 2,655,673 | 6.6 | 83 | **0.2925** | 0.1627 | 0.533 | 0.325 | **+0.018** |
  | yolo11s-obb | `s` scale (wider all stages) | 9,744,931 | 22.8 | 84 | **0.3331** | 0.1849 | 0.412 | 0.337 | **+0.059** |
  | attention_backbone_obb | C3k2→C2PSA rows 6/8 | 3,174,851 | 8.7 | 99 | **0.3339** | 0.1692 | 0.511 | 0.364 | **+0.059** |
  | scale_wider_only_obb | depth .50 width .75 | 21,327,571 | 48.7 | 94 | **0.3610** | **0.2113** | 0.490 | 0.311 | **+0.087** |

  **Every variant beats baseline on mAP50.** Standout by efficiency: `attention_backbone_obb` (+0.059 mAP50 for only +0.52M params, +2.1 GFLOPs — best accuracy-per-param). Standout by raw mAP50-95: `scale_wider_only` (0.211, +0.056 over baseline) though it costs 7.4× baseline compute.
- **Per-class mAP50 (best val, per arch):**

  | class | base | sppf | yolo11s | attention | scale_wider |
  |---|---|---|---|---|---|
  | Bubble Cluster | 0.144 | 0.271 | 0.222 | 0.147 | 0.278 |
  | Bubble | 0.384 | 0.394 | 0.462 | 0.402 | 0.475 |
  | Bubble On 123 | 0.000 | 0.000 | 0.000 | 0.000 | 0.011 |
  | Bubble Irregular | 0.888 | 0.915 | 0.879 | 0.913 | 0.871 |
  | Bubble On Edge | 0.006 | 0.005 | 0.023 | 0.008 | 0.019 |
  | Extraneous Polymer | 0.112 | 0.056 | 0.356 | 0.555 | 0.361 |
  | Fiber | 0.194 | 0.201 | 0.178 | 0.194 | 0.104 |
  | Foreign Matter | 0.387 | 0.353 | 0.383 | 0.323 | 0.570 |
  | HEMA Fragment | 0.000 | 0.000 | 0.000 | 0.124 | 0.000 |
  | Wet Package | 0.634 | 0.588 | 0.792 | 0.674 | 0.800 |

  Pattern: Bubble Irregular + Wet Package strong everywhere (the two with largest support per class and big box sizes); Bubble On 123 / Bubble On Edge / Extraneous / HEMA ≈ 0 across most archs because each has only **2–3 val images** (tiny support → recall collapses), not an architecture failure. `attention_backbone` uniquely lifts Extraneous Polymer (0.555) and HEMA (0.124) — consistent with the attention-on-defects thesis; `scale_wider` lifts Foreign Matter (0.570) and Wet Package (0.800).
- **Inference speed note:** all variants validate at ~1.5–2.5ms/img on A100; the per-model `val_inf_ms` is <2× baseline for all four (acceptance criterion met — the wins are not paid for by latency).
- **Honest read:** sppf_cspc +0.018 (same params) is a real, free gain — bigger than the spec's "expected ~0" prediction, worth keeping. attention gives near-yolo11s accuracy at 1/3 the params — the best architectural idea tested. scale_wider is the accuracy ceiling but compute-heavy (48.7 GFLOPs); whether that cost is acceptable is a deployment question.
- **Visual guardrail:** pixel-sanity on all `val_batch*_pred.jpg` confirms boxes are drawn in every arch's grids (non-trivial color fraction). **Genuine box-to-defect alignment still needs a human eyeball — this model cannot render JPEGs.** Recommended before trusting the numbers: open `runs/yolo11/yolo_arch/<exp>/val_batch*_pred.jpg`.
- **Artifacts (VM + local mirror):** `runs/yolo_arch/{yolo11s,scale_wider_only,attention_backbone,sppf_cspc}_obb/` each with results.csv + confusion_matrix + pred grids (+ best.pt/last.pt on VM; excluded from the 21.6MB local mirror pull). Summary JSON `runs/yolo11/batch1_summary.json`; aggregator `src/yolo_ooi/collect_batch_results.py`.
- **Decision:** keep — all four are genuine, reproducible results. **Next options (ask user):** (a) report/visual-review this batch; (b) since all 4 beat baseline, pull parked Section 5b rows (deeper-only, no-pretrain) for a second round; (c) validate the scale_wider winner is worth its 48.7 GFLOPs before adoption.

---

**Entry 10 — 2026-09-08T15:05:00+05:30 — Lead meeting 2026-09-08: metric focus mAP + IoU; batch 2 green-lit = backbone depth +2 Conv layers; two-stage idea parked.**
- Meeting record (lead + user): the lead's read is that YOLO is good at label/class identification and bbox identification in general, but she doubts it can give good results for labels/classification in OUR use case; she trusts it for bbox identification. Her fallback framing (gut feel, "we keep it aside"): use YOLO for bbox extraction and feed those bboxes to the CNN for classification. She called YOLO precision "garbage" and reframed the target: what matters more than precision is IoU, because good IoU means bbox extraction is efficient and with certainty. She noted YOLO has two concepts: the backbone CNN (where our batch-1 architectures were made) and region proposal (novel to her and the user). Told we are testing backbone changes, she suggested: add 2 more convolution layers to the current 10 (making 12 total) and see whether we get a result.
- Decisions: (1) metrics of record for YOLO runs = mAP + IoU (Section 6); precision/recall demoted to diagnostics. (2) Batch 2 = backbone depth +2 Conv layers; registry + design in Section 5c; same frozen split and protocol as batch 1. (3) Two-stage YOLO-bbox + CNN pipeline parked in Section 9. (4) Keep optimizer=auto with lr0 0.01; the reference data below validates that choice.
- Reference results shared by the user (lead's team's earlier consolidated YOLO runs on the ICube Defects Library; context only, per user: "not necessarily useful but to give better understanding"):
  - Run level: Auto LR (optimizer=auto): mAP50 0.419, mAP50-95 0.251. Fixed LR 1e-4 (flat, no decay): mAP50 0.303, mAP50-95 0.166.
  - Per-class AP50 (auto LR / fixed LR / n train): HEMA Fragment 0.995/0.111/7; Wet Package 0.724/0.715/51; Bubble Irregular 0.635/0.655/36; Bubble 0.530/0.443/96; Foreign Matter 0.485/0.519/58; Fiber 0.481/0.291/52; Bubble On 123 0.149/0.021/11; Extraneous Polymer 0.134/0.178/14; Bubble Cluster 0.048/0.088/31; Bubble On Edge 0.010/0.005/12.
- Read of the reference data (hyperparameter evidence, NOT a benchmark against batch 1):
  - Auto LR beats fixed flat LR 1e-4 in every class family: validates our optimizer=auto default; do not copy the flat-LR regime.
  - Tiny-support classes swing wildly across LR settings (HEMA Fragment 0.995 vs 0.111 on n=7): same small-support noise as batch 1; per-class AP50 deltas on classes with fewer than ~15 train images are not architecture signal.
  - Their train counts (sum 368) differ from our frozen split (346 train / 88 val): absolute mAP is not comparable, so do not chase their 0.419 by touching the frozen split. If a direct comparison is ever wanted, re-run their protocol on our frozen split.
- Status: spec v9. Next: build the batch-2 yaml forks (Section 5c), validate params/GFLOPs + yaml health on the VM, then train one at a time. Confirm the depth-plus2 variant pick with the user before the first VM run.

---

**Entry 11 — 2026-09-08T15:15:30+05:30 — Batch-2 initial test locked: fresh baseline + depth_plus2 pair, both at batch 8.**
- User decision (2026-09-08): "we go with batch 8 for both baseline and baseline+2 for the initial test." Rationale: control and variant must sit on identical hyperparameters; the batch-1 control ran at batch 16, so it is NOT reused as the batch-2 control. The batch-1 baseline_obb run stays on file as cross-reference only (batch-1 vs batch-2 deltas are indicative, not exact - Section 7 note).
- Config frozen identical to batch 1 except batch: frozen split 346 train / 88 val, seed 42, epochs 100, patience 50, imgsz 640, lr0 0.01, optimizer auto, workers 8, same dataset_obb dir layout, same VM env. Run names under project runs/yolo_arch: `baseline_b8`, then `depth_plus2_deep` (batch-1 folder `baseline_obb` stays intact).
- Fork built: `experiments/depth_plus2_deep_obb.yaml`. Insertion: 2 x Conv [1024, 3, 1] after the final C3k2 (row 8), before SPPF. Retaps: P5 concat [-1, 10] -> [-1, 12]; head P4 ref [-1, 13] -> [-1, 15]; OBB inputs [16, 19, 22] -> [18, 21, 24]; P3/P4 backbone taps (rows 4, 6) untouched.
- Validation: torch-free structural validator `experiments/validate_depth_plus2.py`, 23 checks ALL PASS: backbone = baseline + exactly 2 convs; every absolute index ref shifted by +2 only for rows after the insertion; shifted refs resolve to the same module semantics (C2PSA/C3k2 P3/P4/P5); OBB head signature unchanged. It caught a real copy error (fork row 4 had C3k2 [256] where baseline is [512, False, 0.25]) which is now corrected. Exact params/GFLOPs are confirmed on the VM via model.info() before training (Entry 6 pattern).
- Metrics of record for the pair: mAP50, mAP50-95 and `iou_mean` (matched-box IoU on val, overall + per class, conf >= 0.25), per the lead (Section 6). Precision/recall still logged as diagnostics.
- Ballpark-read guide (what each outcome means for the next move): baseline+2 ~ baseline => depth is not the lever, steer to width/attention or data work; baseline+2 clearly beats baseline => depth helps, pull depth-plus2-mid or deeper registry rows; if the gain tracks scale_wider's param class at half the GFLOPs, depth is the better capacity vehicle and combining depth with the attention swap (rows 6/8 C2PSA) is the next test.
- Status: spec v10. Next: VM validation of both yamls (model.info), then train the pair sequentially on the A100, then IoU eval + result report.
- Addendum (VM validation done 2026-09-08): both yamls build cleanly on the VM (ultralytics 8.4.142, same env as batch 1). Measured params: baseline_obb 2,695,747; depth_plus2_deep 3,876,419 (+1.18M, NOT the ~21.3M estimate - the n-scale width factor 0.25 scales the yaml channel args, so each added Conv [1024] is 256 effective channels, ~0.59M params each). GFLOPs readout unavailable via model.info() in this ultralytics build (returns None); est. ~7.5 total (+~0.95). Section 5c cost cells corrected to measured values. Driver + IoU eval scripts pushed to VM (/home/pranayp/yolo_ooi/run_batch2_b8.py, iou_eval.py, iou_geometry.py; geometry IoU sanity-tested locally: identical/disjoint/partial/rotated cases + parse_gt + greedy matching all pass). GPU was busy with teammate srikantht's job at push time; launch waits for the A100 to be free (one-at-a-time rule).

---

**Entry 12 — completed 2026-09-08 (batch-2 initial test done: baseline_b8 + depth_plus2_deep, batch 8).**
- Trained sequentially on the A100 (driver vm/run_batch2_b8.py, batch 8, frozen config). baseline_b8 train 413 s, depth_plus2_deep 895 s, ALL RUNS COMPLETE. Artifacts mirrored locally: runs/yolo11/yolo_arch/{baseline_b8,depth_plus2_deep}/{metrics.json, iou_metrics.json, results.csv} (+ best.pt/last.pt on VM).
- Results (batch 8, seed 42, 88 val / 377 instances):

  | exp | params | best_ep | mAP50 | mAP50-95 | P | R | meanIoU | match% |
  |---|---|---|---|---|---|---|---|---|
  | baseline_b8 | 2,695,747 | 90 | 0.2729 | 0.1556 | 0.406 | 0.313 | 0.568 | 37.4 |
  | depth_plus2_deep | 3,876,419 | 74 | 0.2769 | 0.1434 | 0.539 | 0.259 | 0.556 | 38.5 |

- Read: the +2-conv depth probe is effectively a NULL result. mAP50 flat (+0.004), and the lead's metrics BOTH edge negative: mAP50-95 -0.012, matched-mean-IoU -0.012 (0.568 -> 0.556). depth_plus2 got more precise (P 0.406 -> 0.539) but less sensitive (R 0.313 -> 0.259); it converges earlier (best_ep 90 -> 74) and finds fewer boxes, so both IoU and mAP50-95 (which reward localization + recall) dip. Depth is NOT the lever here -> per the Section 5c ballpark guide, steer to width/attention or data work, not more backbone depth.
- Cross-reference sanity: baseline_b8 (batch 8) mAP50 0.2729 / mAP50-95 0.1556 vs batch-1 baseline (batch 16) 0.2745 / 0.1555 - batch size 8 vs 16 moves almost nothing, so batch-1 numbers ARE usable as cross-reference after all.
- IoU note: matched-mean-IoU ~0.56-0.57 is over only the conf>=0.25 matched boxes (match rate 37-38%); ~62% of GT boxes get no detection at conf 0.25, so recall/match-rate is the real extraction bottleneck, not box accuracy. For the lead's "extract bbox with certainty" framing, the number to move next is recall/match-rate.
- Decision: depth-plus2 = no win, do not pursue more depth; keep in registry as a recorded NULL. Next candidate per batch-1 efficiency winner: attention-backbone + IoU, or address recall (conf threshold / more data / larger imgsz) which is what caps both IoU and mAP50-95.

---

**Entry 13 — 2026-09-08T16:08:42+05:30 — Batch 3 approved: depth-attribution ablation (Arm A type / Arm B location), start small.**
- User decision (2026-09-08): "we will start with arm a and arm b ... start small." Also frames the goal: beyond better/worse results, we keep the learning opportunity - characterizing WHY a change moves (or does not move) the model, and exploring the inner workings.
- Reframe recorded: the batch-2 null conflated fact + TYPE (plain convs) + LOCATION (deepest P5) + DOSE (n-width -> 256ch convs). We do NOT read it as "depth is useless". Control already in hand: C2PSA attention at the deep stages (batch 1) DID help, so the deep stages respond to a new mechanism, not to plain stacked depth. Booked into Registry Section 5d.
- Forks built (both structurally validated, generic validator `experiments/validate_backbone_edit.py`, ALL PASS): `experiments/armA_residual_deep_obb.yaml` (2 x C3k2 [1024, True], insert after row 8) and `experiments/armB_conv_p4_obb.yaml` (2 x Conv [512, 3, 1], insert after row 6). The validator caught a real armB bug before training: the P5 stem row must be Conv [1024, 3, 2] (512 -> 1024), I had written 512.
- Driver `vm/run_batch2_b8.py` refactored to accept run names on argv: `python3 -u run_batch2_b8.py armA_residual_deep armB_conv_p4`. Same frozen config (batch 8, seed 42, 100 ep, patience 50, imgsz 640, lr0 0.01, auto).
- Next: VM param/GFLOPs check of both forks, train sequentially on the A100, then IoU eval (iou_eval.py) on all four (baseline_b8, depth_plus2_deep, armA, armB) to attribute the null to type vs location.
- Status: forks ready locally; VM validation + launch pending (GPU free check first).
---

**Entry 14 — 2026-09-09T09:51:50+05:30 — Batch 3 done: the depth null was LOCATION, not TYPE.**
- Ran the ablation on the A100 (batch 8, frozen config). armA_residual_deep train 457 s, armB_conv_p4 423 s, ALL RUNS COMPLETE. Artifacts mirrored locally (runs/yolo11/yolo_arch/armA_residual_deep, armB_conv_p4) and registry refreshed via experiments/update_registry.py all (9 done rows re-derived from disk, never hand-typed).
- Results (batch 8, seed 42, 88 val / 377 instances):

  | run | params | best_ep | mAP50 | mAP50-95 | P | R | meanIoU | match% |
  |---|---|---|---|---|---|---|---|---|
  | baseline_b8 | 2,695,747 | 90 | 0.2729 | 0.1556 | 0.406 | 0.313 | 0.568 | 37.4 |
  | depth_plus2_deep | 3,876,419 | 74 | 0.2769 | 0.1434 | 0.539 | 0.259 | 0.556 | 38.5 |
  | armA_residual_deep | 3,387,971 | 89 | 0.2678 | 0.1379 | 0.389 | 0.283 | 0.577 | 33.7 |
  | armB_conv_p4 | 2,991,171 | 73 | **0.3096** | 0.1508 | 0.427 | 0.313 | **0.583** | 38.5 |

- **Attribute verdict: LOCATION, not TYPE.**
  - Arm B (plain convs at the P4 stage) is the clear win: mAP50 0.3096 (+0.037 over baseline_b8, the best of the entire batch-2/3 set), matched-IoU 0.583 (+0.015, best measured). This used the SAME plain-conv layer type as the failed depth_plus2_deep - only the placement (higher-res P4 instead of deepest P5) changed.
  - Arm A (residual C3k2 at the deep P5 spot) did NOT rescue it: mAP50 0.2678 (below baseline), mAP50-95 0.1379 (below baseline); IoU 0.577 ~ baseline. Swapping plain convs for residual blocks at the deep spot barely moved mAP -> the failure was the placement, not the layer type.
  - Conclusion: added capacity/features ARE valuable, but only at a resolution the small defects actually route through (P4). At the deepest P5 scale an addition adds ~nothing regardless of module type. Consistent with the small-object hypothesis (Bubble On 123 / On Edge / Extraneous live at small scales; P5/32 at 640 is 20x20).
- **Implication (revises ADR-004):** the earlier "exclude plain depth convs" conclusion is too broad. Depth at P4 is worth keeping and pursuing. Candidate consolidated backbone: attention (rows 6/8 C2PSA) + SPPF k7 + a P4-stage feature block (armB-style).
- Decision: keep armA (recorded null - residual at deep P5) and armB (win, new direction). Next: design the P4-depth-inclusive consolidated variant, or push the P4-depth axis further. Report + stop for user review.

---

---

**Entry 19 — 2026-09-11 — YOLO26 detect entries moved out, two of them corrected (VM verification).**

- The four YOLO26 detect entries that had been appended here (Entry 15 LR comparison, Entry 16 lead meeting on feature concatenation, Entry 17 FeatConcat V1/V2, Entry 18 multiclass baseline) now live in `reports/yolo26/yolo26_arch_experiments_spec.md`, the log for that line.
- Two of them were corrected the same day, after read-only verification against the VM's own artifacts:
  - The arms labelled "auto LR" and "fixed LR 1e-4" were BOTH trained by `optimizer=auto`, which in ultralytics 8.4.142 ignores `lr0` (trainer log: `ignoring 'lr0=0.0001'`, then `AdamW(lr=0.002)`). Measured from `runs/crop_repro/*/results.csv`, both sat at lr 0.000636364 at epoch 1 and peaked at 0.00194, matching at every sampled epoch through 80; the only realised difference was the decay tail plus one arm early-stopping at epoch 87 vs 100. The comparison is void as run, so the crop LR question is still open.
  - FeatConcat V1 contained no head edit at all (its head rows are the stock YOLO26 head), V2's only real edit added raw upsampled P5 rather than a P3 skip, and both additionally dropped `end2end`/`reg_max` (head rebuilt at reg_max=16 with no one2one branch, params 2693491/2726259 against the control's 2504190), used the legacy activated SPPF row, and trained from scratch against a pretrained control. Recorded as UNATTRIBUTABLE.
- Evidence, the full change list (C1-C43) and the required re-runs (R1-R3): `reports/yolo26/DOC_CORRECTIONS_20260911.md` and `experiments/registry.json` (`pending_reruns`).
- The IoU ceiling and defect-scale findings from Entry 15 are unaffected: they rest on the crop runs, which changed nothing but LR arguments.
- This spec remains the YOLO11 OBB source of truth (see the Section 1 scope note).
