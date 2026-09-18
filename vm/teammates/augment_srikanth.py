"""
ICube Defects Library - synthetic augmentation preview generator.

Generates a SAMPLE of augmented images into a separate preview folder
(never touches the original class folders or any train/test split) so
they can be visually inspected before being adopted into training data.

Part A - applied to a sample of images from ALL 22 classes (OOI + LP):
    1. Horizontal flip
    2. Vertical flip / 180 degree rotation
    3. Brightness jitter
    4. Contrast jitter
    5. Gamma correction
    6. Gaussian noise
    7. Mild Gaussian blur
    8. Mild scale / zoom jitter
    9. Mild vignetting perturbation

Part B - cut-paste pipeline, OOI classes only, using the real bounding
boxes in `Object of Interest Tag/annotations.xml`:
    10. Select the image
    11. Mark the defect region   (rotated bbox -> mask, from annotations.xml)
    12. Remove the defect        (mask cut out of the original)
    13. Inpaint the defect region (cv2.inpaint, Telea)
    14. Reinsert the defect      (cv2.seamlessClone, original position AND
                                   a mildly jittered position)

Two OOI classes (Bubble Scatter, HEMA Obstruction) have no boxes at all
in annotations.xml, so only Part A runs for them; this is logged in the
manifest/README.
"""

import os
import random
import hashlib
import csv
import xml.etree.ElementTree as ET

import cv2
import numpy as np

random.seed(42)
np.random.seed(42)

ROOT = "/home/srikantht/ICube Defects Library"
OOI_DIR = os.path.join(ROOT, "Object of Interest Tag")
LP_DIR = os.path.join(ROOT, "Lens Presentation Tag")
ANNOT_XML = os.path.join(OOI_DIR, "annotations.xml")
OUT_DIR = os.path.join(ROOT, "Augmented_Preview")

SAMPLES_PER_CLASS = 4
JITTER_FRAC = 0.08  # fraction of image width/height for cut-paste reinsert jitter

# Classical inpainting (cv2.inpaint / Telea) breaks down on very large defect
# regions that cross structural lens-edge boundaries (verified visually: Fiber
# boxes averaging >300x300px produce smeared triangular artifacts). Above this
# fraction of the image area, skip remove/inpaint/reinsert and only emit the
# mark overlay - these classes (mainly Fiber, HEMA Fragment, and rare large
# outliers in other classes) need a deep-learning inpainter (LaMa/DeepFillv2),
# which is out of scope for this preview pass.
MAX_INPAINT_AREA_FRAC = 0.02

IMG_EXTS = (".bmp", ".png", ".jpg", ".jpeg")

OOI_CLASSES = [
    "Bubble", "Bubble Cluster", "Bubble Irregular", "Bubble On 123",
    "Bubble On Edge", "Bubble Scatter", "Extraneous Polymer", "Fiber",
    "Foreign Matter", "HEMA Fragment", "HEMA Obstruction", "Wet Package",
]
LP_CLASSES = [
    "Cavity Off Center", "Dirty Camera", "Dirty Strobe", "Lens Off Center",
    "Low Dose Obstructing Region of Interest", "Missing Lens",
    "Missing Primary Package", "Multiple Lenses", "Package Misalignment",
    "View Obstructed",
]

manifest_rows = []


def log(tag_group, cls, source_image, technique, output_path, note=""):
    manifest_rows.append({
        "tag_group": tag_group,
        "class": cls,
        "source_image": source_image,
        "technique": technique,
        "output_path": os.path.relpath(output_path, OUT_DIR) if output_path else "",
        "note": note,
    })


def list_images(folder):
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(IMG_EXTS))


def sample_images(folder, n, seed_key):
    files = list_images(folder)
    rng = random.Random(seed_key)
    if len(files) <= n:
        return files
    return rng.sample(files, n)


# ---------------------------------------------------------------------------
# Part A: universal photometric / geometric augmentations
# ---------------------------------------------------------------------------

def aug_hflip(img, rng):
    return cv2.flip(img, 1)


def aug_vflip180(img, rng):
    return cv2.rotate(img, cv2.ROTATE_180)


def aug_brightness(img, rng):
    beta = rng.uniform(15, 30) * rng.choice([-1, 1])
    return cv2.convertScaleAbs(img, alpha=1.0, beta=beta)


def aug_contrast(img, rng):
    alpha = rng.uniform(0.85, 1.20)
    return cv2.convertScaleAbs(img, alpha=alpha, beta=0)


