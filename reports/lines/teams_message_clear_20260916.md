# Teams message: the Clear tag numbers (2026-09-16)

Self-contained, no local paths, no cross-references, every claim carries its number in
the same sentence. Re-verified on the analysis machine before sending.

---

**Clear tag: the exact numbers**

We hold **2,333 "Clear" images**, all of them different pictures. Of those:

| | Images |
|---|---|
| "Clear" images that also carry a defect class | **128** |
| "Clear" images that carry no other label | **2,205** |
| Total "Clear" images | **2,333** |

**How many classes are involved: 6.** Those 128 images are also labelled with six defect classes, as follows:

| Defect class the "Clear" image is also labelled with | Images |
|---|---|
| Bubble | 37 |
| Wet Package | 34 |
| Dirty Strobe | 16 |
| Bubble Irregular | 16 |
| Bubble Cluster | 15 |
| Dirty Camera | 10 |
| **Total** | **128** |

Two further class names appear only in the new drop, on 2 of those same 128 images: Lens Off Center (1) and Multiple Lenses (1), where the older library labels both of those images Wet Package. So the count of class names that touch "Clear" is **6 in the canonical taxonomy, or 8 across both sources**.

**What it means for the dataset.** The defect-class dataset holds **8,401 pictures** today, with "Clear" left out. If "Clear" is added as a 23rd class the dataset becomes **10,606 pictures**, which is 8,401 plus the 2,205 that carry no other label; the 128 that already carry a defect class are inside the 8,401 under that class and are not added twice. Assigning the 8 unlabelled HEMA images to HEMA Fragment or HEMA Obstruction brings the total to **10,614**, which is every picture we hold once the repeated copies are removed.

**Where the 2,205 sit, line by line.**

| Line | "Clear" images with no other label |
|---|---|
| L24 | 1,495 |
| L26 | 283 |
| L27 | 272 |
| L31 | 135 |
| L25 | 20 |
| **All lines** | **2,205** |

**How this was checked.** Every file was re-hashed on the analysis machine: all 12,079 delivered files were read, their hashes matched the storage listing with 0 mismatches, and the counts above were re-derived from the files themselves. The same run reproduced 10,614 unique pictures, 8,401 pictures in the defect-class dataset, 2,213 pictures with no defect label, and the line totals L24 2,853, L25 951, L26 1,220, L27 1,365, L31 2,012.
