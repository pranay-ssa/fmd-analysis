# FMD Crop Mode Test — VM Instructions

## VM Details

| Field | Value |
|-------|-------|
| VM name | vm-amd-a100 |
| User | pranayp |
| IP | 20.253.232.255 |
| Data path | `/home/amd100-user/FMD_Data_26082026/fmd_temp_images/ICube Defects Library/` |
| Output path | `/home/pranayp/fmd_crop_output/` |

## Running experiments here (updated 2026-09-21)

This is the box meant by "my box" or "our VM": the a100 box. Everything that trains runs here.

| Field | Value |
|-------|-------|
| Access from the work laptop | `ssh -o BatchMode=yes amd-a100-vm`. The Windows ssh-agent service holds the key, so there is no passphrase prompt. MSYS ssh cannot see that agent |
| You land as | `amd100-user` |
| Run work as | `sudo -n -u pranayp -H /usr/bin/python3.12 <script.py>` |
| Python | ultralytics 8.4.142 and torch 2.6.0+cu124 sit in pranayp's user site only. `/usr/bin/python3` has neither |
| GPU | one A100 80GB. Check `nvidia-smi` before launching, and do not disturb another run's output |
| Detection set we train on | `/home/pranayp/yolo_ooi/` with `dataset_obb/` (boxes as rotated corners), `dataset_multiclass/` (boxes as upright rectangles, plus `data.yaml`), `runs/`, `yolo26n.pt` |
| Crops | `/home/pranayp/fmd_crop_output/single-size_fixed_crop/<Class>_20260903/<stem>_crop.bmp` with the matching `.txt` |
| Raw frames | `/data/FMD_Data_26082026/fmd_temp_images/`, read only |

Usual detection settings, from `run_yolo26_multiclass.py`: YOLO26n, 100 epochs, imgsz 1280, batch 8,
patience 50, seed 42. About 566 s across the 346 pictures we use.

Three traps in this data, each of which cost a round trip:

- **Crop names drop the score fields.** `20241106_185031_L24_C15_9521_0.9778_0.5263.bmp` in the
  folder record is `20241106_185031_L24_C15_9521_crop.bmp` on the box.
- **Some pictures carry a longer pallet named variant instead**, so a name may not match at all.
  Match on the timestamp and line prefix and require the match to be unique before using it.
- **Only the ten boxed classes have label files.** A tag class folder holds bitmaps and no `.txt`,
  so a folder count is not a labelled count.

## Quick Start

### 1. SSH into VM
```bash
ssh pranayp@20.253.232.255
# Use key file: pranayp-vm-amd-a100-keyfile
```

### 2. Copy script to VM
```bash
# From local machine:
scp vm/test_crop_modes_vm.py pranayp@20.253.232.255:/home/pranayp/
scp vm/setup_vm.sh pranayp@20.253.232.255:/home/pranayp/
```

### 3. Setup environment
```bash
ssh pranayp@20.253.232.255
chmod +x setup_vm.sh
./setup_vm.sh
```

### 4. Run the test
```bash
# Test all classes (uses default paths):
python3 test_crop_modes_vm.py --all

# Test specific classes:
python3 test_crop_modes_vm.py --class "Wet Package" "Fiber" "Bubble"

# Custom paths (if needed):
python3 test_crop_modes_vm.py --all \
  --input-base /home/amd100-user/FMD_Data_26082026/fmd_temp_images/ICube\ Defects\ Library \
  --output-base /home/pranayp/fmd_crop_output
```

## Output Structure

```
/home/pranayp/fmd_crop_output/
├── multi_size_crop/
│   ├── Bubble_20260901/
│   ├── Fiber_20260901/
│   ├── Wet Package_20260901/
│   └── ... (22 classes)
├── single_size_crop/
│   ├── Bubble_20260901/
│   ├── Fiber_20260901/
│   ├── Wet Package_20260901/
│   └── ... (22 classes)
└── crop_mode_comparison_20260901.json
```

## What It Does

1. **Multi-size mode**: Uses per-class margins
   - Fiber: 120px
   - HEMA Fragment: 80px
   - Wet Package: 80px
   - All others: 45px

2. **Single-size mode**: Fixed 120px margin for all

3. **Comparison**: Measures file size difference

## Expected Results

From local testing (1,431 images):
- Multi-size: 2.48 GB
- Single-size: 3.00 GB
- Increase: +21.2% (+0.52 GB)

## Files

| File | Purpose |
|------|---------|
| `test_crop_modes_vm.py` | Standalone script (all config embedded) |
| `setup_vm.sh` | Setup script |

## Requirements

- Python 3.8+
- numpy, pillow, scipy
