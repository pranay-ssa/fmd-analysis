#!/usr/bin/env python3
"""Validate yolo26_feat_concat_v2.yaml structure locally (no GPU needed)."""
import yaml, sys
from pathlib import Path

yaml_path = Path(__file__).parent.parent / "experiments" / "yolo26" / "yolo26_feat_concat_v2.yaml"
with open(yaml_path) as f:
    cfg = yaml.safe_load(f)

backbone = cfg.get("backbone", [])
head = cfg.get("head", [])
all_layers = backbone + head

print(f"Backbone layers: {len(backbone)}")
print(f"Head layers: {len(head)}")
print(f"Total layers: {len(all_layers)}")

# Check every referenced index is valid
errors = []
for i, layer in enumerate(all_layers):
    from_ref = layer[0]  # first element is the "from" reference
    if isinstance(from_ref, list):
        for ref in from_ref:
            if isinstance(ref, int) and ref >= i:
                errors.append(f"Row {i}: references future row {ref}")
            if isinstance(ref, int) and ref < -1:
                errors.append(f"Row {i}: invalid reference {ref}")
    elif isinstance(from_ref, int):
        if from_ref >= i and from_ref != -1:
            errors.append(f"Row {i}: references future row {from_ref}")
        if from_ref < -1:
            errors.append(f"Row {i}: invalid reference {from_ref}")

# Check Detect layer references valid rows
detect_rows = [i for i, l in enumerate(all_layers) if l[2] in ("Detect", "OBB")]
for dr in detect_rows:
    refs = all_layers[dr][0]
    if isinstance(refs, list):
        for r in refs:
            if r >= len(all_layers):
                errors.append(f"Row {dr} (Detect): references row {r} but only {len(all_layers)} layers exist")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("\nAll references valid.")
    # Print layer summary
    for i, layer in enumerate(all_layers):
        from_ref = layer[0]
        n_repeat = layer[1]
        module = layer[2]
        args = layer[3]
        print(f"  {i:2d}  from={str(from_ref):20s}  {module:12s}  args={args}")
