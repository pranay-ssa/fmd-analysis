# -*- coding: utf-8 -*-
"""Structural validator v2: baseline_obb.yaml vs depth_plus2_deep_obb.yaml (torch-free).

Invariant under test: fork == baseline with exactly 2 rows `Conv [1024, 3, 1]`
inserted immediately after the final C3k2[1024] backbone row (base index 8),
before SPPF (base index 9). All head routing references that point at rows
>= insertion point shift by +2; refs to rows 4/6 (before the insert) stay.
Exact params/GFLOPs still require ultralytics model.info() on the VM.
"""
import sys
import yaml

BASE = "experiments/baseline_obb.yaml"
FORK = "experiments/depth_plus2_deep_obb.yaml"

def load(p):
    with open(p, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d["backbone"], d["head"], d["nc"], d["scales"]

bb, hd, nc, sc = load(BASE)
fbb, fhd, fnc, fsc = load(FORK)
INS = 8  # base index of the final C3k2[1024]; convs are inserted right after it

errs = []
def chk(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        errs.append(msg)

chk(nc == fnc == 80, "nc == 80 in both")
chk(sc == fsc, "scales block identical (n only)")
chk(len(bb) == 11 and len(fbb) == 13, "backbone rows 11 -> 13 (+2)")

# 1) backbone: prefix identical, two Conv[1024,3,1] at 9/10, tail identical to base[9:]
chk(fbb[:INS + 1] == bb[:INS + 1], "fork rows 0..8 identical to baseline")
chk(fbb[INS + 1][2] == "Conv" and fbb[INS + 1][3] == [1024, 3, 1],
    "row 9 = new Conv [1024, 3, 1] (depth +1)")
chk(fbb[INS + 2][2] == "Conv" and fbb[INS + 2][3] == [1024, 3, 1],
    "row 10 = new Conv [1024, 3, 1] (depth +2)")
chk(fbb[INS + 3:] == bb[INS + 1:],
    "rows 11..12 (SPPF k5, C2PSA) identical to baseline rows 9..10")

# 2) head: same length; every absolute ref shifts +2 unless it points before the insert (rows 4, 6)
chk(len(hd) == len(fhd), "head row count unchanged (%d)" % len(hd))

def refs(row):
    head = row[0]
    if isinstance(head, int):  # plain [-1, ...] rows carry no absolute refs
        return []
    return [x for x in head if isinstance(x, int) and x >= 0]

def shift(r):
    return r if r <= INS else r + 2

for i, (br, fr) in enumerate(zip(hd, fhd)):
    same_body = br[1:] == fr[1:]  # repeat count, module name, args
    want_refs = [shift(r) for r in refs(br)]
    got_refs = refs(fr)
    # non-routing rows have no refs; routing rows must match expected shifted refs
    ok_refs = (refs(br) == [] and refs(fr) == []) or (got_refs == want_refs)
    chk(same_body and ok_refs,
        "head row %d body identical, refs %s -> %s" % (i, refs(br) if refs(br) else "-", got_refs if got_refs else "-"))
    if not (same_body and ok_refs):
        break

# 3) semantic resolution in the fork: shifted refs land on the same module kinds as in base
full_b = bb + hd
full_f = fbb + fhd
for b_i, f_i in ((10, 12), (13, 15), (16, 18), (19, 21), (22, 24)):
    chk(full_b[b_i][2] == full_f[f_i][2],
        "fork index %d (was %d) resolves to same module %s" % (f_i, b_i, full_f[f_i][2]))

# 4) OBB head signature untouched
last = fhd[-1]
chk(last[0] == [18, 21, 24] and last[1] == 1 and last[2] == "OBB" and last[3] == ["nc", 1],
    "OBB head row = [[18, 21, 24], 1, OBB, [nc, 1]]")

print()
if errs:
    print("STRUCTURAL VALIDATION: %d FAILURE(S)" % len(errs))
    sys.exit(1)
print("STRUCTURAL VALIDATION: ALL CHECKS PASS")
