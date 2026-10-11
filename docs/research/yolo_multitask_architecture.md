---
title: YOLO Multi-Task Architecture Research for FMD
date: 2026-10-09
type: report
status: active
where: docs/research/yolo_multitask_architecture.md
---

# YOLO Multi-Task Architecture Research for FMD

> **Purpose**: Investigate whether a single YOLO-based multi-task model can handle both
> object-level defect detection (OOI) and frame-level lens-presentation (LP) classification,
> replacing the current separate-model pipeline on the production line.
>
> **Scope**: Architecture survey of all YOLO-based multi-task approaches, deep source-code
> verification of YOLO-Master MultiTask, and a concrete FMD feasibility assessment.

---

## 1. Executive Summary

The idea of a multi-head YOLO architecture where one head handles classification (D3/D4 metrics)
and another handles detection (D1/D2 metrics) is technically sound and well-supported by the
literature. YOLOR (2021) proved that a single shared representation can serve detection and
multi-label classification simultaneously. YOLO-Master (CVPR 2026, Tencent) is the most
recent implementation, but its classification branch is single-label and requires COCO-format
data, making it unusable for FMD without modification.

**Key finding**: The architecture concepts are directly transferable, but YOLO-Master's
implementation is not production-ready for FMD. A custom dual-head model built on stable
Ultralytics 8.4.142, using the YOLO-Master design principles (shared backbone, task routing,
multi-task loss), is the recommended path.

**Blocking question**: D1, D2, D3, D4 are not defined anywhere in the FMD repository or
knowledge base. The lead must specify what these metrics represent before architecture work
can be finalized.

---

## 2. Background: The FMD Two-Tier Label Problem

FMD inspection produces two fundamentally different label types:

```
+-------------------------------------------------------------+
|                    FMD Label Spaces                         |
+--------------------+----------------------------------------+
|  OOI (Object)      |  LP (Lens Presentation)                |
|  - Bounding boxes  |  - Image-level tags                    |
|  - 10 classes      |  - 5 tags (multi-label)                |
|  - 346/88 split    |  - 3,377+ tagged images                |
|  - YOLO format     |  - COCO-style or folder-per-class      |
|  - Detection task  |  - Classification task                 |
+--------------------+----------------------------------------+
```

**The leakage problem**: Current separate models sometimes confuse LP tags with OOI
classes and vice versa. A shared backbone could help by learning features that are
discriminative for both tasks simultaneously.

**The production goal**: One model that outputs both detection boxes and LP tag
probabilities, replacing the current multi-model pipeline.

---

## 3. Architecture Survey: YOLO-Based Multi-Task Approaches

### 3.1 YOLOR (You Only Learn One Representation, 2021)

**Paper**: Wang et al., "You Only Learn One Representation: Unified Network for Multiple
Tasks", 2021, from the YOLOv4 team.

**Core idea**: Learn a single unified representation by combining **explicit knowledge**
(from data observations) with **implicit knowledge** (learned latents).

**Architecture**:

```
                    +---------------------+
                    |   Input Image       |
                    +----------+----------+
                               |
                    +----------v----------+
                    |   Shared Backbone   |
                    |   (CSPDarknet)      |
                    +----------+----------+
                               |
                    +----------v----------+
                    |   FPN + PAN Neck    |
                    +----------+----------+
                               |
              +----------------+----------------+
              |                |                |
    +---------v------+  +------v------+  +------v-------+
    | Detection Head |  | Seg Head    |  | Classify     |
    | (anchor-based) |  | (instance)  |  | Head         |
    +----------------+  +-------------+  | (multi-label)|
                                         +--------------+
              |                |                |
    +---------v------+  +------v------+  +------v------+
    | Implicit Know. |  | Implicit    |  | Implicit    |
    | (latent space) |  | Knowledge   |  | Knowledge   |
    +----------------+  +-------------+  +-------------+
```

**Three core mechanisms**:

1. **Kernel space alignment**: Aligns feature distributions across tasks via additive or
   multiplicative interactions with an implicit representation.

2. **Prediction refinement**: Injects implicit representations into output layers to adjust
   predictions (e.g., object coordinates, anchor dimensions).

3. **Multi-task learning**: Implicit representations in each task branch enhance the shared
   feature space with task-adaptive signals.

**Results on COCO test-dev**: 55.4% AP at 30 FPS on V100. Multi-task training improved
all tasks compared to single-task training.

**Relevance to FMD**: HIGH. This is the foundational architecture. The multi-label
classification head is directly analogous to our LP tags.

