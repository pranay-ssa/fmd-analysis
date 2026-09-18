# FMD Crop Mode Test — VM Instructions

## VM Details

| Field | Value |
|-------|-------|
| VM name | vm-amd-a100 |
| User | pranayp |
| IP | 20.253.232.255 |
| Data path | `/home/amd100-user/FMD_Data_26082026/fmd_temp_images/ICube Defects Library/` |
| Output path | `/home/pranayp/fmd_crop_output/` |

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
