---
title: Message for the lead, MultiScale against the baseline
date: 2026-09-29
type: report
status: active
where: reports/multilabel/teams_message_baseline_vs_multiscale_20260929.md
---

# Message for the lead

Written 2026-09-29, not yet sent. Numbers verified against the runs (75-check recompute) and
carried in the workbook below. Short version, written to be pasted into Teams as it stands.

## The message

MultiScale (architecture 1) result, compared with the baseline.

Same data both times: 3,377 lens presentation images, the same frozen 80/20 split (2,700
train, 677 test), the same recipe, the same seed, one model at a time on the same GPU.

| Test set, 677 images | Baseline | MultiScale |
|---|---|---|
| Macro AUPRC | 0.905 | 0.862 |
| Macro F1 | 0.808 | 0.774 |
| Folded Lens recall | 0.056 (2 of 36) | 0.000 |
| Folded Lens F1 | 0.103 | 0.000 |
| Folded Lens AUPRC | 0.523 | 0.496 |
| Training, 50 epochs | 8.3 min | 10.9 min |
| Inference per image, no warmup | 3.29 ms | 3.40 ms |

Four of the five classes are at or near a perfect score in both models. The only class that
fails is Folded Lens, and MultiScale is worse on it rather than better: every one of the 36
Folded Lens images scores below zero, so no threshold reaches the class. More capacity made
that output more confidently negative, not less.

Why Folded Lens will read 0 for every architecture, not just this one. In the annotation
export Folded Lens never appears on its own: all 178 Folded Lens pictures also carry Multiple
Lenses, and 111 of them (62 per cent) carry a further class the model has no output for (Lens
Off Center on 57 per cent, Dirty Camera on 11 per cent). So the model is asked to spot a
folded lens inside pictures that are already off centre and sometimes dirty, with no output in
which to say so, while the Multiple Lenses output explains those images well enough on its
own. The export also holds 1,264 Multiple Lenses pictures without Folded Lens, so a folded
lens is either very rare and subtle or not labelled in some of them, and no architecture
repairs a wrong negative. The data does not separate the two conditions for the model.

That is why the remaining three architectures will also land on 0 for this class, and why the
levers left are in the loss and in the data rather than in the architecture. I will test the
remaining architectures and send the same table for each one. The full comparison for these
two is attached.

## What backs it

- Workbook: `reports/multilabel/FMD_MultiLabel_Baseline_vs_MultiScale_20260929.xlsx`
  (baseline and MultiScale side by side, every class, the Folded Lens detail including the
  picture profile from the annotation export, timing, figures, method).
- Baseline is the plain ResNet50 run of 2026-09-28 already reported. It was repeated on
  2026-09-29 inside the MultiScale session so that training and inference time could be
  measured the same way on the same device; the workbook carries both, and Folded Lens recall
  is at the floor in either column (2 of 36 in the first run, 0 of 36 in the repeat), so the
  answer does not depend on which baseline column is read.
- MultiScale is architecture 1 of the architecture notebook, rebuilt faithfully for the
  training framework in use: 58.4 million parameters against 23.5 million, every filter count
  and head layer the notebook's, with the final layer emitting 5 independent scores because
  the task is multi-label.
- The Folded Lens picture profile is read from the annotation export directly by
  `experiments/multilabel_resnet50/folded_lens_tag_profile.py`, and its counts agree with the
  annotation audit tables produced independently on 2026-09-23.
- Same data, same frozen 80/20 split, same recipe, same seed, one model at a time on the
  A100. Record: `reports/multilabel/ml_arch_sweep_20260929.md`.
