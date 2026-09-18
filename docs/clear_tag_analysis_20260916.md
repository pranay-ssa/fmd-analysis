# The "Clear" tag: numbers, method and verification (2026-09-16)

Written after the lead asked for the exact class count inside the "Clear" tag, to forward to the client.
It exists so that the question, the answer and the way it was checked live in the repository instead of in a
chat thread, and so that nobody re-derives a different number later.

## The question

"Give me the exact number of classes in the Clear tag. I will mail it to the client."

## The answer

The "Clear" group holds **2,333 images**, all of them different pictures.

| | Images |
|---|---|
| Clear images that also carry a defect class | **128** |
| Clear images that carry no other label | **2,205** |
| Total Clear images | **2,333** |

**Classes involved: 6** in the canonical (older library) taxonomy:

| Defect class the Clear image is also labelled with | Images |
|---|---|
| Bubble | 37 |
| Wet Package | 34 |
| Dirty Strobe | 16 |
| Bubble Irregular | 16 |
| Bubble Cluster | 15 |
| Dirty Camera | 10 |
| **Total** | **128** |

Two further class names appear only in the new drop, on 2 of those same 128 images: Lens Off Center (1) and
Multiple Lenses (1), where the older library labels both of them Wet Package. So the count of class names
touching "Clear" is **6 in the canonical taxonomy, or 8 across all sources**. Quote the one the client's
taxonomy uses, and say which.

Two of the 128 images (hashes `9beaab56a1cb25cae4d0fa9c45961491` and `e02d87833be94d9721cb73f91339e6c7`)
each sit in three folders under three different labels, which is the whole dispute in two examples; the copies
can be pulled from the VM with `vm/ops/` tooling if a reviewer wants to see them.

## What it means for the dataset

| | Pictures |
|---|---|
| Defect-class dataset today, Clear excluded | **8,401** |
| If Clear becomes a 23rd class | **10,606** |
| If the 8 unlabelled HEMA images are also assigned | **10,614** |

Two rules land on the same total: Clear taking only its 2,205 exclusive pictures, or Clear taking all 2,333
with the 128 leaving their defect class. The 128 are counted once either way, so the decision changes which
class they belong to, not the size of the dataset. 10,614 is every picture held once repeated copies are
removed, so the arithmetic closes.

Where the 2,205 sit: L24 1,495, L26 283, L27 272, L31 135, L25 20. Clear as a class would be 75 times larger
on L24 than on L25, and on L24 it would be the largest class (1,495 against Missing Primary Package at 1,147).

## How it was verified

Two independent checks, both recorded because the lead asked for extra certainty.

**By content, on the source machine.** `vm/ops/verify_clear_on_vm.py` re-read and re-hashed all 12,079 files in
the three folders on the VM, matched them against `manifest.csv` written at download time (**0 hash
mismatches**), rebuilt the pooled dataset from the files themselves and diffed **48 published numbers** against
the values in this repository. Run it with:

```bash
scp vm/ops/verify_clear_on_vm.py amd-a100-vm:/home/amd100-user/FMD_Data_26082026/
ssh amd-a100-vm 'cd /home/amd100-user/FMD_Data_26082026 && nohup python3 -u verify_clear_on_vm.py > verify_clear.log 2>&1 &'
ssh amd-a100-vm 'cat /home/amd100-user/FMD_Data_26082026/verify_clear.log'
```

It reproduces 12,079 files, 10,614 unique pictures, 8,401 in the defect-class dataset, 2,213 with no defect
label, the 2,333 / 128 / 2,205 Clear split, the five line totals and the class-by-line matrix.

**By file name, in both directions.** Of the 128 Clear images that also carry a defect class, **123 carry
exactly the same file name in the Clear folder as in the defect folder** and **5 are filed under a different
name**, differing only by two appended score fields (for example `..._C1_9761_0.9994_0.4434.bmp` against
`..._C1_9761.bmp`). In the other direction **no file name appears in two folders over different content**, so a
name match is never a false merge. Publish both figures together: a stakeholder re-checking by filename finds
123 of 128, and that difference is a difference between two methods, not a disagreement about the data.

## Superseded numbers

Do not reuse these. Each was published once and corrected after verification.

| Retired | Correct | What happened |
|---|---|---|
| 1,278 pictures in more than one folder | **1,226** | Transposed by hand from the Foreign Matter class total, which is also 1,278 and appears on the same page. The generated page was right; the hand-written prose was wrong in four places |
| 1,225 library files overlapping the new drop | **1,287 by content, 1,249 by name** | An unverified figure in HANDOFF and the basic lead message; the verified pair replaces it, and 38 library files are the same picture under a different name |
| 1,278 files counted twice | **1,465 redundant files** | A name-based overlap count presented as a file count; the content-based total is 12,079 files to 10,614 pictures |
| Test 70% / Test 80% column headers | **Test (30%) / Test (20%)** | The percentage belongs to the column's share, not the split's name |

Standing lesson: a number that is wrong because it was transposed is invisible to a "does this number appear on
the page" check, because it is another correct total from the same page. Diff prose figures against the source
table, or re-derive the whole set from the data.

## Open decision

Whether "Clear" becomes a 23rd class. The evidence says it behaves as a review status ("no visible defect
seen") rather than a defect class: 94.5 percent of its images carry no other label, and the 5.5 percent that do
collide with six subtle classes only. Adding it tests whether a model separates clean from defective; it does
not test defect discrimination, and it changes every per-line table in the line analysis.
