"""
FMD Preprocess Configuration
=============================

Central configuration for the ROI-Crop pipeline. This file contains:
1. Per-class margin settings (multi-size mode)
2. Single-size mode margin (normalizing to max)
3. Core algorithm constants (threshold, blob filters, etc.)

CROP MODES
----------
MULTI-SIZE (--multi-size):
  Uses per-class margins derived from EDA clearance analysis (2026-08-28).
  Each defect class gets a margin that ensures all bounding boxes fit
  within the crop with sufficient clearance.

SINGLE-SIZE (--single-size):
  Uses a fixed margin of 120px for ALL classes, regardless of class.
  This normalizes the crop window to the maximum required margin.
  Trade-off: larger crops = more black border retained = larger file sizes.

MARGIN RATIONALE (from EDA findings)
------------------------------------
- Fiber: 120px (fibers extend ~106px beyond blob at 45px margin)
- HEMA Fragment: 80px (boxes up to 63px past blob at 45px margin)
- Wet Package: 80px (1 image had box 63px past blob at 45px margin)
- All others: 45px (min clearances 49.6-289.2px, safe at default)

USAGE
-----
    from config import get_margin, CROP_MODE, PIPELINE_CONSTANTS

    # For multi-size mode:
    margin = get_margin(class_name="Fiber", mode="multi-size")  # returns 120

    # For single-size mode:
    margin = get_margin(class_name="Fiber", mode="single-size")  # returns 120
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# CROP MODE CONSTANTS
# ---------------------------------------------------------------------------

# Single-size mode: normalize ALL classes to this margin
SINGLE_SIZE_MARGIN: int = 120

# Default margin for classes not in the per-class map
DEFAULT_MARGIN: int = 45

# Per-class margin overrides (multi-size mode)
# Derived from EDA clearance analysis on 2026-08-28
PER_CLASS_MARGINS: Dict[str, int] = {
    "Fiber": 120,
    "HEMA Fragment": 80,
    "Wet Package": 80,
}

# Fixed per-class crop size (W, H) for single-size mode (120px border).
# p99 of single-size crop dims across data/incoming, rounded up to 4 (2026-09-03).
PER_CLASS_CROP_SINGLE: Dict[str, tuple[int, int]] = {
    "Bubble": (1560, 1532),
    "Bubble Cluster": (1596, 1584),
    "Bubble Irregular": (1556, 1524),
    "Bubble On 123": (1540, 1540),
    "Bubble On Edge": (1564, 1564),
    "Bubble Scatter": (1548, 1516),
    "Cavity Off Center": (1704, 1564),
    "Dirty Camera": (1876, 1716),
    "Dirty Strobe": (1572, 1788),
    "Extraneous Polymer": (1576, 1524),
    "Fiber": (1560, 1528),
    "Foreign Matter": (1556, 1784),
    "HEMA Fragment": (1544, 1520),
    "HEMA Obstruction": (1584, 1532),
    "Lens Off Center": (1580, 1560),
    "Low Dose Obstructing Region of Interest": (1548, 1528),
    "Missing Lens": (1544, 1524),
    "Missing Primary Package": (1520, 1516),
    "Multiple Lenses": (1592, 1592),
    "Package Misalignment": (2020, 2048),
    "View Obstructed": (1496, 1296),
    "Wet Package": (1552, 1540),
}

# Fixed per-class crop size (W, H) for multi-size mode (tight per-class margin).
# p99 of multi-size crop dims across data/incoming, rounded up to 4 (2026-09-03).
PER_CLASS_CROP_MULTI: Dict[str, tuple[int, int]] = {
    "Bubble": (1412, 1380),
    "Bubble Cluster": (1444, 1432),
    "Bubble Irregular": (1404, 1372),
    "Bubble On 123": (1392, 1388),
    "Bubble On Edge": (1412, 1416),
    "Bubble Scatter": (1396, 1368),
    "Cavity Off Center": (1556, 1416),
    "Dirty Camera": (1732, 1564),
    "Dirty Strobe": (1420, 1672),
    "Extraneous Polymer": (1424, 1376),
    "Fiber": (1560, 1528),
    "Foreign Matter": (1408, 1668),
    "HEMA Fragment": (1464, 1440),
    "HEMA Obstruction": (1432, 1384),
    "Lens Off Center": (1432, 1408),
    "Low Dose Obstructing Region of Interest": (1400, 1376),
    "Missing Lens": (1396, 1376),
    "Missing Primary Package": (1372, 1364),
    "Multiple Lenses": (1440, 1440),
    "Package Misalignment": (1872, 1992),
    "View Obstructed": (1344, 1144),
    "Wet Package": (1472, 1460),
}

# No-loss guard: pad around detected content when the fixed window can't contain it.
CONTENT_MARGIN: int = 45

# Fallback canonical for classes not in the maps above (should not occur).
DEFAULT_CROP_SINGLE: tuple[int, int] = (1560, 1532)
DEFAULT_CROP_MULTI: tuple[int, int] = (1440, 1440)

# ---------------------------------------------------------------------------
# CORE ALGORITHM CONSTANTS (from preprocess.py)
# These are NOT changed by crop mode - they define the blob detection logic.
# ---------------------------------------------------------------------------

THRESHOLD: int = 3              # "lit" pixel cutoff (0-255). Fixed on purpose.
MIN_BLOB_SIZE: int = 500        # px. Biggest known noise blob: 84. Object: 1.26M.
MIN_BLOB_MEAN: float = 15.0     # mean intensity. Noise streaks: ~5-7. Object: ~60.
RECOVERY_BLOB_MEAN: float = 13.0  # tier-2 fallback mean floor for dim-but-real content.
MIN_CONTENT_ROWS: int = 100     # blank-frame guard: fewer -> declare image failed.
BORDER_ASSERT_FRAC: float = 0.005  # >0.5% lit pixels in discarded ring -> warning.

PIPELINE_VERSION: str = "ROI-Crop 1.1.0"

# Output file format
OUTPUT_FORMAT: str = ".bmp"     # Keep BMP for calibration integrity

# Supported input formats
INPUT_EXTENSIONS: set = {".bmp", ".tif", ".tiff", ".png"}


# ---------------------------------------------------------------------------
# MARGIN LOOKUP FUNCTION
# ---------------------------------------------------------------------------

def get_margin(class_name: str, mode: str = "multi-size") -> int:
    """
    Get the crop margin for a given class and mode.

    Args:
        class_name: Defect class name (must match folder name exactly)
        mode: Either "multi-size" or "single-size"

    Returns:
        Margin in pixels

    Raises:
        ValueError: If mode is not recognized
    """
    if mode == "single-size":
        return SINGLE_SIZE_MARGIN
    elif mode == "multi-size":
        return PER_CLASS_MARGINS.get(class_name, DEFAULT_MARGIN)
    else:
        raise ValueError(f"Unknown crop mode: {mode}. Use 'multi-size' or 'single-size'.")


def get_crop_size(class_name: str, mode: str = "single-size") -> tuple[int, int]:
    """Fixed crop window (W, H) for a class and mode.

    mode 'single-size' -> PER_CLASS_CROP_SINGLE; 'multi-size' -> PER_CLASS_CROP_MULTI.
    Unknown class falls back to DEFAULT_CROP_SINGLE / DEFAULT_CROP_MULTI.
    """
    if mode == "single-size":
        return PER_CLASS_CROP_SINGLE.get(class_name, DEFAULT_CROP_SINGLE)
    elif mode == "multi-size":
        return PER_CLASS_CROP_MULTI.get(class_name, DEFAULT_CROP_MULTI)
    else:
        raise ValueError(f"Unknown crop mode: {mode}. Use 'multi-size' or 'single-size'.")


def get_mode_description(mode: str) -> str:
    """Return a human-readable description of the crop mode."""
    if mode == "single-size":
        return f"Single-size: fixed {SINGLE_SIZE_MARGIN}px margin for all classes"
    elif mode == "multi-size":
        desc = "Multi-size: per-class margins\n"
        desc += f"  Default: {DEFAULT_MARGIN}px\n"
        for cls, m in sorted(PER_CLASS_MARGINS.items()):
            desc += f"  {cls}: {m}px\n"
        return desc
    else:
        return f"Unknown mode: {mode}"


# ---------------------------------------------------------------------------
# MANIFEST SCHEMA
# ---------------------------------------------------------------------------

MANIFEST_COLUMNS = [
    "file", "status", "left", "top", "width", "height",
    "right", "bottom",                      # derived: right=left+width-1, bottom=top+height-1 (inclusive pixels)
    "orig_width", "orig_height",
    "blobs_total", "blobs_kept", "largest_blob_px",
    "border_lit_frac", "pipeline_version", "processed_at_utc",
    "crop_mode", "margin_used", "recovered",      # NEW: recovery tier tag ('', 'tier2_blob13', 'tier3_center')
]


# ---------------------------------------------------------------------------
# ALL KNOWN DEFECT CLASSES (for validation)
# ---------------------------------------------------------------------------

ALL_DEFECT_CLASSES = [
    "Bubble",
    "Bubble Cluster",
    "Bubble Irregular",
    "Bubble On 123",
    "Bubble On Edge",
    "Bubble Scatter",
    "Cavity Off Center",
    "Dirty Camera",
    "Dirty Strobe",
    "Extraneous Polymer",
    "Fiber",
    "Foreign Matter",
    "HEMA Fragment",
    "HEMA Obstruction",
    "Lens Off Center",
    "Low Dose Obstructing Region of Interest",
    "Missing Lens",
    "Missing Primary Package",
    "Multiple Lenses",
    "Package Misalignment",
    "View Obstructed",
    "Wet Package",
]
