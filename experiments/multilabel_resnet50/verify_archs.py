#!/usr/bin/env python3
"""Build every architecture in train.py and prove the port is faithful.

Three independent checks, in order:

1. Module arithmetic. The parameter count of each architecture's own modules
   (three Inception/SE blocks, the decode path, the head) is computed here from the
   notebook's filter dictionaries by explicit formula and compared against the sum
   of the built modules' parameters. That is a separate arithmetic path to the same
   numbers, so a wrong filter count or a forgotten bias shows up.
2. Totals against the Keras reference. The four architectures were already built in
   Keras for the 22-class CNN line and those counts are on record. Rebuilding them
   for 5 classes changes only the final Dense (delta 17,425), and two framework
   accounting differences are predictable and cancelling:
     - the shared torchvision trunk (one constant, cancels in every delta);
     - Keras counts BatchNorm moving_mean/moving_var as weights (4 per channel),
       PyTorch keeps them as buffers (2 per channel), so every BN outside the trunk
       reads 2 * channels lower here. Printed, not fudged.
3. Structure. Logits (batch, 5); the three taps are the residual Add outputs at
   28x28x512, 14x14x1024 and 7x7x2048; the fusion tensor is 3584 channels at 14x14.

No ImageNet weights are downloaded (weights=None): this is a structure check.
Run it wherever torch is installed:
    python3 experiments/multilabel_resnet50/verify_archs.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import train as T  # noqa: E402

import torch  # noqa: E402
import torchvision  # noqa: E402

# Keras counts from reports/cnn/CNN_6arch_results_20260915.md (22-class heads).
KERAS_22 = {
    "resnet50": 25_716_630,
    "resnet50_inception": 58_547_094,
    "resnet50_se": 50_544_246,
    "resnet50_inception_attention": 58_744_051,
    "resnet50_inception_refine": 45_988_758,
}
HEAD_DELTA = (1024 * 22 + 22) - (1024 * 5 + 5)          # final Dense, 22 classes -> 5
BN_EXTRA_CHANNELS = {                                   # BN channels each arch adds
    T.ARCH_MULTISCALE: 2048,                            # outside the shared trunk
    T.ARCH_MULTILVL_ATTENTION: 2048,
    T.ARCH_INCEPTION_ATTENTION: 2048,
    T.ARCH_INCEPTION_REFINE: 4096,                       # the refined decode has two
}
HEAD_BN_CHANNELS = T.FUSION_CHANNELS                     # same in all four, cancels
INCEPTION_ARCHS = (T.ARCH_MULTISCALE, T.ARCH_INCEPTION_ATTENTION, T.ARCH_INCEPTION_REFINE)
KERAS_TRUNK_DIFF = 25_636_712 - 25_557_032               # Keras vs torchvision ResNet50
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print("  %-56s %s %s" % (name, "PASS" if ok else "FAIL", detail))


def inc_params(c_in, f, attention):
    """Parameters of one Inception block straight from the notebook's filter dict."""
    p = c_in * f["branch1"] + f["branch1"]                              # 1x1
    p += c_in * f["branch2_reduce"] + f["branch2_reduce"]                # 1x1
    p += f["branch2_reduce"] * f["branch2_out"] * 9 + f["branch2_out"]   # 3x3
    p += c_in * f["branch3_reduce"] + f["branch3_reduce"]                # 1x1
    p += f["branch3_reduce"] * f["branch3_out"] * 25 + f["branch3_out"]  # 5x5
    p += c_in * f["branch4_out"] + f["branch4_out"]                      # pool + 1x1
    if attention:
        for c in (f["branch1"], f["branch2_out"], f["branch3_out"], f["branch4_out"]):
            p += (c * (c // 16) + c // 16) + ((c // 16) * c + c)         # SE on the branch
    return p


def sum_params(module):
    return sum(p.numel() for p in module.parameters())


def expected_blocks(attention):
    return sum(inc_params(T.TAP_CHANNELS[key], T.INC_FILTERS[key], attention)
               for key in ("l3", "l4", "l5"))


DECODE_TRANSPOSED = 2048 * 2048 * 4 + 2048 + 2 * 2048                  # conv-transpose + BN
DECODE_REFINED = 2048 * 9 + 2 * 2048 + 2048 * 2048 + 2 * 2048          # depthwise+BN, 1x1+BN
SE_TAPS = sum((c * (c // 16) + c // 16) + ((c // 16) * c + c) for c in (512, 1024, 2048))
HEAD = ((T.FUSION_CHANNELS * 2048 + 2048) + (2048 * 1024 + 1024) + (1024 * 5 + 5)
        + 2 * T.FUSION_CHANNELS)


def build(arch):
    return T.build_model(torch, torchvision, "none", len(T.LP_TAGS), arch).eval()


print("torch %s torchvision %s" % (torch.__version__, torchvision.__version__))

print("\n[1] module arithmetic (hand count against the built modules)")
params = {arch: T.count_params(build(arch)) for arch in T.ARCHS}
for arch in INCEPTION_ARCHS:
    model = build(arch)
    blocks = sum_params(model.i3) + sum_params(model.i4) + sum_params(model.i5)
    want_blocks = expected_blocks(arch == T.ARCH_INCEPTION_ATTENTION)
    check("%s Inception blocks" % arch, blocks == want_blocks, "%d" % want_blocks)
    check("%s head (GAP-BN-2048-1024-5)" % arch, sum_params(model.head) == HEAD, "%d" % HEAD)
    want_decode = DECODE_REFINED if arch == T.ARCH_INCEPTION_REFINE else DECODE_TRANSPOSED
    check("%s decode path" % arch, sum_params(model.up5) == want_decode, "%d" % want_decode)
model_se = build(T.ARCH_MULTILVL_ATTENTION)
check("%s tap SE blocks" % T.ARCH_MULTILVL_ATTENTION,
      sum_params(model_se.se3) + sum_params(model_se.se4) + sum_params(model_se.se5) == SE_TAPS,
      "%d" % SE_TAPS)
check("Architecture 3 adds SE inside every branch",
      expected_blocks(True) - expected_blocks(False) == 196_957,
      "+%d" % (expected_blocks(True) - expected_blocks(False)))
MODULES = {
    T.ARCH_RESNET50: 2048 * 5 + 5,
    T.ARCH_MULTISCALE: expected_blocks(False) + DECODE_TRANSPOSED + HEAD,
    T.ARCH_MULTILVL_ATTENTION: SE_TAPS + DECODE_TRANSPOSED + HEAD,
    T.ARCH_INCEPTION_ATTENTION: expected_blocks(True) + DECODE_TRANSPOSED + HEAD,
    T.ARCH_INCEPTION_REFINE: expected_blocks(False) + DECODE_REFINED + HEAD,
}
TRUNK = params[T.ARCH_RESNET50] - (2048 * 5 + 5)      # torchvision resnet50, no classifier
print("  torchvision trunk without the classifier: %d" % TRUNK)
for arch in T.ARCHS:
    check("%s total == trunk + own modules" % arch, params[arch] == TRUNK + MODULES[arch],
          "%d = %d + %d" % (params[arch], TRUNK, MODULES[arch]))

print("\n[2] totals against the Keras reference of the 22-class line")
print("  Keras counts a BatchNorm as 4 params per channel, torch as 2 (the rest are buffers).")
print("  %-30s %13s %13s %10s" % ("architecture", "torch", "keras@5cls", "residue"))
residues = set()
for arch in INCEPTION_ARCHS:
    keras5 = KERAS_22[arch] - HEAD_DELTA
    residue = keras5 - params[arch] - 2 * (BN_EXTRA_CHANNELS[arch] + HEAD_BN_CHANNELS)
    residues.add(residue)
    print("  %-30s %13d %13d %10d" % (arch, params[arch], keras5, residue))
check("one shared Keras-vs-torch trunk residue across the four",
      len(residues) == 1 and residues == {KERAS_TRUNK_DIFF}, str(sorted(residues)))
check("residue is the documented ResNet50 accounting difference",
      residues == {KERAS_TRUNK_DIFF},
      "Keras 25,636,712 - torchvision 25,557,032 = %d" % KERAS_TRUNK_DIFF)
base = T.ARCH_MULTISCALE
for arch in (T.ARCH_MULTILVL_ATTENTION, T.ARCH_INCEPTION_ATTENTION, T.ARCH_INCEPTION_REFINE):
    keras_delta = KERAS_22[arch] - KERAS_22[base]
    # torch(k) = keras(k) - trunk - bn_shortfall(k), so the delta subtracts the
    # difference in BN shortfall: an arch with more BN layers reads lower, not higher.
    bn_adj = 2 * (BN_EXTRA_CHANNELS[arch] - BN_EXTRA_CHANNELS[base])
    got = params[arch] - params[base]
    check("delta %s - multiscale" % arch, got == keras_delta - bn_adj,
          "%d (Keras %d, BN -%d)" % (got, keras_delta, bn_adj))
plain = torchvision.models.resnet50(weights=None)
plain.fc = torch.nn.Linear(2048, len(T.LP_TAGS))
check("baseline == torchvision resnet50 with Linear(2048, 5)",
      params[T.ARCH_RESNET50] == T.count_params(plain), "%d" % params[T.ARCH_RESNET50])

print("\n[3] structure on a 224x224 input (eval mode)")
x = torch.randn(2, 3, 224, 224)
for arch in T.ARCHS:
    model = build(arch)
    with torch.no_grad():
        y = model(x)
    check("%s logits shape" % arch, tuple(y.shape) == (2, len(T.LP_TAGS)), str(tuple(y.shape)))
for arch in INCEPTION_ARCHS + (T.ARCH_MULTILVL_ATTENTION,):
    model = build(arch)
    with torch.no_grad():
        taps = model.taps(x)
    shapes = [tuple(t.shape[1:]) for t in taps]
    check("%s taps 512/1024/2048 at 28/14/7" % arch,
          shapes == [(512, 28, 28), (1024, 14, 14), (2048, 7, 7)], str(shapes))
    check("%s taps use the residual-add hook" % arch, model.taps.used_hooks, T.taps_mode(model))
for arch in INCEPTION_ARCHS:
    model = build(arch)
    seen = []
    original = model.head.forward

    def spy(t, _original=original, _sink=seen):
        _sink.append(tuple(t.shape[1:]))
        return _original(t)
    model.head.forward = spy
    with torch.no_grad():
        model(x)
    model.head.forward = original
    check("%s fusion tensor 3584x14x14" % arch, seen and seen[0] == (3584, 14, 14), str(seen))

print("\n%d checks, %d failed" % (len(checks), sum(1 for _, ok, _ in checks if not ok)))
for name, ok, detail in checks:
    if not ok:
        print("  FAILED: %s %s" % (name, detail))
sys.exit(1 if any(not ok for _, ok, _ in checks) else 0)
