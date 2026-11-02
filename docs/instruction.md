---
title: Standing instructions
date: 2026-11-01
type: reference
status: active
where: docs/instruction.md
---

# Standing instructions

This file is the hand-written register for standing instructions: lead
directives, assumptions and constraints, and workflow rules. It is written by
hand and appended to by hand. No script regenerates it and nothing overwrites
it.

The companion file, the [FMD session coverage map](reference/session_coverage_map.md),
is the opposite. It is machine-mined from session history (94 sessions, 231
standing instructions) and is overwritten on every regeneration. A hand edit
there does not survive. A new rule goes here, never there. The map answers
"how much of what was said in sessions has a document"; this register answers
"what are the rules, and when did each one arrive".

How to use this register:

- Every entry states its date, its source (meeting, session or lead
  directive), and its status: `active` or `superseded`.
- A superseded entry is never deleted. It stays, with a `superseded by:`
  pointer to the entry or decision that replaced it, so the history stays
  auditable.
- Only verified claims are written here. Every entry names the document,
  decision file or session quote it was confirmed against. Nothing false,
  nothing superseded presented as current.
- To add an entry: copy the template (date, source, status, instruction in one
  or two sentences, confirmation pointer) and append it under the right
  section.

## Lead directives

### 2026-08-27 - Document the warnings and the alert system

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: State what the seven warnings are and what alert system is in
  use. No document in this repository answers the question, which is why it
  sits in the coverage map gap list.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-08-27.

### 2026-09-11 - Wait for the GPU, do not reroute

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: If the GPU is blocked, wait for it. Do not move the work
  somewhere else.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-09-11.

### 2026-09-15 - Training material ships as a notebook

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: Deliver the model-training material as a Jupyter notebook, not
  as shell scripts with arguments. The stated reason: new people cannot
  follow the script form, and the notebook is the format the reader is
  comfortable with.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-09-15.

### 2026-09-29 - A bland workbook gets redone

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: When the baseline-versus-multiscale workbook looks bland,
  redo it. Every point that has to be mentioned must appear in it.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-09-29.

### 2026-09-30 - Slides and diagrams are landscape, and subagents help

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: Prepare both the slides and the diagram, using subagents for
  the parallel work. The diagram must be horizontal (landscape) so it fits a
  traditional slide. The deliverable toolchain is Microsoft Office.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-09-30.

## Assumptions and constraints

### 2026-09-17 - No warm-up in this training

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: The training run carries no warm-up phase.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-09-17.

### 2026-10-13 - The population for now is the 1,047-picture pull

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: Work with the 1,047-picture pull for now. The pre-merge
  seven-file record stays the record for the experiment; whether the 24-file
  population joins is still an open decision, and the trained models are
  pre-merge measurements until then.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-10-13; HANDOFF.md state entries 2026-10-28 and "Next, in order"
  item 2.

### 2026-10-21 - Unannotated pictures are out

- Source: lead directive (frame decision 15)
- Status: active
- Instruction: The 3,676 unannotated pictures are excluded. Zero tags means
  no tags; there is no inference of labels for them.
- Confirmed against: docs/decisions/2026-10-21-multilabel-edge-frame.md,
  decision 15.

### 2026-10-21 - The split recipe is frozen

- Source: lead directive (frame decision 8)
- Status: active
- Instruction: 70/30 two-way split, seed 42, grouped on content md5, split
  file plus meta JSON. No validation split: the trainer falls back to a fixed
  schedule and never selects on the test set.
- Confirmed against: docs/decisions/2026-10-21-multilabel-edge-frame.md,
  decision 8; HANDOFF.md "Decisions that are settled and must not be
  relitigated".

### 2026-10-21 - Clear is a folder-derived class

- Source: lead directive (frame decision 14, grill round 6)
- Status: superseded
- Superseded by: the 2026-10-23 entry "Clear is exclusive (Option A)" below.
- Instruction: Clear = the winning path sits in a Clear class folder of the
  two Updated libraries. The folder decides candidacy, and Clear read 1 only
  when the picture carried no defect-class label; LP tags did not block Clear.
- Confirmed against: docs/decisions/2026-10-21-multilabel-edge-frame.md,
  decision 14.

### 2026-10-23 - Standalone tags carry no co-tags

