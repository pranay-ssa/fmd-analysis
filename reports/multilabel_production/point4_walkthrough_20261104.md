---
title: Sorting defect types instead of one flag - what we tested and learned
date: 2026-11-04
type: report
status: active
where: reports/multilabel_production/point4_walkthrough_20261104.md
---

# Sorting defect types instead of one flag: what we tested and learned

## Why we did this

Until now the model answered one question about objects: is there something in the picture or not.
That answer is too blunt for two reasons. It cannot say what the object is, so a bubble and a strand
of foreign matter look identical in the output. And it treats everything the same way, so a harmless
bubble counts against a picture exactly as much as contamination does.

The instruction guide already sorts objects into named classes. We tested whether the model can learn
those names, whether it should learn them from every picture that shows the object or only from the
subset that also passed the size check, and whether the answer can be turned into a simple pass or
fail for a picture.

One of the eight classes, Surface Groove, does not appear in this dataset at all. It stays in the
tables so nothing is silently dropped, and it is excluded from every average. Seven classes are
actually learnable.

## How we tested it

Four training runs. The pictures, the split, the recipe and the random seed were identical in all
four. One thing changed per run, so each result has a single explanation:

| Run | What it learned | What changed | The question |
|---|---|---|---|
| 1 | Object classes | baseline | Can the model name the defect type at all? |
| 2 | Size-gate subset | labels only | Does it lose accuracy if we only teach flagged objects? |
| 3 | Object classes | weights | Can we make the rare defects learnable? |
| 4 | Objects plus lens conditions | scope | Do the two jobs survive in one model? |

The data was split three ways before anything was trained: about seven pictures in ten for learning,
one and a half in ten held back to choose operating points, and one and a half in ten kept untouched
until the end. Nothing was tuned on the final set. That matters, because a model that is tuned on the
pictures it is judged on always looks better than it is.

## Run 1: defect classes instead of the size flag

The first comparison taught us the same seven classes in two ways. One version used every picture
that shows the object. The other used only pictures where the object also passed the size check, the
"gate" that the earlier work relied on.

| | Learned from every picture | Learned only from size-flagged objects |
|---|---|---|
| Score across seven classes | **0.4955** | 0.4391 |

The class version wins, and not narrowly. The interesting part is where the gap comes from, and where
it does not.

We expected the gate version to be blind to small objects it was never shown. It was not. On the
pictures whose contamination was never size-flagged, it still found about eight in ten. It had
learned what contamination looks like, not what the flag looks like, and it applied that to objects
it had never been told about.

So the cost of the gate is not coverage. It is sharpness. The gate version ranks the harder cases
worse: contamination, wet packages and one obstruction class all fall behind, while the two bubble
classes barely move. That is a real argument in one direction: teach the class, report the size flag
as a subset of it.

Two smaller observations from this run. Fibre came out slightly better under the gate version, but
the entire unflagged fibre set in the final test is two pictures, so that difference is noise and we
do not report it as a finding. And every class scored well above the level a random guesser would
reach, which is the first evidence that the model is learning shapes and textures rather than
exploiting how common each class is.

## Run 2: giving the rare defects weight

Four of the seven classes are rare. One appears in only about two pictures in a hundred. With
ordinary training, a model can ignore a rare class entirely and still look respectable overall. We
corrected that by telling the loss how rare each class is, so a missed rare defect costs more than a
missed common one. The correction is computed from the training pictures only, once, before training
starts.

| | Without weights | With weights |
|---|---|---|
| Score across seven classes | 0.4955 | **0.6330** |
| HEMA obstruction | 0.569 | **0.963** |
| Extraneous polymer | 0.109 | **0.428** |
| Wet package | 0.390 | **0.572** |
| Fibre | 0.266 | **0.345** |
| Foreign matter | 0.545 | 0.528 |
| Bubble cluster | 0.656 | 0.631 |

This is the largest single improvement in the whole set of experiments. Four classes moved from
unusable to solid. The two small regressions are inside the range we would expect from a different
random seed, and the two bubble classes are unchanged.

There is a second effect worth knowing. Without weights, the usual half-way cut is the wrong
operating point for the rare classes: four of them score zero at that cut and only become useful once
the cut is moved. With weights, the model's confidence is calibrated well enough that the half-way
cut is usable. That matters in production, because it means fewer moving parts between training and
deployment.

