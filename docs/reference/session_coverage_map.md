---
title: FMD session coverage map
date: 2026-11-01
type: reference
status: active
where: docs/reference/session_coverage_map.md
---

# FMD session coverage map

Coverage of 3 months of Hermes session history (2026-08-21 to 2026-11-01, both
laptops, 94 sessions, 231 standing instructions) against the markdown in this
repository. Generated, not hand-written.

> **Typo tolerance and stemming are active since 2026-11-01.** The first run
> used exact-token matching, which penalised the speaker's spelling: of 1,099
> content tokens missing from their best-matching doc, 553 (50.3%) were
> misspellings present in no document at all, and only 22 distinct tokens
> genuinely needed a synonym. That is why a hand-written alias table was
> ruled out and those 22 synonym tokens stay unaliased. The scorer now applies
> **typo tolerance (edit distance 1, tokens >= 6 chars) plus Snowball (English)
> stemming**, and the corpus excludes `docs/archive/`. Figures below are from
> one run of `python tools/coverage_map.py` with that method.
> 
> This report is excluded from its own corpus. It quotes instructions verbatim,
> and leaving it in made the headline jump 19 COVERED rows on a single
> regeneration purely from the report's own wording.

## Headline

| Verdict | Before | After | Change |
|---|---|---|---|
| COVERED | 93 | **130** | +37 |
| PARTIAL | 120 | **92** | -28 |
| GAP | 18 | **9** | -9 |
| **Total** | **231** | **231** | |

Before is the baseline scorer with `docs/archive/` in the corpus (cell A0B0 of
the 2x2 below), and it reproduces the 93/120/18 the first version of this
report published. After is the corrected scorer with the archive excluded (cell
A1B1), which is the configuration `python tools/coverage_map.py` prints.

## Why both changes were needed: the 2x2

Scoring method and corpus exclusion changed together, so each was run in
isolation to attribute the effect honestly. All four cells ran on the same
231 rows and the same corpus snapshot.

| Cell | COVERED | PARTIAL | GAP |
|---|---|---|---|
| A0B0 baseline, archive IN  | 93 | 120 | 18 |
| A1B0 typo+stem, archive IN  | 164 | 60 | 7 |
| A0B1 baseline, archive OUT | 82 | 113 | 36 |
| A1B1 typo+stem, archive OUT | 130 | 92 | 9 |

**Main effects on COVERED:**

- Scoring method (typo + stem), archive held in: **93 -> 164 (+71)**
- Excluding archive, baseline scoring held: **93 -> 82 (-11)**, and GAP **18 -> 36**
- Both together: 93 -> 130 (+37)

**The two levers interact, and the order matters.** Excluding `docs/archive/`
under the *baseline* scorer pushes GAP 18 -> 36 (+18), because the archived handoffs were the only
place those rules were worded. With the corrected scorer already in place the
same exclusion leaves GAP 7 -> 9. **The scoring
fix is what makes the archive exclusion safe.** The method is also the single
largest effect, worth +71 COVERED on its own.

## Coverage by category (corrected)

| Category | n | COVERED | PARTIAL | GAP |
|---|---|---|---|---|
| uncategorised | 141 | 82 | 50 | 9 |
| domain_rule | 46 | 23 | 23 | 0 |
| lead_client | 29 | 17 | 12 | 0 |
| workflow | 28 | 14 | 14 | 0 |
| presentation | 16 | 8 | 8 | 0 |

Categories are multi-label, so the n column sums above 231: 24 instructions
carry more than one tag.

## Coverage by month (corrected)

| Month | n | COVERED | PARTIAL | GAP |
|---|---|---|---|---|
| 2026-08 | 25 | 15 | 9 | 1 |
| 2026-09 | 95 | 52 | 37 | 6 |
| 2026-10 | 111 | 63 | 46 | 2 |

## The 9 remaining gaps

Instructions with no document footprint under the corrected method.

**2026-08-27**

> Okay what are the 7 warnig that we have and what are they and what is the allert system we are using

**2026-09-11**

> Do it !if gpu is blocked we will wait

**2026-09-15**

> Becasue the way the tway way we are using the model training using the args and sh scrips is not easy to undertand for new ppl so hence the juypter book she will underdstand if its in the format that she is comfortable with !

**2026-09-16**

> CONNECTION_STRING = ( "DefaultEndpointsProtocol=https;" "AccountName=stjnjmakearmor;" "AccountKey=[REDACTED];" "EndpointSuffix=core.windows.net" ) We have to prep a script and move it to the vm

**2026-09-17**

> we dont need warm up for this

**2026-09-29**

> Redo the fmd baseline vs multiscale excel it looks bland we have to make sure that all the points to be mentioned there

**2026-09-30**

> Do both ! prep the slides and do the diagram aswell using subagents while you are at it, underdtand that diagram should be horizotal or in landscape so that it will pit in a traditional slides , we are using microsoft offics

**2026-10-13**

> We will just pull 1047 for now

**2026-10-25**

> dont make any chnages we will continue this tomorrow

## 35 instructions no longer matched after the archive exclusion