- Source: session (HANDOFF.md ticket 023 entry)
- Status: active
- Instruction: A picture carrying a standalone tag (P1_MPP, P1_PPM, P1_COC,
  F2_FOV) carries only that label. This was measured across all eight newer
  files with zero violations, not assumed.
- Confirmed against: HANDOFF.md ticket 023 entry; docs/wayfinder/tickets/
  023-standalone-tag-audit.md.

### 2026-10-23 - Clear is exclusive (Option A)

- Source: lead directive (docs/decisions/2026-10-23-clear-exclusive.md)
- Status: active
- Instruction: A picture is Clear only when it carries no other label of any
  kind: no defect, no gate tag, no LP tag. A tagged picture is never Clear.
  The ten Clear-folder pictures that carried only a Dirty Camera tag become
  Dirty Camera only.
- Confirmed against: docs/decisions/2026-10-23-clear-exclusive.md. This
  amends the 2026-10-21 Clear rule: the folder still decides candidacy, but
  Clear no longer survives a second label.

### 2026-10-23 - The split label space is Draft 2 codes plus Clear

- Source: lead directive (docs/decisions/2026-10-23-split-label-space.md)
- Status: active
- Instruction: The split stratifies only on classes that exist in the Draft 2
  guide, plus Clear. Excluded as classes: Bubble On 123, Bubble On Edge, HEMA
  Obstruction. For the four gated plain families (Foreign Matter, Fiber,
  Extraneous Polymer, HEMA) only the micron-gate tag counts as that class.
  The gate rule applies to those four classes only.
- Confirmed against: docs/decisions/2026-10-23-split-label-space.md;
  docs/decisions/2026-10-26-split-considerations.md rules 3 to 6.

### 2026-10-26 - The split rules are frozen, and EDA and split read the size flag differently

- Source: lead directive (docs/decisions/2026-10-26-split-considerations.md)
- Status: active
- Instruction: A picture that shows a class belongs to that class in the EDA,
  and the micron-gate tag is reported there as "of which size-flagged". In the
  split, the four gated classes are positive on the size flag only. An
  un-gated object-only picture is counted in its class in every EDA table and
  is outside the split. Never present the gate-only split count as the class
  count, or the class count as the split positives. Split v6 is the current
  split for the trained models.
- Confirmed against: docs/decisions/2026-10-26-split-considerations.md,
  rules 5 to 8 and the amendments dated 2026-10-28 and 2026-10-29;
  HANDOFF.md state entry 2026-10-28.

### 2026-10-28 - The trained models are pre-merge measurements

- Source: session (HANDOFF.md state entry 2026-10-28)
- Status: active
- Instruction: Both trained variants measure the pre-merge seven-file record.
  They are not read as 24-file results until the join is decided; if the join
  happens, the label tables rebuild on the 7,470-row split and the models
  retrain.
- Confirmed against: HANDOFF.md state entry 2026-10-28 and "Next, in order"
  item 2.

### 2026-10-28 - The two families are named LP class and OOI class

- Source: lead directive (docs/decisions/2026-10-28-naming-lp-and-ooi.md)
- Status: active
- Instruction: Use "LP class" for one of the twelve lens-presentation answers
  and "OOI class" for one of the eight object classes marked as a region. The
  thirteenth answer is the "OOI flag": it says at least one OOI class is
  present, so it is scored by fire rate on three groups (OOI-only, mixed,
  Clear), never by average precision. The word
  "condition" is dropped from results artifacts, and "object" alone is no
  longer used as a class word. Older documents keep their earlier wording.
- Confirmed against: docs/decisions/2026-10-28-naming-lp-and-ooi.md.

## Workflow rules

### 2026-09-16 - Storage credentials live in a script, never in a document

- Source: session (quoted in the coverage map gap list)
- Status: active
- Instruction: The storage connection details go into a script that is moved
  to the VM. They are never written into a document, a report or this
  register. The coverage map quotes that message with the account key
  redacted; this entry does not repeat any part of the string.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-09-16 (key redacted there).

### 2026-10-25 - Stop-work instruction for that evening

- Source: session (quoted in the coverage map gap list)
- Status: superseded
- Superseded by: the 2026-10-26 resumption, recorded in the HANDOFF.md state
  entry dated 2026-10-26.
