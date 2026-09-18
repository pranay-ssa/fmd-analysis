#!/bin/bash
# FMD Crop Mode Test — VM Setup Script
# ======================================
#
# This script sets up the environment on the VM to run the crop mode test.
# Run this ONCE after copying files to the VM.

set -e  # Exit on error

echo "=========================================="
echo "FMD Crop Mode Test — VM Setup"
echo "=========================================="

# Check Python version
echo ""
echo "Checking Python..."
python3 --version || { echo "ERROR: Python3 not found. Install Python 3.8+"; exit 1; }

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install numpy pillow scipy || { echo "ERROR: Failed to install dependencies"; exit 1; }

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "import numpy; import PIL; import scipy; print('All dependencies OK')"

# Check data directory
DATA_DIR="${1:-/home/amd100-user/FMD_Data_26082026/fmd_temp_images/ICube Defects Library}"
OUTPUT_DIR="${2:-/home/pranayp/fmd_crop_output}"

echo "Input directory: $DATA_DIR"
echo "Output directory: $OUTPUT_DIR"
if [ -d "$DATA_DIR" ]; then
    CLASS_COUNT=$(ls -d "$DATA_DIR"/*/ 2>/dev/null | wc -l)
    echo "Found $CLASS_COUNT class folders"
else
    echo "WARNING: Data directory not found at $DATA_DIR"
    echo "Please ensure your data is at: $DATA_DIR/<Class>/*.bmp"
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "Usage:"
echo "  python3 test_crop_modes_vm.py --all"
echo ""
echo "Or test specific classes:"
echo "  python3 test_crop_modes_vm.py --class \"Wet Package\" \"Fiber\""
echo ""
echo "Default paths:"
echo "  Input:  /home/amd100-user/FMD_Data_26082026/fmd_temp_images/ICube Defects Library"
echo "  Output: /home/pranayp/fmd_crop_output"
echo "=========================================="
