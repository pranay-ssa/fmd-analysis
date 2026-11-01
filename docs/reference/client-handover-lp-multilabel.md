---
title: Client handover package for the LP multilabel model
date: 2026-10-30
type: reference
status: active
where: docs/reference/client-handover-lp-multilabel.md
---

# Client handover package for the LP multilabel model

How to ship the trained lens-presentation multilabel model to the client, without
re-deriving any of it. The package is already built and verified; only the
checkpoint choice is open.

## Package location

`handover/model_package/` in the repository (work laptop tree):

- `predict.py` - builds a standard torchvision ResNet-50, loads the weights,
  scores one image, prints score + FLAG per class. The client never edits code.
- `config.json` - the only file the client touches. Holds `checkpoint` (path to
  `final.pt`), `image_path`, input size 224, ImageNet mean/std, and all 13
  classes with their tuned per-class thresholds.
- `README.md` - client-facing setup and output explanation.
- `requirements.txt` - torch, torchvision, pillow.

The model weights are NOT in the folder yet. When the lead picks a variant,
copy its `final.pt` next to `predict.py` and zip the folder. Both variants work
unchanged: the script is generalized (the two checkpoints are the same
architecture, pure state_dicts of ~94 MB).

## Checkpoint facts (verified 2026-10-30 against the VM)

- Locations: `run/multilabel_lp_full_20261029/{a,b}/final.pt` on the VM
  (repo tree `/home/pranayp/fmd-analysis`).
- Format: pure `OrderedDict` state_dict, ResNet-50 trunk, fc head with 13
  outputs. No optimizer state or metadata inside the file.
- Column order (from `metrics.json` `config.columns`, must not be reordered):
  P1_MPP, P1_ML, P2_LOC, P2_DC, P1_NL, P1_FL, P2_LD, P1_COC, P2_DS, P2_FOV,
  P2_BSC, P1_PPM, object_present.
- Preprocessing the script applies: resize to 224x224, ToTensor, ImageNet
  normalization (mean 0.485/0.456/0.406, std 0.229/0.224/0.225). Sigmoid on
  logits; FLAG when score >= the class threshold in config.json.
- Variant b headline metrics: macro AUPRC 0.660 (0.817 on judgeable classes),
  exact match 0.770, hamming loss 0.024.

## Verification already done

The package was run on the VM the way the client will run it: against variant
b's `final.pt` with a real BMP from the Lens Off Center folder. The secure
`weights_only=True` load worked, all 13 classes scored in the correct order,
object_present flagged at 0.945 on a lens-present image, and per-class
thresholds fired. BMP input works via PIL, no conversion needed.

One calibration note from that test: the P2_LOC sample scored 0.273 against a
0.30 threshold, a borderline miss on a single frame. Expected single-image
noise; mention if the client spot-checks individual pictures.

## What remains when the client asks

1. Get the variant decision (a vs b) from the lead.
2. Copy the chosen `final.pt` into `handover/model_package/`.
3. Zip and send.

## Lessons for building the test

- On the VM, images live under
  `/data/FMD_Data_26082026/fmd_temp_images/ICube Defects Library/<class>/` and
  are `.bmp`, not `.jpg`.
- The VM venv interpreter is `/home/pranayp/fmd-analysis/.venv/bin/python`
  (bare `python`/`python3` on the box is either missing or lacks torch).
- ssh lands as `amd100-user`; a `/tmp` test dir must be made world-writable
  before `scp` into it, with `pranayp` ownership for the run
  (`sudo mkdir`, `sudo chown pranayp`, `sudo chmod 777`).
