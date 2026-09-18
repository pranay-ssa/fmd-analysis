# FM3 Edge Algorithm URS — Open Dilemmas for the Lead Meeting

**Date:** 2026-09-04
**Source documents:**
- `samples/FM3 Edge Algorithm URS Final Draft .pdf` (28 Aug 2026, 34 pages, Revision: DRAFT)
- `Manufacturing Condition Ontology V1.docx` (Bryce Barrineau, V1.0)
- `D:/02-SSA/JnJ-Docs/FMD Official docs/FMD Annotation Guide - FM vs FM-Exclusion Classes (2026-08-21).md`

**Why this exists:** Lead asked us to flag points worth raising in the FM3 meetings that go beyond the obvious, with cross-references between the URS and the ontology so the questions can be backed by source documents when the time comes.

---

## 1. The 20% HEMA overlap threshold is explicitly "pending EDA"

**URS p22, Section 5.2.1 (HEMA):**
> *"A subcategory of HEMA defects are those that overlap with **more than 20% (pending EDA)** of the visible lens will be classified under presentation defects as HEMA Obstruction as they will impact the systems ability to identify other defects under and around the HEMA."*

**Cross-reference — Ontology (Manufacturing Condition Ontology V1.docx, line 153, HEMA Fragment):**
> *"This tag refers to cases where the ring has been broken into smaller chunks and presents as an object that can be bounded rather than **obstructing a large swathe** of the image."*

**Cross-reference — Ontology (line 224, HEMA Obstruction):**
> *"This tag specifically refers to cases where the artifact is **largely intact** and **obscures a large region** of the image."*

**Cross-reference — Annotation Guide (§3.18):**
> *"**largely intact** and obscures a **large region**"* (qualitative).

**Why it matters:** The URS uses a numeric threshold (20%). The ontology and annotation guide use qualitative language ("large swathe", "largely intact", "large region"). None of these three documents define the boundary consistently, and the URS itself flags the number as pending EDA. Our EDA only covered 8 HEMA Fragment images — not statistically meaningful for setting a threshold.

**Dilemma to raise:** Who owns the EDA that validates the 20% number, and when does it happen? If the EDA shifts the number, it changes how HEMA Fragment vs HEMA Obstruction get labeled in training.

---

## 2. TAR/TRR are per-artifact, not just overall

**URS p26-27, Section 5 (Performance Metrics):**
> *"The True Accept Rate will be used to evaluate True Accept conditions, **stratified by artifact**. For example, there is a different True Accept Rate for pristine images, acceptable-sized air bubbles, and acceptable small debris. The True Reject Rate will be used to assess true reject conditions, **stratified by debris type**."*

**URS p28, Section 6.1 (Edge Algorithm Targets):**
> *"TAR = 99.9%, TRR = 99.7%"*

**Why it matters:** The algorithm must hit these targets **for each individual class**, not just the blended overall rate. Our dataset has 22 classes, several of them with very small sample counts:
- Bubble Scatter: 7 images total (6+1w)
- HEMA Fragment: 8 images total
- Missing Lens: 21 images
- View Obstructed: 22 images

The VAL-0009 sample size chart referenced in URS Section 6.2 (p29) is based on a 95% probability of success at 99% confidence. Per-class TRR at 99.7% on small samples is statistically thin.

**Dilemma to raise:** Are we statistically set up to prove per-class TRR with the current image counts? Do we need more images for the small classes before the algorithm can be validated per-stratum?

---

## 3. FAR can only be calculated on 100% defective populations

**URS p28:**
> *"False Accept Rate can only be calculated when the test population is **100% defective**. This enables direct measurement of the system's defect detection capability **independent of production defect prevalence**."*

**Why it matters:** To validate TRR per class, the test set for that class must be 100% defective images. Our current frozen split (802 train / 201 test, stratified by class) does NOT enforce this — it stratifies by class but the test set contains both pristine and defective images mixed.

**Dilemma to raise:** Does the validation pipeline need a separate 100%-defective test set per class for FAR computation, separate from the main frozen split?

---

## 4. Primary Package Marks need batch-level analysis, not per-image

**URS p20-21, Section 5.1.13 (Primary Package Mark):**
> *"Consistent presence across **multiple images from the same batch**"*
> *"Requirement for **batch-level analysis** to distinguish from true rejects"*
> *"The current FMD system's inability to distinguish PPMs from genuine debris represents a **critical area for algorithmic improvement**."*

**Cross-reference — Ontology Annotation Specification (lines 283-307):** Primary Package Mark (PPM) is **not listed as a class** anywhere in the ontology. The 13 Image Level TAGs and 11 Object Level BBOXs total 24 classes; PPMs are absent.

**Cross-reference — URS lists PPMs under "internal presentation defects":**
> URS p20: *"This class of presentation defects will be handled **internally** by our onsite image quality tools"*

**Why it matters:** This is a stronger point than we originally flagged. The ontology confirms PPMs are not formally a class — they're a property of the package itself. Our CNN is per-image classification and cannot solve this without architectural changes (temporal/batch input).

**Dilemma to raise:** If PPMs are not in the ontology as a class, and the URS says they're handled by on-site tools, why are we training the algorithm to handle them at all? Or is the assumption that the algorithm just needs to NOT false-reject on PPM-affected images?

---

## 5. Single vs. two-algorithm decision is still open

**URS p28, Section 6:**
> *"It is **recommended** that two algorithms be developed to reduce the requirements for each algorithm solution. If only one algorithm is developed, it must meet the requirements of **both** the Edge Algorithm and the Back Office Algorithm."*

