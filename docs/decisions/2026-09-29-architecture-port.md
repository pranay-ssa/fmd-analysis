---
title: The notebook architectures are built on the torchvision ResNet50 trunk, with a 5-score final layer
date: 2026-09-29
type: decision
status: active
where: docs/decisions/2026-09-29-architecture-port.md
---

# Architecture source and final layer

## Decision

The four architectures in `notebooks/FMD_ResNet50Architectures.ipynb` were rebuilt inside
`experiments/multilabel_resnet50/train.py` on the same torchvision ResNet50 trunk that the
2026-09-28 baseline uses, behind a single `--arch` flag. The training framework is not
changed and no second framework is introduced.

The rebuilt architectures keep every filter count, branch tap, fusion width, decode path
and fully connected head of the notebook. The final layer is the only deliberate
difference: it emits 5 independent scores under `BCEWithLogitsLoss`, instead of the
notebook's softmax over its class count, because one image can carry several lens
presentation tags.

## Why the trunk is shared rather than rebuilt

The alternative was to follow the notebook literally, including its own ResNet50 body and
its own initialisation. That would have made the five sweep rows differ in two ways at once,
architecture and initialisation, and the experiment exists to isolate the architecture. The
notebook's forward path starts from the same ImageNet-initialised ResNet50 features in both
frameworks, so building the four architectures on the torchvision trunk removes the second
variable and costs nothing in fidelity: the pieces the notebook adds (Inception branches at
three depth levels, squeeze-and-excitation, the decode paths, the head) are all built
exactly as written.

## Why the final layer differs

The notebook solves a single-label problem, so it ends in a softmax and its output width is
its class count. This task is multi-label: the 5 tags are not exclusive (Folded Lens never
appears without Multiple Lenses in this export, and 178 images carry two tags). A softmax
over the 5 tags would force a false choice between them. The head is therefore kept exactly
as the notebook writes it up to the last layer, and the last layer is `Linear(*, 5)` with no
softmax.

## How the fidelity claim is backed

Fidelity is a parameter count check plus a structure check, both in `verify_archs.py`
(38 checks, 0 failed on the VM):

1. Every module's parameter count is recomputed from the notebook's own filter dictionary
   and compared against the built module, so the arithmetic is done twice by different
   routes.
2. Totals are compared against the same architectures as built earlier in the notebook's
   own framework for the 22-class CNN line. The two frameworks differ by one accounting
   rule: one counts BatchNorm moving statistics as weights (4 per channel) and the other
   keeps them as buffers (2 per channel). The shortfall per architecture was computed by
   hand and matches exactly, and the shared trunk cancels out of every pairwise comparison.
3. Structure: logits shape `(batch, 5)`, fusion tensor 3,584 channels at 14x14, and the
   three taps resolve to the notebook's pre-activation residual add layers (not the
   post-activation stage outputs), checked after a real forward pass.

## Consequence

Four of the five sweep rows are the notebook's architectures and one is the plain ResNet50
control. Because the trunk is shared and the initialisation is ImageNet weights in every
row, any difference between rows is attributable to the architecture that was added on top
of the trunk and to nothing else, subject to the run-to-run band the control re-run
measured (macro F1 0.037 on the same config and seed in a new session).