def aug_gamma(img, rng):
    gamma = rng.uniform(0.8, 1.25)
    inv = 1.0 / gamma
    lut = np.array([((i / 255.0) ** inv) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(img, lut)


def aug_gauss_noise(img, rng):
    sigma = rng.uniform(5, 10)
    noise = np.random.normal(0, sigma, img.shape).astype(np.float32)
    out = img.astype(np.float32) + noise
    return np.clip(out, 0, 255).astype(np.uint8)


def aug_gauss_blur(img, rng):
    k = rng.choice([3, 5])
    return cv2.GaussianBlur(img, (k, k), 0)


def aug_scale_zoom(img, rng):
    factor = rng.uniform(1.05, 1.15)
    h, w = img.shape[:2]
    resized = cv2.resize(img, (int(w * factor), int(h * factor)), interpolation=cv2.INTER_LINEAR)
    rh, rw = resized.shape[:2]
    top = (rh - h) // 2
    left = (rw - w) // 2
    return resized[top:top + h, left:left + w]


def aug_vignette(img, rng):
    h, w = img.shape[:2]
    strength = rng.uniform(0.15, 0.30)
    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2.0, w / 2.0
    max_r = np.sqrt(cx ** 2 + cy ** 2)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_r
    mask = 1.0 - strength * (r ** 2)
    out = img.astype(np.float32) * mask
    return np.clip(out, 0, 255).astype(np.uint8)


PART_A_TECHNIQUES = [
    ("hflip", aug_hflip),
    ("vflip180", aug_vflip180),
    ("brightness", aug_brightness),
    ("contrast", aug_contrast),
    ("gamma", aug_gamma),
    ("gauss_noise", aug_gauss_noise),
    ("gauss_blur", aug_gauss_blur),
    ("scale_zoom", aug_scale_zoom),
    ("vignette", aug_vignette),
]


def run_part_a(tag_group, cls, src_dir, out_root):
    files = sample_images(src_dir, SAMPLES_PER_CLASS, seed_key=f"{tag_group}/{cls}")
    for fname in files:
        stem = os.path.splitext(fname)[0]
        img = cv2.imread(os.path.join(src_dir, fname), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img_out_dir = os.path.join(out_root, cls, stem)
        os.makedirs(img_out_dir, exist_ok=True)

        orig_path = os.path.join(img_out_dir, "original.png")
        cv2.imwrite(orig_path, img)
        log(tag_group, cls, fname, "original", orig_path)

        rng = random.Random(hashlib.md5(fname.encode()).hexdigest())
        for name, fn in PART_A_TECHNIQUES:
            out_img = fn(img, rng)
            out_path = os.path.join(img_out_dir, f"{name}.png")
            cv2.imwrite(out_path, out_img)
            log(tag_group, cls, fname, name, out_path)


# ---------------------------------------------------------------------------
# Part B: cut-paste pipeline for OOI classes (uses annotations.xml boxes)
# ---------------------------------------------------------------------------

def load_annotations(xml_path):
    """Return dict: image basename -> list of box dicts (largest box first isn't
    guaranteed; caller picks representative box)."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    by_name = {}
    for im in root.findall("image"):
        name = im.attrib["name"]
        base = os.path.basename(name)
        boxes = []
        for b in im.findall("box"):
            boxes.append({
                "label": b.attrib["label"],
                "xtl": float(b.attrib["xtl"]),
                "ytl": float(b.attrib["ytl"]),
                "xbr": float(b.attrib["xbr"]),
                "ybr": float(b.attrib["ybr"]),
                "rotation": float(b.attrib.get("rotation", 0.0)),
            })
        if boxes:
            by_name[base] = boxes
    return by_name


def rotated_rect_mask(shape, box, dilate_frac=0.25):
    """Build a filled mask for a CVAT rotated box, dilated by dilate_frac of
    its own size to leave room for inpainting/blending."""
    h, w = shape[:2]
    cx = (box["xtl"] + box["xbr"]) / 2.0
    cy = (box["ytl"] + box["ybr"]) / 2.0
    bw = (box["xbr"] - box["xtl"]) * (1.0 + dilate_frac)
    bh = (box["ybr"] - box["ytl"]) * (1.0 + dilate_frac)
    angle = box["rotation"]
    rect = ((cx, cy), (bw, bh), angle)
    pts = cv2.boxPoints(rect).astype(np.int32)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillConvexPoly(mask, pts, 255)
    return mask, (cx, cy), (bw, bh)


def largest_box(boxes):
    def area(b):
        return (b["xbr"] - b["xtl"]) * (b["ybr"] - b["ytl"])
    return max(boxes, key=area)


def run_part_b(cls, src_dir, out_root, boxes_by_name):
    files = sample_images(src_dir, SAMPLES_PER_CLASS, seed_key=f"cutpaste/{cls}")
    for fname in files:
        boxes = boxes_by_name.get(fname)
        if not boxes:
            continue  # no annotation for this particular sampled file
        box = largest_box(boxes)

        stem = os.path.splitext(fname)[0]
        img = cv2.imread(os.path.join(src_dir, fname), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        h, w = img.shape[:2]
        img_out_dir = os.path.join(out_root, cls, stem)
        os.makedirs(img_out_dir, exist_ok=True)

        # 11. Mark the defect region
        mask, (cx, cy), (bw, bh) = rotated_rect_mask(img.shape, box)
        overlay = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        overlay[mask > 0] = (0, 0, 255)
        overlay = cv2.addWeighted(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), 0.6, overlay, 0.4, 0)
        mark_path = os.path.join(img_out_dir, "cutpaste_01_mark.png")
        cv2.imwrite(mark_path, overlay)
        log("Object of Interest Tag", cls, fname, "cutpaste_mark", mark_path)

        area_frac = cv2.countNonZero(mask) / float(h * w)
        if area_frac > MAX_INPAINT_AREA_FRAC:
            log("Object of Interest Tag", cls, fname, "cutpaste_SKIPPED_too_large", "",
                note=f"defect covers {area_frac*100:.2f}% of image (> {MAX_INPAINT_AREA_FRAC*100:.0f}% "
                     "threshold) - classical inpainting fails at this size, needs deep inpainting")
            continue

        # 12. Remove the defect (visualize as blacked-out region)
        removed = img.copy()
        removed[mask > 0] = 0
        removed_path = os.path.join(img_out_dir, "cutpaste_02_removed.png")
        cv2.imwrite(removed_path, removed)
        log("Object of Interest Tag", cls, fname, "cutpaste_removed", removed_path)

        # 13. Inpaint the defect region
        inpainted = cv2.inpaint(img, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
        inpaint_path = os.path.join(img_out_dir, "cutpaste_03_inpainted.png")
        cv2.imwrite(inpaint_path, inpainted)
        log("Object of Interest Tag", cls, fname, "cutpaste_inpainted", inpaint_path)

        # extract the defect patch (axis-aligned crop around the dilated
        # rotated box) and its mask, for seamlessClone
        x0 = max(int(cx - bw / 2) - 2, 0)
        x1 = min(int(cx + bw / 2) + 2, w)
        y0 = max(int(cy - bh / 2) - 2, 0)
        y1 = min(int(cy + bh / 2) + 2, h)
        if x1 - x0 < 3 or y1 - y0 < 3:
            continue
        patch = img[y0:y1, x0:x1]
        patch_mask = mask[y0:y1, x0:x1]

        # 14. Reinsert the defect (feathered alpha blend, not Poisson/seamlessClone:
        # verified that cv2.seamlessClone silently discards very small defects -
        # e.g. Bubble On 123 boxes are ~7x7 px - because the Poisson solver has no
        # stable solution for such tiny masks; alpha feathering is robust at any size)
        ph, pw = patch_mask.shape
        alpha = cv2.GaussianBlur(patch_mask.astype(np.float32) / 255.0, (7, 7), 0)

        def alpha_paste(bg, cx_paste, cy_paste):
            px0 = int(round(cx_paste - pw / 2.0))
            py0 = int(round(cy_paste - ph / 2.0))
            px0 = int(np.clip(px0, 0, w - pw))
            py0 = int(np.clip(py0, 0, h - ph))
            out = bg.copy()
            roi = out[py0:py0 + ph, px0:px0 + pw].astype(np.float32)
            blended = alpha * patch.astype(np.float32) + (1 - alpha) * roi
            out[py0:py0 + ph, px0:px0 + pw] = blended.astype(np.uint8)
            return out

        # 14a. Reinsert at the original position (sanity-check reconstruction)
        reins_orig = alpha_paste(inpainted, cx, cy)
        p1 = os.path.join(img_out_dir, "cutpaste_04_reinsert_original_pos.png")
        cv2.imwrite(p1, reins_orig)
        log("Object of Interest Tag", cls, fname, "cutpaste_reinsert_original_pos", p1)

        # 14b. Reinsert at a mildly jittered position -> genuinely new sample
        rng = random.Random(hashlib.md5(fname.encode()).hexdigest())
        dx = int(rng.uniform(-JITTER_FRAC, JITTER_FRAC) * w)
        dy = int(rng.uniform(-JITTER_FRAC, JITTER_FRAC) * h)
        cxj = cx + dx
        cyj = cy + dy
        reins_jit = alpha_paste(inpainted, cxj, cyj)
        p2 = os.path.join(img_out_dir, "cutpaste_05_reinsert_jittered_pos.png")
        cv2.imwrite(p2, reins_jit)
        log("Object of Interest Tag", cls, fname, "cutpaste_reinsert_jittered_pos", p2,
            note=f"dx={dx},dy={dy}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ooi_out = os.path.join(OUT_DIR, "Object of Interest Tag")
    lp_out = os.path.join(OUT_DIR, "Lens Presentation Tag")
    os.makedirs(ooi_out, exist_ok=True)
    os.makedirs(lp_out, exist_ok=True)

    print("Loading annotations.xml ...")
    boxes_by_name = load_annotations(ANNOT_XML)
    print(f"  {len(boxes_by_name)} images have >=1 box")

    print("\n=== Part A: universal augmentations, all 22 classes ===")
    for cls in LP_CLASSES:
        src = os.path.join(LP_DIR, cls)
        print(f"  [LP] {cls}")
        run_part_a("Lens Presentation Tag", cls, src, lp_out)
    for cls in OOI_CLASSES:
        src = os.path.join(OOI_DIR, cls)
        print(f"  [OOI] {cls}")
        run_part_a("Object of Interest Tag", cls, src, ooi_out)

    print("\n=== Part B: cut-paste pipeline, OOI classes with boxes ===")
    classes_with_boxes = sorted({b["label"] for boxes in boxes_by_name.values() for b in boxes})
    print(f"  classes with box annotations: {classes_with_boxes}")
    skipped = [c for c in OOI_CLASSES if c not in classes_with_boxes]
    print(f"  OOI classes with NO box annotations (Part A only): {skipped}")
    for cls in OOI_CLASSES:
        if cls not in classes_with_boxes:
            continue
        src = os.path.join(OOI_DIR, cls)
        print(f"  [cutpaste] {cls}")
        run_part_b(cls, src, ooi_out, boxes_by_name)

    manifest_path = os.path.join(OUT_DIR, "manifest.csv")
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["tag_group", "class", "source_image", "technique", "output_path", "note"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"\nManifest written: {manifest_path} ({len(manifest_rows)} rows)")

    readme_path = os.path.join(OUT_DIR, "README.txt")
    with open(readme_path, "w") as f:
        f.write(
            "ICube Defects Library - Augmentation PREVIEW folder\n"
            "====================================================\n"
            "This folder is generated by augment_pipeline.py for visual inspection only.\n"
            "Nothing here has been added to any train/test split or the original class folders.\n\n"
            f"Samples per class: {SAMPLES_PER_CLASS} (deterministic random sample, seed=42)\n\n"
            "Part A (9 universal techniques) was applied to a sample from ALL 22 classes:\n"
            "  hflip, vflip180, brightness, contrast, gamma, gauss_noise, gauss_blur, scale_zoom, vignette\n"
            "Each sampled source image gets its own subfolder containing original.png + the 9 variants.\n\n"
            "Part B (5-step cut-paste pipeline) was applied only to OOI classes that have real bounding\n"
            "box annotations in 'Object of Interest Tag/annotations.xml':\n"
            f"  {classes_with_boxes}\n"
            f"OOI classes with NO annotated boxes (Part A only, no cut-paste): {skipped}\n\n"
            "For images with multiple annotated boxes, the LARGEST box was used as the representative\n"
            "defect for the cut-paste demo (to keep the preview readable) - full-scale generation would\n"
            "process every box.\n\n"
            f"Defects covering more than {int(MAX_INPAINT_AREA_FRAC*100)}% of the image area get ONLY the\n"
            "cutpaste_01_mark.png step - remove/inpaint/reinsert are skipped (see manifest.csv note\n"
            "'cutpaste_SKIPPED_too_large'). This was added after visually confirming that cv2.inpaint\n"
            "(Telea) produces smeared triangular artifacts on very large defects that cross the lens'\n"
            "curved structural edges (seen clearly on a Fiber sample). Fiber and HEMA Fragment are mostly\n"
            "affected since their boxes average 300x300px+; a deep-learning inpainter (LaMa/DeepFillv2)\n"
            "would be needed for those classes - out of scope for this preview.\n\n"
            "Cut-paste outputs per image (in the same per-image subfolder as the Part A variants):\n"
            "  cutpaste_01_mark.png                 - defect region highlighted in red\n"
            "  cutpaste_02_removed.png               - defect region blacked out\n"
            "  cutpaste_03_inpainted.png             - background reconstructed with cv2.inpaint (Telea)\n"
            "  cutpaste_04_reinsert_original_pos.png - defect pasted back at its original location\n"
            "                                          (feathered alpha blend) - sanity check\n"
            f"  cutpaste_05_reinsert_jittered_pos.png - defect pasted at a small random offset (+/-{int(JITTER_FRAC*100)}%\n"
            "                                          of image width/height) - this is the actual new\n"
            "                                          synthetic training sample\n\n"
            "See manifest.csv for the full list of generated files with source image and technique.\n"
        )
    print(f"README written: {readme_path}")


if __name__ == "__main__":
    main()