**Cross-reference — Ontology Annotation Specification (lines 283-307):** The ontology's formal split already maps cleanly onto two-algorithm architecture:
- **13 Image Level TAGs** = natural fit for the **Edge Algorithm** (pass/fail, image-level, no measurement)
- **11 Object Level BBOXs** = natural fit for the **Back Office Algorithm** (classify, measure, depth over speed)

**Why it matters:** The URS recommends two but the decision isn't finalized. Our CNN training work is classification (Back Office scope). If they pick a single algorithm, the training target changes entirely — we'd need a binary pass/fail model on the 13 TAG classes instead.

**Dilemma to raise:** Has the two-algorithm decision been finalized? If two, what is the deliverable timeline for each? The ontology already structurally supports the split.

---

## 6. The 647um threshold comes from QP-0050, not the annotation guide

**URS p7, Section 4.1:**
> *"Detection of objects on the lens or in solution that are **647um or larger**"*

**Cross-reference — Ontology (line 14):**
> *"FM definition threshold: **647 um** (0.647 mm); Source document: QP-0050, Rev 115"*

**Why it matters:** Our preprocessing pipeline does NOT filter by size — it crops all images to a fixed window. The 647um threshold is applied at inference time by the algorithm, not at preprocessing. This is a useful clarification for the lead: our pipeline produces a 647um-agnostic crop set, and the size threshold is downstream.

**Not a dilemma — just worth stating explicitly so nobody asks where the size filter lives.**

---

## 7. Bubble Obstruction vs Bubble Scatter — ontology confirms clean separation

**URS p5, Section 5.1 (Bowl Presentation):**
> *"Additional bowl presentation defects that will be handled internally include: ... **Bubble obstruction**"*
> URS treats **Bubble Scatter** as an algorithm-handled defect (Section 5.1.5).

**Cross-reference — Ontology Annotation Specification (line 295):** **Bubble Scatter** is the only bubble-related entry in the Image Level TAGs. There is NO "Bubble Obstruction" entry anywhere in the ontology's 24 classes.

**Cross-reference — Ontology (line 180, Bubble Scatter):**
> *"Bubble Scatter presents as a field of many small bubbles beneath the lens surface... This phenomenon differs from **individual bubble obstructions** by creating a diffuse pattern of interference across the field of view."*

**Why it matters:** The URS mentions "Bubble Obstruction" as an internal defect, but the ontology has ZERO bubble obstruction entries. The ontology is cleaner: all bubble-related items are either Bubble Scatter (TAG, algorithm-handled) or one of the bbox classes (Bubble, Bubble Cluster, etc., Back Office-handled). No "Bubble Obstruction" class needs to be trained.

**Dilemma to raise:** Confirm that "Bubble Obstruction" in the URS is not meant as a training class — it's an internal concern only, not a label the algorithm outputs.

---

## 8. Current FMD has 80% capability, FM3 targets 99.7% TRR

**URS p4:**
> *"The current FMDVS is only capable of identifying whether FM or debris exists within the package at an **80% capability requirement**."*

**URS p28:**
> *"True Reject Rate (TRR) = **99.7%**"*

**Why it matters:** The jump from 80% to 99.7% is significant. The URS does not specify what false-reject budget (FRR) is acceptable in production. At 99.7% TRR, the false-reject rate on pristine images could still be significant if the base defect rate is low. The kickoff deck referenced 150 ms/image latency and ≥99% TAR/TRR targets — these are in tension with the URS's 99.7% number.

**Dilemma to raise:** What is the acceptable FRR budget in production? Has the 99.7% TRR target been finalized, or is it still negotiable?

---

## 9. HEMA Obstruction definition mismatch — three documents, three different wordings

| Document | Wording |
|----------|---------|
| URS p22 | *"overlap with **more than 20%** of the visible lens"* (numeric) |
| Ontology line 224 | *"**largely intact** and obscures a **large region**"* (qualitative) |
| Annotation Guide §3.18 | *"**largely intact** and obscures a **large region**"* (qualitative) |

**Why it matters:** The URS is the engineering spec but is internally flagged "pending EDA". The ontology is the formal class definition but uses qualitative language. The annotation guide was written for human annotators. None of these three documents are reconciled.

**Dilemma to raise:** Which document is the authoritative definition for the 20% threshold? If the URS is authoritative, the annotation team needs a procedure to measure lens overlap consistently. If the ontology is authoritative, the URS 20% number needs EDA validation before it can be used.

---

## Bonus: bubble <5x5 pixel rule (annotation rule, confirmed by both ontology and guide)

**Ontology line 168:**
> *"Bubbles less than 5x5 pixels should not be annotated with the bubble label. Bubbles smaller than 5x5 pixels can only be annotated as bubble clusters or bubble scatter when they appear as such."*

**Why it matters:** Our preprocessing pipeline preserves features down to small bubble sizes. If a human relabels the training data, this rule means standalone Bubble labels should not be applied to <5x5px features. This is worth raising during the training-data audit to confirm consistency.

---

## Updated ranking — strongest dilemmas to lead with

1. **HEMA 20% threshold** (URS p22) — pending EDA, ontology/guide qualitative, no reconciliation. **Open.**
2. **Two-algorithm decision** (URS p28) — ontology structurally supports the split, but decision not finalized. **Open.**
3. **PPMs not in the ontology** — stronger footing now. **Open.**
4. **Per-class TRR with small samples** — VAL-0009 chart, Bubble Scatter=7, HEMA Fragment=8. **Open.**
5. **FAR requires 100% defective test populations** — our split doesn't enforce this. **Open.**

Cleared by cross-referencing: Bubble Obstruction classification (#7), 647um source (#6), algorithm split mapping (#5 partial).