**Limitation**: Code is from 2021, unmaintained, based on older YOLO versions. Would need
significant porting.

### 3.2 YOLO-R (Multi-Task Learning with Implicit Knowledge, 2021)

**Source**: LearnOpenCV summary of YOLO-R from the YOLOv4 team.

**Core finding**: "Features extracted for a specific task are not generalized enough to be
applied to other tasks." Multi-task learning forces the model to learn a generalized
representation.

**Tasks**: Object detection, **multi-label image classification**, and feature embedding.

**Architecture difference from YOLOR**: Uses a single convolutional layer with two
**learnable priors** for kernel space alignment and prediction refinement.

**Relevance to FMD**: HIGH. The multi-label classification + detection combination is
exactly what we need.

**Limitation**: 2021 paper, code quality and maintenance uncertain.

### 3.3 YOLO-P (Palm Oil Detection, 2023)

**What it is**: A modified YOLOv3-tiny with DenseNet backbone for palm oil plantation
detection. "P" stands for "Palm."

**Multi-task?**: NO. Single-task detector.

**Relevance to FMD**: NONE. The teammate likely confused the name with a multi-task
architecture. There is no multi-task YOLO-P.

### 3.4 YOLO-Master MultiTask (Tencent, CVPR 2026, Preview)

This is the most recent and most relevant implementation. Verified against source code.

#### 3.4.1 Model YAML Configuration

File: `ultralytics/cfg/models/26/yolo26-master-mt-n.yaml`

```yaml
nc: 80                                          # number of classes (shared)
end2end: True                                   # one2one + one2many heads
reg_max: 1                                      # DFL bins
kpt_shape: [17, 3]                              # COCO keypoints
nm: 32                                          # mask coefficients
npr: 256                                        # mask prototypes
tasks: ['detect', 'segment', 'pose']             # active supervised tasks

scales:
  n: [0.50, 0.25, 1024]

backbone:
  - [-1, 1, Conv, [64, 3, 2]]                  # 0-P1/2
  - [-1, 1, Conv, [128, 3, 2]]                 # 1-P2/4
  - [-1, 2, C3k2, [256, False, 0.25]]          # 2
  - [-1, 1, Conv, [256, 3, 2]]                 # 3-P3/8
  - [-1, 2, C3k2, [512, False, 0.25]]          # 4
  - [-1, 1, Conv, [512, 3, 2]]                 # 5-P4/16
  - [-1, 2, C3k2, [512, True]]                 # 6
  - [-1, 1, Conv, [1024, 3, 2]]                # 7-P5/32
  - [-1, 2, C3k2, [1024, True]]               # 8
  - [-1, 1, SPPF, [1024, 5, 3, True]]         # 9
  - [-1, 2, C2PSA, [1024]]                    # 10

head:
  # MoT-enhanced neck with C2fMoT blocks
  - [-1, 1, nn.Upsample, [None, 2, "nearest"]]  # 11
  - [[-1, 6], 1, Concat, [1]]                    # 12
  - [-1, 2, C2fMoT, [...]]                       # 13: MoT-adapted P4
  - [-1, 1, nn.Upsample, [None, 2, "nearest"]]  # 14
  - [[-1, 4], 1, Concat, [1]]                    # 15
  - [-1, 2, C2fMoT, [...]]                       # 16: MoT-adapted P3
  - [-1, 1, Conv, [256, 3, 2]]                  # 17
  - [[-1, 13], 1, Concat, [1]]                   # 18
  - [-1, 2, C2fMoT, [...]]                       # 19: MoT-adapted P4
  - [-1, 1, Conv, [512, 3, 2]]                  # 20
  - [[-1, 10], 1, Concat, [1]]                   # 21
  - [-1, 2, C2fMoT, [...]]                       # 22: MoT-adapted P5

  # Unified Multi-Task Head
  - [[16, 19, 22], 1, MultiTaskHead, [nc]]      # 23
```

#### 3.4.2 MultiTaskHead Architecture (from source code)

File: `ultralytics/nn/modules/multitask/head.py`

