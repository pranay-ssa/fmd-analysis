# Update: detecting defects on cropped images (YOLO11 and YOLO26)

**Date:** Tuesday 15 September 2026

## 1. What cropping does

Before training, we cut each defect out of the frame and resize that piece to a fixed size. A typical defect is about 13 pixels across in the original frame. Inside a crop it keeps about 11 of those pixels. If the whole frame is resized to the same input size instead, it keeps only about 7. In other words the crop gives each defect about 1.6 times the size in each direction, or roughly two and a half times the pixels, and that is why more defects are found.

| Setup (same cropped images) | Detection score, higher is better |
|---|---|
| All defects treated as one class | 0.664 |
| Split into the ten defect classes | 0.535 |

The second row is the harder task, because the model must also decide which of the ten types each defect is.

## 2. Cropping finds more defects, but box precision is limited by the data

| What we measure | Value | Reading |
|---|---|---|
| Typical overlap of a found box with the correct box | about 0.80 | The same in every setup we have tried |
| Training images available | 346 | Each image is a crop holding about 5 defects, so 2020 labelled defects in total |
| Typical defect size in the original frame | about 13 pixels across | Our drawn boxes carry 4 to 5 pixels of variation, roughly a third of a defect |

Box precision does not move when we change the model or the pipeline. That tells us the limit is the amount and the quality of our annotations, not the model. More annotated data is the lever here.

## 3. Learning rate: close on small data, and the effect grows with defect size

Our own comparison, on the 346 training images:

| Model (our crops, defects about 11 px) | Automatic rate | Fixed rate 1e-4 | Difference |
|---|---|---|---|
| YOLO26n | 0.617 | 0.577 | 0.039 |
| YOLO11n | 0.601 | 0.568 | 0.033 |

The same comparison in the reference runs, where the identical images are trained at two different input sizes. "Resized to 1280" means the frame was shrunk to about half size first; "native size" means the frame was kept at its original width.

| Input size in the reference runs | Automatic rate | Fixed rate | Difference |
|---|---|---|---|
| Frames resized to 1280 px wide (defects about 7 px) | 0.473 | 0.463 | 0.010 |
| Frames at native size, about 2500 px wide (defects about 13 px) | 0.596 | 0.515 | 0.081 |

The pattern is the point: the gap between the two settings grows as the defects carry more pixels. Our own numbers sit between the two reference rows, which is what the size explanation predicts. Two cautions: the reference rows come from a different dataset, so this is a pattern to test rather than a settled rule, and with only 346 images we cannot yet tell how much of our own gap is real and how much is run-to-run variation. Our theory to test on production-grade data: the learning rate starts to matter once there is enough data and enough defect detail to learn from.

## 4. Early-layer detail: tested, and the answer is no

We tested whether extra detail from the early layers of the network helps find the classes we miss most: bubble on the ring, bubble on the edge, and fibers. Added directly it cost points (0.608 against a 0.664 control), so we then tested the cleaned-up version, where the detail passes through a filtering block before it enters the model. That also cost points:

| Setup | Detection score, higher is better |
|---|---|
| Unchanged model | 0.535 |
| With the extra cleaned-up detail | 0.436 |
| Difference | -0.099 |

The model found fewer defects, not more (recall fell by 0.106), and the unchanged model reproduced our recorded baseline exactly, so the comparison is trustworthy. Extra low-layer detail has now been tested twice, raw and cleaned up, and it lost both times. The reading: the standard connection pattern is already the right shape, so gains have to come from strengthening the processing inside it. That is where our earlier gains came from (on the previous model line, an attention change was worth +0.059).

## 5. Input image size: our biggest measured lever, and what it costs

We compared the same images trained at two input sizes. "Resized to 1280" is what every run so far has done: the frame is shrunk to 1280 pixels wide first. "Native size" keeps the frame at its original width, about 2448 pixels.

| Measure | At 1280 px | At native size | Change |
|---|---|---|---|
| Detection score, YOLO26n | 0.473 | 0.596 | +0.123 (+26%) |
| Detection score, YOLO11n | 0.487 | 0.680 | +0.194 (+40%) |
| Training time, 100 epochs on one A100 | 6.2 min | 23.3 min | 3.7x |
| Inference per image | about 2 ms | about 8 ms | about 3x |

On the stricter score (mAP50-95) the same three comparisons improve by 32% and 57%.

Three things follow.

1. **Input size is worth more than anything else we have measured.** It moved the score by 0.12 to 0.19. The learning-rate setting moved it by 0.01 to 0.08, and the best model change we ever measured moved it by 0.059. This is not a tuning detail, it is the main lever.
2. **It is not free, and the price scales with the frame.** 3.4x to 3.7x the training time and about 3x the time per image. Whether the inference cost matters depends on where this runs: on a server-class GPU both sizes process well over 90 images per second, so the training bill is the real cost, while on an edge device the 3x would matter a great deal.
3. **Cropping is what makes the detail affordable.** A defect in our crop reaches the model at about 11 pixels, which is close to the 13 pixels that full frames only reach by going native. Our crop costs a fraction of the compute to get there, because a crop is about 1.2x wider than 1280, while a full frame is 1.9x wider. We are getting most of the resolution benefit without paying the full-frame price.

Related measurement, useful as a rule: the inference size must match the training size. Our model scores 0.5355 at the size it was trained on and 0.4849 when it is asked to evaluate at a larger size, so 0.05 of score can be thrown away for nothing.

Why we are not settling the input size now: these numbers come from a different dataset than ours, and our own set has 346 training images with defects of about 13 pixels. At that size, effects above about 0.1 are clear, while effects below about 0.02 cannot be told apart from run-to-run variation, so a size decision made here would not transfer. The right place to decide it is the production set, where the frame size, the defect sizes and the volume are the real ones. What we will bring then is a measured curve of score against training time for two or three input sizes, so the choice is made on evidence rather than preference.

## 6. New guardrail

Every design change now passes an automatic check before training starts. The check compares the new design against the stock one and stops on any difference we did not intend. A run can no longer silently differ from what we say it is.

## Key takeaways

1. Cropping works: the same defects are larger for the model, and more of them are found.
2. Box precision (about 0.80) is limited by our data, not by the model. More annotated data is the lever.
3. The learning-rate question is not settled. On 346 images the two settings sit close, and the gap widens as the defects carry more pixels, so this needs the production-grade set to answer.
4. Extra early-layer detail loses score whether it is raw or cleaned up. The gains we have measured came from inside the existing pathway, so that is where the next changes will come from.
5. Input image size is the biggest lever we have measured: +26% to +40% of score for full-size frames against 1280, at 3.4x to 3.7x training time and about 3x inference. Cropping keeps nearly all of that detail at a fraction of the cost, which is why our crops are the right starting point. We will set the final input size on the production data, where the decision can be made properly.
