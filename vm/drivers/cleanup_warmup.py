#!/usr/bin/env python3
"""Remove the duplicate mangled warmup line."""

FILE = '/home/pranayp/model_training.py'

with open(FILE) as f:
    lines = f.readlines()

# Find and remove the mangled line (starts with "# Warmup:" but contains "if args.warmup:" on same line)
cleaned = []
for line in lines:
    if '# Warmup:' in line and 'if args.warmup:' in line:
        continue  # skip mangled line
    cleaned.append(line)

removed = len(lines) - len(cleaned)
with open(FILE, 'w') as f:
    f.writelines(cleaned)

print(f'Removed {removed} mangled line(s)')
