"""Answer, from the source export, what Folded Lens images actually carry.

Parses data/Updated Annotations 20260922.xml exactly as build_labels.py does (image
elements, child tags with a label attribute) and reports the full tag set of every
Folded Lens picture, the same view for Multiple Lenses pictures that are not Folded
Lens, and the folder each sits in. Read only.

    python folded_lens_tag_profile.py
"""
import collections
# stdlib ElementTree is deliberate and safe here: the input is our own CVAT export
# (data/Updated Annotations 20260922.xml), a local trusted file, never third-party
# input, and this is the same parser the repo's label builder uses. No entity
# expansion is performed on external input.
import xml.etree.ElementTree as ET
from pathlib import Path

XML = Path("data/Updated Annotations 20260922.xml")
NAME = {
    "P1_COC": "Cavity Off Center", "P1_FL": "Folded Lens", "P1_ML": "Multiple Lenses",
    "P1_MPP": "Missing Primary Package", "P1_NL": "Missing Lens",
    "P2_LOC": "Lens Off Center", "P2_DC": "Dirty Camera", "P2_DS": "Dirty Strobe",
    "P2_HMO": "HEMA Obstruction", "P2_LD": "Low Dose Obstructing ROI", "P2_BSC": "Bubble Scatter",
    "P1_PPM": "Package Misalignment", "P2_FOV": "View Obstructed",
}
P1 = ["P1_COC", "P1_FL", "P1_ML", "P1_MPP", "P1_NL"]

root = ET.parse(XML).getroot()
images = []
for img in root.findall("image"):
    tags = sorted({c.get("label") for c in img if c.tag == "tag" and c.get("label")})
    boxes = sorted({c.get("label") for c in img if c.tag == "box" and c.get("label")})
    images.append({"name": img.get("name", ""), "tags": set(tags), "boxes": set(boxes)})

print("images in the export: %d" % len(images))
all_labels = collections.Counter(t for im in images for t in im["tags"])
print("distinct tag labels: %d -> %s" % (len(all_labels), sorted(all_labels)))

fl = [im for im in images if "P1_FL" in im["tags"]]
ml_only = [im for im in images if "P1_ML" in im["tags"] and "P1_FL" not in im["tags"]]
print("\nFolded Lens pictures: %d" % len(fl))
print("Multiple Lenses pictures without Folded Lens: %d" % len(ml_only))

print("\n=== what else do the 178 Folded Lens pictures carry ===")
other = collections.Counter()
for im in fl:
    if not im["tags"] - {"P1_FL"}:
        other["nothing else at all"] += 1
    else:
        other[" + ".join(sorted(im["tags"] - {"P1_FL"}))] += 1
for combo, n in other.most_common():
    print("  %-58s %3d  (%.0f%%)" % (combo, n, 100.0 * n / len(fl)))

print("\n=== per tag, how often it sits on a Folded Lens picture ===")
print("  %-32s %8s %10s %12s" % ("tag", "on FL", "on ML only", "FL rate"))
for t in sorted(all_labels):
    if t == "P1_FL":
        continue
    a = sum(1 for im in fl if t in im["tags"])
    b = sum(1 for im in ml_only if t in im["tags"])
    print("  %-32s %8d %10d %11.0f%%" % ("%s (%s)" % (NAME.get(t, t), t), a, b, 100.0 * a / len(fl)))

print("\n=== how many pictures carry another tag besides the 5 model tags ===")
extra_all = [im for im in images if im["tags"] - set(P1)]
print("  whole export: %d of %d" % (len(extra_all), len(images)))
print("  of the 178 Folded Lens: %d (%.0f%%)" % (
    sum(1 for im in fl if im["tags"] - {"P1_FL"}), 100.0 * sum(1 for im in fl if im["tags"] - {"P1_FL"}) / len(fl)))
print("  of the %d Multiple Lenses without Folded Lens: %d (%.0f%%)" % (
    len(ml_only), sum(1 for im in ml_only if im["tags"] - set(P1)),
    100.0 * sum(1 for im in ml_only if im["tags"] - set(P1)) / len(ml_only)))

print("\n=== which folder do the Folded Lens pictures sit in ===")
for folder, n in collections.Counter(
        "/".join(im["name"].split("/")[:-1]) for im in fl).most_common():
    print("  %-60s %3d" % (folder, n))

print("\n=== box annotations on Folded Lens pictures (object level) ===")
print("  pictures with any box: %d" % sum(1 for im in fl if im["boxes"]))
for label, n in collections.Counter(b for im in fl for b in im["boxes"]).most_common():
    print("  %-40s %3d" % (label, n))

print("\n=== model label space check: how many P1 tags per Folded Lens picture ===")
dist = collections.Counter(len(im["tags"] & set(P1)) for im in fl)
for k in sorted(dist):
    print("  %d of the 5 model tags: %d pictures" % (k, dist[k]))