```
+-------------------------------------------------------------+
|                  MultiTaskHead (extends Detect)             |
|                                                             |
|  Input: [P3, P4, P5] from FPN                               |
|                                                             |
|  +-------------------------------------------------------+  |
|  | TaskRouter (optional)                                  | |
|  |  - Per-token task affinity scores [B, T, H, W]         | |
|  |  - Top-K soft blending (K=2)                           | |
|  |  - Cross-task feature association                      | |
|  +-------------------------------------------------------+  |
|                         |                                   |
|  +----------------------v--------------------------------+  |
|  | Task-specific heads (parallel branches):               | |
|  |                                                        | |
|  |  [1] Detect head (always present)                      | |
|  |      cv2 (box) + cv3 (cls)                             | |
|  |      one2many + one2one branches                       | |
|  |      Output: boxes + scores [B, N, 4+nc]               | |
|  |                                                        | |
|  |  [2] Segment head (optional)                           | |
|  |      Proto26 + cv4_seg                                 | |
|  |      Output: mask coefficients                         | |
|  |                                                        | |
|  |  [3] Pose head (optional)                              | |
|  |      cv4_pose                                          | |
|  |      Output: keypoints [B, max_det, nk]                | |
|  |                                                        | |
|  |  [4] Classify head (optional)                          | |
|  |      AdaptiveAvgPool2d(1)                              | |
|  |      Conv(cls_in, cls_in//2, 1)                        | |
|  |      Flatten + Linear(cls_in//2, nc)                   | |
|  |      Output: class_logits [B, nc]                      | |
|  |                                                        | |
|  |  [5] Depth head (optional)                             | |
|  |      cv4_depth -> [B, 1, H, W]                         | |
|  |                                                        | |
|  |  [6] Normal head (optional)                            | |
|  |      cv4_normal -> [B, 3, H, W]                        | |
|  |                                                        | |
|  |  [7] Semantic head (optional)                          | |
|  |      cv4_semantic -> [B, nc, H, W]                     | |
|  |                                                        | |
|  |  [8] OBB head (COMPATIBILITY ONLY - NOT TRAINABLE)     | |
|  |      Raises ValueError if used                         | |
|  +--------------------------------------------------------+ |
|                                                             |
|  Learnable task_importance: nn.Parameter([num_tasks])       |
+-------------------------------------------------------------+
```

#### 3.4.3 TaskRouter Architecture (from source code)

File: `ultralytics/nn/modules/multitask/router.py`

```
Input: [B, C, H, W]
        |
   +----v------------------------------------+
   | affinity_router (MoT-style)             |
   |   Conv(C, C//8, 1) -> GN -> SiLU        |
   |   -> Conv(C//8, num_tasks, 1)           |
   |   -> [B, num_tasks, H, W]               |
   +----+------------------------------------+
        |
   +----v------------------------------------+
   | Top-K soft blending                     |
   |   top_k=2 (primary + secondary)         |
   |   softmax / temperature                 |
   |   exploration: 0.98*sparse + 0.02*dense |
   +----+------------------------------------+
        |
   +----v------------------------------------+
   | Task feature generation                 |
   |   task_feats = x * affinity             |
   |   -> [B, num_tasks, C, H, W]            |
   +----+------------------------------------+
        |
   +----v------------------------------------+
   | Cross-task association                  |
   |   cross_task_proj(x) -> shared_feats    |
   |   -> [B, shared_C, H, W]                |
   +----+------------------------------------+
        |
   Output: (task_features, shared_features, routing_stats)
```

#### 3.4.4 Training Pipeline (from source code)

File: `ultralytics/models/yolo/multitask/train.py`

```python
# Per-task loss name kits
_TASK_LOSS_NAMES = {
    "detect": ("box_loss", "cls_loss", "dfl_loss"),
    "segment": ("box_loss", "cls_loss", "dfl_loss", "seg_loss"),
    "pose": ("box_loss", "pose_loss", "kobj_loss", "cls_loss", "dfl_loss"),
    "classify": ("cls_global_loss",),
    "depth": ("depth_loss",),
    "normal": ("normal_loss",),
    "semantic": ("semantic_loss",),
}

# Unified loss vector (fixed-width for terminal/log rows)
_UNIFIED_LOSS_NAMES = (
    "box_loss", "cls_loss", "dfl_loss", "seg_loss",
    "pose_loss", "cls_global_loss", "depth_loss",
    "normal_loss", "semantic_loss",
)

# Validation contract: every task needs head + targets + loss + validation evidence
def validate_multitask_contract(data, head):
    # - Rejects 'obb' in tasks (raises ValueError)
    # - Requires 'multitask_format: coco'
    # - Checks head.set_active_tasks() exists
    # - Validates dataset has targets for each enabled task
    # - Classification requires: "cls_img" in label and "cls_img_valid": True
```

#### 3.4.5 Dataset Configuration

