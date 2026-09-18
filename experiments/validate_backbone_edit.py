# -*- coding: utf-8 -*-
"""Generic structural validator for a baseline_obb.yaml fork that inserts N rows at position P.

Checks (torch-free):
1. Fork backbone = baseline[0..P] + exactly `new_rows` + baseline[P+1..].
2. Head row count unchanged; every absolute routing ref shifts by +N when it points past P,
   else unchanged; refs resolve to the same module semantics.
3. OBB head signature unchanged: [[a,b,c], 1, OBB, [nc, 1]] with a/b/c = the shifted branch rows.
Exact params/GFLOPs are confirmed on the VM with model.info()/parameter count.
"""
import sys
import yaml

BASE = "experiments/baseline_obb.yaml"

# (fork, insert_after_row_P, N, expected_new_rows, matcher_label)
CASES = [
    ("experiments/armA_residual_deep_obb.yaml", 8, 2,
     [[-1, 1, "C3k2", [1024, True]], [-1, 1, "C3k2", [1024, True]]], "armA_residual_deep"),
    ("experiments/armB_conv_p4_obb.yaml", 6, 2,
     [[-1, 1, "Conv", [512, 3, 1]], [-1, 1, "Conv", [512, 3, 1]]], "armB_conv_p4"),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    return d["backbone"], d["head"], d["nc"], d["scales"]


bb, hd, nc, sc = load(BASE)
fails = 0
for fork, P, N, new_rows, label in CASES:
    fbb, fhd, fnc, fsc = load(fork)
    print("=" * 80)
    print("VALIDATE:", label, " (insert %d row(s) after baseline row %d)" % (N, P))
    bad = []
    def chk(cond, msg):
        print(("  PASS  " if cond else "  FAIL  ") + msg)
        if not cond:
            bad.append(msg)
    chk(nc == fnc == 80, "nc == 80")
    chk(sc == fsc, "scales block identical")
    chk(len(fbb) == len(bb) + N, "backbone rows %d -> %d" % (len(bb), len(bb) + N))
    chk(fbb[:P + 1] == bb[:P + 1], "rows 0..%d identical to baseline" % P)
    chk(fbb[P + 1:P + 1 + N] == new_rows, "rows %d..%d == expected new rows" % (P + 1, P + N))
    chk(fbb[P + 1 + N:] == bb[P + 1:], "tail rows identical to baseline rows %d.." % (P + 1))
    chk(len(fhd) == len(hd), "head row count unchanged")
    # head routing refs: shift by +N when ref > P, else unchanged
    def refs(row):
        head = row[0]
        if isinstance(head, int):
            return []
        return [x for x in head if isinstance(x, int) and x >= 0]
    for i, (br, fr) in enumerate(zip(hd, fhd)):
        want = [r if r <= P else r + N for r in refs(br)]
        got = refs(fr)
        body_ok = br[1:] == fr[1:]
        refs_ok = (refs(br) == [] and refs(fr) == []) or got == want
        chk(body_ok and refs_ok, "head row %d body identical, refs %s -> %s"
            % (i, refs(br) if refs(br) else "-", got if got else "-"))
        if not (body_ok and refs_ok):
            break
    full_b = bb + hd
    full_f = fbb + fhd
    # semantic resolution: baseline branch rows (16,19,22=curr) -> fork (16+N,19+N,22+N) same module
    for b_i, f_i in ((10, 12), (13, 15), (16, 18), (19, 21), (22, 24)):
        chk(full_b[b_i][2] == full_f[f_i][2],
            "fork idx %d (was %d) -> same module %s" % (f_i, b_i, full_f[f_i][2]))
    last = fhd[-1]
    chk(last[0] == [16 + N, 19 + N, 22 + N] and last[1] == 1 and last[2] == "OBB" and last[3] == ["nc", 1],
        "OBB head = [[%d, %d, %d], 1, OBB, [nc, 1]]" % (16 + N, 19 + N, 22 + N))
    print("  => %s: %s" % (label, "PASS" if not bad else "FAIL"))
    if bad:
        fails += 1

print("=" * 80)
if fails:
    print("TOTAL: %d FORK(S) FAILED" % fails)
    sys.exit(1)
print("TOTAL: ALL FORKS PASS")