These were COVERED only because `docs/archive/` supplied the wording. They are
not lost content: the archive files still exist and remain readable by path,
`git grep`, or `rg --no-ignore`. Listed because they are the honest cost of
excluding the archive.

| Date | Instruction (truncated) |
|---|---|
| 2026-08-27 | Prepare a HEMA specific report that should contail all your findings into and the nest steps as well we will c |
| 2026-09-02 | We will go with A also from the report i have read aout the brightness floor ! have it at 13 would be helpful  |
| 2026-09-08 | First we will test few of the suggestions to get a better idea and then we can prepare a detailed analysisc do |
| 2026-09-08 | adding the layers is bust or the location that we added and the type we have added make it a bust ! beacsue sh |
| 2026-09-09 | Thats the plan but we have to give the results do that they will now understand what we have done and if and a |
| 2026-09-09 | Oka these are the resulsta nd the file for the experiments thats other teamate has done , go through it we wil |
| 2026-09-09 | Truth to be told we have the restructure the whole fmd preprocess folder to begin it our intial idea is that t |
| 2026-09-15 | No, we will continue this work from tomorryow make note of it and we will close for the day |
| 2026-09-16 | To answer this 'One model cannot be shown to cover every class on every line, because no line shows every clas |
| 2026-09-21 | Can run a simple test ? we will make a test train split for the 55 images , you can decide if we need 70, 30 o |
| 2026-09-22 | i shared the 128 analysis and the the previous fiber ep dillemma so we have to wait till response come ! i hav |
| 2026-09-24 | I know for a factthat she meant to only work with those 178 images but other 111 images have 2 lp +OoI tags ?  |
| 2026-09-24 | before that can you tell me why we are using pytorch and why she is usinf keras and is there any major differe |
| 2026-09-28 | Okay in the presvious session we have compledted the new multilable architecture and as she has asked us to se |
| 2026-09-28 | Before anything I want to bring this up becasue we have it now ! WHen i asked for the resulsts for the run, th |
| 2026-09-29 | I got the message from the lead "Pranay can you check the result with MultiScale Architecture? to see if the f |
| 2026-09-29 | We will make another folder in crops called eda and we will perform eda or already done docs to there an dalso |
| 2026-09-30 | We will need to prepare the 4 slide reagrding the Multi label for the next week deck , idea is that what and w |
| 2026-10-06 | Sorry I was busy and burntout so i took break from work ! i have seen the questions and all the answers you ah |
| 2026-10-07 | Okay now we have to move the files to our vm box pranayp, and reverify everything i will be going to office to |
| 2026-10-07 | Okay thats all i need to know , im going back to home so we will continue it later |
| 2026-10-07 | Lets start with the report we have to show the numbers related to baseline resnet 50 and the multiscale for no |
| 2026-10-13 | Alright we have the email saying that they have uploaded the data into storage blob we use a previous script i |
| 2026-10-15 | she asked me this "Also send me the EDA that you have performed. Particularly I am looking for LP EDA. rest al |
| 2026-10-15 | Accordignto the email from JnJ they said we can consider the ambigious as fiber , does that actually mean that |
| 2026-10-21 | here is what we are going to do , first make a detailed markdown for both the drafts , i know there are images |
| 2026-10-22 | I asked of P2 and F2 doubt to lead we will hear from them soon but i thing its safe to assum that P2 is the co |
| 2026-10-22 | also can you explain me what matric is ? also this is just my thought process but we have previous bubbls and  |
| 2026-10-23 | Good thats clear anough , now what we can do is based on the analysis we should make a teams message saying th |
| 2026-10-25 | i will re check the numbers again ! this has been an repeadting issues with the newer and older names mismatch |

## What this report does not measure

- Whether an agent actually retrieves a rule at the moment it needs it. This
  measures document presence under a scoring method, not runtime retrieval.
- Assistant-side instructions. Only user messages were mined.
- 103 file-paste messages over 3,000 chars were excluded as non-instruction.
- 250 retry duplicates were removed by exact-text dedupe before scoring.
- Typo tolerance uses edit distance 1 on tokens >= 6 characters; shorter tokens
  match exactly. Snowball (English) stemming is applied to both sides.
- This report quotes instructions verbatim, so it is excluded from its own
  corpus. Leaving it in made the headline jump 19 COVERED rows on one
  regeneration, purely from the report's own wording.

## Method

1. 94 FMD sessions from `state.db` (read-only), both machines, one corpus.
2. 1,334 user messages -> 773 after size/system filtering -> 981 after dedupe
   (250 retry duplicates removed) -> 231 matching standing-instruction patterns.
3. Secrets redacted before any scoring.
4. Each instruction scored by content-token recall against 149 markdown files
   (`docs/archive/` and this report itself excluded).
5. Match = exact token, or stemmed match, or edit distance <= 1 for tokens >= 6.
6. Verdict: verbatim 3-gram or recall >= 0.70 is COVERED; >= 0.45 PARTIAL; else GAP.
7. All four cells of the method x corpus 2x2 run on the same 231 rows.