File: `ultralytics/cfg/datasets/coco8-multitask.yaml`

```yaml
path: coco8-seg
train: images/train
val: images/val

tasks:
  - detect
  - segment
  - pose
  - classify
  - depth
  - obb          # listed but will raise ValueError at runtime

kpt_shape: [17, 3]
flip_idx: [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]

# Classes (shared across ALL tasks - same nc)
names:
  0: person
  1: bicycle
  # ... 80 COCO classes
```

### 3.5 Generalist YOLO (WACV 2025)

**Architecture**: Unified encoder (GELAN backbone) + primary-secondary co-attention +
efficient prediction heads.

**Tasks**: Object detection, instance segmentation, semantic segmentation, panoptic
segmentation, image captioning.

**Key innovation**: **Gradient masking** determines which features each task can affect,
reducing task conflicts.

**Relevance to FMD**: MEDIUM. The gradient masking idea is interesting for handling LP vs
OI label space conflicts, but the architecture is complex and the task types are different.

### 3.6 Native Ultralytics YOLO26 (Stable)

**Architecture**: Each task (detect, segment, classify, pose, OBB) is a **separate model**
with its own head. No joint multi-task training.

**Classification**: Single-label only (softmax + cross-entropy).

**Relevance to FMD**: LOW for multi-task. But the stable base for building a custom
dual-head model.

### 3.7 YOLOPv2 (Panoptic Driving Perception, 2022)

**Architecture**: Shared encoder + three separate decoder heads (detection, drivable area
segmentation, lane detection).

**Relevance to FMD**: LOW. Domain is autonomous driving, not manufacturing inspection.
The shared-encoder-multiple-decoders pattern is similar but the tasks are not relevant.

---

## 4. Architecture Comparison Matrix

| Architecture  | Year | Detection | Multi-Label Cls | Joint Train | Maturity    | FMD Fit |
|---------------|------|-----------|-----------------|-------------|-------------|---------|
| YOLOR         | 2021 | Yes       | Yes             | Yes         | Unmaintained| HIGH (concept) |
| YOLO-R        | 2021 | Yes       | Yes             | Yes         | Unmaintained| HIGH (concept) |
| YOLO-P        | 2023 | Yes       | No              | No          | Published   | NONE        |
| YOLO-Master MT| 2026 | Yes       | No (single-label)| Yes (preview)| Preview     | MEDIUM      |
| Generalist YOLO| 2025| Yes       | No              | Yes         | Research    | MEDIUM      |
| YOLO26 Native | 2026 | Yes       | No              | No          | Stable      | LOW         |
| YOLOPv2       | 2022 | Yes       | No              | Yes         | Published   | LOW         |
| **Custom Dual-Head** | - | **Yes** | **Yes** | **Yes** | **Build on stable** | **HIGH** |

---

## 5. YOLO-Master MultiTask: Verified Limitations for FMD

| Limitation                | Detail                                                                 | FMD Impact                    |
|---------------------------|------------------------------------------------------------------------|-------------------------------|
| COCO format required      | `multitask_format: coco` is enforced in validation                    | Our YOLO-format labels need conversion |
| Single-label classification| Classify head uses softmax, outputs [B, nc]                           | Our LP tags are multi-label   |
| Shared nc                 | Classification uses same nc as detection                              | Detection has 10, LP has 5   |
| Preview status            | "task-specific multi-output prediction remains preview"              | Not production-ready          |
| No OBB support            | OBB raises ValueError if in tasks list                                | We use OBB for detection      |
| No YOLO format            | Only COCO JSON annotations accepted                                   | Our pipeline uses YOLO txt    |

---

## 6. D1-D4 Metrics: Undefined

**D1, D2, D3, D4 are not defined anywhere in the FMD repository or knowledge base.**

Searched:
- All `.md` files in `D:/fmd-analysis` (zero matches for defect metrics labeled D1-D4)
- All wiki pages in `D:/FMD-KB` (zero matches)
- The string "D1" appears only as spreadsheet cell references, defect class names, or
  unrelated contexts.

**Possible interpretations**:

| If D1-D4 are...          | Then classification head handles...  | And detection head handles...      |
|--------------------------|--------------------------------------|------------------------------------|
| Severity grades          | Severity classification per image    | Localization + severity            |
| (D1=minor, D4=critical)  |                                      |                                    |
| Lens zones               | Zone classification per image        | Localization + zone                |
| (D1=center, D4=edge)     |                                      |                                    |
| Defect dimensions        | Dimensional classification           | Localization + dimensions          |
| (D1=size, D4=shape)      |                                      |                                    |
| Pass/fail grades         | Binary classification                | Binary classification              |
| (D1=pass, D4=fail)       |                                      |                                    |

