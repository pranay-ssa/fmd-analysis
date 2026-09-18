# Class subset split: the six classes the lead highlighted

Built by `src/build_class_subset_splits.py` from the full per-line assignment in
`run/line_splits_20260917/`. A picture keeps the train or test side it already had, so this
subset run and the full run score the same pictures on the same side.

Classes: Missing Primary Package, Multiple Lenses, Foreign Matter, Lens Off Center, Missing Lens, HEMA Obstruction

| Line | Pictures | Train | Test |
|---|---|---|---|
| L24 | 2298 | 1608 | 690 |
| L25 | 578 | 404 | 174 |
| L26 | 856 | 599 | 257 |
| L27 | 725 | 507 | 218 |
| L31 | 438 | 306 | 132 |
| **All five** | **4895** | **3424** | **1471** |

All six classes are present on all five lines, so every line trains and scores all six.