## Run 3: one model for both jobs

The second job is the twelve lens conditions: folded lens, dirty camera, multiple lenses and so on.
They had their own model. The question was whether the two can share one, or whether teaching object
types would damage what the lens model already knew.

The combined model trains nineteen columns: twelve lens conditions and seven object classes. It is
nineteen rather than twenty because the eighth class has no pictures.

| | Before the combination | Combined |
|---|---|---|
| Object classes | 0.6330 | **0.6380** |
| Lens conditions (eight with enough pictures to judge) | 0.8182 | **0.8815** |

Neither job suffered, and the lens side improved by more than six points. The most likely reason is
that more labelled work on the same pictures forces the shared part of the model to learn better
general features, which then help the lens task too. The object side stayed level within noise.

We set a rule before running it: if the lens score moved by more than one point, we would report it
as a move rather than as stability. It moved six points upward, so it is reported as a gain, not as
"unchanged". Being precise about that distinction is the difference between an honest result and a
convenient one.

## The pass or fail rule

The rule agreed for a picture: it passes only if it is clear, or if it carries nothing but bubbles.
Everything else fails. That includes all twelve lens conditions, wet packaging, contamination, fibre,
extraneous polymer, obstruction, and the class that never appears. A picture fails when any one of
the failing classes fires, so every failure has a named reason and can be reviewed.

This is not a second model. It is the same model, read at picture level, which means the rule can be
re-tightened or re-loosened without retraining anything.

Results on the untouched final set of 1,121 pictures, 353 of which should pass:

| Measure | At the default cut | At the tuned cut |
|---|---|---|
| Failing pictures caught | 760 of 768 (98.96%) | 759 of 768 (98.83%) |
| Clear pictures passed | 316 of 317 | 316 of 317 |
| Clear pictures wrongly failed | 1 | 1 |
| Bubble-only pictures passed | 8 of 36 | 9 of 36 |
| Pictures passed overall | 324 of 353 (91.8%) | 325 of 353 (92.1%) |

For comparison, the earlier model, read with the same rule on the same pictures, catches 710 of 768
and wrongly fails 3 clear pictures. The improvement is on identical footing, not a change of scope.

The honest weak point is the bubble-only group. Twenty-eight of the thirty-six are wrongly failed,
and the reason is specific: bubble edges look like small foreign particles to the model, so
contamination fires on twenty-three of them and fibre on eleven. That is the first thing to fix next,
and it is a targeted fix rather than a redesign.

## How to read these numbers

Accuracy is not used anywhere in this report, and it should not be. A rule that fails every picture
would be right about sixty-nine percent of the time on this data and would be useless, because it
never passes anything. So the two numbers that matter are the catch rate (how many genuinely failing
pictures we find) and the false-fail rate (how many good pictures we wrongly reject).

The per-class score is average precision. In plain terms: if you took the pictures the model is most
confident about, one at a time, how often would the defect actually be there, compared with a random
draw. A random draw scores the frequency of the class in the data, so a score of 0.428 on a class that
appears in two percent of pictures is far above chance, while 0.1 on a class that appears in
twenty-nine percent would be poor.

The operating point is chosen on the held-back validation pictures only, never on the final set. The
final set is read once, after training, and nothing is adjusted afterwards.

## What we would test next, in order

1. Bubble-only false fails. Teach the model with examples of bubbly pictures that carry no
   contamination, or make it more cautious specifically on contamination and fibre.
2. A wider range of operating points. Two classes chose the top of the allowed range, which means the
   true best point may sit outside it.
3. A second run with a different random seed, to separate real differences from run-to-run noise.
4. The gate version with weights applied, which closes the original question completely rather than
   comparing the gate against an unweighted baseline.

## Limits to keep in mind

- One run per setting. Differences under about three points should be treated as unproven until a
  second seed confirms them.
- The rarest classes have very few test pictures: seventeen for extraneous polymer, twenty-seven for
  obstruction. One picture changing place moves those scores noticeably.
- The size gate is a reporting subset, not a second kind of defect. It is never taught as a class of
  its own.
- The size class that never appears is excluded from every average and is shown as zero in the
  tables so the gap is visible rather than hidden.