**Action required**: Ask the lead to define D1-D4 before architecture work is finalized.

---

## 7. Recommended Architecture: Custom Dual-Head YOLO

### 7.1 Architecture Diagram

```
     Input Image (1280x1280)
               |
   +-----------v------------+
   | Shared Backbone        |
   | (YOLO26n, C3k2 blocks) |
   +-----------+------------+
               |
   +-----------v------------+
   | Shared Neck            |
   | (FPN + PAN)            |
   +-----------+------------+
               |
      +--------+------------+
      |                     |
      P5                  P3/P4
      |                     |
      v                     v
   +----+       +---------------------+
   |GAP |       |  Detect Head (OBB)  |
   +----+       |  - cv2 (box)        |
      |         |  - cv3 (cls)        |
      v         |  - angle head       |
  +------+      |  - one2one branch   |
  | FC   |      +---------+-----------+
  | 5    |                |
  | sig  |                v
  +------+      Boxes + Classes + Angles
      |
      v
 LP Tags (5 sigmoid outputs)
 [Missing Primary Package]
 [Multiple Lenses]
 [Missing Lens]
 [Cavity Off Center]
 [Folded Lens]
```

### 7.2 Key Differences from YOLO-Master

| Feature               | YOLO-Master                  | Custom FMD                    |
|-----------------------|------------------------------|-------------------------------|
| Classification type   | Single-label (softmax)       | Multi-label (sigmoid)         |
| Class count           | Shared nc (80)               | Separate: detect=10, LP=5     |
| Label format          | COCO JSON                    | YOLO txt + LP tag list        |
| Detection type        | AABB                         | OBB (oriented bounding boxes)  |
| Base framework        | Preview (ultralytics 8.4.101)| Stable (ultralytics 8.4.142)  |
| Task routing          | Yes (TaskRouter)             | Optional (can add later)      |

### 7.3 Loss Function

```python
# Detection loss: standard YOLO26 OBB loss
L_detection = L_box + L_cls + L_angle + L_dfl

# Classification loss: binary cross-entropy for multi-label
L_classification = BCEWithLogitsLoss(lp_logits, lp_targets)

# Total loss with balancing
L_total = L_detection + lambda * L_classification
# lambda starts at 1.0, tune based on task priority
```

### 7.4 Why This Architecture

1. **Shared backbone**: Proven to work (YOLOR, YOLO-Master). Learns features useful for
   both tasks simultaneously.

2. **Multi-label head**: `GAP -> FC(5) -> Sigmoid`. Each output is an independent
   probability. Handles the 5 LP tags where each image can have 0-4 tags.

3. **Separate class counts**: Detection nc=10 (OI classes), Classification nc=5 (LP tags).
   No forced sharing.

4. **OBB support**: Uses oriented bounding boxes for defect detection. YOLO-Master
   does not support OBB in multi-task mode.

5. **Stable base**: Built on ultralytics 8.4.142, the version already in production use.

---

## 8. The Leakage Problem: What the Architecture Can and Cannot Solve

### What multi-task learning CAN do

- Learn a shared representation that captures features useful for both tasks.
- Reduce confusion between semantically similar labels (e.g., "Missing Lens" LP tag vs
  "Missing Lens" OOI class).
- The implicit knowledge mechanism in YOLOR explicitly aligns feature distributions
  across tasks.
- TaskRouter in YOLO-Master routes features to task-specific experts, potentially
  separating LP-relevant features from OI-relevant features.

### What multi-task learning CANNOT do

- Fix fundamentally ambiguous labels. If "Missing Lens" appears in both LP and OOI
  contexts with different meanings, the model will still confuse them.
- Fix label noise or annotation inconsistencies.
- Fix the data ceiling (346 training images, 4-5px annotation noise).
- Fix the two-tier label format difference (boxes vs image-level tags).

### The real fix for leakage

1. **Label disambiguation**: Ensure LP tags and OOI classes have distinct names.
2. **Label hierarchy**: If LP tags are frame-level and OOI classes are object-level,
   the model should learn this from the data. The multi-task architecture helps because
   the classification head sees the whole image while the detection head sees local
   regions.
3. **Data**: More training examples where LP tags and OOI classes co-occur with clear
   distinctions.