- Instruction: On the evening of 2026-10-25: make no changes, work continues
  the next day. The instruction applied to that evening only and the work
  resumed on 2026-10-26.
- Confirmed against: docs/reference/session_coverage_map.md, gap dated
  2026-10-25; HANDOFF.md state entry 2026-10-26.

### 2026-10-25 - The Fiber and Extraneous Polymer reply convention

- Source: session (HANDOFF.md state entry 2026-10-25, reply convention)
- Status: active
- Instruction: In the reply, the 32 renamed objects keep the earlier Fiber
  name so the columns agree with the onboarding report. The annotation
  reading (Fiber 245/178, Extraneous Polymer 150/144) is stated in a note on
  the sheet. The next annotation uses the newer name.
- Confirmed against: HANDOFF.md state entry 2026-10-25, reply convention
  paragraph.

### 2026-10-28 - Numbers go to the user the moment they are read

- Source: session (HANDOFF.md, rules in force, as recorded in the handoff
  dated 2026-10-28)
- Status: active
- Instruction: Report a number as soon as it is read, before any verification
  or documentation pass. Verification runs in parallel and a correction
  follows if it contradicts the first reading.
- Confirmed against: HANDOFF.md "Rules in force".

### 2026-10-28 - Triple check, as defined here

- Source: session (HANDOFF.md, rules in force, as recorded in the handoff
  dated 2026-10-28)
- Status: active
- Instruction: A triple check is three legs: a verifier with hand-typed
  expected values, a byte-identical rerun, and an independent second
  derivation. All three must pass.
- Confirmed against: HANDOFF.md "Rules in force".

### 2026-10-28 - Compute is local; the VM is read-only for proofs

- Source: session (HANDOFF.md, rules in force, as recorded in the handoff
  dated 2026-10-28)
- Status: active
- Instruction: All compute runs local. The amd-a100 VM is used read-only for
  hash and census proofs; scripts are piped over ssh and nothing is written
  to the shared VM tree.
- Confirmed against: HANDOFF.md "Rules in force".

### 2026-10-28 - Pitfalls are logged

- Source: session (HANDOFF.md, rules in force, as recorded in the handoff
  dated 2026-10-28)
- Status: active
- Instruction: Every pitfall found in the work goes into docs/pitfalls.md,
  not only into chat.
- Confirmed against: HANDOFF.md "Rules in force"; docs/pitfalls.md exists.

### 2026-09-19 - Every repository doc carries the five-line header, and the index is generated

- Source: lead directive (AGENTS.md, docs and the board)
- Status: active
- Instruction: Every repository doc starts with the five-line header (title,
  date, type, status, where). docs/INDEX.md is generated by
  tools/index_docs.py and is never edited by hand: the edit is lost on the
  next run. Run the tool after adding, moving or renaming a doc.
- Confirmed against: AGENTS.md "Docs and the board"; HANDOFF.md "Rules in
  force".

### 2026-11-01 - The archive never wins a search

- Source: lead directive (AGENTS.md, searching this repository, added in the
  2026-11-01 retrieval batch)
- Status: active
- Instruction: docs/archive/ is superseded material and an audit trail only.
  It stays readable by path, but a current document always answers over it.
  Before quoting any doc, check its status header and prefer the newest
  docs/decisions/ file. Reaching the archive is deliberate and explicit.
- Confirmed against: AGENTS.md "Searching this repository".

### 2026-09-19 - Reader-facing artifacts carry no internal names

- Source: lead directive (AGENTS.md, reader-facing artifacts)
- Status: active
- Instruction: Anything a lead or a client reads is built for them: no file
  paths, script names, run-folder names, ticket ids, branch names or version
  tags. Result first, method last and short. Every count names its population
  in the header, and unavoidable terms are defined once.
- Confirmed against: AGENTS.md "Reader-facing artifacts (reports, workbooks,
  decks, messages)".

### 2026-11-01 - This register, not the coverage map, holds new rules

- Source: lead directive (this batch)
- Status: active
- Instruction: A new standing instruction is appended to this file with its
  date, source and status. It is not added to
  docs/reference/session_coverage_map.md, because that file is regenerated and
  the edit would be lost. The coverage map stays machine-mined.
- Confirmed against: docs/reference/session_coverage_map.md ("Generated, not
  hand-written").