---

## 9. Implementation Roadmap

### Phase 1: Proof of Concept 

1. Take YOLO26n OBB detection model.
2. Add classification head: `GAP -> FC(5) -> Sigmoid` on P5 layer.
3. Train on 10-20 images with both detection and classification labels.
4. Verify both heads converge simultaneously.
5. Compare detection mAP against detection-only baseline.

### Phase 2: Full Training Pipeline 

1. Build data loader that reads both OI box labels and LP tag labels.
2. Implement combined loss: `L_total = L_detection + lambda * L_classification`.
3. Train on full 346/88 split for detection, 70/30 for classification.
4. Evaluate per-class metrics for both heads.
5. Compare against separate detection-only and classification-only baselines.

### Phase 3: Optimization 

1. Tune lambda (loss balancing hyperparameter).
2. Add TaskRouter from YOLO-Master (optional).
3. Add per-class loss weighting for imbalanced classes.
4. Test on production-line images.
5. Compare inference latency against current multi-model pipeline.

### Phase 4: Production Deployment

1. Export to ONNX/TensorRT.
2. Integrate with crop preprocessing pipeline.
3. Set confidence thresholds for both heads.
4. Build pass/fail logic on top of detection + classification outputs.
5. A/B test against current separate-model pipeline.

---

## 10. Risks and Mitigations

| Risk                          | Mitigation                                              |
|-------------------------------|---------------------------------------------------------|
| LP tags are multi-label, not single-label | Use sigmoid head, not softmax                   |
| Detection and classification tasks conflict | Tune lambda; use TaskRouter; add gradient masking |
| LP and OOI label names overlap | Rename to distinct names before training               |
| Small dataset (346 images)    | Use pretrained weights; data augmentation; early stop   |
| Preview code instability      | Build on stable ultralytics, not preview               |
| D1-D4 undefined               | Ask lead before architecture work                      |

---

## 11. Key References

| Source | URL |
|--------|-----|
| YOLOR paper | https://arxiv.org/abs/2105.13255 |
| YOLO-R summary | https://learnopencv.com/mastering-all-yolo-models/ |
| YOLO-Master GitHub | https://github.com/Tencent/YOLO-Master |
| YOLO-Master CHANGELOG | https://github.com/Tencent/YOLO-Master/blob/main/CHANGELOG.md |
| YOLO26 paper | https://arxiv.org/html/2606.03748v1 |
| Generalist YOLO (WACV 2025) | https://openaccess.thecvf.com/content/WACV2025/papers/Chang_Generalist_You_Only_Look_at_Once_for_Real-Time_End-to-End_Multi-Task_Visual_Language_Models_WACV_2025_paper.pdf |
| YOLO-MT head.py | https://github.com/Tencent/YOLO-Master/blob/main/ultralytics/nn/modules/multitask/head.py |
| YOLO-MT router.py | https://github.com/Tencent/YOLO-Master/blob/main/ultralytics/nn/modules/multitask/router.py |
| YOLO-MT train.py | https://github.com/Tencent/YOLO-Master/blob/main/ultralytics/models/yolo/multitask/train.py |
| YOLO-MT dataset yaml | https://github.com/Tencent/YOLO-Master/blob/main/ultralytics/cfg/datasets/coco8-multitask.yaml |
| FMD two-tier labels | D:/FMD-KB/20 - LLM Wiki/Pipelines.md |
| FMD project overview | D:/FMD-KB/20 - LLM Wiki/Project Overview.md |
| FMD decisions log | D:/FMD-KB/20 - LLM Wiki/Decisions Log.md |

---

## 12. Conclusion

The YOLO multi-task architecture idea is technically feasible and well-supported by the
literature. YOLOR (2021) and YOLO-R (2021) proved that a single shared representation can
serve detection and multi-label classification simultaneously. YOLO-Master (2026) is the
most recent implementation, but its classification branch is single-label and requires
COCO-format data, making it unusable for FMD without modification.

**The recommended path** is a custom dual-head architecture built on stable Ultralytics
8.4.142, using the YOLO-Master design principles (shared backbone, task routing, multi-task
loss). The key design choices are:

1. Multi-label classification head (sigmoid, not softmax)
2. Separate class counts for detection (10) and classification (5)
3. YOLO format labels (not COCO)
4. OBB detection (not AABB)
5. Optional TaskRouter for feature routing

**The blocking question** remains: what are D1, D2, D3, D4? Once defined, the architecture
can be finalized and a proof of concept can be built.

